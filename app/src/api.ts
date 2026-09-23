// Zugriff auf die MedVox-API (server/). Alle Fehler werden als ApiError mit
// deutscher Meldung geworfen, damit die Ansichten sie direkt anzeigen können.

export type Health = { status: string; whisper: "ok" | "down" | string };
// Patiententyp: wählt je Leistung BEMA (Kasse) oder GOZ/GOÄ (Privat).
export type PatientType = "kasse" | "privat";
// bema, goz (Privatleistung, auch GOÄ) oder zuzahlung (Privatleistung beim Kassenpatienten)
export type SuggestionKind = "bema" | "goz" | "zuzahlung";
export type Suggestion = {
  code: string;
  system: string;
  title: string;
  kind: SuggestionKind;
  count: number;
  teeth: number[];
  reason: string;
  decide: string[];
  alternative: boolean;
};
export type TranscribeResult = {
  transcript: string;
  patient_type: PatientType;
  duration_s: number;
  latency_s: number;
  codes: string[];
  suggestions: Suggestion[];
};
export type TransferCreated = { code: string; expires_at: string };
export type TransferData = { transcript: string; codes: string[]; created_at: string };

export class ApiError extends Error {
  readonly status: number; // 0 = Netzwerk/Server nicht erreichbar

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

const MESSAGES: Record<number, string> = {
  401: "Nicht angemeldet.",
  404: "Nicht gefunden.",
  413: "Aufnahme zu lang (maximal 60 Sekunden).",
  415: "Audioformat wird vom Server nicht unterstützt.",
  429: "Zu viele Abfragen – bitte kurz warten.",
  503: "Whisper nicht bereit – Transkriptionsdienst auf dem Praxis-Mac prüfen.",
};

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, init);
  } catch {
    throw new ApiError(0, "Server nicht erreichbar – WLAN und Praxis-Mac prüfen.");
  }
  if (!res.ok) {
    let detail = "";
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* Body ohne JSON */
    }
    throw new ApiError(res.status, detail || MESSAGES[res.status] || `Serverfehler (HTTP ${res.status}).`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

function json(method: string, body: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

export const api = {
  health: () => request<Health>("/api/v1/health"),
  session: () => request<void>("/api/v1/session"),
  login: (password: string) => request<void>("/api/v1/login", json("POST", { password })),
  logout: () => request<void>("/api/v1/logout", { method: "POST" }),

  transcribe(audio: Blob, filename: string, patientType: PatientType): Promise<TranscribeResult> {
    const form = new FormData();
    form.append("file", audio, filename);
    form.append("patient_type", patientType);
    return request<TranscribeResult>("/api/v1/transcribe", { method: "POST", body: form });
  },

  createTransfer: (transcript: string, codes: string[]) =>
    request<TransferCreated>("/api/v1/transfer", json("POST", { transcript, codes })),
  getTransfer: (code: string) =>
    request<TransferData>(`/api/v1/transfer/${encodeURIComponent(code)}`),
};

// Ziffern im Kopierformat der Praxis: kommagetrennt, z. B. "01, 8, 13c, 2080".
export function joinCodes(codes: string[]): string {
  return codes.join(", ");
}

// Art je Ziffer der erbrachten Hauptvorschläge; Schlüssel wie in `codes` ohne Anzahl ("2x 41a" -> "41a").
export function kindsOf(suggestions: Suggestion[]): Record<string, SuggestionKind> {
  const kinds: Record<string, SuggestionKind> = {};
  for (const s of suggestions) if (!s.alternative) kinds[s.code] = s.kind;
  return kinds;
}

export function codeOf(copyCode: string): string {
  return copyCode.replace(/^\d+x\s+/, "");
}

// Gespeicherter Patiententyp; alles Unbekannte gilt als Kasse (Standard des Servers).
export function parsePatientType(raw: string | null): PatientType {
  return raw === "privat" ? "privat" : "kasse";
}

// Kurzcodes: 6 Zeichen aus einem eindeutigen Alphabet (ohne 0/O/1/I).
export const CODE_LENGTH = 6;
export function normalizeCode(raw: string): string {
  return raw.toUpperCase().replace(/[^A-HJ-NP-Z2-9]/g, "").slice(0, CODE_LENGTH);
}
