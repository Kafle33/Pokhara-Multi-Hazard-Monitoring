"""
Main FastAPI application for Pokhara Multi-Hazard Monitoring System
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import logging

# Import API routers
from api.hazard import router as hazard_router
from api.layers import router as layers_router
from api.preview import router as preview_router
from config import API_CONFIG, LOGGING_CONFIG

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG['level']),
    format=LOGGING_CONFIG['format']
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Pokhara Multi-Hazard Monitoring System",
    description="Geospatial API for landslide, flood, and exposure hazard analysis",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=API_CONFIG['cors_origins'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(hazard_router)
app.include_router(layers_router)
app.include_router(preview_router)

# Serve frontend static files
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
    logger.info(f"Serving frontend from {frontend_dir}")


@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("=" * 60)
    logger.info("Pokhara Multi-Hazard Monitoring System")
    logger.info("Starting FastAPI application...")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("Shutting down application...")


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Pokhara Multi-Hazard Monitoring System",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
