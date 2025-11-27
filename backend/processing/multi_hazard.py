"""
Multi-hazard integration module
Combines landslide, flood, and exposure into composite risk map
"""

import numpy as np
from pathlib import Path
from typing import Dict, Optional
import logging

from processing.utils.raster_utils import read_raster, save_cog, raster_to_geojson
from config import MULTI_HAZARD_CONFIG, OUTPUTS_DIR

logger = logging.getLogger(__name__)


def normalize_raster(array: np.ndarray, method: str = "min_max") -> np.ndarray:
    """
    Normalize raster values to 0-1 range
    
    Args:
        array: Input array
        method: "min_max" or "z_score"
    
    Returns:
        Normalized array
    """
    array_f = array.astype(np.float32)
    
    if method == "min_max":
        min_val = array_f.min()
        max_val = array_f.max()
        
        if max_val > min_val:
            normalized = (array_f - min_val) / (max_val - min_val)
        else:
            normalized = array_f
    
    elif method == "z_score":
        mean = array_f.mean()
        std = array_f.std()
        
        if std > 0:
            normalized = (array_f - mean) / std
            # Clip to 0-1
            normalized = np.clip(normalized, 0, 1)
        else:
            normalized = array_f
    
    else:
        raise ValueError(f"Unknown normalization method: {method}")
    
    return normalized


def combine_hazards(
    landslide_path: Path,
    flood_path: Path,
    exposure_path: Optional[Path] = None,
    weights: Optional[Dict[str, float]] = None,
    output_path: Optional[Path] = None
) -> tuple:
    """
    Combine multiple hazard layers into composite risk map
    
    Args:
        landslide_path: Path to landslide susceptibility raster
        flood_path: Path to flood extent raster
        exposure_path: Path to exposure raster (optional)
        weights: Weights for each hazard
        output_path: Path to save output
    
    Returns:
        Tuple of (risk_array, profile)
    """
    logger.info("="*60)
    logger.info("CREATING MULTI-HAZARD RISK MAP")
    logger.info("="*60)
    
    # Use default weights if not provided
    if weights is None:
        weights = MULTI_HAZARD_CONFIG['weights']
    
    # Read landslide
    logger.info(f"Reading landslide from {landslide_path}")
    landslide, profile = read_raster(landslide_path)
    landslide_norm = normalize_raster(landslide, MULTI_HAZARD_CONFIG['normalization_method'])
    
    # Read flood
    logger.info(f"Reading flood from {flood_path}")
    flood, _ = read_raster(flood_path)
    flood_norm = normalize_raster(flood, MULTI_HAZARD_CONFIG['normalization_method'])
    
    # Initialize risk
    risk = weights['landslide'] * landslide_norm + weights['flood'] * flood_norm
    
    # Add exposure if available
    if exposure_path and exposure_path.exists():
        logger.info(f"Reading exposure from {exposure_path}")
        exposure, _ = read_raster(exposure_path)
        exposure_norm = normalize_raster(exposure, MULTI_HAZARD_CONFIG['normalization_method'])
        
        # Recalculate with all three
        total_weight = sum(weights.values())
        risk = (
            weights['landslide'] / total_weight * landslide_norm +
            weights['flood'] / total_weight * flood_norm +
            weights['exposure'] / total_weight * exposure_norm
        )
    else:
        # Normalize without exposure
        total_weight = weights['landslide'] + weights['flood']
        risk = (
            weights['landslide'] / total_weight * landslide_norm +
            weights['flood'] / total_weight * flood_norm
        )
    
    logger.info(f"Combined risk range: {risk.min():.3f} - {risk.max():.3f}")
    
    # Save if output path provided
    if output_path:
        save_cog(risk, output_path, profile, nodata=0)
        logger.info(f"Saved multi-hazard risk to {output_path}")
    
    return risk, profile


def classify_risk(
    risk_array: np.ndarray,
    thresholds: Optional[Dict[str, float]] = None
) -> np.ndarray:
    """
    Classify continuous risk into discrete classes
    
    Args:
        risk_array: Continuous risk values (0-1)
        thresholds: Classification thresholds
    
    Returns:
        Classified risk (1-5)
    """
    if thresholds is None:
        thresholds = MULTI_HAZARD_CONFIG['classification_thresholds']
    
    classified = np.zeros_like(risk_array, dtype=np.uint8)
    
    classified[risk_array <= thresholds['very_low']] = 1
    classified[(risk_array > thresholds['very_low']) & (risk_array <= thresholds['low'])] = 2
    classified[(risk_array > thresholds['low']) & (risk_array <= thresholds['moderate'])] = 3
    classified[(risk_array > thresholds['moderate']) & (risk_array <= thresholds['high'])] = 4
    classified[risk_array > thresholds['high']] = 5
    
    return classified


def run_multi_hazard_integration(
    landslide_path: Optional[Path] = None,
    flood_path: Optional[Path] = None,
    exposure_path: Optional[Path] = None,
    output_dir: Optional[Path] = None
) -> Dict[str, Path]:
    """
    Run complete multi-hazard integration pipeline
    
    Args:
        landslide_path: Path to landslide raster
        flood_path: Path to flood raster
        exposure_path: Path to exposure raster
        output_dir: Output directory
    
    Returns:
        Dictionary of output paths
    """
    logger.info("="*60)
    logger.info("STARTING MULTI-HAZARD INTEGRATION PIPELINE")
    logger.info("="*60)
    
    # Use defaults
    if landslide_path is None:
        landslide_path = OUTPUTS_DIR / "landslide_susceptibility_probability.tif"
    if flood_path is None:
        flood_path = OUTPUTS_DIR / "flood_extent.tif"
    if exposure_path is None:
        exposure_path = OUTPUTS_DIR / "exposure_density.tif"
    if output_dir is None:
        output_dir = OUTPUTS_DIR
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    outputs = {}
    
    # STEP 1: Combine hazards
    logger.info("Step 1: Combining hazard layers")
    risk_path = output_dir / "multi_hazard_risk.tif"
    risk, profile = combine_hazards(
        landslide_path=landslide_path,
        flood_path=flood_path,
        exposure_path=exposure_path if exposure_path.exists() else None,
        output_path=risk_path
    )
    outputs['risk_raster'] = risk_path
    
    # STEP 2: Classify risk
    logger.info("Step 2: Classifying risk levels")
    classified = classify_risk(risk)
    
    classified_path = output_dir / "multi_hazard_risk_classified.tif"
    save_cog(classified, classified_path, profile, nodata=0)
    outputs['classified_raster'] = classified_path
    
    # STEP 3: Convert to GeoJSON
    logger.info("Step 3: Converting to GeoJSON")
    
    class_names = {
        1: "very_low",
        2: "low",
        3: "moderate",
        4: "high",
        5: "very_high"
    }
    
    geojson_path = output_dir / "multi_hazard_risk.geojson"
    raster_to_geojson(
        raster_path=classified_path,
        output_path=geojson_path,
        class_names=class_names
    )
    outputs['geojson'] = geojson_path
    
    logger.info("="*60)
    logger.info("MULTI-HAZARD INTEGRATION COMPLETE")
    logger.info(f"Outputs: {outputs}")
    logger.info("="*60)
    
    return outputs


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    outputs = run_multi_hazard_integration()
    print(f"Multi-hazard integration complete. Outputs: {outputs}")
