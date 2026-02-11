import React, { useState, useRef, useCallback } from 'react';
import { Mic, MicOff, Loader2, FileText, Settings, Copy, Check, Activity } from 'lucide-react';
import { BillingCodesDisplay } from './components/BillingCodesDisplay';
import { SettingsPanel, loadSettings, saveSettings } from './components/SettingsPanel';
import { DocumentationResponse, SelectedBillingCode, RecordingState, PatientFormData, AppSettings } from './types';

function App() {
  const [appSettings, setAppSettings] = useState<AppSettings>(loadSettings);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [transcriptionCopied, setTranscriptionCopied] = useState(false);

  const [recordingState, setRecordingState] = useState<RecordingState>({
    isRecording: false,
    isProcessing: false,
    duration: 0,
  });

  const [documentation, setDocumentation] = useState<DocumentationResponse | null>(null);
  const [patientData, setPatientData] = useState<PatientFormData>({
    patientId: '',
    dentistName: appSettings.dentistName,
    insuranceType: appSettings.defaultInsuranceType,
  });

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const durationIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 44100,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      const mimeType = MediaRecorder.isTypeSupported('audio/wav')
        ? 'audio/wav'
        : MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm';

      console.log('🎤 Using audio format:', mimeType);

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType,
        audioBitsPerSecond: 64000,
      });
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        console.log('🎵 Audio blob created:', audioBlob.size, 'bytes, type:', audioBlob.type);
        await processAudio(audioBlob);
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.start();
      setRecordingState((prev) => ({ ...prev, isRecording: true, duration: 0 }));

      durationIntervalRef.current = setInterval(() => {
        setRecordingState((prev) => {
          const newDuration = prev.duration + 1;
          if (newDuration >= appSettings.autoStopDuration) {
            stopRecording();
            return prev;
          }
          return { ...prev, duration: newDuration };
        });
      }, 1000);
    } catch (error) {
      console.error('Error starting recording:', error);
      alert('Fehler beim Zugriff auf das Mikrofon');
    }
  };

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      setRecordingState((prev) => ({ ...prev, isRecording: false }));

      if (durationIntervalRef.current) {
        clearInterval(durationIntervalRef.current);
      }
    }
  }, []);

  const processAudio = async (audioBlob: Blob) => {
    setRecordingState((prev) => ({ ...prev, isProcessing: true }));

    try {
      const formData = new FormData();

      const fileExtension = audioBlob.type.includes('wav')
        ? '.wav'
        : audioBlob.type.includes('webm')
        ? '.webm'
        : audioBlob.type.includes('mp4')
        ? '.mp4'
        : '.webm';

      console.log('📤 Uploading audio:', audioBlob.type, fileExtension);

      formData.append('audio_file', audioBlob, `recording${fileExtension}`);
      formData.append('patient_id', patientData.patientId);
      formData.append('dentist_id', patientData.dentistName);
      formData.append('insurance_type', patientData.insuranceType);

      const response = await fetch(`${appSettings.apiEndpoint}/documentation/process-audio`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('📨 API Response:', result);

      const doc = result.success ? result.documentation : null;
      setDocumentation(doc);
    } catch (error) {
      console.error('Error processing audio:', error);
      alert('Fehler bei der Verarbeitung der Aufnahme');
    } finally {
      setRecordingState((prev) => ({ ...prev, isProcessing: false }));
    }
  };

  const handleExport = (selectedCodes: SelectedBillingCode[]) => {
    const exportData = {
      patient: patientData,
      selected_codes: selectedCodes,
      export_date: new Date().toISOString(),
      total_codes: selectedCodes.length,
    };

    const dataStr = JSON.stringify(exportData, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });

    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `medvox-export-${patientData.patientId || 'patient'}-${new Date().toISOString().split('T')[0]}.json`;
    link.click();

    URL.revokeObjectURL(url);
  };

  const handleAddManual = () => {
    alert('Manuelle Eingabe kommt bald!');
  };

  const handleSettingsSave = (newSettings: AppSettings) => {
    setAppSettings(newSettings);
    saveSettings(newSettings);
    // Update patient data with new defaults
    setPatientData((prev) => ({
      ...prev,
      dentistName: newSettings.dentistName,
    }));
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  /** Get the plain text from the transcription response */
  const getTranscriptionText = (): string => {
    if (!documentation) return '';
    const t = documentation.transcription;
    if (typeof t === 'string') return t;
    return t?.text || '';
  };

  const copyTranscription = async () => {
    const text = getTranscriptionText();
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setTranscriptionCopied(true);
      setTimeout(() => setTranscriptionCopied(false), 2000);
    } catch {
      // fallback
    }
  };

  const transcriptionText = getTranscriptionText();
  const transcriptionConfidence =
    typeof documentation?.transcription === 'object'
      ? documentation.transcription?.confidence
      : documentation?.confidence;
  const transcriptionLanguage =
    typeof documentation?.transcription === 'object'
      ? documentation.transcription?.language
      : documentation?.language;

  const progressPercent = (recordingState.duration / appSettings.autoStopDuration) * 100;

  return (
    <div className="min-h-screen bg-dental-surface">
      {/* Header */}
      <header className="bg-white border-b border-gray-100 sticky top-0 z-30">
        <div className="max-w-4xl mx-auto px-4 sm:px-6">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center">
              <img src="/logo.png" alt="MedVox" className="h-12" />
            </div>

            <div className="flex items-center gap-3">
              <div className="hidden sm:flex items-center gap-1.5 text-xs text-gray-400">
                <Activity className="h-3 w-3 text-dental-success" />
                <span>Bereit</span>
              </div>
              <button
                onClick={() => setSettingsOpen(true)}
                className="btn-icon"
                title="Einstellungen"
              >
                <Settings className="h-4.5 w-4.5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-6 space-y-5">
        {/* Patient Bar */}
        <div className="card !p-4">
          <div className="flex flex-col sm:flex-row sm:items-center gap-3">
            <div className="flex-1">
              <input
                type="text"
                value={patientData.patientId}
                onChange={(e) => setPatientData((prev) => ({ ...prev, patientId: e.target.value }))}
                className="input-field"
                placeholder="Patient-ID eingeben..."
              />
            </div>

            {/* Insurance Toggle Pill */}
            <div className="flex rounded-xl bg-dental-surface border border-gray-200 p-0.5 shrink-0">
              <button
                onClick={() => setPatientData((prev) => ({ ...prev, insuranceType: 'BEMA' }))}
                className={`px-5 py-2 rounded-[10px] text-sm font-medium transition-all duration-200 ${
                  patientData.insuranceType === 'BEMA'
                    ? 'bg-dental-bema text-white shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                BEMA
              </button>
              <button
                onClick={() => setPatientData((prev) => ({ ...prev, insuranceType: 'GOZ' }))}
                className={`px-5 py-2 rounded-[10px] text-sm font-medium transition-all duration-200 ${
                  patientData.insuranceType === 'GOZ'
                    ? 'bg-dental-goz text-white shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                GOZ
              </button>
            </div>
          </div>
        </div>

        {/* Recording Section */}
        <div className="card text-center">
          {!recordingState.isRecording && !recordingState.isProcessing && (
            <div className="py-4">
              <button
                onClick={startRecording}
                className="group relative inline-flex items-center justify-center"
              >
                {/* Outer ring */}
                <span className="absolute w-24 h-24 rounded-full bg-dental-primary/10 group-hover:bg-dental-primary/15 transition-colors duration-300" />
                {/* Inner button */}
                <span className="relative w-16 h-16 rounded-full bg-gradient-to-br from-dental-primary to-dental-primary-dark flex items-center justify-center shadow-lg group-hover:shadow-xl transition-all duration-200 group-active:scale-95">
                  <Mic className="h-7 w-7 text-white" />
                </span>
              </button>
              <p className="mt-4 text-sm text-gray-500">Aufnahme starten</p>
            </div>
          )}

          {recordingState.isRecording && (
            <div className="py-4 space-y-5 animate-fade-in">
              {/* Animated recording button */}
              <button
                onClick={stopRecording}
                className="group relative inline-flex items-center justify-center"
              >
                <span className="absolute w-24 h-24 rounded-full bg-red-100 animate-pulse-ring" />
                <span className="relative w-16 h-16 rounded-full bg-gradient-to-br from-red-500 to-red-600 flex items-center justify-center shadow-lg group-active:scale-95 transition-transform">
                  <MicOff className="h-7 w-7 text-white" />
                </span>
              </button>

              {/* Timer */}
              <div>
                <div className="text-3xl font-mono font-light text-gray-900 tracking-widest">
                  {formatDuration(recordingState.duration)}
                </div>
                <p className="text-xs text-gray-400 mt-1">
                  Aufnahme läuft &middot; max {appSettings.autoStopDuration}s
                </p>
              </div>

              {/* Progress bar */}
              <div className="max-w-xs mx-auto">
                <div className="h-1 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-red-400 rounded-full transition-all duration-1000 ease-linear"
                    style={{ width: `${Math.min(progressPercent, 100)}%` }}
                  />
                </div>
              </div>
            </div>
          )}

          {recordingState.isProcessing && (
            <div className="py-8 space-y-4 animate-fade-in">
              <Loader2 className="h-10 w-10 animate-spin mx-auto text-dental-primary" />
              <div>
                <p className="text-base font-medium text-gray-900">Verarbeitung läuft...</p>
                <p className="text-sm text-gray-400 mt-1">
                  Transkription und {patientData.insuranceType}-Analyse
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Results */}
        {documentation && (
          <div className="space-y-5 animate-slide-up">
            {/* Transcription */}
            <div className="card">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                  <FileText className="h-4.5 w-4.5 text-gray-400" />
                  Transkription
                </h2>
                {transcriptionText && (
                  <button
                    onClick={copyTranscription}
                    className="btn-ghost flex items-center gap-1.5 text-sm"
                  >
                    {transcriptionCopied ? (
                      <>
                        <Check className="h-3.5 w-3.5 text-dental-success" />
                        <span className="text-dental-success">Kopiert!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="h-3.5 w-3.5" />
                        Kopieren
                      </>
                    )}
                  </button>
                )}
              </div>

              {transcriptionText ? (
                <div className="bg-dental-surface rounded-xl p-4 border border-gray-100">
                  <p className="text-gray-800 leading-relaxed">{transcriptionText}</p>
                  {transcriptionConfidence != null && transcriptionConfidence > 0 && (
                    <div className="mt-3 flex items-center gap-3 text-xs text-gray-400">
                      <span>
                        Vertrauen: {Math.round(transcriptionConfidence * 100)}%
                      </span>
                      <span>&middot;</span>
                      <span>Sprache: {transcriptionLanguage || 'DE'}</span>
                    </div>
                  )}
                </div>
              ) : (
                <div className="bg-amber-50 rounded-xl p-4 border border-amber-200">
                  <p className="text-amber-800 text-sm font-medium">Keine Transkription erkannt</p>
                  <p className="text-amber-600 text-xs mt-1">
                    Die Spracherkennung konnte keinen Text erkennen. Bitte sprechen Sie deutlich und nah am Mikrofon.
                    Stellen Sie sicher, dass die Aufnahme mindestens 2-3 Sekunden lang ist.
                  </p>
                </div>
              )}
            </div>

            {/* Billing Codes - only show if transcription was successful */}
            {transcriptionText && (
              <BillingCodesDisplay
                procedures={documentation.procedures || []}
                billingCodes={documentation.billing_codes || []}
                onExport={handleExport}
                onAddManual={handleAddManual}
              />
            )}

            {/* Clinical Notes */}
            {(documentation.findings || documentation.patient?.befunde) && (
              <div className="card">
                <h2 className="text-lg font-semibold text-gray-900 mb-3">Klinische Notizen</h2>
                <div className="bg-dental-surface rounded-xl p-4 border border-gray-100">
                  <p className="text-gray-800 text-sm leading-relaxed">
                    {documentation.findings ||
                      (documentation.patient?.befunde &&
                        (Array.isArray(documentation.patient.befunde)
                          ? documentation.patient.befunde.join(', ')
                          : documentation.patient.befunde))}
                  </p>
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Settings Panel */}
      <SettingsPanel
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        settings={appSettings}
        onSave={handleSettingsSave}
      />
    </div>
  );
}

export default App;
