// Tests für den eigenen QR-Encoder (node --test, ohne zusätzliche Abhängigkeit).
import assert from "node:assert/strict";
import { test } from "node:test";
import { encodeQr, reedSolomon } from "../src/qr/encode.ts";

test("Reed-Solomon: bekannter Prüfvektor (Version 1-L)", () => {
  // "HELLO WORLD" im Byte-Modus, Version 1, Stufe L: 19 Datencodewörter
  // (Modus 0100, Länge 11, Text, Terminator, Füllbytes EC/11) und die
  // 7 EC-Codewörter aus der Referenzimplementierung segno (ISO 18004).
  const data = new Uint8Array([
    0x40, 0xb4, 0x84, 0x54, 0xc4, 0xc4, 0xf2, 0x05, 0x74, 0xf5, 0x24, 0xc4, 0x40, 0xec, 0x11, 0xec, 0x11, 0xec, 0x11,
  ]);
  assert.deepEqual(Array.from(reedSolomon(data, 7)), [0xc8, 0x46, 0x26, 0x41, 0xe8, 0xf8, 0xf6]);
});

// Format-Information (15 Bit, BCH-kodiert und maskiert) für Stufe L je Maske,
// Tabelle C.1 der Norm; Index = Maskenmuster.
const FORMAT_L = [
  "111011111000100",
  "111001011110011",
  "111110110101010",
  "111100010011101",
  "110011000101111",
  "110001100011000",
  "110110001000001",
  "110100101110110",
];

// Liest die 15 Format-Bits (MSB zuerst) aus beiden Kopien der Matrix.
function readFormatBits(m: boolean[][]): { primary: string; secondary: string } {
  const s = m.length;
  const b = (row: number, col: number) => (m[row][col] ? "1" : "0");
  let primary = "";
  for (let col = 0; col <= 5; col++) primary += b(8, col);
  primary += b(8, 7) + b(8, 8) + b(7, 8);
  for (let row = 5; row >= 0; row--) primary += b(row, 8);
  let secondary = "";
  for (let row = s - 1; row >= s - 7; row--) secondary += b(row, 8);
  for (let col = s - 8; col <= s - 1; col++) secondary += b(8, col);
  return { primary, secondary };
}

for (const text of ["HELLO WORLD", "https://medvox.local/transfer?code=ABC234"]) {
  test(`Format-Information ist gültig für Stufe L und die gewählte Maske (${text})`, () => {
    const m = encodeQr(text);
    const { primary, secondary } = readFormatBits(m);
    assert.equal(secondary, primary);
    const info = parseInt(primary, 2) ^ 0x5412; // 2 Bit EC-Stufe, 3 Bit Maske, 10 Bit BCH
    assert.equal((info >> 13) & 0b11, 0b01, "EC-Stufe L");
    assert.equal(primary, FORMAT_L[(info >> 10) & 0b111]);
    assert.equal(m[m.length - 8][8], true, "stets dunkles Modul");
  });
}

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
