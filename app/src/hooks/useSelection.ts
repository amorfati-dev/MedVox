// Auswahl in der Ergebnisliste: abgewählte Ziffern (wie früher die Chips) und übernommene
// Zuzahlungs-Optionen (E4: abgewählt voreingestellt, per Tipp übernehmbar). Daraus die Evident-Zeilen
// für „Ziffern kopieren“ (beim Kassenpatienten auch je Block), „Nur Ziffern“ und die Übergabe an die Rezeption.
import { useCallback, useMemo, useState } from "react";
import { codeOf, joinBlocks, type EvidentBlocks, type Suggestion } from "../api";
import { buildGroups, copyBlocks, copyLines, type Group } from "../result";

export type Selection = {
  groups: Group[]; // Ergebnisliste nach Zahn
  evident: string[]; // Kopier- und Übergabeformat (Kurzformen): Kassenblock, Leerzeile, Privatblock
  blocks: EvidentBlocks; // dieselben Zeilen je Block („Kassenleistungen/Privatleistungen kopieren“)
  numbers: string[]; // „Nur Ziffern“
  toggleCode: (code: string) => void; // Ziffer ohne Anzahl ("41a"); gilt für alle Zähne mit dieser Ziffer
  toggleOption: (key: string) => void; // optionKey
  clear: () => void;
};

// `codes`: Ziffern im Kopierformat ("2x 41a") aus der Warteschlange.
export function useSelection(codes: string[], suggestions: Suggestion[]): Selection {
  // Abgewählte Ziffern merken; neu vorgeschlagene gelten damit automatisch als gewählt.
  const [deselected, setDeselected] = useState<ReadonlySet<string>>(() => new Set());
  const [adopted, setAdopted] = useState<ReadonlySet<string>>(() => new Set());
  const active = useMemo(() => codes.filter((c) => !deselected.has(c)), [codes, deselected]);
  // Kopier- und Übergabeformat für Evident: je Zahn eine Zeile, Zahn vorn.
  const blocks = useMemo(() => copyBlocks(suggestions, active, adopted), [suggestions, active, adopted]);
  const evident = useMemo(() => joinBlocks(blocks), [blocks]);
  const numbers = useMemo(() => copyLines(suggestions, active, adopted, false), [suggestions, active, adopted]);
  const groups = useMemo(() => buildGroups(suggestions, active, adopted, evident), [suggestions, active, adopted, evident]);

  const toggleCode = useCallback(
    (code: string) => {
      const key = codes.find((c) => codeOf(c) === code);
      if (!key) return;
      setDeselected((prev) => {
        const next = new Set(prev);
        if (!next.delete(key)) next.add(key);
        return next;
      });
    },
    [codes],
  );

  const toggleOption = useCallback((key: string) => {
    setAdopted((prev) => {
      const next = new Set(prev);
      if (!next.delete(key)) next.add(key);
      return next;
    });
  }, []);

  const clear = useCallback(() => {
    setDeselected(new Set());
    setAdopted(new Set());
  }, []);

  return { groups, evident, blocks, numbers, toggleCode, toggleOption, clear };
}
