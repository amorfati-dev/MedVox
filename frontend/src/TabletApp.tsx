import React, { useState, useCallback, useEffect } from 'react';
import { Mic, Loader2, FileText, Settings, Hash, LogOut, Check } from 'lucide-react';
import { BillingCodesDisplay } from './components/BillingCodesDisplay';
import { SettingsPanel, loadSettings, saveSettings } from './components/SettingsPanel';
import { ShortCodeModal } from './components/ShortCodeModal';
import { SessionPanel } from './components/SessionPanel';
import { LoginPage } from './pages/LoginPage';
import { SelectedBillingCode, PatientFormData, AppSettings, ProcessingMode, AuthUser } from './types';
import { useRecording } from './hooks/useRecording';

const AUTH_TOKEN_KEY = 'medvox-auth-token';

/** Tracks landscape vs. portrait orientation, re-evaluated on resize. */
function useOrientation(): boolean {
  const [isLandscape, setIsLandscape] = useState(
    () => window.innerWidth > window.innerHeight,
  );
  useEffect(() => {
    const update = () => setIsLandscape(window.innerWidth > window.innerHeight);
    window.addEventListener('resize', update);
    return () => window.removeEventListener('resize', update);
  }, []);
  return isLandscape;
}

export function TabletApp() {
  const isLandscape = useOrientation();

  // ── Auth state ─────────────────────────────────────────────────────────────
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
    }).catch(() => {/* server unreachable – keep token */});
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const apiFetch = useCallback(async (url: string, options: RequestInit = {}): Promise<Response> => {
    const headers = new Headers(options.headers);
    if (token) headers.set('Authorization', `Bearer ${token}`);
    const res = await fetch(url, { ...options, headers });
    if (res.status === 401) handleLogout();
    return res;
  }, [token]);

  // ── App state ──────────────────────────────────────────────────────────────
  const [appSettings, setAppSettings] = useState<AppSettings>(() => loadSettings());
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [sessionPanelOpen, setSessionPanelOpen] = useState(false);
  const [processingMode, setProcessingMode] = useState<ProcessingMode>(
    appSettings.defaultProcessingMode,
  );

  const getCurrentDentist = () =>
    appSettings.dentists.find((d) => d.id === appSettings.currentDentistId) ||
    appSettings.dentists[0];

  const [patientData, setPatientData] = useState<PatientFormData>({
    patientId: '',
    dentistName: getCurrentDentist()?.name || 'Unknown',
    insuranceType: appSettings.defaultInsuranceType,
  });
  const [selectedDentistId, setSelectedDentistId] = useState<string>(
    () => getCurrentDentist()?.id || 'dentist-1',
  );

  // ── Recording hook ─────────────────────────────────────────────────────────
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
  } = useRecording({ appSettings, patientData, processingMode, apiFetch });

  // ── Settings / dentist handlers ────────────────────────────────────────────
  const handleSettingsSave = (newSettings: AppSettings) => {
    setAppSettings(newSettings);
    saveSettings(newSettings);
    const currentDentist =
      newSettings.dentists.find((d) => d.id === newSettings.currentDentistId) ||
      newSettings.dentists[0];
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
      const updated = { ...appSettings, currentDentistId: dentistId };
      setAppSettings(updated);
      saveSettings(updated);
    }
  };

  const handleExport = (selectedCodes: SelectedBillingCode[]) => {
    const exportData = {
      patient: patientData,
      selected_codes: selectedCodes,
      export_date: new Date().toISOString(),
      total_codes: selectedCodes.length,
    };
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `medvox-export-${patientData.patientId || 'patient'}-${new Date().toISOString().split('T')[0]}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleLoadSession = async (sessionId: number) => {
    try {
      const response = await apiFetch(
        `${appSettings.apiEndpoint}/documentation/sessions/${sessionId}`,
      );
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

  // ── Guard ──────────────────────────────────────────────────────────────────
  if (!token) {
    return <LoginPage apiEndpoint={appSettings.apiEndpoint} onLogin={handleLogin} />;
  }

  // ── Derived ────────────────────────────────────────────────────────────────
  const transcriptionText = getTranscriptionText();
  const hasBillingCodes =
    ((documentation?.billing_codes || documentation?.abrechnungspositionen) ?? []).length > 0;
  const isProcessingAny = recordingState.isProcessing || sessionState === 'processing';

  // ── Sub-components (inline for locality) ──────────────────────────────────

  /** Large round recording / pause button */
  const RecordButton = () => {
    if (recordingState.isRecording && !recordingState.isProcessing) {
      return (
        <button
          onClick={handlePause}
          className="relative inline-flex items-center justify-center touch-manipulation"
          style={{ minWidth: 140, minHeight: 140 }}
        >
          <span className="absolute rounded-full bg-orange-100 animate-pulse-ring"
            style={{ width: 140, height: 140 }} />
          <span
            className="relative rounded-full bg-gradient-to-br from-orange-500 to-orange-600 flex items-center justify-center shadow-2xl active:scale-95 transition-transform"
            style={{ width: 112, height: 112 }}
          >
            <svg className="text-white" width="48" height="48" fill="currentColor" viewBox="0 0 24 24">
              <rect x="6" y="4" width="4" height="16" rx="1"/>
              <rect x="14" y="4" width="4" height="16" rx="1"/>
            </svg>
          </span>
        </button>
      );
    }

    return (
      <button
        onClick={startRecording}
        className="relative inline-flex items-center justify-center touch-manipulation"
        style={{ minWidth: 140, minHeight: 140 }}
      >
        <span className="absolute rounded-full bg-dental-primary/10"
          style={{ width: 140, height: 140 }} />
        <span
          className="relative rounded-full bg-gradient-to-br from-dental-primary to-dental-primary-dark flex items-center justify-center shadow-2xl active:scale-95 transition-transform"
          style={{ width: 112, height: 112 }}
        >
          <Mic className="text-white" width={48} height={48} />
        </span>
      </button>
    );
  };

  /** Left panel content: recording controls */
  const RecordingPanel = () => (
    <div className="flex flex-col items-center justify-center gap-6 h-full py-6">
      {/* Processing Mode Toggle (idle only) */}
      {sessionState === 'idle' && !recordingState.isRecording && !isProcessingAny && (
        <div className="flex rounded-xl bg-dental-surface border border-gray-200 p-0.5">
          <button
            onClick={() => setProcessingMode('with_billing')}
            style={{ minHeight: 52 }}
            className={`px-5 py-3 rounded-[10px] text-base font-medium transition-all duration-200 ${
              processingMode === 'with_billing'
                ? 'bg-dental-primary text-white shadow-sm'
                : 'text-gray-500'
            }`}
          >
            Mit Abrechnung
          </button>
          <button
            onClick={() => setProcessingMode('transcription_only')}
            style={{ minHeight: 52 }}
            className={`px-5 py-3 rounded-[10px] text-base font-medium transition-all duration-200 ${
              processingMode === 'transcription_only'
                ? 'bg-blue-500 text-white shadow-sm'
                : 'text-gray-500'
            }`}
          >
            Nur Transkription
          </button>
        </div>
      )}

      {/* Record / Pause button */}
      {!isProcessingAny && <RecordButton />}

      {/* Timer (recording) */}
      {recordingState.isRecording && !isProcessingAny && (
        <div className="text-center">
          <div className="text-5xl font-mono font-light text-gray-900 tracking-widest">
            {formatDuration(recordingState.duration)}
          </div>
          <p className="text-sm text-gray-400 mt-2">Aufnahme läuft</p>
          <div className="mt-3 w-48 mx-auto">
            <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-orange-400 rounded-full transition-all duration-1000 ease-linear"
                style={{ width: `${Math.min(progressPercent, 100)}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Processing spinner */}
      {isProcessingAny && (
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-16 w-16 animate-spin text-dental-primary" />
          <p className="text-lg font-medium text-gray-700">
            {sessionState === 'processing' ? 'Session wird verarbeitet…' : 'Transkription läuft…'}
          </p>
        </div>
      )}

      {/* Paused state */}
      {sessionState === 'paused' && !recordingState.isRecording && !isProcessingAny && session && (
        <div className="w-full max-w-xs space-y-4">
          <div className="flex items-center justify-center gap-2 px-4 py-2 bg-blue-50 rounded-full">
            <div className="w-2.5 h-2.5 bg-blue-500 rounded-full animate-pulse" />
            <span className="text-base font-medium text-blue-700">
              {session.segments.length} Segment{session.segments.length !== 1 ? 'e' : ''}
            </span>
          </div>

          {/* Accumulated transcription preview */}
          <div className="bg-gray-50 rounded-xl p-3 border border-gray-200 max-h-24 overflow-y-auto">
            <p className="text-sm text-gray-700 leading-relaxed">
              {session.accumulatedTranscription || 'Keine Transkription verfügbar'}
            </p>
          </div>

          {/* Action buttons */}
          <div className="flex flex-col gap-3">
            <button
              onClick={handleResume}
              style={{ minHeight: 52 }}
              className="btn-primary flex items-center justify-center gap-2 text-base"
            >
              <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z"/>
              </svg>
              Fortsetzen
            </button>
            <button
              onClick={handleFinalize}
              style={{ minHeight: 52 }}
              className="btn-secondary bg-green-600 hover:bg-green-700 text-white flex items-center justify-center gap-2 text-base"
            >
              <Check className="h-5 w-5" />
              Fertigstellen
            </button>
            <button
              onClick={handleDiscard}
              style={{ minHeight: 52 }}
              className="btn-ghost text-red-600 hover:text-red-700 hover:bg-red-50 text-base"
            >
              Verwerfen
            </button>
          </div>
        </div>
      )}

      {/* Idle hint */}
      {sessionState === 'idle' && !recordingState.isRecording && !isProcessingAny && (
        <p className="text-sm text-gray-400">Tippen zum Starten</p>
      )}
    </div>
  );

  /** Right panel content: results */
  const ResultsPanel = () => {
    if (!documentation && !isProcessingAny) {
      return (
        <div className="flex items-center justify-center h-full">
          <p className="text-gray-300 text-lg">Ergebnis erscheint hier</p>
        </div>
      );
    }

    if (isProcessingAny) {
      return (
        <div className="flex items-center justify-center h-full">
          <p className="text-gray-400 text-base animate-pulse">Verarbeitung läuft…</p>
        </div>
      );
    }

    return (
      <div className="space-y-4 h-full overflow-y-auto pr-1">
        {/* Transcription */}
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <FileText className="h-4 w-4 text-gray-400" />
            <h3 className="text-base font-semibold text-gray-900">Transkription</h3>
          </div>
          {transcriptionText ? (
            <div className="bg-dental-surface rounded-xl p-3 border border-gray-100">
              <p className="text-gray-800 text-sm leading-relaxed">{transcriptionText}</p>
            </div>
          ) : (
            <div className="bg-amber-50 rounded-xl p-3 border border-amber-200">
              <p className="text-amber-800 text-sm">Keine Transkription erkannt</p>
            </div>
          )}
        </div>

        {/* Billing Codes */}
        {transcriptionText && processingMode === 'with_billing' && (
          <BillingCodesDisplay
            procedures={documentation?.procedures || []}
            billingCodes={documentation?.billing_codes || []}
            onExport={handleExport}
            onAddManual={() => alert('Manuelle Eingabe kommt bald!')}
          />
        )}

        {/* Transfer button */}
        {transcriptionText && hasBillingCodes && (
          <div className="card bg-gradient-to-br from-dental-primary/5 to-dental-primary/10 border-dental-primary/20">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-dental-primary/10 rounded-xl">
                  <Hash className="h-5 w-5 text-dental-primary" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">Zur Rezeption senden</h3>
                  <p className="text-sm text-gray-500">Transfer-Code erstellen</p>
                </div>
              </div>
              <button
                onClick={createTransferSession}
                style={{ minHeight: 52 }}
                className="btn-primary flex items-center gap-2 text-base px-5"
              >
                <Hash className="h-5 w-5" />
                Code erstellen
              </button>
            </div>
          </div>
        )}
      </div>
    );
  };

  // ── Landscape layout ───────────────────────────────────────────────────────
  if (isLandscape) {
    return (
      <div className="h-screen flex flex-col bg-dental-surface overflow-hidden">
        {/* Header */}
        <header className="bg-white border-b border-gray-100 shrink-0 px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <img src="/logo.png" alt="MedVox" className="h-10" />

            {/* Patient ID */}
            <input
              type="text"
              value={patientData.patientId}
              onChange={(e) => setPatientData((prev) => ({ ...prev, patientId: e.target.value }))}
              className="input-field text-xl w-44"
              style={{ minHeight: 44 }}
              placeholder="Patient-ID…"
            />

            {/* Dentist */}
            {appSettings.dentists.length > 0 && (
              <select
                value={selectedDentistId}
                onChange={(e) => handleDentistChange(e.target.value)}
                className="input-field text-base w-48"
                style={{ minHeight: 44 }}
              >
                {appSettings.dentists.map((d) => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </select>
            )}

            {/* Insurance toggle */}
            <div className="flex rounded-xl bg-dental-surface border border-gray-200 p-0.5">
              {(['BEMA', 'GOZ'] as const).map((type) => (
                <button
                  key={type}
                  onClick={() => setPatientData((prev) => ({ ...prev, insuranceType: type }))}
                  style={{ minHeight: 44 }}
                  className={`px-5 py-2 rounded-[10px] text-sm font-medium transition-all duration-200 ${
                    patientData.insuranceType === type
                      ? type === 'BEMA' ? 'bg-dental-bema text-white shadow-sm' : 'bg-dental-goz text-white shadow-sm'
                      : 'text-gray-500'
                  }`}
                >
                  {type}
                </button>
              ))}
            </div>
          </div>

          {/* Right actions */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSessionPanelOpen(true)}
              style={{ minHeight: 44, minWidth: 44 }}
              className="btn-icon"
              title="Behandlungen"
            >
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
              </svg>
            </button>
            <button
              onClick={() => setSettingsOpen(true)}
              style={{ minHeight: 44, minWidth: 44 }}
              className="btn-icon"
              title="Einstellungen"
            >
              <Settings className="h-5 w-5" />
            </button>
            <button
              onClick={handleLogout}
              style={{ minHeight: 44, minWidth: 44 }}
              className="btn-icon"
              title={authUser ? `Abmelden (${authUser.email})` : 'Abmelden'}
            >
              <LogOut className="h-5 w-5" />
            </button>
          </div>
        </header>

        {/* Two-column body */}
        <div className="flex flex-1 overflow-hidden">
          {/* Left column – 40% */}
          <div className="w-2/5 border-r border-gray-200 bg-white overflow-y-auto">
            <RecordingPanel />
          </div>

          {/* Right column – 60% */}
          <div className="w-3/5 p-5 overflow-y-auto">
            <ResultsPanel />
          </div>
        </div>

        {/* Modals */}
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

  // ── Portrait layout ────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-dental-surface">
      {/* Compact header */}
      <header className="bg-white border-b border-gray-100 sticky top-0 z-30 px-4 h-14 flex items-center justify-between">
        <img src="/logo.png" alt="MedVox" className="h-9" />
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSessionPanelOpen(true)}
            style={{ minHeight: 44, minWidth: 44 }}
            className="btn-icon"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
            </svg>
          </button>
          <button
            onClick={() => setSettingsOpen(true)}
            style={{ minHeight: 44, minWidth: 44 }}
            className="btn-icon"
          >
            <Settings className="h-5 w-5" />
          </button>
          <button
            onClick={handleLogout}
            style={{ minHeight: 44, minWidth: 44 }}
            className="btn-icon"
          >
            <LogOut className="h-5 w-5" />
          </button>
        </div>
      </header>

      <main className="px-4 py-4 space-y-4">
        {/* Patient bar */}
        <div className="card !p-4 space-y-3">
          <input
            type="text"
            value={patientData.patientId}
            onChange={(e) => setPatientData((prev) => ({ ...prev, patientId: e.target.value }))}
            className="input-field text-xl"
            style={{ minHeight: 52 }}
            placeholder="Patient-ID eingeben…"
          />

          <div className="flex gap-3">
            {appSettings.dentists.length > 0 && (
              <select
                value={selectedDentistId}
                onChange={(e) => handleDentistChange(e.target.value)}
                className="input-field text-base flex-1"
                style={{ minHeight: 52 }}
              >
                {appSettings.dentists.map((d) => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </select>
            )}

            <div className="flex rounded-xl bg-dental-surface border border-gray-200 p-0.5 shrink-0">
              {(['BEMA', 'GOZ'] as const).map((type) => (
                <button
                  key={type}
                  onClick={() => setPatientData((prev) => ({ ...prev, insuranceType: type }))}
                  style={{ minHeight: 44 }}
                  className={`px-5 py-2 rounded-[10px] text-sm font-medium transition-all duration-200 ${
                    patientData.insuranceType === type
                      ? type === 'BEMA' ? 'bg-dental-bema text-white shadow-sm' : 'bg-dental-goz text-white shadow-sm'
                      : 'text-gray-500'
                  }`}
                >
                  {type}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Recording section */}
        <div className="card text-center">
          <RecordingPanel />
        </div>

        {/* Results */}
        {(documentation || isProcessingAny) && (
          <div className="space-y-4">
            <ResultsPanel />
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
