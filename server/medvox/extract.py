"""Regel-Extraktor: BEMA/GOZ/GOÄ-Vorschläge aus dem normalisierten Diktat (WP-8).

``extract(text, teeth, patient)`` ist eine reine Funktion über dem von ``lexicon.correct`` und
``normalize.normalize`` aufbereiteten Text; sie schlägt nur Ziffern aus
``catalog/catalog_v1.json`` vor. Der Patiententyp (``kasse`` | ``privat``) wählt je Leistung
genau eine Ziffer (``extract_patient``). Jeder Vorschlag nennt die auslösenden Wörter
(„wegen: Kofferdam gelegt“) und was der Behandler noch entscheiden muss. Geplantes
(„Extraktion 48 planen“) wird nie als erbracht vorgeschlagen, sondern mit
``planned=True`` getrennt geführt. Ablauf und Grenzen: ``server/README.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from medvox.extract_anesthesia import ANESTHESIA, aliases
from medvox.extract_billing import co_payment_offers, drop_included, flag_not_beside, surcharge
from medvox.extract_build import Builder
from medvox.extract_catalog import Catalog, load_catalog
from medvox.extract_conflicts import flag_conflicts
from medvox.extract_draft import Draft, Tagged
from medvox.extract_endo import adopt_canal_counts, endo_offers
from medvox.extract_limits import apply_limits
from medvox.extract_match import find_hits
from medvox.extract_patient import PATIENT_TYPES, co_payment_basis, kind, pair_flags, pair_label, settle, translate
from medvox.extract_rules import REMOVAL
from medvox.extract_surgery import SEVERE_OSTEOTOMY, flag_lone_pla0, severe_osteotomy, split_bleeding, wisdom_offers
from medvox.extract_text import TextContext
from medvox.extract_xray import bitewing_projections
from medvox.normalize import ToothRef


@dataclass(frozen=True)
class Suggestion:
    code: str
    system: str  # BEMA | GOZ | GOÄ
    title: str
    points: int | None  # BEMA-Bewertungszahl bzw. GOZ/GOÄ-Punktzahl; None = nicht verifiziert
    teeth: tuple[int, ...] = ()  # FDI-Nummern, zu denen der Vorschlag gehört
    count: int = 1  # Anzahl (je Kanal, je Zahn ohne Zahnangabe, "2x")
    reason: str = ""  # „wegen: …“ mit dem diktierten Wortlaut
    decide: tuple[str, ...] = ()  # was der Behandler noch entscheiden oder prüfen muss
    planned: bool = False  # nur geplant – nicht abrechnen
    alternative: bool = False  # zusätzlicher Kandidat (Zuzahlung, Gegenstück ohne Paar, Zuschlag dazu)
    kind: str = "bema"  # bema | goz (Privatleistung, auch GOÄ) | zuzahlung (Privatleistung beim Kassenpatienten)
    evident: str | None = None  # Evident-Kurzform aus dem Katalog ("l1"); None = Ziffer verwenden
    addon: bool = False  # Option „ggf. dazu“ (Ä1/Zst, unsicheres Nbl2): per Tipp übernehmbar, nie vorausgewählt


@dataclass
class Extraction:
    suggestions: list[Suggestion] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)  # Hinweise ohne Ziffer (verneint, enthalten, unbekannt)
    patient: str = "kasse"  # Patiententyp, für den die Vorschläge gelten


def analyze(text: str, teeth: list[ToothRef], patient: str = "kasse") -> Extraction:
    """Vorschläge plus Hinweise für ein normalisiertes Diktat eines Kassen- oder Privatpatienten."""
    if patient not in PATIENT_TYPES:
        raise ValueError(f"Patiententyp {patient!r} unbekannt, erwartet: {', '.join(PATIENT_TYPES)}")
    catalog = load_catalog()
    ctx = TextContext(text, teeth)
    hits, unknown = find_hits(catalog, ctx.folded)
    hits = aliases(catalog, ctx, hits)
    notes = [f"{code} diktiert, steht nicht im Katalog v1 – kein Vorschlag" for code in unknown]
    tagged = []
    for hit in hits:
        if ctx.negated(hit.start, hit.end):
            notes.append(f"verneint, nicht vorgeschlagen: „{ctx.original(*ctx.clause(hit.start)).strip(' ,')}“")
            continue
        teeth = (ctx.teeth_carried if carried(hit.entry) else ctx.teeth_for)(hit.start, hit.end)
        tagged.append(Tagged(hit, teeth, ctx.plan_marker(hit.start),
                             ctx.sentence(hit.start)))
    builder = Builder(catalog, ctx)
    drafts = drop_included(builder.build(translate(catalog, tagged, patient)), notes)
    pair_flags(catalog, drafts)
    drafts, extra = settle(catalog, drafts, patient, notes)
    if patient == "privat":
        bitewing_projections(ctx, drafts)
    flag_not_beside(catalog, drafts)
    primaries, bleeding = split_bleeding(ctx, [d for d in drafts if not d.planned], notes)
    extra += bleeding
    primaries = severe_osteotomy(primaries)
    adopt_canal_counts(catalog, primaries)
    if patient == "kasse":
        extra += co_payment_offers(catalog, primaries)
        extra += endo_offers(catalog, primaries, primaries + extra)
        primaries = co_payment_basis(catalog, ctx, primaries)
    extra += wisdom_offers(catalog, primaries, patient)
    flag_lone_pla0(primaries)
    flag_not_beside(catalog, extra, primaries + extra)
    flag_conflicts(catalog, primaries)
    added = surcharge(catalog, primaries + extra, builder.dictated_surcharges, notes, patient)
    ordered = _ordered(primaries, extra + ([added] if added else []))
    planned = [d for d in drafts if d.planned]
    suggestions = [_suggestion(catalog, ctx, d, patient) for d in apply_limits(ordered + planned)]
    return Extraction(suggestions, list(dict.fromkeys(notes)), patient)


def carried(entry) -> bool:
    """Anästhesie und Zahnentfernung ohne Zahnnummer im Satz gehören zum zuletzt diktierten Zahn (Diktierpausen)."""
    return entry.key in ANESTHESIA or entry.key == SEVERE_OSTEOTOMY or entry.code in REMOVAL.get(entry.system, {}).values()


def extract(text: str, teeth: list[ToothRef], patient: str = "kasse") -> list[Suggestion]:
    """Alle Vorschläge (erbracht, Alternativen, geplant) für ein normalisiertes Diktat."""
    return analyze(text, teeth, patient).suggestions


def billable_codes(suggestions: list[Suggestion]) -> list[str]:
    """Kopierformat der Praxis für die erbrachten Hauptvorschläge: "13c, 2x 41a, 4x IP5"."""
    totals: dict[str, int] = {}
    for s in suggestions:
        if not s.planned and not s.alternative:
            totals[s.code] = totals.get(s.code, 0) + s.count
    return [code if n == 1 else f"{n}x {code}" for code, n in totals.items()]


def _ordered(primaries: list[Draft], extra: list[Draft]) -> list[Draft]:
    """Hauptvorschläge in Diktatreihenfolge, Alternativen direkt hinter ihrer Hauptposition.

    Optionen „ggf. dazu“ (Ä1/Zst) ganz zuletzt: der GOZ-Zuschlag bleibt direkt hinter seiner Chirurgie."""
    result: list[Draft] = []
    for d in primaries:
        result.append(d)
        result += [a for a in extra if a.alternative_to is d and not a.addon]
    rest = [a for a in extra if not any(a is r for r in result)]
    return result + [a for a in rest if not a.addon] + [a for a in rest if a.addon]


def _suggestion(catalog: Catalog, ctx: TextContext, d: Draft, patient: str) -> Suggestion:
    words = list(dict.fromkeys(ctx.original(t.hit.start, t.hit.end) for t in d.hits))
    reason = d.reason or f"wegen: {', '.join(words)}"
    if (pair := pair_label(catalog, d, patient)) and not d.reason:
        reason += f" ({pair})"
    kind_ = kind(catalog, d.entry, patient)
    if kind_ == "zuzahlung" and d.entry.co_payment:
        co = d.entry.co_payment
        head = "Zuzahlung möglich" if d.alternative_to is not None else "Zuzahlung"
        head += f" zu {co.basis_label}" if co.basis else " (eigenständige Privatleistung)"
        reason = f"{head}: {co.note} – {reason}"
    elif patient == "kasse" and d.entry.analog:
        reason = f"{d.entry.analog} – {reason}"
    elif d.alternative_to is not None and not d.reason:
        reason = f"Privat-Alternative zu {d.alternative_to.entry.label} ({reason})"
    if d.detail:
        reason += f" – {d.detail}"
    if d.limit_note:
        reason += f" – {d.limit_note}"
    if d.planned:
        reason = f"geplant („{d.plan}“), nicht abrechnen – {reason}"
    teeth = (d.fdi,) if d.fdi is not None else d.context
    return Suggestion(
        d.entry.code, d.entry.system, d.entry.title, d.entry.points, tuple(teeth), d.count, reason,
        tuple(d.decide), d.planned, d.alternative_to is not None or d.addon, kind_, d.entry.evident, d.addon,
    )
