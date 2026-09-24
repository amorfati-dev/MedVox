"""FastAPI-Anwendung des MedVox-Servers.

Start im Entwicklungsbetrieb: `make dev` (siehe server/Makefile).
Konfiguration über Umgebungsvariablen: `medvox/settings.py`, server/README.md.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from medvox import (
    __version__,
    db,
    routes_auth,
    routes_correction,
    routes_dentists,
    routes_patients,
    routes_transcribe,
    routes_transfer,
)
from medvox.ratelimit import RateLimiter
from medvox.settings import Settings

log = logging.getLogger("medvox.main")


async def purge_loop(settings: Settings) -> None:
    """Löscht abgelaufene Transfers, Sitzungen und Patientendiktate periodisch, unabhängig von Zugriffen (WP-11)."""
    while True:
        await asyncio.sleep(settings.purge_interval_s)
        try:
            await asyncio.to_thread(db.purge_expired_at, settings.db_path)
        except Exception:
            log.exception("Periodisches Aufräumen fehlgeschlagen")


def create_app(
    settings: Settings | None = None, transport: httpx.BaseTransport | None = None
) -> FastAPI:
    """Baut die App; `transport` erlaubt Tests einen gemockten whisper-server."""
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        db.init_db(settings.db_path)
        db.purge_expired_at(settings.db_path)
        # Prompt-Datei bewusst schon beim Start lesen, damit die Warnung bei fehlender
        # Datei (FALLBACK_PROMPT) sofort im Log steht und nicht erst beim ersten Diktat.
        settings.whisper_prompt
        app.state.http = httpx.Client(transport=transport)
        sweep = asyncio.create_task(purge_loop(settings))
        try:
            yield
        finally:
            sweep.cancel()
            app.state.http.close()

    app = FastAPI(title="MedVox Server", version=__version__, lifespan=lifespan)
    app.state.settings = settings
    app.state.transfer_limiter = RateLimiter(settings.transfer_lookups_per_min)
    app.state.login_limiter = RateLimiter(settings.login_attempts_per_min)
    app.include_router(routes_transcribe.router)
    app.include_router(routes_auth.router)
    app.include_router(routes_transfer.router)
    app.include_router(routes_patients.router)
    app.include_router(routes_dentists.router)
    app.include_router(routes_correction.router)
    return app


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
app = create_app()
