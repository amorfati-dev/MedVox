// Abrechnungsziffern als abwählbare Chips. Abgewählte Chips bleiben sichtbar,
// zählen aber nicht mehr zum Kopier-/Übergabeergebnis. Zuzahlungen (Privatleistung
// beim Kassenpatienten) sind farblich abgesetzt und beschriftet.
import { codeOf, type SuggestionKind } from "../api";

type Props = {
  all: string[]; // alle vorgeschlagenen Ziffern im Kopierformat ("2x 41a")
  active: string[]; // aktuell ausgewählte
  kinds: Record<string, SuggestionKind>; // Art je Ziffer (ohne Anzahl)
  onToggle: (code: string) => void;
};

export function CodeChips({ all, active, kinds, onToggle }: Props) {
  if (all.length === 0) {
    return <p className="muted">Noch keine Ziffern-Vorschläge.</p>;
  }
  const coPayment = (code: string) => kinds[codeOf(code)] === "zuzahlung";
  return (
    <>
      <ul className="chips" aria-label="Abrechnungsziffern">
        {all.map((code) => {
          const on = active.includes(code);
          const extra = coPayment(code);
          const classes = ["chip", on ? "chip-active" : "", extra ? "chip-zuzahlung" : ""].filter(Boolean);
          return (
            <li key={code}>
              <button
                type="button"
                className={classes.join(" ")}
                aria-pressed={on}
                aria-label={extra ? `${code}, Zuzahlung` : code}
                onClick={() => onToggle(code)}
              >
                {code}
                {extra && <span className="chip-tag">Zuzahlung</span>}
              </button>
            </li>
          );
        })}
      </ul>
      {all.some(coPayment) && (
        <p className="muted legend">Zuzahlung: Privatleistung des Kassenpatienten – nur mit Vereinbarung abrechnen.</p>
      )}
    </>
  );
}
