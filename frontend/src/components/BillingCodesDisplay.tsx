import React, { useState, useMemo } from 'react';
import { Check, Plus, Download, Copy, ClipboardCheck, FileText } from 'lucide-react';
import { SelectedBillingCode, BillingCode, DentalProcedure } from '../types';

interface BillingCodesDisplayProps {
  procedures?: DentalProcedure[];
  billingCodes?: BillingCode[];
  onExport: (selectedCodes: SelectedBillingCode[]) => void;
  onAddManual: () => void;
}

export const BillingCodesDisplay: React.FC<BillingCodesDisplayProps> = ({
  procedures = [],
  billingCodes = [],
  onExport,
  onAddManual,
}) => {
  const [copiedAll, setCopiedAll] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Normalize and memoize billing codes from props
  const normalizedCodes = useMemo((): SelectedBillingCode[] => {
    const codes: SelectedBillingCode[] = [];

    procedures.forEach((procedure, procIndex) => {
      const procedureCodes = procedure.billing_codes || procedure.abrechnung || [];

      procedureCodes.forEach((code, codeIndex) => {
        const systemValue = (code.system || code.code_system || 'bema').toLowerCase();
        const normalizedSystem = systemValue === 'goz' ? 'GOZ' : 'BEMA';

        codes.push({
          id: `proc-${procIndex}-${codeIndex}`,
          code: code.code,
          system: normalizedSystem as 'BEMA' | 'GOZ',
          description:
            code.description || code.description_de || code.bezeichnung || code.leistungsbeschreibung,
          quantity: code.quantity || code.anzahl || 1,
          selected: true,
          is_zusatzleistung: code.is_zusatzleistung || false,
          tooth_number: code.tooth_number || procedure.tooth || procedure.tooth_number || procedure.zahn,
          procedure_context:
            procedure.procedure_name || procedure.procedure_description_de || procedure.prozedur,
          tooth_context: procedure.tooth || procedure.tooth_number || procedure.zahn,
        });
      });
    });

    billingCodes.forEach((code, index) => {
      const systemValue = (code.system || code.code_system || 'bema').toLowerCase();
      const normalizedSystem = systemValue === 'goz' ? 'GOZ' : 'BEMA';

      codes.push({
        id: `standalone-${index}`,
        code: code.code,
        system: normalizedSystem as 'BEMA' | 'GOZ',
        description:
          code.description || code.description_de || code.bezeichnung || code.leistungsbeschreibung,
        quantity: code.quantity || code.anzahl || 1,
        selected: true,
        is_zusatzleistung: code.is_zusatzleistung || false,
        tooth_number: code.tooth_number,
      });
    });

    return codes;
  }, [procedures, billingCodes]);

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  React.useEffect(() => {
    const allIds = new Set(normalizedCodes.map((code) => code.id));
    setSelectedIds(allIds);
  }, [normalizedCodes.length]);

  const displayCodes = normalizedCodes.map((code) => ({
    ...code,
    selected: selectedIds.has(code.id),
  }));

  const toggleCodeSelection = (id: string) => {
    setSelectedIds((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  const handleSelectAll = () => {
    const allSelected = displayCodes.every((code) => code.selected);
    if (allSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(displayCodes.map((code) => code.id)));
    }
  };

  const handleExport = () => {
    const selected = displayCodes.filter((code) => code.selected);
    onExport(selected);
  };

  /** Format a single code for Evident: e.g. "13a" or "2080" */
  const formatCodeForEvident = (code: SelectedBillingCode): string => {
    return code.code || '';
  };

  /** Format all selected codes as Evident-compatible comma-separated string */
  const getEvidentString = (): string => {
    return displayCodes
      .filter((code) => code.selected)
      .map(formatCodeForEvident)
      .filter(Boolean)
      .join(', ');
  };

  /** Format detailed text for clipboard (with descriptions) */
  const getDetailedString = (): string => {
    return displayCodes
      .filter((code) => code.selected)
      .map((code) => {
        const system = code.system || 'BEMA';
        const suffix = code.is_zusatzleistung ? ' (Zusatzleistung)' : '';
        const tooth = code.tooth_context ? ` (Zahn ${code.tooth_context})` : '';
        return `${system} ${code.code}${tooth}${suffix}`;
      })
      .join('\n');
  };

  /** Copy Evident-format codes to clipboard */
  const copyForEvident = async () => {
    const text = getEvidentString();
    try {
      await navigator.clipboard.writeText(text);
      setCopiedAll(true);
      setTimeout(() => setCopiedAll(false), 2000);
    } catch {
      // fallback
    }
  };

  /** Copy a single code to clipboard */
  const copySingleCode = async (code: SelectedBillingCode) => {
    try {
      await navigator.clipboard.writeText(code.code);
      setCopiedId(code.id);
      setTimeout(() => setCopiedId(null), 1500);
    } catch {
      // fallback
    }
  };

  const selectedCount = displayCodes.filter((code) => code.selected).length;
  const totalCodes = displayCodes.length;
  const bemaCount = displayCodes.filter((c) => c.selected && c.system === 'BEMA' && !c.is_zusatzleistung).length;
  const gozCount = displayCodes.filter((c) => c.selected && c.system === 'GOZ' && !c.is_zusatzleistung).length;
  const zusatzCount = displayCodes.filter((c) => c.selected && c.is_zusatzleistung).length;

  if (totalCodes === 0) {
    return (
      <div className="card animate-fade-in">
        <h2 className="text-lg font-semibold text-gray-900 mb-1">Abrechnungsziffern</h2>
        <div className="text-center py-10 text-gray-400">
          <FileText className="h-10 w-10 mx-auto mb-3 opacity-40" />
          <p className="text-sm">Noch keine Abrechnungsziffern erkannt</p>
          <button onClick={onAddManual} className="btn-secondary mt-4 flex items-center gap-2 mx-auto text-sm">
            <Plus className="h-4 w-4" />
            Manuell hinzufügen
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="card animate-slide-up">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Abrechnungsziffern</h2>
          <div className="flex items-center gap-2 mt-1.5">
            {bemaCount > 0 && (
              <span className="badge-bema">{bemaCount} BEMA</span>
            )}
            {gozCount > 0 && (
              <span className="badge-goz">{gozCount} GOZ</span>
            )}
            {zusatzCount > 0 && (
              <span className="badge-zusatz">{zusatzCount} Zusatz</span>
            )}
          </div>
        </div>
      </div>

      {/* Controls bar */}
      <div className="flex items-center justify-between mb-4 p-3 bg-dental-surface rounded-xl border border-gray-100">
        <label className="flex items-center gap-2.5 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={selectedCount === totalCodes}
            onChange={handleSelectAll}
            className="w-4 h-4 rounded border-gray-300 text-dental-primary focus:ring-dental-primary/40"
          />
          <span className="text-sm font-medium text-gray-600">
            Alle ({selectedCount}/{totalCodes})
          </span>
        </label>

        <div className="flex gap-2">
          <button
            onClick={onAddManual}
            className="btn-ghost flex items-center gap-1.5 text-sm"
          >
            <Plus className="h-3.5 w-3.5" />
            Hinzufügen
          </button>
          <button
            onClick={handleExport}
            disabled={selectedCount === 0}
            className="btn-ghost flex items-center gap-1.5 text-sm disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Download className="h-3.5 w-3.5" />
            JSON
          </button>
          <div className="relative">
            <button
              onClick={copyForEvident}
              disabled={selectedCount === 0}
              className="btn-primary flex items-center gap-1.5 text-sm disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {copiedAll ? (
                <>
                  <ClipboardCheck className="h-3.5 w-3.5" />
                  Kopiert!
                </>
              ) : (
                <>
                  <Copy className="h-3.5 w-3.5" />
                  Evident kopieren
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Preview of the Evident copy string */}
      {selectedCount > 0 && (
        <div className="mb-4 px-3.5 py-2.5 bg-gray-50 rounded-xl border border-gray-100">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">Evident-Format</span>
            <button
              onClick={copyForEvident}
              className="text-xs text-dental-primary hover:text-dental-primary-dark font-medium transition-colors"
            >
              {copiedAll ? 'Kopiert!' : 'Kopieren'}
            </button>
          </div>
          <p className="mt-1 text-sm font-mono text-gray-700 break-all">
            {getEvidentString()}
          </p>
        </div>
      )}

      {/* Billing Codes List */}
      <div className="space-y-2">
        {displayCodes.map((code) => {
          const isZusatz = code.is_zusatzleistung;
          const systemClass =
            isZusatz
              ? 'badge-zusatz'
              : code.system === 'GOZ'
              ? 'badge-goz'
              : 'badge-bema';

          return (
            <div
              key={code.id}
              className={`group flex items-center gap-3 p-3.5 rounded-xl border transition-all duration-150 ${
                code.selected
                  ? isZusatz
                    ? 'border-dental-zusatz/30 bg-dental-zusatz-light/30'
                    : code.system === 'GOZ'
                    ? 'border-dental-goz/30 bg-dental-goz-light/30'
                    : 'border-dental-bema/30 bg-dental-bema-light/30'
                  : 'border-gray-100 bg-white hover:bg-gray-50/50'
              }`}
            >
              <input
                type="checkbox"
                checked={code.selected}
                onChange={() => toggleCodeSelection(code.id)}
                className="w-4 h-4 rounded border-gray-300 text-dental-primary focus:ring-dental-primary/40 shrink-0"
              />

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className={systemClass}>
                    {isZusatz ? 'Zusatz' : code.system} {code.code}
                  </span>
                  {code.tooth_context && (
                    <span className="text-xs text-gray-500">
                      Zahn {code.tooth_context}
                    </span>
                  )}
                  {(code.quantity ?? 1) > 1 && (
                    <span className="text-xs text-gray-400">{code.quantity}x</span>
                  )}
                </div>
                <p className="text-sm text-gray-700 truncate">
                  {code.description || 'Keine Beschreibung'}
                </p>
              </div>

              {/* Copy single code button */}
              <button
                onClick={() => copySingleCode(code)}
                className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity btn-icon !p-1.5"
                title={`${code.code} kopieren`}
              >
                {copiedId === code.id ? (
                  <Check className="h-3.5 w-3.5 text-dental-success" />
                ) : (
                  <Copy className="h-3.5 w-3.5" />
                )}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
};
