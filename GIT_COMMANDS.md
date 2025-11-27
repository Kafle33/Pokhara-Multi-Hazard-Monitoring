# Git Commands for Pokhara Multi-Hazard System

Run these commands to push the project to the repository.

## 1. Initialize and Configure

```bash
# Initialize git (if not already done)
git init

# Add remote origin
git remote add origin git@github.com:Kafle33/Pokhara-Multi-Hazard-Monitoring.git
# If origin already exists but is wrong:
# git remote set-url origin git@github.com:Kafle33/Pokhara-Multi-Hazard-Monitoring.git

# Configure user (optional, if not set globally)
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

## 2. Commit Code by Component

### Core Backend & Configuration
```bash
git add backend/config.py backend/main.py backend/__init__.py requirements.txt .gitignore
git commit -m "feat(core): Initial setup of FastAPI backend and configuration"
```

### Utilities
```bash
git add backend/processing/utils/
git commit -m "feat(utils): Add raster and geojson processing utilities"
```

### Landslide Module
```bash
git add backend/processing/landslide/
git commit -m "feat(landslide): Add landslide susceptibility modeling pipeline"
```

### Flood Module
```bash
git add backend/processing/flood/
git commit -m "feat(flood): Add SAR-based flood mapping pipeline"
```

### Exposure Module
```bash
git add backend/processing/exposure/
git commit -m "feat(exposure): Add exposure analysis pipeline"
```

### Multi-Hazard Integration
```bash
git add backend/processing/multi_hazard.py
git commit -m "feat(multi-hazard): Add multi-hazard risk integration logic"
```

### API Endpoints
```bash
git add backend/api/
git commit -m "feat(api): Add REST endpoints for hazards, layers, and previews"
```

### Frontend Application
```bash
git add frontend/
git commit -m "feat(frontend): Add Leaflet web interface and styling"
```

### Documentation & Scripts
```bash
git add README.md DATA_STRUCTURE.md PROCESSING_GUIDE.md scripts/
git commit -m "docs: Add comprehensive documentation and helper scripts"
```

### Data Directory Structure (excluding large files)
```bash
git add data/raw/.gitkeep data/processed/.gitkeep data/outputs/.gitkeep
git commit -m "chore: Add data directory structure"
```

## 3. Push to Remote

```bash
git branch -M main
git push -u origin main
```
