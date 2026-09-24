// Blatt „Zähne antippen“ für eine Je-Zahn-Position (4050/4055, AIT a/b, 2000 …), gebaut wie das Katalog-Blatt.
// Ein Kiefer auf einmal, je Kieferhälfte eine Reihe mit 8 Zähnen von der Mitte aus (Tasten ≥ 64 px): dieselbe
// Spalte ist derselbe Zahntyp, 1–5 einwurzelig, 6–8 mehrwurzelig. Antippen wählt den Zahn, noch einmal
// antippen nimmt ihn heraus; die Ziffer folgt der Wurzelzahl (teeth.ts). An 14/24 fragt das Blatt nach der
// Wurzelzahl, „Übernehmen“ geht erst danach. Keinen „ganzen Kiefer“: fehlende Zähne würden sonst mitgezählt.
// Alle Zähne einer schon angetippten Position herausnehmen und „Position entfernen“ nimmt sie ganz heraus.
import { useEffect, useState } from "react";
import type { PatientType, Suggestion } from "../api";
import type { CatalogEntry } from "../catalog";
import { plural } from "../status";
import {
  answerRoot,
  chartRows,
  codeAt,
  jawOf,
  openTeeth,
  rootOf,
  tapCounts,
  tapStart,
  toggleTooth,
  type Jaw,
  type TapState,
} from "../teeth";
import { Icon } from "./Icon";
import { PATIENT_LABEL } from "./PatientSwitch";
import { JawSwitch, jawCounts } from "./ToothChart";

type Props = {
  codes: string[]; // [einwurzelig, mehrwurzelig] oder die eine Ziffer
  catalog: Map<string, CatalogEntry>;
  patientType: PatientType;
  suggestions: Suggestion[];
  onApply: (state: TapState) => void;
  onClose: () => void;
};

export function ToothTapSheet({ codes, catalog, patientType, suggestions, onApply, onClose }: Props) {
  const [state, setState] = useState(() => tapStart(suggestions, codes));
  const [jaw, setJaw] = useState<Jaw>(() => (state.teeth.length > 0 ? jawOf(state.teeth[0]) : "ok"));
  const entry = catalog.get(codes[0]);
  const label = entry?.title.split(",")[0] ?? codes.join("/");
  const tone = entry?.kind === "bema" ? "tk-kasse" : "tk-privat";
  const pair = codes.length === 2;
  const open = openTeeth(state, codes);
  const ask = open[0];
  const total = state.teeth.length;
  const remove = total === 0 && suggestions.some((s) => s.tapped && codes.includes(s.code));
  const title = `${label} · Zähne antippen · ${PATIENT_LABEL[patientType]}`;

  useEffect(() => {
    const onKey = (ev: KeyboardEvent) => ev.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const go = open.length > 0 ? `Erst Zahn ${ask} klären` : remove ? "Position entfernen" : total === 0 ? "Mindestens einen Zahn antippen" : `Übernehmen · ${plural(total, "Zahn", "Zähne")}`;
  return (
    <div className="picker-backdrop">
      <section className="picker chart-sheet" role="dialog" aria-modal="true" aria-label={title}>
        <header className="picker-head">
          <h2>{title}</h2>
          <button type="button" className="btn btn-icon" aria-label="Schließen" onClick={onClose}>
            <Icon name="x" />
          </button>
        </header>
        <p className="cat-note">
          Antippen wählt den Zahn, noch einmal antippen nimmt ihn heraus. Abgerechnet werden nur angetippte Zähne
          {pair ? "; die Ziffer folgt der Wurzelzahl." : `, je Zahn einmal ${codes[0]}.`}
        </p>
        <JawSwitch jaw={jaw} counts={jawCounts(state.teeth)} onChange={setJaw} />
        {pair && (
          <div className="roots" aria-hidden="true">
            <span className="r1">1–5 einwurzelig → {codes[0]}</span>
            <span className="r2">6–8 mehrwurzelig → {codes[1]}</span>
          </div>
        )}
        <div className="tq-rows">
          {chartRows(jaw, state.teeth).map((r) => (
            <div key={r.quadrant} className="tq">
              <span className="tq-label">{r.label}</span>
              {r.teeth.map((t) => {
                const on = state.teeth.includes(t);
                const code = on ? codeAt(t, codes, state.answered) : null;
                const asks = pair && rootOf(t) === "ask";
                return (
                  <button
                    key={t}
                    type="button"
                    className={!on ? "tk tk-none" : code === null ? "tk tk-open" : `tk ${tone}`}
                    aria-pressed={on}
                    aria-label={`Zahn ${t}${on ? `, ${code ?? "Wurzelzahl offen"}` : ""}`}
                    onClick={() => setState((s) => toggleTooth(s, t))}
                  >
                    <b>{t}</b>
                    {on ? <small>{code ?? "?"}</small> : asks && <small className="tk-ask">1 oder 2 W.</small>}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
        {ask !== undefined && (
          <div className="root-ask" role="group" aria-label={`Wurzelzahl Zahn ${ask}`}>
            <p>
              <Icon name="warn" /> <b>Zahn {ask}:</b> ein- oder zweiwurzelig? Obere 4er haben oft zwei Wurzeln – MedVox rät nicht.
            </p>
            <button type="button" className="btn" onClick={() => setState((s) => answerRoot(s, ask, codes[0]))}>
              einwurzelig · {codes[0]}
            </button>
            <button type="button" className="btn" onClick={() => setState((s) => answerRoot(s, ask, codes[1]))}>
              zweiwurzelig · {codes[1]}
            </button>
          </div>
        )}
        <div className="sheet-foot">
          <p className="sheet-sum">
            {tapCounts(state, codes).map((c, n) => (
              <span key={c.code}>
                {n > 0 && " · "}
                <b>{c.code}</b> × {c.count}
              </span>
            ))}
            {open.length > 0 && <span className="open"> · {open.length} offen</span>}
          </p>
          <button type="button" className="btn" onClick={onClose}>
            Abbrechen
          </button>
          <button type="button" className="btn btn-primary" disabled={open.length > 0 || (total === 0 && !remove)} onClick={() => onApply(state)}>
            {open.length === 0 && total > 0 && <Icon name="check" />}
            {go}
          </button>
        </div>
      </section>
    </div>
  );
}
