// Transkript am iPad; nach einer Textkorrektur sind die geänderten Wörter unterstrichen (grün).
import { useMemo } from "react";
import { wordDiff } from "../textdiff";

type Props = { text: string; original: string | null }; // original: Text vor der Korrektur, null = nicht korrigiert

export function TranscriptText({ text, original }: Props) {
  const parts = useMemo(() => (original === null || original === text ? null : wordDiff(original, text)), [original, text]);
  return (
    <p className="transcript" aria-live="polite">
      {parts === null
        ? text
        : parts
            .filter((p) => p.kind !== "del")
            .map((p, i) => (
              <span key={i}>
                {i > 0 && " "}
                {p.kind === "ins" ? <mark className="corr">{p.text}</mark> : p.text}
              </span>
            ))}
    </p>
  );
}
