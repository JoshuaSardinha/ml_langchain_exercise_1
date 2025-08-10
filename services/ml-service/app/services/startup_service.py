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
    
    def _are_documents_processed(self) -> bool:
        """Check if documents are already processed in vector database"""
        try:
            if not self.vectordb_path.exists():
                logger.info("Vector database directory not found")
                return False
            
            doc_service = LangChainDocumentService()
            stats = doc_service.get_stats()
            
            if "error" in stats:
                logger.info(f"Vector database not accessible or has error: {stats.get('error', 'unknown error')}")
                return False
            
            doc_count = stats.get("total_chunks", 0)
            
            llm_configured = stats.get("llm_configured", False)
            rag_available = stats.get("rag_chain_available", False)
            
            if doc_count > 0:
                logger.info(f"Found {doc_count} document chunks in vector database")
                if not llm_configured:
                    logger.warning("Documents processed but LLM not configured")
                if not rag_available:
                    logger.warning("Documents processed but RAG chain not available")
                return True
            else:
                logger.info("Vector database exists but contains no documents")
                return False
                
        except Exception as e:
            logger.warning(f"Error checking document processing status: {e}")
            return False
    
    def _train_models(self) -> bool:
        """Train ML models using the existing training logic"""
        try:
            logger.info("="*60)
            logger.info("Starting ML model training...")
            logger.info("="*60)
            
            # Initialize services
            data_service = DataService(data_path="data/raw/patient_data.csv")
            ml_service = MLService(data_service=data_service, auto_load_models=False)
            
            # Log data summary
            summary = data_service.get_data_summary()
            logger.info(f"Loaded {summary['total_patients']} patients with {summary['features']} features")
            
            # Train COPD classifier
            logger.info("Training COPD classifier...")
            copd_metrics = ml_service.train_copd_classifier(
                test_size=0.2,
                random_state=42,
                use_grid_search=True
            )
            logger.info(f"COPD Classifier - Accuracy: {copd_metrics['accuracy']:.3f}, F1: {copd_metrics['f1_score']:.3f}")
            
            # Train ALT regressor  
            logger.info("Training ALT regressor...")
            alt_metrics = ml_service.train_alt_regressor(
                test_size=0.2,
                random_state=42,
                use_grid_search=True
            )
            logger.info(f"ALT Regressor - R²: {alt_metrics['r2_score']:.3f}, MAE: {alt_metrics['mae']:.3f}")
            
            # Save models
            logger.info("Saving trained models...")
            ml_service.save_models()
            
            logger.info("="*60)
            logger.info("ML model training completed successfully!")
            logger.info("="*60)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to train models: {e}")
            return False
    
    def _process_documents(self) -> bool:
        """Process documents using the existing LangChain service"""
        try:
            logger.info("="*60)
            logger.info("Starting document processing...")
            logger.info("="*60)
            
            doc_service = LangChainDocumentService()
            
            stats = doc_service.get_stats()
            existing_chunks = stats.get("total_chunks", 0)
            
            force_reprocess = existing_chunks == 0 or "error" in stats
            
            if force_reprocess:
                logger.info("No existing documents found or vector store not properly initialized, will process documents")
            
            result = doc_service.process_documents(force_reprocess=force_reprocess)
            
            if "error" in result:
                logger.error(f"Document processing failed: {result['error']}")
                return False
            
            if result["status"] == "already_processed":
                logger.info(f"Documents already processed ({result['total_documents']} chunks)")
            else:
                logger.info(f"Processed {result['documents_processed']} documents into {result['total_chunks']} chunks")
            
            logger.info("="*60)
            logger.info("Document processing completed successfully!")
            logger.info("="*60)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to process documents: {e}")
            return False
    
    def initialize_system(self) -> Dict[str, Any]:
        """Initialize the system by ensuring models are trained and documents are processed"""
        logger.info("="*80)
        logger.info("🚀 INITIALIZING DATA DOCTOR SYSTEM")
        logger.info("="*80)
        
        initialization_status = {
            "models_trained": False,
            "documents_processed": False,
            "initialization_successful": False,
            "errors": []
        }
        
        try:
            # Check and train models if needed
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
            
            # Check and process documents if needed
            if self._are_documents_processed():
                logger.info("✅ Documents are already processed and ready")
                initialization_status["documents_processed"] = True
            else:
                logger.info("⏳ Documents not processed, processing now...")
                if self._process_documents():
                    initialization_status["documents_processed"] = True
                    logger.info("✅ Documents processed successfully")
                else:
                    error_msg = "Failed to process documents"
                    logger.error(f"❌ {error_msg}")
                    initialization_status["errors"].append(error_msg)
            
            # Determine overall success
            initialization_status["initialization_successful"] = (
                initialization_status["models_trained"] and 
                initialization_status["documents_processed"]
            )
            
            if initialization_status["initialization_successful"]:
                logger.info("="*80)
                logger.info("🎉 SYSTEM INITIALIZATION COMPLETED SUCCESSFULLY!")
                logger.info("📊 ML models are trained and ready for predictions")
                logger.info("📚 Documents are processed and ready for search")
                logger.info("🌐 API endpoints are now ready to accept requests")
                logger.info("="*80)
            else:
                logger.error("="*80)
                logger.error("💥 SYSTEM INITIALIZATION FAILED!")
                logger.error("The following components failed to initialize:")
                for error in initialization_status["errors"]:
                    logger.error(f"   • {error}")
                logger.error("API will start but some endpoints may not work properly")
                logger.error("="*80)
            
        except Exception as e:
            error_msg = f"Unexpected error during system initialization: {e}"
            logger.error(f"💥 {error_msg}")
            initialization_status["errors"].append(error_msg)
        
        return initialization_status