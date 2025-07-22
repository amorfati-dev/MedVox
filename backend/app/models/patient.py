"""
Patient model for dental practice
"""

from datetime import date
from sqlalchemy import Column, String, Date, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel


class Gender(enum.Enum):
    """Patient gender options"""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class InsuranceType(enum.Enum):
    """Insurance type options"""
    PUBLIC = "public"  # Gesetzlich versichert
    PRIVATE = "private"  # Privat versichert
    SELF_PAY = "self_pay"  # Selbstzahler


class Patient(BaseModel):
    """Patient model with dental practice specific fields"""
    
    __tablename__ = "patients"
    
    # Personal information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(SQLEnum(Gender), nullable=False)
    
    # Contact information
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    mobile = Column(String(50), nullable=True)
    
    # Address
    street = Column(String(200), nullable=True)
    house_number = Column(String(20), nullable=True)
    postal_code = Column(String(10), nullable=True)
    city = Column(String(100), nullable=True)
    
    # Insurance information
    insurance_type = Column(SQLEnum(InsuranceType), default=InsuranceType.PUBLIC, nullable=False)
    insurance_company = Column(String(100), nullable=True)
    insurance_number = Column(String(50), nullable=True)
    
    # Medical information
    allergies = Column(Text, nullable=True)
    medications = Column(Text, nullable=True)
    medical_notes = Column(Text, nullable=True)
    
    # External system IDs
    evident_patient_id = Column(String(50), nullable=True, unique=True, index=True)
    
    # Relationships
    recordings = relationship("Recording", back_populates="patient", lazy="dynamic")
    treatments = relationship("Treatment", back_populates="patient", lazy="dynamic")
    
    @property
    def full_name(self) -> str:
        """Return patient's full name"""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def age(self) -> int:
        """Calculate patient's age"""
        if not self.date_of_birth:
            return 0
        today = date.today()
        age = today.year - self.date_of_birth.year
        if today.month < self.date_of_birth.month or (
            today.month == self.date_of_birth.month and today.day < self.date_of_birth.day
        ):
            age -= 1
        return age
    
    def __repr__(self) -> str:
        return f"<Patient {self.full_name} - {self.insurance_type.value}>" 