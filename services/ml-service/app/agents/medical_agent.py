import os
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain.tools import BaseTool

from app.tools import DataQueryTool, PredictionTool, DocumentSearchTool, VisualizationTool

try:
    from langchain_openai import ChatOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    ChatGoogleGenerativeAI = None

try:
    from langchain_anthropic import ChatAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

load_dotenv()
logger = logging.getLogger(__name__)


class MedicalAgent:
    """ReAct agent specialized for medical data analysis and document retrieval"""
    
    def __init__(self, 
                 data_service=None,
                 ml_service=None, 
                 document_service=None,
                 verbose: bool = True):
        
        self.data_service = data_service
        self.ml_service = ml_service
        self.document_service = document_service
        self.verbose = verbose
        
        self.llm = self._initialize_llm()
        
        self.tools = self._initialize_tools()
        
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="output"
        )
        
        self.agent_executor = self._initialize_agent()
    
    def _initialize_llm(self):
        """Initialize the Large Language Model"""
        openai_key = os.getenv("OPENAI_API_KEY")
        google_key = os.getenv("GOOGLE_API_KEY")
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        
        if openai_key and OPENAI_AVAILABLE:
            logger.info("Using OpenAI LLM for agent")
            return ChatOpenAI(
                api_key=openai_key,
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                temperature=0.1,  # Lower temperature for more consistent reasoning
                max_tokens=2000
            )
        elif google_key and GEMINI_AVAILABLE:
            logger.info("Using Google Gemini LLM for agent")
            return ChatGoogleGenerativeAI(
                google_api_key=google_key,
                model=os.getenv("GEMINI_MODEL", "gemini-pro"),
                temperature=0.1,
                max_output_tokens=2000
            )
        elif anthropic_key and ANTHROPIC_AVAILABLE:
            logger.info("Using Anthropic Claude LLM for agent")
            return ChatAnthropic(
                api_key=anthropic_key,
                model=os.getenv("CLAUDE_MODEL", "claude-3-opus-20240229"),
                temperature=0.1,
                max_tokens=2000
            )
        else:
            raise ValueError("No LLM API key found. Please set OPENAI_API_KEY, GOOGLE_API_KEY, or ANTHROPIC_API_KEY")
    
    def _initialize_tools(self) -> List[BaseTool]:
        """Initialize all available tools"""
        tools = []
        
        if self.data_service:
            tools.append(DataQueryTool(data_service=self.data_service))
        
        tools.append(PredictionTool(ml_service=self.ml_service))
        
        if self.document_service:
            tools.append(DocumentSearchTool(document_service=self.document_service))
        
        if self.data_service:
            tools.append(VisualizationTool(data_service=self.data_service))
        
        logger.info(f"Initialized {len(tools)} tools: {[tool.name for tool in tools]}")
        return tools
    
    def _initialize_agent(self):
        """Initialize the OpenAI Functions agent executor"""
        if not self.llm:
            raise ValueError("LLM not initialized")
        
        prompt = PromptTemplate.from_template(self._get_agent_prompt())
        
        agent = create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=self.verbose,
            max_iterations=int(os.getenv("AGENT_MAX_ITERATIONS", 10)),
            max_execution_time=int(os.getenv("AGENT_MAX_EXECUTION_TIME", 60)),
            return_intermediate_steps=True
        )
        
        return agent_executor
    
    def _get_agent_prompt(self) -> str:
        """Get the system prompt for the medical agent"""
        return """You are Data Doctor, a medical data analyst AI assistant. You help clinical analysts by:

1. Analyzing patient data and providing insights
2. Making predictions using machine learning models  
3. Searching medical documents and clinical knowledge
4. Creating visualizations to illustrate findings

## Tool Usage Guidelines:

### Data Queries (use data_query tool)
For questions about patient statistics, demographics, and dataset exploration:
- "How many smokers are in the dataset?"
- "How many males older than 40 are readmitted?"
- "How many patients were taking more than 5 medications?"
- "Compare lab results across readmitted vs non-readmitted patients"

### Predictions (use prediction tool)
For health outcome predictions. Extract specific parameter values from natural language queries.

**Required Parameters**: target, age, sex, bmi, medication_count
**Optional Parameters**: exercise_frequency, diet_quality, smoker, days_hospitalized, readmitted, urban_rural

**Parameter Extraction Rules**:
- target: "copd" (for COPD classification) OR "alt" (for ALT regression)
- age: numeric value from "X year old" or "X-year-old" 
- sex: "Male" or "Female"
- bmi: numeric value (e.g., 27.5)
- medication_count: numeric from "takes X medications"
- exercise_frequency: "None", "Rarely", "Weekly", "Daily" (map "doesn't exercise" → "None", "athlete" → "Daily")
- diet_quality: "Poor", "Average", "Good", "Excellent"
- smoker: true/false boolean (default false if not mentioned)
- days_hospitalized: numeric (default 0, extract from "in hospital for X days")
- readmitted: true/false boolean (default false, extract from "readmitted")  
- urban_rural: "Urban" or "Rural" (default "Urban", extract from "center of city" → "Urban")

**Example Predictions**:
- "What is the predicted value for chronic_obstructive_pulmonary_disease for 55 year old male with bmi of 27.5, which takes 3 medications, doesn't exercise, and have poor diet quality?"
- "What is the predicted value for alanine_aminotransferases for woman at 44 years, that has been in a hospital for 5 days, readmitted, athlete that lives in the center of the city?"

### Document Search (use document_search tool)
For medical knowledge, clinical information, and patient-specific medical details from documents:
- "What medications was the heart attack patient taking?"
- "What are the symptoms of seasonal allergies?"
- "Summarize the treatment plan for diabetic patients over 60."
- Questions about treatments, medications, symptoms, diagnoses, or clinical protocols

**IMPORTANT**: Always use document_search for medication-related questions, treatment plans, and clinical information from medical records.

### Visualizations (use visualization tool)
Create charts that support your analysis:
- Bar charts for categories, histograms for distributions, scatter plots for relationships
- Any request for charts, graphs, or data visualization

## Instructions:
- Always think step by step and extract specific parameter values before calling tools
- Use multiple tools when needed for comprehensive answers
- For medication/treatment questions, ALWAYS use document_search first
- Provide context and interpretation for predictions and statistics
- Be accurate, thorough, and clear in your responses

Previous conversation: {chat_history}
Current query: {input}

{agent_scratchpad}"""
    
    def run(self, query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Run the agent with a query"""
        try:
            logger.info(f"Processing query: {query[:100]}...")
            
            result = self.agent_executor.invoke({
                "input": query,
                "chat_history": self.memory.chat_memory.messages if self.memory else []
            })
            
            return {
                "query": query,
                "answer": result["output"],
                "session_id": session_id,
                "intermediate_steps": result.get("intermediate_steps", []),
                "tools_used": [step[0].tool for step in result.get("intermediate_steps", [])],
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error running agent: {e}")
            return {
                "query": query,
                "answer": f"I encountered an error while processing your request: {str(e)}",
                "session_id": session_id,
                "success": False,
                "error": str(e)
            }
    
    def stream_run(self, query: str, session_id: Optional[str] = None):
        """Stream the agent execution (generator)"""
        try:
            result = self.run(query, session_id)
            yield result
            
        except Exception as e:
            yield {
                "query": query,
                "answer": f"Error: {str(e)}",
                "session_id": session_id,
                "success": False,
                "error": str(e)
            }
    
    def get_available_tools(self) -> List[Dict[str, str]]:
        """Get information about available tools"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.args_schema.model_json_schema() if tool.args_schema else None
            }
            for tool in self.tools
        ]
    
    def clear_memory(self):
        """Clear conversation memory"""
        if self.memory:
            self.memory.clear()
            logger.info("Agent memory cleared")
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """Get summary of conversation memory"""
        if not self.memory:
            return {"messages": 0, "memory": []}
        
        messages = self.memory.chat_memory.messages
        return {
            "messages": len(messages),
            "memory": [
                {
                    "type": type(msg).__name__,
                    "content": msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
                }
                for msg in messages[-10:]  # Last 10 messages
            ]
        }
    
    def validate_setup(self) -> Dict[str, Any]:
        """Validate that the agent is properly configured"""
        validation = {
            "llm_configured": self.llm is not None,
            "tools_available": len(self.tools),
            "memory_enabled": self.memory is not None,
            "agent_executor_ready": self.agent_executor is not None,
            "services": {
                "data_service": self.data_service is not None,
                "ml_service": self.ml_service is not None,
                "document_service": self.document_service is not None
            },
            "environment_vars": {
                "llm_key_set": bool(os.getenv("OPENAI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")),
                "agent_max_iterations": os.getenv("AGENT_MAX_ITERATIONS", "10"),
                "agent_max_execution_time": os.getenv("AGENT_MAX_EXECUTION_TIME", "60")
            }
        }
        
        validation["ready"] = (
            validation["llm_configured"] and 
            validation["tools_available"] > 0 and 
            validation["agent_executor_ready"]
        )
        
        return validation
    
    def handle_example_queries(self) -> List[Dict[str, str]]:
        """Get example queries that demonstrate the agent's capabilities"""
        return [
            {
                "category": "Data Statistics",
                "query": "How many smokers are in the dataset?",
                "description": "Uses data_query tool to count smoking patients"
            },
            {
                "category": "Data Comparison", 
                "query": "Compare lab results across readmitted vs non-readmitted patients",
                "description": "Uses data_query and visualization tools for comparison"
            },
            {
                "category": "Prediction",
                "query": "What is the predicted value for chronic_obstructive_pulmonary_disease for 55 year old male with bmi of 27.5, which takes 3 medications, doesn't exercise, and have poor diet quality?",
                "description": "Uses prediction tool with patient features"
            },
            {
                "category": "Medical Knowledge",
                "query": "What are the symptoms of seasonal allergies?",
                "description": "Uses document_search to find clinical information"
            },
            {
                "category": "Data Visualization",
                "query": "Show me the age distribution of patients",
                "description": "Uses visualization tool to create histogram"
            },
            {
                "category": "Complex Analysis",
                "query": "How many males older than 40 are readmitted and show me a chart",
                "description": "Combines data_query and visualization tools"
            }
        ]