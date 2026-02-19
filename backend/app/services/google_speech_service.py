"""
Google Cloud Speech-to-Text Service
Replaces OpenAI Whisper for more accurate German dental transcription
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


class GoogleCloudSpeechService:
    """Google Cloud Speech-to-Text transcription service optimized for German dental terminology"""
    
    def __init__(self):
        self.api_key = settings.GOOGLE_CLOUD_API_KEY
        self.project_id = settings.GOOGLE_CLOUD_PROJECT_ID
        self.language_code = "de-DE"
        self.sample_rate = settings.AUDIO_SAMPLE_RATE
        
        if not self.api_key:
            raise AudioTranscriptionError("Google Cloud API key not configured")
    
    def _get_dental_speech_contexts(self) -> list:
        """Enhanced German dental terminology for better recognition"""
        return [
            {
                "phrases": [
                    # Dental procedures
                    "Füllung", "Füllungen", "Dreiflächige Füllung", "Zweiflächige Füllung",
                    "Komposite", "Amalgam", "Kunststofffüllung", "Kompositfüllung",
                    "Wurzelkanalbehandlung", "Endodontie", "Krone", "Brücke", "Implantat",
                    "Extraktion", "Ziehen", "Entfernung",
                    
                    # Anesthesia
                    "Lokalanästhesie", "Leitungsanästhesie", "Infiltrationsanästhesie",
                    "Betäubung", "Anästhesie", "Spritze",
                    
                    # Diagnostic
                    "Röntgen", "Röntgenbild", "Zahnfilm", "OPG", "Orthopantomogramm",
                    "Vitalitätsprüfung", "Perkussion", "Palpation",
                    "Untersuchung", "Befund", "Diagnose",
                    
                    # Tooth numbers and positions
                    "Zahn", "Zähne", "Backenzahn", "Schneidezahn", "Eckzahn",
                    "rechts", "links", "oben", "unten", "Oberkiefer", "Unterkiefer",
                    "mesial", "distal", "okklusal", "bukkal", "palatinal", "lingual",
                    "MOD", "MO", "DO", "OD", "OM",
                    
                    # Materials
                    "Glasionomerzement", "Phosphatzement", "Adhäsiv", "Bonding",
                    "Matrize", "Keil", "Kofferdamm", "Ätzgel", "Primer",
                    
                    # Conditions
                    "Karies", "kariös", "Parodontitis", "Gingivitis", "Pulpitis",
                    "Nekrose", "Fistel", "Schwellung", "Schmerzen",
                    
                    # BEMA/GOZ codes (common ones)
                    "BEMA", "GOZ", "Gebührenziffer", "Abrechnungsziffer",
                    "Kassenleistung", "Privatleistung", "Zuzahlung"
                ],
                "boost": 15.0  # Boost recognition confidence for these terms
            }
        ]
    
    async def transcribe(self, audio_file: BinaryIO, filename: str) -> TranscriptionResult:
        """
        Transcribe audio using Google Cloud Speech-to-Text API
        
        Args:
            audio_file: Audio file binary data
            filename: Original filename for logging
            
        Returns:
            TranscriptionResult with transcribed text and metadata
        """
        start_time = time.time()
        
        try:
            import requests
            import base64
            
            logger.info("Starting Google Cloud Speech transcription", 
                       filename=filename,
                       language=self.language_code)
            
            # Use REST API with API key directly
            api_url = f"https://speech.googleapis.com/v1/speech:recognize?key={self.api_key}"
            
            # Read audio content
            audio_file.seek(0)
            audio_content = audio_file.read()
            
            # Encode audio as base64
            audio_base64 = base64.b64encode(audio_content).decode('utf-8')
            
            # Create request payload
            dental_phrases = [phrase for context in self._get_dental_speech_contexts() for phrase in context["phrases"]]
            
            # Try different encoding based on filename
            if filename.endswith('.webm'):
                encoding = "WEBM_OPUS"
                sample_rate = 44100  # Match frontend sample rate
            elif filename.endswith('.wav'):
                encoding = "LINEAR16"
                sample_rate = 44100
            else:
                # Default to a more universal format
                encoding = "LINEAR16" 
                sample_rate = 44100
            
            # Enhanced configuration for better German dental recognition
            config = {
                "encoding": encoding,
                "languageCode": self.language_code,
                "alternativeLanguageCodes": ["de-AT", "de-CH"],
                "maxAlternatives": 1,
                "enableWordConfidence": True,
                "enableWordTimeOffsets": True,
                "enableAutomaticPunctuation": True,
                "useEnhanced": True,  # Premium model for better accuracy
                "model": "latest_long",  # Best model for longer audio
                "speechContexts": [
                    {
                        "phrases": [
                            "Zahn", "Zahlen", "Füllung", "dreiflächig", "MOD", 
                            "Karies", "Lokalanästhesie", "Röntgen", "Zahnfilm",
                            "sechsunddreißig", "36", "dreiundvierzig", "43",
                            "BEMA", "GOZ", "Abrechnung"
                        ],
                        "boost": 20.0
                    }
                ]
            }
            
            # Only add sample rate for non-WEBM formats (WEBM OPUS determines its own rate)
            if encoding != "WEBM_OPUS":
                config["sampleRateHertz"] = sample_rate
            
            request_data = {
                "config": config,
                "audio": {
                    "content": audio_base64
                }
            }
            
            logger.info(f"Using encoding: {encoding}, sample rate: {sample_rate}")
            
            # Debug: Log request size
            logger.info(f"Audio content size: {len(audio_content)} bytes")
            logger.info(f"Base64 content size: {len(audio_base64)} characters")
            
            # Perform transcription
            logger.info("Sending audio to Google Cloud Speech API")
            headers = {
                "Content-Type": "application/json"
            }
            
            response = requests.post(api_url, json=request_data, headers=headers)
            
            # Debug: Log response details
            logger.info(f"Google Cloud Speech API Response Status: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"Google Cloud Speech API Error: {response.text}")
                raise AudioTranscriptionError(f"Google Cloud Speech API error: {response.status_code} - {response.text}")
            
            response_data = response.json()
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # Process results
            if not response_data.get("results"):
                logger.warning("No transcription results from Google Cloud Speech",
                              response_keys=list(response_data.keys()),
                              response_preview=str(response_data)[:500])
                # Return empty result instead of raising - let the processor decide
                return TranscriptionResult(
                    text="",
                    language="de",
                    confidence=0.0,
                    segments=[],
                    processing_time_ms=processing_time,
                    stt_model="google-cloud-speech"
                )
            
            # Merge all result segments (Google returns one entry per utterance/pause)
            all_results = response_data["results"]
            transcribed_text = " ".join(
                r["alternatives"][0]["transcript"]
                for r in all_results
                if r.get("alternatives")
            )
            confidences = [
                r["alternatives"][0].get("confidence", 0.9)
                for r in all_results
                if r.get("alternatives")
            ]
            overall_confidence = sum(confidences) / len(confidences) if confidences else 0.9

            # Use first result for word-level segments (detailed data)
            result = all_results[0]
            alternative = result["alternatives"][0]
            
            # Extract word-level segments
            segments = []
            if alternative.get("words"):
                current_segment = {
                    "id": 0,
                    "start": 0,
                    "end": 0,
                    "text": "",
                    "words": [],
                    "avg_confidence": 0.0
                }
                
                for i, word in enumerate(alternative["words"]):
                    # Convert duration strings to seconds
                    start_time_sec = 0
                    end_time_sec = 0
                    
                    if "startTime" in word:
                        start_time_str = word["startTime"].rstrip('s')
                        start_time_sec = float(start_time_str) if start_time_str else 0
                    
                    if "endTime" in word:
                        end_time_str = word["endTime"].rstrip('s')
                        end_time_sec = float(end_time_str) if end_time_str else 0
                    
                    word_confidence = word.get("confidence", 0.9)
                    
                    current_segment["words"].append({
                        "word": word["word"],
                        "start": start_time_sec,
                        "end": end_time_sec,
                        "confidence": word_confidence
                    })
                    
                    current_segment["text"] += word["word"] + " "
                    
                    # Group words into segments (roughly every 10 words)
                    if i % 10 == 9 or i == len(alternative["words"]) - 1:
                        current_segment["end"] = end_time_sec
                        if current_segment["words"]:
                            current_segment["avg_confidence"] = sum(w["confidence"] for w in current_segment["words"]) / len(current_segment["words"])
                        current_segment["text"] = current_segment["text"].strip()
                        
                        segments.append(current_segment)
                        
                        # Start new segment
                        current_segment = {
                            "id": len(segments),
                            "start": end_time_sec,
                            "end": end_time_sec,
                            "text": "",
                            "words": [],
                            "avg_confidence": 0.0
                        }
            
            logger.info("Google Cloud Speech transcription completed",
                       filename=filename,
                       text_length=len(transcribed_text),
                       confidence=overall_confidence,
                       segments_count=len(segments),
                       processing_time_ms=processing_time)
            
            return TranscriptionResult(
                text=transcribed_text,
                language="de",
                confidence=overall_confidence,
                segments=segments,
                processing_time_ms=processing_time,
                stt_model="google-cloud-speech"
            )
            
        except ImportError:
            raise AudioTranscriptionError("Required libraries not installed. Run: pip install requests")
        except Exception as e:
            logger.error("Google Cloud Speech transcription failed", 
                        filename=filename, 
                        error=str(e))
            raise AudioTranscriptionError(f"Google Cloud Speech transcription error: {str(e)}") 