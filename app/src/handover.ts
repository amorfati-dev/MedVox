// Schon per Kurzcode abgeholte Stände eines Diktats mit dem aktuellen vergleichen: je Zahn und
// Position (so wie in den Evident-Zeilen), damit Rezeption und Büro nur die Änderung eintragen.
// Mit Endung, damit `node --test` das Modul direkt laden kann (allowImportingTsExtensions).
import type { Handover } from "./api.ts";

// Evident-Zeilen ("36,13c,2100"; ohne Zahn ",01") als Paare „Zahn,Position“.
function pairs(lines: string[]): Set<string> {
  const found = new Set<string>();
  for (const line of lines) {
    const [tooth, ...codes] = line.split(",");
    for (const code of codes) found.add(`${tooth},${code}`);
  }
  return found;
}

// Zeilen aus `lines`, die nur die Positionen enthalten, die in `other` fehlen.
function missing(lines: string[], other: string[]): string[] {
  const known = pairs(other);
  const out: string[] = [];
  for (const line of lines) {
    const [tooth, ...codes] = line.split(",");
    const rest = codes.filter((code) => !known.has(`${tooth},${code}`));
    if (rest.length > 0) out.push([tooth, ...rest].join(","));
  }
  return out;
}

export type HandoverDiff = {
  added: string[]; // neu seit den Abholungen – nur diese in Evident nachtragen
  removed: string[]; // schon abgeholt, jetzt nicht mehr im Diktat – in Evident prüfen
};

export function handoverDiff(current: string[], earlier: Handover[]): HandoverDiff {
  const before = earlier.flatMap((h) => h.codes);
  return { added: missing(current, before), removed: missing(before, current) };
}
