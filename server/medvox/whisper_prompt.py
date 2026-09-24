"""Whisper-Prompt je Anfrage: Grundtext (Prompt-Datei, fest) plus die aktiven Fachbegriffe aus dem Wörterbuch.

MedVox schickt den Prompt bei jeder Transkription mit (`transcribe.call_whisper`); ein neuer Fachbegriff
wirkt deshalb ab dem nächsten Diktat, ohne Neustart. Die Begriffe stehen hinter dem Grundtext:
„<Grundtext> Keramikinlay, Bulkfill.“

Grenze: whisper.cpp nimmt vom Prompt höchstens `n_text_ctx / 2` Token (`max_prompt_ctx` in
`src/whisper.cpp`), eines davon für das Vorgänger-Zeichen, und schneidet vorne ab – zuerst ginge also
der Anfang des Grundtexts verloren. Nachgemessen am 24.09.2026 mit dem installierten
`ggml-large-v3-turbo.bin` (whisper.cpp-Stand aus `infra/whisper/install.sh`): `n_text_ctx` 448, also
223 Token Text; der Grundtext aus `infra/whisper/prompt.txt` hat 154. Ab dem zweiten 30-s-Fenster einer
Aufnahme teilt sich der Platz mit dem bis dahin erkannten Text – das bestimmt whisper.cpp, nicht MedVox.

Gezählt wird wie in whisper.cpp (`tokenize`): Text nach dessen Regex in Wörter teilen (Buchstaben nur
ASCII, Umlaute zählen wie Satzzeichen), darin jeweils das längste Stück aus dem Vokabular des Modells.
Das Vokabular steht vorne in der Modelldatei (unter 1 MB gelesen). Fehlt die Datei (Entwicklung, CI),
wird vorsichtig geschätzt (`exact` = False): je Wortstück ein Token je angefangene zwei Bytes.
"""

from __future__ import annotations

import logging
import re
import struct
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

log = logging.getLogger("medvox.prompt")

GGML_MAGIC = 0x67676D6C
DEFAULT_TEXT_CTX = 448  # alle Whisper-Modelle
# Regex aus whisper.cpp; [[:alpha:]]/[[:digit:]] im C-Locale = nur ASCII
_SPLIT = re.compile(rb"'s|'t|'re|'ve|'m|'ll|'d| ?[A-Za-z]+| ?[0-9]+| ?[^\sA-Za-z0-9]+|\s+(?!\S)|\s+")


@dataclass(frozen=True)
class Vocab:
    text_ctx: int
    tokens: frozenset[bytes]
    longest: int


@dataclass(frozen=True)
class Budget:
    """Füllstand des Prompts in Token: Grundtext, Ergänzungen, Grenze; `exact` = mit dem Modell gezählt."""

    base: int
    terms: int
    limit: int
    exact: bool


def compose(base: str, terms: list[str]) -> str:
    """Prompt einer Anfrage: Grundtext, dahinter die Begriffe als Aufzählung."""
    return f"{base} {', '.join(terms)}." if terms else base


def _read_vocab(path: Path) -> Vocab:
    with path.open("rb") as fh:
        magic, *hparams = struct.unpack("<I11i", fh.read(48))
        if magic != GGML_MAGIC:
            raise ValueError("keine ggml-Modelldatei")
        n_mel, n_fft = struct.unpack("<2i", fh.read(8))
        fh.seek(4 * n_mel * n_fft, 1)
        (n_vocab,) = struct.unpack("<i", fh.read(4))
        tokens = set()
        for _ in range(n_vocab):
            (length,) = struct.unpack("<I", fh.read(4))
            tokens.add(fh.read(length))
    tokens.discard(b"")
    return Vocab(text_ctx=hparams[5], tokens=frozenset(tokens), longest=max(map(len, tokens)))


@lru_cache(maxsize=2)
def _cached_vocab(path: Path, mtime: float, size: int) -> Vocab | None:
    try:
        return _read_vocab(path)
    except (OSError, ValueError, struct.error, MemoryError) as exc:
        log.warning("Vokabular aus %s nicht lesbar (%s) – Prompt-Länge wird geschätzt", path, type(exc).__name__)
        return None


def load_vocab(path: Path) -> Vocab | None:
    """Vokabular der Modelldatei (zwischengespeichert, bis sich die Datei ändert); None ohne Datei."""
    try:
        stat = path.stat()
    except OSError:
        return None
    return _cached_vocab(path, stat.st_mtime, stat.st_size)


def count_tokens(text: str, vocab: Vocab | None) -> int:
    """Token wie whisper.cpp; ohne Vokabular eine vorsichtige Schätzung (eher zu viel)."""
    pieces = _SPLIT.findall(text.encode("utf-8"))
    if vocab is None:
        return sum(-(-len(p) // 2) for p in pieces)
    count = 0
    for word in pieces:
        i = 0
        while i < len(word):
            j = min(len(word), i + vocab.longest)
            while j > i and word[i:j] not in vocab.tokens:
                j -= 1
            if j > i:
                count += 1
            i = max(j, i + 1)  # unbekanntes Byte: whisper.cpp überspringt es ebenfalls
    return count


def budget(base: str, terms: list[str], model: Path) -> Budget:
    """Füllstand für Grundtext plus Begriffe."""
    vocab = load_vocab(model)
    base_tokens = count_tokens(base, vocab)
    total = count_tokens(compose(base, terms), vocab)
    text_ctx = vocab.text_ctx if vocab else DEFAULT_TEXT_CTX
    return Budget(base=base_tokens, terms=total - base_tokens, limit=text_ctx // 2 - 1, exact=vocab is not None)
