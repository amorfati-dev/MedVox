// Hilfsfunktionen rund um MediaRecorder: MIME-Wahl (Safari zuerst),
// Mikrofonzugriff und ein einfacher Pegelmesser über die Web-Audio-API.

// Reihenfolge = Präferenz: Safari/iPadOS liefert nur audio/mp4,
// Chrome/Firefox bevorzugt WebM/Opus.
export const MIME_CANDIDATES = ["audio/mp4", "audio/webm;codecs=opus", "audio/webm"];

export function pickMimeType(): string | null {
  if (typeof MediaRecorder === "undefined") return null;
  for (const mime of MIME_CANDIDATES) {
    if (MediaRecorder.isTypeSupported(mime)) return mime;
  }
  return null;
}

// Dateiname für den Upload, damit der Server den Typ zuordnen kann.
export function filenameFor(mime: string): string {
  return mime.startsWith("audio/mp4") ? "diktat.m4a" : "diktat.webm";
}

export type MicError = "verweigert" | "kein-mikrofon" | "unsicher" | "unbekannt";

export async function requestMicrophone(): Promise<
  { ok: true; stream: MediaStream } | { ok: false; error: MicError }
> {
  if (!window.isSecureContext) return { ok: false, error: "unsicher" };
  if (!navigator.mediaDevices?.getUserMedia) return { ok: false, error: "kein-mikrofon" };
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    return { ok: true, stream };
  } catch (e) {
    const name = e instanceof DOMException ? e.name : "";
    if (name === "NotAllowedError" || name === "SecurityError") {
      return { ok: false, error: "verweigert" };
    }
    if (name === "NotFoundError" || name === "OverconstrainedError") {
      return { ok: false, error: "kein-mikrofon" };
    }
    return { ok: false, error: "unbekannt" };
  }
}

export const MIC_MESSAGES: Record<MicError, string> = {
  verweigert: "Mikrofon verweigert – in den Safari-Einstellungen für medvox.local erlauben.",
  "kein-mikrofon": "Kein Mikrofon gefunden oder Aufnahme in diesem Browser nicht möglich.",
  unsicher: "Aufnahme nur über HTTPS möglich – bitte https://medvox.local öffnen.",
  unbekannt: "Mikrofon konnte nicht gestartet werden.",
};

export function stopStream(stream: MediaStream | null): void {
  stream?.getTracks().forEach((track) => track.stop());
}

// Pegelmesser: liefert per Callback einen Wert 0..1 (RMS), etwa 20-mal pro Sekunde.
export type LevelMeter = { stop: () => void };

export function startLevelMeter(stream: MediaStream, onLevel: (level: number) => void): LevelMeter {
  const Ctx = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!Ctx) return { stop: () => undefined };
  const ctx = new Ctx();
  const source = ctx.createMediaStreamSource(stream);
  const analyser = ctx.createAnalyser();
  analyser.fftSize = 512;
  source.connect(analyser);
  const buffer = new Uint8Array(analyser.fftSize);
  const timer = window.setInterval(() => {
    analyser.getByteTimeDomainData(buffer);
    let sum = 0;
    for (const v of buffer) {
      const d = (v - 128) / 128;
      sum += d * d;
    }
    onLevel(Math.min(1, Math.sqrt(sum / buffer.length) * 3));
  }, 50);
  return {
    stop: () => {
      window.clearInterval(timer);
      source.disconnect();
      void ctx.close();
    },
  };
}
