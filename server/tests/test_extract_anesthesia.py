"""Anästhesie je Zahn (extract_anesthesia): Anzahl am Zahn, „IP“ als I, „X2“ hinter I als Anzahl, Diktierpausen
und die Praxisregel ``repeat`` (KZVB: zweite Anästhesie je Zahn erst ab Ost1, Angabe des Behandlers 2026-09-24).

``PAUSED`` ist das zweite echte Whisper-Transkript desselben Pilotpatienten (Kassenpatient). Der Behandler:
18 = I + X2 („nur eine Infiltrationsanästhesie“, kein Ost), 28 = I*2 + Ost1; ein OPG war nicht gesprochen.
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from medvox.catalog import validate as v
from medvox.extract import Extraction, Suggestion, analyze, billable_codes
from medvox.extract_anesthesia import IP_AS_I, LONG_UNCOUNTED, NEIGHBOURS, REPEATED, X2_AS_COUNT
from medvox.extract_catalog import load_catalog
from medvox.lexicon import correct
from medvox.normalize import normalize

PAUSED = (
    "Der Patient kommt für 4 Achter. Achter entfernt. Und zwar 18. IP, X2. Zahn im Ganzen rausgehebelt. 28. IP, 1. "
    "Infiltrationsanästhesie. 2x. Beim zweiten Mal lange Dauer. 28. Dann Ost, 1. zur Kontrolle ob noch ein "
    "Wurkelrest drin steckt."
)
KZVB = load_catalog().get("BEMA", "40").repeat.note


def run(dictation: str, patient: str = "kasse") -> Extraction:
    corrected, _ = correct(dictation)
    n = normalize(corrected)
    return analyze(n.text, n.teeth, patient)


def main(result: Extraction) -> list[Suggestion]:
    return [s for s in result.suggestions if not s.planned and not s.alternative]


def one(result: Extraction, code: str, fdi: int) -> Suggestion:
    (found,) = [s for s in main(result) if s.code == code and s.teeth == (fdi,)]
    return found


# --- zweites Pilotdiktat --------------------------------------------------------------------------


def test_paused_dictation_statutory():
    result = run(PAUSED)
    assert [(s.code, s.teeth, s.count) for s in main(result)] == [
        ("40", (18,), 1), ("44", (18,), 1), ("40", (28,), 2), ("47a", (28,), 1)]
    assert billable_codes(result.suggestions) == ["3x 40", "44", "47a"]
    i18, i28 = one(result, "40", 18), one(result, "40", 28)
    assert KZVB in i18.decide and IP_AS_I in i18.decide and X2_AS_COUNT not in i18.decide  # 44 steht am Zahn
    assert i28.reason.endswith("2× diktiert, zweite wegen „lange Dauer“") and KZVB not in i28.decide
    assert one(result, "47a", 28).evident == "ost1"
    assert not any(s.code.startswith("Ä935") for s in result.suggestions)


# --- Anzahl am Zahn ------------------------------------------------------------------------------


def test_one_hit_with_neighbouring_teeth_stays_one_infiltration():
    assert [(s.code, s.teeth, s.count) for s in main(run("Infiltrationsanästhesie 36, 37."))] == [("40", (36, 37), 1)]


def test_separate_infiltrations_on_neighbouring_teeth_are_flagged():
    result = run("Infiltrationsanästhesie 36. Infiltrationsanästhesie 37.")
    assert [(s.teeth, s.count) for s in main(result)] == [((36,), 1), ((37,), 1)]
    assert all(NEIGHBOURS.format(a=36, b=37) in s.decide for s in main(result))
    assert not any(s.decide for s in main(run("Infiltrationsanästhesie 11. Infiltrationsanästhesie 21.")))


def test_long_duration_without_count_only_asks():
    s = one(run("Leitungsanästhesie 46 wegen langer Dauer, Extraktion 46."), "41a", 46)
    assert s.count == 1 and s.decide == (LONG_UNCOUNTED.format(word="langer Dauer"),)


def test_same_anesthesia_named_twice_counts_once_with_hint():
    s = one(run("Leitungsanästhesie 46. Extraktion 46, Leitungsanästhesie 46."), "41a", 46)
    assert s.count == 1 and REPEATED.format(n=2) in s.decide


@pytest.mark.parametrize("said", ["46 2x Leitungsanästhesie", "2x Leitungsanästhesie 46",
                                  "46 Leitungsanästhesie mal 2", "Leitungsanästhesie 46 2x"])
def test_count_binds_to_the_tooth(said):
    assert [(s.code, s.teeth, s.count) for s in main(run(f"{said}, Osteotomie 46."))][0] == ("41a", (46,), 2)


def test_anesthesia_without_tooth_still_counts_per_session():
    assert billable_codes(run("L1, L1, Ost1 an 38.").suggestions) == ["2x 41a", "47a"]


@pytest.mark.parametrize(("said", "code"), [
    ("38 L1, L1 lange Dauer, Ost2.", "41a"), ("L1, L1 lange Dauer, Ost2 38.", "41a"),
    ("18 IP, IP lange Dauer, Ost2.", "40"),
])
def test_repeated_short_form_counts_twice_wherever_the_tooth_stands(said, code):
    s = next(s for s in main(run(said)) if s.code == code)
    assert s.count == 2 and "lange Dauer" in s.reason
    assert not any(REPEATED.format(n=2) == d for d in s.decide)


def test_repeated_short_form_without_osteotomy_stays_one():
    s = one(run("38 L1, L1 lange Dauer, Extraktion 38."), "41a", 38)
    assert s.count == 1 and KZVB in s.decide and REPEATED.format(n=2) not in s.decide


def test_repeated_hint_only_when_counted_once():
    s = next(s for s in main(run("L1, L1, Ost2 38.")) if s.code == "41a")
    assert s.count == 2 and REPEATED.format(n=2) not in s.decide


# --- Praxisregel repeat (KZVB): zweite Anästhesie erst ab Ost1 am selben Zahn ------------------------


@pytest.mark.parametrize(("surgery", "count"), [
    ("Osteotomie 46", 2), ("46 Ost2", 2), ("Extraktion 46", 1), ("46 X2", 1), ("Füllung 46 okklusal", 1),
    ("Osteotomie 36", 1),  # Osteotomie an einem anderen Zahn zählt nicht
])
def test_second_anesthesia_only_with_osteotomy_on_that_tooth(surgery, count):
    s = one(run(f"46 Leitungsanästhesie 2x lange Dauer, {surgery}."), "41a", 46)
    assert s.count == count
    assert (KZVB in s.decide) == (count == 1)  # nie still: gekürzt immer mit Hinweis


def test_repeat_rule_is_statutory_only():
    s = one(run("46 Leitungsanästhesie 2x lange Dauer, Extraktion 46.", "privat"), "0100", 46)
    assert s.count == 2 and KZVB not in s.decide


def test_catalog_validator_checks_repeat_targets():
    raw = json.loads(v.CATALOG_PATH.read_text(encoding="utf-8"))
    entry = next(e for e in raw["entries"] if e["system"] == "BEMA" and e["code"] == "40")
    assert entry["repeat"]["source"].startswith("Angabe des Behandlers 2026-09-24")
    entry["repeat"]["only_with"].append({"system": "BEMA", "code": "99x"})
    assert any("repeat-Ziel BEMA 99x fehlt" in err for err in v.check_rules(raw)[0])


# --- „IP“, „X2“, Diktierpausen --------------------------------------------------------------------


@pytest.mark.parametrize("said", ["18. IP.", "18 IP", "18, IP."])
def test_ip_after_a_tooth_is_infiltration(said):
    s = one(run(f"{said} Osteotomie 18."), "40", 18)
    assert s.count == 1 and IP_AS_I in s.decide


def test_ip_without_tooth_or_count_is_no_anesthesia():
    assert "40" not in [s.code for s in run("IP besprochen.").suggestions]
    assert [s.code for s in main(run("Kind 8 Jahre, IP5 an 16."))] == ["IP5"]


@pytest.mark.parametrize("said", ["18 IP, X2", "18 I x2", "18 IP x 2"])
def test_x2_right_after_i_is_the_count(said):
    result = run(f"{said}, Osteotomie 18.")
    assert [(s.code, s.count) for s in main(result)] == [("40", 2), ("47a", 1)]
    assert X2_AS_COUNT not in one(result, "40", 18).decide  # Zahnentfernung steht schon am Zahn
    alone = one(run(f"{said}."), "40", 18)  # ohne Osteotomie: KZVB auf 1, X2 könnte die Extraktion sein
    assert alone.count == 1 and KZVB in alone.decide and X2_AS_COUNT in alone.decide
    assert "44" not in [s.code for s in run(f"{said}.").suggestions]


@pytest.mark.parametrize("said", ["18 X2", "Zahn 18 X2", "18 Infiltrationsanästhesie, 18 X2"])
def test_x2_alone_is_still_the_extraction(said):
    assert "44" in [s.code for s in main(run(f"{said}."))]


def test_fragments_join_their_tooth_and_count():
    result = run("Und zwar 36. Leitungsanästhesie. 2x. Osteotomie.")
    assert [(s.code, s.teeth, s.count) for s in main(result)] == [("41a", (36,), 2), ("47a", (36,), 1)]


def test_sentence_with_own_tooth_does_not_borrow_one():
    assert [(s.code, s.teeth) for s in main(run("Zahn 36 Füllung okklusal. Leitungsanästhesie, Zahnfilm 16."))][1] == (
        "41a", ())


@pytest.mark.parametrize("word", ["Ost, 1", "Ost 1", "Ost1"])
def test_ost1_with_punctuation(word):
    assert [(s.code, s.teeth) for s in main(run(f"28. Dann {word}."))] == [("47a", (28,))]


def test_validator_cli_still_passes():
    proc = subprocess.run([sys.executable, "-m", "medvox.catalog.validate"], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr
