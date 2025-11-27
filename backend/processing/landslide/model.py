"""
Machine Learning models for landslide susceptibility prediction
Implements Random Forest and XGBoost classifiers
"""

import numpy as np
import pickle
from pathlib import Path
from typing import Tuple, Optional
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
import logging

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    logging.warning("XGBoost not available, using Random Forest only")

logger = logging.getLogger(__name__)


class LandslideModel:
    """
    Landslide susceptibility model wrapper
    Supports Random Forest and XGBoost
    """
    
    def __init__(self, model_type: str = "RandomForest", **params):
        """
        Initialize model
        
        Args:
            model_type: "RandomForest" or "XGBoost"
            **params: Model hyperparameters
        """
        self.model_type = model_type
        self.params = params
        self.model = None
        self.feature_names = None
        
    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        test_size: float = 0.3,
        random_state: int = 42
    ) -> dict:
        """
        Train the model
        
        Args:
            X: Feature matrix (n_samples, n_features)
            y: Labels (n_samples,)
            test_size: Test set proportion
            random_state: Random seed
        
        Returns:
            Dictionary with training metrics
        """
        logger.info(f"Training {self.model_type} model")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )
        
        # Initialize model
        if self.model_type == "RandomForest":
            self.model = RandomForestClassifier(
                n_estimators=self.params.get('n_estimators', 100),
                max_depth=self.params.get('max_depth', 10),
                random_state=random_state,
                n_jobs=-1
            )
        elif self.model_type == "XGBoost" and XGBOOST_AVAILABLE:
            self.model = xgb.XGBClassifier(
                n_estimators=self.params.get('n_estimators', 100),
                max_depth=self.params.get('max_depth', 10),
                random_state=random_state,
                n_jobs=-1,
                eval_metric='logloss'
            )
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")
        
        # Train
        self.model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test)
        y_prob = self.model.predict_proba(X_test)[:, 1]
        
        metrics = {
            'classification_report': classification_report(y_test, y_pred),
            'roc_auc': roc_auc_score(y_test, y_prob),
            'train_samples': len(X_train),
            'test_samples': len(X_test)
        }
        
        logger.info(f"Model trained. ROC-AUC: {metrics['roc_auc']:.3f}")
        logger.info(f"\n{metrics['classification_report']}")
        
        return metrics
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict class labels
        
        Args:
            X: Feature matrix (n_samples, n_features)
        
        Returns:
            Predicted labels (n_samples,)
        """
        if self.model is None:
            raise ValueError("Model not trained yet")
        
        return self.model.predict(X)
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Predict landslide probability
        
        Args:
            X: Feature matrix (n_samples, n_features)
        
        Returns:
            Probabilities for positive class (n_samples,)
        """
        if self.model is None:
            raise ValueError("Model not trained yet")
        
        return self.model.predict_proba(X)[:, 1]
    
    def get_feature_importance(self) -> np.ndarray:
        """Get feature importance scores"""
        if self.model is None:
            raise ValueError("Model not trained yet")
        
        return self.model.feature_importances_
    
    def save(self, file_path: Path) -> None:
        """Save model to disk"""
        with open(file_path, 'wb') as f:
            pickle.dump(self, f)
        logger.info(f"Model saved to {file_path}")
    
    @staticmethod
    def load(file_path: Path) -> 'LandslideModel':
        """Load model from disk"""
        with open(file_path, 'rb') as f:
            model = pickle.load(f)
        logger.info(f"Model loaded from {file_path}")
        return model


def classify_susceptibility(
    probabilities: np.ndarray,
    thresholds: dict
) -> np.ndarray:
    """
    Classify continuous probabilities into discrete susceptibility classes
    
    Args:
        probabilities: Continuous probability values (0-1)
        thresholds: Dictionary of class_name: threshold_value
            e.g., {'very_low': 0.2, 'low': 0.4, 'moderate': 0.6, 'high': 0.8}
    
    Returns:
        Classification array with values 1-5
    """
    classified = np.zeros_like(probabilities, dtype=np.uint8)
    
    # Define class values
    class_mapping = {
        'very_low': 1,
        'low': 2,
        'moderate': 3,
        'high': 4,
        'very_high': 5
    }
    
    # Sort thresholds
    sorted_classes = ['very_low', 'low', 'moderate', 'high', 'very_high']
    
    for i, class_name in enumerate(sorted_classes[:-1]):
        if class_name in thresholds:
            threshold = thresholds[class_name]
            
            if i == 0:
                mask = probabilities <= threshold
            else:
                prev_class = sorted_classes[i-1]
                prev_threshold = thresholds.get(prev_class, 0)
                mask = (probabilities > prev_threshold) & (probabilities <= threshold)
            
            classified[mask] = class_mapping[class_name]
    
    # Very high (above highest threshold)
    if 'high' in thresholds:
        classified[probabilities > thresholds['high']] = class_mapping['very_high']
    
    return classified


def train_and_save_model(
    X: np.ndarray,
    y: np.ndarray,
    output_path: Path,
    model_type: str = "RandomForest",
    **params
) -> Tuple[LandslideModel, dict]:
    """
    Convenience function to train and save model
    
    Args:
        X: Features
        y: Labels
        output_path: Path to save model
        model_type: Model type
        **params: Model parameters
    
    Returns:
        Tuple of (model, metrics)
    """
    model = LandslideModel(model_type=model_type, **params)
    metrics = model.train(X, y)
    model.save(output_path)
    
    return model, metrics
