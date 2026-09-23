// Ergebnis rechts: Kopfzeile (Patiententyp, Zählungen, „Nur Ziffern“), je Zahn ein Block mit der
// kopierten Evident-Zeile, dann „Geplant – wird nicht abgerechnet“ und „Hinweise“.
import type { PatientType, Suggestion } from "../api";
import type { Counts, Group } from "../result";
import { plural } from "../status";
import { CopyButton } from "./CopyButton";
import { Icon } from "./Icon";
import { PATIENT_LABEL } from "./PatientSwitch";
import { FrameRows, OptionRow, ResultRow } from "./ResultRow";

type HeadProps = {
  counts: Counts;
  resultType: PatientType | null;
  numbersText: string; // „Nur Ziffern“: dieselben Zeilen mit amtlichen Ziffern
};

// Kopfzeile über Transkript und Liste: Patiententyp-Etikett, Zählungen, „Nur Ziffern“.
export function ResultHead({ counts, resultType, numbersText }: HeadProps) {
  return (
    <header className="result-head">
      {resultType && <span className={`badge badge-${resultType}`}>{PATIENT_LABEL[resultType]}</span>}
      <span className="counts">
        {plural(counts.positions, "Ziffer", "Ziffern")}
        {counts.options > 0 && ` · ${plural(counts.options, "Option", "Optionen")}`}
        {counts.check > 0 && (
          <span className="counts-check">
            {" · "}
            <Icon name="warn" /> {counts.check} prüfen
          </span>
        )}
        {counts.planned > 0 && ` · ${counts.planned} geplant`}
      </span>
      <CopyButton label="Nur Ziffern" text={numbersText} />
    </header>
  );
}

type Props = {
  groups: Group[];
  planned: Suggestion[]; // schon ohne Wiederholungen (uniquePlanned)
  notes: string[];
  onToggle: (code: string) => void;
  onAdopt: (key: string) => void;
};

export function ResultList({ groups, planned: plans, notes, onToggle, onAdopt }: Props) {
  if (groups.length === 0 && plans.length === 0 && notes.length === 0) {
    return <p className="muted empty">Noch keine Ziffern-Vorschläge.</p>;
  }
  return (
    <>
      {groups.length > 0 && <h2 className="list-title">Abrechnen</h2>}
      {groups.map((g) => (
        <section key={g.tooth ?? "ohne"} className={g.tooth === null ? "tooth tooth-none" : "tooth"}>
          <header className="tooth-head">
            <h3>{g.tooth === null ? "Ohne Zahn – in Evident manuell eintragen" : `Zahn ${g.tooth}`}</h3>
            <code className="tooth-line">{g.line ?? "nichts ausgewählt"}</code>
          </header>
          <ul className="rows">
            {g.items.map((item) =>
              "row" in item ? (
                <ResultRow key={item.row.key} row={item.row} onToggle={onToggle} onAdopt={onAdopt} />
              ) : "frame" in item ? (
                <FrameRows key={item.frame.key} frame={item.frame} tooth={g.tooth} onToggle={onToggle} onAdopt={onAdopt} />
              ) : (
                <OptionRow key={item.option.key} option={item.option} onAdopt={onAdopt} />
              ),
            )}
          </ul>
        </section>
      ))}

      {plans.length > 0 && (
        <section className="planned">
          <h2 className="list-title">Geplant – wird nicht abgerechnet</h2>
          <ul className="rows">
            {plans.map((s) => (
              <li key={`${s.code}@${s.teeth.join("+")}`} className="row row-planned">
                <div className="row-main">
                  <span className="box box-plan" aria-hidden="true">
                    <Icon name="calendar" />
                  </span>
                  <span className="row-code">{s.code}</span>
                  <span className="row-body">
                    <span className="row-title">
                      {s.title} <span className="row-tag">{s.system}</span>
                    </span>
                    {s.teeth.length > 0 && <span className="row-meta">Zahn {s.teeth.join(", ")}</span>}
                    <span className="row-reason">{s.reason}</span>
                  </span>
                </div>
                {s.decide.map((text) => (
                  <p key={text} className="check-strip">
                    <Icon name="warn" />
                    <span>{text}</span>
                  </p>
                ))}
              </li>
            ))}
          </ul>
        </section>
      )}

      {notes.length > 0 && (
        <section className="notes">
          <h2 className="list-title">Hinweise</h2>
          <ul>
            {notes.map((n) => (
              <li key={n}>
                <Icon name="info" />
                <span>{n}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}
