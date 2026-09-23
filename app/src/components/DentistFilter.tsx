// Büro: Filter nach Behandler über der Patientenliste. Voreinstellung „Alle“ – der Filter ist eine
// Bequemlichkeit, keine Schranke: jeder sieht alle Patienten, Kopieraktionen bleiben unverändert.
import type { DentistRef } from "../api";

type Props = {
  choices: DentistRef[];
  value: number | null; // null = alle
  onChange: (value: number | null) => void;
};

export function DentistFilter({ choices, value, onChange }: Props) {
  if (choices.length < 2 && value === null) return null; // ein Behandler: nichts zu filtern
  const option = (id: number | null, label: string) => (
    <button key={id ?? "alle"} type="button" className="btn" aria-pressed={value === id} onClick={() => onChange(id)}>
      {label}
    </button>
  );
  return (
    <div className="dentist-filter" role="group" aria-label="Nach Behandler filtern">
      <span className="dentist-filter-label">Behandler</span>
      {option(null, "Alle")}
      {choices.map((d) => option(d.id, d.name))}
    </div>
  );
}
