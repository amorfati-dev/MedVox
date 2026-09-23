// Upload-Warteschlange: aufgenommene Abschnitte in Aufnahmereihenfolge an
// /api/v1/transcribe schicken. Kein Fehlerpfad verwirft Audio – bei einem
// Fehler bleibt der Abschnitt am Kopf der Warteschlange stehen.
import { useCallback, useRef, useState, type RefObject } from "react";
import { api, ApiError, kindsOf, type PatientType, type Suggestion, type SuggestionKind } from "../api";
import { filenameFor } from "./recorder";

// Fehler, die eine Wiederholung desselben Abschnitts nie bestehen würde.
const PERMANENT_STATUS = [400, 413, 415];

export type UploadQueue = {
  waiting: number; // Abschnitte in der Warteschlange (inkl. laufender Übertragung)
  uploading: boolean; // Übertragung läuft
  blocked: boolean; // Warteschlange steht nach einem Fehler
  permanent: boolean; // der wartende Abschnitt wird dauerhaft abgelehnt
  sessionLost: boolean; // Server antwortete 401
  transcript: string;
  codes: string[];
  kinds: Record<string, SuggestionKind>; // Art je Ziffer (bema, goz, zuzahlung)
  suggestions: Suggestion[]; // Vorschläge aller Abschnitte in Diktatreihenfolge (Zahnzuordnung)
  resultType: PatientType | null; // Patiententyp, für den die Ziffern berechnet wurden
  lastLatency: number | null;
  error: string | null;
  setError: (message: string | null) => void;
  enqueue: (blob: Blob) => void;
  resume: () => void; // angehaltene Warteschlange fortsetzen
  dropSegment: () => void; // nur den wartenden Abschnitt verwerfen
  sessionExpired: () => void; // 401 aus einem anderen Aufruf
  relogin: () => void;
  reset: () => void; // Transkript und wartende Abschnitte verwerfen
};

// `patientType` hält den Patiententyp des laufenden Diktats; jeder Abschnitt wird damit ausgewertet.
export function useUploadQueue(onSessionLost: () => void, patientType: RefObject<PatientType>): UploadQueue {
  const [waiting, setWaiting] = useState(0);
  const [paused, setPaused] = useState(false);
  const [permanent, setPermanent] = useState(false);
  const [sessionLost, setSessionLost] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [codes, setCodes] = useState<string[]>([]);
  const [kinds, setKinds] = useState<Record<string, SuggestionKind>>({});
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [resultType, setResultType] = useState<PatientType | null>(null);
  const [lastLatency, setLastLatency] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const queue = useRef<Blob[]>([]);
  const draining = useRef(false);
  const halted = useRef(false);
  const epoch = useRef(0); // steigt beim Verwerfen; entwertet laufende Übertragungen

  const halt = useCallback(
    (unauthorized: boolean) => {
      halted.current = true;
      setPaused(true);
      if (!unauthorized) return;
      setSessionLost(true);
      onSessionLost();
    },
    [onSessionLost],
  );

  const drain = useCallback(async () => {
    if (draining.current || halted.current) return;
    draining.current = true;
    try {
      while (queue.current.length > 0 && !halted.current) {
        const blob = queue.current[0];
        const mine = epoch.current;
        try {
          const result = await api.transcribe(blob, filenameFor(blob.type), patientType.current);
          if (mine !== epoch.current) continue;
          const text = result.transcript.trim();
          setTranscript((prev) => (prev && text ? `${prev} ${text}` : prev || text));
          setCodes((prev) => Array.from(new Set([...prev, ...result.codes])));
          setKinds((prev) => ({ ...prev, ...kindsOf(result.suggestions) }));
          setSuggestions((prev) => [...prev, ...result.suggestions]);
          setResultType(result.patient_type);
          setLastLatency(result.latency_s);
          setError(null);
        } catch (e) {
          if (mine !== epoch.current) continue;
          const unauthorized = e instanceof ApiError && e.status === 401;
          halt(unauthorized);
          if (!unauthorized) {
            setPermanent(e instanceof ApiError && PERMANENT_STATUS.includes(e.status));
            setError(e instanceof ApiError ? e.message : "Unbekannter Fehler beim Hochladen.");
          }
          return;
        }
        queue.current.shift();
        setWaiting(queue.current.length);
      }
    } finally {
      draining.current = false;
    }
  }, [halt, patientType]);

  const enqueue = useCallback(
    (blob: Blob) => {
      if (blob.size === 0) {
        setError("Keine Audiodaten aufgenommen.");
        return;
      }
      queue.current.push(blob);
      setWaiting(queue.current.length);
      void drain();
    },
    [drain],
  );

  const resume = useCallback(() => {
    setError(null);
    setPermanent(false);
    halted.current = false;
    setPaused(false);
    void drain();
  }, [drain]);

  // Dauerhaft abgelehnten Abschnitt einzeln verwerfen; Transkript bleibt unberührt.
  const dropSegment = useCallback(() => {
    queue.current.shift();
    setWaiting(queue.current.length);
    resume();
  }, [resume]);

  const reset = useCallback(() => {
    epoch.current += 1;
    queue.current = [];
    halted.current = false;
    setWaiting(0);
    setPaused(false);
    setPermanent(false);
    setTranscript("");
    setCodes([]);
    setKinds({});
    setSuggestions([]);
    setResultType(null);
    setLastLatency(null);
    setError(null);
  }, []);

  return {
    waiting,
    uploading: waiting > 0 && !paused,
    blocked: waiting > 0 && paused,
    permanent,
    sessionLost,
    transcript,
    codes,
    kinds,
    suggestions,
    resultType,
    lastLatency,
    error,
    setError,
    enqueue,
    resume,
    dropSegment,
    sessionExpired: () => halt(true),
    relogin: () => setSessionLost(false),
    reset,
  };
}
