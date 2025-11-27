"""
End-to-end flood mapping pipeline using Sentinel-1 SAR
"""

from pathlib import Path
from typing import Optional, Dict
import logging

from .sar_processing import process_sar_for_flood, calculate_flood_statistics
from ..utils.raster_utils import raster_to_geojson
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import FLOOD_CONFIG, OUTPUTS_DIR, INPUT_FILES

logger = logging.getLogger(__name__)


def run_flood_pipeline(
    sar_path: Optional[Path] = None,
    dem_path: Optional[Path] = None,
    output_dir: Optional[Path] = None
) -> Dict[str, Path]:
    """
    Run complete flood mapping pipeline
    
    Args:
        sar_path: Path to Sentinel-1 SAR backscatter
        dem_path: Path to DEM
        output_dir: Directory for outputs
    
    Returns:
        Dictionary mapping output names to file paths
    """
    logger.info("="*60)
    logger.info("STARTING FLOOD MAPPING PIPELINE")
    logger.info("="*60)
    
    # Use defaults from config if not provided
    if sar_path is None:
        sar_path = INPUT_FILES['sentinel1_sar']
    if dem_path is None:
        dem_path = INPUT_FILES['dem']
    if output_dir is None:
        output_dir = OUTPUTS_DIR
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    outputs = {}
    
    # STEP 1: Process SAR for flood detection
    logger.info("Step 1: Processing SAR for flood detection")
    
    flood_mask_path = output_dir / "flood_extent.tif"
    flood_mask = process_sar_for_flood(
        sar_path=sar_path,
        dem_path=dem_path,
        output_path=flood_mask_path,
        threshold=FLOOD_CONFIG['sar_threshold'],
        use_otsu=FLOOD_CONFIG['use_otsu'],
        dem_threshold=FLOOD_CONFIG['dem_threshold'],
        morphology_kernel=FLOOD_CONFIG['morphology_kernel_size']
    )
    outputs['flood_raster'] = flood_mask_path
    
    # STEP 2: Calculate statistics
    logger.info("Step 2: Calculating flood statistics")
    stats = calculate_flood_statistics(flood_mask)
    outputs['statistics'] = stats
    
    # STEP 3: Convert to GeoJSON
    logger.info("Step 3: Converting to GeoJSON")
    
    class_names = {
        0: "no_flood",
        1: "flood"
    }
    
    geojson_path = output_dir / "flood_extent.geojson"
    raster_to_geojson(
        raster_path=flood_mask_path,
        output_path=geojson_path,
        class_names=class_names
    )
    outputs['geojson'] = geojson_path
    
    logger.info("="*60)
    logger.info("FLOOD MAPPING PIPELINE COMPLETE")
    logger.info(f"Outputs: {outputs}")
    logger.info("="*60)
    
    return outputs


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    outputs = run_flood_pipeline()
    print(f"Pipeline complete. Outputs: {outputs}")
