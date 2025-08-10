import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

from .data_service import DataService
from .ml_service import MLService
from .langchain_service import LangChainDocumentService

logger = logging.getLogger(__name__)

class StartupService:
    """Service for ensuring models are trained and documents are processed on startup"""
    
    def __init__(self):
        self.models_path = Path("data/models")
        self.vectordb_path = Path("data/vectordb_langchain")
        
    def _are_models_trained(self) -> bool:
        """Check if ML models are already trained and saved"""
        try:
            required_files = [
                self.models_path / "copd_classifier.pkl",
                self.models_path / "alt_regressor.pkl",
                self.models_path / "preprocessor.pkl"
            ]
            
            models_exist = all(file.exists() for file in required_files)
            if models_exist:
                logger.info("ML models found on disk")
                return True
            else:
                missing_files = [f.name for f in required_files if not f.exists()]
                logger.info(f"Missing model files: {missing_files}")
                return False
                
        except Exception as e:
            logger.warning(f"Error checking model files: {e}")
            return False
    
    
    def _train_models(self) -> bool:
        """Train ML models using the existing training logic"""
        try:
            logger.info("="*60)
            logger.info("Starting ML model training...")
            logger.info("="*60)
            
            data_service = DataService(data_path="data/raw/patient_data.csv")
            ml_service = MLService(data_service=data_service, auto_load_models=False)
            
            summary = data_service.get_data_summary()
            logger.info(f"Loaded {summary['total_patients']} patients with {summary['features']} features")
            
            logger.info("Training COPD classifier...")
            copd_metrics = ml_service.train_copd_classifier(
                test_size=0.2,
                random_state=42,
                use_grid_search=True
            )
            logger.info(f"COPD Classifier - Accuracy: {copd_metrics['accuracy']:.3f}, F1: {copd_metrics['f1_score']:.3f}")
            
            logger.info("Training ALT regressor...")
            alt_metrics = ml_service.train_alt_regressor(
                test_size=0.2,
                random_state=42,
                use_grid_search=True
            )
            logger.info(f"ALT Regressor - R²: {alt_metrics['r2_score']:.3f}, MAE: {alt_metrics['mae']:.3f}")
            
            logger.info("Saving trained models...")
            ml_service.save_models()
            
            logger.info("="*60)
            logger.info("ML model training completed successfully!")
            logger.info("="*60)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to train models: {e}")
            return False
    
    
    def initialize_system(self) -> Dict[str, Any]:
        """Initialize the system by ensuring models are trained"""
        logger.info("="*80)
        logger.info("🚀 INITIALIZING DATA DOCTOR ML MODELS")
        logger.info("="*80)
        
        initialization_status = {
            "models_trained": False,
            "initialization_successful": False,
            "errors": []
        }
        
        try:
            if self._are_models_trained():
                logger.info("✅ ML models are already trained and ready")
                initialization_status["models_trained"] = True
            else:
                logger.info("⏳ ML models not found, training now...")
                if self._train_models():
                    initialization_status["models_trained"] = True
                    logger.info("✅ ML models trained successfully")
                else:
                    error_msg = "Failed to train ML models"
                    logger.error(f"❌ {error_msg}")
                    initialization_status["errors"].append(error_msg)
            
            initialization_status["initialization_successful"] = initialization_status["models_trained"]
            
            if initialization_status["initialization_successful"]:
                logger.info("="*80)
                logger.info("🎉 ML MODEL INITIALIZATION COMPLETED SUCCESSFULLY!")
                logger.info("📊 ML models are trained and ready for predictions")
                logger.info("📄 Note: Documents must be processed separately using setup-documents.sh")
                logger.info("🌐 API endpoints are now ready to accept requests")
                logger.info("="*80)
            else:
                logger.error("="*80)
                logger.error("💥 ML MODEL INITIALIZATION FAILED!")
                logger.error("The following components failed to initialize:")
                for error in initialization_status["errors"]:
                    logger.error(f"   • {error}")
                logger.error("API will start but ML endpoints may not work properly")
                logger.error("="*80)
            
        except Exception as e:
            error_msg = f"Unexpected error during system initialization: {e}"
            logger.error(f"💥 {error_msg}")
            initialization_status["errors"].append(error_msg)
        
        return initialization_status