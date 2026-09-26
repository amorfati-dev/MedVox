"""Schwere Osteotomie („schwere Ost“): Kasse GOÄ Ä2650 (2026-09-25), Privat GOZ 3045 (2026-09-26, Angaben des Behandlers).

BEMA hat über Ost2 (48) keine Ziffer; beim Kassenpatienten berechnet der Behandler Ä2650 als Analogposition,
beim Privatpatienten GOZ 3045 mit Zuschlag 0510 (767 Punkte) wie bei 3040. Am selben Zahn nie zusätzlich Ost1/Ost2,
und für die zweite Anästhesie (KZVB) zählt Ä2650 als „Ost1 oder höher“.
"""

from __future__ import annotations

import pytest

from medvox.extract_catalog import load_catalog
from medvox.extract_surgery import SEVERE_OSTEOTOMY, WISDOM_NOTE
from tests.test_extract_surgery import main, one, per_tooth, run


@pytest.mark.parametrize("word", ["schwere Ost", "schwere OS", "Schwere Osteotomie", "schwere Ost 2", "schwere Ost2",
                                  "schwere Ost zwei"])
def test_severe_osteotomy_spellings(word):
    assert [(s.system, s.code, s.teeth) for s in main(run(f"38 {word}."))] == [("GOÄ", "Ä2650", (38,))]
    private = run(f"38 {word}.", "privat")
    assert [(s.system, s.code, s.teeth) for s in main(private)] == [("GOZ", "3045", (38,)), ("GOZ", "0510", (38,))]
    assert private.notes == []


def test_severe_osteotomy_at_38_statutory_allows_a_second_block():
    result = run("38 schwere Ost, Leitungsanästhesie 2x lange Dauer.")
    assert per_tooth(result) == {38: {"Ä2650": 1, "41a": 2}}
    anesthesia = one(result, "41a", 38)
    assert anesthesia.decide == () and anesthesia.reason.endswith("zweite wegen „lange Dauer“")
    severe = one(result, "Ä2650", 38)
    assert severe.kind == "bema" and severe.reason.startswith("Analogposition: schwere Osteotomie als GOÄ Ä2650")
    assert result.notes == []


def test_severe_osteotomy_counts_the_repeated_short_form():
    assert per_tooth(run("38 schwere Ost, L1, L1, lange Dauer.")) == {38: {"Ä2650": 1, "41a": 2}}


def test_second_block_without_osteotomy_stays_capped():
    assert per_tooth(run("38 Extraktion, Leitungsanästhesie 2x lange Dauer.")) == {38: {"44": 1, "41a": 1}}


def test_severe_osteotomy_replaces_ost2_at_the_same_tooth():
    result = run("38 Ost2, schwere Ost.")
    assert [(s.code, s.teeth) for s in main(result)] == [("Ä2650", (38,))]
    assert "↔" not in one(result, "Ä2650", 38).reason  # Ost2 ist kein Paar von Ä2650
    private = run("38 Ost2, schwere Ost.", "privat")
    assert per_tooth(private) == {38: {"3045": 1, "0510": 1}} and private.notes == []
    assert "↔" not in one(private, "3045", 38).reason


def test_ost2_at_another_tooth_stays():
    assert per_tooth(run("38 Ost2, 48 schwere Ost.")) == {38: {"48": 1}, 48: {"Ä2650": 1}}


def test_plain_ost2_is_unchanged():
    assert [(s.code, s.teeth) for s in main(run("38 Ost2."))] == [("48", (38,))]


def test_private_severe_osteotomy_at_38_is_goz3045_with_surcharge():
    result = run("38 schwere Ost, Leitungsanästhesie.", "privat")
    assert per_tooth(result) == {38: {"3045": 1, "0100": 1, "0510": 1}}
    assert {s.code for s in result.suggestions}.isdisjoint({"Ä2650", "3030", "3040", "0500", "0520", "0530"})
    surcharge = one(result, "0510", 38)
    assert "GOZ 3045" in surcharge.reason and "767 Punkte" in surcharge.reason
    assert one(result, "3045", 38).kind == "goz" and result.notes == []


def test_private_second_block_beside_goz3045():
    assert per_tooth(run("38 schwere Ost, Leitungsanästhesie 2x lange Dauer.", "privat")) == {
        38: {"3045": 1, "0100": 2, "0510": 1}}


def test_statutory_severe_osteotomy_stays_ae2650_without_surcharge():
    result = run("38 schwere Ost, Leitungsanästhesie.")
    assert per_tooth(result) == {38: {"Ä2650": 1, "41a": 1}}
    assert not {s.code for s in result.suggestions} & {"3045", "0500", "0510", "0520", "0530"}


@pytest.mark.parametrize(("dictation", "patient", "code"), [("38 GOÄ Ä2650.", "privat", "3045"),
                                                              ("38 GOZ 3045.", "kasse", "Ä2650")])
def test_dictated_severe_code_follows_the_patient_type(dictation, patient, code):
    assert [(s.code, s.teeth) for s in main(run(dictation, patient)) if s.code in {"Ä2650", "3045"}] == [(code, (38,))]


@pytest.mark.parametrize("dictation", ["Nächste Sitzung 38 schwere Ost.", "38 Extraktion. Geplant: 48 schwere Ost."])
def test_planned_private_severe_osteotomy_is_goz3045(dictation):
    result = run(dictation, "privat")
    assert [s.code for s in result.suggestions if s.planned] == ["3045"] and result.notes == []
    assert all(s.code != "0510" for s in result.suggestions)  # Geplantes bestimmt keinen Zuschlag
    assert any(s.code == "Ä2650" and s.planned for s in run(dictation).suggestions)


def test_planned_severe_osteotomy_replaces_planned_ost2_at_the_same_tooth():
    planned = [(s.code, s.teeth) for s in run("38 Extraktion. Geplant: 48 Ost2 schwere Ost.").suggestions if s.planned]
    assert planned == [("Ä2650", (48,))]
    private = run("38 Extraktion. Geplant: 48 Ost2 schwere Ost.", "privat")
    assert [(s.code, s.teeth) for s in private.suggestions if s.planned] == [("3045", (48,))]


def test_severe_osteotomy_is_confirmed_in_the_catalog():
    statutory, private = (load_catalog().get(*SEVERE_OSTEOTOMY[p]) for p in ("kasse", "privat"))
    assert statutory is not None and statutory.points == 740 and statutory.equivalents == ()
    assert private is not None and private.points == 767 and private.equivalents == () and private.analog is None


# --- Ä2650 gilt als Osteotomie: Ä1/Zst, Pla0, Nbl2 wie neben Ost1/Ost2 ----------------------------------


def test_severe_osteotomy_at_a_wisdom_tooth_offers_a1_and_zst():
    options = [s for s in run("38 schwere Ost.").suggestions if s.addon]
    assert [s.code for s in options] == ["Ä1", "107"] and all(s.teeth == (38,) and s.reason == WISDOM_NOTE for s in options)
    assert not any(s.addon for s in run("36 schwere Ost.").suggestions)
    private = [(s.code, s.teeth) for s in run("38 schwere Ost.", "privat").suggestions if s.addon]
    assert private == [("Ä1", (38,))]


def test_pla0_beside_severe_osteotomy_needs_no_pla1_hint():
    assert one(run("28 schwere Ost, plastische Deckung."), "51b", 28).decide == ()


def test_bleeding_beside_severe_osteotomy_is_an_nbl2_option_not_papilla_bleeding():
    result = run("48 schwere Ost, starke Blutung.")
    option = next(s for s in result.suggestions if s.code == "37")
    assert option.addon and not any("nicht vorgeschlagen" in n for n in result.notes)
    private = run("48 schwere Ost, starke Blutung.", "privat")
    assert next(s for s in private.suggestions if s.code == "3060").addon
    assert [(s.code, s.teeth) for s in main(run("48 schwere Ost, starke Blutung, Umschlingungsnaht.")) if s.code == "37"] == [
        ("37", (48,))]
