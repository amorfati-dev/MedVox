import React, { useState, useMemo } from 'react';
import { Check, Plus, Download, Euro, FileText } from 'lucide-react';
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
  onAddManual
}) => {
  // Normalize and memoize billing codes directly from props
  const normalizedCodes = useMemo((): SelectedBillingCode[] => {
    const codes: SelectedBillingCode[] = [];

    // Extract codes from procedures
    procedures.forEach((procedure, procIndex) => {
      const procedureCodes = procedure.billing_codes || procedure.abrechnung || [];
      
      procedureCodes.forEach((code, codeIndex) => {
        codes.push({
          id: `proc-${procIndex}-${codeIndex}`,
          code: code.code,
          system: (code.system || code.code_system || 'BEMA') as 'BEMA' | 'GOZ',
          description: code.description || code.description_de || code.bezeichnung || code.leistungsbeschreibung,
          quantity: code.quantity || code.anzahl || 1,
          selected: true, // Auto-select detected codes
          procedure_context: procedure.procedure_name || procedure.procedure_description_de || procedure.prozedur,
          tooth_context: procedure.tooth || procedure.tooth_number || procedure.zahn
        });
      });
    });

    // Extract standalone billing codes
    billingCodes.forEach((code, index) => {
      codes.push({
        id: `standalone-${index}`,
        code: code.code,
        system: (code.system || code.code_system || 'BEMA') as 'BEMA' | 'GOZ',
        description: code.description || code.description_de || code.bezeichnung || code.leistungsbeschreibung,
        quantity: code.quantity || code.anzahl || 1,
        selected: true
      });
    });

    return codes;
  }, [procedures, billingCodes]);

  // Simple approach: use normalized codes directly for display, 
  // track selection state separately
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // Initialize all codes as selected when new data arrives
  React.useEffect(() => {
    const allIds = new Set(normalizedCodes.map(code => code.id));
    setSelectedIds(allIds);
  }, [normalizedCodes.length]); // Only trigger on length change to avoid loops

  // Combine normalized codes with selection state for display
  const displayCodes = normalizedCodes.map(code => ({
    ...code,
    selected: selectedIds.has(code.id)
  }));

  const toggleCodeSelection = (id: string) => {
    setSelectedIds(prev => {
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
    const allSelected = displayCodes.every(code => code.selected);
    if (allSelected) {
      setSelectedIds(new Set()); // Deselect all
    } else {
      setSelectedIds(new Set(displayCodes.map(code => code.id))); // Select all
    }
  };

  const handleExport = () => {
    const selected = displayCodes.filter(code => code.selected);
    onExport(selected);
  };

  const calculateTotal = () => {
    // This would need to be enhanced with actual BEMA/GOZ fee calculation
    return displayCodes.filter(code => code.selected).length * 25; // Placeholder
  };

  const selectedCount = displayCodes.filter(code => code.selected).length;
  const totalCodes = displayCodes.length;

  if (totalCodes === 0) {
    return (
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Euro className="h-5 w-5" />
            Abrechnungsziffern
          </h2>
        </div>
        <div className="text-center py-8 text-gray-500">
          <FileText className="h-12 w-12 mx-auto mb-3 opacity-50" />
          <p>Noch keine Abrechnungsziffern erkannt</p>
          <button 
            onClick={onAddManual}
            className="btn-primary mt-4 flex items-center gap-2 mx-auto"
          >
            <Plus className="h-4 w-4" />
            Manuell hinzufügen
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <Euro className="h-5 w-5" />
          Abrechnungsziffern
        </h2>
        <div className="text-right text-sm text-gray-600">
          Gesamt: <span className="font-semibold text-dental-success">€{calculateTotal().toFixed(2)}</span>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between mb-4 p-3 bg-gray-50 rounded-lg">
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={selectedCount === totalCodes}
              onChange={handleSelectAll}
              className="rounded border-gray-300 text-dental-primary focus:ring-dental-primary"
            />
            <span className="text-sm font-medium">
              Alle auswählen ({selectedCount}/{totalCodes})
            </span>
          </label>
        </div>
        
        <div className="flex gap-2">
          <button 
            onClick={onAddManual}
            className="btn-secondary flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            Hinzufügen
          </button>
          <button 
            onClick={handleExport}
            disabled={selectedCount === 0}
            className="btn-primary flex items-center gap-2 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            <Download className="h-4 w-4" />
            Export ({selectedCount})
          </button>
        </div>
      </div>

      {/* Billing Codes List */}
      <div className="space-y-3">
        {displayCodes.map((code) => (
          <div 
            key={code.id}
            className={`p-4 border rounded-lg transition-colors ${
              code.selected 
                ? 'border-dental-primary bg-blue-50' 
                : 'border-gray-200 bg-white'
            }`}
          >
            <div className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={code.selected}
                onChange={() => toggleCodeSelection(code.id)}
                className="mt-1 rounded border-gray-300 text-dental-primary focus:ring-dental-primary"
              />
              
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 mb-2">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-dental-primary text-white">
                    {code.system || 'BEMA'} {code.code}
                  </span>
                  {code.tooth_context && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-800">
                      Zahn {code.tooth_context}
                    </span>
                  )}
                  <span className="text-xs text-gray-500">
                    {code.quantity || 1}x
                  </span>
                </div>
                
                <p className="text-sm font-medium text-gray-900">
                  {code.description || 'Keine Beschreibung verfügbar'}
                </p>
                
                {code.procedure_context && (
                  <p className="text-xs text-gray-600 mt-1">
                    Kontext: {code.procedure_context}
                  </p>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}; 