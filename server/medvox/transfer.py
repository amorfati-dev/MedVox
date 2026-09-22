"""Kurzcode-Transfer: Transkript + Ziffern für den Rezeptions-PC (WP-10).

Sechsstellige Codes aus einem verwechslungsfreien Alphabet (ohne 0/O/1/I),
TTL 15 Minuten, innerhalb der TTL mehrfach abrufbar. Abgelaufene Einträge
werden bei jedem Schreiben entfernt; Abrufe sind je IP auf 10/min begrenzt.
"""

from __future__ import annotations

import json
import secrets
import threading
import time
from collections import defaultdict, deque
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
        conn.execute("DELETE FROM transfers WHERE expires_at <= ?", (now,))
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
    with db.connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM transfers WHERE code = ? AND expires_at > ?",
            (code.strip().upper(), time.time()),
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


class RateLimiter:
    """Gleitendes Fenster je Schlüssel (hier: Client-IP), im Speicher."""

    def __init__(self, limit: int, window_s: float = 60.0) -> None:
        self.limit = limit
        self.window_s = window_s
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= now - self.window_s:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True
