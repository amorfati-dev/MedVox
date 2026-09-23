// Wer diktiert: ganz oben in der Steuerung, groß genug, dass niemand zehn Minuten unter dem Namen
// eines Kollegen diktiert. Nicht bestätigt (nach der Übergabe oder einer langen Pause) bernsteinfarben
// mit der Frage „Wer diktiert jetzt?“; ein Tipp öffnet die Auswahl (DentistPicker).
import type { DentistChoice } from "../hooks/useDentist";
import { Icon } from "./Icon";

type Props = {
  choice: DentistChoice;
  onOpen: () => void;
  locked: boolean; // laufendes Diktat: der Behandler gilt bis zum Schluss
};

export function DentistBar({ choice, onOpen, locked }: Props) {
  const { current, unsure: ask } = choice;
  const name = current?.name ?? (ask ? "Behandler wählen" : "Ohne Behandler");
  const label = locked ? "Diktat von" : ask ? "Wer diktiert jetzt?" : "Es diktiert";
  return (
    <button
      type="button"
      className={ask ? "patient-bar dentist-bar dentist-ask" : "patient-bar dentist-bar"}
      onClick={onOpen}
      disabled={locked}
      aria-label={`${label} ${name} – Behandler wechseln`}
    >
      <Icon name="badge" />
      <span className="patient-text">
        <span className="patient-label">{label}</span>
        <span className="dentist-name">{name}</span>
      </span>
      <span className="patient-change">{ask ? "Wählen" : "Wechseln"}</span>
    </button>
  );
}
