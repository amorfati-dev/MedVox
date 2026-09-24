// Eine Zeile der Ergebnisliste: Kästchen · Ziffer · Leistung · „wegen: …“ · Prüfstreifen.
// Die ganze Zeile ist die Tippfläche (Handschuhe). Abgewählte Zeilen bleiben stehen, durchgestrichen.
// Am iPad ergänzte Zeilen tragen statt „wegen: …“ den Vermerk „von Hand“, ersetzte „geändert“.
// Mengenweise berechnete Zeilen (je Kanal, mehrmals je Sitzung) tragen rechts die Knöpfe − Anzahl +.
import type { Suggestion } from "../api";
import type { Counter } from "../hooks/useCorrection";
import type { Frame, Option, Row, Tag } from "../result";
import { CountStepper } from "./CountStepper";
import { Icon } from "./Icon";

const TAG_LABEL: Record<Tag, (s: Suggestion) => string> = {
  bema: (s) => s.system,
  goz: (s) => s.system,
  kassenanteil: () => "Kassenanteil",
  zuzahlung: () => "Zuzahlung",
};

function Checks({ decide }: { decide: string[] }) {
  return decide.map((text) => (
    <p key={text} className="check-strip">
      <Icon name="warn" />
      <span>
        <strong>Prüfen:</strong> {text}
      </span>
    </p>
  ));
}

// „Zähne antippen“ an einer Je-Zahn-Position (Zahnschema, ToothTapSheet); Türkis Kasse, Indigo privat.
export function TapButton({ codes, kind, label, onTap }: { codes: string[]; kind: string; label?: string; onTap: () => void }) {
  const what = codes.length === 2 ? `${codes[0]} / ${codes[1]} nach Wurzelzahl` : `${codes[0]} je Zahn`;
  return (
    <button type="button" className={kind === "bema" ? "tap-teeth kasse" : "tap-teeth"} onClick={onTap}>
      <Icon name="edit" />
      {label ?? `Zähne antippen · ${what}`}
    </button>
  );
}

function Teeth({ s }: { s: Suggestion }) {
  return s.teeth.length > 1 ? <span className="row-meta">Zähne {s.teeth.join(", ")}</span> : null;
}

// `onRemove`: Zeile „von Hand“ entfernen (wird immer kopiert, also nicht abwählbar); fehlt = nicht änderbar.
// `counter`: Anzahl mit − / + ändern (nur am iPad); fehlt = nur anzeigen.
// `tapCodes`/`onTap`: Je-Zahn-Position – Knopf „Zähne antippen“ unter der Zeile (nur am iPad).
type RowProps = {
  row: Row;
  onToggle: (code: string) => void;
  onAdopt: (key: string) => void;
  onRemove?: (s: Suggestion) => void;
  counter?: Counter | null;
  tapCodes?: (code: string) => string[] | null;
  onTap?: (code: string) => void;
};

// Vermerk einer Korrektur am iPad; null = so vom Extraktor.
function edited(row: Row): string | null {
  if (row.source === "hand") return "von Hand";
  if (row.source !== "geaendert") return null;
  if (row.s.source !== "geaendert") return "Anzahl von Hand";
  if (row.s.replaced) return `geändert · vorher ${row.s.replaced}`;
  return row.s.counted !== undefined ? "Anzahl von Hand" : "geändert";
}

export function ResultRow({ row, onToggle, onAdopt, onRemove, counter, tapCodes, onTap }: RowProps) {
  const { s, tag, count, selected } = row;
  const tap = onTap && tapCodes?.(s.code);
  const mark = edited(row);
  const hand = row.source === "hand";
  // Abgewählt: keine Knöpfe – eine Zeile fällt nur über die Abwahl weg, nie über die Anzahl.
  const range = selected && counter ? counter.range(s) : null;
  return (
    <li className={`row row-${tag}${selected ? "" : " row-off"}${range ? " row-stepped" : ""}`}>
      <button
        type="button"
        className="row-main"
        role="checkbox"
        aria-checked={selected}
        aria-label={`${s.system} ${s.code}${count > 1 ? `, ${count}-mal` : ""}, ${s.title}${mark ? `, ${mark}` : ""}${selected ? "" : ", abgewählt"}${hand && onRemove ? ", antippen entfernt die Zeile" : ""}`}
        onClick={() => (hand ? onRemove?.(s) : onToggle(s.code))}
      >
        <span className="box" aria-hidden="true">
          {selected && <Icon name="check" />}
        </span>
        <span className="row-code">
          {s.code}
          {count > 1 && !range && <span className="row-count">{count}×</span>}
        </span>
        <span className="row-body">
          <span className="row-title">
            {s.title} <span className="row-tag">{TAG_LABEL[tag](s)}</span>
            {mark && <span className="row-tag tag-hand">{mark}</span>}
          </span>
          {s.evident && <span className="row-meta">Evident: {s.evident}</span>}
          <Teeth s={s} />
          {row.source !== "hand" && <span className="row-reason">{s.reason}</span>}
        </span>
      </button>
      {range && counter && <CountStepper s={s} count={count} max={range.max} onSet={counter.set} />}
      <Checks decide={s.decide} />
      {tap && onTap && <TapButton codes={tap} kind={s.kind} onTap={() => onTap(s.code)} />}
      {row.options.length > 0 && (
        <ul className="options">
          {row.options.map((o) => (
            <OptionRow key={o.key} option={o} onAdopt={onAdopt} counter={counter} />
          ))}
        </ul>
      )}
    </li>
  );
}

type OptionProps = { option: Option; onAdopt: (key: string) => void; counter?: Counter | null };

// Option (`alternative`): Zuzahlungs-Optionen und „ggf. dazu“ (`addon`: Ä1/Zst zur Weisheitszahn-OP) sind
// abgewählt voreingestellt und per Tipp übernehmbar; andere Optionen (Privat-Gegenstück ohne Paar) bleiben
// ein Hinweis. Übernommen zählt sie wie eine Zeile.
export function OptionRow({ option, onAdopt, counter }: OptionProps) {
  const { s, adoptable, adopted } = option;
  const range = adopted && counter ? counter.range(s) : null;
  const label = s.addon
    ? adopted ? "Option · übernommen" : "Option · ggf. dazu"
    : adopted ? "Zuzahlung · übernommen" : adoptable ? "Option · Zuzahlung möglich" : "Option · nur Hinweis";
  const body = (
    <>
      <span className="box" aria-hidden="true">
        {adopted && <Icon name="check" />}
      </span>
      <span className="row-code">{s.code}</span>
      <span className="row-body">
        <span className="row-title">
          {s.title} <span className="row-tag">{label}</span>
        </span>
        <Teeth s={s} />
        <span className="row-reason">{s.reason}</span>
        {adoptable && !adopted && <span className="row-hint">Antippen, um mit abzurechnen</span>}
      </span>
    </>
  );
  return (
    <li className={`option${adopted ? " option-on" : ""}${adoptable ? "" : " option-info"}${range ? " row-stepped" : ""}`}>
      {adoptable ? (
        <button
          type="button"
          className="row-main"
          role="checkbox"
          aria-checked={adopted}
          aria-label={`Option ${s.system} ${s.code}, ${s.title}, ${adopted ? "übernommen" : "nicht übernommen"}`}
          onClick={() => onAdopt(option.key)}
        >
          {body}
        </button>
      ) : (
        <div className="row-main">{body}</div>
      )}
      {range && counter && <CountStepper s={s} count={s.count} max={range.max} onSet={counter.set} />}
      <Checks decide={s.decide} />
    </li>
  );
}

type FrameProps = { frame: Frame; tooth: number | null } & Omit<RowProps, "row">;

// Mehrkosten: Kassenanteil und Zuzahlung am selben Zahn in einem Rahmen.
export function FrameRows({ frame, tooth, onToggle, onAdopt, onRemove, counter }: FrameProps) {
  const { basis, copay } = frame;
  const where = tooth === null ? "" : ` Zahn ${tooth}`;
  return (
    <li className="frame">
      <p className="frame-head">
        {basis ? (
          <>
            Mehrkosten{where} · Kasse zahlt <strong>{basis.s.code}</strong> · Patient zahlt{" "}
            <strong>{copay.s.code}</strong> · Vereinbarung nötig
          </>
        ) : (
          <>
            Zuzahlung · Patient zahlt <strong>{copay.s.code}</strong> · Vereinbarung nötig
          </>
        )}
      </p>
      <ul className="rows">
        {basis && <ResultRow row={basis} onToggle={onToggle} onAdopt={onAdopt} onRemove={onRemove} counter={counter} />}
        <ResultRow row={copay} onToggle={onToggle} onAdopt={onAdopt} onRemove={onRemove} counter={counter} />
      </ul>
    </li>
  );
}
