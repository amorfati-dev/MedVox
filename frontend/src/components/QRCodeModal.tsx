import React, { useState, useEffect } from 'react';
import { X, QrCode, Clock, ExternalLink, Smartphone } from 'lucide-react';
import { TransferSession } from '../types';

interface QRCodeModalProps {
  isOpen: boolean;
  onClose: () => void;
  transferSession: TransferSession | null;
}

export const QRCodeModal: React.FC<QRCodeModalProps> = ({
  isOpen,
  onClose,
  transferSession,
}) => {
  const [timeRemaining, setTimeRemaining] = useState<number>(0);

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

  return (
    <>
      {/* Overlay */}
      <div className="overlay" onClick={onClose} />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-elevated max-w-lg w-full p-6 animate-slide-up">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-dental-primary/10 rounded-xl">
                <QrCode className="h-6 w-6 text-dental-primary" />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-gray-900">
                  Zur Rezeption senden
                </h2>
                <p className="text-sm text-gray-500">
                  QR-Code scannen zum Übertragen
                </p>
              </div>
            </div>
            <button onClick={onClose} className="btn-icon">
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* QR Code */}
          <div className="flex flex-col items-center mb-6">
            <div className="bg-white p-4 rounded-2xl border-4 border-dental-primary/20 mb-4">
              <img
                src={transferSession.qr_code}
                alt="QR Code"
                className="w-64 h-64"
              />
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
            <div className="flex items-start gap-3 mb-3">
              <div className="p-1.5 bg-dental-primary/10 rounded-lg mt-0.5">
                <Smartphone className="h-4 w-4 text-dental-primary" />
              </div>
              <div className="flex-1">
                <h3 className="text-sm font-semibold text-gray-900 mb-1">
                  So funktioniert's:
                </h3>
                <ol className="text-sm text-gray-600 space-y-1.5 list-decimal list-inside">
                  <li>QR-Code mit Smartphone am Rezeptions-PC scannen</li>
                  <li>Transfer-Seite öffnet sich automatisch</li>
                  <li>Codes kopieren und in PVS einfügen</li>
                </ol>
              </div>
            </div>
          </div>

          {/* Manual Link */}
          <button
            onClick={() => window.open(transferSession.transfer_url, '_blank')}
            className="w-full btn-secondary flex items-center justify-center gap-2 text-sm"
          >
            <ExternalLink className="h-4 w-4" />
            Link manuell öffnen
          </button>

          {/* Session ID (for debugging) */}
          {import.meta.env.DEV && (
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
