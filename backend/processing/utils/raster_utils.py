"""
Raster processing utilities for multi-hazard system
Handles DEM derivatives, raster-to-GeoJSON conversion, and visualization
"""

import numpy as np
import rasterio
from rasterio.features import shapes
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.io import MemoryFile
from scipy.ndimage import sobel
import json
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def calculate_slope(dem_array: np.ndarray, cell_size: float = 30) -> np.ndarray:
    """
    Calculate slope in degrees from DEM
    
    Args:
        dem_array: Digital Elevation Model as 2D array
        cell_size: Pixel size in meters
    
    Returns:
        Slope array in degrees
    """
    # Calculate gradients using Sobel filters
    dx = sobel(dem_array, axis=1) / (8 * cell_size)
    dy = sobel(dem_array, axis=0) / (8 * cell_size)
    
    # Calculate slope in radians then convert to degrees
    slope_rad = np.arctan(np.sqrt(dx**2 + dy**2))
    slope_deg = np.degrees(slope_rad)
    
    return slope_deg.astype(np.float32)


def calculate_aspect(dem_array: np.ndarray) -> np.ndarray:
    """
    Calculate aspect (orientation) in degrees from DEM
    
    Args:
        dem_array: Digital Elevation Model as 2D array
    
    Returns:
        Aspect array in degrees (0-360)
    """
    dx = sobel(dem_array, axis=1)
    dy = sobel(dem_array, axis=0)
    
    aspect_rad = np.arctan2(-dy, dx)
    aspect_deg = np.degrees(aspect_rad)
    
    # Convert to 0-360 range (0 = North, clockwise)
    aspect_deg = 90 - aspect_deg
    aspect_deg = np.where(aspect_deg < 0, aspect_deg + 360, aspect_deg)
    
    return aspect_deg.astype(np.float32)


def calculate_curvature(dem_array: np.ndarray, cell_size: float = 30) -> np.ndarray:
    """
    Calculate plan curvature from DEM
    
    Args:
        dem_array: Digital Elevation Model as 2D array
        cell_size: Pixel size in meters
    
    Returns:
        Curvature array
    """
    # Second derivatives
    dxx = sobel(sobel(dem_array, axis=1), axis=1) / (cell_size ** 2)
    dyy = sobel(sobel(dem_array, axis=0), axis=0) / (cell_size ** 2)
    
    # Plan curvature approximation
    curvature = dxx + dyy
    
    return curvature.astype(np.float32)


def raster_to_geojson(
    raster_path: Path,
    output_path: Path,
    class_names: Optional[Dict[int, str]] = None,
    simplify_tolerance: float = 0.0001
) -> dict:
    """
    Convert classified raster to GeoJSON polygons
    
    Args:
        raster_path: Path to input raster
        output_path: Path to output GeoJSON
        class_names: Mapping of pixel values to class names
        simplify_tolerance: Geometry simplification tolerance
    
    Returns:
        GeoJSON FeatureCollection as dict
    """
    logger.info(f"Converting raster {raster_path} to GeoJSON")
    
    with rasterio.open(raster_path) as src:
        image = src.read(1)
        mask = image != src.nodata
        
        features = []
        for geom, value in shapes(image, mask=mask, transform=src.transform):
            value = int(value)
            
            feature = {
                "type": "Feature",
                "geometry": geom,
                "properties": {
                    "value": value,
                    "class": class_names.get(value, f"Class_{value}") if class_names else f"Class_{value}"
                }
            }
            features.append(feature)
    
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    # Save to file
    with open(output_path, 'w') as f:
        json.dump(geojson, f)
    
    logger.info(f"Created GeoJSON with {len(features)} features")
    return geojson


def classify_raster(
    continuous_array: np.ndarray,
    thresholds: Dict[str, float],
    class_values: Optional[Dict[str, int]] = None
) -> np.ndarray:
    """
    Classify continuous raster into discrete classes based on thresholds
    
    Args:
        continuous_array: Input continuous values
        thresholds: Dictionary of class_name: threshold_value
        class_values: Optional mapping of class_name to output pixel value
    
    Returns:
        Classified array with integer values
    """
    if class_values is None:
        class_values = {name: i+1 for i, name in enumerate(sorted(thresholds.keys()))}
    
    classified = np.zeros_like(continuous_array, dtype=np.uint8)
    
    # Sort thresholds
    sorted_thresholds = sorted(thresholds.items(), key=lambda x: x[1])
    
    for i, (class_name, threshold) in enumerate(sorted_thresholds):
        if i == 0:
            mask = continuous_array <= threshold
        else:
            prev_threshold = sorted_thresholds[i-1][1]
            mask = (continuous_array > prev_threshold) & (continuous_array <= threshold)
        
        classified[mask] = class_values[class_name]
    
    # Handle values above highest threshold
    if len(sorted_thresholds) > 0:
        highest_threshold = sorted_thresholds[-1][1]
        # Find the "very_high" or highest class
        max_class = max(class_values.values())
        classified[continuous_array > highest_threshold] = max_class
    
    return classified


def save_cog(
    array: np.ndarray,
    output_path: Path,
    profile: dict,
    nodata: Optional[float] = None
) -> None:
    """
    Save array as Cloud-Optimized GeoTIFF
    
    Args:
        array: Input array
        output_path: Output path
        profile: Rasterio profile (width, height, transform, crs, etc.)
        nodata: NoData value
    """
    profile.update({
        'count': 1,
        'dtype': array.dtype,
        'compress': 'LZW',
        'tiled': True,
        'blockxsize': 256,
        'blockysize': 256,
    })
    
    if nodata is not None:
        profile['nodata'] = nodata
    
    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(array, 1)
    
    logger.info(f"Saved raster to {output_path}")


def apply_colormap(
    array: np.ndarray,
    colormap: Dict[str, str],
    class_mapping: Dict[int, str]
) -> np.ndarray:
    """
    Apply colormap to classified array for visualization
    
    Args:
        array: Classified array with integer values
        colormap: Dictionary mapping class names to hex colors
        class_mapping: Dictionary mapping pixel values to class names
    
    Returns:
        RGB array (height, width, 3)
    """
    rgb = np.zeros((*array.shape, 3), dtype=np.uint8)
    
    for value, class_name in class_mapping.items():
        if class_name in colormap:
            hex_color = colormap[class_name].lstrip('#')
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            mask = array == value
            rgb[mask] = [r, g, b]
    
    return rgb


def read_raster(file_path: Path) -> Tuple[np.ndarray, dict]:
    """
    Read raster file and return array with metadata
    
    Args:
        file_path: Path to raster file
    
    Returns:
        Tuple of (array, profile)
    """
    with rasterio.open(file_path) as src:
        array = src.read(1)
        profile = src.profile.copy()
    
    return array, profile


def align_rasters(
    rasters: List[Path],
    reference_idx: int = 0
) -> List[Tuple[np.ndarray, dict]]:
    """
    Align multiple rasters to same extent and resolution
    
    Args:
        rasters: List of raster file paths
        reference_idx: Index of reference raster for alignment
    
    Returns:
        List of (array, profile) tuples
    """
    # Read reference
    ref_array, ref_profile = read_raster(rasters[reference_idx])
    aligned = [(ref_array, ref_profile)]
    
    # Align others to reference
    for i, raster_path in enumerate(rasters):
        if i == reference_idx:
            continue
        
        with rasterio.open(raster_path) as src:
            # Create output array with reference shape
            aligned_array = np.empty(ref_array.shape, dtype=src.dtypes[0])
            
            reproject(
                source=rasterio.band(src, 1),
                destination=aligned_array,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=ref_profile['transform'],
                dst_crs=ref_profile['crs'],
                resampling=Resampling.bilinear
            )
            
            aligned.append((aligned_array, ref_profile))
    
    return aligned
