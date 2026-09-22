// Aufnahme-Hook: MediaRecorder-Segmente aufnehmen und an die Upload-Warteschlange
// übergeben, die die Transkripte der Abschnitte aneinanderhängt.
import { useCallback, useEffect, useRef, useState } from "react";
import {
  MIC_MESSAGES,
  pickMimeType,
  requestMicrophone,
  startLevelMeter,
  stopStream,
  type LevelMeter,
} from "./recorder";
import { useUploadQueue } from "./useUploadQueue";

export const MAX_SECONDS = 60; // Server-Limit pro Abschnitt
// Automatischer Stopp knapp unter dem Server-Limit (Ticker-Raster, Anlaufzeit).
export const AUTO_STOP_SECONDS = MAX_SECONDS - 1;

// "fortsetzbar": die Aufnahme wurde unterbrochen (Zeitlimit, abgelaufene Sitzung
// oder Übertragungsfehler); das Diktat bleibt erhalten.
export type DictationPhase = "bereit" | "aufnahme" | "sende" | "fortsetzbar";

export type Dictation = {
  phase: DictationPhase;
  seconds: number; // Laufzeit des aktuellen Segments
  remaining: number; // Sekunden bis zum automatischen Stopp
  level: number; // Pegel 0..1
  uploading: boolean; // ein Abschnitt wird gerade transkribiert
  waiting: number; // Abschnitte, die auf die Übertragung warten
  retryable: boolean; // Übertragung fehlgeschlagen, Wiederholung möglich
  retry: () => void; // fehlgeschlagene Übertragung wiederholen
  discardable: boolean; // der wartende Abschnitt wird dauerhaft abgelehnt
  dropSegment: () => void; // nur diesen Abschnitt verwerfen, Rest weitersenden
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
};

export function useDictation(): Dictation {
  const [recording, setRecording] = useState(false);
  const [resumable, setResumable] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [level, setLevel] = useState(0);

  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const meter = useRef<LevelMeter | null>(null);
  const chunks = useRef<Blob[]>([]);
  const ticker = useRef<number | null>(null);
  const unwatchLimit = useRef<(() => void) | null>(null);
  const continueAfter = useRef(false);
  const starting = useRef(false);
  const lost = useRef(false); // Sitzung abgelaufen: keine neue Aufnahme starten
  const alive = useRef(true); // Hook noch eingebunden
  const mime = useRef<string | null>(pickMimeType());

  const clearTimers = useCallback(() => {
    if (ticker.current !== null) window.clearInterval(ticker.current);
    ticker.current = null;
    unwatchLimit.current?.();
    unwatchLimit.current = null;
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

  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      release();
    };
  }, [release]);

  // Abgelaufene Sitzung beendet die Aufnahme; die Abschnitte bleiben erhalten.
  const onSessionLost = useCallback(() => {
    lost.current = true;
    continueAfter.current = false;
    setResumable(true);
    const rec = recorder.current;
    if (rec?.state === "recording") rec.stop();
  }, []);

  const uploads = useUploadQueue(onSessionLost);
  const { enqueue, setError } = uploads;

  const startSegment = useCallback(
    (mic: MediaStream): void => {
      if (!alive.current || lost.current) {
        release();
        return;
      }
      const rec = new MediaRecorder(mic, { mimeType: mime.current ?? undefined });
      chunks.current = [];
      const startedAt = Date.now();
      // Zeitstempel statt Ticker: Safari drosselt Intervalle im Hintergrund.
      const checkLimit = () => {
        const elapsedMs = Date.now() - startedAt;
        setSeconds(Math.floor(elapsedMs / 1000));
        if (elapsedMs >= AUTO_STOP_SECONDS * 1000 && rec.state === "recording") {
          rec.stop();
          setResumable(true);
        }
      };
      rec.ondataavailable = (ev) => {
        if (ev.data.size > 0) chunks.current.push(ev.data);
        checkLimit();
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
      setSeconds(0);
      setRecording(true);
      setResumable(false);
      ticker.current = window.setInterval(checkLimit, 250);
      document.addEventListener("visibilitychange", checkLimit);
      unwatchLimit.current = () => document.removeEventListener("visibilitychange", checkLimit);
    },
    [clearTimers, enqueue, release, setError],
  );

  const reset = useCallback(() => {
    lost.current = false;
    setResumable(false);
    uploads.reset();
  }, [uploads]);

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
        if (append) uploads.resume();
        else reset();
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
    [release, reset, setError, startSegment, uploads],
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

  const relogin = useCallback(() => {
    lost.current = false;
    uploads.relogin();
  }, [uploads]);

  return {
    phase: recording ? "aufnahme" : uploads.uploading ? "sende" : resumable || uploads.blocked ? "fortsetzbar" : "bereit",
    seconds,
    remaining: Math.max(0, AUTO_STOP_SECONDS - seconds),
    level,
    uploading: uploads.uploading,
    waiting: uploads.waiting,
    retryable: uploads.blocked && !uploads.permanent,
    retry: uploads.resume,
    discardable: uploads.blocked && uploads.permanent,
    dropSegment: uploads.dropSegment,
    transcript: uploads.transcript,
    codes: uploads.codes,
    error: uploads.error,
    lastLatency: uploads.lastLatency,
    supported: mime.current !== null,
    sessionLost: uploads.sessionLost,
    sessionExpired: uploads.sessionExpired,
    relogin,
    start,
    resume,
    stop,
    next,
    reset,
  };
}
