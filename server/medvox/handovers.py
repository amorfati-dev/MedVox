"""Abgeholte Kurzcodes je Diktat: wann welcher Stand an der Rezeption abgeholt wurde.

Je erstem Abruf eines verknüpften Kurzcodes eine Zeile: Diktat-ID, Code, Revision, Zeitpunkt und
die übergebenen Evident-Zeilen (nur Ziffern, kein Transkript, keine Patientennummer). Die Zeilen
bleiben, solange das Diktat offen ist oder sein Grabstein liegt (`db.purge_expired`), damit ein
späterer Kurzcode oder das Büro sieht, was schon übergeben wurde – und nur die Änderung einträgt.
"""

from __future__ import annotations

import json
import sqlite3


def record(
    conn: sqlite3.Connection, dictation_id: str, code: str, revision: int | None, codes: list[str], now: float
) -> None:
    conn.execute(
        "INSERT INTO handovers (dictation_id, code, revision, fetched_at, codes_json) VALUES (?, ?, ?, ?, ?)",
        (dictation_id, code, revision, now, json.dumps(codes)),
    )


def _out(row: sqlite3.Row) -> dict:
    return {"fetched_at": row["fetched_at"], "codes": json.loads(row["codes_json"])}


def before(conn: sqlite3.Connection, dictation_id: str, code: str) -> list[dict]:
    """Abholungen desselben Diktats vor dem ersten Abruf dieses Codes, älteste zuerst."""
    rows = conn.execute(
        "SELECT fetched_at, codes_json FROM handovers WHERE dictation_id = ? AND code != ?"
        " AND fetched_at <= (SELECT min(fetched_at) FROM handovers WHERE code = ?) ORDER BY fetched_at",
        (dictation_id, code, code),
    ).fetchall()
    return [_out(r) for r in rows]


def by_dictation(conn: sqlite3.Connection, dictation_ids: list[str]) -> dict[str, list[dict]]:
    """Alle Abholungen je Diktat, älteste zuerst."""
    found: dict[str, list[dict]] = {d: [] for d in dictation_ids}
    if not dictation_ids:
        return found
    marks = ",".join("?" * len(dictation_ids))
    rows = conn.execute(
        f"SELECT dictation_id, fetched_at, codes_json FROM handovers WHERE dictation_id IN ({marks})"
        " ORDER BY fetched_at",
        dictation_ids,
    ).fetchall()
    for r in rows:
        found[r["dictation_id"]].append(_out(r))
    return found
