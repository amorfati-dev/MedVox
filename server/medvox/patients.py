"""Diktate je Patient für die spätere Übertragung im Büro (Evident-Patientennummer, keine Namen).

Am Stuhl entstehen Diktate für mehrere Patienten hintereinander; im Büro werden sie später
nach Evident übertragen. Ein Patient ist nur die Evident-Nummer, ein Diktat trägt Transkript,
Vorschläge und die Auswahl vom iPad (`data`). Diktate ohne Nummer liegen als „ohne Patient“
bereit und werden später zugeordnet.

Aufbewahrung (Vorgabe des Behandlers): ein Diktat bleibt, bis es als übertragen markiert ist,
und wird spätestens 24 Stunden nach seiner Anlage gelöscht – was zuerst eintritt. „Übertragen“
löscht den Inhalt sofort; die Patientenzeile bleibt nur mit Nummer, Zeiten und Anzahl stehen,
damit die Liste den Zustand zeigt, und läuft mit ihrem jüngsten Diktat ab. Aufgeräumt wird wie
beim Kurzcode-Transfer bei jedem Schreiben und Lesen (`db.purge_expired`), beim Start und
periodisch (`main.py`). Ein übertragenes, gelöschtes oder abgelaufenes Diktat hinterlässt einen
Grabstein ohne Inhalt (`db.bury`); Speichern unter dieser ID wird abgelehnt (`DictationClosed`),
damit es nie wieder offen erscheint und nicht zweimal nach Evident geht.
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from medvox import db

RETENTION_S = 24 * 3600  # harte Grenze, nicht per Umgebung verlängerbar


class DictationClosed(Exception):
    """Das Diktat ist schon übertragen, gelöscht oder abgelaufen und darf nicht neu entstehen."""


@dataclass(frozen=True)
class Patient:
    id: int
    number: str
    created_at: float
    updated_at: float  # jüngstes Diktat (Sortierung der Liste)
    transferred_at: float | None
    transferred_count: int  # bereits übertragene (gelöschte) Diktate
    open_count: int  # noch nicht übertragene Diktate


@dataclass(frozen=True)
class Dictation:
    id: str
    patient_id: int | None  # None = ohne Patient
    number: str | None
    revision: int  # steigt mit jeder Änderung; „übertragen“ löscht nur die gesehene Fassung
    created_at: float
    updated_at: float
    data: dict


_PATIENT_SQL = (
    "SELECT p.*, (SELECT count(*) FROM dictations d WHERE d.patient_id = p.id) AS open_count FROM patients p"
)
_DICTATION_SQL = "SELECT d.*, p.number FROM dictations d LEFT JOIN patients p ON p.id = d.patient_id"


def _patient(row: sqlite3.Row) -> Patient:
    return Patient(
        row["id"], row["number"], row["created_at"], row["updated_at"],
        row["transferred_at"], row["transferred_count"], row["open_count"],
    )


def _dictation(row: sqlite3.Row) -> Dictation:
    return Dictation(
        row["id"], row["patient_id"], row["number"], row["revision"],
        row["created_at"], row["updated_at"], json.loads(row["data_json"]),
    )


def _patient_id(conn: sqlite3.Connection, number: str, now: float) -> int:
    """ID des Patienten mit dieser Nummer; legt ihn an, falls es ihn (noch) nicht gibt."""
    row = conn.execute("SELECT id FROM patients WHERE number = ?", (number,)).fetchone()
    if row is not None:
        return row["id"]
    cur = conn.execute(
        "INSERT INTO patients (number, created_at, updated_at, expires_at) VALUES (?, ?, ?, ?)",
        (number, now, now, now + RETENTION_S),
    )
    return int(cur.lastrowid)


def _touch(conn: sqlite3.Connection, patient_id: int, dictation_expires: float, now: float) -> None:
    """Patient lebt mindestens so lange wie sein jüngstes Diktat; `updated_at` sortiert die Liste."""
    conn.execute(
        "UPDATE patients SET updated_at = ?, expires_at = max(expires_at, ?) WHERE id = ?",
        (now, dictation_expires, patient_id),
    )


def _get_patient(conn: sqlite3.Connection, patient_id: int) -> Patient | None:
    row = conn.execute(f"{_PATIENT_SQL} WHERE p.id = ?", (patient_id,)).fetchone()
    return None if row is None else _patient(row)


def _get_dictation(conn: sqlite3.Connection, dictation_id: str) -> Dictation | None:
    row = conn.execute(f"{_DICTATION_SQL} WHERE d.id = ?", (dictation_id,)).fetchone()
    return None if row is None else _dictation(row)


def create_patient(db_path: Path, number: str, now: float | None = None) -> Patient:
    """Legt den Patienten an oder liefert den vorhandenen mit dieser Nummer."""
    now = time.time() if now is None else now
    with db.connect(db_path) as conn:
        db.purge_expired(conn, now)
        patient = _get_patient(conn, _patient_id(conn, number, now))
    assert patient is not None
    return patient


def list_patients(db_path: Path, now: float | None = None) -> tuple[list[Patient], list[Dictation]]:
    """Alle Patienten (jüngstes Diktat zuerst) und die Diktate ohne Patient (jüngstes zuerst)."""
    now = time.time() if now is None else now
    with db.connect(db_path) as conn:
        db.purge_expired(conn, now)
        patients = conn.execute(f"{_PATIENT_SQL} ORDER BY p.updated_at DESC, p.id DESC").fetchall()
        loose = conn.execute(
            f"{_DICTATION_SQL} WHERE d.patient_id IS NULL ORDER BY d.updated_at DESC"
        ).fetchall()
    return [_patient(r) for r in patients], [_dictation(r) for r in loose]


def get_patient(
    db_path: Path, patient_id: int, now: float | None = None
) -> tuple[Patient, list[Dictation]] | None:
    """Patient mit seinen offenen Diktaten in Diktatreihenfolge; None, wenn es ihn nicht (mehr) gibt."""
    now = time.time() if now is None else now
    with db.connect(db_path) as conn:
        db.purge_expired(conn, now)
        patient = _get_patient(conn, patient_id)
        if patient is None:
            return None
        rows = conn.execute(
            f"{_DICTATION_SQL} WHERE d.patient_id = ? ORDER BY d.created_at, d.id", (patient_id,)
        ).fetchall()
    return patient, [_dictation(r) for r in rows]


def save_dictation(
    db_path: Path, dictation_id: str, data: dict, number: str | None, now: float | None = None
) -> Dictation:
    """Legt das Diktat an oder ersetzt seinen Inhalt (iPad speichert nach jeder Änderung).

    `number` ordnet nur ein neues Diktat oder eines „ohne Patient“ zu (Patient angelegt, falls
    nötig); ein schon zugeordnetes bleibt bei seinem Patienten, auch wenn das Büro es umgehängt
    hat. Die 24 Stunden zählen ab der ersten Speicherung und verlängern sich durch Änderungen
    nicht. Hat die ID einen Grabstein, gibt es `DictationClosed`.
    """
    now = time.time() if now is None else now
    payload = json.dumps(data, ensure_ascii=False)
    with db.connect(db_path) as conn:
        db.purge_expired(conn, now)
        if conn.execute("SELECT 1 FROM dictation_tombstones WHERE id = ?", (dictation_id,)).fetchone():
            raise DictationClosed(dictation_id)
        row = conn.execute("SELECT patient_id, expires_at FROM dictations WHERE id = ?", (dictation_id,)).fetchone()
        patient_id = row["patient_id"] if row else None
        if patient_id is None and number:
            patient_id = _patient_id(conn, number, now)
        if row is None:
            expires = now + RETENTION_S
            conn.execute(
                "INSERT INTO dictations (id, patient_id, created_at, updated_at, expires_at, data_json)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (dictation_id, patient_id, now, now, expires, payload),
            )
        else:
            expires = row["expires_at"]
            conn.execute(
                "UPDATE dictations SET patient_id = ?, revision = revision + 1, updated_at = ?, data_json = ?"
                " WHERE id = ?",
                (patient_id, now, payload, dictation_id),
            )
        if patient_id is not None:
            _touch(conn, patient_id, expires, now)
        saved = _get_dictation(conn, dictation_id)
    assert saved is not None
    return saved


def assign_dictation(db_path: Path, dictation_id: str, patient_id: int, now: float | None = None) -> Dictation | None:
    """Hängt ein vorhandenes Diktat (z. B. „ohne Patient“) an diesen Patienten; None, wenn eins fehlt."""
    now = time.time() if now is None else now
    with db.connect(db_path) as conn:
        db.purge_expired(conn, now)
        row = conn.execute("SELECT expires_at FROM dictations WHERE id = ?", (dictation_id,)).fetchone()
        if row is None or _get_patient(conn, patient_id) is None:
            return None
        conn.execute(
            "UPDATE dictations SET patient_id = ?, revision = revision + 1, updated_at = ? WHERE id = ?",
            (patient_id, now, dictation_id),
        )
        _touch(conn, patient_id, row["expires_at"], now)
        return _get_dictation(conn, dictation_id)


def delete_dictation(db_path: Path, dictation_id: str, now: float | None = None) -> bool:
    now = time.time() if now is None else now
    with db.connect(db_path) as conn:
        db.purge_expired(conn, now)
        return db.bury(conn, "id = ?", (dictation_id,), now) > 0


def mark_transferred(
    db_path: Path, patient_id: int, seen: dict[str, int], now: float | None = None
) -> tuple[Patient, list[Dictation]] | None:
    """Löscht die übertragenen Diktate des Patienten sofort und vermerkt Zeit und Anzahl.

    `seen`: Diktat-ID → Revision, wie sie im Büro angezeigt wurde. Nur genau diese Fassungen
    gelten als übertragen; ein inzwischen neues oder geändertes Diktat bleibt offen.
    """
    now = time.time() if now is None else now
    with db.connect(db_path) as conn:
        db.purge_expired(conn, now)
        if _get_patient(conn, patient_id) is None:
            return None
        rows = conn.execute("SELECT id, revision FROM dictations WHERE patient_id = ?", (patient_id,)).fetchall()
        done = [r["id"] for r in rows if seen.get(r["id"]) == r["revision"]]
        for d in done:
            db.bury(conn, "id = ?", (d,), now)
        if done or not rows:
            conn.execute(
                "UPDATE patients SET transferred_at = ?, transferred_count = transferred_count + ? WHERE id = ?",
                (now, len(done), patient_id),
            )
    return get_patient(db_path, patient_id, now)


def delete_patient(db_path: Path, patient_id: int, now: float | None = None) -> bool:
    """Löscht den Patienten mit allen Diktaten."""
    now = time.time() if now is None else now
    with db.connect(db_path) as conn:
        db.purge_expired(conn, now)
        db.bury(conn, "patient_id = ?", (patient_id,), now)
        return conn.execute("DELETE FROM patients WHERE id = ?", (patient_id,)).rowcount > 0


def close_handed_over(conn: sqlite3.Connection, dictation_id: str, now: float) -> None:
    """Kurzcode abgerufen: das verknüpfte Diktat gilt als übertragen wie im Büro.

    Der Grabstein entsteht auch, wenn das iPad das Diktat noch gar nicht gespeichert hat – sein
    Speichern wird dann abgelehnt, statt das Diktat ein zweites Mal offen anzulegen.
    """
    row = conn.execute("SELECT patient_id FROM dictations WHERE id = ?", (dictation_id,)).fetchone()
    db.bury(conn, "id = ?", (dictation_id,), now)
    conn.execute("INSERT OR IGNORE INTO dictation_tombstones (id, closed_at) VALUES (?, ?)", (dictation_id, now))
    if row is not None and row["patient_id"] is not None:
        conn.execute(
            "UPDATE patients SET transferred_at = ?, transferred_count = transferred_count + 1 WHERE id = ?",
            (now, row["patient_id"]),
        )
