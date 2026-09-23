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


def display_text(text: str) -> str:
    """Transkript mit FDI-Nummern und zusammengefügten Codes, Flächen wie diktiert."""
    originals: list[str] = []

    def mark(letters: str):
        def sub(m: re.Match) -> str:
            originals.append(m.group())
            return (letters or _SURFACE_WORDS[m.group(1).lower()]) + _SF + _KEEP
        return sub

    def surfaces(t: str) -> str:
        # Wie `normalize._surfaces`, aber ohne Zusammenziehen zu „mod“: jedes Wort bleibt ein Token.
        t = _SURFACE_WORD.sub(mark(""), t)
        return _SURFACE_MOD.sub(mark("mod"), t)

    shown = normalize(text, surfaces).text
    words = iter(originals)
    return _KEPT.sub(lambda _: next(words), shown)
