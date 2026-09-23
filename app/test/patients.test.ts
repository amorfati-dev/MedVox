// Büro: der Kopiertext je Patient ist Zeichen für Zeichen der, den das iPad für dieselben Vorschläge
// und dieselbe Auswahl kopieren würde (Goldstandard wie test/evident-golden.test.ts), dazu Zustand
// und Hilfen der Patientenliste.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { evidentText, type PatientSummary, type StoredDictation, type TranscribeResult } from "../src/api.ts";
import {
  dictationCopy,
  normalizeLabel,
  normalizeNumber,
  patientName,
  patientState,
  pickable,
  pickAction,
  preview,
} from "../src/patients.ts";
import { buildGroups, copyLines, optionKey, positionsOf } from "../src/result.ts";

type Golden = Record<string, Record<string, { evident: string[]; numbers: string[] }>>;
const fixtures = JSON.parse(readFileSync(new URL("./fixtures/anhang-b.json", import.meta.url), "utf8")) as Record<
  string,
  TranscribeResult
>;
const golden = JSON.parse(readFileSync(new URL("./fixtures/evident-golden.json", import.meta.url), "utf8")) as Golden;

// So speichert das iPad ein Diktat (useDictationSave) und so kommt es im Büro zurück.
function stored(r: TranscribeResult, deselected: string[] = [], adopted: string[] = []): StoredDictation {
  return {
    id: "diktat-0001",
    patient: "4711",
    patient_id: 1,
    revision: 1,
    created_at: "2026-09-23T08:00:00+00:00",
    updated_at: "2026-09-23T08:00:00+00:00",
    transcript: r.transcript,
    patient_type: r.patient_type,
    codes: r.codes,
    suggestions: r.suggestions,
    planned: r.planned ?? [],
    notes: r.notes ?? [],
    deselected,
    adopted,
  };
}

for (const [name, r] of Object.entries(fixtures)) {
  test(`Kopiertext im Büro wie am iPad: ${name}`, () => {
    const cases: Array<[string, string[]]> = [["alle", []], ...r.codes.map((c): [string, string[]] => [`ohne ${c}`, [c]])];
    for (const [label, deselected] of cases) {
      const copy = dictationCopy(stored(r, deselected));
      assert.deepEqual(copy.evident, golden[name][label].evident, `${label} (Ziffern kopieren)`);
      assert.deepEqual(copy.numbers, golden[name][label].numbers, `${label} (Nur Ziffern)`);
    }
  });
}

test("übernommene Zuzahlungs-Optionen und Mehrkosten wie am iPad", () => {
  let checked = 0;
  for (const r of Object.values(fixtures)) {
    const options = r.suggestions.filter((s) => s.alternative && s.kind === "zuzahlung").map(optionKey);
    if (options.length === 0) continue;
    const adopted = new Set(options);
    for (const deselected of [[], r.codes.slice(0, 1)]) {
      const active = r.codes.filter((c) => !deselected.includes(c));
      const evident = copyLines(r.suggestions, active, adopted);
      const copy = dictationCopy(stored(r, deselected, options));
      assert.deepEqual(copy.evident, evident);
      assert.deepEqual(copy.numbers, copyLines(r.suggestions, active, adopted, false));
      assert.deepEqual(copy.positions, positionsOf(buildGroups(r.suggestions, active, adopted, evident)));
      assert.ok(evidentText(copy.evident).length > 0);
    }
    checked += 1;
  }
  assert.ok(checked > 0, "Fixtures enthalten Zuzahlungs-Optionen");
});

function summary(fields: Partial<PatientSummary>): PatientSummary {
  return {
    id: 1,
    number: "4711",
    created_at: "2026-09-23T08:00:00+00:00",
    updated_at: "2026-09-23T08:00:00+00:00",
    dictations: 0,
    transferred: 0,
    transferred_at: null,
    ...fields,
  };
}

test("Zustand in der Liste: offen, übertragen, noch kein Diktat", () => {
  assert.equal(patientState(summary({ dictations: 2 })), "offen");
  assert.equal(patientState(summary({ dictations: 1, transferred: 1, transferred_at: "2026-09-23T09:00:00+00:00" })), "offen");
  assert.equal(patientState(summary({ transferred: 2, transferred_at: "2026-09-23T09:00:00+00:00" })), "übertragen");
  assert.equal(patientState(summary({})), "leer");
  const list = [summary({ id: 1, dictations: 1 }), summary({ id: 2, transferred: 1, transferred_at: "x" }), summary({ id: 3 })];
  assert.deepEqual(
    pickable(list).map((p) => p.id),
    [1, 3],
  );
});

test("Patientennummer: nur Ziffern, höchstens 12", () => {
  assert.equal(normalizeNumber("00 47-11a"), "004711");
  assert.equal(normalizeNumber("12345678901234"), "123456789012");
});

test("Kürzel: nur Buchstaben, Punkt, Bindestrich, höchstens 12, keine Ziffern", () => {
  assert.equal(normalizeLabel("M.K."), "M.K.");
  assert.equal(normalizeLabel("  Ö.  Ü-1980"), "Ö. Ü-");
  assert.equal(normalizeLabel("Max Mustermann"), "Max Musterma");
  assert.equal(normalizeLabel("<b>"), "b");
});

test("Nummer mit Kürzel für Texte, ohne Kürzel nur die Nummer", () => {
  assert.equal(patientName("4711", "M.K."), "4711 · M.K.");
  assert.equal(patientName("4711", null), "4711");
  assert.equal(patientName("4711"), "4711");
});

test("Kürzel kommt nie in die Kopierzeilen", () => {
  const r = fixtures[Object.keys(fixtures)[0]];
  const plain = dictationCopy(stored(r));
  const labelled = dictationCopy({ ...stored(r), patient_label: "M.K." });
  assert.deepEqual(labelled, plain);
  assert.ok(!labelled.evident.join("\n").includes("M.K."));
});

test("Vorschau des Transkripts", () => {
  assert.equal(preview("  Zahn 36   mod "), "Zahn 36 mod");
  assert.equal(preview("a".repeat(80), 10), `${"a".repeat(9)} …`);
});

test("Nummer am iPad: ein Diktat ohne Patient wird nie still zugeordnet", () => {
  // Diktat ohne Nummer auf dem Bildschirm, danach Patient 4711 eingetippt oder aus der Liste gewählt.
  assert.equal(pickAction(null, "4711", "offen"), "fragen");
  // Kein Ergebnis am Bildschirm: nur der aktive Patient wechselt.
  assert.equal(pickAction(null, "4711", "keins"), "wechseln");
  assert.equal(pickAction("4711", "4712", "keins"), "wechseln");
  // Das Diktat gehört schon einem Patienten: es bleibt dort, der Bildschirm wird frei.
  assert.equal(pickAction("4711", "4712", "offen"), "neu");
  assert.equal(pickAction("4711", null, "offen"), "neu");
  // Schon übertragen: nichts mehr zuzuordnen, nur neu beginnen.
  assert.equal(pickAction(null, "4711", "übertragen"), "neu");
  // Dieselbe Nummer noch einmal: nichts ändert sich.
  assert.equal(pickAction("4711", "4711", "offen"), "bleiben");
  assert.equal(pickAction(null, null, "offen"), "bleiben");
});
