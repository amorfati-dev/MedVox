// Aktiver Patient oben in der Steuerung: Evident-Nummer groß, „ohne Patient“ bernsteinfarben.
// Ein Tipp öffnet die Auswahl (Tastenfeld und offene Patienten). Darunter, ob das Diktat auf dem
// Praxis-Mac gespeichert ist.
import type { DictationSave } from "../hooks/useDictationSave";
import { plural } from "../status";
import { Icon } from "./Icon";

type Props = {
  number: string | null;
  onOpen: () => void;
  locked: boolean; // laufendes Diktat mit Patient: Wechsel erst danach
  save: DictationSave;
};

const SAVE_TEXT = {
  speichert: "Wird gespeichert …",
  gespeichert: "Gespeichert – im Büro unter „Patienten“",
  fehler: "Noch nicht gespeichert – wird wiederholt",
} as const;

export function PatientBar({ number, onOpen, locked, save }: Props) {
  return (
    <div className="patient">
      <button
        type="button"
        className={number ? "patient-bar" : "patient-bar patient-none"}
        onClick={onOpen}
        disabled={locked}
        aria-label={number ? `Patient ${number} – wechseln` : "Ohne Patient – Patientennummer eingeben"}
      >
        <Icon name="user" />
        <span className="patient-text">
          <span className="patient-label">{number ? "Patient" : "Ohne Patient"}</span>
          <span className="patient-number">{number ?? "Nummer eingeben"}</span>
        </span>
        <span className="patient-change">{number ? "Wechseln" : "Eingeben"}</span>
      </button>
      {locked && <p className="switch-hint">Der Patient gilt für das ganze laufende Diktat.</p>}
      {save.state !== "aus" && (
        <p className={`patient-save patient-save-${save.state}`} role="status">
          <Icon name={save.state === "gespeichert" ? "check" : save.state === "fehler" ? "warn" : "spinner"} />
          <span>
            {SAVE_TEXT[save.state]}
            {save.state === "fehler" && save.error ? ` (${save.error})` : ""}
          </span>
        </p>
      )}
      {save.backlog > 0 && (
        <p className={save.error ? "patient-save patient-save-fehler" : "patient-save"} role="status">
          <Icon name={save.error ? "warn" : "spinner"} />
          <span>
            {plural(save.backlog, "früheres Diktat", "frühere Diktate")}{" "}
            {save.error ? "noch nicht gespeichert – wird wiederholt" : "wird gespeichert …"}
          </span>
        </p>
      )}
    </div>
  );
}
