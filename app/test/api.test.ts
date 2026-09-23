import assert from "node:assert/strict";
import { test } from "node:test";
import { codeOf, joinCodes, kindsOf, normalizeCode, parsePatientType } from "../src/api.ts";

test("normalizeCode: Großschreibung, nur erlaubtes Alphabet, 6 Zeichen", () => {
  assert.equal(normalizeCode("abc234"), "ABC234");
  assert.equal(normalizeCode(" a-b c 2 3 4 5 "), "ABC234");
  assert.equal(normalizeCode("0O1Iab"), "AB");
  assert.equal(normalizeCode("ABCDEFGH"), "ABCDEF");
});

test("joinCodes: Kopierformat der Praxis", () => {
  assert.equal(joinCodes(["01", "8", "13c", "2080"]), "01, 8, 13c, 2080");
  assert.equal(joinCodes([]), "");
});

test("codeOf: Anzahl aus dem Kopierformat entfernen", () => {
  assert.equal(codeOf("2x 41a"), "41a");
  assert.equal(codeOf("28x 1040"), "1040");
  assert.equal(codeOf("Ä925a"), "Ä925a");
});

test("kindsOf: nur Hauptvorschläge bestimmen die Art einer Ziffer", () => {
  const base = { system: "GOZ", title: "", count: 1, teeth: [], reason: "", decide: [] };
  const kinds = kindsOf([
    { ...base, code: "13c", system: "BEMA", kind: "bema", alternative: false },
    { ...base, code: "2100", kind: "zuzahlung", alternative: true },
    { ...base, code: "2060", kind: "zuzahlung", alternative: false },
  ]);
  assert.deepEqual(kinds, { "13c": "bema", "2060": "zuzahlung" });
});

test("parsePatientType: unbekannte Werte gelten als Kasse", () => {
  assert.equal(parsePatientType("privat"), "privat");
  assert.equal(parsePatientType("kasse"), "kasse");
  assert.equal(parsePatientType(null), "kasse");
  assert.equal(parsePatientType("PRIVAT"), "kasse");
});
