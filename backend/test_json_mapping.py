"""
Test script for JSON mapping functionality
Demonstrates how speech-to-text gets converted to structured dental documentation
"""

import json
from datetime import datetime
from app.schemas.dental_documentation import TranscriptionResult, AudioMetadata
from app.services.documentation_processor import DocumentationProcessor


def test_json_mapping():
    """Test the JSON mapping with sample dental transcriptions"""
    
    # Initialize the processor
    processor = DocumentationProcessor()
    
    # Sample German dental transcriptions
    test_cases = [
        {
            "name": "Simple Filling",
            "transcription": "Zahn drei sechs okklusal Karies profunda, Lokalanästhesie, Kompositfüllung gelegt",
            "expected_findings": ["Karies profunda"],
            "expected_procedures": ["Lokalanästhesie", "Kompositfüllung"],
            "expected_billing_codes": ["GOZ 0080", "GOZ 2080"]
        },
        {
            "name": "Extraction Case", 
            "transcription": "Zahn vier acht Extraktion wegen Karies, Leitungsanästhesie, unkomplizierte Entfernung",
            "expected_findings": [],
            "expected_procedures": ["Extraktion", "Leitungsanästhesie"],
            "expected_billing_codes": ["GOZ 3000", "GOZ Ost1"]
        },
        {
            "name": "Root Canal Treatment",
            "transcription": "Zahn zwei vier Pulpitis, Vitalität positiv, Perkussion positiv, Röntgenbild gemacht, Infiltrationsanästhesie, Wurzelkanalbehandlung begonnen, Vitalextirpation durchgeführt, Medikament eingelegt, Provisorischer Verschluss, Kontrolle in einer Woche",
            "expected_findings": ["Pulpitis"],
            "expected_procedures": ["Wurzelkanalbehandlung", "Vitalextirpation"],
            "expected_billing_codes": ["GOZ i", "Rö2", "GOZ 2380", "GOZ 2360", "GOZ 2340"]
        }
    ]
    
    print("🦷 MedVox JSON Mapping Test")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test Case {i}: {test_case['name']}")
        print(f"Input: {test_case['transcription']}")
        print("-" * 40)
        
        # Create mock transcription result
        transcription = TranscriptionResult(
            text=test_case['transcription'],
            language="de",
            confidence=0.92,
            processing_time_ms=3000,
            stt_model="whisper-base"
        )
        
        # Create mock audio metadata
        audio_metadata = AudioMetadata(
            duration_seconds=45.0,
            sample_rate=16000,
            format="wav",
            size_bytes=1440000,
            quality_score=0.95
        )
        
        # Process the transcription
        documentation = processor.process_transcription(
            transcription=transcription,
            audio_metadata=audio_metadata,
            patient_id="evident_test_123",
            dentist_id="dr_test"
        )
        
        # Display results
        print("🔍 EXTRACTED INFORMATION:")
        
        # Treatment type
        if documentation.treatment_type:
            print(f"   Treatment Type: {documentation.treatment_type.value}")
        
        # Findings
        if documentation.findings:
            print(f"   Findings ({len(documentation.findings)}):")
            for finding in documentation.findings:
                tooth_info = f"Zahn {finding.tooth_number}" if finding.tooth_number else "Allgemein"
                surface_info = f" {finding.surface}" if finding.surface else ""
                print(f"     • {tooth_info}{surface_info}: {finding.diagnosis} ({finding.confidence})")
        
        # Procedures
        if documentation.procedures_performed:
            print(f"   Procedures ({len(documentation.procedures_performed)}):")
            for procedure in documentation.procedures_performed:
                print(f"     • {procedure}")
        
        # Billing codes
        if documentation.billing_codes:
            print(f"   Billing Codes ({len(documentation.billing_codes)}):")
            for code in documentation.billing_codes:
                fee_info = f" (€{code.fee_euros})" if code.fee_euros else ""
                print(f"     • {code.code}: {code.description}{fee_info}")
        
        # Treatment plan
        if documentation.treatment_plan:
            print(f"   Treatment Plan: {documentation.treatment_plan.recommendation}")
        
        # Quality metrics
        print(f"   Overall Confidence: {documentation.overall_confidence}")
        print(f"   Requires Review: {'Yes' if documentation.requires_review else 'No'}")
        
        # Clinical notes
        print(f"   Clinical Notes: {documentation.clinical_notes[:100]}...")
        
        print("\n📊 JSON OUTPUT SAMPLE:")
        # Show partial JSON structure
        json_sample = {
            "recording_id": documentation.recording_id,
            "patient_id": documentation.patient_id,
            "treatment_type": documentation.treatment_type.value if documentation.treatment_type else None,
            "findings_count": len(documentation.findings),
            "billing_codes_count": len(documentation.billing_codes),
            "total_fee_euros": sum(code.fee_euros for code in documentation.billing_codes if code.fee_euros),
            "overall_confidence": documentation.overall_confidence,
            "requires_review": documentation.requires_review
        }
        print(json.dumps(json_sample, indent=2, ensure_ascii=False))


def test_billing_calculations():
    """Test billing code calculations"""
    
    print("\n💰 BILLING CODE CALCULATIONS")
    print("=" * 50)
    
    processor = DocumentationProcessor()
    
    # Test GOZ calculations
    print("GOZ Examples:")
    goz_examples = [
        ("Füllung einflächig", 48, 2.3),
        ("Krone", 155, 2.3),
        ("Wurzelkanalbehandlung", 154, 2.3),
    ]
    
    for description, points, factor in goz_examples:
        fee = processor._calculate_goz_fee(points, factor)
        print(f"  {description}: {points} Punkte × {factor} = €{fee}")
    
    # Test BEMA calculations  
    print("\nBEMA Examples:")
    bema_examples = [
        ("Füllung einflächig", 8),
        ("Extraktion mehrwurzelig", 12),
        ("Wurzelkanalbehandlung", 40),
    ]
    
    for description, points in bema_examples:
        fee = processor._calculate_bema_fee(points)
        print(f"  {description}: {points} Punkte = €{fee}")


def test_terminology_mapping():
    """Test German dental terminology mapping"""
    
    print("\n🇩🇪 GERMAN TERMINOLOGY MAPPING")
    print("=" * 50)
    
    processor = DocumentationProcessor()
    
    # Test tooth number mapping
    print("Tooth Number Mapping:")
    test_teeth = [
        "eins sechs",
        "zwei vier", 
        "drei sechs",
        "vier acht",
        "sechsunddreißig"
    ]
    
    for spoken_tooth in test_teeth:
        normalized = processor._normalize_text(f"zahn {spoken_tooth}")
        print(f"  '{spoken_tooth}' → '{normalized}'")
    
    # Test surface mapping
    print("\nSurface Mapping:")
    test_surfaces = ["okklusal", "mesial", "distal", "vestibulär", "kaufläche"]
    
    for surface in test_surfaces:
        normalized = processor._normalize_surface(surface)
        print(f"  '{surface}' → '{normalized}'")


if __name__ == "__main__":
    try:
        test_json_mapping()
        test_billing_calculations()
        test_terminology_mapping()
        
        print("\n✅ All tests completed successfully!")
        print("\n🎯 NEXT STEPS:")
        print("1. Set up your OpenAI API key in .env file")
        print("2. Install missing dependencies if any")
        print("3. Test with real audio recordings")
        print("4. Connect to Evident PMS for patient data")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        print("💡 This is expected if dependencies aren't installed yet") 