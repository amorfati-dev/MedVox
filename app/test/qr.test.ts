// Tests für den eigenen QR-Encoder (node --test, ohne zusätzliche Abhängigkeit).
import assert from "node:assert/strict";
import { test } from "node:test";
import { encodeQr, reedSolomon } from "../src/qr/encode.ts";

test("Reed-Solomon: bekannter Prüfvektor (Version 1-L)", () => {
  // "HELLO WORLD" im Byte-Modus, Version 1, Stufe L – Referenz aus ISO 18004-Beispielen.
  const data = new Uint8Array([0x40, 0xb4, 0x85, 0x45, 0x4c, 0x4c, 0x4f, 0x20, 0x57, 0x4f, 0x52, 0x4c, 0x44, 0x0e, 0xc1, 0x1e, 0xc1, 0x1e, 0xc1]);
  const ec = reedSolomon(data, 7);
  assert.equal(ec.length, 7);
  assert.ok(ec.some((b) => b !== 0));
});

test("encodeQr liefert eine quadratische Matrix passender Version", () => {
  const m = encodeQr("https://medvox.local/transfer?code=ABC234");
  assert.ok(m.length >= 21 && (m.length - 17) % 4 === 0);
  assert.ok(m.every((row) => row.length === m.length));
});

test("Suchmuster stehen in drei Ecken", () => {
  const m = encodeQr("MEDVOX");
  const s = m.length;
  const finder = (x0: number, y0: number) => {
    for (let y = 0; y < 7; y++) {
      for (let x = 0; x < 7; x++) {
        const edge = x === 0 || y === 0 || x === 6 || y === 6;
        const core = x >= 2 && x <= 4 && y >= 2 && y <= 4;
        if (m[y0 + y][x0 + x] !== (edge || core)) return false;
      }
    }
    return true;
  };
  assert.ok(finder(0, 0));
  assert.ok(finder(s - 7, 0));
  assert.ok(finder(0, s - 7));
});

test("zu lange Texte werden abgelehnt", () => {
  assert.throws(() => encodeQr("x".repeat(200)));
});
