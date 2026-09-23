"""Behandlerliste der Gemeinschaftspraxis: wer ein Diktat aufgenommen hat (Zuordnung, keine Anmeldung).

Alle Behandler sehen alle Patienten; der Behandler eines Diktats dient nur der Zuordnung für
Abrechnung und Nachvollziehbarkeit. Das Praxis-Passwort bleibt die einzige Schranke, jede
angemeldete Person darf die Liste pflegen. Ein Behandler wird nie gelöscht, nur inaktiv gesetzt:
Er erscheint dann nicht mehr zur Auswahl am iPad, alte Diktate behalten ihn aber.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from medvox import db


@dataclass(frozen=True)
class Dentist:
    id: int
    name: str  # wie er angezeigt wird, z. B. „Dr. Hartmann“
    practitioner_id: str | None  # optional: Evident-/BEMA-Behandlernummer
    active: bool


def _dentist(row: sqlite3.Row) -> Dentist:
    return Dentist(row["id"], row["name"], row["practitioner_id"], bool(row["active"]))


def _get(conn: sqlite3.Connection, dentist_id: int) -> Dentist | None:
    row = conn.execute("SELECT * FROM dentists WHERE id = ?", (dentist_id,)).fetchone()
    return None if row is None else _dentist(row)


def known(conn: sqlite3.Connection, dentist_id: int | None) -> int | None:
    """Die ID, wenn es diesen Behandler gibt (auch inaktiv), sonst None – ein Diktat scheitert nie daran."""
    if dentist_id is None:
        return None
    return dentist_id if _get(conn, dentist_id) is not None else None


def names(db_path: Path) -> dict[int, str]:
    """Name je ID, auch der inaktiven (Anzeige alter Diktate)."""
    with db.connect(db_path) as conn:
        return {r["id"]: r["name"] for r in conn.execute("SELECT id, name FROM dentists")}


def list_dentists(db_path: Path) -> list[Dentist]:
    """Alle Behandler, aktive zuerst, sonst in der Reihenfolge des Anlegens."""
    with db.connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM dentists ORDER BY active DESC, id").fetchall()
    return [_dentist(r) for r in rows]


def create_dentist(db_path: Path, name: str, practitioner_id: str | None = None) -> Dentist:
    with db.connect(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO dentists (name, practitioner_id, created_at) VALUES (?, ?, ?)",
            (name, practitioner_id, time.time()),
        )
        created = _get(conn, int(cur.lastrowid))
    assert created is not None
    return created


def update_dentist(db_path: Path, dentist_id: int, changes: dict) -> Dentist | None:
    """Ändert Name, Behandlernummer und/oder aktiv; None, wenn es ihn nicht gibt."""
    allowed = {k: v for k, v in changes.items() if k in ("name", "practitioner_id", "active")}
    with db.connect(db_path) as conn:
        if _get(conn, dentist_id) is None:
            return None
        for column, value in allowed.items():
            conn.execute(f"UPDATE dentists SET {column} = ? WHERE id = ?", (value, dentist_id))
        return _get(conn, dentist_id)
