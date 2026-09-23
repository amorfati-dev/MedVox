"""Behandler nachträglich zuordnen: ein Diktat ohne Behandler bekommt im Büro seinen Behandler.

Diktate ohne Behandler (Pilotdaten, Start ohne Behandlerliste) stehen im Büro als „Behandler fehlt“.
Zugeordnet wird nur, solange das Diktat keinen hat – einmal gesetzt, bleibt der Behandler eines
Diktats für immer (`medvox/patients.py`). Der Patient bekommt ihn als Eröffner, falls er noch keinen hat.
"""

from __future__ import annotations

import time
from pathlib import Path

from medvox import db, dentists, patients


class AlreadyAttributed(Exception):
    """Das Diktat hat schon einen Behandler; der bleibt."""


def assign_dentist(
    db_path: Path, dictation_id: str, dentist_id: int, now: float | None = None
) -> patients.Dictation | None:
    """Setzt den Behandler eines Diktats ohne Behandler; None, wenn Diktat oder Behandler fehlen."""
    now = time.time() if now is None else now
    with db.connect(db_path) as conn:
        db.purge_expired(conn, now)
        row = conn.execute("SELECT patient_id, dentist_id FROM dictations WHERE id = ?", (dictation_id,)).fetchone()
        if row is None or dentists.known(conn, dentist_id) is None:
            return None
        if row["dentist_id"] is not None:
            raise AlreadyAttributed(dictation_id)
        conn.execute("UPDATE dictations SET dentist_id = ? WHERE id = ?", (dentist_id, dictation_id))
        if row["patient_id"] is not None:
            conn.execute(
                "UPDATE patients SET dentist_id = coalesce(dentist_id, ?) WHERE id = ?", (dentist_id, row["patient_id"])
            )
        return patients._get_dictation(conn, dictation_id)
