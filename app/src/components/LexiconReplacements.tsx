// Karte „Ersetzungen“: eigene Einträge (abschalten statt löschen, „seit …“ und Herkunft), die zehn
// eingebauten zum Nachlesen und das Formular mit Probe.
import type { LexiconState } from "../hooks/useLexicon";
import { byKind, entryMeta, lexiconApi, type Lexicon, type LexiconEntry } from "../lexicon";
import { ReplacementForm, type Prefill } from "./ReplacementForm";

type Props = {
  lexicon: Lexicon;
  busy: boolean;
  act: LexiconState["act"];
  prefill: { nonce: number; value: Prefill } | null;
};

export function LexiconReplacements({ lexicon, busy, act, prefill }: Props) {
  const own = byKind(lexicon.entries, "ersetzung");
  const toggle = (e: LexiconEntry) =>
    void act(async () => {
      await lexiconApi.setActive(e.id, !e.active);
      return e.active
        ? `„${e.wrong}“ wird ab dem nächsten Diktat nicht mehr ersetzt.`
        : `„${e.wrong}“ → „${e.right}“ gilt wieder.`;
    });

  return (
    <section className="card">
      <h2>Ersetzungen · falsch gehört → richtig</h2>
      {own.length === 0 && <p className="muted">Noch keine eigenen Ersetzungen.</p>}
      {own.map((e) => (
        <div key={e.id} className={e.active ? "lex-row" : "lex-row lex-off"}>
          <span className="lex-wrong">{e.wrong}</span>
          <span aria-hidden="true">→</span>
          <span className="lex-right">{e.right}</span>
          <span className="lex-actions">
            <button type="button" className="btn" disabled={busy} onClick={() => toggle(e)}>
              {e.active ? "Abschalten" : "Wieder einschalten"}
            </button>
          </span>
          <span className="lex-meta">{entryMeta(e)}</span>
        </div>
      ))}
      <details className="lex-builtin">
        <summary>Dazu {lexicon.builtin.length} eingebaute Ersetzungen (im Code, nicht änderbar)</summary>
        <ul>
          {lexicon.builtin.map((b) => (
            <li key={b.wrong}>
              <span className="lex-wrong">{b.wrong}</span> → <b>{b.right}</b>
            </li>
          ))}
        </ul>
      </details>
      <h3>Neue Ersetzung</h3>
      <ReplacementForm key={prefill?.nonce ?? 0} busy={busy} act={act} initial={prefill?.value ?? null} />
    </section>
  );
}
