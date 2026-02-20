# QR-Code Transfer Feature

**Status**: ✅ MVP Complete
**Version**: 1.0.0
**Datum**: 2026-02-12

## 🎯 Problem & Lösung

### Problem
Arzt dokumentiert im Behandlungszimmer, muss aber zum Rezeptionsrechner gehen um Codes in PVS (Praxisverwaltungssystem) einzugeben.

### Lösung
**QR-Code basierter Transfer zwischen Geräten**
- Behandlungszimmer: iPad/Tablet generiert QR-Code
- Rezeption: PC scannt QR-Code → Codes werden angezeigt
- Copy & Paste in beliebiges PVS (Evident, Z1, CharlieOS, etc.)

---

## 🏗️ Architektur

```
┌─────────────────────┐
│  Behandlungsraum    │
│  (iPad/Tablet)      │
│                     │
│  1. Aufnahme        │
│  2. BEMA/GOZ-Codes  │
│  3. QR-Code erstell │
└──────────┬──────────┘
           │
           │ QR-Code enthält:
           │ Session-ID (UUID)
           │
           ▼
┌─────────────────────┐
│   Rezeption (PC)    │
│                     │
│  1. QR scannen      │
│  2. Browser öffnet  │
│  3. Session abrufen │
│  4. Codes kopieren  │
│  5. In PVS einfügen │
└─────────────────────┘
```

---

## 🔧 Technische Details

### Backend

#### Transfer Service
```python
# app/services/transfer_service.py
class TransferService:
    - create_session()     # Session erstellen
    - get_session()        # Session abrufen (one-time)
    - generate_qr_code()   # QR-Code als base64
    - get_transfer_url()   # URL für Transfer-Page
```

**Features:**
- In-Memory Storage (TTLCache)
- Auto-Expiration (5 Minuten)
- One-Time-Use (Security)
- UUID-basierte Sessions

#### API Endpoints
```
POST /api/v1/transfer/create
  → Erstellt Session, gibt QR-Code zurück

GET /api/v1/transfer/{session_id}
  → Ruft Session ab (one-time use)

GET /api/v1/transfer/health
  → Health Check
```

### Frontend

#### Components
```
QRCodeModal.tsx         (134 Zeilen)
  - QR-Code Display
  - Countdown Timer
  - Anleitung

TransferPage.tsx        (323 Zeilen)
  - Session abrufen
  - Codes anzeigen
  - Copy-Funktionen
  - Error Handling
```

#### Routes
```
/                       → App (Hauptseite)
/transfer/:sessionId    → TransferPage (QR-Scan)
```

---

## 🔒 Security & DSGVO

### One-Time-Use
✅ Session wird nach **erstem** Abruf gelöscht
✅ Verhindert mehrfaches Scannen

### Auto-Expiration
✅ Sessions laufen nach **5 Minuten** ab
✅ Automatische Löschung via TTLCache
✅ DSGVO-konform: Keine Daten-Leaks

### Datensparsamkeit
✅ QR-Code enthält **nur Session-ID**
✅ Keine Patientendaten im QR-Code
✅ Keine Billing-Codes im QR-Code
✅ Daten nur temporär gespeichert

### Session-ID Format
```
550e8400-e29b-41d4-a716-446655440000
```
- UUID v4 (random)
- Nicht ratebar
- Keine sequentiellen IDs

---

## 📊 Tests

### Backend Tests
```bash
# Service Tests (17)
pytest tests/test_transfer_service.py

# API Tests (23)
pytest tests/test_transfer_api.py

# Alle Transfer Tests (40)
pytest tests/test_transfer*.py
```

**Coverage**: 100% der Kernfunktionalität

### Test-Kategorien
- ✅ Session Creation
- ✅ Session Retrieval
- ✅ Expiration
- ✅ QR Code Generation
- ✅ Cleanup
- ✅ DSGVO Compliance
- ✅ API Validation
- ✅ Security

---

## 🚀 Deployment

### Backend
```bash
cd backend

# Dependencies installieren
pip install qrcode Pillow cachetools

# Server starten
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend

# Dependencies installieren
npm install react-router-dom

# Dev Server starten
npm run dev
```

### Production
```bash
# Backend
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend
npm run build
# Serve dist/ folder mit nginx/caddy
```

---

## 💡 Usage

### 1. Aufnahme erstellen (Behandlungszimmer)
```typescript
// User nimmt auf → Codes werden generiert
// Automatisch in App.tsx nach processAudio()
```

### 2. QR-Code generieren
```typescript
// User klickt "QR-Code erstellen"
const session = await createTransferSession();
// QRCodeModal wird angezeigt
```

### 3. QR-Code scannen (Rezeption)
```
1. Smartphone/Tablet QR-Scanner öffnen
2. QR-Code scannen
3. Browser öffnet automatisch:
   https://medvox.app/transfer/550e8400-...
4. Transfer-Page lädt Daten
```

### 4. Codes übertragen
```
1. Button "Alle kopieren" klicken
2. In PVS (Evident/Z1/etc.) einfügen
3. Format: "13a, 2080, Ä5004, ..."
```

---

## 🎨 UI/UX

### QR-Code Modal
- ✅ Großer, gut scannbarer QR-Code
- ✅ Countdown Timer (visuell)
- ✅ Schritt-für-Schritt Anleitung
- ✅ Manueller Link als Fallback
- ✅ ESC zum Schließen

### Transfer Page
- ✅ **Schnell-Übertragung**: Ein-Klick-Copy
- ✅ Evident-Format: `13a, 2080, Ä5004`
- ✅ Farbcodierung: BEMA (Blau), GOZ (Grün)
- ✅ Zusatzleistungen markiert
- ✅ Einzelne Codes kopierbar (Hover)
- ✅ Transkription anzeigen
- ✅ Error-States mit hilfreichen Tipps

---

## 🔮 Future Enhancements

### Phase 2 (Optional)
- [ ] Bluetooth Low Energy (BLE) Auto-Transfer
- [ ] Browser-Extension für Auto-Fill
- [ ] Netzwerk-Clipboard (mDNS/WebSockets)
- [ ] Email/SMS-Benachrichtigung

### Nice-to-Have
- [ ] QR-Code Customization (Logo, Farben)
- [ ] Session-Historie (letzte 5 Transfers)
- [ ] Analytics (wie oft gescannt?)
- [ ] Push-Notifications (Transfer ready)

---

## 📝 Changelog

### v1.0.0 (2026-02-12)
✅ MVP Release
- Transfer Service implementiert
- API Endpoints erstellt
- Frontend-Integration
- QRCodeModal Component
- TransferPage Component
- React Router Setup
- 40 Tests passing

---

## 🤝 Contributing

### Code-Stil
- **TDD**: Tests zuerst, dann Implementation
- **KISS**: Keep It Simple, Stupid
- **Pragmatisch**: MVP über Feature-Bloat

### Git Workflow
```bash
git checkout -b feature/transfer-enhancement
# ... changes ...
git commit -m "feat: add XYZ to transfer"
git push origin feature/transfer-enhancement
```

---

**Made with ❤️ for dental professionals**

**Team**: Claude (AI Engineer) + Martin (Product Owner)
