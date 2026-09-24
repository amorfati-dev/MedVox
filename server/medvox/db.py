"""SQLite-Zugriff (stdlib sqlite3) für Sitzungen, Transfer-Codes, Diktate je Patient und Behandler.

Die Datenbank enthält nie Audio und keine Patienten-Stammdaten; ein Patient ist nur die
Evident-Patientennummer, auf Wunsch mit Kürzel (Initialen, `patients.label`), das nur so lange bleibt,
wie der Patient offene Diktate hat. Transkripte liegen als Transfer-Eintrag bis zum Ablauf der TTL darin
und als Diktat eines Patienten, bis es als übertragen markiert ist – höchstens 24 Stunden
(`medvox/patients.py`); danach bleibt nur ein Grabstein (ID und Zeitpunkt) für sieben Tage,
damit ein iPad es nicht neu anlegt. Am iPad korrigierte Diktate hinterlassen beim Übertragen oder Ablauf
nur ihre geänderten Stellen ohne Bezug zum Patienten, höchstens 12 Monate (`medvox/corrections.py`).
`secure_delete` sorgt dafür, dass SQLite gelöschte Zeilen in der Datei
überschreibt statt sie in freien Seiten liegen zu lassen (WP-11).
"""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from medvox import corrections

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
    positions_json  TEXT NOT NULL DEFAULT '[]',
    dictation_id    TEXT,
    dictation_revision  INTEGER,
    handed_over_at  REAL
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
    saved_revision  INTEGER NOT NULL DEFAULT 1,  -- Revision, die das letzte Speichern vom iPad lieferte
    created_at  REAL NOT NULL,
    updated_at  REAL NOT NULL,
    expires_at  REAL NOT NULL,
    data_json   TEXT NOT NULL
);
-- Grabstein eines übertragenen, gelöschten oder abgelaufenen Diktats: nur ID und Zeitpunkt, kein
-- Inhalt, keine Patientennummer. Solange er liegt, wird die ID nie wieder angelegt.
CREATE TABLE IF NOT EXISTS dictation_tombstones (
    id          TEXT PRIMARY KEY,
    closed_at   REAL NOT NULL
);
-- Behandler der Gemeinschaftspraxis (`medvox/dentists.py`): nur Zuordnung, keine Anmeldung und keine
-- Rechte. Wird nie gelöscht, nur inaktiv gesetzt, damit alte Diktate ihren Behandler behalten.
CREATE TABLE IF NOT EXISTS dentists (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    practitioner_id TEXT,  -- optional: Evident-/BEMA-Behandlernummer
    active          INTEGER NOT NULL DEFAULT 1,
    created_at      REAL NOT NULL
);
-- Abgeholter Kurzcode eines Diktats (`medvox/handovers.py`): nur Evident-Zeilen, kein Transkript.
-- Bleibt, solange das Diktat offen ist oder sein Grabstein liegt.
CREATE TABLE IF NOT EXISTS handovers (
    dictation_id    TEXT NOT NULL,
    code            TEXT NOT NULL,
    revision        INTEGER,
    fetched_at      REAL NOT NULL,
    codes_json      TEXT NOT NULL
);
-- Korrektur-Sammlung (`medvox/corrections.py`): nur geänderte Textstellen (höchstens 4 Wörter Umfeld) und
-- Ziffernänderungen; ohne Verknüpfung zu Patient, Diktat oder Behandler, ohne Datum. Höchstens 12 Monate.
CREATE TABLE IF NOT EXISTS corrections (
    id              INTEGER PRIMARY KEY,  -- zufällig (corrections.record), keine Reihenfolge
    week            TEXT NOT NULL,  -- Kalenderwoche „2026-W39“
    patient_type    TEXT,           -- kasse | privat
    kind            TEXT NOT NULL,  -- text | ziffer
    before          TEXT NOT NULL,
    after           TEXT NOT NULL,
    catalog_version TEXT NOT NULL
);
"""

TOMBSTONE_S = 7 * 24 * 3600  # länger als die 24 Stunden eines Diktats

# Spalten, die nach der ersten Installation dazukamen: Tabelle → [(Name, Definition)]. Bestehende
# Datenbanken bekommen sie beim Start per ALTER TABLE; alte Einträge gelten als ohne Angabe (NULL).
ADDED_COLUMNS = {
    "transfers": [
        ("patient_type", "TEXT"),
        ("positions_json", "TEXT NOT NULL DEFAULT '[]'"),
        ("dictation_id", "TEXT"),  # gespeichertes Diktat, das der Abruf des Kurzcodes schließt
        ("dictation_revision", "INTEGER"),  # genau dieser Stand wurde übergeben; None = noch nicht gespeichert
        ("handed_over_at", "REAL"),  # erster Abruf; weitere Abrufe schließen nichts mehr
        ("dentist_id", "INTEGER"),  # Behandler des Diktats, für die Anzeige an der Rezeption
    ],
    # Behandler beim Start der Aufnahme, danach unveränderlich; NULL = ohne Behandler (Pilotdaten)
    "dictations": [("dentist_id", "INTEGER")],
    # Behandler des ersten Diktats: wer den Patienten eröffnet hat; Kürzel (Initialen) zum Wiederfinden
    "patients": [("dentist_id", "INTEGER"), ("label", "TEXT")],
}

# Erster Eintrag der Behandlerliste bei leerer Liste: bei einer neuen Datenbank und beim ersten Start
# einer bestehenden nach dem Update (dann fragt jedes iPad mit diesem Eintrag); in der App umbenennen.
FIRST_DENTIST = "Behandler 1"


def init_db(path: Path) -> None:
    """Legt Verzeichnis und Tabellen an (idempotent)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as conn:
        conn.executescript(SCHEMA)
        for table, columns in ADDED_COLUMNS.items():
            present = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
            for name, definition in columns:
                if name not in present:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
        # Einmalig: Behandler werden nie gelöscht, eine leere Liste gibt es nur bei einer neuen Datenbank
        # oder beim ersten Start einer bestehenden nach dem Update.
        if conn.execute("SELECT count(*) FROM dentists").fetchone()[0] == 0:
            conn.execute("INSERT INTO dentists (name, created_at) VALUES (?, ?)", (FIRST_DENTIST, time.time()))


# Wird nach jedem Commit mit Änderungen aufgerufen (Pfad der Datenbank): Live-Aktualisierung des Büros
# (`medvox/events.py`). Nur das Signal „geändert“, nie Inhalte.
_listeners: list[Callable[[Path], None]] = []


def on_change(listener: Callable[[Path], None]) -> Callable[[], None]:
    """Meldet `listener` für Änderungen an; liefert die Abmeldung."""
    _listeners.append(listener)
    return lambda: _listeners.remove(listener)


@contextmanager
def connect(path: Path) -> Iterator[sqlite3.Connection]:
    """Kurzlebige Verbindung je Aufruf; Commit bei Erfolg, Rollback bei Fehler."""
    conn = sqlite3.connect(path, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA secure_delete = ON")
    try:
        yield conn
        conn.commit()
        changed = conn.total_changes > 0
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()
    if changed:
        for listener in list(_listeners):
            listener(path)


def bury(conn: sqlite3.Connection, where: str, params: tuple, now: float, collect: bool = False) -> int:
    """Löscht die Diktate, auf die `where` passt, und hinterlässt je einen Grabstein.

    `collect`: übertragen oder abgelaufen – ihre Korrekturen vorher sammeln (`corrections.py`); beim
    Verwerfen oder Löschen nicht.
    """
    if collect:
        corrections.record(conn, where, params, now)
    conn.execute(
        f"INSERT OR IGNORE INTO dictation_tombstones (id, closed_at) SELECT id, ? FROM dictations WHERE {where}",
        (now, *params),
    )
    return conn.execute(f"DELETE FROM dictations WHERE {where}", params).rowcount


def drop_labels(conn: sqlite3.Connection) -> None:
    """Kürzel lebt wie der Inhalt: übertragen und nichts mehr offen, bleibt nur die Nummer."""
    conn.execute(
        "UPDATE patients SET label = NULL WHERE label IS NOT NULL AND transferred_at IS NOT NULL"
        " AND id NOT IN (SELECT patient_id FROM dictations WHERE patient_id IS NOT NULL)"
    )


def purge_expired(conn: sqlite3.Connection, now: float | None = None) -> None:
    """Entfernt abgelaufene Sitzungen, Transfer-Einträge, Diktate, Patienten, Grabsteine und Abholungen (WP-11)."""
    now = time.time() if now is None else now
    conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
    conn.execute("DELETE FROM transfers WHERE expires_at <= ?", (now,))
    bury(conn, "expires_at <= ?", (now,), now, collect=True)
    conn.execute("DELETE FROM patients WHERE expires_at <= ?", (now,))
    # Diktate eines gelöschten Patienten nie verwaist stehen lassen.
    bury(conn, "patient_id IS NOT NULL AND patient_id NOT IN (SELECT id FROM patients)", (), now)
    drop_labels(conn)
    conn.execute("DELETE FROM dictation_tombstones WHERE closed_at <= ?", (now - TOMBSTONE_S,))
    conn.execute(
        "DELETE FROM handovers WHERE dictation_id NOT IN (SELECT id FROM dictations)"
        " AND dictation_id NOT IN (SELECT id FROM dictation_tombstones)"
    )
    corrections.purge(conn, now)


def purge_expired_at(path: Path) -> None:
    """Eigenständiger Aufräumlauf (Start und periodischer Sweep in `main.py`)."""
    with connect(path) as conn:
        purge_expired(conn)
