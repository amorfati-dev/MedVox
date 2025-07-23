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
    use_mock: bool = Form(False, description="Use mock transcription for testing")
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
            dentist_id=dentist_id
        )
        
        logger.info(f"Documentation result: {documentation}")
        logger.info(f"Procedures found: {len(documentation.procedures_performed) if documentation.procedures_performed else 0}")
        logger.info(f"Billing codes found: {len(documentation.billing_codes) if documentation.billing_codes else 0}")
        
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