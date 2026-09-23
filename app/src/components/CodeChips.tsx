// Abrechnungsziffern als abwählbare Chips. Abgewählte Chips bleiben sichtbar,
// zählen aber nicht mehr zum Kopier-/Übergabeergebnis. Zuzahlungen (Privatleistung
// beim Kassenpatienten) sind farblich abgesetzt und beschriftet. Neben der Ziffer steht leiser
// die Evident-Kurzform, wenn der Katalog eine kennt ("41a · l1").
import { codeOf, type SuggestionKind } from "../api";

type Props = {
  all: string[]; // alle vorgeschlagenen Ziffern im Kopierformat ("2x 41a")
  active: string[]; // aktuell ausgewählte
  kinds: Record<string, SuggestionKind>; // Art je Ziffer (ohne Anzahl)
  forms: Record<string, string>; // Evident-Kurzform je Ziffer (ohne Anzahl)
  onToggle: (code: string) => void;
};

export function CodeChips({ all, active, kinds, forms, onToggle }: Props) {
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
          const short = forms[codeOf(code)];
          const classes = ["chip", on ? "chip-active" : "", extra ? "chip-zuzahlung" : ""].filter(Boolean);
          return (
            <li key={code}>
              <button
                type="button"
                className={classes.join(" ")}
                aria-pressed={on}
                aria-label={[code, short && `Evident ${short}`, extra && "Zuzahlung"].filter(Boolean).join(", ")}
                onClick={() => onToggle(code)}
              >
                {code}
                {short && <span className="chip-short"> · {short}</span>}
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
