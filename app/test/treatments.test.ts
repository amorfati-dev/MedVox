// Kopieren je Behandlung: je Zahn (zuletzt ohne Zahn) die Zeilen dieses Zahns aus dem Gesamttext,
// Kassen- und Privatzeile getrennt – Zeichen für Zeichen wie im Gesamt-Kopiertext.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { evidentBlocks, evidentLines, evidentText, type Suggestion, type TranscribeResult } from "../src/api.ts";
import { treatmentLabel, treatments } from "../src/treatments.ts";

function sug(code: string, teeth: number[], extra: Partial<Suggestion> = {}): Suggestion {
  const system = /^\d{4}$/.test(code) ? "GOZ" : "BEMA";
  return { code, system, title: "", kind: "bema", count: 1, teeth, reason: "", decide: [], alternative: false, ...extra };
}

// Diktat des Behandlers, Kassenpatient, wie der Extraktor es heute liefert: „Zahn zwei fünf, Füllung
// zweiflächig, Kunststoff mit BMF. Zahn vier sechs Wurzelkanalbehandlung begonnen mit
// Infiltrationsanästhesie, Rö2, WK mal drei, VitE mal drei, med phys und Längenbestimmungen …“.
const twoTeeth = [
  sug("13b", [25]),
  sug("2080", [25], { kind: "zuzahlung", alternative: true }),
  sug("12", [25], { evident: "bmf" }),
  sug("32", [46]),
  sug("40", [46]),
  sug("Ä925a", [46]),
  sug("28", [46]),
  sug("34", [46]),
  sug("2400", [46], { kind: "zuzahlung" }),
];
const active = ["13b", "12", "32", "40", "Ä925a", "28", "34", "2400"];

test("Zwei Behandlungen: 25 und 46 einzeln, an 46 Kasse und Privat getrennt", () => {
  const whole = evidentLines(twoTeeth, active);
  assert.equal(evidentText(whole), "25,13b,bmf\n46,32,40,Ä925a,28,34\n\n46,2400");
  const list = treatments(evidentBlocks(twoTeeth, active));
  assert.deepEqual(list, [
    { tooth: "25", kasse: ["25,13b,bmf"], privat: [] },
    { tooth: "46", kasse: ["46,32,40,Ä925a,28,34"], privat: ["46,2400"] },
  ]);
  assert.equal(evidentText(list[0].kasse), "25,13b,bmf");
  assert.equal(evidentText(list[1].kasse), "46,32,40,Ä925a,28,34");
  assert.equal(evidentText(list[1].privat), "46,2400");
});

test("Positionen ohne Zahn: eigene Behandlung zuletzt, kopiert ohne führendes Komma", () => {
  const suggestions = [sug("01", []), sug("13c", [14]), sug("1040", [], { kind: "zuzahlung", count: 20 }), sug("44", [46])];
  const list = treatments(evidentBlocks(suggestions, ["01", "13c", "20x 1040", "44"]));
  assert.deepEqual(
    list.map((t) => t.tooth),
    ["14", "46", null],
  );
  assert.equal(evidentText(list[2].kasse), "01");
  assert.equal(evidentText(list[2].privat), "1040*20");
});

test("Beschriftung: Zahn oder ohne Zahn, beim Kassenpatienten mit Kasse/Privat", () => {
  assert.equal(treatmentLabel("25", null), "Zahn 25 kopieren");
  assert.equal(treatmentLabel("46", "kasse"), "Zahn 46 Kasse kopieren");
  assert.equal(treatmentLabel("46", "privat"), "Zahn 46 Privat kopieren");
  assert.equal(treatmentLabel(null, "kasse"), "Ohne Zahn Kasse kopieren");
});

// Alle Anhang-B-Diktate, jede Auswahl, Kurzformen und „Nur Ziffern“: jede Behandlung kopiert genau Zeilen
// des Gesamttexts im selben Block, und zusammen ergeben die Behandlungen alle Zeilen – keine fehlt, keine doppelt.
const fixtures = JSON.parse(readFileSync(new URL("./fixtures/anhang-b.json", import.meta.url), "utf8")) as Record<
  string,
  TranscribeResult
>;

test("Anhang B: Behandlungen zerlegen den Gesamttext vollständig und zeichengleich", () => {
  for (const [name, result] of Object.entries(fixtures)) {
    const choices = [result.codes, ...result.codes.map((c) => result.codes.filter((x) => x !== c))];
    for (const chosen of choices) {
      for (const shortForms of [true, false]) {
        const blocks = evidentBlocks(result.suggestions, chosen, shortForms);
        const list = treatments(blocks);
        for (const block of ["kasse", "privat"] as const) {
          const own = list.flatMap((t) => t[block]);
          assert.deepEqual([...own].sort(), [...blocks[block]].sort(), `${name} ${block}`);
          for (const t of list) for (const line of t[block]) assert.equal(line.split(",")[0], t.tooth ?? "", name);
        }
        assert.equal(new Set(list.map((t) => t.tooth)).size, list.length, name);
      }
    }
  }
});
