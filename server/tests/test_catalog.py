"""Katalog v1 und erweiterter Katalog: Validierung läuft durch, und der Validator findet echte Fehler."""
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

SERVER_DIR = Path(__file__).resolve().parents[1]
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from medvox.catalog import validate as v  # noqa: E402

EXTENDED_PATH = v.CATALOG_PATH.with_name("catalog_extended.json")


@pytest.fixture(scope="module")
def catalog():
    errors, _infos, catalog = v.validate()
    assert errors == []
    return catalog


@pytest.fixture(scope="module")
def extended():
    errors, _infos, catalog = v.validate(EXTENDED_PATH)
    assert errors == []
    return catalog


def _errors_for(catalog: dict) -> list[str]:
    schema = v.load(v.SCHEMA_PATH)
    errors: list[str] = []
    v.check_schema(catalog, schema, schema, "$", errors)
    if not errors:
        errors, _ = v.check_rules(catalog)
    return errors


def test_catalog_v1_is_a_mini_catalog(catalog):
    # Vorgabe des Behandlers: 60-80 Alltagspositionen. Die Obergrenze liegt hoeher, weil er im Review
    # sechs Positionen ausdruecklich fuer v1 nachgefordert hat (Ae935a/Ae5002, GOZ 0500-0530; 84 geprueft)
    # und die Patiententyp-Umschaltung zwoelf Positionen nach v1 geholt hat: die GOZ-Paare von v1-BEMA-
    # Positionen (2020, 2350, 3020, 3300, 1000, 4000, 4020, 4070, 4075) und die Inlays 2150-2170.
    # Nachgefordert: Abszesseroeffnung BEMA Ae161 (Inz1), GOAe Ae2428/Ae2430 (inz1/inz2) und GOZ 2420
    # („phys“, Endo-Zuzahlung je Kanal; Angabe des Behandlers 2026-09-24, aus dem erweiterten Katalog geholt).
    # Weisheitszahn-OP (Angabe des Behandlers 2026-09-24): Nbl2 (BEMA 37 / GOZ 3060), Pla0 (BEMA 51b / GOZ 3090).
    # Schwere Osteotomie GOAe Ae2650 (Angabe des Behandlers 2026-09-25), privat GOZ 3045 (2026-09-26, aus dem
    # erweiterten Katalog geholt).
    assert 60 <= len(catalog["entries"]) <= 106


def test_positions_new_in_v1_are_marked_for_review(catalog):
    marked = {e["code"] for e in catalog["entries"] if e["review"].get("note") == "neu, bitte prüfen"}
    assert marked == {"2020", "2350", "3020", "3300", "1000", "4000", "4020", "4070", "4075", "2150", "2160", "2170",
                      "Ä161", "Ä2428", "Ä2430"}
    proc = subprocess.run(
        [sys.executable, "-m", "medvox.catalog.validate", "--markdown"], cwd=SERVER_DIR, capture_output=True, text=True
    )
    assert "| GOZ 2350 **(neu, bitte prüfen)** |" in proc.stdout
    assert "| GOZ 2060 |" in proc.stdout


def test_extended_catalog_merges_cleanly_with_v1(catalog, extended):
    """Phase-2-Vollimport: beide Dateien zusammen verletzen keine Fachregel (Ziffern, Keywords, Familien)."""
    merged = {"meta": catalog["meta"], "entries": catalog["entries"] + extended["entries"]}
    assert _errors_for(merged) == []
    assert len(merged["entries"]) > len(catalog["entries"])


def test_cli_validates_extended_catalog():
    proc = subprocess.run(
        [sys.executable, "-m", "medvox.catalog.validate", "--quiet", "--catalog", str(EXTENDED_PATH)],
        cwd=SERVER_DIR, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr


def test_cli_exits_zero_and_prints_table():
    proc = subprocess.run(
        [sys.executable, "-m", "medvox.catalog.validate"], cwd=SERVER_DIR, capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr
    assert "== BEMA" in proc.stdout and "== GOZ" in proc.stdout and "== GOÄ" in proc.stdout
    assert proc.stdout.rstrip().endswith("Positionen)")


def test_review_table_lists_every_code(catalog):
    table = v.review_table(catalog)
    for e in catalog["entries"]:
        assert f"  {e['code']:<7}" in table


def test_every_entry_cites_an_https_source(catalog, extended):
    for e in catalog["entries"] + extended["entries"]:
        assert all(url.startswith("https://") for url in e["sources"]), e["code"]


def test_null_points_are_valid_and_listed_for_review(catalog):
    unverified = copy.deepcopy(catalog)
    entry = unverified["entries"][3]
    entry["points"] = None
    assert _errors_for(unverified) == []
    table = v.review_table(unverified)
    assert f"  {entry['code']:<7}    ?  " in table
    assert table.rstrip().endswith(f"Punkte nicht verifiziert (bitte prüfen): {entry['system']} {entry['code']}")
    assert v.review_table(catalog).rstrip().endswith("Punkte nicht verifiziert (bitte prüfen): keine")


def test_detects_duplicate_code(catalog):
    broken = copy.deepcopy(catalog)
    broken["entries"].append(copy.deepcopy(broken["entries"][0]))
    assert any("2× vorhanden" in err for err in _errors_for(broken))


def test_detects_schema_violation(catalog):
    broken = copy.deepcopy(catalog)
    broken["entries"][0]["points"] = "33"
    assert any("points" in err for err in _errors_for(broken))
    for capitalised in ("Großgeschrieben", "Überkappung", "ärztliche Beratung"):
        broken = copy.deepcopy(catalog)
        broken["entries"][0]["keywords"].append(capitalised)
        assert any("keywords" in err for err in _errors_for(broken)), capitalised


def test_detects_keyword_collision_within_system(catalog):
    broken = copy.deepcopy(catalog)
    bema = [e for e in broken["entries"] if e["system"] == "BEMA"]
    bema[1]["keywords"].append(bema[0]["keywords"][0])
    assert any("mehreren Ziffern" in err for err in _errors_for(broken))


def test_detects_broken_surface_family(catalog):
    broken = copy.deepcopy(catalog)
    entry = next(e for e in broken["entries"] if e["code"] == "13a")
    entry["surfaces_to_code"]["3"] = "13x"
    assert any("unbekannte Ziffer 13x" in err for err in _errors_for(broken))


def test_surface_families(catalog, extended):
    by = {(e["system"], e["code"]): e for e in catalog["entries"]}
    assert by[("BEMA", "13a")]["surfaces_to_code"] == {"1": "13a", "2": "13b", "3": "13c", "4": "13d"}
    assert by[("GOZ", "2060")]["surfaces_to_code"] == {"1": "2060", "2": "2080", "3": "2100", "4": "2120"}
    by_ext = {(e["system"], e["code"]): e for e in extended["entries"]}
    assert by_ext[("GOZ", "2050")]["surfaces_to_code"] == {"1": "2050", "2": "2070", "3": "2090", "4": "2110"}


def test_old_repo_errors_are_not_reproduced(catalog, extended):
    """Report Abschnitt 4: diese Ziffern waren im Alt-Repo erfunden oder falsch belegt."""
    by = {(e["system"], e["code"]): e for e in catalog["entries"] + extended["entries"]}
    for invented in ("42", "28a", "28b", "50", "60", "70", "80", "90", "P200", "P201", "IP3"):
        assert ("BEMA", invented) not in by
    assert by[("BEMA", "40")]["title"].startswith("Infiltrationsanästhesie")
    assert by[("BEMA", "41a")]["title"].startswith("Leitungsanästhesie")
    assert "Zahnfilm" not in by[("GOZ", "5000")]["title"]
    assert by[("GOÄ", "Ä5000")]["title"].startswith("Zahnfilm")
    assert by[("GOZ", "0010")]["points"] == 100
    assert catalog["meta"]["punktwert_cent"]["GOZ"] == 5.62421


def test_schema_file_is_valid_json():
    json.loads(v.SCHEMA_PATH.read_text(encoding="utf-8"))


# --- Paare und Zuzahlungs-Liste ------------------------------------------------------------


def _entry(catalog: dict, system: str, code: str) -> dict:
    return next(e for e in catalog["entries"] if (e["system"], e["code"]) == (system, code))


def test_captains_pair_is_recorded_both_ways(catalog):
    assert {"system": "GOZ", "code": "3030"} in _entry(catalog, "BEMA", "47a")["equivalent"]
    assert {"system": "BEMA", "code": "47a"} in _entry(catalog, "GOZ", "3030")["equivalent"]


def test_every_private_position_has_a_co_payment_decision(catalog, extended):
    for e in catalog["entries"] + extended["entries"]:
        assert (e["system"] != "BEMA") == ("zuzahlung" in e), e["code"]
    assert _entry(catalog, "GOZ", "0500")["zuzahlung"]["allowed"] is False  # Zuschlag nur beim Privatpatienten


def test_detects_one_sided_pair(catalog):
    broken = copy.deepcopy(catalog)
    _entry(broken, "GOZ", "3030")["equivalent"] = [{"system": "BEMA", "code": "48"}]
    errors = _errors_for(broken)
    assert any("BEMA 47a: Paar GOZ 3030 ist nicht beidseitig" in err for err in errors)


def test_detects_pair_within_one_system(catalog):
    broken = copy.deepcopy(catalog)
    _entry(broken, "BEMA", "43")["equivalent"] = [{"system": "BEMA", "code": "44"}]
    assert any("im anderen System" in err for err in _errors_for(broken))


def test_detects_missing_or_misplaced_co_payment(catalog):
    broken = copy.deepcopy(catalog)
    moved = _entry(broken, "GOZ", "2060").pop("zuzahlung")
    _entry(broken, "BEMA", "13a")["zuzahlung"] = moved
    errors = _errors_for(broken)
    assert any("GOZ 2060: 'zuzahlung' fehlt" in err for err in errors)
    assert any("BEMA 13a: 'zuzahlung' gibt es nur bei GOZ/GOÄ" in err for err in errors)


def test_markdown_review_tables(catalog):
    proc = subprocess.run(
        [sys.executable, "-m", "medvox.catalog.validate", "--markdown"], cwd=SERVER_DIR, capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr
    assert "| ☐ | 47a | " in proc.stdout and "| GOZ 3030 |" in proc.stdout
    assert "### Zuzahlung – Konservierend" in proc.stdout and "| GOZ 2060 |" in proc.stdout
    assert "\n## Quellen\n\n- Q1: [" in proc.stdout
    assert "## Erweiterter Katalog" in proc.stdout and "| GOZ 2210 |" in proc.stdout
    assert "keine Rechtsberatung" in proc.stdout
    # PRUEFLISTE.md ist die erzeugte Fassung (make catalog-review) und darf nicht veralten
    assert v.CATALOG_PATH.with_name("PRUEFLISTE.md").read_text(encoding="utf-8") == proc.stdout


def test_evident_short_forms_are_only_the_confirmed_ones(catalog, extended):
    forms = {(e["system"], e["code"]): e["evident"] for e in catalog["entries"] + extended["entries"] if "evident" in e}
    assert forms == {
        ("BEMA", "41a"): "l1", ("GOZ", "0100"): "l1", ("BEMA", "35"): "wf",
        ("BEMA", "47a"): "ost1", ("GOZ", "3030"): "ost1", ("BEMA", "48"): "ost2", ("BEMA", "40"): "i",
        ("BEMA", "37"): "nbl2", ("BEMA", "51b"): "pla0",
        ("BEMA", "Ä935d"): "opg", ("GOÄ", "Ä5004"): "opg", ("BEMA", "Ä935a"): "pan1", ("GOÄ", "Ä5002"): "pan1",
        ("BEMA", "12"): "bmf",
        ("BEMA", "Ä161"): "inz1", ("GOÄ", "Ä2428"): "inz1", ("GOÄ", "Ä2430"): "inz2",
    }


def test_evident_short_form_must_be_lowercase(catalog):
    for bad in ("L1", "wf*3", "", "3x"):
        broken = copy.deepcopy(catalog)
        broken["entries"][0]["evident"] = bad
        assert any("evident" in err for err in _errors_for(broken)), bad


def test_detects_misplaced_analog_position(catalog):
    broken = copy.deepcopy(catalog)
    _entry(broken, "GOÄ", "Ä2428")["analog"] = copy.deepcopy(_entry(broken, "GOÄ", "Ä2430")["analog"])
    assert any("GOÄ Ä2428: 'analog' nur bei GOZ/GOÄ ohne BEMA-Paar" in err for err in _errors_for(broken))


def test_detects_broken_or_one_sided_conflict(catalog):
    broken = copy.deepcopy(catalog)
    _entry(broken, "BEMA", "Ä161")["conflicts"][0]["code"] = "99x"
    assert any("BEMA Ä161: Konflikt BEMA 99x fehlt" in err for err in _errors_for(broken))
    broken = copy.deepcopy(catalog)
    _entry(broken, "GOÄ", "Ä2428")["conflicts"] = [c for c in _entry(broken, "GOÄ", "Ä2428")["conflicts"]
                                                    if c["code"] != "3030"]
    assert any("BEMA Ä161: Paar GOÄ Ä2428 trägt den Konflikt mit GOZ 3030 nicht" in err for err in _errors_for(broken))
