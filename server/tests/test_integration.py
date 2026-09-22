"""Integrationstest gegen den echten whisper-server (WP-1) und echtes ffmpeg.

Läuft nur, wenn `WHISPER_URL` (Standard http://127.0.0.1:8178) antwortet:
`uv run pytest -m integration -s`. Erzeugt mit macOS `say` ein deutsches Diktat.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from medvox.auth import hash_password
from medvox.main import create_app
from medvox.settings import Settings
from tests.conftest import PASSWORD, whisper_running

SENTENCE = "Zahn drei sechs, Karies profunda, Kompositfüllung mesial okklusal distal."
pytestmark = pytest.mark.integration


@pytest.mark.skipif(not whisper_running(), reason="whisper-server antwortet nicht")
@pytest.mark.skipif(not shutil.which("say") or not shutil.which("ffmpeg"), reason="say/ffmpeg fehlen")
def test_real_whisper_hears_tooth_36(tmp_path: Path) -> None:
    aiff = tmp_path / "diktat.aiff"
    subprocess.run(["say", "-v", "Anna", "-o", str(aiff), SENTENCE], check=True, timeout=30)
    tmp_dir = tmp_path / "audio-tmp"
    tmp_dir.mkdir()
    settings = Settings(
        whisper_url=Settings.from_env().whisper_url,
        password_hash=hash_password(PASSWORD, iterations=1000),
        db_path=tmp_path / "medvox.db",
        tmp_dir=tmp_dir,
    )
    with TestClient(create_app(settings)) as client:
        assert client.post("/api/v1/login", json={"password": PASSWORD}).status_code == 204
        response = client.post(
            "/api/v1/transcribe", files={"file": ("diktat.m4a", aiff.read_bytes(), "audio/mp4")}
        )
    assert response.status_code == 200, response.text
    body = response.json()
    print(f"\nTranskript: {body['transcript']!r}  ({body['duration_s']} s Audio, {body['latency_s']} s)")
    text = body["transcript"].lower()
    assert "36" in text or "drei sechs" in text
    assert body["codes"] == []
    assert list(tmp_dir.iterdir()) == []
