"""
Transcription model for storing transcribed text from recordings
"""

from sqlalchemy import Column, String, Text, ForeignKey, Float, JSON, Integer
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Transcription(BaseModel):
    """Transcription model for audio-to-text conversions"""
    
    __tablename__ = "transcriptions"
    
    # Transcription content
    text = Column(Text, nullable=False)
    language = Column(String(10), default="de", nullable=False)  # ISO language code
    
    # Transcription metadata
    model_used = Column(String(50), nullable=True)  # e.g., "whisper-large"
    confidence_score = Column(Float, nullable=True)  # Overall confidence 0-1
    processing_time = Column(Float, nullable=True)  # Time taken in seconds
    
    # Segments with timestamps (for future word-level highlighting)
    segments = Column(JSON, nullable=True)  # Array of {text, start, end, confidence}
    
    # Medical terms detected
    medical_terms = Column(JSON, nullable=True)  # Array of detected medical terms
    
    # Foreign key
    recording_id = Column(Integer, ForeignKey("recordings.id"), unique=True, nullable=False)
    
    # Relationships
    recording = relationship("Recording", back_populates="transcription")
    treatment = relationship("Treatment", back_populates="transcription", uselist=False)
    
    def __repr__(self) -> str:
        text_preview = self.text[:50] + "..." if len(self.text) > 50 else self.text
        return f"<Transcription {text_preview}>" 