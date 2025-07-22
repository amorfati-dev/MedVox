"""
Medical code model for GOZ/BEMA codes
"""

from sqlalchemy import Column, String, Text, Float, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel
from app.models.treatment import treatment_medical_codes


class CodeSystem(enum.Enum):
    """Medical code systems used in German dental practices"""
    GOZ = "goz"  # Gebührenordnung für Zahnärzte (private insurance)
    BEMA = "bema"  # Bewertungsmaßstab zahnärztlicher Leistungen (public insurance)


class MedicalCode(BaseModel):
    """Medical codes for dental procedures (GOZ/BEMA)"""
    
    __tablename__ = "medical_codes"
    
    # Code identification
    code = Column(String(20), nullable=False, index=True)
    system = Column(SQLEnum(CodeSystem), nullable=False)
    
    # Code description
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Financial information
    base_points = Column(Float, nullable=True)  # Points value for BEMA
    base_fee = Column(Float, nullable=True)  # Base fee for GOZ
    
    # Categorization
    category = Column(String(100), nullable=True)  # e.g., "Konservierende Zahnheilkunde"
    subcategory = Column(String(100), nullable=True)  # e.g., "Füllungen"
    
    # Metadata
    is_active = Column(Boolean, default=True, nullable=False)
    valid_from = Column(String(10), nullable=True)  # YYYY-MM-DD
    valid_until = Column(String(10), nullable=True)  # YYYY-MM-DD
    
    # Search optimization
    search_terms = Column(Text, nullable=True)  # Comma-separated search terms
    
    # Relationships
    treatments = relationship(
        "Treatment",
        secondary=treatment_medical_codes,
        back_populates="medical_codes",
        lazy="dynamic"
    )
    
    def __repr__(self) -> str:
        return f"<MedicalCode {self.system.value} {self.code} - {self.name}>"
    
    @property
    def full_code(self) -> str:
        """Return formatted code with system prefix"""
        return f"{self.system.value.upper()} {self.code}" 