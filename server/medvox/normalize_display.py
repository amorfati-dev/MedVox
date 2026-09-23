"""Anzeigefassung des Transkripts: das, was der Behandler liest und ins PVS kopiert.

Wendet dieselbe Zahn- und Code-Normalisierung an wie `normalize` („drei sechs“ -> 36,
„BEMA dreizehn a“ -> BEMA 13a, „Ä neun drei fünf d“ -> Ä935d), lässt aber die Flächen
so stehen, wie sie diktiert wurden („mesial okklusal distal“, nicht „mod“). Die interne
Form für den Extraktor bleibt unverändert `normalize(text).text`.
"""

from __future__ import annotations

import re

from medvox.normalize import _SF, _SURFACE_MOD, _SURFACE_WORD, _SURFACE_WORDS, normalize

# Hängt hinter dem Flächenbuchstaben und überlebt das Aufräumen in `normalize`,
# damit das diktierte Wort danach wieder eingesetzt werden kann.
_KEEP = "\x03"
_KEPT = re.compile(rf"[modblpi]+{_KEEP}")
_SURFACE = re.compile(f"{_SURFACE_WORD.pattern}|{_SURFACE_MOD.pattern}", re.I)


def display_text(text: str) -> str:
    """Transkript mit FDI-Nummern und zusammengefügten Codes, Flächen wie diktiert."""
    originals: list[str] = []

    def mark(m: re.Match) -> str:
        originals.append(m.group())
        letters = _SURFACE_WORDS[m.group(1).lower()] if m.group(1) else "mod"
        return letters + _SF + _KEEP

    def surfaces(t: str) -> str:
        # Wie `normalize._surfaces`, aber ohne Zusammenziehen zu „mod“: jedes Wort bleibt ein Token.
        return _SURFACE.sub(mark, t)

    shown = normalize(text, surfaces).text
    words = iter(originals)
    return _KEPT.sub(lambda _: next(words), shown)
