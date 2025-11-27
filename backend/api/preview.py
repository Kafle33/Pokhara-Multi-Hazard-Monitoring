"""
Raster preview API endpoints
Serves raster visualizations as PNG with colormaps
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pathlib import Path
import rasterio
import numpy as np
from io import BytesIO
from PIL import Image
import logging

from config import OUTPUTS_DIR, COLORMAPS
from processing.utils.raster_utils import apply_colormap

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/preview", tags=["preview"])


def get_colormap_for_layer(layer_name: str) -> tuple:
    """
    Get appropriate colormap and class mapping for layer
    
    Args:
        layer_name: Name of the layer
    
    Returns:
        Tuple of (colormap_dict, class_mapping_dict)
    """
    # Determine layer type from name
    if "landslide" in layer_name.lower():
        colormap = COLORMAPS['landslide']
        class_mapping = {1: "very_low", 2: "low", 3: "moderate", 4: "high", 5: "very_high"}
    elif "flood" in layer_name.lower():
        colormap = COLORMAPS['flood']
        class_mapping = {0: "no_flood", 1: "flood"}
    elif "exposure" in layer_name.lower():
        colormap = COLORMAPS['exposure']
        class_mapping = {1: "very_low", 2: "low", 3: "moderate", 4: "high", 5: "very_high"}
    elif "multi_hazard" in layer_name.lower() or "risk" in layer_name.lower():
        colormap = COLORMAPS['multi_hazard']
        class_mapping = {1: "very_low", 2: "low", 3: "moderate", 4: "high", 5: "very_high"}
    else:
        # Default colormap
        colormap = COLORMAPS['multi_hazard']
        class_mapping = {1: "very_low", 2: "low", 3: "moderate", 4: "high", 5: "very_high"}
    
    return colormap, class_mapping


@router.get("/raster/{layer_name}")
async def preview_raster(layer_name: str):
    """
    Generate and serve PNG preview of raster with appropriate colormap
    
    Args:
        layer_name: Name of the raster layer (without .tif extension)
    
    Returns:
        PNG image
    """
    try:
        # Find raster file (try multiple patterns)
        possible_paths = [
            OUTPUTS_DIR / f"{layer_name}.tif",
            OUTPUTS_DIR / f"{layer_name}_classified.tif",
            OUTPUTS_DIR / f"{layer_name}_probability.tif",
        ]
        
        raster_path = None
        for path in possible_paths:
            if path.exists():
                raster_path = path
                break
        
        if raster_path is None:
            raise HTTPException(
                status_code=404,
                detail=f"Raster '{layer_name}' not found"
            )
        
        # Read raster
        with rasterio.open(raster_path) as src:
            array = src.read(1)
        
        # Get colormap
        colormap, class_mapping = get_colormap_for_layer(layer_name)
        
        # Apply colormap
        rgb = apply_colormap(array, colormap, class_mapping)
        
        # Convert to PIL Image
        img = Image.fromarray(rgb, mode='RGB')
        
        # Save to BytesIO
        buf = BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        
        logger.info(f"Serving raster preview: {layer_name}")
        
        return StreamingResponse(buf, media_type="image/png")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating raster preview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/thumbnail/{layer_name}")
async def get_thumbnail(layer_name: str, max_size: int = 256):
    """
    Generate thumbnail preview of raster
    
    Args:
        layer_name: Name of the raster layer
        max_size: Maximum dimension for thumbnail
    
    Returns:
        PNG thumbnail
    """
    try:
        # Find raster
        possible_paths = [
            OUTPUTS_DIR / f"{layer_name}.tif",
            OUTPUTS_DIR / f"{layer_name}_classified.tif",
        ]
        
        raster_path = None
        for path in possible_paths:
            if path.exists():
                raster_path = path
                break
        
        if raster_path is None:
            raise HTTPException(status_code=404, detail=f"Raster '{layer_name}' not found")
        
        # Read with downsampling for thumbnail
        with rasterio.open(raster_path) as src:
            # Calculate overview factor
            factor = max(src.width // max_size, src.height // max_size, 1)
            
            # Read downsampled
            array = src.read(
                1,
                out_shape=(src.height // factor, src.width // factor),
                resampling=rasterio.enums.Resampling.nearest
            )
        
        # Get colormap and apply
        colormap, class_mapping = get_colormap_for_layer(layer_name)
        rgb = apply_colormap(array, colormap, class_mapping)
        
        # Create thumbnail
        img = Image.fromarray(rgb, mode='RGB')
        img.thumbnail((max_size, max_size))
        
        # Save to buffer
        buf = BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        
        return StreamingResponse(buf, media_type="image/png")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating thumbnail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
