// Anzeige der Evident-Zeilen so, wie sie kopiert werden: eine je Zahn, in dieser Reihenfolge; die Zeile
// ohne Zahn trägt einen Hinweis. Beim Kassenpatienten (`labelled`) stehen Kassen- und Privatblock
// getrennt und beschriftet – Evident setzt nach einer Privatposition alles Folgende auf privat, deshalb
// kommt der Privatblock zuletzt.
import { isToothless, type EvidentBlocks } from "../api";

type Props = { blocks: EvidentBlocks; labelled?: boolean };

export function EvidentLines({ blocks, labelled = false }: Props) {
  const { kasse, privat } = blocks;
  if (kasse.length + privat.length === 0) return <p className="codes-line muted">keine</p>;
  if (!labelled) return <Lines lines={[...kasse, ...privat]} />;
  return (
    <>
      {kasse.length > 0 && (
        <>
          <h3 className="codes-label codes-label-kasse">Kassenleistungen</h3>
          <Lines lines={kasse} />
        </>
      )}
      {privat.length > 0 && (
        <>
          <h3 className="codes-label codes-label-privat">Privatleistungen – immer zuletzt einfügen</h3>
          <Lines lines={privat} />
        </>
      )}
    </>
  );
}

function Lines({ lines }: { lines: string[] }) {
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
