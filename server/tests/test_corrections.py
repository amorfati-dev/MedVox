"""Korrektur-Sammlung (F2 = b): nur geänderte Stellen, ohne Bezug zum Patienten, höchstens 12 Monate.

Geschrieben wird beim Übertragen (Büro, Kurzcode) und beim Ablauf, nie beim Verwerfen oder Löschen.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from medvox import corrections, db, patients
from medvox.extract_catalog import load_catalog
from medvox.settings import Settings

ORIGINAL = (
    "Zahn 36 mesial okklusal distal Karies profunda, Kompositfüllung in Adhäsivtechnik, zweiflächig, Kofferdam"
    " gelegt. Zahn 46 okklusal Karies. Zahn steinentfernung. Zahn 16 Wurzelkanalbehandlung planen."
)
FIXED = ORIGINAL.replace("zweiflächig", "dreiflächig").replace("Zahn steinentfernung", "Zahnsteinentfernung")


def sug(code: str, teeth: list[int], count: int = 1, **extra) -> dict:
    return {"code": code, "system": "BEMA", "title": code, "points": None, "teeth": teeth, "count": count,
            "reason": "", "decide": [], "planned": False, "alternative": False, "kind": "bema", **extra}


CORRECTED = {
    "transcript": FIXED,
    "patient_type": "kasse",
    "codes": ["13c", "12", "13a", "107"],
    "suggestions": [sug("13c", [36]), sug("12", [36]), sug("13a", [46]), sug("107", [], source="hand")],
    "deselected": [],
    "original": {
        "transcript": ORIGINAL,
        "codes": ["13b", "12", "13a"],
        "positions": [{"tooth": 36, "code": "13b"}, {"tooth": 36, "code": "12"}, {"tooth": 46, "code": "13a"}],
    },
}


def rows(db_path: Path) -> list[tuple]:
    with sqlite3.connect(db_path) as conn:
        return conn.execute("SELECT week, patient_type, kind, before, after, catalog_version FROM corrections").fetchall()


@pytest.fixture
def db_path(settings: Settings) -> Path:
    db.init_db(settings.db_path)
    return settings.db_path


def test_transfer_keeps_only_the_changed_spots(db_path: Path) -> None:
    now = time.time()
    saved = patients.save_dictation(db_path, "diktat-0001", CORRECTED, "4711", now=now, label="M.K.")
    patients.mark_transferred(db_path, saved.patient_id, {saved.id: saved.revision}, now=now)
    found = rows(db_path)
    version = load_catalog().version
    assert {(k, b, a) for _w, _t, k, b, a, _v in found} == {
        ("text", "in Adhäsivtechnik, zweiflächig, Kofferdam gelegt.", "in Adhäsivtechnik, dreiflächig, Kofferdam gelegt."),
        ("text", "okklusal Karies. Zahn steinentfernung. Zahn 16", "okklusal Karies. Zahnsteinentfernung. Zahn 16"),
        ("ziffer", "13b", "13c"),
        ("ziffer", "", "107"),
    }
    assert {(w, t, v) for w, t, _k, _b, _a, v in found} == {(corrections.week(now), "kasse", version)}


def test_a_correction_row_never_names_patient_dentist_or_time(db_path: Path) -> None:
    now = time.time()
    with db.connect(db_path) as conn:
        dentist = conn.execute("SELECT id, name FROM dentists").fetchone()
    saved = patients.save_dictation(db_path, "diktat-0001", CORRECTED, "4711", dentist["id"], now=now, label="M.K.")
    patients.mark_transferred(db_path, saved.patient_id, {saved.id: saved.revision}, now=now)
    with sqlite3.connect(db_path) as conn:
        columns = [r[1] for r in conn.execute("PRAGMA table_info(corrections)")]
    assert columns == ["id", "week", "patient_type", "kind", "before", "after", "catalog_version"]
    text = repr(rows(db_path))
    for secret in ("4711", "M.K.", dentist["name"], "diktat-0001", time.strftime("%Y-%m-%d", time.localtime(now))):
        assert secret not in text
    assert FIXED not in text and ORIGINAL not in text  # nie der ganze Text


def test_long_rewrites_are_dropped_and_context_is_short() -> None:
    before = "eins zwei drei vier " + " ".join(f"alt{i}" for i in range(13)) + " fünf sechs sieben acht"
    after = "eins zwei drei vier " + " ".join(f"neu{i}" for i in range(13)) + " fünf sechs sieben acht"
    assert corrections.text_spots(before, after) == []
    spots = corrections.text_spots("a b c d falsch e f g h", "a b c d richtig e f g h")
    assert spots == [("c d falsch e f", "c d richtig e f")]


def test_nearby_spots_merge_so_rows_cannot_rebuild_the_text() -> None:
    words = "a b c d e f g h i j k l m n o p q r s t".split()
    fixed = [w.upper() if w in {"b", "e", "h"} else w for w in words]
    spots = corrections.text_spots(" ".join(words), " ".join(fixed))
    assert spots == [("a b c d e f g h i j", "a B c d E f g H i j")]
    common = "Zahn 36 " + " ".join(f"alt{i} Zahn" for i in range(8))
    rewritten = "Zahn 36 " + " ".join(f"neu{i} Zahn" for i in range(8))
    assert corrections.text_spots(common, rewritten) == []


def test_row_ids_do_not_reveal_insertion_order(db_path: Path) -> None:
    now = time.time()
    for n in range(3):
        saved = patients.save_dictation(db_path, f"diktat-000{n}", CORRECTED, f"47{n}", now=now)
        patients.mark_transferred(db_path, saved.patient_id, {saved.id: saved.revision}, now=now)
    with sqlite3.connect(db_path) as conn:
        ids = sorted(r[0] for r in conn.execute("SELECT id FROM corrections"))
    assert len(ids) == 12
    assert all(b - a > 1 for a, b in zip(ids, ids[1:]))


def test_code_changes_count_and_deselection() -> None:
    data = {
        "codes": ["2x 25", "13b", "40"],
        "deselected": ["40"],
        "suggestions": [sug("25", [36], 2, source="hand"), sug("25", [36]), sug("13b", [36]), sug("40", [36]),
                        sug("2100", [36], alternative=True)],
    }
    original = [{"tooth": 36, "code": "25"}, {"tooth": 36, "code": "13b"}, {"tooth": 36, "code": "40"}]
    assert corrections.code_changes(original, data) == [("40", ""), ("25", "2x 25")]


def test_hand_position_counts_even_if_the_code_is_deselected_elsewhere() -> None:
    data = {
        "codes": ["13a", "13a"],
        "deselected": ["13a"],
        "suggestions": [sug("13a", [36]), sug("13a", [46], source="hand")],
    }
    assert corrections.code_changes([{"tooth": 36, "code": "13a"}], data) == [("13a", ""), ("", "13a")]


def test_expiry_collects_but_discard_does_not(settings: Settings, logged_in: TestClient) -> None:
    db_path = settings.db_path
    old = time.time() - patients.RETENTION_S - 1
    patients.save_dictation(db_path, "abgelaufen-1", CORRECTED, "4711", now=old)
    patients.save_dictation(db_path, "verworfen-1", CORRECTED, "4712")
    patients.save_dictation(db_path, "geloescht-1", CORRECTED, "4713")
    assert logged_in.delete("/api/v1/dictations/verworfen-1").status_code == 204
    pid = next(p["id"] for p in logged_in.get("/api/v1/patients").json()["patients"] if p["number"] == "4713")
    assert logged_in.delete(f"/api/v1/patients/{pid}").status_code == 204
    assert len(rows(db_path)) == 4  # nur das abgelaufene Diktat


def test_short_code_transfer_collects(logged_in: TestClient, settings: Settings) -> None:
    saved = logged_in.put("/api/v1/dictations/diktat-0001", json={**CORRECTED, "patient": "4711"}).json()
    assert saved["original"]["transcript"] == ORIGINAL  # das Büro sieht das Original
    body = {"transcript": FIXED, "codes": ["36,13c"], "dictation_id": "diktat-0001", "dictation_revision": saved["revision"]}
    code = logged_in.post("/api/v1/transfer", json=body).json()["code"]
    assert TestClient(logged_in.app).get(f"/api/v1/transfer/{code}").status_code == 200
    assert len(rows(settings.db_path)) == 4


def test_ipad_hand_position_is_saved(logged_in: TestClient) -> None:
    """Eine am iPad ergänzte Position hat die Felder der App (ohne `planned`) und wird gespeichert."""
    hand = {"code": "107", "system": "BEMA", "title": "Zahnstein", "kind": "bema", "count": 1, "points": None,
            "teeth": [], "reason": "von Hand ergänzt", "decide": [], "alternative": False, "evident": None, "source": "hand"}
    body = {**CORRECTED, "suggestions": [*CORRECTED["suggestions"][:3], hand]}
    saved = logged_in.put("/api/v1/dictations/diktat-0002", json=body)
    assert saved.status_code == 200
    assert saved.json()["suggestions"][-1]["source"] == "hand" and saved.json()["suggestions"][-1]["planned"] is False


def test_uncorrected_dictation_leaves_nothing(db_path: Path) -> None:
    plain = {k: v for k, v in CORRECTED.items() if k != "original"}
    saved = patients.save_dictation(db_path, "diktat-0001", plain, "4711")
    patients.mark_transferred(db_path, saved.patient_id, {saved.id: saved.revision})
    assert rows(db_path) == []


def test_rows_older_than_twelve_months_are_purged(db_path: Path) -> None:
    now = time.time()
    with db.connect(db_path) as conn:
        for ts in (now - corrections.KEEP_S - 7 * 86400, now - corrections.KEEP_S + 8 * 86400):
            conn.execute(
                "INSERT INTO corrections (week, patient_type, kind, before, after, catalog_version)"
                " VALUES (?, 'kasse', 'text', 'a', 'b', '1')",
                (corrections.week(ts),),
            )
    db.purge_expired_at(db_path)
    assert [r[0] for r in rows(db_path)] == [corrections.week(now - corrections.KEEP_S + 8 * 86400)]


def test_week_sorts_as_text() -> None:
    assert corrections.week(time.mktime((2025, 12, 29, 12, 0, 0, 0, 0, -1))) == "2026-W01"
    assert corrections.week(time.mktime((2025, 12, 22, 12, 0, 0, 0, 0, -1))) < "2026-W01"
