"""Kurzcode-Transfer: Transkript + Ziffern für den Rezeptions-PC (WP-10).

Dazu, rein informativ für die Rezeption: der Patiententyp und je Position Zahn, Ziffer und Art
(bema, goz, zuzahlung, kassenanteil). Kopiert wird weiterhin nur `codes` (Evident-Zeilen).

Sechsstellige Codes aus einem verwechslungsfreien Alphabet (ohne 0/O/1/I),
TTL 15 Minuten, innerhalb der TTL mehrfach abrufbar. Nennt das iPad beim Anlegen die ID des
gespeicherten Diktats (`dictation_id`), schließt der erste Abruf dieses Diktat wie „übertragen“
im Büro (`patients.close_handed_over`) – Kurzcode und Patientenliste sind nie zwei Wege zu
demselben Diktat. Abgelaufene Einträge
werden bei jedem Schreiben und Lesen entfernt; zusätzlich räumt `main.py`
beim Start und periodisch auf (WP-11).
"""

from __future__ import annotations

import json
import secrets
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from medvox import db, patients

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6


def new_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=UTC).isoformat(timespec="seconds")


@dataclass(frozen=True)
class Transfer:
    code: str
    transcript: str
    codes: list[str]
    created_at: float
    expires_at: float
    patient_type: str | None = None  # kasse | privat; None bei älteren iPad-Versionen
    positions: list[dict] = field(default_factory=list)  # {"tooth", "code", "kind"}


def create_transfer(
    db_path: Path,
    transcript: str,
    codes: list[str],
    ttl_s: int,
    patient_type: str | None = None,
    positions: list[dict] | None = None,
    dictation_id: str | None = None,
) -> Transfer:
    """Speichert einen Eintrag unter einem neuen, noch unbenutzten Code."""
    positions = list(positions or [])
    now = time.time()
    with db.connect(db_path) as conn:
        db.purge_expired(conn, now)
        while True:
            code = new_code()
            exists = conn.execute("SELECT 1 FROM transfers WHERE code = ?", (code,)).fetchone()
            if exists is None:
                break
        conn.execute(
            "INSERT INTO transfers (code, transcript, codes_json, created_at, expires_at,"
            " patient_type, positions_json, dictation_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (code, transcript, json.dumps(codes), now, now + ttl_s, patient_type, json.dumps(positions), dictation_id),
        )
    return Transfer(code, transcript, list(codes), now, now + ttl_s, patient_type, positions)


def get_transfer(db_path: Path, code: str) -> Transfer | None:
    """Liefert den Eintrag, solange er nicht abgelaufen ist; sonst None. Schließt das verknüpfte Diktat."""
    now = time.time()
    with db.connect(db_path) as conn:
        db.purge_expired(conn, now)
        row = conn.execute(
            "SELECT * FROM transfers WHERE code = ?", (code.strip().upper(),)
        ).fetchone()
        if row is not None and row["dictation_id"]:
            patients.close_handed_over(conn, row["dictation_id"], now)
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
    )
