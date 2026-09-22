# MedVox Server – Entwicklungsbefehle (benötigt `uv`, https://docs.astral.sh/uv/)

.PHONY: sync test dev

sync:
	uv sync

test: sync
	uv run pytest

dev: sync
	uv run uvicorn medvox.main:app --host 127.0.0.1 --port 8000 --reload
