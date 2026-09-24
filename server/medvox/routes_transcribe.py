"""Routen für Health-Check und Transkription."""

from __future__ import annotations

import logging
from typing import Annotated, Literal

import httpx
from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from medvox import lexicon_entries, transcribe, whisper_prompt
from medvox.auth import require_session
from medvox.extract import Suggestion, analyze, billable_codes
from medvox.extract_findings import extract_findings
from medvox.extract_patient import PATIENT_TYPES
from medvox.lexicon import correct
from medvox.normalize import normalize
from medvox.normalize_display import display_text

log = logging.getLogger("medvox.transcribe")
router = APIRouter(prefix="/api/v1")
HEALTH_TIMEOUT_S = 1.0


class Health(BaseModel):
    """Antwort von GET /api/v1/health."""

    status: str
    whisper: str


class SuggestionOut(BaseModel):
    """Ein Ziffernvorschlag des Regel-Extraktors (WP-8) mit Begründung."""

    code: str
    system: str
    title: str
    points: int | None
    teeth: list[int]
    count: int
    reason: str
    decide: list[str]
    planned: bool = False  # fehlt bei am iPad ergänzten Positionen (nie geplant)
    alternative: bool
    kind: str  # bema | goz (Privatleistung, auch GOÄ) | zuzahlung (Privatleistung beim Kassenpatienten)
    evident: str | None = None  # Evident-Kurzform ("l1"), sonst None – dann gilt die Ziffer
    addon: bool = False  # Option „ggf. dazu“ (Ä1/Zst zur Weisheitszahn-OP): per Tipp übernehmbar wie eine Zuzahlung
    # Herkunft: regel (Extraktor), hand (am iPad aus dem Katalog ergänzt), geaendert (am iPad ersetzt, z. B. 13b → 13c)
    source: Literal["regel", "hand", "geaendert"] = "regel"
    tapped: bool = False  # nur am iPad: Zahn im Zahnschema angetippt (Je-Zahn-Position, app/src/teeth.ts)


class ToothOut(BaseModel):
    """Zahn fürs Zahnschema: diktierte Flächen und Befundwörter (``extract_findings``), nie eine Ziffer."""

    tooth: int | None  # FDI-Nummer, None = Befund ohne Zahn
    surfaces: str = Field(default="", max_length=20)
    findings: list[Annotated[str, Field(max_length=100)]] = Field(default_factory=list, max_length=20)


class TranscribeResponse(BaseModel):
    transcript: str
    patient_type: str = "kasse"  # Patiententyp, für den die Vorschläge gelten: kasse | privat
    duration_s: float
    latency_s: float
    codes: list[str]  # erbrachte Hauptvorschläge im Kopierformat ("13c", "2x 41a")
    suggestions: list[SuggestionOut] = []  # erbracht: Hauptvorschläge und Privat-Alternativen
    planned: list[SuggestionOut] = []  # nur geplant – nie abrechnen
    notes: list[str] = []  # Hinweise ohne Ziffer (verneint, enthalten, Zuschlag nicht bestimmbar)
    teeth: list[ToothOut] = []  # Zahnschema: diktierte Zähne mit Flächen und Befunden


def _out(s: Suggestion) -> SuggestionOut:
    return SuggestionOut(
        code=s.code, system=s.system, title=s.title, points=s.points, teeth=list(s.teeth), count=s.count,
        reason=s.reason, decide=list(s.decide), planned=s.planned, alternative=s.alternative, kind=s.kind,
        evident=s.evident, addon=s.addon,
    )


def build_response(
    text: str, duration_s: float, latency_s: float, patient_type: str = "kasse",
    extra: dict[tuple[str, ...], str] | None = None,
) -> TranscribeResponse:
    """Lexikon -> Normalisierer -> Extraktor und Befunde; `transcript` ist die Anzeigefassung (FDI, Flächen wie diktiert).

    `extra`: die eingeschalteten Ersetzungen aus dem Wörterbuch (`lexicon_entries.active`).
    """
    corrected, _ = correct(text, extra)
    normalized = normalize(corrected)
    result = analyze(normalized.text, normalized.teeth, patient_type)
    return TranscribeResponse(
        transcript=display_text(corrected), patient_type=result.patient, duration_s=duration_s, latency_s=latency_s,
        codes=billable_codes(result.suggestions),
        suggestions=[_out(s) for s in result.suggestions if not s.planned],
        planned=[_out(s) for s in result.suggestions if s.planned],
        notes=result.notes,
        teeth=[
            ToothOut(tooth=t.tooth, surfaces=t.surfaces, findings=list(t.findings))
            for t in extract_findings(normalized.text, normalized.teeth)
        ],
    )


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
async def transcribe_upload(
    file: UploadFile, request: Request, patient_type: str = Form("kasse")
) -> TranscribeResponse:
    """Nimmt eine Aufnahme entgegen und liefert das lexikon-korrigierte Transkript plus Ziffernvorschläge.

    ``patient_type`` (Formularfeld, Standard ``kasse``) wählt je Leistung BEMA oder GOZ/GOÄ. Das Wörterbuch
    der Praxis wird je Anfrage gelesen: Fachbegriffe in den Prompt, Ersetzungen vor den Normalisierer.
    """
    settings = request.app.state.settings
    if patient_type not in PATIENT_TYPES:
        raise HTTPException(status_code=422, detail="Patiententyp muss „kasse“ oder „privat“ sein.")
    content_type = transcribe.media_type(file.content_type)
    if content_type is None:
        raise HTTPException(
            status_code=415, detail="Nur audio/mp4, audio/webm oder audio/wav werden angenommen."
        )
    audio = await _read_limited(file, settings.max_upload_bytes)
    if not audio:
        raise HTTPException(status_code=400, detail="Die Aufnahme ist leer.")
    words = await run_in_threadpool(lexicon_entries.active, settings.db_path)
    prompt = whisper_prompt.compose(settings.whisper_prompt, words.terms)
    try:
        result = await run_in_threadpool(
            transcribe.transcribe_bytes, request.app.state.http, settings, audio, content_type, prompt
        )
    except transcribe.TranscribeError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return build_response(result.text, result.duration_s, result.latency_s, patient_type, words.replacements)
