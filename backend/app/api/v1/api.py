"""
Main API router for v1 endpoints
"""

from fastapi import APIRouter

# Import endpoint routers
from app.api.v1.endpoints import documentation

api_router = APIRouter()

# Include documentation endpoints
api_router.include_router(
    documentation.router, 
    prefix="/documentation", 
    tags=["documentation"]
)

# Future endpoint routers (to be implemented)
# from app.api.v1.endpoints import auth, patients, evident
# api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
# api_router.include_router(patients.router, prefix="/patients", tags=["patients"])
# api_router.include_router(evident.router, prefix="/evident", tags=["evident"])

# API root endpoint
@api_router.get("/")
async def api_root():
    """API root endpoint"""
    return {
        "message": "MedVox API v1", 
        "status": "active",
        "version": "1.0.0",
        "features": [
            "Audio processing",
            "Speech-to-text transcription", 
            "German dental terminology",
            "BEMA/GOZ billing code generation",
            "Structured documentation output"
        ],
        "endpoints": {
            "documentation": "/api/v1/documentation/",
            "process_audio": "/api/v1/documentation/process-audio",
            "process_text": "/api/v1/documentation/process-text",
            "supported_formats": "/api/v1/documentation/supported-formats",
            "docs": "/docs"
        }
    } 