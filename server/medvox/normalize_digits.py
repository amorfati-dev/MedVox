"""Ziffernfolgen des Normalisierers zu FDI-Zähnen paaren (WP-5).

Ein Lauf aus Einzelziffern ("3 6", "3-6", "1, 6, 2, 6", "3, 5, 6") wird an den
Kommas in Items zerlegt:

1. Ein Item aus zwei Einzelziffern mit Leerzeichen/Bindestrich ("3 6", "3-6")
   ist ein Zahnpaar, egal was nach dem nächsten Komma folgt.
2. Ein Item aus einer Einzelziffer vor einem Einheiten-/Zählwort ("3 Kanäle",
   "6 mm") ist eine Anzahl und wird nie gepaart; ebenso ein Bindestrich-Bereich
   ("2-3 Tagen").
3. Nur eine Folge kommagetrennter Einzelziffern ohne Einheit dahinter paart
   über die Kommas hinweg ("1, 6, 2, 6" -> 16, 26); folgt eine Einheit, ist die
   ganze Folge eine Messwertliste ("3, 5, 6 mm").
"""

from __future__ import annotations

import re


def is_fdi(number: int) -> bool:
    """True für bleibende (11-48) und Milchzahn-FDI-Nummern (51-85)."""
    quadrant, tooth = divmod(number, 10)
    return (1 <= quadrant <= 4 and 1 <= tooth <= 8) or (5 <= quadrant <= 8 and 1 <= tooth <= 5)


def _arch(fdi: int) -> list[int]:
    """Alle Zähne des Kiefers (OK/UK, bleibend/Milch) in FDI-Reihenfolge."""
    quadrant = fdi // 10
    right, left = {1: (1, 2), 2: (1, 2), 3: (4, 3), 4: (4, 3), 5: (5, 6), 6: (5, 6), 7: (8, 7), 8: (8, 7)}[quadrant]
    last = 8 if quadrant <= 4 else 5
    return [right * 10 + t for t in range(last, 0, -1)] + [left * 10 + t for t in range(1, last + 1)]


def expand_range(first: int, last: int) -> list[int]:
    """Zähne von ``first`` bis ``last`` entlang des Kiefers ("17 bis 27" -> 14 Zähne)."""
    arch = _arch(first)
    if last not in arch:
        return [first, last]
    i, j = arch.index(first), arch.index(last)
    return arch[i : j + 1] if i <= j else arch[j : i + 1][::-1]


_SEPARATOR = re.compile(r"(\s*,\s*|\s*-\s*|\s+)")


def _pair_left_to_right(digits: list[str], group: list[int]) -> set[int]:
    """Indizes, deren Ziffer mit der folgenden zu einem FDI-Zahn verschmilzt."""
    joined: set[int] = set()
    j = 0
    while j + 1 < len(group):
        if is_fdi(int(digits[group[j]] + digits[group[j + 1]])):
            joined.add(group[j])
            j += 2
        else:
            j += 1
    return joined


def pair_digit_run(run: str, unit_follows: bool) -> str:
    """Einzelziffern eines Laufs nach den Modulregeln paaren (``unit_follows``: Einheit direkt dahinter)."""
    parts = _SEPARATOR.split(run)
    digits, seps = parts[0::2], parts[1::2]
    items: list[list[int]] = [[0]]
    for k, sep in enumerate(seps):
        if "," in sep:
            items.append([])
        items[-1].append(k + 1)
    # Aufeinanderfolgende Einzelziffer-Items bilden eine Gruppe (Regel 3), jedes andere Item steht allein.
    groups: list[list[int]] = []
    singles = False
    for item in items:
        if singles and len(item) == 1:
            groups[-1].append(item[0])
        else:
            groups.append(item)
        singles = len(item) == 1
    joined: set[int] = set()
    for n, group in enumerate(groups):
        if n == len(groups) - 1 and unit_follows and not (len(group) == 2 and not seps[group[0]].strip()):
            continue
        joined |= _pair_left_to_right(digits, group)
    return "".join(d + ("" if k in joined else seps[k] if k < len(seps) else "") for k, d in enumerate(digits))
