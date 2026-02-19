import React, { useState, useCallback, useEffect } from 'react';
import { Mic, Loader2, FileText, Settings, Copy, Check, Activity, Hash, Clock, LogOut } from 'lucide-react';
import { BillingCodesDisplay } from './components/BillingCodesDisplay';
import { SettingsPanel, loadSettings, saveSettings } from './components/SettingsPanel';
import { ShortCodeModal } from './components/ShortCodeModal';
import { SessionPanel } from './components/SessionPanel';
import { LoginPage } from './pages/LoginPage';
import { DocumentationResponse, SelectedBillingCode, PatientFormData, AppSettings, ProcessingMode, AuthUser } from './types';
import { useRecording } from './hooks/useRecording';

const AUTH_TOKEN_KEY = 'medvox-auth-token';

function App() {
  // Auth state
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(AUTH_TOKEN_KEY));
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);

  const handleLogin = (newToken: string) => {
    localStorage.setItem(AUTH_TOKEN_KEY, newToken);
    setToken(newToken);
  };

  const handleLogout = () => {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    setToken(null);
    setAuthUser(null);
  };

  // Validate token on mount and fetch current user
  useEffect(() => {
    if (!token) return;
    fetch(`${loadSettings().apiEndpoint}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then(async (res) => {
      if (res.status === 401) {
        handleLogout();
      } else if (res.ok) {
        const user: AuthUser = await res.json();
        setAuthUser(user);
      }
    }).catch(() => {
      // Server unreachable - keep token, will fail on next API call
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auth-aware fetch wrapper
  const apiFetch = useCallback(async (url: string, options: RequestInit = {}): Promise<Response> => {
    const headers = new Headers(options.headers);
    if (token) headers.set('Authorization', `Bearer ${token}`);
    const res = await fetch(url, { ...options, headers });
    if (res.status === 401) handleLogout();
    return res;
  }, [token]);

  const [appSettings, setAppSettings] = useState<AppSettings>(() => loadSettings());
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [sessionPanelOpen, setSessionPanelOpen] = useState(false);
  const [transcriptionCopied, setTranscriptionCopied] = useState(false);
  const [processingMode, setProcessingMode] = useState<ProcessingMode>(appSettings.defaultProcessingMode);

  const getCurrentDentist = () =>
    appSettings.dentists.find((d) => d.id === appSettings.currentDentistId) || appSettings.dentists[0];

  const [patientData, setPatientData] = useState<PatientFormData>({
    patientId: '',
    dentistName: getCurrentDentist()?.name || 'Unknown',
    insuranceType: appSettings.defaultInsuranceType,
  });
  const [selectedDentistId, setSelectedDentistId] = useState<string>(
    () => getCurrentDentist()?.id || 'dentist-1',
  );

  // Recording logic extracted into hook
  const recording = useRecording({ appSettings, patientData, processingMode, apiFetch });
  const {
    recordingState,
    session,
    sessionState,
    documentation,
    transferSession,
    codeModalOpen,
    startRecording,
    handlePause,
    handleResume,
    handleFinalize,
    handleDiscard,
    createTransferSession,
    setDocumentation,
    setCodeModalOpen,
    getTranscriptionText,
    progressPercent,
    formatDuration,
  } = recording;

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

    const currentDentist =
      newSettings.dentists.find((d) => d.id === newSettings.currentDentistId) || newSettings.dentists[0];

    if (currentDentist) {
      setSelectedDentistId(currentDentist.id);
      setPatientData((prev) => ({ ...prev, dentistName: currentDentist.name }));
    }
  };

  const handleDentistChange = (dentistId: string) => {
    setSelectedDentistId(dentistId);
    const dentist = appSettings.dentists.find((d) => d.id === dentistId);
    if (dentist) {
      setPatientData((prev) => ({ ...prev, dentistName: dentist.name }));
      const updatedSettings = { ...appSettings, currentDentistId: dentistId };
      setAppSettings(updatedSettings);
      saveSettings(updatedSettings);
    }
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
      const response = await apiFetch(`${appSettings.apiEndpoint}/documentation/sessions/${sessionId}`);

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

      const result = await response.json();

      if (result.success && result.documentation) {
        setDocumentation(result.documentation);
        if (result.documentation.patient_id) {
          setPatientData((prev) => ({ ...prev, patientId: result.documentation.patient_id }));
        }
        setSessionPanelOpen(false);
      } else {
        alert('Fehler: Session konnte nicht geladen werden');
      }
    } catch (error) {
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

  if (!token) {
    return <LoginPage apiEndpoint={appSettings.apiEndpoint} onLogin={handleLogin} />;
  }

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
              <button
                onClick={handleLogout}
                className="btn-icon"
                title={authUser ? `Abmelden (${authUser.email})` : 'Abmelden'}
              >
                <LogOut className="h-4.5 w-4.5" />
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
          {/* IDLE STATE */}
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
                <span className="absolute w-24 h-24 rounded-full bg-dental-primary/10 group-hover:bg-dental-primary/15 transition-colors duration-300" />
                <span className="relative w-16 h-16 rounded-full bg-gradient-to-br from-dental-primary to-dental-primary-dark flex items-center justify-center shadow-lg group-hover:shadow-xl transition-all duration-200 group-active:scale-95">
                  <Mic className="h-7 w-7 text-white" />
                </span>
              </button>
              <p className="mt-4 text-sm text-gray-500">Aufnahme starten</p>
              <p className="mt-1 text-xs text-gray-400">Drücke Pause zum Unterbrechen</p>
            </div>
          )}

          {/* RECORDING STATE */}
          {recordingState.isRecording && !recordingState.isProcessing && (
            <div className="py-4 space-y-5 animate-fade-in">
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

              <div>
                <div className="text-3xl font-mono font-light text-gray-900 tracking-widest">
                  {formatDuration(recordingState.duration)}
                </div>
                <p className="text-xs text-gray-400 mt-1">
                  Aufnahme läuft &middot; Pause zum Anhalten
                </p>
              </div>

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

          {/* PAUSED STATE */}
          {sessionState === 'paused' && !recordingState.isRecording && !recordingState.isProcessing && session && (
            <div className="py-6 space-y-5 animate-fade-in">
              <div className="mb-6">
                <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-50 rounded-full mb-4">
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                  <span className="text-sm font-medium text-blue-700">
                    Session aktiv ({session.segments.length} Segment{session.segments.length !== 1 ? 'e' : ''})
                  </span>
                </div>

                <div className="max-w-md mx-auto bg-gray-50 rounded-xl p-4 border border-gray-200">
                  <p className="text-sm text-gray-600 font-medium mb-2">Bisherige Transkription:</p>
                  <p className="text-sm text-gray-800 leading-relaxed line-clamp-3">
                    {session.accumulatedTranscription || 'Keine Transkription verfügbar'}
                  </p>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
                <button onClick={handleResume} className="btn-primary flex items-center gap-2 w-full sm:w-auto">
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

          {/* PROCESSING STATE */}
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
                  <button onClick={copyTranscription} className="btn-ghost flex items-center gap-1.5 text-sm">
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
                      <span>Vertrauen: {Math.round(transcriptionConfidence * 100)}%</span>
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
            {transcriptionText && ((documentation.billing_codes || documentation.abrechnungspositionen) ?? []).length > 0 && (
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
                  <button onClick={createTransferSession} className="btn-primary flex items-center gap-2">
                    <Hash className="h-4 w-4" />
                    Code erstellen
                  </button>
                </div>
              </div>
            )}

            {/* Billing Codes */}
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

      <SettingsPanel
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        settings={appSettings}
        onSave={handleSettingsSave}
      />

      <SessionPanel
        isOpen={sessionPanelOpen}
        onClose={() => setSessionPanelOpen(false)}
        onLoadSession={handleLoadSession}
        apiEndpoint={appSettings.apiEndpoint}
        currentDentistName={patientData.dentistName}
        fetchFn={apiFetch}
      />

      <ShortCodeModal
        isOpen={codeModalOpen}
        onClose={() => setCodeModalOpen(false)}
        transferSession={transferSession}
      />
    </div>
  );
}

export default App;
