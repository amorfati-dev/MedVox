"""Feste Fachregeln des Extraktors (WP-8), zum Nachlesen an einer Stelle.

Alles, was nicht aus Keywords und Regeltexten des Katalogs folgt, steht hier als
kleine Tabelle mit Verweis auf die Katalogregel, aus der sie stammt. Jede Ziffer in
diesen Tabellen muss in ``catalog_v1.json`` stehen (``tests/test_extract_rules.py``).
"""

from __future__ import annotations

import re

# Zahnentfernung: je System die Ziffer für jede Art. Ein-/mehrwurzelig entscheidet die
# FDI-Nummer; "tieffrakturiert" nur mit Befundwort, Osteotomie retiniert/verlagert nur mit
# Befundwort. GOZ 3020 (tieffrakturiert) steht nicht im Katalog v1.
REMOVAL: dict[str, dict[str, str]] = {
    "BEMA": {"single": "43", "multi": "44", "fractured": "45", "osteo": "47a", "osteo_retained": "48"},
    "GOZ": {"single": "3000", "multi": "3010", "osteo": "3030", "osteo_retained": "3040"},
}
OSTEO_KINDS = ("osteo", "osteo_retained")

# Paare einwurzelig -> mehrwurzelig außerhalb der Zahnentfernung (Katalog-README: Definition
# wie BEMA 43/44).
ROOT_PAIRS: dict[tuple[str, str], tuple[str, str]] = {
    ("BEMA", "AITa"): ("AITa", "AITb"),
    ("BEMA", "AITb"): ("AITa", "AITb"),
    ("GOZ", "4050"): ("4050", "4055"),
    ("GOZ", "4055"): ("4050", "4055"),
}

# Leistung -> Leistung, in der sie am selben Zahn bzw. in derselben Sitzung enthalten ist.
# 31: "bei vitaler Pulpa in 28 enthalten"; 11: "im Rahmen von 34 (Med) bereits enthalten".
INCLUDED_IN: dict[tuple[str, str], tuple[str, str]] = {
    ("BEMA", "31"): ("BEMA", "28"),
    ("BEMA", "11"): ("BEMA", "34"),
}

# GOZ-Zuschläge zu chirurgischen Leistungen (Anlage 1, Abschnitt L): Ziffer, Punkte von, bis.
SURCHARGES: tuple[tuple[str, int, int | None], ...] = (
    ("0500", 250, 499),
    ("0510", 500, 799),
    ("0520", 800, 1199),
    ("0530", 1200, None),
)
SURCHARGE_CODES = frozenset(code for code, _lo, _hi in SURCHARGES)


def surcharge_for(points: int) -> tuple[str, int, int | None] | None:
    """Zuschlagsstufe für die Punktzahl der höchstbewerteten chirurgischen Leistung."""
    for code, lo, hi in SURCHARGES:
        if points >= lo and (hi is None or points <= hi):
            return code, lo, hi
    return None


def multi_rooted(fdi: int) -> bool:
    """BEMA-Definition: mehrwurzelig sind alle Molaren, die oberen 4er und alle Milchmolaren."""
    quadrant, tooth = divmod(fdi, 10)
    if quadrant >= 5:
        return tooth >= 4
    return tooth >= 6 or (tooth == 4 and quadrant in (1, 2))


# Keywords einer Entfernungs-Ziffer, die eine Handlung beschreiben; die übrigen ("retiniert",
# "Längsfraktur", "mehrwurzelig") sind Befundwörter und lösen allein nichts aus.
REMOVAL_ACT = re.compile(r"extrah|extrakt|entfern|gezogen|osteotom|ost\d|x\d|operativ|aufklappung|abgetragen")
_RETAINED = re.compile(r"retinier|verlager|impaktiert|zahnkeim")
_FRACTURED = re.compile(r"fraktur|zerstoert")


def removal_modifier(folded_keyword: str) -> str | None:
    """"retained", "fractured", "multi" oder None für ein Befundwort der Zahnentfernung."""
    if _RETAINED.search(folded_keyword):
        return "retained"
    if _FRACTURED.search(folded_keyword):
        return "fractured"
    if "mehrwurzelig" in folded_keyword:
        return "multi"
    return None


def surface_count_word(folded_keyword: str) -> bool:
    """Flächenzahl-Wort einer Füllungs-Familie ("dreiflächig", "mod"): wählt die Ziffer, löst allein nichts aus."""
    return "flaech" in folded_keyword or folded_keyword == "mod"
