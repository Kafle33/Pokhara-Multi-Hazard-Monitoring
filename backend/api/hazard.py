"""
Hazard processing API endpoints
Provides REST API for triggering hazard analyses
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, Dict
from pathlib import Path
import logging

from processing.landslide.pipeline import run_landslide_pipeline
from processing.flood.pipeline import run_flood_pipeline
from processing.exposure.pipeline import run_exposure_pipeline
from processing.multi_hazard import run_multi_hazard_integration

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/hazard", tags=["hazard"])


class HazardRequest(BaseModel):
    """Base request model for hazard processing"""
    train_model: Optional[bool] = Field(False, description="Train new ML model (landslide only)")
    output_dir: Optional[str] = Field(None, description="Custom output directory")


class LandslideRequest(HazardRequest):
    """Landslide susceptibility request"""
    dem_path: Optional[str] = None
    landcover_path: Optional[str] = None
    rainfall_path: Optional[str] = None


class FloodRequest(HazardRequest):
    """Flood mapping request"""
    sar_path: Optional[str] = None
    dem_path: Optional[str] = None
    threshold: Optional[float] = Field(-18, description="SAR threshold in dB")
    use_otsu: Optional[bool] = Field(True, description="Use Otsu automatic thresholding")


class ExposureRequest(HazardRequest):
    """Exposure analysis request"""
    hazard_raster: str = Field(..., description="Path to hazard raster for exposure analysis")


class HazardResponse(BaseModel):
    """Response model for hazard processing"""
    status: str
    message: str
    outputs: Optional[Dict[str, str]] = None


@router.post("/landslide", response_model=HazardResponse)
async def process_landslide(request: LandslideRequest):
    """
    Trigger landslide susceptibility analysis
    
    Returns paths to generated outputs (GeoTIFF + GeoJSON)
    """
    try:
        logger.info("Processing landslide susceptibility request")
        
        # Prepare parameters
        kwargs = {
            "train_new_model": request.train_model
        }
        
        if request.dem_path:
            kwargs["dem_path"] = Path(request.dem_path)
        if request.landcover_path:
            kwargs["landcover_path"] = Path(request.landcover_path)
        if request.rainfall_path:
            kwargs["rainfall_path"] = Path(request.rainfall_path)
        if request.output_dir:
            kwargs["output_dir"] = Path(request.output_dir)
        
        # Run pipeline
        outputs = run_landslide_pipeline(**kwargs)
        
        # Convert Path objects to strings
        outputs_str = {k: str(v) for k, v in outputs.items()}
        
        return HazardResponse(
            status="success",
            message="Landslide susceptibility analysis complete",
            outputs=outputs_str
        )
    
    except Exception as e:
        logger.error(f"Landslide processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/flood", response_model=HazardResponse)
async def process_flood(request: FloodRequest):
    """
    Trigger flood mapping from SAR data
    
    Returns paths to generated outputs (GeoTIFF + GeoJSON)
    """
    try:
        logger.info("Processing flood mapping request")
        
        kwargs = {}
        
        if request.sar_path:
            kwargs["sar_path"] = Path(request.sar_path)
        if request.dem_path:
            kwargs["dem_path"] = Path(request.dem_path)
        if request.output_dir:
            kwargs["output_dir"] = Path(request.output_dir)
        
        # Run pipeline
        outputs = run_flood_pipeline(**kwargs)
        
        # Format statistics
        if 'statistics' in outputs:
            stats = outputs.pop('statistics')
            outputs['statistics'] = str(stats)
        
        # Convert Path objects to strings
        outputs_str = {k: str(v) for k, v in outputs.items()}
        
        return HazardResponse(
            status="success",
            message="Flood mapping complete",
            outputs=outputs_str
        )
    
    except Exception as e:
        logger.error(f"Flood processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/exposure", response_model=HazardResponse)
async def process_exposure(request: ExposureRequest):
    """
    Trigger exposure analysis
    
    Requires a hazard raster (landslide or flood) as input
    """
    try:
        logger.info("Processing exposure analysis request")
        
        hazard_path = Path(request.hazard_raster)
        
        if not hazard_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Hazard raster not found: {hazard_path}"
            )
        
        kwargs = {"hazard_raster_path": hazard_path}
        
        if request.output_dir:
            kwargs["output_dir"] = Path(request.output_dir)
        
        # Run pipeline
        outputs = run_exposure_pipeline(**kwargs)
        
        # Convert Path objects to strings
        outputs_str = {k: str(v) for k, v in outputs.items()}
        
        return HazardResponse(
            status="success",
            message="Exposure analysis complete",
            outputs=outputs_str
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Exposure processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/multi_risk", response_model=HazardResponse)
async def process_multi_hazard():
    """
    Generate composite multi-hazard risk map
    
    Combines landslide, flood, and exposure outputs
    """
    try:
        logger.info("Processing multi-hazard integration request")
        
        # Run integration
        outputs = run_multi_hazard_integration()
        
        # Convert Path objects to strings
        outputs_str = {k: str(v) for k, v in outputs.items()}
        
        return HazardResponse(
            status="success",
            message="Multi-hazard risk map generated",
            outputs=outputs_str
        )
    
    except Exception as e:
        logger.error(f"Multi-hazard integration error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_status():
    """Check API status"""
    return {
        "status": "online",
        "service": "Pokhara Multi-Hazard Monitoring System",
        "version": "1.0.0"
    }
