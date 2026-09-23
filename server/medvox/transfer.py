"""Kurzcode-Transfer: Transkript + Ziffern für den Rezeptions-PC (WP-10).

Dazu, rein informativ für die Rezeption: der Patiententyp und je Position Zahn, Ziffer und Art
(bema, goz, zuzahlung, kassenanteil). Kopiert wird weiterhin nur `codes` (Evident-Zeilen).

Sechsstellige Codes aus einem verwechslungsfreien Alphabet (ohne 0/O/1/I),
TTL 15 Minuten, innerhalb der TTL mehrfach abrufbar. Nennt das iPad beim Anlegen die ID des
gespeicherten Diktats (`dictation_id`), schließt der erste Abruf dieses Diktat wie „übertragen“
im Büro (`handovers.hand_over`), genau in dem Stand, den der Code trägt (`dictation_revision`).
Ist das Diktat schon vorher übertragen worden, gibt der Code nichts mehr heraus und wird
gelöscht (`AlreadyTransferred`) – Kurzcode und Patientenliste sind nie zwei Wege zu demselben
Diktat. Der Code nennt den Behandler des Diktats (beim Anlegen festgehalten, auch nach dem
Schließen des Diktats sichtbar). Abgelaufene Einträge werden bei jedem Schreiben und Lesen entfernt; zusätzlich räumt `main.py`
beim Start und periodisch auf (WP-11).
"""

from __future__ import annotations

import json
import secrets
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from medvox import db, dentists, handovers

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6


def new_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=UTC).isoformat(timespec="seconds")


class AlreadyTransferred(Exception):
    """Das verknüpfte Diktat war beim ersten Abruf schon übertragen, gelöscht oder abgelaufen."""

    def __init__(self, closed_at: float) -> None:
        super().__init__(closed_at)
        self.closed_at = closed_at


@dataclass(frozen=True)
class Transfer:
    code: str
    transcript: str
    codes: list[str]
    created_at: float
    expires_at: float
    patient_type: str | None = None  # kasse | privat; None bei älteren iPad-Versionen
    positions: list[dict] = field(default_factory=list)  # {"tooth", "code", "kind"}
    earlier: list[dict] = field(default_factory=list)  # frühere Abholungen desselben Diktats (handovers.py)
    dentist_name: str | None = None  # Behandler des Diktats; None bei Diktaten ohne Behandler


def create_transfer(
    db_path: Path,
    transcript: str,
    codes: list[str],
    ttl_s: int,
    patient_type: str | None = None,
    positions: list[dict] | None = None,
    dictation_id: str | None = None,
    dictation_revision: int | None = None,
    dentist_id: int | None = None,
) -> Transfer:
    """Speichert einen Eintrag unter einem neuen, noch unbenutzten Code.

    Behandler: der des gespeicherten Diktats, sonst der vom iPad genannte (Diktat noch nicht gespeichert).
    """
    positions = list(positions or [])
    now = time.time()
    with db.connect(db_path) as conn:
        db.purge_expired(conn, now)
        while True:
            code = new_code()
            exists = conn.execute("SELECT 1 FROM transfers WHERE code = ?", (code,)).fetchone()
            if exists is None:
                break
        stored = conn.execute("SELECT dentist_id FROM dictations WHERE id = ?", (dictation_id,)).fetchone()
        dentist_id = stored["dentist_id"] if stored is not None else dentists.known(conn, dentist_id)
        conn.execute(
            "INSERT INTO transfers (code, transcript, codes_json, created_at, expires_at, patient_type,"
            " positions_json, dictation_id, dictation_revision, dentist_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                code, transcript, json.dumps(codes), now, now + ttl_s, patient_type, json.dumps(positions),
                dictation_id, dictation_revision, dentist_id,
            ),
        )
    return Transfer(code, transcript, list(codes), now, now + ttl_s, patient_type, positions)


def get_transfer(db_path: Path, code: str) -> Transfer | None:
    """Liefert den Eintrag, solange er nicht abgelaufen ist; sonst None.

    Der erste Abruf schließt das verknüpfte Diktat; war es schon übertragen, wird der Code
    gelöscht und `AlreadyTransferred` ausgelöst.
    """
    now = time.time()
    closed_at = None
    earlier: list[dict] = []
    with db.connect(db_path) as conn:
        db.purge_expired(conn, now)
        row = conn.execute(
            "SELECT t.*, d.name AS dentist_name FROM transfers t LEFT JOIN dentists d ON d.id = t.dentist_id"
            " WHERE t.code = ?",
            (code.strip().upper(),),
        ).fetchone()
        if row is not None and row["dictation_id"] and row["handed_over_at"] is None:
            closed_at = handovers.hand_over(conn, row["dictation_id"], row["dictation_revision"], now)
            if closed_at is None:
                conn.execute("UPDATE transfers SET handed_over_at = ? WHERE code = ?", (now, row["code"]))
                codes = json.loads(row["codes_json"])
                handovers.record(conn, row["dictation_id"], row["code"], row["dictation_revision"], codes, now)
            else:
                conn.execute("DELETE FROM transfers WHERE code = ?", (row["code"],))
        if closed_at is None and row is not None and row["dictation_id"]:
            earlier = handovers.before(conn, row["dictation_id"], row["code"])
    if closed_at is not None:
        raise AlreadyTransferred(closed_at)
    if row is None:
        return None
    return Transfer(
        row["code"],
        row["transcript"],
        json.loads(row["codes_json"]),
        row["created_at"],
        row["expires_at"],
        row["patient_type"],
        json.loads(row["positions_json"]),
        earlier,
        row["dentist_name"],
    )
