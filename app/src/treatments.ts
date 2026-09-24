// Kopieren je Behandlung: mehrere Zähne in einem Diktat sollen einzeln nach Evident, sonst geraten die
// Positionen beim Einfügen durcheinander. Eine Behandlung ist ein Zahn (bzw. die Zeile ohne Zahn); ihre
// Zeilen sind genau die Zeilen dieses Zahns aus dem Gesamt-Kopiertext, Kassen- und Privatzeile getrennt
// (Evident setzt nach einer Privatposition alles Folgende auf privat). Getestet in test/treatments.test.ts.
// Mit Endung, damit `node --test` das Modul direkt laden kann (allowImportingTsExtensions).
import { isToothless, type EvidentBlocks } from "./api.ts";

export type Treatment = { tooth: string | null; kasse: string[]; privat: string[] }; // tooth null = ohne Zahn

// Reihenfolge wie im Gesamttext: Zähne in erster Nennung, die Zeile ohne Zahn zuletzt.
export function treatments({ kasse, privat }: EvidentBlocks): Treatment[] {
  const byTooth = new Map<string | null, Treatment>();
  const add = (line: string, block: "kasse" | "privat") => {
    const tooth = isToothless(line) ? null : line.split(",")[0];
    let t = byTooth.get(tooth);
    if (!t) {
      t = { tooth, kasse: [], privat: [] };
      byTooth.set(tooth, t);
    }
    t[block].push(line);
  };
  for (const line of kasse) add(line, "kasse");
  for (const line of privat) add(line, "privat");
  return [...byTooth.values()].sort((a, b) => Number(a.tooth === null) - Number(b.tooth === null));
}

// Beschriftung der Kopieraktion; beim Kassenpatienten (`labelled`) immer mit Kasse/Privat.
export function treatmentLabel(tooth: string | null, block: "kasse" | "privat" | null): string {
  const what = tooth === null ? "Ohne Zahn" : `Zahn ${tooth}`;
  return block === null ? `${what} kopieren` : `${what} ${block === "kasse" ? "Kasse" : "Privat"} kopieren`;
}
