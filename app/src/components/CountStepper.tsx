// Knöpfe − Anzahl + an einer mengenweise berechneten Zeile (je Kanal, mehrmals je Sitzung) oder
// übernommenen Zuzahlungs-Option, nur am iPad.
// Nie unter 1 – weg fällt eine Zeile nur über die Abwahl; nie über die bestätigte Höchstzahl (`max`).
import type { Suggestion } from "../api";
import { Icon } from "./Icon";

type Props = { s: Suggestion; count: number; max: number | null; onSet: (s: Suggestion, count: number) => void };

export function CountStepper({ s, count, max, onSet }: Props) {
  const where = s.teeth.length > 0 ? ` an Zahn ${s.teeth[0]}` : "";
  return (
    <div className="stepper" role="group" aria-label={`Anzahl ${s.system} ${s.code}${where}`}>
      <button type="button" className="step" aria-label={`${s.code} eins weniger`} disabled={count <= 1} onClick={() => onSet(s, count - 1)}>
        <Icon name="minus" />
      </button>
      <output className="step-count" aria-live="polite">
        {count}×
      </output>
      <button
        type="button"
        className="step"
        aria-label={`${s.code} eins mehr${max !== null && count >= max ? ` – höchstens ${max}` : ""}`}
        disabled={max !== null && count >= max}
        onClick={() => onSet(s, count + 1)}
      >
        <Icon name="plus" />
      </button>
    </div>
  );
}
