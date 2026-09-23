// Anzeige der Evident-Zeilen (eine je Zahn); die Zeile ohne Zahn trägt einen Hinweis.
import { isToothless } from "../api";

type Props = { lines: string[] };

export function EvidentLines({ lines }: Props) {
  if (lines.length === 0) return <p className="codes-line muted">keine</p>;
  return (
    <ul className="codes-lines">
      {lines.map((line) =>
        isToothless(line) ? (
          <li key={line}>
            {line.slice(1)} <span className="toothless-hint">ohne Zahn – in Evident manuell eintragen</span>
          </li>
        ) : (
          <li key={line}>{line}</li>
        ),
      )}
    </ul>
  );
}
