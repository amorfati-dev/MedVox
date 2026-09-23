// Diktate je Patient (Evident-Patientennummer): reine Funktionen für iPad und Büro, getestet in
// test/patients.test.ts. Das Kopierformat entsteht mit denselben Funktionen wie am iPad (selectedLines),
// damit Text und Ziffern im Büro Zeichen für Zeichen dem entsprechen, was das iPad kopieren würde.
// Mit Endung, damit `node --test` das Modul direkt laden kann (allowImportingTsExtensions).
import type { PatientSummary, StoredDictation, TransferPosition } from "./api.ts";
import { buildGroups, positionsOf, selectedLines } from "./result.ts";

// Evident-Patientennummer: nur Ziffern, höchstens 12 (wie der Server prüft).
export const NUMBER_MAX = 12;
export function normalizeNumber(raw: string): string {
  return raw.replace(/\D/g, "").slice(0, NUMBER_MAX);
}

// Kopiertexte und Mehrkosten-Positionen eines gespeicherten Diktats.
export type DictationCopy = {
  evident: string[]; // „Ziffern kopieren“: Evident-Zeilen mit Kurzformen
  numbers: string[]; // „Nur Ziffern“
  positions: TransferPosition[]; // Zahn, Ziffer, Art – für die Mehrkosten-Tabelle
};

export function dictationCopy(d: StoredDictation): DictationCopy {
  const deselected = new Set(d.deselected);
  const adopted = new Set(d.adopted);
  const evident = selectedLines(d.suggestions, d.codes, deselected, adopted);
  const numbers = selectedLines(d.suggestions, d.codes, deselected, adopted, false);
  const active = d.codes.filter((c) => !deselected.has(c));
  const positions = positionsOf(buildGroups(d.suggestions, active, adopted, evident));
  return { evident, numbers, positions };
}

// offen: noch nicht übertragene Diktate; übertragen: alles übertragen (Inhalt gelöscht);
// leer: Nummer eingegeben, noch kein Diktat.
export type PatientState = "offen" | "übertragen" | "leer";

export function patientState(p: PatientSummary): PatientState {
  if (p.dictations > 0) return "offen";
  return p.transferred > 0 || p.transferred_at !== null ? "übertragen" : "leer";
}

export const STATE_LABEL: Record<PatientState, string> = {
  offen: "offen",
  übertragen: "übertragen",
  leer: "noch kein Diktat",
};

// Patienten, die am iPad zur Auswahl stehen: alles, was nicht schon übertragen ist.
export function pickable(patients: PatientSummary[]): PatientSummary[] {
  return patients.filter((p) => patientState(p) !== "übertragen");
}

// Uhrzeit „10:42“ aus einem ISO-Zeitstempel des Servers.
export function clock(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
}

// Anfang des Transkripts für Listen („Zahn 36 mod Karies …“).
export function preview(text: string, max = 60): string {
  const t = text.trim().replace(/\s+/g, " ");
  return t.length <= max ? t : `${t.slice(0, max - 1).trimEnd()} …`;
}

// ID eines neuen Diktats (vom iPad vergeben, damit wiederholtes Speichern nie doppelt anlegt).
export function newDictationId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") return crypto.randomUUID();
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}
