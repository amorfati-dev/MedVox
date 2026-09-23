"""Patiententyp im Regel-Extraktor: jede diktierte Leistung genau einmal, im richtigen System.

Eine Leistung hat oft ein Paar im anderen System (Katalogfeld ``equivalent``: Ost1 = BEMA 47a
/ GOZ 3030). Der Patiententyp wählt genau eine Seite, nie beide:

- ``kasse``: BEMA. GOZ/GOÄ nur, wenn die Position auf der Zuzahlungs-Liste steht
  (``zuzahlung.allowed``); eine sonst diktierte Privatziffer wird auf ihr BEMA-Paar umgestellt.
  Eine Mehrkosten-Füllung oder ein Inlay bringt ihre BEMA-Basis mit: die zahlt die Kasse.
- ``privat``: nur GOZ/GOÄ. BEMA-Fundstellen werden auf ihr Privat-Paar umgestellt.

Umgestellt wird schon an der Fundstelle, bevor der Builder Flächenzahl, Zahnentfernung und
ein-/mehrwurzelig auflöst: so gelten dessen Regeln unverändert im Zielsystem, und „Osteotomie 38,
GOZ 3030“ ergibt eine einzige Position. Ohne hinterlegtes Paar bleibt die Fundstelle, wie sie ist;
``settle`` bietet dann das Gegenstück aus dem Regeltext als Alternative mit Entscheidung an oder
nennt den Wegfall in den Hinweisen.
"""

from __future__ import annotations

from dataclasses import replace

from medvox.extract_billing import counterpart_drafts, exclusive
from medvox.extract_build import Draft, Tagged
from medvox.extract_catalog import Catalog, Entry, related
from medvox.extract_match import Hit
from medvox.extract_rules import private_only
from medvox.extract_text import TextContext

PATIENT_TYPES = ("kasse", "privat")
PATIENT_LABEL = {"kasse": "Kassenpatient", "privat": "Privatpatient"}
_OWN = {"kasse": ("BEMA",), "privat": ("GOZ", "GOÄ")}


def kind(catalog: Catalog, entry: Entry, patient: str) -> str:
    """"bema", "goz" (Privatleistung, auch GOÄ) oder "zuzahlung" (Privatleistung beim Kassenpatienten)."""
    if entry.system == "BEMA":
        return "bema"
    if patient == "kasse" and catalog.co_payment_allowed(entry):
        return "zuzahlung"
    return "goz"


def translate(catalog: Catalog, tagged: list[Tagged], patient: str) -> list[Tagged]:
    """Fundstellen im fremden System auf ihr hinterlegtes Paar im System des Patienten umstellen."""
    result = []
    for t in tagged:
        entry = t.hit.entry
        stays = entry.system in _OWN[patient] or (patient == "kasse" and (
            catalog.co_payment_allowed(entry) or private_only(entry, t.hit.keyword)))
        target = None if stays else _pick(catalog, t.hit)
        result.append(replace(t, hit=replace(t.hit, entry=target, via=entry)) if target else t)
    return result


def _pick(catalog: Catalog, hit: Hit) -> Entry | None:
    """Paar zur Fundstelle; bei mehreren (BEMA 12 = GOZ 2030/2040) das zum diktierten Wort passende."""
    options = [e for e, _link in catalog.equivalents(hit.entry)]
    if len(options) > 1 and not hit.code_word:
        options = [e for e in options if any(related(hit.keyword, k) for k in e.keywords)] or options
    return options[0] if options else None


def co_payment_basis(catalog: Catalog, ctx: TextContext, drafts: list[Draft]) -> list[Draft]:
    """Kassenpatient: vor jede erbrachte Mehrkosten-Füllung/Inlay (GOZ-Füllungsfamilie) ihre BEMA-Basis als Kassenanteil.

    Nur, wenn am Zahn nicht schon eine der Basis-Ziffern erbracht ist; die Ziffer folgt der Flächenzahl.
    """
    result: list[Draft] = []
    for d in drafts:
        basis = _basis(catalog, d)
        if basis and not any(o.entry.system == "BEMA" and o.entry.code in d.entry.co_payment.basis
                             and o.fdi == d.fdi for o in drafts):
            words = ", ".join(dict.fromkeys(ctx.original(t.hit.start, t.hit.end) for t in d.hits))
            share = Draft(basis, d.fdi, False, list(d.hits), d.count, d.context, list(d.decide), surfaces=d.surfaces)
            share.reason = f"Kassenanteil: Basis der Zuzahlung {d.entry.label} – wegen: {words}"
            result.append(share)
        result.append(d)
    return result


def _basis(catalog: Catalog, d: Draft) -> Entry | None:
    """BEMA-Basis nach Flächenzahl (2080 -> 13b, Inlay 2170 dreiflächig -> 13c)."""
    if d.planned or d.alternative_to is not None or not d.entry.family or not catalog.co_payment_allowed(d.entry):
        return None
    basis = d.entry.co_payment.basis
    if len(basis) <= 1:
        return catalog.get("BEMA", basis[0]) if basis else None
    surfaces = d.surfaces or d.entry.family.index(d.entry.code) + 1
    return catalog.get("BEMA", basis[min(surfaces, len(basis)) - 1])


def _translated(d: Draft) -> list:
    """Umgestellte Fundstellen, die zu dieser Leistung selbst gehören (nicht das Zählwort einer anderen Füllungsart)."""
    return [t for t in d.hits if t.hit.via and t.hit.entry.family == d.entry.family]


def pair_flags(catalog: Catalog, drafts: list[Draft]) -> None:
    """Umgestellte Leistungen tragen den Unterschied, den das Paar notiert (Einheit, Anzahl), als Prüfhinweis."""
    for d in drafts:
        for t in _translated(d):
            link = catalog.link(t.hit.via, t.hit.entry)
            if link and link.note and link.note not in d.decide:
                d.decide.append(link.note)


def pair_label(catalog: Catalog, d: Draft, patient: str) -> str:
    """„BEMA 47a ↔ GOZ 3030, für Privatpatienten GOZ“ für eine umgestellte Leistung, sonst leer."""
    via = list(dict.fromkeys(t.hit.via for t in _translated(d)))
    if not via:
        return ""
    pairs = [e for e, _link in catalog.equivalents(d.entry)]
    # "Kofferdam privat" -> 12: das diktierte Paar; AITa -> 4075 (mehrwurzelig): das Paar der Zielziffer
    other = [e for e in via if e in pairs] or [e for e in pairs if e.system == via[0].system] or via
    return f"{'/'.join(e.label for e in other)} ↔ {d.entry.label}, für {PATIENT_LABEL[patient]}en {d.entry.system}"


def settle(catalog: Catalog, drafts: list[Draft], patient: str, notes: list[str]) -> tuple[list[Draft], list[Draft]]:
    """(Vorschläge im System des Patienten, Rückfall-Alternativen für Leistungen ohne hinterlegtes Paar)."""
    own = [d for d in drafts if kind(catalog, d.entry, patient) != ("goz" if patient == "kasse" else "bema")]
    foreign = [d for d in drafts if not any(d is o for o in own)]
    extra: list[Draft] = []
    if patient == "kasse":
        for f in foreign:
            rival = None if f.planned else next((b for b in own if b.entry.system == "BEMA" and not b.planned and any(
                c.key == f.key for c in counterpart_drafts(catalog, b))), None)
            if rival:
                exclusive(rival, f)
                extra.append(f)
            else:
                notes.append(_dropped(f, patient))
        return own, extra
    taken = {d.key: d for d in own}
    for b in foreign:
        options = [] if b.planned else counterpart_drafts(catalog, b)
        if not options:
            notes.append(_dropped(b, patient))
        for c in options:
            if c.key in taken:  # dieselbe Leistung ist schon als GOZ/GOÄ erkannt
                host = taken[c.key]
                host.hits = sorted(host.hits + [t for t in c.hits if t not in host.hits], key=lambda t: t.hit.start)
                continue
            c.alternative_to = b
            c.decide.insert(0, f"{b.entry.label} hat kein hinterlegtes Privat-Paar – Gegenstück laut Regeltext prüfen")
            taken[c.key] = c
            extra.append(c)
    return own, extra


def _dropped(d: Draft, patient: str) -> str:
    what = f"{d.entry.label} ({d.entry.title})"
    if patient == "privat":
        return f"{what} hat kein GOZ/GOÄ-Paar im Katalog – für Privatpatienten nicht vorgeschlagen"
    why = next((w for t in d.hits if (w := private_only(d.entry, t.hit.keyword))), None)
    if why:
        return f"{what}: {why} – bei Kassenpatienten nur privat nach Vereinbarung, nicht vorgeschlagen"
    return f"{what} steht nicht auf der Zuzahlungs-Liste und hat kein BEMA-Paar – für Kassenpatienten nicht vorgeschlagen"
