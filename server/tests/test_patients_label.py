"""Kürzel (Initialen) zur Evident-Nummer: optional, bereinigt, nie in Logs, weg mit dem Inhalt."""

from __future__ import annotations

import logging
import sqlite3
import time

import pytest
from fastapi.testclient import TestClient

from medvox import patients
from medvox.settings import Settings

PATIENTS = "/api/v1/patients"
DICTATIONS = "/api/v1/dictations"
TRANSFER = "/api/v1/transfer"
DICTATION = {"transcript": "Zahn 36 mod Karies.", "patient_type": "kasse", "codes": ["13c"]}
DAY = 24 * 3600


def put(client: TestClient, did: str, patient: str | None = None, label: str | None = None, **fields) -> dict:
    body = {**DICTATION, **fields, **({"patient": patient} if patient else {})}
    if label is not None:
        body["patient_label"] = label
    response = client.put(f"{DICTATIONS}/{did}", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def by_number(client: TestClient, number: str) -> dict:
    return next(p for p in client.get(PATIENTS).json()["patients"] if p["number"] == number)


def done(client: TestClient, saved: dict) -> dict:
    seen = [{"id": saved["id"], "revision": saved["revision"]}]
    return client.post(f"{PATIENTS}/{saved['patient_id']}/transferred", json={"seen": seen}).json()


def test_label_is_optional(logged_in: TestClient) -> None:
    put(logged_in, "diktat-0001", "4711")
    assert by_number(logged_in, "4711")["label"] is None
    assert logged_in.post(PATIENTS, json={"number": "4712"}).json()["label"] is None
    put(logged_in, "diktat-0002", "4713", "   ")
    assert by_number(logged_in, "4713")["label"] is None


def test_label_saved_with_the_dictation(logged_in: TestClient) -> None:
    saved = put(logged_in, "diktat-0001", "4711", "M.K.")
    assert saved["patient_label"] == "M.K."
    assert "patient_label" not in saved["codes"] and saved["codes"] == ["13c"]  # nie in den Kopierzeilen
    patient = by_number(logged_in, "4711")
    assert patient["label"] == "M.K."
    item = logged_in.get(f"{PATIENTS}/{patient['id']}").json()["items"][0]
    assert item["patient_label"] == "M.K." and item["patient"] == "4711"


def test_label_kept_without_one(logged_in: TestClient) -> None:
    put(logged_in, "diktat-0000", "4711", "A. S.")
    put(logged_in, "diktat-0001", "4711")  # Nummer am Tastenfeld ohne Kürzel: bleibt
    assert by_number(logged_in, "4711")["label"] == "A. S."
    put(logged_in, "diktat-0002", "4711", "A.S.")  # neues Kürzel ersetzt das alte
    assert by_number(logged_in, "4711")["label"] == "A.S."


def test_label_follows_the_unassigned_dictation(logged_in: TestClient) -> None:
    put(logged_in, "diktat-0001")
    assert logged_in.get(PATIENTS).json()["unassigned"][0]["patient_label"] is None
    put(logged_in, "diktat-0001", "4711", "M.K.")  # Nummer und Kürzel nachgetragen
    assert by_number(logged_in, "4711")["label"] == "M.K."


@pytest.mark.parametrize(
    ("raw", "stored"),
    [
        ("MK", "MK"),
        ("  m.k.  ", "m.k."),
        ("M.  K.", "M. K."),
        ("A-B.", "A-B."),
        ("Ö.-Ü.", "Ö.-Ü."),
        ("U\u0308.", "Ü."),
        ("A. B. C. D.", "A. B. C. D."),
        ("AB-CD", "AB-CD"),
    ],
)
def test_label_accepts_initials(logged_in: TestClient, raw: str, stored: str) -> None:
    saved = put(logged_in, "diktat-0001", "4711", raw)
    assert saved["patient_label"] == stored


@pytest.mark.parametrize(
    "raw", ["Max", "Muel", "Mueller", "Max Musterma", "A.B.C.D.E.", "A-BCD", "M.K. 1980", "M..K.", "M--K", ".MK", "<b>", "123"]
)
def test_label_rejects_anything_but_initials(logged_in: TestClient, raw: str) -> None:
    response = logged_in.put(f"{DICTATIONS}/diktat-0001", json={**DICTATION, "patient": "4711", "patient_label": raw})
    assert response.status_code == 422 and raw not in response.text
    assert logged_in.get(PATIENTS).json()["patients"] == []  # nichts gespeichert


def test_label_set_when_office_assigns_to_transferred_patient(logged_in: TestClient) -> None:
    done(logged_in, put(logged_in, "diktat-0001", "4711", "M.K."))
    loose = put(logged_in, "diktat-0002")
    patient = logged_in.post(PATIENTS, json={"number": "4711"}).json()
    body = {"dictation_id": loose["id"], "label": "M. K."}
    moved = logged_in.post(f"{PATIENTS}/{patient['id']}/dictations", json=body).json()
    assert moved["patient_label"] == "M. K."
    assert by_number(logged_in, "4711")["label"] == "M. K."
    body["label"] = "Mueller"
    rejected = logged_in.post(f"{PATIENTS}/{patient['id']}/dictations", json=body)
    assert rejected.status_code == 422 and "Mueller" not in rejected.text


def test_label_gone_after_transfer(logged_in: TestClient, settings: Settings) -> None:
    saved = put(logged_in, "diktat-0001", "4711", "G.K.")
    after = done(logged_in, saved)
    assert after["label"] is None and after["transferred"] == 1
    assert by_number(logged_in, "4711")["label"] is None
    with sqlite3.connect(settings.db_path) as conn:
        assert conn.execute("SELECT label FROM patients").fetchall() == [(None,)]


def test_label_stays_while_something_is_open(logged_in: TestClient) -> None:
    first = put(logged_in, "diktat-0001", "4711", "M.K.")
    put(logged_in, "diktat-0002", "4711", "M.K.")
    assert done(logged_in, first)["label"] == "M.K."  # zweites Diktat noch offen


def test_label_gone_after_code_fetch(logged_in: TestClient) -> None:
    saved = put(logged_in, "diktat-0001", "4711", "M.K.")
    body = {"transcript": DICTATION["transcript"], "codes": ["36,13c"], "dictation_id": "diktat-0001"}
    code = logged_in.post(TRANSFER, json={**body, "dictation_revision": saved["revision"]}).json()["code"]
    read = TestClient(logged_in.app).get(f"{TRANSFER}/{code}")
    assert read.status_code == 200 and "M.K." not in read.text
    assert by_number(logged_in, "4711")["label"] is None


def test_label_expires_with_the_patient(logged_in: TestClient, settings: Settings) -> None:
    t0 = time.time() - DAY - 60
    patients.save_dictation(settings.db_path, "gestern-01", DICTATION, "4711", now=t0, label="M.K.")
    found, _ = patients.list_patients(settings.db_path)
    assert found == []
    with sqlite3.connect(settings.db_path) as conn:
        assert conn.execute("SELECT count(*) FROM patients WHERE label IS NOT NULL").fetchone()[0] == 0


def test_logs_without_label(logged_in: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    saved = put(logged_in, "diktat-0001", "987654", "Z.X.")
    done(logged_in, saved)
    assert "Diktat gespeichert" in caplog.text and "Z.X." not in caplog.text
