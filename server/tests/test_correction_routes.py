"""Korrektur am iPad: Ziffern aus berichtigtem Text neu berechnen (/analyze), Katalog-Blatt (/catalog)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from medvox.extract_catalog import load_catalog
from medvox.extract_rules import SURCHARGE_CODES

ANALYZE = "/api/v1/analyze"
CATALOG = "/api/v1/catalog"
ANHANG_B = Path(__file__).resolve().parents[2] / "app" / "test" / "fixtures" / "anhang-b.json"


def positions(result: dict) -> list[tuple]:
    rows = result["suggestions"] + result["planned"]
    return [(s["code"], tuple(s["teeth"]), s["count"], s["alternative"], s["planned"]) for s in rows]


def test_analyze_needs_a_session(client: TestClient) -> None:
    assert client.post(ANALYZE, json={"text": "Zahn 36 Füllung einflächig"}).status_code == 401
    assert client.get(CATALOG).status_code == 401


@pytest.mark.parametrize("name", list(json.loads(ANHANG_B.read_text(encoding="utf-8"))))
def test_analyze_is_a_fixpoint_for_anhang_b(logged_in: TestClient, name: str) -> None:
    """Das angezeigte Transkript ergibt ohne Änderung dieselben Ziffern, Zähne, Anzahlen und Optionen."""
    shown = json.loads(ANHANG_B.read_text(encoding="utf-8"))[name]
    again = logged_in.post(ANALYZE, json={"text": shown["transcript"], "patient_type": shown["patient_type"]})
    assert again.status_code == 200
    result = again.json()
    assert result["transcript"] == shown["transcript"]
    assert result["codes"] == shown["codes"]
    assert positions(result) == [
        (s["code"], tuple(s["teeth"]), s["count"], s["alternative"], s.get("planned", False))
        for s in shown["suggestions"] + shown.get("planned", [])
    ]
    assert result["duration_s"] == 0 and result["latency_s"] == 0
    assert all(s["source"] == "regel" for s in result["suggestions"])


def test_corrected_word_brings_the_missing_code_back(logged_in: TestClient) -> None:
    before = logged_in.post(ANALYZE, json={"text": "Zahn steinentfernung, Politur, Fluoridierung."}).json()
    after = logged_in.post(ANALYZE, json={"text": "Zahnsteinentfernung, Politur, Fluoridierung."}).json()
    assert "107" not in before["codes"] and "107" in after["codes"]


def test_analyze_uses_the_patient_type(logged_in: TestClient) -> None:
    text = "Zahn drei sechs okklusal Kompositfüllung einflächig"
    kasse = logged_in.post(ANALYZE, json={"text": text, "patient_type": "kasse"}).json()
    privat = logged_in.post(ANALYZE, json={"text": text, "patient_type": "privat"}).json()
    assert kasse["patient_type"] == "kasse" and kasse["codes"] == ["13a"]
    assert privat["patient_type"] == "privat" and privat["codes"] == ["2060"]
    assert logged_in.post(ANALYZE, json={"text": text, "patient_type": "gesetzlich"}).status_code == 422


def test_analyze_logs_only_counts(logged_in: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        logged_in.post(ANALYZE, json={"text": "Zahn 36 Geheimbefund Kompositfüllung einflächig"})
    assert "Geheimbefund" not in caplog.text and "Zeichen" in caplog.text


def test_catalog_for_kasse_is_bema_plus_co_payment_list(logged_in: TestClient) -> None:
    body = logged_in.get(CATALOG, params={"patient_type": "kasse"}).json()
    catalog = load_catalog()
    assert body["version"] == catalog.version and body["patient_type"] == "kasse"
    listed = {(e["system"], e["code"]): e for e in body["entries"]}
    for entry in catalog.entries:
        allowed = entry.system == "BEMA" or entry.analog is not None or catalog.co_payment_allowed(entry)
        assert (entry.key in listed) == allowed, entry.label
    assert not SURCHARGE_CODES & {code for _system, code in listed}  # Zuschlag nur bei Privat
    assert listed[("GOZ", "2080")]["kind"] == "zuzahlung"
    assert listed[("BEMA", "13b")]["family"] == ["13a", "13b", "13c", "13d"]
    assert listed[("BEMA", "12")]["evident"] == catalog.get("BEMA", "12").evident


def test_catalog_for_privat_is_goz_and_goae_only(logged_in: TestClient) -> None:
    body = logged_in.get(CATALOG, params={"patient_type": "privat"}).json()
    assert body["entries"] and {e["system"] for e in body["entries"]} == {"GOZ", "GOÄ"}
    assert {e["kind"] for e in body["entries"]} == {"goz"}
    assert SURCHARGE_CODES <= {e["code"] for e in body["entries"]}
    inlay = next(e for e in body["entries"] if e["code"] == "2160")
    assert inlay["family"] == ["2150", "2160", "2170", "2170"]
    assert logged_in.get(CATALOG, params={"patient_type": "egal"}).status_code == 422
