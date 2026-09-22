"""SQLite-Zugriff (stdlib sqlite3) für Sitzungen und Transfer-Codes.

Die Datenbank enthält nie Audio und keine Patienten-Stammdaten; Transkripte
liegen nur als Transfer-Eintrag bis zum Ablauf der TTL darin.
"""

from __future__ import annotations

import sqlite3
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
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA)


@contextmanager
def connect(path: Path) -> Iterator[sqlite3.Connection]:
    """Kurzlebige Verbindung je Aufruf; Commit bei Erfolg, Rollback bei Fehler."""
    conn = sqlite3.connect(path, timeout=5.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()
