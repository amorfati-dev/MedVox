# Project agent memory

MedVox: lokale Diktat-Transkription mit BEMA/GOZ-Vorschlägen für eine Zahnarztpraxis.
Drei Teile: `server/` (Python 3.12, FastAPI), `app/` (Vite + React + TypeScript) und `infra/` (bash-Skripte für die launchd-Dienste auf dem Praxis-Mac).
Befehle und Arbeitspakete: `README.md`; Server-Targets: `server/Makefile`; App-Skripte: `app/package.json`; Praxis-Mac: `infra/README.md`.
Betrieb: `make install` / `make status` im Repo-Root. Die installierten Dienste laufen aus Kopien unter `~/Library/Application Support/MedVox/`, nie aus dem Repo oder einem Worktree – Code-Änderungen wirken dort erst nach erneutem `make install`.

## Leitplanken

- UI-Texte, Doku, Kommentare und Commit-Beschreibungen auf Deutsch; Code-Bezeichner dürfen englisch sein.
- Jedes Modul (Python-Datei, TS/TSX-Datei) höchstens 300 Zeilen; bei Bedarf aufteilen statt wachsen lassen.
- Oberfläche: Farben nur als Tokens in `app/src/styles/tokens.css` (hell/dunkel; Türkis Kasse, Indigo Privat/Zuzahlung, Bernstein prüfen, Rot nur Aufnahme/Fehler), Tippflächen ≥ 64 px (Handschuhe), Querformat ab 900 px zwei Spalten. Aufnahme- und Warteschlangenlogik (`useDictation`, `useUploadQueue`) bleibt von der Anzeige getrennt; der Anzeigezustand wird nur abgeleitet (`app/src/status.ts`).
- Minimale Abhängigkeiten: Server nur fastapi, uvicorn, httpx, python-multipart, pydantic (+ pytest); App zur Laufzeit nur react, react-dom, als Dev-Toolchain nur vite, typescript, @vitejs/plugin-react, @types/react, @types/react-dom – nichts weiteres ohne begründeten Anlass. Kein UI-Framework, kein Tailwind. Neue Abhängigkeiten sind eine bewusste Entscheidung des Behandlers. `ffmpeg` ist Systemvoraussetzung des Servers (per subprocess), keine Python-Abhängigkeit.
- Keine Cloud-Dienste, keine externen APIs, keine Telemetrie. Alles läuft im Praxis-LAN auf dem Praxis-Mac.
- BEMA/GOZ/GOÄ-Katalog: `server/medvox/catalog/` (Aufbau, Regeln und Pflege in dessen `README.md`). Einzige Quelle, aus der der Extraktor Ziffern vorschlagen darf; Punktwerte nur aus den amtlichen Quellen, sonst `null` – nie raten. Höchstzahlen („je Sitzung“, „je Kieferhälfte oder Frontzahnbereich“) stehen maschinenlesbar in `max_per` und begrenzen die Anzahl im Extraktor erst, wenn der Behandler sie bestätigt hat (`max_per_status` „bestaetigt“, sonst „vorschlag“) – Mengenregeln dort pflegen, nicht im Code.
- Patiententyp: eine diktierte Leistung ist ein Paar BEMA/GOZ (`equivalent`, Ost1 = 47a/3030), `kasse` wählt BEMA plus nur Privatpositionen mit `zuzahlung.allowed`, `privat` nur GOZ/GOÄ. Den Zuschlag 0500–0530 gibt es nur bei `privat`. Paare und Zuzahlungs-Liste prüft der Behandler in `catalog/PRUEFLISTE.md` (`make catalog-review`).
- Zahnnummern sind zweistellige FDI-Nummern ("36", "16, 26"). Diktiert wird "drei sechs", nie "sechsunddreißig".
- „Ziffern kopieren" (iPad, Rezeption, Übergabe) liefert das Evident-Format: je Zahn eine Zeile `36,Ä925a,l1,13a`, Positionen ohne Zahn in der letzten Zeile (in der App als „ohne Zahn – in Evident manuell eintragen" markiert) – Evident nimmt Positionen nur hinter einem Zahn an. Kurzformen (`l1`, `wf*3`) nur aus dem Katalogfeld `evident`, das nur vom Behandler bestätigte Formen trägt – nie aus `abbrev` ableiten. Beispiel und Regeln: `docs/diktierhilfe.md`, Code: `evidentLines` in `app/src/api.ts`. Evident setzt nach einer Privatposition alles Folgende auf privat: beim Kassenpatienten erst alle Kassenzeilen, Leerzeile, dann alle Privatpositionen (`evidentBlocks`). Zuzahlungs-Optionen (`alternative`, Kasse) kommen nur nach Antippen dazu (`copyLines` in `app/src/result.ts`); jede Änderung am Kopierformat zeigt `app/test/evident-golden.test.ts`.
- Audio wird nie persistiert: nur temporär bis zur Transkription, danach gelöscht. Keine Patienten-Stammdaten, Logs ohne Transkripttext.
- Der alte Cloud-Prototyp (Google STT + Gemini) ist nur in der Git-Historie vor diesem Neuaufbau; seine BEMA/GOZ-Daten waren fachlich falsch und werden nicht übernommen.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
