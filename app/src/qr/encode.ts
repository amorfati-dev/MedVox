// Kleiner QR-Code-Encoder ohne Abhängigkeiten (ISO/IEC 18004).
// Bewusst eingeschränkt auf das, was MedVox braucht: Byte-Modus,
// Fehlerkorrektur-Stufe L, Versionen 1–5 (bis 108 Byte, ein RS-Block).
// Ergebnis ist eine quadratische Matrix aus booleschen Modulen (true = dunkel).

export type QrMatrix = boolean[][];

// Pro Version (Index 0 = Version 1): Gesamt-Codewörter und EC-Codewörter (Stufe L).
const TOTAL_CODEWORDS = [26, 44, 70, 100, 134];
const EC_CODEWORDS = [7, 10, 15, 20, 26];
const FORMAT_BITS_L = 1; // EC-Stufe L im Format-Feld

// ---------------------------------------------------------------------------
// Galois-Feld GF(256) mit dem QR-Primitivpolynom 0x11D
// ---------------------------------------------------------------------------

const EXP = new Uint8Array(512);
const LOG = new Uint8Array(256);
(() => {
  let x = 1;
  for (let i = 0; i < 255; i++) {
    EXP[i] = x;
    LOG[x] = i;
    x <<= 1;
    if (x & 0x100) x ^= 0x11d;
  }
  for (let i = 255; i < 512; i++) EXP[i] = EXP[i - 255];
})();

function gfMul(a: number, b: number): number {
  if (a === 0 || b === 0) return 0;
  return EXP[LOG[a] + LOG[b]];
}

// Reed-Solomon-Prüfbytes für `data` mit `count` EC-Codewörtern.
export function reedSolomon(data: Uint8Array, count: number): Uint8Array {
  // Generatorpolynom (x - α^0)(x - α^1)…(x - α^(count-1))
  let gen = [1];
  for (let i = 0; i < count; i++) {
    const next = new Array<number>(gen.length + 1).fill(0);
    for (let j = 0; j < gen.length; j++) {
      next[j] ^= gen[j];
      next[j + 1] ^= gfMul(gen[j], EXP[i]);
    }
    gen = next;
  }
  const rest = new Uint8Array(count);
  for (const byte of data) {
    const factor = byte ^ rest[0];
    rest.copyWithin(0, 1);
    rest[count - 1] = 0;
    for (let j = 0; j < count; j++) rest[j] ^= gfMul(gen[j + 1], factor);
  }
  return rest;
}

// ---------------------------------------------------------------------------
// Datenstrom: Modus, Länge, Nutzdaten, Terminator, Füllbytes, EC-Bytes
// ---------------------------------------------------------------------------

function chooseVersion(byteLength: number): number {
  for (let v = 1; v <= TOTAL_CODEWORDS.length; v++) {
    if (TOTAL_CODEWORDS[v - 1] - EC_CODEWORDS[v - 1] - 2 >= byteLength) return v;
  }
  throw new Error(`QR: Text zu lang (${byteLength} Byte, maximal 106)`);
}

function buildCodewords(bytes: Uint8Array, version: number): Uint8Array {
  const dataLen = TOTAL_CODEWORDS[version - 1] - EC_CODEWORDS[version - 1];
  const bits: number[] = [];
  const push = (value: number, width: number) => {
    for (let i = width - 1; i >= 0; i--) bits.push((value >>> i) & 1);
  };
  push(0b0100, 4); // Byte-Modus
  push(bytes.length, 8); // Zeichenzahl (8 Bit bis Version 9)
  for (const b of bytes) push(b, 8);
  push(0, Math.min(4, dataLen * 8 - bits.length)); // Terminator
  while (bits.length % 8 !== 0) bits.push(0);
  const data = new Uint8Array(dataLen);
  for (let i = 0; i < bits.length; i++) data[i >> 3] |= bits[i] << (7 - (i & 7));
  for (let i = bits.length / 8, pad = 0xec; i < dataLen; i++, pad ^= 0xfd) data[i] = pad;
  const ec = reedSolomon(data, EC_CODEWORDS[version - 1]);
  const out = new Uint8Array(dataLen + ec.length);
  out.set(data);
  out.set(ec, dataLen);
  return out;
}

// ---------------------------------------------------------------------------
// Matrix: Funktionsmuster, Datenplatzierung, Maske, Format-Information
// ---------------------------------------------------------------------------

class Grid {
  readonly size: number;
  readonly modules: QrMatrix;
  readonly reserved: boolean[][];

  constructor(size: number) {
    this.size = size;
    this.modules = Array.from({ length: size }, () => new Array<boolean>(size).fill(false));
    this.reserved = Array.from({ length: size }, () => new Array<boolean>(size).fill(false));
  }

  set(x: number, y: number, dark: boolean): void {
    this.modules[y][x] = dark;
    this.reserved[y][x] = true;
  }

  finder(cx: number, cy: number): void {
    for (let dy = -4; dy <= 4; dy++) {
      for (let dx = -4; dx <= 4; dx++) {
        const x = cx + dx;
        const y = cy + dy;
        if (x < 0 || y < 0 || x >= this.size || y >= this.size) continue;
        const d = Math.max(Math.abs(dx), Math.abs(dy));
        this.set(x, y, d !== 2 && d !== 4);
      }
    }
  }

  alignment(cx: number, cy: number): void {
    for (let dy = -2; dy <= 2; dy++) {
      for (let dx = -2; dx <= 2; dx++) {
        this.set(cx + dx, cy + dy, Math.max(Math.abs(dx), Math.abs(dy)) !== 1);
      }
    }
  }

  drawFunctionPatterns(version: number): void {
    const s = this.size;
    for (let i = 0; i < s; i++) {
      this.set(6, i, i % 2 === 0);
      this.set(i, 6, i % 2 === 0);
    }
    this.finder(3, 3);
    this.finder(s - 4, 3);
    this.finder(3, s - 4);
    if (version >= 2) this.alignment(s - 7, s - 7);
    this.drawFormatBits(0); // reserviert die Format-Felder
  }

  // 15 Bit BCH-kodierte Format-Information (EC-Stufe + Maske), zwei Kopien.
  drawFormatBits(mask: number): void {
    const data = (FORMAT_BITS_L << 3) | mask;
    let rem = data;
    for (let i = 0; i < 10; i++) rem = (rem << 1) ^ ((rem >>> 9) * 0x537);
    const bits = ((data << 10) | rem) ^ 0x5412;
    const bit = (i: number) => ((bits >>> i) & 1) === 1;
    const s = this.size;
    for (let i = 0; i <= 5; i++) this.set(8, i, bit(i));
    this.set(8, 7, bit(6));
    this.set(8, 8, bit(7));
    this.set(7, 8, bit(8));
    for (let i = 9; i < 15; i++) this.set(14 - i, 8, bit(i));
    for (let i = 0; i < 8; i++) this.set(s - 1 - i, 8, bit(i));
    for (let i = 8; i < 15; i++) this.set(8, s - 15 + i, bit(i));
    this.set(8, s - 8, true); // stets dunkles Modul
  }

  // Codewörter im Zickzack von rechts unten einsortieren (Spalte 6 überspringen).
  placeData(codewords: Uint8Array): void {
    const s = this.size;
    let i = 0;
    const total = codewords.length * 8;
    for (let right = s - 1; right >= 1; right -= 2) {
      if (right === 6) right = 5;
      for (let vert = 0; vert < s; vert++) {
        for (let j = 0; j < 2; j++) {
          const x = right - j;
          const upward = ((right + 1) & 2) === 0;
          const y = upward ? s - 1 - vert : vert;
          if (!this.reserved[y][x] && i < total) {
            this.modules[y][x] = ((codewords[i >> 3] >>> (7 - (i & 7))) & 1) === 1;
            i++;
          }
        }
      }
    }
  }

  applyMask(mask: number): void {
    for (let y = 0; y < this.size; y++) {
      for (let x = 0; x < this.size; x++) {
        if (!this.reserved[y][x] && maskBit(mask, x, y)) this.modules[y][x] = !this.modules[y][x];
      }
    }
  }
}

function maskBit(mask: number, x: number, y: number): boolean {
  switch (mask) {
    case 0: return (x + y) % 2 === 0;
    case 1: return y % 2 === 0;
    case 2: return x % 3 === 0;
    case 3: return (x + y) % 3 === 0;
    case 4: return (Math.floor(x / 3) + Math.floor(y / 2)) % 2 === 0;
    case 5: return ((x * y) % 2) + ((x * y) % 3) === 0;
    case 6: return (((x * y) % 2) + ((x * y) % 3)) % 2 === 0;
    default: return (((x + y) % 2) + ((x * y) % 3)) % 2 === 0;
  }
}

// Bewertung nach den vier Regeln der Norm; kleinere Werte sind besser.
export function penalty(m: QrMatrix): number {
  const s = m.length;
  let score = 0;
  const column = (x: number) => m.map((row) => row[x]);
  for (let i = 0; i < s; i++) {
    for (const line of [m[i], column(i)]) {
      let run = 1;
      for (let k = 1; k <= s; k++) {
        if (k < s && line[k] === line[k - 1]) {
          run++;
        } else {
          if (run >= 5) score += run - 2;
          run = 1;
        }
      }
      const text = line.map((d) => (d ? "1" : "0")).join("");
      for (let k = 0; k + 7 <= s; k++) {
        if (text.slice(k, k + 7) !== "1011101") continue;
        if (k >= 4 && text.slice(k - 4, k) === "0000") score += 40;
        else if (k + 11 <= s && text.slice(k + 7, k + 11) === "0000") score += 40;
      }
    }
  }
  for (let y = 0; y + 1 < s; y++) {
    for (let x = 0; x + 1 < s; x++) {
      const c = m[y][x];
      if (c === m[y][x + 1] && c === m[y + 1][x] && c === m[y + 1][x + 1]) score += 3;
    }
  }
  let dark = 0;
  for (const row of m) for (const d of row) if (d) dark++;
  const total = s * s;
  score += (Math.ceil(Math.abs(dark * 20 - total * 10) / total) - 1) * 10;
  return score;
}

// Erzeugt die QR-Matrix für einen Text (UTF-8, bis 106 Byte).
export function encodeQr(text: string): QrMatrix {
  const bytes = new TextEncoder().encode(text);
  const version = chooseVersion(bytes.length);
  const grid = new Grid(17 + 4 * version);
  grid.drawFunctionPatterns(version);
  grid.placeData(buildCodewords(bytes, version));
  let best = 0;
  let bestScore = Infinity;
  for (let mask = 0; mask < 8; mask++) {
    grid.drawFormatBits(mask);
    grid.applyMask(mask);
    const score = penalty(grid.modules);
    grid.applyMask(mask);
    if (score < bestScore) {
      bestScore = score;
      best = mask;
    }
  }
  grid.drawFormatBits(best);
  grid.applyMask(best);
  return grid.modules;
}
