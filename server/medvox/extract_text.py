"""Satzbau des normalisierten Diktats für den Regel-Extraktor (WP-8).

``TextContext`` faltet den Text (klein, Umlaute ausgeschrieben – wie die Keywords),
findet Sätze, Teilsätze und Zahngruppen und beantwortet für eine Fundstelle:
Welche Zähne gehören dazu? Ist sie geplant oder verneint? Welche Anzahl
("1 Kanal", "28 Zähne", "2x") steht dabei? Alle Positionen beziehen sich auf den
gefalteten Text; ``original`` holt den diktierten Wortlaut für die Begründung zurück.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from medvox.extract_catalog import fold_with_map
from medvox.normalize import ToothRef
from medvox.normalize_digits import expand_range

_SENTENCE_END = re.compile(r"[.;!?](?=\s|$)")
_COMMA = re.compile(",")
_TOOTH_TOKEN = re.compile(r"(?<![\w.])(\d\d)(?:\s*-\s*(\d\d))?(?!\w)")
# "36 o, Zahn 37 mod": ein wiederholtes "Zahn" nach Komma/"und" gehört noch zur Aufzählung.
_GROUP_GAP = re.compile(r"(?:\s*[modblpi]{1,5})?\s*(?:(?:,|und)\s*zahn|,|und|-|bis)?\s*")
_TRAILING_SURFACES = re.compile(r"\s*,?\s*[modblpi]{1,5}\b")
# Zwischen Leistung und nachfolgender Zahnnummer erlaubt: "Extraktion 47", "Vitalitätsprüfung an 16".
_LEAD_IN = re.compile(r"\s*(?:(?:an|am|bei|von|regio|zahn|zaehne|den|der|des|dem|im|in|fuer)\s+)*")

# Plan-Marker: der Teilsatz (mit Doppelpunkt: der Rest des Satzes) ist geplant, nicht erbracht.
_PLAN = re.compile(
    r"(?<![a-z])(?:geplant\w*|planen|plane|planung|vorgesehen|empfohlen|wiedervorlage|termin"
    r"|naechste[nrs]?\s+(?:sitzung|termin|mal|behandlung)|beim\s+naechsten\s+mal"
    r"|indikation\s+(?:zur|zum|fuer)|ueberweisung|ueberwiesen"
    r"|in\s+(?:\d+|einer|einem|zwei)\s+(?:tag|tagen|woche|wochen|monat|monaten))(?![a-z])(\s*:)?"
)
_NEGATION_BEFORE = re.compile(r"(?<![a-z])(?:kein|keine|keinen|keiner|ohne|nicht)\s+(?:[a-z]+\s+)?$")
_NEGATION_AFTER = re.compile(r"\s+(?:\d\d\s+)?(?:nicht|kein\w*)(?![a-z])")
_CANALS = re.compile(r"(?<![\w.])(\d+)\s*(?:wurzel)?kan(?:al|aele|aelen)(?![a-z])")
_TEETH_COUNT = re.compile(r"(?<![\w.])(\d+)\s*zaehnen?(?![a-z])")
_TIMES_AFTER = re.compile(r"\s*(\d+)\s*(?:x|mal)(?![a-z])")
_TIMES_BEFORE = re.compile(r"(?<![\w.])(\d+)\s*(?:x|mal)\s*$")


@dataclass(frozen=True)
class ToothGroup:
    start: int
    end: int
    teeth: tuple[ToothRef, ...]


def _tooth_tokens(folded: str, teeth: list[ToothRef]) -> list[tuple[int, int, list[ToothRef]]]:
    """Zahnnummern im Text, in Reihenfolge an die Zahnliste des Normalisierers angelegt."""
    tokens: list[tuple[int, int, list[ToothRef]]] = []
    i = 0
    for m in _TOOTH_TOKEN.finditer(folded):
        if i >= len(teeth):
            break
        numbers = [int(m.group(1))]
        if m.group(2):
            numbers = expand_range(numbers[0], int(m.group(2)))
        if [t.fdi for t in teeth[i : i + len(numbers)]] == numbers:
            tokens.append((m.start(), m.end(), teeth[i : i + len(numbers)]))
            i += len(numbers)
        elif teeth[i].fdi == numbers[0]:
            tokens.append((m.start(), m.end(), [teeth[i]]))
            i += 1
    return tokens


def _groups(folded: str, teeth: list[ToothRef]) -> list[ToothGroup]:
    groups: list[ToothGroup] = []
    for start, end, refs in _tooth_tokens(folded, teeth):
        if groups and _GROUP_GAP.fullmatch(folded, groups[-1].end, start):
            last = groups[-1]
            groups[-1] = ToothGroup(last.start, end, last.teeth + tuple(refs))
        else:
            groups.append(ToothGroup(start, end, tuple(refs)))
    result = []
    for g in groups:
        trail = _TRAILING_SURFACES.match(folded, g.end)
        result.append(ToothGroup(g.start, trail.end() if trail else g.end, g.teeth))
    return result


class TextContext:
    def __init__(self, text: str, teeth: list[ToothRef]) -> None:
        self.text = text
        self.folded, self._index = fold_with_map(text)
        self.groups = _groups(self.folded, teeth)
        ends = [m.end() for m in _SENTENCE_END.finditer(self.folded)]
        starts = [0] + ends
        self.sentences = [(s, e) for s, e in zip(starts, ends + [len(self.folded)]) if s < e]
        self._planned = self._plan_spans()

    def original(self, start: int, end: int) -> str:
        return self.text[self._index[start] : self._index[end - 1] + 1]

    def sentence(self, pos: int) -> tuple[int, int]:
        for s, e in self.sentences:
            if s <= pos < e:
                return s, e
        return 0, len(self.folded)

    def clause(self, pos: int) -> tuple[int, int]:
        """Teilsatz um ``pos``; Kommas innerhalb einer Zahnaufzählung ("16, 26 und 36") trennen nicht."""
        s, e = self.sentence(pos)
        commas = [m.end() for m in _COMMA.finditer(self.folded, s, e) if not self.in_group(m.start())]
        cuts = [s, *commas, e]
        for a, b in zip(cuts, cuts[1:]):
            if a <= pos < b:
                return a, b
        return s, e

    def in_group(self, pos: int) -> bool:
        return any(g.start <= pos < g.end for g in self.groups)

    def _plan_spans(self) -> list[tuple[int, int, str]]:
        spans = []
        for m in _PLAN.finditer(self.folded):
            s, e = self.clause(m.start())
            if m.group(1):  # "Nächste Sitzung: …" gilt bis zum Satzende
                e = self.sentence(m.start())[1]
            spans.append((s, e, self.original(m.start(), m.end() - len(m.group(1) or ""))))
        return spans

    def plan_marker(self, pos: int) -> str | None:
        """Wortlaut des Plan-Markers, der ``pos`` als geplant markiert, sonst None."""
        return next((word for s, e, word in self._planned if s <= pos < e), None)

    def negated(self, start: int, end: int) -> bool:
        clause_start = self.clause(start)[0]
        return bool(_NEGATION_BEFORE.search(self.folded, clause_start, start)
                    or _NEGATION_AFTER.match(self.folded, end))

    def teeth_for(self, start: int, end: int) -> tuple[ToothRef, ...]:
        """Zähne einer Fundstelle: direkt folgende Zahngruppe, sonst die letzte davor im selben Satz."""
        s, e = self.sentence(start)
        inside = [g for g in self.groups if g.start <= start < g.end]
        if inside:
            return inside[0].teeth
        for g in self.groups:
            if g.start >= end and g.start < e and _LEAD_IN.fullmatch(self.folded, end, g.start):
                return g.teeth
        before = [g for g in self.groups if s <= g.start and g.end <= start]
        return before[-1].teeth if before else ()

    def _nearest(self, pattern: re.Pattern[str], start: int) -> int | None:
        s, e = self.sentence(start)
        found = [(abs(m.start() - start), int(m.group(1))) for m in pattern.finditer(self.folded, s, e)]
        return min(found)[1] if found else None

    def canals(self, start: int) -> int | None:
        return self._nearest(_CANALS, start)

    def teeth_count(self, start: int) -> int | None:
        return self._nearest(_TEETH_COUNT, start)

    def times(self, start: int, end: int) -> int | None:
        """Ausdrückliche Anzahl direkt an der Fundstelle ("BEMA 13a 2x", "2x L1")."""
        m = _TIMES_AFTER.match(self.folded, end) or _TIMES_BEFORE.search(self.folded, 0, start)
        return int(m.group(1)) if m else None
