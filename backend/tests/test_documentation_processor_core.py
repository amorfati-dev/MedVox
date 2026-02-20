import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.schemas.dental_documentation import AudioMetadata, TranscriptionResult
from app.services.documentation_processor import DocumentationProcessor


def test_empty_transcription_returns_no_billing_codes():
    processor = DocumentationProcessor()

    transcription = TranscriptionResult(
        text="   ",
        language="de",
        confidence=0.0,
        processing_time_ms=10,
        stt_model="test",
    )
    metadata = AudioMetadata(
        duration_seconds=1.0,
        sample_rate=16000,
        format="wav",
        size_bytes=1024,
        quality_score=0.5,
    )

    result = asyncio.run(
        processor.process_transcription(
            transcription_result=transcription,
            audio_metadata=metadata,
            insurance_type="bema",
            patient_id="p1",
            dentist_id="d1",
        )
    )

    assert result.billing_codes == []
    assert result.procedures_performed == []
    assert "Keine Transkription erkannt" in result.clinical_notes
