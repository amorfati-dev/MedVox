"""Rate-Limit je Client-IP für Login und Transfer-Abruf (im Speicher)."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

LOOPBACK = ("127.0.0.1", "::1")


def client_ip(request: Request) -> str:
    """Client-IP; hinter dem lokalen Reverse-Proxy (Caddy, WP-3) aus X-Forwarded-For."""
    direct = request.client.host if request.client else "unbekannt"
    forwarded = request.headers.get("x-forwarded-for", "")
    if direct in LOOPBACK and forwarded:
        return forwarded.split(",")[0].strip()
    return direct


class RateLimiter:
    """Gleitendes Fenster je Schlüssel (hier: Client-IP), im Speicher."""

    def __init__(self, limit: int, window_s: float = 60.0) -> None:
        self.limit = limit
        self.window_s = window_s
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= now - self.window_s:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True

    def check(self, request: Request, detail: str) -> None:
        """429 mit deutscher Meldung, wenn die Client-IP ihr Fenster ausgeschöpft hat."""
        if not self.allow(client_ip(request)):
            raise HTTPException(status_code=429, detail=detail)
