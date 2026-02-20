"""
Pydantic schemas for Transfer API

Defines request/response models for QR-code based data transfer
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime


class BillingCodeSchema(BaseModel):
    """
    Billing code (BEMA/GOZ)

    Flexible schema to support various formats from LLM
    """
    code: str = Field(..., description="Billing code (e.g., '13a', '2080')")
    system: Optional[str] = Field(None, description="BEMA or GOZ")
    description: Optional[str] = Field(None, description="Code description")
    quantity: Optional[int] = Field(1, description="Quantity/count")
    tooth_number: Optional[str] = Field(None, description="Tooth number (e.g., '36')")
    is_zusatzleistung: Optional[bool] = Field(False, description="Additional private service")


class CreateTransferRequest(BaseModel):
    """
    Request to create a new transfer session
    """
    billing_codes: List[BillingCodeSchema] = Field(
        ...,
        min_length=1,
        description="List of billing codes to transfer"
    )
    transcription: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="Voice transcription text"
    )
    patient_id: Optional[str] = Field(
        None,
        max_length=100,
        description="Optional patient identifier"
    )

    @field_validator('billing_codes')
    @classmethod
    def validate_billing_codes_not_empty(cls, v):
        """Ensure at least one billing code"""
        if not v or len(v) == 0:
            raise ValueError("At least one billing code required")
        return v


class CreateTransferResponse(BaseModel):
    """
    Response after creating transfer session
    """
    session_id: str = Field(..., description="Unique session identifier (UUID)")
    short_code: str = Field(..., description="6-character transfer code (e.g., AB1234)")
    transfer_url: str = Field(..., description="URL for transfer page")
    qr_code: str = Field(..., description="QR code as base64 data URL")
    expires_at: datetime = Field(..., description="Expiration timestamp")
    expires_in_seconds: int = Field(..., description="Seconds until expiration")

    model_config = ConfigDict(json_schema_extra={"example": {
        "session_id": "550e8400-e29b-41d4-a716-446655440000",
        "transfer_url": "https://medvox.app/transfer/550e8400-e29b-41d4-a716-446655440000",
        "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANS...",
        "expires_at": "2026-02-12T10:35:00.000000",
        "expires_in_seconds": 300
    }})


class TransferSessionResponse(BaseModel):
    """
    Response when retrieving transfer session
    """
    session_id: str = Field(..., description="Session identifier")
    billing_codes: List[Dict[str, Any]] = Field(..., description="List of billing codes")
    transcription: str = Field(..., description="Voice transcription")
    patient_id: Optional[str] = Field(None, description="Patient identifier if provided")
    created_at: datetime = Field(..., description="Session creation timestamp")

    model_config = ConfigDict(json_schema_extra={"example": {
        "session_id": "550e8400-e29b-41d4-a716-446655440000",
        "billing_codes": [
            {
                "code": "13a",
                "system": "BEMA",
                "description": "Füllungstherapie einflächig",
                "quantity": 1,
                "tooth_number": "36"
            }
        ],
        "transcription": "Zahn 36, MOD-Füllung mit Komposite",
        "patient_id": "12345",
        "created_at": "2026-02-12T10:30:00.000000"
    }})


class ErrorResponse(BaseModel):
    """
    Standard error response
    """
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Machine-readable error code")

    model_config = ConfigDict(json_schema_extra={"example": {
        "detail": "Session not found or expired",
        "error_code": "SESSION_NOT_FOUND"
    }})
