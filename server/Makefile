# MedVox Server – Entwicklungsbefehle (benötigt `uv`, https://docs.astral.sh/uv/)

.PHONY: sync test test-integration dev set-password

sync:
	uv sync

test: sync
	uv run pytest

# Gegen den echten whisper-server (WHISPER_URL) und ffmpeg; braucht macOS `say`.
test-integration: sync
	uv run pytest -m integration -s

dev: sync
	uv run uvicorn medvox.main:app --host 127.0.0.1 --port 8000 --reload

# Fragt ein Passwort ab und gibt den Wert für MEDVOX_PASSWORD_HASH aus.
set-password: sync
	uv run python -m medvox.auth
