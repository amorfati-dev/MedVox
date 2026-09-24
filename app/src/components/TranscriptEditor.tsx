// Transkript bearbeiten: großes Textfeld, „Abbrechen“ und „Übernehmen · Ziffern neu berechnen“
// (useCorrection.applyText). Tippen geht nur ohne Handschuhe – am Stuhl reicht das Katalog-Blatt.
import { useState } from "react";
import { Icon } from "./Icon";

type Props = {
  initial: string;
  busy: boolean;
  error: string | null;
  onApply: (text: string) => void;
  onCancel: () => void;
};

export function TranscriptEditor({ initial, busy, error, onApply, onCancel }: Props) {
  const [text, setText] = useState(initial);
  return (
    <section className="transcript-box">
      <div className="box-head">
        <h2>Transkript bearbeiten</h2>
      </div>
      <textarea
        className="editor"
        value={text}
        onChange={(e) => setText(e.target.value)}
        aria-label="Transkript"
        autoFocus
        autoCorrect="off"
        spellCheck={false}
      />
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <div className="editor-actions">
        <button type="button" className="btn" disabled={busy} onClick={onCancel}>
          Abbrechen
        </button>
        <button type="button" className="btn btn-primary" disabled={busy || !text.trim()} onClick={() => onApply(text)}>
          <Icon name={busy ? "spinner" : "check"} />
          {busy ? "Berechne …" : "Übernehmen · Ziffern neu berechnen"}
        </button>
      </div>
      <p className="editor-hint">
        Zahlen wie „36“ bleiben Zahnnummern. Neu berechnet wird aus dem ganzen Text, von Hand ergänzte Ziffern und
        Abwahlen bleiben erhalten.
      </p>
    </section>
  );
}
