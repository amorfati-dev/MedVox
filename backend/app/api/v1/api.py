"""
Main API router for v1 endpoints
"""

from fastapi import APIRouter

# Import endpoint routers
from app.api.v1.endpoints import documentation, transfer, auth

api_router = APIRouter()

# Auth endpoints (public - login does not require a token)
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"]
)

# Documentation endpoints (protected - require JWT)
api_router.include_router(
    documentation.router,
    prefix="/documentation",
    tags=["documentation"]
)

# Transfer endpoints (create: protected, retrieve: public - secured by UUID + one-time use)
api_router.include_router(
    transfer.router,
    prefix="/transfer",
    tags=["transfer"]
)


@api_router.get("/")
async def api_root():
    """API root endpoint"""
    return {
        "message": "MedVox API v1",
        "status": "active",
        "version": "1.0.0",
        "endpoints": {
            "login": "/api/v1/auth/login",
            "me": "/api/v1/auth/me",
            "process_audio": "/api/v1/documentation/process-audio",
            "transfer_create": "/api/v1/transfer/create",
            "transfer_retrieve": "/api/v1/transfer/{session_id}",
            "docs": "/docs",
        },
    }
