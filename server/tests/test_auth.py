from dataclasses import replace

import httpx
from fastapi.testclient import TestClient

from medvox.auth import SESSION_COOKIE, hash_password, verify_password
from medvox.main import create_app
from medvox.settings import Settings
from tests.conftest import PASSWORD


def test_hash_roundtrip() -> None:
    stored = hash_password("geheim123", iterations=1000)
    assert stored.startswith("pbkdf2_sha256$1000$")
    assert verify_password("geheim123", stored)
    assert not verify_password("geheim124", stored)
    assert not verify_password("geheim123", "kaputt")


def test_session_requires_login(client: TestClient) -> None:
    assert client.get("/api/v1/session").status_code == 401


def test_login_wrong_password(client: TestClient) -> None:
    response = client.post("/api/v1/login", json={"password": "falsch"})
    assert response.status_code == 401
    assert "falsch" in response.json()["detail"]
    assert SESSION_COOKIE not in client.cookies


def test_login_sets_httponly_cookie_and_session_works(client: TestClient) -> None:
    response = client.post("/api/v1/login", json={"password": PASSWORD})
    assert response.status_code == 204
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{SESSION_COOKIE}=")
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie
    assert client.get("/api/v1/session").status_code == 200


def test_logout_invalidates_session(logged_in: TestClient) -> None:
    assert logged_in.post("/api/v1/logout").status_code == 204
    assert logged_in.get("/api/v1/session").status_code == 401


def test_forged_cookie_is_rejected(client: TestClient) -> None:
    client.cookies.set(SESSION_COOKIE, "erfunden")
    assert client.get("/api/v1/session").status_code == 401


def test_login_without_configured_hash(settings: Settings) -> None:
    app = create_app(
        replace(settings, password_hash=""),
        transport=httpx.MockTransport(lambda r: httpx.Response(200)),
    )
    with TestClient(app) as tc:
        response = tc.post("/api/v1/login", json={"password": PASSWORD})
    assert response.status_code == 503


def test_login_rate_limit_per_ip(client: TestClient, settings: Settings) -> None:
    for _ in range(settings.login_attempts_per_min):
        assert client.post("/api/v1/login", json={"password": "falsch"}).status_code == 401
    limited = client.post("/api/v1/login", json={"password": PASSWORD})
    assert limited.status_code == 429
    assert "Anmeldeversuche" in limited.json()["detail"]
    other = TestClient(client.app, client=("192.168.1.50", 1234))  # eigenes Fenster je IP
    assert other.post("/api/v1/login", json={"password": PASSWORD}).status_code == 204
