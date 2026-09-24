"""Wurzelkanalbehandlung im Pilot: diktierte Kanalzahl, VitE, Rö2, Flächenzahl als Ziffer, Endo-Zuzahlungen.

Beispiel-Diktat des Behandlers (Testpatient „ohne Patient“): „zahn 46 wurzelkanalbehandlung begonnen mit
infiltrationsanästhesie,rö2, wk*3, vite*3 med phys und längenbestimungen als privat die letzten 2“. Befunde:
„mal drei“/„*3“ ging verloren (32 und 28 je einmal), „VitE“ kam als „PTE 3x“ an, „Röntgen zwei“ ergab kein
Ä925a, „2 flächig“ ergab 13a, „phys“ (GOZ 2420) fehlte still, und beim Kassenpatienten fehlten die
Zuzahlungs-Optionen der Endo. Laut Behandler (2026-09-24) zahlen Kassenpatienten bei der Endo 2400
(Längenbestimmung) und 2420 („phys“) zu, beide je Kanal; sie werden bei jeder WK angeboten.
„als privat die letzten 2“ wertet der Extraktor bewusst nicht aus (offene Frage an den Behandler).

``EXAMPLES`` steht als echte Server-Antwort (``build_response``) in ``app/test/fixtures/endo-beispiel.json``;
``app/test/endo-beispiel.test.ts`` prüft daran die Evident-Zeilen. Neu erzeugen nach einer gewollten
Änderung: ``cd server && uv run python tests/test_extract_endo.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from medvox.extract import Extraction, analyze, billable_codes
from medvox.extract_rules import CANALS_OPEN
from medvox.lexicon import correct
from medvox.normalize import normalize
from medvox.routes_transcribe import build_response

FIXTURE = Path(__file__).resolve().parents[2] / "app" / "test" / "fixtures" / "endo-beispiel.json"

EXAMPLES = {
    "original": ("zahn 46 wurzelkanalbehandlung begonnen mit infiltrationsanästhesie,rö2, wk*3, vite*3 med phys "
                 "und längenbestimungen als privat die letzten 2"),
    "gesprochen": ("Zahn zwei fünf, Füllung zweiflächig, Kunststoff mit BMF. Zahn vier sechs Wurzelkanalbehandlung "
                   "begonnen mit Infiltrationsanästhesie, Röntgen zwei, WK mal drei, VitE mal drei, med phys und "
                   "Längenbestimmungen als privat die letzten zwei."),
    "verhoert": ("Zahn vier sechs Wurzelkanalbehandlung begonnen mit Infiltrationsanästhesie, Röntgen zwei, "
                 "WK mal drei, PTE 3x, med phys und Längenbestimmungen."),
    "getippt": ("Zahn 25, Füllung 2 flächig, Kunststoff mit BMF. Zahn 46 Wurzelkanalbehandlung begonnen mit "
                "Infiltrationsanästhesie, Rö2, WK*3, VitE*3 med phys und Längenbestimmungen als privat die letzten 2"),
}
# Pilot-Diktat nach dem VitE-Fix: Whisper hörte VitE als „WD“, die Anzahl steht davor („2x WD“, „2x WK“),
# und „med“ als „MET“.
PILOT = ("Zahn 25 Infiltrationsanästhesie, Wurzelkanalbehandlung beginnen, 2x WD, 2x WK, MET, Zahn 46 "
         "Dreiflächige Füllung, MOD, Leitungsanästhesie, Viertelseite PAR 1, BMF, Starke Blutung, Blutungsstillung.")
# Erbrachte Hauptvorschläge an 46 (Ziffer -> Anzahl): 2420 („phys“) und 2400 sind diktiert und zählen je
# Kanal wie WK.
ENDO_46 = {"32": 3, "40": 1, "Ä925a": 1, "28": 3, "34": 1, "2420": 3, "2400": 3}
FILLING_25 = {"13b": 1, "12": 1}


def run(dictation: str, patient: str = "kasse") -> Extraction:
    corrected, _ = correct(dictation)
    n = normalize(corrected)
    return analyze(n.text, n.teeth, patient)


def main_at(result: Extraction, fdi: int) -> dict[str, int]:
    return {s.code: s.count for s in result.suggestions if not s.alternative and fdi in s.teeth}


def options_at(result: Extraction, fdi: int) -> dict[str, int]:
    return {s.code: s.count for s in result.suggestions if s.alternative and fdi in s.teeth}


@pytest.mark.parametrize("name", list(EXAMPLES))
def test_captains_example(name):
    result = run(EXAMPLES[name])
    assert main_at(result, 46) == ENDO_46
    assert not any(CANALS_OPEN in s.decide for s in result.suggestions if not s.alternative)
    assert {s.code: s.kind for s in result.suggestions if s.code in {"2400", "2420"}} == {
        "2400": "zuzahlung", "2420": "zuzahlung"}
    # Zuzahlungs-Optionen der Endo (Kassenpatient), nie vorausgewählt; 2400 und 2420 sind schon diktiert.
    assert options_at(result, 46) == {"2197": 1, "2430": 1}
    if 25 in [t for s in result.suggestions for t in s.teeth]:
        assert main_at(result, 25) == FILLING_25
        assert options_at(result, 25) == {"2080": 1}  # Füllung unverändert: nur die Mehrkosten 2080
        assert not any(s.decide for s in result.suggestions if 25 in s.teeth)


def test_pilot_vite_heard_as_wd_with_count_before():
    result = run(PILOT)
    assert main_at(result, 25) == {"40": 1, "32": 2, "28": 2, "34": 1}
    # Endo-Zuzahlungen: 2400/2420 je Kanal wie WK, 2197/2430 neben der Einlage (34)
    assert options_at(result, 25) == {"2400": 2, "2420": 2, "2197": 1, "2430": 1}
    assert main_at(result, 46) == {"13c": 1, "41a": 1, "Ä935a": 1, "12": 1}
    assert options_at(result, 46) == {"2100": 1}
    assert not any(s.decide for s in result.suggestions)


def test_count_before_equals_count_after():
    def counted(said):
        return [(s.code, s.teeth, s.count, s.alternative, s.decide) for s in run(f"Zahn 25 {said}.").suggestions]
    assert counted("2x WK, 2x VitE") == counted("WK*2, VitE*2") == counted("2x WK, 2x WD")


def test_fixture_is_the_current_server_response():
    assert json.loads(FIXTURE.read_text(encoding="utf-8")) == _responses(), (
        "Fixture veraltet – cd server && uv run python tests/test_extract_endo.py")


@pytest.mark.parametrize(
    "said",
    ["WK mal drei", "WK 3x", "WK*3", "WK * 3", "3x WK", "WK dreimal", "Wurzelkanalaufbereitung an drei Kanälen"],
)
def test_dictated_canal_count(said):
    result = run(f"Zahn drei sechs {said}.")
    assert main_at(result, 36) == {"32": 3}
    assert not any(s.decide for s in result.suggestions if not s.alternative)


def test_no_count_said_stays_one_with_check_note():
    result = run("Zahn drei sechs WK, VitE.")
    assert main_at(result, 36) == {"32": 1, "28": 1}
    assert all(CANALS_OPEN in s.decide for s in result.suggestions if s.code in {"32", "28", "2400"})


def test_count_belongs_to_the_position_it_follows():
    result = run("Zahn drei sechs WK 3x, VitE.")
    assert main_at(result, 36) == {"32": 3, "28": 1}
    assert CANALS_OPEN in next(s for s in result.suggestions if s.code == "28").decide


def test_count_for_several_teeth_is_flagged():
    result = run("Zahn drei sechs und drei sieben WK mal drei.")
    wk = [s for s in result.suggestions if s.code == "32"]
    assert [(s.teeth, s.count) for s in wk] == [((36,), 3), ((37,), 3)]
    assert all(any("mehrere Zähne" in f for f in s.decide) for s in wk)


def test_adopted_count_keeps_the_several_teeth_note():
    result = run("Zahn drei sechs, drei sieben WK mal drei, Längenbestimmung.")
    adopted = [s for s in result.suggestions if s.code in {"2400", "2420"}]
    assert sorted((s.code, s.teeth, s.count) for s in adopted) == [
        ("2400", (36,), 3), ("2400", (37,), 3), ("2420", (36,), 3), ("2420", (37,), 3)]
    assert all(any("mehrere Zähne" in f for f in s.decide) for s in adopted)


@pytest.mark.parametrize("said", ["Röntgen, zwei Kanäle aufbereitet", "Röntgen. Zwei Kanäle aufbereitet"])
def test_xray_before_punctuation_is_no_short_form(said):
    result = run(f"Zahn drei sechs {said}.")
    assert not any(s.code == "Ä925a" for s in result.suggestions)
    assert [s.count for s in result.suggestions if s.code == "32"] == [2]


def test_session_counts_are_unchanged():
    assert billable_codes(run("Drei sechs, drei sieben okklusal Karies, BEMA dreizehn a zweimal.").suggestions) == [
        "2x 13a"]


@pytest.mark.parametrize("said", ["Röntgen zwei", "Rö zwei", "Rö 2", "Röntgen 2", "Rö2"])
def test_xray_short_form_spoken(said):
    assert main_at(run(f"Zahn vier sechs Trepanation, {said}."), 46) == {"31": 1, "Ä925a": 1}


def test_xray_followed_by_a_tooth_number_is_no_short_form():
    result = run("Röntgen zwei sechs, Karies.")
    assert not any(s.code == "Ä925a" for s in result.suggestions)


@pytest.mark.parametrize("said, code", [("2 flächig", "13b"), ("3 flächig", "13c"), ("2-flächig", "13b"),
                                        ("zwei flächig", "13b"), ("4flächig", "13d")])
def test_surface_count_as_digit(said, code):
    result = run(f"Zahn drei sechs Füllung {said}.")
    assert main_at(result, 36) == {code: 1}
    assert not any(s.decide for s in result.suggestions if not s.alternative)


def test_endo_options_follow_the_dictated_canal_count():
    result = run("Zahn drei sechs WK mal drei.")
    options = [(s.code, s.alternative, s.kind, s.count, s.decide) for s in result.suggestions if s.code != "32"]
    assert options == [("2400", True, "zuzahlung", 3, ()), ("2420", True, "zuzahlung", 3, ())]
    assert billable_codes(result.suggestions) == ["3x 32"]  # Optionen nur nach Antippen
    unknown = [(s.code, s.count, s.decide) for s in run("Zahn drei sechs WK.").suggestions if s.alternative]
    assert unknown == [("2400", 1, (CANALS_OPEN,)), ("2420", 1, (CANALS_OPEN,))]


@pytest.mark.parametrize("said", ["phys", "Phys", "physikalisch", "physikalische Längenbestimmung",
                                  "elektrophysikalisch"])
def test_phys_is_goz_2420(said):
    result = run(f"Zahn drei sechs WK mal drei, {said}.")
    assert main_at(result, 36) == {"32": 3, "2420": 3}
    assert options_at(result, 36) == {"2400": 3}
    assert run(f"Zahn drei sechs WK mal drei, {said}.", "privat").suggestions[1].code == "2420"


def test_private_patient_gets_no_co_payment_options():
    result = run("Zahn drei sechs WK mal drei, Längenbestimmung, phys.", "privat")
    assert main_at(result, 36) == {"2410": 3, "2400": 3, "2420": 3}
    assert not any(s.alternative for s in result.suggestions)


def test_planned_endo_offers_nothing():
    result = run("Zahn drei sechs: Wurzelkanalbehandlung geplant.")
    assert not any(s.alternative for s in result.suggestions)


def _responses() -> dict:
    return {f"{name}-{patient}": build_response(text, 10.0, 0.8, patient).model_dump()
            for name, text in {**EXAMPLES, "pilot-wd": PILOT}.items() for patient in ("kasse", "privat")}


if __name__ == "__main__":
    FIXTURE.write_text(json.dumps(_responses(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
