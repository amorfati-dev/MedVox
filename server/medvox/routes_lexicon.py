"""Routen der Wörterbuch-Seite (`/woerterbuch`): Einträge, Füllstand des Prompts, Vorschläge aus Korrekturen.

Nur mit Sitzung, ohne weitere Rechte (wie die Behandlerliste). Ein Eintrag gilt ab dem Speichern für jedes
folgende Diktat (Entscheidung F5); abgeschaltet wird per `PUT …/{id}` mit `active: false`, gelöscht nie.
Die Probe läuft über `POST /api/v1/analyze` mit `draft` (`routes_correction.py`). In Logs stehen nur IDs
und Anzahlen, nie die Wörter.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from medvox import corrections, db, lexicon_entries, lexicon_suggest, whisper_prompt
from medvox.auth import require_session
from medvox.lexicon import BUILTIN_SHOWN
from medvox.settings import Settings

log = logging.getLogger("medvox.lexicon")
router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_session)])


class EntryOut(BaseModel):
    id: int
    kind: Literal["ersetzung", "begriff"]
    wrong: str  # leer bei Begriffen
    right: str
    active: bool
    source: Literal["hand", "korrektur"]
    created_at: float  # Unix-Zeit, für „seit …“


class BuiltinOut(BaseModel):
    wrong: str
    right: str


class PromptOut(BaseModel):
    base: str  # Grundtext aus der Prompt-Datei, auf der Seite nur lesbar
    base_tokens: int
    terms_tokens: int  # die eingeschalteten Begriffe
    limit: int  # so viele Token nimmt whisper.cpp höchstens, davor schneidet es ab
    exact: bool  # mit dem Vokabular des Modells gezählt; sonst vorsichtig geschätzt


class LexiconOut(BaseModel):
    entries: list[EntryOut]
    builtin: list[BuiltinOut]  # eingebaute Ersetzungen (`lexicon.ALIASES`), nicht änderbar
    prompt: PromptOut


class EntryIn(BaseModel):
    kind: Literal["ersetzung", "begriff"]
    wrong: str = Field("", max_length=200)
    right: str = Field(max_length=200)
    source: Literal["hand", "korrektur"] = "hand"


class ActiveIn(BaseModel):
    active: bool


class SuggestionOut(BaseModel):
    kind: Literal["text", "ziffer"]
    before: str
    after: str
    count: int
    takeable: bool
    taken: bool


class SuggestionsOut(BaseModel):
    suggestions: list[SuggestionOut]
    total: int
    first_week: str | None
    last_week: str | None


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def _out(e: lexicon_entries.Entry) -> EntryOut:
    return EntryOut(id=e.id, kind=e.kind, wrong=e.wrong, right=e.right, active=e.active, source=e.source,
                    created_at=e.created_at)


def _prompt(settings: Settings, terms: list[str]) -> PromptOut:
    room = whisper_prompt.budget(settings.whisper_prompt, terms, settings.whisper_model)
    return PromptOut(base=settings.whisper_prompt, base_tokens=room.base, terms_tokens=room.terms, limit=room.limit,
                     exact=room.exact)


@router.get("/lexicon", response_model=LexiconOut)
def list_all(request: Request) -> LexiconOut:
    settings = _settings(request)
    entries = lexicon_entries.list_entries(settings.db_path)
    terms = [e.right for e in sorted(entries, key=lambda e: (e.created_at, e.id)) if e.active and e.kind == "begriff"]
    return LexiconOut(
        entries=[_out(e) for e in entries],
        builtin=[BuiltinOut(wrong=" ".join(words), right=right) for words, right in BUILTIN_SHOWN],
        prompt=_prompt(settings, terms),
    )


def _checked(work):
    try:
        return work()
    except lexicon_entries.Rejected as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/lexicon", response_model=EntryOut)
def create(body: EntryIn, request: Request) -> EntryOut:
    settings = _settings(request)
    entry = _checked(lambda: lexicon_entries.create(
        settings.db_path, body.kind, body.wrong, body.right, body.source, settings.whisper_prompt,
        settings.whisper_model,
    ))
    log.info("Wörterbuch: %s angelegt (ID %d, %s)", entry.kind, entry.id, entry.source)
    return _out(entry)


@router.put("/lexicon/{entry_id}", response_model=EntryOut)
def set_active(entry_id: int, body: ActiveIn, request: Request) -> EntryOut:
    """Abschalten oder wieder einschalten (dann gelten die Schutzregeln erneut)."""
    settings = _settings(request)
    entry = _checked(lambda: lexicon_entries.set_active(
        settings.db_path, entry_id, body.active, settings.whisper_prompt, settings.whisper_model,
    ))
    if entry is None:
        raise HTTPException(status_code=404, detail="Eintrag nicht gefunden.")
    log.info("Wörterbuch: Eintrag %d %s", entry_id, "eingeschaltet" if body.active else "abgeschaltet")
    return _out(entry)


@router.get("/lexicon/suggestions", response_model=SuggestionsOut)
def suggestions(request: Request) -> SuggestionsOut:
    """Gleiche Änderungen aus der Korrektur-Sammlung, gezählt; übernommen wird nur per Tipp."""
    path: Path = _settings(request).db_path
    current = [e for e in lexicon_entries.list_entries(path) if e.active]
    with db.connect(path) as conn:
        found = lexicon_suggest.collect(conn, current)
    return SuggestionsOut(
        suggestions=[SuggestionOut(**vars(s)) for s in found.suggestions],
        total=found.total, first_week=found.first_week, last_week=found.last_week,
    )


@router.delete("/corrections", status_code=204)
def delete_corrections(request: Request) -> Response:
    """„Alle löschen“: die ganze Korrektur-Sammlung, sofort und endgültig."""
    with db.connect(_settings(request).db_path) as conn:
        removed = corrections.delete_all(conn)
    log.info("Korrektur-Sammlung gelöscht (%d Stellen)", removed)
    return Response(status_code=204)
