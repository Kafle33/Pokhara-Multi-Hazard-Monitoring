"""
Feature extraction module for landslide susceptibility modeling
Extracts terrain and environmental features from DEM and other inputs
"""

import numpy as np
import rasterio
from pathlib import Path
from typing import Tuple, List
import logging

from ..utils.raster_utils import (
    calculate_slope,
    calculate_aspect,
    calculate_curvature,
    read_raster,
    save_cog
)

logger = logging.getLogger(__name__)


def extract_terrain_features(
    dem_path: Path,
    output_dir: Path,
    cell_size: float = 30
) -> Tuple[Path, Path, Path]:
    """
    Extract terrain features from DEM
    
    Args:
        dem_path: Path to DEM raster
        output_dir: Directory to save outputs
        cell_size: DEM cell size in meters
    
    Returns:
        Tuple of (slope_path, aspect_path, curvature_path)
    """
    logger.info(f"Extracting terrain features from {dem_path}")
    
    # Read DEM
    dem_array, profile = read_raster(dem_path)
    
    # Calculate derivatives
    slope = calculate_slope(dem_array, cell_size)
    aspect = calculate_aspect(dem_array)
    curvature = calculate_curvature(dem_array, cell_size)
    
    # Save outputs
    output_dir.mkdir(parents=True, exist_ok=True)
    
    slope_path = output_dir / "slope.tif"
    aspect_path = output_dir / "aspect.tif"
    curvature_path = output_dir / "curvature.tif"
    
    save_cog(slope, slope_path, profile)
    save_cog(aspect, aspect_path, profile)
    save_cog(curvature, curvature_path, profile)
    
    logger.info(f"Terrain features saved to {output_dir}")
    
    return slope_path, aspect_path, curvature_path


def stack_features(
    feature_paths: List[Path],
    output_path: Path
) -> np.ndarray:
    """
    Stack multiple feature rasters into a single multi-band raster
    
    Args:
        feature_paths: List of paths to feature rasters
        output_path: Path to save stacked output
    
    Returns:
        Stacked array (n_features, height, width)
    """
    logger.info(f"Stacking {len(feature_paths)} features")
    
    # Read first raster for profile
    with rasterio.open(feature_paths[0]) as src:
        profile = src.profile.copy()
        height, width = src.shape
    
    # Initialize stack
    n_features = len(feature_paths)
    stack = np.zeros((n_features, height, width), dtype=np.float32)
    
    # Read each feature
    for i, feature_path in enumerate(feature_paths):
        array, _ = read_raster(feature_path)
        stack[i] = array
    
    # Update profile for multi-band
    profile.update({
        'count': n_features,
        'dtype': 'float32'
    })
    
    # Save stacked raster
    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(stack)
    
    logger.info(f"Stacked features saved to {output_path}")
    
    return stack


def prepare_training_features(
    feature_stack_path: Path,
    landslide_inventory_path: Path,
    n_negative_samples: int = None
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Prepare training data from feature stack and landslide inventory
    
    Args:
        feature_stack_path: Path to stacked feature raster
        landslide_inventory_path: Path to landslide inventory GeoJSON (points)
        n_negative_samples: Number of negative samples (non-landslide) to extract
    
    Returns:
        Tuple of (X, y) where X is features and y is labels
    """
    import geopandas as gpd
    
    logger.info("Preparing training data")
    
    # Read feature stack
    with rasterio.open(feature_stack_path) as src:
        features = src.read()  # (n_bands, height, width)
        transform = src.transform
        
        # Read landslide inventory
        landslides = gpd.read_file(landslide_inventory_path)
        
        # Extract feature values at landslide locations (positive samples)
        positive_samples = []
        for idx, point in landslides.iterrows():
            # Get pixel coordinates
            py, px = rasterio.transform.rowcol(transform, point.geometry.x, point.geometry.y)
            
            # Extract feature values
            if 0 <= py < features.shape[1] and 0 <= px < features.shape[2]:
                sample = features[:, py, px]
                positive_samples.append(sample)
        
        positive_samples = np.array(positive_samples)
        n_positive = len(positive_samples)
        
        logger.info(f"Extracted {n_positive} positive samples")
        
        # Generate negative samples (random non-landslide locations)
        if n_negative_samples is None:
            n_negative_samples = n_positive  # Balance classes
        
        negative_samples = []
        height, width = features.shape[1], features.shape[2]
        
        # Simple random sampling (in practice, should avoid landslide areas)
        attempts = 0
        max_attempts = n_negative_samples * 10
        
        while len(negative_samples) < n_negative_samples and attempts < max_attempts:
            py = np.random.randint(0, height)
            px = np.random.randint(0, width)
            
            sample = features[:, py, px]
            
            # Check if any feature is nodata
            if not np.any(np.isnan(sample)) and not np.any(sample == -9999):
                negative_samples.append(sample)
            
            attempts += 1
        
        negative_samples = np.array(negative_samples)
        logger.info(f"Generated {len(negative_samples)} negative samples")
        
        # Combine positive and negative
        X = np.vstack([positive_samples, negative_samples])
        y = np.array([1] * n_positive + [0] * len(negative_samples))
        
        logger.info(f"Training data: X shape={X.shape}, y shape={y.shape}")
        
        return X, y


def extract_features_for_prediction(feature_stack_path: Path) -> Tuple[np.ndarray, dict]:
    """
    Extract features for prediction over entire area
    
    Args:
        feature_stack_path: Path to stacked feature raster
    
    Returns:
        Tuple of (features_2d, metadata) where features_2d is (n_pixels, n_features)
    """
    with rasterio.open(feature_stack_path) as src:
        features = src.read()  # (n_bands, height, width)
        profile = src.profile.copy()
        
        # Reshape to (n_pixels, n_features)
        n_bands, height, width = features.shape
        features_2d = features.reshape(n_bands, -1).T
        
        # Create mask for valid pixels
        valid_mask = ~np.any(np.isnan(features_2d), axis=1)
        valid_mask &= ~np.any(features_2d == -9999, axis=1)
        
        metadata = {
            'profile': profile,
            'shape': (height, width),
            'valid_mask': valid_mask
        }
        
        return features_2d, metadata
