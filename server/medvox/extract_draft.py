"""Fundstelle und Entwurf des Regel-Extraktors (WP-8): die Bausteine zwischen Abgleich und Vorschlag.

``Tagged`` ist eine Katalog-Fundstelle mit ihren Zähnen, geplant/erbracht und Satz; ``Draft`` sammelt
Fundstellen derselben Ziffer am selben Zahn (bzw. derselben Sitzung) zu einem späteren Vorschlag.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from medvox.extract_catalog import Entry
from medvox.extract_match import Hit
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
    surfaces: int | None = None  # diktierte Flächenzahl 1..4 bei Füllungen, None wenn nicht erkannt
    limit_note: str = ""  # Höchstzahl (extract_limits) bzw. übernommene Kanalzahl (extract_endo), in der Begründung
    detail: str = ""  # diktierte Angabe zur Anzahl ("zweite wegen „lange Dauer“", extract_anesthesia), in der Begründung
    addon: bool = False  # Option „ggf. dazu“ zum Antippen (Ä1/Zst zur Weisheitszahn-OP, extract_surgery)
    counted: bool = False  # Kanalzahl ausdrücklich diktiert ("WK*3", "3 Kanäle"), nicht angenommen

    @property
    def key(self) -> tuple[str, str, int | None, bool]:
        return self.entry.system, self.entry.code, self.fdi, self.planned

    @property
    def start(self) -> int:
        return min((t.hit.start for t in self.hits), default=10**9)
