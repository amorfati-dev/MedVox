# MedVox

Lokale Diktat-Transkription für die Zahnarztpraxis: Sprache auf dem iPad/iPhone
aufnehmen, auf dem Praxis-Mac transkribieren, BEMA-/GOZ-Positionen vorschlagen
und den Text per Kurzcode/QR an den Rezeptions-PC übergeben – oder je Patient (Evident-Nummer)
sammeln und nach der Runde durch die Zimmer im Büro übertragen (höchstens 24 Stunden gespeichert).
**Kein Byte verlässt das Praxis-LAN**, keine Cloud-Dienste, Audio wird nach der
Transkription gelöscht.

Dieses Repository ist ein kompletter Neuaufbau (Phase 1). Die frühere
Cloud-Prototyp-Version liegt nur noch in der Git-Historie.

## Pakete

| Paket | Technik | Aufgabe |
|---|---|---|
| `server/` | Python 3.12, FastAPI | API auf dem Praxis-Mac: Transkription (whisper.cpp), Normalisierung, Katalog-Regeln, Kurzcode-Transfer, Diktate je Patient |
| `app/` | Vite + React + TypeScript (ohne UI-Framework) | PWA für iPad/iPhone und Rezeptions-Browser |
| `infra/` | Shell + launchd | Installation auf dem Praxis-Mac: whisper-server, Backend, App und LAN-HTTPS (Caddy, eigene CA) – Anleitung in [`infra/README.md`](infra/README.md) |
| `docs/` | Markdown | Abnahmeprotokoll und Diktierhilfe für die Praxis |

## Entwicklung

Server (benötigt [`uv`](https://docs.astral.sh/uv/) und `ffmpeg`; Details in `server/README.md`):

```sh
cd server
make test           # pytest
make dev            # http://127.0.0.1:8000/api/v1/health
make catalog-check  # BEMA/GOZ/GOÄ-Katalog prüfen, Review-Tabelle ausgeben
make catalog-review # Prüfliste Paare/Zuzahlung (catalog/PRUEFLISTE.md) neu erzeugen
```

App (benötigt Node ≥ 22.18; `npm test` führt TypeScript direkt aus):

```sh
cd app
npm install
npm run dev        # http://localhost:5173, /api wird an den Server weitergeleitet
npm run typecheck
npm run build
npm test           # Unit-Tests (node --test)
```

## Praxis-Mac (Betrieb)

Ein Befehl richtet alles ein bzw. zieht nach einem Update nach (Details:
[`infra/README.md`](infra/README.md)):

```sh
make install        # Spracherkennung, Backend, App, HTTPS – endet mit der Adresse für iPad und Rezeption
make set-password   # Behandler-Passwort setzen oder ändern
make status         # eine Zeile je Dienst; Exit-Code ≠ 0 bei jedem echten Problem
make restart-test   # jeden Dienst hart neu starten und die Rückkehr messen
```

Abnahme in der Praxis: [`docs/abnahme.md`](docs/abnahme.md). Wie man diktiert:
[`docs/diktierhilfe.md`](docs/diktierhilfe.md).

## Struktur

Die Arbeitspakete der Phase 1 (Details im Planungsbericht, nicht Teil des Repos):

- WP-0 Grundgerüst (dieses Repository-Skelett)
- WP-1 whisper-server als Praxisdienst
- WP-2 Schlankes Backend-Skelett (`POST /api/v1/transcribe`, Login)
- WP-3 LAN-HTTPS + Zertifikat (mkcert)
- WP-4 PWA-Aufnahme iPad-fest
- WP-5 Normalisierer (Zahnnummern → FDI, Flächen, Zahlwörter)
- WP-6 Fachwörterbuch + Fuzzy-Korrektur
- WP-7 Katalog v1 (BEMA/GOZ, vom Behandler geprüft; siehe `server/medvox/catalog/README.md`)
- WP-8 Regel-Extraktor
- WP-9 iPad-Ergebnisansicht
- WP-10 Kurzcode-Transfer
- WP-11 Datensparsamkeit
- WP-12 Praxis-Installation + Abnahmelauf

Leitplanken für alle Pakete stehen in `AGENTS.md`; iPad-Installation und Testschritte in `app/README.md`.
