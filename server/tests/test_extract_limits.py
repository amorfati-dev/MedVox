"""Höchstzahl je Position (Katalogfeld ``max_per``): BEMA 12 „bmf“ nur einmal je Sitzung und Bereich.

Es wirken nur vom Behandler bestätigte Höchstzahlen (``max_per_status`` „bestaetigt“); die übrigen sind
Vorschläge und lassen die Vorschläge des Extraktors unverändert.

Praxisbefund: „Kofferdam gelegt“ an 36 und an 37 wurde als 12*2 kopiert – abrechenbar ist 12 dort einmal.
"""

from __future__ import annotations

import copy

import pytest

from medvox.catalog import validate as v
from medvox.extract import Extraction, Suggestion, analyze, billable_codes
from medvox.extract_build import Draft
from medvox.extract_catalog import Catalog, load_catalog
from medvox.extract_limits import NO_REGION, apply_limits, region
from medvox.lexicon import correct
from medvox.normalize import normalize

# Einträge mit Höchstzahl (Einheit, Anzahl), je gegen den amtlichen KZBV-/GOZ-Text gelesen; alle übrigen
# v1-Einträge tragen ausdrücklich "unbegrenzt". Bestätigt hat der Behandler bisher nur CONFIRMED.
LIMITED = {
    ("BEMA", "01"): ("sitzung", 1), ("BEMA", "04"): ("sitzung", 1), ("BEMA", "8"): ("sitzung", 1),
    ("BEMA", "105"): ("sitzung", 1), ("BEMA", "107"): ("sitzung", 1), ("BEMA", "IP1"): ("sitzung", 1),
    ("BEMA", "IP2"): ("sitzung", 1), ("BEMA", "IP4"): ("halbjahr", 2),
    ("BEMA", "12"): ("kieferhaelfte", 1), ("BEMA", "38"): ("kieferhaelfte", 1),
    ("BEMA", "26"): ("zahn", 1), ("BEMA", "34"): ("zahn", 1), ("BEMA", "IP5"): ("zahn", 1),
    ("BEMA", "AITa"): ("zahn", 1), ("BEMA", "AITb"): ("zahn", 1),
    ("BEMA", "28"): ("kanal", 1), ("BEMA", "32"): ("kanal", 1), ("BEMA", "35"): ("kanal", 1),
    ("GOZ", "0070"): ("sitzung", 1), ("GOZ", "1000"): ("sitzung", 1), ("GOZ", "1020"): ("sitzung", 1),
    ("GOZ", "4000"): ("jahr", 2), ("GOZ", "4005"): ("jahr", 2), ("GOZ", "4020"): ("sitzung", 1),
    ("GOZ", "0500"): ("sitzung", 1), ("GOZ", "0510"): ("sitzung", 1), ("GOZ", "0520"): ("sitzung", 1),
    ("GOZ", "0530"): ("sitzung", 1),
    ("GOZ", "0080"): ("kieferhaelfte", 1), ("GOZ", "2030"): ("kieferhaelfte", 2), ("GOZ", "2040"): ("kieferhaelfte", 1),
    ("GOZ", "3290"): ("kieferhaelfte", 1), ("GOZ", "3300"): ("kieferhaelfte", 2),
    ("GOZ", "1040"): ("zahn", 1), ("GOZ", "2000"): ("zahn", 1), ("GOZ", "2430"): ("zahn", 1),
    ("GOZ", "4050"): ("zahn", 1), ("GOZ", "4055"): ("zahn", 1), ("GOZ", "4070"): ("zahn", 1), ("GOZ", "4075"): ("zahn", 1),
    ("GOZ", "2360"): ("kanal", 1), ("GOZ", "2400"): ("kanal", 2), ("GOZ", "2410"): ("kanal", 1), ("GOZ", "2420"): ("kanal", 1),
    ("GOZ", "2440"): ("kanal", 1),
}
CONFIRMED = {("BEMA", "12")}


def run(dictation: str, patient: str = "kasse") -> Extraction:
    corrected, _ = correct(dictation)
    n = normalize(corrected)
    return analyze(n.text, n.teeth, patient)


def performed(result: Extraction, code: str) -> list[Suggestion]:
    return [s for s in result.suggestions if s.code == code and not s.planned and not s.alternative]


def test_every_v1_entry_states_its_limit():
    _errors, _infos, catalog = v.validate()
    limits = {(e["system"], e["code"]): e["max_per"] for e in catalog["entries"]}
    assert {k: (m["unit"], m["count"]) for k, m in limits.items() if m["unit"] != "unbegrenzt"} == LIMITED
    assert all("count" not in m for k, m in limits.items() if k not in LIMITED)


def test_only_confirmed_limits_are_enforced():
    _errors, _infos, catalog = v.validate()
    status = {(e["system"], e["code"]): e.get("max_per_status") for e in catalog["entries"]}
    assert {k for k, st in status.items() if st == "bestaetigt"} == CONFIRMED
    assert {k for k, st in status.items() if st == "vorschlag"} == set(LIMITED) - CONFIRMED
    enforced = {e.key: e.limit for e in load_catalog().entries if e.limit is not None}
    assert enforced == {k: LIMITED[k] for k in CONFIRMED}


@pytest.mark.parametrize("limit", [{"unit": "sitzung"}, {"unit": "unbegrenzt", "count": 1}])
def test_validator_requires_count_exactly_for_limits(limit):
    _errors, _infos, catalog = v.validate()
    broken = copy.deepcopy(catalog)
    next(e for e in broken["entries"] if e["code"] == "12")["max_per"] = limit
    errors, _ = v.check_rules(broken)
    assert any("BEMA 12: max_per braucht 'count'" in err for err in errors)


@pytest.mark.parametrize("code, change", [
    ("12", lambda e: e.pop("max_per_status")),
    ("01", lambda e: e.update(max_per={"unit": "unbegrenzt"})),
])
def test_validator_requires_status_exactly_for_limits(code, change):
    _errors, _infos, catalog = v.validate()
    broken = copy.deepcopy(catalog)
    change(next(e for e in broken["entries"] if e["code"] == code))
    errors, _ = v.check_rules(broken)
    assert any(f"BEMA {code}: max_per_status gehört genau zu einer Höchstzahl" in err for err in errors)


def test_kofferdam_twice_in_one_jaw_half_is_billed_once():
    result = run("Zahn drei sechs Füllung dreiflächig, Kofferdam gelegt. "
                 "Zahn drei sieben Füllung zweiflächig, Kofferdam gelegt.")
    [bmf] = performed(result, "12")
    assert (bmf.count, bmf.teeth, bmf.evident) == (1, (36, 37), "bmf")
    assert "2× diktiert, höchstens 1× je Kieferhälfte oder Frontzahnbereich (UK links)" in bmf.reason
    assert billable_codes(result.suggestions) == ["13c", "12", "13b"]


KOFFERDAM_BOTH_HALVES = ("Zahn drei sechs Füllung dreiflächig, Kofferdam gelegt. "
                         "Zahn vier sechs Füllung zweiflächig, Kofferdam gelegt.")


def test_kofferdam_in_both_jaw_halves_is_billed_per_half():
    result = run(KOFFERDAM_BOTH_HALVES)
    pieces = performed(result, "12")
    assert [(s.count, s.teeth) for s in pieces] == [(1, (36,)), (1, (46,))]
    assert "eigene Position für UK links" in pieces[0].reason and "UK rechts" in pieces[1].reason
    assert "2x 12" in billable_codes(result.suggestions)


def test_privat_counterpart_with_proposed_limit_is_unchanged():
    result = run(KOFFERDAM_BOTH_HALVES, "privat")
    [goz] = performed(result, "2040")
    assert (goz.count, goz.teeth) == (2, (36, 46)) and "höchstens" not in goz.reason
    assert billable_codes(result.suggestions) == ["2100", "2x 2040", "2080"]


def test_one_mention_covering_two_jaw_halves_gives_one_per_half():
    assert [s.teeth for s in performed(run("Kofferdam an drei sechs und vier sechs."), "12")] == [(36,), (46,)]


def test_front_teeth_form_one_region():
    assert [s.teeth for s in performed(run("Kofferdam an eins eins und zwei eins."), "12")] == [(11, 21)]
    assert [s.teeth for s in performed(run("Kofferdam an eins drei und eins vier."), "12")] == [(13,), (14,)]


def test_unknown_region_gives_one_with_decide_note():
    [bmf] = performed(run("Kofferdam gelegt, Kofferdam gelegt."), "12")
    assert bmf.count == 1 and NO_REGION in bmf.decide and "höchstens 1×" in bmf.reason


def test_proposed_limit_changes_nothing():
    [zst] = performed(run("Zahnsteinentfernung 2x."), "107")
    assert zst.count == 2 and "höchstens" not in zst.reason
    [vit] = performed(run("Vitalitätsprüfung drei sechs. Vitalitätsprüfung vier sechs."), "8")
    assert vit.count == 2 and "höchstens" not in vit.reason


def test_unlimited_position_still_multiplies():
    result = run("Leitungsanästhesie 2x, Zahn drei sechs Wurzelkanalaufbereitung drei Kanäle.")
    assert billable_codes(result.suggestions) == ["2x 41a", "3x 32"]
    assert all("höchstens" not in s.reason for s in result.suggestions)


@pytest.mark.parametrize("fdi, expected", [
    (13, "OK-Front"), (23, "OK-Front"), (14, "OK rechts"), (27, "OK links"), (33, "UK-Front"),
    (43, "UK-Front"), (36, "UK links"), (48, "UK rechts"), (53, "OK-Front"), (55, "OK rechts"), (84, "UK rechts"),
])
def test_region_from_fdi(fdi, expected):
    assert region(fdi) == expected


@pytest.mark.parametrize("code, limit", [
    ("IP4", {"unit": "sitzung", "count": 2}),  # „einmal je Kalenderhalbjahr (hohes Kariesrisiko: zweimal)“
    ("4000", {"unit": "sitzung", "count": 2}),  # „höchstens zweimal je Jahr“
    ("IP4", {"unit": "jahr", "count": 2}),  # Einheit passt nicht zum Regeltext
])
def test_validator_rejects_period_limits_as_session_limits(code, limit):
    _errors, _infos, catalog = v.validate()
    broken = copy.deepcopy(catalog)
    next(e for e in broken["entries"] if e["code"] == code)["max_per"] = limit
    errors, _ = v.check_rules(broken)
    assert any(f"{code}: Grenze je Halbjahr/Jahr" in err for err in errors)


def _confirmed(codes: set[str]) -> Catalog:
    _errors, _infos, raw = v.validate()
    raw = copy.deepcopy(raw)
    for e in raw["entries"]:
        if e["code"] in codes and "count" in e.get("max_per", {}):
            e["max_per_status"] = "bestaetigt"
    return Catalog(raw)


def test_period_limits_never_get_a_stepper_even_when_confirmed():
    cat = _confirmed({"IP4", "4000", "4005", "2030", "3300"})
    for system, code in (("BEMA", "IP4"), ("GOZ", "4000"), ("GOZ", "4005"), ("GOZ", "2030"), ("GOZ", "3300")):
        entry = cat.get(system, code)
        assert entry.limit is not None and not cat.stepper(entry)[0], code


def test_confirmed_period_limit_caps_one_session():
    entry = _confirmed({"4000"}).get("GOZ", "4000")
    [draft] = apply_limits([Draft(entry, None, False, count=3)])
    assert draft.count == 2 and draft.limit_note == "3× diktiert, höchstens 2× je Jahr"
