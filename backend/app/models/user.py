"""
User model for authentication and authorization
"""

from sqlalchemy import Boolean, Column, String, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel


class UserRole(enum.Enum):
    """User roles in the system"""
    ADMIN = "admin"
    DENTIST = "dentist"
    ASSISTANT = "assistant"
    RECEPTIONIST = "receptionist"


class User(BaseModel):
    """User model for dental practice staff"""
    
    __tablename__ = "users"
    
    # Authentication fields
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # Profile fields
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.DENTIST, nullable=False)
    
    # Status fields
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    
    # Professional fields
    license_number = Column(String(50), nullable=True)  # For dentists
    specialization = Column(String(100), nullable=True)  # e.g., "Orthodontics"
    
    # Relationships
    recordings = relationship("Recording", back_populates="created_by", lazy="dynamic")
    treatments = relationship("Treatment", back_populates="performed_by", lazy="dynamic")
    
    @property
    def full_name(self) -> str:
        """Return user's full name"""
        return f"{self.first_name} {self.last_name}"
    
    def __repr__(self) -> str:
        return f"<User {self.email} - {self.role.value}>" 