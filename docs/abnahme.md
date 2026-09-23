# Abnahme Phase 1 – Protokoll für die Praxis

Sechs Prüfungen, eine je Abnahmekriterium aus dem Plan (Phase 1), dazu Prüfung 7 für die
Diktate je Patient (mehrere Patienten, übertragen im Büro) und Prüfung 8 für mehrere Behandler an
geteilten iPads. Jede Zeile
abhaken und notieren, was tatsächlich zu sehen war – auch wenn es geklappt hat.
Schlägt etwas fehl: Uhrzeit notieren, `make status` im Terminal ausführen und die
Ausgabe mit aufschreiben.

**Vorbereitung (einmalig):**

- [ ] Im Repo-Verzeichnis auf dem Praxis-Mac: `make install` – am Terminal bleiben: beim
      ersten Mal fragt der Zertifikatsschritt nach dem **Mac-Passwort**. Abgebrochen? Einfach
      `make install` noch einmal. Endet mit „Alles in Ordnung." und der Adresse
      `https://medvox.local` – die gilt in jedem Netz; nach einem Netzwechsel ist nichts neu zu
      tun. `make status` zeigt „Name medvox.local … HTTPS antwortet".
- [ ] Ausweichadresse notiert (Zeile „HTTPS-Zugang" in `make status`), nur für Geräte, die
      `medvox.local` nicht finden (`infra/README.md`, Abschnitt 8): `https://`______________
- [ ] `make set-password` – eigenes Passwort gesetzt (mind. 8 Zeichen).
- [ ] Praxis-CA auf iPad und Rezeptions-PC installiert (`infra/README.md`, Abschnitte 3 und 4).
- [ ] Ruhezustand am Netzteil aus (`infra/README.md`, Abschnitt 5); `make status` zeigt keinen
      Hinweis „Ruhezustand".
- [ ] Behandlerliste: iPad → ⋯ → Behandlerliste (`/behandler`). Den ersten Eintrag „Behandler 1"
      auf den eigenen Namen umbenennen, alle Behandler der Praxis hinzufügen (Name wie angezeigt,
      Behandlernummer optional).
- [ ] `docs/diktierhilfe.md` ausgedruckt neben dem Behandlungsstuhl.

Datum: ____________  Mac: ____________  iPad/iOS-Version: ____________

---

## 1. Diktat auf dem iPad – Ergebnis in höchstens 3 Sekunden

1. [ ] iPad: MedVox vom Home-Bildschirm öffnen, anmelden.
2. [ ] ⋯-Menü → „Gerätetest" (`/check`): „Alles bereit", jede Kachel ✓, „Mikrofon testen" erlaubt.
3. [ ] Im Behandlungszimmer „Aufnehmen", etwa 30 Sekunden diktieren, z. B.:
       „Zahn drei sechs mesial okklusal distal Karies profunda. Infiltrationsanästhesie mit
       Artikain. Kofferdam gelegt. Zahn drei sechs mesial okklusal distal Kompositfüllung in
       Adhäsivtechnik. Zahn vier sechs Vitalitätsprüfung positiv. Zahnsteinentfernung.
       Zahn eins sechs Wurzelkanalaufbereitung geplant."
4. [ ] „Stopp" tippen und mit der Handy-Stoppuhr messen, bis Transkript **und** Ziffern
       sichtbar sind. Soll: **≤ 3 s**.
5. [ ] Zehn echte Diktate aus dem Praxisalltag auf dieselbe Weise (Messprotokoll unten).

Gemessen (Stoppuhr): ______ s   App zeigt „Transkription in ___ s"
Ziffern-Vorschläge: _______________________________________________
Beobachtet: ______________________________________________________

## 2. Zahnnummern als FDI, Flächen normalisiert

1. [ ] Im angezeigten Text des Diktats aus Punkt 1 stehen die Zähne als Ziffern:
       „Zahn **36** mesial okklusal distal …", „Zahn **46** …", „Zahn **16** …" – Flächen
       ausgeschrieben, wie diktiert.
2. [ ] Die Vorschläge nennen dieselben Zähne, die Füllung als **13c** (drei Flächen).
3. [ ] Diktat „Zahn eins sechs zwei sechs Versiegelung" → Text „Zahn 16 26 …", Vorschlag für
       **16 und 26** (2x).
4. [ ] Diktat „BEMA dreizehn a" → im Text „BEMA 13a".
5. [ ] Im Text keine englischen Schreibweisen („mesial occlusal", „composite").

Beobachtet: ______________________________________________________

## 3. Kurzcode an die Rezeption, Einfügen in Evident

1. [ ] iPad: „An Rezeption" (Leiste unten) → sechsstelliger Code und QR-Code erscheinen.
       Code: ______
2. [ ] Rezeptions-PC: `https://medvox.local/transfer` öffnen, Code eingeben → Text und Ziffern
       erscheinen.
3. [ ] „Text kopieren" → in Evident in die Dokumentation einfügen (Strg+V): Umlaute, Absätze
       und Zahnnummern kommen richtig an.
4. [ ] „Ziffern kopieren" → in Evident einfügen: je Zahn eine Zeile „36,Ä925a,l1,13a",
       Positionen ohne Zahn („01,107") in der letzten Zeile (siehe `docs/diktierhilfe.md`).
5. [ ] Zeit vom Tippen auf „Senden" bis zum Text in Evident: ______ s

Beobachtet: ______________________________________________________

## 4. Ohne Internet: alles läuft weiter, kein Internetverkehr

1. [ ] **Nur die Internetleitung** vom Router ziehen (DSL-/Glasfaser-/Kabelmodem-Kabel).
       Den Router selbst **anlassen** – er ist das Praxis-WLAN, über das iPad und
       Rezeptions-PC den Mac erreichen.
2. [ ] Kontrolle: Safari auf dem iPad kann keine externe Seite mehr öffnen.
3. [ ] Punkte 1 und 3 wiederholen (Diktat, Ziffern, Kurzcode, Einfügen) – alles funktioniert.
4. [ ] Auf dem Mac im Terminal – zeigt alle offenen Verbindungen der MedVox-Dienste:
       ```sh
       lsof -nP -iTCP -sTCP:ESTABLISHED | grep -E '^(whisper|caddy|python|uvicorn)'
       ```
       Erwartet: nur Adressen `127.0.0.1` und Praxis-LAN (`192.168.…`), **keine anderen**.
       Zusätzlich *Aktivitätsanzeige → Netzwerk*: whisper-server, caddy, python ohne
       gesendete Daten ins Internet.
5. [ ] Internetleitung wieder einstecken.

Beobachtet: ______________________________________________________

## 5. Keine Audiodatei auf dem Mac, Kurzcodes verfallen

1. [ ] Direkt nach einem Diktat: `make status` → Zeile
       „✓ Audiodateien – keine gespeichert".
2. [ ] Gegenprobe im Terminal – darf nichts ausgeben:
       ```sh
       find ~/Library/Application\ Support/MedVox ~/Library/Logs/MedVox \
            \( -name '*.m4a' -o -name '*.wav' -o -name '*.webm' -o -name '*.mp4' \) -print
       ```
3. [ ] Logs enthalten keinen Diktattext – ein Wort aus dem Diktat suchen, darf nichts finden:
       `grep -ri "Kofferdam" ~/Library/Logs/MedVox/`
4. [ ] Code aus Punkt 3 nach **mehr als 15 Minuten** an der Rezeption erneut eingeben →
       „nicht gefunden".
5. [ ] Nach weiteren 5 Minuten ist auch die gespeicherte Zeile weg (0 = in Ordnung):
       `sqlite3 ~/Library/Application\ Support/MedVox/medvox.db "select count(*) from transfers where expires_at < cast(strftime('%s','now') as real)"`

Beobachtet: ______________________________________________________

## 6. Mac neu starten – Dienste laufen ohne Zutun

1. [ ] Vorab (ohne Neustart): `make restart-test` – jeder Dienst wird hart beendet und
       meldet sich nach wenigen Sekunden zurück; endet mit „Alles in Ordnung."
2. [ ] Mac neu starten: Apfelmenü → *Neustart…* oder im Terminal
       ```sh
       sudo shutdown -r now
       ```
       (fragt nach dem Mac-Passwort).
3. [ ] Anmelden (bzw. automatische Anmeldung abwarten), **nichts starten**, 1 Minute warten.
4. [ ] `make status` → „Alles in Ordnung."
5. [ ] Auf dem iPad ohne neue Anmeldung diktieren – funktioniert.

Uhrzeit Neustart: ______  `make status` grün um: ______
Beobachtet: ______________________________________________________

## 7. Mehrere Patienten hintereinander, übertragen im Büro

1. [ ] iPad: oben links auf „Ohne Patient" tippen, Evident-Nummer über das Tastenfeld eingeben
       (z. B. 4711), **OK** → die Nummer steht groß oben links.
2. [ ] Diktieren → unter der Nummer „Gespeichert – im Büro unter ‚Patienten'".
3. [ ] **Neu** → zweites Diktat für denselben Patienten.
4. [ ] **Nächster Patient** → Tastenfeld erscheint; 4711 steht rechts unter „Offene Patienten".
       Zweite Nummer (z. B. 4712) eingeben, diktieren.
5. [ ] **Nächster Patient** → „Ohne Patient weiter" wählen, diktieren → „Gespeichert ohne Patient".
       Danach oben die Nummer 4713 eintragen → Nachfrage „Das Diktat auf dem Bildschirm Patient 4713
       zuordnen?" → **Ja, Patient 4713 zuordnen** → das Diktat gehört jetzt 4713.
       Gegenprobe: noch ein Diktat ohne Nummer, oben 4714 eintragen → **Nein, neues Diktat für 4714**
       → Bildschirm leer, 4714 oben; das Diktat bleibt „ohne Patient" (Schritt 7).
6. [ ] Noch ein Diktat ohne Nummer aufnehmen und **nicht** zuordnen.
7. [ ] Rezeptions-PC: `https://medvox.local/patienten` (mit dem Praxis-Passwort anmelden) → oben
       „Ohne Patient", darunter 4713, 4712, 4711 (jüngstes zuerst), 4711 mit „2 Diktate", alle „offen".
8. [ ] „Ohne Patient" → **Patient zuordnen** → Nummer eingeben → erscheint beim Patienten.
9. [ ] 4711: je Diktat „Text kopieren", „Ziffern kopieren", „Nur Ziffern" → in Evident einfügen:
       dasselbe Format wie am iPad (Prüfung 3).
10. [ ] **Als übertragen markieren** → „übertragen" mit Uhrzeit; Text und Ziffern sind weg. Gegenprobe
       (0 = in Ordnung):
       `sqlite3 ~/Library/Application\ Support/MedVox/medvox.db "select count(*) from dictations d join patients p on p.id = d.patient_id where p.number = '4711'"`
11. [ ] Am nächsten Morgen: die gestern nicht übertragenen Patienten sind aus der Liste
       verschwunden (spätestens 24 Stunden nach dem Diktat), Gegenprobe (0 = in Ordnung):
       `sqlite3 ~/Library/Application\ Support/MedVox/medvox.db "select count(*) from dictations where created_at < cast(strftime('%s','now') as real) - 86400"`
12. [ ] Der Kurzcode („An Rezeption", Prüfung 3) funktioniert unverändert daneben. Diktat für 4715
       aufnehmen, **An Rezeption**, Code am Rezeptions-PC abrufen → in `/patienten` steht 4715 als
       „übertragen", nicht als „offen".
13. [ ] Danach am iPad beim selben Diktat eine Ziffer abwählen → „Dieses Diktat wurde bereits
       übertragen"; in `/patienten` erscheint es **nicht** wieder als offen.
14. [ ] Diktat für 4716, **An Rezeption**, danach am iPad eine Ziffer abwählen, erst dann den alten
       Code abrufen → Rezeption zeigt den Stand des Codes; in `/patienten` bleibt 4716 offen mit dem
       bernsteinfarbenen Hinweis „Schon an der Rezeption abgeholt" (Uhrzeit, damalige Zeilen, „Neu
       seitdem"). **Als übertragen markieren** zeigt die Warnung erst noch einmal. Stattdessen am
       iPad erneut **An Rezeption** und den neuen Code abrufen → über den Ziffern steht dieselbe
       Warnung mit der früheren Abholung und nur der neuen Position unter „Neu seitdem".
15. [ ] Diktat für 4717, **An Rezeption**, Code **nicht** abrufen; im Büro 4717 **Als übertragen
       markieren**; dann den Code abrufen → „Dieses Diktat wurde bereits am … übertragen … – nicht
       erneut in Evident eintragen", keine Ziffern; erneuter Abruf → „Kein Diktat unter diesem Code".

Beobachtet: ______________________________________________________

## 8. Mehrere Behandler an geteilten iPads

Zwei Behandler (hier A und B) und ein iPad; Behandlerliste wie in der Vorbereitung angelegt.

1. [ ] iPad neu öffnen (oder ein anderes iPad) → „Wer diktiert?" erscheint von selbst mit den
       aktiven Behandlern. **A** antippen → oben links „Es diktiert A".
2. [ ] Seite neu laden → weiterhin „Es diktiert A", keine Frage.
3. [ ] Patient 4721 wählen, diktieren. Während der Aufnahme ist die Leiste gesperrt („Diktat von A").
4. [ ] Ergebnis steht noch da: oben auf den Namen tippen, **B** wählen → Bildschirm wird frei,
       „Es diktiert B". Im Büro (`/patienten`) steht das Diktat von 4721 weiterhin bei **A**.
5. [ ] B diktiert für 4721 → im Büro hat 4721 zwei Diktate, eins von A, eins von B; beim Patienten
       „Eröffnet von A"; links unter 4721 „A, B".
6. [ ] B: **An Rezeption** → Code bleibt sichtbar, oben bernsteinfarben „Wer diktiert jetzt?".
       Rezeptions-PC: Code abrufen → neben „Diktat" steht **B**. Am iPad **Neu** → erst die Frage,
       nach dem Tipp auf einen Namen startet die Aufnahme.
7. [ ] Büro: Filter **B** → nur Patienten mit Diktaten von B; **Alle** → wieder alle. „Ziffern
       kopieren" liefert in beiden Fällen dasselbe wie ohne Filter.
8. [ ] iPad 30 Minuten liegen lassen (Wert `MEDVOX_DENTIST_IDLE_S`, Voreinstellung 1800 s) → beim
       nächsten Hinsehen fragt es „Wer diktiert?".
9. [ ] Behandlerliste: B **Inaktiv setzen** → B erscheint am iPad nicht mehr zur Auswahl; das Diktat
       von B im Büro trägt weiterhin den Namen B.
10. [ ] Die Auswahl „Wer diktiert?" bietet kein „Ohne Behandler diktieren", solange aktive Behandler
       in der Liste stehen. Diktate aus der Zeit vor der Behandlerliste (falls noch da) stehen im Büro
       bernsteinfarben als „Behandler fehlt" (beim Diktat und links beim Patienten) und lassen sich wie
       bisher kopieren und übertragen. **Behandler zuordnen** → A wählen → das Diktat steht bei A, der
       Patient „Eröffnet von A"; „Behandler zuordnen" erscheint danach nicht mehr.

Beobachtet: ______________________________________________________

---

## Messprotokoll: 10 echte Diktate

| # | Leistung (Stichwort) | Stoppuhr (s) | Hörfehler im Text | Ziffern richtig / falsch / fehlend |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |
| 6 | | | | |
| 7 | | | | |
| 8 | | | | |
| 9 | | | | |
| 10 | | | | |

Hörfehler, die mehrfach vorkommen, wandern ins Wörterbuch (`server/medvox/lexicon.py`) bzw. in
den Prompt (`infra/whisper/prompt.txt`, danach `make install`).

**Abnahme erteilt:** [ ] ja  [ ] nein, offen: ________________________________
Datum, Unterschrift: ______________________
