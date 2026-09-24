"""Abrechnungsregeln über die ganze Sitzung (WP-8): Enthaltensein, „nicht neben“,
Zuzahlungs-Angebote, Privat-Gegenstücke ohne hinterlegtes Paar und der GOZ-Zuschlag.

Den Patiententyp setzt ``extract_patient`` vorher um: jede Leistung mit hinterlegtem Paar
(``equivalent``) ist dann schon genau eine Ziffer im System des Patienten. Hier bleibt:
einem Kassenpatienten wird das erlaubte Zuzahlungs-Gegenstück einer BEMA-Position
(Mehrkostenfüllung) als zusätzliche Alternative angeboten; für Leistungen ohne Paar liefert
der Regeltext („Privatpatient: GOZ …“) die Gegenstücke, und stehen BEMA und GOZ derselben
Leistung am selben Zahn nebeneinander, trägt die GOZ-Position als Alternative einen
Entscheidungshinweis. Der Zuschlag 0500–0530 gilt nur für Privatpatienten.
"""

from __future__ import annotations

from medvox.extract_draft import Draft
from medvox.extract_catalog import Catalog, Entry, related
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


# --- Gegenstücke -------------------------------------------------------------------------


def translate_draft(catalog: Catalog, d: Draft, listed: Entry, hits: list) -> list[Draft]:
    """Entwurf ``d`` als Entwürfe von ``listed``: Einheit je Zahn/Sitzung, ein-/mehrwurzelig aus der FDI-Nummer."""
    unit = catalog.unit(listed)
    count = d.count if unit == catalog.unit(d.entry) else 1
    if d.fdi is not None:
        fdis: list[int | None] = [d.fdi]
    else:
        fdis = [None] if unit == "session" else list(d.context) or [None]
    result = []
    for fdi in fdis:
        entry = listed
        if fdi is not None and entry.key in ROOT_PAIRS:
            single, multi = ROOT_PAIRS[entry.key]
            entry = catalog.get(entry.system, multi if multi_rooted(fdi) else single)
        new = Draft(entry, fdi, d.planned, list(hits), count, d.context if fdi is None else ())
        if d.entry.family or d.entry.code in REMOVAL.get(d.entry.system, {}).values():
            new.decide += [f for f in d.decide if f not in new.decide]  # gleiche Herleitung
        if fdi is None and unit != "session" and not new.decide:
            new.decide.append("Zahn nicht diktiert – je Zahn")
        result.append(new)
    return result


def co_payment_offers(catalog: Catalog, drafts: list[Draft]) -> list[Draft]:
    """Kassenpatient: erlaubtes Zuzahlungs-Paar, das die erbrachte BEMA-Position als Basis nennt (Mehrkostenfüllung)."""
    taken = {d.key for d in drafts}
    result: list[Draft] = []
    for d in drafts:
        if d.planned or d.entry.system != "BEMA":
            continue
        for listed, _link in catalog.equivalents(d.entry):
            # Nur „neben“ (Basis nennt die BEMA-Ziffer), nicht „statt“ (2000 statt IP5 außerhalb der Altersgrenze).
            if not catalog.co_payment_allowed(listed) or d.entry.code not in listed.co_payment.basis:
                continue
            for alt in translate_draft(catalog, d, listed, d.hits):
                if alt.key not in taken:
                    taken.add(alt.key)
                    alt.alternative_to = d
                    result.append(alt)
    return result


def counterpart_drafts(catalog: Catalog, d: Draft) -> list[Draft]:
    """Privat-Gegenstücke einer BEMA-Position laut Regeltext – Rückfall, wenn kein Paar hinterlegt ist."""
    result: list[Draft] = []
    seen = set()
    for listed, hits in _counterpart_entries(catalog, d):
        for c in translate_draft(catalog, d, listed, hits):
            if c.key not in seen:
                seen.add(c.key)
                result.append(c)
    return result


def exclusive(bema: Draft, rival: Draft) -> None:
    """BEMA- und GOZ-Position derselben Leistung am selben Zahn ohne hinterlegtes Paar: nur eine abrechnen."""
    rival.alternative_to = bema
    where = f" an {bema.fdi}" if bema.fdi is not None else ""
    flag = (f"{bema.entry.label} (Kassenpatient) oder {rival.entry.label} (Privatpatient) für dieselbe "
            f"Leistung{where} – nur eine abrechnen")
    for d in (bema, rival):
        if flag not in d.decide:
            d.decide.append(flag)


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
    found = []
    for e in listed:
        hits = [t for t in d.hits if not t.hit.code_word and any(related(t.hit.keyword, k) for k in e.keywords)]
        if hits:
            found.append((e, hits))
    main = [e for c in parts if c.main_rule and (e := catalog.get(c.system, c.code))]
    return found or [(e, list(d.hits)) for e in main]


# --- Zuschlag ------------------------------------------------------------------------------


def surcharge(catalog: Catalog, drafts: list[Draft], dictated: list, notes: list[str],
              patient: str) -> Draft | None:
    """Privatpatient: genau ein GOZ-Zuschlag je Sitzung aus der höchstbewerteten chirurgischen GOZ-Leistung."""
    # Der Zuschlag gilt nur für Privatpatienten: beim Kassenpatienten wird er nie erwogen, auch
    # nicht diktiert. Beim Privatpatienten ist jede Chirurgie schon auf ihre GOZ-Ziffer umgestellt
    # („Ost1“ = 3030), deren Punkte die Stufe bestimmen.
    if patient != "privat":
        if dictated:
            notes.append("Zuschlag 0500–0530 diktiert: gilt nur für Privatpatienten – beim Kassenpatienten "
                         "nicht vorgeschlagen")
        return None
    goz = [d for d in drafts if not d.planned and d.entry.system == "GOZ" and d.entry.area == "Chirurgie"
           and d.entry.code not in SURCHARGE_CODES]
    surgical = [d for d in goz if d.alternative_to is None]
    undecided = [d for d in goz if d.alternative_to is not None]
    if surgical or not undecided or not dictated:
        return _surcharge(catalog, surgical, dictated, notes)
    result = _surcharge(catalog, undecided, dictated, notes)
    if result:
        rival = max(undecided, key=lambda d: d.entry.points or 0)
        result.alternative_to = rival.alternative_to
        result.decide.insert(0, f"Zuschlag nur, wenn {rival.entry.label} abgerechnet wird")
    return result


def _surcharge(catalog: Catalog, surgical: list[Draft], dictated: list, notes: list[str]) -> Draft | None:
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
