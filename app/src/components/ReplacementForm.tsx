// Neue Ersetzung „falsch gehört → richtig“ mit Probe: derselbe Beispielsatz läuft ohne und mit dem Entwurf
// durch /analyze, erst danach lässt sich der Eintrag speichern (Entscheidung F5: sofort wirksam, mit Probe).
// Die Schutzregeln prüft der Server schon bei der Probe und nennt den Grund.
import { useEffect, useState, type FormEvent } from "react";
import { ApiError, type TranscribeResult } from "../api";
import type { LexiconState } from "../hooks/useLexicon";
import { lexiconApi, probeCodes, probeKey, type LexiconSource } from "../lexicon";
import { Icon } from "./Icon";

// Vorbelegung aus einem Vorschlag der Korrektur-Sammlung
export type Prefill = { wrong: string; right: string; sentence: string; source: LexiconSource };
type Probe = { key: string; text: string; before: TranscribeResult; after: TranscribeResult };
type Props = { busy: boolean; act: LexiconState["act"]; initial: Prefill | null };

export function ReplacementForm({ busy, act, initial }: Props) {
  const [wrong, setWrong] = useState(initial?.wrong ?? "");
  const [right, setRight] = useState(initial?.right ?? "");
  const [sentence, setSentence] = useState(initial?.sentence ?? "");
  const [source, setSource] = useState<LexiconSource>(initial?.source ?? "hand");
  const [probe, setProbe] = useState<Probe | null>(null);
  const [probing, setProbing] = useState(false);
  const [refusal, setRefusal] = useState<string | null>(null);

  const text = sentence.trim() || wrong.trim();
  const key = probeKey({ wrong, right }, text);
  const probed = probe?.key === key;
  const filled = wrong.trim() !== "" && right.trim() !== "";

  const runProbe = async () => {
    setProbing(true);
    setRefusal(null);
    try {
      const draft = { wrong, right };
      const [before, after] = await Promise.all([lexiconApi.probe(text, null), lexiconApi.probe(text, draft)]);
      setProbe({ key: probeKey(draft, text), text, before, after });
    } catch (e) {
      setProbe(null);
      setRefusal(e instanceof ApiError ? e.message : "Probe fehlgeschlagen.");
    } finally {
      setProbing(false);
    }
  };

  // Aus einem Vorschlag übernommen: die Probe gleich zeigen.
  useEffect(() => {
    if (initial) void runProbe();
  }, []);

  const pair = (value: string, set: (v: string) => void) => {
    set(value);
    setSource("hand"); // selbst geändert: nicht mehr „aus Korrekturen übernommen“
    setRefusal(null);
  };

  const add = async (ev: FormEvent) => {
    ev.preventDefault();
    const shown = `„${wrong.trim()}“ → „${right.trim()}“`;
    const ok = await act(async () => {
      await lexiconApi.add("ersetzung", wrong, right, source);
      return `${shown} gilt ab dem nächsten Diktat für alle iPads.`;
    });
    if (ok) {
      setWrong("");
      setRight("");
      setSentence("");
      setSource("hand");
      setProbe(null);
    }
  };

  return (
    <form className="lex-form" onSubmit={add}>
      <div className="lex-pair">
        <div>
          <label htmlFor="lex-wrong">Falsch gehört (1–3 Wörter)</label>
          <input id="lex-wrong" value={wrong} maxLength={80} placeholder="z. B. Zahn steinentfernung"
            onChange={(ev) => pair(ev.target.value, setWrong)} />
        </div>
        <div>
          <label htmlFor="lex-right">Richtig</label>
          <input id="lex-right" value={right} maxLength={60} placeholder="z. B. Zahnsteinentfernung"
            onChange={(ev) => pair(ev.target.value, setRight)} />
        </div>
      </div>
      <label htmlFor="lex-sentence">Beispielsatz für die Probe (leer: nur das falsch Gehörte)</label>
      <input id="lex-sentence" value={sentence} maxLength={500} placeholder="z. B. Zahn steinentfernung, Politur, Fluoridierung."
        onChange={(ev) => setSentence(ev.target.value)} />
      {refusal && (
        <p className="field-warn" role="alert">
          <Icon name="warn" /> {refusal}
        </p>
      )}
      {probed && probe && (
        <div className="probe" role="status">
          <p>
            <b>Probe</b> mit Ihrem Satz: <span className="mono">{probe.text}</span>
          </p>
          <p>
            → <span className="mono">{probe.after.transcript}</span>
          </p>
          <p>
            Ziffern (Kasse) vorher <b>{probeCodes(probe.before)}</b> · nachher <b>{probeCodes(probe.after)}</b>
          </p>
          {probe.before.transcript === probe.after.transcript && (
            <p className="muted">Der Entwurf ändert diesen Satz nicht – steht das falsch Gehörte genau so darin?</p>
          )}
        </div>
      )}
      <div className="actions">
        <button type="button" className="btn" disabled={busy || probing || !filled} onClick={() => void runProbe()}>
          {probing ? "Probe läuft …" : "Probe"}
        </button>
        <button type="submit" className="btn btn-primary" disabled={busy || probing || !filled || !probed}>
          Hinzufügen
        </button>
      </div>
      {filled && !probed && !refusal && <p className="small muted">Erst die Probe, dann Hinzufügen.</p>}
    </form>
  );
}
