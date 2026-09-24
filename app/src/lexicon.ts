// Wörterbuch der Praxis (/woerterbuch): Ersetzungen „falsch gehört → richtig“ und Fachbegriffe für den
// Whisper-Prompt. Ein Eintrag gilt ab dem Speichern für alle Diktate (Entscheidung F5), abgeschaltet
// statt gelöscht; die Schutzregeln prüft der Server (server/medvox/lexicon_entries.py) und meldet sie als Text.
// Reine Funktionen, getestet in test/lexicon.test.ts. Mit Endung, damit `node --test` sie lädt.
import type { TranscribeResult } from "./api.ts";
import { json, request } from "./http.ts";

export type LexiconKind = "ersetzung" | "begriff";
export type LexiconSource = "hand" | "korrektur";
export type LexiconEntry = {
  id: number;
  kind: LexiconKind;
  wrong: string; // leer bei Begriffen
  right: string;
  active: boolean;
  source: LexiconSource;
  created_at: number; // Unix-Zeit in Sekunden
};
export type PromptGauge = {
  base: string; // Grundtext (infra/whisper/prompt.txt), hier nur lesbar
  base_tokens: number;
  terms_tokens: number;
  limit: number; // mehr nimmt whisper.cpp nicht, davor schneidet es ab
  exact: boolean; // mit dem Vokabular des Modells gezählt, sonst vorsichtig geschätzt
};
export type Lexicon = {
  entries: LexiconEntry[];
  builtin: { wrong: string; right: string }[];
  prompt: PromptGauge;
};
export type LexiconSuggestion = {
  kind: "text" | "ziffer";
  before: string;
  after: string;
  count: number;
  takeable: boolean; // besteht die Schutzregeln, noch nicht eingetragen
  taken: boolean;
};
export type SuggestionList = {
  suggestions: LexiconSuggestion[];
  total: number;
  first_week: string | null;
  last_week: string | null;
};
export type Draft = { wrong: string; right: string };

export const lexiconApi = {
  list: () => request<Lexicon>("/api/v1/lexicon"),
  add: (kind: LexiconKind, wrong: string, right: string, source: LexiconSource) =>
    request<LexiconEntry>("/api/v1/lexicon", json("POST", { kind, wrong, right, source })),
  setActive: (id: number, active: boolean) => request<LexiconEntry>(`/api/v1/lexicon/${id}`, json("PUT", { active })),
  suggestions: () => request<SuggestionList>("/api/v1/lexicon/suggestions"),
  clearCorrections: () => request<void>("/api/v1/corrections", { method: "DELETE" }),
  // Probe: derselbe Satz ohne und mit dem Entwurf durch /analyze (Kasse); gespeichert wird nichts.
  probe: (text: string, draft: Draft | null) =>
    request<TranscribeResult>("/api/v1/analyze", json("POST", { text, patient_type: "kasse", draft })),
};

// „seit 24.09.“
export function sinceLabel(createdAt: number): string {
  const d = new Date(createdAt * 1000);
  return `seit ${String(d.getDate()).padStart(2, "0")}.${String(d.getMonth() + 1).padStart(2, "0")}.`;
}

export function entryMeta(e: LexiconEntry): string {
  const origin = e.source === "korrektur" ? "aus Korrekturen übernommen" : "von Hand";
  return e.active ? `${origin} · ${sinceLabel(e.created_at)}` : `${origin} · abgeschaltet`;
}

export function byKind(entries: LexiconEntry[], kind: LexiconKind): LexiconEntry[] {
  return entries.filter((e) => e.kind === kind);
}

// Ein Begriff kostet im Mittel etwa 6 Token (Komma, Leerzeichen, 2–5 Wortstücke; Umlaute zählen extra).
export const TOKENS_PER_TERM = 6;

export type GaugeView = {
  basePct: number;
  termsPct: number;
  used: number;
  free: number;
  moreTerms: number; // Platz für etwa so viele weitere Begriffe
  full: boolean;
};

export function gaugeView(p: PromptGauge): GaugeView {
  const used = p.base_tokens + p.terms_tokens;
  const free = Math.max(0, p.limit - used);
  const pct = (n: number) => Math.min(100, Math.round((n / Math.max(1, p.limit)) * 100));
  return {
    basePct: pct(p.base_tokens),
    termsPct: Math.min(pct(p.terms_tokens), 100 - pct(p.base_tokens)),
    used,
    free,
    moreTerms: Math.floor(free / TOKENS_PER_TERM),
    full: free < TOKENS_PER_TERM,
  };
}

// „KW 39–40“ aus „2026-W39“ / „2026-W40“; über den Jahreswechsel mit Jahr.
export function weekRange(first: string | null, last: string | null): string {
  if (!first || !last) return "";
  const [fy, fw] = first.split("-W");
  const [ly, lw] = last.split("-W");
  const f = Number(fw);
  const l = Number(lw);
  if (fy !== ly) return `KW ${f}/${fy} – ${l}/${ly}`;
  return f === l ? `KW ${f}` : `KW ${f}–${l}`;
}

// Ziffernänderung als Satz: „13b → 13c“, „107 ergänzt“, „13b entfernt“.
export function codeChange(s: LexiconSuggestion): string {
  if (!s.before) return `${s.after} ergänzt`;
  if (!s.after) return `${s.before} entfernt`;
  return `${s.before} → ${s.after}`;
}

export function probeCodes(r: TranscribeResult): string {
  return r.codes.length ? r.codes.join(", ") : "keine";
}

// Ergebnis einer Probe gehört nur zu genau dem Entwurf und Satz, für den sie lief.
export function probeKey(draft: Draft, sentence: string): string {
  return JSON.stringify([draft.wrong.trim(), draft.right.trim(), sentence.trim()]);
}
