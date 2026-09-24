// Katalog fürs Katalog-Blatt (GET /api/v1/catalog, schon nach Patiententyp gefiltert) und die Ziffern je
// Zahn, mit denen Korrektur (correction.ts) und Vergleich (textdiff.ts) rechnen. Reine Funktionen,
// getestet in test/correction.test.ts. Eine freie Ziffern-Eingabe gibt es nicht: ergänzt wird nur, was
// hier steht; Kurzformen nur aus dem Katalogfeld `evident`.
// Mit Endung, damit `node --test` das Modul direkt laden kann (allowImportingTsExtensions).
import type { PatientType, Suggestion, SuggestionKind } from "./api.ts";

export type CatalogEntry = {
  code: string;
  system: string; // BEMA | GOZ | GOÄ
  title: string;
  area: string; // Fachbereich (Diagnostik … PAR)
  points: number | null; // wird nie angezeigt
  kind: SuggestionKind;
  evident?: string | null;
  family: string[]; // Füllungsfamilie nach Flächenzahl 1–4 (13a–13d, 2150/2160/2170/2170), sonst leer
  per_tooth?: boolean; // „je Zahn“ (max_per zahn): Zähne im Zahnschema antippbar
  roots?: string[]; // Paar nach Wurzelzahl [einwurzelig, mehrwurzelig] (4050/4055), sonst leer
};
export type CatalogList = { version: string; patient_type: PatientType; entries: CatalogEntry[] };

// Ziffer an einem Zahn (null = ohne Zahn) mit Anzahl.
export type Position = { tooth: number | null; code: string; count: number };
// Stand vor der Korrektur: Transkript, Ziffern und Vorschläge je Zahn aller Abschnitte, wie sie kamen.
export type Original = { transcript: string; codes: string[]; positions: Position[] };

export const EMPTY_ORIGINAL: Original = { transcript: "", codes: [], positions: [] };

// Fachbereiche in der Reihenfolge der Knöpfe; unbekannte hinten an.
const AREAS = ["Diagnostik", "Röntgen", "Anästhesie", "Konservierend", "Endodontie", "Chirurgie", "Prophylaxe", "PAR"];

export function areas(entries: CatalogEntry[]): string[] {
  const present = new Set(entries.map((e) => e.area));
  return [...AREAS.filter((a) => present.has(a)), ...[...present].filter((a) => !AREAS.includes(a))];
}

export function toothOf(s: Suggestion): number | null {
  return s.teeth.length > 0 ? s.teeth[0] : null;
}

// Erbrachte Hauptvorschläge (keine Optionen, nichts Geplantes) als Ziffern je Zahn.
export function mainPositions(suggestions: Suggestion[]): Position[] {
  return suggestions.filter((s) => !s.alternative).map((s) => ({ tooth: toothOf(s), code: s.code, count: s.count }));
}

// Ziffern je Zahn wie in der Evident-Zeile: dieselbe Ziffer am selben Zahn zählt einmal mit der höchsten Anzahl.
export function perTooth(positions: Position[]): Map<number | null, Map<string, number>> {
  const teeth = new Map<number | null, Map<string, number>>();
  for (const p of positions) {
    const codes = teeth.get(p.tooth) ?? new Map<string, number>();
    codes.set(p.code, Math.max(codes.get(p.code) ?? 0, p.count));
    teeth.set(p.tooth, codes);
  }
  return teeth;
}

// Kopierformat der erbrachten Hauptvorschläge ("13c", "2x 41a"): je Zahn die höchste Anzahl, über die Zähne summiert.
export function codesOf(suggestions: Suggestion[]): string[] {
  const totals = new Map<string, number>();
  for (const codes of perTooth(mainPositions(suggestions)).values()) {
    for (const [code, n] of codes) totals.set(code, (totals.get(code) ?? 0) + n);
  }
  return [...totals].map(([code, n]) => (n === 1 ? code : `${n}x ${code}`));
}

// Katalog nach Ziffer; bei gleicher Ziffer in zwei Systemen gilt der erste Eintrag.
export function byCode(entries: CatalogEntry[]): Map<string, CatalogEntry> {
  const map = new Map<string, CatalogEntry>();
  for (const e of entries) if (!map.has(e.code)) map.set(e.code, e);
  return map;
}

// Ziffern einer Je-Zahn-Position beim Antippen: das Paar nach Wurzelzahl oder die Ziffer allein.
export function tapCodes(entry: CatalogEntry): string[] {
  return entry.roots && entry.roots.length === 2 ? entry.roots : [entry.code];
}

// Gehören zwei Ziffern zur selben Füllungsfamilie (13b/13c, 2080/2100)?
export function sameFamily(a: string, b: string, catalog: Map<string, CatalogEntry>): boolean {
  const fa = catalog.get(a)?.family ?? [];
  return fa.length > 0 && fa.includes(b);
}

// Suche nach Ziffer, Kurzform oder Wort im Titel, dazu der gewählte Fachbereich (null = alle).
export function filterCatalog(entries: CatalogEntry[], query: string, area: string | null): CatalogEntry[] {
  const q = fold(query.trim());
  return entries.filter(
    (e) =>
      (area === null || e.area === area) &&
      (q === "" || fold(e.code).startsWith(q) || fold(e.evident ?? "") === q || fold(e.title).includes(q)),
  );
}

function fold(text: string): string {
  return text.toLowerCase().replace(/ä/g, "ae").replace(/ö/g, "oe").replace(/ü/g, "ue").replace(/ß/g, "ss");
}
