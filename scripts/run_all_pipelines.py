"""
Run all hazard processing pipelines to generate outputs
"""

import sys
sys.path.append('..')

from backend.processing.landslide.pipeline import run_landslide_pipeline
from backend.processing.flood.pipeline import run_flood_pipeline
from backend.processing.exposure.pipeline import run_exposure_pipeline
from backend.processing.multi_hazard import run_multi_hazard_integration
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

print("="*70)
print(" POKHARA MULTI-HAZARD PROCESSING PIPELINE")
print("="*70)

# 1. Run Landslide Susceptibility Analysis
print("\n\n🏔️  STEP 1: LANDSLIDE SUSCEPTIBILITY ANALYSIS")
print("-"*70)
try:
    landslide_outputs = run_landslide_pipeline(train_new_model=True)
    print(f"\n✅ Landslide analysis complete!")
    print(f"   Outputs: {len(landslide_outputs)} files generated")
except Exception as e:
    print(f"\n❌ Landslide analysis failed: {e}")
    import traceback
    traceback.print_exc()

# 2. Run Flood Mapping
print("\n\n🌊 STEP 2: FLOOD MAPPING")
print("-"*70)
try:
    flood_outputs = run_flood_pipeline()
    print(f"\n✅ Flood mapping complete!")
    print(f"   Outputs: {len(flood_outputs)} files generated")
except Exception as e:
    print(f"\n❌ Flood mapping failed: {e}")
    import traceback
    traceback.print_exc()

# 3. Run Exposure Analysis (using landslide output)
print("\n\n🏘️  STEP 3: EXPOSURE ANALYSIS")
print("-"*70)
try:
    from pathlib import Path
    from backend.config import OUTPUTS_DIR
    
    hazard_raster = OUTPUTS_DIR / "landslide_susceptibility_probability.tif"
    exposure_outputs = run_exposure_pipeline(hazard_raster_path=hazard_raster)
    print(f"\n✅ Exposure analysis complete!")
    print(f"   Outputs: {len(exposure_outputs)} files generated")
except Exception as e:
    print(f"\n❌  Exposure analysis failed: {e}")
    import traceback
    traceback.print_exc()

# 4. Run Multi-Hazard Integration
print("\n\n⚠️  STEP 4: MULTI-HAZARD RISK INTEGRATION")
print("-"*70)
try:
    multi_hazard_outputs = run_multi_hazard_integration()
    print(f"\n✅ Multi-hazard integration complete!")
    print(f"   Outputs: {len(multi_hazard_outputs)} files generated")
except Exception as e:
    print(f"\n❌ Multi-hazard integration failed: {e}")
    import traceback
    traceback.print_exc()

print("\n\n" + "="*70)
print(" 🎉 ALL PIPELINES COMPLETE!")
print("="*70)
print("\nGenerated outputs in data/outputs/:")
print("  📊 Landslide susceptibility maps (GeoTIFF + GeoJSON)")
print("  📊 Flood extent maps (GeoTIFF + GeoJSON)")
print("  📊 Exposure analysis (GeoTIFF + GeoJSON)")
print("  📊 Multi-hazard risk map (GeoTIFF + GeoJSON)")
print("\n🌐 View results at: http://localhost:8000")
print("   Toggle layers in the sidebar to visualize hazards!")
