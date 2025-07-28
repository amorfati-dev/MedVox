#!/bin/bash

# Test the API response structure
echo "Testing MedVox API response..."

# Create a simple test audio file using text-to-speech
echo "Creating test audio..."
say -o test_audio.m4a "Dreiflächige Füllung, 36 MOD, Zahnfilm, Zahnflaschebehandlung mit Medikament Chlorhexamid."

# Send to API
echo "Sending to API..."
curl -X POST http://localhost:8000/api/v1/documentation/process-audio \
  -F "audio_file=@test_audio.m4a" \
  -F "patient_id=TEST123" \
  -F "dentist_id=ZA001" \
  -F "insurance_type=BEMA" \
  -F "use_mock=false" \
  -H "X-Model-Version: gemini-2.5-pro" \
  | python -m json.tool > api_response.json

echo "Response saved to api_response.json"
echo "Raw Gemini Response:"
cat api_response.json | python -c "import json, sys; data = json.load(sys.stdin); print(data.get('documentation', {}).get('raw_gemini_response', 'NOT FOUND')[:500] + '...' if data.get('documentation', {}).get('raw_gemini_response') else 'NOT FOUND')"

# Clean up
rm -f test_audio.m4a 