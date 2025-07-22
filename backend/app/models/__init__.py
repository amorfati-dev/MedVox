"""
Database models for MedVox application
"""

from app.models.base import Base, BaseModel, TimestampMixin
from app.models.user import User, UserRole
from app.models.patient import Patient, Gender, InsuranceType
from app.models.recording import Recording, RecordingStatus
from app.models.transcription import Transcription
from app.models.treatment import Treatment, treatment_medical_codes
from app.models.medical_code import MedicalCode, CodeSystem

# Export all models and enums
__all__ = [
    # Base classes
    "Base",
    "BaseModel", 
    "TimestampMixin",
    
    # Models
    "User",
    "Patient",
    "Recording",
    "Transcription",
    "Treatment",
    "MedicalCode",
    
    # Enums
    "UserRole",
    "Gender",
    "InsuranceType",
    "RecordingStatus",
    "CodeSystem",
    
    # Association tables
    "treatment_medical_codes",
] 