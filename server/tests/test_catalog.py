"""Katalog v1: Validierung läuft durch, und der Validator findet echte Fehler."""
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


@pytest.fixture(scope="module")
def catalog():
    errors, _infos, catalog = v.validate()
    assert errors == []
    return catalog


def _errors_for(catalog: dict) -> list[str]:
    schema = v.load(v.SCHEMA_PATH)
    errors: list[str] = []
    v.check_schema(catalog, schema, schema, "$", errors)
    if not errors:
        errors, _ = v.check_rules(catalog)
    return errors


def test_catalog_is_valid(catalog):
    assert len(catalog["entries"]) >= 60


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


def test_every_entry_has_verified_points_and_source(catalog):
    for e in catalog["entries"]:
        assert e["points"] is not None, e["code"]
        assert all(url.startswith("https://") for url in e["sources"])


def test_detects_duplicate_code(catalog):
    broken = copy.deepcopy(catalog)
    broken["entries"].append(copy.deepcopy(broken["entries"][0]))
    assert any("2× vorhanden" in err for err in _errors_for(broken))


def test_detects_schema_violation(catalog):
    broken = copy.deepcopy(catalog)
    broken["entries"][0]["points"] = "33"
    assert any("points" in err for err in _errors_for(broken))
    broken = copy.deepcopy(catalog)
    broken["entries"][0]["keywords"].append("Großgeschrieben")
    assert any("keywords" in err for err in _errors_for(broken))


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


def test_surface_families(catalog):
    by = {(e["system"], e["code"]): e for e in catalog["entries"]}
    assert by[("BEMA", "13a")]["surfaces_to_code"] == {"1": "13a", "2": "13b", "3": "13c", "4": "13d"}
    assert by[("GOZ", "2060")]["surfaces_to_code"] == {"1": "2060", "2": "2080", "3": "2100", "4": "2120"}
    assert by[("GOZ", "2050")]["surfaces_to_code"] == {"1": "2050", "2": "2070", "3": "2090", "4": "2110"}


def test_old_repo_errors_are_not_reproduced(catalog):
    """Report Abschnitt 4: diese Ziffern waren im Alt-Repo erfunden oder falsch belegt."""
    by = {(e["system"], e["code"]): e for e in catalog["entries"]}
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
