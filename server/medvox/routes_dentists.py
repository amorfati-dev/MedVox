"""Routen für die Behandlerliste (`medvox/dentists.py`): auflisten, anlegen, ändern, inaktiv setzen.

Nur mit Sitzung, aber ohne weitere Rechte: jede angemeldete Person darf die Liste pflegen. Die
Liste nennt auch, nach wie vielen Sekunden ohne Bedienung das iPad wieder fragt, wer diktiert.
"""

from __future__ import annotations

import logging
import pathlib
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, StringConstraints

from medvox import dentists
from medvox.auth import require_session

log = logging.getLogger("medvox.dentists")
router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_session)])

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
# Evident-/BEMA-Behandlernummer: optional, leer = keine
PractitionerId = Annotated[str, StringConstraints(strip_whitespace=True, max_length=20, pattern=r"^[A-Za-z0-9./-]*$")]
NOT_FOUND = "Behandler nicht gefunden."


class DentistOut(BaseModel):
    id: int
    name: str
    practitioner_id: str | None
    active: bool


class DentistList(BaseModel):
    dentists: list[DentistOut]  # aktive zuerst
    idle_s: int  # so lange ohne Bedienung, dann fragt das iPad neu, wer diktiert


class DentistCreate(BaseModel):
    name: Name
    practitioner_id: PractitionerId | None = None


class DentistUpdate(BaseModel):
    """Nur die mitgeschickten Felder ändern sich; `active: true` holt einen Behandler zurück."""

    name: Name | None = None
    practitioner_id: PractitionerId | None = None
    active: bool | None = None


def _out(d: dentists.Dentist) -> DentistOut:
    return DentistOut(id=d.id, name=d.name, practitioner_id=d.practitioner_id, active=d.active)


def _db(request: Request) -> pathlib.Path:
    return request.app.state.settings.db_path


@router.get("/dentists", response_model=DentistList)
def list_all(request: Request) -> DentistList:
    return DentistList(
        dentists=[_out(d) for d in dentists.list_dentists(_db(request))],
        idle_s=request.app.state.settings.dentist_idle_s,
    )


@router.post("/dentists", response_model=DentistOut)
def create(body: DentistCreate, request: Request) -> DentistOut:
    created = dentists.create_dentist(_db(request), body.name, body.practitioner_id or None)
    log.info("Behandler angelegt (ID %d)", created.id)
    return _out(created)


@router.patch("/dentists/{dentist_id}", response_model=DentistOut)
def update(dentist_id: int, body: DentistUpdate, request: Request) -> DentistOut:
    changes = body.model_dump(exclude_unset=True)
    if changes.get("name", "") is None or changes.get("active", False) is None:
        raise HTTPException(status_code=422, detail="Name und aktiv dürfen nicht leer sein.")
    if "practitioner_id" in changes:
        changes["practitioner_id"] = changes["practitioner_id"] or None
    updated = dentists.update_dentist(_db(request), dentist_id, changes)
    if updated is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return _out(updated)


@router.delete("/dentists/{dentist_id}", response_model=DentistOut)
def deactivate(dentist_id: int, request: Request) -> DentistOut:
    """Inaktiv setzen statt löschen: nicht mehr zur Auswahl, alte Diktate behalten ihren Behandler."""
    updated = dentists.update_dentist(_db(request), dentist_id, {"active": False})
    if updated is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    log.info("Behandler inaktiv gesetzt (ID %d)", dentist_id)
    return _out(updated)
