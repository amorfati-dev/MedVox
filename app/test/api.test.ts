import assert from "node:assert/strict";
import { test } from "node:test";
import { joinCodes, normalizeCode } from "../src/api.ts";

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
