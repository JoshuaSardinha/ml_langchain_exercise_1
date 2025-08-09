from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging

from .config import settings
from .api.endpoints import router
from .services.startup_service import StartupService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Data Doctor ML Service...")
    
    # Initialize system: train models and process documents if needed
    startup_service = StartupService()
    initialization_result = startup_service.initialize_system()
    
    # Store initialization result for potential use by endpoints
    app.state.initialization_result = initialization_result
    
    if not initialization_result["initialization_successful"]:
        logger.warning("System initialization completed with errors - some API endpoints may not work properly")
    
    yield
    logger.info("Shutting down Data Doctor ML Service...")

app = FastAPI(
    title="Data Doctor ML Service",
    description="AI Health Assistant with predictive modeling, data analytics, and document search",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Data Doctor ML Service is running", "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG
    )