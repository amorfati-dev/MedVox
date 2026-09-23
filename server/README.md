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
| `POST /transcribe` | ja | multipart `file` (audio/mp4, audio/webm, audio/wav; ≤ 60 s, ≤ 10 MB), optional `patient_type` = `kasse` (Standard) \| `privat` | `{"transcript", "patient_type", "duration_s", "latency_s", "codes", "suggestions", "planned", "notes"}` – `transcript` ist die Anzeigefassung (lexikon-korrigiert, Zahnnummern als FDI, Codes zusammengefügt, Flächen wie diktiert); `patient_type` der Typ, für den die Vorschläge gelten; `codes` die erbrachten Hauptvorschläge im Kopierformat (`"13c"`, `"2x 41a"`); `suggestions`/`planned` je Vorschlag `code, system, title, points, teeth, count, reason, decide, planned, alternative, kind` mit `kind` = `bema` \| `goz` (Privatleistung, auch GOÄ) \| `zuzahlung` (Privatleistung beim Kassenpatienten); siehe „Regel-Extraktor“. Unbekannter `patient_type`: 422 |
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
`db.py` (SQLite, Aufräumen), `lexicon.py`/`normalize*.py`/`extract*.py` (Text-Pipeline),
`routes_*.py` (HTTP-Schicht), `main.py` (App-Fabrik). Tests in `tests/`, whisper und
ffmpeg dort per `httpx.MockTransport` bzw. Shell-Fake ersetzt.

## Text-Pipeline

Jedes Transkript durchläuft drei reine, unit-getestete Schritte:
**Roh-Transkript → `medvox.lexicon.correct` → `medvox.normalize.normalize` → Extraktor (WP-8).**
Angezeigt und kopiert wird `medvox.normalize_display.display_text` des korrigierten Texts (siehe unten).
`correct` behebt systematische Whisper-Verhörer anhand eines kuratierten Dental-Lexikons
("Artikein" → "Artikain", "Psycho 3" → "PSI 3", "L935d" → "Ä935d") und gibt jede Korrektur
mit ihren Zeichen-Offsets zurück, damit die UI zeigen kann, was geändert wurde; häufige
deutsche Wörter stehen auf einer Whitelist, Codes und Zahlen werden nie angefasst.

`display_text` (`normalize_display.py`) erzeugt daraus den Text, den der Behandler liest und ins PVS
kopiert: dieselbe Zahn- und Code-Normalisierung wie `normalize` („drei sechs“ → 36, „BEMA dreizehn a“
→ BEMA 13a, „Ä neun drei fünf d“ → Ä935d, Zahlwörter → Ziffern), aber Flächen bleiben so, wie sie
diktiert wurden („Zahn 36 mesial okklusal distal“, nicht „mod“). Die interne Form für den Extraktor
ist davon unberührt.

`normalize` erzeugt die maschinenlesbare Form für den Regel-Extraktor: gesprochene Ziffernpaare
und alle Whisper-Schreibweisen werden zu FDI-Nummern ("drei sechs", "3-6", "3,6" → 36;
"1626" → 16, 26; "36-37" und "17 bis 27" sind Bereiche). Gepaart werden nur zwei Einzelziffern;
längere Läufe nur direkt hinter "Zahn"/"Regio" ("Zahn 1 6 2 6" → 16, 26), sodass Messwertreihen
("Sondierungstiefen 3 2 3 2 2 3"), Dosierungsschemata ("1-1-1") und Kommalisten ("1, 6, 2, 6")
unverändert bleiben. Quadrantenangaben werden aufgelöst
("Oberkiefer rechts sechs" → 16), Flächen werden zu Buchstaben ("mesial okklusal distal" →
"mod"; später im Satz folgende Flächen gehören zum Zahn davor, solange kein anderer Zahn
dazwischen steht: "Zahn 36, GOZ 2170, mesial, okklusal" → 36 mo), deutsche Zahlwörter zu Ziffern ("BEMA dreizehn a" → "BEMA 13a", "Ibuprofen
sechshundert" → "Ibuprofen 600"), während Codes ("GOZ 2100", "Ä935d") und Anzahlen ("28 Zähne")
nie als Zähne gelesen werden. Zusätzlich liefert es die strukturierte Liste der Zahnbezüge
(FDI-Nummer plus Flächen). Ausprobieren mit `python -m medvox.normalize --demo` oder
`python -m medvox.normalize "Zahn drei sechs mod Karies"`.

## Regel-Extraktor (WP-8)

`medvox.extract.extract(text, teeth, patient)` ist reine Rechenarbeit (kein Modell, kein I/O) über dem
normalisierten Text und schlägt nur Ziffern aus `catalog/catalog_v1.json` vor; `patient` ist `kasse`
(Standard) oder `privat`. Module: `extract_catalog.py` (Katalog laden, Einheit je Kanal/Zahn/Sitzung,
Paare und Zuzahlungs-Liste, Privat-Gegenstücke aus dem Regeltext), `extract_match.py` (diktierte Ziffern
„BEMA 13a“ zuerst, dann Keywords mit Longest-Match-wins, groß/klein- und umlautunabhängig),
`extract_text.py` (Sätze, Zahngruppen, Plan-Marker, Verneinung, Anzahlen), `extract_patient.py`
(Patiententyp: Fundstellen auf ihr Paar umstellen, Rückfall ohne Paar), `extract_build.py`
(Regelfamilien), `extract_billing.py` (Enthaltensein, „nicht neben“, Zuzahlungs-Angebote, Zuschlag),
`extract_rules.py` (die festen Fachtabellen zum Nachlesen).

- **Füllungen:** die Flächenzahl wählt 13a–d bzw. 2060–2120 je Zahn – ein freistehendes Zählwort
  („dreiflächig“, „Kompositfüllung MOD“, „BEMA 13a“) gilt nur für die Zähne seines Satzes und geht
  vor den am Zahn diktierten Flächen; Flächen direkt am Zahn („37 mod“) gelten nur für diesen Zahn.
  Widerspruch wird markiert. Flächenwörter allein („36 mod Karies“) lösen keine Füllung aus.
- **Ein-/mehrwurzelig** (43/44, AIT a/b, 4050/4055, 4070/4075) aus der FDI-Nummer. Zahnentfernung braucht ein
  Handlungswort (Extraktion, Osteotomie, X1, Ost1); Befundwörter (retiniert, Längsfraktur) wählen nur
  die Ziffer (48 statt 47a, 45 statt 43/44). „Implantat entfernt“ bleibt GOZ 3000 (Implantat, nicht Zahn;
  beim Kassenpatienten nur ein Hinweis, weil keine Kassenleistung).
- **Anzahl:** je Zahn ein Vorschlag pro Zahn, je Kanal mit der diktierten Kanalzahl („3 Kanäle“),
  ohne Zahnangabe „28 Zähne“; Sitzungsleistungen zählen ein wiederholtes Wort („L1, L1“) oder „2x“.
- **Geplant:** „geplant/planen, nächste Sitzung, Termin, Indikation zur, Überweisung, Wiedervorlage,
  in 2 Wochen …“ machen den Teilsatz (mit Doppelpunkt den Rest des Satzes) zum Plan: `planned`,
  nie in `codes`. „ohne/kein/nicht“ direkt an der Leistung verhindert den Vorschlag (Hinweis in `notes`).
- **Patiententyp (Kasse/Privat):** eine diktierte Leistung ist ein Paar aus BEMA- und GOZ/GOÄ-Ziffer
  (Katalogfeld `equivalent`, z. B. Ost1 = BEMA 47a / GOZ 3030); der Patiententyp wählt genau eine davon,
  nie beide. Umgestellt wird schon an der Fundstelle, sodass Flächenzahl, Zahnentfernung und
  ein-/mehrwurzelig im Zielsystem gelten („Osteotomie 38, GOZ 3030“ ergibt eine einzige Position).
  - `kasse`: BEMA-Positionen plus genau die Privatpositionen der Zuzahlungs-Liste (`zuzahlung.allowed`,
    z. B. Mehrkostenfüllung GOZ 2060–2120, PZR 1040, elektrometrische Längenbestimmung 2400), mit
    `kind: "zuzahlung"` und Basis und Grundlage in `reason`. Eine als GOZ diktierte Mehrkosten-Füllung oder
    ein Inlay bringt ihre BEMA-Basis nach Flächenzahl als Kassenanteil mit („adhäsive Kompositfüllung 36
    zweiflächig“ → 13b und 2080, „Keramikinlay 36 dreiflächig“ → 13c und 2170), außer die Basis ist am Zahn
    schon erbracht. Ist die Flächenzahl unbekannt und deckt die GOZ-Ziffer mehrere BEMA-Stufen ab (2170 =
    drei- oder vierflächig), trägt die Basis „Flächenzahl nicht erkannt – 13a–d prüfen“. Das erlaubte Zuzahlungs-Paar einer erbrachten BEMA-Position (Kompositfüllung adhäsiv zu
    13a–d) erscheint zusätzlich als `alternative` (nicht in `codes`). Andere diktierte Privatziffern werden
    auf ihr BEMA-Paar umgestellt („Osteotomie privat“ → 47a) oder mit Hinweis in `notes` weggelassen
    (keine Kassenleistung, z. B. „Implantat entfernt“, Oberflächenanästhesie).
  - `privat`: nur GOZ/GOÄ (`kind: "goz"`); BEMA-Leistungen ohne Privat-Paar (ATG, MHU, BEV) entfallen
    mit Hinweis.
  - Ohne hinterlegtes Paar gilt der Regeltext („Privatpatient: GOZ …“): stehen BEMA und GOZ derselben
    Leistung am selben Zahn nebeneinander, wird die GOZ-Position zur `alternative` und beide tragen
    `decide` („nur eine abrechnen“).
- **Zuschlag 0500–0530:** nur beim Privatpatienten; genau einer je Sitzung, aus der Punktzahl der
  höchstbewerteten erbrachten chirurgischen GOZ-Leistung – „L1, L1, Ost1“ ergibt dort 2x 0100, 3030 und
  0500 (3030 hat 350 Punkte). Die Begründung nennt Ziffer und Punkte. Beim Kassenpatienten wird nie ein
  Zuschlag erwogen; ein diktierter Zuschlag steht dann nur als Hinweis in `notes`. Ist eine Punktzahl
  unbekannt (null), wird keine Stufe geraten, sondern ein Hinweis ausgegeben.

Abnahme: die zwölf Diktate aus Anhang B (`tests/test_extract_acceptance.py`), beim Kassenpatienten auf
Ziffernebene Precision 92 % (24/26), Recall 96 % (24/25); dieselben Diktate beim Privatpatienten stehen
dort als `EXPECTED_PRIVAT`. Die Erwartungen stammen vom selben Autor wie die Regeln
und sind vom Behandler zu prüfen.

### Bekannte Grenzen

- Kontext außerhalb des Katalogs fehlt: „Fluoridierung“ ergibt IP4 und „Mundhygieneinstruktion“ MHU
  auch bei PZR eines Erwachsenen (d05); Alter und PAR-Strecke werden nicht erkannt.
- Keywords müssen in dieser Reihenfolge diktiert werden: „Spülung mit Chlorhexidin“ trifft
  „chlorhexidin spülung“ (BEMA 105) nicht (d12) – Abhilfe über zusätzliche Katalog-Keywords.
- Privatpatient und Füllung: BEMA 13a–d wird auf die Kompositfüllung in Adhäsivtechnik GOZ 2060–2120
  umgestellt, auch bei Glasionomer; die plastische Füllung ohne Adhäsivtechnik (GOZ 2050–2110) steht nur
  im erweiterten Katalog.
- Befundwörter als Keywords: „Karies profunda“ ergibt 25 (Cp), „Längsfraktur“ ergibt 45 (X3) –
  jeweils mit Hinweis zu prüfen; „Füllung intakt“ in einem Befund würde als Füllung gelesen.
- Zahnzuordnung: Zähne direkt hinter der Leistung, sonst die letzte Zahngruppe davor im selben Satz.
  „36 o Karies, 37 mo Karies, Füllungen“ ordnet die Füllung nur 37 zu – Zähne direkt hinter der
  Leistung nennen oder je Zahn einen Satz.
- Fehlt die Flächenzahl, die Kanalzahl oder bei Entfernung/AIT der Zahn, kommt der kleinste
  Vorschlag mit Hinweis in `decide` (die heutige Ergebnisansicht zeigt `decide` noch nicht).
- Plan-Marker wirken nur im eigenen Teilsatz; „danach“ oder Zeitangaben ohne Marker („morgen
  Extraktion“) gelten als erbracht. Verneinung nur direkt an der Leistung.
- Enthaltensein ist nur für 31 in 28 und 11 in 34 hinterlegt; „nicht neben“ aus dem Katalog wird
  markiert, nicht automatisch aufgelöst. Weitere Abrechnungsausschlüsse (Frequenzen, Halbjahr)
  prüft der Extraktor nicht.
- Zuschlag nur für chirurgische GOZ-Positionen im Katalog v1 (3000–3040); 4090/4130 und Implantate
  fehlen im Katalog.
