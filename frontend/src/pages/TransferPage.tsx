import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Loader2, CheckCircle2, XCircle, Copy, Check, FileText, Clock, AlertTriangle } from 'lucide-react';

interface BillingCode {
  code: string;
  system?: string;
  description?: string;
  quantity?: number;
  tooth_number?: string;
  is_zusatzleistung?: boolean;
}

interface TransferData {
  session_id: string;
  billing_codes: BillingCode[];
  transcription: string;
  patient_id?: string;
  created_at: string;
}

export const TransferPage: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();

  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>(
    sessionId ? 'loading' : 'idle'
  );
  const [transferData, setTransferData] = useState<TransferData | null>(null);
  const [error, setError] = useState<string>('');
  const [copiedAll, setCopiedAll] = useState(false);
  const [copiedTranscription, setCopiedTranscription] = useState(false);
  const [codeInput, setCodeInput] = useState<string>('');

  useEffect(() => {
    if (sessionId) {
      fetchTransferData();
    }
  }, [sessionId]);

  const fetchTransferData = async () => {
    try {
      setStatus('loading');

      const response = await fetch(`/api/v1/transfer/${sessionId}`);

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Session nicht gefunden oder bereits abgerufen');
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: TransferData = await response.json();
      console.log('📨 Transfer data received:', data);

      setTransferData(data);
      setStatus('success');
    } catch (err) {
      console.error('Error fetching transfer data:', err);
      setError(err instanceof Error ? err.message : 'Fehler beim Laden der Daten');
      setStatus('error');
    }
  };

  const formatCodesForEvident = (): string => {
    if (!transferData) return '';
    return transferData.billing_codes
      .map((code) => code.code)
      .join(', ');
  };

  const copyAllCodes = async () => {
    const text = formatCodesForEvident();
    try {
      await navigator.clipboard.writeText(text);
      setCopiedAll(true);
      setTimeout(() => setCopiedAll(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const copyTranscription = async () => {
    if (!transferData) return;
    try {
      await navigator.clipboard.writeText(transferData.transcription);
      setCopiedTranscription(true);
      setTimeout(() => setCopiedTranscription(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const copySingleCode = async (code: string) => {
    try {
      await navigator.clipboard.writeText(code);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleCodeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const code = codeInput.trim().toUpperCase().replace('-', '');

    if (code.length !== 6) {
      setError('Code muss 6 Zeichen lang sein');
      return;
    }

    try {
      setStatus('loading');
      setError('');

      const response = await fetch(`/api/v1/transfer/code/${code}`);

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Code nicht gefunden oder bereits verwendet');
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: TransferData = await response.json();
      console.log('📨 Transfer data received via code:', data);

      setTransferData(data);
      setStatus('success');
    } catch (err) {
      console.error('Error fetching via code:', err);
      setError(err instanceof Error ? err.message : 'Fehler beim Laden der Daten');
      setStatus('error');
    }
  };

  const handleCodeInput = (value: string) => {
    // Auto-format with dash: ABC123 → ABC-123
    let formatted = value.toUpperCase().replace(/[^A-Z0-9]/g, '');

    if (formatted.length > 6) {
      formatted = formatted.slice(0, 6);
    }

    setCodeInput(formatted);

    // Auto-submit when 6 characters entered
    if (formatted.length === 6) {
      setTimeout(() => {
        const form = document.getElementById('code-form') as HTMLFormElement;
        form?.requestSubmit();
      }, 300);
    }
  };

  // Idle state - Code input
  if (status === 'idle') {
    return (
      <div className="min-h-screen bg-dental-surface flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-card p-8">
          <div className="text-center mb-6">
            <div className="p-3 bg-dental-primary/10 rounded-full w-fit mx-auto mb-4">
              <FileText className="h-8 w-8 text-dental-primary" />
            </div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              MedVox Transfer
            </h1>
            <p className="text-gray-600">
              Transfer-Code eingeben
            </p>
          </div>

          <form id="code-form" onSubmit={handleCodeSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                6-stelliger Code
              </label>
              <input
                type="text"
                value={codeInput}
                onChange={(e) => handleCodeInput(e.target.value)}
                placeholder="AB1234"
                className="input-field text-center text-2xl font-mono tracking-widest uppercase"
                autoFocus
                maxLength={6}
              />
              <p className="mt-2 text-xs text-gray-500 text-center">
                Code von iPad/Tablet eingeben
              </p>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-sm text-red-800">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={codeInput.length !== 6}
              className="btn-primary w-full"
            >
              Codes laden
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-gray-100">
            <p className="text-xs text-gray-500 text-center">
              Der Code ist nur <strong>einmalig verwendbar</strong> und läuft nach{' '}
              <strong>5 Minuten</strong> ab.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Loading state
  if (status === 'loading') {
    return (
      <div className="min-h-screen bg-dental-surface flex items-center justify-center p-4">
        <div className="text-center space-y-4">
          <Loader2 className="h-12 w-12 animate-spin mx-auto text-dental-primary" />
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Daten werden geladen...</h2>
            <p className="text-sm text-gray-500 mt-2">Einen Moment bitte</p>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (status === 'error') {
    return (
      <div className="min-h-screen bg-dental-surface flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-card p-8 text-center">
          <div className="p-3 bg-red-50 rounded-full w-fit mx-auto mb-4">
            <XCircle className="h-8 w-8 text-red-500" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Transfer fehlgeschlagen</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div className="text-left text-sm text-amber-800">
                <p className="font-medium mb-1">Mögliche Gründe:</p>
                <ul className="list-disc list-inside space-y-1 text-amber-700">
                  <li>Session bereits abgerufen (One-Time-Use)</li>
                  <li>Session abgelaufen (max. 5 Minuten gültig)</li>
                  <li>Ungültige Session-ID</li>
                </ul>
              </div>
            </div>
          </div>
          <button
            onClick={() => navigate('/')}
            className="btn-primary w-full"
          >
            Zurück zur Startseite
          </button>
        </div>
      </div>
    );
  }

  // Success state
  return (
    <div className="min-h-screen bg-dental-surface p-4 pb-8">
      <div className="max-w-3xl mx-auto space-y-6 pt-8">
        {/* Success Header */}
        <div className="bg-white rounded-2xl shadow-card p-6 text-center">
          <div className="p-3 bg-dental-success/10 rounded-full w-fit mx-auto mb-4">
            <CheckCircle2 className="h-8 w-8 text-dental-success" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            Transfer erfolgreich!
          </h1>
          <p className="text-gray-600">
            Die Daten können jetzt in das PVS übertragen werden
          </p>
        </div>

        {/* Patient Info */}
        {transferData?.patient_id && (
          <div className="bg-white rounded-2xl shadow-card p-6">
            <h2 className="text-sm font-medium text-gray-500 mb-2">Patient-ID</h2>
            <p className="text-lg font-semibold text-gray-900">{transferData.patient_id}</p>
          </div>
        )}

        {/* Quick Copy All */}
        <div className="bg-gradient-to-br from-dental-primary/10 to-dental-primary/5 border-2 border-dental-primary/20 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Schnell-Übertragung</h2>
              <p className="text-sm text-gray-600">Alle Codes für Evident/Z1/CharlieOS</p>
            </div>
            <button
              onClick={copyAllCodes}
              className="btn-primary flex items-center gap-2"
            >
              {copiedAll ? (
                <>
                  <Check className="h-4 w-4" />
                  Kopiert!
                </>
              ) : (
                <>
                  <Copy className="h-4 w-4" />
                  Alle kopieren
                </>
              )}
            </button>
          </div>
          <div className="bg-white rounded-xl p-4 font-mono text-sm text-gray-800 border border-dental-primary/20">
            {formatCodesForEvident()}
          </div>
        </div>

        {/* Transcription */}
        {transferData?.transcription && (
          <div className="bg-white rounded-2xl shadow-card p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                <FileText className="h-5 w-5 text-gray-400" />
                Transkription
              </h2>
              <button
                onClick={copyTranscription}
                className="btn-ghost flex items-center gap-2 text-sm"
              >
                {copiedTranscription ? (
                  <>
                    <Check className="h-4 w-4 text-dental-success" />
                    <span className="text-dental-success">Kopiert!</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-4 w-4" />
                    Kopieren
                  </>
                )}
              </button>
            </div>
            <div className="bg-dental-surface rounded-xl p-4">
              <p className="text-gray-800 leading-relaxed">{transferData.transcription}</p>
            </div>
          </div>
        )}

        {/* Billing Codes Detail */}
        <div className="bg-white rounded-2xl shadow-card p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Abrechnungspositionen ({transferData?.billing_codes.length})
          </h2>
          <div className="space-y-2">
            {transferData?.billing_codes.map((code, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 bg-dental-surface rounded-xl hover:bg-gray-100 transition-colors group"
              >
                <div className="flex items-center gap-3 flex-1">
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2.5 py-1 rounded-lg text-xs font-semibold ${
                        code.system?.toUpperCase() === 'GOZ'
                          ? 'bg-dental-goz-light text-dental-goz'
                          : 'bg-dental-bema-light text-dental-bema'
                      }`}
                    >
                      {code.system?.toUpperCase() || 'BEMA'}
                    </span>
                    <span className="text-lg font-bold text-gray-900">{code.code}</span>
                  </div>

                  <div className="flex-1">
                    {code.description && (
                      <p className="text-sm text-gray-600">{code.description}</p>
                    )}
                    <div className="flex items-center gap-2 text-xs text-gray-400 mt-1">
                      {code.tooth_number && <span>Zahn {code.tooth_number}</span>}
                      {code.quantity && code.quantity > 1 && (
                        <>
                          <span>•</span>
                          <span>{code.quantity}x</span>
                        </>
                      )}
                      {code.is_zusatzleistung && (
                        <>
                          <span>•</span>
                          <span className="text-dental-zusatz font-medium">Zusatzleistung</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => copySingleCode(code.code)}
                  className="btn-ghost opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <Copy className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Session Info */}
        <div className="bg-gray-50 rounded-xl p-4 text-center">
          <div className="flex items-center justify-center gap-2 text-sm text-gray-500">
            <Clock className="h-4 w-4" />
            <span>
              Diese Session wurde einmalig abgerufen und ist nicht mehr verfügbar
            </span>
          </div>
        </div>

        {/* Back Button */}
        <button
          onClick={() => navigate('/')}
          className="btn-secondary w-full"
        >
          Zurück zur Startseite
        </button>
      </div>
    </div>
  );
};
