"""
Session schemas for managing multiple recordings
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class SessionSummary(BaseModel):
    """Summary of a recording session for list display"""

    id: int = Field(..., description="Session/Recording ID")
    patient_id: Optional[str] = Field(None, description="Patient identifier")
    dentist_id: int = Field(..., description="Dentist user ID")
    dentist_name: str = Field(..., description="Dentist name for display")
    transcription_preview: str = Field(..., description="First 100 characters of transcription")
    processing_mode: str = Field(..., description="Processing mode: transcription_only or with_billing")
    billing_codes_count: int = Field(0, description="Number of billing codes extracted")
    created_at: datetime = Field(..., description="Session creation timestamp")
    status: str = Field(..., description="Recording status")

    model_config = ConfigDict(json_schema_extra={"example": {
        "id": 123,
        "patient_id": "12345",
        "dentist_id": 1,
        "dentist_name": "Dr. Müller",
        "transcription_preview": "Zahn 36 okklusal Karies profunda...",
        "processing_mode": "with_billing",
        "billing_codes_count": 3,
        "created_at": "2026-02-12T10:30:00",
        "status": "transcribed"
    }})


class SessionListResponse(BaseModel):
    """Response containing list of sessions"""

    sessions: List[SessionSummary] = Field(..., description="List of session summaries")
    total: int = Field(..., description="Total number of sessions")

    model_config = ConfigDict(json_schema_extra={"example": {
        "sessions": [],
        "total": 10
    }})
