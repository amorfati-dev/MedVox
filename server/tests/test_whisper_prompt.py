"""Prompt je Anfrage (Grundtext + Fachbegriffe) und Token-Zählung wie whisper.cpp."""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

from medvox.settings import DEFAULT_MODEL_FILE
from medvox.whisper_prompt import GGML_MAGIC, budget, compose, count_tokens, load_vocab

BASE_FILE = Path(__file__).resolve().parents[2] / "infra" / "whisper" / "prompt.txt"


def fake_model(path: Path, tokens: list[bytes], text_ctx: int = 448) -> Path:
    """Kopf einer ggml-Modelldatei: Magic, 11 hparams, Mel-Filter (2×3), Vokabular."""
    hparams = [len(tokens), 1500, 1280, 20, 32, text_ctx, 1280, 20, 4, 128, 1]
    data = struct.pack("<I11i", GGML_MAGIC, *hparams) + struct.pack("<2i", 2, 3) + b"\0" * 24
    data += struct.pack("<i", len(tokens)) + b"".join(struct.pack("<I", len(t)) + t for t in tokens)
    path.write_bytes(data + b"Gewichte folgen")
    return path


def test_compose_appends_terms_behind_the_base_text() -> None:
    assert compose("Zahnarzt-Diktat.", []) == "Zahnarzt-Diktat."
    assert compose("Zahnarzt-Diktat.", ["Keramikinlay", "Bulkfill"]) == "Zahnarzt-Diktat. Keramikinlay, Bulkfill."


def test_tokens_are_the_longest_known_pieces_per_word(tmp_path: Path) -> None:
    vocab = load_vocab(fake_model(tmp_path / "m.bin", [b"Zahn", b"arzt", b" Zahn", b"-", b"D", b"ik", b"tat", b".",
                                                       b"\xc3\xa4", b" K", b"Zahnarzt"]))
    assert vocab is not None and vocab.text_ctx == 448
    assert count_tokens("Zahnarzt", vocab) == 1
    assert count_tokens("Zahnarzt-Diktat.", vocab) == 6  # Zahnarzt - D ik tat .
    assert count_tokens(" Zahn", vocab) == 1
    assert count_tokens(" Kä", vocab) == 2  # Umlaute zählen wie Satzzeichen: eigenes Wortstück
    assert count_tokens("q", vocab) == 0  # unbekanntes Byte: auch whisper.cpp überspringt es


def test_without_model_the_count_is_an_overestimate(tmp_path: Path) -> None:
    assert load_vocab(tmp_path / "fehlt.bin") is None
    assert load_vocab(tmp_path) is None  # ein Verzeichnis ist keine Modelldatei
    assert count_tokens("Zahnarzt-Diktat.", None) == 9  # je angefangene 2 Bytes: 4 + 1 + 3 + 1
    assert count_tokens(", Adhäsiv", None) >= 6  # mit dem Modell 6
    room = budget("Zahnarzt-Diktat.", ["Keramikinlay"], tmp_path / "fehlt.bin")
    assert (room.limit, room.exact) == (223, False)


def test_budget_counts_base_and_terms_separately(tmp_path: Path) -> None:
    model = fake_model(tmp_path / "m.bin", [b"Zahn", b".", b" Inlay", b",", b" Bulk", b"fill"], text_ctx=100)
    room = budget("Zahn.", ["Inlay", "Bulkfill"], model)
    assert (room.base, room.terms, room.limit, room.exact) == (2, 5, 49, True)  # „ Inlay“ „,“ „ Bulk“ „fill“ „.“


@pytest.mark.skipif(not DEFAULT_MODEL_FILE.is_file(), reason="nur auf dem Praxis-Mac mit installiertem Modell")
def test_measured_with_the_installed_model() -> None:
    """Nachgemessen mit whisper.cpp selbst (whisper_tokenize, whisper_model_n_text_ctx) am 24.09.2026."""
    vocab = load_vocab(DEFAULT_MODEL_FILE)
    assert vocab is not None and vocab.text_ctx == 448
    assert count_tokens("Zahnarzt-Diktat.", vocab) == 9
    assert count_tokens(", Keramikinlay", vocab) == 5
    assert count_tokens(", Wurzelstiftaufbau", vocab) == 8
    assert count_tokens(", Adhäsiv", vocab) == 6
    if BASE_FILE.read_text(encoding="utf-8").strip().startswith("Zahnarzt-Diktat. Zahn drei sechs"):
        assert budget(BASE_FILE.read_text(encoding="utf-8").strip(), [], DEFAULT_MODEL_FILE).base == 154
