# MedVox Project Structure

## Directory Structure
```
medvox/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI application entry point
│   │   ├── config.py            # Configuration settings
│   │   ├── database.py          # Database connection setup
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py     # Authentication endpoints
│   │   │   │   ├── evident/    # evident integration endpoints
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── patients.py    # Patient import/sync
│   │   │   │   │   ├── export.py      # Document export
│   │   │   │   │   └── sync.py        # Data synchronization
│   │   │   │   ├── recordings.py
│   │   │   │   ├── transcriptions.py
│   │   │   │   └── documents.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── security.py     # JWT, password hashing
│   │   │   ├── deps.py         # Dependencies
│   │   │   └── exceptions.py   # Custom exceptions
│   │   ├── integrations/
│   │   │   ├── __init__.py
│   │   │   ├── evident/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── client.py   # evident API client
│   │   │   │   ├── models.py   # evident data models
│   │   │   │   ├── mappers.py  # Data transformation
│   │   │   │   └── exceptions.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── patient_ref.py  # Patient references to evident
│   │   │   ├── recording.py
│   │   │   ├── transcription.py
│   │   │   ├── document.py
│   │   │   └── export_log.py   # Track exports to evident
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── patient.py
│   │   │   ├── recording.py
│   │   │   ├── transcription.py
│   │   │   ├── document.py
│   │   │   └── evident.py      # evident-specific schemas
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py
│   │   │   ├── evident_service.py      # Main evident integration
│   │   │   ├── patient_sync_service.py # Patient synchronization
│   │   │   ├── recording_service.py
│   │   │   ├── transcription_service.py
│   │   │   ├── document_service.py
│   │   │   ├── export_service.py       # Export to evident
│   │   │   └── ai_service.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── audio.py        # Audio processing utilities
│   │       ├── templates.py    # Document templates
│   │       ├── validators.py   # Input validators
│   │       └── evident_formatter.py # evident format helpers
│   ├── migrations/              # Alembic migrations
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_evident_integration.py
│   │   ├── test_recordings.py
│   │   └── test_services.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── public/
│   │   ├── index.html
│   │   └── favicon.ico
│   ├── src/
│   │   ├── components/
│   │   │   ├── auth/
│   │   │   │   ├── LoginForm.tsx
│   │   │   │   └── ProtectedRoute.tsx
│   │   │   ├── evident/
│   │   │   │   ├── PatientSelector.tsx
│   │   │   │   ├── PatientInfo.tsx
│   │   │   │   ├── ExportDialog.tsx
│   │   │   │   └── SyncStatus.tsx
│   │   │   ├── recording/
│   │   │   │   ├── RecordButton.tsx
│   │   │   │   ├── AudioVisualizer.tsx
│   │   │   │   └── RecordingStatus.tsx
│   │   │   ├── transcription/
│   │   │   │   ├── TranscriptionEditor.tsx
│   │   │   │   └── TranscriptionPreview.tsx
│   │   │   ├── document/
│   │   │   │   ├── DocumentGenerator.tsx
│   │   │   │   ├── DocumentPreview.tsx
│   │   │   │   └── EvidentPreview.tsx
│   │   │   └── layout/
│   │   │       ├── Header.tsx
│   │   │       ├── Sidebar.tsx
│   │   │       └── Layout.tsx
│   │   ├── pages/
│   │   │   ├── Login.tsx
│   │   │   ├── Dashboard.tsx
│   │   │   ├── PatientSelect.tsx # New: Select patient from evident
│   │   │   ├── Recording.tsx
│   │   │   └── Documents.tsx
│   │   ├── services/
│   │   │   ├── api.ts          # Axios config
│   │   │   ├── auth.ts
│   │   │   ├── evident.ts      # evident API service
│   │   │   ├── recording.ts
│   │   │   └── transcription.ts
│   │   ├── hooks/
│   │   │   ├── useAuth.ts
│   │   │   ├── useEvidentPatient.ts
│   │   │   ├── useRecording.ts
│   │   │   └── useTranscription.ts
│   │   ├── store/
│   │   │   ├── authSlice.ts
│   │   │   ├── evidentSlice.ts # evident state management
│   │   │   ├── recordingSlice.ts
│   │   │   └── store.ts
│   │   ├── types/
│   │   │   ├── index.ts
│   │   │   ├── api.ts
│   │   │   └── evident.ts      # evident type definitions
│   │   ├── utils/
│   │   │   ├── constants.ts
│   │   │   └── helpers.ts
│   │   ├── App.tsx
│   │   └── index.tsx
│   ├── package.json
│   ├── tsconfig.json
│   ├── Dockerfile
│   └── .env.example
├── docker/
│   ├── docker-compose.yml
│   ├── postgres/
│   │   └── init.sql
│   └── nginx/
│       └── nginx.conf
├── docs/
│   ├── API.md
│   ├── EVIDENT_INTEGRATION.md  # evident integration guide
│   ├── SETUP.md
│   ├── DEPLOYMENT.md
│   └── SECURITY.md
├── scripts/
│   ├── setup.sh
│   ├── test.sh
│   ├── test-evident.sh         # Test evident integration
│   └── deploy.sh
├── .github/
│   └── workflows/
│       ├── test.yml
│       └── deploy.yml
├── .gitignore
├── README.md
└── LICENSE
```

## Key Files Description - evident Integration

### Backend Integration Components

#### `backend/app/integrations/evident/`
Core evident integration module containing:
- **client.py**: API client for evident communication
- **models.py**: Data models matching evident's schema
- **mappers.py**: Transform data between MedVox and evident formats

#### `backend/app/services/evident_service.py`
Main service orchestrating evident operations:
- Patient data import
- Document export
- Authentication with evident
- Error handling and retries

#### `backend/app/api/v1/evident/`
REST endpoints for evident operations:
- `/patients`: Import and sync patient data
- `/export`: Export documents to evident
- `/sync`: Manual sync trigger

### Frontend Integration Components

#### `frontend/src/components/evident/`
UI components for evident integration:
- **PatientSelector**: Search and select patients from evident
- **ExportDialog**: Confirm and track document exports
- **SyncStatus**: Display sync status and errors

#### `frontend/src/pages/PatientSelect.tsx`
New workflow page where users select a patient from evident before recording

## Environment Variables Update

### Backend (.env)
```env
# Database
DATABASE_URL=postgresql://user:password@localhost/medvox

# Security
SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI Services
OPENAI_API_KEY=your-openai-key
WHISPER_MODEL=large-v3

# evident Integration
EVIDENT_API_URL=https://api.evident.de/v1
EVIDENT_API_KEY=your-evident-api-key
EVIDENT_PRACTICE_ID=your-practice-id
EVIDENT_SYNC_INTERVAL=300  # seconds

# Storage
UPLOAD_PATH=/app/uploads
MAX_UPLOAD_SIZE=100MB

# CORS
ALLOWED_ORIGINS=http://localhost:3000
```

### Frontend (.env)
```env
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WEBSOCKET_URL=ws://localhost:8000
REACT_APP_EVIDENT_ENABLED=true
```

## Data Flow with evident

### Patient Selection Flow
1. User logs in to MedVox
2. System fetches patient list from evident
3. User searches/selects patient
4. Patient context loaded for session

### Recording to Export Flow
1. Patient selected from evident
2. Voice recording created
3. Transcription generated
4. Document created in evident format
5. One-click export to evident patient record
6. Export logged and confirmed

### Data Storage Strategy
- **Minimal Storage**: Only store references to evident data
- **No Duplication**: Patient data remains in evident
- **Temporary Files**: Audio and working files deleted after export
- **Audit Trail**: Keep logs of all evident interactions

## Development Workflow Updates

1. **evident Setup**
   ```bash
   # Set evident credentials
   cp .env.example .env
   # Add EVIDENT_API_KEY and other credentials
   
   # Test evident connection
   ./scripts/test-evident.sh
   ```

2. **Testing with evident**
   ```bash
   # Run integration tests
   docker-compose exec backend pytest tests/test_evident_integration.py
   ```

3. **Mock evident for Development**
   ```bash
   # Use mock evident server
   docker-compose -f docker-compose.dev.yml up evident-mock
   ``` 