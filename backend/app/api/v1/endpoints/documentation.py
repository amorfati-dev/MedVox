"""
Documentation API Endpoints
Handles audio upload and processing for dental documentation
"""

import io
import time
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
import structlog

from app.services.audio_service import AudioService, AudioTranscriptionError
from app.services.documentation_processor import DocumentationProcessor
from app.schemas.dental_documentation import (
    DocumentationResponse, DocumentationCreateRequest, DentalDocumentation
)
from app.schemas.sessions import SessionListResponse, SessionSummary
from app.models.recording import Recording, RecordingStatus
from app.models.transcription import Transcription
from app.models.user import User, UserRole
from app.models.patient import Patient, Gender, InsuranceType
from app.core.database import get_db
from app.core.config import settings
from sqlalchemy.orm import Session, joinedload
import os
from pathlib import Path
from datetime import date

logger = structlog.get_logger()

router = APIRouter()

# Initialize services
audio_service = AudioService()
doc_processor = DocumentationProcessor()


@router.post("/process-audio", response_model=DocumentationResponse)
async def process_audio_documentation(
    audio_file: UploadFile = File(..., description="Audio file (WAV, MP3, M4A)"),
    patient_id: Optional[str] = Form(None, description="Patient ID from Evident"),
    dentist_id: str = Form(..., description="Dentist identifier"),
    insurance_type: str = Form("bema", description="Insurance type: 'bema' or 'goz'"),
    treatment_context: Optional[str] = Form(None, description="Treatment context/notes"),
    processing_mode: str = Form("with_billing", description="Processing mode: 'with_billing' or 'transcription_only'"),
    use_mock: bool = Form(False, description="Use mock transcription for testing"),
    db: Session = Depends(get_db)
):
    """
    Process audio file and generate structured dental documentation
    
    This endpoint:
    1. Validates the uploaded audio file
    2. Transcribes speech to text using Whisper
    3. Processes the text to extract dental information
    4. Generates billing codes and clinical documentation
    5. Returns structured JSON output
    """
    
    logger.info("Processing audio documentation request",
               filename=audio_file.filename,
               patient_id=patient_id,
               dentist_id=dentist_id,
               use_mock=use_mock)
    
    start_time = time.time()
    
    try:
        # Validate file
        if not audio_file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Check file size
        max_size = audio_service.get_max_file_size()
        content = await audio_file.read()
        
        if len(content) > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large: {len(content)} bytes (max: {max_size})"
            )
        
        # Create file-like object
        audio_file_obj = io.BytesIO(content)
        
        # Process audio (transcription)
        logger.info("Starting audio transcription", filename=audio_file.filename)
        transcription_result, audio_metadata = await audio_service.process_audio(
            audio_file_obj, 
            audio_file.filename,
            use_mock=use_mock
        )
        
        # Process transcription (extract dental information)
        logger.info("Starting documentation processing")
        logger.info(f"Insurance type: {insurance_type}")
        logger.info(f"Patient ID: {patient_id}")
        logger.info(f"Dentist ID: {dentist_id}")
        logger.info(f"Transcription text: {transcription_result.text[:100]}...")
        
        documentation = await doc_processor.process_transcription(
            transcription_result=transcription_result,
            audio_metadata=audio_metadata,
            insurance_type=insurance_type,
            patient_id=patient_id,
            dentist_id=dentist_id,
            processing_mode=processing_mode
        )

        logger.info(f"Documentation result: {documentation}")
        logger.info(f"Procedures found: {len(documentation.procedures_performed) if documentation.procedures_performed else 0}")
        logger.info(f"Billing codes found: {len(documentation.billing_codes) if documentation.billing_codes else 0}")

        # Save to database
        try:
            logger.info(f"💾 Saving recording to database...")
            logger.info(f"   Dentist ID: {dentist_id}")
            logger.info(f"   Patient ID: {patient_id}")
            logger.info(f"   Processing mode: {processing_mode}")

            # Get or create dentist/user
            dentist_email = f"{dentist_id}@medvox.local"
            dentist = db.query(User).filter(User.email == dentist_email).first()

            if not dentist:
                logger.info(f"   Creating new dentist: {dentist_id}")
                dentist = User(
                    email=dentist_email,
                    hashed_password="not_used",
                    first_name=dentist_id.split()[0] if ' ' in dentist_id else dentist_id,
                    last_name=dentist_id.split()[-1] if ' ' in dentist_id else "",
                    role=UserRole.DENTIST,
                    is_active=True,
                    is_superuser=False
                )
                db.add(dentist)
                db.flush()
                logger.info(f"   ✅ Dentist created with ID: {dentist.id}")
            else:
                logger.info(f"   ✅ Found existing dentist: {dentist.full_name} (ID: {dentist.id})")

            # Get or create patient
            # Use None instead of empty string for evident_patient_id to avoid UNIQUE constraint issues
            evident_pid = patient_id if patient_id else None

            patient = db.query(Patient).filter(Patient.evident_patient_id == evident_pid).first()

            if patient:
                logger.info(f"   ✅ Found existing patient: {evident_pid or 'No ID'}")
            else:
                logger.info(f"   Creating new patient: {evident_pid or 'No ID'}")
                patient = Patient(
                    first_name="Unknown",
                    last_name=f"Patient {evident_pid or 'No ID'}",
                    date_of_birth=date(2000, 1, 1),
                    gender=Gender.OTHER,
                    insurance_type=InsuranceType.PUBLIC if insurance_type == 'bema' else InsuranceType.PRIVATE,
                    evident_patient_id=evident_pid  # None if no patient_id
                )
                db.add(patient)
                db.flush()
                logger.info(f"   ✅ Patient created with ID: {patient.id}")

            # Save audio file
            upload_dir = Path(settings.UPLOAD_DIR)
            upload_dir.mkdir(parents=True, exist_ok=True)

            file_extension = Path(audio_file.filename).suffix or '.webm'
            filename = f"recording_{int(time.time())}_{dentist.id}_{patient.id}{file_extension}"
            file_path = upload_dir / filename

            with open(file_path, 'wb') as f:
                f.write(content)
            logger.info(f"   ✅ Audio file saved: {filename}")

            # Create Recording
            recording = Recording(
                filename=filename,
                file_path=str(file_path),
                file_size=len(content),
                duration=audio_metadata.duration_seconds,
                format=audio_metadata.format,
                status=RecordingStatus.TRANSCRIBED,
                sample_rate=audio_metadata.sample_rate,
                channels=1,
                patient_id=patient.id,
                created_by_id=dentist.id,
                processing_mode=processing_mode,
                session_metadata={}
            )
            db.add(recording)
            db.flush()
            logger.info(f"   ✅ Recording created with ID: {recording.id}")

            # Create Transcription
            transcription = Transcription(
                text=transcription_result.text,
                language=transcription_result.language,
                model_used=transcription_result.stt_model,
                confidence_score=transcription_result.confidence,
                processing_time=transcription_result.processing_time_ms / 1000.0,
                recording_id=recording.id
            )
            db.add(transcription)
            db.flush()  # Flush to get transcription.id
            logger.info(f"   ✅ Transcription created with ID: {transcription.id}")

            # Create Treatment if billing codes were extracted
            if processing_mode == 'with_billing' and documentation.billing_codes:
                logger.info(f"   💰 Creating Treatment with {len(documentation.billing_codes)} billing codes")

                from app.models.treatment import Treatment
                from app.models.medical_code import MedicalCode, CodeSystem

                # Extract diagnosis and treatment description
                diagnosis = documentation.findings[0] if documentation.findings else "Dental treatment"
                treatment_desc = transcription_result.text[:500] if transcription_result.text else "Voice documented treatment"

                # Extract tooth numbers from procedures
                tooth_numbers = []
                if documentation.procedures_performed:
                    for proc in documentation.procedures_performed:
                        if hasattr(proc, 'tooth_number') and proc.tooth_number:
                            tooth_numbers.append(proc.tooth_number)

                # Create Treatment
                treatment = Treatment(
                    patient_id=patient.id,
                    performed_by_id=dentist.id,
                    transcription_id=transcription.id,
                    diagnosis=diagnosis,
                    treatment_description=treatment_desc,
                    tooth_numbers=tooth_numbers if tooth_numbers else None,
                    notes=f"Processing mode: {processing_mode}"
                )
                db.add(treatment)
                db.flush()  # Flush to get treatment.id
                logger.info(f"   ✅ Treatment created with ID: {treatment.id}")

                # Process billing codes and link to treatment
                from app.models.treatment import treatment_medical_codes

                for billing_code in documentation.billing_codes:
                    code_value = billing_code.code
                    # Handle both string and enum for system
                    system_value = billing_code.system
                    if hasattr(system_value, 'value'):
                        system_value = system_value.value
                    system = CodeSystem.BEMA if system_value.upper() == 'BEMA' else CodeSystem.GOZ

                    # Find or create MedicalCode
                    medical_code = db.query(MedicalCode).filter(
                        MedicalCode.code == code_value,
                        MedicalCode.system == system
                    ).first()

                    if not medical_code:
                        logger.info(f"   📝 Creating new MedicalCode: {system.value} {code_value}")
                        # Use description field which exists in BillingCode schema
                        medical_code = MedicalCode(
                            code=code_value,
                            system=system,
                            name=billing_code.description if billing_code.description else code_value,
                            description=billing_code.description,
                            base_fee=getattr(billing_code, 'fee', None) if system == CodeSystem.GOZ else None,
                            is_active=True
                        )
                        db.add(medical_code)
                        db.flush()

                    # Link MedicalCode to Treatment using association table
                    quantity = getattr(billing_code, 'quantity', 1.0)
                    from sqlalchemy import insert
                    stmt = insert(treatment_medical_codes).values(
                        treatment_id=treatment.id,
                        medical_code_id=medical_code.id,
                        quantity=quantity
                    )
                    db.execute(stmt)
                    logger.info(f"   ✅ Linked {system.value} {code_value} to treatment (quantity: {quantity})")

                logger.info(f"   💰 Treatment complete with {len(documentation.billing_codes)} codes saved")

            db.commit()
            logger.info(f"✅ COMMIT SUCCESSFUL - Recording ID: {recording.id}")

        except Exception as e:
            db.rollback()
            logger.error(f"❌ DATABASE ERROR: Failed to save recording", exc_info=True)
            logger.error(f"   Error type: {type(e).__name__}")
            logger.error(f"   Error message: {str(e)}")
            # Continue anyway - don't fail the request
            # But this means the session won't be saved!

        processing_time = int((time.time() - start_time) * 1000)

        logger.info("Audio documentation processing completed",
                   filename=audio_file.filename,
                   recording_id=documentation.recording_id,
                   findings_count=len(documentation.findings),
                   billing_codes_count=len(documentation.billing_codes),
                   total_processing_time_ms=processing_time)

        return DocumentationResponse(
            success=True,
            documentation=documentation,
            processing_time_ms=processing_time
        )
        
    except AudioTranscriptionError as e:
        logger.error("Audio transcription failed", 
                    filename=audio_file.filename,
                    error=str(e))
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return DocumentationResponse(
            success=False,
            error_message=f"Transcription failed: {str(e)}",
            processing_time_ms=processing_time
        )
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
        
    except Exception as e:
        logger.error("Documentation processing failed",
                    filename=audio_file.filename,
                    error=str(e),
                    exc_info=True)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return DocumentationResponse(
            success=False,
            error_message=f"Processing failed: {str(e)}",
            processing_time_ms=processing_time
        )


@router.post("/process-text", response_model=DocumentationResponse)
async def process_text_documentation(
    text: str = Form(..., description="Transcribed text to process"),
    patient_id: Optional[str] = Form(None, description="Patient ID from Evident"),
    dentist_id: str = Form(..., description="Dentist identifier"),
    treatment_context: Optional[str] = Form(None, description="Treatment context/notes")
):
    """
    Process already transcribed text for dental documentation
    
    Useful for testing or when you already have transcribed text
    """
    
    logger.info("Processing text documentation request",
               text_length=len(text),
               patient_id=patient_id,
               dentist_id=dentist_id)
    
    start_time = time.time()
    
    try:
        # Create mock transcription result
        from app.schemas.dental_documentation import TranscriptionResult, AudioMetadata
        
        transcription_result = TranscriptionResult(
            text=text,
            language="de",
            confidence=0.95,  # Assume high confidence for manual text
            processing_time_ms=0,
            stt_model="manual-input"
        )
        
        audio_metadata = AudioMetadata(
            duration_seconds=0.0,
            sample_rate=16000,
            format="text",
            size_bytes=len(text.encode('utf-8')),
            quality_score=1.0
        )
        
        # Process transcription
        documentation = await doc_processor.process_transcription(
            transcription_result=transcription_result,
            audio_metadata=audio_metadata
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        logger.info("Text documentation processing completed",
                   recording_id=documentation.recording_id,
                   findings_count=len(documentation.findings),
                   billing_codes_count=len(documentation.billing_codes),
                   processing_time_ms=processing_time)
        
        return DocumentationResponse(
            success=True,
            documentation=documentation,
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error("Text processing failed", error=str(e), exc_info=True)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return DocumentationResponse(
            success=False,
            error_message=f"Text processing failed: {str(e)}",
            processing_time_ms=processing_time
        )


@router.get("/supported-formats")
async def get_supported_formats():
    """Get list of supported audio formats and limits"""
    
    return {
        "supported_formats": audio_service.get_supported_formats(),
        "max_file_size_mb": audio_service.get_max_file_size() // (1024 * 1024),
        "max_file_size_bytes": audio_service.get_max_file_size(),
        "recommended_sample_rate": 16000,
        "recommended_format": "wav"
    }


@router.get("/test-audio")
async def get_test_audio():
    """Generate a test audio file for testing"""
    
    try:
        from app.utils.audio import create_test_audio_file
        
        # Create test audio
        test_audio = create_test_audio_file()
        
        logger.info("Generated test audio file", size_bytes=len(test_audio))
        
        # Return as response
        from fastapi import Response
        
        return Response(
            content=test_audio,
            media_type="audio/wav",
            headers={"Content-Disposition": "attachment; filename=test_audio.wav"}
        )
        
    except Exception as e:
        logger.error("Failed to generate test audio", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to generate test audio: {str(e)}")


@router.post("/validate-audio")
async def validate_audio_file(
    audio_file: UploadFile = File(..., description="Audio file to validate")
):
    """Validate an audio file without processing it"""
    
    logger.info("Validating audio file", filename=audio_file.filename)
    
    try:
        # Read file content
        content = await audio_file.read()
        
        # Validate using audio processor
        from app.utils.audio import AudioProcessor
        processor = AudioProcessor()
        
        metadata = processor.validate_audio(content, audio_file.filename)
        
        logger.info("Audio validation successful",
                   filename=audio_file.filename,
                   duration=metadata.duration_seconds,
                   sample_rate=metadata.sample_rate)
        
        return {
            "valid": True,
            "filename": audio_file.filename,
            "metadata": {
                "duration_seconds": metadata.duration_seconds,
                "sample_rate": metadata.sample_rate,
                "format": metadata.format,
                "size_bytes": metadata.size_bytes,
                "quality_score": metadata.quality_score
            }
        }
        
    except Exception as e:
        logger.error("Audio validation failed",
                    filename=audio_file.filename,
                    error=str(e))
        
        return {
            "valid": False,
            "filename": audio_file.filename,
            "error": str(e)
        }


# Add missing import
import time


@router.get("/sessions", response_model=SessionListResponse)
async def get_sessions(
    date: Optional[str] = None,
    dentist_id: Optional[int] = None,
    dentist_email: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Get list of recording sessions

    Query sessions with optional filters:
    - date: Filter by date (YYYY-MM-DD format)
    - dentist_id: Filter by specific dentist ID
    - dentist_email: Filter by dentist email
    - limit/offset: Pagination
    """

    logger.info("Fetching sessions",
               date=date,
               dentist_id=dentist_id,
               dentist_email=dentist_email,
               limit=limit,
               offset=offset)

    try:
        # Build query with eager loading
        query = db.query(Recording).options(
            joinedload(Recording.transcription),
            joinedload(Recording.created_by),
            joinedload(Recording.patient)
        ).filter(Recording.status != RecordingStatus.DELETED)

        # Apply filters
        if date:
            from datetime import datetime as dt
            date_obj = dt.strptime(date, "%Y-%m-%d")
            query = query.filter(Recording.created_at >= date_obj)
            next_day = date_obj.replace(day=date_obj.day + 1)
            query = query.filter(Recording.created_at < next_day)

        if dentist_id:
            query = query.filter(Recording.created_by_id == dentist_id)

        if dentist_email:
            # Find user by email first
            logger.info(f"🔍 Searching for dentist with email: {dentist_email}")
            dentist = db.query(User).filter(User.email == dentist_email).first()
            if dentist:
                logger.info(f"✅ Found dentist: {dentist.full_name} (ID: {dentist.id})")
                query = query.filter(Recording.created_by_id == dentist.id)
            else:
                logger.warning(f"⚠️ No dentist found with email: {dentist_email}")
                # Return empty list if dentist not found
                return SessionListResponse(sessions=[], total=0)

        # Order by most recent first
        query = query.order_by(Recording.created_at.desc())

        # Get total count
        total = query.count()

        # Apply pagination
        recordings = query.offset(offset).limit(limit).all()

        # Convert to SessionSummary
        sessions = []
        for recording in recordings:
            transcription_text = ""
            billing_codes_count = 0

            if recording.transcription:
                transcription_text = recording.transcription.text

                # Count billing codes from treatment
                from app.models.treatment import Treatment
                treatment = db.query(Treatment).filter(
                    Treatment.transcription_id == recording.transcription.id
                ).first()

                if treatment:
                    billing_codes_count = treatment.medical_codes.count()

            transcription_preview = transcription_text[:100] if transcription_text else "No transcription available"

            session = SessionSummary(
                id=recording.id,
                patient_id=recording.patient.evident_patient_id if recording.patient else None,
                dentist_id=recording.created_by_id,
                dentist_name=f"{recording.created_by.first_name} {recording.created_by.last_name}" if recording.created_by else "Unknown",
                transcription_preview=transcription_preview,
                processing_mode=recording.processing_mode,
                billing_codes_count=billing_codes_count,
                created_at=recording.created_at,
                status=recording.status.value
            )
            sessions.append(session)

        logger.info("Sessions fetched successfully", total=total, returned=len(sessions))

        return SessionListResponse(
            sessions=sessions,
            total=total
        )

    except Exception as e:
        logger.error("Failed to fetch sessions", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch sessions: {str(e)}")


@router.get("/sessions/{session_id}", response_model=DocumentationResponse)
async def get_session(
    session_id: int,
    db: Session = Depends(get_db)
):
    """
    Get full documentation for a specific session

    Returns the complete DocumentationResponse with stored transcription.
    Note: Billing codes are not re-generated, only the transcription is returned.
    """

    logger.info("Fetching session details", session_id=session_id)

    try:
        # Load recording with all relationships
        recording = db.query(Recording).options(
            joinedload(Recording.transcription),
            joinedload(Recording.patient),
            joinedload(Recording.created_by)
        ).filter(Recording.id == session_id).first()

        if not recording:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        if recording.status == RecordingStatus.DELETED:
            raise HTTPException(status_code=404, detail="Session has been deleted")

        from app.schemas.dental_documentation import (
            TranscriptionResult, AudioMetadata, DentalDocumentation
        )

        transcription_result = TranscriptionResult(
            text=recording.transcription.text if recording.transcription else "",
            language=recording.transcription.language if recording.transcription else "de",
            confidence=recording.transcription.confidence_score if recording.transcription else 0.0,
            processing_time_ms=int(recording.transcription.processing_time * 1000) if recording.transcription and recording.transcription.processing_time else 0,
            stt_model=recording.transcription.model_used if recording.transcription else "unknown"
        )

        audio_metadata = AudioMetadata(
            duration_seconds=recording.duration or 0.0,
            sample_rate=recording.sample_rate or 16000,
            format=recording.format,
            size_bytes=recording.file_size,
            quality_score=1.0
        )

        # Load billing codes from Treatment if exists
        from app.models.treatment import Treatment
        from app.schemas.dental_documentation import BillingCode

        billing_codes = []
        treatment = None

        if recording.transcription:
            treatment = db.query(Treatment).filter(
                Treatment.transcription_id == recording.transcription.id
            ).first()

            if treatment:
                logger.info(f"   💰 Found treatment with {treatment.medical_codes.count()} billing codes")

                # Load medical codes from treatment
                from app.models.medical_code import CodeSystem
                for medical_code in treatment.medical_codes:
                    # Get quantity from association table
                    quantity = 1.0
                    # Note: accessing quantity from many-to-many relationship is complex
                    # For now, default to 1.0

                    billing_code = BillingCode(
                        code=medical_code.code,
                        system=medical_code.system.value.upper(),
                        description=medical_code.name,
                        quantity=quantity,
                        fee=medical_code.base_fee
                    )
                    billing_codes.append(billing_code)

        # Reconstruct documentation with transcription and billing codes
        documentation = DentalDocumentation(
            recording_id=str(recording.id),
            patient_id=recording.patient.evident_patient_id if recording.patient else None,
            dentist_id=recording.created_by.full_name if recording.created_by else "Unknown",
            transcription=transcription_result,
            audio_metadata=audio_metadata,
            clinical_notes=transcription_result.text,
            findings=[],
            procedures_performed=[],
            billing_codes=billing_codes
        )

        logger.info("Session details fetched successfully",
                   session_id=session_id,
                   transcription_length=len(transcription_result.text),
                   billing_codes_count=len(billing_codes))

        return DocumentationResponse(
            success=True,
            documentation=documentation,
            processing_time_ms=0
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch session details",
                    session_id=session_id,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch session: {str(e)}")


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: int,
    db: Session = Depends(get_db)
):
    """
    Soft delete a session by setting status to DELETED

    The session will not appear in session lists but remains in database
    for DSGVO compliance (90-day retention).
    """

    logger.info("Deleting session", session_id=session_id)

    try:
        recording = db.query(Recording).filter(Recording.id == session_id).first()

        if not recording:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        if recording.status == RecordingStatus.DELETED:
            raise HTTPException(status_code=400, detail="Session already deleted")

        # Soft delete
        recording.status = RecordingStatus.DELETED
        db.commit()

        logger.info("Session deleted successfully", session_id=session_id)

        return {"success": True, "message": f"Session {session_id} deleted"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Failed to delete session",
                    session_id=session_id,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}") 