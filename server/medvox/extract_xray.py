"""Bissflügelaufnahmen beim Privatpatienten: GOÄ Ä5000 zählt je Projektion.

Diktiert wird die Leistung als „Bissflügel(aufnahme)“ (Katalog: BEMA Ä925a, Paar GOÄ Ä5000). Steht direkt
dahinter im selben Teilsatz „rechts und links“ oder „beidseits“, sind es zwei Projektionen (Ä5000 zweimal);
sonst bleibt es bei einer mit dem Prüfhinweis des Paares („zählt je Projektion … Anzahl prüfen“) – nie geraten.
"""

from __future__ import annotations

import re

from medvox.extract_draft import Draft
from medvox.extract_text import TextContext

BOTH_SIDES = re.compile(r"\s*(?:rechts\s+und\s+links|links\s+und\s+rechts|beidseits|beidseitig\w*)(?![a-z])")
_BITEWING = "bissfluegel"
_PROJECTION_NOTE = "GOÄ Ä5000 zählt je Projektion"


def bitewing_projections(ctx: TextContext, drafts: list[Draft]) -> None:
    """Privat: Ä5000 aus „Bissflügel … rechts und links/beidseits“ zählt zwei Projektionen, ohne Prüfhinweis."""
    for d in drafts:
        if (d.entry.system, d.entry.code) != ("GOÄ", "Ä5000") or not d.hits:
            continue
        if not all(_BITEWING in t.hit.keyword for t in d.hits):
            continue
        if any(_both_sides_after(ctx, t.hit.end) for t in d.hits):
            d.count = 2
            d.decide = [f for f in d.decide if not f.startswith(_PROJECTION_NOTE)]
            d.limit_note = "rechts und links: 2 Projektionen"


def _both_sides_after(ctx: TextContext, end: int) -> bool:
    _, clause_end = ctx.clause(end - 1)
    return bool(BOTH_SIDES.match(ctx.folded, end, clause_end))
