// Ergebnis rechts: Kopfzeile (Patiententyp, Zählungen, „Nur Ziffern“), je Zahn ein Block mit der
// kopierten Evident-Zeile, dann „Geplant – wird nicht abgerechnet“ und „Hinweise“. Am Fuß jedes Zahnblocks
// und unter der Liste öffnet sich das Katalog-Blatt (Ziffer ändern oder ergänzen), sofern `onEdit` da ist.
import type { PatientType, Suggestion } from "../api";
import type { Counter } from "../hooks/useCorrection";
import type { Counts, Group } from "../result";
import { plural } from "../status";
import { CopyButton } from "./CopyButton";
import { Icon } from "./Icon";
import { PATIENT_LABEL } from "./PatientSwitch";
import { collectTapped } from "../teeth";
import { FrameRows, OptionRow, ResultRow } from "./ResultRow";
import { TappedBlock } from "./TappedBlock";

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
  onEdit?: (tooth: number | undefined) => void; // Katalog-Blatt: an diesem Zahn, undefined = Zahn erst wählen
  onRemove?: (s: Suggestion) => void; // Zeile „von Hand“ entfernen
  tapCodes?: (code: string) => string[] | null; // Je-Zahn-Position: Ziffern fürs Antippen
  onTap?: (code: string) => void; // Blatt „Zähne antippen“ öffnen
  counter?: Counter | null; // Anzahl mit − / + ändern
};

export function ResultList({ groups: all, planned: plans, notes, onToggle, onAdopt, onEdit, onRemove, tapCodes, onTap, counter }: Props) {
  const { groups, collected } = collectTapped(all);
  // „Zähne antippen“ einmal je Position: an ihrer ersten Zeile (meist der ohne Zahn); schon angetippte
  // Positionen ändert der Sammelblock („Zähne ändern“).
  const pairOf = (code: string) => tapCodes?.(code)?.join("/") ?? null;
  const seen = new Set(collected.flatMap((b) => b.rows.map((r) => pairOf(r.row.s.code))));
  const tapAt = new Set<string>();
  for (const item of groups.flatMap((g) => g.items)) {
    const pair = "row" in item ? pairOf(item.row.s.code) : null;
    if (pair === null || !("row" in item) || seen.has(pair)) continue;
    seen.add(pair);
    tapAt.add(item.row.key);
  }
  const elsewhere = onEdit && (
    <button type="button" className="list-add" onClick={() => onEdit(undefined)}>
      <Icon name="plus" />
      Ziffer ohne Zahn oder an anderem Zahn
    </button>
  );
  if (all.length === 0 && plans.length === 0 && notes.length === 0) {
    return (
      <>
        <p className="muted empty">Noch keine Ziffern-Vorschläge.</p>
        {elsewhere}
      </>
    );
  }
  return (
    <>
      {all.length > 0 && <h2 className="list-title">Abrechnen</h2>}
      {groups.map((g) => (
        <section key={g.tooth ?? "ohne"} className={g.tooth === null ? "tooth tooth-none" : "tooth"}>
          <header className="tooth-head">
            <h3>{g.tooth === null ? "Ohne Zahn – in Evident manuell eintragen" : `Zahn ${g.tooth}`}</h3>
            <span className="tooth-lines">
              {g.lines.length > 0 ? (
                g.lines.map((line) => (
                  <code key={line} className="tooth-line">
                    {line}
                  </code>
                ))
              ) : (
                <code className="tooth-line">nichts ausgewählt</code>
              )}
            </span>
          </header>
          <ul className="rows">
            {g.items.map((item) =>
              "row" in item ? (
                <ResultRow
                  key={item.row.key}
                  row={item.row}
                  onToggle={onToggle}
                  onAdopt={onAdopt}
                  onRemove={onRemove}
                  counter={counter}
                  tapCodes={tapCodes}
                  onTap={tapAt.has(item.row.key) ? onTap : undefined}
                />
              ) : "frame" in item ? (
                <FrameRows
                  key={item.frame.key}
                  frame={item.frame}
                  tooth={g.tooth}
                  onToggle={onToggle}
                  onAdopt={onAdopt}
                  onRemove={onRemove}
                  counter={counter}
                />
              ) : (
                <OptionRow key={item.option.key} option={item.option} onAdopt={onAdopt} counter={counter} />
              ),
            )}
          </ul>
          {onEdit && g.tooth !== null && (
            <button type="button" className="tooth-add" onClick={() => onEdit(g.tooth ?? undefined)}>
              <Icon name="plus" />
              Ziffer ändern oder ergänzen · Zahn {g.tooth}
            </button>
          )}
        </section>
      ))}
      {collected.map((block) => (
        <TappedBlock key={block.key} block={block} tapCodes={tapCodes} onTap={onTap} />
      ))}
      {elsewhere}

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
