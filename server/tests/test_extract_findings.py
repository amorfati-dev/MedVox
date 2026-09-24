"""Zahnschema (Ship 3): Befunde je Zahn, Feld `teeth` in /analyze und im Diktat, „je Zahn“ im Katalog."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from medvox.corrections import code_changes
from medvox.extract_catalog import fold
from medvox.extract_findings import FINDINGS_PATH, ToothFindings, extract_findings
from medvox.lexicon import correct
from medvox.normalize import normalize


def findings(text: str) -> list[ToothFindings]:
    normalized = normalize(correct(text)[0])
    return extract_findings(normalized.text, normalized.teeth)


def test_tooth_surfaces_and_longest_finding() -> None:
    assert findings("Zahn drei sechs mesial okklusal distal Karies profunda, Kompositfüllung dreiflächig.") == [
        ToothFindings(36, "mod", ("Karies profunda",)),
    ]


def test_each_tooth_once_in_dictation_order() -> None:
    result = findings("Zahn 46 okklusal Karies, Füllung einflächig. Zahn 16 Pulpitis, Trepanation. 46 Aufbissbeschwerden.")
    assert result == [
        ToothFindings(46, "o", ("Karies", "Aufbissbeschwerden")),
        ToothFindings(16, "", ("Pulpitis",)),
    ]


def test_negated_finding_is_left_out() -> None:
    assert findings("Zahn 36 keine Karies, Versiegelung.") == [ToothFindings(36, "", ())]


def test_finding_without_tooth_comes_last() -> None:
    assert findings("Gingivitis, Zahnstein entfernt. Zahn 11 Fraktur.") == [
        ToothFindings(11, "", ("Fraktur",)),
        ToothFindings(None, "", ("Gingivitis",)),
    ]


def test_a_group_of_teeth_shares_the_finding() -> None:
    result = findings("16, 26 Karies media.")
    assert [(t.tooth, t.findings) for t in result] == [(16, ("Karies media",)), (26, ("Karies media",))]


def test_finding_words_are_unique_and_never_codes() -> None:
    raw = json.loads(FINDINGS_PATH.read_text(encoding="utf-8"))
    keywords = [fold(k) for item in raw["findings"] for k in item["keywords"]]
    assert len(keywords) == len(set(keywords))
    assert all(item["review"] in {"vorschlag", "bestaetigt"} for item in raw["findings"])
    assert not any(k.replace(" ", "").isdigit() for k in keywords)


def test_analyze_returns_the_teeth(logged_in: TestClient) -> None:
    result = logged_in.post("/api/v1/analyze", json={"text": "Zahn 36 mod Karies profunda, Füllung dreiflächig."}).json()
    assert result["teeth"] == [{"tooth": 36, "surfaces": "mod", "findings": ["Karies profunda"]}]


def test_dictation_keeps_teeth_and_tapped(logged_in: TestClient) -> None:
    tapped = {
        "code": "4055", "system": "GOZ", "title": "Zahnsteinentfernung, mehrwurzeliger Zahn", "points": 13,
        "teeth": [16], "count": 1, "reason": "Zahn angetippt", "decide": [], "alternative": False, "kind": "goz",
        "source": "hand", "tapped": True,
    }
    body = {
        "transcript": "Zahnstein entfernt.", "patient_type": "privat", "codes": ["4055"], "suggestions": [tapped],
        "teeth": [{"tooth": 36, "surfaces": "mod", "findings": ["Karies profunda"]}],
    }
    saved = logged_in.put("/api/v1/dictations/diktat-zahnschema", json=body).json()
    assert saved["teeth"] == body["teeth"]
    assert saved["suggestions"][0]["tapped"] is True


@pytest.mark.parametrize(
    ("patient_type", "code", "roots"),
    [("privat", "4050", ["4050", "4055"]), ("privat", "2000", []), ("kasse", "AITb", ["AITa", "AITb"])],
)
def test_catalog_marks_per_tooth_positions(logged_in: TestClient, patient_type: str, code: str, roots: list) -> None:
    entries = logged_in.get(f"/api/v1/catalog?patient_type={patient_type}").json()["entries"]
    entry = next(e for e in entries if e["code"] == code)
    assert entry["per_tooth"] is True and entry["roots"] == roots


def test_session_positions_are_not_per_tooth(logged_in: TestClient) -> None:
    entries = logged_in.get("/api/v1/catalog?patient_type=kasse").json()["entries"]
    assert {e["code"]: e["per_tooth"] for e in entries}["107"] is False
    assert not next(e for e in entries if e["code"] == "13c")["per_tooth"]


def test_correction_record_keeps_the_tapped_change_without_teeth() -> None:
    """F2 = b: aus 4050 ohne Zahn werden je Zahn 4050/4055 – festgehalten nur Ziffern, nie Zähne."""
    def tap(code: str, tooth: int) -> dict:
        return {"code": code, "teeth": [tooth], "count": 1, "source": "hand", "tapped": True, "alternative": False}

    data = {"codes": ["2x 4050", "4055"], "suggestions": [tap("4050", 11), tap("4050", 12), tap("4055", 16)]}
    changes = code_changes([{"tooth": None, "code": "4050", "count": 1}], data)
    assert sorted(changes) == [("", "4050"), ("", "4050"), ("", "4055"), ("4050", "")]
