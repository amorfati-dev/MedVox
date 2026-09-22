# Project agent memory

MedVox: lokale Diktat-Transkription mit BEMA/GOZ-Vorschlägen für eine Zahnarztpraxis.
Drei Teile: `server/` (Python 3.12, FastAPI), `app/` (Vite + React + TypeScript) und `infra/` (bash-Skripte für die launchd-Dienste auf dem Praxis-Mac).
Befehle und Arbeitspakete: `README.md`; Server-Targets: `server/Makefile`; App-Skripte: `app/package.json`; Praxis-Mac: `infra/README.md`.

## Leitplanken

- UI-Texte, Doku, Kommentare und Commit-Beschreibungen auf Deutsch; Code-Bezeichner dürfen englisch sein.
- Jedes Modul (Python-Datei, TS/TSX-Datei) höchstens 300 Zeilen; bei Bedarf aufteilen statt wachsen lassen.
- Minimale Abhängigkeiten: Server nur fastapi, uvicorn, httpx, python-multipart, pydantic (+ pytest); App zur Laufzeit nur react, react-dom, als Dev-Toolchain nur vite, typescript, @vitejs/plugin-react, @types/react, @types/react-dom – nichts weiteres ohne begründeten Anlass. Kein UI-Framework, kein Tailwind. Neue Abhängigkeiten sind eine bewusste Entscheidung des Behandlers. `ffmpeg` ist Systemvoraussetzung des Servers (per subprocess), keine Python-Abhängigkeit.
- Keine Cloud-Dienste, keine externen APIs, keine Telemetrie. Alles läuft im Praxis-LAN auf dem Praxis-Mac.
- BEMA/GOZ/GOÄ-Katalog: `server/medvox/catalog/` (Aufbau, Regeln und Pflege in dessen `README.md`). Einzige Quelle, aus der der Extraktor Ziffern vorschlagen darf; Punktwerte nur aus den amtlichen Quellen, sonst `null` – nie raten.
- Zahnnummern sind zweistellige FDI-Nummern ("36", "16, 26"). Diktiert wird "drei sechs", nie "sechsunddreißig".
- Audio wird nie persistiert: nur temporär bis zur Transkription, danach gelöscht. Keine Patienten-Stammdaten, Logs ohne Transkripttext.
- Der alte Cloud-Prototyp (Google STT + Gemini) ist nur in der Git-Historie vor diesem Neuaufbau; seine BEMA/GOZ-Daten waren fachlich falsch und werden nicht übernommen.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
