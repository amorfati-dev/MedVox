// Büro, linke Spalte: Diktate „ohne Patient“ oben, dann alle Patienten, jüngstes Diktat zuerst –
// mit Nummer, Anzahl der Diktate, Uhrzeit und ob schon übertragen.
import type { PatientList } from "../api";
import { clock, patientState, preview, STATE_LABEL } from "../patients";
import { plural } from "../status";

export type Selection = { kind: "patient"; id: number } | { kind: "ohne"; id: string } | null;

type Props = { list: PatientList | null; selected: Selection; onSelect: (s: Selection) => void };

export function PatientListCard({ list, selected, onSelect }: Props) {
  const on = (s: Selection) => (selected?.kind === s?.kind && selected?.id === s?.id ? " plist-on" : "");
  return (
    <section className="card plist" aria-label="Patienten">
      <h2>Patienten heute</h2>
      {list === null ? (
        <p className="muted">Lade …</p>
      ) : list.patients.length === 0 && list.unassigned.length === 0 ? (
        <p className="muted">Noch keine Diktate gespeichert. Am iPad die Patientennummer eingeben und diktieren.</p>
      ) : (
        <ul>
          {list.unassigned.map((d) => (
            <li key={d.id}>
              <button
                type="button"
                className={`plist-item plist-ohne${on({ kind: "ohne", id: d.id })}`}
                onClick={() => onSelect({ kind: "ohne", id: d.id })}
              >
                <span className="plist-number">Ohne Patient</span>
                <span className="state-chip state-ohne">zuordnen</span>
                <span className="plist-meta">
                  {clock(d.created_at)} · {preview(d.transcript) || "(leer)"}
                </span>
              </button>
            </li>
          ))}
          {list.patients.map((p) => {
            const state = patientState(p);
            return (
              <li key={p.id}>
                <button
                  type="button"
                  className={`plist-item${on({ kind: "patient", id: p.id })}`}
                  onClick={() => onSelect({ kind: "patient", id: p.id })}
                >
                  <span className="plist-number">{p.number}</span>
                  <span className={`state-chip state-${state === "übertragen" ? "done" : state}`}>{STATE_LABEL[state]}</span>
                  <span className="plist-meta">
                    {p.dictations > 0 && `${plural(p.dictations, "Diktat", "Diktate")} · ${clock(p.updated_at)}`}
                    {p.dictations > 0 && p.transferred > 0 && " · "}
                    {p.transferred > 0 && `${p.transferred} übertragen ${clock(p.transferred_at)}`}
                    {state === "leer" && `angelegt ${clock(p.created_at)}`}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
      <p className="muted small">
        Diktate bleiben, bis sie als übertragen markiert sind – höchstens 24 Stunden, danach löscht der Praxis-Mac sie.
      </p>
    </section>
  );
}
