import React, { useState, useEffect } from 'react';
import { X, Hash, Clock, Copy, Check } from 'lucide-react';
import { TransferSession } from '../types';

interface ShortCodeModalProps {
  isOpen: boolean;
  onClose: () => void;
  transferSession: TransferSession | null;
}

export const ShortCodeModal: React.FC<ShortCodeModalProps> = ({
  isOpen,
  onClose,
  transferSession,
}) => {
  const [timeRemaining, setTimeRemaining] = useState<number>(0);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!transferSession) return;

    // Update countdown every second
    const interval = setInterval(() => {
      const now = new Date().getTime();
      const expiresAt = new Date(transferSession.expires_at).getTime();
      const remaining = Math.max(0, Math.floor((expiresAt - now) / 1000));
      setTimeRemaining(remaining);

      if (remaining === 0) {
        clearInterval(interval);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [transferSession]);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    if (isOpen) {
      window.addEventListener('keydown', handleEscape);
    }

    return () => window.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  if (!isOpen || !transferSession) return null;

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatCodeWithDash = (code: string): string => {
    // Format AB1234 as AB-1234 for readability
    if (code.length === 6) {
      return `${code.slice(0, 3)}-${code.slice(3)}`;
    }
    return code;
  };

  const copyCode = async () => {
    if (!transferSession) return;
    try {
      await navigator.clipboard.writeText(transferSession.short_code ?? '');
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  const formattedCode = formatCodeWithDash(transferSession.short_code ?? '');

  return (
    <>
      {/* Overlay */}
      <div className="overlay" onClick={onClose} />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-elevated max-w-md w-full p-6 animate-slide-up">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-dental-primary/10 rounded-xl">
                <Hash className="h-6 w-6 text-dental-primary" />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-gray-900">
                  Transfer-Code
                </h2>
                <p className="text-sm text-gray-500">
                  Zur Rezeption übertragen
                </p>
              </div>
            </div>
            <button onClick={onClose} className="btn-icon">
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Short Code Display */}
          <div className="flex flex-col items-center mb-6">
            <div className="bg-gradient-to-br from-dental-primary/10 to-dental-primary/5 border-4 border-dental-primary/20 rounded-2xl p-8 mb-4 w-full">
              <div className="text-center">
                <p className="text-sm text-gray-500 mb-2">Code eingeben am PC:</p>
                <div className="flex items-center justify-center gap-2">
                  <span className="text-6xl font-bold font-mono text-dental-primary tracking-widest">
                    {formattedCode}
                  </span>
                  <button
                    onClick={copyCode}
                    className="btn-icon ml-2"
                    title="Code kopieren"
                  >
                    {copied ? (
                      <Check className="h-5 w-5 text-dental-success" />
                    ) : (
                      <Copy className="h-5 w-5" />
                    )}
                  </button>
                </div>
              </div>
            </div>

            {/* Time Remaining */}
            <div className="flex items-center gap-2 text-sm text-gray-600 bg-gray-50 px-4 py-2 rounded-xl">
              <Clock className="h-4 w-4" />
              <span>
                Gültig noch: <strong className="text-dental-primary">{formatTime(timeRemaining)}</strong>
              </span>
            </div>
          </div>

          {/* Instructions */}
          <div className="bg-dental-surface p-4 rounded-xl mb-4">
            <h3 className="text-sm font-semibold text-gray-900 mb-2">
              So funktioniert's:
            </h3>
            <ol className="text-sm text-gray-600 space-y-2 list-decimal list-inside">
              <li>Gehe zum Rezeptions-PC</li>
              <li>Öffne: <span className="font-mono text-dental-primary">medvox.app</span></li>
              <li>Gib Code ein: <span className="font-mono font-bold">{formattedCode}</span></li>
              <li>Codes werden geladen → in PVS einfügen</li>
            </ol>
          </div>

          {/* Tips */}
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-3 text-xs text-blue-800">
            <p className="font-medium mb-1">💡 Tipp:</p>
            <p>
              Code ist nur <strong>einmalig</strong> verwendbar. Nach dem Abrufen ist er nicht mehr gültig.
            </p>
          </div>

          {/* Session ID (for debugging) */}
          {process.env.NODE_ENV === 'development' && (
            <div className="mt-4 pt-4 border-t border-gray-100">
              <p className="text-xs text-gray-400 font-mono">
                Session: {transferSession.session_id}
              </p>
            </div>
          )}
        </div>
      </div>
    </>
  );
};
