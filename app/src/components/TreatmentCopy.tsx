// Je Behandlung (Zahn, zuletzt ohne Zahn) eine eigene Kopieraktion – nur, wenn das Diktat mehr als eine
// Behandlung hat. Beim Kassenpatienten (`labelled`) Kassen- und Privatzeile eines Zahns getrennt, ebenso
// immer dann, wenn ein Zahn beides hat (Evident setzt nach einer Privatposition alles Folgende auf privat).
// Kopiert werden genau die Zeilen dieses Zahns aus dem Gesamttext (treatments.ts).
import { evidentText, type EvidentBlocks } from "../api";
import { treatmentLabel, treatments } from "../treatments";
import { CopyButton } from "./CopyButton";

type Props = { blocks: EvidentBlocks; labelled: boolean };

export function TreatmentCopy({ blocks, labelled }: Props) {
  const list = treatments(blocks);
  if (list.length < 2) return null;
  return (
    <>
      <h3 className="codes-label">Je Behandlung kopieren</h3>
      <div className="actions">
        {list.flatMap((t) => {
          const key = t.tooth ?? "-";
          if (!labelled && (t.kasse.length === 0 || t.privat.length === 0)) {
            const lines = [...t.kasse, ...t.privat];
            return [<CopyButton key={key} label={treatmentLabel(t.tooth, null)} text={evidentText(lines)} />];
          }
          return (["kasse", "privat"] as const)
            .filter((block) => t[block].length > 0)
            .map((block) => (
              <CopyButton key={`${key}-${block}`} label={treatmentLabel(t.tooth, block)} text={evidentText(t[block])} />
            ));
        })}
      </div>
    </>
  );
}
