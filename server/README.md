# MedVox Server

FastAPI-Dienst auf dem Praxis-Mac: nimmt Aufnahmen vom iPad entgegen, wandelt sie
mit ffmpeg in 16-kHz-WAV, lässt sie vom lokalen whisper-server (WP-1) transkribieren
und übergibt Transkripte per Kurzcode an den Rezeptions-PC oder speichert sie je Patient
(Evident-Nummer) für die spätere Übertragung im Büro. Audio liegt nur bis zur
Antwort des whisper-servers als temporäre Datei vor und wird danach immer gelöscht;
Logs enthalten weder Audio noch Transkripttext oder Patientennummern. Diktate je Patient
bleiben, bis sie als übertragen markiert sind, höchstens 24 Stunden nach ihrer Anlage
(`medvox/patients.py`, fest, nicht per Umgebung verlängerbar). Abgelaufene Kurzcodes,
Sitzungen und Patientendiktate werden bei jedem Zugriff, beim Start und alle 5 Minuten aus
der SQLite-Datei entfernt (`secure_delete`, gelöschte Zeilen werden überschrieben).
Ein übertragenes, gelöschtes oder abgelaufenes Diktat hinterlässt einen Grabstein
(`dictation_tombstones`: nur Diktat-ID und Zeitpunkt, kein Inhalt, keine Patientennummer), der
sieben Tage bleibt; solange lehnt `PUT /dictations/{id}` diese ID mit 410 ab, damit ein iPad ein
schon übertragenes Diktat nie wieder offen anlegt.

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
| `WHISPER_PROMPT_FILE` | `<repo>/infra/whisper/prompt.txt` | Grundtext des Diktat-Prompts für whisper (dahinter je Anfrage die Fachbegriffe aus dem Wörterbuch); fehlt die Datei, gilt `FALLBACK_PROMPT` aus `medvox/settings.py` (Übergang bis WP-1, der Server warnt beim Start im Log) |
| `WHISPER_MODEL` | `~/Library/Application Support/MedVox/models/ggml-large-v3-turbo.bin` | Nur zum Zählen der Prompt-Token (Vokabular vorne in der Datei, `medvox/whisper_prompt.py`); fehlt sie, wird vorsichtig geschätzt |
| `MEDVOX_PASSWORD_HASH` | – (Pflicht) | PBKDF2-Hash des Behandler-Passworts (`make set-password`) |
| `MEDVOX_DB_PATH` | `~/Library/Application Support/MedVox/medvox.db` | SQLite mit Sitzungen und Transfer-Codes |
| `MEDVOX_TRANSFER_TTL_S` | `900` | Lebensdauer eines Kurzcodes (15 min) |
| `MEDVOX_SESSION_TTL_S` | `2592000` | Lebensdauer der Login-Sitzung (30 Tage) |
| `MEDVOX_DENTIST_IDLE_S` | `1800` | So lange ohne Bedienung, dann fragt das iPad neu, wer diktiert (30 min) |
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
| `POST /transcribe` | ja | multipart `file` (audio/mp4, audio/webm, audio/wav; ≤ 60 s, ≤ 10 MB), optional `patient_type` = `kasse` (Standard) \| `privat` | `{"transcript", "patient_type", "duration_s", "latency_s", "codes", "suggestions", "planned", "notes"}` – `transcript` ist die Anzeigefassung (lexikon-korrigiert, Zahnnummern als FDI, Codes zusammengefügt, Flächen wie diktiert); `patient_type` der Typ, für den die Vorschläge gelten; `codes` die erbrachten Hauptvorschläge im Kopierformat (`"13c"`, `"2x 41a"`); `suggestions`/`planned` je Vorschlag `code, system, title, points, teeth, count, reason, decide, planned, alternative, kind, evident, source` (Evident-Kurzform aus dem Katalog oder `null`; `source` = `regel`, am iPad `hand` bzw. `geaendert`) mit `kind` = `bema` \| `goz` (Privatleistung, auch GOÄ) \| `zuzahlung` (Privatleistung beim Kassenpatienten); siehe „Regel-Extraktor“. Unbekannter `patient_type`: 422 |
| `POST /analyze` | ja | JSON `{"text": str, "patient_type"?: "kasse"\|"privat", "draft"?: {"wrong", "right"}}` – am iPad berichtigter Text aller Abschnitte (≤ 50 000 Zeichen); `draft` = Probe auf der Wörterbuch-Seite: eine noch nicht gespeicherte Ersetzung nur für diese Anfrage | wie `/transcribe` (`duration_s`/`latency_s` = 0): dieselbe Kette ohne Audio, mit den eingeschalteten Ersetzungen des Wörterbuchs (und `draft`); für das angezeigte, unveränderte Transkript ergeben sich dieselben Ziffern (Fixpunkt, `tests/test_correction_routes.py`); `draft` verletzt eine Schutzregel: 422 mit Begründung; Log nur Anzahlen |
| `GET /catalog?patient_type=kasse\|privat` | ja | – | `{"version", "patient_type", "entries": [{code, system, title, area, points, kind, evident, family, counted, max_count}]}` – Positionen aus `catalog_v1.json`, die für den Patiententyp vorgeschlagen werden dürfen (wie der Extraktor: Kasse = BEMA inkl. Analogpositionen plus Zuzahlungs-Liste, Privat = GOZ/GOÄ, Zuschlag 0500–0530 nur Privat); `family` = Ziffern nach Flächenzahl 1–4 (13a–13d) oder leer. `counted` = Anzahl am iPad mit − / + änderbar (je Kanal oder laut bestätigtem `max_per` mehrmals je Sitzung, `Catalog.stepper`), `max_count` = bestätigte Höchstzahl dafür oder `null`. Für das Katalog-Blatt am iPad, keine freie Ziffern-Eingabe |
| `POST /transfer` | ja | JSON `{"transcript": str, "codes": [str], "patient_type"?: "kasse"\|"privat", "positions"?: [{"tooth": int\|null, "code": str, "kind": "bema"\|"goz"\|"zuzahlung"\|"kassenanteil"}], "dictation_id"?: str, "dictation_revision"?: int, "dentist_id"?: int}` – die App schickt als `codes` die Evident-Zeilen, eine je Zahn (`"36,Ä925a,l1,13a"`, letzte Zeile ohne Zahn); `patient_type` und `positions` sind nur zur Anzeige an der Rezeption (Zuzahlung, Kassenanteil); `dictation_id`/`dictation_revision` verknüpfen den Code mit genau diesem Stand des gespeicherten Diktats (siehe unten); der Behandler ist der des gespeicherten Diktats, sonst `dentist_id` | `{"code": "ABC123", "expires_at": iso8601}` |
| `GET /transfer/{code}` | nein | – | `{"transcript", "codes", "created_at", "patient_type", "positions", "earlier", "dentist_name"}` (ältere Einträge: `null`/`[]`; `earlier` = schon abgeholte Stände desselben Diktats) oder 404; 410 ohne Inhalt, wenn das verknüpfte Diktat schon übertragen ist (Code danach gelöscht); 429 bei > 10 Abrufen/min/IP |
| `PUT /dictations/{id}` | ja | JSON `{"patient"?: "4711", "patient_label"?: "M.K.", "dentist_id"?: 3, "transcript", "patient_type", "codes", "suggestions", "planned", "notes", "deselected", "adopted", "original"?}` – Stand eines Diktats, `id` vom iPad (8–64 Zeichen `A-Za-z0-9-`); `patient` = Evident-Nummer (1–12 Ziffern, Patient wird bei Bedarf angelegt), ohne `patient` bleibt die Zuordnung (neu: „ohne Patient“); ein schon zugeordnetes Diktat wechselt durch `patient` nie den Patienten (Umhängen nur im Büro); `dentist_id` (Behandler beim Start der Aufnahme) zählt nur beim ersten Speichern und ändert sich danach nie, unbekannte ID = ohne Behandler; `patient_label` = Kürzel des Patienten (Initialen: höchstens 4 Buchstaben, höchstens 2 direkt hintereinander, getrennt durch Punkt, Leerzeichen oder Bindestrich; leer = vorhandenes behalten, sonst 422 ohne Echo); `original` = `{"transcript", "codes", "positions": [{"tooth", "code", "count"}]}` nur bei einer Korrektur am iPad: der Stand davor, lebt wie das Diktat (Büro zeigt „am iPad korrigiert“ und das Original; beim Übertragen oder Ablauf bleiben nur die geänderten Stellen, siehe „Korrektur-Sammlung“) | Diktat mit `id, patient, patient_label, patient_id, revision, created_at, updated_at, dentist_id, dentist_name` und den Feldern der Anfrage; jede Änderung erhöht `revision`, die 24 Stunden zählen ab der ersten Speicherung; 410, wenn das Diktat schon übertragen, gelöscht oder abgelaufen ist |
| `DELETE /dictations/{id}` | ja | – | 204 oder 404 |
| `PUT /dictations/{id}/dentist` | ja | JSON `{"dentist_id": 3}` | Behandler eines Diktats ohne Behandler nachtragen (Büro, „Behandler fehlt“); der Patient bekommt ihn als Eröffner, falls er noch keinen hat. Das Diktat; 409, wenn es schon einen Behandler hat (bleibt unverändert); 404, wenn Diktat oder Behandler fehlen |
| `POST /patients` | ja | JSON `{"number": "4711"}` | Patient `{id, number, label, created_at, updated_at, dictations, transferred, transferred_at, dentist_id, dentist_name, dentists, without_dentist}` – vorhandener mit derselben Nummer oder neu; `label` = Kürzel, solange etwas offen ist; `dentist_*` = Behandler des ersten Diktats (hat den Patienten eröffnet), `dentists` = er und die Behandler der offenen Diktate (`[{id, name}]`), `without_dentist` = offene Diktate ohne Behandler |
| `GET /patients` | ja | – | `{"patients": [...], "unassigned": [Diktat, ...]}` – jüngstes Diktat zuerst; `dictations` offen, `transferred` schon übertragen |
| `GET /patients/{id}` | ja | – | Patient plus `items`: offene Diktate in Diktatreihenfolge; 404 |
| `POST /patients/{id}/dictations` | ja | JSON `{"dictation_id": "…", "label"?: "M.K."}` | hängt ein gespeichertes Diktat (z. B. „ohne Patient“) an diesen Patienten und setzt dabei das Kürzel (wie bei `PUT /dictations/{id}`; leer = vorhandenes behalten); 404 |
| `POST /patients/{id}/transferred` | ja | JSON `{"seen": [{"id", "revision"}]}` – die im Büro angezeigten Diktate | löscht genau diese Fassungen sofort und vermerkt Zeit und Anzahl; neuere oder geänderte bleiben in `items` offen |
| `DELETE /patients/{id}` | ja | – | 204 (mit allen Diktaten) oder 404 |
| `GET /events` | ja | – | Live-Strom des Büros (Server-Sent Events, `medvox/events.py`): sofort `event: changed` mit der aktuellen Versionsnummer, danach bei jeder Änderung an der Datenbank (Diktat gespeichert, zugeordnet, übertragen, gelöscht, abgelaufen, Kurzcode abgeholt, Behandler) erneut, sonst alle 15 s `event: ping`. `data` ist nur die Versionsnummer – nie Transkript, Ziffern, Nummer oder Kürzel; die Seite lädt über `GET /patients` neu. Endet bei Abmeldung (nächster `ping`) und nach 10 Minuten (der Browser verbindet sich neu) |
| `GET /dentists` | ja | – | `{"dentists": [{id, name, practitioner_id, active}], "idle_s": 1800}` – aktive zuerst; `idle_s` aus `MEDVOX_DENTIST_IDLE_S` |
| `POST /dentists` | ja | JSON `{"name": "Dr. Hartmann", "practitioner_id"?: "12"}` (Name 1–60 Zeichen, Nummer ≤ 20 Zeichen `A-Za-z0-9./-`) | der neue Behandler |
| `PATCH /dentists/{id}` | ja | JSON mit beliebigen von `name`, `practitioner_id` (leer = keine), `active` | der geänderte Behandler; 404 |
| `DELETE /dentists/{id}` | ja | – | inaktiv setzen (nie löschen): der Behandler mit `active: false`; 404 |
| `GET /lexicon` | ja | – | `{"entries": [{id, kind, wrong, right, active, source, created_at}], "builtin": [{wrong, right}], "prompt": {base, base_tokens, terms_tokens, limit, exact}}` – Wörterbuch der Praxis (`kind` = `ersetzung` \| `begriff`, `source` = `hand` \| `korrektur`), eingeschaltete zuerst; `builtin` = die dreizehn eingebauten Ersetzungen (nur lesen); `prompt` = Grundtext und Füllstand in Token (`limit` 223 bei allen Whisper-Modellen, `exact` = mit dem Modell-Vokabular gezählt) |
| `POST /lexicon` | ja | JSON `{"kind": "ersetzung"\|"begriff", "wrong"?: str, "right": str, "source"?: "hand"\|"korrektur"}` | der neue, eingeschaltete Eintrag – gilt ab der nächsten Anfrage (kein Neustart); Schutzregel verletzt (Ziffer/Zahlwort, Allerweltswort allein, eingebaute Ersetzung oder eingebauter Fachbegriff, schon vorhanden, Prompt voll): 422 mit Begründung |
| `PUT /lexicon/{id}` | ja | JSON `{"active": bool}` | ab- oder wieder einschalten (nie löschen; beim Einschalten gelten die Schutzregeln erneut); 404, 422 |
| `GET /lexicon/suggestions` | ja | – | `{"suggestions": [{kind, before, after, count, takeable, taken}], "total", "first_week", "last_week"}` – gleiche Änderungen aus der Korrektur-Sammlung gezählt (Textstellen ohne gemeinsames Umfeld), häufigste zuerst, höchstens 30; `takeable` nur für Textpaare, die die Schutzregeln bestehen; Ziffernänderungen sind nur Information |
| `DELETE /corrections` | ja | – | 204 – „Alle löschen“: die ganze Korrektur-Sammlung, sofort |

Fehler tragen eine deutsche Meldung in `{"detail": "…"}`: 400 unlesbare oder leere
Aufnahme, 401 nicht angemeldet, 413 zu groß oder zu lang, 415 falscher Typ,
500 ffmpeg fehlt oder Konvertierung zu langsam, 502 whisper-server meldet Fehler,
503 whisper-server nicht erreichbar.
Kurzcodes bestehen aus 6 Zeichen ohne 0/O/1/I und sind innerhalb der TTL mehrfach abrufbar.

Kurzcode und Patientenliste sind nie zwei Wege zu demselben Diktat – genau ein Stand wird genau
einmal übergeben. Beim Anlegen schickt das iPad die ID des gespeicherten Diktats als `dictation_id`
und die Revision genau dieses Inhalts als `dictation_revision` mit (fehlt, solange das Speichern
noch läuft). Beides steht in den Spalten `transfers.dictation_id` und `transfers.dictation_revision`
(bestehende Datenbanken bekommen sie beim Start per `ALTER TABLE`, wie `patient_type` und
`positions_json`); `transfers.handed_over_at` merkt sich den ersten Abruf. Jeder erste Abruf
eines verknüpften Codes wird in `handovers` festgehalten (Diktat-ID, Code, Revision, Zeitpunkt und
die übergebenen Evident-Zeilen – kein Transkript, keine Patientennummer, `medvox/handovers.py`); die
Zeilen bleiben, solange das Diktat offen ist oder sein Grabstein liegt, und gehen mit ihm. Der erste Abruf
`GET /transfer/{code}`:

- Diktat unverändert (Revision wie beim letzten Speichern vom iPad, Spalte `dictations.saved_revision`;
  Zuordnen im Büro und Abhol-Vermerke zählen nicht als Änderung): geschlossen wie „übertragen“ im Büro – Inhalt gelöscht,
  Grabstein gesetzt, beim Patienten Zeit und Anzahl vermerkt.
- Diktat danach geändert (oder beim Anlegen noch nicht gespeichert): der Code liefert seinen Stand,
  das Diktat bleibt offen und speicherbar und bekommt eine neue Revision; im Büro trägt es die
  Abholung (`handovers`: Zeit und damals übergebene Zeilen) und die App zeigt, was seitdem neu ist.
- Hatte das Diktat schon eine Abholung (z. B. Code A vor der Korrektur, jetzt Code B), liefert der
  Abruf zusätzlich `earlier: [{"fetched_at", "codes"}]`; die Rezeption sieht vor den Ziffern, was
  schon übergeben wurde und welche Positionen neu sind, und trägt nur diese ein.
- Diktat noch gar nicht gespeichert: Grabstein, das spätere Speichern bekommt 410.
- Diktat schon übertragen, gelöscht oder abgelaufen (Grabstein, z. B. im Büro oder durch einen
  anderen Kurzcode): 410 mit Zeitpunkt („… bereits am … übertragen … – nicht erneut in Evident
  eintragen“), ohne Transkript und Ziffern; der Code wird gelöscht (danach 404).

Weitere Abrufe desselben Codes innerhalb der TTL liefern den Inhalt erneut, ohne etwas zu schließen.
Wird der Code nie abgerufen, bleibt das Diktat offen und läuft normal ab. Ohne `dictation_id`
(ältere iPad-Versionen) bleibt alles wie bisher.

Behandler (`medvox/dentists.py`, Tabelle `dentists`): nur Zuordnung für Abrechnung und
Nachvollziehbarkeit, keine Anmeldung und keine Rechte – jeder Angemeldete sieht alle Patienten und
darf die Liste pflegen. Ist die Liste leer – bei einer neuen Datenbank und beim ersten Start einer
bestehenden nach dem Update –, legt der Server einen Eintrag „Behandler 1“ an (in der App umbenennen). Bestehende Datenbanken bekommen beim Start `dictations.dentist_id`,
`patients.dentist_id` und `transfers.dentist_id` per `ALTER TABLE`; Einträge aus der Zeit davor
bleiben ohne Behandler (`null`) und funktionieren unverändert; das Büro trägt ihn nachträglich ein
(`PUT /dictations/{id}/dentist`, `medvox/attribution.py`), danach ist er wie jeder andere fest.

Korrektur-Sammlung (`medvox/corrections.py`, Tabelle `corrections`, Entscheidung des Behandlers F2 = b):
Ein am iPad korrigiertes Diktat trägt `original`. Wird es übertragen (Büro oder Kurzcode) oder läuft es ab,
schreibt `db.bury` in derselben Transaktion nur die geänderten Stellen (Text vorher/nachher mit wenig Umfeld,
Ziffernänderungen ohne Zahn wie `13b` → `13c`, `` → `107`, `25` → `2x 25`), dazu Patiententyp, Kalenderwoche
(`2026-W39`) und Katalogstand; zufällige Zeilen-ID, keine Fremdschlüssel. Welche Stellen bleiben und was nie
gespeichert wird: Docstring von `medvox/corrections.py`, Datenschutz in `docs/diktierhilfe.md`. Beim Verwerfen
oder Löschen wird nichts gesammelt.
Zeilen bleiben, bis sie gelöscht werden, höchstens 12 Monate (`corrections.purge` bei jedem Aufräumen);
die Wörterbuch-Seite zählt sie als Vorschläge (`medvox/lexicon_suggest.py`) und löscht sie mit „Alle löschen“.

Wörterbuch der Praxis (`medvox/lexicon_entries.py`, Tabelle `lexicon_entries`, Entscheidung F5 = sofort wirksam):
Ersetzungen „falsch gehört → richtig“ (1–3 ganze Wörter) gehen je Anfrage als `extra` an `lexicon.correct`,
Fachbegriffe hinter den Grundtext in den Prompt (`whisper_prompt.compose`; keine unscharfe Korrektur für sie).
Beides wird bei jeder Transkription und jedem `/analyze` aus SQLite gelesen – kein Neustart, kein `make install`.
Einträge werden nur abgeschaltet, nie gelöscht. Prompt-Grenze nachgemessen mit dem installierten
ggml-large-v3-turbo (`n_text_ctx` 448 → 223 Token Text, Grundtext 154 Token; Einzelheiten im Docstring von
`medvox/whisper_prompt.py`): ein Begriff, der nicht mehr passt, wird abgelehnt, statt dass whisper.cpp den
Anfang des Grundtexts abschneidet.

## Module

`medvox/settings.py` (Umgebung), `transcribe.py` (ffmpeg → whisper, Temp-Dateien),
`auth.py` (PBKDF2, Sitzungen), `transfer.py` (Kurzcodes), `corrections.py` (Korrektur-Sammlung),
`lexicon_entries.py`/`lexicon_suggest.py`/`whisper_prompt.py` (Wörterbuch, Vorschläge, Prompt je Anfrage), `handovers.py` (abgeholte Kurzcodes je Diktat), `patients.py` (Diktate je Patient,
Aufbewahrung), `dentists.py` (Behandlerliste), `attribution.py` (Behandler nachtragen), `ratelimit.py` (Client-IP, Fenster),
`db.py` (SQLite, Aufräumen), `lexicon.py`/`normalize*.py`/`extract*.py` (Text-Pipeline),
`routes_*.py` (HTTP-Schicht; `routes_correction.py`: `/analyze`, `/catalog`; `routes_lexicon.py`: Wörterbuch), `main.py` (App-Fabrik). Tests in `tests/`, whisper und
ffmpeg dort per `httpx.MockTransport` bzw. Shell-Fake ersetzt.

## Text-Pipeline

Jedes Transkript durchläuft drei reine, unit-getestete Schritte:
**Roh-Transkript → `medvox.lexicon.correct` → `medvox.normalize.normalize` → Extraktor (WP-8).**
Angezeigt und kopiert wird `medvox.normalize_display.display_text` des korrigierten Texts (siehe unten).
`correct` behebt systematische Whisper-Verhörer anhand eines kuratierten Dental-Lexikons
("Artikein" → "Artikain", "Psycho 3" → "PSI 3", "L935d" → "Ä935d") und gibt jede Korrektur
mit ihren Zeichen-Offsets zurück, damit die UI zeigen kann, was geändert wurde; häufige
deutsche Wörter stehen auf einer Whitelist, Codes und Zahlen werden nie angefasst. Einige Verhörer
gelten nur im Zusammenhang (`CONTEXT_ALIASES`): „PTE 3x“/„2x WD“ → VitE nur neben einer Anzahl (davor oder
dahinter), „MET“ → „med“ nur im Abschnitt eines Zahns mit Wurzelkanalbehandlung (`lexicon_endo.py`), „Röntgen
zwei“/„Rö zwei“ → „Rö2“ nur, wenn keine weitere Ziffer folgt („Röntgen zwei sechs“ bleibt Zahn 26);
„2 flächig“ → „zweiflächig“. Zwei-Wort-Ersetzungen greifen nur bei Leerraum zwischen den Wörtern (vor
„flächig“ auch „-“), nie über Satzzeichen („Röntgen, zwei Kanäle“ bleibt unverändert). Dazu kommen je
Anfrage die eingeschalteten Ersetzungen aus dem Wörterbuch der Praxis (`correct(text, extra)`, bis drei
Wörter): das längere Wortfenster geht vor, bei gleicher Länge die eingebaute Ersetzung.

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
dazwischen steht und sie nicht zum nächsten Zahn hinführen: "Zahn 36, GOZ 2170, mesial, okklusal"
→ 36 mo, aber "Zahn 36 Füllung, Karies mesial an 37" → 36 ohne Fläche), deutsche Zahlwörter zu Ziffern ("BEMA dreizehn a" → "BEMA 13a", "Ibuprofen
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
`extract_endo.py` (Zuzahlungs-Optionen der Endo, Kanalzahl der Je-Kanal-Zuzahlungen),
`extract_limits.py` (Höchstzahl aus dem Katalogfeld `max_per`), `extract_rules.py` (die festen
Fachtabellen zum Nachlesen).

- **Füllungen:** die Flächenzahl wählt 13a–d bzw. 2060–2120 je Zahn – ein freistehendes Zählwort
  („dreiflächig“, „Kompositfüllung MOD“, „BEMA 13a“) gilt nur für die Zähne seines Satzes und geht
  vor den am Zahn diktierten Flächen; Flächen direkt am Zahn („37 mod“) gelten nur für diesen Zahn.
  Widerspruch wird markiert. Flächenwörter allein („36 mod Karies“) lösen keine Füllung aus.
- **Ein-/mehrwurzelig** (43/44, AIT a/b, 4050/4055, 4070/4075) aus der FDI-Nummer. Zahnentfernung braucht ein
  Handlungswort (Extraktion, Osteotomie, X1, Ost1); Befundwörter (retiniert, Längsfraktur) wählen nur
  die Ziffer (48 statt 47a, 45 statt 43/44). „Implantat entfernt“ bleibt GOZ 3000 (Implantat, nicht Zahn;
  beim Kassenpatienten nur ein Hinweis, weil keine Kassenleistung).
- **Anzahl:** je Zahn ein Vorschlag pro Zahn, je Kanal mit der diktierten Kanalzahl – direkt an der
  Position („WK mal drei“, „WK*3“, „VitE 3x“, „3x WK“) oder „3 Kanäle“ im Satz; eine Anzahl gilt nur für
  die Position, an der sie steht („WK 3x, VitE“ → VitE einmal mit Hinweis). Ohne Kanalzahl bleibt es bei
  1 mit „Kanalzahl nicht diktiert“ – nie hochgezählt. „x3“ ist keine Anzahl, sondern X3 (BEMA 45). Eine
  Zuzahlung je Kanal (2400, 2420) übernimmt die diktierte Kanalzahl ihrer Basis am selben Zahn („WK*3,
  Längenbestimmung“ → 3x 2400), samt deren Hinweis zur Kanalzahl (mehrere Zähne genannt). Ohne
  Zahnangabe „28 Zähne“; Sitzungsleistungen zählen ein wiederholtes Wort („L1, L1“) oder „2x“.
  Danach gilt die vom Behandler bestätigte Höchstzahl aus dem Katalog (`max_per` mit
  `max_per_status` „bestaetigt“, bisher nur BEMA 12): „Kofferdam gelegt“ an 36 und an 37 bleibt
  **einmal** BEMA 12 (je Kieferhälfte oder Frontzahnbereich), die Begründung nennt die Begrenzung.
  Liegen die Zähne in mehreren Bereichen (36 und 46), steht die Position je Bereich einmal da, mit den
  Zähnen dieses Bereichs; ohne Zahnnummer einmal mit Prüfhinweis. Positionen ohne Grenze
  (`unbegrenzt`, z. B. 41a) oder mit nur vorgeschlagener Grenze (`vorschlag`, z. B. 107) zählen weiter
  wie diktiert, bis der Behandler die Grenze bestätigt.
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
    13a–d) erscheint zusätzlich als `alternative` (nicht in `codes`). Ebenso bei jeder erbrachten
    Endo-Position (`extract_endo.py`): die erlaubten Zuzahlungen, die sie als Basis nennen (2400
    Längenbestimmung und 2420 „phys“ neben 32, 2197 neben 34/35), und ihr eigenständiges Privat-Paar (2430 zu 34, erst ab der 4. Einlage) –
    nur als Option, nie vorausgewählt; eine schon diktierte Position wird nicht noch einmal angeboten.
    Andere diktierte Privatziffern werden
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
  Vorschlag mit Hinweis in `decide` (in der App als Prüfstreifen „Prüfen: …“ unter der Zeile).
- Plan-Marker wirken nur im eigenen Teilsatz; „danach“ oder Zeitangaben ohne Marker („morgen
  Extraktion“) gelten als erbracht. Verneinung nur direkt an der Leistung.
- Enthaltensein ist nur für 31 in 28 und 11 in 34 hinterlegt; „nicht neben“ aus dem Katalog wird
  markiert, nicht automatisch aufgelöst. Weitere Abrechnungsausschlüsse (Frequenzen, Halbjahr)
  prüft der Extraktor nicht.
- Zuschlag nur für chirurgische GOZ-Positionen im Katalog v1 (3000–3040); 4090/4130 und Implantate
  fehlen im Katalog.
