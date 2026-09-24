"""Feste Fachregeln des Extraktors (WP-8), zum Nachlesen an einer Stelle.

Alles, was nicht aus Keywords und Regeltexten des Katalogs folgt, steht hier als
kleine Tabelle mit Verweis auf die Katalogregel, aus der sie stammt. Jede Ziffer in
diesen Tabellen muss in ``catalog_v1.json`` stehen (``tests/test_extract_rules.py``).
"""

from __future__ import annotations

import re
from dataclasses import replace

# Zahnentfernung: je System die Ziffer für jede Art. Ein-/mehrwurzelig entscheidet die
# FDI-Nummer; "tieffrakturiert" nur mit Befundwort, Osteotomie retiniert/verlagert nur mit
# Befundwort.
REMOVAL: dict[str, dict[str, str]] = {
    "BEMA": {"single": "43", "multi": "44", "fractured": "45", "osteo": "47a", "osteo_retained": "48"},
    "GOZ": {"single": "3000", "multi": "3010", "fractured": "3020", "osteo": "3030", "osteo_retained": "3040"},
}
OSTEO_KINDS = ("osteo", "osteo_retained")

# Paare einwurzelig -> mehrwurzelig außerhalb der Zahnentfernung (Katalog-README: Definition
# wie BEMA 43/44).
ROOT_PAIRS: dict[tuple[str, str], tuple[str, str]] = {
    ("BEMA", "AITa"): ("AITa", "AITb"),
    ("BEMA", "AITb"): ("AITa", "AITb"),
    ("GOZ", "4050"): ("4050", "4055"),
    ("GOZ", "4055"): ("4050", "4055"),
    ("GOZ", "4070"): ("4070", "4075"),
    ("GOZ", "4075"): ("4070", "4075"),
}

# Leistung -> Leistung, in der sie am selben Zahn bzw. in derselben Sitzung enthalten ist.
# 31: "bei vitaler Pulpa in 28 enthalten"; 11: "im Rahmen von 34 (Med) bereits enthalten".
# GOZ wie BEMA: 2390 nur als selbstständige Leistung; 2430 schließt den provisorischen Verschluss ein.
INCLUDED_IN: dict[tuple[str, str], tuple[str, str]] = {
    ("BEMA", "31"): ("BEMA", "28"),
    ("BEMA", "11"): ("BEMA", "34"),
    ("GOZ", "2390"): ("GOZ", "2360"),
    ("GOZ", "2020"): ("GOZ", "2430"),
}

# Privatziffer, die für ein bestimmtes diktiertes Wort keine Kassenleistung ist, obwohl sie ein
# BEMA-Paar hat: "Implantat entfernt" ist GOZ 3000, aber nicht BEMA 43 (Implantate sind keine
# Kassenleistung). Beim Kassenpatienten wird sie nicht umgestellt, sondern mit Hinweis weggelassen.
_PRIVATE_ONLY: dict[tuple[str, str], tuple[re.Pattern[str], str]] = {
    ("GOZ", "3000"): (re.compile(r"implantat"), "Implantatentfernung ist keine Kassenleistung"),
}


def private_only(entry, folded_keyword: str) -> str | None:
    """Grund, warum dieses diktierte Wort beim Kassenpatienten nicht auf das BEMA-Paar umgestellt wird."""
    rule = _PRIVATE_ONLY.get((entry.system, entry.code))
    return rule[1] if rule and rule[0].search(folded_keyword) else None

# Abszesseröffnung: die Tiefe wählt die Ziffer – oberflächlich BEMA Ä161 (Inz1) = GOÄ Ä2428,
# tiefliegend GOÄ Ä2430 (beim Kassenpatienten Analogposition, Katalogfeld analog). Die Tiefenwörter
# sind Keywords von Ä2428/Ä2430;
# die übrigen Wörter von Ä161 („Abszess eröffnet“, „Abszessinzision“) lassen die Tiefe offen, dann wird
# nicht still eine Tiefe gewählt, sondern nachgefragt. Gezählt wird je Abszess = je Fundstelle, nie je
# genanntem Zahn: lieber zu wenig mit Hinweis als zu viel.
INCISION_OPEN = ("BEMA", "Ä161")
INCISION = frozenset({INCISION_OPEN, ("GOÄ", "Ä2428"), ("GOÄ", "Ä2430")})
INCISION_VERB = re.compile(r"\s*(?:eroeffnet|inzidiert|gespalten)\b")  # „oberflächlichen Abszess eröffnet regio 46“
INCISION_REPEATED = "{n} Inzisionen an {fdi} diktiert – ein Abszess angenommen; falls mehrere Abszesse, von Hand ergänzen"
INCISION_TEETH = "mehrere Zähne genannt – ein Abszess angenommen; falls es mehrere Abszesse waren, von Hand aufteilen"
_INCISION_DEPTH = {
    "BEMA": "Tiefe nicht diktiert – oberflächlich Ä161 (Inz1) oder tiefliegend GOÄ Ä2430 als Analogposition (inz2) wählen",
    "GOÄ": "Tiefe nicht diktiert – oberflächlich GOÄ Ä2428 (inz1) oder tiefliegend GOÄ Ä2430 (inz2) wählen",
}


def incision_depth_open(hit) -> str | None:
    """Prüfhinweis, wenn eine Abszesseröffnung ohne oberflächlich/tiefliegend diktiert wurde."""
    origin = hit.via or hit.entry
    if origin.key != INCISION_OPEN or hit.code_word:
        return None
    return _INCISION_DEPTH.get(hit.entry.system)


def incision_depth_stated(hit) -> bool:
    """Abszesseröffnung mit diktierter Tiefe („tiefliegenden Abszess“, „Inz1“)."""
    return (hit.via or hit.entry).key in INCISION and not incision_depth_open(hit)


def incision_depth(tagged: list) -> list:
    """„Subperiostaler Abszess inzidiert“: ein Wort ohne Tiefe gehört zur Abszesseröffnung mit Tiefe im selben Satz."""
    stated = [t for t in tagged if incision_depth_stated(t.hit)]
    result = []
    for t in tagged:
        host = next((s for s in stated if s.sentence == t.sentence and (
            not t.teeth or not s.teeth or set(t.teeth) & set(s.teeth))), None) if incision_depth_open(t.hit) else None
        result.append(replace(t, hit=replace(t.hit, entry=host.hit.entry, via=None)) if host else t)
    return result

# Je-Kanal-Position ohne diktierte Kanalzahl: nie hochzählen, der Behandler trägt die Anzahl ein.
CANALS_OPEN = "Kanalzahl nicht diktiert – je Kanal berechnen"
# Eine Kanalzahl an einer Fundstelle mit mehreren Zähnen: gilt je Zahn, aber der Behandler prüft sie.
CANALS_TEETH = "mehrere Zähne genannt – Kanalzahl je Zahn prüfen"

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
REMOVAL_ACT = re.compile(r"extrah|extrakt|entfern|gezogen|gehebelt|osteotom|ost?,?\s?\d|x\d|operativ|aufklappung|abgetragen")
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
