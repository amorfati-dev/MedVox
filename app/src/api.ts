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
  points?: number | null; // BEMA-Bewertungszahl bzw. GOZ/GOÄ-Punkte; wird nie angezeigt (Patient schaut mit)
  teeth: number[];
  reason: string;
  decide: string[];
  alternative: boolean;
  evident?: string | null; // Evident-Kurzform aus dem Katalog ("l1"), sonst die Ziffer verwenden
};
export type TranscribeResult = {
  transcript: string;
  patient_type: PatientType;
  duration_s: number;
  latency_s: number;
  codes: string[];
  suggestions: Suggestion[]; // erbracht: Hauptvorschläge und Optionen (`alternative`)
  planned?: Suggestion[]; // nur geplant – nie abrechnen
  notes?: string[]; // Hinweise ohne Ziffer (verneint, enthalten, Zuschlag nicht bestimmbar)
};
export type TransferCreated = { code: string; expires_at: string };
// Art einer übergebenen Position; kassenanteil = BEMA-Basis einer Zuzahlung am selben Zahn.
export type PositionKind = "bema" | "goz" | "zuzahlung" | "kassenanteil";
// Übergebene Position, nur zur Anzeige an der Rezeption (kopiert wird `codes`).
export type TransferPosition = { tooth: number | null; code: string; kind: PositionKind };
export type TransferDetails = { patient_type: PatientType; positions: TransferPosition[] };
// `codes`: Evident-Zeilen, eine je Zahn ("36,Ä925a,l1,13a"), siehe evidentLines.
// `patient_type`/`positions` fehlen bei Einträgen älterer iPad-Versionen.
export type TransferData = {
  transcript: string;
  codes: string[];
  created_at: string;
  patient_type?: PatientType | null;
  positions?: TransferPosition[];
};

// Stand eines Diktats, wie das iPad ihn beim Patienten speichert (PUT /api/v1/dictations/{id}):
// die Felder aus /transcribe aller Abschnitte plus die Auswahl (abgewählte Ziffern, übernommene Optionen).
export type DictationContent = {
  transcript: string;
  patient_type: PatientType | null;
  codes: string[];
  suggestions: Suggestion[];
  planned: Suggestion[];
  notes: string[];
  deselected: string[]; // Ziffern im Kopierformat ("2x 41a")
  adopted: string[]; // optionKey übernommener Zuzahlungs-Optionen
};
// `patient`: Evident-Patientennummer; fehlt sie, bleibt die bisherige Zuordnung („ohne Patient“ bei neuen).
export type DictationBody = DictationContent & { patient?: string };
export type StoredDictation = DictationContent & {
  id: string;
  patient: string | null;
  patient_id: number | null;
  revision: number; // „übertragen“ löscht nur genau die angezeigte Fassung
  created_at: string;
  updated_at: string;
};
export type PatientSummary = {
  id: number;
  number: string; // Evident-Patientennummer
  created_at: string;
  updated_at: string; // jüngstes Diktat
  dictations: number; // offen
  transferred: number; // schon übertragen (Inhalt gelöscht)
  transferred_at: string | null;
};
export type PatientDetail = PatientSummary & { items: StoredDictation[] };
export type PatientList = { patients: PatientSummary[]; unassigned: StoredDictation[] };

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
  502: "Praxis-Mac antwortet nicht – MedVox-Dienst auf dem Praxis-Mac prüfen.",
  503: "Whisper nicht bereit – Transkriptionsdienst auf dem Praxis-Mac prüfen.",
  504: "Praxis-Mac antwortet zu langsam – bitte erneut versuchen.",
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

  createTransfer: (transcript: string, codes: string[], details?: TransferDetails) =>
    request<TransferCreated>("/api/v1/transfer", json("POST", { transcript, codes, ...details })),
  getTransfer: (code: string) =>
    request<TransferData>(`/api/v1/transfer/${encodeURIComponent(code)}`),

  // Diktate je Patient: am Stuhl speichern, im Büro übertragen (höchstens 24 Stunden).
  saveDictation: (id: string, body: DictationBody) =>
    request<StoredDictation>(`/api/v1/dictations/${encodeURIComponent(id)}`, json("PUT", body)),
  deleteDictation: (id: string) =>
    request<void>(`/api/v1/dictations/${encodeURIComponent(id)}`, { method: "DELETE" }),
  listPatients: () => request<PatientList>("/api/v1/patients"),
  createPatient: (number: string) => request<PatientSummary>("/api/v1/patients", json("POST", { number })),
  getPatient: (id: number) => request<PatientDetail>(`/api/v1/patients/${id}`),
  appendDictation: (patientId: number, dictationId: string) =>
    request<StoredDictation>(`/api/v1/patients/${patientId}/dictations`, json("POST", { dictation_id: dictationId })),
  markTransferred: (patientId: number, seen: StoredDictation[]) =>
    request<PatientDetail>(
      `/api/v1/patients/${patientId}/transferred`,
      json("POST", { seen: seen.map((d) => ({ id: d.id, revision: d.revision })) }),
    ),
  deletePatient: (id: number) => request<void>(`/api/v1/patients/${id}`, { method: "DELETE" }),
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

// Evident-Kurzform je Ziffer der erbrachten Hauptvorschläge (z. B. 41a → "l1").
export function evidentOf(suggestions: Suggestion[]): Record<string, string> {
  const forms: Record<string, string> = {};
  for (const s of suggestions) if (!s.alternative && s.evident) forms[s.code] = s.evident;
  return forms;
}

// Kopierformat für Evident: Evident nimmt Abrechnungspositionen nur hinter einem Zahn an.
// Je Zahn eine Zeile "Zahn,Ziffer,Ziffer" in Diktatreihenfolge, z. B. "36,Ä925a,l1,13a";
// Positionen ohne Zahn (01, Ä1, 107) stehen in einer letzten Zeile mit leerem Zahnfeld (",01,107").
// Das leere Zahnfeld kennzeichnet die Zeile für die Anzeige; kopiert wird sie ohne (evidentText).
// Mit `shortForms` (Standard) steht die Evident-Kurzform aus dem Katalog statt der Ziffer ("l1"
// statt "41a"), sonst die Ziffer; ohne `shortForms` nur amtliche Ziffern („Nur Ziffern“).
type Line = { tooth: number | null; counts: Map<string, number>; forms: Map<string, string> };

// Evident setzt nach einer Privatposition alles Folgende ebenfalls auf privat. Beim Kassenpatienten
// stehen deshalb alle Kassenzeilen zuerst und alle Privatpositionen (Zuzahlung, GOZ/GOÄ) in einem
// eigenen Block danach – nicht nur zuletzt in ihrer Zahnzeile; ein Zahn kann in beiden Blöcken stehen.
// Beim Privatpatienten ist alles privat: ein Block, Format unverändert.
export type EvidentBlocks = { kasse: string[]; privat: string[] };

export function isPrivate(s: Suggestion): boolean {
  return s.kind !== "bema";
}

// `suggestions`: erbrachte Vorschläge aller Abschnitte in Diktatreihenfolge;
// `active`: ausgewählte Ziffern im Kopierformat ("2x 41a") – abgewählte Ziffern fehlen.
// Mehrfach erbrachte Positionen stehen einmal mit "*Anzahl", hinter Kurzform wie Ziffer ("36,wf*3",
// "11,2410*3"); für Ziffern nach Auskunft des Behandlers, im Pilot noch an Evident zu prüfen.
export function evidentBlocks(suggestions: Suggestion[], active: string[], shortForms = true): EvidentBlocks {
  const chosen = new Set(active.map(codeOf));
  const copied = suggestions.filter((s) => !s.alternative && chosen.has(s.code));
  return {
    kasse: toothLines(copied.filter((s) => !isPrivate(s)), shortForms),
    privat: toothLines(copied.filter(isPrivate), shortForms),
  };
}

// Beide Blöcke als eine Zeilenliste, getrennt durch eine Leerzeile, wenn beide etwas enthalten.
export function evidentLines(suggestions: Suggestion[], active: string[], shortForms = true): string[] {
  return joinBlocks(evidentBlocks(suggestions, active, shortForms));
}

export function joinBlocks({ kasse, privat }: EvidentBlocks): string[] {
  return kasse.length > 0 && privat.length > 0 ? [...kasse, "", ...privat] : [...kasse, ...privat];
}

// Umkehrung von joinBlocks für übergebene Zeilen (Rezeption). Ohne Leerzeile ist es ein Block:
// `allPrivate` sagt, ob das der Privatblock ist (nur Privatpositionen übergeben).
export function splitBlocks(lines: string[], allPrivate = false): EvidentBlocks {
  const gap = lines.indexOf("");
  if (gap >= 0) return { kasse: lines.slice(0, gap), privat: lines.slice(gap + 1) };
  return allPrivate ? { kasse: [], privat: lines } : { kasse: lines, privat: [] };
}

function toothLines(suggestions: Suggestion[], shortForms: boolean): string[] {
  const lines = new Map<number | null, Line>();
  for (const s of suggestions) {
    const tooth = s.teeth.length > 0 ? s.teeth[0] : null;
    let line = lines.get(tooth);
    if (!line) {
      line = { tooth, counts: new Map(), forms: new Map() };
      lines.set(tooth, line);
    }
    // Wiederholt ein späterer Abschnitt dieselbe Ziffer am selben Zahn, zählt sie einmal.
    line.counts.set(s.code, Math.max(line.counts.get(s.code) ?? 0, s.count));
    if (shortForms && s.evident) line.forms.set(s.code, s.evident);
  }
  const ordered = [...lines.values()].sort((a, b) => Number(a.tooth === null) - Number(b.tooth === null));
  return ordered.map(({ tooth, counts, forms }) => {
    const codes = [...counts].map(([code, n]) => {
      const form = forms.get(code) ?? code;
      return n > 1 ? `${form}*${n}` : form;
    });
    return [tooth === null ? "" : String(tooth), ...codes].join(",");
  });
}

// Zeile ohne Zahn: in Evident manuell eintragen.
export function isToothless(line: string): boolean {
  return line.startsWith(",");
}

// Text in der Zwischenablage: eine Zeile je Zahn, die Zeile ohne Zahn ohne führendes Komma; die
// Leerzeile zwischen Kassen- und Privatblock bleibt stehen.
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
