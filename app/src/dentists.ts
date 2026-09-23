// Behandler der Gemeinschaftspraxis: wer ein Diktat aufgenommen hat – Zuordnung, keine Anmeldung.
// Alle sehen alle Patienten; das Praxis-Passwort bleibt die einzige Schranke. Die Liste liegt auf dem
// Praxis-Mac (/api/v1/dentists; inaktiv setzen per PATCH `active: false` oder DELETE), die Wahl am iPad im Gerät (useDentist).
// Reine Funktionen, getestet in test/dentists.test.ts. Mit Endung, damit `node --test` sie lädt.
import type { DentistRef, PatientList, PatientSummary, StoredDictation } from "./api.ts";
import { json, request } from "./http.ts";

export type Dentist = {
  id: number;
  name: string; // wie er angezeigt wird, z. B. „Dr. Hartmann“
  practitioner_id: string | null; // optional: Evident-/BEMA-Behandlernummer
  active: boolean; // inaktiv: nicht mehr zur Auswahl, alte Diktate behalten ihn
};
export type DentistList = { dentists: Dentist[]; idle_s: number };
export type DentistChange = Partial<Pick<Dentist, "name" | "practitioner_id" | "active">>;

export const dentistApi = {
  list: () => request<DentistList>("/api/v1/dentists"),
  add: (name: string, practitionerId: string | null) =>
    request<Dentist>("/api/v1/dentists", json("POST", { name, practitioner_id: practitionerId })),
  update: (id: number, change: DentistChange) => request<Dentist>(`/api/v1/dentists/${id}`, json("PATCH", change)),
  // Büro: Behandler eines Diktats ohne Behandler nachtragen; hat es schon einen, lehnt der Server ab (409).
  assign: (dictationId: string, dentistId: number) =>
    request<StoredDictation>(
      `/api/v1/dictations/${encodeURIComponent(dictationId)}/dentist`,
      json("PUT", { dentist_id: dentistId }),
    ),
};

// Voreinstellung des Servers (MEDVOX_DENTIST_IDLE_S), bis die Liste geladen ist.
export const DEFAULT_IDLE_S = 30 * 60;

// Wahl am Gerät: welcher Behandler, ob er für das nächste Diktat bestätigt ist, letzte Bedienung (ms).
// Nach einer Übergabe an die Rezeption oder langer Pause ist er nicht mehr bestätigt: das iPad fragt,
// wer jetzt diktiert, statt still beim letzten zu bleiben.
export type DeviceDentist = { id: number | null; confirmed: boolean; lastActive: number };

export function idleExpired(lastActive: number, now: number, idleS: number): boolean {
  return now - lastActive >= idleS * 1000;
}

// Gespeicherte Wahl nach dem Neuladen: bleibt, ist aber nach langer Pause nicht mehr bestätigt.
export function restoreDevice(raw: string | null, now: number, idleS: number): DeviceDentist {
  try {
    const v = JSON.parse(raw ?? "null") as Partial<DeviceDentist> | null;
    const id = typeof v?.id === "number" ? v.id : null;
    const lastActive = typeof v?.lastActive === "number" ? v.lastActive : 0;
    return { id, confirmed: v?.confirmed === true && !idleExpired(lastActive, now, idleS), lastActive };
  } catch {
    return { id: null, confirmed: false, lastActive: 0 };
  }
}

// Muss das iPad vor dem nächsten Diktat fragen? Ohne aktive Behandler in der Liste nie (dann ohne
// Behandler diktieren); sonst, wenn die Wahl nicht bestätigt ist oder kein aktiver Behandler gewählt.
export function mustAsk(device: DeviceDentist, active: Dentist[]): boolean {
  if (active.length === 0) return false;
  return !device.confirmed || !active.some((d) => d.id === device.id);
}

// „Ohne Behandler diktieren“ nur, solange die geladene Liste keinen aktiven Behandler hat (erster
// Start) – sonst landete jedes folgende Diktat ohne Zuordnung. null = Liste noch nicht geladen.
export function offerNone(active: Dentist[] | null): boolean {
  return active !== null && active.length === 0;
}

// Büro: Filter nach Behandler – eine Bequemlichkeit, keine Schranke. null = alle (Voreinstellung).
// Ein Patient passt, wenn der Behandler ihn eröffnet oder eins seiner offenen Diktate aufgenommen hat.
export function filterByDentist(list: PatientList, dentist: number | null): PatientList {
  if (dentist === null) return list;
  return {
    patients: list.patients.filter((p) => (p.dentists ?? []).some((d) => d.id === dentist)),
    unassigned: list.unassigned.filter((d) => d.dentist_id === dentist),
  };
}

// Auswahl im Filter: aktive Behandler, dazu inaktive, die in der Liste noch vorkommen.
export function filterChoices(roster: Dentist[], list: PatientList | null): DentistRef[] {
  const seen = new Set<number>();
  for (const p of list?.patients ?? []) for (const d of p.dentists ?? []) seen.add(d.id);
  for (const d of list?.unassigned ?? []) if (d.dentist_id != null) seen.add(d.dentist_id);
  return roster.filter((d) => d.active || seen.has(d.id)).map(({ id, name }) => ({ id, name }));
}

// Anzeige „Dr. Hartmann“; ohne Behandler „Behandler fehlt“ – im Büro nachträglich zuordnen.
export const MISSING_DENTIST = "Behandler fehlt";
export function dentistLabel(name: string | null | undefined): string {
  return name ?? MISSING_DENTIST;
}

// Büro, Patientenliste: beteiligte Behandler, dazu „Behandler fehlt“, solange ein offenes Diktat keinen hat.
export function patientDentists(p: PatientSummary): string {
  const names = (p.dentists ?? []).map((d) => d.name);
  if ((p.without_dentist ?? 0) > 0) names.push(MISSING_DENTIST);
  return names.join(", ");
}
