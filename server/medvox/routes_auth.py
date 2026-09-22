"""Routen für Login, Logout und Sitzungsabfrage (ein Nutzer)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from medvox import auth, ratelimit

log = logging.getLogger("medvox.auth")
router = APIRouter(prefix="/api/v1")


class LoginRequest(BaseModel):
    password: str


def _is_https(request: Request) -> bool:
    forwarded = request.headers.get("x-forwarded-proto", "")
    return request.url.scheme == "https" or forwarded.lower() == "https"


@router.post("/login", status_code=204, response_class=Response)
def login(body: LoginRequest, request: Request, response: Response) -> Response:
    settings = request.app.state.settings
    limiter: ratelimit.RateLimiter = request.app.state.login_limiter
    limiter.check(request, "Zu viele Anmeldeversuche. Bitte eine Minute warten.")
    if not settings.password_hash:
        log.error("MEDVOX_PASSWORD_HASH ist nicht gesetzt (make set-password)")
        raise HTTPException(status_code=503, detail="Auf dem Server ist kein Passwort konfiguriert.")
    if not auth.verify_password(body.password, settings.password_hash):
        log.warning("Login fehlgeschlagen")
        raise HTTPException(status_code=401, detail="Das Passwort ist falsch.")
    token = auth.create_session(settings.db_path, settings.session_ttl_s)
    response.set_cookie(
        auth.SESSION_COOKIE,
        token,
        max_age=settings.session_ttl_s,
        httponly=True,
        samesite="strict",
        secure=_is_https(request),
        path="/",
    )
    response.status_code = 204
    return response


@router.post("/logout", status_code=204, response_class=Response)
def logout(request: Request, response: Response) -> Response:
    settings = request.app.state.settings
    auth.delete_session(settings.db_path, request.cookies.get(auth.SESSION_COOKIE))
    response.delete_cookie(auth.SESSION_COOKIE, path="/")
    response.status_code = 204
    return response


@router.get("/session")
def session(request: Request) -> dict[str, str]:
    auth.require_session(request)
    return {"status": "ok"}
