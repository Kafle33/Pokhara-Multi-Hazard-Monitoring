"""
GeoJSON utilities for multi-hazard system
"""

import json
import geopandas as gpd
from shapely.geometry import shape, mapping
from shapely.ops import unary_union
from typing import Dict, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def read_geojson(file_path: Path) -> dict:
    """Read GeoJSON file"""
    with open(file_path, 'r') as f:
        return json.load(f)


def write_geojson(geojson: dict, file_path: Path) -> None:
    """Write GeoJSON to file"""
    with open(file_path, 'w') as f:
        json.dump(geojson, f, indent=2)
    logger.info(f"Saved GeoJSON to {file_path}")


def simplify_geojson(geojson: dict, tolerance: float = 0.0001) -> dict:
    """Simplify geometries in GeoJSON"""
    gdf = gpd.GeoDataFrame.from_features(geojson['features'])
    gdf['geometry'] = gdf['geometry'].simplify(tolerance)
    
    return json.loads(gdf.to_json())


def merge_polygons(geojson: dict, group_by: str = None) -> dict:
    """
    Merge adjacent polygons in GeoJSON
    
    Args:
        geojson: Input GeoJSON
        group_by: Property name to group by before merging
    """
    gdf = gpd.GeoDataFrame.from_features(geojson['features'])
    
    if group_by and group_by in gdf.columns:
        merged_features = []
        for group_value in gdf[group_by].unique():
            group_gdf = gdf[gdf[group_by] == group_value]
            merged_geom = unary_union(group_gdf.geometry)
            
            feature = {
                "type": "Feature",
                "geometry": mapping(merged_geom),
                "properties": {group_by: group_value}
            }
            merged_features.append(feature)
        
        return {
            "type": "FeatureCollection",
            "features": merged_features
        }
    else:
        # Merge all
        merged_geom = unary_union(gdf.geometry)
        return {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": mapping(merged_geom),
                "properties": {}
            }]
        }


def calculate_area(geojson: dict, unit: str = 'm2') -> dict:
    """
    Add area property to each feature
    
    Args:
        geojson: Input GeoJSON
        unit: Area unit ('m2', 'km2', 'ha')
    """
    gdf = gpd.GeoDataFrame.from_features(geojson['features'], crs="EPSG:4326")
    
    # Reproject to UTM for accurate area calculation (assuming Nepal)
    gdf_utm = gdf.to_crs("EPSG:32645")  # UTM Zone 45N for Pokhara
    
    areas = gdf_utm.geometry.area
    
    if unit == 'km2':
        areas = areas / 1_000_000
    elif unit == 'ha':
        areas = areas / 10_000
    
    features = json.loads(gdf.to_json())['features']
    for i, feature in enumerate(features):
        feature['properties']['area'] = float(areas.iloc[i])
        feature['properties']['area_unit'] = unit
    
    return {
        "type": "FeatureCollection",
        "features": features
    }


def filter_by_area(geojson: dict, min_area: float) -> dict:
    """Remove features smaller than minimum area (in m²)"""
    filtered_features = []
    
    for feature in geojson['features']:
        geom = shape(feature['geometry'])
        # Simple area filter (not accurate for lat/lon, but fast)
        if geom.area * 111000 * 111000 > min_area:  # Rough conversion
            filtered_features.append(feature)
    
    return {
        "type": "FeatureCollection",
        "features": filtered_features
    }


def add_properties(geojson: dict, properties: Dict) -> dict:
    """Add properties to all features"""
    for feature in geojson['features']:
        feature['properties'].update(properties)
    return geojson
