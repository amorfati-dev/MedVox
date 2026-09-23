"""Behandler: Liste pflegen, Diktate beim Start der Aufnahme zuordnen, Pilotdaten ohne Behandler.

Gemeinschaftspraxis: jeder sieht alle Patienten, der Behandler ist nur Zuordnung. Ein Diktat behält
den Behandler seines ersten Speicherns, auch wenn das iPad danach auf jemand anderen wechselt.
"""

from __future__ import annotations

import dataclasses
import re
import sqlite3
import time

import httpx
from fastapi.testclient import TestClient

from medvox import db
from medvox.main import create_app
from medvox.settings import Settings

DENTISTS = "/api/v1/dentists"
PATIENTS = "/api/v1/patients"
DICTATIONS = "/api/v1/dictations"
TRANSFER = "/api/v1/transfer"
DICTATION = {"transcript": "Zahn 36 mod Karies.", "patient_type": "kasse", "codes": ["13c"]}


def add(client: TestClient, name: str, **fields) -> dict:
    response = client.post(DENTISTS, json={"name": name, **fields})
    assert response.status_code == 200, response.text
    return response.json()


def put(client: TestClient, did: str, patient: str | None = None, dentist: int | None = None, **fields) -> dict:
    body = {**DICTATION, **fields, **({"patient": patient} if patient else {})}
    if dentist is not None:
        body["dentist_id"] = dentist
    response = client.put(f"{DICTATIONS}/{did}", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def patient(client: TestClient, number: str) -> dict:
    return next(p for p in client.get(PATIENTS).json()["patients"] if p["number"] == number)


def items(client: TestClient, number: str) -> list[dict]:
    return client.get(f"{PATIENTS}/{patient(client, number)['id']}").json()["items"]


def test_roster_requires_login(client: TestClient) -> None:
    assert client.get(DENTISTS).status_code == 401
    assert client.post(DENTISTS, json={"name": "Dr. Hartmann"}).status_code == 401
    assert client.patch(f"{DENTISTS}/1", json={"name": "x"}).status_code == 401
    assert client.delete(f"{DENTISTS}/1").status_code == 401


def test_new_database_is_seeded_with_one_dentist_and_idle_setting(logged_in: TestClient) -> None:
    listing = logged_in.get(DENTISTS).json()
    assert [(d["name"], d["active"]) for d in listing["dentists"]] == [(db.FIRST_DENTIST, True)]
    assert listing["idle_s"] == 30 * 60  # Voreinstellung: nach 30 Minuten neu fragen


def test_idle_setting_comes_from_settings(settings: Settings, whisper) -> None:
    custom = dataclasses.replace(settings, dentist_idle_s=600)
    with TestClient(create_app(custom, transport=httpx.MockTransport(whisper))) as tc:
        tc.post("/api/v1/login", json={"password": "praxis-geheim"})
        assert tc.get(DENTISTS).json()["idle_s"] == 600


def test_add_edit_deactivate_and_reactivate(logged_in: TestClient) -> None:
    created = add(logged_in, "  Dr. Hartmann ", practitioner_id="12")
    assert created["name"] == "Dr. Hartmann" and created["practitioner_id"] == "12" and created["active"]
    edited = logged_in.patch(f"{DENTISTS}/{created['id']}", json={"name": "Dr. B. Hartmann", "practitioner_id": ""})
    assert edited.status_code == 200
    assert edited.json()["name"] == "Dr. B. Hartmann" and edited.json()["practitioner_id"] is None
    gone = logged_in.delete(f"{DENTISTS}/{created['id']}")
    assert gone.status_code == 200 and gone.json()["active"] is False
    listing = logged_in.get(DENTISTS).json()["dentists"]
    assert listing[-1]["id"] == created["id"] and not listing[-1]["active"]  # bleibt, aktive zuerst
    back = logged_in.patch(f"{DENTISTS}/{created['id']}", json={"active": True})
    assert back.json()["active"] is True


def test_roster_validation(logged_in: TestClient) -> None:
    assert logged_in.post(DENTISTS, json={"name": "   "}).status_code == 422
    assert logged_in.post(DENTISTS, json={"name": "x" * 61}).status_code == 422
    assert logged_in.post(DENTISTS, json={"name": "Dr. A", "practitioner_id": "1; drop"}).status_code == 422
    assert logged_in.patch(f"{DENTISTS}/1", json={"name": None}).status_code == 422
    assert logged_in.patch(f"{DENTISTS}/999", json={"name": "x"}).status_code == 404
    assert logged_in.delete(f"{DENTISTS}/999").status_code == 404


def test_dictation_keeps_dentist_from_its_first_save(logged_in: TestClient) -> None:
    a, b = add(logged_in, "Dr. A")["id"], add(logged_in, "Dr. B")["id"]
    first = put(logged_in, "diktat-0001", "4711", dentist=a)
    assert first["dentist_id"] == a and first["dentist_name"] == "Dr. A"
    # Das iPad wechselt auf Dr. B; ein späteres Speichern desselben Diktats ändert nichts.
    again = put(logged_in, "diktat-0001", "4711", dentist=b, transcript="ergänzt")
    assert again["dentist_id"] == a and again["transcript"] == "ergänzt"
    unset = put(logged_in, "diktat-0001", "4711", transcript="ohne Angabe")
    assert unset["dentist_id"] == a


def test_device_switch_does_not_rewrite_past_dictations(logged_in: TestClient) -> None:
    a, b = add(logged_in, "Dr. A")["id"], add(logged_in, "Dr. B")["id"]
    put(logged_in, "diktat-0001", "4711", dentist=a)
    put(logged_in, "diktat-0002", "4711", dentist=b)  # Kollege übernimmt das iPad beim selben Patienten
    put(logged_in, "diktat-0001", "4711", dentist=b, deselected=["13c"])  # Auswahl am alten Diktat
    assert [d["dentist_name"] for d in items(logged_in, "4711")] == ["Dr. A", "Dr. B"]
    p = patient(logged_in, "4711")
    assert p["dentist_id"] == a and p["dentist_name"] == "Dr. A"  # hat den Patienten eröffnet
    assert [d["name"] for d in p["dentists"]] == ["Dr. A", "Dr. B"]


def test_patient_opener_survives_transfer_and_renaming(logged_in: TestClient) -> None:
    a = add(logged_in, "Dr. A")["id"]
    put(logged_in, "diktat-0001", "4711", dentist=a)
    p = patient(logged_in, "4711")
    seen = [{"id": d["id"], "revision": d["revision"]} for d in items(logged_in, "4711")]
    logged_in.post(f"{PATIENTS}/{p['id']}/transferred", json={"seen": seen})
    logged_in.patch(f"{DENTISTS}/{a}", json={"name": "Dr. A. Neu"})
    logged_in.delete(f"{DENTISTS}/{a}")  # auch inaktiv bleibt die Zuordnung sichtbar
    after = patient(logged_in, "4711")
    assert after["dictations"] == 0 and after["dentist_name"] == "Dr. A. Neu"


def test_list_shows_everyone_and_unassigned_carry_their_dentist(logged_in: TestClient) -> None:
    a, b = add(logged_in, "Dr. A")["id"], add(logged_in, "Dr. B")["id"]
    put(logged_in, "diktat-0001", "4711", dentist=a)
    put(logged_in, "diktat-0002", "4712", dentist=b)
    put(logged_in, "diktat-0003", dentist=b)  # ohne Patient
    listing = logged_in.get(PATIENTS).json()
    assert {p["number"]: p["dentist_name"] for p in listing["patients"]} == {"4711": "Dr. A", "4712": "Dr. B"}
    assert [d["dentist_name"] for d in listing["unassigned"]] == ["Dr. B"]
    # Zuordnen im Büro: der Patient übernimmt den Behandler des Diktats, das Diktat behält ihn.
    new = logged_in.post(PATIENTS, json={"number": "4713"}).json()
    assert new["dentist_id"] is None
    moved = logged_in.post(f"{PATIENTS}/{new['id']}/dictations", json={"dictation_id": "diktat-0003"}).json()
    assert moved["dentist_id"] == b and patient(logged_in, "4713")["dentist_name"] == "Dr. B"


def test_dictation_without_dentist_stays_usable(logged_in: TestClient) -> None:
    saved = put(logged_in, "diktat-0001", "4711")
    assert saved["dentist_id"] is None and saved["dentist_name"] is None
    assert put(logged_in, "diktat-0002", "4711", dentist=999)["dentist_id"] is None  # unbekannt: ohne
    p = patient(logged_in, "4711")
    assert p["dentist_id"] is None and p["dentists"] == []
    code = logged_in.post(
        TRANSFER, json={"transcript": "x", "codes": ["36,13c"], "dictation_id": "diktat-0001", "dictation_revision": 1}
    ).json()["code"]
    assert logged_in.get(f"{TRANSFER}/{code}").json()["dentist_name"] is None
    seen = [{"id": d["id"], "revision": d["revision"]} for d in items(logged_in, "4711")]
    after = logged_in.post(f"{PATIENTS}/{p['id']}/transferred", json={"seen": seen}).json()
    assert after["items"] == []


def test_short_code_names_the_dentist_even_after_it_closed_the_dictation(logged_in: TestClient) -> None:
    a, b = add(logged_in, "Dr. A")["id"], add(logged_in, "Dr. B")["id"]
    saved = put(logged_in, "diktat-0001", "4711", dentist=a)
    body = {"transcript": "x", "codes": ["36,13c"], "dictation_id": "diktat-0001", "dictation_revision": saved["revision"]}
    code = logged_in.post(TRANSFER, json={**body, "dentist_id": b}).json()["code"]  # gespeicherter gilt
    assert logged_in.get(f"{TRANSFER}/{code}").json()["dentist_name"] == "Dr. A"
    assert items(logged_in, "4711") == []  # der Abruf hat das Diktat geschlossen
    assert logged_in.get(f"{TRANSFER}/{code}").json()["dentist_name"] == "Dr. A"
    # Noch nicht gespeichertes Diktat: der vom iPad genannte Behandler.
    early = logged_in.post(TRANSFER, json={"transcript": "y", "codes": [], "dentist_id": b}).json()["code"]
    assert logged_in.get(f"{TRANSFER}/{early}").json()["dentist_name"] == "Dr. B"


def test_pilot_database_without_dentists_keeps_its_data(settings: Settings, whisper) -> None:
    """Eine Datenbank von vor der Behandlerliste: Spalten kommen dazu, nichts geht verloren."""
    old_schema = re.sub(r"-- Behandler der.*?CREATE TABLE IF NOT EXISTS dentists \(.*?\);\n", "", db.SCHEMA, flags=re.S)
    assert "dentists" not in old_schema
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    with sqlite3.connect(settings.db_path) as conn:
        conn.executescript(old_schema)
        conn.execute(
            "INSERT INTO patients (number, created_at, updated_at, expires_at) VALUES ('4711', ?, ?, ?)",
            (now, now, now + 3600),
        )
        conn.execute(
            "INSERT INTO dictations (id, patient_id, created_at, updated_at, expires_at, data_json)"
            " VALUES ('pilot-0001', 1, ?, ?, ?, ?)",
            (now, now, now + 3600, '{"transcript": "Pilot", "patient_type": "kasse", "codes": ["13c"]}'),
        )
    with TestClient(create_app(settings, transport=httpx.MockTransport(whisper))) as tc:
        tc.post("/api/v1/login", json={"password": "praxis-geheim"})
        pilot = items(tc, "4711")
        assert [(d["id"], d["transcript"], d["dentist_id"]) for d in pilot] == [("pilot-0001", "Pilot", None)]
        assert patient(tc, "4711")["dentist_name"] is None
        assert [d["name"] for d in tc.get(DENTISTS).json()["dentists"]] == [db.FIRST_DENTIST]
        # Weiter bearbeitbar; ein nachträglich genannter Behandler ändert das alte Diktat nicht.
        assert put(tc, "pilot-0001", dentist=1, transcript="Pilot ergänzt")["dentist_id"] is None
        assert patient(tc, "4711")["without_dentist"] == 1
        # Im Büro zugeordnet: ab dann fest, auch als Eröffner des Patienten.
        assigned = tc.put(f"{DICTATIONS}/pilot-0001/dentist", json={"dentist_id": 1}).json()
        assert (assigned["transcript"], assigned["dentist_name"]) == ("Pilot ergänzt", db.FIRST_DENTIST)
        assert patient(tc, "4711")["dentist_name"] == db.FIRST_DENTIST
    db.init_db(settings.db_path)  # erneuter Start: kein zweiter Eintrag
    with db.connect(settings.db_path) as conn:
        assert conn.execute("SELECT count(*) FROM dentists").fetchone()[0] == 1


def test_office_assigns_missing_dentist_once_and_fills_the_opener(logged_in: TestClient) -> None:
    a, b = add(logged_in, "Dr. A")["id"], add(logged_in, "Dr. B")["id"]
    put(logged_in, "diktat-0001", "4711")
    put(logged_in, "diktat-0002")  # ohne Patient
    listing = logged_in.get(PATIENTS).json()
    assert listing["unassigned"][0]["dentist_id"] is None
    p = patient(logged_in, "4711")
    assert (p["dentist_id"], p["without_dentist"]) == (None, 1)

    saved = logged_in.put(f"{DICTATIONS}/diktat-0001/dentist", json={"dentist_id": a})
    assert saved.status_code == 200, saved.text
    assert (saved.json()["dentist_id"], saved.json()["dentist_name"]) == (a, "Dr. A")
    p = patient(logged_in, "4711")
    assert (p["dentist_name"], p["without_dentist"], [d["name"] for d in p["dentists"]]) == ("Dr. A", 0, ["Dr. A"])
    assert [d["dentist_name"] for d in items(logged_in, "4711")] == ["Dr. A"]

    again = logged_in.put(f"{DICTATIONS}/diktat-0001/dentist", json={"dentist_id": b})
    assert again.status_code == 409
    assert items(logged_in, "4711")[0]["dentist_id"] == a
    put(logged_in, "diktat-0003", "4712", dentist=b)
    assert logged_in.put(f"{DICTATIONS}/diktat-0003/dentist", json={"dentist_id": a}).status_code == 409
    assert items(logged_in, "4712")[0]["dentist_id"] == b

    assert logged_in.put(f"{DICTATIONS}/diktat-0002/dentist", json={"dentist_id": 999}).status_code == 404
    assert logged_in.put(f"{DICTATIONS}/unbekannt-01/dentist", json={"dentist_id": a}).status_code == 404
    loose = logged_in.put(f"{DICTATIONS}/diktat-0002/dentist", json={"dentist_id": b}).json()
    assert (loose["patient_id"], loose["dentist_name"]) == (None, "Dr. B")


def test_assigning_dentist_requires_login(client: TestClient) -> None:
    assert client.put(f"{DICTATIONS}/diktat-0001/dentist", json={"dentist_id": 1}).status_code == 401
