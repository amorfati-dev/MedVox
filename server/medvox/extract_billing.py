"""Abrechnungsregeln über die ganze Sitzung (WP-8): Enthaltensein, „nicht neben“,
Privat-Alternativen zu BEMA-Positionen und der GOZ-Zuschlag zu chirurgischen Leistungen.

Der Versichertenstatus schränkt nichts ein: BEMA- und GOZ-Vorschläge stehen
nebeneinander, und wo der Katalog ein Privat-Gegenstück nennt, kommt es als
zusätzliche Alternative dazu – es ersetzt nie den BEMA-Vorschlag.
"""

from __future__ import annotations

import re

from medvox.extract_build import Draft
from medvox.extract_catalog import Catalog, Entry, fold
from medvox.extract_rules import INCLUDED_IN, REMOVAL, ROOT_PAIRS, SURCHARGE_CODES, multi_rooted, surcharge_for


def drop_included(drafts: list[Draft], notes: list[str]) -> list[Draft]:
    """Leistungen entfernen, die in einer anderen Leistung derselben Sitzung/desselben Zahnes enthalten sind."""
    kept = []
    for d in drafts:
        host = INCLUDED_IN.get((d.entry.system, d.entry.code))
        teeth = _teeth(d)
        if host and any(
            (o.entry.system, o.entry.code) == host and o.planned == d.planned
            and (not teeth or not _teeth(o) or teeth & _teeth(o)) for o in drafts
        ):
            notes.append(f"{d.entry.label} ({d.entry.title}) ist in {host[0]} {host[1]} enthalten – nicht vorgeschlagen")
            continue
        kept.append(d)
    return kept


def flag_not_beside(catalog: Catalog, drafts: list[Draft], pool: list[Draft] | None = None) -> None:
    """Markiert Vorschläge aus ``drafts``, die laut Katalog nicht neben einer Ziffer aus ``pool`` stehen dürfen."""
    for d in drafts:
        clash = sorted(catalog.not_beside(d.entry) & {
            o.entry.code for o in (pool or drafts) if o.entry.system == d.entry.system and o.planned == d.planned})
        if clash:
            flag = f"laut Katalog nicht neben {', '.join(clash)} in derselben Sitzung – eine wählen"
            if flag not in d.decide:
                d.decide.append(flag)


def _teeth(d: Draft) -> set[int]:
    return {d.fdi} if d.fdi is not None else set(d.context)


# --- Privat-Alternativen ------------------------------------------------------------------


def alternatives(catalog: Catalog, drafts: list[Draft]) -> list[Draft]:
    """Je erbrachter BEMA-Position die Privat-Gegenstücke aus dem Katalog als zusätzliche Kandidaten."""
    taken = {d.key for d in drafts}
    result: list[Draft] = []
    for d in drafts:
        if d.planned or d.entry.system != "BEMA":
            continue
        for listed, hits in _counterpart_entries(catalog, d):
            unit = catalog.unit(listed)
            count = d.count if unit == catalog.unit(d.entry) else 1
            if d.fdi is not None:
                fdis: list[int | None] = [d.fdi]
            else:
                fdis = [None] if unit == "session" else list(d.context) or [None]
            for fdi in fdis:
                entry = listed
                if fdi is not None and (entry.system, entry.code) in ROOT_PAIRS:
                    single, multi = ROOT_PAIRS[(entry.system, entry.code)]
                    entry = catalog.get(entry.system, multi if multi_rooted(fdi) else single)
                key = (entry.system, entry.code, fdi, False)
                if key in taken:
                    continue
                taken.add(key)
                alt = Draft(entry, fdi, False, hits, count, d.context if fdi is None else ())
                alt.alternative_to = d
                if d.entry.family or d.entry.code in REMOVAL["BEMA"].values():
                    alt.decide += [f for f in d.decide if f not in alt.decide]  # gleiche Herleitung
                if fdi is None and unit != "session" and not alt.decide:
                    alt.decide.append("Zahn nicht diktiert – je Zahn")
                result.append(alt)
    return result


def _counterpart_entries(catalog: Catalog, d: Draft) -> list[tuple[Entry, list]]:
    """Privat-Gegenstücke im Katalog v1 plus die Fundstellen, die sie begründen."""
    head = catalog.get(d.entry.system, d.entry.family[0]) if d.entry.family else d.entry
    parts = catalog.counterparts(head)  # Füllungs-Familie: Gegenstück steht bei der einflächigen Ziffer
    listed = [e for c in parts if (e := catalog.get(c.system, c.code))]
    if d.entry.family:  # Füllung: gleiche Flächenzahl in der Privat-Familie
        index = d.entry.family.index(d.entry.code)
        families = {e.family: e.system for e in listed if e.family}
        return [(catalog.get(system, family[index]), list(d.hits)) for family, system in families.items()]
    kinds = {v: k for k, v in REMOVAL["BEMA"].items()}
    if d.entry.code in kinds:  # Zahnentfernung: gleiche Art im GOZ-Teil
        code = REMOVAL["GOZ"].get(kinds[d.entry.code])
        return [(catalog.get("GOZ", code), list(d.hits))] if code else []
    related = []
    for e in listed:
        hits = [t for t in d.hits if not t.hit.code_word and any(_related(t.hit.keyword, k) for k in e.keywords)]
        if hits:
            related.append((e, hits))
    main = [e for c in parts if c.main_rule and (e := catalog.get(c.system, c.code))]
    return related or [(e, list(d.hits)) for e in main]


def _related(trigger: str, keyword: str) -> bool:
    """Privat-Keyword ("kofferdam privat") passt zum auslösenden Wort ("kofferdam gelegt")."""
    core = re.sub(r"\s*\bprivat\b\s*", " ", fold(keyword)).strip()
    return bool(core) and (_contains(trigger, core) or _contains(core, trigger))


def _contains(text: str, part: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(part)}(?![a-z0-9])", text) is not None


# --- Zuschlag ------------------------------------------------------------------------------


def surcharge(catalog: Catalog, drafts: list[Draft], dictated: list, notes: list[str]) -> Draft | None:
    """Genau ein GOZ-Zuschlag je Sitzung aus der höchstbewerteten erbrachten chirurgischen GOZ-Leistung."""
    # Nur eine selbst als GOZ erbrachte Leistung trägt den Zuschlag. BEMA-Chirurgie und ihr bloß
    # angebotenes Privat-Gegenstück lösen ihn nie aus: der Zuschlag gilt nur für Privatpatienten.
    surgical = [d for d in drafts if not d.planned and d.entry.system == "GOZ" and d.alternative_to is None
                and d.entry.area == "Chirurgie" and d.entry.code not in SURCHARGE_CODES]
    known = [d for d in surgical if d.entry.points is not None]
    unknown = [d.entry.label for d in surgical if d.entry.points is None]
    driver = max(known, key=lambda d: d.entry.points or 0, default=None)
    said = sorted({t.hit.entry.code for t in dictated})
    if unknown:
        least = surcharge_for(driver.entry.points) if driver and driver.entry.points else None
        hint = f"; mindestens {least[0]} wegen {driver.entry.label} ({driver.entry.points} Punkte)" if least else ""
        notes.append(f"Zuschlag 0500–0530 nicht bestimmbar: Punktzahl von {', '.join(dict.fromkeys(unknown))} "
                     f"unbekannt{hint}")
        return _dictated_only(dictated, "Stufe nicht nachprüfbar (Punktzahl unbekannt)")
    if driver is None:
        return _dictated_only(dictated, "keine erbrachte chirurgische GOZ-Leistung erkannt")
    bracket = surcharge_for(driver.entry.points or 0)
    if bracket is None:
        return _dictated_only(dictated,
                              f"höchste chirurgische Leistung {driver.entry.label} hat nur {driver.entry.points} Punkte")
    code, lo, hi = bracket
    entry = catalog.get("GOZ", code)
    result = Draft(entry, None, False, list(driver.hits), 1, (driver.fdi,) if driver.fdi else driver.context)
    span = f"{lo}–{hi}" if hi else f"ab {lo}"
    result.reason = (f"Zuschlag zu {driver.entry.label} {driver.entry.title} ({driver.entry.points} Punkte, "
                     f"höchstbewertete chirurgische Leistung der Sitzung) → Stufe {span} Punkte")
    if said and said != [code]:
        result.decide.append(f"diktiert war {', '.join(said)} – Stufe aus den Punkten ist {code}")
    return result


def _dictated_only(dictated: list, why: str) -> Draft | None:
    if not dictated:
        return None
    first = dictated[0]
    d = Draft(first.hit.entry, None, False, list(dictated), 1)
    d.decide.append(f"Zuschlag diktiert, aber {why}")
    return d
