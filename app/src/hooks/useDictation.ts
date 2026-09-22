// Aufnahme-Hook: MediaRecorder-Segmente aufnehmen, an /api/v1/transcribe
// schicken und die Transkripte der Segmente aneinanderhängen.
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

// "fortsetzbar": nach dem automatischen Stopp bleibt das Transkript erhalten,
// „Weiter“ hängt an, „Neues Diktat“ beginnt neu.
export type DictationPhase = "bereit" | "aufnahme" | "sende" | "fortsetzbar";

export type Dictation = {
  phase: DictationPhase;
  seconds: number; // Laufzeit des aktuellen Segments
  remaining: number; // Sekunden bis zum automatischen Stopp
  level: number; // Pegel 0..1
  uploading: boolean; // ein Abschnitt wird gerade transkribiert
  transcript: string;
  codes: string[];
  error: string | null;
  lastLatency: number | null;
  supported: boolean; // MediaRecorder mit passendem MIME vorhanden
  sessionLost: boolean; // Server antwortete 401; Transkript und offene Abschnitte bleiben erhalten
  relogin: () => void; // nach erneuter Anmeldung: zurückgehaltene Abschnitte hochladen
  start: () => Promise<void>; // neues Diktat: verwirft das bisherige Transkript
  resume: () => Promise<void>; // nach dem automatischen Stopp: nächsten Abschnitt anhängen
  stop: () => void; // beendet das Segment und lädt es hoch
  next: () => void; // "Weiter": Segment hochladen, Aufnahme läuft auf demselben Stream weiter
  reset: () => void; // Transkript verwerfen
  setCodes: (codes: string[]) => void;
};

export function useDictation(): Dictation {
  const [recording, setRecording] = useState(false);
  const [pending, setPending] = useState(0); // laufende Uploads
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
  const uploads = useRef<Promise<void>>(Promise.resolve());
  const held = useRef<Blob[]>([]); // Abschnitte, deren Upload mit 401 scheiterte
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

  const upload = useCallback(async (blob: Blob) => {
    if (blob.size === 0) {
      setError("Keine Audiodaten aufgenommen.");
      return;
    }
    setPending((n) => n + 1);
    try {
      const result = await api.transcribe(blob, filenameFor(blob.type || mime.current || ""));
      const text = result.transcript.trim();
      setTranscript((prev) => (prev && text ? `${prev} ${text}` : prev || text));
      setCodes((prev) => Array.from(new Set([...prev, ...result.codes])));
      setLastLatency(result.latency_s);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        held.current.push(blob);
        setSessionLost(true);
        if (recorder.current?.state === "recording") {
          continueAfter.current = false;
          recorder.current.stop();
        }
        return;
      }
      setError(e instanceof ApiError ? e.message : "Unbekannter Fehler beim Hochladen.");
    } finally {
      setPending((n) => n - 1);
    }
  }, []);

  const relogin = useCallback(() => {
    const blobs = held.current;
    held.current = [];
    setSessionLost(false);
    for (const blob of blobs) uploads.current = uploads.current.then(() => upload(blob));
  }, [upload]);

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
        uploads.current = uploads.current.then(() => upload(blob));
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
    [clearTimers, release, upload],
  );

  const reset = useCallback(() => {
    setTranscript("");
    setCodes([]);
    setError(null);
    setLastLatency(null);
    setResumable(false);
  }, []);

  // Mikrofon holen und das erste Segment starten; `append` behält das Transkript.
  const begin = useCallback(
    async (append: boolean) => {
      if (recorder.current || starting.current) return;
      if (!mime.current) {
        setError("Dieser Browser unterstützt keine Audioaufnahme (MediaRecorder fehlt).");
        return;
      }
      starting.current = true;
      try {
        const mic = await requestMicrophone();
        if (!mic.ok) {
          setError(MIC_MESSAGES[mic.error]);
          return;
        }
        stream.current = mic.stream;
        if (append) setError(null);
        else reset();
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
    [release, reset, startSegment],
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

  return {
    phase: recording ? "aufnahme" : pending > 0 ? "sende" : resumable ? "fortsetzbar" : "bereit",
    seconds,
    remaining: Math.max(0, AUTO_STOP_SECONDS - seconds),
    level,
    uploading: pending > 0,
    transcript,
    codes,
    error,
    lastLatency,
    supported: mime.current !== null,
    sessionLost,
    relogin,
    start,
    resume,
    stop,
    next,
    reset,
    setCodes,
  };
}
