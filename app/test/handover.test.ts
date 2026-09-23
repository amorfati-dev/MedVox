// Zweiter Kurzcode nach einer Korrektur: Rezeption und Büro sehen, was schon abgeholt wurde und was neu ist.
import assert from "node:assert/strict";
import { test } from "node:test";
import { handoverDiff } from "../src/handover.ts";

const A = { fetched_at: "2026-09-23T08:10:00+00:00", codes: ["36,13c"] };

test("Code A (36,13c) abgeholt, danach 2100 übernommen: nur 2100 ist neu", () => {
  assert.deepEqual(handoverDiff(["36,13c,2100"], [A]), { added: ["36,2100"], removed: [], changed: [] });
});

test("nach der Abholung abgewählt: als nicht mehr enthalten gemeldet", () => {
  assert.deepEqual(handoverDiff(["36,2100"], [A]), { added: ["36,2100"], removed: ["36,13c"], changed: [] });
});

test("je Zahn verglichen, Zeile ohne Zahn bleibt als solche erkennbar", () => {
  const earlier = [A, { fetched_at: "2026-09-23T08:20:00+00:00", codes: ["36,13c,2100", ",01"] }];
  assert.deepEqual(handoverDiff(["36,13c,2100", "37,13c", ",01,Ä1"], earlier), {
    added: ["37,13c", ",Ä1"],
    removed: [],
    changed: [],
  });
});

test("ohne frühere Abholung ist alles neu", () => {
  assert.deepEqual(handoverDiff(["36,13c"], []), { added: ["36,13c"], removed: [], changed: [] });
});

test("nur die Anzahl geändert (wf*2 abgeholt, jetzt wf*3): 1× nachtragen, nicht wf*3 obendrauf", () => {
  const earlier = [{ fetched_at: "2026-09-23T08:10:00+00:00", codes: ["36,wf*2"] }];
  assert.deepEqual(handoverDiff(["36,wf*3"], earlier), {
    added: [],
    removed: [],
    changed: ["36: wf jetzt 3× statt 2× – 1× nachtragen"],
  });
  assert.deepEqual(handoverDiff(["36,wf"], earlier).changed, ["36: wf jetzt 1× statt 2× – 1× zu viel in Evident – prüfen"]);
});

test("zwei Abholungen mit derselben Position zählen nicht doppelt", () => {
  const earlier = [
    { fetched_at: "2026-09-23T08:10:00+00:00", codes: ["36,wf*2"] },
    { fetched_at: "2026-09-23T08:20:00+00:00", codes: ["36,wf*2,2100"] },
  ];
  assert.deepEqual(handoverDiff(["36,wf*2,2100"], earlier), { added: [], removed: [], changed: [] });
});
