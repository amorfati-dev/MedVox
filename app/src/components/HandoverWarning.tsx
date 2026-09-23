// Warnung, wenn ein Stand dieses Diktats schon per Kurzcode an der Rezeption abgeholt wurde:
// wann, was damals übergeben wurde und was seitdem neu ist (handoverDiff) – nie still doppelt eintragen.
import type { Handover } from "../api";
import { handoverDiff } from "../handover";
import { clock } from "../patients";
import { EvidentLines } from "./EvidentLines";

type Props = { earlier: Handover[]; current: string[] };

export function HandoverWarning({ earlier, current }: Props) {
  if (earlier.length === 0) return null;
  const diff = handoverDiff(current, earlier);
  return (
    <div className="handed-over" role="alert">
      <p>
        <strong>Schon an der Rezeption abgeholt</strong> – ein früherer Stand dieses Diktats wurde per Kurzcode
        übergeben. Nicht noch einmal komplett in Evident eintragen, nur die Änderung.
      </p>
      {earlier.map((h) => (
        <div key={h.fetched_at}>
          <p>Abgeholt um {clock(h.fetched_at)} Uhr:</p>
          <EvidentLines lines={h.codes} />
        </div>
      ))}
      <p>Neu seitdem:</p>
      <EvidentLines lines={diff.added} />
      {diff.changed.length > 0 && (
        <>
          <p>Anzahl geändert:</p>
          <ul className="codes-lines">
            {diff.changed.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </>
      )}
      {diff.removed.length > 0 && (
        <>
          <p>Abgeholt, aber nicht mehr im Diktat – in Evident prüfen:</p>
          <EvidentLines lines={diff.removed} />
        </>
      )}
    </div>
  );
}
