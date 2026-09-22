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

export const MAX_SECONDS = 60;

export type DictationPhase = "bereit" | "aufnahme" | "sende";

export type Dictation = {
  phase: DictationPhase;
  seconds: number; // Laufzeit des aktuellen Segments
  remaining: number; // Sekunden bis zum harten Limit
  level: number; // Pegel 0..1
  transcript: string;
  codes: string[];
  error: string | null;
  lastLatency: number | null;
  supported: boolean; // MediaRecorder mit passendem MIME vorhanden
  start: () => Promise<void>;
  stop: () => void; // beendet das Segment und lädt es hoch
  next: () => Promise<void>; // "Weiter": Segment hochladen und sofort neues starten
  reset: () => void; // Transkript verwerfen
  setCodes: (codes: string[]) => void;
};

export function useDictation(): Dictation {
  const [phase, setPhase] = useState<DictationPhase>("bereit");
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
  }, [clearTimers]);

  useEffect(() => release, [release]);

  const upload = useCallback(async (blob: Blob) => {
    if (blob.size === 0) {
      setError("Keine Audiodaten aufgenommen.");
      return;
    }
    setPhase("sende");
    try {
      const result = await api.transcribe(blob, filenameFor(blob.type || mime.current || ""));
      const text = result.transcript.trim();
      setTranscript((prev) => (prev && text ? `${prev} ${text}` : prev || text));
      setCodes((prev) => Array.from(new Set([...prev, ...result.codes])));
      setLastLatency(result.latency_s);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Unbekannter Fehler beim Hochladen.");
    }
  }, []);

  const start = useCallback(async () => {
    if (recorder.current) return;
    setError(null);
    if (!mime.current) {
      setError("Dieser Browser unterstützt keine Audioaufnahme (MediaRecorder fehlt).");
      return;
    }
    const mic = await requestMicrophone();
    if (!mic.ok) {
      setError(MIC_MESSAGES[mic.error]);
      return;
    }
    stream.current = mic.stream;
    chunks.current = [];
    let rec: MediaRecorder;
    try {
      rec = new MediaRecorder(mic.stream, { mimeType: mime.current });
    } catch {
      release();
      setError("Aufnahme konnte nicht gestartet werden (MediaRecorder).");
      return;
    }
    recorder.current = rec;
    rec.ondataavailable = (ev) => {
      if (ev.data.size > 0) chunks.current.push(ev.data);
    };
    rec.onstop = () => {
      const blob = new Blob(chunks.current, { type: rec.mimeType || mime.current || "" });
      chunks.current = [];
      const again = continueAfter.current;
      continueAfter.current = false;
      release();
      void upload(blob).then(() => {
        setPhase("bereit");
        if (again) void start();
      });
    };
    rec.start(250);
    meter.current = startLevelMeter(mic.stream, setLevel);
    const startedAt = Date.now();
    setSeconds(0);
    setPhase("aufnahme");
    ticker.current = window.setInterval(() => {
      const elapsed = Math.floor((Date.now() - startedAt) / 1000);
      setSeconds(elapsed);
      if (elapsed >= MAX_SECONDS && rec.state === "recording") {
        rec.stop();
        setError(`Aufnahme zu lang – bei ${MAX_SECONDS} Sekunden automatisch beendet und hochgeladen.`);
      }
    }, 250);
  }, [release, upload]);

  const stop = useCallback(() => {
    const rec = recorder.current;
    if (rec && rec.state === "recording") {
      clearTimers();
      rec.stop();
    }
  }, [clearTimers]);

  const next = useCallback(async () => {
    continueAfter.current = true;
    stop();
  }, [stop]);

  const reset = useCallback(() => {
    setTranscript("");
    setCodes([]);
    setError(null);
    setLastLatency(null);
  }, []);

  return {
    phase,
    seconds,
    remaining: Math.max(0, MAX_SECONDS - seconds),
    level,
    transcript,
    codes,
    error,
    lastLatency,
    supported: mime.current !== null,
    start,
    stop,
    next,
    reset,
    setCodes,
  };
}
