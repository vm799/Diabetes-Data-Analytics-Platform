"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from .core.config import settings
from .api.endpoints import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting TrueTrend Diabetes Analytics Platform")
    
    yield
    
    # Shutdown
    logger.info("Shutting down TrueTrend platform")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Honest clinical diabetes insights platform providing pattern detection and dual-mode reporting",
    lifespan=lifespan
)

# Add security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.trutrend.health"]
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint with platform information."""
    return {
        "platform": settings.app_name,
        "version": settings.app_version,
        "description": "Honest clinical diabetes insights",
        "status": "operational",
        "features": [
            "CSV data ingestion (Dexcom, LibreView, Glooko, etc.)",
            "Clinical pattern detection",
            "Dual-mode reporting (clinical/patient)",
            "HIPAA/GDPR compliance framework",
            "Real-time analytics processing"
        ],
        "endpoints": {
            "upload": "/api/v1/upload-csv",
            "analytics": "/api/v1/analytics/{patient_id}",
            "reports": "/api/v1/report/{patient_id}/pdf",
            "simulate": "/api/v1/simulate-analytics/{patient_id}",
            "health": "/api/v1/health"
        },
        "demo_instructions": {
            "step_1": "Upload a CSV file using POST /api/v1/upload-csv",
            "step_2": "View analytics using GET /api/v1/analytics/{patient_id}",
            "step_3": "Try simulation mode: POST /api/v1/simulate-analytics/{patient_id}",
            "documentation": "Visit /docs for interactive API documentation"
        }
    }


@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 handler."""
    return HTTPException(
        status_code=404,
        detail="Endpoint not found. Visit / for available endpoints."
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info"
    )