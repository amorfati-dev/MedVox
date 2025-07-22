"""
Audio Processing Utilities
Handles audio format validation, conversion, and metadata extraction
"""

import io
import struct
import wave
from typing import BinaryIO, Dict, Any
from pathlib import Path
import structlog

from app.schemas.dental_documentation import AudioMetadata
from app.core.config import settings

logger = structlog.get_logger()


class AudioValidationError(Exception):
    """Custom exception for audio validation errors"""
    pass


class AudioProcessor:
    """Audio processing and validation utilities"""
    
    def __init__(self):
        self.supported_formats = settings.supported_audio_formats_list
        self.max_file_size = settings.MAX_AUDIO_SIZE_MB * 1024 * 1024
        self.target_sample_rate = settings.AUDIO_SAMPLE_RATE
    
    def validate_audio(self, audio_data: bytes, filename: str) -> AudioMetadata:
        """
        Validate audio file and extract metadata
        
        Args:
            audio_data: Raw audio file bytes
            filename: Original filename
            
        Returns:
            AudioMetadata with file information
            
        Raises:
            AudioValidationError: If validation fails
        """
        logger.info("Validating audio file", filename=filename, size_bytes=len(audio_data))
        
        # Check file size
        if len(audio_data) > self.max_file_size:
            raise AudioValidationError(
                f"File too large: {len(audio_data)} bytes (max: {self.max_file_size})"
            )
        
        if len(audio_data) < 1000:  # Minimum reasonable file size
            raise AudioValidationError("File too small to contain valid audio")
        
        # Check file extension
        file_ext = Path(filename).suffix.lower().lstrip('.')
        if file_ext not in self.supported_formats:
            raise AudioValidationError(
                f"Unsupported format: {file_ext}. Supported: {', '.join(self.supported_formats)}"
            )
        
        # Extract metadata based on format
        try:
            if file_ext == 'wav':
                metadata = self._analyze_wav(audio_data)
            elif file_ext in ['mp3', 'm4a']:
                metadata = self._analyze_compressed_audio(audio_data, file_ext)
            else:
                # Generic metadata for other formats
                metadata = AudioMetadata(
                    duration_seconds=0.0,  # Unknown
                    sample_rate=self.target_sample_rate,
                    format=file_ext,
                    size_bytes=len(audio_data),
                    quality_score=None
                )
            
            logger.info("Audio validation successful", 
                       filename=filename,
                       duration=metadata.duration_seconds,
                       sample_rate=metadata.sample_rate,
                       quality_score=metadata.quality_score)
            
            return metadata
            
        except Exception as e:
            logger.error("Audio analysis failed", filename=filename, error=str(e))
            raise AudioValidationError(f"Failed to analyze audio: {str(e)}")
    
    def _analyze_wav(self, audio_data: bytes) -> AudioMetadata:
        """Analyze WAV file format"""
        
        try:
            # Create BytesIO from audio data
            audio_io = io.BytesIO(audio_data)
            
            # Open with wave module
            with wave.open(audio_io, 'rb') as wav_file:
                frames = wav_file.getnframes()
                sample_rate = wav_file.getframerate()
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                
                # Calculate duration
                duration_seconds = frames / sample_rate if sample_rate > 0 else 0.0
                
                # Calculate quality score based on sample rate and bit depth
                quality_score = self._calculate_quality_score(sample_rate, sample_width, channels)
                
                return AudioMetadata(
                    duration_seconds=duration_seconds,
                    sample_rate=sample_rate,
                    format="wav",
                    size_bytes=len(audio_data),
                    quality_score=quality_score
                )
                
        except wave.Error as e:
            raise AudioValidationError(f"Invalid WAV file: {str(e)}")
        except Exception as e:
            raise AudioValidationError(f"WAV analysis error: {str(e)}")
    
    def _analyze_compressed_audio(self, audio_data: bytes, format_name: str) -> AudioMetadata:
        """Analyze compressed audio formats (MP3, M4A, etc.)"""
        
        try:
            # For compressed formats, we'll do basic validation
            # and estimate metadata (could be enhanced with libraries like mutagen)
            
            # Basic file signature validation
            signatures = {
                'mp3': [b'ID3', b'\xff\xfb', b'\xff\xf3', b'\xff\xf2'],
                'm4a': [b'ftyp', b'M4A ']
            }
            
            file_start = audio_data[:10]
            valid_signature = False
            
            for signature in signatures.get(format_name, []):
                if signature in file_start:
                    valid_signature = True
                    break
            
            if not valid_signature:
                logger.warning("No valid signature found, but proceeding", format=format_name)
            
            # Estimate duration (rough approximation for MP3)
            estimated_duration = self._estimate_compressed_duration(audio_data, format_name)
            
            # Default quality score for compressed audio
            quality_score = 0.8  # Assume good quality
            
            return AudioMetadata(
                duration_seconds=estimated_duration,
                sample_rate=self.target_sample_rate,  # Assume target sample rate
                format=format_name,
                size_bytes=len(audio_data),
                quality_score=quality_score
            )
            
        except Exception as e:
            raise AudioValidationError(f"{format_name.upper()} analysis error: {str(e)}")
    
    def _estimate_compressed_duration(self, audio_data: bytes, format_name: str) -> float:
        """Estimate duration for compressed audio formats"""
        
        # Rough estimation based on typical bitrates
        typical_bitrates = {
            'mp3': 128000,  # 128 kbps
            'm4a': 128000,  # 128 kbps
        }
        
        bitrate = typical_bitrates.get(format_name, 128000)
        
        # Duration = (file_size_bits * 8) / bitrate
        estimated_duration = (len(audio_data) * 8) / bitrate
        
        # Add some bounds checking
        estimated_duration = max(0.1, min(estimated_duration, 3600))  # 0.1s to 1 hour
        
        return estimated_duration
    
    def _calculate_quality_score(self, sample_rate: int, sample_width: int, channels: int) -> float:
        """Calculate audio quality score (0.0 to 1.0)"""
        
        score = 0.0
        
        # Sample rate scoring
        if sample_rate >= 44100:
            score += 0.4
        elif sample_rate >= 22050:
            score += 0.3
        elif sample_rate >= 16000:
            score += 0.2
        else:
            score += 0.1
        
        # Bit depth scoring
        if sample_width >= 3:  # 24-bit or higher
            score += 0.3
        elif sample_width >= 2:  # 16-bit
            score += 0.2
        else:  # 8-bit
            score += 0.1
        
        # Channel scoring
        if channels >= 2:  # Stereo or more
            score += 0.2
        else:  # Mono
            score += 0.1
        
        # Bonus for standard professional settings
        if sample_rate == 44100 and sample_width == 2:
            score += 0.1
        
        return min(1.0, score)
    
    def convert_to_wav(self, audio_data: bytes, filename: str) -> bytes:
        """
        Convert audio to WAV format if needed
        
        Args:
            audio_data: Original audio data
            filename: Original filename
            
        Returns:
            WAV-formatted audio data
        """
        file_ext = Path(filename).suffix.lower().lstrip('.')
        
        if file_ext == 'wav':
            return audio_data  # Already WAV
        
        try:
            # For now, we'll assume the audio is already in a compatible format
            # In a full implementation, you'd use libraries like pydub for conversion
            logger.info("Audio conversion not implemented, using original data", format=file_ext)
            return audio_data
            
        except Exception as e:
            logger.error("Audio conversion failed", error=str(e))
            raise AudioValidationError(f"Audio conversion failed: {str(e)}")
    
    def enhance_audio_for_speech(self, audio_data: bytes) -> bytes:
        """
        Apply audio enhancements for better speech recognition
        
        Args:
            audio_data: Raw audio data
            
        Returns:
            Enhanced audio data
        """
        # Placeholder for audio enhancement
        # Could include noise reduction, normalization, etc.
        
        logger.info("Audio enhancement not implemented, using original data")
        return audio_data
    
    def detect_speech_activity(self, audio_data: bytes) -> Dict[str, Any]:
        """
        Detect speech activity in audio
        
        Returns:
            Dictionary with speech detection results
        """
        # Placeholder for voice activity detection
        # Could detect silence periods, speech segments, etc.
        
        return {
            "has_speech": True,  # Assume speech is present
            "speech_ratio": 0.8,  # 80% speech
            "silence_periods": [],
            "speech_segments": []
        }


def create_test_audio_file() -> bytes:
    """Create a test WAV file for testing purposes"""
    
    # Create a simple test WAV file
    sample_rate = 16000
    duration = 2.0  # 2 seconds
    frequency = 440  # A4 note
    
    import math
    
    # Generate sine wave
    frames = int(duration * sample_rate)
    audio_data = []
    
    for i in range(frames):
        # Generate sine wave sample
        sample = int(32767 * 0.3 * math.sin(2 * math.pi * frequency * i / sample_rate))
        audio_data.append(struct.pack('<h', sample))  # Little-endian 16-bit
    
    # Create WAV header and combine with audio data
    audio_bytes = b''.join(audio_data)
    
    # Create minimal WAV file
    wav_data = io.BytesIO()
    with wave.open(wav_data, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b''.join(audio_data))
    
    return wav_data.getvalue()


# Optional enhanced audio processing with external libraries
class EnhancedAudioProcessor(AudioProcessor):
    """Enhanced audio processor with external library support"""
    
    def __init__(self):
        super().__init__()
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check for optional audio processing libraries"""
        self.has_pydub = False
        self.has_librosa = False
        
        try:
            import pydub
            self.has_pydub = True
            logger.info("pydub available for audio conversion")
        except ImportError:
            logger.info("pydub not available (optional)")
        
        try:
            import librosa
            self.has_librosa = True
            logger.info("librosa available for audio analysis")
        except ImportError:
            logger.info("librosa not available (optional)")
    
    def convert_to_wav(self, audio_data: bytes, filename: str) -> bytes:
        """Enhanced audio conversion using pydub"""
        
        if not self.has_pydub:
            return super().convert_to_wav(audio_data, filename)
        
        try:
            from pydub import AudioSegment
            
            file_ext = Path(filename).suffix.lower().lstrip('.')
            
            if file_ext == 'wav':
                return audio_data
            
            # Load audio with pydub
            audio_io = io.BytesIO(audio_data)
            audio_segment = AudioSegment.from_file(audio_io, format=file_ext)
            
            # Convert to WAV with target settings
            wav_audio = audio_segment.set_frame_rate(self.target_sample_rate).set_channels(1)
            
            # Export to bytes
            wav_io = io.BytesIO()
            wav_audio.export(wav_io, format="wav")
            
            logger.info("Audio converted to WAV", 
                       original_format=file_ext,
                       target_sample_rate=self.target_sample_rate)
            
            return wav_io.getvalue()
            
        except ImportError:
            return super().convert_to_wav(audio_data, filename)
        except Exception as e:
            logger.error("Enhanced audio conversion failed", error=str(e))
            raise AudioValidationError(f"Audio conversion failed: {str(e)}")
    
    def analyze_audio_quality(self, audio_data: bytes) -> Dict[str, float]:
        """Advanced audio quality analysis using librosa"""
        
        if not self.has_librosa:
            return {"quality_score": 0.8}  # Default score
        
        try:
            import librosa
            import numpy as np
            
            # Load audio with librosa
            audio_io = io.BytesIO(audio_data)
            y, sr = librosa.load(audio_io, sr=None)
            
            # Calculate various quality metrics
            rms_energy = float(np.sqrt(np.mean(y**2)))
            spectral_centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
            zero_crossing_rate = float(np.mean(librosa.feature.zero_crossing_rate(y)))
            
            # Combine metrics into quality score
            quality_score = min(1.0, (rms_energy * 2 + spectral_centroid / 1000 + (1 - zero_crossing_rate)) / 3)
            
            return {
                "quality_score": quality_score,
                "rms_energy": rms_energy,
                "spectral_centroid": spectral_centroid,
                "zero_crossing_rate": zero_crossing_rate
            }
            
        except Exception as e:
            logger.error("Advanced audio analysis failed", error=str(e))
            return {"quality_score": 0.8} 