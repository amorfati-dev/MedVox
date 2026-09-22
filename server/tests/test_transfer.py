"""Kurzcode-Transfer: anlegen, lesen, Ablauf, Rate-Limit."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from medvox import transfer
from medvox.settings import Settings

URL = "/api/v1/transfer"
BODY = {"transcript": "Zahn 36 mesial okklusal distal Kompositfüllung.", "codes": ["13c", "2100"]}


def test_create_requires_login(client: TestClient) -> None:
    assert client.post(URL, json=BODY).status_code == 401


def test_create_and_read(logged_in: TestClient) -> None:
    created = logged_in.post(URL, json=BODY)
    assert created.status_code == 201 or created.status_code == 200
    code = created.json()["code"]
    assert len(code) == 6 and set(code) <= set(transfer.CODE_ALPHABET)
    assert created.json()["expires_at"].endswith("+00:00")

    fresh = TestClient(logged_in.app)  # ohne Cookie: Abruf braucht keinen Login
    for _ in range(2):  # mehrfach lesbar
        read = fresh.get(f"{URL}/{code}")
        assert read.status_code == 200
        assert read.json()["transcript"] == BODY["transcript"]
        assert read.json()["codes"] == BODY["codes"]
        assert "created_at" in read.json()
    assert fresh.get(f"{URL}/{code.lower()}").status_code == 200  # Groß-/Kleinschreibung egal


def test_unknown_code_404(client: TestClient) -> None:
    response = client.get(f"{URL}/ZZZZZZ")
    assert response.status_code == 404
    assert "Code" in response.json()["detail"]


def test_expired_entry_is_gone_and_purged(settings: Settings, logged_in: TestClient) -> None:
    db_path: Path = settings.db_path
    entry = transfer.create_transfer(db_path, "alt", [], ttl_s=0)
    time.sleep(0.01)
    assert transfer.get_transfer(db_path, entry.code) is None
    assert logged_in.get(f"{URL}/{entry.code}").status_code == 404
    transfer.create_transfer(db_path, "neu", [], ttl_s=60)  # Schreiben räumt Abgelaufenes weg
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT code FROM transfers").fetchall()
    assert [r[0] for r in rows] != [] and entry.code not in [r[0] for r in rows]


def test_rate_limit_per_ip(client: TestClient, settings: Settings) -> None:
    for _ in range(settings.transfer_lookups_per_min):
        assert client.get(f"{URL}/ABCDEF").status_code == 404
    limited = client.get(f"{URL}/ABCDEF")
    assert limited.status_code == 429
    assert "warten" in limited.json()["detail"]
    # Eine andere IP (über X-Forwarded-For hinter Caddy) hat ihr eigenes Fenster.
    other = client.get(f"{URL}/ABCDEF", headers={"x-forwarded-for": "192.168.1.50"})
    assert other.status_code == 404


def test_rate_limiter_window() -> None:
    limiter = transfer.RateLimiter(limit=2, window_s=0.05)
    assert limiter.allow("a") and limiter.allow("a") and not limiter.allow("a")
    assert limiter.allow("b")
    time.sleep(0.06)
    assert limiter.allow("a")


def test_code_alphabet_is_unambiguous() -> None:
    assert not set("0O1I") & set(transfer.CODE_ALPHABET)
    assert len(transfer.new_code()) == transfer.CODE_LENGTH
