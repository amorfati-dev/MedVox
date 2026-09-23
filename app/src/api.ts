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
// `codes`: Evident-Zeilen, eine je Zahn ("36,Ä925a,41a,13a"), siehe evidentLines.
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

// Art je Ziffer der erbrachten Hauptvorschläge; Schlüssel wie in `codes` ohne Anzahl ("2x 41a" -> "41a").
export function kindsOf(suggestions: Suggestion[]): Record<string, SuggestionKind> {
  const kinds: Record<string, SuggestionKind> = {};
  for (const s of suggestions) if (!s.alternative) kinds[s.code] = s.kind;
  return kinds;
}

export function codeOf(copyCode: string): string {
  return copyCode.replace(/^\d+x\s+/, "");
}

// Kopierformat für Evident: Evident nimmt Abrechnungspositionen nur hinter einem Zahn an.
// Je Zahn eine Zeile "Zahn,Ziffer,Ziffer" in Diktatreihenfolge, z. B. "36,Ä925a,41a,13a";
// Positionen ohne Zahn (01, Ä1, 107) stehen in einer letzten Zeile mit leerem Zahnfeld (",01,107").
// Das leere Zahnfeld kennzeichnet die Zeile für die Anzeige; kopiert wird sie ohne (evidentText).
type Line = { tooth: number | null; counts: Map<string, number> };

// `suggestions`: erbrachte Vorschläge aller Abschnitte in Diktatreihenfolge;
// `active`: ausgewählte Chips im Kopierformat ("2x 41a") – abgewählte Ziffern fehlen.
// Eine Ziffer mit Anzahl steht so oft in der Zeile, wie sie erbracht wurde ("11,32,32,32").
export function evidentLines(suggestions: Suggestion[], active: string[]): string[] {
  const chosen = new Set(active.map(codeOf));
  const lines = new Map<number | null, Line>();
  for (const s of suggestions) {
    if (s.alternative || !chosen.has(s.code)) continue;
    const tooth = s.teeth.length > 0 ? s.teeth[0] : null;
    let line = lines.get(tooth);
    if (!line) {
      line = { tooth, counts: new Map() };
      lines.set(tooth, line);
    }
    // Wiederholt ein späterer Abschnitt dieselbe Ziffer am selben Zahn, zählt sie einmal (wie die Chips).
    line.counts.set(s.code, Math.max(line.counts.get(s.code) ?? 0, s.count));
  }
  const ordered = [...lines.values()].sort((a, b) => Number(a.tooth === null) - Number(b.tooth === null));
  return ordered.map(({ tooth, counts }) => {
    const codes = [...counts].flatMap(([code, n]) => Array<string>(n).fill(code));
    return [tooth === null ? "" : String(tooth), ...codes].join(",");
  });
}

// Zeile ohne Zahn: in Evident manuell eintragen.
export function isToothless(line: string): boolean {
  return line.startsWith(",");
}

// Text in der Zwischenablage: eine Zeile je Zahn, die Zeile ohne Zahn ohne führendes Komma.
export function evidentText(lines: string[]): string {
  return lines.map((line) => (isToothless(line) ? line.slice(1) : line)).join("\n");
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
