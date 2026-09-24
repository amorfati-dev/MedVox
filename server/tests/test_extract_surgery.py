"""Weisheitszahn-OP (Rückmeldung des Behandlers 2026-09-24): Anästhesie je Zahn, Ost1/Ost2-Schreibweisen,
Nbl2 (BEMA 37) und Pla0 (BEMA 51b), Ä1/Zst als Option „ggf. dazu“.

Fixture ist das echte Whisper-Transkript des Pilotdiktats (Kassenpatient); der Behandler erwartet an 18 und
28 je I*2 + Ost2, an 38 und 48 je L1*2 + Ost2, dazu das OPG.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from medvox.extract import Extraction, Suggestion, analyze, billable_codes
from medvox.extract_anesthesia import ANESTHESIA, SECOND_UNSAID
from medvox.extract_catalog import load_catalog
from medvox.extract_surgery import NBL2, OSTEOTOMY, PLA0, PLA0_ALONE, WISDOM_NOTE, WISDOM_OPTIONS
from medvox.lexicon import correct
from medvox.normalize import normalize
from medvox.routes_transcribe import build_response
from tests.test_extract_anesthesia import PAUSED

FIXTURE = Path(__file__).resolve().parents[2] / "app" / "test" / "fixtures" / "weisheitszahn-op.json"
WISDOM_OP = (
    "Der Patient kommt für 4 Achter, hat keine Fragen mehr. Wir spritzen ein Infiltrationsanästhesie 18 2x mit "
    "lange Dauer bei der zweiten. 28 Infiltrationsanästhesie 2x, OS2, 38 OS2, Leitungsanästhesie 2x lange Dauer, "
    "48 Leitungsanästhesie 2x lange Dauer, 18 OS2, 48 OS2, OPG zur Kontrolle, ob noch kurz drin drin sind."
)


def run(dictation: str, patient: str = "kasse") -> Extraction:
    corrected, _ = correct(dictation)
    n = normalize(corrected)
    return analyze(n.text, n.teeth, patient)


def main(result: Extraction) -> list[Suggestion]:
    return [s for s in result.suggestions if not s.planned and not s.alternative]


def per_tooth(result: Extraction) -> dict[int, dict[str, int]]:
    teeth: dict[int, Counter] = {}
    for s in main(result):
        teeth.setdefault(s.teeth[0], Counter())[s.code] += s.count
    return {fdi: dict(codes) for fdi, codes in teeth.items()}


def one(result: Extraction, code: str, fdi: int) -> Suggestion:
    (found,) = [s for s in main(result) if s.code == code and s.teeth == (fdi,)]
    return found


# --- Pilotdiktat --------------------------------------------------------------------------------


def test_wisdom_tooth_dictation_statutory():
    result = run(WISDOM_OP)
    assert per_tooth(result) == {
        18: {"40": 2, "48": 1}, 28: {"40": 2, "48": 1},
        38: {"41a": 2, "48": 1}, 48: {"41a": 2, "48": 1, "Ä935d": 1},
    }
    assert billable_codes(result.suggestions) == ["4x 40", "4x 48", "4x 41a", "Ä935d"]
    assert {s.code: s.evident for s in main(result)} == {"40": "i", "48": "ost2", "41a": "l1", "Ä935d": "opg"}
    assert result.notes == []


def test_long_duration_goes_into_the_reason_never_into_the_count():
    result = run(WISDOM_OP)
    for code, fdi in (("40", 18), ("41a", 38), ("41a", 48)):
        s = one(result, code, fdi)
        assert s.reason.endswith("2× diktiert, zweite wegen „lange Dauer“") and s.decide == ()
    # an 28 ist „lange Dauer“ nicht diktiert: die zweite bleibt gezählt, aber mit Prüfhinweis
    assert one(result, "40", 28).decide == (SECOND_UNSAID.format(n=2),)


def test_wisdom_tooth_dictation_offers_a1_and_zst_only_as_options():
    result = run(WISDOM_OP)
    options = [s for s in result.suggestions if s.alternative]
    assert [(s.code, s.teeth, s.addon, s.kind, s.reason) for s in options] == [
        ("Ä1", (28,), True, "bema", WISDOM_NOTE), ("107", (28,), True, "bema", WISDOM_NOTE)]
    assert not any(s.addon for s in main(result))


def test_wisdom_tooth_dictation_private():
    result = run(WISDOM_OP, "privat")
    assert per_tooth(result) == {
        18: {"0090": 2, "3040": 1}, 28: {"0090": 2, "3040": 1, "0510": 1},
        38: {"0100": 2, "3040": 1}, 48: {"0100": 2, "3040": 1, "Ä5004": 1},
    }
    assert [(s.system, s.code) for s in result.suggestions if s.addon] == [("GOÄ", "Ä1")]


# --- Ost1/Ost2 wie Whisper sie schreibt --------------------------------------------------------


@pytest.mark.parametrize("word", ["Ost2", "Ost 2", "OS2", "OS 2", "Os 2", "Ost zwei"])
def test_ost2_spellings(word):
    assert [(s.code, s.teeth, s.evident) for s in main(run(f"38 {word}."))] == [("48", (38,), "ost2")]
    assert [(s.code, s.teeth) for s in main(run(f"38 {word}.", "privat"))] == [("3040", (38,)), ("0510", (38,))]


@pytest.mark.parametrize("word", ["Ost1", "Ost 1", "OS1", "Os 1", "Ost eins"])
def test_ost1_spellings(word):
    assert [(s.code, s.teeth, s.evident) for s in main(run(f"46 {word}."))] == [("47a", (46,), "ost1")]


def test_repeated_tooth_does_not_double_count_the_osteotomy():
    result = run("28 Infiltrationsanästhesie, OS2, 18 OS2, 28 OS2.")
    assert per_tooth(result) == {28: {"40": 1, "48": 1}, 18: {"48": 1}}


# --- Nbl2, Pla0 --------------------------------------------------------------------------------


@pytest.mark.parametrize("words", ["Nbl2", "Nbl zwei", "starke Blutung, Umschlingungsnaht", "starke Blutung, Naht",
                                   "starke Blutung, Bipo", "Nachblutung stark, Parasorb Fleece",
                                   "starke Blutung, Umstechung"])
def test_nbl2_only_when_said_or_bleeding_with_a_measure(words):
    result = run(f"48 Ost2, {words}.")
    assert [(s.code, s.teeth, s.evident) for s in main(result) if s.code == "37"] == [("37", (48,), "nbl2")]
    assert [s.code for s in main(run(f"48 Ost2, {words}.", "privat")) if s.code == "3060"] == ["3060"]


@pytest.mark.parametrize("dictation", ["Extraktion 46. Parasorb eingelegt.", "Extraktion 46. Bipolar koaguliert.",
                                       "48 Ost2, Umschlingungsnaht.", "48 Ost2, starke Blutung.",
                                       "Parasorb eingelegt."])
def test_lone_measure_or_bleeding_is_only_an_option(dictation):
    for patient, code in (("kasse", "37"), ("privat", "3060")):
        result = run(dictation, patient)
        assert code not in [s.code for s in main(result)]
        option = next(s for s in result.suggestions if s.code == code)
        assert option.alternative and option.addon and "antippen, wenn erbracht" in option.decide[0]
        assert code not in billable_codes(result.suggestions)


def test_strong_bleeding_without_surgery_is_papilla_bleeding_not_nbl2():
    result = run("Zahn 46 dreiflächige Füllung, BMF, starke Blutung, Blutungsstillung.")
    assert "37" not in [s.code for s in result.suggestions]
    assert any("Nbl2 (BEMA 37) nicht vorgeschlagen" in n for n in result.notes)
    assert "37" in [s.code for s in main(run("Zahn 46 starke Blutung, Umschlingungsnaht."))]


@pytest.mark.parametrize("word", ["plastische Deckung", "Kieferhöhle verschlossen", "Pla0", "Pla null",
                                  "speicheldichter Verschluss der Kieferhöhle"])
def test_pla0_words(word):
    result = run(f"28 Ost2, {word}.")
    assert [(s.code, s.teeth, s.evident, s.decide) for s in main(result) if s.code == "51b"] == [
        ("51b", (28,), "pla0", ())]
    privat = [s for s in main(run(f"28 Ost2, {word}.", "privat")) if s.code == "3090"]
    assert len(privat) == 1 and "GOZ 3100" in privat[0].decide[0]


def test_sealing_the_sinus_is_not_a_provisional_filling():
    assert [s.code for s in main(run("28 Ost2, speicheldichter Verschluss der Kieferhöhle."))] == ["48", "51b"]


def test_pla0_without_osteotomy_asks_for_pla1():
    result = run("Zahn 26 Extraktion, Kieferhöhle verschlossen.")
    assert one(result, "51b", 26).decide == (PLA0_ALONE,)


# --- Optionen Ä1/Zst ----------------------------------------------------------------------------


def test_options_only_for_performed_wisdom_tooth_osteotomy():
    assert not any(s.addon for s in run("Osteotomie 36.").suggestions)
    assert not any(s.addon for s in run("38 retiniert, Osteotomie 38 planen.").suggestions)
    assert not any(s.addon for s in run("Extraktion 48.").suggestions)


def test_dictated_options_are_not_offered_again():
    assert [s.code for s in run("Beratung, 38 Ost2.").suggestions if s.addon] == ["107"]
    assert [s.code for s in run("Eingehende Untersuchung, 38 Ost2.").suggestions if s.addon] == ["107"]  # Ä1 nicht neben 01


def test_new_tables_only_name_catalog_codes():
    catalog = load_catalog()
    keys = set(ANESTHESIA) | set(OSTEOTOMY) | set(NBL2) | {PLA0}
    keys |= {key for options in WISDOM_OPTIONS.values() for key in options}
    assert [key for key in sorted(keys) if catalog.get(*key) is None] == []


def test_fixture_is_the_current_server_response():
    assert json.loads(FIXTURE.read_text(encoding="utf-8")) == _responses(), (
        "Fixture veraltet – cd server && uv run python tests/test_extract_surgery.py")


def _responses() -> dict:
    """Beide Pilotdiktate (tests/test_extract_anesthesia.py: PAUSED) je Kasse und Privat für die App-Tests."""
    return {f"{name}-{patient}": build_response(text, 10.0, 0.8, patient).model_dump()
            for name, text in (("pilot", WISDOM_OP), ("pausen", PAUSED)) for patient in ("kasse", "privat")}


if __name__ == "__main__":
    FIXTURE.write_text(json.dumps(_responses(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
