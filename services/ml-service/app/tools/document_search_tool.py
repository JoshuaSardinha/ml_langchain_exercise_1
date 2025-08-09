import logging
from typing import Dict, Any, Optional, List
from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolRun
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class DocumentSearchInput(BaseModel):
    """Input schema for DocumentSearchTool"""
    query: str = Field(description="Medical question or topic to search for in documents")
    document_type: Optional[str] = Field(
        default=None,
        description="Filter by document type: 'lab_report', 'discharge_summary', 'clinical_note', 'consultation'"
    )
    patient_id: Optional[str] = Field(
        default=None,
        description="Filter by specific patient ID"
    )
    max_results: int = Field(
        default=5,
        description="Maximum number of documents to return"
    )
    use_llm: bool = Field(
        default=True,
        description="Whether to use LLM for enhanced answering"
    )


class DocumentSearchTool(BaseTool):
    """Tool for searching and retrieving information from medical documents"""
    
    name: str = "document_search"
    description: str = """Useful for finding information from medical documents and clinical knowledge."""
    args_schema: type = DocumentSearchInput
    document_service: Optional[Any] = None
    
    def __init__(self, document_service=None, **kwargs):
        super().__init__(document_service=document_service, **kwargs)
    
    def _run(
        self,
        query: str,
        document_type: Optional[str] = None,
        patient_id: Optional[str] = None,
        max_results: int = 5,
        use_llm: bool = True,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Execute the document search"""
        try:
            if not self.document_service:
                return "Error: Document service not initialized"
            
            if use_llm and hasattr(self.document_service, 'search_documents'):
                result = self.document_service.search_documents(
                    query=query,
                    n_results=max_results,
                    use_llm=use_llm
                )
            else:
                result = self.document_service.search_documents(
                    query=query,
                    n_results=max_results,
                    use_llm=False
                )
            
            return self._format_search_result(result, query)
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return f"Error searching documents: {str(e)}"
    
    async def _arun(self, *args, **kwargs):
        """Async version not implemented"""
        raise NotImplementedError("DocumentSearchTool does not support async")
    
    def _format_search_result(self, result: Dict[str, Any], query: str) -> str:
        """Format search results for display"""
        if "error" in result:
            return f"Search Error: {result['error']}"
        
        if "answer" in result:
            response = f"Answer: {result['answer']}\n\n"
            
            if "sources" in result and result["sources"]:
                response += "Sources:\n"
                for i, source in enumerate(result["sources"][:3], 1):  # Limit to top 3 sources
                    source_info = source.get('metadata', {}).get('source', 'Unknown')
                    response += f"{i}. Document: {source_info}\n"
                    if len(source['content']) > 200:
                        response += f"   Preview: {source['content'][:200]}...\n\n"
                    else:
                        response += f"   Preview: {source['content']}\n\n"
            
            return response
        
        elif "results" in result:
            response = f"Found {result['total_results']} relevant documents:\n\n"
            
            for i, doc in enumerate(result["results"][:3], 1):  # Limit to top 3
                source_info = doc.get('metadata', {}).get('source', 'Unknown')
                response += f"{i}. Document: {source_info}\n"
                
                content = doc.get('content', '')
                if len(content) > 300:
                    response += f"   Content: {content[:300]}...\n\n"
                else:
                    response += f"   Content: {content}\n\n"
            
            return response
        
        return "No results found for your query."
    
    def search_specific_condition(self, condition: str) -> str:
        """Search for specific medical condition information"""
        common_conditions = {
            "seasonal allergies": [
                "seasonal allergies", "hay fever", "allergic rhinitis", 
                "pollen allergy", "environmental allergies"
            ],
            "diabetes": [
                "diabetes", "diabetic", "blood sugar", "insulin", 
                "glucose", "glycemic control"
            ],
            "hypertension": [
                "hypertension", "high blood pressure", "blood pressure", 
                "BP", "antihypertensive"
            ],
            "heart attack": [
                "myocardial infarction", "heart attack", "MI", 
                "cardiac arrest", "coronary event"
            ]
        }
        
        condition_lower = condition.lower()
        search_terms = []
        
        for key, terms in common_conditions.items():
            if key in condition_lower or condition_lower in terms:
                search_terms = terms
                break
        
        if not search_terms:
            search_terms = [condition]
        
        return self._run(search_terms[0])
    
    def search_medications(self, patient_context: str = "") -> str:
        """Search for medication information"""
        if patient_context:
            query = f"medications {patient_context}"
        else:
            query = "medications prescriptions drugs treatment"
        
        return self._run(query, max_results=8)
    
    def search_treatment_plan(self, condition: str, demographics: str = "") -> str:
        """Search for treatment plans for specific conditions"""
        query = f"treatment plan {condition}"
        if demographics:
            query += f" {demographics}"
        
        return self._run(query, max_results=6)
    
    def search_symptoms(self, condition: str) -> str:
        """Search for symptoms of a specific condition"""
        query = f"symptoms {condition} signs presentation"
        return self._run(query, max_results=5)
    
    def search_diagnosis(self, condition: str) -> str:
        """Search for diagnostic information"""
        query = f"diagnosis {condition} diagnostic criteria testing"
        return self._run(query, max_results=5)
    
    def get_document_types_info(self) -> str:
        """Get information about available document types"""
        if self.document_service and hasattr(self.document_service, 'get_stats'):
            stats = self.document_service.get_stats()
            if "document_types" in stats:
                response = "Available document types:\n"
                for doc_type, count in stats["document_types"].items():
                    response += f"- {doc_type.replace('_', ' ').title()}: {count} documents\n"
                return response
        
        return "Document type information not available"