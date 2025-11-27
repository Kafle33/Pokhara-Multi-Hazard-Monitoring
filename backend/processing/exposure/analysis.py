"""
Exposure analysis module for multi-hazard system
Analyzes building and population exposure to hazards
"""

import numpy as np
import rasterio
from rasterio import features
import geopandas as gpd
from shapely.geometry import Point, box
from pathlib import Path
from typing import Tuple, Optional, Dict
import logging

from ..utils.raster_utils import read_raster, save_cog

logger = logging.getLogger(__name__)


def rasterize_buildings(
    buildings_path: Path,
    reference_raster_path: Path,
    output_path: Path
) -> np.ndarray:
    """
    Rasterize building footprints to match reference raster
    
    Args:
        buildings_path: Path to buildings GeoJSON
        reference_raster_path: Reference raster for extent and resolution
        output_path: Output path for rasterized buildings
    
    Returns:
        Building density raster
    """
    logger.info("Rasterizing building footprints")
    
    # Read buildings
    buildings = gpd.read_file(buildings_path)
    
    # Read reference raster for metadata
    with rasterio.open(reference_raster_path) as src:
        profile = src.profile.copy()
        transform = src.transform
        shape = (src.height, src.width)
    
    # Rasterize buildings (count)
    shapes_gen = ((geom, 1) for geom in buildings.geometry)
    building_raster = features.rasterize(
        shapes=shapes_gen,
        out_shape=shape,
        transform=transform,
        fill=0,
        dtype=np.uint16
    )
    
    save_cog(building_raster, output_path, profile, nodata=0)
    
    logger.info(f"Rasterized {len(buildings)} buildings")
    
    return building_raster


def calculate_exposure_density(
    hazard_raster: np.ndarray,
    buildings_raster: np.ndarray,
    population_raster: Optional[np.ndarray] = None,
    weights: Dict[str, float] = None
) -> np.ndarray:
    """
    Calculate exposure density combining hazard, buildings, and population
    
    Args:
        hazard_raster: Hazard intensity/probability raster (0-1 or classified)
        buildings_raster: Building count/density raster
        population_raster: Population density raster (optional)
        weights: Weights for combining factors
    
    Returns:
        Exposure density raster
    """
    logger.info("Calculating exposure density")
    
    if weights is None:
        weights = {
            'hazard': 0.4,
            'buildings': 0.4,
            'population': 0.2
        }
    
    # Normalize hazard to 0-1
    hazard_norm = hazard_raster.astype(np.float32)
    if hazard_norm.max() > 1:
        hazard_norm = hazard_norm / hazard_norm.max()
    
    # Normalize buildings
    buildings_norm = buildings_raster.astype(np.float32)
    if buildings_norm.max() > 0:
        buildings_norm = buildings_norm / buildings_norm.max()
    
    # Calculate exposure
    exposure = weights['hazard'] * hazard_norm + weights['buildings'] * buildings_norm
    
    # Add population if available
    if population_raster is not None:
        pop_norm = population_raster.astype(np.float32)
        if pop_norm.max() > 0:
            pop_norm = pop_norm / pop_norm.max()
        
        # Renormalize weights
        total_weight = sum(weights.values())
        exposure = (
            weights['hazard'] / total_weight * hazard_norm +
            weights['buildings'] / total_weight * buildings_norm +
            weights['population'] / total_weight * pop_norm
        )
    
    logger.info(f"Exposure range: {exposure.min():.3f} - {exposure.max():.3f}")
    
    return exposure


def calculate_risk_index(
    landslide_suscept: np.ndarray,
    flood_extent: np.ndarray,
    exposure: np.ndarray,
    weights: Dict[str, float] = None
) -> np.ndarray:
    """
    Calculate simple multi-hazard risk index
    
    Args:
        landslide_suscept: Landslide susceptibility (0-1 or classified)
        flood_extent: Flood extent (binary or probability)
        exposure: Exposure density (0-1)
        weights: Weights for each component
    
    Returns:
        Risk index raster
    """
    logger.info("Calculating risk index")
    
    if weights is None:
        weights = {
            'landslide': 0.35,
            'flood': 0.35,
            'exposure': 0.30
        }
    
    # Normalize all to 0-1
    def normalize(arr):
        arr_f = arr.astype(np.float32)
        if arr_f.max() > 0:
            return arr_f / arr_f.max()
        return arr_f
    
    ls_norm = normalize(landslide_suscept)
    flood_norm = normalize(flood_extent)
    exp_norm = normalize(exposure)
    
    # Calculate weighted risk
    risk = (
        weights['landslide'] * ls_norm +
        weights['flood'] * flood_norm +
        weights['exposure'] * exp_norm
    )
    
    logger.info(f"Risk index range: {risk.min():.3f} - {risk.max():.3f}")
    
    return risk


def classify_exposure(
    exposure: np.ndarray,
    thresholds: Dict[str, float] = None
) -> np.ndarray:
    """
    Classify continuous exposure into discrete classes
    
    Args:
        exposure: Continuous exposure values (0-1)
        thresholds: Classification thresholds
    
    Returns:
        Classified exposure (1-5)
    """
    if thresholds is None:
        thresholds = {
            'very_low': 0.2,
            'low': 0.4,
            'moderate': 0.6,
            'high': 0.8
        }
    
    classified = np.zeros_like(exposure, dtype=np.uint8)
    
    classified[exposure <= thresholds['very_low']] = 1
    classified[(exposure > thresholds['very_low']) & (exposure <= thresholds['low'])] = 2
    classified[(exposure > thresholds['low']) & (exposure <= thresholds['moderate'])] = 3
    classified[(exposure > thresholds['moderate']) & (exposure <= thresholds['high'])] = 4
    classified[exposure > thresholds['high']] = 5
    
    return classified


def count_exposed_buildings(
    buildings_gdf: gpd.GeoDataFrame,
    hazard_zones_gdf: gpd.GeoDataFrame,
    hazard_class_field: str = 'class'
) -> Dict:
    """
    Count buildings exposed to different hazard levels
    
    Args:
        buildings_gdf: Buildings GeoDataFrame
        hazard_zones_gdf: Hazard zones GeoDataFrame with classification
        hazard_class_field: Field name for hazard class
    
    Returns:
        Dictionary with exposure counts by hazard class
    """
    logger.info("Counting exposed buildings")
    
    # Spatial join
    exposed = gpd.sjoin(buildings_gdf, hazard_zones_gdf, how='inner', predicate='intersects')
    
    # Count by hazard class
    counts = exposed[hazard_class_field].value_counts().to_dict()
    
    logger.info(f"Exposed buildings by class: {counts}")
    
    return counts
