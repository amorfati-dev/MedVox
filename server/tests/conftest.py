"""Gemeinsame Fixtures: temporäre DB, gemockter whisper-server, Fake-ffmpeg."""

from __future__ import annotations

import io
import json
import os
import stat
import wave
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from medvox.auth import hash_password
from medvox.main import create_app
from medvox.settings import Settings

PASSWORD = "praxis-geheim"
WHISPER_TEXT = " Zahn drei sechs mesial okklusal distal.\n"

# Ein Fake-ffmpeg, das eine WAV-Eingabe unverändert als Ausgabe kopiert und
# wie das Original bei Nicht-Audio mit Exit 1 abbricht
# (Argumente wie im echten Aufruf: ... -i <in> ... <out>).
FAKE_FFMPEG = """#!/bin/sh
in=""
while [ $# -gt 0 ]; do
  case "$1" in -i) in="$2"; shift;; esac
  out="$1"; shift
done
head -c 4 "$in" | grep -q RIFF || exit 1
cp "$in" "$out"
"""


def make_wav(seconds: float = 1.0, rate: int = 16000, channels: int = 1) -> bytes:
    """Stille als PCM-16-WAV."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(b"\x00\x00" * int(seconds * rate) * channels)
    return buf.getvalue()


class FakeWhisper:
    """httpx.MockTransport-Handler; `mode` = ok | down | error."""

    def __init__(self) -> None:
        self.mode = "ok"
        self.text = WHISPER_TEXT
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.mode == "down":
            raise httpx.ConnectError("connection refused", request=request)
        if self.mode == "error":
            return httpx.Response(500, text="boom")
        if request.url.path == "/inference":
            return httpx.Response(200, json={"text": self.text})
        return httpx.Response(200, text="<html>whisper</html>")


@pytest.fixture
def whisper() -> FakeWhisper:
    return FakeWhisper()


@pytest.fixture
def ffmpeg(tmp_path: Path) -> Path:
    script = tmp_path / "bin" / "ffmpeg"
    script.parent.mkdir()
    script.write_text(FAKE_FFMPEG)
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return script


@pytest.fixture
def settings(tmp_path: Path, ffmpeg: Path) -> Settings:
    tmp_dir = tmp_path / "audio-tmp"
    tmp_dir.mkdir()
    return Settings(
        whisper_url="http://whisper.test",
        whisper_prompt_file=tmp_path / "fehlt.txt",
        password_hash=hash_password(PASSWORD, iterations=1000),
        db_path=tmp_path / "db" / "medvox.db",
        ffmpeg=str(ffmpeg),
        tmp_dir=tmp_dir,
    )


@pytest.fixture
def client(settings: Settings, whisper: FakeWhisper):
    app = create_app(settings, transport=httpx.MockTransport(whisper))
    with TestClient(app) as tc:
        yield tc


@pytest.fixture
def logged_in(client: TestClient) -> TestClient:
    response = client.post("/api/v1/login", json={"password": PASSWORD})
    assert response.status_code == 204
    return client


def whisper_running() -> bool:
    """Für den Integrationstest: antwortet ein echter whisper-server?"""
    url = os.environ.get("WHISPER_URL", "http://127.0.0.1:8178")
    try:
        return httpx.get(f"{url}/", timeout=1.0).status_code == 200
    except httpx.HTTPError:
        return False


__all__ = ["json"]
