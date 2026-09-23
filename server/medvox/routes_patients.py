"""Routen für Diktate je Patient (Übertragung später aus dem Büro), siehe `medvox/patients.py`.

Alles nur mit Sitzung: die Liste enthält Transkripte. In Logs stehen nur Anzahlen, nie
Transkripttext oder Patientennummer.
"""

from __future__ import annotations

import logging
import pathlib
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response
from pydantic import BaseModel, Field

from medvox import patients
from medvox.auth import require_session
from medvox.routes_transcribe import SuggestionOut
from medvox.transfer import iso

log = logging.getLogger("medvox.patients")
router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_session)])

NUMBER_PATTERN = r"^[0-9]{1,12}$"  # Evident-Patientennummer, nur Ziffern
DictationId = Annotated[str, Path(pattern=r"^[A-Za-z0-9-]{8,64}$")]
Text = Annotated[str, Field(max_length=2_000)]
Code = Annotated[str, Field(max_length=64)]


class PatientCreate(BaseModel):
    number: str = Field(pattern=NUMBER_PATTERN)


class DictationIn(BaseModel):
    """Stand eines Diktats vom iPad: dieselben Felder wie die Antwort von /transcribe plus Auswahl."""

    patient: str | None = Field(default=None, pattern=NUMBER_PATTERN)  # None = Zuordnung behalten
    transcript: str = Field(default="", max_length=50_000)
    patient_type: Literal["kasse", "privat"] | None = None
    codes: list[Code] = Field(default_factory=list, max_length=200)
    suggestions: list[SuggestionOut] = Field(default_factory=list, max_length=500)
    planned: list[SuggestionOut] = Field(default_factory=list, max_length=200)
    notes: list[Text] = Field(default_factory=list, max_length=200)
    deselected: list[Code] = Field(default_factory=list, max_length=200)  # abgewählte Ziffern ("2x 41a")
    adopted: list[Code] = Field(default_factory=list, max_length=200)  # übernommene Optionen (optionKey)


class DictationOut(DictationIn):
    id: str
    patient_id: int | None
    revision: int
    created_at: str
    updated_at: str


class PatientOut(BaseModel):
    id: int
    number: str
    created_at: str
    updated_at: str
    dictations: int  # offene (noch nicht übertragene) Diktate
    transferred: int  # schon übertragene Diktate
    transferred_at: str | None


class PatientDetail(PatientOut):
    items: list[DictationOut]


class PatientList(BaseModel):
    patients: list[PatientOut]
    unassigned: list[DictationOut]  # Diktate „ohne Patient“


class Seen(BaseModel):
    id: str
    revision: int


class TransferredIn(BaseModel):
    seen: list[Seen] = Field(max_length=200)  # die im Büro angezeigten Diktate


class AssignIn(BaseModel):
    dictation_id: str = Field(pattern=r"^[A-Za-z0-9-]{8,64}$")


def _patient_out(p: patients.Patient) -> PatientOut:
    return PatientOut(
        id=p.id, number=p.number, created_at=iso(p.created_at), updated_at=iso(p.updated_at),
        dictations=p.open_count, transferred=p.transferred_count,
        transferred_at=iso(p.transferred_at) if p.transferred_at is not None else None,
    )


def _dictation_out(d: patients.Dictation) -> DictationOut:
    return DictationOut(
        **d.data, patient=d.number, id=d.id, patient_id=d.patient_id, revision=d.revision,
        created_at=iso(d.created_at), updated_at=iso(d.updated_at),
    )


def _detail(found: tuple[patients.Patient, list[patients.Dictation]] | None) -> PatientDetail:
    if found is None:
        raise HTTPException(status_code=404, detail="Patient nicht gefunden (übertragen, gelöscht oder älter als 24 Stunden).")
    patient, items = found
    return PatientDetail(**_patient_out(patient).model_dump(), items=[_dictation_out(d) for d in items])


def _db(request: Request) -> pathlib.Path:
    return request.app.state.settings.db_path


@router.post("/patients", response_model=PatientOut)
def create(body: PatientCreate, request: Request) -> PatientOut:
    return _patient_out(patients.create_patient(_db(request), body.number))


@router.get("/patients", response_model=PatientList)
def list_all(request: Request) -> PatientList:
    found, loose = patients.list_patients(_db(request))
    return PatientList(patients=[_patient_out(p) for p in found], unassigned=[_dictation_out(d) for d in loose])


@router.get("/patients/{patient_id}", response_model=PatientDetail)
def get(patient_id: int, request: Request) -> PatientDetail:
    return _detail(patients.get_patient(_db(request), patient_id))


@router.post("/patients/{patient_id}/dictations", response_model=DictationOut)
def append(patient_id: int, body: AssignIn, request: Request) -> DictationOut:
    """Hängt ein gespeichertes Diktat (z. B. „ohne Patient“) an diesen Patienten."""
    moved = patients.assign_dictation(_db(request), body.dictation_id, patient_id)
    if moved is None:
        raise HTTPException(status_code=404, detail="Diktat oder Patient nicht gefunden.")
    return _dictation_out(moved)


@router.post("/patients/{patient_id}/transferred", response_model=PatientDetail)
def transferred(patient_id: int, body: TransferredIn, request: Request) -> PatientDetail:
    seen = {s.id: s.revision for s in body.seen}
    detail = _detail(patients.mark_transferred(_db(request), patient_id, seen))
    log.info("Patient als übertragen markiert (%d Diktate noch offen)", len(detail.items))
    return detail


@router.delete("/patients/{patient_id}", status_code=204)
def delete(patient_id: int, request: Request) -> Response:
    if not patients.delete_patient(_db(request), patient_id):
        raise HTTPException(status_code=404, detail="Patient nicht gefunden.")
    return Response(status_code=204)


@router.put("/dictations/{dictation_id}", response_model=DictationOut)
def save(dictation_id: DictationId, body: DictationIn, request: Request) -> DictationOut:
    """Speichert den Stand eines Diktats (anlegen oder ersetzen); mit `patient` beim Patienten."""
    data = body.model_dump(exclude={"patient"})
    saved = patients.save_dictation(_db(request), dictation_id, data, body.patient)
    log.info("Diktat gespeichert (%d Zeichen, %d Ziffern)", len(body.transcript), len(body.codes))
    return _dictation_out(saved)


@router.delete("/dictations/{dictation_id}", status_code=204)
def delete_dictation(dictation_id: DictationId, request: Request) -> Response:
    if not patients.delete_dictation(_db(request), dictation_id):
        raise HTTPException(status_code=404, detail="Diktat nicht gefunden.")
    return Response(status_code=204)
