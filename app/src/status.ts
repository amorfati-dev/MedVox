// Anzeigezustand der Diktat-Ansicht, nur aus dem Zustand von useDictation abgeleitet.
// Die Aufnahme- und Warteschlangenlogik bleibt in hooks/useDictation.ts und hooks/useUploadQueue.ts.
import type { DictationPhase } from "./hooks/useDictation";

// bereit, aufnahme, senden, fertig (bereit mit Ergebnis), fortsetzbar (unterbrochen, nichts verloren),
// fehler (dauerhaft: Mikrofon, Browser, Abschnitt abgelehnt).
export type UiState = "bereit" | "aufnahme" | "senden" | "fertig" | "fortsetzbar" | "fehler";

export type StatusInput = {
  phase: DictationPhase;
  supported: boolean;
  discardable: boolean;
  error: string | null;
  transcript: string;
};

export function uiState(d: StatusInput): UiState {
  if (d.phase === "aufnahme") return "aufnahme";
  if (!d.supported) return "fehler";
  if (d.phase === "sende") return "senden";
  if (d.discardable) return "fehler";
  if (d.phase === "fortsetzbar") return "fortsetzbar";
  if (d.error) return "fehler";
  return d.transcript ? "fertig" : "bereit";
}

// Uhr mit gleich breiten Ziffern: 0:07, 1:00.
export function formatClock(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

// Zahl mit Wort in Einzahl/Mehrzahl: „1 Abschnitt“, „2 Abschnitte“.
export function plural(n: number, one: string, many: string): string {
  return `${n} ${n === 1 ? one : many}`;
}

// Sekunden mit deutschem Komma: 0,8 s.
export function formatSeconds(s: number): string {
  return `${s.toFixed(1).replace(".", ",")} s`;
}
