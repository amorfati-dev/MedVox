# Praxis-Mac einrichten

Diese Anleitung richtet den Mac in der Praxis als Server für MedVox ein:

| Dienst | Was er tut | Skripte |
|---|---|---|
| **whisper-server** (`de.medvox.whisper-server`) | Spracherkennung lokal auf dem Mac (whisper.cpp, Modell `large-v3-turbo`, Deutsch, Dental-Prompt). Lauscht nur auf `127.0.0.1:8178` – nie im Netz. | `infra/whisper/` |
| **Backend** (`de.medvox.server`) | FastAPI aus `server/`: Anmeldung, Transkription (ffmpeg → whisper-server), Ziffern-Vorschläge, Kurzcodes. Lauscht nur auf `127.0.0.1:8000`. Liest den Passwort-Hash aus `password-hash` (von `make set-password`). | `infra/server/` |
| **Caddy** (`de.medvox.caddy`) | HTTPS im Praxis-LAN auf Port 443: liefert die App (`~/Library/Application Support/MedVox/app`, gebaut von `infra/app/install.sh`) aus und leitet `/api` an das Backend (`127.0.0.1:8000`) weiter – eine Adresse, eine Origin. Zertifikat von der eigenen Praxis-CA (mkcert). | `infra/tls/` |
| **Name** (`de.medvox.mdns`) | Meldet per Bonjour/mDNS den Namen `medvox.local` mit der aktuellen Adresse des Macs im LAN an (`dns-sd -P`) und meldet ihn nach einem Netzwechsel von selbst neu an. Der Mac behält seinen eigenen Namen. | `infra/mdns/` |

**Die Adresse für iPad und Rezeptions-PC ist `https://medvox.local`** – in der Praxis, zu Hause, in jedem Netz dieselbe.

Alle vier laufen als `launchd`-Benutzeragenten: Sie starten beim Anmelden, laufen dauerhaft und werden nach einem Absturz automatisch neu gestartet. **Es verlässt kein Byte das Praxis-LAN** – der einzige Internetzugriff ist die einmalige Installation (Homebrew, whisper.cpp, Modell).

Alles, was die Skripte anlegen, liegt in `~/Library/Application Support/MedVox/` (whisper-Build, Modell, Zertifikate, Caddyfile, Kopie des Backends in `server/`, gebaute App in `app/`, Passwort-Hash, SQLite, Audio-Zwischenordner `tmp/`), `~/Library/LaunchAgents/de.medvox.*.plist` und `~/Library/Logs/MedVox/`. OpenSuperWhisper wird nicht angefasst.

## 1. Voraussetzungen (einmalig)

1. **Xcode Command Line Tools:** im Terminal `xcode-select --install` – Dialog bestätigen, ein paar Minuten warten.
2. **Homebrew:** falls `brew --version` nichts ausgibt, den Befehl von <https://brew.sh> ausführen.
3. `brew install ffmpeg uv node` (Node ≥ 22.18). `make install` prüft alles und nennt genau, was fehlt.
4. Mac ist im Praxis-WLAN/LAN. Eine feste IP-Adresse ist nicht nötig: die Geräte finden ihn unter `medvox.local` (Abschnitt 8).
5. Repo geklont, Terminal im Repo-Verzeichnis (`cd ~/medvox` o. ä.).

## 2. Installieren – ein Befehl

```bash
make install          # ~5–10 Minuten beim ersten Mal, danach Sekunden
```

Das Skript (`infra/install.sh`) prüft die Voraussetzungen, dann der Reihe nach:

1. **Spracherkennung** (`infra/whisper/install.sh`): whisper.cpp bauen, Modell übernehmen,
   Dienst einrichten. Das Modell (1,6 GB) wird heruntergeladen, falls noch keins installiert ist.
   Liegt `ggml-large-v3-turbo.bin` schon auf dem Mac, wird diese Datei stattdessen **kopiert**:
   `make install MODEL=/pfad/zum/ggml-large-v3-turbo.bin`.
2. **Backend** (`infra/server/install.sh`): `server/` nach `…/MedVox/server` kopieren,
   Python-Pakete mit `uv` installieren, Dienst `de.medvox.server` laden.
3. **App** (`infra/app/install.sh`): `npm ci && npm run build`, Ergebnis nach `…/MedVox/app`.
4. **HTTPS** (`infra/tls/setup.sh`): Praxis-CA, Zertifikat (für `medvox.local` und die aktuelle LAN-IP), Caddy. Beim allerersten Mal
   fragt `mkcert -install` im Terminal nach dem **Mac-Passwort** (sudo – die Praxis-CA kommt in
   den System-Schlüsselbund). Dieser Schritt läuft deshalb nicht unbeaufsichtigt: am Terminal
   bleiben und das Passwort eingeben. Bricht der Lauf dort ab (Passwort nicht eingegeben,
   Fenster geschlossen), einfach **`make install` noch einmal** ausführen – die CA ist dann
   eingetragen, der zweite Lauf fragt nicht mehr und schließt die Installation ab.
5. **Name** (`infra/mdns/install.sh`): Dienst `de.medvox.mdns`, damit der Mac im LAN auf
   `medvox.local` antwortet.
6. **Passwort**: ist noch keines gesetzt, fragt es jetzt danach (`make set-password`).
7. **Prüfung** (`make status`) und Ausgabe der Adresse `https://medvox.local` für iPad und Rezeptions-PC.

Nach einem Update des Repos (`git pull`) einfach erneut `make install` – der Stand wird
kopiert, die Dienste neu geladen. Danach darf das Repo woanders liegen: die Dienste laufen
nur aus `~/Library/Application Support/MedVox/`.

## 3. Praxis-CA auf iPad / iPhone installieren (einmal pro Gerät)

Safari erlaubt das Mikrofon nur über HTTPS, und HTTPS braucht ein Zertifikat, dem das iPad vertraut. Dafür wird die Praxis-CA (`~/Library/Application Support/MedVox/tls/rootCA.pem`) einmal auf jedes Gerät gebracht:

1. **Datei aufs Gerät:** Finder → `rootCA.pem` → Rechtsklick → *Teilen* → **AirDrop** an das iPad. (Alternative: als Mail-Anhang schicken und den Anhang auf dem iPad antippen.)
2. iPad meldet „Profil geladen". **Einstellungen** öffnen → ganz oben *Profil geladen* antippen (oder *Allgemein → VPN & Geräteverwaltung*) → Profil „mkcert …" → **Installieren** → Gerätecode → nochmals **Installieren**.
3. **Vertrauen aktivieren – ohne diesen Schritt bleibt Safari rot:** *Einstellungen → Allgemein → Info → Zertifikatsvertrauenseinstellungen* → Schalter bei „mkcert …" **einschalten** → *Weiter*.
4. Safari: `https://medvox.local` öffnen – kein Warnhinweis mehr. Dann *Teilen → Zum Home-Bildschirm*, damit die App als PWA startet.

## 4. Praxis-CA auf dem Windows-Rezeptions-PC

1. `rootCA.pem` auf den PC bringen (USB-Stick, Mail, Netzfreigabe) und in `rootCA.crt` umbenennen.
2. Doppelklick → **Zertifikat installieren…** → *Aktueller Benutzer* (oder *Lokaler Computer*, braucht Admin) → *Alle Zertifikate in folgendem Speicher speichern* → *Durchsuchen…* → **Vertrauenswürdige Stammzertifizierungsstellen** → Fertig stellen → Sicherheitsabfrage mit *Ja*.
   Alternativ als Administrator in PowerShell: `Import-Certificate -FilePath rootCA.crt -CertStoreLocation Cert:\LocalMachine\Root`
3. Edge/Chrome neu starten und `https://medvox.local` öffnen (Windows 10/11 löst `.local`-Namen selbst per mDNS auf). Firefox nutzt einen eigenen Speicher: `about:config` → `security.enterprise_roots.enabled` auf `true`.

## 5. Mac darf am Netzteil nicht einschlafen

Schläft der Mac, ist der Dienst weg. Deshalb bei Netzstrom den Ruhezustand abschalten – **einmal einstellen, die Skripte machen das bewusst nicht:**

- **Systemeinstellungen → Batterie → Optionen…** → „Automatischen Ruhezustand verhindern, wenn das Display ausgeschaltet ist und das Gerät am Netzteil angeschlossen ist" **einschalten**. Zusätzlich *Energiesparmodus* auf „Nie" (Netzteil).
  Bei einem Mac mini/Studio: *Systemeinstellungen → Energie*, gleicher Schalter.
- oder im Terminal (fragt nach dem Passwort): `sudo pmset -c sleep 0 disablesleep 1`
  `-c` = nur am Netzteil. Wieder rückgängig: `sudo pmset -c sleep 10 disablesleep 0`.
- Display darf ausgehen, das stört nicht. Der Mac muss **angemeldet** bleiben (Benutzeragenten laufen nur in der angemeldeten Sitzung) – Bildschirm sperren ist in Ordnung. Für einen unbeaufsichtigten Start nach Stromausfall: *Systemeinstellungen → Benutzer & Gruppen → Automatisch anmelden* für das Praxiskonto (dann FileVault-Hinweis beachten).

## 6. Läuft alles? – Prüfen

```bash
make status           # eine Zeile je Baustein, Exit-Code 0 nur wenn alles funktioniert
make restart-test     # jeden Dienst hart neu starten (launchctl kickstart -k), Rückkehr messen
infra/whisper/status.sh   # Details Spracherkennung: Health-Check mit stummer 1-s-WAV, Log
infra/whisper/smoke.sh    # spricht ein Diktat mit der Mac-Stimme "Anna" und prüft "36"/"drei sechs"
infra/tls/check.sh        # Details HTTPS: Zertifikat-SANs, TLS-Kette, App und Backend unter medvox.local
```

`make status` prüft Spracherkennung, Backend (inkl. Verbindung zur Spracherkennung),
Passwort, HTTPS-Zugang (App **und** API), den Namen `medvox.local` (löst er auf die aktuelle
Adresse auf, antwortet HTTPS darunter?), Zertifikat und dass keine Audiodatei im
Zwischenordner liegen geblieben ist. Ein ausgefallenes Backend ist ein Fehler, keine
Warnung. Hinweiszeilen (Ruhezustand am Netzteil, Zertifikat läuft in < 30 Tagen ab,
Ausweichadresse nach Netzwechsel nicht mehr im Zertifikat) zählen nicht als Fehler.

Von Hand:

```bash
launchctl print gui/$(id -u)/de.medvox.whisper-server | grep state   # state = running
launchctl print gui/$(id -u)/de.medvox.server | grep state
launchctl print gui/$(id -u)/de.medvox.caddy | grep state
launchctl print gui/$(id -u)/de.medvox.mdns | grep state
dns-sd -G v4 medvox.local       # zeigt die Adresse, unter der medvox.local antwortet (Strg+C)
tail -f ~/Library/Logs/MedVox/server.log
```

**Was in den Logs steht – und was nicht.** `whisper-server.log` enthält den
Start-Banner von whisper/ggml, die `system_info`-Zeile und pro Anfrage eine
Zeile `operator(): processing 'diktat.wav' (… samples, … sec), 8 threads, …,
lang = de, …`. **Kein erkannter Text** – nachgemessen auf dem Praxis-Mac mit
einem 12-s-Diktat. Der Dateiname des Uploads steht aber drin, deshalb dürfen die
Schalter `-pr`/`--print-realtime`, `-pp` und `-ps` **nie** in die plist: `-pr`
würde das Transkript nach stdout und damit ins Log schreiben (AGENTS.md: „Logs
ohne Transkripttext"). `server.log` enthält Start-/Fehlermeldungen des Backends und je Diktat eine Zeile
„Transkription: … s Audio in … s" – ohne Text; das Zugriffslog von uvicorn ist
abgeschaltet (`--no-access-log`), weil Anfrage-URLs Kurzcodes enthalten.
`caddy.log` enthält nur Caddys Laufzeitmeldungen;
Zugriffslogs und Caddys Fehlerlog (`http.log.error`, etwa bei 502) sind bewusst
abgeschaltet, damit keine Anfrage-URLs (und später keine Kurzcodes) auf der
Platte landen – ein `caddy-access.log` aus einer früheren Fassung dieser
Skripte löscht `setup.sh` beim nächsten Lauf. `mdns.log` enthält nur, wann
`medvox.local` mit welcher Adresse des Macs angemeldet wurde.

Alle Logs sind auf 5 MiB gedeckelt: darüber wird der Inhalt nach `.1` (`.2`,
`.3`) gesichert und die Datei geleert – von den Installationsskripten und bei
jedem `make status`.

Neustart eines Dienstes: `launchctl kickstart -k gui/$(id -u)/de.medvox.whisper-server` (bzw. `…/de.medvox.server`, `…/de.medvox.caddy`, `…/de.medvox.mdns`).

Nach einem Neustart des Macs (`sudo shutdown -r now`, Abnahme Punkt 6): anmelden, 1 Minute warten, `make status` – muss „Alles in Ordnung." zeigen, ohne dass etwas von Hand gestartet wird.

## 7. Prompt ändern

Eigene Fachbegriffe (Materialnamen, Praxis-Kürzel) und Verhörer („Zahn steinentfernung“ → „Zahnsteinentfernung“) trägt die Praxis auf der Seite **Wörterbuch** ein (⋯ → Wörterbuch, `https://medvox.local/woerterbuch`) – sie gelten sofort, ohne Neustart und ohne `make install`.

Der Grundtext des Prompts (Vokabular-Anker für Whisper) steht **nur** in `infra/whisper/prompt.txt` – eine Zeile; die Begriffe aus dem Wörterbuch hängt der Server je Anfrage dahinter. whisper.cpp nimmt davon höchstens 223 Token (nachgemessen mit dem installierten Modell; der Grundtext hat 150), darüber schneidet es vorne ab – die Wörterbuch-Seite zeigt den Füllstand. Den Grundtext ändern:

```bash
make install                # schreibt die plists neu und startet die Dienste
infra/whisper/smoke.sh      # gegenprüfen
```

Gleiches gilt für die Thread-Zahl: `infra/whisper/de.medvox.whisper-server.plist.template` anpassen, `install.sh` erneut ausführen. Die Ports liegen fest in `infra/common.sh`.

## 8. Adresse `https://medvox.local` – auch nach einem Netzwechsel

iPad und Rezeptions-PC öffnen immer **`https://medvox.local`**. Der Dienst `de.medvox.mdns`
meldet diesen Namen per Bonjour/mDNS mit der Adresse an, die der Mac gerade hat, und prüft
alle 5 Sekunden, ob sie sich geändert hat (Praxis ↔ zu Hause, neue Adresse vom Router,
WLAN kurz weg). Dann meldet er den Namen mit der neuen Adresse neu an. Das Zertifikat gilt
für den Namen, nicht für die Adresse. **Nach einem Netzwechsel ist deshalb nichts neu zu
tun** – kein `make install`, keine neue Adresse auf dem iPad, keine Zertifikatswarnung.
Ein paar Sekunden nach dem Wechsel ist MedVox unter demselben Namen wieder da. Der Mac
behält dabei seinen eigenen Namen (*Systemeinstellungen → Allgemein → Info → Name* bleibt,
wie er ist); `medvox.local` kommt nur hinzu.

Wer MedVox früher unter der Zahlenadresse auf den Home-Bildschirm gelegt hat: einmal in
Safari `https://medvox.local` öffnen, neu anmelden und erneut *Teilen → Zum Home-Bildschirm*
– das alte Symbol kann weg (für das iPad sind es zwei verschiedene Adressen).

**Ausweichadresse:** `https://<LAN-IP>` (die Zahl zeigt `make status` in der Zeile
„HTTPS-Zugang") funktioniert weiterhin, bis sich die Adresse ändert. Sie ist nur für den
Fall gedacht, dass ein Gerät `.local`-Namen nicht auflöst – etwa ein älterer Windows-PC
oder ein Gästenetz, das Bonjour zwischen den Geräten sperrt. Ändert sich die Adresse, zeigt
`make status` einen Hinweis; `make install` stellt das Zertifikat dann auch für die neue
Zahl aus (gleiche Praxis-CA, auf den Geräten ist nichts neu zu installieren).

`make status` zeigt in der Zeile „Name medvox.local", ob der Name auf die aktuelle Adresse
auflöst und HTTPS darunter antwortet. Das prüft der Mac bei sich selbst; findet ein Gerät
den Namen trotzdem nicht, sind beide wirklich im selben Netz? (Das iPad darf nicht im
Gäste-WLAN hängen.)

## 9. Deinstallieren

```bash
infra/whisper/uninstall.sh          # Dienst weg, Build und Modell bleiben
launchctl bootout gui/$(id -u)/de.medvox.server \
  && rm -f ~/Library/LaunchAgents/de.medvox.server.plist  # Backend-Dienst weg
launchctl bootout gui/$(id -u)/de.medvox.caddy \
  && rm -f ~/Library/LaunchAgents/de.medvox.caddy.plist   # Caddy-Dienst weg
launchctl bootout gui/$(id -u)/de.medvox.mdns \
  && rm -f ~/Library/LaunchAgents/de.medvox.mdns.plist    # Name medvox.local weg
mkcert -uninstall                   # Praxis-CA aus dem macOS-Schlüsselbund entfernen
```

Was die Skripte angelegt haben, liegt danach noch in
`~/Library/Application Support/MedVox/` und kann von Hand gelöscht werden.

## Technische Notizen

- Die Ports stehen fest: whisper-server auf `127.0.0.1:8178`, Caddy auf 443. Port 443 braucht auf macOS keine Root-Rechte (seit 10.14 dürfen Benutzerprozesse Ports < 1024 binden), deshalb läuft Caddy als normaler Benutzeragent auf 443 – kein `:8443` in der Adresse.
- Caddy lauscht auf allen Schnittstellen und wählt die Seite nach dem Namen: `https://medvox.local` funktioniert deshalb auch unter einer neuen Adresse, obwohl im Caddyfile noch die alte Zahl steht.
- `de.medvox.mdns` läuft aus `…/MedVox/mdns/run.sh` (mit einer Kopie von `common.sh`, dieselbe `lan_ip`-Regel: Schnittstelle der Standardroute). `dns-sd -P` hält die Adresse fest, mit der es gestartet wurde; deshalb vergleicht `run.sh` alle 5 s die LAN-IP und startet `dns-sd` bei einer Änderung neu (ohne Netz: abgemeldet, bis wieder eine Adresse da ist). Nebenbei erscheint „MedVox" als `_https._tcp`-Dienst im Bonjour-Browser. Nur IPv4.
- `/api/v1/events` (Live-Strom der Büroliste, Server-Sent Events) reicht Caddy ohne gzip und ohne Pufferung durch (`flush_interval -1`); das Backend bricht offene Ströme beim Neustart nach 3 s ab (`--timeout-graceful-shutdown` in `infra/server/run.sh`), die Seiten verbinden sich selbst neu.
- Caddy leitet `http://<IP>` auf HTTPS um, hält `admin off` (kein Admin-API-Port) und setzt `Cache-Control: no-store`.
- whisper-server wird auf dem in `install.sh` festgelegten Commit von whisper.cpp gebaut (Stand der Messungen im Plan).
- Pfad zur gebauten App für Caddy: `~/Library/Application Support/MedVox/app` (nie ein Repo-/Worktree-Pfad).
- Das Backend läuft aus `…/MedVox/server` mit eigener `.venv` (`uv sync --frozen --no-dev --no-install-project`); launchd kennt Homebrew nicht im `PATH`, deshalb steht der ffmpeg-Pfad als `MEDVOX_FFMPEG` in der plist. Audio-Zwischendateien liegen in `…/MedVox/tmp` (`MEDVOX_TMP_DIR`), damit `make status` prüfen kann, dass dort nichts liegen bleibt.
- Die Zertifikatsprüfung liest die SANs aus `openssl x509 -noout -text`: das mit macOS gelieferte `/usr/bin/openssl` (LibreSSL) kennt `-ext subjectAltName` nicht.
- Vom Backend (WP-2) aus: `POST http://127.0.0.1:8178/inference` mit `file=@audio.wav` (16 kHz mono), `language=de`, `response_format=json` → `{"text": "…"}`. Der Prompt ist im Dienst gesetzt; ein `prompt=`-Feld in der Anfrage überschreibt ihn.
