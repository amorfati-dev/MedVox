"""
Dental Documentation JSON Schemas
Core data structures for mapping speech-to-text into structured dental documentation
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator


class TreatmentType(str, Enum):
    """Common dental treatment types"""
    PROPHYLAXIS = "prophylaxis"
    FILLING = "filling" 
    EXTRACTION = "extraction"
    ROOT_CANAL = "root_canal"
    CROWN = "crown"
    BRIDGE = "bridge"
    IMPLANT = "implant"
    SURGERY = "surgery"
    EXAMINATION = "examination"
    CONSULTATION = "consultation"


class ToothNumbering(str, Enum):
    """FDI tooth numbering system (standard in Germany)"""
    # Adult teeth (11-18, 21-28, 31-38, 41-48)
    # Child teeth (51-55, 61-65, 71-75, 81-85)
    pass  # Will be populated with actual tooth numbers


class BillingSystem(str, Enum):
    """German dental billing systems"""
    BEMA = "bema"  # Statutory insurance
    GOZ = "goz"    # Private insurance/self-pay


class ConfidenceLevel(str, Enum):
    """AI confidence levels for recognition"""
    HIGH = "high"      # >90% confidence
    MEDIUM = "medium"  # 70-90% confidence  
    LOW = "low"        # 50-70% confidence
    UNSURE = "unsure"  # <50% confidence


class DentalFinding(BaseModel):
    """Individual dental finding/diagnosis"""
    
    tooth_number: Optional[str] = Field(None, description="FDI tooth number (e.g. '36', '11')")
    surface: Optional[str] = Field(None, description="Tooth surface (mesial, distal, okklusal, etc.)")
    diagnosis: str = Field(..., description="Clinical finding/diagnosis")
    severity: Optional[str] = Field(None, description="Severity level if applicable")
    confidence: ConfidenceLevel = Field(ConfidenceLevel.MEDIUM, description="AI confidence level")
    
    class Config:
        json_schema_extra = {
            "example": {
                "tooth_number": "36",
                "surface": "okklusal",
                "diagnosis": "Karies profunda",
                "severity": "tief",
                "confidence": "high"
            }
        }


class BillingCode(BaseModel):
    """Billing code (BEMA/GOZ) with details"""
    
    code: str = Field(..., description="Billing code (e.g. 'BEMA 13', 'GOZ 2080')")
    system: BillingSystem = Field(..., description="Billing system")
    description: str = Field(..., description="Code description")
    factor: Optional[float] = Field(None, description="GOZ factor if applicable")
    points: Optional[int] = Field(None, description="Point value")
    fee_euros: Optional[float] = Field(None, description="Calculated fee in EUR")
    tooth_number: Optional[str] = Field(None, description="Related tooth if applicable")
    confidence: ConfidenceLevel = Field(ConfidenceLevel.MEDIUM, description="AI confidence level")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "GOZ 2080",
                "system": "goz",
                "description": "Füllung einflächig",
                "factor": 2.3,
                "points": 48,
                "fee_euros": 26.40,
                "tooth_number": "36",
                "confidence": "high"
            }
        }


class TreatmentPlan(BaseModel):
    """Treatment planning recommendations"""
    
    recommendation: str = Field(..., description="Treatment recommendation")
    priority: Optional[str] = Field(None, description="Priority level (urgent, routine, optional)")
    estimated_sessions: Optional[int] = Field(None, description="Estimated number of sessions")
    follow_up_weeks: Optional[int] = Field(None, description="Follow-up period in weeks")
    notes: Optional[str] = Field(None, description="Additional notes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "recommendation": "Wurzelkanalbehandlung Zahn 36",
                "priority": "urgent",
                "estimated_sessions": 3,
                "follow_up_weeks": 2,
                "notes": "Röntgenkontrolle erforderlich"
            }
        }


class AudioMetadata(BaseModel):
    """Metadata about the audio recording"""
    
    duration_seconds: float = Field(..., description="Recording duration")
    sample_rate: int = Field(16000, description="Audio sample rate")
    format: str = Field("wav", description="Audio format")
    size_bytes: int = Field(..., description="File size in bytes")
    quality_score: Optional[float] = Field(None, description="Audio quality score 0-1")
    
    class Config:
        json_schema_extra = {
            "example": {
                "duration_seconds": 45.2,
                "sample_rate": 16000,
                "format": "wav",
                "size_bytes": 1440000,
                "quality_score": 0.95
            }
        }


class TranscriptionResult(BaseModel):
    """Raw speech-to-text result"""
    
    text: str = Field(..., description="Transcribed text")
    language: str = Field("de", description="Detected language")
    confidence: float = Field(..., description="Overall transcription confidence 0-1")
    segments: Optional[List[Dict[str, Any]]] = Field(None, description="Time-segmented transcription")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    stt_model: str = Field("whisper-base", description="STT model used")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "Zahn drei sechs okklusal Karies profunda, Füllung Komposit gelegt",
                "language": "de",
                "confidence": 0.92,
                "processing_time_ms": 3200,
                "stt_model": "whisper-base"
            }
        }


class DentalDocumentation(BaseModel):
    """Complete structured dental documentation from voice input"""
    
    # Input data
    recording_id: str = Field(..., description="Unique recording identifier")
    patient_id: Optional[str] = Field(None, description="Patient identifier (evident ID)")
    dentist_id: str = Field(..., description="Dentist identifier")
    timestamp: datetime = Field(default_factory=datetime.now, description="Documentation timestamp")
    
    # Audio and transcription
    audio_metadata: AudioMetadata = Field(..., description="Audio recording metadata")
    transcription: TranscriptionResult = Field(..., description="Speech-to-text result")
    
    # Processed clinical data
    treatment_type: Optional[TreatmentType] = Field(None, description="Primary treatment type")
    findings: List[DentalFinding] = Field(default_factory=list, description="Clinical findings")
    procedures_performed: List[str] = Field(default_factory=list, description="Procedures performed")
    billing_codes: List[BillingCode] = Field(default_factory=list, description="Billing codes")
    treatment_plan: Optional[TreatmentPlan] = Field(None, description="Future treatment planning")
    
    # Clinical documentation
    clinical_notes: str = Field("", description="Structured clinical notes")
    anesthesia_used: Optional[str] = Field(None, description="Anesthesia type if used")
    materials_used: List[str] = Field(default_factory=list, description="Materials/medications used")
    
    # Quality and review
    overall_confidence: ConfidenceLevel = Field(ConfidenceLevel.MEDIUM, description="Overall AI confidence")
    requires_review: bool = Field(False, description="Flag if manual review needed")
    review_notes: Optional[str] = Field(None, description="Notes for manual review")
    
    # Integration status
    exported_to_evident: bool = Field(False, description="Exported to Evident PMS")
    export_timestamp: Optional[datetime] = Field(None, description="Export timestamp")
    
    @validator('overall_confidence', always=True)
    def calculate_overall_confidence(cls, v, values):
        """Calculate overall confidence based on transcription and extracted data"""
        transcription = values.get('transcription')
        billing_codes = values.get('billing_codes', [])
        
        if not transcription:
            return ConfidenceLevel.LOW
            
        # Base confidence on transcription quality
        base_confidence = transcription.confidence
        
        # Adjust based on billing code confidence
        if billing_codes:
            avg_code_confidence = sum(
                1.0 if code.confidence == ConfidenceLevel.HIGH else
                0.8 if code.confidence == ConfidenceLevel.MEDIUM else
                0.6 if code.confidence == ConfidenceLevel.LOW else 0.4
                for code in billing_codes
            ) / len(billing_codes)
            base_confidence = (base_confidence + avg_code_confidence) / 2
        
        # Convert to confidence level
        if base_confidence >= 0.9:
            return ConfidenceLevel.HIGH
        elif base_confidence >= 0.7:
            return ConfidenceLevel.MEDIUM
        elif base_confidence >= 0.5:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.UNSURE
    
    @validator('requires_review', always=True)
    def determine_review_requirement(cls, v, values):
        """Determine if manual review is required"""
        overall_confidence = values.get('overall_confidence', ConfidenceLevel.LOW)
        billing_codes = values.get('billing_codes', [])
        
        # Require review for low confidence
        if overall_confidence in [ConfidenceLevel.LOW, ConfidenceLevel.UNSURE]:
            return True
            
        # Require review for high-value billing codes
        if any(code.fee_euros and code.fee_euros > 100 for code in billing_codes):
            return True
            
        # Require review if no billing codes found but procedures mentioned
        procedures = values.get('procedures_performed', [])
        if procedures and not billing_codes:
            return True
            
        return False
    
    class Config:
        json_schema_extra = {
            "example": {
                "recording_id": "rec_2024_07_20_001",
                "patient_id": "evident_12345",
                "dentist_id": "dr_mueller",
                "treatment_type": "filling",
                "findings": [
                    {
                        "tooth_number": "36",
                        "surface": "okklusal",
                        "diagnosis": "Karies profunda",
                        "confidence": "high"
                    }
                ],
                "procedures_performed": ["Lokalanästhesie", "Kompositfüllung"],
                "billing_codes": [
                    {
                        "code": "GOZ 2080",
                        "system": "goz",
                        "description": "Füllung einflächig",
                        "fee_euros": 26.40,
                        "confidence": "high"
                    },
                    {
                        "code": "BEMA L1",
                        "system": "bema",
                        "description": "Leitungsanästhesie",
                        "fee_euros": 10.72,
                        "confidence": "high"
                    },
                    {
                        "code": "GOZ 0090",
                        "system": "goz",
                        "description": "Leitungsanästhesie",
                        "fee_euros": 12.00,
                        "confidence": "high"
                    },
                    {
                        "code": "BEMA bmf",
                        "system": "bema",
                        "description": "Stillung einer Papillenblutung, Zähne separiert",
                        "fee_euros": 6.00,
                        "confidence": "medium"
                    }
                ],
                "clinical_notes": "Zahn 36 okklusal: Karies profunda entfernt, Kompositfüllung gelegt",
                "overall_confidence": "high",
                "requires_review": False
            }
        }


# Response schemas for API endpoints
class DocumentationCreateRequest(BaseModel):
    """Request to create documentation from audio"""
    
    patient_id: Optional[str] = Field(None, description="Patient ID from Evident")
    dentist_id: str = Field(..., description="Dentist identifier")
    treatment_context: Optional[str] = Field(None, description="Treatment context/notes")
    # Audio file will be uploaded separately
    
    class Config:
        json_schema_extra = {
            "example": {
                "patient_id": "evident_12345",
                "dentist_id": "dr_mueller",
                "treatment_context": "Routine checkup and cleaning"
            }
        }


class DocumentationResponse(BaseModel):
    """API response with documentation result"""
    
    success: bool = Field(..., description="Processing success")
    documentation: Optional[DentalDocumentation] = Field(None, description="Structured documentation")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    processing_time_ms: int = Field(..., description="Total processing time")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "documentation": {
                    "recording_id": "rec_2024_07_20_001",
                    "overall_confidence": "high",
                    "requires_review": False
                },
                "processing_time_ms": 5420
            }
        } 