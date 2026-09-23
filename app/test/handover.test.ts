// Zweiter Kurzcode nach einer Korrektur: Rezeption und Büro sehen, was schon abgeholt wurde und was neu ist –
// je Zahn und Position mit Anzahl, getrennt nach Kassen- und Privatblock.
import assert from "node:assert/strict";
import { test } from "node:test";
import { joinBlocks, splitBlocks } from "../src/api.ts";
import { handoverDiff } from "../src/handover.ts";

const at = (min: number) => `2026-09-23T08:${String(min).padStart(2, "0")}:00+00:00`;
const A = { fetched_at: at(10), codes: ["36,13c"] };
const none = { kasse: [], privat: [] };
const kasse = (...lines: string[]) => ({ kasse: lines, privat: [] });

test("Code A (36,13c) abgeholt, danach 2100 übernommen: nur 2100 ist neu", () => {
  assert.deepEqual(handoverDiff(kasse("36,13c,2100"), [A]), { added: kasse("36,2100"), removed: none, changed: none });
});

test("nach der Abholung abgewählt: als nicht mehr enthalten gemeldet", () => {
  assert.deepEqual(handoverDiff(kasse("36,2100"), [A]), {
    added: kasse("36,2100"),
    removed: kasse("36,13c"),
    changed: none,
  });
});

test("je Zahn verglichen, Zeile ohne Zahn bleibt als solche erkennbar", () => {
  const earlier = [A, { fetched_at: at(20), codes: ["36,13c,2100", ",01"] }];
  const diff = handoverDiff(kasse("36,13c,2100", "37,13c", ",01,Ä1"), earlier);
  assert.deepEqual(diff.added, kasse("37,13c", ",Ä1"));
  assert.deepEqual(diff.removed, none);
});

test("ohne frühere Abholung ist alles neu", () => {
  assert.deepEqual(handoverDiff(kasse("36,13c"), []).added, kasse("36,13c"));
});

test("nur die Anzahl geändert (wf*2 abgeholt, jetzt wf*3): 1× nachtragen, nicht wf*3 obendrauf", () => {
  const earlier = [{ fetched_at: at(10), codes: ["36,wf*2"] }];
  assert.deepEqual(handoverDiff(kasse("36,wf*3"), earlier), {
    added: none,
    removed: none,
    changed: { kasse: ["36: wf jetzt 3× statt 2× – 1× nachtragen"], privat: [] },
  });
  assert.deepEqual(handoverDiff(kasse("36,wf"), earlier).changed.kasse, [
    "36: wf jetzt 1× statt 2× – 1× zu viel in Evident – prüfen",
  ]);
});

test("zwei Abholungen mit derselben Position zählen nicht doppelt", () => {
  const earlier = [
    { fetched_at: at(10), codes: ["36,wf*2"] },
    { fetched_at: at(20), codes: ["36,wf*2,2100"] },
  ];
  assert.deepEqual(handoverDiff(kasse("36,wf*2,2100"), earlier), { added: none, removed: none, changed: none });
});

test("Kassenpatient: 46,13c (Kasse) und 2100 an 36 (Zuzahlung) neu – getrennt, Kasse zuerst", () => {
  // Code A mit 36,13c abgeholt; danach 13c an 46 und die Zuzahlung 2100 an 36.
  const current = { kasse: ["36,13c", "46,13c"], privat: ["36,2100"] };
  assert.deepEqual(joinBlocks(current), ["36,13c", "46,13c", "", "36,2100"]); // so kommt Code B an
  const diff = handoverDiff(splitBlocks(joinBlocks(current)), [A]);
  assert.deepEqual(diff.added, { kasse: ["46,13c"], privat: ["36,2100"] });
  assert.deepEqual(diff.removed, none);
});

test("Kassenpatient: Kassen- und Privatposition ohne Zahn bleiben getrennt", () => {
  const earlier = [{ fetched_at: at(10), codes: [",01"] }];
  const diff = handoverDiff({ kasse: [",01"], privat: [",Ä1"] }, earlier);
  assert.deepEqual(diff.added, { kasse: [], privat: [",Ä1"] });
  assert.deepEqual(diff.removed, none);
});

test("Privatpatient: frühere Abholung ohne Leerzeile ist der Privatblock", () => {
  const earlier = [{ fetched_at: at(10), codes: ["36,2080"] }];
  const diff = handoverDiff({ kasse: [], privat: ["36,2080,2100"] }, earlier, true);
  assert.deepEqual(diff.added, { kasse: [], privat: ["36,2100"] });
  assert.deepEqual(diff.removed, none);
});
