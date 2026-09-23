"""Kurzcode und Patientenliste: genau ein Stand eines Diktats wird übergeben, genau einmal.

Das iPad nennt beim Anlegen des Kurzcodes das gespeicherte Diktat und dessen Revision. Der erste
Abruf schließt genau diesen Stand; ein danach geänderter bleibt offen (mit Vermerk), ein schon
übertragener gibt nichts mehr heraus.
"""

from __future__ import annotations

import sqlite3
import time

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


def items(client: TestClient, number: str) -> list[dict]:
    return client.get(f"{PATIENTS}/{patient(client, number)['id']}").json()["items"]


def code_for(client: TestClient, saved: dict | None, did: str = "diktat-0001", codes: list[str] | None = None) -> str:
    body = {"transcript": DICTATION["transcript"], "codes": codes or ["36,13c"], "dictation_id": did}
    if saved is not None:
        body["dictation_revision"] = saved["revision"]
    return client.post(TRANSFER, json=body).json()["code"]


def fetched(db_path) -> list[tuple]:
    with sqlite3.connect(db_path) as conn:
        return conn.execute("SELECT dictation_id, codes_json FROM handovers ORDER BY fetched_at").fetchall()


def tombstones(db_path) -> list[str]:
    with sqlite3.connect(db_path) as conn:
        return [r[0] for r in conn.execute("SELECT id FROM dictation_tombstones ORDER BY id")]


def test_fetch_closes_the_unchanged_dictation(logged_in: TestClient, settings: Settings) -> None:
    saved = put(logged_in, "diktat-0001", "4711").json()
    code = code_for(logged_in, saved)
    assert patient(logged_in, "4711")["dictations"] == 1  # noch nicht abgerufen: bleibt offen

    reception = TestClient(logged_in.app)
    for _ in range(2):  # der Abruf bleibt innerhalb der TTL wiederholbar
        read = reception.get(f"{TRANSFER}/{code}")
        assert read.status_code == 200 and read.json()["transcript"] == DICTATION["transcript"]
        assert read.json()["codes"] == ["36,13c"]

    assert tombstones(settings.db_path) == ["diktat-0001"]
    state = patient(logged_in, "4711")
    assert state["dictations"] == 0 and state["transferred"] == 1 and state["transferred_at"]
    assert put(logged_in, "diktat-0001", "4711").status_code == 410


def test_changed_after_the_code_stays_open_with_a_note(logged_in: TestClient, settings: Settings) -> None:
    # Code gezeigt, danach am iPad eine Zuzahlungs-Option übernommen (neue Revision), dann Abruf.
    saved = put(logged_in, "diktat-0001", "4711").json()
    code = code_for(logged_in, saved, codes=["36,13c"])
    changed = put(logged_in, "diktat-0001", "4711", adopted=["2100@36"]).json()
    assert changed["revision"] == saved["revision"] + 1

    read = TestClient(logged_in.app).get(f"{TRANSFER}/{code}")
    assert read.status_code == 200 and read.json()["codes"] == ["36,13c"]  # der Stand des Codes

    (item,) = items(logged_in, "4711")
    assert item["adopted"] == ["2100@36"]  # offen, mit der Abholung für das Büro
    assert [h["codes"] for h in item["handovers"]] == [["36,13c"]] and item["handovers"][0]["fetched_at"]
    assert item["revision"] > changed["revision"]  # was das Büro vorher sah, gilt nicht mehr
    assert patient(logged_in, "4711")["dictations"] == 1 and tombstones(settings.db_path) == []

    again = put(logged_in, "diktat-0001", "4711", adopted=["2100@36"], deselected=["13c"])
    assert again.status_code == 200 and len(again.json()["handovers"]) == 1  # weiter speicherbar
    seen = [{"id": "diktat-0001", "revision": again.json()["revision"]}]
    done = logged_in.post(f"{PATIENTS}/{again.json()['patient_id']}/transferred", json={"seen": seen}).json()
    assert done["items"] == [] and done["transferred"] == 1  # im Büro wie gewohnt abschließbar


def test_second_code_after_the_correction_closes_it(logged_in: TestClient, settings: Settings) -> None:
    # Code A, danach korrigiert, A abgeholt (Korrektur bleibt offen); dann Code B für die Korrektur.
    saved = put(logged_in, "diktat-0001", "4711").json()
    code_a = code_for(logged_in, saved, codes=["36,13c"])
    changed = put(logged_in, "diktat-0001", "4711", adopted=["2100@36"]).json()
    reception = TestClient(logged_in.app)
    assert reception.get(f"{TRANSFER}/{code_a}").status_code == 200
    assert patient(logged_in, "4711")["dictations"] == 1

    code_b = code_for(logged_in, changed, codes=["36,13c,2100"])  # Revision, die das iPad kennt
    for _ in range(2):  # auch beim erneuten Abruf bleibt der Hinweis
        read = reception.get(f"{TRANSFER}/{code_b}")
        assert read.status_code == 200 and read.json()["codes"] == ["36,13c,2100"]
        (earlier,) = read.json()["earlier"]  # die Rezeption sieht, was A schon übergeben hat
        assert earlier["codes"] == ["36,13c"] and earlier["fetched_at"].endswith("+00:00")
    assert reception.get(f"{TRANSFER}/{code_a}").json()["earlier"] == []  # A war die erste Abholung
    state = patient(logged_in, "4711")
    assert state["dictations"] == 0 and state["transferred"] == 1
    assert tombstones(settings.db_path) == ["diktat-0001"]
    assert fetched(settings.db_path) == [("diktat-0001", '["36,13c"]'), ("diktat-0001", '["36,13c,2100"]')]

    # Die Abholungen bleiben mit dem Grabstein und gehen mit ihm.
    patients.list_patients(settings.db_path, now=time.time() + db.TOMBSTONE_S + 1)
    assert fetched(settings.db_path) == [] and tombstones(settings.db_path) == []


def test_single_code_has_no_earlier_handover(logged_in: TestClient) -> None:
    saved = put(logged_in, "diktat-0001", "4711").json()
    read = TestClient(logged_in.app).get(f"{TRANSFER}/{code_for(logged_in, saved)}")
    assert read.status_code == 200 and read.json()["earlier"] == []
    plain = logged_in.post(TRANSFER, json={"transcript": "ohne Verknüpfung"}).json()["code"]
    assert TestClient(logged_in.app).get(f"{TRANSFER}/{plain}").json()["earlier"] == []


def test_code_after_office_reassignment_still_closes(logged_in: TestClient) -> None:
    saved = put(logged_in, "diktat-0001", "4711").json()
    code = code_for(logged_in, saved)
    other = logged_in.post(PATIENTS, json={"number": "4712"}).json()["id"]
    logged_in.post(f"{PATIENTS}/{other}/dictations", json={"dictation_id": "diktat-0001"})  # Inhalt unverändert
    assert TestClient(logged_in.app).get(f"{TRANSFER}/{code}").status_code == 200
    assert patient(logged_in, "4712")["dictations"] == 0 and patient(logged_in, "4712")["transferred"] == 1


def test_code_after_office_transfer_is_refused(logged_in: TestClient) -> None:
    saved = put(logged_in, "diktat-0001", "4711").json()
    code = code_for(logged_in, saved)
    seen = [{"id": saved["id"], "revision": saved["revision"]}]
    assert logged_in.post(f"{PATIENTS}/{saved['patient_id']}/transferred", json={"seen": seen}).status_code == 200

    reception = TestClient(logged_in.app)
    read = reception.get(f"{TRANSFER}/{code}")
    assert read.status_code == 410
    body = read.json()
    assert set(body) == {"detail"}  # nichts Abrechenbares
    assert "bereits am" in body["detail"] and "Uhr" in body["detail"] and "nicht erneut in Evident" in body["detail"]
    assert "Geheimbefund" not in read.text and "13c" not in read.text
    assert reception.get(f"{TRANSFER}/{code}").status_code == 404  # Code ist verbraucht


def test_second_code_for_the_same_dictation_is_refused(logged_in: TestClient) -> None:
    saved = put(logged_in, "diktat-0001", "4711").json()
    first, second = code_for(logged_in, saved), code_for(logged_in, saved)
    reception = TestClient(logged_in.app)
    assert reception.get(f"{TRANSFER}/{first}").status_code == 200
    assert reception.get(f"{TRANSFER}/{second}").status_code == 410
    assert reception.get(f"{TRANSFER}/{first}").status_code == 200  # der abgeholte bleibt lesbar


def test_code_fetched_before_the_ipad_saved(logged_in: TestClient) -> None:
    # Speichern hing noch (WLAN), die Rezeption hat den Code schon abgerufen.
    code = code_for(logged_in, None)
    assert TestClient(logged_in.app).get(f"{TRANSFER}/{code}").status_code == 200
    assert put(logged_in, "diktat-0001").status_code == 410
    assert logged_in.get(PATIENTS).json()["unassigned"] == []


def test_unfetched_code_leaves_the_dictation_open(logged_in: TestClient) -> None:
    saved = put(logged_in, "diktat-0001").json()
    code_for(logged_in, saved)
    logged_in.post(TRANSFER, json={"transcript": "ohne Verknüpfung (ältere iPad-Version)"})
    assert [d["id"] for d in logged_in.get(PATIENTS).json()["unassigned"]] == ["diktat-0001"]
    assert put(logged_in, "diktat-0001", transcript="ergänzt").status_code == 200
