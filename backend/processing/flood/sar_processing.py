"""
SAR processing module for flood detection using Sentinel-1
Implements thresholding and DEM-based masking
"""

import numpy as np
import rasterio
from pathlib import Path
from typing import Tuple, Optional
from scipy.ndimage import binary_opening, binary_closing
from skimage.filters import threshold_otsu
import logging

from ..utils.raster_utils import read_raster, save_cog

logger = logging.getLogger(__name__)


def apply_threshold(
    sar_array: np.ndarray,
    threshold: Optional[float] = None,
    use_otsu: bool = True
) -> np.ndarray:
    """
    Apply threshold to SAR backscatter to detect water
    
    Args:
        sar_array: SAR backscatter values (dB)
        threshold: Manual threshold value (dB), if not using Otsu
        use_otsu: Use Otsu's automatic thresholding
    
    Returns:
        Binary flood mask (1=water, 0=non-water)
    """
    logger.info("Applying threshold to SAR data")
    
    # Remove nodata
    valid_mask = ~np.isnan(sar_array) & (sar_array != -9999)
    
    if use_otsu:
        # Otsu's method for automatic thresholding
        valid_values = sar_array[valid_mask]
        threshold = threshold_otsu(valid_values)
        logger.info(f"Otsu threshold: {threshold:.2f} dB")
    else:
        logger.info(f"Using manual threshold: {threshold:.2f} dB")
    
    # Water typically has low backscatter values
    water_mask = np.zeros_like(sar_array, dtype=np.uint8)
    water_mask[valid_mask] = (sar_array[valid_mask] < threshold).astype(np.uint8)
    
    logger.info(f"Initial water pixels: {np.sum(water_mask)}")
    
    return water_mask


def apply_dem_mask(
    water_mask: np.ndarray,
    dem_array: np.ndarray,
    elevation_threshold: float = 100
) -> np.ndarray:
    """
    Remove false positives from water mask using DEM elevation
    
    Args:
        water_mask: Binary water mask
        dem_array: Digital Elevation Model
        elevation_threshold: Elevation above which to remove water detections (meters)
    
    Returns:
        Refined water mask
    """
    logger.info(f"Applying DEM mask (elevation threshold: {elevation_threshold}m)")
    
    # Remove water detections above threshold elevation
    high_elevation = dem_array > elevation_threshold
    refined_mask = water_mask.copy()
    refined_mask[high_elevation] = 0
    
    removed_pixels = np.sum(water_mask) - np.sum(refined_mask)
    logger.info(f"Removed {removed_pixels} high-elevation false positives")
    
    return refined_mask


def apply_morphological_operations(
    mask: np.ndarray,
    kernel_size: int = 3
) -> np.ndarray:
    """
    Apply morphological opening and closing to clean up mask
    
    Args:
        mask: Binary mask
        kernel_size: Size of structuring element
    
    Returns:
        Cleaned mask
    """
    logger.info("Applying morphological operations")
    
    # Create structuring element
    from scipy.ndimage import generate_binary_structure
    structure = generate_binary_structure(2, 1)
    
    # Opening (erosion then dilation) - removes small objects
    opened = binary_opening(mask, structure=structure, iterations=kernel_size)
    
    # Closing (dilation then erosion) - fills small holes
    cleaned = binary_closing(opened, structure=structure, iterations=kernel_size)
    
    logger.info(f"Cleaned pixels: {np.sum(cleaned)}")
    
    return cleaned.astype(np.uint8)


def process_sar_for_flood(
    sar_path: Path,
    dem_path: Path,
    output_path: Path,
    threshold: Optional[float] = -18,
    use_otsu: bool = True,
    dem_threshold: float = 100,
    morphology_kernel: int = 3
) -> np.ndarray:
    """
    Complete SAR processing pipeline for flood detection
    
    Args:
        sar_path: Path to Sentinel-1 SAR backscatter (dB)
        dem_path: Path to DEM
        output_path: Path to save flood mask
        threshold: Manual threshold for water detection
        use_otsu: Use automatic Otsu thresholding
        dem_threshold: Elevation threshold for masking
        morphology_kernel: Morphological kernel size
    
    Returns:
        Binary flood mask
    """
    logger.info("="*60)
    logger.info("PROCESSING SAR FOR FLOOD DETECTION")
    logger.info("="*60)
    
    # Read SAR data
    logger.info(f"Reading SAR from {sar_path}")
    sar_array, sar_profile = read_raster(sar_path)
    
    # Read DEM
    logger.info(f"Reading DEM from {dem_path}")
    dem_array, _ = read_raster(dem_path)
    
    # Ensure same dimensions
    if sar_array.shape != dem_array.shape:
        raise ValueError(
            f"SAR and DEM dimensions mismatch: {sar_array.shape} vs {dem_array.shape}"
        )
    
    # Step 1: Apply threshold
    water_mask = apply_threshold(sar_array, threshold=threshold, use_otsu=use_otsu)
    
    # Step 2: Apply DEM mask
    water_mask = apply_dem_mask(water_mask, dem_array, elevation_threshold=dem_threshold)
    
    # Step 3: Morphological cleanup
    water_mask = apply_morphological_operations(water_mask, kernel_size=morphology_kernel)
    
    # Save output
    save_cog(water_mask, output_path, sar_profile, nodata=0)
    
    logger.info(f"Flood mask saved to {output_path}")
    logger.info("="*60)
    
    return water_mask


def calculate_flood_statistics(flood_mask: np.ndarray, pixel_size: float = 30) -> dict:
    """
    Calculate statistics about flood extent
    
    Args:
        flood_mask: Binary flood mask
        pixel_size: Pixel size in meters
    
    Returns:
        Dictionary with flood statistics
    """
    flood_pixels = np.sum(flood_mask)
    flood_area_m2 = flood_pixels * (pixel_size ** 2)
    flood_area_km2 = flood_area_m2 / 1_000_000
    
    stats = {
        'flood_pixels': int(flood_pixels),
        'flood_area_m2': float(flood_area_m2),
        'flood_area_km2': float(flood_area_km2),
        'total_pixels': int(flood_mask.size),
        'flood_percentage': float(flood_pixels / flood_mask.size * 100)
    }
    
    logger.info(f"Flood statistics: {stats}")
    
    return stats
