// Schon per Kurzcode abgeholte Stände eines Diktats mit dem aktuellen vergleichen: je Zahn und
// Position mit Anzahl (so wie in den Evident-Zeilen, "36,wf*3"), damit Rezeption und Büro nur die
// Änderung eintragen – getrennt nach Kassen- und Privatblock (evidentBlocks), weil Evident nach
// einer Privatposition alles Folgende privat setzt. Mit Endung für `node --test`.
import { splitBlocks, type EvidentBlocks, type Handover } from "./api.ts";

type Block = keyof EvidentBlocks;
type Entry = { block: Block; tooth: string; form: string; n: number };

// Positionen der Blöcke als „Zahn,Position“ → Eintrag; die Leerzeile zwischen den Blöcken zählt nicht.
function entries(blocks: EvidentBlocks, into = new Map<string, Entry>(), blockOf?: Map<string, Entry>): Map<string, Entry> {
  for (const block of ["kasse", "privat"] as const) {
    for (const line of blocks[block]) {
      if (line === "") continue;
      const [tooth, ...tokens] = line.split(",");
      for (const token of tokens) {
        const m = /^(.+)\*(\d+)$/.exec(token);
        const [form, n] = m ? [m[1], Number(m[2])] : [token, 1];
        const key = `${tooth},${form}`;
        // Jede Abholung nach der ersten trägt nur die Änderung ein: in Evident steht das Höchste.
        const was = into.get(key);
        into.set(key, { block: blockOf?.get(key)?.block ?? block, tooth, form, n: Math.max(was?.n ?? 0, n) });
      }
    }
  }
  return into;
}

// Einträge als Evident-Zeilen je Block, Zähne in der Reihenfolge ihres ersten Auftretens.
function lines(list: Entry[]): EvidentBlocks {
  const out: EvidentBlocks = { kasse: [], privat: [] };
  for (const block of ["kasse", "privat"] as const) {
    const teeth = new Map<string, string[]>();
    for (const e of list.filter((x) => x.block === block)) {
      const tokens = teeth.get(e.tooth) ?? [];
      tokens.push(e.n > 1 ? `${e.form}*${e.n}` : e.form);
      teeth.set(e.tooth, tokens);
    }
    const ordered = [...teeth].sort(([a], [b]) => Number(a === "") - Number(b === ""));
    out[block] = ordered.map(([tooth, tokens]) => [tooth, ...tokens].join(","));
  }
  return out;
}

export type HandoverDiff = {
  added: EvidentBlocks; // ganz neu seit den Abholungen – nur diese in Evident nachtragen
  removed: EvidentBlocks; // schon abgeholt, jetzt nicht mehr im Diktat – in Evident prüfen
  changed: { kasse: string[]; privat: string[] }; // nur die Anzahl geändert, als Satz
};

// `allPrivate`: übergebene Zeilen ohne Leerzeile sind der Privatblock (wie splitBlocks).
export function handoverDiff(current: EvidentBlocks, earlier: Handover[], allPrivate = false): HandoverDiff {
  const now = entries(current);
  const before = new Map<string, Entry>();
  for (const h of earlier) entries(splitBlocks(h.codes, allPrivate), before, now);
  const changed: HandoverDiff["changed"] = { kasse: [], privat: [] };
  for (const [key, e] of now) {
    const was = before.get(key)?.n;
    if (was === undefined || was === e.n) continue;
    const what = e.n > was ? `${e.n - was}× nachtragen` : `${was - e.n}× zu viel in Evident – prüfen`;
    changed[e.block].push(`${e.tooth || "ohne Zahn"}: ${e.form} jetzt ${e.n}× statt ${was}× – ${what}`);
  }
  return {
    added: lines([...now].filter(([k]) => !before.has(k)).map(([, e]) => e)),
    removed: lines([...before].filter(([k]) => !now.has(k)).map(([, e]) => e)),
    changed,
  };
}
