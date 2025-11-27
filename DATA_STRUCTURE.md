# Data Directory Structure Explained

## 📁 Directory Overview

```
data/
├── raw/          ← INPUT: Your original satellite/GIS data
├── processed/    ← INTERMEDIATE: Temporary files during processing
└── outputs/      ← FINAL: Results shown to users
```

---

## 📂 1. `data/raw/` - Input Data

**Purpose:** Store your original, unmodified data files

**Contents:**
```
raw/
├── dem.tif                      (978 KB) - Digital Elevation Model
├── landcover.tif                (245 KB) - Land use classification
├── rainfall.tif                 (978 KB) - Precipitation data
├── sentinel1_sar.tif            (978 KB) - SAR backscatter (dB)
├── buildings.geojson            (63 KB)  - Building footprints
└── landslide_inventory.geojson  (8.7 KB) - Historical landslides
```

**File Types:**
- **Rasters**: GeoTIFF format (`.tif`)
- **Vectors**: GeoJSON format (`.geojson`)

**What happens to these?**
- ✅ Never modified or deleted
- ✅ Read by processing pipelines
- ❌ NOT sent to frontend
- ❌ NOT visible on map

---

## 📂 2. `data/processed/` - Intermediate Files

**Purpose:** Store temporary/intermediate results during processing

**Contents:**
```
processed/
├── slope.tif                    (1.1 MB) - Slope calculated from DEM
├── aspect.tif                   (1.1 MB) - Aspect (orientation) from DEM
├── curvature.tif                (1.2 MB) - Terrain curvature
├── landslide_features_stack.tif (4.4 MB) - All features combined (5 bands)
└── buildings_raster.tif         (3.7 KB) - Buildings converted to raster
```

**File Types:**
- **All GeoTIFF rasters** (`.tif`)
- Some multi-band (landslide_features_stack has 5 bands)

**What happens to these?**
- ✅ Generated during processing
- ✅ Used by later processing steps
- ✅ Can be deleted safely (will regenerate)
- ❌ NOT sent to frontend
- ❌ NOT visible on map

**Example Flow:**
```
DEM (raw) 
  → slope.tif (processed)
  → aspect.tif (processed)
  → curvature.tif (processed)
  → landslide_features_stack.tif (processed)
  → ML model uses this
  → Final output (outputs/)
```

---

## 📂 3. `data/outputs/` - Final Results

**Purpose:** Store finished analysis results that users will see

**Contents:**
```
outputs/
├── RASTER FILES (GeoTIFF):
│   ├── landslide_susceptibility_probability.tif  (549 KB)  - Float32, continuous 0-1
│   ├── landslide_susceptibility_classified.tif   (70 KB)   - UInt8, classes 1-5
│   ├── flood_extent.tif                          (2.1 KB)  - UInt8, binary 0/1
│   ├── exposure_density.tif                      (446 KB)  - Float32, continuous
│   ├── exposure_classified.tif                   (30 KB)   - UInt8, classes 1-5
│   ├── multi_hazard_risk.tif                     (456 KB)  - Float32, continuous
│   └── multi_hazard_risk_classified.tif          (43 KB)   - UInt8, classes 1-5
│
└── VECTOR FILES (GeoJSON):
    ├── landslide_susceptibility_zones.geojson    (25 MB)   - 40,896 polygons
    ├── flood_extent.geojson                      (45 B)    - 0 polygons (no flood)
    ├── exposure_zones.geojson                    (8.6 MB)  - 22,676 polygons
    └── multi_hazard_risk.geojson                 (14 MB)   - 40,896 polygons
```

**File Types - TWO versions of each result:**

### A) **GeoTIFF Rasters** (`.tif`)
- **Format**: TIFF image with geospatial metadata
- **Compression**: LZW (lossless)
- **Data types**: 
  - `Float32` (32-bit decimal) for continuous values (probabilities, densities)
  - `UInt8` (8-bit integer) for classifications (1-5)
- **Use cases**:
  - Analysis in GIS software (QGIS, ArcGIS)
  - Further processing/calculations
  - Downloading for offline work
  - Creating custom visualizations

### B) **GeoJSON Vectors** (`.geojson`)
- **Format**: JSON with geometry + properties
- **Structure**:
  ```json
  {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [...]},
        "properties": {
          "value": 3,
          "class": "moderate"
        }
      }
    ]
  }
  ```
- **Use cases**:
  - ✅ **Displayed on web map** (Leaflet)
  - Web APIs, sharing
  - Interactive features with popups

---

## 🗺️ What Does the Frontend Visualize?

### **Answer: VECTORS ONLY (GeoJSON)**

The Leaflet frontend **displays GeoJSON files**, NOT rasters.

**Why?**
1. **Performance**: Rasters are huge (500x500 = 250,000 pixels), vectors are polygons
2. **Interactivity**: Can click on polygons, show popups with data
3. **Styling**: Can color-code by class (Very Low = green, High = red)
4. **File size**: GeoJSON is more compact for web transmission

**Visualization Flow:**
```
Processing creates:
  ├── landslide_susceptibility_classified.tif (70 KB raster)
  └── landslide_susceptibility_zones.geojson (25 MB vector)
           ↓
   Frontend loads GeoJSON via API
           ↓
   Leaflet renders colored polygons on map
           ↓
   User clicks → popup shows class & value
```

**How conversion happens:**
```python
# In raster_to_geojson() function:
1. Read classified raster (values 1-5)
2. Convert each contiguous area of same value → polygon
3. Add properties: {"value": 3, "class": "moderate"}
4. Save as GeoJSON FeatureCollection
```

---

## 📊 File Format Details

### GeoTIFF Specifications

Each `.tif` file contains:
- **Georeference**: Coordinates, CRS (EPSG:4326 = lat/lon)
- **Pixel values**: The actual data
- **Metadata**: NoData value, data type, compression
- **Tiled**: 256x256 pixel tiles for efficiency

Example (landslide probability):
```
Size: 500 x 500 pixels
Data type: Float64 (64-bit decimal)
Values: 0.0 to 1.0 (probability)
CRS: EPSG:4326
Compression: LZW
```

### GeoJSON Specifications

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [83.9234, 28.2156],
            [83.9235, 28.2156],
            [83.9235, 28.2157],
            [83.9234, 28.2157],
            [83.9234, 28.2156]
          ]
        ]
      },
      "properties": {
        "value": 3,           ← Integer class (1-5)
        "class": "moderate"   ← Human-readable name
      }
    },
    { /* next polygon... */ }
  ]
}
```

---

## 🎨 Frontend Rendering

### What Leaflet Does:

```javascript
// 1. Fetch GeoJSON from API
fetch('/api/layers/landslide_susceptibility_zones')
  .then(response => response.json())
  .then(geojson => {
    
    // 2. Create Leaflet GeoJSON layer
    L.geoJSON(geojson, {
      
      // 3. Style each feature by class
      style: (feature) => {
        const className = feature.properties.class;
        const color = COLORS[className]; // e.g., "moderate" → "#E67E22"
        return {
          fillColor: color,
          fillOpacity: 0.6,
          color: color,
          weight: 2
        };
      },
      
      // 4. Add popup on click
      onEachFeature: (feature, layer) => {
        layer.bindPopup(`
          <h3>Landslide Susceptibility</h3>
          <strong>Class:</strong> ${feature.properties.class}<br>
          <strong>Value:</strong> ${feature.properties.value}
        `);
      }
    }).addTo(map);
  });
```

**Result:** Color-coded polygons you can click!

---

## 🔄 Complete Data Flow

```
┌─────────────────┐
│  data/raw/      │  ← You provide
│  - dem.tif      │
│  - sar.tif      │
└────────┬────────┘
         │
         ↓ [Processing Pipeline]
         │
┌────────┴────────┐
│  data/processed/│  ← Temporary
│  - slope.tif    │
│  - aspect.tif   │
└────────┬────────┘
         │
         ↓ [Further Processing]
         │
┌────────┴────────────────────────┐
│  data/outputs/                  │  ← Final results
│  ├── *.tif (rasters)           │  → For GIS software
│  └── *.geojson (vectors)       │  → For web map
└────────┬────────────────────────┘
         │
         ↓ [API serves GeoJSON]
         │
┌────────┴────────┐
│  Frontend       │
│  Leaflet Map    │  ← User sees colored polygons
└─────────────────┘
```

---

## 💡 Key Takeaways

| Folder | Contains | Used By | Visible on Map? |
|--------|----------|---------|-----------------|
| `raw/` | Original data | Processing pipelines | ❌ No |
| `processed/` | Intermediate files | Later processing steps | ❌ No |
| `outputs/` (*.tif) | Final rasters | GIS software, downloads | ❌ No |
| `outputs/` (*.geojson) | Final vectors | **Frontend map** | ✅ **YES** |

**Frontend displays:** **ONLY GeoJSON vectors** from `data/outputs/*.geojson`

**Rasters are:**
- Created for analysis/downloads
- Converted to vectors for web display
- NOT directly rendered in browser (too slow/large)

---

## 🎯 Example: Landslide Output

**Created by pipeline:**
1. `landslide_susceptibility_probability.tif` (549 KB)
   - Raster with continuous values 0.0-1.0
   - For GIS analysis

2. `landslide_susceptibility_classified.tif` (70 KB)  
   - Raster with classes 1-5
   - Source for GeoJSON conversion

3. `landslide_susceptibility_zones.geojson` (25 MB)
   - 40,896 polygon features
   - **This is what appears on the map!**
   - Color-coded: green→yellow→orange→red→purple

When you check the "Landslide Susceptibility" box in the sidebar, the frontend loads the **GeoJSON** file and renders it as colored polygons.
