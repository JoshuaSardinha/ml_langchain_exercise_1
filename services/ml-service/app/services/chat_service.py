import os
import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from dotenv import load_dotenv

from app.services.langchain_service import LangChainDocumentService
from app.services.data_service import DataService
from app.services.ml_service import MLService
from app.agents.medical_agent import MedicalAgent
from app.config import settings

load_dotenv()
logger = logging.getLogger(__name__)


class ChatService:
    """
    Main orchestration service that manages conversations and coordinates
    between the medical agent, document service, data service, and ML service
    """
    
    def __init__(self):
        # Initialize all services
        self.data_service = None
        self.ml_service = None
        self.document_service = None
        self.agent = None
        
        # Session management
        self.active_sessions = {}  # session_id -> session_data
        
        # Initialize services
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize all required services"""
        try:
            logger.info("Initializing chat service components...")
            
            self.data_service = self._init_data_service()
            self.ml_service = self._init_ml_service()
            self.document_service = self._init_document_service()
            self.agent = self._init_medical_agent()
            
            logger.info("Chat service initialization completed")
            
        except Exception as e:
            logger.error(f"Error initializing chat service: {e}")
            raise
    
    def _init_data_service(self):
        """Initialize data service"""
        try:
            service = DataService()
            logger.info("Data service initialized")
            return service
        except Exception as e:
            logger.warning(f"Data service initialization failed: {e}")
            return None
    
    def _init_ml_service(self):
        """Initialize ML service"""
        try:
            service = MLService()
            logger.info("ML service initialized")
            return service
        except Exception as e:
            logger.warning(f"ML service initialization failed: {e}")
            return None
    
    def _init_document_service(self):
        """Initialize document service with LangChain using configured paths"""
        try:
            service = LangChainDocumentService(
                docs_path=settings.DOCS_DIR,
                vectordb_path=settings.VECTORDB_DIR,
                embedding_model=settings.EMBEDDING_MODEL
            )
            logger.info(f"LangChain document service initialized with configured paths: docs={settings.DOCS_DIR}, vectordb={settings.VECTORDB_DIR}")
            return service
        except Exception as e:
            logger.warning(f"Document service initialization failed: {e}")
            return None
    
    def _init_medical_agent(self):
        """Initialize medical agent"""
        try:
            agent = MedicalAgent(
                data_service=self.data_service,
                ml_service=self.ml_service,
                document_service=self.document_service,
                verbose=os.getenv("AGENT_VERBOSE", "true").lower() == "true"
            )
            logger.info("Medical agent initialized")
            return agent
        except Exception as e:
            logger.error(f"Medical agent initialization failed: {e}")
            return None
    
    def create_session(self, user_id: Optional[str] = None) -> str:
        """Create a new conversation session"""
        session_id = str(uuid.uuid4())
        
        self.active_sessions[session_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.now(),
            "last_activity": datetime.now(),
            "message_count": 0,
            "conversation_history": []
        }
        
        logger.info(f"Created new session: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information"""
        return self.active_sessions.get(session_id)
    
    def update_session_activity(self, session_id: str):
        """Update last activity timestamp for session"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["last_activity"] = datetime.now()
    
    def chat(self, 
             message: str, 
             session_id: Optional[str] = None,
             user_id: Optional[str] = None) -> Dict[str, Any]:
        """Main chat interface - processes user messages and returns AI responses"""
        
        session_id = self._ensure_session(session_id, user_id)
        session = self.active_sessions[session_id]
        
        try:
            logger.info(f"Processing message in session {session_id}: {message[:100]}...")
            
            if not self.agent:
                return self._handle_no_agent_response(message, session_id)
            
            if message.startswith('/'):
                return self._handle_command(message, session_id)
            
            response = self.agent.run(message, session_id)
            self._update_session_history(session, message, response)
            
            return self._build_chat_response(session_id, message, response, session)
            
        except Exception as e:
            logger.error(f"Error in chat processing: {e}")
            return self._build_error_response(session_id, message, str(e))
    
    def _ensure_session(self, session_id: Optional[str], user_id: Optional[str]) -> str:
        """Ensure a valid session exists and return session ID"""
        if not session_id or session_id not in self.active_sessions:
            session_id = self.create_session(user_id)
        
        self.update_session_activity(session_id)
        return session_id
    
    def _update_session_history(self, session: Dict[str, Any], message: str, response: Dict[str, Any]):
        """Update session conversation history"""
        session["message_count"] += 1
        session["conversation_history"].append({
            "timestamp": datetime.now(),
            "user_message": message,
            "ai_response": response.get("answer", ""),
            "tools_used": response.get("tools_used", []),
            "success": response.get("success", False)
        })
    
    def _build_chat_response(self, session_id: str, message: str, response: Dict[str, Any], session: Dict[str, Any]) -> Dict[str, Any]:
        """Build chat response dictionary"""
        chat_response = {
            "session_id": session_id,
            "user_message": message,
            "message": response.get("answer", ""),
            "tools_used": response.get("tools_used", []),
            "timestamp": datetime.now().isoformat(),
            "success": response.get("success", False),
            "metadata": {
                "session_info": {
                    "message_count": session["message_count"],
                    "created_at": session["created_at"].isoformat()
                }
            }
        }
        
        if not response.get("success", False):
            chat_response["error"] = response.get("error")
        
        return chat_response
    
    def _build_error_response(self, session_id: str, message: str, error: str) -> Dict[str, Any]:
        """Build error response dictionary"""
        return {
            "session_id": session_id,
            "user_message": message,
            "message": f"I encountered an error while processing your request: {error}",
            "error": error,
            "success": False,
            "timestamp": datetime.now().isoformat()
        }
    
    def _handle_no_agent_response(self, message: str, session_id: str) -> Dict[str, Any]:
        """Handle responses when agent is not available"""
        
        # Try to provide basic responses for common queries
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["help", "hello", "hi"]):
            response = """Hello! I'm the Data Doctor AI assistant. I can help you with:

1. 📊 **Patient Data Analysis**: Ask about statistics, demographics, and trends
2. 🔮 **Health Predictions**: Predict COPD classifications and ALT levels
3. 📚 **Medical Knowledge**: Search clinical documents and medical information  
4. 📈 **Data Visualizations**: Create charts and graphs from patient data

However, I'm currently experiencing some technical difficulties. Please check that:
- API keys are configured (OpenAI, Gemini, or Claude)
- All services are properly initialized

Try asking a simple question like "How many patients are in the dataset?" to test basic functionality."""
        
        elif "status" in message_lower or "health" in message_lower:
            status = self.get_system_status()
            response = f"System Status:\n{self._format_status(status)}"
        
        else:
            response = """I'm sorry, but I'm currently unable to process your request due to a system issue. 

This is likely because:
1. No LLM API key is configured (OpenAI, Gemini, or Claude)
2. Required services failed to initialize
3. Dependencies are missing

Please check the system configuration and try again."""
        
        return {
            "session_id": session_id,
            "user_message": message,
            "message": response,
            "success": False,
            "error": "Agent not available",
            "timestamp": datetime.now().isoformat()
        }
    
    def _handle_command(self, command: str, session_id: str) -> Dict[str, Any]:
        """Handle special slash commands"""
        
        command_lower = command.lower().strip()
        
        if command_lower == "/help":
            response = self._get_help_text()
        elif command_lower == "/status":
            status = self.get_system_status()
            response = self._format_status(status)
        elif command_lower == "/examples":
            response = self._get_examples_text()
        elif command_lower == "/tools":
            response = self._get_tools_text()
        elif command_lower == "/clear":
            if self.agent:
                self.agent.clear_memory()
            response = "Conversation memory cleared."
        elif command_lower == "/session":
            session = self.get_session(session_id)
            response = f"Session Info:\n{self._format_session_info(session)}"
        else:
            response = f"Unknown command: {command}\nType /help for available commands."
        
        return {
            "session_id": session_id,
            "user_message": command,
            "message": response,
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "is_command": True
        }
    
    def _get_help_text(self) -> str:
        """Get help text"""
        return """**Data Doctor AI Assistant - Help**

**Available Commands:**
- `/help` - Show this help message
- `/status` - Show system status
- `/examples` - Show example queries
- `/tools` - Show available tools
- `/clear` - Clear conversation memory
- `/session` - Show session information

**What I can do:**
1. **Data Analysis**: "How many smokers are in the dataset?"
2. **Predictions**: "Predict COPD for 55-year-old male with BMI 27.5..."
3. **Document Search**: "What are the symptoms of seasonal allergies?"
4. **Visualizations**: "Show age distribution" or "Create a bar chart of smokers"

**Tips:**
- Be specific in your questions
- Ask for visualizations to better understand data
- I can combine multiple analyses in one response
- Ask follow-up questions to dive deeper"""
    
    def _get_examples_text(self) -> str:
        """Get example queries"""
        examples = [
            "How many smokers are in the dataset?",
            "Compare lab results across readmitted vs non-readmitted patients",
            "Predict COPD for 55-year-old male with BMI 27.5, 3 medications, rarely exercises",
            "What are the symptoms of seasonal allergies?",
            "Show me the age distribution of patients",
            "How many males older than 40 are readmitted?",
            "Create a scatter plot of BMI vs ALT levels",
            "What medications was the heart attack patient taking?",
            "Summarize treatment plan for diabetic patients over 60"
        ]
        
        return "**Example Queries:**\n\n" + "\n".join(f"• {ex}" for ex in examples)
    
    def _get_tools_text(self) -> str:
        """Get tools information"""
        if not self.agent:
            return "Tools information not available - agent not initialized."
        
        tools = self.agent.get_available_tools()
        response = "**Available Tools:**\n\n"
        
        for tool in tools:
            response += f"**{tool['name']}**: {tool['description']}\n\n"
        
        return response
    
    def _format_status(self, status: Dict[str, Any]) -> str:
        """Format system status for display"""
        response = "**System Status:**\n\n"
        
        response += f"**Overall Ready**: {'✅' if status.get('ready') else '❌'}\n\n"
        
        response += "**Services:**\n"
        services = status.get('services', {})
        for service, available in services.items():
            status_icon = "✅" if available else "❌"
            response += f"- {service.replace('_', ' ').title()}: {status_icon}\n"
        
        response += f"\n**LLM Configured**: {'✅' if status.get('llm_configured') else '❌'}\n"
        response += f"**Tools Available**: {status.get('tools_available', 0)}\n"
        
        env_vars = status.get('environment_vars', {})
        response += f"**API Key Set**: {'✅' if env_vars.get('llm_key_set') else '❌'}\n"
        
        return response
    
    def _format_session_info(self, session: Optional[Dict[str, Any]]) -> str:
        """Format session information"""
        if not session:
            return "Session not found."
        
        return f"""**Session Information:**
- ID: {session['session_id']}
- Created: {session['created_at'].strftime('%Y-%m-%d %H:%M:%S')}
- Last Activity: {session['last_activity'].strftime('%Y-%m-%d %H:%M:%S')}
- Messages: {session['message_count']}
- User ID: {session.get('user_id', 'Anonymous')}"""
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        status = {
            "services": {
                "data_service": self.data_service is not None,
                "ml_service": self.ml_service is not None,
                "document_service": self.document_service is not None,
                "agent": self.agent is not None
            },
            "active_sessions": len(self.active_sessions),
            "environment_vars": {
                "llm_key_set": bool(
                    os.getenv("OPENAI_API_KEY") or 
                    os.getenv("GOOGLE_API_KEY") or 
                    os.getenv("ANTHROPIC_API_KEY")
                )
            }
        }
        
        # Get agent validation if available
        if self.agent:
            agent_status = self.agent.validate_setup()
            status.update(agent_status)
        else:
            status.update({
                "llm_configured": False,
                "tools_available": 0,
                "ready": False
            })
        
        return status
    
    def initialize_documents(self, force_reprocess: bool = False) -> Dict[str, Any]:
        """Initialize document processing"""
        if not self.document_service:
            return {"error": "Document service not available"}
        
        try:
            result = self.document_service.process_documents(force_reprocess=force_reprocess)
            logger.info(f"Document initialization result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error initializing documents: {e}")
            return {"error": str(e)}
    
    def get_conversation_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get conversation history for a session"""
        session = self.get_session(session_id)
        if not session:
            return []
        
        history = session.get("conversation_history", [])
        return history[-limit:] if limit else history
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            logger.info(f"Deleted session: {session_id}")
            return True
        return False
    
    def cleanup_old_sessions(self, hours: int = 24):
        """Clean up sessions older than specified hours"""
        cutoff_time = datetime.now() - datetime.timedelta(hours=hours)
        
        sessions_to_delete = []
        for session_id, session in self.active_sessions.items():
            if session["last_activity"] < cutoff_time:
                sessions_to_delete.append(session_id)
        
        for session_id in sessions_to_delete:
            self.delete_session(session_id)
        
        logger.info(f"Cleaned up {len(sessions_to_delete)} old sessions")
        return len(sessions_to_delete)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        stats = {
            "active_sessions": len(self.active_sessions),
            "total_messages": sum(
                session["message_count"] 
                for session in self.active_sessions.values()
            ),
            "services_status": self.get_system_status()
        }
        
        # Add document service stats
        if self.document_service and hasattr(self.document_service, 'get_stats'):
            try:
                doc_stats = self.document_service.get_stats()
                stats["document_stats"] = doc_stats
            except Exception as e:
                logger.warning(f"Could not get document stats: {e}")
        
        return stats