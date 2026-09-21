# Project agent memory

This file is the project's committed home for project-intrinsic agent knowledge: build, test, release, architecture, and sharp-edge notes that should travel with the code.

- MedVox is being rebuilt from scratch (captain decision, 2026-09-21): local-only dental dictation on a practice Mac, iPad PWA client. `backend/` and `frontend/` are the old cloud prototype and are reference only; nothing from them is reused.
- Practice-Mac services live in `infra/` (German README: `infra/README.md`). Runtime state is outside the repo in `~/Library/Application Support/MedVox/`, `~/Library/LaunchAgents/de.medvox.*.plist`, `~/Library/Logs/MedVox/`.
- Fixed ports: whisper-server `127.0.0.1:8178` (`POST /inference`, multipart `file`, `language=de`, `response_format=json`), backend `127.0.0.1:8000` (WP-2, behind Caddy `/api`), Caddy HTTPS `:443` in the LAN serving `app/dist`.
- The dental Whisper prompt has a single source: `infra/whisper/prompt.txt`; `infra/whisper/install.sh` re-renders the launchd plist from it.
- Never touch OpenSuperWhisper's files (`~/Library/Application Support/ru.starmel.OpenSuperWhisper/`); the model is copied, not linked.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
