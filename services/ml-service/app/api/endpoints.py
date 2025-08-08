from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional
import logging

from ..models.schemas import HealthResponse
from pydantic import BaseModel
from typing import Union
from ..services.langchain_service import LangChainDocumentService
from ..services.chat_service import ChatService
from ..config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Request models
class PredictionRequest(BaseModel):
    target: str  # 'copd' or 'alt'
    age: float
    sex: str
    bmi: float
    medication_count: int
    exercise_frequency: Optional[str] = "Rarely"
    diet_quality: Optional[str] = "Poor"
    smoker: Optional[str] = "No"
    days_hospitalized: Optional[int] = 0
    readmitted: Optional[int] = 0
    urban: Optional[int] = 1

class QueryDataRequest(BaseModel):
    query: str

langchain_service: LangChainDocumentService = None
chat_service: ChatService = None

def get_document_service() -> LangChainDocumentService:
    """Get or create document service instance"""
    global langchain_service
    if langchain_service is None:
        try:
            langchain_service = LangChainDocumentService(
                docs_path=settings.DOCS_DIR,
                vectordb_path=settings.VECTORDB_DIR,
                embedding_model=settings.EMBEDDING_MODEL
            )
        except Exception as e:
            logger.error(f"Failed to initialize document service: {e}")
            raise HTTPException(status_code=500, detail=f"Document service initialization failed: {e}")
    return langchain_service

def get_chat_service() -> ChatService:
    """Get or create chat service instance"""
    global chat_service
    if chat_service is None:
        try:
            chat_service = ChatService()
        except Exception as e:
            logger.error(f"Failed to initialize chat service: {e}")
            raise HTTPException(status_code=500, detail=f"Chat service initialization failed: {e}")
    return chat_service

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    vectordb_ready = False
    ml_models_loaded = False
    
    try:
        doc_service = get_document_service()
        vectordb_ready = doc_service.vector_store is not None
    except Exception as e:
        logger.warning(f"Document service health check warning: {e}")
    
    try:
        chat_svc = get_chat_service()
        if chat_svc.ml_service:
            model_status = chat_svc.ml_service.are_models_loaded()
            ml_models_loaded = model_status.get("any_model_loaded", False)
    except Exception as e:
        logger.warning(f"ML service health check warning: {e}")
    
    return HealthResponse(
        status="healthy",
        service="ml-service", 
        version="1.0.0",
        models_loaded=ml_models_loaded,
        vectordb_ready=vectordb_ready
    )

@router.get("/status")
async def service_status():
    """Detailed service status"""
    return {
        "service": "Data Doctor ML Service",
        "status": "running",
        "endpoints": [
            "/api/v1/health",
            "/api/v1/status",
            "/api/v1/chat",
            "/api/v1/predict",
            "/api/v1/query-data",
            "/api/v1/search-docs",
            "/api/v1/docs/process",
            "/api/v1/docs/stats"
        ],
        "implementation": "LangChain-powered"
    }

@router.post("/search-docs")
async def search_documents(query: str, use_llm: bool = True, max_results: int = 5):
    """Search medical documents using LangChain-powered semantic similarity"""
    try:
        doc_service = get_document_service()
        result = doc_service.search_documents(
            query=query,
            n_results=max_results,
            use_llm=use_llm
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in document search: {e}")
        raise HTTPException(status_code=500, detail=f"Document search failed: {e}")

@router.post("/docs/process")
async def process_documents(force_reprocess: bool = False):
    """Process medical documents using LangChain and build vector database"""
    try:
        doc_service = get_document_service()
        result = doc_service.process_documents(force_reprocess=force_reprocess)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in document processing: {e}")
        raise HTTPException(status_code=500, detail=f"Document processing failed: {e}")

@router.get("/docs/stats")
async def get_document_stats():
    """Get statistics about processed documents using LangChain"""
    try:
        doc_service = get_document_service()
        stats = doc_service.get_stats()
        
        if "error" in stats:
            raise HTTPException(status_code=400, detail=stats["error"])
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get document stats: {e}")

@router.post("/chat")
async def chat_endpoint(
    message: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None
):
    """Main chat interface using LangChain-powered conversation"""
    try:
        chat_svc = get_chat_service()
        response = chat_svc.chat(message, session_id, user_id)
        return response
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {e}")


@router.get("/chat/status")
async def chat_status():
    """Get chat service system status"""
    try:
        chat_svc = get_chat_service()
        status = chat_svc.get_system_status()
        return status
        
    except Exception as e:
        logger.error(f"Error getting chat status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get chat status: {e}")


@router.post("/predict")
async def predict_endpoint(request: PredictionRequest):
    """Make predictions using ML models"""
    try:
        chat_svc = get_chat_service()
        
        if not chat_svc.ml_service:
            raise HTTPException(status_code=503, detail="ML service not available")
        
        # Convert request to dict format expected by ML service
        patient_data = {
            "age": request.age,
            "sex": request.sex,
            "bmi": request.bmi,
            "medication_count": request.medication_count,
            "exercise_frequency": request.exercise_frequency,
            "diet_quality": request.diet_quality,
            "smoker": request.smoker,
            "days_hospitalized": request.days_hospitalized,
            "readmitted": request.readmitted,
            "urban": request.urban
        }
        
        if request.target.lower() in ['copd', 'chronic_obstructive_pulmonary_disease']:
            result = chat_svc.ml_service.predict_copd(patient_data)
        elif request.target.lower() in ['alt', 'alanine_aminotransferase']:
            result = chat_svc.ml_service.predict_alt(patient_data)
        else:
            raise HTTPException(status_code=400, detail="Invalid target. Use 'copd' or 'alt'")
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in prediction endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")


@router.post("/query-data")
async def query_data_endpoint(request: QueryDataRequest):
    """Query patient data using natural language"""
    try:
        chat_svc = get_chat_service()
        
        if not chat_svc.data_service:
            raise HTTPException(status_code=503, detail="Data service not available")
        
        result = chat_svc.data_service.generate_analytics_response(request.query)
        return result
        
    except Exception as e:
        logger.error(f"Error in query data endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Data query failed: {e}")


