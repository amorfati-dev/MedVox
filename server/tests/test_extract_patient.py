"""Patiententyp: Paare BEMA <-> GOZ/GOÄ, Zuzahlungs-Liste und Zuschlag nur beim Privatpatienten."""

from __future__ import annotations

import json

import pytest

from medvox import extract as extract_module
from medvox.extract import Extraction, analyze, billable_codes
from medvox.extract_catalog import CATALOG_PATH, Catalog, load_catalog
from medvox.extract_rules import surcharge_for
from medvox.lexicon import correct
from medvox.normalize import normalize
from tests.test_extract_acceptance import DICTATIONS

MORE = [
    "Osteotomie drei acht", "L1, L1, Ost1 an drei acht.", "Osteotomie privat drei acht, GOZ drei null drei null.",
    "Kofferdam privat, Zahnfilm privat eins sechs, Oberflächenanästhesie.", "Implantat entfernt regio drei sechs.",
    "Wurzelkanalaufbereitung drei sechs, drei Kanäle, elektrometrische Längenbestimmung, Ultraschallaktivierung.",
    "Zahnstein entfernt, professionelle Zahnreinigung, Fluoridierung.", "Zuschlag GOZ null fünf eins null.",
]


def run(dictation: str, patient: str) -> Extraction:
    corrected, _ = correct(dictation)
    n = normalize(corrected)
    return analyze(n.text, n.teeth, patient)


def surgical(result: Extraction) -> list[str]:
    return [s.code for s in result.suggestions if s.code.startswith("05")]


# --- Paar: Ost1 = BEMA 47a / GOZ 3030 --------------------------------------------------------


def test_osteotomy_is_47a_for_statutory_and_3030_for_private_never_both():
    kasse = run("Osteotomie drei acht", "kasse")
    privat = run("Osteotomie drei acht", "privat")
    assert [(s.code, s.teeth, s.kind) for s in kasse.suggestions] == [("47a", (38,), "bema")]
    assert [(s.code, s.teeth, s.kind) for s in privat.suggestions if s.code != "0500"] == [("3030", (38,), "goz")]
    assert "BEMA 47a ↔ GOZ 3030" in privat.suggestions[0].reason


def test_private_surcharge_bracket_follows_from_3030_points():
    points = load_catalog().get("GOZ", "3030").points
    bracket = surcharge_for(points)
    result = run("Osteotomie drei acht", "privat")
    assert surgical(result) == [bracket[0]] == ["0500"]
    assert f"{points} Punkte" in result.suggestions[-1].reason


def test_statutory_patient_never_gets_a_surcharge():
    for dictation in ("Osteotomie drei acht", "Osteotomie drei acht retiniert, Osteotomie vier acht",
                      "Osteotomie privat drei acht, GOZ drei null drei null"):
        assert surgical(run(dictation, "kasse")) == []


def test_unrecorded_pair_still_comes_back_as_decide_alternative(monkeypatch):
    raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    for entry in raw["entries"]:
        if entry["code"] in {"47a", "3030"}:
            entry.pop("equivalent")
    monkeypatch.setattr(extract_module, "load_catalog", lambda: Catalog(raw))
    result = run("Osteotomie drei acht, GOZ drei null drei null", "kasse")
    assert [(s.code, s.alternative) for s in result.suggestions] == [("47a", False), ("3030", True)]
    assert all(any("BEMA 47a" in f and "GOZ 3030" in f and "nur eine" in f for f in s.decide)
               for s in result.suggestions)


def test_each_single_pair_resolves_to_exactly_one_code():
    catalog = load_catalog()
    for bema in (e for e in catalog.entries if e.system == "BEMA"):
        pairs = catalog.equivalents(bema)
        if len(pairs) != 1:
            continue
        other, _link = pairs[0]
        if len(catalog.equivalents(other)) != 1 or catalog.co_payment_allowed(other):
            continue
        dictation = f"{bema.label}, {other.label}."
        for patient, want in (("kasse", bema), ("privat", other)):
            codes = [(s.system, s.code) for s in run(dictation, patient).suggestions if not s.code.startswith("05")]
            assert codes == [want.key], (dictation, patient, codes)


# --- BEMA und GOZ in einer Sitzung ---------------------------------------------------------------


def test_mixed_bema_and_goz_in_one_session():
    # Kassenpatient mit Mehrkostenfüllung: BEMA 13a plus GOZ 2060 als Zuzahlung, nie eine GOZ-Alternative außerhalb der Liste.
    result = run("Drei sechs okklusal, Füllung mit Komposit, BEMA 13a, Zusatzleistung GOZ 2060, Kofferdam gelegt.", "kasse")
    assert billable_codes(result.suggestions) == ["13a", "2060", "12"]
    assert [(s.code, s.kind) for s in result.suggestions if not s.alternative] == [("13a", "bema"), ("2060", "zuzahlung"), ("12", "bema")]
    assert all(s.kind == "zuzahlung" for s in result.suggestions if s.alternative)


def test_bema_and_goz_surgery_on_same_tooth_are_one_service():
    # Ost1 = BEMA 47a / GOZ 3030: beide diktiert ist dieselbe Leistung, der Patiententyp wählt eine Ziffer.
    kasse = run("Osteotomie drei acht, GOZ drei null drei null", "kasse")
    assert [(s.code, s.alternative, s.decide) for s in kasse.suggestions] == [("47a", False, ())]

    privat = run("Osteotomie drei acht, GOZ drei null drei null, Zuschlag GOZ null fünf drei null", "privat")
    assert billable_codes(privat.suggestions) == ["3030", "0500"]
    (zuschlag,) = [s for s in privat.suggestions if s.code.startswith("05")]
    assert "diktiert war 0530 – Stufe aus den Punkten ist 0500" in zuschlag.decide


def test_private_counterpart_only_for_private_patient():
    kasse = run("Infiltrationsanästhesie, Zahnfilm eins sechs.", "kasse")
    assert billable_codes(kasse.suggestions) == ["40", "Ä925a"]
    assert [s for s in kasse.suggestions if s.alternative] == []
    privat = run("Infiltrationsanästhesie, Zahnfilm eins sechs.", "privat")
    assert [(s.system, s.code, s.teeth) for s in privat.suggestions] == [("GOZ", "0090", ()), ("GOÄ", "Ä5000", (16,))]
    assert "Zahn nicht diktiert – je Zahn" in privat.suggestions[0].decide  # GOZ 0090 gilt je Zahn


# --- Kasse: BEMA plus nur erlaubte Zuzahlung; Privat: nie BEMA ------------------------------------


@pytest.mark.parametrize("dictation", list(DICTATIONS.values()) + MORE)
def test_private_patient_never_gets_bema(dictation):
    result = run(dictation, "privat")
    assert result.patient == "privat"
    assert [s.code for s in result.suggestions if s.system == "BEMA" or s.kind != "goz"] == []


@pytest.mark.parametrize("dictation", list(DICTATIONS.values()) + MORE)
def test_statutory_patient_gets_bema_plus_only_allowed_co_payments(dictation):
    catalog = load_catalog()
    for s in run(dictation, "kasse").suggestions:
        entry = catalog.get(s.system, s.code)
        assert s.kind == ("bema" if s.system == "BEMA" else "zuzahlung"), s
        assert s.system == "BEMA" or catalog.co_payment_allowed(entry), s


def test_co_payment_reason_names_basis_and_note():
    result = run("Drei sechs okklusal, Füllung mit Komposit, BEMA 13a, Zusatzleistung GOZ 2060.", "kasse")
    assert billable_codes(result.suggestions) == ["13a", "2060"]
    (zuzahlung,) = [s for s in result.suggestions if s.kind == "zuzahlung"]
    note = load_catalog().get("GOZ", "2060").co_payment.note
    assert zuzahlung.reason.startswith(f"Zuzahlung zu BEMA 13a: {note}")


def test_co_payment_counterpart_is_offered_as_alternative_only():
    result = run("Zahn drei sechs mesial okklusal distal, Kompositfüllung.", "kasse")
    assert billable_codes(result.suggestions) == ["13c"]
    (offer,) = [s for s in result.suggestions if s.alternative]
    assert (offer.code, offer.kind, offer.teeth) == ("2100", "zuzahlung", (36,))
    assert offer.reason.startswith("Zuzahlung möglich zu BEMA 13c")


def test_private_only_service_without_pair_is_noted_for_statutory_patient():
    result = run("Oberflächenanästhesie.", "kasse")
    assert result.suggestions == []
    assert any("GOZ 0080" in note and "Kassenpatienten nicht vorgeschlagen" in note for note in result.notes)


def test_statutory_only_service_is_noted_for_private_patient():
    result = run("Therapiegespräch.", "privat")
    assert result.suggestions == []
    assert any("BEMA ATG" in note and "Privatpatienten nicht vorgeschlagen" in note for note in result.notes)


def test_unknown_patient_type_is_rejected():
    with pytest.raises(ValueError, match="Patiententyp"):
        run("Osteotomie drei acht", "gesetzlich")
