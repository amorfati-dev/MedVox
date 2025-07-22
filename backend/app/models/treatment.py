"""
Treatment model for dental procedures and treatments
"""

from datetime import datetime
from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Float, JSON, Table, Integer
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, Base


# Association table for many-to-many relationship between treatments and medical codes
treatment_medical_codes = Table(
    'treatment_medical_codes',
    Base.metadata,
    Column('treatment_id', ForeignKey('treatments.id'), primary_key=True),
    Column('medical_code_id', ForeignKey('medical_codes.id'), primary_key=True),
    Column('quantity', Float, default=1.0),  # How many times this code was applied
    Column('notes', Text, nullable=True)
)


class Treatment(BaseModel):
    """Treatment model for dental procedures"""
    
    __tablename__ = "treatments"
    
    # Treatment information
    treatment_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    tooth_numbers = Column(JSON, nullable=True)  # Array of tooth numbers [14, 15, 16]
    diagnosis = Column(Text, nullable=False)
    treatment_description = Column(Text, nullable=False)
    
    # Treatment planning
    treatment_plan = Column(Text, nullable=True)
    next_appointment = Column(DateTime, nullable=True)
    
    # Financial information
    total_cost = Column(Float, nullable=True)
    insurance_coverage = Column(Float, nullable=True)
    patient_payment = Column(Float, nullable=True)
    
    # Documentation
    notes = Column(Text, nullable=True)
    images = Column(JSON, nullable=True)  # Array of image URLs/paths
    
    # Foreign keys
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    performed_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    transcription_id = Column(Integer, ForeignKey("transcriptions.id"), nullable=True, unique=True)
    
    # External system IDs
    evident_treatment_id = Column(String(50), nullable=True, unique=True, index=True)
    
    # Relationships
    patient = relationship("Patient", back_populates="treatments")
    performed_by = relationship("User", back_populates="treatments")
    transcription = relationship("Transcription", back_populates="treatment")
    medical_codes = relationship(
        "MedicalCode",
        secondary=treatment_medical_codes,
        back_populates="treatments",
        lazy="dynamic"
    )
    
    def __repr__(self) -> str:
        return f"<Treatment {self.treatment_date} - {self.diagnosis[:30]}...>" 