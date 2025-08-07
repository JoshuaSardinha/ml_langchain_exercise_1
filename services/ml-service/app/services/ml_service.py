import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
import joblib
import logging
from datetime import datetime

from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, VotingClassifier, VotingRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix,
    mean_absolute_error, mean_squared_error, r2_score,
    f1_score, precision_recall_fscore_support
)
from sklearn.preprocessing import LabelEncoder

from xgboost import XGBClassifier, XGBRegressor

from ..models.ml_models import COPDClassifier, ALTRegressor
from ..utils.preprocessing import DataPreprocessor, extract_feature_importance
from .data_service import DataService

logger = logging.getLogger(__name__)

class MLService:
    """Service for training and managing ML models"""
    
    def __init__(self, data_service: Optional[DataService] = None):
        self.data_service = data_service or DataService()
        self.copd_model = None
        self.alt_model = None
        self.preprocessor = self.data_service.preprocessor
        self.copd_label_encoder = LabelEncoder()
        self.model_metrics = {}
        self.feature_importance = {}
        
    def train_copd_classifier(self, 
                            test_size: float = 0.2,
                            random_state: int = 42,
                            use_grid_search: bool = True) -> Dict[str, Any]:
        """Train COPD classification model"""
        logger.info("Starting COPD classifier training...")
        
        X, y = self.data_service.get_training_data(target='copd')
        
        X_processed = self.data_service.preprocess_data(X, fit=True)
        
        self.copd_label_encoder.fit(['A', 'B', 'C', 'D'])
        y_encoded = self.copd_label_encoder.transform(y)
        
        X_train, X_test, y_train, y_test = train_test_split(
            X_processed, y_encoded, 
            test_size=test_size, 
            random_state=random_state,
            stratify=y_encoded
        )
        
        if use_grid_search:
            param_grid = {
                'n_estimators': [100, 200, 300],
                'max_depth': [3, 5, 7],
                'learning_rate': [0.01, 0.1, 0.3],
                'subsample': [0.7, 0.8, 0.9]
            }
            base_model = XGBClassifier(
                random_state=random_state, 
                use_label_encoder=False,
                eval_metric='mlogloss'
            )
            
            cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=random_state)
            
            grid_search = GridSearchCV(
                base_model, param_grid, 
                cv=cv, scoring='f1_weighted',
                n_jobs=-1, verbose=1
            )
            
            logger.info(f"Performing grid search for COPD classifier (XGBoost)...")
            grid_search.fit(X_train, y_train)
            
            self.copd_model = grid_search.best_estimator_
            best_params = grid_search.best_params_
            logger.info(f"Best parameters: {best_params}")
        else:
            self.copd_model = XGBClassifier(
                n_estimators=200,
                max_depth=5,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=random_state,
                use_label_encoder=False,
                eval_metric='mlogloss'
            )
            self.copd_model.fit(X_train, y_train)
            best_params = {}
        
        y_pred = self.copd_model.predict(X_test)
        y_pred_proba = self.copd_model.predict_proba(X_test)
        
        accuracy = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average='weighted')
        precision, recall, fscore, support = precision_recall_fscore_support(
            y_test, y_pred, average='weighted'
        )
        
        cm = confusion_matrix(y_test, y_pred)
        
        cv_scores = cross_val_score(
            self.copd_model, X_train, y_train, 
            cv=5, scoring='f1_weighted'
        )
        
        feature_names = self.preprocessor.get_feature_names()
        self.feature_importance['copd'] = extract_feature_importance(
            self.copd_model, feature_names
        )
        
        self.model_metrics['copd'] = {
            'accuracy': float(accuracy),
            'f1_score': float(f1),
            'precision': float(precision),
            'recall': float(recall),
            'cv_score_mean': float(cv_scores.mean()),
            'cv_score_std': float(cv_scores.std()),
            'confusion_matrix': cm.tolist(),
            'class_labels': ['A', 'B', 'C', 'D'],
            'best_params': best_params,
            'training_date': datetime.now().isoformat(),
            'test_size': test_size,
            'n_training_samples': len(X_train),
            'n_test_samples': len(X_test)
        }
        
        class_report = classification_report(
            y_test, y_pred, 
            target_names=['A', 'B', 'C', 'D'],
            output_dict=True
        )
        self.model_metrics['copd']['classification_report'] = class_report
        
        logger.info(f"COPD Classifier - Accuracy: {accuracy:.3f}, F1: {f1:.3f}")
        
        return self.model_metrics['copd']
    
    def train_alt_regressor(self,
                          test_size: float = 0.2,
                          random_state: int = 42,
                          use_grid_search: bool = True) -> Dict[str, Any]:
        """Train ALT regression model"""
        logger.info("Starting ALT regressor training...")
        
        X, y = self.data_service.get_training_data(target='alt')
        
        X_processed = self.data_service.preprocess_data(X, fit=False)
        
        X_train, X_test, y_train, y_test = train_test_split(
            X_processed, y, 
            test_size=test_size, 
            random_state=random_state
        )
        
        if use_grid_search:
            param_grid = {
                'n_estimators': [100, 200, 300],
                'max_depth': [3, 5, 7],
                'learning_rate': [0.01, 0.1, 0.3],
                'subsample': [0.7, 0.8, 0.9]
            }
            base_model = XGBRegressor(random_state=random_state)
            
            grid_search = GridSearchCV(
                base_model, param_grid, 
                cv=5, scoring='neg_mean_absolute_error',
                n_jobs=-1, verbose=1
            )
            
            logger.info(f"Performing grid search for ALT regressor (XGBoost)...")
            grid_search.fit(X_train, y_train)
            
            self.alt_model = grid_search.best_estimator_
            best_params = grid_search.best_params_
            logger.info(f"Best parameters: {best_params}")
        else:
            self.alt_model = XGBRegressor(
                n_estimators=200,
                max_depth=5,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=random_state
            )
            self.alt_model.fit(X_train, y_train)
            best_params = {}
        
        y_pred = self.alt_model.predict(X_test)
        
        mae = mean_absolute_error(y_test, y_pred)
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        r2 = r2_score(y_test, y_pred)
        
        tolerance_5 = np.mean(np.abs(y_test - y_pred) <= 5)
        tolerance_10 = np.mean(np.abs(y_test - y_pred) <= 10)
        tolerance_15 = np.mean(np.abs(y_test - y_pred) <= 15)
        
        cv_scores = cross_val_score(
            self.alt_model, X_train, y_train, 
            cv=5, scoring='neg_mean_absolute_error'
        )
        
        feature_names = self.preprocessor.get_feature_names()
        self.feature_importance['alt'] = extract_feature_importance(
            self.alt_model, feature_names
        )
        
        self.model_metrics['alt'] = {
            'mae': float(mae),
            'mse': float(mse),
            'rmse': float(rmse),
            'r2_score': float(r2),
            'within_5_units': float(tolerance_5),
            'within_10_units': float(tolerance_10),
            'within_15_units': float(tolerance_15),
            'cv_mae_mean': float(-cv_scores.mean()),
            'cv_mae_std': float(cv_scores.std()),
            'best_params': best_params,
            'training_date': datetime.now().isoformat(),
            'test_size': test_size,
            'n_training_samples': len(X_train),
            'n_test_samples': len(X_test),
            'target_mean': float(y_train.mean()),
            'target_std': float(y_train.std())
        }
        
        residuals = y_test - y_pred
        self.model_metrics['alt']['residuals'] = {
            'mean': float(residuals.mean()),
            'std': float(residuals.std()),
            'min': float(residuals.min()),
            'max': float(residuals.max())
        }
        
        logger.info(f"ALT Regressor - MAE: {mae:.3f}, R2: {r2:.3f}")
        
        return self.model_metrics['alt']
    
    def predict_copd(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict COPD classification for a patient"""
        if self.copd_model is None:
            return {"error": "COPD model not trained"}
        
        try:
            X = self.data_service.prepare_prediction_input(patient_data)
            
            prediction_encoded = self.copd_model.predict(X)[0]
            prediction = self.copd_label_encoder.inverse_transform([prediction_encoded])[0]
            
            probabilities = self.copd_model.predict_proba(X)[0]
            confidence = float(np.max(probabilities))
            
            class_probs = {
                class_name: float(prob) 
                for class_name, prob in zip(['A', 'B', 'C', 'D'], probabilities)
            }
            
            feature_names = self.preprocessor.get_feature_names()
            top_features = list(self.feature_importance.get('copd', {}).keys())[:10]
            
            return {
                "prediction": prediction,
                "confidence": confidence,
                "class_probabilities": class_probs,
                "top_features": top_features,
                "model_accuracy": self.model_metrics.get('copd', {}).get('accuracy', 0)
            }
            
        except Exception as e:
            logger.error(f"Error in COPD prediction: {e}")
            return {"error": str(e)}
    
    def predict_alt(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict ALT value for a patient"""
        if self.alt_model is None:
            return {"error": "ALT model not trained"}
        
        try:
            X = self.data_service.prepare_prediction_input(patient_data)
            
            prediction = float(self.alt_model.predict(X)[0])
            
            mae = self.model_metrics.get('alt', {}).get('mae', 10)
            confidence = max(0.5, min(0.95, 1 - (mae / 50)))  # Scale confidence based on MAE
            
            if hasattr(self.alt_model, 'estimators_'):
                tree_predictions = np.array([tree.predict(X)[0] for tree in self.alt_model.estimators_])
                prediction_std = float(tree_predictions.std())
                prediction_interval = {
                    "lower": float(prediction - 1.96 * prediction_std),
                    "upper": float(prediction + 1.96 * prediction_std)
                }
            else:
                prediction_interval = {
                    "lower": float(prediction - mae),
                    "upper": float(prediction + mae)
                }
            
            top_features = list(self.feature_importance.get('alt', {}).keys())[:10]
            
            return {
                "prediction": prediction,
                "confidence": confidence,
                "prediction_interval": prediction_interval,
                "top_features": top_features,
                "model_mae": mae,
                "reference_range": {
                    "normal_min": 7,
                    "normal_max": 56,
                    "unit": "U/L"
                }
            }
            
        except Exception as e:
            logger.error(f"Error in ALT prediction: {e}")
            return {"error": str(e)}
    
    def save_models(self, model_dir: str = "data/models"):
        """Save trained models and preprocessor"""
        model_path = Path(model_dir)
        model_path.mkdir(parents=True, exist_ok=True)
        
        if self.copd_model:
            joblib.dump(self.copd_model, model_path / "copd_classifier.pkl")
            joblib.dump(self.copd_label_encoder, model_path / "copd_label_encoder.pkl")
            logger.info(f"Saved COPD model to {model_path / 'copd_classifier.pkl'}")
        
        if self.alt_model:
            joblib.dump(self.alt_model, model_path / "alt_regressor.pkl")
            logger.info(f"Saved ALT model to {model_path / 'alt_regressor.pkl'}")
        
        self.data_service.save_preprocessor(str(model_path / "preprocessor.pkl"))
        logger.info(f"Saved preprocessor to {model_path / 'preprocessor.pkl'}")
        
        joblib.dump(self.model_metrics, model_path / "model_metrics.pkl")
        joblib.dump(self.feature_importance, model_path / "feature_importance.pkl")
        
        logger.info("All models and metadata saved successfully")
    
    def load_models(self, model_dir: str = "data/models"):
        """Load trained models and preprocessor"""
        model_path = Path(model_dir)
        
        try:
            copd_path = model_path / "copd_classifier.pkl"
            if copd_path.exists():
                self.copd_model = joblib.load(copd_path)
                self.copd_label_encoder = joblib.load(model_path / "copd_label_encoder.pkl")
                logger.info("Loaded COPD model")
            
            alt_path = model_path / "alt_regressor.pkl"
            if alt_path.exists():
                self.alt_model = joblib.load(alt_path)
                logger.info("Loaded ALT model")
            
            preprocessor_path = model_path / "preprocessor.pkl"
            if preprocessor_path.exists():
                self.data_service.load_preprocessor(str(preprocessor_path))
                self.preprocessor = self.data_service.preprocessor
                logger.info("Loaded preprocessor")
            
            metrics_path = model_path / "model_metrics.pkl"
            if metrics_path.exists():
                self.model_metrics = joblib.load(metrics_path)
            
            importance_path = model_path / "feature_importance.pkl"
            if importance_path.exists():
                self.feature_importance = joblib.load(importance_path)
            
            logger.info("All models loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded models"""
        info = {
            "copd_model": {
                "loaded": self.copd_model is not None,
                "metrics": self.model_metrics.get('copd', {}),
                "top_features": list(self.feature_importance.get('copd', {}).keys())[:5]
            },
            "alt_model": {
                "loaded": self.alt_model is not None,
                "metrics": self.model_metrics.get('alt', {}),
                "top_features": list(self.feature_importance.get('alt', {}).keys())[:5]
            },
            "preprocessor": {
                "loaded": self.preprocessor.is_fitted if hasattr(self.preprocessor, 'is_fitted') else False
            }
        }
        
        return info