"""Ein übertragenes, gelöschtes oder abgelaufenes Diktat kommt nie wieder – auch nicht über den Kurzcode.

Das iPad speichert nach jeder Änderung erneut (PUT); ohne Grabstein legte ein solcher Aufruf das
schon übertragene Diktat als offen neu an, und es ginge ein zweites Mal nach Evident.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from fastapi.testclient import TestClient

from medvox import db, patients
from medvox.settings import Settings

PATIENTS = "/api/v1/patients"
DICTATIONS = "/api/v1/dictations"
TRANSFER = "/api/v1/transfer"
DICTATION = {"transcript": "Zahn 36 mod Geheimbefund.", "patient_type": "kasse", "codes": ["13c"]}


def put(client: TestClient, did: str, patient: str | None = None, **fields):
    body = {**DICTATION, **fields, **({"patient": patient} if patient else {})}
    return client.put(f"{DICTATIONS}/{did}", json=body)


def patient(client: TestClient, number: str) -> dict:
    return next(p for p in client.get(PATIENTS).json()["patients"] if p["number"] == number)


def tombstones(db_path: Path) -> list[tuple]:
    with sqlite3.connect(db_path) as conn:
        return conn.execute("SELECT * FROM dictation_tombstones ORDER BY id").fetchall()


def open_dictations(db_path: Path) -> list[str]:
    with sqlite3.connect(db_path) as conn:
        return [r[0] for r in conn.execute("SELECT id FROM dictations ORDER BY id")]


def test_put_after_transfer_is_refused(logged_in: TestClient, settings: Settings) -> None:
    put(logged_in, "diktat-0001")  # ohne Patient gespeichert
    pid = logged_in.post(PATIENTS, json={"number": "4711"}).json()["id"]
    moved = logged_in.post(f"{PATIENTS}/{pid}/dictations", json={"dictation_id": "diktat-0001"}).json()
    seen = [{"id": moved["id"], "revision": moved["revision"]}]
    assert logged_in.post(f"{PATIENTS}/{pid}/transferred", json={"seen": seen}).status_code == 200

    # Am iPad danach die Nummer nachgetragen: das Diktat darf nicht wieder offen erscheinen.
    again = put(logged_in, "diktat-0001", "4711")
    assert again.status_code == 410 and "bereits übertragen" in again.json()["detail"]
    assert open_dictations(settings.db_path) == []
    assert patient(logged_in, "4711")["dictations"] == 0 and patient(logged_in, "4711")["transferred"] == 1


def test_put_after_delete_is_refused(logged_in: TestClient, settings: Settings) -> None:
    put(logged_in, "diktat-0001")
    put(logged_in, "diktat-0002", "4711")
    assert logged_in.delete(f"{DICTATIONS}/diktat-0001").status_code == 204
    assert logged_in.delete(f"{PATIENTS}/{patient(logged_in, '4711')['id']}").status_code == 204
    assert put(logged_in, "diktat-0001").status_code == 410
    assert put(logged_in, "diktat-0002", "4711").status_code == 410
    assert open_dictations(settings.db_path) == []


def test_put_after_24_hours_is_refused(settings: Settings) -> None:
    db.init_db(settings.db_path)
    t0 = time.time() - patients.RETENTION_S - 1
    patients.save_dictation(settings.db_path, "gestern-01", DICTATION, "4711", now=t0)
    patients.list_patients(settings.db_path)  # Aufräumen macht einen Grabstein daraus
    try:
        patients.save_dictation(settings.db_path, "gestern-01", DICTATION, "4711")
    except patients.DictationClosed:
        pass
    else:
        raise AssertionError("abgelaufenes Diktat wurde neu angelegt")
    assert open_dictations(settings.db_path) == []


def test_tombstone_holds_no_content_and_expires(logged_in: TestClient, settings: Settings) -> None:
    saved = put(logged_in, "diktat-0001", "987654").json()
    seen = [{"id": saved["id"], "revision": saved["revision"]}]
    logged_in.post(f"{PATIENTS}/{saved['patient_id']}/transferred", json={"seen": seen})
    ((did, closed_at),) = tombstones(settings.db_path)  # nur ID und Zeitpunkt
    assert did == "diktat-0001" and closed_at <= time.time()
    with sqlite3.connect(settings.db_path) as conn:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    raw = settings.db_path.read_bytes()
    assert b"Geheimbefund" not in raw

    patients.list_patients(settings.db_path, now=time.time() + db.TOMBSTONE_S + 1)
    assert tombstones(settings.db_path) == []


def test_ipad_save_keeps_office_reassignment(logged_in: TestClient) -> None:
    saved = put(logged_in, "diktat-0001", "4711").json()
    other = logged_in.post(PATIENTS, json={"number": "4712"}).json()["id"]
    logged_in.post(f"{PATIENTS}/{other}/dictations", json={"dictation_id": "diktat-0001"})

    # Das iPad speichert weiter mit der alten Nummer (z. B. eine Ziffer abgewählt).
    again = put(logged_in, "diktat-0001", "4711", deselected=["13c"])
    assert again.status_code == 200 and again.json()["patient"] == "4712"
    assert again.json()["revision"] == saved["revision"] + 2
    assert patient(logged_in, "4711")["dictations"] == 0 and patient(logged_in, "4712")["dictations"] == 1


def test_short_code_fetch_closes_the_saved_dictation(logged_in: TestClient, settings: Settings) -> None:
    put(logged_in, "diktat-0001", "4711")
    code = logged_in.post(
        TRANSFER, json={"transcript": DICTATION["transcript"], "codes": ["36,13c"], "dictation_id": "diktat-0001"}
    ).json()["code"]
    assert patient(logged_in, "4711")["dictations"] == 1  # noch nicht abgerufen: bleibt offen

    reception = TestClient(logged_in.app)
    for _ in range(2):  # der Abruf bleibt innerhalb der TTL wiederholbar
        read = reception.get(f"{TRANSFER}/{code}")
        assert read.status_code == 200 and read.json()["transcript"] == DICTATION["transcript"]

    assert open_dictations(settings.db_path) == []
    assert [t[0] for t in tombstones(settings.db_path)] == ["diktat-0001"]
    state = patient(logged_in, "4711")
    assert state["dictations"] == 0 and state["transferred"] == 1 and state["transferred_at"]
    assert put(logged_in, "diktat-0001", "4711").status_code == 410


def test_short_code_fetched_before_the_ipad_saved(logged_in: TestClient, settings: Settings) -> None:
    # Speichern hing noch (WLAN), die Rezeption hat den Code schon abgerufen.
    code = logged_in.post(TRANSFER, json={"transcript": "x", "dictation_id": "diktat-0001"}).json()["code"]
    assert TestClient(logged_in.app).get(f"{TRANSFER}/{code}").status_code == 200
    assert put(logged_in, "diktat-0001").status_code == 410
    assert logged_in.get(PATIENTS).json()["unassigned"] == []


def test_unfetched_short_code_leaves_the_dictation_open(logged_in: TestClient) -> None:
    put(logged_in, "diktat-0001")
    logged_in.post(TRANSFER, json={"transcript": "x", "dictation_id": "diktat-0001"})
    logged_in.post(TRANSFER, json={"transcript": "ohne Verknüpfung (ältere iPad-Version)"})
    assert [d["id"] for d in logged_in.get(PATIENTS).json()["unassigned"]] == ["diktat-0001"]
    assert put(logged_in, "diktat-0001", transcript="ergänzt").status_code == 200
