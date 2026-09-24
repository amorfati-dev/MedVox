// Beispiel-Diktat des Behandlers zur Wurzelkanalbehandlung (Testpatient „ohne Patient“), als echte Server-
// Antworten in `fixtures/endo-beispiel.json` (erzeugt und gegen den Server geprüft in
// server/tests/test_extract_endo.py). Diktierte Kanalzahl kopiert als "*3" („WK*3“ → 32*3, „VitE*3“ → 28*3);
// „phys“ (2420) und Längenbestimmung (2400) zählen je Kanal wie WK; weitere Endo-Zuzahlungen stehen beim
// Kassenpatienten als Option da und kommen nur nach Antippen dazu.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import type { TranscribeResult } from "../src/api.ts";
import { copyLines, optionKey } from "../src/result.ts";

const fixtures = JSON.parse(readFileSync(new URL("./fixtures/endo-beispiel.json", import.meta.url), "utf8")) as Record<
  string,
  TranscribeResult
>;
const none = new Set<string>();
const ENDO_KASSE = ["46,32*3,40,Ä925a,28*3,34", "", "46,2420*3,2400*3"];
const ENDO_PRIVAT = ["46,2410*3,0090,Ä5000,2360*3,2430,2420*3,2400*3"];

for (const name of ["original", "gesprochen", "verhoert", "getippt"]) {
  test(`Evident-Zeilen des Endo-Beispiels, Kassenpatient: ${name}`, () => {
    const r = fixtures[`${name}-kasse`];
    const filling = name === "gesprochen" || name === "getippt" ? ["25,13b,bmf"] : [];
    const [kasse, gap, privat] = ENDO_KASSE;
    assert.deepEqual(copyLines(r.suggestions, r.codes, none), [...filling, kasse, gap, privat]);
    const options = r.suggestions.filter((s) => s.alternative).map((s) => `${s.code}@${s.teeth.join("+")}`);
    assert.deepEqual(options, [...(filling.length ? ["2080@25"] : []), "2197@46", "2430@46"]);
  });

  test(`Endo-Beispiel, Privatpatient ohne Optionen: ${name}`, () => {
    const r = fixtures[`${name}-privat`];
    assert.equal(r.suggestions.filter((s) => s.alternative).length, 0);
    assert.deepEqual(copyLines(r.suggestions, r.codes, none).filter((l) => l.startsWith("46")), ENDO_PRIVAT);
  });
}

test("Endo-Option kommt nur nach Antippen in den Privatblock", () => {
  const r = fixtures["original-kasse"];
  const option = r.suggestions.find((s) => s.code === "2197");
  assert.ok(option);
  assert.deepEqual(copyLines(r.suggestions, r.codes, new Set([optionKey(option)])), [
    "46,32*3,40,Ä925a,28*3,34",
    "",
    "46,2197,2420*3,2400*3",
  ]);
});

test("Pilot-Diktat „2x WD, 2x WK, MET“: Anzahl davor kopiert wie „WK*2“, 46 unverändert", () => {
  const r = fixtures["pilot-wd-kasse"];
  assert.deepEqual(copyLines(r.suggestions, r.codes, none), ["25,40,32*2,28*2,34", "46,13c,l1,pan1,bmf"]);
  const options = r.suggestions.filter((s) => s.alternative).map((s) => `${s.code}@${s.teeth.join("+")}`);
  assert.deepEqual(options, ["2400@25", "2420@25", "2197@25", "2430@25", "2100@46"]);
});
