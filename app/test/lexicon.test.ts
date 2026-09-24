// Wörterbuch-Seite: Anzeige von Herkunft und „seit …“, Füllstand des Prompts, Kalenderwochen, Ziffernänderungen.
import assert from "node:assert/strict";
import { test } from "node:test";
import type { TranscribeResult } from "../src/api.ts";
import {
  codeChange,
  entryMeta,
  gaugeView,
  probeCodes,
  probeKey,
  sinceLabel,
  weekRange,
  type LexiconEntry,
  type LexiconSuggestion,
} from "../src/lexicon.ts";

const sept24 = new Date(2026, 8, 24, 10, 0).getTime() / 1000;
const entry: LexiconEntry = {
  id: 1, kind: "ersetzung", wrong: "Zahn steinentfernung", right: "Zahnsteinentfernung", active: true,
  source: "korrektur", created_at: sept24,
};

test("Herkunft und seit wann, abgeschaltet statt gelöscht", () => {
  assert.equal(sinceLabel(sept24), "seit 24.09.");
  assert.equal(entryMeta(entry), "aus Korrekturen übernommen · seit 24.09.");
  assert.equal(entryMeta({ ...entry, source: "hand", active: false }), "von Hand · abgeschaltet");
});

test("Füllstand: Grundtext und Ergänzungen im Verhältnis zur Grenze von whisper.cpp", () => {
  const g = gaugeView({ base: "", base_tokens: 150, terms_tokens: 13, limit: 223, exact: true });
  assert.deepEqual(g, { basePct: 67, termsPct: 6, used: 163, free: 60, moreTerms: 10, full: false });
  const full = gaugeView({ base: "", base_tokens: 150, terms_tokens: 70, limit: 223, exact: true });
  assert.equal(full.full, true);
  assert.equal(full.basePct + full.termsPct <= 100, true);
  const over = gaugeView({ base: "", base_tokens: 216, terms_tokens: 20, limit: 223, exact: false });
  assert.equal(over.free, 0);
  assert.equal(over.basePct + over.termsPct, 100);
});

test("Kalenderwochen der Sammlung", () => {
  assert.equal(weekRange("2026-W39", "2026-W40"), "KW 39–40");
  assert.equal(weekRange("2026-W39", "2026-W39"), "KW 39");
  assert.equal(weekRange("2026-W52", "2027-W02"), "KW 52/2026 – 2/2027");
  assert.equal(weekRange(null, null), "");
});

test("Ziffernänderungen sind nur Information", () => {
  const s = (before: string, after: string): LexiconSuggestion =>
    ({ kind: "ziffer", before, after, count: 1, takeable: false, taken: false });
  assert.equal(codeChange(s("13b", "13c")), "13b → 13c");
  assert.equal(codeChange(s("", "107")), "107 ergänzt");
  assert.equal(codeChange(s("13b", "")), "13b entfernt");
});

test("Probe gilt nur für genau diesen Entwurf und Satz", () => {
  const draft = { wrong: "Zahn steinentfernung", right: "Zahnsteinentfernung" };
  assert.equal(probeKey(draft, "Satz"), probeKey({ wrong: " Zahn steinentfernung ", right: draft.right }, "Satz "));
  assert.notEqual(probeKey(draft, "Satz"), probeKey({ ...draft, right: "Zahnstein" }, "Satz"));
  assert.notEqual(probeKey(draft, "Satz"), probeKey(draft, "anderer Satz"));
  const result = (codes: string[]) => ({ codes }) as unknown as TranscribeResult;
  assert.equal(probeCodes(result(["107", "IP4"])), "107, IP4");
  assert.equal(probeCodes(result([])), "keine");
});
