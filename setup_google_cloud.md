# Google Cloud Speech-to-Text Setup für MedVox

## 🚀 Übersicht

MedVox nutzt jetzt **Google Cloud Speech-to-Text** als primäres STT-System anstelle von OpenAI Whisper für:
- **Höhere Genauigkeit** bei deutscher Sprache
- **Spezielle medizinische Terminologie** Unterstützung
- **Bessere Performance** bei Fachbegriffen

## 📋 Voraussetzungen

1. **Google Cloud Account** mit aktivierter Billing
2. **Speech-to-Text API** aktiviert
3. **API Key** generiert

## 🔧 Setup Schritte

### 1. Google Cloud Console Setup

1. Gehen Sie zu [Google Cloud Console](https://console.cloud.google.com/)
2. Erstellen Sie ein neues Projekt oder wählen Sie ein bestehendes
3. Aktivieren Sie die **Speech-to-Text API**:
   ```
   APIs & Services → Library → Speech-to-Text API → Enable
   ```

### 2. API Key erstellen

1. Gehen Sie zu **APIs & Services → Credentials**
2. Klicken Sie **Create Credentials → API Key**
3. Kopieren Sie den generierten API Key
4. **Empfohlen**: Beschränken Sie den Key auf Speech-to-Text API

### 3. Umgebungsvariablen setzen

Bearbeiten Sie Ihre `.env` Datei:

```env
# Google Cloud Speech-to-Text (Primär)
GOOGLE_CLOUD_API_KEY=your-actual-api-key-here
GOOGLE_CLOUD_PROJECT_ID=your-project-id-here

# OpenAI Whisper (Fallback - optional)
OPENAI_API_KEY=your-openai-key-if-available
```

### 4. Dependencies installieren

```bash
cd MedVox/backend
source ../venv/bin/activate
pip install -r requirements.txt
```

### 5. Backend neu starten

```bash
# Im MedVox/backend Verzeichnis
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## ✅ Verifizierung

1. **Backend Logs prüfen**: Sie sollten sehen:
   ```
   Using Google Cloud Speech-to-Text API
   ```

2. **Frontend testen**: Machen Sie eine Aufnahme und prüfen Sie die Transkription

## 🎯 Optimierungen für deutsche Zahnmedizin

Das System ist bereits konfiguriert mit:

- **Deutsches Sprachmodell**: `de-DE` mit `de-AT`, `de-CH` Varianten
- **Medizinisches Modell**: `medical_conversation`
- **Dental-Terminologie Boost**: 60+ zahnmedizinische Fachbegriffe
- **Enhanced Recognition**: Automatische Zeichensetzung, Wort-Konfidenz
- **WebM Support**: Direkte Unterstützung für Browser-Audio

## 🔄 Fallback-System

```
Google Cloud Speech → OpenAI Whisper → Error
      (Primär)           (Fallback)
```

Wenn Google Cloud nicht verfügbar ist, fällt das System automatisch auf OpenAI Whisper zurück.

## 💰 Kosten

- **Google Cloud Speech**: ~$0.006 pro 15 Sekunden Audio
- **Deutlich günstiger** als OpenAI Whisper für kontinuierliche Nutzung
- **Bessere Qualität** bei deutschen medizinischen Begriffen

## 🛠️ Troubleshooting

### Problem: "Google Cloud API key not configured"
**Lösung**: Prüfen Sie die `.env` Datei und starten Sie das Backend neu

### Problem: "ImportError: google-cloud-speech"
**Lösung**: 
```bash
pip install google-cloud-speech==2.24.1
```

### Problem: "Authentication failed"
**Lösung**: Prüfen Sie ob:
- API Key korrekt ist
- Speech-to-Text API aktiviert ist
- Billing Account verknüpft ist

## 📊 Erwartete Verbesserungen

- **Genauigkeit**: +15-25% bei deutschen Fachbegriffen
- **Confidence**: Höhere Konfidenz-Scores
- **Speed**: Ähnliche oder bessere Performance
- **Reliability**: Weniger Fehlinterpretationen bei "Zahn 36", "MOD", etc.

## 🔧 Konfiguration anpassen

In `config.py` können Sie anpassen:
- `language_code`: Andere Sprachen
- `sample_rate`: Audio-Qualität
- `dental_speech_contexts`: Zusätzliche Fachbegriffe

## ✨ Neue Features

- **Wort-Level Timestamps**: Präzise Timing-Informationen
- **Konfidenz-Scores**: Pro Wort und Segment
- **Automatische Zeichensetzung**: Bessere Lesbarkeit
- **Multi-Speaker Support**: Zukünftige Erweiterung möglich 