"""SQLite-Zugriff (stdlib sqlite3) für Sitzungen, Transfer-Codes und Diktate je Patient.

Die Datenbank enthält nie Audio und keine Patienten-Stammdaten; ein Patient ist nur die
Evident-Patientennummer. Transkripte liegen als Transfer-Eintrag bis zum Ablauf der TTL darin
und als Diktat eines Patienten, bis es als übertragen markiert ist – höchstens 24 Stunden
(`medvox/patients.py`). `secure_delete` sorgt dafür, dass SQLite gelöschte Zeilen in der Datei
überschreibt statt sie in freien Seiten liegen zu lassen (WP-11).
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
    expires_at  REAL NOT NULL,
    patient_type    TEXT,
    positions_json  TEXT NOT NULL DEFAULT '[]'
);
-- Patient = nur die Evident-Nummer. Die Zeile bleibt nach „übertragen“ ohne Inhalt stehen,
-- damit die Liste den Zustand zeigt; sie läuft ab, wenn ihr jüngstes Diktat abliefe.
-- AUTOINCREMENT: eine gelöschte ID wird nie an einen anderen Patienten vergeben.
CREATE TABLE IF NOT EXISTS patients (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    number              TEXT NOT NULL UNIQUE,
    created_at          REAL NOT NULL,
    updated_at          REAL NOT NULL,
    expires_at          REAL NOT NULL,
    transferred_at      REAL,
    transferred_count   INTEGER NOT NULL DEFAULT 0
);
-- Ein Diktat (Transkript, Vorschläge, Auswahl); ID vom iPad, patient_id NULL = „ohne Patient“.
CREATE TABLE IF NOT EXISTS dictations (
    id          TEXT PRIMARY KEY,
    patient_id  INTEGER,
    revision    INTEGER NOT NULL DEFAULT 1,
    created_at  REAL NOT NULL,
    updated_at  REAL NOT NULL,
    expires_at  REAL NOT NULL,
    data_json   TEXT NOT NULL
);
"""

# Spalten, die nach der ersten Installation dazukamen: (Name, Definition). Bestehende Datenbanken
# bekommen sie beim Start per ALTER TABLE; alte Einträge gelten als ohne Angabe.
ADDED_TRANSFER_COLUMNS = [
    ("patient_type", "TEXT"),
    ("positions_json", "TEXT NOT NULL DEFAULT '[]'"),
]


def init_db(path: Path) -> None:
    """Legt Verzeichnis und Tabellen an (idempotent)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as conn:
        conn.executescript(SCHEMA)
        present = {row["name"] for row in conn.execute("PRAGMA table_info(transfers)")}
        for name, definition in ADDED_TRANSFER_COLUMNS:
            if name not in present:
                conn.execute(f"ALTER TABLE transfers ADD COLUMN {name} {definition}")


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
    """Entfernt abgelaufene Sitzungen, Transfer-Einträge, Diktate und Patienten (WP-11)."""
    now = time.time() if now is None else now
    conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
    conn.execute("DELETE FROM transfers WHERE expires_at <= ?", (now,))
    conn.execute("DELETE FROM dictations WHERE expires_at <= ?", (now,))
    conn.execute("DELETE FROM patients WHERE expires_at <= ?", (now,))
    # Diktate eines gelöschten Patienten nie verwaist stehen lassen.
    conn.execute("DELETE FROM dictations WHERE patient_id IS NOT NULL AND patient_id NOT IN (SELECT id FROM patients)")


def purge_expired_at(path: Path) -> None:
    """Eigenständiger Aufräumlauf (Start und periodischer Sweep in `main.py`)."""
    with connect(path) as conn:
        purge_expired(conn)
