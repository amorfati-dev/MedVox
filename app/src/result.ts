// Ergebnisliste: Vorschläge nach Zahn gruppiert, wie Evident sie braucht (je Zahn ein Block, Positionen
// ohne Zahn im letzten Block). Mehrkosten (Kassenanteil + Zuzahlung am selben Zahn) stehen in einem
// gemeinsamen Rahmen, Optionen (`alternative`) unter ihrer Leistung. Reine Funktionen, getestet in
// test/result.test.ts gegen die Anhang-B-Diktate.
// Mit Endung, damit `node --test` das Modul direkt laden kann (allowImportingTsExtensions).
import {
  codeOf,
  evidentBlocks,
  isToothless,
  joinBlocks,
  type EvidentBlocks,
  type Source,
  type Suggestion,
  type TransferPosition,
} from "./api.ts";

// bema/goz wie vom Server; kassenanteil = BEMA-Basis einer Zuzahlung am selben Zahn.
export type Tag = "bema" | "goz" | "kassenanteil" | "zuzahlung";

export type Option = {
  key: string; // optionKey: Ziffer und Zähne
  s: Suggestion;
  adoptable: boolean; // Zuzahlungs-Option beim Kassenpatienten: per Tipp übernehmbar (E4)
  adopted: boolean;
};

export type Row = {
  key: string;
  s: Suggestion;
  tag: Tag;
  count: number; // höchste Anzahl, falls ein späterer Abschnitt dieselbe Ziffer am Zahn wiederholt
  selected: boolean; // wird kopiert und an die Rezeption gesendet
  options: Option[];
  source: Source; // „von Hand“ ergänzt oder am iPad geändert (auch: Anzahl von Hand erhöht)
};

// Mehrkosten-Rahmen: „Kasse zahlt 13a · Patient zahlt 2150“; ohne Basis eigenständige Zuzahlung (PZR).
export type Frame = { key: string; basis: Row | null; copay: Row };
export type Item = { row: Row } | { frame: Frame } | { option: Option };

export type Group = {
  tooth: number | null; // null = ohne Zahn
  lines: string[]; // kopierte Evident-Zeilen dieses Zahns (ohne führendes Komma): Kasse, dann Privat; [] = nichts gewählt
  items: Item[];
};

// Eine Option ist über Ziffer und Zähne eindeutig (dieselbe Option aus zwei Abschnitten zählt einmal).
export function optionKey(s: Suggestion): string {
  return `${s.code}@${s.teeth.join("+")}`;
}

function adoptable(s: Suggestion): boolean {
  return s.alternative && s.kind === "zuzahlung";
}

// Vorschläge für das Kopierformat: übernommene Zuzahlungs-Optionen zählen wie jede gewählte Position.
// Ohne übernommene Option ist das Ergebnis genau die Eingabe – das Kopierformat bleibt dann unverändert.
export function billable(suggestions: Suggestion[], adopted: ReadonlySet<string>): Suggestion[] {
  if (adopted.size === 0) return suggestions;
  return suggestions.map((s) => (adoptable(s) && adopted.has(optionKey(s)) ? { ...s, alternative: false } : s));
}

// Gewählte Ziffern im Kopierformat plus die Ziffern übernommener Optionen.
export function billableCodes(active: string[], suggestions: Suggestion[], adopted: ReadonlySet<string>): string[] {
  const chosen = new Set(active.map(codeOf));
  const extra = suggestions.filter((s) => adoptable(s) && adopted.has(optionKey(s)) && !chosen.has(s.code));
  return [...active, ...new Set(extra.map((s) => s.code))];
}

// Evident-Zeilen (mit Kurzformen oder „Nur Ziffern“) für die aktuelle Auswahl, Kassen- und Privatblock
// getrennt („Kassenleistungen kopieren“, „Privatleistungen kopieren“). Eine übernommene Option bringt
// nur sich selbst an ihrem Zahn mit, nie eine abgewählte Position mit derselben Ziffer.
export function copyBlocks(
  suggestions: Suggestion[],
  active: string[],
  adopted: ReadonlySet<string>,
  shortForms = true,
): EvidentBlocks {
  const chosen = new Set(active.map(codeOf));
  const kept = adopted.size === 0 ? suggestions : suggestions.filter((s) => s.alternative || chosen.has(s.code));
  return evidentBlocks(billable(kept, adopted), billableCodes(active, suggestions, adopted), shortForms);
}

// Beide Blöcke als eine Zeilenliste („Ziffern kopieren“): Kasse, Leerzeile, Privat.
export function copyLines(
  suggestions: Suggestion[],
  active: string[],
  adopted: ReadonlySet<string>,
  shortForms = true,
): string[] {
  return joinBlocks(copyBlocks(suggestions, active, adopted, shortForms));
}

// Evident-Zeilen aus der Auswahl in der Ergebnisliste: alle Ziffern außer den abgewählten, dazu die
// übernommenen Optionen. Dieselbe Rechnung am iPad (useSelection) und im Büro (patients.ts).
export function selectedLines(
  suggestions: Suggestion[],
  codes: string[],
  deselected: ReadonlySet<string>,
  adopted: ReadonlySet<string>,
  shortForms = true,
): string[] {
  return copyLines(suggestions, codes.filter((c) => !deselected.has(c)), adopted, shortForms);
}

// „Zuzahlung zu BEMA 13a/13b/13c/13d: …“ → ["13a", "13b", "13c", "13d"]
function basisCodes(reason: string): string[] {
  const m = /^Zuzahlung(?: möglich)? zu BEMA ([^\s:]+)/.exec(reason);
  return m ? m[1].split("/") : [];
}

function tagOf(s: Suggestion): Tag {
  if (s.kind === "bema" && s.reason.startsWith("Kassenanteil:")) return "kassenanteil";
  return s.kind;
}

// `lines`: Evident-Zeilen der aktuellen Auswahl (copyLines), für die leisen Zeilen im Blockkopf.
export function buildGroups(
  suggestions: Suggestion[],
  active: string[],
  adopted: ReadonlySet<string>,
  lines: string[],
): Group[] {
  const chosen = new Set(active.map(codeOf));
  const groups = new Map<number | null, { rows: Item[]; last: Row | null }>();
  const seen = new Map<string, Row | Option>();

  for (const s of suggestions) {
    const tooth = s.teeth.length > 0 ? s.teeth[0] : null;
    let group = groups.get(tooth);
    if (!group) {
      group = { rows: [], last: null };
      groups.set(tooth, group);
    }
    const key = `${s.alternative ? "o" : "p"}|${tooth ?? "-"}|${s.code}`;
    const known = seen.get(key);
    if (known) {
      if ("count" in known && s.count > known.count && s.source && s.source !== "regel" && known.source === "regel") {
        known.source = "geaendert"; // Anzahl am Katalog-Blatt erhöht
      }
      if ("count" in known) known.count = Math.max(known.count, s.count);
      continue;
    }
    if (s.alternative) {
      const k = optionKey(s);
      const option: Option = { key: k, s, adoptable: adoptable(s), adopted: adoptable(s) && adopted.has(k) };
      seen.set(key, option);
      if (group.last) group.last.options.push(option);
      else group.rows.push({ option });
      continue;
    }
    const row: Row = { key, s, tag: tagOf(s), count: s.count, selected: chosen.has(s.code), options: [], source: s.source ?? "regel" };
    seen.set(key, row);
    group.rows.push({ row });
    group.last = row;
  }

  const ordered = [...groups.entries()].sort(([a], [b]) => Number(a === null) - Number(b === null));
  return ordered.map(([tooth, { rows }]) => ({
    tooth,
    lines: linesFor(tooth, lines),
    items: framed(rows),
  }));
}

function linesFor(tooth: number | null, lines: string[]): string[] {
  const own = lines.filter((l) => (tooth === null ? isToothless(l) : l !== "" && l.split(",")[0] === String(tooth)));
  return own.map((l) => (isToothless(l) ? l.slice(1) : l));
}

// Zuzahlung und ihre BEMA-Basis am selben Zahn in einen Rahmen: bevorzugt der Kassenanteil, der die
// Zuzahlung nennt („Kassenanteil: Basis der Zuzahlung GOZ 2150“), sonst die BEMA-Ziffer aus „zu BEMA …“.
function framed(items: Item[]): Item[] {
  const rows = items.flatMap((i) => ("row" in i ? [i.row] : []));
  const basisOf = new Map<Row, Row | null>();
  const used = new Set<Row>();
  for (const copay of rows.filter((r) => r.s.kind === "zuzahlung")) {
    const codes = basisCodes(copay.s.reason);
    const named = rows.find(
      (r) => r.tag === "kassenanteil" && !used.has(r) && r.s.reason.includes(`Zuzahlung ${copay.s.system} ${copay.s.code}`),
    );
    const basis = named ?? rows.find((r) => r.s.kind === "bema" && !used.has(r) && codes.includes(r.s.code)) ?? null;
    if (basis) used.add(basis);
    basisOf.set(copay, basis);
  }
  const result: Item[] = [];
  for (const item of items) {
    if (!("row" in item)) {
      result.push(item);
      continue;
    }
    const row = item.row;
    if (used.has(row)) continue; // steht im Rahmen seiner Zuzahlung
    if (!basisOf.has(row)) {
      result.push(item);
      continue;
    }
    const basis = basisOf.get(row) ?? null;
    result.push({ frame: { key: `mk|${row.key}`, basis, copay: row } });
  }
  return result;
}

// Geplantes aus mehreren Abschnitten nur einmal zeigen.
export function uniquePlanned(planned: Suggestion[]): Suggestion[] {
  const seen = new Set<string>();
  return planned.filter((s) => {
    const key = optionKey(s);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export type Counts = { positions: number; options: number; check: number; planned: number };

// Zählungen für die Kopfzeile: gewählte Positionen (inkl. übernommener Optionen), offene Optionen,
// Prüfhinweise, Geplantes.
export function countGroups(groups: Group[], planned: Suggestion[]): Counts {
  const counts: Counts = { positions: 0, options: 0, check: 0, planned: planned.length };
  const option = (o: Option) => {
    if (o.adopted) counts.positions += 1;
    else counts.options += 1;
    counts.check += o.s.decide.length;
  };
  const row = (r: Row) => {
    if (r.selected) counts.positions += 1;
    counts.check += r.s.decide.length;
    r.options.forEach(option);
  };
  for (const g of groups) {
    for (const item of g.items) {
      if ("row" in item) row(item.row);
      else if ("frame" in item) {
        if (item.frame.basis) row(item.frame.basis);
        row(item.frame.copay);
      } else option(item.option);
    }
  }
  return counts;
}

// Gewählte Positionen für die Rezeption (E6): Zahn, Ziffer, Art – übernommene Optionen als Zuzahlung.
export function positionsOf(groups: Group[]): TransferPosition[] {
  const result: TransferPosition[] = [];
  const add = (s: Suggestion, kind: Tag) => result.push({ tooth: s.teeth[0] ?? null, code: s.code, kind });
  const row = (r: Row) => {
    if (r.selected) add(r.s, r.tag);
    for (const o of r.options) if (o.adopted) add(o.s, "zuzahlung");
  };
  for (const g of groups) {
    for (const item of g.items) {
      if ("row" in item) row(item.row);
      else if ("frame" in item) {
        if (item.frame.basis) row(item.frame.basis);
        row(item.frame.copay);
      } else if (item.option.adopted) add(item.option.s, "zuzahlung");
    }
  }
  return result;
}
