// Rückmeldung des Behandlers zur Weisheitszahn-OP (Kassenpatient, 2026-09-24): echtes Whisper-Transkript als
// Server-Antwort in `fixtures/weisheitszahn-op.json` (erzeugt und geprüft in server/tests/test_extract_surgery.py).
// Erwartet: 18 und 28 je I*2 + Ost2, 38 und 48 je L1*2 + Ost2, dazu das OPG; Ä1 und Zst stehen als Option
// „ggf. dazu“ und kommen nur nach Antippen in die Kassenzeile. Zweites Diktat („pausen“, Whisper mit Punkten bei
// jeder Pause): 18 = I + X2 (KZVB: zweite Anästhesie erst ab Ost1), 28 = I*2 + Ost1.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import type { TranscribeResult } from "../src/api.ts";
import { buildGroups, copyLines, optionKey, positionsOf } from "../src/result.ts";

const fixtures = JSON.parse(readFileSync(new URL("./fixtures/weisheitszahn-op.json", import.meta.url), "utf8")) as Record<
  string,
  TranscribeResult
>;
const none = new Set<string>();
const KASSE = ["18,i*2,ost2", "28,i*2,ost2", "38,ost2,l1*2", "48,l1*2,ost2,opg"];

test("Weisheitszahn-OP, Kassenpatient: Anästhesie und Ost2 je Zahn, Optionen nicht vorausgewählt", () => {
  const r = fixtures["pilot-kasse"];
  assert.deepEqual(copyLines(r.suggestions, r.codes, none), KASSE);
  assert.deepEqual(copyLines(r.suggestions, r.codes, none, false), [
    "18,40*2,48", "28,40*2,48", "38,48,41a*2", "48,41a*2,48,Ä935d",
  ]);
  const options = r.suggestions.filter((s) => s.alternative);
  assert.deepEqual(options.map((s) => [optionKey(s), s.addon, s.kind]), [["Ä1@28", true, "bema"], ["107@28", true, "bema"]]);
});

test("Weisheitszahn-OP: Ä1 und Zst nach Antippen in der Kassenzeile, an der Rezeption als Kassenleistung", () => {
  const r = fixtures["pilot-kasse"];
  const adopted = new Set(["Ä1@28", "107@28"]);
  const lines = copyLines(r.suggestions, r.codes, adopted);
  assert.deepEqual(lines, [KASSE[0], "28,i*2,ost2,Ä1,107", ...KASSE.slice(2)]);
  const positions = positionsOf(buildGroups(r.suggestions, r.codes, adopted, lines));
  assert.deepEqual(positions.filter((p) => p.code === "Ä1" || p.code === "107"), [
    { tooth: 28, code: "Ä1", kind: "bema" }, { tooth: 28, code: "107", kind: "bema" },
  ]);
});

test("Weisheitszahn-OP, Privatpatient: nur GOÄ Ä1 als Option, im Privatblock nach Antippen", () => {
  const r = fixtures["pilot-privat"];
  assert.deepEqual(r.suggestions.filter((s) => s.addon).map(optionKey), ["Ä1@28"]);
  const lines = copyLines(r.suggestions, r.codes, new Set(["Ä1@28"]));
  assert.ok(lines[1].startsWith("28,0090*2,3040") && lines[1].endsWith(",Ä1"), lines[1]);
});

test("Zweites Diktat mit Pausen, Kassenpatient: 18 I + X2, 28 I*2 + Ost1", () => {
  const r = fixtures["pausen-kasse"];
  assert.deepEqual(copyLines(r.suggestions, r.codes, none), ["18,i,44", "28,i*2,ost1"]);
  assert.deepEqual(copyLines(r.suggestions, r.codes, none, false), ["18,40,44", "28,40*2,47a"]);
  const i18 = r.suggestions.find((s) => s.code === "40" && s.teeth[0] === 18);
  assert.ok(i18?.decide.some((d) => d.startsWith("Zweite Anästhesie nur ab Ost1 abrechenbar (KZVB)")));
});
