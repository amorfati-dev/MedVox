"""Vorschläge fürs Wörterbuch aus der Korrektur-Sammlung (`corrections`, Entscheidung F2 = b).

Gleiche Änderungen werden gezählt. Eine Textstelle trägt bis zu zwei Wörter Umfeld je Seite
(`corrections.text_spots`); verglichen wird ihr Kern ohne das gemeinsame Umfeld – „Zahn steinentfernung,
Politur,“ → „Zahnsteinentfernung, Politur,“ ergibt „Zahn steinentfernung“ → „Zahnsteinentfernung“.
Übernehmen lässt sich ein Paar nur per Tipp und nur, wenn es die Schutzregeln besteht
(`lexicon_entries.check_replacement`); alles andere, auch jede Ziffernänderung, ist nur Information –
Ziffern pflegt der Behandler im Katalog (`catalog/README.md`), nicht hier.
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from dataclasses import dataclass

from medvox.lexicon_entries import Entry, Rejected, check_replacement

MAX_SHOWN = 30
_PUNCT = ",.;:!?()\"'„“”–-"


@dataclass(frozen=True)
class Suggestion:
    kind: str  # text | ziffer
    before: str
    after: str
    count: int
    takeable: bool  # besteht die Schutzregeln und ist noch nicht eingetragen
    taken: bool  # gleiche Ersetzung ist schon eingeschaltet


@dataclass(frozen=True)
class Collection:
    suggestions: list[Suggestion]
    total: int  # Änderungsstellen in der Sammlung
    first_week: str | None  # „2026-W39“
    last_week: str | None


def core(before: str, after: str) -> tuple[str, str]:
    """Die geänderte Stelle ohne das gemeinsame Umfeld (Wörter, danach Satzzeichen an den Rändern)."""
    a, b = before.split(), after.split()
    while a and b and a[0] == b[0]:
        a, b = a[1:], b[1:]
    while a and b and a[-1] == b[-1]:
        a, b = a[:-1], b[:-1]
    old, new = " ".join(a), " ".join(b)
    while old and new and old[-1] == new[-1] and old[-1] in _PUNCT:
        old, new = old[:-1], new[:-1]
    while old and new and old[0] == new[0] and old[0] in _PUNCT:
        old, new = old[1:], new[1:]
    return old.strip(), new.strip()


def _takeable(before: str, after: str, current: list[Entry]) -> tuple[bool, bool]:
    taken = any(
        e.kind == "ersetzung" and e.wrong.lower() == before.lower() and e.right == after for e in current
    )
    if taken:
        return False, True
    try:
        check_replacement(before, after, current)
    except Rejected:
        return False, False
    return True, False


def collect(conn: sqlite3.Connection, current: list[Entry]) -> Collection:
    """Gezählte Vorschläge, häufigste zuerst; `current` sind die eingeschalteten Einträge."""
    rows = conn.execute("SELECT kind, before, after, week FROM corrections").fetchall()
    counts: Counter[tuple[str, str, str]] = Counter()
    for row in rows:
        before, after = core(row["before"], row["after"]) if row["kind"] == "text" else (row["before"], row["after"])
        if before or after:
            counts[(row["kind"], before, after)] += 1
    suggestions = []
    for (kind, before, after), n in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        takeable, taken = _takeable(before, after, current) if kind == "text" else (False, False)
        suggestions.append(Suggestion(kind, before, after, n, takeable, taken))
    weeks = sorted(row["week"] for row in rows)
    return Collection(suggestions[:MAX_SHOWN], len(rows), weeks[0] if weeks else None, weeks[-1] if weeks else None)
