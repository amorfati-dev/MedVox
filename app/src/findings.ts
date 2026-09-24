// Befunde und Leistungen je Zahn fürs Zahnschema und „Befund kopieren“ (Entscheidung F4: eine Zeile je Zahn,
// „36 mod: Karies profunda – Kompositfüllung adhäsiv, dreiflächig (2100), …“). Reine Funktionen, getestet in
// test/findings.test.ts. Leistungen sind genau die kopierten Positionen (wie „Ziffern kopieren“); Befunde
// und Flächen kommen vom Server (`teeth`), bei älteren Diktaten ohne `teeth` nur die Zähne aus den Ziffern.
// Mit Endung, damit `node --test` das Modul direkt laden kann (allowImportingTsExtensions).
import type { Suggestion, SuggestionKind } from "./api.ts";
import { toothOf } from "./catalog.ts";
import { billable, billableCodes, copiedMain } from "./result.ts";
import { toothRanges, type ToothInfo } from "./teeth.ts";

export type Item = { code: string; title: string; count: number; kind: SuggestionKind; tapped: boolean; check: boolean };
export type FindingRow = { tooth: number | null; surfaces: string; findings: string[]; done: Item[]; planned: Item[] };
// Markierung im Schema: wer zahlt (Kasse/Privat), nur geplant, nur Befund; `check` = offener Prüfhinweis.
export type Mark = { tone: "kasse" | "privat" | "plan" | "find"; check: boolean; label: string };

function add(list: Item[], s: Suggestion): void {
  const known = list.find((i) => i.code === s.code);
  if (known) {
    known.count = Math.max(known.count, s.count);
    known.tapped ||= s.tapped === true;
    known.check ||= s.decide.length > 0;
    return;
  }
  list.push({ code: s.code, title: s.title, count: s.count, kind: s.kind, tapped: s.tapped === true, check: s.decide.length > 0 });
}

// Je Zahn (FDI-Reihenfolge, ohne Zahn zuletzt): Flächen, Befunde, kopierte Positionen, Geplantes.
// `active`: gewählte Ziffern im Kopierformat, `adopted`: übernommene Optionen – wie beim Kopieren.
export function findingRows(
  suggestions: Suggestion[],
  planned: Suggestion[],
  active: string[],
  adopted: ReadonlySet<string>,
  teeth: ToothInfo[],
): FindingRow[] {
  const rows = new Map<number | null, FindingRow>();
  const row = (tooth: number | null) => {
    let r = rows.get(tooth);
    if (!r) rows.set(tooth, (r = { tooth, surfaces: "", findings: [], done: [], planned: [] }));
    return r;
  };
  for (const t of teeth) {
    const r = row(t.tooth);
    r.surfaces += [...t.surfaces].filter((c) => !r.surfaces.includes(c)).join("");
    for (const f of t.findings) if (!r.findings.includes(f)) r.findings.push(f);
  }
  const copied = copiedMain(billable(suggestions, adopted), billableCodes(active, suggestions, adopted));
  for (const s of copied) add(row(toothOf(s)).done, s);
  for (const s of planned) add(row(toothOf(s)).planned, s);
  return [...rows.values()]
    .filter((r) => r.findings.length + r.done.length + r.planned.length > 0 || r.surfaces !== "")
    .sort((a, b) => (a.tooth ?? 1000) - (b.tooth ?? 1000));
}

function part(i: Item): string {
  return `${i.title} (${i.count > 1 ? `${i.count}x ` : ""}${i.code})`;
}

export function findingLine(r: FindingRow): string {
  const head = r.tooth === null ? "ohne Zahn" : r.surfaces ? `${r.tooth} ${r.surfaces}` : String(r.tooth);
  const parts = [
    r.findings.join(", "),
    r.done.map(part).join(", "),
    r.planned.length > 0 ? `geplant – ${r.planned.map(part).join(", ")}` : "",
  ].filter(Boolean);
  return parts.length > 0 ? `${head}: ${parts.join(" – ")}` : head;
}

// „Befund kopieren“: eine Zeile je Zahn, auch für angetippte Zähne.
export function findingText(rows: FindingRow[]): string {
  return rows.map(findingLine).join("\n");
}

export function chartMarks(rows: FindingRow[]): Map<number, Mark> {
  const marks = new Map<number, Mark>();
  for (const r of rows) {
    if (r.tooth === null) continue;
    const privat = r.done.some((i) => i.kind !== "bema");
    const tone = privat ? "privat" : r.done.length > 0 ? "kasse" : r.planned.length > 0 ? "plan" : "find";
    const n = r.done.length;
    const label = r.surfaces || (n === 1 ? r.done[0].code : n > 1 ? `${n} Ziff.` : r.planned.length > 0 ? "geplant" : "");
    marks.set(r.tooth, { tone, check: r.done.some((i) => i.check), label });
  }
  return marks;
}

// Liste am Schirm: angetippte Positionen stehen gesammelt je Leistung („Zahnsteinentfernung → 4050 an 11–13 …“),
// Zähne nur mit angetippten Positionen fallen aus der Liste; ohne Zahn nur mit Befund.
export type Shown = { rows: FindingRow[]; tapped: { label: string; parts: { code: string; kind: SuggestionKind; teeth: string }[] }[] };

export function shownFindings(rows: FindingRow[]): Shown {
  const groups = new Map<string, Map<string, { kind: SuggestionKind; teeth: number[] }>>();
  const shown: FindingRow[] = [];
  for (const r of rows) {
    for (const i of r.done.filter((d) => d.tapped && r.tooth !== null)) {
      const label = i.title.split(",")[0];
      const codes = groups.get(label) ?? new Map<string, { kind: SuggestionKind; teeth: number[] }>();
      groups.set(label, codes);
      const known = codes.get(i.code) ?? { kind: i.kind, teeth: [] };
      codes.set(i.code, { ...known, teeth: [...known.teeth, r.tooth as number] });
    }
    const done = r.done.filter((d) => !d.tapped);
    const keep = r.tooth === null ? r.findings.length > 0 : r.findings.length + done.length + r.planned.length > 0;
    if (keep) shown.push({ ...r, done });
  }
  const tapped = [...groups].map(([label, codes]) => ({
    label,
    parts: [...codes]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([code, { kind, teeth }]) => ({ code, kind, teeth: toothRanges(teeth) })),
  }));
  return { rows: shown, tapped };
}
