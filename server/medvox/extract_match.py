"""Fundstellen im gefalteten Diktat: diktierte Ziffern und Katalog-Keywords (WP-8).

Diktierte Ziffern mit System ("BEMA 13a", "GOZ 2100", "BEMA Ziffer Ä935d") werden
zuerst erkannt und haben Vorrang. Danach gilt für Keywords Longest-Match-wins: von
überlappenden Treffern bleibt der längste ("offene kürettage" schlägt "kürettage"),
bei gleicher Länge der frühere. Treffer nur an Wortgrenzen; das letzte Wort eines
Keywords darf eine Flexionsendung tragen ("Füllungen" trifft "füllung").
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from medvox.extract_catalog import Catalog, Entry, fold

_SYSTEMS = {"bema": "BEMA", "goz": "GOZ", "goae": "GOÄ"}
_EXPLICIT = re.compile(
    r"(?<![a-z0-9])(bema|goz|goae)[\s-]+(?:ziffer\s+|nr\.?\s+)?((?=[a-z]*\d)[a-z0-9]{1,7})(?![a-z0-9])"
)
_ENDING = "(?:e|en|er|es|em|n|s)?"


@dataclass(frozen=True)
class Hit:
    entry: Entry
    start: int
    end: int
    keyword: str  # gefaltetes Keyword bzw. die diktierte Ziffer
    code_word: bool  # die Ziffer oder amtliche Kurzbezeichnung selbst wurde diktiert
    via: Entry | None = None  # diktierte Ziffer im anderen System, vom Patiententyp auf ``entry`` umgestellt


def _keyword_pattern(keyword: str) -> re.Pattern[str]:
    words = [w for w in re.split(r"[\s-]+", fold(keyword)) if w]
    ending = _ENDING if words[-1].isalpha() and len(words[-1]) >= 5 else ""
    body = r"[\s-]+".join(re.escape(w) for w in words)
    return re.compile(rf"(?<![a-z0-9]){body}{ending}(?![a-z0-9])")


@lru_cache(maxsize=4)
def _patterns(catalog: Catalog) -> tuple[tuple[re.Pattern[str], str, Entry], ...]:
    return tuple((_keyword_pattern(k), fold(k), e) for e in catalog.entries for k in e.keywords)


def find_hits(catalog: Catalog, folded: str) -> tuple[list[Hit], list[str]]:
    """Alle Fundstellen in Textreihenfolge plus diktierte Ziffern, die nicht im Katalog v1 stehen."""
    taken: list[Hit] = []
    unknown: list[str] = []
    for m in _EXPLICIT.finditer(folded):
        system = _SYSTEMS[m.group(1)]
        entry = catalog.find_code(system, m.group(2))
        if entry is None:
            unknown.append(f"{system} {m.group(2)}")
            continue
        taken.append(Hit(entry, m.start(), m.end(), m.group(2), True))
    candidates: list[Hit] = []
    for pattern, keyword, entry in _patterns(catalog):
        for m in pattern.finditer(folded):
            candidates.append(Hit(entry, m.start(), m.end(), keyword, catalog.is_code_word(entry, keyword)))
    candidates.sort(key=lambda h: (h.start - h.end, h.start))
    for hit in candidates:
        if all(hit.end <= t.start or hit.start >= t.end for t in taken):
            taken.append(hit)
    return sorted(taken, key=lambda h: h.start), unknown
