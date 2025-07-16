# MedVox MVP Development Plan

## Project Overview
˚ **The MVP will integrate with evident PMS for seamless patient data transfer and documentation export.**

## MVP Scope & Objectives

### Core Features for MVP
1. **evident Integration** 🆕
   - Import patient data from evident PMS
   - Export generated documentation back to evident
   - Sync patient records automatically
   - Support evident's data formats and APIs

2. **Voice Recording & Transcription**
   - Real-time voice capture during dental procedures
   - Accurate transcription with medical terminology support
   - Support for German and English languages

3. **Basic Documentation Generation**
   - Convert transcriptions into structured clinical notes
   - Template-based documentation matching evident's format
   - Export directly to patient records in evident

4. **Simple User Management**
   - Dentist login/authentication
   - Link with evident user accounts
   - Session management

5. **Data Security & Compliance**
   - GDPR-compliant data handling
   - Encrypted storage
   - Audit logging
   - No duplicate data storage (reference evident data)

## Technical Architecture

### Tech Stack
- **Backend**: FastAPI (Python 3.11+)
- **Frontend**: React 18 with TypeScript
- **Database**: PostgreSQL 15 (minimal storage, mainly references)
- **AI/ML Services**: 
  - OpenAI Whisper (speech-to-text)
  - GPT-4 API (text processing)
- **Integration**: 
  - evident API/SDK
  - HL7 FHIR (if supported)
- **Infrastructure**: Docker, Docker Compose (local dev)
- **Authentication**: JWT with evident SSO integration

### Architecture Diagram
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  evident PMS    │◀────│   MedVox        │────▶│   PostgreSQL    │
│  (Patient Data) │────▶│   Backend       │     │   (References)  │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │   AI Services   │
                        │ - Whisper STT   │
                        │ - GPT-4 API     │
                        └─────────────────┘
```

## Development Phases

### Phase 1: Foundation & evident Research (Week 1-2)
- [ ] Research evident API documentation
- [ ] Set up evident test environment
- [ ] Project setup and repository structure
- [ ] Basic backend API structure
- [ ] evident integration proof of concept

### Phase 2: evident Integration (Week 3)
- [ ] Implement patient data import from evident
- [ ] Create patient sync mechanism
- [ ] Document export functionality to evident
- [ ] Test data flow with evident test system

### Phase 3: Core Functionality (Week 4-5)
- [ ] Voice recording interface
- [ ] Whisper integration for transcription
- [ ] Basic transcription API endpoints
- [ ] Link recordings to evident patients

### Phase 4: AI Processing (Week 6)
- [ ] GPT-4 integration for text processing
- [ ] Template system matching evident's documentation format
- [ ] Dental terminology enhancement
- [ ] Generate evident-compatible documents

### Phase 5: Integration & Export (Week 7)
- [ ] Complete evident export functionality
- [ ] Ensure proper document formatting
- [ ] Handle evident-specific fields and requirements
- [ ] Test full workflow with evident

### Phase 6: Testing & Refinement (Week 8)
- [ ] End-to-end testing with evident
- [ ] Security audit
- [ ] Performance optimization
- [ ] User acceptance testing in real practice

## Detailed Task Breakdown

### evident Integration Tasks
1. **API Research & Setup**
   - Obtain evident API documentation
   - Set up test credentials
   - Understand data models and formats
   - Identify integration points

2. **Data Mapping**
   - Map evident patient fields to MedVox
   - Define document format requirements
   - Handle evident-specific metadata
   - Create transformation utilities

3. **Integration Services**
   ```python
   # New services for evident integration
   services/
   ├── evident_service.py      # Main integration service
   ├── patient_sync_service.py # Patient data synchronization
   ├── document_export_service.py # Document export to evident
   └── evident_auth_service.py # evident authentication/SSO
   ```

### Backend Development Tasks
1. **API Structure**
   ```
   /api/v1/
   ├── auth/          # Authentication with evident SSO
   ├── evident/       # evident-specific endpoints
   │   ├── patients/  # Patient import/sync
   │   ├── export/    # Document export
   │   └── sync/      # Data synchronization
   ├── recordings/    # Voice recording management
   ├── transcriptions/# Transcription processing
   └── documents/     # Document generation
   ```

2. **Database Schema (Minimal)**
   - Users table (linked to evident users)
   - Patient references (evident patient IDs)
   - Recordings table
   - Transcriptions table
   - Export logs table
   - Audit logs table

### Frontend Development Tasks
1. **evident Integration UI**
   - Patient selector from evident
   - Import status indicators
   - Export confirmation dialogs
   - Sync status dashboard

2. **Workflow Changes**
   - Select patient from evident before recording
   - Preview document in evident format
   - One-click export to evident
   - Show evident patient details

## Security & Compliance Requirements

### Data Protection
- No duplicate patient data storage
- Reference evident data only
- Encrypted audio file storage
- Secure API communication
- evident API credentials protection

### Integration Security
- Secure evident API key storage
- OAuth2/SSO with evident (if available)
- API rate limiting
- Connection encryption

## Testing Strategy

### Integration Tests
- evident API connection tests
- Patient import functionality
- Document export validation
- Data consistency checks
- Error handling scenarios

### End-to-End Tests
- Complete workflow from evident patient selection to document export
- Multiple patient scenarios
- Network failure handling
- Data validation

## Risk Mitigation

### Integration Risks
- **Risk**: evident API limitations
  - **Mitigation**: Work closely with evident support, implement workarounds
  
- **Risk**: Data format incompatibilities
  - **Mitigation**: Flexible mapping system, manual field mapping UI

- **Risk**: evident API changes
  - **Mitigation**: Version checking, abstraction layer, regular updates

### Data Consistency Risks
- **Risk**: Sync conflicts
  - **Mitigation**: One-way sync priority, conflict resolution UI

## Timeline Summary

- **Week 1-2**: Foundation and evident research
- **Week 3**: evident integration implementation
- **Week 4-5**: Core recording and transcription
- **Week 6**: AI integration and processing
- **Week 7**: Complete integration and export
- **Week 8**: Testing with real evident system

## Next Steps

1. **Contact evident**
   - Request API documentation
   - Set up test environment
   - Understand integration requirements

2. **Technical Setup**
   - Create development environment
   - Set up evident test instance
   - Design integration architecture

3. **Proof of Concept**
   - Test patient data import
   - Test document export
   - Validate data formats

## Resources Required

### Team
- 1 Full-stack Developer
- 1 Integration Specialist (part-time)
- 1 AI/ML Engineer (part-time)
- evident technical contact

### Tools & Services
- evident test environment
- evident API access
- OpenAI API subscription
- Development tools

### Budget Estimate
- Development: €18,000-23,000
- evident integration: €3,000-5,000
- AI API costs: €500/month
- Infrastructure: €200/month
- Total MVP: €25,000-30,000

## evident Integration Requirements

### Prerequisites
- [ ] evident API access credentials
- [ ] Test practice account
- [ ] API documentation
- [ ] Technical contact at evident

### Key Integration Points
1. **Patient Import**
   - GET /patients endpoint
   - Patient demographics
   - Insurance information
   - Treatment history (if needed)

2. **Document Export**
   - POST /documents endpoint
   - Correct formatting (PDF/XML)
   - Metadata requirements
   - Attachment handling

3. **Authentication**
   - API key management
   - User mapping
   - Session handling

---

This updated plan focuses on evident integration as a core MVP feature, ensuring seamless workflow integration with existing practice management systems. 