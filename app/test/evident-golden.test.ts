// Kopierformat für Evident bleibt Zeichen für Zeichen: `fixtures/evident-golden.json` wurde mit dem
// Stand von main 7eaf85a (PR #12) aus `fixtures/anhang-b.json` erzeugt – die zwölf Anhang-B-Diktate
// plus das Abnahme-Diktat (docs/abnahme.md 1.3 mit Inlay 46 und „kein OPG“), je Kasse und Privat,
// als echte Server-Antworten (`build_response`). Geprüft werden alle Ziffern ausgewählt und jede
// einzelne Ziffer abgewählt, mit Kurzformen und „Nur Ziffern“.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { evidentLines, type TranscribeResult } from "../src/api.ts";

type Golden = Record<string, Record<string, { evident: string[]; numbers: string[] }>>;

const fixtures = JSON.parse(readFileSync(new URL("./fixtures/anhang-b.json", import.meta.url), "utf8")) as Record<
  string,
  TranscribeResult
>;
const golden = JSON.parse(readFileSync(new URL("./fixtures/evident-golden.json", import.meta.url), "utf8")) as Golden;

// Auswahlfälle wie beim Erzeugen: alle Ziffern, dann je eine abgewählt.
function selections(codes: string[]): Array<[string, string[]]> {
  return [["alle", codes], ...codes.map((c): [string, string[]] => [`ohne ${c}`, codes.filter((x) => x !== c)])];
}

test("Goldstandard deckt alle Diktate ab (12 Anhang-B + Abnahme, je Kasse und Privat)", () => {
  assert.equal(Object.keys(fixtures).length, 26);
  assert.deepEqual(Object.keys(golden).sort(), Object.keys(fixtures).sort());
});

for (const [name, result] of Object.entries(fixtures)) {
  test(`evidentLines unverändert: ${name}`, () => {
    for (const [label, active] of selections(result.codes)) {
      const expected = golden[name][label];
      assert.deepEqual(evidentLines(result.suggestions, active), expected.evident, `${label} (Kurzformen)`);
      assert.deepEqual(evidentLines(result.suggestions, active, false), expected.numbers, `${label} (Nur Ziffern)`);
    }
  });
}
