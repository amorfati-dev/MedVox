// Statusfeld über dem Aufnahmeknopf: jeder Zustand dreifach codiert (Farbe, Symbol, Wort).
// Rot vollflächig nur während der Aufnahme; Fehler sind rot getönt, Unterbrechungen bernsteinfarben.
import { useEffect, useState } from "react";
import { AUTO_STOP_SECONDS, MAX_SECONDS } from "../hooks/useDictation";
import { formatClock, plural, type UiState } from "../status";
import { Icon, type IconName } from "./Icon";

type Props = {
  state: UiState;
  seconds: number; // Laufzeit des aktuellen Abschnitts
  level: number; // Pegel 0..1
  waiting: number; // Abschnitte, die auf die Übertragung warten
  uploading: boolean; // ein Abschnitt wird gerade übertragen
  error: string | null;
  rejected: boolean; // der wartende Abschnitt wird dauerhaft abgelehnt
  summary: string; // „0,8 s · 7 Ziffern · 1 geplant“ für „Ergebnis da“
};

// Ab 5 s Übertragung zeigt das Feld die Sekunden, damit ein Hänger auffällt.
function useElapsed(active: boolean): number {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    setElapsed(0);
    if (!active) return;
    const started = Date.now();
    const timer = window.setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 500);
    return () => window.clearInterval(timer);
  }, [active]);
  return elapsed;
}

const HATCH_FROM = ((MAX_SECONDS - 10) / MAX_SECONDS) * 100; // letzte 10 s schraffiert

export function StatusPanel({ state, seconds, level, waiting, uploading, error, rejected, summary }: Props) {
  const sending = useElapsed(state === "senden");
  const remaining = Math.max(0, AUTO_STOP_SECONDS - seconds);

  if (state === "aufnahme") {
    return (
      <section className="status status-aufnahme" aria-label="Status">
        <p className="status-word" role="status">
          <span className="rec-dot" aria-hidden="true" />
          Aufnahme
        </p>
        <p className="status-clock" aria-label={`${seconds} Sekunden, noch ${remaining} Sekunden`}>
          {formatClock(seconds)}
        </p>
        <div className="progress" aria-hidden="true">
          <div className="progress-hatch" style={{ left: `${HATCH_FROM}%` }} />
          <div className="progress-fill" style={{ width: `${Math.min(100, (seconds / MAX_SECONDS) * 100)}%` }} />
        </div>
        <div className="level" aria-hidden="true">
          <div className="level-fill" style={{ width: `${Math.round(level * 100)}%` }} />
        </div>
        <p className="status-detail">
          {remaining <= 10 ? `Noch ${remaining} s – dann wird der Abschnitt automatisch gesendet` : `noch ${remaining} s`}
        </p>
        {uploading && <p className="status-detail">Voriger Abschnitt wird übertragen …</p>}
        {error && <p className="status-detail">{error}</p>}
      </section>
    );
  }

  const view: Record<Exclude<UiState, "aufnahme">, { icon: IconName; word: string }> = {
    bereit: { icon: "mic", word: "Bereit" },
    senden: { icon: "spinner", word: "Wird übertragen" },
    fertig: { icon: "check", word: "Ergebnis da" },
    fortsetzbar: { icon: "pause", word: "Unterbrochen – nichts verloren" },
    fehler: { icon: "x", word: rejected ? "Abschnitt abgelehnt" : "Fehler" },
  };
  const { icon, word } = view[state];

  return (
    <section className={`status status-${state}`} aria-label="Status">
      <p className="status-word" role="status">
        <Icon name={icon} />
        {word}
      </p>
      {state === "bereit" && <p className="status-detail">höchstens {MAX_SECONDS} s je Abschnitt</p>}
      {state === "senden" && (
        <p className="status-detail">
          Auf dem Praxis-Mac{waiting > 1 ? ` · ${plural(waiting, "Abschnitt", "Abschnitte")}` : ""}
          {sending >= 5 ? ` · seit ${sending} s` : " …"}
        </p>
      )}
      {state === "fertig" && <p className="status-detail">{summary}</p>}
      {state === "fortsetzbar" && (
        <p className="status-detail">
          {waiting > 0
            ? `${plural(waiting, "Abschnitt wartet", "Abschnitte warten")} auf die Übertragung.`
            : "Aufnahme angehalten – „Weiter aufnehmen“ hängt den nächsten Abschnitt an."}
        </p>
      )}
      {error && (
        <p className="status-cause" role={state === "fehler" ? "alert" : undefined}>
          {error}
        </p>
      )}
      {rejected && <p className="status-detail">Nur diesen Abschnitt verwerfen – der bisherige Text bleibt.</p>}
    </section>
  );
}
