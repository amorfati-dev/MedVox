# MedVox App (iPad-PWA und Rezeptions-Seite)

Vite + React + TypeScript ohne UI-Framework und ohne weitere Laufzeit-Abhängigkeiten.

## Ansichten

| Pfad | Zweck |
|---|---|
| `/` | Diktat: Anmeldung; quer (≥ 900 px) links Steuerung (aktiver Patient mit Evident-Nummer und Tastenfeld, Schalter Kassenpatient/Privatpatient, Statusfeld, Aufnahmeknopf), rechts Ergebnis (Transkript, Liste nach Zahn mit Begründung und Prüfhinweis, Mehrkosten-Rahmen, Zuzahlungs-Optionen, Geplantes, Hinweise), Leiste Text · Ziffern · An Rezeption (Kurzcode + QR); hoch untereinander |
| `/patienten` | Büro (mit Anmeldung): Patienten von heute und Diktate „ohne Patient“, je Diktat Text/Ziffern/Nur Ziffern kopieren, zuordnen, „Als übertragen markieren“ (löscht den Inhalt) |
| `/transfer` | Rezeption: Kurzcode eingeben (oder per QR-Link `?code=…`), Text/Ziffern/beides kopieren – ohne Anmeldung |
| `/check` | Gerätetest: HTTPS, MediaRecorder-Formate, Mikrofon, Server-Health |

Aufbau in `src/`: `api.ts` (API-Client, deutsche Fehlermeldungen, Evident-Kopierformat), `router.ts` (Pfad-Switch),
`hooks/useDictation.ts` + `hooks/useUploadQueue.ts` + `hooks/recorder.ts` (MediaRecorder, MIME `audio/mp4` vor `audio/webm`,
60-s-Limit, Abschnitte anhängen), `hooks/usePatientType.ts` (Patiententyp im `localStorage`), `qr/encode.ts` (eigener QR-Encoder, Byte-Modus, Stufe L, Version 1–5),
`status.ts` (Anzeigezustand aus useDictation), `result.ts` (Ergebnisliste nach Zahn, Zuzahlungs-Optionen im Kopierformat),
`patients.ts` + `hooks/useDictationSave.ts` + `hooks/usePatientList.ts` (Diktate je Patient speichern, Büroliste; Kopiertext
mit denselben Funktionen wie am iPad),
`theme.ts` (Auto/Hell/Dunkel je Gerät), `styles/` (`tokens.css` mit allen Farben hell/dunkel), `views/`, `components/`. Der Service Worker (`public/sw.js`) cached nur die App-Hülle, nie `/api/` oder Audio.

Icons: `public/icon.svg` ist die Quelle; `public/apple-touch-icon.png` (180×180, iPadOS nimmt kein SVG als
Home-Bildschirm-Icon) wird daraus einmalig ohne abgerundete Ecken gerendert – iPadOS rundet selbst:

```sh
sed 's/ rx="96"//' public/icon.svg > /tmp/icon.svg && sips -s format png -z 180 180 /tmp/icon.svg --out public/apple-touch-icon.png
```

## Entwicklung

```sh
npm install
npm run dev        # /api → http://127.0.0.1:8000 (Server: `make dev`)
npm run typecheck
npm test           # node --test (QR-Encoder, Router, Kurzcode-Format, Ziffernart, Patiententyp, Ergebnisliste,
                   # Kopierformat gegen test/fixtures/evident-golden.json, auch im Büro), Node ≥ 22.18
npm run build      # dist/
```

Entwickelt wird gegen den echten Server (`server/`, `make dev`); im Betrieb liefert Caddy App und API
über dieselbe Origin (`https://medvox.local`), die App nutzt nur relative `/api/…`-Pfade.

## Manueller Test auf dem iPad

1. CA-Profil installieren: das mkcert-Root-Zertifikat (siehe `infra/`) per AirDrop/Mail auf das iPad
   bringen, unter *Einstellungen → Allgemein → VPN & Geräteverwaltung* installieren und unter
   *Einstellungen → Allgemein → Info → Zertifikatsvertrauenseinstellungen* volles Vertrauen aktivieren.
2. In Safari `https://medvox.local` öffnen (kein Schloss-Warnhinweis mehr).
3. *Teilen → Zum Home-Bildschirm* – die App startet dann im Vollbild (standalone).
4. Aus der App `/check` öffnen (⋯-Menü → „Gerätetest“): Banner „Alles bereit“, jede Kachel ✓;
   „Mikrofon testen“ antippen und die Freigabe erteilen. Wird das Mikrofon verweigert: *Einstellungen → Safari →
   Mikrofon* bzw. *Einstellungen → MedVox → Mikrofon* auf „Erlauben“ setzen.
5. Anmelden, Patiententyp wählen (Kassenpatient/Privatpatient; bleibt gespeichert und gilt für das ganze
   Diktat, während einer Aufnahme ist der Schalter gesperrt), Aufnehmen, „Zahn drei sechs …“ diktieren,
   Stopp: das Statusfeld zeigt „Ergebnis da“, rechts Transkript und die Liste nach Zahn mit dem Typ, für
   den sie berechnet wurde („Kassenpatient“); Zuzahlungen sind indigo, Kassenanteil und Zuzahlung am
   selben Zahn stehen in einem Rahmen, Zuzahlungs-Optionen gestrichelt und abgewählt (ein Tipp übernimmt sie).
   Während der Aufnahme hängt „Abschnitt anhängen“ einen weiteren Abschnitt an. Kurz vor 60 s wird der
   Abschnitt automatisch beendet und hochgeladen; die App zeigt dann „Unterbrochen – nichts verloren“ mit
   „Weiter aufnehmen“ (nächsten Abschnitt anhängen) und „Verwerfen“ (löscht das Diktat, auch beim Patienten).
   „Aufnehmen“ bzw. „Neu“ beginnt immer ein neues Diktat für den aktiven Patienten, „Nächster Patient“ leert
   den Bildschirm und fragt die nächste Nummer ab. Antwortet der Server mit
   „nicht angemeldet“ (Sitzung abgelaufen), erscheint die Anmeldung; Transkript und noch nicht übertragene
   Abschnitte bleiben erhalten. Nach der Anmeldung steht das Diktat wieder als „fortsetzbar“ bereit:
   „Weiter aufnehmen“ überträgt die wartenden Abschnitte in Aufnahmereihenfolge und nimmt weiter auf. Auch
   jeder andere Fehler beim Übertragen (z. B. Whisper nicht bereit, WLAN weg) behält den Abschnitt: die
   Meldung erscheint mit „Erneut senden“. Lehnt der Server einen Abschnitt dauerhaft ab (zu lang, falsches
   Format), erscheint „Diesen Abschnitt verwerfen“ – nur dieser Abschnitt entfällt, der bisherige Text
   bleibt; das ganze Diktat verwirft nur „Ganzes Diktat verwerfen“, „Verwerfen“ bzw. „Nächster Patient“.
6. Patient: oben links antippen, Nummer eingeben (oder einen offenen Patienten antippen); nach dem Diktat
   steht darunter „Gespeichert“. Ohne Nummer diktiert: „Gespeichert ohne Patient“, Nummer oben nachtragen.
   Am PC `https://medvox.local/patienten` öffnen: der Patient steht mit Anzahl und Uhrzeit oben in der Liste.
7. „An Rezeption“: 6-stelligen Code am Rezeptions-PC unter `https://medvox.local/transfer`
   eingeben oder den QR-Code mit dem Handy scannen; dort „Text“, „Ziffern“ oder „beides“ kopieren.
