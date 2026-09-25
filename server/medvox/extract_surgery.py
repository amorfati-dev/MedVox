"""Weisheitszahn-OP im Regel-Extraktor: Optionen „ggf. dazu“ und Pla0 nur neben einer Osteotomie.

Praxisregel des Behandlers (2026-09-24): zu einer erbrachten Osteotomie (Ost1/Ost2: BEMA 47a/48 bzw.
GOZ 3030/3040) an einem Weisheitszahn (18, 28, 38, 48) kommen Beratung (Ä1) und Zahnsteinentfernung
(Zst, BEMA 107) „ggf. dazu“. Sie stehen als Option zum Antippen am ersten operierten Weisheitszahn,
nie vorausgewählt und nie, wenn sie schon diktiert sind. Beim Privatpatienten nur GOÄ Ä1: Zst ist dort
GOZ 4050/4055 je Zahn, und welche Zähne, sagt das Diktat nicht.

Nbl2 (BEMA 37 / GOZ 3060) wird nur vorgeschlagen, wenn „Nbl2“ selbst diktiert ist oder eine starke Blutung
zusammen mit einer Maßnahme (Umschlingungsnaht/Naht/Umstechung, Bipo, Parasorb). Eine Maßnahme oder die Blutung
allein steht nur als Option zum Antippen mit Prüfhinweis da. „starke Blutung“ ohne Maßnahme und ohne
Zahnentfernung oder Osteotomie in der Sitzung (etwa „BMF, starke Blutung“ an einer Füllung – Papillenblutung,
Teil von BEMA 12) fällt mit Hinweis weg.

BEMA 51b (Pla0) gilt laut amtlichem Text nur in Verbindung mit einer Osteotomie; ohne 47a/48/Ä2650 in der
Sitzung bleibt sie stehen, aber mit Hinweis auf 51a (Pla1, nicht im Katalog v1).

Schwere Osteotomie („schwere Ost“, Angabe des Behandlers 2026-09-25) ist GOÄ Ä2650 – beim Kassenpatienten als
Analogposition, BEMA hat über Ost2 nichts. Sie ersetzt Ost1/Ost2 am selben Zahn, nie beide in den Vorschlägen,
und gilt überall als Osteotomie: Ä1/Zst-Optionen am Weisheitszahn, Pla0 und Nbl2 wie neben Ost1/Ost2.
"""

from __future__ import annotations

import re
from dataclasses import replace

from medvox.extract_catalog import Catalog
from medvox.extract_draft import Draft, Tagged
from medvox.extract_rules import REMOVAL
from medvox.extract_text import TextContext

WISDOM_TEETH = frozenset({18, 28, 38, 48})
SEVERE_OSTEOTOMY = ("GOÄ", "Ä2650")
OST1_OST2 = frozenset({("BEMA", "47a"), ("BEMA", "48"), ("GOZ", "3030"), ("GOZ", "3040")})
OSTEOTOMY = OST1_OST2 | {SEVERE_OSTEOTOMY}
WISDOM_OPTIONS = {"kasse": (("BEMA", "Ä1"), ("BEMA", "107")), "privat": (("GOÄ", "Ä1"),)}
WISDOM_NOTE = "ggf. dazu bei Weisheitszahn-OP (Praxisregel des Behandlers) – antippen, wenn erbracht"
NBL2 = frozenset({("BEMA", "37"), ("GOZ", "3060")})
BLEEDING = frozenset({"starke blutung", "nachblutung stark", "starke nachblutung"})
_MEASURE = re.compile(r"(?<![a-z])(?:[a-z]*naht|umstech[a-z]*|umstochen|abgebunden|knochenbolzung|bipo[a-z]*|parasorb)"
                      r"(?![a-z])")
NBL2_OPTION = ("Nbl2 ({code}) nur bei starker Blutung mit Umschlingungsnaht/Naht/Umstechung, Bipo oder Parasorb – "
               "diktiert nur „{words}“; antippen, wenn erbracht")
LONE_BLEEDING = ("„{word}“ ohne Zahnentfernung/Osteotomie in dieser Sitzung – Nbl2 ({code}) nicht vorgeschlagen; "
                 "Papillenblutung gehört zu den besonderen Maßnahmen (bmf), sonst Nbl1 (BEMA 36 / GOZ 3050) prüfen")
PLA0 = ("BEMA", "51b")
PLA0_ALONE = "BEMA 51b (Pla0) nur in Verbindung mit einer Osteotomie (47a/48/Ä2650) – sonst 51a (Pla1) prüfen"


def wisdom_offers(catalog: Catalog, primaries: list[Draft], patient: str) -> list[Draft]:
    """Ä1 und Zst als Option zur ersten erbrachten Osteotomie an einem Weisheitszahn."""
    host = next((d for d in primaries if d.entry.key in OSTEOTOMY and d.fdi in WISDOM_TEETH), None)
    if host is None:
        return []
    have = {d.entry.key for d in primaries}
    offers = []
    for key in WISDOM_OPTIONS[patient]:
        entry = catalog.get(*key)
        if entry is None or key in have or any((entry.system, c) in have for c in catalog.not_beside(entry)):
            continue
        offers.append(Draft(entry, None, False, context=(host.fdi,), alternative_to=host, reason=WISDOM_NOTE,
                            addon=True))
    return offers


def severe_osteotomy(primaries: list[Draft]) -> list[Draft]:
    """Ä2650 an einem Zahn übernimmt die Fundstellen einer Osteotomie (47a/48 bzw. 3030/3040) desselben Zahns."""
    severe = {d.fdi: d for d in primaries if d.entry.key == SEVERE_OSTEOTOMY and d.fdi is not None}
    kept = []
    for d in primaries:
        host = severe.get(d.fdi) if d.entry.key in OST1_OST2 else None
        if host is None:
            kept.append(d)
            continue
        absorbed = [replace(t, hit=replace(t.hit, via=None)) for t in d.hits]  # kein Paar Ost2 ↔ Ä2650 anzeigen
        host.hits = sorted(host.hits + [t for t in absorbed if t not in host.hits], key=lambda t: t.hit.start)
    return kept


def flag_lone_pla0(primaries: list[Draft]) -> None:
    """Pla0 ohne Osteotomie in derselben Sitzung: Hinweis statt stiller Wahl."""
    if any(d.entry.key in OSTEOTOMY for d in primaries):
        return
    for d in primaries:
        if d.entry.key == PLA0 and PLA0_ALONE not in d.decide:
            d.decide.append(PLA0_ALONE)


def split_bleeding(ctx: TextContext, primaries: list[Draft], notes: list[str]) -> tuple[list[Draft], list[Draft]]:
    """Nbl2 bleibt nur mit „Nbl2“ oder starker Blutung plus Maßnahme; sonst Option (bzw. ohne OP: Hinweis)."""
    surgery = any(d.entry.code in REMOVAL.get(d.entry.system, {}).values() or d.entry.key == SEVERE_OSTEOTOMY
                  for d in primaries)
    kept, offers = [], []
    for d in primaries:
        if d.entry.key not in NBL2 or any(t.hit.code_word for t in d.hits):
            kept.append(d)
            continue
        if any(t.hit.keyword in BLEEDING and _measure_beside(ctx, t) for t in d.hits):
            kept.append(d)
            continue
        if not surgery and all(t.hit.keyword in BLEEDING for t in d.hits):
            word = ctx.original(d.hits[0].hit.start, d.hits[0].hit.end)
            notes.append(LONE_BLEEDING.format(word=word, code=d.entry.label))
            continue
        words = ", ".join(dict.fromkeys(ctx.original(t.hit.start, t.hit.end) for t in d.hits))
        d.addon = True
        d.decide.append(NBL2_OPTION.format(code=d.entry.label, words=words))
        offers.append(d)
    return kept, offers


def _measure_beside(ctx: TextContext, bleeding: Tagged) -> bool:
    """Nicht verneinte Maßnahme im Satz der starken Blutung am selben Zahn („keine Naht“, andere Zähne nicht)."""
    own = {tooth.fdi for tooth in bleeding.teeth}
    for m in _MEASURE.finditer(ctx.folded, *bleeding.sentence):
        teeth = {tooth.fdi for tooth in ctx.teeth_for(m.start(), m.end())}
        if not ctx.negated(m.start(), m.end()) and (not teeth or not own or teeth & own):
            return True
    return False
