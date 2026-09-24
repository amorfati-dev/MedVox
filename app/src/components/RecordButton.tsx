// Großer Aufnahmeknopf wie in Sprachmemos: roter Kern im Ring „Aufnehmen“, während der Aufnahme
// rotes Quadrat „Stopp“, beim Senden grau und gesperrt; „Erneut senden“ bernsteinfarben.
// Während der Aufnahme füllt sich der Ring bis zur Abschnittsgrenze (`progress` 0..1) und unter
// dem Wort stehen Laufzeit und Grenze (`clock` „0:42 / 1:00“). Gestaltung: styles/record.css.
import type { CSSProperties } from "react";
import { Icon, type IconName } from "./Icon";

export type RecordVariant = "aufnehmen" | "stopp" | "warten" | "erneut" | "neu";

const LOOK: Record<RecordVariant, { icon: IconName; label: string; aria: string }> = {
  aufnehmen: { icon: "mic", label: "Aufnehmen", aria: "Aufnahme starten" },
  stopp: { icon: "stop", label: "Stopp", aria: "Aufnahme beenden" },
  warten: { icon: "spinner", label: "Bitte warten", aria: "Wird übertragen – bitte warten" },
  erneut: { icon: "send", label: "Erneut senden", aria: "Wartende Abschnitte erneut senden" },
  neu: { icon: "mic", label: "Neu", aria: "Neues Diktat aufnehmen – das bisherige bleibt beim Patienten gespeichert" },
};

type Props = {
  variant: RecordVariant;
  onClick: () => void;
  disabled?: boolean;
  label?: string;
  aria?: string;
  progress?: number; // Anteil der Abschnittsgrenze (nur „stopp“)
  clock?: string; // Laufzeit und Grenze (nur „stopp“)
  final?: boolean; // letzte 10 s vor dem automatischen Senden
};

export function RecordButton({ variant, onClick, disabled, label, aria, progress, clock, final }: Props) {
  const look = LOOK[variant];
  const style = progress === undefined ? undefined : ({ "--progress": Math.min(1, Math.max(0, progress)) } as CSSProperties);
  const classes = ["record", `record-${variant}`, final ? "record-final" : ""].filter(Boolean).join(" ");
  return (
    <button
      type="button"
      className={classes}
      style={style}
      onClick={onClick}
      disabled={disabled || variant === "warten"}
      aria-label={aria ?? look.aria}
    >
      <span className="record-ring" aria-hidden="true" />
      <span className="record-core">
        <Icon name={look.icon} className="record-icon" />
      </span>
      <span className="record-text">
        <span className="record-label">{label ?? look.label}</span>
        {clock && <span className="record-clock">{clock}</span>}
      </span>
    </button>
  );
}
