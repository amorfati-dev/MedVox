import React, { useState, useRef, useCallback } from 'react';
import { Mic, MicOff, Loader2, FileText, Settings, Copy, Check, Activity, Hash, Clock } from 'lucide-react';
import { BillingCodesDisplay } from './components/BillingCodesDisplay';
import { SettingsPanel, loadSettings, saveSettings } from './components/SettingsPanel';
import { ShortCodeModal } from './components/ShortCodeModal';
import { SessionPanel } from './components/SessionPanel';
import { DocumentationResponse, SelectedBillingCode, RecordingState, PatientFormData, AppSettings, TransferSession, ProcessingMode, RecordingSession, SessionState, AudioSegment } from './types';

function App() {
  const [appSettings, setAppSettings] = useState<AppSettings>(() => {
    const loaded = loadSettings();
    return loaded;
  });
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [sessionPanelOpen, setSessionPanelOpen] = useState(false);
  const [transcriptionCopied, setTranscriptionCopied] = useState(false);
  const [codeModalOpen, setCodeModalOpen] = useState(false);
  const [transferSession, setTransferSession] = useState<TransferSession | null>(null);
  const [processingMode, setProcessingMode] = useState<ProcessingMode>(appSettings.defaultProcessingMode);

  const [recordingState, setRecordingState] = useState<RecordingState>({
    isRecording: false,
    isProcessing: false,
    duration: 0,
  });

  // Session-based recording state (ALWAYS session mode now)
  const [session, setSession] = useState<RecordingSession | null>(null);
  const [sessionState, setSessionState] = useState<SessionState>('idle');

  const [documentation, setDocumentation] = useState<DocumentationResponse | null>(null);

  const getCurrentDentist = () => {
    return appSettings.dentists.find(d => d.id === appSettings.currentDentistId) || appSettings.dentists[0];
  };

  const [patientData, setPatientData] = useState<PatientFormData>({
    patientId: '',
    dentistName: getCurrentDentist()?.name || 'Unknown',
    insuranceType: appSettings.defaultInsuranceType,
  });
  const [selectedDentistId, setSelectedDentistId] = useState<string>(() => {
    const currentDentist = getCurrentDentist();
    return currentDentist?.id || 'dentist-1';
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
        const duration = recordingState.duration;

        stream.getTracks().forEach((track) => track.stop());

        // ALWAYS session mode: Add segment and quick transcribe
        {
          // Add segment to session
          setRecordingState((prev) => ({ ...prev, isProcessing: true }));

          const transcription = await quickTranscribe(audioBlob);

          const segment: AudioSegment = {
            blob: audioBlob,
            duration,
            transcription,
            timestamp: new Date(),
          };

          setSession((prev) => {
            if (!prev) {
              // First segment - create new session
              return {
                segments: [segment],
                isActive: true,
                accumulatedTranscription: transcription,
                patientId: patientData.patientId,
                dentistName: patientData.dentistName,
                insuranceType: patientData.insuranceType,
              };
            }

            // Add to existing session
            return {
              ...prev,
              segments: [...prev.segments, segment],
              accumulatedTranscription: prev.accumulatedTranscription + ' ' + transcription,
            };
          });

          setSessionState('paused');
          setRecordingState((prev) => ({ ...prev, isProcessing: false }));
        }
      };

      mediaRecorder.start();
      setRecordingState((prev) => ({ ...prev, isRecording: true, duration: 0 }));

      // Set session state to recording if session is active
      if (session || sessionState === 'paused') {
        setSessionState('recording');
      }

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

  // Session Management Functions
  const handlePause = useCallback(async () => {
    // Stop the current recording
    stopRecording();

    // The audioBlob will be handled in mediaRecorder.onstop
    // We'll add it to the session there
  }, [stopRecording]);

  const handleResume = useCallback(async () => {
    // Start a new recording segment
    setSessionState('recording');
    await startRecording();
  }, []);

  const handleFinalize = useCallback(async () => {
    if (!session || session.segments.length === 0) return;

    setSessionState('processing');

    try {
      // Merge all audio blobs
      const mergedBlob = await mergeAudioBlobs(session.segments.map(s => s.blob));

      // Process the merged audio
      await processAudioWithSession(mergedBlob, session);

      // Clear session
      setSession(null);
      setSessionState('idle');
    } catch (error) {
      console.error('Error finalizing session:', error);
      alert('Fehler beim Abschließen der Session');
      setSessionState('paused');
    }
  }, [session]);

  const handleDiscard = useCallback(() => {
    if (confirm('Möchten Sie die aktuelle Session wirklich verwerfen?')) {
      setSession(null);
      setSessionState('idle');
      setDocumentation(null);
    }
  }, []);

  // Helper: Merge audio blobs
  const mergeAudioBlobs = async (blobs: Blob[]): Promise<Blob> => {
    // Simple concatenation for WebM - works for most cases
    return new Blob(blobs, { type: blobs[0]?.type || 'audio/webm' });
  };

  // Quick transcription (STT only, no LLM)
  const quickTranscribe = async (audioBlob: Blob): Promise<string> => {
    try {
      const formData = new FormData();
      const fileExtension = audioBlob.type.includes('wav') ? '.wav' : '.webm';
      formData.append('audio_file', audioBlob, `segment${fileExtension}`);
      formData.append('processing_mode', 'transcription_only');

      const response = await fetch(`${appSettings.apiEndpoint}/documentation/process-audio`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) return '[Transkription fehlgeschlagen]';

      const result = await response.json();
      const transcription = result.documentation?.transcription;

      if (typeof transcription === 'string') return transcription;
      if (transcription?.text) return transcription.text;

      return '[Keine Transkription]';
    } catch (error) {
      console.error('Quick transcription error:', error);
      return '[Fehler]';
    }
  };

  // Process audio with session context
  const processAudioWithSession = async (audioBlob: Blob, sessionData: RecordingSession) => {
    setRecordingState((prev) => ({ ...prev, isProcessing: true }));

    try {
      const formData = new FormData();
      const fileExtension = audioBlob.type.includes('wav') ? '.wav' : '.webm';

      formData.append('audio_file', audioBlob, `recording${fileExtension}`);
      formData.append('patient_id', sessionData.patientId);
      formData.append('dentist_id', sessionData.dentistName);
      formData.append('insurance_type', sessionData.insuranceType);
      formData.append('processing_mode', processingMode);

      const response = await fetch(`${appSettings.apiEndpoint}/documentation/process-audio`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();

      const doc = result.success ? result.documentation : null;
      setDocumentation(doc);

      // Invalidate sessions cache
      if (doc) {
        const currentDentist = getCurrentDentist();
        if (currentDentist) {
          const cacheKey = `medvox-sessions-cache-${currentDentist.name}`;
          localStorage.removeItem(cacheKey);
        }
      }
    } catch (error) {
      console.error('Error processing audio:', error);
      alert('Fehler bei der Verarbeitung der Aufnahme');
    } finally {
      setRecordingState((prev) => ({ ...prev, isProcessing: false }));
    }
  };

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


      formData.append('audio_file', audioBlob, `recording${fileExtension}`);
      formData.append('patient_id', patientData.patientId);
      formData.append('dentist_id', patientData.dentistName);
      formData.append('insurance_type', patientData.insuranceType);
      formData.append('processing_mode', processingMode);

      const response = await fetch(`${appSettings.apiEndpoint}/documentation/process-audio`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();

      const doc = result.success ? result.documentation : null;
      setDocumentation(doc);

      // Invalidate sessions cache so SessionPanel shows new recording
      if (doc) {
        const currentDentist = getCurrentDentist();
        if (currentDentist) {
          const cacheKey = `medvox-sessions-cache-${currentDentist.name}`;
          localStorage.removeItem(cacheKey);
        }
      }
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

  const createTransferSession = async () => {
    if (!documentation) return;

    try {
      // Extract billing codes from documentation
      const billingCodes = documentation.billing_codes || documentation.abrechnungspositionen || [];
      const transcription = getTranscriptionText();

      if (billingCodes.length === 0) {
        alert('Keine Abrechnungscodes zum Übertragen vorhanden');
        return;
      }

      // Create transfer session
      const response = await fetch(`${appSettings.apiEndpoint}/transfer/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          billing_codes: billingCodes,
          transcription: transcription,
          patient_id: patientData.patientId || undefined,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const session: TransferSession = await response.json();

      setTransferSession(session);
      setCodeModalOpen(true);
    } catch (error) {
      console.error('Error creating transfer session:', error);
      alert('Fehler beim Erstellen der Übertragung');
    }
  };

  const handleSettingsSave = (newSettings: AppSettings) => {
    setAppSettings(newSettings);
    saveSettings(newSettings);

    // Update patient data with new defaults
    const currentDentist = newSettings.dentists.find(d => d.id === newSettings.currentDentistId) || newSettings.dentists[0];

    if (currentDentist) {
      setSelectedDentistId(currentDentist.id);
      setPatientData((prev) => ({
        ...prev,
        dentistName: currentDentist.name,
      }));
    }
  };

  const handleDentistChange = (dentistId: string) => {
    setSelectedDentistId(dentistId);
    const dentist = appSettings.dentists.find(d => d.id === dentistId);
    if (dentist) {
      setPatientData((prev) => ({
        ...prev,
        dentistName: dentist.name,
      }));

      // Update currentDentistId in settings and save
      const updatedSettings = {
        ...appSettings,
        currentDentistId: dentistId,
      };
      setAppSettings(updatedSettings);
      saveSettings(updatedSettings);
    }
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

  const handleLoadSession = async (sessionId: number) => {
    try {
      const response = await fetch(`${appSettings.apiEndpoint}/documentation/sessions/${sessionId}`);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();

      if (result.success && result.documentation) {

        setDocumentation(result.documentation);

        // Set patient ID if available
        if (result.documentation.patient_id) {
          setPatientData((prev) => ({
            ...prev,
            patientId: result.documentation.patient_id
          }));
        }

        setSessionPanelOpen(false);
      } else {
        console.error('❌ Session load failed:', result);
        alert('Fehler: Session konnte nicht geladen werden');
      }
    } catch (error) {
      console.error('❌ Error loading session:', error);
      alert('Fehler beim Laden der Behandlung: ' + error);
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
                onClick={() => setSessionPanelOpen(true)}
                className="btn-icon"
                title="Behandlungen"
              >
                <Clock className="h-4.5 w-4.5" />
              </button>
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

            {/* Dentist Dropdown - always show if dentists configured */}
            {appSettings.dentists.length > 0 && (
              <div className="sm:w-56">
                <select
                  value={selectedDentistId}
                  onChange={(e) => handleDentistChange(e.target.value)}
                  className="input-field text-sm"
                >
                  {appSettings.dentists.map((dentist) => (
                    <option key={dentist.id} value={dentist.id}>
                      {dentist.name}
                    </option>
                  ))}
                </select>
              </div>
            )}

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
          {/* IDLE STATE: Start Button */}
          {sessionState === 'idle' && !recordingState.isRecording && !recordingState.isProcessing && (
            <div className="py-4">
              {/* Processing Mode Toggle */}
              <div className="flex justify-center mb-6">
                <div className="flex rounded-xl bg-dental-surface border border-gray-200 p-0.5">
                  <button
                    onClick={() => setProcessingMode('with_billing')}
                    className={`px-4 py-2 rounded-[10px] text-sm font-medium transition-all duration-200 ${
                      processingMode === 'with_billing'
                        ? 'bg-dental-primary text-white shadow-sm'
                        : 'text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    Mit Abrechnung
                  </button>
                  <button
                    onClick={() => setProcessingMode('transcription_only')}
                    className={`px-4 py-2 rounded-[10px] text-sm font-medium transition-all duration-200 ${
                      processingMode === 'transcription_only'
                        ? 'bg-blue-500 text-white shadow-sm'
                        : 'text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    Nur Transkription
                  </button>
                </div>
              </div>

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
              <p className="mt-1 text-xs text-gray-400">Drücke Pause zum Unterbrechen</p>
            </div>
          )}

          {/* RECORDING STATE: Pause Button */}
          {recordingState.isRecording && !recordingState.isProcessing && (
            <div className="py-4 space-y-5 animate-fade-in">
              {/* Pause button */}
              <button
                onClick={handlePause}
                className="group relative inline-flex items-center justify-center"
              >
                <span className="absolute w-24 h-24 rounded-full bg-orange-100 animate-pulse-ring" />
                <span className="relative w-16 h-16 rounded-full bg-gradient-to-br from-orange-500 to-orange-600 flex items-center justify-center shadow-lg group-active:scale-95 transition-transform">
                  <svg className="h-7 w-7 text-white" fill="currentColor" viewBox="0 0 24 24">
                    <rect x="6" y="4" width="4" height="16" rx="1"/>
                    <rect x="14" y="4" width="4" height="16" rx="1"/>
                  </svg>
                </span>
              </button>

              {/* Timer */}
              <div>
                <div className="text-3xl font-mono font-light text-gray-900 tracking-widest">
                  {formatDuration(recordingState.duration)}
                </div>
                <p className="text-xs text-gray-400 mt-1">
                  Aufnahme läuft &middot; Pause zum Anhalten
                </p>
              </div>

              {/* Progress bar */}
              <div className="max-w-xs mx-auto">
                <div className="h-1 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-orange-400 rounded-full transition-all duration-1000 ease-linear"
                    style={{ width: `${Math.min(progressPercent, 100)}%` }}
                  />
                </div>
              </div>
            </div>
          )}

          {/* PAUSED STATE: Session Info + Action Buttons */}
          {sessionState === 'paused' && !recordingState.isRecording && !recordingState.isProcessing && session && (
            <div className="py-6 space-y-5 animate-fade-in">
              {/* Session Info */}
              <div className="mb-6">
                <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-50 rounded-full mb-4">
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                  <span className="text-sm font-medium text-blue-700">
                    Session aktiv ({session.segments.length} Segment{session.segments.length !== 1 ? 'e' : ''})
                  </span>
                </div>

                {/* Accumulated Transcription Preview */}
                <div className="max-w-md mx-auto bg-gray-50 rounded-xl p-4 border border-gray-200">
                  <p className="text-sm text-gray-600 font-medium mb-2">Bisherige Transkription:</p>
                  <p className="text-sm text-gray-800 leading-relaxed line-clamp-3">
                    {session.accumulatedTranscription || 'Keine Transkription verfügbar'}
                  </p>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
                <button
                  onClick={handleResume}
                  className="btn-primary flex items-center gap-2 w-full sm:w-auto"
                >
                  <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M8 5v14l11-7z"/>
                  </svg>
                  Fortsetzen
                </button>
                <button
                  onClick={handleFinalize}
                  className="btn-secondary bg-green-600 hover:bg-green-700 text-white flex items-center gap-2 w-full sm:w-auto"
                >
                  <Check className="h-4 w-4" />
                  Abschließen
                </button>
                <button
                  onClick={handleDiscard}
                  className="btn-ghost text-red-600 hover:text-red-700 hover:bg-red-50 w-full sm:w-auto"
                >
                  Verwerfen
                </button>
              </div>
            </div>
          )}

          {/* PROCESSING STATE: Loading */}
          {(recordingState.isProcessing || sessionState === 'processing') && (
            <div className="py-8 space-y-4 animate-fade-in">
              <Loader2 className="h-10 w-10 animate-spin mx-auto text-dental-primary" />
              <div>
                <p className="text-base font-medium text-gray-900">
                  {sessionState === 'processing' ? 'Session wird verarbeitet...' : 'Transkription läuft...'}
                </p>
                <p className="text-sm text-gray-400 mt-1">
                  {sessionState === 'processing'
                    ? `Extrahiere Billing-Codes (${session?.segments.length || 0} Segmente)`
                    : `Transkription und ${patientData.insuranceType}-Analyse`
                  }
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

            {/* Transfer Code Button */}
            {transcriptionText && (documentation.billing_codes || documentation.abrechnungspositionen)?.length > 0 && (
              <div className="card bg-gradient-to-br from-dental-primary/5 to-dental-primary/10 border-dental-primary/20">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-dental-primary/10 rounded-xl">
                      <Hash className="h-5 w-5 text-dental-primary" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900">Zur Rezeption senden</h3>
                      <p className="text-sm text-gray-500">Transfer-Code zum Eintippen am PC</p>
                    </div>
                  </div>
                  <button
                    onClick={createTransferSession}
                    className="btn-primary flex items-center gap-2"
                  >
                    <Hash className="h-4 w-4" />
                    Code erstellen
                  </button>
                </div>
              </div>
            )}

            {/* Billing Codes - only show if transcription was successful and mode is with_billing */}
            {transcriptionText && processingMode === 'with_billing' && (
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
                    {documentation.findings && Array.isArray(documentation.findings)
                      ? documentation.findings.map((f: any) =>
                          typeof f === 'string' ? f : f.diagnosis || JSON.stringify(f)
                        ).join(', ')
                      : documentation.findings ||
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

      {/* Session Panel */}
      <SessionPanel
        isOpen={sessionPanelOpen}
        onClose={() => setSessionPanelOpen(false)}
        onLoadSession={handleLoadSession}
        apiEndpoint={appSettings.apiEndpoint}
        currentDentistName={patientData.dentistName}
      />

      {/* Short Code Modal */}
      <ShortCodeModal
        isOpen={codeModalOpen}
        onClose={() => setCodeModalOpen(false)}
        transferSession={transferSession}
      />
    </div>
  );
}

export default App;
