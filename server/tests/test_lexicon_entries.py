"""Wörterbuch der Praxis: Schutzregeln beim Speichern und Wieder-Einschalten, Ersetzungen in `lexicon.correct`."""

from __future__ import annotations

from pathlib import Path

import pytest

from medvox import db, lexicon_entries
from medvox.lexicon import BUILTIN_SHOWN, correct
from medvox.lexicon_entries import Entry, Rejected, check_replacement, check_term

BASE = "Zahnarzt-Diktat. Zahn drei sechs mesial okklusal distal, Karies profunda, Kofferdam."
NO_MODEL = Path("/fehlt/ggml.bin")


def _entry(id_: int, kind: str, wrong: str, right: str, active: bool = True) -> Entry:
    return Entry(id_, kind, wrong, right, active, "hand", 0.0)


@pytest.mark.parametrize(
    "wrong, right, reason",
    [
        ("Zahn", "Zahnstein", "allein geht nicht"),
        ("in der", "Inlay", "Allerweltswörter"),
        ("drei sechs", "Zahn", "Zahlen"),
        ("Zahn 36", "Zahn", "Zahlen"),
        ("Keramik", "Keramik 2", "Zahlen"),
        ("sechsunddreißig", "Molar", "Zahlen"),
        ("Karies", "Kariös", "eingebauter Fachbegriff"),
        ("Füllungen", "Inlays", "eingebauter Fachbegriff"),
        ("Psycho", "PSI", "eingebaute Ersetzung"),
        ("bis Registrat", "Bissregistrat", "eingebaute Ersetzung"),
        ("PTE", "VitE", "eingebaute Ersetzung"),
        ("Keramik in Lay", "Keramik in Lay Inlay", "falsch Gehörte selbst"),
        ("eins zwei drei vier", "Test", "Zahlen"),
        ("Poly Ether Masse Neu", "Polyether", "höchstens drei Wörter"),
        ("Poly-Ether", "Polyether", "ganze Wörter"),
        ("Ab", "Abformung", "drei Buchstaben"),
        ("", "Polyether", "ausfüllen"),
        ("Poly Ether", "Poly, Ether", "ohne Satzzeichen"),
        ("Extraktion", "Extraktionswunde", "eingebauter Fachbegriff"),
        ("Füllung", "Kompositfüllung", "eingebauter Fachbegriff"),
    ],
)
def test_guard_rules_reject_with_a_reason(wrong: str, right: str, reason: str) -> None:
    with pytest.raises(Rejected, match=reason):
        check_replacement(wrong, right, [])


def test_a_built_in_term_may_stay_inside_a_longer_replacement() -> None:
    assert check_replacement("Karies profunder", "Karies profunda", []) == ("Karies profunder", "Karies profunda")


@pytest.mark.parametrize(
    "wrong, right",
    [
        ("Zahnstein entfernung", "Zahnsteinentfernung"),
        ("Komposit füllung", "Kompositfüllung"),
        ("Wurzel kanal behandlung", "Wurzelkanalbehandlung"),
    ],
)
def test_a_split_compound_may_be_joined_again(wrong: str, right: str) -> None:
    assert check_replacement(wrong, right, []) == (wrong, right)


def test_replacement_is_cleaned_and_accepted() -> None:
    assert check_replacement("  Zahn   steinentfernung ", "Zahnsteinentfernung", []) == (
        "Zahn steinentfernung", "Zahnsteinentfernung")
    assert check_replacement("Keramik in Lay", "Keramikinlay", []) == ("Keramik in Lay", "Keramikinlay")
    assert check_replacement("ein Lay", "Inlay", []) == ("ein Lay", "Inlay")  # „ein“ ist der Artikel


def test_only_one_active_replacement_per_heard_phrase() -> None:
    current = [_entry(1, "ersetzung", "Poly Ether", "Polyether")]
    with pytest.raises(Rejected, match="schon eine Ersetzung"):
        check_replacement("poly ether", "Polyäther", current)
    assert check_replacement("poly ether", "Polyäther", current, own_id=1)  # sich selbst wieder einschalten


@pytest.mark.parametrize(
    "term, reason",
    [
        ("Kofferdam", "Grundtext"),
        ("Bulk, Fill", "ohne Komma"),
        ("Stift 2", "Zahlen"),
        ("X", "2 bis"),
        ("Bulkfill", "Ergänzungen"),
    ],
)
def test_term_guard_rules(term: str, reason: str) -> None:
    with pytest.raises(Rejected, match=reason):
        check_term(term, [_entry(1, "begriff", "", "Bulkfill")], BASE, NO_MODEL)


def test_term_is_refused_when_the_prompt_is_full() -> None:
    long_base = "Zahnarzt-Diktat. " + ", ".join(["Wurzelkanalaufbereitung"] * 40)
    with pytest.raises(Rejected, match="Prompt ist voll"):
        check_term("Keramikinlay", [], long_base, NO_MODEL)


def test_new_replacement_takes_effect_in_the_next_request(tmp_path: Path) -> None:
    path = tmp_path / "medvox.db"
    db.init_db(path)
    assert lexicon_entries.active(path).replacements == {}
    entry = lexicon_entries.create(path, "ersetzung", "Zahn steinentfernung", "Zahnsteinentfernung", "hand", BASE,
                                   NO_MODEL)
    term = lexicon_entries.create(path, "begriff", "", "Keramikinlay", "korrektur", BASE, NO_MODEL)
    words = lexicon_entries.active(path)
    assert words.replacements == {("zahn", "steinentfernung"): "Zahnsteinentfernung"}
    assert words.terms == ["Keramikinlay"]
    lexicon_entries.set_active(path, entry.id, False, BASE, NO_MODEL)
    assert lexicon_entries.active(path).replacements == {}
    listed = lexicon_entries.list_entries(path)
    assert [(e.id, e.active) for e in listed] == [(term.id, True), (entry.id, False)]  # abgeschaltet, nie gelöscht
    assert lexicon_entries.set_active(path, 999, True, BASE, NO_MODEL) is None


def test_switching_back_on_checks_the_guard_rules_again(tmp_path: Path) -> None:
    path = tmp_path / "medvox.db"
    db.init_db(path)
    old = lexicon_entries.create(path, "ersetzung", "Poly Ether", "Polyether", "hand", BASE, NO_MODEL)
    lexicon_entries.set_active(path, old.id, False, BASE, NO_MODEL)
    lexicon_entries.create(path, "ersetzung", "Poly Ether", "Polyäther", "hand", BASE, NO_MODEL)
    with pytest.raises(Rejected, match="schon eine Ersetzung"):
        lexicon_entries.set_active(path, old.id, True, BASE, NO_MODEL)


# --- Reihenfolge der Ersetzungen in lexicon.correct ------------------------------------------------------


def test_replacements_run_before_the_normaliser_on_whole_words() -> None:
    extra = {("zahn", "steinentfernung"): "Zahnsteinentfernung"}
    text, (c,) = correct("Zahn steinentfernung, Politur.", extra)
    assert text == "Zahnsteinentfernung, Politur."
    assert (c.original, c.corrected) == ("Zahn steinentfernung", "Zahnsteinentfernung")
    assert correct("Zahnsteinentfernung, Politur.", extra)[1] == []  # schon richtig: nichts zu tun
    assert correct("Zahn, steinentfernung", extra)[0] == "Zahn, steinentfernung"  # nur über Leerraum


def test_longer_window_wins_and_built_in_wins_on_equal_length() -> None:
    extra = {("keramik", "in", "lay"): "Keramikinlay", ("in", "lay"): "Inlay", ("bis", "registrat"): "falsch"}
    assert correct("Keramik in Lay und in Lay", extra)[0] == "Keramikinlay und Inlay"
    assert correct("bis Registrat", extra)[0] == "Bissregistrat"


def test_three_word_window_needs_whitespace_between_all_words() -> None:
    extra = {("keramik", "in", "lay"): "Keramikinlay"}
    assert correct("Keramik in, Lay", extra)[0] == "Keramik in, Lay"


def test_replacement_is_not_fuzzy_corrected_again() -> None:
    text, corrections = correct("Artikein und Bulk Fil", {("bulk", "fil"): "Bulkfil"})
    assert text == "Artikain und Bulkfil"
    assert [c.corrected for c in corrections] == ["Artikain", "Bulkfil"]


def test_without_extra_nothing_changes() -> None:
    raw = "Zahn steinentfernung, Keramik in Lay"
    assert correct(raw) == correct(raw, {}) == (raw, [])


def test_thirteen_built_in_replacements_are_shown() -> None:
    assert len(BUILTIN_SHOWN) == 13
    assert (("psycho",), "PSI") in BUILTIN_SHOWN
