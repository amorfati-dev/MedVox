"""Diktate je Patient: anlegen, mehrere Diktate, „ohne Patient“ zuordnen, übertragen, löschen."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from medvox.routes_transcribe import build_response
from medvox.settings import Settings

PATIENTS = "/api/v1/patients"
DICTATIONS = "/api/v1/dictations"
DICTATION = {
    "transcript": "Zahn 36 mod Karies profunda, Kompositfüllung dreiflächig.",
    "patient_type": "kasse",
    "codes": ["13c"],
}


def put(client: TestClient, did: str, patient: str | None = None, **fields) -> dict:
    body = {**DICTATION, **fields, **({"patient": patient} if patient else {})}
    response = client.put(f"{DICTATIONS}/{did}", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def listing(client: TestClient) -> dict:
    response = client.get(PATIENTS)
    assert response.status_code == 200
    return response.json()


def by_number(client: TestClient, number: str) -> dict:
    return next(p for p in listing(client)["patients"] if p["number"] == number)


def detail(client: TestClient, patient_id: int) -> dict:
    response = client.get(f"{PATIENTS}/{patient_id}")
    assert response.status_code == 200
    return response.json()


def test_everything_requires_login(client: TestClient) -> None:
    assert client.get(PATIENTS).status_code == 401
    assert client.post(PATIENTS, json={"number": "4711"}).status_code == 401
    assert client.get(f"{PATIENTS}/1").status_code == 401
    assert client.post(f"{PATIENTS}/1/transferred", json={"seen": []}).status_code == 401
    assert client.delete(f"{PATIENTS}/1").status_code == 401
    assert client.put(f"{DICTATIONS}/diktat-0001", json=DICTATION).status_code == 401


def test_create_is_idempotent_per_number(logged_in: TestClient) -> None:
    first = logged_in.post(PATIENTS, json={"number": "004711"}).json()
    again = logged_in.post(PATIENTS, json={"number": "004711"}).json()
    assert first["id"] == again["id"] and first["number"] == "004711"  # führende Nullen bleiben
    assert first["dictations"] == 0 and first["transferred"] == 0 and first["transferred_at"] is None


@pytest.mark.parametrize("number", ["", "12a4", "Müller", "1234567890123", " 4711"])
def test_only_evident_numbers(logged_in: TestClient, number: str) -> None:
    assert logged_in.post(PATIENTS, json={"number": number}).status_code == 422
    body = {**DICTATION, "patient": number}
    assert logged_in.put(f"{DICTATIONS}/diktat-0001", json=body).status_code == 422


def test_several_dictations_per_patient(logged_in: TestClient) -> None:
    put(logged_in, "diktat-0001", "4711", transcript="Erstes Diktat.")
    put(logged_in, "diktat-0002", "4711", transcript="Zweites Diktat.")
    patient = by_number(logged_in, "4711")
    assert patient["dictations"] == 2
    items = detail(logged_in, patient["id"])["items"]
    assert [d["transcript"] for d in items] == ["Erstes Diktat.", "Zweites Diktat."]
    assert all(d["patient"] == "4711" and d["patient_id"] == patient["id"] for d in items)


def test_saving_again_replaces_the_dictation(logged_in: TestClient) -> None:
    # Jeder weitere Abschnitt oder jede Auswahländerung am iPad speichert denselben Stand neu.
    first = put(logged_in, "diktat-0001", "4711", transcript="Zahn 36")
    second = put(logged_in, "diktat-0001", "4711", transcript="Zahn 36 mod", deselected=["13c"])
    assert second["revision"] == first["revision"] + 1 and second["created_at"] == first["created_at"]
    items = detail(logged_in, by_number(logged_in, "4711")["id"])["items"]
    assert len(items) == 1 and items[0]["transcript"] == "Zahn 36 mod" and items[0]["deselected"] == ["13c"]


def test_unassigned_dictation_assigned_later(logged_in: TestClient) -> None:
    put(logged_in, "diktat-0001")  # Nummer vergessen
    loose = listing(logged_in)["unassigned"]
    assert [d["id"] for d in loose] == ["diktat-0001"] and loose[0]["patient"] is None
    assert loose[0]["transcript"] == DICTATION["transcript"]

    patient = logged_in.post(PATIENTS, json={"number": "4711"}).json()
    moved = logged_in.post(f"{PATIENTS}/{patient['id']}/dictations", json={"dictation_id": "diktat-0001"})
    assert moved.status_code == 200 and moved.json()["patient"] == "4711"
    assert listing(logged_in)["unassigned"] == []
    assert [d["id"] for d in detail(logged_in, patient["id"])["items"]] == ["diktat-0001"]

    # Das iPad speichert das Diktat später noch einmal ohne Nummer: die Zuordnung bleibt.
    put(logged_in, "diktat-0001", transcript="nachträglich ergänzt")
    assert detail(logged_in, patient["id"])["items"][0]["transcript"] == "nachträglich ergänzt"
    assert listing(logged_in)["unassigned"] == []


def test_number_entered_after_dictating(logged_in: TestClient) -> None:
    put(logged_in, "diktat-0001")
    put(logged_in, "diktat-0001", "4711")  # am iPad danach die Nummer eingetippt
    assert listing(logged_in)["unassigned"] == []
    assert by_number(logged_in, "4711")["dictations"] == 1


def test_assign_unknown_is_404(logged_in: TestClient) -> None:
    patient = logged_in.post(PATIENTS, json={"number": "4711"}).json()
    assert logged_in.post(f"{PATIENTS}/{patient['id']}/dictations", json={"dictation_id": "fehlt-0001"}).status_code == 404
    put(logged_in, "diktat-0001")
    assert logged_in.post(f"{PATIENTS}/999/dictations", json={"dictation_id": "diktat-0001"}).status_code == 404


def test_suggestions_are_stored_unchanged(logged_in: TestClient) -> None:
    # Das Büro rechnet die Evident-Zeilen aus genau diesen Daten – sie dürfen sich nicht verändern.
    result = build_response(
        "Zahn drei sechs mesial okklusal distal Karies profunda, Infiltrationsanästhesie, "
        "Kompositfüllung in Adhäsivtechnik, dreiflächig, Kofferdam gelegt.", 4.0, 0.8, "kasse",
    ).model_dump()
    stored = {k: result[k] for k in ("transcript", "patient_type", "codes", "suggestions", "planned", "notes")}
    assert stored["suggestions"], "Beispiel braucht Vorschläge"
    put(logged_in, "diktat-0001", "4711", **stored, adopted=["2100@36"])
    item = detail(logged_in, by_number(logged_in, "4711")["id"])["items"][0]
    for key, value in stored.items():
        assert item[key] == value, key
    assert item["adopted"] == ["2100@36"]


def _db_bytes(db_path: Path) -> bytes:
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    return db_path.read_bytes()


def test_transferred_patient_content_is_gone(logged_in: TestClient, settings: Settings) -> None:
    put(logged_in, "diktat-0001", "4711", transcript="Geheimer Befund eins.")
    put(logged_in, "diktat-0002", "4711", transcript="Geheimer Befund zwei.")
    patient = by_number(logged_in, "4711")
    items = detail(logged_in, patient["id"])["items"]
    seen = [{"id": d["id"], "revision": d["revision"]} for d in items]
    done = logged_in.post(f"{PATIENTS}/{patient['id']}/transferred", json={"seen": seen})
    assert done.status_code == 200
    assert done.json()["items"] == [] and done.json()["transferred"] == 2 and done.json()["transferred_at"]

    with sqlite3.connect(settings.db_path) as conn:
        assert conn.execute("SELECT count(*) FROM dictations").fetchone()[0] == 0
    assert b"Geheimer Befund" not in _db_bytes(settings.db_path)  # secure_delete: auch nicht in freien Seiten


def test_transfer_keeps_what_the_office_has_not_seen(logged_in: TestClient) -> None:
    shown = put(logged_in, "diktat-0001", "4711")
    changed = put(logged_in, "diktat-0002", "4711")
    put(logged_in, "diktat-0002", "4711", transcript="am iPad ergänzt, nachdem das Büro geöffnet hat")
    put(logged_in, "diktat-0003", "4711")  # neu dazugekommen
    patient_id = shown["patient_id"]
    seen = [{"id": d["id"], "revision": d["revision"]} for d in (shown, changed)]
    after = logged_in.post(f"{PATIENTS}/{patient_id}/transferred", json={"seen": seen}).json()
    assert [d["id"] for d in after["items"]] == ["diktat-0002", "diktat-0003"]
    assert after["transferred"] == 1 and after["dictations"] == 2


def test_list_shows_open_and_transferred_newest_first(logged_in: TestClient) -> None:
    done = put(logged_in, "diktat-0001", "1001")
    put(logged_in, "diktat-0002", "1002")
    logged_in.post(PATIENTS, json={"number": "1003"})  # Nummer eingegeben, noch kein Diktat
    logged_in.post(
        f"{PATIENTS}/{done['patient_id']}/transferred", json={"seen": [{"id": done["id"], "revision": done["revision"]}]}
    )
    patients = listing(logged_in)["patients"]
    assert [p["number"] for p in patients] == ["1003", "1002", "1001"]
    state = {p["number"]: (p["dictations"], p["transferred"], p["transferred_at"] is not None) for p in patients}
    assert state == {"1003": (0, 0, False), "1002": (1, 0, False), "1001": (0, 1, True)}

    # Derselbe Patient später am Tag noch einmal: wieder offen, oben in der Liste.
    put(logged_in, "diktat-0004", "1001")
    first = listing(logged_in)["patients"][0]
    assert first["number"] == "1001" and first["dictations"] == 1 and first["transferred"] == 1


def test_delete_patient_and_dictation(logged_in: TestClient, settings: Settings) -> None:
    put(logged_in, "diktat-0001", "4711")
    put(logged_in, "diktat-0002")
    patient_id = by_number(logged_in, "4711")["id"]
    assert logged_in.delete(f"{PATIENTS}/{patient_id}").status_code == 204
    assert logged_in.get(f"{PATIENTS}/{patient_id}").status_code == 404
    assert logged_in.delete(f"{PATIENTS}/{patient_id}").status_code == 404
    assert logged_in.delete(f"{DICTATIONS}/diktat-0002").status_code == 204
    assert logged_in.delete(f"{DICTATIONS}/diktat-0002").status_code == 404
    with sqlite3.connect(settings.db_path) as conn:
        assert conn.execute("SELECT count(*) FROM dictations").fetchone()[0] == 0
    # Eine neue Nummer bekommt nie die ID des gelöschten Patienten.
    assert logged_in.post(PATIENTS, json={"number": "4712"}).json()["id"] != patient_id


def test_logs_without_transcript_or_number(logged_in: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    saved = put(logged_in, "diktat-0001", "987654", transcript="Vertraulicher Befund")
    logged_in.post(
        f"{PATIENTS}/{saved['patient_id']}/transferred", json={"seen": [{"id": saved["id"], "revision": saved["revision"]}]}
    )
    assert "Diktat gespeichert" in caplog.text
    assert "Vertraulicher" not in caplog.text and "987654" not in caplog.text


def test_invalid_dictation_rejected(logged_in: TestClient) -> None:
    assert logged_in.put(f"{DICTATIONS}/kurz", json=DICTATION).status_code == 422
    assert logged_in.put(f"{DICTATIONS}/diktat-0001", json={**DICTATION, "patient_type": "gesetzlich"}).status_code == 422
    assert logged_in.put(f"{DICTATIONS}/diktat-0001", json={**DICTATION, "suggestions": [{"code": "13c"}]}).status_code == 422
