"""Abszesseröffnung (Inzision): die Tiefe wählt die Ziffer, ohne Tiefe wird nachgefragt.

Oberflächlich = BEMA Ä161 (Inz1) bzw. GOÄ Ä2428, Evident „inz1“; tiefliegend = GOÄ Ä2430, Evident
„inz2“ – im BEMA (Stand 1. Januar 2026) gibt es dafür keine Ziffer. Falsch wäre vor allem, still die
falsche der beiden Tiefen zu wählen.
"""

from __future__ import annotations

import pytest

from medvox.extract import Extraction, Suggestion, analyze, billable_codes
from medvox.lexicon import correct
from medvox.normalize import normalize

DEPTH_OPEN_KASSE = ("Tiefe nicht diktiert – Ä161 (Inz1) nur beim oberflächlichen Abszess; "
                    "für den tiefliegenden hat der BEMA keine Ziffer")
DEPTH_OPEN_PRIVAT = "Tiefe nicht diktiert – oberflächlich GOÄ Ä2428 (inz1) oder tiefliegend GOÄ Ä2430 (inz2) wählen"


def run(dictation: str, patient: str = "kasse") -> Extraction:
    corrected, _ = correct(dictation)
    n = normalize(corrected)
    return analyze(n.text, n.teeth, patient)


def performed(result: Extraction) -> list[Suggestion]:
    return [s for s in result.suggestions if not s.planned and not s.alternative]


@pytest.mark.parametrize("patient, system, code", [("kasse", "BEMA", "Ä161"), ("privat", "GOÄ", "Ä2428")])
def test_superficial_incision_is_inz1(patient, system, code):
    [s] = performed(run("Regio drei sechs oberflächlichen Abszess eröffnet.", patient))
    assert (s.system, s.code, s.evident, s.teeth, s.decide) == (system, code, "inz1", (36,), ())


def test_deep_incision_is_inz2_for_private_patients():
    [s] = performed(run("Zahn drei sechs tiefliegenden Abszess eröffnet, Drainage eingelegt.", "privat"))
    assert (s.system, s.code, s.evident, s.points, s.teeth, s.decide) == ("GOÄ", "Ä2430", "inz2", 303, (36,), ())


def test_deep_incision_has_no_bema_code():
    result = run("Tiefliegende Inzision regio vier sieben.")
    assert result.suggestions == []
    assert any(n.startswith("GOÄ Ä2430") and "kein BEMA-Paar" in n for n in result.notes)


@pytest.mark.parametrize("words", [
    "Inzision", "Abszess inzidiert", "Abszess eröffnet", "Abszessinzision", "Abszesseröffnung",
    "Entlastungsschnitt", "Abszessspaltung", "Abszess gespalten",
])
@pytest.mark.parametrize("patient, code, flag", [("kasse", "Ä161", DEPTH_OPEN_KASSE), ("privat", "Ä2428", DEPTH_OPEN_PRIVAT)])
def test_incision_without_depth_asks(words, patient, code, flag):
    [s] = performed(run(f"Regio drei sechs {words}.", patient))
    assert (s.code, s.teeth, s.decide) == (code, (36,), (flag,))


@pytest.mark.parametrize("dictation, patient, code", [
    ("Inz eins an drei sechs.", "kasse", "Ä161"),
    ("Inz eins an drei sechs.", "privat", "Ä2428"),
    ("Inz zwei regio drei sechs.", "privat", "Ä2430"),
    ("BEMA Ä161 regio drei sechs.", "kasse", "Ä161"),
    ("Ä zwei vier drei null regio drei sechs.", "privat", "Ä2430"),
])
def test_short_form_and_code_name_the_depth(dictation, patient, code):
    [s] = performed(run(dictation, patient))
    assert (s.code, s.decide) == (code, ())


def test_goae_number_without_umlaut_is_not_the_goz_number():
    # „GOÄ 2430“ ist die tiefe Inzision, nicht GOZ 2430 (medikamentöse Einlage)
    [s] = performed(run("GOÄ Ziffer 2430 an drei sechs.", "privat"))
    assert (s.system, s.code) == ("GOÄ", "Ä2430")
    assert billable_codes(run("GOÄ 5004.", "privat").suggestions) == ["Ä5004"]


@pytest.mark.parametrize("patient", ["kasse", "privat"])
def test_depth_word_settles_the_other_words_of_the_same_incision(patient):
    [s] = performed(run("Regio drei sechs oberflächliche Inzision, Abszess eröffnet.", patient))
    assert (s.code, s.count, s.decide) == ({"kasse": "Ä161", "privat": "Ä2428"}[patient], 1, ())


def test_deep_word_takes_the_open_word_along():
    [s] = performed(run("Subperiostaler Abszess inzidiert regio drei sechs.", "privat"))
    assert (s.code, s.count, s.teeth, s.decide) == ("Ä2430", 1, (36,), ())
    kasse = run("Subperiostaler Abszess inzidiert regio drei sechs.")
    assert kasse.suggestions == [] and any(n.startswith("GOÄ Ä2430") for n in kasse.notes)


def test_open_word_at_another_tooth_stays_its_own_incision():
    result = run("Inzision an drei sechs, tiefliegender Abszess an vier sieben.", "privat")
    assert [(s.code, s.teeth, s.decide) for s in performed(result)] == [
        ("Ä2428", (36,), (DEPTH_OPEN_PRIVAT,)), ("Ä2430", (47,), ())]


def test_goae_incision_gets_no_goz_surcharge():
    # 0500–0530 gelten nur für die in GOZ Abschnitt L genannten GOZ-Nummern; Ä2430 (303 Punkte) ist keine
    assert billable_codes(run("Tiefliegenden Abszess drei sechs eröffnet.", "privat").suggestions) == ["Ä2430"]
    osteo = run("Osteotomie drei acht, tiefliegenden Abszess eröffnet.", "privat")
    assert billable_codes(osteo.suggestions) == ["3030", "Ä2430", "0500"]
    assert "GOZ 3030" in next(s.reason for s in osteo.suggestions if s.code == "0500")


def test_negated_incision_is_not_suggested():
    assert run("Keine Inzision nötig.").suggestions == []
