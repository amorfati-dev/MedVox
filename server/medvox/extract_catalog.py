"""Katalog v1 als Nachschlagewerk für den Regel-Extraktor (WP-8).

Lädt ``catalog/catalog_v1.json`` einmal und stellt bereit: Einträge nach System
und Ziffer, die Keyword-Liste für den Abgleich, die Abrechnungseinheit je
Eintrag (je Kanal / je Zahn / je Sitzung), die Höchstzahl (``max_per``), die Paare derselben Leistung in BEMA und
GOZ/GOÄ (``equivalent``), die Zuzahlungs-Liste (``zuzahlung``) und die im Regeltext
notierten Privat-Gegenstücke einer BEMA-Position. Der erweiterte Katalog wird bewusst
nicht geladen: der Extraktor darf nur Ziffern aus ``catalog_v1.json`` vorschlagen.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

CATALOG_PATH = Path(__file__).resolve().parent / "catalog" / "catalog_v1.json"

_UMLAUTS = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def fold(text: str) -> str:
    """Klein, Umlaute ausgeschrieben: "Kürettage" und "Kuerettage" fallen zusammen."""
    return unicodedata.normalize("NFC", text).lower().translate(_UMLAUTS)


def fold_with_map(text: str) -> tuple[str, list[int]]:
    """Gefalteter Text plus, je gefaltetem Zeichen, sein Index im Originaltext."""
    out: list[str] = []
    index: list[int] = []
    for i, ch in enumerate(text):
        piece = ch.lower().translate(_UMLAUTS)
        out.append(piece)
        index += [i] * len(piece)
    return "".join(out), index


@dataclass(frozen=True)
class Link:
    """Gegenstück derselben diktierten Leistung im anderen System (``equivalent``)."""

    system: str
    code: str
    note: str | None = None  # Unterschied, den der Behandler prüfen muss (Einheit, Anzahl)


@dataclass(frozen=True)
class CoPayment:
    """Eintrag der Zuzahlungs-Liste: darf ein Kassenpatient diese Privatleistung bezahlen?"""

    allowed: bool
    basis: tuple[str, ...]  # BEMA-Ziffern, neben denen sie üblich ist; leer = eigenständige Privatleistung
    note: str

    @property
    def basis_label(self) -> str:
        return f"BEMA {'/'.join(self.basis)}" if self.basis else ""


@dataclass(frozen=True)
class Conflict:
    """Position, die nicht in derselben Sitzung neben dieser abgerechnet wird (außer ``except``)."""

    system: str
    code: str
    note: str


@dataclass(frozen=True)
class Entry:
    code: str
    system: str  # BEMA | GOZ | GOÄ
    area: str
    title: str
    abbrev: str | None
    points: int | None
    keywords: tuple[str, ...]
    rules: tuple[str, ...]
    family: tuple[str, ...] = ()  # Füllungs-Familie (surfaces_to_code "1".."4"), sonst leer
    equivalents: tuple[Link, ...] = ()
    co_payment: CoPayment | None = None  # nur GOZ/GOÄ
    evident: str | None = None  # vom Behandler bestätigte Evident-Kurzform ("l1"), sonst None
    limit: tuple[str, int] | None = None  # bestätigtes max_per: ("kieferhaelfte", 1) = höchstens 1× je Bereich; sonst None
    analog: str | None = None  # Begründung, wenn beim Kassenpatienten als Analogposition berechnet (``analog``)
    conflicts: tuple[Conflict, ...] = ()  # nicht in derselben Sitzung (``conflicts``)
    per: tuple[str, int | None] | None = None  # ``max_per`` wie im Katalog, auch unbestätigt: ("unbegrenzt", None)

    @property
    def key(self) -> tuple[str, str]:
        return self.system, self.code

    @property
    def label(self) -> str:
        return f"{self.system} {self.code}"


# Einheit aus dem Regeltext: nur ein Regelanfang zählt ("je Zahn …"); in anderen Sätzen
# steht "je Zahn" auch verneint ("einmal je Sitzung, nicht je Zahn").
_PER_CANAL = re.compile(r"^je (?:Wurzel)?[Kk]anal")
_PER_TOOTH = re.compile(r"^je (?:Zahn|Kavität|behandeltem|einwurzeligem|mehrwurzeligem)")
# "Privatpatient: GOZ 2030/2040", "Mehrkosten/Privatpatient: GOZ 2050–2120", "(Privatpatient: GOZ 2400)"
_PRIVATE = re.compile(r"(^[^:(]*)?Privatpatient[^:]*:\s*(?:vgl\.\s*)?(GOZ|GOÄ)\s+([^;()]+)")
_PRIVATE_CODE = re.compile(r"Ä?\d{3,4}[a-z]?(?:\s*[–-]\s*Ä?\d{3,4}[a-z]?)?")
_NOT_BESIDE = re.compile(r"nicht neben ([^;(]+)")


@dataclass(frozen=True)
class Counterpart:
    system: str
    code: str
    main_rule: bool  # Regel beginnt mit "Privatpatient…" (sonst nur in Klammern erwähnt)


class Catalog:
    def __init__(self, raw: dict) -> None:
        self.version: str = raw.get("meta", {}).get("version", "")  # Katalogstand, z. B. in der Korrektur-Sammlung
        self.entries: list[Entry] = []
        for e in raw["entries"]:
            s2c = e.get("surfaces_to_code")
            family = tuple(s2c[k] for k in ("1", "2", "3", "4")) if s2c else ()
            links = tuple(Link(x["system"], x["code"], x.get("note")) for x in e.get("equivalent", []))
            z = e.get("zuzahlung")
            co = CoPayment(z["allowed"], tuple(z["basis"]), z["note"]) if z else None
            m = e.get("max_per")
            limit = (m["unit"], m["count"]) if e.get("max_per_status") == "bestaetigt" else None
            conflicts = tuple(Conflict(c["system"], c["code"], c["note"]) for c in e.get("conflicts", []))
            self.entries.append(Entry(
                e["code"], e["system"], e["area"], e["title"], e.get("abbrev"), e["points"],
                tuple(e["keywords"]), tuple(e["rules"]), family, links, co, e.get("evident"), limit,
                (e.get("analog") or {}).get("note"), conflicts, (m["unit"], m.get("count")) if m else None,
            ))
        self._by_key = {e.key: e for e in self.entries}
        self._by_folded: dict[tuple[str, str], Entry] = {(e.system, fold(e.code)): e for e in self.entries}

    def get(self, system: str, code: str) -> Entry | None:
        return self._by_key.get((system, code))

    def equivalents(self, entry: Entry) -> list[tuple[Entry, Link]]:
        """Gegenstücke derselben Leistung im anderen System, in Katalogreihenfolge."""
        return [(e, link) for link in entry.equivalents if (e := self.get(link.system, link.code))]

    def link(self, source: Entry, target: Entry) -> Link | None:
        return next((x for x in source.equivalents if (x.system, x.code) == target.key), None)

    @staticmethod
    def co_payment_allowed(entry: Entry) -> bool:
        """Steht auf der Zuzahlungs-Liste: Kassenpatient darf diese Privatleistung bezahlen."""
        return entry.co_payment is not None and entry.co_payment.allowed

    def find_code(self, system: str, folded_code: str) -> Entry | None:
        """Eintrag zu einer diktierten Ziffer ("13a", "ae935d") im genannten System.

        GOÄ-Ziffern auch ohne Ä („GOÄ 2430“ = Ä2430) – sonst träfe die Zahl die GOZ-Ziffer 2430.
        """
        entry = self._by_folded.get((system, folded_code))
        if entry is None and system == "GOÄ" and folded_code.isdigit():
            entry = self._by_folded.get((system, "ae" + folded_code))
        return entry

    def is_code_word(self, entry: Entry, folded_keyword: str) -> bool:
        """Keyword ist die Ziffer selbst oder die amtliche Kurzbezeichnung ("ip5", "l1", "2060")."""
        compact = folded_keyword.replace(" ", "")
        return compact in {fold(entry.code), fold(entry.abbrev or "")} or compact.isdigit()

    @staticmethod
    def unit(entry: Entry) -> str:
        """"canal", "tooth" oder "session" – bestimmt die Anzahl der Vorschläge."""
        if any(_PER_CANAL.match(r) for r in entry.rules):
            return "canal"
        if entry.family or any(_PER_TOOTH.match(r) for r in entry.rules):
            return "tooth"
        return "session"

    def stepper(self, entry: Entry) -> tuple[bool, int | None]:
        """Anzahl je Zeile am iPad änderbar (− / +) und ihre bestätigte Höchstzahl (None = keine).

        Nur mengenweise berechnete Positionen: je Kanal, oder je Sitzung mehrmals (``max_per`` mit einer Anzahl
        über 1). „unbegrenzt“ heißt nur amtlich ohne Höchstzahl (Extraktion, Beratung) und gibt kein − / +.
        Je-Zahn-Positionen stehen je Zahn einmal da – mehr Zähne ergänzt das Katalog-Blatt. Die Höchstzahl gilt nur bestätigt und nicht bei ``kanal`` (die zählt je Kanal).
        """
        unit = self.unit(entry)
        most = entry.per[1] if entry.per else None
        counted = unit == "canal" or (unit == "session" and (most or 0) > 1)
        limit = entry.limit[1] if entry.limit and entry.limit[0] != "kanal" else None
        return counted and (limit is None or limit > 1), limit

    def counterparts(self, entry: Entry) -> list[Counterpart]:
        """Privat-Gegenstücke einer BEMA-Position laut Regeltext (auch solche, die nicht im Katalog stehen)."""
        if entry.system != "BEMA":
            return []
        found: list[Counterpart] = []
        for rule in entry.rules:
            for m in _PRIVATE.finditer(rule):
                system, main = m.group(2), m.group(1) is not None
                for token in _PRIVATE_CODE.findall(m.group(3)):
                    for code in self._expand(system, token):
                        if all(c.code != code for c in found):
                            found.append(Counterpart(system, code, main))
        return found

    def _expand(self, system: str, token: str) -> list[str]:
        parts = [p.strip() for p in re.split(r"[–-]", token)]
        if len(parts) == 1:
            return parts
        lo, hi = (int(re.sub(r"\D", "", p)) for p in parts)
        return [e.code for e in self.entries
                if e.system == system and e.code.isdigit() and lo <= int(e.code) <= hi]

    def not_beside(self, entry: Entry) -> set[str]:
        """Ziffern desselben Systems, neben denen ``entry`` laut Regeltext nicht berechnet wird."""
        codes: set[str] = set()
        for rule in entry.rules:
            for m in _NOT_BESIDE.finditer(rule):
                codes |= {t for t in re.split(r"[\s,/]+", m.group(1)) if self.get(entry.system, t)}
        return codes


def related(trigger: str, keyword: str) -> bool:
    """Privat-Keyword ("kofferdam privat") passt zum auslösenden Wort ("kofferdam gelegt")."""
    core = re.sub(r"\s*\bprivat\b\s*", " ", fold(keyword)).strip()
    return bool(core) and (_contains(trigger, core) or _contains(core, trigger))


def _contains(text: str, part: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(part)}(?![a-z0-9])", text) is not None


@lru_cache(maxsize=1)
def load_catalog(path: Path = CATALOG_PATH) -> Catalog:
    return Catalog(json.loads(path.read_text(encoding="utf-8")))
