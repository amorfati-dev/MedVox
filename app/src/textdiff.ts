// Was eine Korrektur geändert hat: Wörter (Büro: „Original vor der Korrektur“ mit Durchstreichung und
// Einfügung) und Ziffern je Zahn („13b → 13c an Zahn 36 · 107 ergänzt“; Streifen am iPad). Reine
// Funktionen, getestet in test/correction.test.ts.
// Mit Endung, damit `node --test` das Modul direkt laden kann (allowImportingTsExtensions).
import { perTooth, sameFamily, type CatalogEntry, type Position } from "./catalog.ts";

export type Part = { kind: "same" | "del" | "ins"; text: string };

const MAX_CELLS = 4_000_000; // Obergrenze der Vergleichstabelle (≈ 2000 × 2000 Wörter)

// Wortweiser Vergleich (längste gemeinsame Teilfolge); gleiche Anfangs- und Endstücke vorab abgetrennt.
export function wordDiff(before: string, after: string): Part[] {
  const a = before.split(/\s+/).filter(Boolean);
  const b = after.split(/\s+/).filter(Boolean);
  let head = 0;
  while (head < a.length && head < b.length && a[head] === b[head]) head += 1;
  let tail = 0;
  while (tail < a.length - head && tail < b.length - head && a[a.length - 1 - tail] === b[b.length - 1 - tail]) tail += 1;
  const x = a.slice(head, a.length - tail);
  const y = b.slice(head, b.length - tail);
  if (x.length * y.length > MAX_CELLS) {
    // fast alles neu geschrieben: als ein Block gelöscht/eingefügt statt quadratisch zu rechnen
    const words = [...a.slice(0, head).map((word) => ({ kind: "same" as const, word })),
      ...x.map((word) => ({ kind: "del" as const, word })), ...y.map((word) => ({ kind: "ins" as const, word })),
      ...a.slice(a.length - tail).map((word) => ({ kind: "same" as const, word }))];
    return merge(words);
  }
  const width = y.length + 1;
  const lcs = new Uint32Array((x.length + 1) * width);
  for (let i = x.length - 1; i >= 0; i -= 1) {
    for (let j = y.length - 1; j >= 0; j -= 1) {
      lcs[i * width + j] = x[i] === y[j] ? lcs[(i + 1) * width + j + 1] + 1 : Math.max(lcs[(i + 1) * width + j], lcs[i * width + j + 1]);
    }
  }
  const words: { kind: Part["kind"]; word: string }[] = a.slice(0, head).map((word) => ({ kind: "same", word }));
  let i = 0;
  let j = 0;
  while (i < x.length || j < y.length) {
    if (i < x.length && j < y.length && x[i] === y[j]) {
      words.push({ kind: "same", word: x[i] });
      i += 1;
      j += 1;
    } else if (j >= y.length || (i < x.length && lcs[(i + 1) * width + j] >= lcs[i * width + j + 1])) {
      words.push({ kind: "del", word: x[i] });
      i += 1;
    } else {
      words.push({ kind: "ins", word: y[j] });
      j += 1;
    }
  }
  for (const word of a.slice(a.length - tail)) words.push({ kind: "same", word });
  return merge(words);
}

// Aufeinanderfolgende Wörter gleicher Art zusammenfassen; gelöschte vor eingefügten.
function merge(words: { kind: Part["kind"]; word: string }[]): Part[] {
  const parts: Part[] = [];
  for (const { kind, word } of words) {
    const last = parts[parts.length - 1];
    if (last && last.kind === kind) last.text += ` ${word}`;
    else parts.push({ kind, text: word });
  }
  return parts;
}

// Nur die Umgebung der Änderungen: unveränderte Stücke auf `around` Wörter je Seite gekürzt („…“).
export function excerpt(parts: Part[], around = 3): Part[] {
  return parts.map((p, i) => {
    if (p.kind !== "same") return p;
    const words = p.text.split(" ");
    const first = i === 0;
    const last = i === parts.length - 1;
    const keep = (first ? 0 : around) + (last ? 0 : around);
    if (words.length <= keep + 1) return p;
    const lead = first ? [] : words.slice(0, around);
    const trail = last ? [] : words.slice(words.length - around);
    return { kind: "same", text: [...lead, "…", ...trail].join(" ") };
  });
}

export type Change = { tooth: number | null; before: string; after: string }; // "" = nicht da; "2x 25" mit Anzahl

function label(code: string, count: number): string {
  return count > 1 ? `${count}x ${code}` : code;
}

// Ziffernänderungen je Zahn: ersetzt (gleiche Familie), ergänzt, entfallen, Anzahl geändert.
export function codeChanges(before: Position[], after: Position[], catalog: Map<string, CatalogEntry>): Change[] {
  const old = perTooth(before);
  const now = perTooth(after);
  const changes: Change[] = [];
  for (const tooth of new Set([...old.keys(), ...now.keys()])) {
    const was = old.get(tooth) ?? new Map<string, number>();
    const is = now.get(tooth) ?? new Map<string, number>();
    const added = [...is.keys()].filter((c) => !was.has(c));
    for (const [code, n] of was) {
      if (is.has(code)) continue;
      const twin = added.find((c) => sameFamily(code, c, catalog));
      if (twin) added.splice(added.indexOf(twin), 1);
      changes.push({ tooth, before: label(code, n), after: twin ? label(twin, is.get(twin) ?? 1) : "" });
    }
    for (const code of added) changes.push({ tooth, before: "", after: label(code, is.get(code) ?? 1) });
    for (const [code, n] of was) {
      const m = is.get(code);
      if (m !== undefined && m !== n) changes.push({ tooth, before: label(code, n), after: label(code, m) });
    }
  }
  return changes;
}

// „13b → 13c an Zahn 36 · neu 107 (ohne Zahn)“ (Streifen am iPad) bzw. „… · 107 ergänzt“ (Büro);
// `code` markiert die Ziffern für die Hervorhebung.
export type Segment = { text: string; code?: boolean };

export function describeParts(changes: Change[], style: "neu" | "ergänzt"): Segment[] {
  const out: Segment[] = [];
  changes.forEach(({ tooth, before, after }, i) => {
    if (i > 0) out.push({ text: " · " });
    const at = tooth === null ? "" : ` an Zahn ${tooth}`;
    if (!before && style === "neu") out.push({ text: "neu " }, { text: after, code: true }, { text: at || " (ohne Zahn)" });
    else if (!before) out.push({ text: after, code: true }, { text: ` ergänzt${at}` });
    else if (!after) out.push({ text: before, code: true }, { text: ` entfällt${at}` });
    else out.push({ text: `${before} → ${after}`, code: true }, { text: at });
  });
  return out;
}

export function describe(changes: Change[], style: "neu" | "ergänzt"): string {
  return describeParts(changes, style)
    .map((s) => s.text)
    .join("");
}
