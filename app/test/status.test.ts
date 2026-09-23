import assert from "node:assert/strict";
import { test } from "node:test";
import { formatClock, formatSeconds, plural, uiState, type StatusInput } from "../src/status.ts";

const base: StatusInput = { phase: "bereit", supported: true, discardable: false, error: null, transcript: "" };

test("uiState: die sechs Zustände", () => {
  assert.equal(uiState(base), "bereit");
  assert.equal(uiState({ ...base, transcript: "Zahn 36" }), "fertig");
  assert.equal(uiState({ ...base, phase: "aufnahme" }), "aufnahme");
  assert.equal(uiState({ ...base, phase: "sende" }), "senden");
  assert.equal(uiState({ ...base, phase: "fortsetzbar", error: "WLAN weg" }), "fortsetzbar");
  assert.equal(uiState({ ...base, phase: "fortsetzbar", discardable: true, error: "zu lang" }), "fehler");
  assert.equal(uiState({ ...base, error: "Mikrofon verweigert" }), "fehler");
  assert.equal(uiState({ ...base, supported: false }), "fehler");
});

test("uiState: Aufnahme geht vor jedem Fehler", () => {
  assert.equal(uiState({ ...base, phase: "aufnahme", error: "x", discardable: true }), "aufnahme");
});

test("formatClock, plural, formatSeconds", () => {
  assert.equal(formatClock(7), "0:07");
  assert.equal(formatClock(59), "0:59");
  assert.equal(formatClock(60), "1:00");
  assert.equal(plural(1, "Abschnitt", "Abschnitte"), "1 Abschnitt");
  assert.equal(plural(2, "Abschnitt", "Abschnitte"), "2 Abschnitte");
  assert.equal(formatSeconds(0.79), "0,8 s");
});
