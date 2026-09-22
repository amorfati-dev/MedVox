"""Login für den einen Behandler: PBKDF2-Passwort-Hash und Session-Cookies.

Hash erzeugen: `make set-password` (ruft `python -m medvox.auth` auf) und den
ausgegebenen Wert als `MEDVOX_PASSWORD_HASH` setzen. Sitzungen liegen in
SQLite, damit ein Neustart des Servers den Behandler nicht abmeldet.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from pathlib import Path

from fastapi import HTTPException, Request

from medvox import db

SESSION_COOKIE = "medvox_session"
PBKDF2_ITERATIONS = 600_000
_HASH_PREFIX = "pbkdf2_sha256"


def hash_password(password: str, iterations: int = PBKDF2_ITERATIONS) -> str:
    """Erzeugt `pbkdf2_sha256$<iter>$<salt>$<hash>` (Base64, ohne Padding)."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return "$".join(
        (
            _HASH_PREFIX,
            str(iterations),
            base64.b64encode(salt).decode("ascii").rstrip("="),
            base64.b64encode(digest).decode("ascii").rstrip("="),
        )
    )


def _b64decode(value: str) -> bytes:
    return base64.b64decode(value + "=" * (-len(value) % 4))


def verify_password(password: str, stored_hash: str) -> bool:
    """Prüft ein Passwort in konstanter Zeit gegen den gespeicherten Hash."""
    try:
        prefix, iterations, salt, digest = stored_hash.split("$")
        if prefix != _HASH_PREFIX:
            return False
        expected = _b64decode(digest)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), _b64decode(salt), int(iterations)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def create_session(db_path: Path, ttl_s: int) -> str:
    """Legt eine neue Sitzung an, räumt abgelaufene auf und liefert das Token."""
    token = secrets.token_urlsafe(32)
    now = time.time()
    with db.connect(db_path) as conn:
        db.purge_expired(conn, now)
        conn.execute(
            "INSERT INTO sessions (token, created_at, expires_at) VALUES (?, ?, ?)",
            (token, now, now + ttl_s),
        )
    return token


def session_valid(db_path: Path, token: str | None) -> bool:
    if not token:
        return False
    with db.connect(db_path) as conn:
        row = conn.execute(
            "SELECT 1 FROM sessions WHERE token = ? AND expires_at > ?",
            (token, time.time()),
        ).fetchone()
    return row is not None


def delete_session(db_path: Path, token: str | None) -> None:
    if not token:
        return
    with db.connect(db_path) as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))


def require_session(request: Request) -> None:
    """FastAPI-Dependency: 401, wenn kein gültiges Session-Cookie vorliegt."""
    settings = request.app.state.settings
    if not session_valid(settings.db_path, request.cookies.get(SESSION_COOKIE)):
        raise HTTPException(status_code=401, detail="Nicht angemeldet.")


def _main() -> None:
    """`python -m medvox.auth`: fragt ein Passwort ab und gibt den Hash aus."""
    import getpass
    import sys

    first = getpass.getpass("Neues MedVox-Passwort: ")
    if len(first) < 8:
        sys.exit("Das Passwort muss mindestens 8 Zeichen haben.")
    if first != getpass.getpass("Wiederholen: "):
        sys.exit("Die Eingaben stimmen nicht überein.")
    print("\nVor `make dev` in der Shell des Servers setzen:\n")
    print(f"export MEDVOX_PASSWORD_HASH='{hash_password(first)}'")


if __name__ == "__main__":
    _main()
