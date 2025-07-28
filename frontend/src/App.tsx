import React, { useState, useRef } from 'react';
import { Mic, MicOff, Loader2, User, FileText, Settings } from 'lucide-react';
import { BillingCodesDisplay } from './components/BillingCodesDisplay';
import { DocumentationResponse, SelectedBillingCode, RecordingState, PatientFormData } from './types';

function App() {
  const [recordingState, setRecordingState] = useState<RecordingState>({
    isRecording: false,
    isProcessing: false,
    duration: 0
  });
  
  const [documentation, setDocumentation] = useState<DocumentationResponse | null>(null);
  const [patientData, setPatientData] = useState<PatientFormData>({
    patientId: '12314',
    dentistName: 'Dr. Martin Hartmann',
    insuranceType: 'BEMA'
  });
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const durationIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true
        }
      });
      
      // Try to use WAV format if supported, fallback to WebM
      const mimeType = MediaRecorder.isTypeSupported('audio/wav') 
        ? 'audio/wav'
        : MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm';
      
      console.log('🎤 Using audio format:', mimeType);
      
      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        console.log('🎵 Audio blob created:', audioBlob.size, 'bytes, type:', audioBlob.type);
        await processAudio(audioBlob);
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setRecordingState(prev => ({ ...prev, isRecording: true, duration: 0 }));
      
      durationIntervalRef.current = setInterval(() => {
        setRecordingState(prev => ({ ...prev, duration: prev.duration + 1 }));
      }, 1000);
    } catch (error) {
      console.error('Error starting recording:', error);
      alert('Fehler beim Zugriff auf das Mikrofon');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && recordingState.isRecording) {
      mediaRecorderRef.current.stop();
      setRecordingState(prev => ({ ...prev, isRecording: false }));
      
      if (durationIntervalRef.current) {
        clearInterval(durationIntervalRef.current);
      }
    }
  };

  const processAudio = async (audioBlob: Blob) => {
    setRecordingState(prev => ({ ...prev, isProcessing: true }));
    
    try {
      const formData = new FormData();
      
      // Determine file extension based on blob type
      const fileExtension = audioBlob.type.includes('wav') ? '.wav' 
        : audioBlob.type.includes('webm') ? '.webm'
        : audioBlob.type.includes('mp4') ? '.mp4'
        : '.webm';
      
      console.log('📤 Uploading audio:', audioBlob.type, fileExtension);
      
      formData.append('audio_file', audioBlob, `recording${fileExtension}`);
      formData.append('patient_id', patientData.patientId);
      formData.append('dentist_id', patientData.dentistName);
      formData.append('insurance_type', patientData.insuranceType);

      const response = await fetch('/api/v1/documentation/process-audio', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('📨 API Response:', result);
      
      // Extract documentation from the response structure
      const documentation = result.success ? result.documentation : null;
      setDocumentation(documentation);
    } catch (error) {
      console.error('Error processing audio:', error);
      alert('Fehler bei der Verarbeitung der Aufnahme');
    } finally {
      setRecordingState(prev => ({ ...prev, isProcessing: false }));
    }
  };

  const handleExport = (selectedCodes: SelectedBillingCode[]) => {
    const exportData = {
      patient: patientData,
      selected_codes: selectedCodes,
      export_date: new Date().toISOString(),
      total_codes: selectedCodes.length
    };
    
    const dataStr = JSON.stringify(exportData, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `medvox-export-${patientData.patientId}-${new Date().toISOString().split('T')[0]}.json`;
    link.click();
    
    URL.revokeObjectURL(url);
  };

  const handleAddManual = () => {
    // This would open a modal for manual code entry
    alert('Manual code addition coming soon!');
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              🦷 MedVox
            </h1>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 text-sm">
                <div className="flex items-center gap-1">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span>Mikrofon bereit</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span>API verbunden</span>
                </div>
              </div>
              <button className="btn-secondary">
                <Settings className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* Patient Info */}
        <div className="card">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Patient ID
              </label>
              <input
                type="text"
                value={patientData.patientId}
                onChange={(e) => setPatientData(prev => ({ ...prev, patientId: e.target.value }))}
                className="input-field"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Zahnarzt
              </label>
              <input
                type="text"
                value={patientData.dentistName}
                onChange={(e) => setPatientData(prev => ({ ...prev, dentistName: e.target.value }))}
                className="input-field"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Abrechnung
              </label>
              <div className="flex border border-gray-300 rounded-lg overflow-hidden">
                <button
                  onClick={() => setPatientData(prev => ({ ...prev, insuranceType: 'BEMA' }))}
                  className={`flex-1 px-4 py-2 text-sm font-medium ${
                    patientData.insuranceType === 'BEMA'
                      ? 'bg-dental-primary text-white'
                      : 'bg-white text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  BEMA
                </button>
                <button
                  onClick={() => setPatientData(prev => ({ ...prev, insuranceType: 'GOZ' }))}
                  className={`flex-1 px-4 py-2 text-sm font-medium ${
                    patientData.insuranceType === 'GOZ'
                      ? 'bg-dental-primary text-white'
                      : 'bg-white text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  GOZ
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Recording Section */}
        <div className="card text-center">
          <div className="space-y-4">
            {!recordingState.isRecording && !recordingState.isProcessing && (
              <button
                onClick={startRecording}
                className="btn-primary mx-auto flex items-center gap-3 text-lg px-8 py-4"
              >
                <Mic className="h-6 w-6" />
                Aufnahme starten
              </button>
            )}

            {recordingState.isRecording && (
              <div className="space-y-4">
                <div className="flex items-center justify-center gap-3">
                  <div className="w-4 h-4 bg-red-500 rounded-full recording-pulse"></div>
                  <span className="text-lg font-medium">Aufnahme läuft...</span>
                </div>
                <div className="text-2xl font-mono text-dental-primary">
                  {formatDuration(recordingState.duration)}
                </div>
                <button
                  onClick={stopRecording}
                  className="btn-secondary mx-auto flex items-center gap-3"
                >
                  <MicOff className="h-5 w-5" />
                  Aufnahme beenden
                </button>
                
                {/* Debug: Test Button */}
                <button
                  onClick={() => {
                    setDocumentation({
                      transcription: "TEST: Patient kommt, Füllung 3-6 MOD, Zahnfilm, BMF.",
                      confidence: 0.95,
                      language: "DE"
                    });
                  }}
                  className="btn-secondary mx-auto flex items-center gap-2 text-sm"
                >
                  🧪 Test Transcription
                </button>
              </div>
            )}

            {recordingState.isProcessing && (
              <div className="space-y-4">
                <Loader2 className="h-8 w-8 animate-spin mx-auto text-dental-primary" />
                <p className="text-lg font-medium">Verarbeitung läuft...</p>
                <p className="text-sm text-gray-600">
                  Transkription und BEMA/GOZ-Analyse
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Documentation Results */}
        {documentation && (
          <>
            {/* Debug: Raw API Response */}
            <div className="card border-2 border-blue-200 bg-blue-50">
              <h2 className="text-xl font-semibold mb-4 text-blue-800">🔍 DEBUG: API Response</h2>
              <pre className="bg-white p-4 rounded border text-xs overflow-auto max-h-40">
                {JSON.stringify(documentation, null, 2)}
              </pre>
            </div>

            {/* Transcription */}
            <div className="card">
              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Transkription
              </h2>
              {(() => {
                const transcription = documentation.transcription;
                const transcriptionText = typeof transcription === 'string' ? transcription : transcription?.text;
                const confidence = typeof transcription === 'object' ? transcription?.confidence : documentation.confidence;
                const language = typeof transcription === 'object' ? transcription?.language : documentation.language;
                
                return transcriptionText ? (
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <p className="text-gray-900 text-lg">{transcriptionText}</p>
                    {confidence && (
                      <div className="mt-2 text-xs text-gray-600">
                        Vertrauen: {Math.round(confidence * 100)}% • Sprache: {language || 'DE'}
                      </div>
                    )}
                  </div>
                                ) : (
                  <div className="bg-red-50 p-4 rounded-lg border border-red-200">
                    <p className="text-red-800">❌ Keine Transkription erhalten!</p>
                  </div>
                );
              })()}
            </div>

            {/* Procedures and Billing Codes */}
            <BillingCodesDisplay
              procedures={documentation.procedures || []}
              billingCodes={documentation.billing_codes || []}
              onExport={handleExport}
              onAddManual={handleAddManual}
            />

            {/* Clinical Notes */}
            {(documentation.findings || documentation.patient?.befunde) && (
              <div className="card">
                <h2 className="text-xl font-semibold mb-4">📝 Klinische Notizen</h2>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <p>{documentation.findings || documentation.patient?.befunde}</p>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default App; 