# MedVox Server

FastAPI-Dienst auf dem Praxis-Mac: nimmt Aufnahmen vom iPad entgegen, wandelt sie
mit ffmpeg in 16-kHz-WAV, lässt sie vom lokalen whisper-server (WP-1) transkribieren
und übergibt Transkripte per Kurzcode an den Rezeptions-PC. Audio liegt nur bis zur
Antwort des whisper-servers als temporäre Datei vor und wird danach immer gelöscht;
Logs enthalten weder Audio noch Transkripttext. Abgelaufene Kurzcodes und Sitzungen
werden bei jedem Zugriff, beim Start und alle 5 Minuten aus der SQLite-Datei entfernt
(`secure_delete`, gelöschte Zeilen werden überschrieben).

## Voraussetzungen

- Python ≥ 3.12 und [`uv`](https://docs.astral.sh/uv/)
- `ffmpeg` im PATH (`brew install ffmpeg`) – Systemvoraussetzung, keine Python-Abhängigkeit
- laufender whisper-server (siehe `infra/whisper/`), Standard `http://127.0.0.1:8178`

## Befehle

```sh
make test              # pytest (whisper-server und ffmpeg werden gemockt)
make test-integration  # echter whisper-server + ffmpeg + macOS `say`
make set-password      # Passwort abfragen, MEDVOX_PASSWORD_HASH ausgeben
make dev               # uvicorn auf http://127.0.0.1:8000 mit Reload
```

Vor `make dev` den Hash aus `make set-password` in die Umgebung übernehmen,
z. B. `export MEDVOX_PASSWORD_HASH='pbkdf2_sha256$...'`; ohne ihn antwortet
`/api/v1/login` mit 503.

## Umgebungsvariablen

| Variable | Standard | Bedeutung |
|---|---|---|
| `WHISPER_URL` | `http://127.0.0.1:8178` | Adresse des whisper-servers |
| `WHISPER_PROMPT_FILE` | `<repo>/infra/whisper/prompt.txt` | Diktat-Prompt für whisper; fehlt die Datei, gilt `FALLBACK_PROMPT` aus `medvox/settings.py` (Übergang bis WP-1, der Server warnt beim Start im Log) |
| `MEDVOX_PASSWORD_HASH` | – (Pflicht) | PBKDF2-Hash des Behandler-Passworts (`make set-password`) |
| `MEDVOX_DB_PATH` | `~/Library/Application Support/MedVox/medvox.db` | SQLite mit Sitzungen und Transfer-Codes |
| `MEDVOX_TRANSFER_TTL_S` | `900` | Lebensdauer eines Kurzcodes (15 min) |
| `MEDVOX_SESSION_TTL_S` | `2592000` | Lebensdauer der Login-Sitzung (30 Tage) |
| `MEDVOX_FFMPEG` | `ffmpeg` | Pfad zum ffmpeg-Binary |
| `MEDVOX_TMP_DIR` | System-Temp | Verzeichnis für die kurzlebigen Audio-Dateien |

Feste Grenzen (`medvox/settings.py`): Upload ≤ 10 MB, Aufnahme ≤ 60 s,
Transfer-Abrufe und Login-Versuche je ≤ 10 pro Minute und IP. Die Client-IP stammt
aus `X-Forwarded-For`, wenn die Verbindung vom lokalen Reverse-Proxy (Caddy, WP-3)
kommt, sonst direkt vom Peer.

## API (`/api/v1`)

| Methode, Pfad | Login | Anfrage | Antwort |
|---|---|---|---|
| `GET /health` | nein | – | `{"status":"ok","whisper":"ok"\|"down"}` – echter Probe-Aufruf des whisper-servers, 1 s Timeout |
| `POST /login` | nein | JSON `{"password": "…"}` | 204 + HttpOnly-Cookie `medvox_session` (SameSite=Strict); 401 falsches Passwort, 429 bei > 10 Versuchen/min/IP, 503 kein Hash konfiguriert |
| `POST /logout` | – | – | 204, Cookie gelöscht |
| `GET /session` | ja | – | 200 `{"status":"ok"}` oder 401 |
| `POST /transcribe` | ja | multipart `file` (audio/mp4, audio/webm, audio/wav; ≤ 60 s, ≤ 10 MB) | `{"transcript", "duration_s", "latency_s", "codes": []}` – `codes` füllt erst der Regel-Extraktor (WP-8) |
| `POST /transfer` | ja | JSON `{"transcript": str, "codes": [str]}` | `{"code": "ABC123", "expires_at": iso8601}` |
| `GET /transfer/{code}` | nein | – | `{"transcript", "codes", "created_at"}` oder 404; 429 bei > 10 Abrufen/min/IP |

Fehler tragen eine deutsche Meldung in `{"detail": "…"}`: 400 unlesbare oder leere
Aufnahme, 401 nicht angemeldet, 413 zu groß oder zu lang, 415 falscher Typ,
500 ffmpeg fehlt oder Konvertierung zu langsam, 502 whisper-server meldet Fehler,
503 whisper-server nicht erreichbar.
Kurzcodes bestehen aus 6 Zeichen ohne 0/O/1/I und sind innerhalb der TTL mehrfach abrufbar.

## Module

`medvox/settings.py` (Umgebung), `transcribe.py` (ffmpeg → whisper, Temp-Dateien),
`auth.py` (PBKDF2, Sitzungen), `transfer.py` (Kurzcodes), `ratelimit.py` (Client-IP, Fenster),
`db.py` (SQLite, Aufräumen),
`routes_*.py` (HTTP-Schicht), `main.py` (App-Fabrik). Tests in `tests/`, whisper und
ffmpeg dort per `httpx.MockTransport` bzw. Shell-Fake ersetzt.

## Text-Pipeline

Jedes Transkript durchläuft drei reine, unit-getestete Schritte:
**Roh-Transkript → `medvox.lexicon.correct` → `medvox.normalize.normalize` → Extraktor (WP-8).**
`correct` behebt systematische Whisper-Verhörer anhand eines kuratierten Dental-Lexikons
("Artikein" → "Artikain", "Psycho 3" → "PSI 3", "L935d" → "Ä935d") und gibt jede Korrektur
mit ihren Zeichen-Offsets zurück, damit die UI zeigen kann, was geändert wurde; häufige
deutsche Wörter stehen auf einer Whitelist, Codes und Zahlen werden nie angefasst. Der
korrigierte Text ist das, was der Behandler liest und ins PVS kopiert.

`normalize` erzeugt die maschinenlesbare Form für den Regel-Extraktor: gesprochene Ziffernpaare
und alle Whisper-Schreibweisen werden zu FDI-Nummern ("drei sechs", "3-6", "3,6" → 36;
"1626" → 16, 26; "36-37" und "17 bis 27" sind Bereiche). Gepaart werden nur zwei Einzelziffern;
längere Läufe nur direkt hinter "Zahn"/"Regio" ("Zahn 1 6 2 6" → 16, 26), sodass Messwertreihen
("Sondierungstiefen 3 2 3 2 2 3"), Dosierungsschemata ("1-1-1") und Kommalisten ("1, 6, 2, 6")
unverändert bleiben. Quadrantenangaben werden aufgelöst
("Oberkiefer rechts sechs" → 16), Flächen werden zu Buchstaben ("mesial okklusal distal" →
"mod"), deutsche Zahlwörter zu Ziffern ("BEMA dreizehn a" → "BEMA 13a", "Ibuprofen
sechshundert" → "Ibuprofen 600"), während Codes ("GOZ 2100", "Ä935d") und Anzahlen ("28 Zähne")
nie als Zähne gelesen werden. Zusätzlich liefert es die strukturierte Liste der Zahnbezüge
(FDI-Nummer plus Flächen). Ausprobieren mit `python -m medvox.normalize --demo` oder
`python -m medvox.normalize "Zahn drei sechs mod Karies"`.
