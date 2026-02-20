import React from 'react';
import { AlertTriangle, X } from 'lucide-react';

type ToastProps = {
  message: string | null;
  onClose: () => void;
};

export const Toast: React.FC<ToastProps> = ({ message, onClose }) => {
  if (!message) return null;

  return (
    <div className="fixed top-4 right-4 z-[60] max-w-sm w-[calc(100%-2rem)]">
      <div className="bg-amber-50 dark:bg-amber-950/60 border border-amber-200 dark:border-amber-900 rounded-xl shadow-card p-3">
        <div className="flex items-start gap-2">
          <AlertTriangle className="h-4 w-4 text-amber-700 dark:text-amber-400 mt-0.5 shrink-0" />
          <p className="text-sm text-amber-900 dark:text-amber-200 flex-1">{message}</p>
          <button
            onClick={onClose}
            className="btn-icon !p-1.5"
            aria-label="Fehlermeldung schließen"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
