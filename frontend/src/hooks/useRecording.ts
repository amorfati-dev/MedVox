import { useState, useRef, useCallback } from 'react';
import {
  RecordingState,
  RecordingSession,
  SessionState,
  AudioSegment,
  DocumentationResponse,
  TransferSession,
  PatientFormData,
  AppSettings,
  ProcessingMode,
} from '../types';

export interface UseRecordingOptions {
  appSettings: AppSettings;
  patientData: PatientFormData;
  processingMode: ProcessingMode;
  apiFetch: (url: string, options?: RequestInit) => Promise<Response>;
  onError?: (message: string) => void;
}

export function useRecording({
  appSettings,
  patientData,
  processingMode,
  apiFetch,
  onError,
}: UseRecordingOptions) {
  const [recordingState, setRecordingState] = useState<RecordingState>({
    isRecording: false,
    isProcessing: false,
    duration: 0,
  });
  const [session, setSession] = useState<RecordingSession | null>(null);
  const [sessionState, setSessionState] = useState<SessionState>('idle');
  const [documentation, setDocumentation] = useState<DocumentationResponse | null>(null);
  const [transferSession, setTransferSession] = useState<TransferSession | null>(null);
  const [codeModalOpen, setCodeModalOpen] = useState(false);

  // Media refs
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const durationIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // Track current duration to avoid stale closure in mediaRecorder.onstop
  const durationRef = useRef(0);

  // Refs for options – updated on every render to avoid stale closures in callbacks
  const appSettingsRef = useRef(appSettings);
  const patientDataRef = useRef(patientData);
  const processingModeRef = useRef(processingMode);
  const apiFetchRef = useRef(apiFetch);
  appSettingsRef.current = appSettings;
  patientDataRef.current = patientData;
  processingModeRef.current = processingMode;
  apiFetchRef.current = apiFetch;

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const getTranscriptionText = useCallback((): string => {
    if (!documentation) return '';
    const t = documentation.transcription;
    if (typeof t === 'string') return t;
    return t?.text || '';
  }, [documentation]);

  const quickTranscribe = async (audioBlob: Blob): Promise<string> => {
    try {
      const formData = new FormData();
      const fileExtension = audioBlob.type.includes('wav') ? '.wav' : '.webm';
      formData.append('audio_file', audioBlob, `segment${fileExtension}`);
      formData.append('processing_mode', 'transcription_only');

      const response = await apiFetchRef.current(
        `${appSettingsRef.current.apiEndpoint}/documentation/process-audio`,
        { method: 'POST', body: formData },
      );

      if (!response.ok) return '[Transkription fehlgeschlagen]';

      const result = await response.json();
      const transcription = result.documentation?.transcription;
      if (typeof transcription === 'string') return transcription;
      if (transcription?.text) return transcription.text;
      return '[Keine Transkription]';
    } catch {
      return '[Fehler]';
    }
  };

  const processAudioWithSession = async (audioBlob: Blob, sessionData: RecordingSession) => {
    setRecordingState((prev) => ({ ...prev, isProcessing: true }));
    try {
      const formData = new FormData();
      const fileExtension = audioBlob.type.includes('wav') ? '.wav' : '.webm';
      formData.append('audio_file', audioBlob, `recording${fileExtension}`);
      formData.append('patient_id', sessionData.patientId);
      formData.append('dentist_id', sessionData.dentistName);
      formData.append('insurance_type', sessionData.insuranceType);
      formData.append('processing_mode', processingModeRef.current);

      const response = await apiFetchRef.current(
        `${appSettingsRef.current.apiEndpoint}/documentation/process-audio`,
        { method: 'POST', body: formData },
      );

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

      const result = await response.json();
      const doc = result.success ? result.documentation : null;
      setDocumentation(doc);

      if (doc) {
        const settings = appSettingsRef.current;
        const currentDentist =
          settings.dentists.find((d) => d.id === settings.currentDentistId) || settings.dentists[0];
        if (currentDentist) {
          localStorage.removeItem(`medvox-sessions-cache-${currentDentist.name}`);
        }
      }
    } catch (error) {
      console.error('Error processing audio:', error);
      onError?.('Fehler bei der Verarbeitung der Aufnahme');
    } finally {
      setRecordingState((prev) => ({ ...prev, isProcessing: false }));
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

  // Stable ref to stopRecording for use inside setInterval closure
  const stopRecordingRef = useRef(stopRecording);
  stopRecordingRef.current = stopRecording;

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

      const mediaRecorder = new MediaRecorder(stream, { mimeType, audioBitsPerSecond: 64000 });
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        const duration = durationRef.current;
        stream.getTracks().forEach((track) => track.stop());

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
            return {
              segments: [segment],
              isActive: true,
              accumulatedTranscription: transcription,
              patientId: patientDataRef.current.patientId,
              dentistName: patientDataRef.current.dentistName,
              insuranceType: patientDataRef.current.insuranceType,
            };
          }
          return {
            ...prev,
            segments: [...prev.segments, segment],
            accumulatedTranscription: prev.accumulatedTranscription + ' ' + transcription,
          };
        });

        setSessionState('paused');
        setRecordingState((prev) => ({ ...prev, isProcessing: false }));
      };

      mediaRecorder.start();
      durationRef.current = 0;
      setRecordingState((prev) => ({ ...prev, isRecording: true, duration: 0 }));
      setSessionState('recording');

      durationIntervalRef.current = setInterval(() => {
        setRecordingState((prev) => {
          const newDuration = prev.duration + 1;
          durationRef.current = newDuration;
          if (newDuration >= appSettingsRef.current.autoStopDuration) {
            stopRecordingRef.current();
            return prev;
          }
          return { ...prev, duration: newDuration };
        });
      }, 1000);
    } catch (error) {
      console.error('Error starting recording:', error);
      onError?.('Fehler beim Zugriff auf das Mikrofon');
    }
  };

  // Ref so handleResume always calls the latest startRecording
  const startRecordingRef = useRef<() => Promise<void>>(startRecording);
  startRecordingRef.current = startRecording;

  const handlePause = useCallback(() => {
    stopRecording();
  }, [stopRecording]);

  const handleResume = useCallback(async () => {
    await startRecordingRef.current();
  }, []);

  const handleFinalize = useCallback(async () => {
    if (!session || session.segments.length === 0) return;
    setSessionState('processing');
    try {
      const mergedBlob = new Blob(
        session.segments.map((s) => s.blob),
        { type: session.segments[0]?.blob.type || 'audio/webm' },
      );
      await processAudioWithSession(mergedBlob, session);
      setSession(null);
      setSessionState('idle');
    } catch (error) {
      console.error('Error finalizing session:', error);
      onError?.('Fehler beim Abschließen der Session');
      setSessionState('paused');
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session]);

  const handleDiscard = useCallback(() => {
    if (confirm('Möchten Sie die aktuelle Session wirklich verwerfen?')) {
      setSession(null);
      setSessionState('idle');
      setDocumentation(null);
    }
  }, []);

  const createTransferSession = useCallback(async () => {
    if (!documentation) return;
    try {
      const billingCodes = documentation.billing_codes || documentation.abrechnungspositionen || [];
      const transcription = (() => {
        const t = documentation.transcription;
        if (typeof t === 'string') return t;
        return t?.text || '';
      })();

      if (billingCodes.length === 0) {
        onError?.('Keine Abrechnungscodes zum Übertragen vorhanden');
        return;
      }

      const response = await apiFetchRef.current(
        `${appSettingsRef.current.apiEndpoint}/transfer/create`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            billing_codes: billingCodes,
            transcription,
            patient_id: patientDataRef.current.patientId || undefined,
          }),
        },
      );

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

      const transferData: TransferSession = await response.json();
      setTransferSession(transferData);
      setCodeModalOpen(true);
    } catch (error) {
      console.error('Error creating transfer session:', error);
      onError?.('Fehler beim Erstellen der Übertragung');
    }
  }, [documentation, onError]);

  const progressPercent = (recordingState.duration / appSettings.autoStopDuration) * 100;

  return {
    // State
    recordingState,
    session,
    sessionState,
    documentation,
    transferSession,
    codeModalOpen,
    // Actions
    startRecording,
    stopRecording,
    handlePause,
    handleResume,
    handleFinalize,
    handleDiscard,
    createTransferSession,
    setDocumentation,
    setCodeModalOpen,
    // Helpers
    getTranscriptionText,
    progressPercent,
    formatDuration,
  };
}
