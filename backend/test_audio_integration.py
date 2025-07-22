"""
Audio Integration Test Script
Tests the complete pipeline: Audio Upload → Transcription → Documentation → JSON Output
"""

import asyncio
import io
import json
import time
from pathlib import Path
import structlog

# Configure simple logging for tests
import logging
logging.basicConfig(level=logging.INFO)

from app.services.audio_service import AudioService, AudioTranscriptionError
from app.services.documentation_processor import DocumentationProcessor
from app.utils.audio import create_test_audio_file, AudioProcessor
from app.schemas.dental_documentation import TranscriptionResult, AudioMetadata


class AudioIntegrationTester:
    """Test suite for audio integration"""
    
    def __init__(self):
        self.audio_service = AudioService()
        self.doc_processor = DocumentationProcessor()
        self.audio_processor = AudioProcessor()
        
    async def test_mock_transcription_pipeline(self):
        """Test the complete pipeline with mock transcription"""
        
        print("\n🎤 TESTING MOCK AUDIO PIPELINE")
        print("=" * 50)
        
        try:
            # Create test audio file
            print("📁 Creating test audio file...")
            test_audio = create_test_audio_file()
            audio_file = io.BytesIO(test_audio)
            filename = "test_audio.wav"
            
            print(f"✅ Test audio created: {len(test_audio)} bytes")
            
            # Process with mock transcription
            print("\n🔄 Processing audio with mock transcription...")
            start_time = time.time()
            
            transcription_result, audio_metadata = await self.audio_service.process_audio(
                audio_file,
                filename,
                use_mock=True
            )
            
            processing_time = time.time() - start_time
            
            print(f"✅ Mock transcription completed in {processing_time:.2f}s")
            print(f"📝 Transcribed text: {transcription_result.text}")
            print(f"🎯 Confidence: {transcription_result.confidence}")
            
            # Process transcription into documentation
            print("\n📋 Processing transcription into documentation...")
            documentation = self.doc_processor.process_transcription(
                transcription=transcription_result,
                audio_metadata=audio_metadata,
                patient_id="test_patient_123",
                dentist_id="dr_test"
            )
            
            # Display results
            print("\n🔍 EXTRACTED INFORMATION:")
            print(f"   Recording ID: {documentation.recording_id}")
            print(f"   Treatment Type: {documentation.treatment_type}")
            print(f"   Findings: {len(documentation.findings)}")
            print(f"   Procedures: {len(documentation.procedures_performed)}")
            print(f"   Billing Codes: {len(documentation.billing_codes)}")
            print(f"   Total Fee: €{sum(code.fee_euros for code in documentation.billing_codes if code.fee_euros):.2f}")
            print(f"   Confidence: {documentation.overall_confidence}")
            print(f"   Requires Review: {documentation.requires_review}")
            
            # Show JSON output
            print("\n📊 JSON OUTPUT:")
            json_output = {
                "recording_id": documentation.recording_id,
                "patient_id": documentation.patient_id,
                "treatment_type": documentation.treatment_type.value if documentation.treatment_type else None,
                "findings": [
                    {
                        "tooth": finding.tooth_number,
                        "surface": finding.surface,
                        "diagnosis": finding.diagnosis
                    }
                    for finding in documentation.findings
                ],
                "billing_codes": [
                    {
                        "code": code.code,
                        "description": code.description,
                        "fee_euros": code.fee_euros
                    }
                    for code in documentation.billing_codes
                ]
            }
            print(json.dumps(json_output, indent=2, ensure_ascii=False))
            
            return True
            
        except Exception as e:
            print(f"❌ Mock transcription test failed: {e}")
            return False
    
    async def test_text_processing_pipeline(self):
        """Test processing with different German dental texts"""
        
        print("\n📝 TESTING TEXT PROCESSING PIPELINE")
        print("=" * 50)
        
        test_cases = [
            {
                "name": "Complex Treatment",
                "text": "Zahn zwei sechs mesial distal Karies profunda, Lokalanästhesie mit Artikain, Exkavation, Kompositfüllung Klasse zwei gelegt, Politur, Kontrolle in zwei Wochen"
            },
            {
                "name": "Emergency Extraction",
                "text": "Notfall Patient, Zahn drei acht akute Pulpitis, starke Schmerzen, Infiltrationsanästhesie, Extraktion wegen Wurzelfraktur, Naht, Schmerzmittel verschrieben"
            },
            {
                "name": "Root Canal Treatment",
                "text": "Zahn eins vier Wurzelkanalbehandlung zweite Sitzung, Leitungsanästhesie, Aufbereitung mit Handinstrumenten, Desinfektion, Calciumhydroxid Einlage, provisorischer Verschluss"
            },
            {
                "name": "Prophylaxis Session",
                "text": "Professionelle Zahnreinigung durchgeführt, Zahnsteinentfernung mit Ultraschall, Politur mit Prophylaxepaste, Fluoridierung, Mundhygieneinstruktionen gegeben"
            }
        ]
        
        results = []
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📋 Test Case {i}: {test_case['name']}")
            print(f"Input: {test_case['text']}")
            print("-" * 40)
            
            try:
                # Create transcription result
                transcription = TranscriptionResult(
                    text=test_case['text'],
                    language="de",
                    confidence=0.95,
                    processing_time_ms=100,
                    stt_model="test-input"
                )
                
                audio_metadata = AudioMetadata(
                    duration_seconds=30.0,
                    sample_rate=16000,
                    format="text",
                    size_bytes=len(test_case['text']),
                    quality_score=1.0
                )
                
                # Process documentation
                documentation = self.doc_processor.process_transcription(
                    transcription=transcription,
                    audio_metadata=audio_metadata,
                    patient_id=f"test_patient_{i}",
                    dentist_id="dr_test"
                )
                
                # Display results
                print("🔍 Results:")
                if documentation.treatment_type:
                    print(f"   Treatment: {documentation.treatment_type.value}")
                
                if documentation.findings:
                    print(f"   Findings ({len(documentation.findings)}):")
                    for finding in documentation.findings:
                        tooth_info = f"Zahn {finding.tooth_number}" if finding.tooth_number else "General"
                        surface_info = f" {finding.surface}" if finding.surface else ""
                        print(f"     • {tooth_info}{surface_info}: {finding.diagnosis}")
                
                if documentation.procedures_performed:
                    print(f"   Procedures ({len(documentation.procedures_performed)}):")
                    for procedure in documentation.procedures_performed:
                        print(f"     • {procedure}")
                
                if documentation.billing_codes:
                    total_fee = sum(code.fee_euros for code in documentation.billing_codes if code.fee_euros)
                    print(f"   Billing ({len(documentation.billing_codes)} codes, €{total_fee:.2f}):")
                    for code in documentation.billing_codes:
                        fee_info = f" (€{code.fee_euros})" if code.fee_euros else ""
                        print(f"     • {code.code}: {code.description}{fee_info}")
                
                print(f"   Confidence: {documentation.overall_confidence}")
                print(f"   Review Required: {'Yes' if documentation.requires_review else 'No'}")
                
                results.append({
                    "case": test_case['name'],
                    "success": True,
                    "findings_count": len(documentation.findings),
                    "procedures_count": len(documentation.procedures_performed),
                    "billing_codes_count": len(documentation.billing_codes),
                    "total_fee": sum(code.fee_euros for code in documentation.billing_codes if code.fee_euros)
                })
                
            except Exception as e:
                print(f"❌ Processing failed: {e}")
                results.append({
                    "case": test_case['name'],
                    "success": False,
                    "error": str(e)
                })
        
        # Summary
        print("\n📊 TEST SUMMARY")
        print("=" * 30)
        successful = sum(1 for r in results if r['success'])
        print(f"Successful tests: {successful}/{len(results)}")
        
        for result in results:
            if result['success']:
                print(f"✅ {result['case']}: {result['findings_count']} findings, "
                      f"{result['billing_codes_count']} codes, €{result['total_fee']:.2f}")
            else:
                print(f"❌ {result['case']}: {result['error']}")
        
        return successful == len(results)
    
    async def test_audio_validation(self):
        """Test audio file validation"""
        
        print("\n🔍 TESTING AUDIO VALIDATION")
        print("=" * 30)
        
        try:
            # Test valid WAV file
            print("📁 Testing valid WAV file...")
            test_audio = create_test_audio_file()
            metadata = self.audio_processor.validate_audio(test_audio, "test.wav")
            
            print(f"✅ WAV validation successful:")
            print(f"   Duration: {metadata.duration_seconds:.2f}s")
            print(f"   Sample Rate: {metadata.sample_rate}Hz")
            print(f"   Format: {metadata.format}")
            print(f"   Quality Score: {metadata.quality_score:.2f}")
            
            # Test invalid format
            print("\n📁 Testing invalid format...")
            try:
                self.audio_processor.validate_audio(b"invalid data", "test.xyz")
                print("❌ Should have failed validation")
                return False
            except Exception as e:
                print(f"✅ Correctly rejected invalid format: {e}")
            
            # Test file too small
            print("\n📁 Testing file too small...")
            try:
                self.audio_processor.validate_audio(b"tiny", "test.wav")
                print("❌ Should have failed validation")
                return False
            except Exception as e:
                print(f"✅ Correctly rejected small file: {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ Audio validation test failed: {e}")
            return False
    
    async def test_service_availability(self):
        """Test which transcription services are available"""
        
        print("\n🔧 TESTING SERVICE AVAILABILITY")
        print("=" * 35)
        
        # Check OpenAI service
        if self.audio_service.openai_service:
            print("✅ OpenAI Whisper API: Available")
            print(f"   Model: {self.audio_service.openai_service.model}")
        else:
            print("❌ OpenAI Whisper API: Not configured (no API key)")
        
        # Check local Whisper
        try:
            import whisper
            print("✅ Local Whisper: Available")
            print(f"   Model size: {self.audio_service.local_service.model_size}")
        except ImportError:
            print("❌ Local Whisper: Not installed")
        
        # Check mock service
        print("✅ Mock Service: Available (for testing)")
        
        # Check supported formats
        formats = self.audio_service.get_supported_formats()
        max_size = self.audio_service.get_max_file_size() // (1024 * 1024)
        print(f"\n📋 Supported formats: {', '.join(formats)}")
        print(f"📏 Max file size: {max_size}MB")
        
        return True
    
    def run_manual_openai_test(self):
        """Manual test for OpenAI integration (requires API key)"""
        
        print("\n🔑 MANUAL OPENAI TEST")
        print("=" * 25)
        print("To test OpenAI Whisper integration:")
        print("1. Add your OpenAI API key to .env file:")
        print("   OPENAI_API_KEY=your_api_key_here")
        print("2. Create a test audio file with German dental speech")
        print("3. Use the FastAPI interface at /docs to upload the file")
        print("4. Set use_mock=False to use real OpenAI transcription")
        print("\nExample curl command:")
        print("curl -X POST 'http://localhost:8000/api/v1/documentation/process-audio' \\")
        print("  -F 'audio_file=@test_recording.wav' \\")
        print("  -F 'dentist_id=dr_test' \\")
        print("  -F 'use_mock=false'")


async def run_all_tests():
    """Run all audio integration tests"""
    
    print("🦷 MedVox Audio Integration Test Suite")
    print("=" * 50)
    
    tester = AudioIntegrationTester()
    
    # Run tests
    tests = [
        ("Service Availability", tester.test_service_availability),
        ("Audio Validation", tester.test_audio_validation),
        ("Mock Transcription Pipeline", tester.test_mock_transcription_pipeline),
        ("Text Processing Pipeline", tester.test_text_processing_pipeline),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            success = await test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append((test_name, False))
    
    # Final summary
    print("\n" + "=" * 50)
    print("🎯 FINAL TEST RESULTS")
    print("=" * 50)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Audio integration is working correctly.")
        
        print("\n🚀 NEXT STEPS:")
        print("1. Set up OpenAI API key for real transcription")
        print("2. Test with real audio recordings")
        print("3. Start the FastAPI server: uvicorn app.main:app --reload")
        print("4. Open browser to http://localhost:8000/docs")
        print("5. Test audio upload via the web interface")
        
    else:
        print("⚠️  Some tests failed. Check the errors above.")
    
    # Show manual OpenAI test info
    tester.run_manual_openai_test()


if __name__ == "__main__":
    asyncio.run(run_all_tests()) 