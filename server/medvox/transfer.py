"""Kurzcode-Transfer: Transkript + Ziffern für den Rezeptions-PC (WP-10).

Sechsstellige Codes aus einem verwechslungsfreien Alphabet (ohne 0/O/1/I),
TTL 15 Minuten, innerhalb der TTL mehrfach abrufbar. Abgelaufene Einträge
werden bei jedem Schreiben und Lesen entfernt; zusätzlich räumt `main.py`
beim Start und periodisch auf (WP-11).
"""

from __future__ import annotations

import json
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from medvox import db

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6


def new_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class Transfer:
    code: str
    transcript: str
    codes: list[str]
    created_at: float
    expires_at: float


def create_transfer(db_path: Path, transcript: str, codes: list[str], ttl_s: int) -> Transfer:
    """Speichert einen Eintrag unter einem neuen, noch unbenutzten Code."""
    now = time.time()
    with db.connect(db_path) as conn:
        db.purge_expired(conn, now)
        while True:
            code = new_code()
            exists = conn.execute("SELECT 1 FROM transfers WHERE code = ?", (code,)).fetchone()
            if exists is None:
                break
        conn.execute(
            "INSERT INTO transfers (code, transcript, codes_json, created_at, expires_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (code, transcript, json.dumps(codes), now, now + ttl_s),
        )
    return Transfer(code, transcript, list(codes), now, now + ttl_s)


def get_transfer(db_path: Path, code: str) -> Transfer | None:
    """Liefert den Eintrag, solange er nicht abgelaufen ist; sonst None."""
    now = time.time()
    with db.connect(db_path) as conn:
        db.purge_expired(conn, now)
        row = conn.execute(
            "SELECT * FROM transfers WHERE code = ?", (code.strip().upper(),)
        ).fetchone()
    if row is None:
        return None
    return Transfer(
        row["code"],
        row["transcript"],
        json.loads(row["codes_json"]),
        row["created_at"],
        row["expires_at"],
    )
