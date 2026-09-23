// Nachfrage, bevor eine Nummer das Diktat „ohne Patient“ auf dem Bildschirm bekommt: nie still
// zuordnen, damit kein Diktat beim falschen Patienten landet (pickAction in patients.ts).
import { useEffect } from "react";
import { patientName } from "../patients";

type Props = {
  number: string;
  label: string | null; // Kürzel, in der Frage hinter der Nummer
  onAssign: () => void; // Diktat auf dem Bildschirm diesem Patienten zuordnen
  onNew: () => void; // Diktat bleibt „ohne Patient“ gespeichert, neues Diktat für diesen Patienten
  onCancel: () => void;
};

export function AssignDialog({ number: bare, label, onAssign, onNew, onCancel }: Props) {
  const number = patientName(bare, label);
  useEffect(() => {
    const onKey = (ev: KeyboardEvent) => {
      if (ev.key === "Escape") onCancel();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onCancel]);

  return (
    <div className="picker-backdrop">
      <section className="picker assign" role="alertdialog" aria-modal="true" aria-labelledby="assign-title">
        <h2 id="assign-title">Das Diktat auf dem Bildschirm Patient {number} zuordnen?</h2>
        <p className="muted">Es wurde ohne Patient aufgenommen. Nur zuordnen, wenn es wirklich von Patient {number} ist.</p>
        <div className="assign-actions">
          <button type="button" className="btn btn-primary btn-block" onClick={onAssign}>
            Ja, Patient {number} zuordnen
          </button>
          <button type="button" className="btn btn-block" onClick={onNew}>
            Nein, neues Diktat für {number}
          </button>
          <button type="button" className="btn btn-quiet btn-block" onClick={onCancel}>
            Abbrechen
          </button>
        </div>
      </section>
    </div>
  );
}
