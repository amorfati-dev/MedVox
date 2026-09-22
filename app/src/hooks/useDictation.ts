// Aufnahme-Hook: MediaRecorder-Segmente aufnehmen, in Aufnahmereihenfolge an
// /api/v1/transcribe schicken und die Transkripte aneinanderhängen.
import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "../api";
import {
  filenameFor,
  MIC_MESSAGES,
  pickMimeType,
  requestMicrophone,
  startLevelMeter,
  stopStream,
  type LevelMeter,
} from "./recorder";

export const MAX_SECONDS = 60; // Server-Limit pro Abschnitt
// Automatischer Stopp knapp unter dem Server-Limit (Ticker-Raster, Anlaufzeit).
export const AUTO_STOP_SECONDS = MAX_SECONDS - 1;

// "fortsetzbar": die Aufnahme wurde unterbrochen (Zeitlimit oder abgelaufene
// Sitzung), das Diktat bleibt erhalten – „Weiter“ hängt an, „Neues Diktat“ beginnt neu.
export type DictationPhase = "bereit" | "aufnahme" | "sende" | "fortsetzbar";

export type Dictation = {
  phase: DictationPhase;
  seconds: number; // Laufzeit des aktuellen Segments
  remaining: number; // Sekunden bis zum automatischen Stopp
  level: number; // Pegel 0..1
  uploading: boolean; // ein Abschnitt wird gerade transkribiert
  waiting: number; // Abschnitte, die auf die Übertragung warten
  transcript: string;
  codes: string[];
  error: string | null;
  lastLatency: number | null;
  supported: boolean; // MediaRecorder mit passendem MIME vorhanden
  sessionLost: boolean; // Server antwortete 401; Diktat und offene Abschnitte bleiben erhalten
  sessionExpired: () => void; // 401 aus einem anderen Aufruf: Aufnahme unterbrechen
  relogin: () => void; // nach erneuter Anmeldung zurück in den fortsetzbaren Zustand
  start: () => Promise<void>; // neues Diktat: verwirft das bisherige Transkript
  resume: () => Promise<void>; // "Weiter" nach einer Unterbrechung: anhängen
  stop: () => void; // beendet das Segment und lädt es hoch
  next: () => void; // "Weiter": Segment hochladen, Aufnahme läuft auf demselben Stream weiter
  reset: () => void; // Transkript und offene Abschnitte verwerfen
  setCodes: (codes: string[]) => void;
};

export function useDictation(): Dictation {
  const [recording, setRecording] = useState(false);
  const [waiting, setWaiting] = useState(0); // Länge der Upload-Warteschlange
  const [paused, setPaused] = useState(false); // Warteschlange angehalten (401)
  const [resumable, setResumable] = useState(false);
  const [sessionLost, setSessionLost] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [level, setLevel] = useState(0);
  const [transcript, setTranscript] = useState("");
  const [codes, setCodes] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [lastLatency, setLastLatency] = useState<number | null>(null);

  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const meter = useRef<LevelMeter | null>(null);
  const chunks = useRef<Blob[]>([]);
  const ticker = useRef<number | null>(null);
  const continueAfter = useRef(false);
  const starting = useRef(false);
  const queue = useRef<Blob[]>([]); // Abschnitte in Aufnahmereihenfolge
  const draining = useRef(false);
  const halted = useRef(false);
  const mime = useRef<string | null>(pickMimeType());

  const clearTimers = useCallback(() => {
    if (ticker.current !== null) window.clearInterval(ticker.current);
    ticker.current = null;
    meter.current?.stop();
    meter.current = null;
    setLevel(0);
  }, []);

  const release = useCallback(() => {
    clearTimers();
    stopStream(stream.current);
    stream.current = null;
    recorder.current = null;
    setRecording(false);
  }, [clearTimers]);

  useEffect(() => release, [release]);

  // Sitzung abgelaufen: Aufnahme beenden, Warteschlange anhalten, nichts verwerfen.
  const sessionExpired = useCallback(() => {
    halted.current = true;
    setPaused(true);
    setSessionLost(true);
    setResumable(true);
    const rec = recorder.current;
    if (rec?.state === "recording") {
      continueAfter.current = false;
      rec.stop();
    }
  }, []);

  const drain = useCallback(async () => {
    if (draining.current || halted.current) return;
    draining.current = true;
    try {
      while (queue.current.length > 0 && !halted.current) {
        const blob = queue.current[0];
        try {
          const result = await api.transcribe(blob, filenameFor(blob.type || mime.current || ""));
          const text = result.transcript.trim();
          setTranscript((prev) => (prev && text ? `${prev} ${text}` : prev || text));
          setCodes((prev) => Array.from(new Set([...prev, ...result.codes])));
          setLastLatency(result.latency_s);
        } catch (e) {
          if (e instanceof ApiError && e.status === 401) {
            sessionExpired();
            break;
          }
          setError(e instanceof ApiError ? e.message : "Unbekannter Fehler beim Hochladen.");
        }
        queue.current.shift();
        setWaiting(queue.current.length);
      }
    } finally {
      draining.current = false;
    }
  }, [sessionExpired]);

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

  const relogin = useCallback(() => setSessionLost(false), []);

  // Ein Segment auf dem offenen Mikrofon-Stream aufnehmen; Uploads laufen nacheinander.
  const startSegment = useCallback(
    (mic: MediaStream): void => {
      const rec = new MediaRecorder(mic, { mimeType: mime.current ?? undefined });
      chunks.current = [];
      rec.ondataavailable = (ev) => {
        if (ev.data.size > 0) chunks.current.push(ev.data);
      };
      rec.onstop = () => {
        const blob = new Blob(chunks.current, { type: rec.mimeType || mime.current || "" });
        chunks.current = [];
        const again = continueAfter.current;
        continueAfter.current = false;
        clearTimers();
        enqueue(blob);
        if (!again) {
          release();
          return;
        }
        try {
          startSegment(mic);
        } catch {
          release();
          setError("Aufnahme konnte nicht fortgesetzt werden (MediaRecorder).");
        }
      };
      rec.start(250);
      recorder.current = rec;
      meter.current = startLevelMeter(mic, setLevel);
      const startedAt = Date.now();
      setSeconds(0);
      setRecording(true);
      setResumable(false);
      ticker.current = window.setInterval(() => {
        const elapsedMs = Date.now() - startedAt;
        setSeconds(Math.floor(elapsedMs / 1000));
        if (elapsedMs >= AUTO_STOP_SECONDS * 1000 && rec.state === "recording") {
          rec.stop();
          setResumable(true);
        }
      }, 250);
    },
    [clearTimers, enqueue, release],
  );

  const reset = useCallback(() => {
    queue.current = [];
    halted.current = false;
    setWaiting(0);
    setPaused(false);
    setTranscript("");
    setCodes([]);
    setError(null);
    setLastLatency(null);
    setResumable(false);
  }, []);

  // Mikrofon holen und das erste Segment starten; `append` behält das Diktat.
  const begin = useCallback(
    async (append: boolean) => {
      if (recorder.current || starting.current) return;
      if (!mime.current) {
        setError("Dieser Browser unterstützt keine Audioaufnahme (MediaRecorder fehlt).");
        return;
      }
      starting.current = true;
      try {
        if (append) {
          setError(null);
          halted.current = false;
          setPaused(false);
          void drain();
        } else {
          reset();
        }
        const mic = await requestMicrophone();
        if (!mic.ok) {
          setError(MIC_MESSAGES[mic.error]);
          return;
        }
        stream.current = mic.stream;
        try {
          startSegment(mic.stream);
        } catch {
          release();
          setError("Aufnahme konnte nicht gestartet werden (MediaRecorder).");
        }
      } finally {
        starting.current = false;
      }
    },
    [drain, release, reset, startSegment],
  );

  const start = useCallback(() => begin(false), [begin]);
  const resume = useCallback(() => begin(true), [begin]);

  const stop = useCallback(() => {
    const rec = recorder.current;
    if (rec?.state === "recording") rec.stop();
  }, []);

  const next = useCallback(() => {
    continueAfter.current = true;
    stop();
  }, [stop]);

  const uploading = waiting > 0 && !paused;

  return {
    phase: recording ? "aufnahme" : uploading ? "sende" : resumable ? "fortsetzbar" : "bereit",
    seconds,
    remaining: Math.max(0, AUTO_STOP_SECONDS - seconds),
    level,
    uploading,
    waiting,
    transcript,
    codes,
    error,
    lastLatency,
    supported: mime.current !== null,
    sessionLost,
    sessionExpired,
    relogin,
    start,
    resume,
    stop,
    next,
    reset,
    setCodes,
  };
}
