"""Wörterbuch-Seite: Einträge wirken sofort (F5), Probe über /analyze, Prompt je Anfrage, Vorschläge, Löschen."""

from __future__ import annotations

from fastapi.testclient import TestClient

from medvox import db
from tests.conftest import FakeWhisper, make_wav

LEXICON = "/api/v1/lexicon"
SENTENCE = "Zahn steinentfernung, Politur, Fluoridierung."


def _add(tc: TestClient, kind: str, right: str, wrong: str = "", source: str = "hand"):
    return tc.post(LEXICON, json={"kind": kind, "wrong": wrong, "right": right, "source": source})


def _upload(tc: TestClient):
    return tc.post("/api/v1/transcribe", files={"file": ("a.wav", make_wav(), "audio/wav")})


def _prompts(whisper: FakeWhisper) -> list[bytes]:
    return [r.content for r in whisper.requests if r.url.path == "/inference"]


def test_lexicon_needs_a_session(client: TestClient) -> None:
    assert client.get(LEXICON).status_code == 401
    assert _add(client, "begriff", "Bulkfill").status_code == 401
    assert client.delete("/api/v1/corrections").status_code == 401


def test_page_data_shows_built_ins_and_the_prompt_gauge(logged_in: TestClient) -> None:
    body = logged_in.get(LEXICON).json()
    assert body["entries"] == []
    assert len(body["builtin"]) == 10 and {"wrong": "bis registrat", "right": "Bissregistrat"} in body["builtin"]
    prompt = body["prompt"]
    assert prompt["base"].startswith("Zahnarzt-Diktat.")
    assert prompt["terms_tokens"] == 0 and prompt["limit"] == 223 and prompt["exact"] is False
    assert 0 < prompt["base_tokens"] < prompt["limit"]


def test_probe_shows_the_draft_effect_without_saving(logged_in: TestClient) -> None:
    before = logged_in.post("/api/v1/analyze", json={"text": SENTENCE}).json()
    draft = {"wrong": "Zahn steinentfernung", "right": "Zahnsteinentfernung"}
    after = logged_in.post("/api/v1/analyze", json={"text": SENTENCE, "draft": draft}).json()
    assert "107" not in before["codes"] and "107" in after["codes"]
    assert after["transcript"].startswith("Zahnsteinentfernung")
    assert logged_in.get(LEXICON).json()["entries"] == []  # Probe speichert nichts
    refused = logged_in.post("/api/v1/analyze", json={"text": SENTENCE, "draft": {"wrong": "Zahn", "right": "X"}})
    assert refused.status_code == 422 and "allein geht nicht" in refused.json()["detail"]


def test_saved_replacement_applies_to_the_next_dictation_and_can_be_switched_off(
    logged_in: TestClient, whisper: FakeWhisper
) -> None:
    whisper.text = f" {SENTENCE}\n"
    assert "107" not in _upload(logged_in).json()["codes"]
    created = _add(logged_in, "ersetzung", "Zahnsteinentfernung", "Zahn steinentfernung")
    assert created.status_code == 200
    entry = created.json()
    assert (entry["active"], entry["source"]) == (True, "hand")
    assert "107" in _upload(logged_in).json()["codes"]
    assert "107" in logged_in.post("/api/v1/analyze", json={"text": SENTENCE}).json()["codes"]
    off = logged_in.put(f"{LEXICON}/{entry['id']}", json={"active": False})
    assert off.status_code == 200 and off.json()["active"] is False
    assert "107" not in _upload(logged_in).json()["codes"]
    assert logged_in.get(LEXICON).json()["entries"][0]["id"] == entry["id"]  # bleibt sichtbar
    assert logged_in.put(f"{LEXICON}/999", json={"active": True}).status_code == 404


def test_guard_rules_answer_422_with_a_reason(logged_in: TestClient) -> None:
    for wrong, reason in (("Zahn", "allein geht nicht"), ("drei sechs", "Zahlen"), ("Karies", "Fachbegriff")):
        response = _add(logged_in, "ersetzung", "Irgendwas", wrong)
        assert response.status_code == 422 and reason in response.json()["detail"]
    assert "Grundtext" in _add(logged_in, "begriff", "Zahnarzt").json()["detail"]


def test_terms_go_into_the_prompt_of_each_request(logged_in: TestClient, whisper: FakeWhisper) -> None:
    _upload(logged_in)
    first = _add(logged_in, "begriff", "Keramikinlay").json()
    _add(logged_in, "begriff", "Bulkfill")
    _upload(logged_in)
    logged_in.put(f"{LEXICON}/{first['id']}", json={"active": False})
    _upload(logged_in)
    base, with_terms, one_off = _prompts(whisper)
    assert b"Keramikinlay" not in base
    assert b"Keramikinlay, Bulkfill." in with_terms
    assert b"Keramikinlay" not in one_off and b"Bulkfill." in one_off
    gauge = logged_in.get(LEXICON).json()["prompt"]
    assert gauge["terms_tokens"] > 0


def test_suggestions_count_equal_changes_and_offer_only_safe_ones(logged_in: TestClient, settings) -> None:
    rows = [("text", "Zahn steinentfernung, Politur,", "Zahnsteinentfernung, Politur,")] * 3
    rows += [("text", "und Zahn steinentfernung", "und Zahnsteinentfernung")]
    rows += [("text", "Zahn 36 okklusal", "Zahn 46 okklusal"), ("ziffer", "13b", "13c"), ("ziffer", "13b", "13c")]
    with db.connect(settings.db_path) as conn:
        for i, (kind, before, after) in enumerate(rows):
            conn.execute(
                "INSERT INTO corrections (id, week, patient_type, kind, before, after, catalog_version)"
                " VALUES (?, ?, 'kasse', ?, ?, ?, 'v1')", (i + 1, f"2026-W{39 + i % 2}", kind, before, after))
    body = logged_in.get(f"{LEXICON}/suggestions").json()
    assert (body["total"], body["first_week"], body["last_week"]) == (7, "2026-W39", "2026-W40")
    found = {(s["kind"], s["before"], s["after"]): s for s in body["suggestions"]}
    zst = found[("text", "Zahn steinentfernung", "Zahnsteinentfernung")]
    assert (zst["count"], zst["takeable"], zst["taken"]) == (4, True, False)
    assert body["suggestions"][0] == zst  # häufigste zuerst
    assert found[("text", "36", "46")]["takeable"] is False  # Ziffern nie
    assert (found[("ziffer", "13b", "13c")]["count"], found[("ziffer", "13b", "13c")]["takeable"]) == (2, False)
    _add(logged_in, "ersetzung", "Zahnsteinentfernung", "Zahn steinentfernung", source="korrektur")
    again = logged_in.get(f"{LEXICON}/suggestions").json()["suggestions"][0]
    assert (again["takeable"], again["taken"]) == (False, True)
    assert logged_in.delete("/api/v1/corrections").status_code == 204
    assert logged_in.get(f"{LEXICON}/suggestions").json() == {
        "suggestions": [], "total": 0, "first_week": None, "last_week": None}
