"""Live-Aktualisierung des Büros: Server-Sent Events statt Warten auf den nächsten Abgleich.

Jeder Commit mit Änderungen an der Datenbank (`db.on_change`: neues Diktat, Zuordnen, übertragen,
Löschen, Aufräumen, Kurzcode-Abruf, Behandler) erhöht eine Versionsnummer. `GET /api/v1/events`
schickt nur diese Nummer – nie Transkript, Ziffern, Patientennummer oder Kürzel; die Seite lädt
daraufhin über die bestehende API neu. Ein Prozess (uvicorn ohne Worker), daher reicht ein Zähler
im Speicher. Hinter Caddy ohne Pufferung und ohne gzip (`infra/tls/Caddyfile`).
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from medvox import auth
from medvox.auth import require_session

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_session)])

RETRY_MS = 3_000  # so schnell baut der Browser eine abgerissene Verbindung neu auf


class ChangeHub:
    """Versionszähler; `bump` ist aus jedem Thread aufrufbar, `wait` nur in der Event-Loop."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.version = 0
        self._loop: asyncio.AbstractEventLoop | None = None
        self._changed = asyncio.Event()

    def bind(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def notify(self, path: Path) -> None:
        """Listener für `db.on_change`: nur Änderungen an der eigenen Datenbank zählen."""
        if path == self.db_path and self._loop is not None and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._bump)

    def _bump(self) -> None:
        self.version += 1
        changed, self._changed = self._changed, asyncio.Event()
        changed.set()

    async def wait(self, since: int, timeout: float) -> int:
        """Wartet höchstens `timeout` Sekunden auf eine Version nach `since`; liefert die aktuelle."""
        if self.version == since:
            try:
                await asyncio.wait_for(self._changed.wait(), timeout)
            except TimeoutError:
                pass
        return self.version


def _event(name: str, version: int) -> str:
    return f"event: {name}\ndata: {version}\n\n"


async def stream(request: Request, hub: ChangeHub) -> AsyncIterator[str]:
    """Erst die aktuelle Version (Neuladen nach Verbindungsaufbau), dann jede Änderung.

    Ein `ping` alle `events_heartbeat_s` hält Proxys wach, zeigt der Seite, dass die Verbindung noch
    lebt (`app/src/live.ts`), und prüft die Sitzung erneut (Abmelden beendet den Strom). Nach
    `events_max_s` endet der Strom, der Browser verbindet sich neu. Beim Neustart bricht uvicorn offene
    Ströme nach `--timeout-graceful-shutdown` ab (`infra/server/run.sh`).
    """
    settings = request.app.state.settings
    token = request.cookies.get(auth.SESSION_COOKIE)
    version = hub.version
    yield f"retry: {RETRY_MS}\n" + _event("changed", version)
    end = time.monotonic() + settings.events_max_s
    while (left := end - time.monotonic()) > 0:
        current = await hub.wait(version, min(settings.events_heartbeat_s, left))
        if current != version:
            version = current
            yield _event("changed", version)
            continue
        if await request.is_disconnected():
            return
        if not await asyncio.to_thread(auth.session_valid, settings.db_path, token):
            return
        yield _event("ping", version)


@router.get("/events")
def events(request: Request) -> StreamingResponse:
    return StreamingResponse(
        stream(request, request.app.state.changes),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
