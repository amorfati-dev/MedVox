// Speichert das laufende Diktat beim Patienten auf dem Praxis-Mac, damit es später im Büro
// übertragen werden kann. Jede Änderung (neuer Abschnitt, Auswahl, Patientennummer) ersetzt den
// gespeicherten Stand; Aufträge laufen nacheinander und werden bei einem Fehler wiederholt, bis sie
// ankommen – auch für ein Diktat, das am Bildschirm schon vom nächsten abgelöst wurde. Lehnt der
// Server ein Diktat als schon übertragen ab (410), wird es nie wieder gespeichert.
import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, type DictationBody, type HandoverLink } from "../api";
import { newDictationId } from "../patients";

const RETRY_MS = 5000;

// aus: nichts zu speichern; speichert: Auftrag läuft oder wartet; gespeichert: aktueller Stand liegt
// auf dem Praxis-Mac; fehler: letzter Versuch fehlgeschlagen, wird wiederholt; übertragen: schon
// übertragen, gelöscht oder abgelaufen – nur ein neues Diktat geht weiter.
export type SaveState = "aus" | "speichert" | "gespeichert" | "fehler" | "übertragen";

export type DictationSave = {
  state: SaveState;
  error: string | null;
  backlog: number; // abgelöste Diktate, deren Speichern noch aussteht
  handover: () => HandoverLink | null; // Diktat am Bildschirm und sein gespeicherter Stand (für den Kurzcode)
  detach: () => void; // Diktat ist fertig: das nächste bekommt eine neue ID
  discard: () => void; // Diktat verwerfen: auch den gespeicherten Stand löschen
};

type Job = DictationBody | "löschen";

// `body`: aktueller Stand, null solange das Diktat noch kein Ergebnis hat.
export function useDictationSave(body: DictationBody | null, onUnauthorized: () => void): DictationSave {
  const [state, setState] = useState<SaveState>("aus");
  const [error, setError] = useState<string | null>(null);
  const [backlog, setBacklog] = useState(0);
  const current = useRef<string | null>(null); // ID des Diktats am Bildschirm
  const saved = useRef<string | null>(null); // zuletzt gespeicherter Stand (JSON) des aktuellen Diktats
  const revision = useRef<number | null>(null); // Revision dieses Stands auf dem Praxis-Mac
  const closed = useRef<string | null>(null); // aktuelles Diktat, das der Server als übertragen ablehnt
  const left = useRef<string | null>(null); // Stand des abgelösten Diktats: nie unter neuer ID anlegen
  const reported = useRef(false); // abgelaufene Sitzung nur einmal je Fehlerserie melden
  const jobs = useRef(new Map<string, Job>()); // je Diktat nur der neueste Auftrag
  const running = useRef(false);
  const retry = useRef<number | null>(null);
  const unauthorized = useRef(onUnauthorized);
  unauthorized.current = onUnauthorized;

  const show = useCallback(() => {
    const id = current.current;
    setBacklog([...jobs.current.keys()].filter((k) => k !== id).length);
    if (id !== null && id === closed.current) setState("übertragen");
    else if (id !== null && jobs.current.has(id)) setState((s) => (s === "fehler" ? s : "speichert"));
    else setState(id !== null && saved.current !== null ? "gespeichert" : "aus");
  }, []);

  const run = useCallback(async () => {
    if (running.current) return;
    running.current = true;
    if (retry.current !== null) window.clearTimeout(retry.current);
    retry.current = null;
    try {
      while (jobs.current.size > 0) {
        const [id, job] = jobs.current.entries().next().value as [string, Job];
        let stored: number | null = null;
        try {
          if (job === "löschen") await api.deleteDictation(id).catch(ignoreMissing);
          else stored = (await api.saveDictation(id, job)).revision;
        } catch (e) {
          if (e instanceof ApiError && e.status === 410) {
            jobs.current.delete(id);
            if (id === current.current) closed.current = id;
            setError(null);
            show();
            continue;
          }
          if (e instanceof ApiError && e.status === 401 && !reported.current) {
            reported.current = true;
            unauthorized.current();
          }
          setError(e instanceof ApiError ? e.message : "Speichern fehlgeschlagen.");
          setState("fehler");
          retry.current = window.setTimeout(() => void run(), RETRY_MS);
          return;
        }
        // Kam während der Anfrage ein neuerer Stand, bleibt dessen Auftrag stehen.
        if (jobs.current.get(id) === job) jobs.current.delete(id);
        if (id === current.current && job !== "löschen") {
          saved.current = JSON.stringify(job);
          revision.current = stored;
        }
        reported.current = false;
        setError(null);
        setState("speichert");
        show();
      }
    } finally {
      running.current = false;
      if (jobs.current.size === 0) show();
    }
  }, [show]);

  useEffect(() => {
    if (body === null) {
      left.current = null; // neues Diktat begonnen
      return;
    }
    const json = JSON.stringify(body);
    if (current.current === null) {
      if (json === left.current) return;
      current.current = newDictationId();
      saved.current = null;
      revision.current = null;
    }
    if (json === saved.current || current.current === closed.current) return;
    jobs.current.delete(current.current); // Reihenfolge: der neueste Stand kommt ans Ende
    jobs.current.set(current.current, body);
    show();
    void run();
  }, [body, run, show]);

  useEffect(
    () => () => {
      if (retry.current !== null) window.clearTimeout(retry.current);
    },
    [],
  );

  // Revision nur, wenn genau der Stand am Bildschirm gespeichert ist; sonst schließt der Kurzcode nichts Neueres.
  const handover = useCallback((): HandoverLink | null => {
    const id = current.current;
    if (id === null || id === closed.current) return null;
    return { id, revision: saved.current !== null && !jobs.current.has(id) ? revision.current : null };
  }, []);

  const detach = useCallback(() => {
    left.current = body === null ? null : JSON.stringify(body);
    current.current = null;
    saved.current = null;
    show();
  }, [body, show]);

  const discard = useCallback(() => {
    const id = current.current;
    left.current = body === null ? null : JSON.stringify(body);
    current.current = null;
    saved.current = null;
    if (id !== null && id !== closed.current) {
      jobs.current.delete(id);
      jobs.current.set(id, "löschen");
      void run();
    }
    show();
  }, [body, run, show]);

  return { state, error, backlog, handover, detach, discard };
}

function ignoreMissing(e: unknown): void {
  if (!(e instanceof ApiError && e.status === 404)) throw e;
}
