// Korrektur am iPad (nur hier, das Büro liest nur): Transkript bearbeiten und Ziffern neu berechnen
// (POST /api/v1/analyze, ohne Audio), Ziffer im Katalog-Blatt ersetzen oder ergänzen, eine Stufe
// „Rückgängig“. Die Rechnung liegt in correction.ts; hier nur Zustand und Server-Aufrufe. Der Inhalt
// liegt weiter in der Warteschlange (useUploadQueue.replace), die Auswahl in useSelection.restore.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, ApiError, type PatientType, type Suggestion } from "../api";
import { byCode, codesOf, mainPositions, toothOf, type CatalogEntry } from "../catalog";
import { addPosition, keepAdopted, recompute, remapDeselected, replaceFamily, type Content } from "../correction";
import { applyTap, tapTarget, type TapState } from "../teeth";
import { codeChanges, type Change } from "../textdiff";
import type { Dictation } from "./useDictation";
import type { Selection } from "./useSelection";
import { loadCatalog, useCatalog } from "./useCatalog";

// Katalog-Blatt: für einen Zahn (null = ohne Zahn) oder erst den Zahn wählen („wählen“).
export type SheetTarget = { tooth: number | null } | "wählen";

type Undo = {
  content: Content;
  choice: { deselected: string[]; adopted: string[] };
  corrected: boolean;
  after: Suggestion[]; // gilt nur, solange genau diese Vorschläge angezeigt werden (kein neuer Abschnitt)
  title: string;
  changes: Change[];
};

export type Correction = {
  editing: boolean;
  startEdit: () => void;
  cancelEdit: () => void;
  applyText: (text: string) => Promise<void>; // „Übernehmen · Ziffern neu berechnen“
  busy: boolean;
  error: string | null;
  sheet: SheetTarget | null;
  openSheet: (target: SheetTarget) => void;
  closeSheet: () => void;
  catalog: CatalogEntry[] | null;
  catalogError: string | null;
  add: (entry: CatalogEntry, tooth: number | null) => void;
  replace: (tooth: number | null, from: string, to: CatalogEntry) => void;
  remove: (s: Suggestion) => void; // Zeile „von Hand“ wieder entfernen
  // Zahnschema: Ziffern der Je-Zahn-Position, deren Zähne gerade angetippt werden (null = Blatt zu)
  tap: string[] | null;
  tapCodes: (code: string) => string[] | null; // Je-Zahn-Position laut Katalog: ihre Ziffern, sonst null
  openTap: (code: string) => void;
  closeTap: () => void;
  applyTeeth: (state: TapState) => void; // „Übernehmen“
  notice: { title: string; changes: Change[] } | null; // Streifen mit „Rückgängig“
  undo: () => void;
};

export function useCorrection(d: Dictation, sel: Selection, fallback: PatientType): Correction {
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sheet, setSheet] = useState<SheetTarget | null>(null);
  const [last, setLast] = useState<Undo | null>(null);
  const [tap, setTap] = useState<string[] | null>(null);
  const type = d.resultType ?? fallback;
  // Mit Ergebnis gleich laden: welche Zeile „Zähne antippen“ bekommt, steht im Katalog.
  const cat = useCatalog(type, sheet !== null || d.suggestions.length > 0);
  const catalogMap = useMemo(() => byCode(cat.entries ?? []), [cat.entries]);
  // Angezeigte Vorschläge; ändern sie sich während /analyze läuft (anderer Patient, anderer Behandler,
  // neuer Abschnitt), gehört das Ergebnis nicht mehr zu diesem Stand und wird verworfen.
  const shown = useRef(d.suggestions);
  shown.current = d.suggestions;

  // Bildschirm geleert (anderer Patient, anderer Behandler, neues Diktat): nichts mehr offen lassen,
  // sonst landete der alte Text im nächsten Diktat.
  const empty = d.transcript === "" && d.suggestions.length === 0;
  useEffect(() => {
    if (!empty) return;
    setEditing(false);
    setSheet(null);
    setTap(null);
    setLast(null);
  }, [empty]);

  const commit = useCallback(
    (next: Content, title: string, map: Map<string, CatalogEntry>, adopted = sel.adopted) => {
      const before: Content = { transcript: d.transcript, codes: d.codes, suggestions: d.suggestions, planned: d.planned, notes: d.notes, teeth: d.teeth };
      setLast({
        content: before,
        choice: { deselected: sel.deselected, adopted: sel.adopted },
        corrected: d.corrected,
        after: next.suggestions,
        title,
        changes: codeChanges(mainPositions(d.suggestions), mainPositions(next.suggestions), map),
      });
      d.replace(next, true);
      sel.restore({ deselected: remapDeselected(sel.deselected, next.codes), adopted: keepAdopted(adopted, next.suggestions) });
    },
    [d, sel],
  );

  const applyText = useCallback(
    async (text: string) => {
      if (text.trim() === d.transcript.trim()) {
        setEditing(false);
        return;
      }
      setBusy(true);
      setError(null);
      const start = d.suggestions;
      try {
        const [result, entries] = await Promise.all([api.analyze(text, type), loadCatalog(type)]);
        if (shown.current !== start) return;
        const map = byCode(entries);
        const suggestions = recompute(d.suggestions, result.suggestions, map);
        const next = {
          transcript: result.transcript,
          codes: codesOf(suggestions),
          suggestions,
          planned: result.planned ?? [],
          notes: result.notes ?? [],
          teeth: result.teeth ?? [],
        };
        commit(next, "Ziffern neu berechnet", map);
        setEditing(false);
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) d.sessionExpired();
        setError(e instanceof ApiError ? e.message : "Neu berechnen fehlgeschlagen – der Text bleibt zum erneuten Versuch.");
      } finally {
        setBusy(false);
      }
    },
    [d, type, commit],
  );

  const content = (suggestions: Suggestion[]): Content => ({
    transcript: d.transcript,
    codes: codesOf(suggestions),
    suggestions,
    planned: d.planned,
    notes: d.notes,
    teeth: d.teeth,
  });

  const remove = (s: Suggestion) => {
    const same = (x: Suggestion) => x.source === "hand" && !x.alternative && x.code === s.code && toothOf(x) === toothOf(s);
    commit(content(d.suggestions.filter((x) => !same(x))), "Ziffer entfernt", catalogMap);
  };

  const add = (entry: CatalogEntry, tooth: number | null) =>
    commit(content(addPosition(d.suggestions, entry, tooth)), "Ziffer ergänzt", catalogMap);

  const replace = (tooth: number | null, from: string, to: CatalogEntry) => {
    const next = replaceFamily(d.suggestions, sel.adopted, tooth, from, to, catalogMap);
    commit(content(next.suggestions), "Ziffer geändert", catalogMap, next.adopted);
  };

  const applyTeeth = (state: TapState) => {
    if (tap === null) return;
    const title = state.teeth.length > 0 ? "Zähne angetippt" : "Position entfernt";
    commit(content(applyTap(d.suggestions, tap, state, catalogMap)), title, catalogMap);
    setTap(null);
  };

  const valid = last !== null && last.after === d.suggestions;
  const undo = () => {
    if (!valid) return;
    d.replace(last.content, last.corrected);
    sel.restore(last.choice);
    setLast(null);
  };

  return {
    editing,
    startEdit: () => {
      setError(null);
      setEditing(true);
    },
    cancelEdit: () => setEditing(false),
    applyText,
    busy,
    error,
    sheet,
    openSheet: setSheet,
    closeSheet: () => setSheet(null),
    catalog: cat.entries,
    catalogError: cat.error,
    add,
    replace,
    remove,
    tap,
    tapCodes: (code) => tapTarget(code, catalogMap),
    openTap: (code) => setTap(tapTarget(code, catalogMap)),
    closeTap: () => setTap(null),
    applyTeeth,
    notice: valid ? { title: last.title, changes: last.changes } : null,
    undo,
  };
}
