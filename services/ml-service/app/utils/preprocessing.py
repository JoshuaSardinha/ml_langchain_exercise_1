import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.preprocessing import StandardScaler, LabelEncoder, OneHotEncoder
from typing import List, Optional, Dict, Any, Union
import joblib
from pathlib import Path


class MissingValueHandler(BaseEstimator, TransformerMixin):
    """Handle missing values with different strategies per column"""
    
    def __init__(self, strategies: Dict[str, str] = None):
        self.strategies = strategies or {
            'exercise_frequency': 'Unknown',
            'education_level': 'Unknown'
        }
        
    def fit(self, X, y=None):
        return self
    
    def transform(self, X):
        X_copy = X.copy()
        for col, strategy in self.strategies.items():
            if col in X_copy.columns:
                if strategy == 'Unknown':
                    X_copy[col] = X_copy[col].fillna('Unknown')
                elif strategy == 'mode':
                    mode_val = X_copy[col].mode()[0] if not X_copy[col].mode().empty else 'Unknown'
                    X_copy[col] = X_copy[col].fillna(mode_val)
                elif strategy == 'mean':
                    X_copy[col] = X_copy[col].fillna(X_copy[col].mean())
                elif strategy == 'median':
                    X_copy[col] = X_copy[col].fillna(X_copy[col].median())
        return X_copy


class FeatureEngineer(BaseEstimator, TransformerMixin):
    """Create engineered features based on domain knowledge"""
    
    def __init__(self, enhanced_features=True):
        self.enhanced_features = enhanced_features
    
    def fit(self, X, y=None):
        return self
    
    def transform(self, X):
        X_copy = X.copy()
        
        # Basic features
        X_copy['age_group'] = pd.cut(X_copy['age'], 
                                     bins=[0, 30, 45, 60, 75, 100],
                                     labels=['<30', '30-45', '45-60', '60-75', '75+'])
        
        X_copy['bmi_category'] = pd.cut(X_copy['bmi'],
                                        bins=[0, 18.5, 25, 30, 35, 100],
                                        labels=['Underweight', 'Normal', 'Overweight', 'Obese_I', 'Obese_II+'])
        
        X_copy['smoker_binary'] = (X_copy['smoker'] == 'Yes').astype(int)
        X_copy['high_glucose'] = (X_copy['last_lab_glucose'] > 110).astype(int)
        X_copy['high_meds'] = (X_copy['medication_count'] > 5).astype(int)
        X_copy['health_risk_score'] = (X_copy['smoker_binary'] + 
                                       X_copy['high_glucose'] + 
                                       X_copy['high_meds'] + 
                                       X_copy['readmitted'])
        
        X_copy['age_bmi_interaction'] = X_copy['age'] * X_copy['bmi'] / 100
        X_copy['smoker_age_risk'] = X_copy['smoker_binary'] * X_copy['age']
        
        X_copy['exercise_missing'] = X_copy['exercise_frequency'].isna().astype(int)
        X_copy['education_missing'] = X_copy['education_level'].isna().astype(int)
        
        if self.enhanced_features:
            X_copy['age_squared'] = X_copy['age'] ** 2
            X_copy['bmi_squared'] = X_copy['bmi'] ** 2
            X_copy['albumin_squared'] = X_copy['albumin_globulin_ratio'] ** 2
            
            X_copy['metabolic_risk'] = (
                (X_copy['bmi'] > 30).astype(int) + 
                (X_copy['last_lab_glucose'] > 110).astype(int) +
                (X_copy['albumin_globulin_ratio'] < 0.5).astype(int)
            )
            
            X_copy['hospitalization_risk'] = (
                X_copy['days_hospitalized'] * X_copy['readmitted'] +
                X_copy['medication_count'] / 10
            )
            
            X_copy['smoker_high_bmi'] = ((X_copy['smoker'] == 'Yes') & (X_copy['bmi'] > 30)).astype(int)
            X_copy['elderly_smoker'] = ((X_copy['age'] > 65) & (X_copy['smoker'] == 'Yes')).astype(int)
        
        return X_copy

class CategoricalEncoder(BaseEstimator, TransformerMixin):
    """Encode categorical variables with appropriate strategies"""
    
    def __init__(self):
        self.encoders = {}
        self.columns_to_encode = {}
        
    def fit(self, X, y=None):
        self.columns_to_encode = {
            'one_hot': ['sex', 'diagnosis_code', 'income_bracket', 'age_group', 'bmi_category'],
            'ordinal': {
                'exercise_frequency': {'Unknown': 0, 'Low': 1, 'Medium': 2, 'High': 3},
                'diet_quality': {'Poor': 0, 'Average': 1, 'Good': 2},
                'education_level': {'Unknown': 0, 'Primary': 1, 'Secondary': 2, 'Tertiary': 3}
            },
            'binary': ['smoker', 'urban', 'readmitted']
        }
        
        for col in self.columns_to_encode['one_hot']:
            if col in X.columns:
                self.encoders[col] = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
                self.encoders[col].fit(X[[col]])
        
        return self
    
    def transform(self, X):
        X_copy = X.copy()
        encoded_dfs = []
        
        cols_to_drop = []
        for col in self.columns_to_encode['one_hot']:
            if col in X_copy.columns:
                encoded = self.encoders[col].transform(X_copy[[col]])
                feature_names = [f"{col}_{cat}" for cat in self.encoders[col].categories_[0]]
                encoded_df = pd.DataFrame(encoded, columns=feature_names, index=X_copy.index)
                encoded_dfs.append(encoded_df)
                cols_to_drop.append(col)
        
        X_copy = X_copy.drop(cols_to_drop, axis=1)
        
        for col, mapping in self.columns_to_encode['ordinal'].items():
            if col in X_copy.columns:
                X_copy[col] = X_copy[col].map(mapping).fillna(0)
        
        for col in self.columns_to_encode['binary']:
            if col in X_copy.columns:
                if col == 'smoker':
                    X_copy[col] = (X_copy[col] == 'Yes').astype(int)
                else:
                    X_copy[col] = X_copy[col].astype(int)
        
        encoded_dfs.insert(0, X_copy)
        result = pd.concat(encoded_dfs, axis=1)
        return result


class DataPreprocessor:
    """Main preprocessing pipeline for patient data"""
    
    def __init__(self, enhanced_features=False):
        self.missing_handler = MissingValueHandler()
        self.feature_engineer = FeatureEngineer(enhanced_features=enhanced_features)
        self.categorical_encoder = CategoricalEncoder()
        self.scaler = StandardScaler()
        self.label_encoder_copd = LabelEncoder()
        self.feature_names = None
        self.numerical_features = None
        self.is_fitted = False
        
    def fit(self, X: pd.DataFrame, y_copd: Optional[pd.Series] = None):
        """Fit the preprocessing pipeline"""

        X_transformed = self.missing_handler.fit_transform(X)
        X_transformed = self.feature_engineer.fit_transform(X_transformed)
        X_transformed = self.categorical_encoder.fit_transform(X_transformed)
        
        self.numerical_features = X_transformed.select_dtypes(include=[np.number]).columns.tolist()
        
        cols_to_remove = ['patient_id', 'chronic_obstructive_pulmonary_disease', 'alanine_aminotransferase']
        self.numerical_features = [col for col in self.numerical_features 
                                  if col not in cols_to_remove]
        
        if self.numerical_features:
            self.scaler.fit(X_transformed[self.numerical_features])
        
        if y_copd is not None:
            self.label_encoder_copd.fit(['A', 'B', 'C', 'D'])
        
        self.feature_names = X_transformed.columns.tolist()
        self.is_fitted = True
        
        return self
    
    def transform(self, X: pd.DataFrame) -> np.ndarray:
        """Transform the data"""
        if not self.is_fitted:
            raise ValueError("Preprocessor must be fitted before transform")
        
        X_transformed = self.missing_handler.transform(X)
        X_transformed = self.feature_engineer.transform(X_transformed)
        X_transformed = self.categorical_encoder.transform(X_transformed)
        
        if self.numerical_features:
            X_transformed[self.numerical_features] = self.scaler.transform(
                X_transformed[self.numerical_features]
            )
        
        cols_to_remove = ['patient_id', 'chronic_obstructive_pulmonary_disease', 'alanine_aminotransferase']
        feature_cols = [col for col in X_transformed.columns if col not in cols_to_remove]
        
        return X_transformed[feature_cols].values
    
    def fit_transform(self, X: pd.DataFrame, y_copd: Optional[pd.Series] = None) -> np.ndarray:
        """Fit and transform the data"""
        self.fit(X, y_copd)
        return self.transform(X)
    
    def encode_copd_target(self, y: pd.Series) -> np.ndarray:
        """Encode COPD target variable"""
        return self.label_encoder_copd.transform(y)
    
    def decode_copd_target(self, y: np.ndarray) -> np.ndarray:
        """Decode COPD target variable"""
        return self.label_encoder_copd.inverse_transform(y)
    
    def get_feature_names(self) -> List[str]:
        """Get feature names after transformation"""
        if not self.is_fitted:
            raise ValueError("Preprocessor must be fitted first")
        return self.feature_names
    
    def save(self, filepath: str):
        """Save the preprocessor to disk"""
        joblib.dump(self, filepath)
    
    @classmethod
    def load(cls, filepath: str):
        """Load a preprocessor from disk"""
        return joblib.load(filepath)


def prepare_features_for_prediction(patient_data: Dict[str, Any]) -> pd.DataFrame:
    """Prepare a single patient's data for prediction"""

    df = pd.DataFrame([patient_data])
    
    required_columns = [
        'age', 'sex', 'bmi', 'smoker', 'diagnosis_code', 'medication_count',
        'days_hospitalized', 'readmitted', 'last_lab_glucose', 'exercise_frequency',
        'diet_quality', 'income_bracket', 'education_level', 'urban',
        'albumin_globulin_ratio'
    ]
    
    for col in required_columns:
        if col not in df.columns:
            if col in ['exercise_frequency', 'education_level']:
                df[col] = None
            elif col in ['age', 'bmi', 'medication_count', 'days_hospitalized', 
                        'last_lab_glucose', 'albumin_globulin_ratio']:
                df[col] = 0
            elif col in ['urban', 'readmitted']:
                df[col] = 0
            else:
                df[col] = 'Unknown'
    
    if 'patient_id' not in df.columns:
        df['patient_id'] = 'PRED_001'
    
    return df


def extract_feature_importance(model, feature_names: List[str]) -> Dict[str, float]:
    """Extract feature importance from trained model"""
    importance_dict = {}
    
    if hasattr(model, 'feature_importances_'):
        importances = model.feature_importances_
        for name, importance in zip(feature_names, importances):
            importance_dict[name] = float(importance)
    elif hasattr(model, 'coef_'):
        importances = np.abs(model.coef_).mean(axis=0) if len(model.coef_.shape) > 1 else np.abs(model.coef_)
        for name, importance in zip(feature_names, importances):
            importance_dict[name] = float(importance)
    
    importance_dict = dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))
    
    return importance_dict