"""
Transfer Service - QR-Code based data transfer between devices
Enables seamless transfer of billing codes from treatment room to reception

Features:
- Session-based transfer (UUID)
- Auto-expiring sessions (DSGVO compliant)
- One-time use sessions (security)
- QR code generation
- In-memory storage (MVP)

Author: Claude + Martin
Date: 2026-02-12
"""

import uuid
import base64
import io
import qrcode
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from cachetools import TTLCache
import structlog

from app.utils.short_code import generate_short_code, decode_short_code

logger = structlog.get_logger()


# Custom Exceptions
class SessionNotFoundError(Exception):
    """Raised when session ID doesn't exist"""
    pass


class SessionExpiredError(Exception):
    """Raised when session has expired"""
    pass


@dataclass
class TransferSession:
    """
    Transfer session containing billing codes and transcription

    DSGVO: Sessions auto-expire after TTL
    Security: One-time use (consumed after retrieval)
    """
    id: str
    short_code: str  # 6-character code for easy typing
    billing_codes: List[Dict[str, Any]]
    transcription: str
    patient_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=lambda: datetime.now() + timedelta(seconds=300))


class TransferService:
    """
    Manages transfer sessions for QR-code based data transfer

    Simple, pragmatic implementation:
    - In-memory storage (TTLCache)
    - No database required for MVP
    - Automatic cleanup via TTL
    """

    def __init__(self, session_ttl_seconds: int = 300, base_url: str = "https://medvox.app"):
        """
        Initialize transfer service

        Args:
            session_ttl_seconds: Time-to-live for sessions (default: 5 minutes)
            base_url: Base URL for transfer links
        """
        self.session_ttl = session_ttl_seconds
        self.base_url = base_url

        # In-memory cache with automatic expiration
        # maxsize=1000: supports up to 1000 concurrent sessions
        self._sessions: TTLCache = TTLCache(
            maxsize=1000,
            ttl=session_ttl_seconds
        )

        # Short code → Session ID mapping
        self._code_to_id: TTLCache = TTLCache(
            maxsize=1000,
            ttl=session_ttl_seconds
        )

        logger.info(
            "Transfer service initialized",
            ttl_seconds=session_ttl_seconds,
            max_sessions=1000
        )

    def create_session(
        self,
        billing_codes: List[Dict[str, Any]],
        transcription: str,
        patient_id: Optional[str] = None
    ) -> TransferSession:
        """
        Create a new transfer session

        Args:
            billing_codes: List of billing codes (BEMA/GOZ)
            transcription: Voice transcription text
            patient_id: Optional patient identifier

        Returns:
            TransferSession with unique ID and short code
        """
        # Generate UUID
        session_id = str(uuid.uuid4())

        # Generate short code
        short_code = generate_short_code(session_id, formatted=False)

        # Create session
        session = TransferSession(
            id=session_id,
            short_code=short_code,
            billing_codes=billing_codes,
            transcription=transcription,
            patient_id=patient_id,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=self.session_ttl)
        )

        # Store in cache
        self._sessions[session_id] = session

        # Store code mapping
        self._code_to_id[short_code] = session_id

        logger.info(
            "Transfer session created",
            session_id=session_id,
            short_code=short_code,
            codes_count=len(billing_codes),
            patient_id=patient_id,
            expires_at=session.expires_at.isoformat()
        )

        return session

    def get_session(self, session_id: str) -> TransferSession:
        """
        Retrieve and consume a transfer session

        Security: One-time use - session is deleted after retrieval

        Args:
            session_id: UUID of the session

        Returns:
            TransferSession

        Raises:
            SessionNotFoundError: If session doesn't exist
            SessionExpiredError: If session has expired
        """
        # Check if session exists
        if session_id not in self._sessions:
            # Could be expired or never existed
            logger.warning("Session not found", session_id=session_id)
            raise SessionNotFoundError(f"Session {session_id} not found")

        # Get session
        session = self._sessions[session_id]

        # Check expiration (redundant with TTLCache, but explicit)
        if session.expires_at < datetime.now():
            logger.warning("Session expired", session_id=session_id)
            del self._sessions[session_id]
            # Also delete code mapping
            if session.short_code in self._code_to_id:
                del self._code_to_id[session.short_code]
            raise SessionExpiredError(f"Session {session_id} has expired")

        # Delete session (one-time use for security)
        del self._sessions[session_id]

        # Delete code mapping
        if session.short_code in self._code_to_id:
            del self._code_to_id[session.short_code]

        logger.info(
            "Session retrieved and consumed",
            session_id=session_id,
            short_code=session.short_code,
            codes_count=len(session.billing_codes)
        )

        return session

    def get_session_by_code(self, short_code: str) -> TransferSession:
        """
        Retrieve session by short code

        Args:
            short_code: 6-character code (e.g., "AB1234")

        Returns:
            TransferSession

        Raises:
            SessionNotFoundError: If session doesn't exist
            SessionExpiredError: If session has expired
        """
        # Normalize code
        try:
            normalized_code = decode_short_code(short_code)
        except Exception as e:
            logger.warning("Invalid short code format", short_code=short_code, error=str(e))
            raise SessionNotFoundError(f"Invalid code format: {short_code}")

        # Lookup session ID
        if normalized_code not in self._code_to_id:
            logger.warning("Short code not found", short_code=normalized_code)
            raise SessionNotFoundError(f"Code {normalized_code} not found or expired")

        session_id = self._code_to_id[normalized_code]

        # Get session (this will consume it)
        return self.get_session(session_id)

    def get_transfer_url(self, session_id: str) -> str:
        """
        Generate transfer URL for QR code

        Args:
            session_id: UUID of the session

        Returns:
            Full URL for transfer page
        """
        return f"{self.base_url}/transfer/{session_id}"

    def generate_qr_code(self, session_id: str, size: int = 300) -> str:
        """
        Generate QR code as base64 data URL

        Args:
            session_id: UUID of the session
            size: QR code size in pixels (default: 300x300)

        Returns:
            Base64 data URL (data:image/png;base64,...)
        """
        # Generate transfer URL
        transfer_url = self.get_transfer_url(session_id)

        # Create QR code
        qr = qrcode.QRCode(
            version=1,  # Auto-size
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(transfer_url)
        qr.make(fit=True)

        # Generate image
        img = qr.make_image(fill_color="black", back_color="white")

        # Resize to desired size
        img = img.resize((size, size))

        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode()

        # Return as data URL
        return f"data:image/png;base64,{img_base64}"

    def cleanup_expired_sessions(self) -> int:
        """
        Manually cleanup expired sessions

        Note: TTLCache handles this automatically, but this method
        allows explicit cleanup for testing/monitoring

        Returns:
            Number of sessions removed
        """
        now = datetime.now()
        expired_ids = [
            sid for sid, session in self._sessions.items()
            if session.expires_at < now
        ]

        for sid in expired_ids:
            del self._sessions[sid]

        if expired_ids:
            logger.info(
                "Expired sessions cleaned up",
                removed_count=len(expired_ids)
            )

        return len(expired_ids)

    def get_active_session_count(self) -> int:
        """
        Get count of active sessions (for monitoring)

        Returns:
            Number of active sessions
        """
        return len(self._sessions)


# Singleton instance
_transfer_service: Optional[TransferService] = None


def get_transfer_service() -> TransferService:
    """
    Dependency injection for FastAPI

    Returns:
        Singleton TransferService instance
    """
    global _transfer_service

    if _transfer_service is None:
        # Initialize with default settings
        # TODO: Load from app.core.config.settings
        _transfer_service = TransferService(
            session_ttl_seconds=300,  # 5 minutes
            base_url="http://localhost:3000"  # TODO: Production URL
        )

    return _transfer_service
