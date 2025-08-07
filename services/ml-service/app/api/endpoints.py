from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ml-service",
        "version": "1.0.0",
        "models_loaded": False,  # Will be updated when models are loaded
        "vectordb_ready": False  # Will be updated when vector DB is ready
    }

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
            "/api/v1/search-docs"
        ]
    }