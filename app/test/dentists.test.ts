// Behandler am geteilten iPad und im Büro: Filter steht auf „Alle“ und ist keine Schranke, Diktate ohne
// Behandler bleiben sichtbar, nach langer Pause fragt das iPad neu, wer diktiert.
import assert from "node:assert/strict";
import { test } from "node:test";
import type { PatientList, PatientSummary, StoredDictation } from "../src/api.ts";
import {
  DEFAULT_IDLE_S,
  dentistLabel,
  filterByDentist,
  filterChoices,
  idleExpired,
  mustAsk,
  offerNone,
  patientDentists,
  restoreDevice,
  type Dentist,
} from "../src/dentists.ts";

const A: Dentist = { id: 1, name: "Dr. A", practitioner_id: null, active: true };
const B: Dentist = { id: 2, name: "Dr. B", practitioner_id: "7", active: true };
const C: Dentist = { id: 3, name: "Dr. C", practitioner_id: null, active: false };
const MIN = 60_000;

function patient(id: number, dentists: Dentist[]): PatientSummary {
  return {
    id,
    number: String(4710 + id),
    created_at: "2026-09-23T08:00:00+00:00",
    updated_at: "2026-09-23T08:00:00+00:00",
    dictations: 1,
    transferred: 0,
    transferred_at: null,
    dentist_id: dentists[0]?.id ?? null,
    dentist_name: dentists[0]?.name ?? null,
    dentists: dentists.map(({ id, name }) => ({ id, name })),
  };
}

function loose(id: string, dentist: Dentist | null): StoredDictation {
  return {
    id,
    patient: null,
    patient_id: null,
    revision: 1,
    created_at: "2026-09-23T08:00:00+00:00",
    updated_at: "2026-09-23T08:00:00+00:00",
    transcript: "Zahn 36",
    patient_type: "kasse",
    codes: [],
    suggestions: [],
    planned: [],
    notes: [],
    deselected: [],
    adopted: [],
    dentist_id: dentist?.id ?? null,
    dentist_name: dentist?.name ?? null,
  };
}

// 4711: von Dr. A eröffnet, Dr. B hat auch diktiert; 4712: nur Dr. B; 4713: Pilotdaten ohne Behandler.
const LIST: PatientList = {
  patients: [patient(1, [A, B]), patient(2, [B]), patient(3, [])],
  unassigned: [loose("ohne-a", A), loose("ohne-alt", null)],
};

test("Filter steht auf „Alle“: jeder Patient und jedes Diktat, auch ohne Behandler", () => {
  assert.equal(filterByDentist(LIST, null), LIST);
});

test("Filter nach Behandler: eröffnet oder mitdiktiert – ein Patient kann bei zweien erscheinen", () => {
  const b = filterByDentist(LIST, B.id);
  assert.deepEqual(b.patients.map((p) => p.number), ["4711", "4712"]);
  assert.deepEqual(b.unassigned, []);
  const a = filterByDentist(LIST, A.id);
  assert.deepEqual(a.patients.map((p) => p.number), ["4711"]);
  assert.deepEqual(a.unassigned.map((d) => d.id), ["ohne-a"]);
  assert.equal(LIST.patients.length, 3, "die Liste selbst bleibt unverändert");
});

test("Diktat ohne Behandler (Pilotdaten, ältere iPads) bleibt nutzbar und lesbar", () => {
  const old = { ...patient(4, []), dentist_id: undefined, dentist_name: undefined, dentists: undefined };
  const list: PatientList = { patients: [old], unassigned: [{ ...loose("alt", null), dentist_id: undefined }] };
  assert.equal(filterByDentist(list, null).patients.length, 1);
  assert.deepEqual(filterByDentist(list, A.id), { patients: [], unassigned: [] });
  assert.equal(dentistLabel("Dr. A"), "Dr. A");
});

test("Filterauswahl: aktive Behandler und inaktive nur, solange sie in der Liste vorkommen", () => {
  assert.deepEqual(filterChoices([A, B, C], LIST).map((d) => d.name), ["Dr. A", "Dr. B"]);
  const withC: PatientList = { ...LIST, patients: [...LIST.patients, patient(5, [C])] };
  assert.deepEqual(filterChoices([A, B, C], withC).map((d) => d.name), ["Dr. A", "Dr. B", "Dr. C"]);
  assert.deepEqual(filterChoices([A], null).map((d) => d.name), ["Dr. A"]);
});

test("Pause: nach der eingestellten Zeit ohne Bedienung wird neu gefragt (Voreinstellung 30 min)", () => {
  const t0 = Date.parse("2026-09-23T08:00:00Z");
  assert.equal(DEFAULT_IDLE_S, 30 * 60);
  assert.equal(idleExpired(t0, t0 + 29 * MIN, DEFAULT_IDLE_S), false);
  assert.equal(idleExpired(t0, t0 + 30 * MIN, DEFAULT_IDLE_S), true);
  assert.equal(idleExpired(t0, t0 + 11 * MIN, 10 * 60), true, "Einstellung des Servers gilt");
});

test("Wahl bleibt nach dem Neuladen, gilt nach langer Pause aber nicht mehr als bestätigt", () => {
  const t0 = Date.parse("2026-09-23T08:00:00Z");
  const saved = JSON.stringify({ id: 2, confirmed: true, lastActive: t0 });
  assert.deepEqual(restoreDevice(saved, t0 + 5 * MIN, DEFAULT_IDLE_S), { id: 2, confirmed: true, lastActive: t0 });
  assert.deepEqual(restoreDevice(saved, t0 + 45 * MIN, DEFAULT_IDLE_S), { id: 2, confirmed: false, lastActive: t0 });
  assert.deepEqual(restoreDevice(saved, t0 + 45 * MIN, Infinity).confirmed, true, "vor dem Laden der Einstellung");
  assert.deepEqual(restoreDevice(null, t0, DEFAULT_IDLE_S), { id: null, confirmed: false, lastActive: 0 });
  assert.deepEqual(restoreDevice("kaputt{", t0, DEFAULT_IDLE_S), { id: null, confirmed: false, lastActive: 0 });
});

test("Vor dem nächsten Diktat fragen: unbestätigt, nicht mehr aktiv – nie ohne Behandlerliste", () => {
  const active = [A, B];
  assert.equal(mustAsk({ id: 1, confirmed: true, lastActive: 0 }, active), false);
  assert.equal(mustAsk({ id: 1, confirmed: false, lastActive: 0 }, active), true, "nach Übergabe oder Pause");
  assert.equal(mustAsk({ id: null, confirmed: false, lastActive: 0 }, active), true, "neues Gerät");
  assert.equal(mustAsk({ id: 3, confirmed: true, lastActive: 0 }, active), true, "inzwischen inaktiv");
  assert.equal(mustAsk({ id: null, confirmed: true, lastActive: 0 }, active), true, "ohne Behandler gilt nicht");
  assert.equal(mustAsk({ id: null, confirmed: false, lastActive: 0 }, []), false, "leere Liste blockiert nie");
  assert.equal(mustAsk({ id: null, confirmed: true, lastActive: 0 }, []), false);
});

test("„Ohne Behandler diktieren“ nur bei geladener Liste ohne aktiven Behandler", () => {
  assert.equal(offerNone([A, B]), false);
  assert.equal(offerNone([A]), false);
  assert.equal(offerNone([]), true, "erster Start ohne Behandlerliste");
  assert.equal(offerNone(null), false, "Liste nicht geladen: erst laden, nicht ohne Zuordnung");
});

test("Büro: fehlender Behandler steht als „Behandler fehlt“, beim Diktat und beim Patienten", () => {
  assert.equal(dentistLabel(null), "Behandler fehlt");
  assert.equal(dentistLabel(undefined), "Behandler fehlt");
  assert.equal(patientDentists({ ...patient(1, [A, B]), without_dentist: 0 }), "Dr. A, Dr. B");
  assert.equal(patientDentists({ ...patient(1, [A]), without_dentist: 1 }), "Dr. A, Behandler fehlt");
  assert.equal(patientDentists({ ...patient(3, []), without_dentist: 2 }), "Behandler fehlt");
  assert.equal(patientDentists({ ...patient(3, []), without_dentist: undefined }), "", "übertragen oder leer: nichts");
});
