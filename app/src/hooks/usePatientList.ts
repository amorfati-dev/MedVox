// Büro: Patientenliste und den gewählten Patienten laden; neu bei jeder Änderung auf dem Server
// (Live-Strom, `live.ts`), ohne Strom alle 30 Sekunden, und beim Zurückkehren ins Fenster –
// damit Diktate von den iPads ohne Neuladen erscheinen.
import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, type PatientDetail, type PatientList } from "../api";
import { coalesce, watchChanges, type LiveMode } from "../live";

export type PatientListState = {
  list: PatientList | null;
  detail: PatientDetail | null; // gewählter Patient; null, wenn keiner gewählt oder nicht mehr da
  error: string | null;
  live: LiveMode | null; // null, solange noch offen ist, ob der Strom steht
  refresh: () => Promise<void>;
  setDetail: (detail: PatientDetail | null) => void;
};

export function usePatientList(patientId: number | null, onUnauthorized: () => void): PatientListState {
  const [list, setList] = useState<PatientList | null>(null);
  const [detail, setDetail] = useState<PatientDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [live, setLive] = useState<LiveMode | null>(null);
  const selected = useRef(patientId);
  selected.current = patientId;
  const unauthorized = useRef(onUnauthorized);
  unauthorized.current = onUnauthorized;

  const load = useCallback(async () => {
    const id = selected.current;
    try {
      const [all, one] = await Promise.all([
        api.listPatients(),
        id === null ? null : api.getPatient(id).catch((e: unknown) => (e instanceof ApiError && e.status === 404 ? null : Promise.reject(e))),
      ]);
      setList(all);
      if (selected.current === id) setDetail(one);
      setError(null);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) unauthorized.current();
      else setError(e instanceof ApiError ? e.message : "Liste nicht erreichbar.");
    }
  }, []);
  // Ereignisse, Abgleich und „Aktualisieren“ teilen sich einen Abruf: nie zwei gleichzeitig.
  const [refresh] = useState(() => coalesce(load));

  useEffect(() => {
    setDetail(null);
    void refresh();
  }, [patientId, refresh]);

  useEffect(() => {
    const stop = watchChanges({
      onChange: () => void refresh(),
      onMode: setLive,
      open: typeof EventSource === "undefined" ? null : (url) => new EventSource(url),
    });
    const onVisible = () => document.visibilityState === "visible" && void refresh();
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      stop();
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [refresh]);

  return { list, detail, error, live, refresh, setDetail };
}
