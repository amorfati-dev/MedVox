"""Schwere Osteotomie („schwere Ost“) = GOÄ Ä2650 (Angabe des Behandlers 2026-09-25).

BEMA hat über Ost2 (48) keine Ziffer; beim Kassenpatienten berechnet der Behandler Ä2650 als Analogposition,
beim Privatpatienten ebenfalls Ä2650 (GOZ 3045 ist nicht hinterlegt). Am selben Zahn nie zusätzlich Ost1/Ost2,
und für die zweite Anästhesie (KZVB) zählt Ä2650 als „Ost1 oder höher“.
"""

from __future__ import annotations

import pytest

from medvox.extract_catalog import load_catalog
from medvox.extract_surgery import SEVERE_OSTEOTOMY
from tests.test_extract_surgery import main, one, per_tooth, run


@pytest.mark.parametrize("word", ["schwere Ost", "schwere OS", "Schwere Osteotomie", "schwere Ost 2", "schwere Ost2",
                                  "schwere Ost zwei"])
def test_severe_osteotomy_spellings(word):
    for patient in ("kasse", "privat"):
        assert [(s.system, s.code, s.teeth) for s in main(run(f"38 {word}.", patient))] == [("GOÄ", "Ä2650", (38,))]


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
    for patient in ("kasse", "privat"):
        result = run("38 Ost2, schwere Ost.", patient)
        assert [(s.code, s.teeth) for s in main(result)] == [("Ä2650", (38,))]
        assert "↔" not in one(result, "Ä2650", 38).reason  # Ost2 ist kein Paar von Ä2650


def test_ost2_at_another_tooth_stays():
    assert per_tooth(run("38 Ost2, 48 schwere Ost.")) == {38: {"48": 1}, 48: {"Ä2650": 1}}


def test_plain_ost2_is_unchanged():
    assert [(s.code, s.teeth) for s in main(run("38 Ost2."))] == [("48", (38,))]


def test_private_severe_osteotomy_is_goae_without_goz_surcharge():
    result = run("38 schwere Ost, Leitungsanästhesie.", "privat")
    assert per_tooth(result) == {38: {"Ä2650": 1, "0100": 1}}
    assert {s.code for s in result.suggestions}.isdisjoint({"3045", "3040", "0510"})


def test_severe_osteotomy_is_confirmed_in_the_catalog():
    entry = load_catalog().get(*SEVERE_OSTEOTOMY)
    assert entry is not None and entry.points == 740 and entry.equivalents == ()
