"""Routen für die Korrektur am iPad: Ziffern aus berichtigtem Text neu berechnen, Katalog fürs Katalog-Blatt.

`POST /api/v1/analyze` ist dieselbe Kette wie `/transcribe` (Lexikon -> Normalisierer -> Extraktor,
`build_response`, mit dem Wörterbuch der Praxis), nur ohne Audio: der Text kommt aus dem Transkript-Editor
oder – mit `draft` – als Probe von der Wörterbuch-Seite. `GET /api/v1/catalog`
liefert die Positionen aus `catalog_v1.json`, die für den Patiententyp vorgeschlagen werden dürfen –
nach denselben Regeln wie der Extraktor (`extract_patient.kind`): Kasse = BEMA (auch Analogpositionen)
plus Privatpositionen der Zuzahlungs-Liste, Privat = GOZ/GOÄ (Zuschlag 0500–0530 nur hier). Eine freie
Ziffern-Eingabe gibt es nicht. In Logs stehen nur Anzahlen, nie Text.
"""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from medvox import lexicon_entries
from medvox.auth import require_session
from medvox.extract_catalog import load_catalog
from medvox.extract_patient import kind
from medvox.routes_transcribe import TranscribeResponse, build_response

log = logging.getLogger("medvox.correction")
router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_session)])

PatientType = Literal["kasse", "privat"]
# Art, die beim jeweiligen Patiententyp nie vorgeschlagen wird (wie `settle` im Extraktor)
_FOREIGN = {"kasse": "goz", "privat": "bema"}


class Draft(BaseModel):
    """Probe: eine noch nicht gespeicherte Ersetzung, die nur für diese Anfrage dazukommt."""

    wrong: str = Field(max_length=200)
    right: str = Field(max_length=200)


class AnalyzeIn(BaseModel):
    text: str = Field(max_length=50_000)  # ganzer, am iPad berichtigter Text aller Abschnitte
    patient_type: PatientType = "kasse"
    draft: Draft | None = None


class CatalogItem(BaseModel):
    code: str
    system: str  # BEMA | GOZ | GOÄ
    title: str
    area: str  # Fachbereich (Diagnostik … PAR)
    points: int | None  # nie angezeigt, nur damit eine ergänzte Position wie ein Vorschlag aussieht
    kind: str  # bema | goz | zuzahlung – wie im Vorschlag
    evident: str | None = None  # vom Behandler bestätigte Evident-Kurzform, sonst None
    # Füllungsfamilie nach Flächenzahl 1–4 (13a–13d, 2060–2120, 2150/2160/2170/2170), sonst leer
    family: list[str] = []
    # Anzahl je Zeile am iPad mit − / + änderbar (je Kanal, mehrmals je Sitzung) und bestätigte Höchstzahl
    counted: bool = False
    max_count: int | None = None


class CatalogOut(BaseModel):
    version: str
    patient_type: PatientType
    entries: list[CatalogItem]


@router.post("/analyze", response_model=TranscribeResponse)
def analyze_text(body: AnalyzeIn, request: Request) -> TranscribeResponse:
    """Ziffern neu berechnen aus dem ganzen Text; Dauer und Wartezeit sind 0 (kein Audio).

    Mit `draft` kommt der Entwurf zu den eingeschalteten Ersetzungen dazu, geprüft nach denselben
    Schutzregeln wie beim Speichern (422 mit Begründung).
    """
    path = request.app.state.settings.db_path
    extra = lexicon_entries.active(path).replacements
    if body.draft is not None:
        current = [e for e in lexicon_entries.list_entries(path) if e.active]
        try:
            wrong, right = lexicon_entries.check_replacement(body.draft.wrong, body.draft.right, current)
        except lexicon_entries.Rejected as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        extra = {**extra, tuple(wrong.lower().split()): right}
    result = build_response(body.text, 0.0, 0.0, body.patient_type, extra)
    log.info("Text neu berechnet (%d Zeichen, %d Ziffern)", len(body.text), len(result.codes))
    return result


@router.get("/catalog", response_model=CatalogOut)
def catalog(patient_type: PatientType = "kasse") -> CatalogOut:
    """Positionen des Katalogs v1, die für diesen Patiententyp vorgeschlagen werden dürfen, in Katalogreihenfolge."""
    cat = load_catalog()
    entries = []
    for e in cat.entries:
        k = kind(cat, e, patient_type)
        if k == _FOREIGN[patient_type]:
            continue
        counted, most = cat.stepper(e)
        entries.append(CatalogItem(
            code=e.code, system=e.system, title=e.title, area=e.area, points=e.points, kind=k,
            evident=e.evident, family=list(e.family), counted=counted, max_count=most,
        ))
    return CatalogOut(version=cat.version, patient_type=patient_type, entries=entries)
