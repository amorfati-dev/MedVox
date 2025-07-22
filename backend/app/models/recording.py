"""
Recording model for audio recordings
"""

from sqlalchemy import Column, String, Integer, Float, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel


class RecordingStatus(enum.Enum):
    """Recording processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    TRANSCRIBED = "transcribed"
    FAILED = "failed"
    DELETED = "deleted"


class Recording(BaseModel):
    """Audio recording model"""
    
    __tablename__ = "recordings"
    
    # File information
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)  # Size in bytes
    duration = Column(Float, nullable=True)  # Duration in seconds
    format = Column(String(10), nullable=False)  # wav, mp3, etc.
    
    # Recording metadata
    status = Column(SQLEnum(RecordingStatus), default=RecordingStatus.PENDING, nullable=False)
    error_message = Column(Text, nullable=True)
    
    # Audio metadata
    sample_rate = Column(Integer, nullable=True)
    channels = Column(Integer, nullable=True)
    bitrate = Column(Integer, nullable=True)
    
    # Foreign keys
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    patient = relationship("Patient", back_populates="recordings")
    created_by = relationship("User", back_populates="recordings")
    transcription = relationship("Transcription", back_populates="recording", uselist=False)
    
    def __repr__(self) -> str:
        return f"<Recording {self.filename} - {self.status.value}>" 