"""Routen für den Kurzcode-Transfer zum Rezeptions-PC.

Anlegen erfordert die Sitzung des Behandlers; der Abruf ist ohne Login möglich
(Rezeptions-Browser), dafür je IP auf 10 Abrufe pro Minute begrenzt.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from medvox import ratelimit, transfer
from medvox.auth import require_session

log = logging.getLogger("medvox.transfer")
router = APIRouter(prefix="/api/v1")


class TransferPosition(BaseModel):
    """Eine übergebene Position – nur zur Anzeige an der Rezeption (Zuzahlung, Kassenanteil)."""

    tooth: int | None = Field(default=None, ge=11, le=85)  # FDI-Nummer, None = ohne Zahn
    code: str = Field(min_length=1, max_length=16)
    kind: Literal["bema", "goz", "zuzahlung", "kassenanteil"]


class TransferCreate(BaseModel):
    transcript: str = Field(max_length=20_000)
    codes: list[str] = Field(default_factory=list, max_length=100)
    patient_type: Literal["kasse", "privat"] | None = None  # ältere iPad-Versionen senden nichts
    positions: list[TransferPosition] = Field(default_factory=list, max_length=200)
    # gespeichertes Diktat (PUT /dictations/{id}), das der Abruf als übertragen schließt
    dictation_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9-]{8,64}$")
    dictation_revision: int | None = Field(default=None, ge=1)  # gespeicherter Stand genau dieses Inhalts


class TransferCreated(BaseModel):
    code: str
    expires_at: str


class HandoverOut(BaseModel):
    """Früher an der Rezeption abgeholter Stand desselben Diktats: Zeitpunkt und Evident-Zeilen."""

    fetched_at: str
    codes: list[str]


def handover_out(h: dict) -> HandoverOut:
    return HandoverOut(fetched_at=transfer.iso(h["fetched_at"]), codes=h["codes"])


class TransferRead(BaseModel):
    transcript: str
    codes: list[str]
    created_at: str
    patient_type: str | None = None
    positions: list[TransferPosition] = []
    earlier: list[HandoverOut] = []  # schon abgeholte Stände desselben Diktats: nur die Änderung eintragen


@router.post("/transfer", response_model=TransferCreated, dependencies=[Depends(require_session)])
def create(body: TransferCreate, request: Request) -> TransferCreated:
    settings = request.app.state.settings
    entry = transfer.create_transfer(
        settings.db_path,
        body.transcript,
        body.codes,
        settings.transfer_ttl_s,
        body.patient_type,
        [p.model_dump() for p in body.positions],
        body.dictation_id,
        body.dictation_revision,
    )
    log.info("Transfer angelegt (%d Zeichen, %d Ziffern)", len(body.transcript), len(body.codes))
    return TransferCreated(code=entry.code, expires_at=transfer.iso(entry.expires_at))


@router.get("/transfer/{code}", response_model=TransferRead)
def read(code: str, request: Request) -> TransferRead:
    limiter: ratelimit.RateLimiter = request.app.state.transfer_limiter
    limiter.check(request, "Zu viele Abrufe. Bitte eine Minute warten.")
    try:
        entry = transfer.get_transfer(request.app.state.settings.db_path, code)
    except transfer.AlreadyTransferred as done:
        when = datetime.fromtimestamp(done.closed_at).strftime("%d.%m.%Y um %H:%M Uhr")
        raise HTTPException(
            status_code=410,
            detail=f"Dieses Diktat wurde bereits am {when} übertragen (Büro oder anderer Kurzcode) oder gelöscht"
            " – nicht erneut in Evident eintragen.",
        ) from None
    if entry is None:
        raise HTTPException(status_code=404, detail="Kein Diktat unter diesem Code (oder abgelaufen).")
    return TransferRead(
        transcript=entry.transcript,
        codes=entry.codes,
        created_at=transfer.iso(entry.created_at),
        patient_type=entry.patient_type,
        positions=[TransferPosition(**p) for p in entry.positions],
        earlier=[handover_out(h) for h in entry.earlier],
    )
