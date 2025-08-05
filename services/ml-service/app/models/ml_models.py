from typing import Optional, Dict, Any
import joblib
import numpy as np
from pathlib import Path


class MLModelBase:
    """Base class for ML models"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        self.scaler = None
        self.is_loaded = False
        
        if model_path:
            self.load_model(model_path)
    
    def load_model(self, model_path: str) -> bool:
        """Load model from file"""
        try:
            path = Path(model_path)
            if path.exists():
                self.model = joblib.load(model_path)
                self.is_loaded = True
                return True
        except Exception as e:
            print(f"Error loading model: {e}")
        return False
    
    def predict(self, features: np.ndarray) -> Any:
        """Make prediction"""
        if not self.is_loaded:
            raise ValueError("Model not loaded")
        return self.model.predict(features)


class COPDClassifier(MLModelBase):
    """COPD Classification Model"""
    
    def __init__(self, model_path: Optional[str] = None):
        super().__init__(model_path)
        self.classes = ["A", "B", "C", "D"]
    
    def predict_with_confidence(self, features: np.ndarray) -> Dict[str, Any]:
        """Predict COPD class with confidence scores"""
        if not self.is_loaded:
            return {"prediction": None, "confidence": 0.0, "error": "Model not loaded"}
        
        try:
            prediction = self.model.predict(features)[0]
            if hasattr(self.model, "predict_proba"):
                probabilities = self.model.predict_proba(features)[0]
                confidence = float(np.max(probabilities))
            else:
                confidence = 0.8
            
            return {
                "prediction": prediction,
                "confidence": confidence,
                "error": None
            }
        except Exception as e:
            return {"prediction": None, "confidence": 0.0, "error": str(e)}


class ALTRegressor(MLModelBase):
    """ALT Value Regression Model"""
    
    def __init__(self, model_path: Optional[str] = None):
        super().__init__(model_path)
    
    def predict_with_confidence(self, features: np.ndarray) -> Dict[str, Any]:
        """Predict ALT value"""
        if not self.is_loaded:
            return {"prediction": None, "confidence": 0.0, "error": "Model not loaded"}
        
        try:
            prediction = float(self.model.predict(features)[0])
            # For regression, confidence is harder to estimate without additional info
            confidence = 0.75
            
            return {
                "prediction": prediction,
                "confidence": confidence,
                "error": None
            }
        except Exception as e:
            return {"prediction": None, "confidence": 0.0, "error": str(e)}