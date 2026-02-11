import React, { useState, useEffect } from 'react';
import { X, Save, RotateCcw } from 'lucide-react';
import { AppSettings, DEFAULT_SETTINGS } from '../types';

interface SettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
  settings: AppSettings;
  onSave: (settings: AppSettings) => void;
}

const STORAGE_KEY = 'medvox-settings';

export function loadSettings(): AppSettings {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(stored) };
    }
  } catch {
    // ignore parse errors
  }
  return { ...DEFAULT_SETTINGS };
}

export function saveSettings(settings: AppSettings): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
}

export const SettingsPanel: React.FC<SettingsPanelProps> = ({
  isOpen,
  onClose,
  settings,
  onSave,
}) => {
  const [draft, setDraft] = useState<AppSettings>(settings);

  useEffect(() => {
    setDraft(settings);
  }, [settings]);

  // Close on Escape
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleSave = () => {
    saveSettings(draft);
    onSave(draft);
    onClose();
  };

  const handleReset = () => {
    setDraft({ ...DEFAULT_SETTINGS });
  };

  return (
    <>
      {/* Overlay */}
      <div className="overlay" onClick={onClose} />

      {/* Panel */}
      <div className="slide-panel">
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-5 border-b border-gray-100">
            <h2 className="text-lg font-semibold text-gray-900">Einstellungen</h2>
            <button onClick={onClose} className="btn-icon">
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
            {/* Dentist Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Zahnarzt-Name
              </label>
              <input
                type="text"
                value={draft.dentistName}
                onChange={(e) => setDraft((prev) => ({ ...prev, dentistName: e.target.value }))}
                className="input-field"
                placeholder="Dr. Mustermann"
              />
              <p className="mt-1 text-xs text-gray-400">
                Wird als Standard-Zahnarzt verwendet
              </p>
            </div>

            {/* Default Insurance Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Standard-Abrechnung
              </label>
              <div className="flex rounded-xl border border-gray-200 overflow-hidden">
                <button
                  onClick={() => setDraft((prev) => ({ ...prev, defaultInsuranceType: 'BEMA' }))}
                  className={`flex-1 px-4 py-2.5 text-sm font-medium transition-colors ${
                    draft.defaultInsuranceType === 'BEMA'
                      ? 'bg-dental-bema text-white'
                      : 'bg-white text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  BEMA
                </button>
                <button
                  onClick={() => setDraft((prev) => ({ ...prev, defaultInsuranceType: 'GOZ' }))}
                  className={`flex-1 px-4 py-2.5 text-sm font-medium transition-colors ${
                    draft.defaultInsuranceType === 'GOZ'
                      ? 'bg-dental-goz text-white'
                      : 'bg-white text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  GOZ
                </button>
              </div>
            </div>

            {/* GOZ Factor */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                GOZ-Steigerungsfaktor
              </label>
              <input
                type="number"
                step="0.1"
                min="1.0"
                max="3.5"
                value={draft.gozFactor}
                onChange={(e) =>
                  setDraft((prev) => ({ ...prev, gozFactor: parseFloat(e.target.value) || 2.3 }))
                }
                className="input-field"
              />
              <p className="mt-1 text-xs text-gray-400">Standard: 2,3-fach</p>
            </div>

            {/* Auto-Stop Duration */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Auto-Stopp nach (Sekunden)
              </label>
              <input
                type="number"
                step="5"
                min="10"
                max="120"
                value={draft.autoStopDuration}
                onChange={(e) =>
                  setDraft((prev) => ({
                    ...prev,
                    autoStopDuration: parseInt(e.target.value) || 30,
                  }))
                }
                className="input-field"
              />
              <p className="mt-1 text-xs text-gray-400">
                Aufnahme wird nach dieser Zeit automatisch gestoppt
              </p>
            </div>

            {/* API Endpoint */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                API-Endpunkt
              </label>
              <input
                type="text"
                value={draft.apiEndpoint}
                onChange={(e) => setDraft((prev) => ({ ...prev, apiEndpoint: e.target.value }))}
                className="input-field font-mono text-xs"
                placeholder="/api/v1"
              />
              <p className="mt-1 text-xs text-gray-400">
                Standard: /api/v1 (nur ändern wenn nötig)
              </p>
            </div>
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-gray-100 flex items-center justify-between">
            <button onClick={handleReset} className="btn-ghost flex items-center gap-2 text-sm">
              <RotateCcw className="h-4 w-4" />
              Zurücksetzen
            </button>
            <div className="flex gap-2">
              <button onClick={onClose} className="btn-secondary text-sm">
                Abbrechen
              </button>
              <button onClick={handleSave} className="btn-primary flex items-center gap-2 text-sm">
                <Save className="h-4 w-4" />
                Speichern
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};
