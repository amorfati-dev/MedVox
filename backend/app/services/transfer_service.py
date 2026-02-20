"""
Transfer Service - QR-Code based data transfer between devices
Enables seamless transfer of billing codes from treatment room to reception

Features:
- Session-based transfer (UUID)
- Auto-expiring sessions (DSGVO compliant)
- One-time use sessions (security)
- QR code generation
- SQLite persistence (sessions survive server restarts)

Author: Claude + Martin
Date: 2026-02-12
"""

import uuid
import base64
import io
import json
import sqlite3
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

    Storage: SQLite (persists across server restarts) + TTLCache (fast reads)
    """

    def __init__(
        self,
        session_ttl_seconds: int = 300,
        base_url: str = "http://localhost:3000",
        db_path: str = "./medvox.db"
    ):
        self.session_ttl = session_ttl_seconds
        self.base_url = base_url
        self.db_path = db_path

        # In-memory cache for fast reads
        self._sessions: TTLCache = TTLCache(maxsize=1000, ttl=session_ttl_seconds)
        self._code_to_id: TTLCache = TTLCache(maxsize=1000, ttl=session_ttl_seconds)

        # Initialize SQLite table and load existing sessions
        self._init_db()
        self._load_sessions_from_db()

        logger.info(
            "Transfer service initialized",
            ttl_seconds=session_ttl_seconds,
            max_sessions=1000,
            db_path=db_path
        )

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create transfer_sessions table if it doesn't exist."""
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transfer_sessions (
                    id          TEXT PRIMARY KEY,
                    short_code  TEXT UNIQUE NOT NULL,
                    billing_codes TEXT NOT NULL,
                    transcription TEXT NOT NULL,
                    patient_id  TEXT,
                    created_at  TEXT NOT NULL,
                    expires_at  TEXT NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ts_expires ON transfer_sessions (expires_at)"
            )

    def _load_sessions_from_db(self) -> None:
        """Load non-expired sessions from DB into cache on startup."""
        now = datetime.now().isoformat()
        with self._get_conn() as conn:
            # Delete expired rows first (DSGVO cleanup)
            conn.execute("DELETE FROM transfer_sessions WHERE expires_at <= ?", (now,))
            rows = conn.execute(
                "SELECT * FROM transfer_sessions WHERE expires_at > ?", (now,)
            ).fetchall()

        loaded = 0
        for row in rows:
            session = self._row_to_session(row)
            self._sessions[session.id] = session
            self._code_to_id[session.short_code] = session.id
            loaded += 1

        if loaded:
            logger.info("Sessions loaded from DB on startup", count=loaded)

    def _row_to_session(self, row: sqlite3.Row) -> TransferSession:
        return TransferSession(
            id=row["id"],
            short_code=row["short_code"],
            billing_codes=json.loads(row["billing_codes"]),
            transcription=row["transcription"],
            patient_id=row["patient_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            expires_at=datetime.fromisoformat(row["expires_at"]),
        )

    def _save_to_db(self, session: TransferSession) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO transfer_sessions
                   (id, short_code, billing_codes, transcription, patient_id, created_at, expires_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    session.id,
                    session.short_code,
                    json.dumps(session.billing_codes),
                    session.transcription,
                    session.patient_id,
                    session.created_at.isoformat(),
                    session.expires_at.isoformat(),
                ),
            )

    def _delete_from_db(self, session_id: str) -> None:
        with self._get_conn() as conn:
            conn.execute("DELETE FROM transfer_sessions WHERE id = ?", (session_id,))

    def create_session(
        self,
        billing_codes: List[Dict[str, Any]],
        transcription: str,
        patient_id: Optional[str] = None
    ) -> TransferSession:
        """
        Create a new transfer session (persisted to SQLite + cached in memory).
        """
        session_id = str(uuid.uuid4())
        short_code = generate_short_code(session_id, formatted=False)

        session = TransferSession(
            id=session_id,
            short_code=short_code,
            billing_codes=billing_codes,
            transcription=transcription,
            patient_id=patient_id,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=self.session_ttl),
        )

        # Persist to DB first, then cache
        self._save_to_db(session)
        self._sessions[session_id] = session
        self._code_to_id[short_code] = session_id

        logger.info(
            "Transfer session created",
            session_id=session_id,
            short_code=short_code,
            codes_count=len(billing_codes),
            patient_id=patient_id,
            expires_at=session.expires_at.isoformat(),
        )

        return session

    def get_session(self, session_id: str) -> TransferSession:
        """
        Retrieve and consume a transfer session (one-time use).
        Checks TTLCache first, falls back to SQLite.
        """
        # Try cache first
        session = self._sessions.get(session_id)

        # Fallback to DB (e.g. after server restart)
        if session is None:
            now = datetime.now().isoformat()
            with self._get_conn() as conn:
                row = conn.execute(
                    "SELECT * FROM transfer_sessions WHERE id = ? AND expires_at > ?",
                    (session_id, now),
                ).fetchone()
            if row is None:
                logger.warning("Session not found", session_id=session_id)
                raise SessionNotFoundError(f"Session {session_id} not found")
            session = self._row_to_session(row)

        # Check expiration
        if session.expires_at < datetime.now():
            self._delete_from_db(session_id)
            self._sessions.pop(session_id, None)
            self._code_to_id.pop(session.short_code, None)
            logger.warning("Session expired", session_id=session_id)
            raise SessionExpiredError(f"Session {session_id} has expired")

        # Consume: delete from DB and cache (one-time use)
        self._delete_from_db(session_id)
        self._sessions.pop(session_id, None)
        self._code_to_id.pop(session.short_code, None)

        logger.info(
            "Session retrieved and consumed",
            session_id=session_id,
            short_code=session.short_code,
            codes_count=len(session.billing_codes),
        )

        return session

    def get_session_by_code(self, short_code: str) -> TransferSession:
        """Retrieve session by short code."""
        try:
            normalized_code = decode_short_code(short_code)
        except Exception as e:
            logger.warning("Invalid short code format", short_code=short_code, error=str(e))
            raise SessionNotFoundError(f"Invalid code format: {short_code}")

        # Try cache mapping first
        session_id = self._code_to_id.get(normalized_code)

        # Fallback: query DB directly
        if session_id is None:
            now = datetime.now().isoformat()
            with self._get_conn() as conn:
                row = conn.execute(
                    "SELECT id FROM transfer_sessions WHERE short_code = ? AND expires_at > ?",
                    (normalized_code, now),
                ).fetchone()
            if row is None:
                logger.warning("Short code not found", short_code=normalized_code)
                raise SessionNotFoundError(f"Code {normalized_code} not found or expired")
            session_id = row["id"]

        return self.get_session(session_id)

    def get_transfer_url(self, session_id: str) -> str:
        return f"{self.base_url}/transfer/{session_id}"

    def generate_qr_code(self, session_id: str, size: int = 300) -> str:
        """Generate QR code as base64 data URL."""
        transfer_url = self.get_transfer_url(session_id)

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(transfer_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        img = img.resize((size, size))

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        img_base64 = base64.b64encode(buffer.getvalue()).decode()

        return f"data:image/png;base64,{img_base64}"

    def cleanup_expired_sessions(self) -> int:
        """Delete expired sessions from DB and return count removed."""
        now = datetime.now().isoformat()
        with self._get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM transfer_sessions WHERE expires_at <= ?", (now,)
            )
            removed = cursor.rowcount

        # Also evict from cache
        expired_ids = [
            sid for sid, s in list(self._sessions.items())
            if s.expires_at < datetime.now()
        ]
        for sid in expired_ids:
            session = self._sessions.pop(sid, None)
            if session:
                self._code_to_id.pop(session.short_code, None)

        total = removed + len(expired_ids)
        if total:
            logger.info("Expired sessions cleaned up", db_removed=removed, cache_evicted=len(expired_ids))

        return total

    def get_active_session_count(self) -> int:
        return len(self._sessions)


# Singleton instance
_transfer_service: Optional[TransferService] = None


def get_transfer_service() -> TransferService:
    """Dependency injection for FastAPI."""
    global _transfer_service

    if _transfer_service is None:
        from app.core.config import settings
        _transfer_service = TransferService(
            session_ttl_seconds=settings.TRANSFER_SESSION_TTL,
            base_url=settings.FRONTEND_URL,
            db_path=settings.DATABASE_URL.replace("sqlite:///", ""),
        )

    return _transfer_service
