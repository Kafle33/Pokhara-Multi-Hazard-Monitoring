# Processing Workflow Guide

## Step-by-Step: From Real Data to Visualization

### Step 1: Add Your Real Data

Replace synthetic data with real satellite/GIS data:

```bash
cd /home/roshan/multi-hazard/data/raw/

# Add your files (examples):
# - dem.tif (from SRTM or ALOS PALSAR)
# - landcover.tif (from Sentinel-2 or ESA WorldCover)
# - rainfall.tif (from CHIRPS or local stations)
# - sentinel1_sar.tif (from Copernicus Sentinel-1, VV polarization, dB)
# - buildings.geojson (from OpenStreetMap)
# - landslide_inventory.geojson (from field surveys)
```

**Important:** Ensure all rasters:
- Are in **same CRS** (coordinate system)
- Cover **same geographic extent** (or processing will fail)
- Are in **correct format** (GeoTIFF for rasters, GeoJSON for vectors)

### Step 2: Start the Server (if not running)

```bash
cd /home/roshan/multi-hazard
./venv/bin/python backend/main.py
```

Server will start at: `http://localhost:8000`

### Step 3: Trigger Processing

**Option A: Use the All-in-One Script (Easiest)**

```bash
cd /home/roshan/multi-hazard
./venv/bin/python scripts/run_all_pipelines.py
```

This runs all 4 pipelines in sequence automatically.

---

**Option B: Use API Endpoints (Recommended)**

Open **http://localhost:8000/api/docs** in browser.

Then:

1. **POST /api/hazard/landslide**
   - Click "Try it out"
   - Set `train_model: true` (for first run)
   - Click "Execute"
   - Wait ~30-60 seconds
   - Check response for output paths

2. **POST /api/hazard/flood**
   - Click "Try it out"
   - Click "Execute"
   - Wait ~10-20 seconds

3. **POST /api/hazard/exposure**
   - Click "Try it out"
   - Set `hazard_raster` to landslide output path
   - Click "Execute"

4. **POST /api/hazard/multi_risk**
   - Click "Try it out"
   - Click "Execute"
   - This combines all previous outputs

---

**Option C: Use cURL (Command Line)**

```bash
# Landslide (with model training)
curl -X POST http://localhost:8000/api/hazard/landslide \
  -H "Content-Type: application/json" \
  -d '{"train_model": true}'

# Flood
curl -X POST http://localhost:8000/api/hazard/flood

# Exposure (using landslide output)
curl -X POST http://localhost:8000/api/hazard/exposure \
  -H "Content-Type: application/json" \
  -d '{"hazard_raster": "/home/roshan/multi-hazard/data/outputs/landslide_susceptibility_probability.tif"}'

# Multi-hazard
curl -X POST http://localhost:8000/api/hazard/multi_risk
```

---

**Option D: Python Script**

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. Landslide
print("Running landslide analysis...")
resp = requests.post(f"{BASE_URL}/api/hazard/landslide", 
                     json={"train_model": True})
print(resp.json())

# 2. Flood
print("Running flood mapping...")
resp = requests.post(f"{BASE_URL}/api/hazard/flood")
print(resp.json())

# 3. Multi-hazard
print("Running multi-hazard integration...")
resp = requests.post(f"{BASE_URL}/api/hazard/multi_risk")
print(resp.json())

print("Processing complete!")
```

### Step 4: View Results

**Check outputs:**
```bash
ls -lh /home/roshan/multi-hazard/data/outputs/
```

You should see:
- `*.tif` files (raster outputs)
- `*.geojson` files (vector outputs)

**View in browser:**
1. Open: `http://localhost:8000`
2. Check layer checkboxes in sidebar
3. Click on map features to see details

**View in QGIS/ArcGIS:**
- Open the GeoTIFF files directly
- Load GeoJSON for vector visualization

---

## ⚙️ Configuration Options

### Customize Processing Parameters

Edit `backend/config.py` before processing:

```python
# Landslide model settings
LANDSLIDE_CONFIG = {
    "model_type": "RandomForest",  # or "XGBoost"
    "n_estimators": 100,           # Number of trees
    "max_depth": 10,               # Tree depth
    "classification_thresholds": {
        "very_low": 0.2,
        "low": 0.4,
        "moderate": 0.6,
        "high": 0.8,
    }
}

# Flood settings
FLOOD_CONFIG = {
    "sar_threshold": -18,          # dB threshold for water
    "use_otsu": True,              # Automatic thresholding
    "dem_threshold": 100,          # Mask above 100m elevation
}

# Multi-hazard weights
MULTI_HAZARD_CONFIG = {
    "weights": {
        "landslide": 0.4,          # 40% weight
        "flood": 0.4,              # 40% weight
        "exposure": 0.2,           # 20% weight
    }
}
```

After editing config, **restart the server**.

---

## 🔄 Re-processing

To re-process with new data or different parameters:

1. **Clear old outputs** (optional):
   ```bash
   rm -rf data/outputs/*
   ```

2. **Update data/config** as needed

3. **Re-run pipelines** using any method above

The system will **overwrite** previous outputs.

---

## ❗ Troubleshooting

### Pipeline fails with "File not found"
- Check that all required files exist in `data/raw/`
- Verify file names match what's in `config.py`

### "Model not found" error
- Set `train_model: true` for first landslide run
- Or manually train: `python -c "from backend.processing.landslide.pipeline import run_landslide_pipeline; run_landslide_pipeline(train_new_model=True)"`

### Processing is slow
- Normal for large rasters (>1000x1000 pixels)
- Consider downsampling input data
- Run pipelines individually instead of all at once

### Map shows "No layers available"
- Make sure pipelines completed successfully
- Check `data/outputs/` for GeoJSON files
- Refresh browser page

---

## 📊 Expected Processing Time

With 500x500 pixel rasters:
- Landslide: ~30-60 seconds (includes ML training)
- Flood: ~10-20 seconds
- Exposure: ~15-30 seconds
- Multi-hazard: ~10-20 seconds

**Total: ~1-2 minutes**

Larger rasters will take longer (scales roughly with pixel count).

---

## 🎯 Quick Reference

| Task | Command |
|------|---------|
| **Run all pipelines** | `./venv/bin/python scripts/run_all_pipelines.py` |
| **API docs** | Open `http://localhost:8000/api/docs` |
| **View map** | Open `http://localhost:8000` |
| **Check outputs** | `ls data/outputs/` |
| **Clear outputs** | `rm -rf data/outputs/*` |
| **Restart server** | Ctrl+C, then `./venv/bin/python backend/main.py` |
