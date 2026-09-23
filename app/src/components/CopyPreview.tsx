// Kopiertext für Evident unter der Ergebnisliste: genau die Zeilen, die „Ziffern kopieren“ liefert, eine
// je Zahn zum zeilenweisen Einfügen. Beim Kassenpatienten beschriftet nach Kassen- und Privatblock (der
// Privatblock steht zuletzt), dazu je Block eine eigene Kopieraktion.
import { evidentText, type EvidentBlocks } from "../api";
import { CopyButton } from "./CopyButton";
import { EvidentLines } from "./EvidentLines";

type Props = { blocks: EvidentBlocks; kasse: boolean };

export function CopyPreview({ blocks, kasse }: Props) {
  if (blocks.kasse.length + blocks.privat.length === 0) return null;
  return (
    <section className="copy-preview">
      <h2 className="list-title">Kopiertext für Evident – Zeile für Zeile einfügen</h2>
      <EvidentLines blocks={blocks} labelled={kasse} />
      {kasse && (
        <div className="copy-preview-actions">
          <CopyButton label="Kassenleistungen kopieren" text={evidentText(blocks.kasse)} />
          <CopyButton label="Privatleistungen kopieren" text={evidentText(blocks.privat)} />
        </div>
      )}
    </section>
  );
}
