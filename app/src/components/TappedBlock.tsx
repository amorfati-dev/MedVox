// Sammelblock der Ergebnisliste für im Zahnschema angetippte Zähne („Zahnsteinentfernung je Zahn · 26 Zähne
// angetippt“): je Ziffer eine Zeile mit Anzahl und Zähnen, statt je Zahn ein eigener Block. Die Evident-Zeile
// je Zahn bleibt unverändert (Kopfzeile der Zahnblöcke, Kopiertext). Angetippte Zeilen werden immer kopiert;
// ändern nur über „Zähne ändern“, Rückgängig über den Streifen.
import type { Collected } from "../teeth";
import { plural } from "../status";
import { Icon } from "./Icon";
import { TapButton } from "./ResultRow";

type Props = { block: Collected; tapCodes?: (code: string) => string[] | null; onTap?: (code: string) => void };

export function TappedBlock({ block, tapCodes, onTap }: Props) {
  const first = block.rows[0].row.s;
  const codes = onTap && tapCodes?.(first.code);
  return (
    <section className="tooth">
      <header className="tooth-head">
        <h3>
          {block.label} je Zahn · {plural(block.teeth, "Zahn", "Zähne")} angetippt
        </h3>
        <span className="tooth-lines">
          <code className="tooth-line">{block.rows.map((r) => `${r.row.s.code} × ${r.teeth.length}`).join(" · ")}</code>
        </span>
      </header>
      <ul className="rows">
        {block.rows.map(({ row, teeth }) => (
          <li key={row.s.code} className={`row row-${row.tag}`}>
            <div className="row-main" aria-label={`${row.s.system} ${row.s.code}, ${teeth.length}-mal, ${row.s.title}, Zähne ${teeth.join(", ")}`}>
              <span className="box" aria-hidden="true">
                <Icon name="check" />
              </span>
              <span className="row-code">
                {row.s.code}
                {teeth.length > 1 && <span className="row-count">{teeth.length}×</span>}
              </span>
              <span className="row-body">
                <span className="row-title">
                  {row.s.title} <span className="row-tag">{row.s.system}</span>
                  <span className="row-tag tag-hand">Zähne angetippt</span>
                </span>
                <span className="tooth-teeth">Zahn {teeth.join(", ")}</span>
              </span>
            </div>
          </li>
        ))}
      </ul>
      {codes && onTap && (
        <TapButton codes={codes} kind={first.kind} label={`Zähne ändern · ${block.teeth} angetippt`} onTap={() => onTap(first.code)} />
      )}
    </section>
  );
}
