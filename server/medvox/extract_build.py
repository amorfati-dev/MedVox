"""Aus Fundstellen werden Entwürfe je Ziffer und Zahn (WP-8).

Regelfamilien: Füllungen (Flächenzahl wählt a–d bzw. 2060–2120), Zahnentfernung
(Handlung + Befundwort + FDI-Nummer wählen 43/44/45/47a/48 bzw. 3000–3040),
ein-/mehrwurzelige Paare (AIT a/b, 4050/4055) und alle übrigen Positionen mit ihrer
Einheit je Kanal, je Zahn oder je Sitzung. Geplante und erbrachte Fundstellen werden
getrennt gesammelt; Befundwörter gelten für beide.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from medvox.extract_catalog import Catalog, Entry
from medvox.extract_match import Hit
from medvox.extract_rules import (
    OSTEO_KINDS, REMOVAL, REMOVAL_ACT, ROOT_PAIRS, SURCHARGE_CODES, multi_rooted, removal_modifier,
    surface_count_word,
)
from medvox.extract_text import TextContext
from medvox.normalize import ToothRef


@dataclass
class Tagged:
    hit: Hit
    teeth: tuple[ToothRef, ...]
    plan: str | None  # Plan-Marker oder None (= erbracht)
    sentence: tuple[int, int]


@dataclass
class Draft:
    entry: Entry
    fdi: int | None  # Zahn bei Einheit je Zahn/je Kanal, sonst None
    planned: bool
    hits: list[Tagged] = field(default_factory=list)
    count: int = 1
    context: tuple[int, ...] = ()  # zugehörige Zähne bei Einheit je Sitzung
    decide: list[str] = field(default_factory=list)
    plan: str | None = None
    alternative_to: Draft | None = None
    reason: str = ""
    surfaces: int | None = None  # Flächenzahl 1..4 bei Füllungen

    @property
    def key(self) -> tuple[str, str, int | None, bool]:
        return self.entry.system, self.entry.code, self.fdi, self.planned

    @property
    def start(self) -> int:
        return min((t.hit.start for t in self.hits), default=10**9)


class Builder:
    def __init__(self, catalog: Catalog, ctx: TextContext) -> None:
        self.catalog, self.ctx = catalog, ctx
        self.drafts: dict[tuple[str, str, int | None, bool], Draft] = {}
        self.dictated_surcharges: list[Tagged] = []
        self._surface_words: list[Tagged] = []

    def add(self, entry: Entry, fdi: int | None, t: Tagged, count: int = 1, flag: str | None = None,
            like: Tagged | None = None) -> Draft:
        """Fundstelle ``t`` einem Entwurf zuordnen; ``like`` gibt geplant/erbracht vor (sonst ``t``)."""
        plan = (like or t).plan
        draft = self.drafts.setdefault((entry.system, entry.code, fdi, plan is not None),
                                       Draft(entry, fdi, plan is not None))
        draft.hits.append(t)
        draft.count = max(draft.count, count)
        draft.plan = draft.plan or plan
        if flag and flag not in draft.decide:
            draft.decide.append(flag)
        return draft

    def build(self, tagged: list[Tagged]) -> list[Draft]:
        fillings = [t for t in tagged if t.hit.entry.family]
        removals = [t for t in tagged if t.hit.entry.code in REMOVAL.get(t.hit.entry.system, {}).values()]
        rest = [t for t in tagged if t not in fillings and t not in removals]
        self._fillings(fillings)
        self._removals(removals)
        sessions: dict[tuple[str, str, bool], list[Tagged]] = {}
        for t in rest:
            entry = t.hit.entry
            if entry.system == "GOZ" and entry.code in SURCHARGE_CODES:
                if t.plan is None:
                    self.dictated_surcharges.append(t)
            elif (entry.system, entry.code) in ROOT_PAIRS:
                self._root_pair(t)
            elif (unit := self.catalog.unit(entry)) == "session":
                sessions.setdefault((entry.system, entry.code, t.plan is not None), []).append(t)
            else:
                self._per_tooth(t, entry, unit)
        for group in sessions.values():
            self._session(group)
        self._absorb_toothless()
        return sorted(self.drafts.values(), key=lambda d: d.start)

    def _absorb_toothless(self) -> None:
        """Fundstelle ohne Zahn ("antiinfektiöse Therapie") gehört zu derselben Leistung mit Zahn ("Kürettage 17-27")."""
        for key, d in list(self.drafts.items()):
            if d.fdi is not None or self.catalog.unit(d.entry) == "session":
                continue
            same = ROOT_PAIRS.get((d.entry.system, d.entry.code)) or d.entry.family or (d.entry.code,)
            hosts = [o for o in self.drafts.values() if o.fdi is not None and o.planned == d.planned
                     and o.entry.system == d.entry.system and o.entry.code in same]
            if hosts:
                for host in hosts:
                    host.hits = sorted(host.hits + [t for t in d.hits if t not in host.hits], key=lambda t: t.hit.start)
                del self.drafts[key]

    # --- Füllungen --------------------------------------------------------------------

    def _fillings(self, tagged: list[Tagged]) -> None:
        """Flächenzahl-Wörter in einer Zahngruppe ("37 mod") stecken schon in den Flächen des Zahns."""
        counts = [t for t in tagged if surface_count_word(t.hit.keyword) and not t.hit.code_word]
        hints = [t for t in counts if not self.ctx.in_group(t.hit.start)]
        acts = [t for t in tagged if t not in counts]
        self._surface_words = [t for t in counts if t not in hints]
        for planned in (False, True):
            for family in dict.fromkeys(t.hit.entry.family for t in acts):
                group = [t for t in acts if t.hit.entry.family == family and (t.plan is not None) == planned]
                if group:
                    self._filling_family(family, group, hints)

    def _filling_family(self, family: tuple[str, ...], acts: list[Tagged], hints: list[Tagged]) -> None:
        near = [h for h in hints if h.sentence in {t.sentence for t in acts}]
        teeth = _unique(tooth for t in acts for tooth in t.teeth) or _unique(
            tooth for h in near for tooth in h.teeth)
        for tooth in teeth or [None]:
            own = [t for t in acts if tooth is None or tooth in t.teeth] or acts
            own += [t for t in acts if not t.teeth and t not in own]
            sentences = {t.sentence for t in own if t.teeth} or {t.sentence for t in own}
            mine = [h for h in near if h.sentence in sentences and (tooth is None or not h.teeth or tooth in h.teeth)]
            explicit = {t.hit.entry.family.index(t.hit.entry.code) + 1 for t in own if t.hit.code_word}
            said = {h.hit.entry.family.index(h.hit.entry.code) + 1 for h in mine}
            chosen = explicit or said
            dictated = len(set(tooth.surfaces)) if tooth and tooth.surfaces else None
            flag = None
            if len(chosen) == 1:
                count = next(iter(chosen))
                if dictated and min(dictated, 4) != count:
                    flag = f"Flächen „{tooth.surfaces}“ an {tooth.fdi} diktiert, Ziffer nach {count} Flächen gewählt – prüfen"
            elif dictated:
                count = dictated
                if chosen:
                    flag = "widersprüchliche Flächenzahlen diktiert – Ziffer aus den Flächen am Zahn gewählt"
            else:
                count = 1
                flag = f"Flächenzahl nicht diktiert – {family[0]}–{family[3]} wählen"
            entry = self.catalog.get(acts[0].hit.entry.system, family[min(count, 4) - 1])
            if tooth is None:
                flag = flag or "Zahn nicht diktiert"
            spoken = [h for h in self._surface_words if tooth and tooth in h.teeth
                      and set(h.hit.keyword) == set(tooth.surfaces)]
            for t in own + mine + spoken:
                self.add(entry, tooth.fdi if tooth else None, t, 1, flag, like=acts[0]).surfaces = min(count, 4)

    # --- Zahnentfernung ----------------------------------------------------------------

    def _removals(self, tagged: list[Tagged]) -> None:
        mods = [(t, removal_modifier(t.hit.keyword)) for t in tagged
                if not t.hit.code_word and not REMOVAL_ACT.search(t.hit.keyword)]
        for t in tagged:
            if any(t is m for m, _kind in mods):
                continue
            system = t.hit.entry.system
            kinds = {v: k for k, v in REMOVAL[system].items()}
            for tooth in t.teeth or (None,):
                applying = [(m, kind) for m, kind in mods if kind and (
                    (tooth is not None and tooth in m.teeth)
                    or (m.sentence == t.sentence and (tooth is None or not m.teeth)))]
                found = {kind for _m, kind in applying}
                own_code = t.hit.code_word or "implantat" in t.hit.keyword
                code, flag = self._removal_code(system, kinds[t.hit.entry.code], own_code, found, tooth)
                entry = self.catalog.get(system, code)
                self.add(entry, tooth.fdi if tooth else None, t, 1, flag)
                for m, _kind in applying:
                    self.add(entry, tooth.fdi if tooth else None, m, like=t)

    @staticmethod
    def _removal_code(system: str, kind: str, dictated: bool, found: set[str],
                      tooth: ToothRef | None) -> tuple[str, str | None]:
        table = REMOVAL[system]
        if dictated:
            return table[kind], None if tooth else "Zahn nicht diktiert"
        if kind in OSTEO_KINDS:
            retained = kind == "osteo_retained" or "retained" in found
            return table["osteo_retained" if retained else "osteo"], None if tooth else "Zahn nicht diktiert"
        root = None
        if tooth:
            root = "multi" if multi_rooted(tooth.fdi) else "single"
        elif "multi" in found or kind == "multi":
            root = "multi"
        if kind == "fractured" or "fractured" in found:
            if "fractured" in table:
                alt = table[root] if root else f"{table['single']}/{table['multi']}"
                return table["fractured"], f"tieffrakturiert laut Diktat – sonst {alt}"
            flag = f"tieffrakturiert laut Diktat: keine eigene {system}-Ziffer im Katalog v1"
            return table[root or "single"], flag if root else flag + "; ein-/mehrwurzelig prüfen"
        if root is None:
            return table["single"], "Zahn nicht diktiert – ein- oder mehrwurzelig prüfen"
        return table[root], None

    # --- übrige Positionen -------------------------------------------------------------

    def _root_pair(self, t: Tagged) -> None:
        single, multi = ROOT_PAIRS[(t.hit.entry.system, t.hit.entry.code)]
        if not t.teeth:
            self.add(t.hit.entry, None, t, 1, f"Zahn nicht diktiert – {single}/{multi} je Zahn wählen")
        for tooth in t.teeth:
            entry = self.catalog.get(t.hit.entry.system, multi if multi_rooted(tooth.fdi) else single)
            self.add(entry, tooth.fdi, t)

    def _per_tooth(self, t: Tagged, entry: Entry, unit: str) -> None:
        canals = self.ctx.canals(t.hit.start) if unit == "canal" else None
        flag = "Kanalzahl nicht diktiert – je Kanal berechnen" if unit == "canal" and canals is None else None
        if t.teeth:
            for tooth in _unique(t.teeth):
                self.add(entry, tooth.fdi, t, canals or 1, flag)
            return
        count = self.ctx.teeth_count(t.hit.start) if unit == "tooth" else canals
        count = count or self.ctx.times(t.hit.start, t.hit.end)
        self.add(entry, None, t, count or 1, flag or (None if count else "Zahn nicht diktiert – je Zahn"))

    def _session(self, group: list[Tagged]) -> None:
        repeats = max(Counter(t.hit.keyword for t in group).values())
        times = max((self.ctx.times(t.hit.start, t.hit.end) or 0 for t in group), default=0)
        for t in group:
            draft = self.add(t.hit.entry, None, t, max(repeats, times))
            draft.context = _unique_fdi(draft.context + tuple(tooth.fdi for tooth in t.teeth))


def _unique(items) -> list:
    return list(dict.fromkeys(items))


def _unique_fdi(numbers: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(dict.fromkeys(numbers))
