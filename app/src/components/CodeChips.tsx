// Abrechnungsziffern als abwählbare Chips. Abgewählte Chips bleiben sichtbar,
// zählen aber nicht mehr zum Kopier-/Übergabeergebnis.
type Props = {
  all: string[]; // alle vorgeschlagenen Ziffern
  active: string[]; // aktuell ausgewählte
  onToggle: (code: string) => void;
};

export function CodeChips({ all, active, onToggle }: Props) {
  if (all.length === 0) {
    return <p className="muted">Noch keine Ziffern-Vorschläge (Extraktor folgt).</p>;
  }
  return (
    <ul className="chips" aria-label="Abrechnungsziffern">
      {all.map((code) => {
        const on = active.includes(code);
        return (
          <li key={code}>
            <button
              type="button"
              className={on ? "chip chip-active" : "chip"}
              aria-pressed={on}
              onClick={() => onToggle(code)}
            >
              {code}
            </button>
          </li>
        );
      })}
    </ul>
  );
}
