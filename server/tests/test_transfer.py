"""Kurzcode-Transfer: anlegen, lesen, Ablauf und Aufräumen, Rate-Limit."""

from __future__ import annotations

import sqlite3
import time
from dataclasses import replace
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from medvox import auth, db, ratelimit, transfer
from medvox.main import create_app
from medvox.settings import Settings

URL = "/api/v1/transfer"
BODY = {"transcript": "Zahn 36 mesial okklusal distal Kompositfüllung.", "codes": ["13c", "2100"]}


def test_create_requires_login(client: TestClient) -> None:
    assert client.post(URL, json=BODY).status_code == 401


def test_create_and_read(logged_in: TestClient) -> None:
    created = logged_in.post(URL, json=BODY)
    assert created.status_code == 200
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


def _stored_codes(db_path: Path) -> list[str]:
    with sqlite3.connect(db_path) as conn:
        return [r[0] for r in conn.execute("SELECT code FROM transfers").fetchall()]


def _stored_sessions(db_path: Path) -> int:
    with sqlite3.connect(db_path) as conn:
        return conn.execute("SELECT count(*) FROM sessions").fetchone()[0]


def test_expired_entry_is_purged_on_read(settings: Settings, logged_in: TestClient) -> None:
    db_path: Path = settings.db_path
    entry = transfer.create_transfer(db_path, "alt", [], ttl_s=0)
    time.sleep(0.01)
    assert entry.code in _stored_codes(db_path)
    assert transfer.get_transfer(db_path, entry.code) is None
    assert entry.code not in _stored_codes(db_path)  # Lesen löscht den abgelaufenen Text
    assert logged_in.get(f"{URL}/{entry.code}").status_code == 404


def test_reading_another_code_purges_expired_ones(settings: Settings, logged_in: TestClient) -> None:
    db_path: Path = settings.db_path
    old = transfer.create_transfer(db_path, "alt", [], ttl_s=0)
    fresh = transfer.create_transfer(db_path, "neu", [], ttl_s=60)
    time.sleep(0.01)
    assert logged_in.get(f"{URL}/{fresh.code}").status_code == 200
    assert _stored_codes(db_path) == [fresh.code] and old.code not in _stored_codes(db_path)


def test_expired_rows_are_purged_at_startup(settings: Settings) -> None:
    # Über das Wochenende liegen gebliebene Einträge (abgelaufen, ohne weiteren Zugriff).
    db_path: Path = settings.db_path
    db.init_db(db_path)
    past = time.time() - 60
    with db.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO transfers (code, transcript, codes_json, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
            ("ALTALT", "wochenende", "[]", past, past),
        )
        conn.execute("INSERT INTO sessions VALUES (?, ?, ?)", ("token-alt", past, past))
    assert _stored_codes(db_path) == ["ALTALT"] and _stored_sessions(db_path) == 1
    app = create_app(settings, transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    with TestClient(app):
        assert _stored_codes(db_path) == [] and _stored_sessions(db_path) == 0
    assert not auth.session_valid(db_path, "token-alt")


def test_periodic_sweep_purges_without_requests(settings: Settings) -> None:
    quick = replace(settings, purge_interval_s=0.05)
    app = create_app(quick, transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    with TestClient(app):
        old = transfer.create_transfer(quick.db_path, "alt", [], ttl_s=0)
        deadline = time.time() + 3.0
        while old.code in _stored_codes(quick.db_path) and time.time() < deadline:
            time.sleep(0.05)
        assert old.code not in _stored_codes(quick.db_path)


def test_rate_limit_per_ip(client: TestClient, settings: Settings) -> None:
    for _ in range(settings.transfer_lookups_per_min):
        assert client.get(f"{URL}/ABCDEF").status_code == 404
    limited = client.get(f"{URL}/ABCDEF")
    assert limited.status_code == 429
    assert "warten" in limited.json()["detail"]
    other = TestClient(client.app, client=("192.168.1.50", 1234))  # eigenes Fenster je IP
    assert other.get(f"{URL}/ABCDEF").status_code == 404


def test_forwarded_for_only_trusted_from_loopback(client: TestClient, settings: Settings) -> None:
    # Hinter Caddy (Loopback-Peer) zählt X-Forwarded-For; direkte LAN-Clients können ihn nicht setzen.
    proxied = TestClient(client.app, client=("127.0.0.1", 40000))
    for _ in range(settings.transfer_lookups_per_min):
        proxied.get(f"{URL}/ABCDEF", headers={"x-forwarded-for": "192.168.1.50"})
    assert proxied.get(f"{URL}/ABCDEF", headers={"x-forwarded-for": "192.168.1.50"}).status_code == 429
    assert proxied.get(f"{URL}/ABCDEF", headers={"x-forwarded-for": "192.168.1.51"}).status_code == 404
    direct = TestClient(client.app, client=("192.168.1.60", 40000))
    for _ in range(settings.transfer_lookups_per_min):
        direct.get(f"{URL}/ABCDEF", headers={"x-forwarded-for": "192.168.1.70"})
    assert direct.get(f"{URL}/ABCDEF", headers={"x-forwarded-for": "192.168.1.71"}).status_code == 429


def test_rate_limiter_window() -> None:
    limiter = ratelimit.RateLimiter(limit=2, window_s=0.05)
    assert limiter.allow("a") and limiter.allow("a") and not limiter.allow("a")
    assert limiter.allow("b")
    time.sleep(0.06)
    assert limiter.allow("a")


def test_code_alphabet_is_unambiguous() -> None:
    assert not set("0O1I") & set(transfer.CODE_ALPHABET)
    assert len(transfer.new_code()) == transfer.CODE_LENGTH


def test_patient_type_and_positions_roundtrip(logged_in: TestClient) -> None:
    # E6: Rezeption sieht Patiententyp und Art je Position; kopiert wird weiter nur `codes`.
    body = {
        **BODY,
        "codes": ["46,8,13a,2150"],
        "patient_type": "kasse",
        "positions": [
            {"tooth": 46, "code": "8", "kind": "bema"},
            {"tooth": 46, "code": "13a", "kind": "kassenanteil"},
            {"tooth": 46, "code": "2150", "kind": "zuzahlung"},
            {"tooth": None, "code": "107", "kind": "bema"},
        ],
    }
    code = logged_in.post(URL, json=body).json()["code"]
    read = TestClient(logged_in.app).get(f"{URL}/{code}").json()
    assert read["codes"] == ["46,8,13a,2150"]
    assert read["patient_type"] == "kasse"
    assert read["positions"] == body["positions"]


def test_old_ipad_without_details_still_works(logged_in: TestClient) -> None:
    code = logged_in.post(URL, json=BODY).json()["code"]
    read = TestClient(logged_in.app).get(f"{URL}/{code}").json()
    assert read["patient_type"] is None and read["positions"] == []


def test_invalid_details_rejected(logged_in: TestClient) -> None:
    assert logged_in.post(URL, json={**BODY, "patient_type": "gesetzlich"}).status_code == 422
    bad_kind = {**BODY, "positions": [{"tooth": 36, "code": "13a", "kind": "rabatt"}]}
    assert logged_in.post(URL, json=bad_kind).status_code == 422
    bad_tooth = {**BODY, "positions": [{"tooth": 99, "code": "13a", "kind": "bema"}]}
    assert logged_in.post(URL, json=bad_tooth).status_code == 422


def test_existing_database_gets_new_columns(settings: Settings) -> None:
    # Installierte Datenbank von vor E6: Tabelle ohne die neuen Spalten, ein laufender Eintrag.
    db_path: Path = settings.db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE transfers (code TEXT PRIMARY KEY, transcript TEXT NOT NULL,"
            " codes_json TEXT NOT NULL, created_at REAL NOT NULL, expires_at REAL NOT NULL)"
        )
        now = time.time()
        conn.execute("INSERT INTO transfers VALUES (?, ?, ?, ?, ?)", ("ALTNEU", "vorher", '["36,13a"]', now, now + 60))
    db.init_db(db_path)
    db.init_db(db_path)  # idempotent
    entry = transfer.get_transfer(db_path, "ALTNEU")
    assert entry is not None and entry.codes == ["36,13a"]
    assert entry.patient_type is None and entry.positions == []
