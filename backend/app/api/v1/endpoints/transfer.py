"""
Transfer API Endpoints

Handles QR-code based data transfer between devices
Enables seamless workflow: Treatment Room → Reception
"""

import structlog
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any

from app.schemas.transfer import (
    CreateTransferRequest,
    CreateTransferResponse,
    TransferSessionResponse,
    ErrorResponse
)
from app.services.transfer_service import (
    TransferService,
    get_transfer_service,
    SessionNotFoundError,
    SessionExpiredError
)
from app.api.dependencies import get_current_user
from app.models.user import User

logger = structlog.get_logger()

router = APIRouter()


@router.post(
    "/create",
    response_model=CreateTransferResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create transfer session",
    description="""
    Create a new transfer session with billing codes and transcription.

    Returns:
    - Session ID (UUID)
    - QR code as base64 data URL
    - Transfer URL
    - Expiration info

    The session expires after 5 minutes for DSGVO compliance.
    """
)
async def create_transfer_session(
    request: CreateTransferRequest,
    transfer_service: TransferService = Depends(get_transfer_service),
    current_user: User = Depends(get_current_user),
) -> CreateTransferResponse:
    """
    Create a new transfer session

    Workflow:
    1. Doctor records voice → generates codes
    2. System creates session with QR code
    3. QR code displayed on device
    4. Helper scans QR at reception
    5. Codes transferred to PVS
    """
    try:
        # Convert Pydantic models to dicts for service layer
        billing_codes = [code.model_dump() for code in request.billing_codes]

        # Create session
        session = transfer_service.create_session(
            billing_codes=billing_codes,
            transcription=request.transcription,
            patient_id=request.patient_id
        )

        # Generate QR code
        qr_code = transfer_service.generate_qr_code(session.id)
        transfer_url = transfer_service.get_transfer_url(session.id)

        # Calculate expiry info
        expires_in = int((session.expires_at - datetime.now()).total_seconds())

        logger.info(
            "Transfer session created via API",
            session_id=session.id,
            codes_count=len(billing_codes),
            patient_id=request.patient_id,
            expires_in_seconds=expires_in
        )

        return CreateTransferResponse(
            session_id=session.id,
            short_code=session.short_code,
            transfer_url=transfer_url,
            qr_code=qr_code,
            expires_at=session.expires_at,
            expires_in_seconds=max(0, expires_in)  # Ensure non-negative
        )

    except Exception as e:
        logger.error(
            "Failed to create transfer session",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create transfer session: {str(e)}"
        )


@router.get(
    "/{session_id}",
    response_model=TransferSessionResponse,
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Session not found or expired"
        }
    },
    summary="Retrieve transfer session",
    description="""
    Retrieve a transfer session by ID.

    **Security:**
    - One-time use: Session is deleted after retrieval
    - Auto-expires after 5 minutes

    **Use case:**
    Reception PC scans QR code → opens transfer page → retrieves session data
    """
)
async def get_transfer_session(
    session_id: str,
    transfer_service: TransferService = Depends(get_transfer_service)
) -> TransferSessionResponse:
    """
    Retrieve and consume a transfer session

    This endpoint is called when:
    1. Helper scans QR code at reception
    2. Transfer page loads
    3. Session data is retrieved and displayed
    4. Helper copies codes to PVS

    After retrieval, session is deleted (one-time use)
    """
    try:
        # Retrieve session (consumes it)
        session = transfer_service.get_session(session_id)

        logger.info(
            "Transfer session retrieved via API",
            session_id=session_id,
            codes_count=len(session.billing_codes)
        )

        return TransferSessionResponse(
            session_id=session.id,
            billing_codes=session.billing_codes,
            transcription=session.transcription,
            patient_id=session.patient_id,
            created_at=session.created_at
        )

    except SessionNotFoundError:
        logger.warning(
            "Session not found",
            session_id=session_id
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or already consumed"
        )

    except SessionExpiredError:
        logger.warning(
            "Session expired",
            session_id=session_id
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session has expired"
        )

    except Exception as e:
        logger.error(
            "Failed to retrieve transfer session",
            session_id=session_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve session: {str(e)}"
        )


@router.get(
    "/code/{short_code}",
    response_model=TransferSessionResponse,
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Code not found or expired"
        }
    },
    summary="Retrieve session by short code",
    description="""
    Retrieve a transfer session using a 6-character code.

    **Usage:**
    User enters code: AB1234 → retrieves session data

    **Security:**
    - One-time use: Session is deleted after retrieval
    - Auto-expires after 5 minutes
    - Case-insensitive (AB1234 = ab1234)
    """
)
async def get_session_by_code(
    short_code: str,
    transfer_service: TransferService = Depends(get_transfer_service)
) -> TransferSessionResponse:
    """
    Retrieve session by short code

    This is the main endpoint for the SHORT-CODE workflow:
    1. Doctor sees code on iPad (e.g., AB1234)
    2. Helper goes to PC
    3. Enters code: AB1234
    4. This endpoint retrieves the session
    5. Codes are displayed for PVS entry
    """
    try:
        # Retrieve session by code (consumes it)
        session = transfer_service.get_session_by_code(short_code)

        logger.info(
            "Session retrieved by code",
            short_code=short_code,
            session_id=session.id,
            codes_count=len(session.billing_codes)
        )

        return TransferSessionResponse(
            session_id=session.id,
            billing_codes=session.billing_codes,
            transcription=session.transcription,
            patient_id=session.patient_id,
            created_at=session.created_at
        )

    except (SessionNotFoundError, SessionExpiredError) as e:
        logger.warning(
            "Code lookup failed",
            short_code=short_code,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Code not found or expired: {short_code}"
        )

    except Exception as e:
        logger.error(
            "Failed to retrieve session by code",
            short_code=short_code,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve session: {str(e)}"
        )


@router.get(
    "/health",
    summary="Transfer service health check",
    description="Check if transfer service is operational"
)
async def health_check(
    transfer_service: TransferService = Depends(get_transfer_service)
) -> Dict[str, Any]:
    """
    Health check for transfer service

    Returns:
    - Service status
    - Active session count
    """
    try:
        active_sessions = transfer_service.get_active_session_count()

        return {
            "status": "healthy",
            "service": "transfer",
            "active_sessions": active_sessions,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(
            "Transfer service health check failed",
            error=str(e),
            exc_info=True
        )
        return {
            "status": "unhealthy",
            "service": "transfer",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
