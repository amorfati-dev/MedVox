from fastapi.testclient import TestClient

from tests.conftest import FakeWhisper


def test_health_whisper_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "whisper": "ok"}


def test_health_whisper_down(client: TestClient, whisper: FakeWhisper) -> None:
    whisper.mode = "down"
    assert client.get("/api/v1/health").json() == {"status": "ok", "whisper": "down"}


def test_health_whisper_error_status(client: TestClient, whisper: FakeWhisper) -> None:
    whisper.mode = "error"
    assert client.get("/api/v1/health").json()["whisper"] == "down"
