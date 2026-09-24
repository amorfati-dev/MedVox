"""Höchstzahl je Position (Katalogfeld ``max_per``) im Regel-Extraktor.

Der Builder zählt Fundstellen: „Kofferdam gelegt“ an 36 und noch einmal an 37 ergibt zwei. Abrechnen
darf man aber höchstens, was der amtliche Text erlaubt – BEMA 12 einmal je Sitzung, je Kieferhälfte
oder Frontzahnbereich. ``apply_limits`` begrenzt die Anzahl darauf und nennt die Begrenzung in der
Begründung; eine Position fällt dabei nie weg. Es wirken nur vom Behandler bestätigte Höchstzahlen
(``max_per_status`` „bestaetigt“); Vorschläge ändern nichts, bis er sie bestätigt.

Bei ``kieferhaelfte`` bestimmen die diktierten FDI-Nummern die Bereiche: Frontzahnbereich = Zähne
13–23 bzw. 33–43, Kieferhälfte = Seitenzähne 4–8 eines Quadranten (Milchzähne wie ihr bleibender
Quadrant). Liegen die Zähne in mehreren Bereichen, steht die Position je Bereich einmal da – mit den
Zähnen dieses Bereichs, also in deren Evident-Zeile. Ohne Zahnnummer bleibt es bei der Höchstzahl
eines Bereichs, und der Behandler bekommt einen Prüfhinweis statt einer geratenen höheren Anzahl.
Einheiten ``zahn`` und ``kanal`` zählt der Builder schon je Zahn bzw. nach diktierter Kanalzahl;
hier wird nur ein Zahn-Entwurf mit mehr als der Höchstzahl begrenzt.
"""

from __future__ import annotations

from dataclasses import replace

from medvox.extract_build import Draft

PER = {
    "sitzung": "je Sitzung",
    "kieferhaelfte": "je Kieferhälfte oder Frontzahnbereich",
    "zahn": "je Zahn",
    "kanal": "je Kanal",
    "flaeche": "je Fläche",
    "halbjahr": "je Kalenderhalbjahr",
    "jahr": "je Jahr",
}
_SIDES = {1: "OK rechts", 2: "OK links", 3: "UK links", 4: "UK rechts"}
NO_REGION = "Kieferhälfte/Frontzahnbereich nicht diktiert – je weiterem Bereich einmal mehr berechnen"


def region(fdi: int) -> str:
    """Bereich einer FDI-Nummer: "OK-Front", "UK-Front" oder die Kieferhälfte ("UK links")."""
    quadrant, tooth = divmod(fdi, 10)
    if quadrant >= 5:  # Milchzähne 51–85 wie ihr bleibender Quadrant
        quadrant -= 4
    if tooth <= 3:
        return "OK-Front" if quadrant in (1, 2) else "UK-Front"
    return _SIDES[quadrant]


def apply_limits(drafts: list[Draft]) -> list[Draft]:
    """Anzahl jedes Entwurfs auf ``max_per`` begrenzen; je-Bereich-Positionen nach Bereichen aufteilen."""
    result: list[Draft] = []
    for d in drafts:
        if d.entry.limit is None:
            result.append(d)
            continue
        unit, most = d.entry.limit
        if unit == "kieferhaelfte":
            result += _per_region(d, most)
            continue
        # Grenze je Halbjahr/Jahr: mehr geht auch in einer Sitzung nicht (frühere Sitzungen kennt MedVox nicht)
        if unit in ("sitzung", "halbjahr", "jahr") or (unit == "zahn" and d.fdi is not None):
            _cap(d, most, PER[unit])
        result.append(d)
    return result


def _cap(d: Draft, most: int, per: str) -> bool:
    if d.count <= most:
        return False
    d.limit_note = f"{d.count}× diktiert, höchstens {most}× {per}"
    d.count = most
    return True


def _per_region(d: Draft, most: int) -> list[Draft]:
    teeth = (d.fdi,) if d.fdi is not None else d.context
    regions: dict[str, list[int]] = {}
    for fdi in teeth:
        regions.setdefault(region(fdi), []).append(fdi)
    per = PER["kieferhaelfte"]
    if len(regions) <= 1:
        if _cap(d, most, per):
            if regions:
                d.limit_note += f" ({next(iter(regions))})"
            elif NO_REGION not in d.decide:
                d.decide.append(NO_REGION)
        return [d]
    pieces = []
    for label, fdis in regions.items():
        own = [t for t in d.hits if any(tooth.fdi in fdis for tooth in t.teeth)] or list(d.hits)
        piece = replace(d, hits=own, count=len(own), context=tuple(fdis), decide=list(d.decide))
        _cap(piece, most, per)
        piece.limit_note = "; ".join(filter(None, [f"eigene Position für {label} ({per})", piece.limit_note]))
        pieces.append(piece)
    return pieces
