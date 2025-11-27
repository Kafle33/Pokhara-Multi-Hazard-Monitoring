"""
Generate sample geospatial data for Pokhara Multi-Hazard System
Creates synthetic DEM, landcover, rainfall, SAR, and building data
"""

import numpy as np
import rasterio
from rasterio.transform import from_bounds
import geopandas as gpd
from shapely.geometry import Point, Polygon
import json

# Pokhara region bounds (approximate)
POKHARA_BOUNDS = {
    'west': 83.90,
    'south': 28.15,
    'east': 84.05,
    'north': 28.30
}

# Raster dimensions
WIDTH = 500
HEIGHT = 500

# Create transform
transform = from_bounds(
    POKHARA_BOUNDS['west'],
    POKHARA_BOUNDS['south'],
    POKHARA_BOUNDS['east'],
    POKHARA_BOUNDS['north'],
    WIDTH,
    HEIGHT
)

# Profile for rasters
profile = {
    'driver': 'GTiff',
    'dtype': 'float32',
    'width': WIDTH,
    'height': HEIGHT,
    'count': 1,
    'crs': 'EPSG:4326',
    'transform': transform,
    'nodata': -9999
}

print("Generating sample geospatial data for Pokhara...")

# 1. Generate DEM (Digital Elevation Model)
print("\n1. Creating DEM...")
# Create realistic elevation pattern (higher in north, lower in south)
x = np.linspace(0, 1, WIDTH)
y = np.linspace(0, 1, HEIGHT)
X, Y = np.meshgrid(x, y)

# Base elevation with gradient
dem = 800 + 1200 * Y  # 800m to 2000m elevation

# Add some terrain features
dem += 200 * np.sin(X * 4 * np.pi) * np.cos(Y * 3 * np.pi)
dem += 150 * np.random.randn(HEIGHT, WIDTH)  # Add noise

# Add a valley
valley_mask = (X > 0.4) & (X < 0.6) & (Y > 0.3) & (Y < 0.7)
dem[valley_mask] -= 300

dem = dem.astype(np.float32)

with rasterio.open('../data/raw/dem.tif', 'w', **profile) as dst:
    dst.write(dem, 1)
print(f"   DEM created: range {dem.min():.0f}m to {dem.max():.0f}m")

# 2. Generate Landcover
print("\n2. Creating Landcover...")
landcover = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)

# Different landcover types
# 1=forest, 2=agriculture, 3=urban, 4=water, 5=barren
landcover[:] = 1  # Default forest

# Agriculture in valleys and lower elevations
landcover[dem < 1200] = 2

# Urban areas (concentrated in lower areas)
urban_mask = (X > 0.35) & (X < 0.65) & (Y > 0.2) & (Y < 0.5) & (dem < 1000)
landcover[urban_mask] = 3

# Water bodies
water_mask = (X > 0.45) & (X < 0.55) & (Y > 0.6) & (Y < 0.75) & (dem < 850)
landcover[water_mask] = 4

# Barren at high elevations
landcover[dem > 1800] = 5

profile_uint8 = profile.copy()
profile_uint8['dtype'] = 'uint8'
profile_uint8['nodata'] = 0  # Valid for uint8
with rasterio.open('../data/raw/landcover.tif', 'w', **profile_uint8) as dst:
    dst.write(landcover, 1)
print(f"   Landcover created with {len(np.unique(landcover))} classes")

# 3. Generate Rainfall
print("\n3. Creating Rainfall data...")
# Higher rainfall in mountainous areas
rainfall = 1500 + 500 * Y  # 1500-2000 mm/year
rainfall += 200 * np.random.randn(HEIGHT, WIDTH)
rainfall = np.maximum(rainfall, 1000)  # Minimum 1000mm
rainfall = rainfall.astype(np.float32)

with rasterio.open('../data/raw/rainfall.tif', 'w', **profile) as dst:
    dst.write(rainfall, 1)
print(f"   Rainfall created: {rainfall.min():.0f} to {rainfall.max():.0f} mm/year")

# 4. Generate Sentinel-1 SAR (backscatter in dB)
print("\n4. Creating Sentinel-1 SAR data...")
# Water has low backscatter (<-18 dB)
# Land has higher backscatter (-10 to -5 dB)
sar = -8 + 3 * np.random.randn(HEIGHT, WIDTH)

# Make water bodies have low backscatter
sar[landcover == 4] = -22 + 2 * np.random.randn(np.sum(landcover == 4))

# Simulate flood in low-lying areas
flood_zone = (dem < 900) & (Y < 0.4)
sar[flood_zone] = -20 + 3 * np.random.randn(np.sum(flood_zone))

sar = sar.astype(np.float32)

with rasterio.open('../data/raw/sentinel1_sar.tif', 'w', **profile) as dst:
    dst.write(sar, 1)
print(f"   SAR created: {sar.min():.1f} to {sar.max():.1f} dB")

# 5. Generate Building Footprints
print("\n5. Creating building footprints...")
buildings = []

# Generate buildings in urban areas
np.random.seed(42)
n_buildings = 200

for i in range(n_buildings):
    # Concentrate buildings in urban-friendly areas
    lon = np.random.uniform(POKHARA_BOUNDS['west'] + 0.02, POKHARA_BOUNDS['east'] - 0.02)
    lat = np.random.uniform(POKHARA_BOUNDS['south'] + 0.02, POKHARA_BOUNDS['north'] - 0.05)
    
    # Building size (small rectangles)
    width = np.random.uniform(0.0002, 0.0008)
    height = np.random.uniform(0.0002, 0.0008)
    
    # Create rectangle
    coords = [
        (lon, lat),
        (lon + width, lat),
        (lon + width, lat + height),
        (lon, lat + height),
        (lon, lat)
    ]
    
    buildings.append({
        'type': 'Feature',
        'geometry': {
            'type': 'Polygon',
            'coordinates': [coords]
        },
        'properties': {
            'id': i,
            'type': 'residential' if i % 3 != 0 else 'commercial'
        }
    })

buildings_geojson = {
    'type': 'FeatureCollection',
    'features': buildings
}

with open('../data/raw/buildings.geojson', 'w') as f:
    json.dump(buildings_geojson, f)
print(f"   Created {n_buildings} building footprints")

# 6. Generate Landslide Inventory (training points)
print("\n6. Creating landslide inventory...")
landslide_points = []

# Generate landslide points in susceptible areas:
# - Steep slopes (high elevation gradients)
# - High rainfall areas
n_landslides = 50

for i in range(n_landslides):
    # Prefer northern (mountainous) areas
    lon = np.random.uniform(POKHARA_BOUNDS['west'] + 0.01, POKHARA_BOUNDS['east'] - 0.01)
    lat = np.random.uniform(POKHARA_BOUNDS['south'] + 0.08, POKHARA_BOUNDS['north'] - 0.01)
    
    landslide_points.append({
        'type': 'Feature',
        'geometry': {
            'type': 'Point',
            'coordinates': [lon, lat]
        },
        'properties': {
            'id': i,
            'date': '2024-01-01',
            'type': 'debris_flow'
        }
    })

landslide_geojson = {
    'type': 'FeatureCollection',
    'features': landslide_points
}

with open('../data/raw/landslide_inventory.geojson', 'w') as f:
    json.dump(landslide_geojson, f)
print(f"   Created {n_landslides} landslide inventory points")

print("\n" + "="*60)
print("Sample data generation complete!")
print("="*60)
print("\nGenerated files:")
print("  ✓ data/raw/dem.tif")
print("  ✓ data/raw/landcover.tif")
print("  ✓ data/raw/rainfall.tif")
print("  ✓ data/raw/sentinel1_sar.tif")
print("  ✓ data/raw/buildings.geojson")
print("  ✓ data/raw/landslide_inventory.geojson")
print("\nReady to run hazard processing pipelines!")
