# MedVox

Lokale Diktat-Transkription für die Zahnarztpraxis: Sprache auf dem iPad/iPhone
aufnehmen, auf dem Praxis-Mac transkribieren, BEMA-/GOZ-Positionen vorschlagen
und den Text per Kurzcode/QR an den Rezeptions-PC übergeben.
**Kein Byte verlässt das Praxis-LAN**, keine Cloud-Dienste, Audio wird nach der
Transkription gelöscht.

Dieses Repository ist ein kompletter Neuaufbau (Phase 1). Die frühere
Cloud-Prototyp-Version liegt nur noch in der Git-Historie.

## Pakete

| Paket | Technik | Aufgabe |
|---|---|---|
| `server/` | Python 3.12, FastAPI | API auf dem Praxis-Mac: Transkription (whisper.cpp), Normalisierung, Katalog-Regeln, Kurzcode-Transfer |
| `app/` | Vite + React + TypeScript (ohne UI-Framework) | PWA für iPad/iPhone und Rezeptions-Browser |
| `infra/` | Shell + launchd | Dienste auf dem Praxis-Mac: whisper-server und LAN-HTTPS (Caddy, eigene CA) – Anleitung in [`infra/README.md`](infra/README.md) |

## Entwicklung

Server (benötigt [`uv`](https://docs.astral.sh/uv/) und `ffmpeg`; Details in `server/README.md`):

```sh
cd server
make test   # pytest
make dev    # http://127.0.0.1:8000/api/v1/health
```

App (benötigt Node ≥ 22.12 (oder 20.19+)):

```sh
cd app
npm install
npm run dev        # http://localhost:5173, /api wird an den Server weitergeleitet
npm run typecheck
npm run build
```

Praxis-Mac einrichten (whisper-server, LAN-HTTPS): siehe [`infra/README.md`](infra/README.md).

```sh
infra/whisper/install.sh   # Spracherkennung als launchd-Dienst (WP-1)
infra/tls/setup.sh         # Praxis-CA, Zertifikat, Caddy auf 443 (WP-3)
```

## Struktur

Die Arbeitspakete der Phase 1 (Details im Planungsbericht, nicht Teil des Repos):

- WP-0 Grundgerüst (dieses Repository-Skelett)
- WP-1 whisper-server als Praxisdienst
- WP-2 Schlankes Backend-Skelett (`POST /api/v1/transcribe`, Login)
- WP-3 LAN-HTTPS + Zertifikat (mkcert)
- WP-4 PWA-Aufnahme iPad-fest
- WP-5 Normalisierer (Zahnnummern → FDI, Flächen, Zahlwörter)
- WP-6 Fachwörterbuch + Fuzzy-Korrektur
- WP-7 Katalog v1 (BEMA/GOZ, vom Behandler geprüft)
- WP-8 Regel-Extraktor
- WP-9 iPad-Ergebnisansicht
- WP-10 Kurzcode-Transfer
- WP-11 Datensparsamkeit
- WP-12 Praxis-Installation + Abnahmelauf

Leitplanken für alle Pakete stehen in `AGENTS.md`.
