// Evident setzt nach einer Privatposition alles Folgende auf privat (Praxisbefund: „l1,13b,2080,pan1,bmf“
// machte pan1 und bmf privat). Beim Kassenpatienten kommen deshalb alle Kassenzeilen zuerst, dann eine
// Leerzeile, dann alle Privatpositionen – je Zahn eine Zeile, in beiden Blöcken in Diktatreihenfolge.
import assert from "node:assert/strict";
import { test } from "node:test";
import { evidentBlocks, evidentLines, evidentText, joinBlocks, splitBlocks, type Suggestion } from "../src/api.ts";

function sug(code: string, teeth: number[], extra: Partial<Suggestion> = {}): Suggestion {
  const system = /^\d{4}$/.test(code) ? "GOZ" : "BEMA";
  return { code, system, title: "", kind: "bema", count: 1, teeth, reason: "", decide: [], alternative: false, ...extra };
}

// Das Beispiel des Behandlers: Kassenpatient, an 36 l1, 13b, Zuzahlung 2080, pan1, bmf.
const example = [
  sug("41a", [36], { evident: "l1" }),
  sug("13b", [36]),
  sug("2080", [36], { kind: "zuzahlung" }),
  sug("Ä935a", [36], { evident: "pan1" }),
  sug("12", [36], { evident: "bmf" }),
];
const active = ["41a", "13b", "2080", "Ä935a", "12"];

test("Kassenpatient: 2080 steht zuletzt, alle Kassenpositionen davor", () => {
  assert.deepEqual(evidentLines(example, active), ["36,l1,13b,pan1,bmf", "", "36,2080"]);
  assert.equal(evidentText(evidentLines(example, active)), "36,l1,13b,pan1,bmf\n\n36,2080");
  assert.equal(evidentText(evidentLines(example, active, false)), "36,41a,13b,Ä935a,12\n\n36,2080");
});

test("Kassen- und Privatleistungen einzeln kopiert ergeben zusammen den Gesamttext ohne Leerzeile", () => {
  const blocks = evidentBlocks(example, active);
  assert.equal(evidentText(blocks.kasse), "36,l1,13b,pan1,bmf");
  assert.equal(evidentText(blocks.privat), "36,2080");
  const combined = evidentLines(example, active);
  assert.deepEqual([...blocks.kasse, ...blocks.privat], combined.filter((l) => l !== ""));
  assert.deepEqual(joinBlocks(blocks), combined);
});

test("Privatblock über alle Zähne hinweg zuletzt, Zeilen je Block in Diktatreihenfolge, ohne Zahn je Block zuletzt", () => {
  const suggestions = [
    sug("01", []),
    sug("13c", [14]),
    sug("2100", [14], { kind: "zuzahlung" }),
    sug("1040", [], { kind: "zuzahlung", count: 20 }),
    sug("44", [46]),
    sug("2400", [46], { kind: "zuzahlung" }),
  ];
  const lines = evidentLines(suggestions, ["01", "13c", "2100", "20x 1040", "44", "2400"]);
  assert.deepEqual(lines, ["14,13c", "46,44", ",01", "", "14,2100", "46,2400", ",1040*20"]);
  assert.equal(evidentText(lines), "14,13c\n46,44\n01\n\n14,2100\n46,2400\n1040*20");
});

test("Nur ein Block: keine Leerzeile; Privatpatient unverändert", () => {
  assert.deepEqual(evidentLines(example, ["41a", "13b"]), ["36,l1,13b"]);
  assert.deepEqual(evidentLines(example, ["2080"]), ["36,2080"]);
  const privat = [sug("0100", [36], { kind: "goz", evident: "l1" }), sug("2080", [36], { kind: "goz" }), sug("2040", [36], { kind: "goz" })];
  assert.deepEqual(evidentLines(privat, ["0100", "2080", "2040"]), ["36,l1,2080,2040"]);
});

test("BEMA 12 kopiert als Evident-Kurzform bmf, „Nur Ziffern“ als 12", () => {
  const bmf = [sug("13c", [36]), sug("12", [36, 37], { evident: "bmf" })];
  assert.deepEqual(evidentLines(bmf, ["13c", "12"]), ["36,13c,bmf"]);
  assert.deepEqual(evidentLines(bmf, ["13c", "12"], false), ["36,13c,12"]);
});

test("splitBlocks: Umkehrung für die Rezeption, ohne Leerzeile ein Block", () => {
  assert.deepEqual(splitBlocks(evidentLines(example, active)), { kasse: ["36,l1,13b,pan1,bmf"], privat: ["36,2080"] });
  assert.deepEqual(splitBlocks(["36,l1"]), { kasse: ["36,l1"], privat: [] });
  assert.deepEqual(splitBlocks(["36,2080"], true), { kasse: [], privat: ["36,2080"] });
});
