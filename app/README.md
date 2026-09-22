# MedVox App (iPad-PWA und Rezeptions-Seite)

Vite + React + TypeScript ohne UI-Framework und ohne weitere Laufzeit-Abhängigkeiten.

## Ansichten

| Pfad | Zweck |
|---|---|
| `/` | Diktat: Anmeldung, Aufnahmeknopf, Pegel/Countdown, Transkript, Ziffern-Chips, Kopieren, „An Rezeption senden“ (Kurzcode + QR) |
| `/transfer` | Rezeption: Kurzcode eingeben (oder per QR-Link `?code=…`), Text/Ziffern/beides kopieren – ohne Anmeldung |
| `/check` | Gerätetest: HTTPS, MediaRecorder-Formate, Mikrofon, Server-Health |

Aufbau in `src/`: `api.ts` (API-Client, deutsche Fehlermeldungen), `router.ts` (Pfad-Switch),
`hooks/useDictation.ts` + `hooks/recorder.ts` (MediaRecorder, MIME `audio/mp4` vor `audio/webm`,
60-s-Limit, „Weiter“-Abschnitte), `qr/encode.ts` (eigener QR-Encoder, Byte-Modus, Stufe L, Version 1–5),
`views/`, `components/`. Der Service Worker (`public/sw.js`) cached nur die App-Hülle, nie `/api/` oder Audio.

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
npm test           # node --test (QR-Encoder, Router, Kurzcode-Format), Node ≥ 22.18
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
4. Aus der App `/check` öffnen (Link „Gerätetest“): alle Zeilen müssen ✓ zeigen; „Mikrofon testen“
   antippen und die Freigabe erteilen. Wird das Mikrofon verweigert: *Einstellungen → Safari →
   Mikrofon* bzw. *Einstellungen → MedVox → Mikrofon* auf „Erlauben“ setzen.
5. Anmelden, Aufnehmen, „Zahn drei sechs …“ diktieren, Stopp: Transkript erscheint in großer Schrift.
   „Weiter“ hängt einen weiteren Abschnitt an. Kurz vor 60 s wird der Abschnitt automatisch beendet und
   hochgeladen; die App zeigt dann das bisherige Transkript mit „Weiter“ (nächsten Abschnitt anhängen)
   und „Neues Diktat“ (setzt nur zurück; die Aufnahme beginnt erst mit „Aufnehmen“). „Aufnehmen“ aus dem
   Ruhezustand beginnt immer ein neues Diktat. Antwortet der Server mit „nicht angemeldet“ (Sitzung
   abgelaufen), erscheint die Anmeldung; Transkript und noch nicht übertragene Abschnitte bleiben
   erhalten. Nach der Anmeldung steht das Diktat wieder als „fortsetzbar“ bereit: „Weiter“ überträgt die
   wartenden Abschnitte in Aufnahmereihenfolge und nimmt weiter auf. Auch jeder andere Fehler beim
   Übertragen (z. B. Whisper nicht bereit, WLAN weg) behält den Abschnitt: die Meldung erscheint mit
   „Erneut senden“; verworfen wird ein Abschnitt nur über „Verwerfen“ bzw. „Neues Diktat“.
6. „An Rezeption senden“: 6-stelligen Code am Rezeptions-PC unter `https://medvox.local/transfer`
   eingeben oder den QR-Code mit dem Handy scannen; dort „Text“, „Ziffern“ oder „beides“ kopieren.
