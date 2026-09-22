"""FastAPI-Anwendung des MedVox-Servers.

Start im Entwicklungsbetrieb: `make dev` (siehe server/Makefile).
"""

from fastapi import FastAPI
from pydantic import BaseModel

from medvox import __version__


class Health(BaseModel):
    """Antwort von GET /api/v1/health."""

    status: str
    whisper: str


app = FastAPI(title="MedVox Server", version=__version__)


@app.get("/api/v1/health", response_model=Health)
def health() -> Health:
    """Lebenszeichen des Servers.

    `whisper` bleibt "unknown", bis die Anbindung an den whisper-server
    (WP-1/WP-2) den tatsächlichen Zustand meldet.
    """
    return Health(status="ok", whisper="unknown")
