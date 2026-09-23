# MedVox Server – Entwicklungsbefehle (benötigt `uv`, https://docs.astral.sh/uv/)

.PHONY: sync test test-integration dev set-password catalog-check catalog-review

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

# Katalog v1 und erweiterten Katalog gegen Schema und Fachregeln prüfen, Review-Tabellen ausgeben
catalog-check: sync
	uv run python -m medvox.catalog.validate
	uv run python -m medvox.catalog.validate --catalog medvox/catalog/catalog_extended.json

# Prüfliste Paare/Zuzahlung (Markdown) aus Katalog v1 neu erzeugen
catalog-review: sync
	uv run python -m medvox.catalog.validate --markdown > medvox/catalog/PRUEFLISTE.md
