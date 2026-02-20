"""
Audio Processing Service
Handles speech-to-text conversion using OpenAI Whisper and other STT engines
"""

import os
import tempfile
import time
from typing import Optional, Dict, Any, BinaryIO
from pathlib import Path
import structlog

from app.core.config import settings
from app.schemas.dental_documentation import TranscriptionResult, AudioMetadata
from app.utils.audio import AudioProcessor, AudioValidationError
from app.services.google_speech_service import GoogleCloudSpeechService
from app.services.whisper_service import WhisperService

logger = structlog.get_logger()


class AudioTranscriptionError(Exception):
    """Custom exception for transcription errors"""
    pass


# OpenAI Whisper Service removed - using Google Cloud Speech-to-Text exclusively


# Local Whisper Service removed - using Google Cloud Speech-to-Text exclusively


class MockTranscriptionService:
    """Mock service for testing without actual STT"""
    
    async def transcribe(self, audio_file: BinaryIO, filename: str) -> TranscriptionResult:
        """Mock transcription for testing"""
        
        # Simulate processing time
        await asyncio.sleep(0.5)
        
        # Return mock dental transcription
        mock_text = "Zahn sechs und dreißig okklusal Karies profunda, Lokalanästhesie, Kompositfüllung gelegt"
        
        return TranscriptionResult(
            text=mock_text,
            language="de",
            confidence=0.92,
            processing_time_ms=500,
            stt_model="mock-whisper"
        )


class AudioService:
    """Main audio processing service"""

    def __init__(self):
        self.audio_processor = AudioProcessor()

        # Initialize transcription services based on configuration
        self.whisper_service = WhisperService() if settings.OPENAI_API_KEY else None
        self.google_cloud_service = GoogleCloudSpeechService() if settings.GOOGLE_CLOUD_API_KEY else None
        self.mock_service = MockTranscriptionService()

        # Log which STT provider is configured
        logger.info(
            "AudioService initialized",
            stt_provider=settings.STT_PROVIDER,
            whisper_available=self.whisper_service is not None,
            google_available=self.google_cloud_service is not None
        )
        
    async def process_audio(
        self, 
        audio_file: BinaryIO, 
        filename: str,
        use_mock: bool = False
    ) -> tuple[TranscriptionResult, AudioMetadata]:
        """
        Process audio file: validate, convert, and transcribe
        
        Args:
            audio_file: Audio file binary data
            filename: Original filename
            use_mock: Use mock service for testing
            
        Returns:
            Tuple of (TranscriptionResult, AudioMetadata)
        """
        logger.info("Starting audio processing", filename=filename, use_mock=use_mock)
        
        try:
            # Read audio data
            audio_data = audio_file.read()
            audio_file.seek(0)  # Reset for potential reuse
            
            # Validate audio file
            audio_metadata = self.audio_processor.validate_audio(audio_data, filename)
            
            # Choose transcription service based on configuration
            if use_mock:
                transcription_service = self.mock_service
                logger.info("Using mock transcription service")
            elif settings.STT_PROVIDER == "whisper":
                if self.whisper_service:
                    transcription_service = self.whisper_service
                    logger.info("Using OpenAI Whisper V3 API")
                else:
                    raise AudioTranscriptionError("Whisper not configured. Please set OPENAI_API_KEY.")
            elif settings.STT_PROVIDER == "google":
                if self.google_cloud_service:
                    transcription_service = self.google_cloud_service
                    logger.info("Using Google Cloud Speech-to-Text API")
                else:
                    raise AudioTranscriptionError("Google Cloud Speech-to-Text not configured. Please set GOOGLE_CLOUD_API_KEY.")
            else:
                raise AudioTranscriptionError(f"Unknown STT_PROVIDER: {settings.STT_PROVIDER}. Use 'whisper' or 'google'.")
            
            # All API services can handle file objects directly
            transcription_result = await transcription_service.transcribe(audio_file, filename)
            
            logger.info("Audio processing completed successfully",
                       filename=filename,
                       text_length=len(transcription_result.text),
                       confidence=transcription_result.confidence)
            
            return transcription_result, audio_metadata
            
        except AudioValidationError as e:
            logger.error("Audio validation failed", filename=filename, error=str(e))
            raise AudioTranscriptionError(f"Invalid audio file: {str(e)}")
        except Exception as e:
            logger.error("Audio processing failed", filename=filename, error=str(e))
            raise AudioTranscriptionError(f"Audio processing error: {str(e)}")
    
# Local transcription method removed - using Google Cloud Speech-to-Text exclusively
    
    def get_supported_formats(self) -> list[str]:
        """Get list of supported audio formats"""
        return settings.supported_audio_formats_list
    
    def get_max_file_size(self) -> int:
        """Get maximum allowed file size in bytes"""
        return settings.MAX_AUDIO_SIZE_MB * 1024 * 1024


# Add missing import for asyncio
import asyncio 