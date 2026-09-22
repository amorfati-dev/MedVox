"""SQLite-Zugriff (stdlib sqlite3) für Sitzungen und Transfer-Codes.

Die Datenbank enthält nie Audio und keine Patienten-Stammdaten; Transkripte
liegen nur als Transfer-Eintrag bis zum Ablauf der TTL darin. `secure_delete`
sorgt dafür, dass SQLite gelöschte Zeilen in der Datei überschreibt statt sie
in freien Seiten liegen zu lassen (WP-11).
"""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    token       TEXT PRIMARY KEY,
    created_at  REAL NOT NULL,
    expires_at  REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS transfers (
    code        TEXT PRIMARY KEY,
    transcript  TEXT NOT NULL,
    codes_json  TEXT NOT NULL,
    created_at  REAL NOT NULL,
    expires_at  REAL NOT NULL
);
"""


def init_db(path: Path) -> None:
    """Legt Verzeichnis und Tabellen an (idempotent)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as conn:
        conn.executescript(SCHEMA)


@contextmanager
def connect(path: Path) -> Iterator[sqlite3.Connection]:
    """Kurzlebige Verbindung je Aufruf; Commit bei Erfolg, Rollback bei Fehler."""
    conn = sqlite3.connect(path, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA secure_delete = ON")
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def purge_expired(conn: sqlite3.Connection, now: float | None = None) -> None:
    """Entfernt abgelaufene Sitzungen und Transfer-Einträge (WP-11)."""
    now = time.time() if now is None else now
    conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
    conn.execute("DELETE FROM transfers WHERE expires_at <= ?", (now,))


def purge_expired_at(path: Path) -> None:
    """Eigenständiger Aufräumlauf (Start und periodischer Sweep in `main.py`)."""
    with connect(path) as conn:
        purge_expired(conn)
