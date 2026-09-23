import assert from "node:assert/strict";
import { test } from "node:test";
import { api, codeOf, evidentLines, evidentOf, evidentText, isToothless, kindsOf, normalizeCode, parsePatientType, type Suggestion } from "../src/api.ts";

test("normalizeCode: Großschreibung, nur erlaubtes Alphabet, 6 Zeichen", () => {
  assert.equal(normalizeCode("abc234"), "ABC234");
  assert.equal(normalizeCode(" a-b c 2 3 4 5 "), "ABC234");
  assert.equal(normalizeCode("0O1Iab"), "AB");
  assert.equal(normalizeCode("ABCDEFGH"), "ABCDEF");
});

// Vorschlag wie vom Server; `teeth` leer = ohne Zahn.
function sug(code: string, teeth: number[], extra: Partial<Suggestion> = {}): Suggestion {
  const system = /^\d{4}$/.test(code) ? "GOZ" : "BEMA";
  return { code, system, title: "", kind: "bema", count: 1, teeth, reason: "", decide: [], alternative: false, ...extra };
}

test("evidentLines: Zahn vorn, dann seine Positionen in Vorschlagsreihenfolge", () => {
  const lines = evidentLines([sug("Ä925a", [36]), sug("41a", [36]), sug("13a", [36])], ["Ä925a", "41a", "13a"]);
  assert.deepEqual(lines, ["36,Ä925a,41a,13a"]);
  assert.equal(evidentText(lines), "36,Ä925a,41a,13a");
});

test("evidentLines: zwei Zähne in Diktatreihenfolge, Sitzungspositionen als letzte Zeile ohne Zahn", () => {
  const suggestions = [
    sug("01", []),
    sug("Ä925a", [36]),
    sug("41a", [36]),
    sug("13b", [36]),
    sug("2080", [36], { kind: "zuzahlung", alternative: true }),
    sug("44", [46]),
    sug("107", []),
  ];
  const active = ["01", "Ä925a", "41a", "13b", "44", "107"];
  const lines = evidentLines(suggestions, active);
  assert.deepEqual(lines.map(isToothless), [false, false, true]);
  assert.equal(evidentText(lines), "36,Ä925a,41a,13b\n46,44\n01,107");
});

test("evidentLines: abgewählte Chips fehlen, leere Zeilen entfallen", () => {
  const suggestions = [sug("01", []), sug("41a", [36]), sug("13a", [36]), sug("44", [46])];
  assert.deepEqual(evidentLines(suggestions, ["41a", "13a"]), ["36,41a,13a"]);
  assert.deepEqual(evidentLines(suggestions, []), []);
  assert.equal(evidentText([]), "");
});

test("evidentLines: Anzahl je Zahn als Ziffer*Anzahl, OP-Zuschlag bleibt am Zahn des Servers", () => {
  const suggestions = [
    sug("2410", [11], { count: 3 }),
    sug("3030", [48]),
    sug("0090", [48]),
    sug("0090", [36]),
    sug("0500", [48]),
  ];
  assert.equal(
    evidentText(evidentLines(suggestions, ["3x 2410", "3030", "2x 0090", "0500"])),
    "11,2410*3\n48,3030,0090,0500\n36,0090",
  );
});

test("evidentLines: dieselbe Ziffer am selben Zahn aus zwei Abschnitten zählt einmal", () => {
  const suggestions = [sug("01", []), sug("13a", [36]), sug("01", []), sug("13a", [36]), sug("8", [21])];
  assert.deepEqual(evidentLines(suggestions, ["01", "13a", "8"]), ["36,13a", "21,8", ",01"]);
});

test("evidentLines: Zeile ohne Zahn erkennbar, auch wenn die Ziffer wie ein Zahn aussieht", () => {
  const lines = evidentLines([sug("12", []), sug("13a", [12])], ["12", "13a"]);
  assert.deepEqual(lines.map(isToothless), [false, true]);
  assert.equal(evidentText(lines), "12,13a\n12");
});

test("evidentLines: Wurzelfüllung an drei Kanälen als Evident-Kurzform mit Anzahl", () => {
  const suggestions = [sug("35", [36], { count: 3, evident: "wf" })];
  assert.deepEqual(evidentLines(suggestions, ["3x 35"]), ["36,wf*3"]);
  assert.deepEqual(evidentLines(suggestions, ["3x 35"], false), ["36,35*3"]);
});

test("evidentLines: gemischte Zeile – Kurzform wo bekannt, sonst Ziffer; „Nur Ziffern“ nur Ziffern", () => {
  const suggestions = [
    sug("Ä925a", [36]),
    sug("41a", [36], { evident: "l1" }),
    sug("32", [36], { count: 2 }),
    sug("35", [36], { count: 2, evident: "wf" }),
    sug("13a", [36]),
    sug("47a", [48], { evident: "ost1" }),
    sug("Ä935d", [], { evident: "opg" }),
  ];
  const active = ["Ä925a", "41a", "2x 32", "2x 35", "13a", "47a", "Ä935d"];
  assert.equal(evidentText(evidentLines(suggestions, active)), "36,Ä925a,l1,32*2,wf*2,13a\n48,ost1\nopg");
  assert.equal(evidentText(evidentLines(suggestions, active, false)), "36,Ä925a,41a,32*2,35*2,13a\n48,47a\nÄ935d");
  assert.deepEqual(evidentLines(suggestions, ["Ä925a", "13a"]), ["36,Ä925a,13a"]);
});

test("evidentOf: Kurzformen der Hauptvorschläge für die Chips", () => {
  const forms = evidentOf([
    sug("41a", [36], { evident: "l1" }),
    sug("13a", [36]),
    sug("3030", [48], { evident: "ost1", alternative: true }),
  ]);
  assert.deepEqual(forms, { "41a": "l1" });
});

test("codeOf: Anzahl aus dem Kopierformat entfernen", () => {
  assert.equal(codeOf("2x 41a"), "41a");
  assert.equal(codeOf("28x 1040"), "1040");
  assert.equal(codeOf("Ä925a"), "Ä925a");
});

test("kindsOf: nur Hauptvorschläge bestimmen die Art einer Ziffer", () => {
  const base = { system: "GOZ", title: "", count: 1, teeth: [], reason: "", decide: [] };
  const kinds = kindsOf([
    { ...base, code: "13c", system: "BEMA", kind: "bema", alternative: false },
    { ...base, code: "2100", kind: "zuzahlung", alternative: true },
    { ...base, code: "2060", kind: "zuzahlung", alternative: false },
  ]);
  assert.deepEqual(kinds, { "13c": "bema", "2060": "zuzahlung" });
});

test("parsePatientType: unbekannte Werte gelten als Kasse", () => {
  assert.equal(parsePatientType("privat"), "privat");
  assert.equal(parsePatientType("kasse"), "kasse");
  assert.equal(parsePatientType(null), "kasse");
  assert.equal(parsePatientType("PRIVAT"), "kasse");
});

test("createTransfer: nennt das gespeicherte Diktat, ohne ID wie bisher", async (t) => {
  const bodies: unknown[] = [];
  t.mock.method(globalThis, "fetch", async (_url: string, init: RequestInit) => {
    bodies.push(JSON.parse(String(init.body)));
    return new Response(JSON.stringify({ code: "ABCDEF", expires_at: "" }), { status: 200 });
  });
  await api.createTransfer("Zahn 36", ["36,13c"], undefined, "diktat-0001");
  await api.createTransfer("Zahn 36", ["36,13c"], undefined, null);
  assert.deepEqual(bodies, [
    { transcript: "Zahn 36", codes: ["36,13c"], dictation_id: "diktat-0001" },
    { transcript: "Zahn 36", codes: ["36,13c"] },
  ]);
});
