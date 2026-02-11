# MedVox

**KI-gesteuerte Sprachdokumentation fuer Zahnarztpraxen**

MedVox ermoeglicht Zahnaerzten, waehrend der Behandlung per Spracheingabe zu dokumentieren -- haendefrei und effizient. Das System transkribiert gesprochene Befunde, extrahiert automatisch BEMA- und GOZ-Abrechnungsziffern und bietet Copy-to-Clipboard fuer die direkte Uebernahme ins Evident PMS.

## Features

- **Spracheingabe mit Transkription** -- Google Cloud Speech-to-Text fuer praezise deutsche Zahnmedizin-Erkennung
- **BEMA/GOZ-Abrechnung** -- Automatische Extraktion von Abrechnungsziffern mit Zusatzleistungen-Erkennung fuer Kassenpatienten
- **Evident-Export** -- Kopiere Abrechnungsziffern im Evident-kompatiblen Format (z.B. "01, 8, 13c, 2080")
- **Copy-to-Clipboard** -- Transkription und Billing Codes direkt in die Zwischenablage kopieren
- **Settings-Panel** -- Zahnarzt-Name, Standard-Abrechnung, GOZ-Faktor, Auto-Stopp-Dauer persistent konfigurierbar
- **Farbkodierte Ziffern** -- BEMA (blau), GOZ (gruen), Zusatzleistungen (lila)
- **Modernes UI** -- Professionelles Dental-Branding mit Animationen und responsivem Design

## Architektur

```
Frontend (React/Vite)          Backend (FastAPI)            Externe Services
---------------------          ----------------            ----------------
Mikrofon-Aufnahme      --->    Audio-Validierung    --->   Google Cloud STT
BEMA/GOZ-Toggle        --->    Transkription         --->   Google Gemini 3
Transkription-Anzeige  <---    LLM-Extraktion        --->   (Evident PMS)
Billing Codes + Copy   <---    Billing Code Mapping
Settings (localStorage)
```

## Tech Stack

### Backend
- **FastAPI** -- Python Web-Framework mit automatischer API-Dokumentation
- **Google Cloud Speech-to-Text** -- Spracherkennung optimiert fuer deutsche Zahnmedizin-Terminologie
- **Google Gemini 3 Flash/Pro** -- LLM fuer intelligente Extraktion von Behandlungen und Abrechnungsziffern
- **SQLite** -- Lokale Datenbank (Standard)
- **Pydantic** -- Datenvalidierung und Settings-Management

### Frontend
- **React 18** mit **TypeScript** -- UI-Framework
- **Vite** -- Schnelles Build-System (ersetzt Create React App)
- **Tailwind CSS** -- Utility-first CSS mit erweitertem Dental-Theme
- **Lucide React** -- Icon-Bibliothek
- **Web Audio API** -- Mikrofon-Aufnahme im Browser

## Installation

### Voraussetzungen
- Python 3.12+
- Node.js 18+
- Google Cloud API Key (fuer Speech-to-Text)
- Google Gemini API Key (fuer LLM-Extraktion)

### Backend

```bash
# Repository klonen
git clone https://github.com/amorfati-dev/MedVox.git
cd MedVox

# Virtuelle Umgebung erstellen
python3.12 -m venv venv
source venv/bin/activate

# Abhaengigkeiten installieren
pip install -r backend/requirements.txt

# Umgebungsvariablen konfigurieren
cp env.example .env
# .env bearbeiten: API Keys eintragen

# Backend starten
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend laeuft unter `http://localhost:8000`
API-Dokumentation unter `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend laeuft unter `http://localhost:3000`

## Konfiguration

### Umgebungsvariablen (.env)

| Variable | Beschreibung | Standard |
|----------|-------------|---------|
| `GOOGLE_CLOUD_API_KEY` | Google Cloud API Key fuer Speech-to-Text | Erforderlich |
| `GOOGLE_GEMINI_API_KEY` | Google Gemini API Key fuer LLM | Erforderlich |
| `LLM_MODEL` | Gemini-Modell fuer Extraktion | `gemini-3-flash-preview` |
| `LLM_TEMPERATURE` | LLM-Temperatur (niedriger = konsistenter) | `0.1` |
| `ADVANCED_LLM_MODEL` | Modell fuer komplexe Faelle | `gemini-3-pro-preview` |
| `DATABASE_URL` | Datenbank-Verbindung | `sqlite:///./medvox.db` |
| `DEBUG` | Debug-Modus | `true` |
| `EVIDENT_API_URL` | Evident PMS API Endpunkt | Optional |
| `EVIDENT_API_KEY` | Evident PMS API Key | Optional |

### App-Einstellungen (im Browser)

Ueber das Settings-Panel (Zahnrad-Icon) konfigurierbar:
- Zahnarzt-Name
- Standard-Abrechnungstyp (BEMA/GOZ)
- GOZ-Steigerungsfaktor (Standard: 2,3)
- Auto-Stopp-Dauer (Standard: 30 Sekunden)
- API-Endpunkt

Einstellungen werden in `localStorage` gespeichert.

## Projektstruktur

```
MedVox/
├── backend/
│   ├── app/
│   │   ├── api/v1/              # API Endpoints (documentation, audio)
│   │   ├── core/                # Config, Security
│   │   ├── schemas/             # Pydantic Schemas (BillingCode, DentalDocumentation)
│   │   ├── services/            # Business Logic
│   │   │   ├── llm_processor.py           # Gemini LLM Integration
│   │   │   ├── google_speech_service.py   # Google Cloud STT
│   │   │   ├── documentation_processor.py # Transkription -> Abrechnung
│   │   │   └── audio_service.py           # Audio-Validierung
│   │   └── utils/               # Audio-Utilities
│   └── data/                    # BEMA/GOZ Code-Datenbank
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Hauptkomponente (Aufnahme, Transkription)
│   │   ├── components/
│   │   │   ├── BillingCodesDisplay.tsx  # Abrechnungsziffern + Evident-Copy
│   │   │   └── SettingsPanel.tsx        # Einstellungen (Slide-Panel)
│   │   ├── types/index.ts       # TypeScript Types
│   │   ├── main.tsx             # Vite Entry Point
│   │   └── index.css            # Tailwind + Custom Styles
│   ├── vite.config.ts           # Vite-Konfiguration mit API Proxy
│   ├── tailwind.config.js       # Erweitertes Dental-Theme
│   └── public/
│       └── logo.png             # MedVox Logo
└── env.example                  # Beispiel-Umgebungsvariablen
```

## API-Dokumentation

Wenn der Server laeuft:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Wichtigste Endpoints

| Methode | Pfad | Beschreibung |
|---------|------|-------------|
| POST | `/api/v1/documentation/process-audio` | Audio hochladen und verarbeiten |
| POST | `/api/v1/documentation/process-text` | Text direkt verarbeiten |
| GET | `/api/v1/documentation/supported-formats` | Unterstuetzte Audio-Formate |
| GET | `/health` | Health Check |

## Roadmap

- [x] BEMA/GOZ-Klassifikation mit Zusatzleistungen
- [x] Evident-kompatibles Copy-Format
- [x] Settings-Panel mit localStorage
- [x] Vite-Migration und modernes UI
- [x] Gemini 3 Flash/Pro Integration
- [ ] PWA-Manifest fuer Installierbarkeit
- [ ] Dark Mode
- [ ] Manuelle Code-Eingabe
- [ ] Evident PMS-Integration (API)
- [ ] Multi-Stage-Pipeline fuer komplexe Faelle
- [ ] User-Authentication
- [ ] Mobile App (iOS/Android)

## Lizenz

Dieses Projekt steht unter der MIT-Lizenz -- siehe [LICENSE](LICENSE).

---

**Entwickelt fuer Zahnarztpraxen**
