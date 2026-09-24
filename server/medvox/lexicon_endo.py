"""Verhörer, die nur im Abschnitt eines Zahns mit Wurzelkanalbehandlung gelten (Teil von ``lexicon``)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from medvox.lexicon import Correction

# Verhörer, die nur im Abschnitt eines Zahns mit Wurzelkanalbehandlung gelten: "MET" ist dort "med"
# (medikamentöse Einlage, BEMA 34), sonst bleibt es stehen. Ein Abschnitt reicht von einer Zahnangabe
# ("Zahn", "regio", "25", "zwei fünf") bis zur nächsten; ohne Zahnangabe davor ab Textanfang.
ENDO_ONLY: dict[str, str] = {"met": "med"}
_ENDO_WORDS = ("VitE", "WK", "Vitalexstirpation", "Trepanation")
_ENDO = re.compile(r"(?<!\w)(?:wurzelkanal\w*|wk|vite|vitalexstirpation|trepanation)(?!\w)", re.I)
_DIGIT_WORDS = "eins|zwei|drei|vier|fünf|fuenf|sechs|sieben|acht"
_TOOTH_MARK = re.compile(
    rf"(?<!\w)(?:zahn|zähne|regio|[1-8]\s*[1-8]|(?:{_DIGIT_WORDS})\s+(?:{_DIGIT_WORDS}))(?!\w)", re.I
)


def endo_only(
    text: str, tokens: list[tuple[int, int, str]], found: list[Correction]
) -> list[tuple[str, str, int, int]]:
    """(Original, Ersatz, Start, Ende) für Verhörer aus ``ENDO_ONLY``, wenn im Abschnitt desselben Zahns eine
    Wurzelkanalbehandlung steht; ``found`` sind die übrigen Korrekturen ("2x WD" -> VitE zählt mit)."""
    result = []
    for start, end, token in tokens:
        if (replacement := ENDO_ONLY.get(token.lower())) is None or any(c.start <= start < c.end for c in found):
            continue
        before = [m.end() for m in _TOOTH_MARK.finditer(text, 0, start)]
        after = _TOOTH_MARK.search(text, end)
        lo, hi = before[-1] if before else 0, after.start() if after else len(text)
        if _ENDO.search(text, lo, hi) or any(lo <= c.start < hi and c.corrected in _ENDO_WORDS for c in found):
            result.append((token, replacement, start, end))
    return result
