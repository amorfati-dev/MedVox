"""
OpenAI Whisper V3 Speech-to-Text Service
Enhanced German transcription with better accuracy for dental terminology
"""

import time
import tempfile
import os
from typing import BinaryIO
import structlog

from app.core.config import settings
from app.schemas.dental_documentation import TranscriptionResult

logger = structlog.get_logger()


class AudioTranscriptionError(Exception):
    """Custom exception for audio transcription errors"""
    pass


class WhisperService:
    """OpenAI Whisper V3 transcription service optimized for German dental terminology"""

    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = "whisper-1"  # OpenAI API uses whisper-1 (which is V3)
        self.language = "de"

        if not self.api_key:
            logger.warning("OpenAI API key not configured - Whisper service will not work")

    def _get_dental_prompt(self) -> str:
        """
        Enhanced prompt with German dental terminology for better recognition
        Whisper uses this to bias the transcription towards expected terms
        """
        return (
            "Zahnärztliche Dokumentation mit Fachbegriffen: "
            "Füllung, dreiflächig, zweiflächig, Karies, Lokalanästhesie, "
            "Wurzelkanalbehandlung, Extraktion, Krone, Brücke, Implantat, "
            "BEMA, GOZ, Zahn, okklusal, mesial, distal, vestibulär, palatinal, "
            "Komposite, Amalgam, Röntgen, Zahnfilm, Befund, Diagnose, "
            "sechsunddreißig, dreiundvierzig, Oberkiefer, Unterkiefer"
        )

    async def transcribe(self, audio_file: BinaryIO, filename: str) -> TranscriptionResult:
        """
        Transcribe audio using OpenAI Whisper API

        Args:
            audio_file: Audio file binary data
            filename: Original filename for logging

        Returns:
            TranscriptionResult with transcribed text and metadata
        """
        start_time = time.time()

        if not self.api_key:
            raise AudioTranscriptionError("OpenAI API key not configured")

        try:
            from openai import OpenAI

            logger.info("Starting Whisper V3 transcription",
                       filename=filename,
                       language=self.language)

            # Initialize OpenAI client
            client = OpenAI(api_key=self.api_key)

            # Save audio to temporary file (OpenAI API requires file path)
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp_file:
                audio_file.seek(0)
                tmp_file.write(audio_file.read())
                tmp_file_path = tmp_file.name

            try:
                # Perform transcription with enhanced settings
                logger.info("Sending audio to OpenAI Whisper API")

                with open(tmp_file_path, 'rb') as audio:
                    transcript = client.audio.transcriptions.create(
                        model=self.model,
                        file=audio,
                        language=self.language,
                        prompt=self._get_dental_prompt(),  # Bias towards dental terms
                        temperature=0.0,  # Deterministic for consistency
                        response_format="verbose_json"  # Get detailed information
                    )

                processing_time = int((time.time() - start_time) * 1000)

                # Extract transcription text
                transcribed_text = transcript.text

                # Extract segments if available
                segments = []
                if hasattr(transcript, 'segments') and transcript.segments:
                    for seg in transcript.segments:
                        segment_data = {
                            "id": seg.get('id', 0),
                            "start": seg.get('start', 0.0),
                            "end": seg.get('end', 0.0),
                            "text": seg.get('text', ''),
                            "avg_confidence": seg.get('avg_logprob', 0.0)  # Whisper uses log prob
                        }
                        segments.append(segment_data)

                # Whisper doesn't provide overall confidence, estimate from segments
                overall_confidence = 0.95  # Whisper V3 typically has very high accuracy
                if segments:
                    # Convert log probabilities to rough confidence estimate
                    avg_logprob = sum(s.get('avg_confidence', -0.5) for s in segments) / len(segments)
                    # Map log prob (-inf to 0) to confidence (0 to 1)
                    # Typical range: -1.0 (low) to -0.1 (high)
                    overall_confidence = max(0.5, min(1.0, 1.0 + avg_logprob))

                logger.info("Whisper V3 transcription completed",
                           filename=filename,
                           text_length=len(transcribed_text),
                           confidence=overall_confidence,
                           segments_count=len(segments),
                           processing_time_ms=processing_time)

                return TranscriptionResult(
                    text=transcribed_text,
                    language=self.language,
                    confidence=overall_confidence,
                    segments=segments,
                    processing_time_ms=processing_time,
                    stt_model="whisper-v3"
                )

            finally:
                # Clean up temporary file
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)

        except ImportError:
            raise AudioTranscriptionError(
                "OpenAI library not installed. Run: pip install openai"
            )
        except Exception as e:
            logger.error("Whisper V3 transcription failed",
                        filename=filename,
                        error=str(e))
            raise AudioTranscriptionError(f"Whisper transcription error: {str(e)}")
