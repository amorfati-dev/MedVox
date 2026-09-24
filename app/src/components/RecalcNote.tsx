// Grüner Streifen nach einer Korrektur: was sich an den Ziffern geändert hat, mit „Rückgängig“ (eine Stufe).
import { Fragment } from "react";
import { describeParts, type Change } from "../textdiff";
import { Icon } from "./Icon";

type Props = { title: string; changes: Change[]; onUndo: () => void };

export function RecalcNote({ title, changes, onUndo }: Props) {
  const parts = describeParts(changes, "neu");
  return (
    <div className="recalc" role="status">
      <Icon name="check" />
      <span>
        {title}:{" "}
        {parts.length > 0
          ? parts.map((p, i) => (p.code ? <b key={i}>{p.text}</b> : <Fragment key={i}>{p.text}</Fragment>))
          : "keine Änderung an den Ziffern"}
      </span>
      <button type="button" className="btn" onClick={onUndo}>
        Rückgängig
      </button>
    </div>
  );
}
