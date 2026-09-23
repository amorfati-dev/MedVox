"""Live-Aktualisierung des Büros (`medvox/events.py`): nur ein Versionssignal, schnell beim Büro."""

from __future__ import annotations

import asyncio
import dataclasses
import queue
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient

from medvox import db, patients
from medvox.events import ChangeHub
from medvox.main import create_app
from medvox.settings import Settings

from tests.conftest import PASSWORD

EVENTS = "/api/v1/events"
SECRET = "Zahn 36 Karies profunda"


def test_events_require_login(client: TestClient) -> None:
    assert client.get(EVENTS).status_code == 401


def test_stream_carries_only_the_version(settings: Settings) -> None:
    short = dataclasses.replace(settings, events_heartbeat_s=0.05, events_max_s=0.3)
    with TestClient(create_app(short)) as tc:
        assert tc.post("/api/v1/login", json={"password": PASSWORD}).status_code == 204
        response = tc.get(EVENTS)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-store"
    body = response.text
    assert body.startswith("retry: 3000\nevent: changed\ndata: ")
    assert "event: ping\ndata: " in body  # Lebenszeichen, der Strom endet nach events_max_s


def test_db_writes_notify_reads_do_not(settings: Settings) -> None:
    db.init_db(settings.db_path)
    seen: list[Path] = []
    unsubscribe = db.on_change(seen.append)
    try:
        patients.list_patients(settings.db_path)
        assert seen == []
        patients.save_dictation(settings.db_path, "diktat-0001", {"transcript": SECRET}, "4711", None)
        assert seen == [settings.db_path]
    finally:
        unsubscribe()


def test_hub_wakes_waiters_from_other_threads(tmp_path: Path) -> None:
    async def run() -> None:
        hub = ChangeHub(tmp_path / "a.db")
        hub.bind(asyncio.get_running_loop())
        hub.notify(tmp_path / "andere.db")  # fremde Datenbank zählt nicht
        assert await hub.wait(0, 0.05) == 0
        threading.Timer(0.05, hub.notify, args=(tmp_path / "a.db",)).start()
        started = time.monotonic()
        assert await hub.wait(0, 5) == 1
        assert time.monotonic() - started < 1

    asyncio.run(run())


@pytest.fixture
def server(settings: Settings) -> Iterator[str]:
    """Echter uvicorn auf einem freien Port – TestClient puffert Ströme bis zum Ende."""
    live = dataclasses.replace(settings, events_heartbeat_s=0.2, events_max_s=30)
    config = uvicorn.Config(create_app(live), host="127.0.0.1", port=0, log_level="warning", timeout_graceful_shutdown=1)
    srv = uvicorn.Server(config)
    thread = threading.Thread(target=srv.run, daemon=True)
    thread.start()
    while not srv.started:
        time.sleep(0.01)
    port = srv.servers[0].sockets[0].getsockname()[1]
    yield f"http://127.0.0.1:{port}"
    srv.should_exit = True
    thread.join(5)


def _listen(client: httpx.Client, events: queue.Queue) -> None:
    """Liest den Strom und legt je Ereignis (Zeitpunkt, Zeilen) in die Queue; None = Strom zu Ende."""
    lines: list[str] = []
    try:
        with client.stream("GET", EVENTS, timeout=10) as response:
            for line in response.iter_lines():
                if line:
                    lines.append(line)
                elif lines:
                    events.put((time.monotonic(), lines))
                    lines = []
    except httpx.HTTPError:
        pass
    events.put(None)


def _next_change(events: queue.Queue) -> tuple[float, list[str]]:
    while True:
        item = events.get(timeout=5)
        assert item is not None, "Strom unerwartet beendet"
        if item[1][0] != "event: ping":
            return item


def test_new_dictation_reaches_office_well_under_one_second(server: str) -> None:
    office = httpx.Client(base_url=server, trust_env=False)  # ohne Proxy aus der Umgebung
    ipad = httpx.Client(base_url=server, trust_env=False)  # ohne Proxy aus der Umgebung
    for c in (office, ipad):
        assert c.post("/api/v1/login", json={"password": PASSWORD}).status_code == 204
    events: queue.Queue = queue.Queue()
    threading.Thread(target=_listen, args=(office, events), daemon=True).start()
    _next_change(events)  # Version beim Verbindungsaufbau

    sent = time.monotonic()
    body = {"transcript": SECRET, "patient_type": "kasse", "codes": ["13c"], "patient": "4711", "patient_label": "MK"}
    assert ipad.put("/api/v1/dictations/diktat-live-0001", json=body).status_code == 200
    arrived, lines = _next_change(events)
    listed = office.get("/api/v1/patients").json()  # das Büro lädt über die bestehende API neu
    shown = time.monotonic()

    assert lines[0] == "event: changed" and lines[1].startswith("data: ")
    assert lines[1].removeprefix("data: ").isdigit()  # nur die Versionsnummer
    assert listed["patients"][0]["number"] == "4711"
    print(f"\nSenden → Ereignis im Büro: {(arrived - sent) * 1000:.0f} ms, bis Liste geladen: {(shown - sent) * 1000:.0f} ms")
    assert shown - sent < 0.5

    # Abmelden beendet den Strom beim nächsten Lebenszeichen.
    assert office.post("/api/v1/logout").status_code == 204
    deadline = time.monotonic() + 5
    while (item := events.get(timeout=5)) is not None:
        assert time.monotonic() < deadline
    office.close()
    ipad.close()
