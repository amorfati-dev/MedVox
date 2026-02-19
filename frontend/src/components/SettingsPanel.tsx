import React, { useState, useEffect } from 'react';
import { X, Save, RotateCcw, Plus, Trash2 } from 'lucide-react';
import { AppSettings, DEFAULT_SETTINGS, DentistInfo } from '../types';

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
      const parsed = JSON.parse(stored);

      // Migrate from old dentistName to new dentists array
      if (parsed.dentistName && !parsed.dentists) {
        parsed.dentists = [
          {
            id: 'dentist-1',
            name: parsed.dentistName,
          },
        ];
        parsed.currentDentistId = 'dentist-1';
        delete parsed.dentistName;
      }

      return { ...DEFAULT_SETTINGS, ...parsed };
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
    console.log('💾 SettingsPanel: Saving draft:', draft);
    saveSettings(draft);
    onSave(draft);
    onClose();
  };

  const handleReset = () => {
    setDraft({ ...DEFAULT_SETTINGS });
  };

  const handleAddDentist = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const name = formData.get('name') as string;
    const licenseNumber = formData.get('licenseNumber') as string;

    if (!name.trim()) return;

    const newDentist: DentistInfo = {
      id: `dentist-${Date.now()}`,
      name: name.trim(),
      licenseNumber: licenseNumber.trim() || undefined,
    };

    setDraft((prev) => {
      const newDentists = [...prev.dentists, newDentist];
      // If this is the first dentist or no current dentist selected, select this one
      const newCurrentId = prev.dentists.length === 0 ? newDentist.id : prev.currentDentistId;

      return {
        ...prev,
        dentists: newDentists,
        currentDentistId: newCurrentId,
      };
    });

    e.currentTarget.reset();
  };

  const handleRemoveDentist = (dentistId: string) => {
    setDraft((prev) => {
      const newDentists = prev.dentists.filter((d) => d.id !== dentistId);

      // If we're removing the current dentist, select the first one
      let newCurrentId = prev.currentDentistId;
      if (dentistId === prev.currentDentistId && newDentists.length > 0) {
        newCurrentId = newDentists[0].id;
      }

      return {
        ...prev,
        dentists: newDentists,
        currentDentistId: newCurrentId,
      };
    });
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
            {/* Dentist Management */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Zahnärzte verwalten
              </label>

              {/* Dentist List */}
              <div className="space-y-2 mb-3">
                {draft.dentists.map((dentist) => (
                  <div
                    key={dentist.id}
                    className="flex items-center justify-between p-3 bg-white border border-gray-200 rounded-lg hover:border-dental-primary transition-colors"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-gray-900">{dentist.name}</div>
                      {dentist.licenseNumber && (
                        <div className="text-xs text-gray-500">Arztnummer: {dentist.licenseNumber}</div>
                      )}
                    </div>
                    {draft.dentists.length > 1 && (
                      <button
                        onClick={() => handleRemoveDentist(dentist.id)}
                        className="btn-icon ml-2"
                        title="Zahnarzt entfernen"
                      >
                        <Trash2 className="h-4 w-4 text-red-600" />
                      </button>
                    )}
                  </div>
                ))}
              </div>

              {/* Add Dentist Form */}
              <form onSubmit={handleAddDentist} className="space-y-2">
                <input
                  type="text"
                  name="name"
                  placeholder="Name (z.B. Dr. Müller)"
                  className="input-field text-sm"
                  required
                />
                <input
                  type="text"
                  name="licenseNumber"
                  placeholder="Arztnummer (optional)"
                  className="input-field text-sm"
                />
                <button type="submit" className="btn-secondary w-full flex items-center justify-center gap-2">
                  <Plus className="h-4 w-4" />
                  Zahnarzt hinzufügen
                </button>
              </form>

              <p className="mt-2 text-xs text-gray-400">
                Fügen Sie alle Zahnärzte hinzu, die die App nutzen werden
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

            {/* Default Processing Mode */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Standard-Verarbeitungsmodus
              </label>
              <div className="flex rounded-xl border border-gray-200 overflow-hidden">
                <button
                  onClick={() => setDraft((prev) => ({ ...prev, defaultProcessingMode: 'with_billing' }))}
                  className={`flex-1 px-4 py-2.5 text-sm font-medium transition-colors ${
                    draft.defaultProcessingMode === 'with_billing'
                      ? 'bg-dental-primary text-white'
                      : 'bg-white text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  Mit Abrechnung
                </button>
                <button
                  onClick={() => setDraft((prev) => ({ ...prev, defaultProcessingMode: 'transcription_only' }))}
                  className={`flex-1 px-4 py-2.5 text-sm font-medium transition-colors ${
                    draft.defaultProcessingMode === 'transcription_only'
                      ? 'bg-blue-500 text-white'
                      : 'bg-white text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  Nur Transkription
                </button>
              </div>
              <p className="mt-1 text-xs text-gray-400">
                Wählen Sie, ob standardmäßig Abrechnungscodes extrahiert werden sollen
              </p>
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
                    autoStopDuration: parseInt(e.target.value) || 120,
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
