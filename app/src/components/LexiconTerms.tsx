// Karte „Fachbegriffe für die Erkennung“: stehen nur im Prompt an whisper (Grundtext fest, dahinter die
// eingeschalteten Begriffe), keine unscharfe Korrektur. Der Füllstand zeigt, wie viel Platz whisper.cpp
// noch lässt – darüber schnitte es den Anfang des Grundtexts ab; der Server lehnt dann ab.
import { useState, type FormEvent } from "react";
import type { LexiconState } from "../hooks/useLexicon";
import { byKind, entryMeta, gaugeView, lexiconApi, type Lexicon, type LexiconEntry } from "../lexicon";

type Props = { lexicon: Lexicon; busy: boolean; act: LexiconState["act"] };

export function LexiconTerms({ lexicon, busy, act }: Props) {
  const [term, setTerm] = useState("");
  const terms = byKind(lexicon.entries, "begriff");
  const g = gaugeView(lexicon.prompt);

  const add = async (ev: FormEvent) => {
    ev.preventDefault();
    const shown = term.trim();
    const ok = await act(async () => {
      await lexiconApi.add("begriff", "", shown, "hand");
      return `„${shown}“ steht ab dem nächsten Diktat im Prompt.`;
    });
    if (ok) setTerm("");
  };
  const toggle = (e: LexiconEntry) =>
    void act(async () => {
      await lexiconApi.setActive(e.id, !e.active);
      return e.active ? `„${e.right}“ ist aus dem Prompt genommen.` : `„${e.right}“ steht wieder im Prompt.`;
    });

  return (
    <section className="card">
      <h2>Fachbegriffe für die Erkennung</h2>
      <p className="small muted">Grundtext (fest, aus infra/whisper/prompt.txt):</p>
      <p className="prompt-base">{lexicon.prompt.base}</p>
      <h3>Ihre Ergänzungen</h3>
      {terms.length === 0 && <p className="muted">Noch keine. Ein Begriff hilft Whisper, ihn richtig zu schreiben.</p>}
      {terms.map((e) => (
        <div key={e.id} className={e.active ? "lex-row lex-term" : "lex-row lex-term lex-off"}>
          <span className="lex-right">{e.right}</span>
          <span className="lex-actions">
            <button type="button" className="btn" disabled={busy} onClick={() => toggle(e)}>
              {e.active ? "Abschalten" : "Wieder einschalten"}
            </button>
          </span>
          <span className="lex-meta">{entryMeta(e)}</span>
        </div>
      ))}
      <form className="lex-add" onSubmit={add}>
        <div>
          <label htmlFor="lex-term">Neuer Fachbegriff</label>
          <input id="lex-term" value={term} maxLength={40} placeholder="z. B. Wurzelstiftaufbau" onChange={(ev) => setTerm(ev.target.value)} />
        </div>
        <button type="submit" className="btn btn-primary" disabled={busy || !term.trim() || g.full}>
          Hinzufügen
        </button>
      </form>
      <div className="meter" role="img" aria-label={`Prompt zu ${g.basePct + g.termsPct} % gefüllt`}>
        <i className="meter-base" style={{ width: `${g.basePct}%` }} />
        <i className="meter-terms" style={{ width: `${g.termsPct}%` }} />
      </div>
      <p className={g.full ? "meter-note meter-full" : "meter-note"}>
        <span>
          Grundtext {lexicon.prompt.base_tokens} + Ergänzungen {lexicon.prompt.terms_tokens} von {lexicon.prompt.limit} Token
          {lexicon.prompt.exact ? "" : " (geschätzt – Modelldatei nicht gefunden)"}
        </span>
        <span>{g.full ? "Voll – erst einen Begriff abschalten" : `Platz für etwa ${g.moreTerms} weitere Begriffe`}</span>
      </p>
    </section>
  );
}
