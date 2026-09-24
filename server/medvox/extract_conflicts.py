"""Konflikte aus dem Katalog (``conflicts``): zwei Positionen, die nicht in derselben Sitzung stehen dürfen.

Der Extraktor streicht keine von beiden – beide bleiben mit dem Hinweis aus dem Katalog stehen, der
Behandler entscheidet (Ausnahme wie „separates Operationsgebiet“ folgt nicht sicher aus dem Diktat).
Liegen die Zähne beider Positionen in verschiedenen Quadranten, sagt der Hinweis, dass die Ausnahme
greifen kann – entschieden wird sie nie automatisch.
"""

from __future__ import annotations

from medvox.extract_draft import Draft
from medvox.extract_catalog import Catalog

APART = "Zähne in verschiedenen Quadranten – separates Operationsgebiet möglich"


def flag_conflicts(catalog: Catalog, drafts: list[Draft]) -> None:
    """Markiert erbrachte Vorschläge, die laut Katalog nicht neben einem anderen derselben Sitzung stehen."""
    done = [d for d in drafts if not d.planned]
    for d in done:
        for c in d.entry.conflicts:
            for o in (o for o in done if o.entry.key == (c.system, c.code)):
                apart = _quadrants(d) and _quadrants(o) and not _quadrants(d) & _quadrants(o)
                flag = f"{c.note}; {APART}" if apart else c.note
                for x in (d, o):
                    if flag not in x.decide:
                        x.decide.append(flag)


def _quadrants(d: Draft) -> set[int]:
    teeth = {d.fdi} if d.fdi is not None else set(d.context)
    return {(fdi // 10 - 1) % 4 + 1 for fdi in teeth}
