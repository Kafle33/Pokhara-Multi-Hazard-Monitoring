"""
End-to-end landslide susceptibility processing pipeline
Orchestrates feature extraction, model training/inference, and output generation
"""

import numpy as np
from pathlib import Path
from typing import Optional, Dict
import logging

from .feature_extraction import (
    extract_terrain_features,
    stack_features,
    prepare_training_features,
    extract_features_for_prediction
)
from .model import LandslideModel, classify_susceptibility, train_and_save_model
from ..utils.raster_utils import save_cog, raster_to_geojson
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import LANDSLIDE_CONFIG, PROCESSED_DATA_DIR, OUTPUTS_DIR, INPUT_FILES

logger = logging.getLogger(__name__)


def run_landslide_pipeline(
    dem_path: Optional[Path] = None,
    landcover_path: Optional[Path] = None,
    rainfall_path: Optional[Path] = None,
    landslide_inventory_path: Optional[Path] = None,
    model_path: Optional[Path] = None,
    train_new_model: bool = False,
    output_dir: Optional[Path] = None
) -> Dict[str, Path]:
    """
    Run complete landslide susceptibility analysis pipeline
    
    Args:
        dem_path: Path to DEM raster
        landcover_path: Path to landcover raster
        rainfall_path: Path to rainfall raster
        landslide_inventory_path: Path to landslide inventory (for training)
        model_path: Path to saved model (if not training new)
        train_new_model: Whether to train a new model
        output_dir: Directory for outputs
    
    Returns:
        Dictionary mapping output names to file paths
    """
    logger.info("="*60)
    logger.info("STARTING LANDSLIDE SUSCEPTIBILITY PIPELINE")
    logger.info("="*60)
    
    # Use defaults from config if not provided
    if dem_path is None:
        dem_path = INPUT_FILES['dem']
    if landcover_path is None:
        landcover_path = INPUT_FILES['landcover']
    if rainfall_path is None:
        rainfall_path = INPUT_FILES['rainfall']
    if landslide_inventory_path is None:
        landslide_inventory_path = INPUT_FILES['landslide_inventory']
    if model_path is None:
        model_path = LANDSLIDE_CONFIG['model_path']
    if output_dir is None:
        output_dir = OUTPUTS_DIR
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    outputs = {}
    
    # STEP 1: Extract terrain features
    logger.info("Step 1: Extracting terrain features from DEM")
    slope_path, aspect_path, curvature_path = extract_terrain_features(
        dem_path=dem_path,
        output_dir=PROCESSED_DATA_DIR,
        cell_size=30
    )
    
    # STEP 2: Stack all features
    logger.info("Step 2: Stacking features")
    feature_paths = [slope_path, aspect_path, curvature_path]
    
    # Add landcover and rainfall if available
    if landcover_path.exists():
        feature_paths.append(landcover_path)
    if rainfall_path.exists():
        feature_paths.append(rainfall_path)
    
    feature_stack_path = PROCESSED_DATA_DIR / "landslide_features_stack.tif"
    stack_features(feature_paths, feature_stack_path)
    
    # STEP 3: Train model or load existing
    if train_new_model:
        logger.info("Step 3: Training new landslide susceptibility model")
        
        if not landslide_inventory_path.exists():
            raise FileNotFoundError(
                f"Landslide inventory not found at {landslide_inventory_path}. "
                "Cannot train model without training data."
            )
        
        # Prepare training data
        X, y = prepare_training_features(
            feature_stack_path=feature_stack_path,
            landslide_inventory_path=landslide_inventory_path
        )
        
        # Train and save model
        model, metrics = train_and_save_model(
            X=X,
            y=y,
            output_path=model_path,
            model_type=LANDSLIDE_CONFIG['model_type'],
            n_estimators=LANDSLIDE_CONFIG['n_estimators'],
            max_depth=LANDSLIDE_CONFIG['max_depth']
        )
        
        logger.info(f"Model training complete. Metrics: {metrics}")
    else:
        logger.info("Step 3: Loading existing model")
        
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model not found at {model_path}. "
                "Set train_new_model=True to train a new model."
            )
        
        model = LandslideModel.load(model_path)
    
    # STEP 4: Predict susceptibility over entire area
    logger.info("Step 4: Predicting landslide susceptibility")
    
    features_2d, metadata = extract_features_for_prediction(feature_stack_path)
    valid_mask = metadata['valid_mask']
    shape = metadata['shape']
    profile = metadata['profile']
    
    # Predict probabilities
    probabilities_flat = np.zeros(features_2d.shape[0])
    probabilities_flat[valid_mask] = model.predict_proba(features_2d[valid_mask])
    
    # Reshape to raster
    probabilities = probabilities_flat.reshape(shape)
    
    # Save probability raster
    probability_path = output_dir / "landslide_susceptibility_probability.tif"
    save_cog(probabilities, probability_path, profile, nodata=0)
    outputs['probability'] = probability_path
    
    # STEP 5: Classify into susceptibility zones
    logger.info("Step 5: Classifying susceptibility zones")
    
    classified = classify_susceptibility(
        probabilities=probabilities,
        thresholds=LANDSLIDE_CONFIG['classification_thresholds']
    )
    
    # Save classified raster
    classified_path = output_dir / "landslide_susceptibility_classified.tif"
    save_cog(classified, classified_path, profile, nodata=0)
    outputs['classified_raster'] = classified_path
    
    # STEP 6: Convert to GeoJSON
    logger.info("Step 6: Converting to GeoJSON")
    
    class_names = {
        1: "very_low",
        2: "low",
        3: "moderate",
        4: "high",
        5: "very_high"
    }
    
    geojson_path = output_dir / "landslide_susceptibility_zones.geojson"
    raster_to_geojson(
        raster_path=classified_path,
        output_path=geojson_path,
        class_names=class_names
    )
    outputs['geojson'] = geojson_path
    
    logger.info("="*60)
    logger.info("LANDSLIDE SUSCEPTIBILITY PIPELINE COMPLETE")
    logger.info(f"Outputs: {outputs}")
    logger.info("="*60)
    
    return outputs


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    outputs = run_landslide_pipeline(train_new_model=False)
    print(f"Pipeline complete. Outputs: {outputs}")
