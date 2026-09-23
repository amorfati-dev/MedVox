// Großer Aufnahmeknopf wie in Sprachmemos: roter Kreis „Aufnehmen“, während der Aufnahme
// rotes Quadrat „Stopp“, beim Senden grau und gesperrt; „Erneut senden“ bernsteinfarben.
import { Icon, type IconName } from "./Icon";

export type RecordVariant = "aufnehmen" | "stopp" | "warten" | "erneut" | "neu";

const LOOK: Record<RecordVariant, { icon: IconName; label: string; aria: string }> = {
  aufnehmen: { icon: "mic", label: "Aufnehmen", aria: "Aufnahme starten" },
  stopp: { icon: "stop", label: "Stopp", aria: "Aufnahme beenden" },
  warten: { icon: "spinner", label: "Bitte warten", aria: "Wird übertragen – bitte warten" },
  erneut: { icon: "send", label: "Erneut senden", aria: "Wartende Abschnitte erneut senden" },
  neu: { icon: "mic", label: "Neu", aria: "Neues Diktat aufnehmen – ersetzt das Ergebnis" },
};

type Props = { variant: RecordVariant; onClick: () => void; disabled?: boolean; label?: string; aria?: string };

export function RecordButton({ variant, onClick, disabled, label, aria }: Props) {
  const look = LOOK[variant];
  return (
    <button
      type="button"
      className={`record record-${variant}`}
      onClick={onClick}
      disabled={disabled || variant === "warten"}
      aria-label={aria ?? look.aria}
    >
      <Icon name={look.icon} className="record-icon" />
      <span className="record-label">{label ?? look.label}</span>
    </button>
  );
}
