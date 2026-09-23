"""POST /api/v1/transcribe: Happy Path, Fehlerpfade, Temp-Datei-Aufräumen."""

from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from medvox import transcribe
from medvox.main import create_app
from medvox.settings import FALLBACK_PROMPT, Settings
from tests.conftest import PASSWORD, FakeWhisper, make_wav

URL = "/api/v1/transcribe"


def _upload(client: TestClient, data: bytes, content_type: str = "audio/wav", **form: str) -> httpx.Response:
    return client.post(URL, files={"file": ("aufnahme.wav", data, content_type)}, data=form or None)


def test_requires_login(client: TestClient) -> None:
    assert _upload(client, make_wav()).status_code == 401


def test_happy_path_wav(logged_in: TestClient, whisper: FakeWhisper) -> None:
    response = _upload(logged_in, make_wav(seconds=2.0))
    assert response.status_code == 200
    body = response.json()
    # Anzeigefassung: Zahnnummer als FDI, Flächen wie diktiert.
    assert body["transcript"] == "Zahn 36 mesial okklusal distal."
    assert body["duration_s"] == 2.0
    assert body["latency_s"] >= 0
    assert body["codes"] == []
    inference = [r for r in whisper.requests if r.url.path == "/inference"]
    assert len(inference) == 1
    assert b'name="language"' in inference[0].content and b"de" in inference[0].content


def test_webm_goes_through_ffmpeg(logged_in: TestClient, settings: Settings) -> None:
    # Der Fake-ffmpeg kopiert WAV-Eingaben unverändert durch.
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
    bad = replace(settings, ffmpeg=str(Path(settings.ffmpeg).parent / "fehlt"))
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
    assert transcribe.media_type("audio/x-m4a") is None
    assert transcribe.media_type("audio/x-wav") is None
    assert transcribe.media_type("text/plain") is None
    assert transcribe.media_type(None) is None


def test_missing_prompt_file_warns_at_startup(
    settings: Settings, whisper: FakeWhisper, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING, logger="medvox.settings")
    with TestClient(create_app(settings, transport=httpx.MockTransport(whisper))) as tc:
        assert any("FALLBACK_PROMPT" in r.message for r in caplog.records)
        tc.post("/api/v1/login", json={"password": PASSWORD})
        _upload(tc, make_wav())
    inference = [r for r in whisper.requests if r.url.path == "/inference"]
    assert FALLBACK_PROMPT.encode() in inference[0].content


def test_prompt_file_is_used_without_warning(
    settings: Settings, whisper: FakeWhisper, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("Zahnarzt-Diktat aus Datei.\n", encoding="utf-8")
    caplog.set_level(logging.WARNING, logger="medvox.settings")
    with_file = replace(settings, whisper_prompt_file=prompt)
    with TestClient(create_app(with_file, transport=httpx.MockTransport(whisper))) as tc:
        tc.post("/api/v1/login", json={"password": PASSWORD})
        _upload(tc, make_wav())
    assert not [r for r in caplog.records if "FALLBACK_PROMPT" in r.message]
    inference = [r for r in whisper.requests if r.url.path == "/inference"]
    assert b"Zahnarzt-Diktat aus Datei." in inference[0].content


def test_codes_from_extractor(logged_in: TestClient, whisper: FakeWhisper) -> None:
    whisper.text = " Zahn 36 mesial okklusal distal, Kompositfüllung, Kofferdarm gelegt, Extraktion 48 planen.\n"
    body = _upload(logged_in, make_wav()).json()
    assert body["patient_type"] == "kasse"  # Standard ohne Formularfeld
    assert body["transcript"].startswith("Zahn 36") and "Kofferdam" in body["transcript"]
    assert body["codes"] == ["13c", "12"]
    primary = [(s["code"], s["kind"]) for s in body["suggestions"] if not s["alternative"]]
    assert primary == [("13c", "bema"), ("12", "bema")]
    assert ("2100", "zuzahlung") in [(s["code"], s["kind"]) for s in body["suggestions"] if s["alternative"]]
    assert {s["kind"] for s in body["suggestions"]} <= {"bema", "zuzahlung"}
    assert next(s for s in body["suggestions"] if s["code"] == "12")["reason"] == "wegen: Kofferdam gelegt"
    assert [(p["code"], p["teeth"]) for p in body["planned"]] == [("44", [48])]
    assert body["notes"] == []


def test_private_patient_gets_goz_only(logged_in: TestClient, whisper: FakeWhisper) -> None:
    whisper.text = " L1, L1, Ost1 an 38, Extraktion 48 planen.\n"
    body = _upload(logged_in, make_wav(), patient_type="privat").json()
    assert body["patient_type"] == "privat"
    assert body["codes"] == ["2x 0100", "3030", "0500"]
    assert {(s["system"], s["kind"]) for s in body["suggestions"]} == {("GOZ", "goz")}
    assert [(p["code"], p["teeth"]) for p in body["planned"]] == [("3010", [48])]


def test_statutory_patient_same_dictation(logged_in: TestClient, whisper: FakeWhisper) -> None:
    whisper.text = " L1, L1, Ost1 an 38.\n"
    body = _upload(logged_in, make_wav(), patient_type="kasse").json()
    assert body["codes"] == ["2x 41a", "47a"]  # kein Zuschlag beim Kassenpatienten


def test_unknown_patient_type_422(logged_in: TestClient) -> None:
    response = _upload(logged_in, make_wav(), patient_type="gesetzlich")
    assert response.status_code == 422
    assert "Patiententyp" in response.json()["detail"]
