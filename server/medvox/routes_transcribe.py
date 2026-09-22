"""Routen für Health-Check und Transkription."""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from medvox import transcribe
from medvox.auth import require_session

log = logging.getLogger("medvox.transcribe")
router = APIRouter(prefix="/api/v1")
HEALTH_TIMEOUT_S = 1.0


class Health(BaseModel):
    """Antwort von GET /api/v1/health."""

    status: str
    whisper: str


class TranscribeResponse(BaseModel):
    transcript: str
    duration_s: float
    latency_s: float
    codes: list[str]


@router.get("/health", response_model=Health)
def health(request: Request) -> Health:
    """Lebenszeichen; `whisper` meldet den tatsächlichen Zustand des whisper-servers."""
    settings = request.app.state.settings
    client: httpx.Client = request.app.state.http
    try:
        response = client.get(f"{settings.whisper_url}/", timeout=HEALTH_TIMEOUT_S)
        whisper = "ok" if response.status_code == 200 else "down"
    except httpx.HTTPError:
        whisper = "down"
    return Health(status="ok", whisper=whisper)


async def _read_limited(file: UploadFile, limit: int) -> bytes:
    """Liest höchstens `limit` Bytes; darüber hinaus wird abgebrochen (413)."""
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(64 * 1024):
        total += len(chunk)
        if total > limit:
            raise HTTPException(
                status_code=413, detail=f"Die Aufnahme ist größer als {limit // (1024 * 1024)} MB."
            )
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/transcribe", response_model=TranscribeResponse, dependencies=[Depends(require_session)])
async def transcribe_upload(file: UploadFile, request: Request) -> TranscribeResponse:
    """Nimmt eine Aufnahme entgegen und liefert das rohe Transkript.

    `codes` bleibt in dieser Ausbaustufe leer; der Regel-Extraktor (WP-8) füllt es.
    """
    settings = request.app.state.settings
    content_type = transcribe.media_type(file.content_type)
    if content_type is None:
        raise HTTPException(
            status_code=415, detail="Nur audio/mp4, audio/webm oder audio/wav werden angenommen."
        )
    audio = await _read_limited(file, settings.max_upload_bytes)
    if not audio:
        raise HTTPException(status_code=400, detail="Die Aufnahme ist leer.")
    try:
        result = await run_in_threadpool(
            transcribe.transcribe_bytes, request.app.state.http, settings, audio, content_type
        )
    except transcribe.TranscribeError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return TranscribeResponse(
        transcript=result.text, duration_s=result.duration_s, latency_s=result.latency_s, codes=[]
    )
