"""Kurzcode und Patientenliste: genau ein Stand eines Diktats wird übergeben, genau einmal.

Das iPad nennt beim Anlegen des Kurzcodes das gespeicherte Diktat und dessen Revision. Der erste
Abruf schließt genau diesen Stand; ein danach geänderter bleibt offen (mit Vermerk), ein schon
übertragener gibt nichts mehr heraus.
"""

from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient

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
    assert item["adopted"] == ["2100@36"] and item["handed_over_at"]  # offen, mit Vermerk
    assert item["revision"] > changed["revision"]  # was das Büro vorher sah, gilt nicht mehr
    assert patient(logged_in, "4711")["dictations"] == 1 and tombstones(settings.db_path) == []

    again = put(logged_in, "diktat-0001", "4711", adopted=["2100@36"], deselected=["13c"])
    assert again.status_code == 200 and again.json()["handed_over_at"]  # weiter speicherbar
    seen = [{"id": "diktat-0001", "revision": again.json()["revision"]}]
    done = logged_in.post(f"{PATIENTS}/{again.json()['patient_id']}/transferred", json={"seen": seen}).json()
    assert done["items"] == [] and done["transferred"] == 1  # im Büro wie gewohnt abschließbar


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
