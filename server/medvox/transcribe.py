"""Audio → 16-kHz-WAV → whisper-server → Text.

Die Aufnahme liegt nur als temporäre Datei bis zur Antwort des whisper-servers
vor und wird danach in jedem Fall gelöscht. Logs enthalten keinen Transkripttext.
"""

from __future__ import annotations

import logging
import subprocess
import tempfile
import time
import wave
from dataclasses import dataclass
from pathlib import Path

import httpx

from medvox.settings import Settings

log = logging.getLogger("medvox.transcribe")

# Erlaubte Content-Types der Aufnahme (Safari: audio/mp4, Chrome: audio/webm).
ACCEPTED_TYPES = {
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
    "audio/webm": ".webm",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/wave": ".wav",
}
FFMPEG_TIMEOUT_S = 30.0


class TranscribeError(Exception):
    """Fehler mit HTTP-Status und deutscher Meldung für den Client."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass(frozen=True)
class Transcription:
    text: str
    duration_s: float
    latency_s: float


def media_type(content_type: str | None) -> str | None:
    """Normalisiert `audio/webm;codecs=opus` → `audio/webm`; None wenn unbekannt."""
    base = (content_type or "").split(";", 1)[0].strip().lower()
    return base if base in ACCEPTED_TYPES else None


def wav_info(path: Path) -> tuple[int, int, int, float] | None:
    """(Rate, Kanäle, Bytes je Sample, Dauer in s) oder None bei Nicht-WAV."""
    try:
        with wave.open(str(path), "rb") as wav:
            rate, channels, width = wav.getframerate(), wav.getnchannels(), wav.getsampwidth()
            duration = wav.getnframes() / rate if rate else 0.0
    except (wave.Error, EOFError, OSError):
        return None
    return rate, channels, width, duration


def convert_to_wav(ffmpeg: str, src: Path, dst: Path) -> None:
    """Wandelt mit ffmpeg nach 16 kHz mono PCM-WAV (Format des whisper-servers)."""
    cmd = [ffmpeg, "-nostdin", "-loglevel", "error", "-y", "-i", str(src),
           "-ar", "16000", "-ac", "1", "-f", "wav", str(dst)]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=FFMPEG_TIMEOUT_S, check=False)
    except OSError as exc:
        log.error("ffmpeg nicht startbar (%s): %s", ffmpeg, type(exc).__name__)
        raise TranscribeError(500, "ffmpeg ist auf dem Server nicht installiert.") from exc
    except subprocess.TimeoutExpired as exc:
        raise TranscribeError(500, "Die Audio-Konvertierung hat zu lange gedauert.") from exc
    if result.returncode != 0:
        log.warning("ffmpeg Exit %s", result.returncode)
        raise TranscribeError(400, "Die Aufnahme konnte nicht gelesen werden.")


def call_whisper(client: httpx.Client, settings: Settings, wav_path: Path) -> str:
    """POST /inference beim whisper-server; liefert den rohen Text."""
    data = {"language": "de", "response_format": "json", "temperature": "0.0",
            "prompt": settings.whisper_prompt}
    try:
        with wav_path.open("rb") as fh:
            response = client.post(
                f"{settings.whisper_url}/inference",
                files={"file": ("audio.wav", fh, "audio/wav")},
                data=data,
                timeout=settings.whisper_timeout_s,
            )
    except httpx.HTTPError as exc:
        log.error("whisper-server nicht erreichbar: %s", type(exc).__name__)
        raise TranscribeError(503, "Der Transkriptionsdienst ist nicht erreichbar.") from exc
    if response.status_code != 200:
        log.error("whisper-server antwortet mit Status %s", response.status_code)
        raise TranscribeError(502, "Der Transkriptionsdienst hat einen Fehler gemeldet.")
    try:
        text = response.json()["text"]
    except (ValueError, KeyError, TypeError) as exc:
        raise TranscribeError(502, "Der Transkriptionsdienst hat eine unerwartete Antwort geliefert.") from exc
    return str(text).strip()


def transcribe_bytes(
    client: httpx.Client, settings: Settings, audio: bytes, content_type: str
) -> Transcription:
    """Vollständiger Ablauf für eine Aufnahme; räumt Temp-Dateien immer auf."""
    suffix = ACCEPTED_TYPES[content_type]
    started = time.monotonic()
    tmp_dir = Path(tempfile.mkdtemp(prefix="medvox-", dir=settings.tmp_dir))
    src, wav = tmp_dir / f"in{suffix}", tmp_dir / "out.wav"
    try:
        src.write_bytes(audio)
        info = wav_info(src)
        if info and info[:3] == (16000, 1, 2):
            wav = src  # bereits im Zielformat, ffmpeg nicht nötig
        else:
            convert_to_wav(settings.ffmpeg, src, wav)
            info = wav_info(wav)
        duration = info[3] if info else 0.0
        if duration > settings.max_duration_s:
            raise TranscribeError(
                413, f"Die Aufnahme ist länger als {settings.max_duration_s:.0f} Sekunden."
            )
        text = call_whisper(client, settings, wav)
    finally:
        for path in (src, wav):
            path.unlink(missing_ok=True)
        try:
            tmp_dir.rmdir()
        except OSError:
            log.warning("Temp-Verzeichnis konnte nicht entfernt werden")
    latency = time.monotonic() - started
    log.info("Transkription: %.1f s Audio in %.2f s", duration, latency)
    return Transcription(text=text, duration_s=round(duration, 2), latency_s=round(latency, 3))
