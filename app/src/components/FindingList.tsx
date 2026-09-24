// Befundliste unter dem Zahnschema: je Zahn Flächen, Befund und die kopierten Leistungen („36 · mod ·
// Karies profunda → Kompositfüllung … 2100“), angetippte Positionen gesammelt in einer Zeile je Leistung.
// Nur Anzeige; „Befund kopieren“ liefert dieselben Angaben mit einer Zeile je Zahn (findings.ts).
import { Fragment } from "react";
import { shownFindings, type FindingRow, type Item } from "../findings";

function Codes({ items }: { items: Item[] }) {
  return items.map((i, n) => (
    <Fragment key={i.code}>
      {n > 0 && ", "}
      {i.title} <code className={i.kind === "bema" ? "kasse" : undefined}>{i.count > 1 ? `${i.count}× ${i.code}` : i.code}</code>
    </Fragment>
  ));
}

export function FindingList({ rows }: { rows: FindingRow[] }) {
  const { rows: shown, tapped } = shownFindings(rows);
  if (shown.length === 0 && tapped.length === 0) return null;
  return (
    <ul className="finding-list" aria-label="Befunde je Zahn">
      {shown.map((r) => (
        <li key={r.tooth ?? "ohne"} className="finding">
          <span className="ft">{r.tooth ?? "–"}</span>
          <span className="fs">{r.surfaces || "–"}</span>
          <span>
            {r.findings.length > 0 && <span className="fb">{r.findings.join(", ")} </span>}
            {r.done.length > 0 && (
              <span className="fl">
                → <Codes items={r.done} />
              </span>
            )}
            {r.planned.length > 0 && (
              <span className="fl">
                {" "}
                geplant: <Codes items={r.planned} />
              </span>
            )}
          </span>
        </li>
      ))}
      {tapped.map((t) => (
        <li key={t.label} className="finding">
          <span className="ft" />
          <span className="fs" />
          <span>
            <span className="fb">{t.label} </span>
            <span className="fl">
              →{" "}
              {t.parts.map((p, n) => (
                <Fragment key={p.code}>
                  {n > 0 && " · "}
                  <code className={p.kind === "bema" ? "kasse" : undefined}>{p.code}</code> an {p.teeth}
                </Fragment>
              ))}
            </span>
          </span>
        </li>
      ))}
    </ul>
  );
}
