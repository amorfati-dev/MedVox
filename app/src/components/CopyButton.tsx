// Schaltfläche, die Text in die Zwischenablage kopiert und kurz Rückmeldung gibt.
import { useEffect, useState } from "react";
import { copyText } from "../clipboard";

type Props = { label: string; text: string; disabled?: boolean; primary?: boolean };

export function CopyButton({ label, text, disabled, primary }: Props) {
  const [status, setStatus] = useState<"" | "ok" | "fehler">("");

  useEffect(() => {
    if (!status) return;
    const timer = window.setTimeout(() => setStatus(""), 1800);
    return () => window.clearTimeout(timer);
  }, [status]);

  const caption = status === "ok" ? "Kopiert ✓" : status === "fehler" ? "Kopieren fehlgeschlagen" : label;
  return (
    <button
      type="button"
      className={primary ? "btn btn-primary" : "btn"}
      disabled={disabled || !text}
      onClick={async () => setStatus((await copyText(text)) ? "ok" : "fehler")}
    >
      {caption}
    </button>
  );
}
