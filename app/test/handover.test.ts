// Zweiter Kurzcode nach einer Korrektur: Rezeption und Büro sehen, was schon abgeholt wurde und was neu ist.
import assert from "node:assert/strict";
import { test } from "node:test";
import { handoverDiff } from "../src/handover.ts";

const A = { fetched_at: "2026-09-23T08:10:00+00:00", codes: ["36,13c"] };

test("Code A (36,13c) abgeholt, danach 2100 übernommen: nur 2100 ist neu", () => {
  assert.deepEqual(handoverDiff(["36,13c,2100"], [A]), { added: ["36,2100"], removed: [] });
});

test("nach der Abholung abgewählt: als nicht mehr enthalten gemeldet", () => {
  assert.deepEqual(handoverDiff(["36,2100"], [A]), { added: ["36,2100"], removed: ["36,13c"] });
});

test("je Zahn verglichen, Zeile ohne Zahn bleibt als solche erkennbar", () => {
  const earlier = [A, { fetched_at: "2026-09-23T08:20:00+00:00", codes: ["36,13c,2100", ",01"] }];
  assert.deepEqual(handoverDiff(["36,13c,2100", "37,13c", ",01,Ä1"], earlier), {
    added: ["37,13c", ",Ä1"],
    removed: [],
  });
});

test("ohne frühere Abholung ist alles neu", () => {
  assert.deepEqual(handoverDiff(["36,13c"], []), { added: ["36,13c"], removed: [] });
});
