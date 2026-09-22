"""POST /api/v1/transcribe: Happy Path, Fehlerpfade, Temp-Datei-Aufräumen."""

from __future__ import annotations

from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from medvox import transcribe
from medvox.settings import Settings
from tests.conftest import WHISPER_TEXT, FakeWhisper, make_wav

URL = "/api/v1/transcribe"


def _upload(client: TestClient, data: bytes, content_type: str = "audio/wav") -> httpx.Response:
    return client.post(URL, files={"file": ("aufnahme.wav", data, content_type)})


def test_requires_login(client: TestClient) -> None:
    assert _upload(client, make_wav()).status_code == 401


def test_happy_path_wav(logged_in: TestClient, whisper: FakeWhisper) -> None:
    response = _upload(logged_in, make_wav(seconds=2.0))
    assert response.status_code == 200
    body = response.json()
    assert body["transcript"] == WHISPER_TEXT.strip()
    assert body["duration_s"] == 2.0
    assert body["latency_s"] >= 0
    assert body["codes"] == []
    inference = [r for r in whisper.requests if r.url.path == "/inference"]
    assert len(inference) == 1
    assert b'name="language"' in inference[0].content and b"de" in inference[0].content


def test_webm_goes_through_ffmpeg(logged_in: TestClient, settings: Settings) -> None:
    # Der Fake-ffmpeg kopiert die Eingabe; ein 44,1-kHz-WAV erzwingt den Konvertierungspfad.
    response = _upload(logged_in, make_wav(seconds=1.0, rate=44100), "audio/webm;codecs=opus")
    assert response.status_code == 200
    assert response.json()["duration_s"] == 1.0


def test_unsupported_type_415(logged_in: TestClient) -> None:
    response = _upload(logged_in, b"%PDF-1.4", "application/pdf")
    assert response.status_code == 415
    assert "audio/mp4" in response.json()["detail"]


def test_too_large_413(logged_in: TestClient, settings: Settings) -> None:
    response = _upload(logged_in, b"\x00" * (settings.max_upload_bytes + 1))
    assert response.status_code == 413
    assert "MB" in response.json()["detail"]


def test_too_long_413(logged_in: TestClient, settings: Settings) -> None:
    response = _upload(logged_in, make_wav(seconds=settings.max_duration_s + 1))
    assert response.status_code == 413
    assert "Sekunden" in response.json()["detail"]


def test_empty_upload_400(logged_in: TestClient) -> None:
    assert _upload(logged_in, b"").status_code == 400


def test_unreadable_audio_400(logged_in: TestClient) -> None:
    response = _upload(logged_in, b"kein audio", "audio/mp4")
    assert response.status_code == 400
    assert "nicht gelesen" in response.json()["detail"]


def test_whisper_down_503(logged_in: TestClient, whisper: FakeWhisper) -> None:
    whisper.mode = "down"
    response = _upload(logged_in, make_wav())
    assert response.status_code == 503
    assert "nicht erreichbar" in response.json()["detail"]


def test_whisper_error_502(logged_in: TestClient, whisper: FakeWhisper) -> None:
    whisper.mode = "error"
    assert _upload(logged_in, make_wav()).status_code == 502


def test_no_temp_files_remain(logged_in: TestClient, settings: Settings, whisper: FakeWhisper) -> None:
    tmp_dir = settings.tmp_dir
    assert tmp_dir is not None
    _upload(logged_in, make_wav(seconds=1.0, rate=44100), "audio/mp4")
    whisper.mode = "down"
    _upload(logged_in, make_wav())
    assert list(tmp_dir.iterdir()) == []


def test_temp_files_removed_on_ffmpeg_missing(settings: Settings, whisper: FakeWhisper) -> None:
    bad = Settings(**{**settings.__dict__, "ffmpeg": str(Path(settings.ffmpeg).parent / "fehlt")})
    client = httpx.Client(transport=httpx.MockTransport(whisper))
    try:
        transcribe.transcribe_bytes(client, bad, make_wav(rate=8000), "audio/wav")
    except transcribe.TranscribeError as exc:
        assert exc.status_code == 500
    else:
        raise AssertionError("TranscribeError erwartet")
    assert list(settings.tmp_dir.iterdir()) == []  # type: ignore[union-attr]


def test_media_type_normalisation() -> None:
    assert transcribe.media_type("audio/webm;codecs=opus") == "audio/webm"
    assert transcribe.media_type("AUDIO/MP4") == "audio/mp4"
    assert transcribe.media_type("text/plain") is None
    assert transcribe.media_type(None) is None
