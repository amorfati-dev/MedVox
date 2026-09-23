// Patiententyp (Kasse/Privat) für das nächste Diktat; bleibt im localStorage zwischen Sitzungen erhalten.
import { useCallback, useState } from "react";
import { parsePatientType, type PatientType } from "../api";

const STORAGE_KEY = "medvox.patientType";

function load(): PatientType {
  try {
    return parsePatientType(window.localStorage.getItem(STORAGE_KEY));
  } catch {
    return "kasse"; // Speicher gesperrt (privates Surfen): Standard des Servers
  }
}

export function usePatientType(): [PatientType, (type: PatientType) => void] {
  const [type, setType] = useState<PatientType>(load);
  const change = useCallback((next: PatientType) => {
    setType(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* nicht speicherbar: gilt nur bis zum Neuladen */
    }
  }, []);
  return [type, change];
}
