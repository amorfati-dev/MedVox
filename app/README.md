# MedVox App (iPad-PWA und Rezeptions-Seite)

Vite + React + TypeScript ohne UI-Framework und ohne weitere Laufzeit-Abhängigkeiten.

## Ansichten

| Pfad | Zweck |
|---|---|
| `/` | Diktat: Anmeldung, Aufnahmeknopf, Pegel/Countdown, Transkript, Ziffern-Chips, Kopieren, „An Rezeption senden“ (Kurzcode + QR) |
| `/transfer` | Rezeption: Kurzcode eingeben (oder per QR-Link `?code=…`), Text/Ziffern/beides kopieren – ohne Anmeldung |
| `/check` | Gerätetest: HTTPS, Installiert-als-App, MediaRecorder-Formate, Mikrofon, Server-Health, Sitzung |

Aufbau in `src/`: `api.ts` (API-Client, deutsche Fehlermeldungen), `router.ts` (Pfad-Switch),
`hooks/useDictation.ts` + `hooks/recorder.ts` (MediaRecorder, MIME `audio/mp4` vor `audio/webm`,
60-s-Limit, „Weiter“-Abschnitte), `qr/encode.ts` (eigener QR-Encoder, Byte-Modus, Stufe L, Version 1–5),
`views/`, `components/`. Der Service Worker (`public/sw.js`) cached nur die App-Hülle, nie `/api/` oder Audio.

## Entwicklung

```sh
npm install
npm run dev        # /api → http://127.0.0.1:8000 (Server: `make dev`)
npm run dev:mock   # ohne Server: Dev-Mock der API in dev/mockApi.ts, Passwort „praxis“
npm run typecheck
npm test           # node --test (QR-Encoder, Router, Kurzcode-Format)
npm run build      # dist/; VITE_API_BASE=https://medvox.local für eine andere API-Origin
```

Der Mock existiert nur, bis die Server-Endpunkte (Login, Transcribe, Transfer) gemerged sind; er landet nie im Build.

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
   „Weiter“ hängt einen weiteren Abschnitt an; bei 60 s wird automatisch beendet und hochgeladen.
6. „An Rezeption senden“: 6-stelligen Code am Rezeptions-PC unter `https://medvox.local/transfer`
   eingeben oder den QR-Code mit dem Handy scannen; dort „Text“, „Ziffern“ oder „beides“ kopieren.
