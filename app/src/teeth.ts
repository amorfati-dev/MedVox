// Zahnschema: Anordnung, Markierung je Zahn und das Antippen der Zähne einer Je-Zahn-Position (4050/4055,
// AIT a/b, 2000 …). Reine Funktionen, getestet in test/teeth.test.ts; Anzeige in ToothChart/ToothTapSheet.
//
// Abrechnung geht vor Vollständigkeit: abgerechnet werden nur angetippte Zähne, je Zahn einmal. Die Ziffer
// folgt der Wurzelzahl aus der FDI-Nummer (wie der Extraktor, Katalog-README); bei den oberen 4ern (14, 24)
// rät MedVox nicht – dort muss die Wurzelzahl angegeben werden, bevor übernommen werden kann.
// Mit Endung, damit `node --test` das Modul direkt laden kann (allowImportingTsExtensions).
import type { Suggestion } from "./api.ts";
import { tapCodes, toothOf, type CatalogEntry } from "./catalog.ts";
import { handSuggestion } from "./correction.ts";
import type { Group, Row } from "./result.ts";

// Zahn fürs Zahnschema, wie der Server ihn liefert (extract_findings.py); tooth null = Befund ohne Zahn.
export type ToothInfo = { tooth: number | null; surfaces: string; findings: string[] };
export type Jaw = "ok" | "uk";
export type Root = "single" | "multi" | "ask";

// BEMA-Definition wie extract_rules.multi_rooted; obere 4er fragen statt raten.
export function rootOf(fdi: number): Root {
  const q = Math.floor(fdi / 10);
  const t = fdi % 10;
  if (q >= 5) return t >= 4 ? "multi" : "single";
  if (t >= 6) return "multi";
  return t === 4 && (q === 1 || q === 2) ? "ask" : "single";
}

export function jawOf(fdi: number): Jaw {
  return [1, 2, 5, 6].includes(Math.floor(fdi / 10)) ? "ok" : "uk";
}

// Je Kieferhälfte eine Reihe von der Mitte aus (1→8), damit dieselbe Spalte derselbe Zahntyp ist.
// Milchzähne bekommen eine eigene Reihe, aber nur wenn einer davon gezeigt wird (`shown`).
export type ChartRow = { quadrant: number; label: string; teeth: number[] };
const HALVES: Record<Jaw, [number, string][]> = {
  ok: [[1, "oben rechts"], [2, "oben links"], [5, "Milchz. oben re."], [6, "Milchz. oben li."]],
  uk: [[4, "unten rechts"], [3, "unten links"], [8, "Milchz. unten re."], [7, "Milchz. unten li."]],
};

export function chartRows(jaw: Jaw, shown: Iterable<number> = []): ChartRow[] {
  const quadrants = new Set([...shown].map((t) => Math.floor(t / 10)));
  return HALVES[jaw]
    .filter(([q]) => q <= 4 || quadrants.has(q))
    .map(([q, label]) => ({ quadrant: q, label, teeth: Array.from({ length: q <= 4 ? 8 : 5 }, (_, i) => q * 10 + i + 1) }));
}

// Zähne in FDI-Reihenfolge und als kurzer Text „11–13, 15, 21“.
export function byFdi(teeth: Iterable<number>): number[] {
  return [...new Set(teeth)].sort((a, b) => a - b);
}

export function toothRanges(teeth: Iterable<number>): string {
  const runs: number[][] = [];
  for (const t of byFdi(teeth)) {
    const last = runs[runs.length - 1];
    if (last && t === last[last.length - 1] + 1) last.push(t);
    else runs.push([t]);
  }
  return runs.map((r) => (r.length > 2 ? `${r[0]}–${r[r.length - 1]}` : r.join(", "))).join(", ");
}

// --- Antippen -------------------------------------------------------------------------------------------

// Angetippte Zähne und die angegebene Wurzelzahl (Ziffer) an den Zähnen, bei denen gefragt wird.
export type TapState = { teeth: number[]; answered: Record<number, string> };

// Stand beim Öffnen: alle Zähne, an denen die Position schon steht (diktiert, ergänzt oder angetippt). An
// 14/24 gilt die Ziffer nur als angegeben, wenn sie dort schon einmal angetippt wurde – nie die des Extraktors.
export function tapStart(suggestions: Suggestion[], codes: string[]): TapState {
  const teeth: number[] = [];
  const answered: Record<number, string> = {};
  for (const s of suggestions) {
    const tooth = toothOf(s);
    if (s.alternative || tooth === null || !codes.includes(s.code)) continue;
    teeth.push(tooth);
    if (s.tapped && codes.length > 1 && rootOf(tooth) === "ask") answered[tooth] = s.code;
  }
  return { teeth: byFdi(teeth), answered };
}

export function toggleTooth(state: TapState, fdi: number): TapState {
  if (!state.teeth.includes(fdi)) return { ...state, teeth: byFdi([...state.teeth, fdi]) };
  const answered = Object.fromEntries(Object.entries(state.answered).filter(([t]) => Number(t) !== fdi));
  return { teeth: state.teeth.filter((t) => t !== fdi), answered };
}

export function answerRoot(state: TapState, fdi: number, code: string): TapState {
  return { ...state, answered: { ...state.answered, [fdi]: code } };
}

// Ziffer an diesem Zahn; null = Wurzelzahl noch offen.
export function codeAt(fdi: number, codes: string[], answered: Record<number, string>): string | null {
  if (codes.length === 1) return codes[0];
  const root = rootOf(fdi);
  if (root === "ask") return answered[fdi] ?? null;
  return root === "multi" ? codes[1] : codes[0];
}

export function openTeeth(state: TapState, codes: string[]): number[] {
  return state.teeth.filter((t) => codeAt(t, codes, state.answered) === null);
}

// Anzahl je Ziffer, in der Reihenfolge des Paars (4050 × 18 · 4055 × 8).
export function tapCounts(state: TapState, codes: string[]): { code: string; count: number }[] {
  return codes.map((code) => ({ code, count: state.teeth.filter((t) => codeAt(t, codes, state.answered) === code).length }));
}

// „Übernehmen“: die Position steht danach genau an den angetippten Zähnen, je Zahn einmal („von Hand“,
// `tapped`), an der Stelle der bisherigen Zeilen. Die Zeile ohne Zahn und alle bisherigen Zeilen dieser
// Ziffern entfallen – nichts zählt doppelt. Wirft, solange eine Wurzelzahl offen ist.
export function applyTap(suggestions: Suggestion[], codes: string[], state: TapState, catalog: Map<string, CatalogEntry>): Suggestion[] {
  const mine = (s: Suggestion) => !s.alternative && codes.includes(s.code);
  const added = state.teeth.map((tooth) => {
    const code = codeAt(tooth, codes, state.answered);
    const entry = code === null ? undefined : catalog.get(code);
    if (!entry) throw new Error(`Zahn ${tooth}: Ziffer offen`);
    return { ...handSuggestion(entry, tooth, 1), reason: "Zahn angetippt", tapped: true };
  });
  const at = suggestions.findIndex(mine);
  const kept = suggestions.filter((s) => !mine(s));
  const index = at < 0 ? kept.length : suggestions.slice(0, at).filter((s) => !mine(s)).length;
  return [...kept.slice(0, index), ...added, ...kept.slice(index)];
}

// Die Ziffern, die „Zähne antippen“ an dieser Zeile bearbeitet; null = keine Je-Zahn-Position.
export function tapTarget(code: string, catalog: Map<string, CatalogEntry>): string[] | null {
  const entry = catalog.get(code);
  return entry?.per_tooth ? tapCodes(entry) : null;
}

// --- Anzeige ---------------------------------------------------------------------------------------------

// Angetippte Zeilen stehen in der Liste gesammelt je Leistung („Zahnstein je Zahn · 26 Zähne“) statt in
// je einem Zahnblock; die Evident-Zeile je Zahn bleibt unverändert (Kopfzeile der Zahnblöcke, Kopiertext).
export type Collected = { key: string; label: string; rows: { row: Row; teeth: number[] }[]; teeth: number };

export function collectTapped(groups: Group[]): { groups: Group[]; collected: Collected[] } {
  const blocks = new Map<string, Map<string, { row: Row; teeth: number[] }>>();
  const rest: Group[] = [];
  for (const g of groups) {
    const items = g.items.filter((item) => {
      if (!("row" in item) || !item.row.s.tapped || item.row.options.length > 0 || g.tooth === null) return true;
      const label = item.row.s.title.split(",")[0];
      const rows = blocks.get(label) ?? new Map();
      blocks.set(label, rows);
      const known = rows.get(item.row.s.code);
      if (known) known.teeth.push(g.tooth);
      else rows.set(item.row.s.code, { row: item.row, teeth: [g.tooth] });
      return false;
    });
    if (items.length > 0) rest.push({ ...g, items });
  }
  const collected = [...blocks].map(([label, rows]) => {
    const list = [...rows.values()].sort((a, b) => a.row.s.code.localeCompare(b.row.s.code));
    return { key: `tap|${label}`, label, rows: list, teeth: list.reduce((n, r) => n + r.teeth.length, 0) };
  });
  return { groups: rest, collected };
}

// Zahnschema mehrerer Abschnitte: je Zahn einmal, Flächen und Befunde zusammengeführt (ohne Zahn zuletzt).
export function mergeTeeth(prev: ToothInfo[], next: ToothInfo[]): ToothInfo[] {
  const merged = new Map<number | null, ToothInfo>();
  for (const t of [...prev, ...next]) {
    const known = merged.get(t.tooth);
    if (!known) {
      merged.set(t.tooth, { ...t, findings: [...t.findings] });
      continue;
    }
    known.surfaces += [...t.surfaces].filter((c) => !known.surfaces.includes(c)).join("");
    for (const f of t.findings) if (!known.findings.includes(f)) known.findings.push(f);
  }
  return [...merged.values()].sort((a, b) => Number(a.tooth === null) - Number(b.tooth === null));
}
