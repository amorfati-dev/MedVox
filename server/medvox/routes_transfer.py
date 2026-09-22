"""Routen für den Kurzcode-Transfer zum Rezeptions-PC.

Anlegen erfordert die Sitzung des Behandlers; der Abruf ist ohne Login möglich
(Rezeptions-Browser), dafür je IP auf 10 Abrufe pro Minute begrenzt.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from medvox import ratelimit, transfer
from medvox.auth import require_session

log = logging.getLogger("medvox.transfer")
router = APIRouter(prefix="/api/v1")


class TransferCreate(BaseModel):
    transcript: str = Field(max_length=20_000)
    codes: list[str] = Field(default_factory=list, max_length=100)


class TransferCreated(BaseModel):
    code: str
    expires_at: str


class TransferRead(BaseModel):
    transcript: str
    codes: list[str]
    created_at: str


@router.post("/transfer", response_model=TransferCreated, dependencies=[Depends(require_session)])
def create(body: TransferCreate, request: Request) -> TransferCreated:
    settings = request.app.state.settings
    entry = transfer.create_transfer(
        settings.db_path, body.transcript, body.codes, settings.transfer_ttl_s
    )
    log.info("Transfer angelegt (%d Zeichen, %d Ziffern)", len(body.transcript), len(body.codes))
    return TransferCreated(code=entry.code, expires_at=transfer.iso(entry.expires_at))


@router.get("/transfer/{code}", response_model=TransferRead)
def read(code: str, request: Request) -> TransferRead:
    limiter: ratelimit.RateLimiter = request.app.state.transfer_limiter
    limiter.check(request, "Zu viele Abrufe. Bitte eine Minute warten.")
    entry = transfer.get_transfer(request.app.state.settings.db_path, code)
    if entry is None:
        raise HTTPException(status_code=404, detail="Kein Diktat unter diesem Code (oder abgelaufen).")
    return TransferRead(
        transcript=entry.transcript, codes=entry.codes, created_at=transfer.iso(entry.created_at)
    )
