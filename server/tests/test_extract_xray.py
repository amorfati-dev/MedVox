"""Bissflügelaufnahmen im Pilot: „Bisflügel“ (ein s) erkennen, beim Privatpatienten GOÄ Ä5000 je Projektion.

Echtes Transkript eines Privatpatienten: „… Bisflügelaufnahme rechts und links durchgeführt ohne Befund …“
ergab keine Röntgenziffer – „Bisflügelaufnahme“ passte weder auf den Lexikon-Begriff noch auf das Keyword.
"""

from __future__ import annotations

import pytest

from medvox.extract import Extraction, analyze
from medvox.lexicon import correct
from medvox.normalize import normalize

PILOT = "Bisflügelaufnahme rechts und links durchgeführt ohne Befund."


def run(dictation: str, patient: str) -> Extraction:
    corrected, _ = correct(dictation)
    n = normalize(corrected)
    return analyze(n.text, n.teeth, patient)


def positions(result: Extraction) -> list[tuple]:
    return [(s.code, s.count, s.alternative, s.decide) for s in result.suggestions]


def test_pilot_private_patient_gets_two_projections():
    assert positions(run(PILOT, "privat")) == [("Ä5000", 2, False, ())]


def test_pilot_statutory_patient_keeps_the_bema_mapping():
    assert positions(run(PILOT, "kasse")) == [("Ä925a", 1, False, ())]


@pytest.mark.parametrize("said", ["Bissflügel", "Bissflügelaufnahme", "Bisflügel", "Bisflügelaufnahme"])
def test_plain_bitewing_is_one_projection_with_check_note(said):
    [(code, count, alternative, decide)] = positions(run(f"{said} angefertigt.", "privat"))
    assert (code, count, alternative) == ("Ä5000", 1, False)
    assert any("je Projektion" in f and "prüfen" in f for f in decide)
    assert positions(run(f"{said} angefertigt.", "kasse")) == [("Ä925a", 1, False, ())]


@pytest.mark.parametrize("said", ["Bissflügel beidseits", "Bissflügelaufnahmen links und rechts",
                                  "Bissflügel beidseitig"])
def test_both_sides_are_two_projections(said):
    assert positions(run(f"{said}.", "privat")) == [("Ä5000", 2, False, ())]
    assert positions(run(f"{said}.", "kasse")) == [("Ä925a", 1, False, ())]


@pytest.mark.parametrize("said", ["Bissflügel rechts, Zahn 36 links", "Rechts und links Bissflügel",
                                  "Zahnfilm rechts und links"])
def test_sides_elsewhere_do_not_count(said):
    x_ray = [p for p in positions(run(f"{said}.", "privat")) if p[0] == "Ä5000"]
    assert [(code, count) for code, count, *_ in x_ray] == [("Ä5000", 1)]
    assert any("je Projektion" in f for f in x_ray[0][3])
