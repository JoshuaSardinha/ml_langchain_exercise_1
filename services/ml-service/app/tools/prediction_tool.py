import logging
import numpy as np
from typing import Dict, Any, Optional, List
from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolRun
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PredictionInput(BaseModel):
    """Input schema for PredictionTool"""
    target: str = Field(
        description="Target to predict: 'copd' or 'chronic_obstructive_pulmonary_disease' for COPD, 'alt' or 'alanine_aminotransferase' for ALT"
    )
    age: float = Field(description="Patient age in years")
    sex: str = Field(description="Patient sex: 'Male' or 'Female'")
    bmi: float = Field(description="Body Mass Index")
    medication_count: int = Field(description="Number of medications")
    exercise_frequency: Optional[str] = Field(
        default="Rarely",
        description="Exercise frequency: 'Daily', 'Weekly', 'Rarely'"
    )
    diet_quality: Optional[str] = Field(
        default="Poor",
        description="Diet quality: 'Excellent', 'Good', 'Poor'"
    )
    smoker: Optional[bool] = Field(default=False, description="Whether patient is a smoker (true/false)")
    days_hospitalized: Optional[int] = Field(default=0, description="Days hospitalized")
    readmitted: Optional[bool] = Field(default=False, description="Whether patient was readmitted")
    urban_rural: Optional[str] = Field(
        default="Urban",
        description="Living area: 'Urban' or 'Rural'"
    )


class PredictionTool(BaseTool):
    """Tool for making predictions using trained ML models"""
    
    name: str = "prediction"
    description: str = """Useful for predicting patient health outcomes: COPD classification and ALT levels."""
    args_schema: type = PredictionInput
    ml_service: Optional[Any] = None
    
    def __init__(self, ml_service=None, **kwargs):
        super().__init__(ml_service=ml_service, **kwargs)
    
    def _run(
        self,
        target: str,
        age: float,
        sex: str,
        bmi: float,
        medication_count: int,
        exercise_frequency: str = "Rarely",
        diet_quality: str = "Poor",
        smoker: bool = False,
        days_hospitalized: int = 0,
        readmitted: bool = False,
        urban_rural: str = "Urban",
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Execute the prediction"""
        try:
            if not self.ml_service:
                return "Error: ML service not initialized"
            
            patient_data = self._map_to_training_schema(
                age=age,
                sex=sex,
                bmi=bmi,
                medication_count=medication_count,
                exercise_frequency=exercise_frequency,
                diet_quality=diet_quality,
                smoker=smoker,
                days_hospitalized=days_hospitalized,
                readmitted=readmitted,
                urban_rural=urban_rural
            )
            
            target_lower = target.lower()
            if 'copd' in target_lower or 'chronic_obstructive' in target_lower:
                result = self.ml_service.predict_copd(patient_data)
            elif 'alt' in target_lower or 'alanine' in target_lower:
                result = self.ml_service.predict_alt(patient_data)
            else:
                return f"Error: Unknown prediction target '{target}'. Use 'copd' or 'alt'"
            
            if 'error' in result:
                return f"Error making prediction: {result['error']}"
            
            return self._format_prediction_result(result, target)
            
        except Exception as e:
            logger.error(f"Error making prediction: {e}")
            return f"Error making prediction: {str(e)}"
    
    async def _arun(self, *args, **kwargs):
        """Async version not implemented"""
        raise NotImplementedError("PredictionTool does not support async")
    
    def _map_to_training_schema(self, **kwargs) -> Dict[str, Any]:
        """Map agent parameters to training data schema"""

        patient_data = {
            'age': kwargs['age'],
            'sex': kwargs['sex'],
            'bmi': kwargs['bmi'],
            'medication_count': kwargs['medication_count'],
            'days_hospitalized': kwargs['days_hospitalized'],
            'exercise_frequency': kwargs['exercise_frequency'],
            'diet_quality': kwargs['diet_quality'],
            
            'smoker': 'Yes' if kwargs['smoker'] else 'No',
            
            'readmitted': 1 if kwargs['readmitted'] else 0,
            
            'urban': 1 if kwargs['urban_rural'].lower() == 'urban' else 0,
            
            'diagnosis_code': 'D2',  # Default middle diagnosis code
            'last_lab_glucose': 95.0,  # Normal glucose level
            'income_bracket': 'Middle',  # Default middle income
            'education_level': 'Secondary',  # Default secondary education
            'albumin_globulin_ratio': 0.65  # Normal albumin/globulin ratio
        }
        
        return patient_data
    
    def _format_prediction_result(self, result: Dict[str, Any], target: str) -> str:
        """Format prediction result for display"""
        target_lower = target.lower()
        
        if 'copd' in target_lower or 'chronic_obstructive' in target_lower:
            response = f"COPD Prediction: Class {result['prediction']}\n"
            response += f"Confidence: {result['confidence']*100:.1f}%\n"
            
            if 'class_probabilities' in result:
                response += "\nClass Probabilities:\n"
                for class_name, prob in result['class_probabilities'].items():
                    response += f"- Class {class_name}: {prob*100:.1f}%\n"
            
            if 'top_features' in result:
                response += f"\nTop Features: {', '.join(result['top_features'][:5])}\n"
            
            copd_class = result['prediction']
            if copd_class == 'A':
                response += "\nInterpretation: Low risk, few symptoms"
            elif copd_class == 'B':
                response += "\nInterpretation: Low risk, more symptoms"
            elif copd_class == 'C':
                response += "\nInterpretation: High risk, few symptoms"
            else:  # D
                response += "\nInterpretation: High risk, more symptoms"
                
        else:
            response = f"ALT Prediction: {result['prediction']:.1f} U/L\n"
            
            if 'reference_range' in result:
                ref = result['reference_range']
                response += f"Normal Range: {ref['normal_min']}-{ref['normal_max']} {ref['unit']}\n"
            
            response += f"Confidence: {result['confidence']*100:.1f}%\n"
            
            if 'prediction_interval' in result:
                interval = result['prediction_interval']
                response += f"95% Prediction Interval: ({interval['lower']:.1f}, {interval['upper']:.1f}) U/L\n"
            
            if 'top_features' in result:
                response += f"Top Features: {', '.join(result['top_features'][:5])}"
        
        return response