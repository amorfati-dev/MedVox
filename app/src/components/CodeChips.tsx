// Abrechnungsziffern als abwählbare Chips. Abgewählte Chips bleiben sichtbar,
// zählen aber nicht mehr zum Kopier-/Übergabeergebnis.
type Props = {
  all: string[]; // alle vorgeschlagenen Ziffern
  selected: string[]; // aktuell ausgewählte
  onChange: (selected: string[]) => void;
};

export function CodeChips({ all, selected, onChange }: Props) {
  if (all.length === 0) {
    return <p className="muted">Noch keine Ziffern-Vorschläge (Extraktor folgt).</p>;
  }
  const toggle = (code: string) => {
    onChange(selected.includes(code) ? selected.filter((c) => c !== code) : all.filter((c) => c === code || selected.includes(c)));
  };
  return (
    <ul className="chips" aria-label="Abrechnungsziffern">
      {all.map((code) => {
        const active = selected.includes(code);
        return (
          <li key={code}>
            <button
              type="button"
              className={active ? "chip chip-active" : "chip"}
              aria-pressed={active}
              onClick={() => toggle(code)}
            >
              {code}
            </button>
          </li>
        );
      })}
    </ul>
  );
}
