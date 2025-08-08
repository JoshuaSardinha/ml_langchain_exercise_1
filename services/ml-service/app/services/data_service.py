import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
import json
from datetime import datetime
import logging

from ..utils.preprocessing import DataPreprocessor, prepare_features_for_prediction

logger = logging.getLogger(__name__)

class DataService:
    """Service for handling patient data operations"""
    
    def __init__(self, data_path: str = None):
        self.data_path = Path(data_path) if data_path else Path("data/raw/patient_data.csv")
        self.preprocessor = DataPreprocessor()
        self.df = None
        self.df_processed = None
        self._load_data()
        
    def _load_data(self) -> bool:
        """Load patient data from CSV"""
        try:
            if self.data_path.exists():
                self.df = pd.read_csv(self.data_path)
                logger.info(f"Loaded {len(self.df)} patient records")
                return True
            else:
                logger.warning(f"Data file not found at {self.data_path}")
                return False
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return False
    
    def get_dataframe(self) -> pd.DataFrame:
        """Get the loaded dataframe"""
        if self.df is None:
            self._load_data()
        return self.df if self.df is not None else pd.DataFrame()
    
    def get_data_summary(self) -> Dict[str, Any]:
        """Get summary statistics of the dataset"""
        if self.df is None:
            return {"error": "Data not loaded"}
        
        return {
            "total_patients": len(self.df),
            "features": len(self.df.columns) - 3,  # Exclude patient_id and targets
            "missing_values": self.df.isnull().sum().to_dict(),
            "copd_distribution": self.df['chronic_obstructive_pulmonary_disease'].value_counts().to_dict(),
            "alt_stats": {
                "mean": float(self.df['alanine_aminotransferase'].mean()),
                "std": float(self.df['alanine_aminotransferase'].std()),
                "min": float(self.df['alanine_aminotransferase'].min()),
                "max": float(self.df['alanine_aminotransferase'].max())
            },
            "age_distribution": {
                "mean": float(self.df['age'].mean()),
                "min": int(self.df['age'].min()),
                "max": int(self.df['age'].max())
            },
            "smoker_percentage": float((self.df['smoker'] == 'Yes').mean() * 100)
        }
    
    def query_patients(self, query: Dict[str, Any]) -> pd.DataFrame:
        """Query patients based on filters"""
        if self.df is None:
            return pd.DataFrame()
        
        result = self.df.copy()
        
        for key, value in query.items():
            if key in result.columns:
                if isinstance(value, dict):
                    if 'min' in value:
                        result = result[result[key] >= value['min']]
                    if 'max' in value:
                        result = result[result[key] <= value['max']]
                    if 'in' in value:
                        result = result[result[key].isin(value['in'])]
                else:
                    result = result[result[key] == value]
        
        return result
    
    def get_patient_by_id(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific patient by ID"""
        if self.df is None:
            return None
        
        patient = self.df[self.df['patient_id'] == patient_id]
        if len(patient) > 0:
            return patient.iloc[0].to_dict()
        return None
    
    def analyze_feature_correlations(self) -> Dict[str, Any]:
        """Analyze feature correlations with target variables"""
        if self.df is None:
            return {"error": "Data not loaded"}
        
        df_encoded = self.df.copy()
        df_encoded = df_encoded.drop('patient_id', axis=1)
        
        df_encoded['exercise_frequency'] = df_encoded['exercise_frequency'].fillna('Unknown')
        df_encoded['education_level'] = df_encoded['education_level'].fillna('Unknown')
        
        categorical_cols = df_encoded.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            df_encoded[col] = pd.Categorical(df_encoded[col]).codes
        
        corr_matrix = df_encoded.corr()
        
        copd_corr = corr_matrix['chronic_obstructive_pulmonary_disease'].abs().sort_values(ascending=False)[1:11]
        alt_corr = corr_matrix['alanine_aminotransferase'].abs().sort_values(ascending=False)[1:11]
        
        return {
            "copd_top_correlations": copd_corr.to_dict(),
            "alt_top_correlations": alt_corr.to_dict()
        }
    
    def get_training_data(self, target: str = 'copd') -> Tuple[pd.DataFrame, pd.Series]:
        """Get preprocessed training data"""
        if self.df is None:
            raise ValueError("Data not loaded")
        
        X = self.df.drop(['patient_id', 'chronic_obstructive_pulmonary_disease', 
                         'alanine_aminotransferase'], axis=1)
        
        if target == 'copd':
            y = self.df['chronic_obstructive_pulmonary_disease']
        elif target == 'alt':
            y = self.df['alanine_aminotransferase']
        else:
            raise ValueError(f"Unknown target: {target}")
        
        return X, y
    
    def preprocess_data(self, X: pd.DataFrame, fit: bool = False) -> np.ndarray:
        """Preprocess data using the preprocessing pipeline"""
        if fit:
            return self.preprocessor.fit_transform(X)
        else:
            return self.preprocessor.transform(X)
    
    def prepare_prediction_input(self, patient_data: Dict[str, Any]) -> np.ndarray:
        """Prepare single patient data for prediction"""
        df = prepare_features_for_prediction(patient_data)
        return self.preprocessor.transform(df)
    
    def get_feature_statistics(self, feature: str) -> Dict[str, Any]:
        """Get statistics for a specific feature"""
        if self.df is None or feature not in self.df.columns:
            return {"error": f"Feature {feature} not found"}
        
        feature_data = self.df[feature]
        
        if feature_data.dtype in ['int64', 'float64']:
            return {
                "type": "numerical",
                "mean": float(feature_data.mean()),
                "std": float(feature_data.std()),
                "min": float(feature_data.min()),
                "max": float(feature_data.max()),
                "median": float(feature_data.median()),
                "q25": float(feature_data.quantile(0.25)),
                "q75": float(feature_data.quantile(0.75)),
                "missing": int(feature_data.isna().sum()),
                "unique": int(feature_data.nunique())
            }
        else:
            value_counts = feature_data.value_counts().to_dict()
            return {
                "type": "categorical",
                "value_counts": {str(k): int(v) for k, v in value_counts.items()},
                "unique": int(feature_data.nunique()),
                "missing": int(feature_data.isna().sum()),
                "mode": str(feature_data.mode()[0]) if not feature_data.mode().empty else None
            }
    
    def generate_analytics_response(self, query: str) -> Dict[str, Any]:
        """Generate analytics response based on natural language query"""
        query_lower = query.lower()
        
        if "how many" in query_lower:
            if "patient" in query_lower or "total" in query_lower:
                return {
                    "answer": f"There are {len(self.df)} patients in the dataset.",
                    "data": {"total_patients": len(self.df)}
                }
            elif "smoker" in query_lower:
                smokers = (self.df['smoker'] == 'Yes').sum()
                percentage = (smokers / len(self.df)) * 100
                return {
                    "answer": f"There are {smokers} smokers in the dataset, representing {percentage:.1f}% of all patients.",
                    "data": {
                        "smokers": int(smokers),
                        "non_smokers": int(len(self.df) - smokers),
                        "percentage": float(percentage)
                    },
                    "visualization": {
                        "type": "bar",
                        "data": [
                            {"name": "Smokers", "value": int(smokers)},
                            {"name": "Non-smokers", "value": int(len(self.df) - smokers)}
                        ]
                    }
                }
        
        elif "average" in query_lower or "mean" in query_lower:
            if "age" in query_lower:
                mean_age = self.df['age'].mean()
                return {
                    "answer": f"The average age of patients is {mean_age:.1f} years.",
                    "data": {"mean_age": float(mean_age)}
                }
            elif "bmi" in query_lower:
                mean_bmi = self.df['bmi'].mean()
                return {
                    "answer": f"The average BMI is {mean_bmi:.1f}.",
                    "data": {"mean_bmi": float(mean_bmi)}
                }
            elif "alt" in query_lower or "alanine" in query_lower:
                mean_alt = self.df['alanine_aminotransferase'].mean()
                std_alt = self.df['alanine_aminotransferase'].std()
                return {
                    "answer": f"The average ALT value is {mean_alt:.1f} ± {std_alt:.1f}.",
                    "data": {"mean_alt": float(mean_alt), "std_alt": float(std_alt)}
                }
        
        elif "distribution" in query_lower:
            if "copd" in query_lower or "chronic" in query_lower:
                copd_dist = self.df['chronic_obstructive_pulmonary_disease'].value_counts().to_dict()
                return {
                    "answer": f"COPD classification distribution: " + 
                             ", ".join([f"{k}: {v}" for k, v in copd_dist.items()]),
                    "data": copd_dist,
                    "visualization": {
                        "type": "pie",
                        "data": [{"name": k, "value": int(v)} for k, v in copd_dist.items()]
                    }
                }
        
        elif "correlation" in query_lower:
            correlations = self.analyze_feature_correlations()
            return {
                "answer": "Here are the top feature correlations with the target variables.",
                "data": correlations
            }
        
        return {
            "answer": "I can help you analyze the patient dataset. Try asking about patient counts, averages, distributions, or correlations.",
            "data": self.get_data_summary()
        }
    
    def save_preprocessor(self, filepath: str):
        """Save the fitted preprocessor"""
        self.preprocessor.save(filepath)
    
    def load_preprocessor(self, filepath: str):
        """Load a fitted preprocessor"""
        self.preprocessor = DataPreprocessor.load(filepath)