"""Korrektur-Sammlung: was am iPad berichtigt wurde, ohne Bezug zu Patient oder Diktat (Entscheidung F2 = b).

Ein am iPad korrigiertes Diktat trägt sein Original (`data["original"]`: Transkript und Ziffern je Zahn
vor der Korrektur, nur 24 Stunden wie das Diktat). Wird es übertragen (Büro oder Kurzcode) oder läuft
es ab, bleiben davon nur die geänderten Stellen – beim Verwerfen oder Löschen nichts:

- Text: je geänderte Stelle vorher/nachher mit höchstens zwei Wörtern Umfeld auf jeder Seite (zusammen
  höchstens 4); Stellen, deren Umfeld sich berührt, zählen als eine. Stellen mit mehr als 12 geänderten
  Wörtern werden verworfen.
- Ziffern: `13b` → `13c` (Familie ersetzt), `` → `107` (ergänzt), `13b` → `` (abgewählt oder entfallen),
  `25` → `2x 25` (Anzahl), ohne Zahn.

Dazu nur Patiententyp, Kalenderwoche und Katalogstand. Nie Evident-Nummer, Kürzel, Behandler, Datum
oder Uhrzeit, Diktat-ID oder der ganze Text; die Tabelle hat keine Verknüpfung zu anderen, die Zeilen-ID
ist zufällig (keine Reihenfolge, die Zeilen eines Diktats verbindet). Jede Zeile
bleibt, bis sie gelöscht wird, höchstens 12 Monate (`purge`, bei jedem Aufräumen in `db.purge_expired`).
Geschrieben wird in derselben Transaktion, in der `db.bury` das Diktat löscht.
"""

from __future__ import annotations

import json
import logging
import re
import secrets
import sqlite3
from datetime import datetime
from difflib import SequenceMatcher

from medvox.extract_catalog import load_catalog

log = logging.getLogger("medvox.corrections")

AROUND = 2  # Wörter Umfeld je Seite: zusammen höchstens 4
MAX_SPOT = 12  # längere Stellen werden verworfen
KEEP_S = 365 * 24 * 3600  # höchstens 12 Monate

_COUNT = re.compile(r"^(\d+)x\s+")


def week(ts: float) -> str:
    """Kalenderwoche nach ISO 8601, z. B. „2026-W39“ (sortiert als Text richtig)."""
    year, number, _ = datetime.fromtimestamp(ts).isocalendar()
    return f"{year}-W{number:02d}"


def text_spots(before: str, after: str) -> list[tuple[str, str]]:
    """Geänderte Stellen (vorher, nachher) mit höchstens `AROUND` Wörtern Umfeld je Seite.

    Stellen, deren Umfeld sich berührt oder überschneidet, sind eine Stelle; die Grenze `MAX_SPOT` gilt
    für diese ganze Stelle – sonst ergäben mehrere kurze Stellen zusammen den Text.
    """
    a, b = before.split(), after.split()
    merged: list[list[int]] = []
    for tag, i1, i2, j1, j2 in SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        if merged and i1 - merged[-1][1] <= 2 * AROUND:
            merged[-1][1], merged[-1][3] = i2, j2
        else:
            merged.append([i1, i2, j1, j2])
    spots = []
    for i1, i2, j1, j2 in merged:
        if max(i2 - i1, j2 - j1) > MAX_SPOT:
            continue
        old = a[max(0, i1 - AROUND):i2 + AROUND]
        new = b[max(0, j1 - AROUND):j2 + AROUND]
        spots.append((" ".join(old), " ".join(new)))
    return spots


def _per_tooth(items: list[tuple[int | None, str, int]]) -> dict[int | None, dict[str, int]]:
    """Ziffern je Zahn; dieselbe Ziffer am selben Zahn zählt einmal mit der höchsten Anzahl (wie die Evident-Zeile)."""
    teeth: dict[int | None, dict[str, int]] = {}
    for tooth, code, count in items:
        codes = teeth.setdefault(tooth, {})
        codes[code] = max(codes.get(code, 0), count)
    return teeth


def _label(code: str, count: int) -> str:
    return code if count <= 1 else f"{count}x {code}"


def code_changes(original: list[dict], data: dict) -> list[tuple[str, str]]:
    """Ziffernänderungen vom Original (Regel-Vorschläge) zum gewählten Stand, je Zahn verglichen, ohne Zahn gemeldet."""
    families = {e.code: e.family for e in load_catalog().entries if e.family}
    dropped = set(data.get("deselected", []))
    chosen = {_COUNT.sub("", c) for c in data.get("codes", []) if c not in dropped}
    before = _per_tooth([(p.get("tooth"), p["code"], int(p.get("count", 1))) for p in original])
    main = [
        ((s.get("teeth") or [None])[0], s["code"], int(s.get("count", 1)), s.get("source") == "hand")
        for s in data.get("suggestions", [])
        if not s.get("alternative") and not s.get("planned")
    ]
    # Zeilen „von Hand“ ohne Regel-Vorschlag derselben Ziffer am Zahn werden immer kopiert (wie result.ts).
    ruled = {(tooth, code) for tooth, code, _n, hand in main if not hand}
    after = _per_tooth([
        (tooth, code, count) for tooth, code, count, hand in main
        if code in chosen or (hand and (tooth, code) not in ruled)
    ])
    changes: list[tuple[str, str]] = []
    for tooth in dict.fromkeys([*before, *after]):
        old, new = before.get(tooth, {}), after.get(tooth, {})
        gone = [c for c in old if c not in new]
        added = [c for c in new if c not in old]
        for code in gone:
            twin = next((c for c in added if families.get(c) and families.get(c) == families.get(code)), None)
            if twin is not None:
                added.remove(twin)
            changes.append((_label(code, old[code]), _label(twin, new[twin]) if twin else ""))
        changes += [("", _label(c, new[c])) for c in added]
        changes += [(_label(c, old[c]), _label(c, new[c])) for c in old if c in new and old[c] != new[c]]
    return changes


def changes(data: dict) -> list[tuple[str, str, str]]:
    """(Art, vorher, nachher) eines gespeicherten Diktats; leer, wenn es nicht korrigiert wurde."""
    original = data.get("original")
    if not isinstance(original, dict):
        return []
    rows = [("text", old, new) for old, new in text_spots(original.get("transcript", ""), data.get("transcript", ""))]
    rows += [("ziffer", old, new) for old, new in code_changes(original.get("positions", []), data)]
    return rows


def record(conn: sqlite3.Connection, where: str, params: tuple, now: float) -> int:
    """Hält die Änderungen der Diktate fest, auf die `where` passt (vor dem Löschen durch `db.bury`)."""
    version = load_catalog().version
    count = 0
    for row in conn.execute(f"SELECT data_json FROM dictations WHERE {where}", params).fetchall():
        try:
            data = json.loads(row["data_json"])
            found = changes(data)
        except (AttributeError, KeyError, TypeError, ValueError):
            log.warning("Korrektur eines Diktats nicht lesbar – nicht gesammelt")
            continue
        for kind, old, new in found:
            conn.execute(
                "INSERT INTO corrections (id, week, patient_type, kind, before, after, catalog_version)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (secrets.randbits(62), week(now), data.get("patient_type"), kind, old, new, version),
            )
        count += len(found)
    if count:
        log.info("Korrekturen gesammelt (%d Stellen)", count)
    return count


def purge(conn: sqlite3.Connection, now: float) -> None:
    """Zeilen älter als 12 Monate löschen (ganze Kalenderwochen, nie länger als `KEEP_S`)."""
    conn.execute("DELETE FROM corrections WHERE week <= ?", (week(now - KEEP_S),))
