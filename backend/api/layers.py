"""
Layer management API endpoints
Provides access to processed layers (list, retrieve GeoJSON)
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from typing import List
from pathlib import Path
import json
import logging

from config import OUTPUTS_DIR

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/layers", tags=["layers"])


@router.get("/list")
async def list_layers():
    """
    List all available processed layers
    
    Returns:
        List of available layers with metadata
    """
    try:
        layers = []
        
        # Scan outputs directory for GeoJSON files
        if OUTPUTS_DIR.exists():
            for geojson_file in OUTPUTS_DIR.glob("*.geojson"):
                # Get corresponding raster if exists
                raster_file = geojson_file.with_suffix('.tif')
                
                layer_info = {
                    "name": geojson_file.stem,
                    "geojson": str(geojson_file),
                    "raster": str(raster_file) if raster_file.exists() else None,
                    "type": "vector",
                }
                
                # Try to get feature count
                try:
                    with open(geojson_file, 'r') as f:
                        data = json.load(f)
                        layer_info["feature_count"] = len(data.get('features', []))
                except:
                    pass
                
                layers.append(layer_info)
        
        logger.info(f"Found {len(layers)} layers")
        
        return {
            "count": len(layers),
            "layers": layers
        }
    
    except Exception as e:
        logger.error(f"Error listing layers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{layer_name}")
async def get_layer(layer_name: str):
    """
    Retrieve GeoJSON for a specific layer
    
    Args:
        layer_name: Name of the layer (without .geojson extension)
    
    Returns:
        GeoJSON FeatureCollection
    """
    try:
        # Find GeoJSON file
        geojson_path = OUTPUTS_DIR / f"{layer_name}.geojson"
        
        if not geojson_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Layer '{layer_name}' not found"
            )
        
        # Read and return GeoJSON
        with open(geojson_path, 'r') as f:
            geojson = json.load(f)
        
        logger.info(f"Serving layer: {layer_name}")
        
        return geojson
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving layer {layer_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{layer_name}/download")
async def download_layer(layer_name: str, format: str = "geojson"):
    """
    Download layer file
    
    Args:
        layer_name: Name of the layer
        format: File format ('geojson' or 'tif')
    
    Returns:
        File download
    """
    try:
        if format == "geojson":
            file_path = OUTPUTS_DIR / f"{layer_name}.geojson"
            media_type = "application/geo+json"
        elif format == "tif":
            file_path = OUTPUTS_DIR / f"{layer_name}.tif"
            media_type = "image/tiff"
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format: {format}"
            )
        
        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"File not found: {file_path.name}"
            )
        
        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            filename=file_path.name
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading layer: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
