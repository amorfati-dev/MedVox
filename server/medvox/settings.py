"""Konfiguration des MedVox-Servers aus Umgebungsvariablen.

Alle Werte haben Voreinstellungen für den Praxis-Mac; siehe server/README.md.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

# Standard-Prompt, falls infra/whisper/prompt.txt (WP-1) nicht vorhanden ist.
FALLBACK_PROMPT = (
    "Zahnarzt-Diktat. Zahn drei sechs mesial okklusal distal, Karies profunda, "
    "Kompositfüllung Adhäsivtechnik, Kofferdam, Infiltrationsanästhesie, "
    "Leitungsanästhesie, PSI, Zahnfilm, OPG, Extraktion, Osteotomie, "
    "Wurzelkanalaufbereitung, Kürettage, UPT, BEMA 13a, GOZ 2100, Ä935d."
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROMPT_FILE = REPO_ROOT / "infra" / "whisper" / "prompt.txt"
DEFAULT_DB_PATH = Path.home() / "Library" / "Application Support" / "MedVox" / "medvox.db"


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} muss eine ganze Zahl sein, nicht {raw!r}") from exc


@dataclass(frozen=True)
class Settings:
    """Laufzeitkonfiguration; `Settings.from_env()` liest die Umgebung."""

    whisper_url: str = "http://127.0.0.1:8178"
    whisper_prompt_file: Path = DEFAULT_PROMPT_FILE
    whisper_timeout_s: float = 60.0
    password_hash: str = ""
    db_path: Path = DEFAULT_DB_PATH
    transfer_ttl_s: int = 15 * 60
    session_ttl_s: int = 30 * 24 * 3600
    ffmpeg: str = "ffmpeg"
    tmp_dir: Path | None = None
    max_upload_bytes: int = 10 * 1024 * 1024
    max_duration_s: float = 60.0
    transfer_lookups_per_min: int = 10

    @classmethod
    def from_env(cls) -> "Settings":
        tmp = os.environ.get("MEDVOX_TMP_DIR")
        return cls(
            whisper_url=os.environ.get("WHISPER_URL", cls.whisper_url).rstrip("/"),
            whisper_prompt_file=Path(
                os.environ.get("WHISPER_PROMPT_FILE", str(DEFAULT_PROMPT_FILE))
            ),
            password_hash=os.environ.get("MEDVOX_PASSWORD_HASH", ""),
            db_path=Path(os.environ.get("MEDVOX_DB_PATH", str(DEFAULT_DB_PATH))),
            transfer_ttl_s=_env_int("MEDVOX_TRANSFER_TTL_S", cls.transfer_ttl_s),
            session_ttl_s=_env_int("MEDVOX_SESSION_TTL_S", cls.session_ttl_s),
            ffmpeg=os.environ.get("MEDVOX_FFMPEG", cls.ffmpeg),
            tmp_dir=Path(tmp) if tmp else None,
        )

    @cached_property
    def whisper_prompt(self) -> str:
        """Inhalt der Prompt-Datei (einmal gelesen), sonst FALLBACK_PROMPT."""
        try:
            text = self.whisper_prompt_file.read_text(encoding="utf-8").strip()
        except OSError:
            text = ""
        return text or FALLBACK_PROMPT
