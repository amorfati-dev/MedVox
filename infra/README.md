# Praxis-Mac einrichten

Diese Anleitung richtet den Mac in der Praxis als Server für MedVox ein:

| Dienst | Was er tut | Skripte |
|---|---|---|
| **whisper-server** (`de.medvox.whisper-server`) | Spracherkennung lokal auf dem Mac (whisper.cpp, Modell `large-v3-turbo`, Deutsch, Dental-Prompt). Lauscht nur auf `127.0.0.1:8178` – nie im Netz. | `infra/whisper/` |
| **Backend** (`de.medvox.server`) | FastAPI aus `server/`: Anmeldung, Transkription (ffmpeg → whisper-server), Ziffern-Vorschläge, Kurzcodes. Lauscht nur auf `127.0.0.1:8000`. Liest den Passwort-Hash aus `password-hash` (von `make set-password`). | `infra/server/` |
| **Caddy** (`de.medvox.caddy`) | HTTPS im Praxis-LAN auf Port 443: liefert die App (`~/Library/Application Support/MedVox/app`, gebaut von `infra/app/install.sh`) aus und leitet `/api` an das Backend (`127.0.0.1:8000`) weiter – eine Adresse, eine Origin. Zertifikat von der eigenen Praxis-CA (mkcert). | `infra/tls/` |

Alle drei laufen als `launchd`-Benutzeragenten: Sie starten beim Anmelden, laufen dauerhaft und werden nach einem Absturz automatisch neu gestartet. **Es verlässt kein Byte das Praxis-LAN** – der einzige Internetzugriff ist die einmalige Installation (Homebrew, whisper.cpp, Modell).

Alles, was die Skripte anlegen, liegt in `~/Library/Application Support/MedVox/` (whisper-Build, Modell, Zertifikate, Caddyfile, Kopie des Backends in `server/`, gebaute App in `app/`, Passwort-Hash, SQLite, Audio-Zwischenordner `tmp/`), `~/Library/LaunchAgents/de.medvox.*.plist` und `~/Library/Logs/MedVox/`. OpenSuperWhisper wird nicht angefasst.

## 1. Voraussetzungen (einmalig)

1. **Xcode Command Line Tools:** im Terminal `xcode-select --install` – Dialog bestätigen, ein paar Minuten warten.
2. **Homebrew:** falls `brew --version` nichts ausgibt, den Befehl von <https://brew.sh> ausführen.
3. `brew install ffmpeg uv node` (Node ≥ 22.18). `make install` prüft alles und nennt genau, was fehlt.
4. Mac ist im Praxis-WLAN/LAN und hat eine feste IP-Adresse (im Router: „DHCP-Reservierung" für den Mac – sonst ändert sich die Adresse und das Zertifikat passt nicht mehr, siehe Abschnitt 7).
5. Repo geklont, Terminal im Repo-Verzeichnis (`cd ~/medvox` o. ä.).

## 2. Installieren – ein Befehl

```bash
make install          # ~5–10 Minuten beim ersten Mal, danach Sekunden
```

Das Skript (`infra/install.sh`) prüft die Voraussetzungen, dann der Reihe nach:

1. **Spracherkennung** (`infra/whisper/install.sh`): whisper.cpp bauen, Modell übernehmen,
   Dienst einrichten. Das Modell (1,6 GB) wird von OpenSuperWhisper **kopiert**, falls dort
   vorhanden, sonst heruntergeladen; eigene Datei: `make install MODEL=/pfad/ggml-large-v3-turbo.bin`.
2. **Backend** (`infra/server/install.sh`): `server/` nach `…/MedVox/server` kopieren,
   Python-Pakete mit `uv` installieren, Dienst `de.medvox.server` laden.
3. **App** (`infra/app/install.sh`): `npm ci && npm run build`, Ergebnis nach `…/MedVox/app`.
4. **HTTPS** (`infra/tls/setup.sh`): Praxis-CA, Zertifikat, Caddy. Fragt beim allerersten
   Mal nach dem **Mac-Passwort** (mkcert trägt die CA in den Schlüsselbund ein).
5. **Passwort**: ist noch keines gesetzt, fragt es jetzt danach (`make set-password`).
6. **Prüfung** (`make status`) und Ausgabe der Adressen für iPad und Rezeptions-PC.

Nach einem Update des Repos (`git pull`) einfach erneut `make install` – der Stand wird
kopiert, die Dienste neu geladen. Danach darf das Repo woanders liegen: die Dienste laufen
nur aus `~/Library/Application Support/MedVox/`.

## 3. Praxis-CA auf iPad / iPhone installieren (einmal pro Gerät)

Safari erlaubt das Mikrofon nur über HTTPS, und HTTPS braucht ein Zertifikat, dem das iPad vertraut. Dafür wird die Praxis-CA (`~/Library/Application Support/MedVox/tls/rootCA.pem`) einmal auf jedes Gerät gebracht:

1. **Datei aufs Gerät:** Finder → `rootCA.pem` → Rechtsklick → *Teilen* → **AirDrop** an das iPad. (Alternative: als Mail-Anhang schicken und den Anhang auf dem iPad antippen.)
2. iPad meldet „Profil geladen". **Einstellungen** öffnen → ganz oben *Profil geladen* antippen (oder *Allgemein → VPN & Geräteverwaltung*) → Profil „mkcert …" → **Installieren** → Gerätecode → nochmals **Installieren**.
3. **Vertrauen aktivieren – ohne diesen Schritt bleibt Safari rot:** *Einstellungen → Allgemein → Info → Zertifikatsvertrauenseinstellungen* → Schalter bei „mkcert …" **einschalten** → *Weiter*.
4. Safari: `https://<LAN-IP>` öffnen – kein Warnhinweis mehr. Dann *Teilen → Zum Home-Bildschirm*, damit die App als PWA startet.

## 4. Praxis-CA auf dem Windows-Rezeptions-PC

1. `rootCA.pem` auf den PC bringen (USB-Stick, Mail, Netzfreigabe) und in `rootCA.crt` umbenennen.
2. Doppelklick → **Zertifikat installieren…** → *Aktueller Benutzer* (oder *Lokaler Computer*, braucht Admin) → *Alle Zertifikate in folgendem Speicher speichern* → *Durchsuchen…* → **Vertrauenswürdige Stammzertifizierungsstellen** → Fertig stellen → Sicherheitsabfrage mit *Ja*.
   Alternativ als Administrator in PowerShell: `Import-Certificate -FilePath rootCA.crt -CertStoreLocation Cert:\LocalMachine\Root`
3. Edge/Chrome neu starten und `https://<LAN-IP>` öffnen. Firefox nutzt einen eigenen Speicher: `about:config` → `security.enterprise_roots.enabled` auf `true`.

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
infra/tls/check.sh        # Details HTTPS: Zertifikat-SANs, TLS-Kette, App und Backend über die LAN-IP
```

`make status` prüft Spracherkennung, Backend (inkl. Verbindung zur Spracherkennung),
Passwort, HTTPS-Zugang (App **und** API über die LAN-IP), Zertifikat und dass keine
Audiodatei im Zwischenordner liegen geblieben ist. Ein ausgefallenes Backend ist ein
Fehler, keine Warnung. Hinweiszeilen (Ruhezustand am Netzteil, Zertifikat läuft in
< 30 Tagen ab) zählen nicht als Fehler.

Von Hand:

```bash
launchctl print gui/$(id -u)/de.medvox.whisper-server | grep state   # state = running
launchctl print gui/$(id -u)/de.medvox.server | grep state
launchctl print gui/$(id -u)/de.medvox.caddy | grep state
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
Skripte löscht `setup.sh` beim nächsten Lauf.

Alle Logs sind auf 5 MiB gedeckelt: darüber wird der Inhalt nach `.1` (`.2`,
`.3`) gesichert und die Datei geleert – von den Installationsskripten und bei
jedem `make status`.

Neustart eines Dienstes: `launchctl kickstart -k gui/$(id -u)/de.medvox.whisper-server` (bzw. `…/de.medvox.server`, `…/de.medvox.caddy`).

Nach einem Neustart des Macs (`sudo shutdown -r now`, Abnahme Punkt 6): anmelden, 1 Minute warten, `make status` – muss „Alles in Ordnung." zeigen, ohne dass etwas von Hand gestartet wird.

## 7. Prompt ändern

Der Dental-Prompt (Vokabular-Anker für Whisper) steht **nur** in `infra/whisper/prompt.txt` – eine Zeile. Eigene Begriffe (Materialnamen, Praxis-Kürzel) einfach hinten anhängen, kurz halten (Whisper nutzt ca. 220 Tokens davon), dann:

```bash
make install                # schreibt die plists neu und startet die Dienste
infra/whisper/smoke.sh      # gegenprüfen
```

Gleiches gilt für die Thread-Zahl: `infra/whisper/de.medvox.whisper-server.plist.template` anpassen, `install.sh` erneut ausführen. Die Ports liegen fest in `infra/common.sh`.

## 8. Wenn sich die LAN-IP ändert

`make install` (oder nur `infra/tls/setup.sh`) erneut ausführen: erkennt die neue IP, stellt ein neues Zertifikat aus (gleiche Praxis-CA – auf den Geräten muss **nichts** neu installiert werden) und lädt Caddy neu. `infra/tls/check.sh` warnt, wenn die IP nicht mehr im Zertifikat steht.

Optional, damit die Adresse `https://medvox.local` statt der IP funktioniert: dem Mac den Bonjour-Namen `medvox` geben – *Systemeinstellungen → Allgemein → Info → Name* auf „medvox" (oder `sudo scutil --set LocalHostName medvox`). iPad und Windows (ab 10) lösen `medvox.local` dann per Bonjour/mDNS auf.

## 9. Deinstallieren

```bash
infra/whisper/uninstall.sh          # Dienst weg, Build und Modell bleiben
launchctl bootout gui/$(id -u)/de.medvox.server \
  && rm -f ~/Library/LaunchAgents/de.medvox.server.plist  # Backend-Dienst weg
launchctl bootout gui/$(id -u)/de.medvox.caddy \
  && rm -f ~/Library/LaunchAgents/de.medvox.caddy.plist   # Caddy-Dienst weg
mkcert -uninstall                   # Praxis-CA aus dem macOS-Schlüsselbund entfernen
```

Was die Skripte angelegt haben, liegt danach noch in
`~/Library/Application Support/MedVox/` und kann von Hand gelöscht werden.

## Technische Notizen

- Die Ports stehen fest: whisper-server auf `127.0.0.1:8178`, Caddy auf 443. Port 443 braucht auf macOS keine Root-Rechte (seit 10.14 dürfen Benutzerprozesse Ports < 1024 binden), deshalb läuft Caddy als normaler Benutzeragent auf 443 – kein `:8443` in der Adresse.
- Caddy leitet `http://<IP>` auf HTTPS um, hält `admin off` (kein Admin-API-Port) und setzt `Cache-Control: no-store`.
- whisper-server wird auf dem in `install.sh` festgelegten Commit von whisper.cpp gebaut (Stand der Messungen im Plan).
- Pfad zur gebauten App für Caddy: `~/Library/Application Support/MedVox/app` (nie ein Repo-/Worktree-Pfad).
- Das Backend läuft aus `…/MedVox/server` mit eigener `.venv` (`uv sync --frozen --no-dev --no-install-project`); launchd kennt Homebrew nicht im `PATH`, deshalb steht der ffmpeg-Pfad als `MEDVOX_FFMPEG` in der plist. Audio-Zwischendateien liegen in `…/MedVox/tmp` (`MEDVOX_TMP_DIR`), damit `make status` prüfen kann, dass dort nichts liegen bleibt.
- Die Zertifikatsprüfung liest die SANs aus `openssl x509 -noout -text`: das mit macOS gelieferte `/usr/bin/openssl` (LibreSSL) kennt `-ext subjectAltName` nicht.
- Vom Backend (WP-2) aus: `POST http://127.0.0.1:8178/inference` mit `file=@audio.wav` (16 kHz mono), `language=de`, `response_format=json` → `{"text": "…"}`. Der Prompt ist im Dienst gesetzt; ein `prompt=`-Feld in der Anfrage überschreibt ihn.
