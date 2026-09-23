"""WP-8: Regelfamilien des Extraktors einzeln (Flächen, Endo je Kanal, Plan, Zuschlag, BEMA/GOZ gemischt)."""

from __future__ import annotations

import json
import pytest

from medvox import extract as extract_module
from medvox.extract import Extraction, Suggestion, analyze, billable_codes
from medvox.extract_catalog import CATALOG_PATH, Catalog, load_catalog
from medvox.extract_rules import INCLUDED_IN, REMOVAL, ROOT_PAIRS, SURCHARGES, multi_rooted, surcharge_for
from medvox.lexicon import correct
from medvox.normalize import normalize


def run(dictation: str) -> Extraction:
    corrected, _ = correct(dictation)
    n = normalize(corrected)
    return analyze(n.text, n.teeth)


def performed(result: Extraction) -> list[Suggestion]:
    return [s for s in result.suggestions if not s.planned and not s.alternative]


def by_tooth(result: Extraction) -> dict[int, str]:
    return {s.teeth[0]: s.code for s in performed(result) if len(s.teeth) == 1}


# --- Flächen -> Füllungsziffer ---------------------------------------------------------------


@pytest.mark.parametrize(("surfaces", "bema", "goz"), [
    ("okklusal", "13a", "2060"),
    ("mesial okklusal", "13b", "2080"),
    ("mesial okklusal distal", "13c", "2100"),
    ("mesial okklusal distal bukkal", "13d", "2120"),
])
def test_surface_count_selects_filling_code(surfaces, bema, goz):
    result = run(f"Zahn drei sechs {surfaces}, Kompositfüllung.")
    assert billable_codes(result.suggestions) == [bema]
    alternatives = [s for s in result.suggestions if s.alternative]
    assert [(s.code, s.teeth) for s in alternatives] == [(goz, (36,))]


def test_count_word_overrides_surfaces_and_is_flagged():
    result = run("Eins vier distal okklusal Karies, Kompositfüllung MOD, dreiflächig.")
    (filling,) = performed(result)
    assert (filling.code, filling.teeth) == ("13c", (14,))
    assert any("„do“" in flag for flag in filling.decide)


def test_surface_word_alone_is_no_filling():
    assert run("Zahn drei sechs mesial okklusal distal Karies.").suggestions == []


def test_filling_without_surface_count_is_flagged():
    (filling,) = performed(run("Füllung drei sechs."))
    assert filling.code == "13a"
    assert any("Flächenzahl nicht diktiert" in flag for flag in filling.decide)


def test_each_tooth_gets_its_own_filling():
    result = run("Drei sechs, drei sieben okklusal Karies, Füllungen mit Komposit, jeweils einflächig.")
    assert by_tooth(result) == {36: "13a", 37: "13a"}
    assert billable_codes(result.suggestions) == ["2x 13a"]


@pytest.mark.parametrize("dictation", [
    "Füllung drei sechs okklusal distal. Füllung drei sieben mesial okklusal distal.",
    "Drei sechs okklusal distal Füllung, drei sieben mesial okklusal distal Füllung.",
    "Füllung drei sechs okklusal distal, drei sieben mesial okklusal distal.",
    "Füllung drei sechs okklusal distal. Füllung drei sieben, dreiflächig.",
])
def test_surface_count_belongs_to_its_own_tooth(dictation):
    result = run(dictation)
    assert by_tooth(result) == {36: "13b", 37: "13c"}
    assert not any("prüfen" in flag for s in performed(result) for flag in s.decide)


# --- ein-/mehrwurzelig, Zahnentfernung ------------------------------------------------------


@pytest.mark.parametrize(("fdi", "multi"), [
    (11, False), (13, False), (14, True), (15, False), (16, True), (24, True), (25, False),
    (34, False), (35, False), (36, True), (48, True), (53, False), (64, True), (85, True),
])
def test_multi_rooted_follows_bema_definition(fdi, multi):
    assert multi_rooted(fdi) is multi


def test_extraction_code_from_fdi():
    assert by_tooth(run("Extraktion vier sieben.")) == {47: "44"}
    assert by_tooth(run("Extraktion drei drei.")) == {33: "43"}


def test_finding_word_alone_triggers_no_removal():
    assert performed(run("Drei acht retiniert und verlagert.")) == []


def test_osteotomy_of_retained_tooth():
    assert by_tooth(run("Osteotomie drei acht, retiniert.")) == {38: "48"}


def test_ait_per_tooth_by_root_count():
    result = run("Antiinfektiöse Therapie, Kürettage eins fünf bis eins sieben.")
    assert by_tooth(result) == {15: "AITa", 16: "AITb", 17: "AITb"}
    assert all("Antiinfektiöse Therapie" in s.reason for s in performed(result))


# --- je Kanal / je Zahn -------------------------------------------------------------------


def test_endo_per_canal():
    result = run("Drei sechs Vitalexstirpation, drei Kanäle, Wurzelkanalaufbereitung.")
    assert billable_codes(result.suggestions) == ["3x 28", "3x 32"]


def test_endo_without_canal_count_is_flagged():
    (wf,) = performed(run("Wurzelfüllung eins vier."))
    assert (wf.code, wf.count) == ("35", 1)
    assert any("Kanalzahl" in flag for flag in wf.decide)


def test_per_tooth_count_without_tooth_numbers():
    assert billable_codes(run("Professionelle Zahnreinigung, 28 Zähne.").suggestions) == ["28x 1040"]


def test_included_services_are_dropped_with_note():
    result = run("Zwei fünf Trepanation, Vitalexstirpation, medikamentöse Einlage, provisorischer Verschluss.")
    assert billable_codes(result.suggestions) == ["28", "34"]
    assert any("31" in note for note in result.notes) and any("11" in note for note in result.notes)


# --- geplant vs. erbracht ---------------------------------------------------------------------


@pytest.mark.parametrize("dictation", [
    "Extraktion vier acht planen.",
    "Extraktion vier acht geplant.",
    "Nächste Sitzung: Extraktion vier acht.",
    "Termin zur Extraktion vier acht.",
    "Indikation zur Extraktion vier acht.",
    "Überweisung zur Extraktion vier acht.",
])
def test_planned_is_never_billable(dictation):
    result = run(dictation)
    assert billable_codes(result.suggestions) == []
    (planned,) = [s for s in result.suggestions if s.planned]
    assert (planned.code, planned.teeth) == ("44", (48,))
    assert planned.reason.startswith("geplant")


def test_plan_marker_only_affects_its_clause():
    result = run("Kofferdam gelegt, Extraktion vier acht nächste Sitzung.")
    assert billable_codes(result.suggestions) == ["12"]
    assert [s.code for s in result.suggestions if s.planned] == ["44"]


def test_negation_is_not_proposed():
    result = run("Ohne Kofferdam, Leitungsanästhesie.")
    assert billable_codes(result.suggestions) == ["41a"]
    assert any("verneint" in note for note in result.notes)


# --- Zuschlag -----------------------------------------------------------------------------


@pytest.mark.parametrize(("points", "code"), [
    (249, None), (250, "0500"), (499, "0500"), (500, "0510"), (799, "0510"),
    (800, "0520"), (1199, "0520"), (1200, "0530"), (5000, "0530"),
])
def test_surcharge_brackets(points, code):
    bracket = surcharge_for(points)
    assert (bracket[0] if bracket else None) == code


def test_surcharge_table_matches_catalog_rules():
    catalog = load_catalog()
    for code, lo, hi in SURCHARGES:
        rules = " ".join(catalog.get("GOZ", code).rules)
        assert (f"{lo} bis {hi} Punkten" if hi else f"{lo} und mehr Punkten") in rules


def test_captains_example_l1_l1_ost1():
    result = run("L1, L1, Ost1 an drei acht.")
    assert billable_codes(result.suggestions) == ["2x 41a", "47a"]
    (zuschlag,) = [s for s in result.suggestions if s.code in {"0500", "0510", "0520", "0530"}]
    assert zuschlag.code == "0500" and zuschlag.alternative
    assert "GOZ 3030" in zuschlag.reason and "350 Punkte" in zuschlag.reason
    assert [s.code for s in result.suggestions if s.alternative] == ["0100", "3030", "0500"]


def test_surcharge_once_from_highest_goz_position():
    result = run("Osteotomie privat drei acht retiniert, Extraktion privat vier sieben, Osteotomie privat vier acht.")
    zuschlaege = [s for s in result.suggestions if s.code.startswith("05")]
    assert [(s.code, s.alternative) for s in zuschlaege] == [("0510", False)]
    assert "GOZ 3040" in zuschlaege[0].reason and "540 Punkte" in zuschlaege[0].reason


def test_no_surcharge_below_250_points():
    assert not [s for s in run("Extraktion vier sieben.").suggestions if s.code.startswith("05")]


def test_unknown_points_are_reported_not_guessed(monkeypatch):
    raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    for entry in raw["entries"]:
        if entry["code"] == "3030":
            entry["points"] = None
    monkeypatch.setattr(extract_module, "load_catalog", lambda: Catalog(raw))
    result = run("Osteotomie privat drei sieben.")
    assert not [s for s in result.suggestions if s.code.startswith("05")]
    assert any("nicht bestimmbar" in note and "GOZ 3030" in note for note in result.notes)


def test_missing_goz_counterpart_blocks_surcharge_with_note():
    result = run("Extraktion vier sieben wegen Längsfraktur.")
    assert billable_codes(result.suggestions) == ["45"]
    assert any("GOZ 3020" in note and "nicht bestimmbar" in note for note in result.notes)


# --- BEMA und GOZ gemischt -----------------------------------------------------------------


def test_mixed_bema_and_goz_in_one_session():
    result = run("Drei sechs okklusal, Füllung mit Komposit, BEMA 13a, Zusatzleistung GOZ 2060, Kofferdam gelegt.")
    assert billable_codes(result.suggestions) == ["13a", "2060", "12"]
    assert [s.code for s in result.suggestions if s.alternative] == ["2040"]


def test_private_alternative_never_replaces_bema():
    result = run("Infiltrationsanästhesie, Zahnfilm eins sechs.")
    assert billable_codes(result.suggestions) == ["40", "Ä925a"]
    assert [(s.system, s.code) for s in result.suggestions if s.alternative] == [("GOZ", "0090"), ("GOÄ", "Ä5000")]


def test_unknown_dictated_code_is_noted():
    result = run("BEMA 20a eingegliedert.")
    assert result.suggestions == []
    assert result.notes == ["BEMA 20a diktiert, steht nicht im Katalog v1 – kein Vorschlag"]


# --- nur Katalog v1 --------------------------------------------------------------------------


def test_tables_only_name_catalog_codes():
    catalog = load_catalog()
    codes = [("BEMA", c) for c in REMOVAL["BEMA"].values()] + [("GOZ", c) for c in REMOVAL["GOZ"].values()]
    codes += [(s, c) for (s, _), pair in ROOT_PAIRS.items() for c in pair]
    codes += list(INCLUDED_IN) + list(INCLUDED_IN.values()) + [("GOZ", c) for c, _lo, _hi in SURCHARGES]
    assert [key for key in codes if catalog.get(*key) is None] == []


def test_never_suggests_codes_outside_catalog_v1():
    v1 = {e.key for e in load_catalog().entries}
    extended = json.loads(CATALOG_PATH.with_name("catalog_extended.json").read_text(encoding="utf-8"))
    words = [k for e in extended["entries"] for k in e["keywords"]]
    words += [f"{e['system']} {e['code']}" for e in extended["entries"]]
    words += [k for e in load_catalog().entries for k in e.keywords]
    for i in range(0, len(words), 7):
        chunk = ", ".join(words[i : i + 7]) + " drei sechs mesial okklusal, zwei fünf, 28 Zähne, 3 Kanäle."
        for s in run(chunk).suggestions:
            assert (s.system, s.code) in v1, (s, chunk)
