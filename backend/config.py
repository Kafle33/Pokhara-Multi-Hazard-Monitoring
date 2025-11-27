"""
Configuration module for Pokhara Multi-Hazard Monitoring System
Contains all system parameters, paths, and settings
"""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
OUTPUTS_DIR = DATA_DIR / "outputs"
MODELS_DIR = BASE_DIR / "backend" / "models"

# Ensure directories exist
for dir_path in [RAW_DATA_DIR, PROCESSED_DATA_DIR, OUTPUTS_DIR, MODELS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Input data files (expected in data/raw/)
INPUT_FILES = {
    "dem": RAW_DATA_DIR / "dem.tif",
    "landcover": RAW_DATA_DIR / "landcover.tif",
    "rainfall": RAW_DATA_DIR / "rainfall.tif",
    "sentinel1_sar": RAW_DATA_DIR / "sentinel1_sar.tif",
    "buildings": RAW_DATA_DIR / "buildings.geojson",
    "population": RAW_DATA_DIR / "population.tif",
    "landslide_inventory": RAW_DATA_DIR / "landslide_inventory.geojson",
}

# Raster processing settings
RASTER_CONFIG = {
    "default_resolution": 30,  # meters
    "nodata_value": -9999,
    "compression": "LZW",
    "tiled": True,
    "blockxsize": 256,
    "blockysize": 256,
}

# Landslide susceptibility settings
LANDSLIDE_CONFIG = {
    "model_type": "RandomForest",  # or "XGBoost"
    "n_estimators": 100,
    "max_depth": 10,
    "random_state": 42,
    "test_size": 0.3,
    "classification_thresholds": {
        "very_low": 0.2,
        "low": 0.4,
        "moderate": 0.6,
        "high": 0.8,
        # > 0.8 = very_high
    },
    "feature_names": ["slope", "aspect", "curvature", "rainfall", "landcover"],
    "model_path": MODELS_DIR / "landslide_model.pkl",
}

# Flood mapping settings
FLOOD_CONFIG = {
    "sar_threshold": -18,  # dB, manual threshold for water detection
    "use_otsu": True,  # Use Otsu's method for automatic thresholding
    "dem_threshold": 100,  # meters, remove areas above this elevation
    "morphology_kernel_size": 3,  # pixels, for opening/closing operations
    "min_flood_area": 1000,  # square meters, minimum flood polygon area
}

# Exposure analysis settings
EXPOSURE_CONFIG = {
    "buffer_distance": 100,  # meters, buffer around buildings for exposure analysis
    "exposure_classes": {
        "very_low": 1,
        "low": 2,
        "moderate": 3,
        "high": 4,
        "very_high": 5,
    },
}

# Multi-hazard integration settings
MULTI_HAZARD_CONFIG = {
    "weights": {
        "landslide": 0.4,
        "flood": 0.4,
        "exposure": 0.2,
    },
    "normalization_method": "min_max",  # or "z_score"
    "classification_thresholds": {
        "very_low": 0.2,
        "low": 0.4,
        "moderate": 0.6,
        "high": 0.8,
    },
}

# Visualization colormaps
COLORMAPS = {
    "landslide": {
        "very_low": "#2ECC71",     # Green
        "low": "#F1C40F",          # Yellow
        "moderate": "#E67E22",     # Orange
        "high": "#E74C3C",         # Red
        "very_high": "#8E44AD",    # Purple
    },
    "flood": {
        "no_flood": "#F7F7F7",     # Light gray
        "flood": "#3498DB",        # Blue
    },
    "exposure": {
        "very_low": "#ECEFF1",
        "low": "#90CAF9",
        "moderate": "#42A5F5",
        "high": "#1E88E5",
        "very_high": "#0D47A1",
    },
    "multi_hazard": {
        "very_low": "#2ECC71",
        "low": "#F1C40F",
        "moderate": "#E67E22",
        "high": "#E74C3C",
        "very_high": "#8E44AD",
    },
}

# API settings
API_CONFIG = {
    "cors_origins": ["*"],  # Allow all origins for development
    "max_request_size": 100 * 1024 * 1024,  # 100 MB
}

# Logging
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
}
