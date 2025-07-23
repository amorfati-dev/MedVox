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

logger = structlog.get_logger()


class AudioTranscriptionError(Exception):
    """Custom exception for transcription errors"""
    pass


class OpenAIWhisperService:
    """OpenAI Whisper API integration"""
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL
        self.max_file_size = settings.MAX_AUDIO_SIZE_MB * 1024 * 1024
        
    async def transcribe(self, audio_file: BinaryIO, filename: str) -> TranscriptionResult:
        """
        Transcribe audio using OpenAI Whisper API
        
        Args:
            audio_file: Audio file binary data
            filename: Original filename for format detection
            
        Returns:
            TranscriptionResult with transcribed text and metadata
        """
        if not self.api_key:
            raise AudioTranscriptionError("OpenAI API key not configured")
        
        start_time = time.time()
        
        try:
            # Import OpenAI here to avoid dependency issues if not installed
            import openai
            
            # Configure OpenAI client
            client = openai.OpenAI(api_key=self.api_key)
            
            logger.info("Starting OpenAI Whisper transcription", filename=filename)
            
            # Prepare dental terminology prompt for better accuracy
            dental_prompt = self._get_dental_terminology_prompt() if settings.DENTAL_TERMINOLOGY_BOOST else None
            
            # Call Whisper API with enhanced settings
            response = client.audio.transcriptions.create(
                model=self.model,
                file=(filename, audio_file, "audio/wav"),
                language="de",  # German language
                response_format="verbose_json",  # Get confidence scores
                temperature=settings.WHISPER_TEMPERATURE,  # Enhanced temperature setting
                prompt=dental_prompt  # Dental context for better recognition
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # Extract result
            transcribed_text = response.text
            
            # Get confidence from segments if available
            confidence = getattr(response, 'confidence', 0.9)  # Default confidence
            segments = getattr(response, 'segments', None)
            
            # Convert TranscriptionSegment objects to dictionaries for new OpenAI library
            if segments:
                converted_segments = []
                for segment in segments:
                    if hasattr(segment, '__dict__'):
                        # Convert TranscriptionSegment object to dictionary
                        segment_dict = {
                            'id': getattr(segment, 'id', 0),
                            'start': getattr(segment, 'start', 0.0),
                            'end': getattr(segment, 'end', 0.0),
                            'text': getattr(segment, 'text', ''),
                            'avg_logprob': getattr(segment, 'avg_logprob', -0.5),
                            'compression_ratio': getattr(segment, 'compression_ratio', 1.0),
                            'no_speech_prob': getattr(segment, 'no_speech_prob', 0.0),
                            'temperature': getattr(segment, 'temperature', 0.0)
                        }
                        converted_segments.append(segment_dict)
                    else:
                        # Already a dictionary
                        converted_segments.append(segment)
                segments = converted_segments
            
            # Calculate average confidence from segments if available
            if segments and len(segments) > 0:
                # Convert log probability to confidence (approximate)
                avg_logprob = sum(seg.get('avg_logprob', -0.5) for seg in segments) / len(segments)
                confidence = min(1.0, max(0.0, (avg_logprob + 1.0)))  # Normalize to 0-1
            
            logger.info("OpenAI Whisper transcription completed",
                       text_length=len(transcribed_text),
                       confidence=confidence,
                       processing_time_ms=processing_time)
            
            return TranscriptionResult(
                text=transcribed_text,
                language="de",
                confidence=confidence,
                segments=segments,
                processing_time_ms=processing_time,
                stt_model=f"openai-{self.model}"
            )
            
        except ImportError:
            raise AudioTranscriptionError("OpenAI library not installed. Run: pip install openai")
        except Exception as e:
            logger.error("OpenAI Whisper transcription failed", error=str(e))
            raise AudioTranscriptionError(f"Whisper API error: {str(e)}")
    
    def _get_dental_terminology_prompt(self) -> str:
        """
        Generate a dental terminology prompt to improve Whisper's recognition
        of German dental terms and procedures
        """
        return """Dies ist eine Aufnahme aus einer deutschen Zahnarztpraxis. 
        Häufige Begriffe: Karies, Parodontitis, Zahnextraktion, Füllungstherapie, 
        Lokalanästhesie, Leitungsanästhesie, Röntgenbild, Zahn, okklusal, 
        mesial, distal, vestibulär, lingual, Komposit, Amalgam, Krone, 
        Brücke, Implantat, Wurzelkanalbehandlung, Gingivitis, Prophylaxe,
        BEMA, GOZ, Ziffer, Abrechnung."""


class LocalWhisperService:
    """Local Whisper model (fallback when OpenAI API not available)"""
    
    def __init__(self):
        self.model_size = settings.WHISPER_MODEL_SIZE
        self.device = settings.WHISPER_DEVICE
        self._model = None
        
    def _load_model(self):
        """Lazy load Whisper model"""
        if self._model is None:
            try:
                import whisper
                
                logger.info("Loading local Whisper model", 
                           model_size=self.model_size,
                           device=self.device)
                
                self._model = whisper.load_model(
                    self.model_size, 
                    device=self.device if self.device != "auto" else None
                )
                
                logger.info("Local Whisper model loaded successfully")
                
            except ImportError:
                raise AudioTranscriptionError("Whisper library not installed. Run: pip install openai-whisper")
            except Exception as e:
                raise AudioTranscriptionError(f"Failed to load Whisper model: {str(e)}")
    
    async def transcribe(self, audio_file_path: str) -> TranscriptionResult:
        """
        Transcribe audio using local Whisper model
        
        Args:
            audio_file_path: Path to audio file
            
        Returns:
            TranscriptionResult with transcribed text and metadata
        """
        self._load_model()
        
        start_time = time.time()
        
        try:
            logger.info("Starting local Whisper transcription", file_path=audio_file_path)
            
            # Transcribe with Whisper (enhanced settings)
            result = self._model.transcribe(
                audio_file_path,
                language="de",
                word_timestamps=True,
                temperature=settings.WHISPER_TEMPERATURE,
                initial_prompt="Deutsche Zahnarztpraxis: Karies, Zahn, Lokalanästhesie, Füllung, Röntgenbild"
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # Extract segments for detailed timing
            segments = []
            if "segments" in result:
                segments = [
                    {
                        "start": seg["start"],
                        "end": seg["end"], 
                        "text": seg["text"],
                        "confidence": getattr(seg, "avg_logprob", -0.5)
                    }
                    for seg in result["segments"]
                ]
            
            # Calculate overall confidence
            confidence = 0.85  # Default for local Whisper
            if segments:
                avg_logprob = sum(seg.get("confidence", -0.5) for seg in segments) / len(segments)
                confidence = min(1.0, max(0.0, (avg_logprob + 1.0)))
            
            transcribed_text = result["text"]
            
            logger.info("Local Whisper transcription completed",
                       text_length=len(transcribed_text),
                       confidence=confidence,
                       processing_time_ms=processing_time)
            
            return TranscriptionResult(
                text=transcribed_text,
                language=result.get("language", "de"),
                confidence=confidence,
                segments=segments,
                processing_time_ms=processing_time,
                stt_model=f"whisper-{self.model_size}"
            )
            
        except Exception as e:
            logger.error("Local Whisper transcription failed", error=str(e))
            raise AudioTranscriptionError(f"Local Whisper error: {str(e)}")


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
        
        # Initialize available transcription services
        self.openai_service = OpenAIWhisperService() if settings.OPENAI_API_KEY else None
        self.local_service = LocalWhisperService()
        self.mock_service = MockTranscriptionService()
        
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
            
            # Choose transcription service
            if use_mock:
                transcription_service = self.mock_service
                logger.info("Using mock transcription service")
            elif self.openai_service:
                transcription_service = self.openai_service
                logger.info("Using OpenAI Whisper API")
            else:
                transcription_service = self.local_service
                logger.info("Using local Whisper model")
            
            # For local Whisper, we need to save to temp file
            if transcription_service == self.local_service:
                transcription_result = await self._transcribe_with_local(audio_data, filename)
            else:
                # API services can handle file objects directly
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
    
    async def _transcribe_with_local(self, audio_data: bytes, filename: str) -> TranscriptionResult:
        """Transcribe using local Whisper with temporary file"""
        
        # Create temporary file
        suffix = Path(filename).suffix or ".wav"
        
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_path = temp_file.name
        
        try:
            # Transcribe with local service
            return await self.local_service.transcribe(temp_path)
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except OSError:
                logger.warning("Failed to delete temporary file", path=temp_path)
    
    def get_supported_formats(self) -> list[str]:
        """Get list of supported audio formats"""
        return settings.supported_audio_formats_list
    
    def get_max_file_size(self) -> int:
        """Get maximum allowed file size in bytes"""
        return settings.MAX_AUDIO_SIZE_MB * 1024 * 1024


# Add missing import for asyncio
import asyncio 