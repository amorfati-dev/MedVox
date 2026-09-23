// Zweiwege-Schalter Kassenpatient / Privatpatient: wählt je Leistung BEMA (plus Zuzahlung) oder GOZ/GOÄ.
import type { PatientType } from "../api";

export const PATIENT_LABEL: Record<PatientType, string> = { kasse: "Kassenpatient", privat: "Privatpatient" };
const OPTIONS: PatientType[] = ["kasse", "privat"];

type Props = { value: PatientType; onChange: (type: PatientType) => void; disabled: boolean };

export function PatientSwitch({ value, onChange, disabled }: Props) {
  return (
    <div className="switch" role="radiogroup" aria-label="Patiententyp">
      {OPTIONS.map((type) => (
        <button
          key={type}
          type="button"
          role="radio"
          aria-checked={value === type}
          className={value === type ? `switch-option switch-on switch-${type}` : "switch-option"}
          disabled={disabled}
          onClick={() => onChange(type)}
        >
          {PATIENT_LABEL[type]}
        </button>
      ))}
    </div>
  );
}
