// Diktate je Patient (Evident-Patientennummer): reine Funktionen für iPad und Büro, getestet in
// test/patients.test.ts. Das Kopierformat entsteht mit denselben Funktionen wie am iPad (selectedLines),
// damit Text und Ziffern im Büro Zeichen für Zeichen dem entsprechen, was das iPad kopieren würde.
// Mit Endung, damit `node --test` das Modul direkt laden kann (allowImportingTsExtensions).
import { onlyPrivate, splitBlocks, type EvidentBlocks, type PatientSummary, type StoredDictation, type TransferPosition } from "./api.ts";
import { buildGroups, positionsOf, selectedLines } from "./result.ts";

// Evident-Patientennummer: nur Ziffern, höchstens 12 (wie der Server prüft).
export const NUMBER_MAX = 12;
export function normalizeNumber(raw: string): string {
  return raw.replace(/\D/g, "").slice(0, NUMBER_MAX);
}

// Kürzel (Initialen) zur Nummer, nur zum Wiederfinden in Evident: höchstens 4 Buchstaben, je einer mit
// Punkt dahinter, getrennt nur durch Punkt, Leerzeichen oder Bindestrich („MK“, „M. K.“, „A-B.“) – keine
// Namen, keine Ziffern (wie der Server prüft). Beim Tippen: alles andere fällt weg. Nie in den Kopierzeilen.
export const LABEL_LETTERS = 4;
export const LABEL_MAX = 11; // „A. B. C. D.“
export function normalizeLabel(raw: string): string {
  let out = "";
  let letters = 0;
  for (const c of raw.normalize("NFC")) {
    const last = out.at(-1) ?? "";
    if (/\p{L}/u.test(c)) {
      if (letters === LABEL_LETTERS) break;
      out += c;
      letters += 1;
    } else if (c === "." && /\p{L}/u.test(last)) out += c;
    else if ((c === "-" || /\s/.test(c)) && letters < LABEL_LETTERS && (last === "." || /\p{L}/u.test(last))) {
      out += c === "-" ? "-" : " ";
    }
  }
  return out;
}

// Kürzel zum Speichern: ohne Trenner am Ende, leer = keins.
export function finishLabel(raw: string): string | null {
  return normalizeLabel(raw).replace(/[ -]+$/, "") || null;
}

// Nummer mit Kürzel für Texte und Vorlesen („4711 · M.K.“); ohne Kürzel nur die Nummer.
export function patientName(number: string, label?: string | null): string {
  return label ? `${number} · ${label}` : number;
}

// Kopiertexte und Mehrkosten-Positionen eines gespeicherten Diktats.
export type DictationCopy = {
  evident: string[]; // „Ziffern kopieren“: Evident-Zeilen mit Kurzformen
  numbers: string[]; // „Nur Ziffern“
  positions: TransferPosition[]; // Zahn, Ziffer, Art – für die Mehrkosten-Tabelle
  allPrivate: boolean; // nur Privatpositionen: ein Block, der Privatblock
  blocks: EvidentBlocks; // Kassenpatient: Kassenblock, Leerzeile, Privatblock – wie an der Rezeption
};

export function dictationCopy(d: StoredDictation): DictationCopy {
  const deselected = new Set(d.deselected);
  const adopted = new Set(d.adopted);
  const evident = selectedLines(d.suggestions, d.codes, deselected, adopted);
  const numbers = selectedLines(d.suggestions, d.codes, deselected, adopted, false);
  const active = d.codes.filter((c) => !deselected.has(c));
  const positions = positionsOf(buildGroups(d.suggestions, active, adopted, evident));
  const allPrivate = onlyPrivate(positions);
  return { evident, numbers, positions, allPrivate, blocks: splitBlocks(evident, allPrivate) };
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

// Was eine am iPad gewählte Nummer mit dem Diktat auf dem Bildschirm macht. `onScreen`: keins
// (noch kein Ergebnis), offen (Ergebnis, wird gespeichert) oder übertragen (vom Server abgelehnt).
// bleiben: nichts ändert sich; wechseln: nur der aktive Patient wechselt; neu: Bildschirm leeren,
// das bisherige Diktat bleibt, wo es ist; fragen: das Diktat „ohne Patient“ nie still zuordnen,
// sondern erst nachfragen, ob es dieser Patient ist.
export type PickAction = "bleiben" | "wechseln" | "neu" | "fragen";

export function pickAction(
  current: string | null,
  next: string | null,
  onScreen: "keins" | "offen" | "übertragen",
): PickAction {
  if (next === current) return "bleiben";
  if (onScreen === "keins") return "wechseln";
  if (current !== null || next === null || onScreen === "übertragen") return "neu";
  return "fragen";
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
