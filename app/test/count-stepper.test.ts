// Anzahl mit − / + am iPad: nur an mengenweise berechneten Zeilen laut Katalog, nie unter 1, nie über die
// bestätigte Höchstzahl; Kopierzeile, Kanalzahl-Prüfhinweis, Neu berechnen und Korrektur-Vergleich.
import assert from "node:assert/strict";
import { test } from "node:test";
import type { Suggestion, SuggestionKind } from "../src/api.ts";
import { byCode, codesOf, mainPositions, type CatalogEntry } from "../src/catalog.ts";
import { countRange, recompute, setCount } from "../src/correction.ts";
import { buildGroups, copyLines } from "../src/result.ts";
import { codeChanges, describe } from "../src/textdiff.ts";

const OPEN = "Kanalzahl nicht diktiert – je Kanal berechnen";

function entry(code: string, system: string, kind: SuggestionKind, extra: Partial<CatalogEntry> = {}): CatalogEntry {
  return { code, system, title: `Titel ${code}`, area: "Endodontie", points: null, kind, family: [], ...extra };
}

const CATALOG = byCode([
  entry("32", "BEMA", "bema", { counted: true }), // je Kanal
  entry("35", "BEMA", "bema", { counted: true, evident: "wf" }),
  entry("2400", "GOZ", "zuzahlung", { counted: true }),
  entry("IP4", "BEMA", "bema", { counted: true, max_count: 2 }), // bestätigt höchstens 2× je Sitzung
  entry("12", "BEMA", "bema", { counted: false, max_count: 1, evident: "bmf" }),
  entry("13b", "BEMA", "bema", { family: ["13a", "13b", "13c", "13d"] }),
]);

function s(code: string, teeth: number[], extra: Partial<Suggestion> = {}): Suggestion {
  const e = CATALOG.get(code)!;
  return {
    code, system: e.system, title: e.title, kind: e.kind, count: 1, points: null, teeth, reason: "wegen: diktiert",
    decide: [], alternative: false, evident: e.evident ?? null, ...extra,
  };
}

// Kassenpatient: Endo an 46 ohne diktierte Kanalzahl, dazu 13b an 36.
const ENDO: Suggestion[] = [
  s("32", [46], { decide: [OPEN] }),
  s("2400", [46], { alternative: true, kind: "zuzahlung", reason: "Zuzahlung möglich zu BEMA 32: x", decide: [OPEN] }),
  s("35", [46], { decide: [OPEN] }),
  s("13b", [36]),
];
const none = new Set<string>();
const lines = (list: Suggestion[]) => copyLines(list, codesOf(list), none);

test("Knöpfe nur an mengenweise berechneten Positionen, bis zur bestätigten Höchstzahl", () => {
  assert.deepEqual(countRange(CATALOG.get("32")), { max: null });
  assert.deepEqual(countRange(CATALOG.get("IP4")), { max: 2 });
  assert.equal(countRange(CATALOG.get("12")), null); // einmal je Bereich
  assert.equal(countRange(CATALOG.get("13b")), null); // je Zahn
  assert.equal(countRange(undefined), null); // Katalog noch nicht da
  assert.equal(countRange(entry("X", "BEMA", "bema", { counted: true, max_count: 1 })), null);
});

test("Anzahl setzen ändert die Evident-Zeile und entscheidet den Kanalzahl-Hinweis", () => {
  assert.deepEqual(lines(ENDO), ["46,32,wf", "36,13b"]);
  const out = setCount(setCount(ENDO, 46, "32", 3), 46, "35", 3);
  assert.deepEqual(lines(out), ["46,32*3,wf*3", "36,13b"]);
  const wk = out.find((x) => x.code === "32")!;
  assert.deepEqual([wk.count, wk.source, wk.counted, wk.decide], [3, "geaendert", true, []]);
  // Die Zuzahlungs-Option ist eine eigene Zeile: sie behält ihre Anzahl und ihren Hinweis.
  assert.deepEqual(out.find((x) => x.code === "2400")!.decide, [OPEN]);
  assert.equal(out.find((x) => x.code === "13b"), ENDO[3]); // andere Zeilen unverändert
  const row = buildGroups(out, codesOf(out), none, lines(out))
    .flatMap((g) => g.items)
    .find((i) => "row" in i && i.row.s.code === "32");
  assert.ok(row && "row" in row && row.row.count === 3 && row.row.source === "geaendert");
});

test("Nie unter 1, nie über die bestätigte Höchstzahl, nur an diesem Zahn", () => {
  assert.equal(setCount(ENDO, 46, "32", 0)[0].count, 1);
  assert.equal(setCount([s("IP4", [])], null, "IP4", 5, 2)[0].count, 2);
  const two = [s("32", [46]), s("32", [47])];
  assert.deepEqual(copyLines(setCount(two, 47, "32", 2), ["32"], none), ["46,32", "47,32*2"]);
  // Weniger geht auch: diktiertes WK*3 auf 2.
  assert.deepEqual(lines(setCount(setCount(ENDO, 46, "32", 3), 46, "32", 2))[0], "46,32*2,wf");
});

test("Neu berechnen behält die von Hand gesetzte Anzahl, wo die Ziffer am Zahn wiederkommt", () => {
  const set = setCount(ENDO, 46, "32", 3);
  assert.deepEqual(lines(recompute(set, ENDO, CATALOG)), ["46,32*3,wf", "36,13b"]);
  assert.deepEqual(lines(recompute(set, [s("13b", [36])], CATALOG)), ["36,13b"]); // Endo nicht mehr diktiert
});

test("Streifen und Korrektur-Vergleich nennen die geänderte Anzahl", () => {
  const changes = codeChanges(mainPositions(ENDO), mainPositions(setCount(ENDO, 46, "32", 3)), CATALOG);
  assert.equal(changes.length, 1);
  assert.match(describe(changes, "neu"), /32.*3x 32.*46/);
});
