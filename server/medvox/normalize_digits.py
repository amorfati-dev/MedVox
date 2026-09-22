"""Ziffernfolgen des Normalisierers zu FDI-Zähnen paaren (WP-5).

Ein Lauf aus Einzelziffern wird an den Aufzählungskommas (Komma mit Leerzeichen)
in Items zerlegt. Gepaart wird nur innerhalb eines Items aus genau zwei
Einzelziffern, die ein Leerzeichen, ein Bindestrich oder ein Komma ohne
Leerzeichen verbindet ("3 6", "3-6", "3,6"); über ein Aufzählungskomma hinweg
wird nie gepaart. Damit bleiben Messwertreihen ("Sondierungstiefen 3 2 3 2 2 3"),
Dosierungsschemata ("1-1-1") und Aufzählungen ("1, 6, 2, 6") unverändert. Vor
einem Einheitenwort paart nur das Leerzeichen-Paar, damit "2-3 Tagen" ein
Bereich und "3,5 mm" ein Messwert bleibt.
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


def pair_digit_run(run: str, unit_follows: bool) -> str:
    """Einzelziffern eines Laufs paaren (``unit_follows``: Einheitenwort direkt dahinter)."""
    parts = _SEPARATOR.split(run)
    digits, seps = parts[0::2], parts[1::2]
    items: list[list[int]] = [[0]]
    for k, sep in enumerate(seps):
        if "," in sep and sep != ",":
            items.append([])
        items[-1].append(k + 1)
    joined: set[int] = set()
    for n, item in enumerate(items):
        if len(item) != 2:
            continue
        if unit_follows and n == len(items) - 1 and seps[item[0]].strip():
            continue
        if is_fdi(int(digits[item[0]] + digits[item[1]])):
            joined.add(item[0])
    return "".join(d + ("" if k in joined else seps[k] if k < len(seps) else "") for k, d in enumerate(digits))
