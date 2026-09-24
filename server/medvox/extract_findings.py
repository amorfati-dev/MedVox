"""Befunde je Zahn fürs Zahnschema (Ship 3): Zahn, diktierte Flächen, Befundwörter.

Reine Funktion über dem normalisierten Diktat, mit derselben Zahn-Zuordnung (``TextContext.teeth_for``)
und derselben Verneinung wie die Ziffern: „keine Karies“ ergibt keinen Befund. Die Befundwörter stehen in
``catalog/befunde.json``; die längste passende Phrase gewinnt („Karies profunda“ vor „Karies“). Aus einem
Befund wird nie eine Ziffer – Ziffern schlägt nur der Katalog vor (``extract.py``).

Ergebnis: jeder diktierte Zahn einmal, in Diktatreihenfolge, mit allen Flächen und Befunden; Befunde ohne
Zahn stehen zuletzt unter ``tooth=None``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from medvox.extract_catalog import fold
from medvox.extract_text import TextContext
from medvox.normalize import ToothRef

FINDINGS_PATH = Path(__file__).resolve().parent / "catalog" / "befunde.json"


@dataclass(frozen=True)
class ToothFindings:
    tooth: int | None  # FDI-Nummer, None = Befund ohne Zahn
    surfaces: str = ""  # diktierte Flächen ("mod"), zusammengeführt
    findings: tuple[str, ...] = ()  # Befundwörter wie in befunde.json ("Karies profunda")


@lru_cache(maxsize=1)
def _pattern(path: Path = FINDINGS_PATH) -> tuple[re.Pattern[str], dict[str, str]]:
    """Ein Suchmuster über alle Befundwörter (längste zuerst) und gefaltetes Wort -> Anzeigename."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    labels: dict[str, str] = {}
    for item in raw["findings"]:
        for keyword in item["keywords"]:
            labels[fold(keyword)] = item["label"]
    words = sorted(labels, key=len, reverse=True)
    alternation = "|".join(re.escape(w).replace(r"\ ", r"\s+") for w in words)
    return re.compile(rf"(?<![a-z0-9])(?:{alternation})(?![a-z0-9])"), labels


def extract_findings(text: str, teeth: list[ToothRef]) -> list[ToothFindings]:
    """Zähne des Diktats mit Flächen und Befunden (Befunde ohne Zahn zuletzt, ``tooth=None``)."""
    ctx = TextContext(text, teeth)
    pattern, labels = _pattern()
    surfaces: dict[int, str] = {}
    for ref in teeth:
        known = surfaces.setdefault(ref.fdi, "")
        surfaces[ref.fdi] = known + "".join(c for c in ref.surfaces if c not in known)
    found: dict[int | None, list[str]] = {}
    for m in pattern.finditer(ctx.folded):
        if ctx.negated(m.start(), m.end()):
            continue
        label = labels[" ".join(m.group(0).split())]
        refs = ctx.teeth_for(m.start(), m.end())
        for key in [r.fdi for r in refs] or [None]:
            names = found.setdefault(key, [])
            if label not in names:
                names.append(label)
    result = [ToothFindings(fdi, s, tuple(found.get(fdi, ()))) for fdi, s in surfaces.items()]
    if None in found:
        result.append(ToothFindings(None, "", tuple(found[None])))
    return result
