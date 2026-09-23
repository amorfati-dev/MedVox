"""Aufbewahrung der Patientendiktate: bis „übertragen“, spätestens 24 Stunden nach Anlage.

Aufgeräumt wird wie beim Kurzcode-Transfer: bei jedem Schreiben und Lesen, beim Start und periodisch.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from medvox import db, patients
from medvox.main import create_app
from medvox.settings import Settings

DAY = patients.RETENTION_S
DATA = {"transcript": "Zahn 36 mod", "patient_type": "kasse", "codes": ["13c"]}


@pytest.fixture
def db_path(settings: Settings) -> Path:
    db.init_db(settings.db_path)
    return settings.db_path


def stored(db_path: Path) -> tuple[list[str], list[str]]:
    """(Diktat-IDs, Patientennummern) direkt aus der Datei, ohne Aufräumen."""
    with sqlite3.connect(db_path) as conn:
        dictations = [r[0] for r in conn.execute("SELECT id FROM dictations ORDER BY id")]
        numbers = [r[0] for r in conn.execute("SELECT number FROM patients ORDER BY number")]
    return dictations, numbers


def test_forgotten_dictation_disappears_after_24_hours(settings: Settings, logged_in: TestClient) -> None:
    db_path = settings.db_path
    now = time.time()
    patients.save_dictation(db_path, "vergessen-1", DATA, "4711", now=now - DAY - 1)  # gestern früh, nie übertragen
    patients.save_dictation(db_path, "ohne-pat-1", DATA, None, now=now - DAY - 1)
    patients.save_dictation(db_path, "heute-0001", DATA, "4712", now=now - DAY + 60)  # 23:59 h alt: bleibt
    assert stored(db_path)[0] == ["heute-0001", "ohne-pat-1", "vergessen-1"]

    listing = logged_in.get("/api/v1/patients").json()  # Lesen räumt auf
    assert [p["number"] for p in listing["patients"]] == ["4712"] and listing["unassigned"] == []
    assert stored(db_path) == (["heute-0001"], ["4712"])


def test_change_does_not_extend_the_24_hours(db_path: Path) -> None:
    t0 = time.time() - DAY - 1
    patients.save_dictation(db_path, "diktat-0001", DATA, "4711", now=t0)
    patients.save_dictation(db_path, "diktat-0001", {**DATA, "transcript": "ergänzt"}, "4711", now=t0 + DAY - 60)
    assert patients.list_patients(db_path) == ([], [])
    assert stored(db_path) == ([], [])


def test_patient_lives_as_long_as_its_newest_dictation(db_path: Path) -> None:
    t0 = time.time()
    patients.create_patient(db_path, "4711", now=t0)
    patients.save_dictation(db_path, "morgens-01", DATA, "4711", now=t0)
    patients.save_dictation(db_path, "abends-001", DATA, "4711", now=t0 + 10 * 3600)

    found = patients.get_patient(db_path, patients.create_patient(db_path, "4711", now=t0 + DAY + 1).id, now=t0 + DAY + 1)
    assert found is not None and [d.id for d in found[1]] == ["abends-001"]  # das Morgendiktat ist weg
    patients.list_patients(db_path, now=t0 + 10 * 3600 + DAY + 1)
    assert stored(db_path) == ([], [])


def test_transferred_marker_expires_too(db_path: Path) -> None:
    t0 = time.time()
    saved = patients.save_dictation(db_path, "diktat-0001", DATA, "4711", now=t0)
    assert saved.patient_id is not None
    patients.mark_transferred(db_path, saved.patient_id, {saved.id: saved.revision}, now=t0 + 60)
    assert stored(db_path) == ([], ["4711"])  # Inhalt sofort weg, nur Nummer und Zeiten bleiben
    patients.list_patients(db_path, now=t0 + DAY + 1)
    assert stored(db_path) == ([], [])


def test_writing_purges_expired(db_path: Path) -> None:
    patients.save_dictation(db_path, "alt-000001", DATA, "4711", now=time.time() - DAY - 1)
    patients.save_dictation(db_path, "neu-000001", DATA, "4712")
    assert stored(db_path) == (["neu-000001"], ["4712"])


def _expired_rows(db_path: Path) -> None:
    db.init_db(db_path)
    patients.save_dictation(db_path, "wochenende", DATA, "4711", now=time.time() - 3 * DAY)
    patients.save_dictation(db_path, "ohne-wochenende", DATA, None, now=time.time() - 3 * DAY)


def test_expired_rows_are_purged_at_startup(settings: Settings) -> None:
    # Über das Wochenende liegen gebliebene Diktate (abgelaufen, ohne weiteren Zugriff).
    _expired_rows(settings.db_path)
    assert stored(settings.db_path) == (["ohne-wochenende", "wochenende"], ["4711"])
    app = create_app(settings, transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    with TestClient(app):
        assert stored(settings.db_path) == ([], [])


def test_periodic_sweep_purges_without_requests(settings: Settings) -> None:
    quick = replace(settings, purge_interval_s=0.05)
    app = create_app(quick, transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    with TestClient(app):
        _expired_rows(quick.db_path)
        deadline = time.time() + 3.0
        while stored(quick.db_path) != ([], []) and time.time() < deadline:
            time.sleep(0.05)
        assert stored(quick.db_path) == ([], [])


def test_existing_database_gets_patient_tables(settings: Settings) -> None:
    # Installierte Datenbank von vor den Patientendiktaten: nur Sitzungen und Transfers.
    db_path = settings.db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE sessions (token TEXT PRIMARY KEY, created_at REAL NOT NULL, expires_at REAL NOT NULL)")
    db.init_db(db_path)
    db.init_db(db_path)  # idempotent
    patients.save_dictation(db_path, "diktat-0001", DATA, "4711")
    assert stored(db_path) == (["diktat-0001"], ["4711"])
