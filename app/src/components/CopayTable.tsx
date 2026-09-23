// Mehrkosten-Tabelle (Zuzahlung und Kassenanteil je Zahn) – nur Anzeige, kopiert wird wie bisher.
import type { PositionKind, TransferPosition } from "../api";

const KIND_LABEL: Partial<Record<PositionKind, string>> = {
  kassenanteil: "Kassenanteil – Kasse zahlt",
  zuzahlung: "Zuzahlung – Patient zahlt",
};

type Props = { positions: TransferPosition[] };

export function CopayTable({ positions }: Props) {
  const extra = positions.filter((p) => KIND_LABEL[p.kind]);
  if (extra.length === 0) return null;
  return (
    <table className="copay-table">
      <caption>Mehrkosten – Vereinbarung mit dem Patienten nötig</caption>
      <thead>
        <tr>
          <th scope="col">Zahn</th>
          <th scope="col">Ziffer</th>
          <th scope="col">Art</th>
        </tr>
      </thead>
      <tbody>
        {extra.map((p) => (
          <tr key={`${p.tooth}-${p.code}`} className={`copay-${p.kind}`}>
            <td>{p.tooth ?? "ohne Zahn"}</td>
            <td className="mono">{p.code}</td>
            <td>{KIND_LABEL[p.kind]}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
