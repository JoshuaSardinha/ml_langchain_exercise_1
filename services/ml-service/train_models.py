#!/usr/bin/env python3
"""
Train ML models for the Data Doctor application with XGBoost support
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.data_service import DataService
from app.services.ml_service import MLService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def train_models():
    """Train both COPD and ALT models using XGBoost"""
    
    logger.info("="*60)
    logger.info("Starting model training pipeline")
    logger.info("="*60)
    
    logger.info("Initializing services...")
    data_service = DataService(data_path="data/raw/patient_data.csv")
    ml_service = MLService(data_service=data_service)
    
    summary = data_service.get_data_summary()
    logger.info(f"Loaded {summary['total_patients']} patients with {summary['features']} features")
    
    logger.info("\n" + "="*60)
    logger.info("Training COPD Classifier")
    logger.info("="*60)
    
    copd_metrics = ml_service.train_copd_classifier(
        test_size=0.2,
        random_state=42,
        use_grid_search=True
    )
    
    logger.info("\nCOPD Classifier Results:")
    logger.info(f"  Accuracy: {copd_metrics['accuracy']:.3f}")
    logger.info(f"  F1 Score: {copd_metrics['f1_score']:.3f}")
    logger.info(f"  CV Score: {copd_metrics['cv_score_mean']:.3f} ± {copd_metrics['cv_score_std']:.3f}")
    
    logger.info("\nClassification Report:")
    for class_name in ['A', 'B', 'C', 'D']:
        class_metrics = copd_metrics['classification_report'].get(class_name, {})
        logger.info(f"  Class {class_name}: Precision={class_metrics.get('precision', 0):.3f}, "
                   f"Recall={class_metrics.get('recall', 0):.3f}, "
                   f"F1={class_metrics.get('f1-score', 0):.3f}")
    
    logger.info("\n" + "="*60)
    logger.info("Training ALT Regressor")
    logger.info("="*60)
    
    alt_metrics = ml_service.train_alt_regressor(
        test_size=0.2,
        random_state=42,
        use_grid_search=True
    )
    
    logger.info("\nALT Regressor Results:")
    logger.info(f"  MAE: {alt_metrics['mae']:.3f}")
    logger.info(f"  RMSE: {alt_metrics['rmse']:.3f}")
    logger.info(f"  R² Score: {alt_metrics['r2_score']:.3f}")
    logger.info(f"  Within 15 units: {alt_metrics['within_15_units']*100:.1f}%")
    logger.info(f"  CV MAE: {alt_metrics['cv_mae_mean']:.3f} ± {alt_metrics['cv_mae_std']:.3f}")
    
    logger.info("\n" + "="*60)
    logger.info("Saving models and preprocessor")
    logger.info("="*60)
    
    ml_service.save_models()
    
    logger.info("\n" + "="*60)
    logger.info("Top Features")
    logger.info("="*60)
    
    logger.info("\nTop 10 features for COPD classification:")
    copd_features = list(ml_service.feature_importance.get('copd', {}).items())[:10]
    for i, (feature, importance) in enumerate(copd_features, 1):
        logger.info(f"  {i}. {feature}: {importance:.4f}")
    
    logger.info("\nTop 10 features for ALT regression:")
    alt_features = list(ml_service.feature_importance.get('alt', {}).items())[:10]
    for i, (feature, importance) in enumerate(alt_features, 1):
        logger.info(f"  {i}. {feature}: {importance:.4f}")
    
    logger.info("\n" + "="*60)
    logger.info("Model training completed successfully!")
    logger.info("="*60)
    
    return ml_service


def test_predictions(ml_service):
    """Test model predictions with sample data"""
    
    logger.info("\n" + "="*60)
    logger.info("Testing Model Predictions")
    logger.info("="*60)
    
    test_patient = {
        'age': 55,
        'sex': 'Male',
        'bmi': 27.5,
        'smoker': 'No',
        'diagnosis_code': 'D2',
        'medication_count': 3,
        'days_hospitalized': 4,
        'readmitted': 0,
        'last_lab_glucose': 95.0,
        'exercise_frequency': 'Low',
        'diet_quality': 'Poor',
        'income_bracket': 'Middle',
        'education_level': 'Secondary',
        'urban': 1,
        'albumin_globulin_ratio': 0.65
    }
    
    logger.info("\nTesting COPD prediction...")
    copd_result = ml_service.predict_copd(test_patient)
    
    if 'error' not in copd_result:
        logger.info(f"  Predicted COPD Class: {copd_result['prediction']}")
        logger.info(f"  Confidence: {copd_result['confidence']:.2%}")
        logger.info("  Class Probabilities:")
        for class_name, prob in copd_result['class_probabilities'].items():
            logger.info(f"    {class_name}: {prob:.3f}")
    else:
        logger.error(f"  Error: {copd_result['error']}")
    
    logger.info("\nTesting ALT prediction...")
    alt_result = ml_service.predict_alt(test_patient)
    
    if 'error' not in alt_result:
        logger.info(f"  Predicted ALT Value: {alt_result['prediction']:.1f} U/L")
        logger.info(f"  Confidence: {alt_result['confidence']:.2%}")
        logger.info(f"  95% Prediction Interval: [{alt_result['prediction_interval']['lower']:.1f}, "
                   f"{alt_result['prediction_interval']['upper']:.1f}]")
        logger.info(f"  Model MAE: {alt_result['model_mae']:.1f}")
    else:
        logger.error(f"  Error: {alt_result['error']}")
    
    logger.info("\n" + "="*60)
    logger.info("Testing completed!")
    logger.info("="*60)


if __name__ == "__main__":
    ml_service = train_models()
    test_predictions(ml_service)