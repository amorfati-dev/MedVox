"""Wörterbuch der Praxis: Ersetzungen „falsch gehört → richtig“ und Fachbegriffe für den Whisper-Prompt.

Gepflegt auf der Seite `/woerterbuch` (Entscheidung F5: ein Eintrag gilt sofort für alle Diktate, mit
Probe vorher und Abschalten statt Löschen). Beides wird je Anfrage aus SQLite gelesen – kein Neustart,
kein `make install`:

- Ersetzung: 1–3 ganze Wörter, vor dem Normalisierer angewandt wie die eingebauten `lexicon.ALIASES`
  (`lexicon.correct(text, extra)`); dadurch ändern sich angezeigter Text und Ziffern.
- Fachbegriff: nur im Prompt an whisper (`whisper_prompt.compose`), keine unscharfe Korrektur – eine
  Abweichung um einen Buchstaben hat schon einmal „schwere“ zu „Schmerz“ gemacht (`lexicon.py`).

Schutzregeln beim Speichern und beim Wieder-Einschalten (`check_replacement`, `check_term`): keine Ziffern
und keine Zahlwörter (Zahnnummern und Codes bleiben unangetastet), kein Allerweltswort allein
(`lexicon.NEVER_CORRECT`), nichts, was eine eingebaute Ersetzung oder einen eingebauten Fachbegriff
überschreibt, und kein Fachbegriff mehr, wenn der Prompt voll ist (`whisper_prompt.budget`).
"""

from __future__ import annotations

import re
import sqlite3
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from medvox import db
from medvox.lexicon import ALIASES, CONTEXT_ALIASES, is_common, is_term
from medvox.normalize import number_value
from medvox.whisper_prompt import budget

KINDS = ("ersetzung", "begriff")
SOURCES = ("hand", "korrektur")  # von Hand eingetragen / aus Korrekturen übernommen
MAX_WORDS = 3
MAX_RIGHT = 60
MAX_TERM = 40

_WORD = re.compile(r"[^\W\d_]+")
# „richtig“ und Fachbegriffe: Wörter, getrennt von Leerzeichen oder Bindestrich (kein Komma: der Prompt zählt auf)
_PHRASE = re.compile(r"[^\W\d_]+(?:[ -][^\W\d_]+)*\.?")


class Rejected(ValueError):
    """Schutzregel verletzt; die Meldung steht so auf der Seite."""


@dataclass(frozen=True)
class Entry:
    id: int
    kind: str  # ersetzung | begriff
    wrong: str  # falsch gehört; leer bei Begriffen
    right: str
    active: bool
    source: str  # hand | korrektur
    created_at: float


@dataclass(frozen=True)
class Active:
    """Was in einer Anfrage gilt: Ersetzungen für `lexicon.correct`, Begriffe für den Prompt."""

    replacements: dict[tuple[str, ...], str]
    terms: list[str]


def _clean(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).split())


def _no_numbers(*texts: str) -> None:
    for text in texts:
        spoken = [w for w in _WORD.findall(text) if w.lower() != "ein"]  # „ein“ ist meist der Artikel
        if any(ch.isdigit() for ch in text) or any(number_value(w) for w in spoken):
            raise Rejected("Keine Zahlen und keine Zahlwörter: Zahnnummern und Codes bleiben immer unangetastet.")


def check_replacement(wrong: str, right: str, active: list[Entry], own_id: int | None = None) -> tuple[str, str]:
    """Bereinigtes (falsch, richtig) oder `Rejected` mit Begründung; `own_id` beim Wieder-Einschalten."""
    wrong, right = _clean(wrong), _clean(right)
    if not wrong or not right:
        raise Rejected("Bitte „falsch gehört“ und „richtig“ ausfüllen.")
    _no_numbers(wrong, right)
    words = wrong.split()
    if len(words) > MAX_WORDS:
        raise Rejected("„Falsch gehört“ hat höchstens drei Wörter.")
    if not all(_WORD.fullmatch(w) for w in words):
        raise Rejected("„Falsch gehört“ sind ganze Wörter, ohne Satzzeichen und Bindestrich – so wie Whisper sie schreibt.")
    if len(right) > MAX_RIGHT or not _PHRASE.fullmatch(right):
        raise Rejected(f"„Richtig“ sind Wörter ohne Satzzeichen, höchstens {MAX_RIGHT} Zeichen.")
    low = tuple(w.lower() for w in words)
    if all(is_common(w) for w in words):
        if len(words) == 1:
            raise Rejected(f"„{wrong}“ allein geht nicht, das Wort steht in fast jedem Diktat. "
                           "Bitte mindestens ein zweites Wort dazunehmen.")
        raise Rejected(f"„{wrong}“ sind lauter Allerweltswörter. Bitte ein kennzeichnendes Wort dazunehmen.")
    if len(words) == 1 and len(wrong) < 3:
        raise Rejected("Ein einzelnes Wort braucht mindestens drei Buchstaben.")
    if low in ALIASES or low in CONTEXT_ALIASES:
        raise Rejected(f"Für „{wrong}“ gibt es schon eine eingebaute Ersetzung.")
    kept = {w.lower() for w in _WORD.findall(right)}
    joined = len(words) > 1 and "".join(low) == re.sub(r"[ -]", "", right.lower())
    if not joined and (lost := [w for w in words if is_term(w) and w.lower() not in kept]):
        raise Rejected(f"„{lost[0]}“ ist ein eingebauter Fachbegriff und wird nicht ersetzt.")
    right_words = tuple(w.lower() for w in _WORD.findall(right))
    if any(right_words[k : k + len(low)] == low for k in range(len(right_words))):
        raise Rejected("„Richtig“ enthält das falsch Gehörte selbst – die Ersetzung griffe bei jeder Neuberechnung wieder.")
    for e in active:
        if e.kind == "ersetzung" and e.id != own_id and e.wrong.lower() == wrong.lower():
            raise Rejected(f"Für „{e.wrong}“ gibt es schon eine Ersetzung (→ „{e.right}“). Bitte die erst abschalten.")
    return wrong, right


def check_term(term: str, active: list[Entry], base: str, model: Path, own_id: int | None = None) -> str:
    """Bereinigter Fachbegriff oder `Rejected`; prüft auch, ob er noch in den Prompt passt."""
    term = _clean(term)
    _no_numbers(term)
    if not 2 <= len(term) <= MAX_TERM or not _PHRASE.fullmatch(term) or term.endswith("."):
        raise Rejected(f"Ein Fachbegriff sind Wörter ohne Komma und Satzzeichen, 2 bis {MAX_TERM} Zeichen.")
    terms = [e.right for e in active if e.kind == "begriff" and e.id != own_id]
    if term.lower() in (t.lower() for t in terms):
        raise Rejected(f"„{term}“ steht schon in Ihren Ergänzungen.")
    if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", base, re.I):
        raise Rejected(f"„{term}“ steht schon im Grundtext.")
    room = budget(base, [*terms, term], model)
    if room.base + room.terms > room.limit:
        raise Rejected("Der Prompt ist voll – whisper schnitte sonst den Anfang des Grundtexts ab. "
                       "Bitte zuerst einen anderen Begriff abschalten.")
    return term


def _entry(row: sqlite3.Row) -> Entry:
    return Entry(row["id"], row["kind"], row["wrong"], row["right"], bool(row["active"]), row["source"],
                 row["created_at"])


def _all(conn: sqlite3.Connection) -> list[Entry]:
    rows = conn.execute("SELECT * FROM lexicon_entries ORDER BY active DESC, created_at DESC, id DESC").fetchall()
    return [_entry(r) for r in rows]


def list_entries(db_path: Path) -> list[Entry]:
    """Alle Einträge, eingeschaltete zuerst, sonst die neuesten oben."""
    with db.connect(db_path) as conn:
        return _all(conn)


def active(db_path: Path) -> Active:
    """Die eingeschalteten Einträge für eine Anfrage (älteste Begriffe zuerst, damit der Prompt stabil bleibt)."""
    with db.connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM lexicon_entries WHERE active = 1 ORDER BY created_at, id").fetchall()
    entries = [_entry(r) for r in rows]
    return Active(
        replacements={tuple(e.wrong.lower().split()): e.right for e in entries if e.kind == "ersetzung"},
        terms=[e.right for e in entries if e.kind == "begriff"],
    )


def create(db_path: Path, kind: str, wrong: str, right: str, source: str, base: str, model: Path) -> Entry:
    """Legt einen eingeschalteten Eintrag an, nachdem die Schutzregeln bestanden sind."""
    with db.connect(db_path) as conn:
        current = [e for e in _all(conn) if e.active]
        if kind == "ersetzung":
            wrong, right = check_replacement(wrong, right, current)
        else:
            wrong, right = "", check_term(right, current, base, model)
        cur = conn.execute(
            "INSERT INTO lexicon_entries (kind, wrong, right, active, source, created_at) VALUES (?, ?, ?, 1, ?, ?)",
            (kind, wrong, right, source, time.time()),
        )
        return next(e for e in _all(conn) if e.id == cur.lastrowid)


def set_active(db_path: Path, entry_id: int, on: bool, base: str, model: Path) -> Entry | None:
    """Ab- oder wieder einschalten; beim Einschalten gelten die Schutzregeln erneut. None, wenn es ihn nicht gibt."""
    with db.connect(db_path) as conn:
        entries = _all(conn)
        entry = next((e for e in entries if e.id == entry_id), None)
        if entry is None:
            return None
        if on and not entry.active:
            current = [e for e in entries if e.active]
            if entry.kind == "ersetzung":
                check_replacement(entry.wrong, entry.right, current, own_id=entry.id)
            else:
                check_term(entry.right, current, base, model, own_id=entry.id)
        conn.execute("UPDATE lexicon_entries SET active = ? WHERE id = ?", (int(on), entry_id))
        return next(e for e in _all(conn) if e.id == entry_id)
