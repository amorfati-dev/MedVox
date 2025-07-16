"""
Main API router for v1 endpoints
"""

from fastapi import APIRouter

# Import endpoint routers (we'll create these next)
# from app.api.v1.endpoints import auth, recordings, transcriptions, patients, evident

api_router = APIRouter()

# Include all endpoint routers (commented out until we create them)
# api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
# api_router.include_router(patients.router, prefix="/patients", tags=["patients"])
# api_router.include_router(recordings.router, prefix="/recordings", tags=["recordings"])
# api_router.include_router(transcriptions.router, prefix="/transcriptions", tags=["transcriptions"])
# api_router.include_router(evident.router, prefix="/evident", tags=["evident"])

# Temporary placeholder endpoint
@api_router.get("/")
async def api_root():
    """API root endpoint"""
    return {"message": "MedVox API v1", "status": "active"} 