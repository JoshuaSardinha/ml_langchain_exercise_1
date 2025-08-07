from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    APP_NAME: str = "Data Doctor ML Service"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    PORT: int = 8000
    
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:4200",
        "http://backend:3000",
        "http://frontend:4200"
    ]
    
    DATA_DIR: str = "data"
    MODELS_DIR: str = "data/models"
    VECTORDB_DIR: str = "data/vectordb"
    DOCS_DIR: str = "data/docs"
    
    COPD_MODEL_PATH: Optional[str] = None
    ALT_MODEL_PATH: Optional[str] = None
    FEATURE_SCALER_PATH: Optional[str] = None
    
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    
    MAX_RESPONSE_TIME: int = 30
    MAX_CONCURRENT_REQUESTS: int = 100
    
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()