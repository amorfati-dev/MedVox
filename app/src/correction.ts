// Korrektur am iPad: Ziffer an einem Zahn ersetzen oder aus dem Katalog ergänzen, Ziffern aus dem
// berichtigten Text neu berechnen. Reine Funktionen, getestet in test/correction.test.ts; der Zustand
// liegt in hooks/useCorrection.ts.
//
// Abrechnung geht vor Vollständigkeit: nichts wird auf Verdacht hochgezählt, keine Ziffer erfunden,
// keine still weggelassen. Deshalb:
// - Ersetzen wirkt nur an diesem Zahn (die Abwahl wirkt je Ziffer über alle Zähne und bleibt, wie sie ist);
//   die Zuzahlungs-Option am selben Zahn wandert mit (13b → 13c: 2080 → 2100).
// - Ergänzen legt einen Vorschlag „von Hand“ an. Ist die Ziffer am Zahn schon da, zählt er genau eins
//   mehr als angezeigt („2×“). Gleiche Ziffern am selben Zahn zählen wie in der Evident-Zeile einmal mit
//   der höchsten Anzahl – ein späterer Regel-Vorschlag derselben Ziffer zählt also nie doppelt.
// - Neu berechnen ersetzt die Regel-Vorschläge; Ersetzungen gelten wieder, wo die ersetzte Ziffer am Zahn
//   wieder vorkommt, Positionen „von Hand“ und Abwahlen bleiben. Was dabei wegfällt, zeigt der Streifen.
// Mit Endung, damit `node --test` das Modul direkt laden kann (allowImportingTsExtensions).
import { codeOf, type Suggestion } from "./api.ts";
import { toothOf, type CatalogEntry } from "./catalog.ts";
import { optionKey } from "./result.ts";

// Inhalt eines Diktats, den eine Korrektur ersetzt (wie aus /transcribe bzw. /analyze).
export type Content = { transcript: string; codes: string[]; suggestions: Suggestion[]; planned: Suggestion[]; notes: string[] };
// Auswahl: abgewählte Ziffern im Kopierformat, übernommene Optionen (optionKey).
export type Choice = { deselected: string[]; adopted: string[] };

// Angezeigte Anzahl einer Ziffer an einem Zahn (0 = nicht da).
export function countAt(suggestions: Suggestion[], tooth: number | null, code: string): number {
  return suggestions
    .filter((s) => !s.alternative && toothOf(s) === tooth && s.code === code)
    .reduce((n, s) => Math.max(n, s.count), 0);
}

export function handSuggestion(entry: CatalogEntry, tooth: number | null, count: number): Suggestion {
  return {
    code: entry.code,
    system: entry.system,
    title: entry.title,
    kind: entry.kind,
    count,
    points: entry.points,
    teeth: tooth === null ? [] : [tooth],
    reason: "von Hand ergänzt",
    decide: [],
    alternative: false,
    evident: entry.evident ?? null,
    source: "hand",
  };
}

// Ziffer aus dem Katalog an diesem Zahn ergänzen; schon da: eins mehr als angezeigt.
export function addPosition(suggestions: Suggestion[], entry: CatalogEntry, tooth: number | null): Suggestion[] {
  const count = countAt(suggestions, tooth, entry.code) + 1;
  const mine = (s: Suggestion) => s.source === "hand" && !s.alternative && toothOf(s) === tooth && s.code === entry.code;
  const at = suggestions.findIndex(mine);
  const added = handSuggestion(entry, tooth, count);
  if (at < 0) return [...suggestions, added];
  return suggestions.filter((s, i) => i === at || !mine(s)).map((s, i) => (i === at ? { ...s, count } : s));
}

// "BEMA 13b" im Begründungstext durch "BEMA 13c" ersetzen (Rahmen Kassenanteil/Zuzahlung bleibt verbunden).
function relabel(reason: string, from: string, fromSystem: string, to: CatalogEntry): string {
  const escaped = `${fromSystem} ${from}`.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return reason.replace(new RegExp(`${escaped}(?![0-9A-Za-z])`, "g"), `${to.system} ${to.code}`);
}

// Ersetzt `from` an diesem Zahn durch `to` (Haupt- oder Optionszeile); Flächen-Prüfhinweise sind damit entschieden.
function swap(list: Suggestion[], tooth: number | null, from: string, to: CatalogEntry, alternative: boolean): Suggestion[] {
  const hit = list.find((s) => toothOf(s) === tooth && s.code === from && s.alternative === alternative);
  if (!hit || from === to.code) return list;
  return list.map((s) => {
    if (toothOf(s) !== tooth) return s;
    const reason = relabel(s.reason, from, hit.system, to);
    if (s.code !== from || s.alternative !== alternative) return reason === s.reason ? s : { ...s, reason };
    const hand = s.source === "hand";
    return {
      ...s,
      code: to.code,
      system: to.system,
      title: to.title,
      points: to.points,
      kind: to.kind,
      evident: to.evident ?? null,
      reason,
      decide: s.decide.filter((d) => !d.startsWith("Fläche")),
      source: hand ? "hand" : "geaendert",
      replaced: hand ? undefined : (s.replaced ?? from),
    };
  });
}

// Partner am selben Zahn, der mitwandert: Zuzahlung zur BEMA-Füllung und umgekehrt (gleiche Flächenzahl).
// Nur bei eindeutiger Flächenzahl – das Inlay 2170 gilt für drei und vier Flächen, dort wandert nichts.
function partners(list: Suggestion[], tooth: number | null, from: string, to: CatalogEntry, catalog: Map<string, CatalogEntry>) {
  const i = to.family.indexOf(from);
  const j = to.family.indexOf(to.code);
  if (i < 0 || j < 0 || new Set(to.family).size !== to.family.length) return [];
  const moves: { from: string; to: CatalogEntry; alternative: boolean }[] = [];
  for (const s of list) {
    const own = catalog.get(s.code);
    const target = own && own.system !== to.system && own.family[i] === s.code ? catalog.get(own.family[j]) : undefined;
    if (toothOf(s) === tooth && target && target.code !== s.code && !moves.some((m) => m.from === s.code)) {
      moves.push({ from: s.code, to: target, alternative: s.alternative });
    }
  }
  return moves;
}

// Familie an diesem Zahn ersetzen (13b → 13c); übernommene Optionen wandern mit ihrem Schlüssel.
export function replaceFamily(
  suggestions: Suggestion[],
  adopted: string[],
  tooth: number | null,
  from: string,
  to: CatalogEntry,
  catalog: Map<string, CatalogEntry>,
): { suggestions: Suggestion[]; adopted: string[] } {
  const moves = [{ from, to, alternative: false }, ...partners(suggestions, tooth, from, to, catalog)];
  let list = suggestions;
  const keys = new Map<string, string>();
  for (const m of moves) {
    const next = swap(list, tooth, m.from, m.to, m.alternative);
    next.forEach((s, i) => {
      if (s !== list[i] && s.alternative && s.code !== list[i].code) keys.set(optionKey(list[i]), optionKey(s));
    });
    list = next;
  }
  return { suggestions: list, adopted: adopted.map((k) => keys.get(k) ?? k) };
}

// Neu berechnet: frische Regel-Vorschläge, darauf die Ersetzungen von vorher, dazu alles „von Hand“.
export function recompute(previous: Suggestion[], fresh: Suggestion[], catalog: Map<string, CatalogEntry>): Suggestion[] {
  let list = fresh;
  for (const s of previous) {
    const entry = catalog.get(s.code);
    if (s.source === "geaendert" && s.replaced && entry) list = swap(list, toothOf(s), s.replaced, entry, s.alternative);
  }
  return [...list, ...previous.filter((s) => s.source === "hand")];
}

// Abwahlen bleiben je Ziffer, auch wenn sich die Anzahl im Kopierformat ändert ("13a" → "2x 13a");
// eine Ziffer, die es nicht mehr gibt, fällt aus der Abwahl.
export function remapDeselected(deselected: string[], codes: string[]): string[] {
  const off = new Set(deselected.map(codeOf));
  return codes.filter((c) => off.has(codeOf(c)));
}

// Übernommene Optionen, die es nach der Korrektur noch gibt.
export function keepAdopted(adopted: string[], suggestions: Suggestion[]): string[] {
  const keys = new Set(suggestions.filter((s) => s.alternative).map(optionKey));
  return adopted.filter((k) => keys.has(k));
}
