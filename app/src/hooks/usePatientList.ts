// Büro: Patientenliste und den gewählten Patienten laden; alle 30 Sekunden und beim Zurückkehren
// ins Fenster neu, damit Diktate von den iPads ohne Neuladen erscheinen.
import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, type PatientDetail, type PatientList } from "../api";

const REFRESH_MS = 30_000;

export type PatientListState = {
  list: PatientList | null;
  detail: PatientDetail | null; // gewählter Patient; null, wenn keiner gewählt oder nicht mehr da
  error: string | null;
  refresh: () => Promise<void>;
  setDetail: (detail: PatientDetail | null) => void;
};

export function usePatientList(patientId: number | null, onUnauthorized: () => void): PatientListState {
  const [list, setList] = useState<PatientList | null>(null);
  const [detail, setDetail] = useState<PatientDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const selected = useRef(patientId);
  selected.current = patientId;
  const unauthorized = useRef(onUnauthorized);
  unauthorized.current = onUnauthorized;

  const refresh = useCallback(async () => {
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

  useEffect(() => {
    setDetail(null);
    void refresh();
  }, [patientId, refresh]);

  useEffect(() => {
    const timer = window.setInterval(() => void refresh(), REFRESH_MS);
    const onVisible = () => document.visibilityState === "visible" && void refresh();
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [refresh]);

  return { list, detail, error, refresh, setDetail };
}
