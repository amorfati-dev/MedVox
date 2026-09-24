"""Endodontie: Zuzahlungs-Optionen beim Kassenpatienten und Kanalzahl der Je-Kanal-Zuzahlungen.

Zu jeder erbrachten BEMA-Position der Endodontie bietet der Extraktor dem Kassenpatienten die
erlaubten Privatpositionen der Zuzahlungs-Liste an, die diese Ziffer als Basis nennen (elektrometrische
Längenbestimmung GOZ 2400 und elektrophysikalisch-chemische Methoden GOZ 2420 neben BEMA 32,
adhäsive Befestigung GOZ 2197 neben 34/35), dazu das eigenständige Privat-Paar einer Endo-Position
(GOZ 2430 zu BEMA 34, erst ab der 4. Einlage). Wie bei der Mehrkostenfüllung (2080 zu 13b) sind das
nur Optionen: nie vorausgewählt, kopiert erst nach Antippen. Diktierte Positionen („Längenbestimmung“)
stehen schon als Zuzahlung da und werden nicht noch einmal angeboten.

Je Kanal berechnete Zuzahlungen zählen die am selben Zahn diktierte Kanalzahl ihrer Basis („WK*3“ →
2400 dreimal); ohne diktierte Kanalzahl bleibt es bei 1 mit Prüfhinweis – nie geraten.
"""

from __future__ import annotations

from medvox.extract_billing import translate_draft
from medvox.extract_build import Draft
from medvox.extract_catalog import Catalog, Entry
from medvox.extract_rules import CANALS_OPEN

ENDO = "Endodontie"


def endo_offers(catalog: Catalog, primaries: list[Draft], present: list[Draft]) -> list[Draft]:
    """Kassenpatient: Zuzahlungs-Optionen zu jeder erbrachten Endo-Position, ohne schon vorhandene."""
    taken = {d.key for d in present}
    result: list[Draft] = []
    for d in primaries:
        if d.planned or d.entry.system != "BEMA" or d.entry.area != ENDO:
            continue
        for listed in _fitting(catalog, d.entry):
            for alt in translate_draft(catalog, d, listed, d.hits):
                if alt.key in taken:
                    continue
                taken.add(alt.key)
                alt.alternative_to = d
                if catalog.unit(alt.entry) == "canal" and catalog.unit(d.entry) == "canal":
                    _canal_count(alt, d)
                result.append(alt)
    return result


def _fitting(catalog: Catalog, bema: Entry) -> list[Entry]:
    pairs = {e.key for e, _link in catalog.equivalents(bema)}
    return [e for e in catalog.entries if catalog.co_payment_allowed(e) and (
        bema.code in e.co_payment.basis or (not e.co_payment.basis and e.key in pairs))]


def adopt_canal_counts(catalog: Catalog, drafts: list[Draft]) -> None:
    """Je-Kanal-Zuzahlung ohne eigene Kanalzahl übernimmt die diktierte Kanalzahl ihrer Basis am selben Zahn."""
    for z in drafts:
        if z.counted or z.fdi is None or z.entry.co_payment is None or catalog.unit(z.entry) != "canal":
            continue
        basis = {c for code in z.entry.co_payment.basis if (b := catalog.get("BEMA", code))
                 for c in (b.code, *(e.code for e, _link in catalog.equivalents(b)))}
        host = next((d for d in drafts if d.counted and d.fdi == z.fdi and d.planned == z.planned
                     and d.entry.code in basis and catalog.unit(d.entry) == "canal"), None)
        if host is not None:
            _canal_count(z, host)


def _canal_count(z: Draft, host: Draft) -> None:
    """Kanalzahl von ``host`` übernehmen, wenn sie diktiert ist; sonst bleibt 1 mit Prüfhinweis."""
    if not host.counted:
        if CANALS_OPEN not in z.decide:
            z.decide.append(CANALS_OPEN)
        return
    z.count, z.counted = host.count, True
    if CANALS_OPEN in z.decide:
        z.decide.remove(CANALS_OPEN)
    z.limit_note = f"Kanalzahl wie {host.entry.label} ({host.count}×)"
