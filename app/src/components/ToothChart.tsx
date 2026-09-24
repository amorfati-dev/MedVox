// Zahnschema, nur Anzeige: am iPad eine Karte mit Umschalter Ober-/Unterkiefer (je Kieferhälfte eine Reihe,
// 8 Zähne von der Mitte aus, ≥ 64 px), Legende, Befundliste und „Befund kopieren“; im Büro beide Kiefer
// klein nebeneinander (`ToothChartMini`). Zähne werden im Blatt „Zähne antippen“ gewählt (ToothTapSheet).
import { useMemo, useState } from "react";
import { chartMarks, findingText, type FindingRow, type Mark } from "../findings";
import { plural } from "../status";
import { chartRows, jawOf, type Jaw } from "../teeth";
import { CopyButton } from "./CopyButton";
import { FindingList } from "./FindingList";

export const JAW_LABEL: Record<Jaw, string> = { ok: "Oberkiefer", uk: "Unterkiefer" };
const TONE: Record<Mark["tone"], string> = { kasse: "tk-kasse", privat: "tk-privat", plan: "tk-plan", find: "tk-find" };

function keyClass(mark: Mark | undefined): string {
  return mark ? `tk ${TONE[mark.tone]}${mark.check ? " tk-check" : ""}` : "tk tk-none";
}

export function jawCounts(teeth: Iterable<number>): Record<Jaw, number> {
  const counts = { ok: 0, uk: 0 };
  for (const t of teeth) counts[jawOf(t)] += 1;
  return counts;
}

type SwitchProps = { jaw: Jaw; counts: Record<Jaw, number>; onChange: (jaw: Jaw) => void };

// Umschalter wie Kasse/Privat (PatientSwitch), mit der Zahl markierter Zähne je Kiefer.
export function JawSwitch({ jaw, counts, onChange }: SwitchProps) {
  return (
    <div className="switch jaw-switch" role="radiogroup" aria-label="Kiefer">
      {(["ok", "uk"] as const).map((j) => (
        <button
          key={j}
          type="button"
          role="radio"
          aria-checked={j === jaw}
          className={j === jaw ? "switch-option switch-on switch-jaw" : "switch-option"}
          onClick={() => onChange(j)}
        >
          {JAW_LABEL[j]}
          <small>· {counts[j]}</small>
        </button>
      ))}
    </div>
  );
}

function Rows({ jaw, marks }: { jaw: Jaw; marks: Map<number, Mark> }) {
  return (
    <div className="tq-rows">
      {chartRows(jaw, marks.keys()).map((r) => (
        <div key={r.quadrant} className="tq">
          <span className="tq-label">{r.label}</span>
          {r.teeth.map((t) => {
            const m = marks.get(t);
            return (
              <span key={t} className={keyClass(m)} aria-label={m ? `Zahn ${t}${m.label ? `, ${m.label}` : ""}${m.check ? ", prüfen" : ""}` : undefined}>
                <b>{t}</b>
                {m?.label && <small>{m.label}</small>}
              </span>
            );
          })}
        </div>
      ))}
    </div>
  );
}

const LEGEND = (
  <p className="tchart-legend">
    <span>
      <i className="lg-kasse" />
      Kasse
    </span>
    <span>
      <i className="lg-privat" />
      Privat/Zuzahlung
    </span>
    <span>
      <i className="lg-plan" />
      geplant
    </span>
    <span>
      <i className="lg-check" />
      prüfen
    </span>
  </p>
);

// iPad: zwischen Transkript und „Abrechnen“; es öffnet der Kiefer des ersten Zahns.
export function ToothChart({ rows }: { rows: FindingRow[] }) {
  const marks = useMemo(() => chartMarks(rows), [rows]);
  const [chosen, setJaw] = useState<Jaw | null>(null);
  const first = marks.keys().next();
  if (first.done) return null;
  const jaw = chosen ?? jawOf(first.value);
  return (
    <section className="tchart" aria-label="Zahnschema">
      <div className="box-head">
        <h2>Zahnschema · {plural(marks.size, "Zahn", "Zähne")}</h2>
        <CopyButton label="Befund kopieren" text={findingText(rows)} />
      </div>
      <JawSwitch jaw={jaw} counts={jawCounts(marks.keys())} onChange={setJaw} />
      <Rows jaw={jaw} marks={marks} />
      {LEGEND}
      <FindingList rows={rows} />
    </section>
  );
}

// Büro: beide Kiefer klein nebeneinander, dazu die Befundliste; „Befund kopieren“ steht bei den Kopierknöpfen.
export function ToothChartMini({ rows }: { rows: FindingRow[] }) {
  const marks = useMemo(() => {
    const all = chartMarks(rows);
    return new Map([...all].map(([t, m]) => [t, { ...m, label: "" }]));
  }, [rows]);
  if (marks.size === 0) return null;
  return (
    <>
      <h2>Zahnschema</h2>
      <div className="tchart-mini">
        {(["ok", "uk"] as const).map((j) => (
          <div key={j}>
            <h4>{JAW_LABEL[j]}</h4>
            <Rows jaw={j} marks={marks} />
          </div>
        ))}
      </div>
      <FindingList rows={rows} />
    </>
  );
}
