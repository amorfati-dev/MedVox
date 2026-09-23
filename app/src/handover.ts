// Schon per Kurzcode abgeholte Stände eines Diktats mit dem aktuellen vergleichen: je Zahn und
// Position mit Anzahl (so wie in den Evident-Zeilen, "36,wf*3"), damit Rezeption und Büro nur die
// Änderung eintragen. Mit Endung, damit `node --test` das Modul direkt laden kann.
import type { Handover } from "./api.ts";

// Evident-Zeilen ("36,13c,wf*2"; ohne Zahn ",01") als Zahn → Position → Anzahl.
type Counts = Map<string, Map<string, number>>;

function counts(lines: string[], into: Counts = new Map()): Counts {
  for (const line of lines) {
    const [tooth, ...tokens] = line.split(",");
    const row = into.get(tooth) ?? new Map<string, number>();
    into.set(tooth, row);
    for (const token of tokens) {
      const m = /^(.+)\*(\d+)$/.exec(token);
      const [form, n] = m ? [m[1], Number(m[2])] : [token, 1];
      // Jede Abholung nach der ersten trägt nur die Änderung ein: in Evident steht das Höchste.
      row.set(form, Math.max(row.get(form) ?? 0, n));
    }
  }
  return into;
}

function token(form: string, n: number): string {
  return n > 1 ? `${form}*${n}` : form;
}

// Positionen aus `a`, die in `b` ganz fehlen, als Evident-Zeilen.
function absent(a: Counts, b: Counts): string[] {
  const out: string[] = [];
  for (const [tooth, row] of a) {
    const rest = [...row].filter(([form]) => !b.get(tooth)?.has(form)).map(([form, n]) => token(form, n));
    if (rest.length > 0) out.push([tooth, ...rest].join(","));
  }
  return out;
}

export type HandoverDiff = {
  added: string[]; // ganz neu seit den Abholungen – nur diese in Evident nachtragen
  removed: string[]; // schon abgeholt, jetzt nicht mehr im Diktat – in Evident prüfen
  changed: string[]; // nur die Anzahl geändert, als Satz ("36: wf jetzt 3× statt 2× – 1× nachtragen")
};

export function handoverDiff(current: string[], earlier: Handover[]): HandoverDiff {
  const now = counts(current);
  const before = new Map() as Counts;
  for (const h of earlier) counts(h.codes, before);
  const changed: string[] = [];
  for (const [tooth, row] of now) {
    for (const [form, n] of row) {
      const was = before.get(tooth)?.get(form);
      if (was === undefined || was === n) continue;
      const where = tooth === "" ? "ohne Zahn" : tooth;
      const what = n > was ? `${n - was}× nachtragen` : `${was - n}× zu viel in Evident – prüfen`;
      changed.push(`${where}: ${form} jetzt ${n}× statt ${was}× – ${what}`);
    }
  }
  return { added: absent(now, before), removed: absent(before, now), changed };
}
