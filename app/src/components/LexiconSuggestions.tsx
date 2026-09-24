// Karte „Aus Korrekturen“: gleiche Änderungen aus der Korrektur-Sammlung, gezählt. Übernommen wird nur per
// Tipp (füllt das Formular und zeigt die Probe); Ziffernänderungen sind nur Information für die Pflege des
// Extraktors – der Katalog bleibt im Code. „Alle löschen“ leert die Sammlung nach einer Rückfrage.
import { useState } from "react";
import type { LexiconState } from "../hooks/useLexicon";
import { codeChange, lexiconApi, weekRange, type LexiconSuggestion, type SuggestionList } from "../lexicon";

type Props = {
  found: SuggestionList;
  busy: boolean;
  act: LexiconState["act"];
  onTake: (s: LexiconSuggestion) => void;
};

function Action({ s, busy, onTake }: { s: LexiconSuggestion; busy: boolean; onTake: Props["onTake"] }) {
  if (s.taken) return <span className="state-chip state-done">übernommen</span>;
  if (s.takeable) {
    return (
      <button type="button" className="btn" disabled={busy} onClick={() => onTake(s)}>
        Als Ersetzung übernehmen
      </button>
    );
  }
  return <span className="small muted">{s.kind === "ziffer" ? "für den Extraktor" : "nur Information"}</span>;
}

export function LexiconSuggestions({ found, busy, act, onTake }: Props) {
  const [confirm, setConfirm] = useState(false);
  const clear = () =>
    void act(async () => {
      await lexiconApi.clearCorrections();
      setConfirm(false);
      return "Die Korrektur-Sammlung ist gelöscht.";
    });

  return (
    <section className="card">
      <h2>Aus Korrekturen</h2>
      {found.suggestions.length === 0 && (
        <p className="muted">
          Noch nichts gesammelt. Stellen kommen dazu, wenn ein am iPad korrigiertes Diktat übertragen wird oder abläuft.
        </p>
      )}
      {found.suggestions.map((s) => (
        <div key={`${s.kind}|${s.before}|${s.after}`} className="sugg-row">
          <span className="sugg-n">{s.count}×</span>
          <span className="sugg-pair">
            {s.kind === "ziffer" ? (
              `Ziffer ${codeChange(s)}`
            ) : (
              <>
                <s>{s.before || "–"}</s> → {s.after || "–"}
              </>
            )}
          </span>
          <Action s={s} busy={busy} onTake={onTake} />
        </div>
      ))}
      <div className="corpus-foot">
        <span>
          {found.total} Änderungsstellen{found.total ? ` aus ${weekRange(found.first_week, found.last_week)}` : ""}. Ohne
          Patientennummer, Kürzel, Behandler oder Datum; höchstens 12 Monate.
        </span>
        {found.total > 0 && !confirm && (
          <button type="button" className="btn" disabled={busy} onClick={() => setConfirm(true)}>
            Alle löschen
          </button>
        )}
      </div>
      {confirm && (
        <div className="actions" role="group" aria-label="Löschen bestätigen">
          <button type="button" className="btn btn-warn" disabled={busy} onClick={clear}>
            Ja, alle {found.total} löschen
          </button>
          <button type="button" className="btn" disabled={busy} onClick={() => setConfirm(false)}>
            Abbrechen
          </button>
        </div>
      )}
    </section>
  );
}
