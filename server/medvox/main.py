"""FastAPI-Anwendung des MedVox-Servers.

Start im Entwicklungsbetrieb: `make dev` (siehe server/Makefile).
Konfiguration über Umgebungsvariablen: `medvox/settings.py`, server/README.md.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from medvox import __version__, db, routes_auth, routes_transcribe, routes_transfer
from medvox.settings import Settings
from medvox.transfer import RateLimiter


def create_app(
    settings: Settings | None = None, transport: httpx.BaseTransport | None = None
) -> FastAPI:
    """Baut die App; `transport` erlaubt Tests einen gemockten whisper-server."""
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        db.init_db(settings.db_path)
        app.state.http = httpx.Client(transport=transport)
        try:
            yield
        finally:
            app.state.http.close()

    app = FastAPI(title="MedVox Server", version=__version__, lifespan=lifespan)
    app.state.settings = settings
    app.state.transfer_limiter = RateLimiter(settings.transfer_lookups_per_min)
    app.include_router(routes_transcribe.router)
    app.include_router(routes_auth.router)
    app.include_router(routes_transfer.router)
    return app


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
app = create_app()
