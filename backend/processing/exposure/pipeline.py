"""
End-to-end exposure analysis pipeline
"""

from pathlib import Path
from typing import Optional, Dict
import logging

from .analysis import (
    rasterize_buildings,
    calculate_exposure_density,
    classify_exposure
)
from ..utils.raster_utils import read_raster, save_cog, raster_to_geojson
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import EXPOSURE_CONFIG, OUTPUTS_DIR, PROCESSED_DATA_DIR, INPUT_FILES

logger = logging.getLogger(__name__)


def run_exposure_pipeline(
    hazard_raster_path: Path,
    buildings_path: Optional[Path] = None,
    population_path: Optional[Path] = None,
    output_dir: Optional[Path] = None
) -> Dict[str, Path]:
    """
    Run complete exposure analysis pipeline
    
    Args:
        hazard_raster_path: Path to hazard raster (landslide or flood)
        buildings_path: Path to buildings GeoJSON
        population_path: Path to population raster
        output_dir: Directory for outputs
    
    Returns:
        Dictionary mapping output names to file paths
    """
    logger.info("="*60)
    logger.info("STARTING EXPOSURE ANALYSIS PIPELINE")
    logger.info("="*60)
    
    # Use defaults from config if not provided
    if buildings_path is None:
        buildings_path = INPUT_FILES['buildings']
    if population_path is None:
        population_path = INPUT_FILES.get('population')
    if output_dir is None:
        output_dir = OUTPUTS_DIR
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    outputs = {}
    
    # STEP 1: Read hazard raster
    logger.info(f"Step 1: Reading hazard raster from {hazard_raster_path}")
    hazard_array, hazard_profile = read_raster(hazard_raster_path)
    
    # STEP 2: Rasterize buildings
    logger.info("Step 2: Rasterizing buildings")
    buildings_raster_path = PROCESSED_DATA_DIR / "buildings_raster.tif"
    
    if buildings_path.exists():
        buildings_array = rasterize_buildings(
            buildings_path=buildings_path,
            reference_raster_path=hazard_raster_path,
            output_path=buildings_raster_path
        )
    else:
        logger.warning(f"Buildings not found at {buildings_path}, using empty array")
        buildings_array = np.zeros_like(hazard_array)
    
    # STEP 3: Read population if available
    population_array = None
    if population_path and population_path.exists():
        logger.info("Step 3: Reading population data")
        population_array, _ = read_raster(population_path)
    else:
        logger.info("Step 3: Population data not available, skipping")
    
    # STEP 4: Calculate exposure density
    logger.info("Step 4: Calculating exposure density")
    exposure = calculate_exposure_density(
        hazard_raster=hazard_array,
        buildings_raster=buildings_array,
        population_raster=population_array
    )
    
    # Save continuous exposure
    exposure_path = output_dir / "exposure_density.tif"
    save_cog(exposure, exposure_path, hazard_profile, nodata=0)
    outputs['exposure_raster'] = exposure_path
    
    # STEP 5: Classify exposure
    logger.info("Step 5: Classifying exposure levels")
    classified_exposure = classify_exposure(exposure)
    
    # Save classified exposure
    classified_path = output_dir / "exposure_classified.tif"
    save_cog(classified_exposure, classified_path, hazard_profile, nodata=0)
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
    
    geojson_path = output_dir / "exposure_zones.geojson"
    raster_to_geojson(
        raster_path=classified_path,
        output_path=geojson_path,
        class_names=class_names
    )
    outputs['geojson'] = geojson_path
    
    logger.info("="*60)
    logger.info("EXPOSURE ANALYSIS PIPELINE COMPLETE")
    logger.info(f"Outputs: {outputs}")
    logger.info("="*60)
    
    return outputs


if __name__ == "__main__":
    # Example usage
    import logging
    import numpy as np
    logging.basicConfig(level=logging.INFO)
    
    # This would use an actual hazard raster in practice
    # outputs = run_exposure_pipeline(hazard_raster_path=Path("../outputs/landslide_susceptibility.tif"))
