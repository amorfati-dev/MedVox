// Zahnschema: Wurzelzahl aus der FDI-Nummer (14/24 fragen), Antippen setzt die Zähne einer Je-Zahn-Position
// (4050/4055) ohne Doppelzählung, Neu berechnen behält die angetippten Zähne, Sammelblock, Befund kopieren.
import assert from "node:assert/strict";
import { test } from "node:test";
import type { Suggestion, SuggestionKind } from "../src/api.ts";
import { byCode, codesOf, type CatalogEntry } from "../src/catalog.ts";
import { recompute, withoutTapped } from "../src/correction.ts";
import { chartMarks, findingRows, findingText, shownFindings } from "../src/findings.ts";
import { buildGroups, copyLines } from "../src/result.ts";
import {
  answerRoot,
  applyTap,
  chartRows,
  codeAt,
  collectTapped,
  mergeTeeth,
  openTeeth,
  rootOf,
  tapCounts,
  tapStart,
  tapTarget,
  toggleTooth,
  toothRanges,
  type TapState,
} from "../src/teeth.ts";

function entry(code: string, title: string, kind: SuggestionKind, extra: Partial<CatalogEntry> = {}): CatalogEntry {
  return { code, system: kind === "bema" ? "BEMA" : "GOZ", title, area: "Prophylaxe", points: null, kind, family: [], ...extra };
}

const ZST = ["4050", "4055"];
const CATALOG = byCode([
  entry("4050", "Zahnsteinentfernung, einwurzeliger Zahn", "goz", { per_tooth: true, roots: ZST }),
  entry("4055", "Zahnsteinentfernung, mehrwurzeliger Zahn", "goz", { per_tooth: true, roots: ZST }),
  entry("2000", "Fissurenversiegelung, je Zahn", "goz", { per_tooth: true, roots: [] }),
  entry("2100", "Kompositfüllung adhäsiv, dreiflächig", "goz"),
  entry("107", "Entfernung harter Zahnbeläge (Zahnstein)", "bema"),
]);

function s(code: string, teeth: number[], extra: Partial<Suggestion> = {}): Suggestion {
  const e = CATALOG.get(code)!;
  return { code, system: e.system, title: e.title, kind: e.kind, count: 1, points: null, teeth, reason: "wegen: diktiert", decide: [], alternative: false, ...extra };
}

// PSI beim Privatpatienten: „Zahnstein entfernt. Zahn 36 mod Karies profunda, Füllung dreiflächig.“
const PSI: Suggestion[] = [
  s("4050", [], { decide: ["Zahn nicht diktiert – 4050/4055 je Zahn wählen"] }),
  s("2100", [36]),
];

function tapped(teeth: number[], answered: Record<number, string> = {}): TapState {
  return teeth.reduce((st, t) => toggleTooth(st, t), { teeth: [], answered } as TapState);
}

test("Wurzelzahl: Front und Prämolaren ein-, Molaren mehrwurzelig, obere 4er fragen", () => {
  assert.deepEqual([11, 13, 15, 25, 34, 44, 45].map(rootOf), Array(7).fill("single"));
  assert.deepEqual([16, 17, 18, 26, 36, 47, 48].map(rootOf), Array(7).fill("multi"));
  assert.deepEqual([14, 24].map(rootOf), ["ask", "ask"]);
  assert.deepEqual([53, 54, 84].map(rootOf), ["single", "multi", "multi"]);
});

test("Schema: ein Kiefer, je Hälfte 8 Zähne von der Mitte aus; Milchzähne nur wenn gezeigt", () => {
  assert.deepEqual(chartRows("ok").map((r) => r.teeth), [
    [11, 12, 13, 14, 15, 16, 17, 18],
    [21, 22, 23, 24, 25, 26, 27, 28],
  ]);
  assert.deepEqual(chartRows("uk").map((r) => r.quadrant), [4, 3]);
  assert.deepEqual(chartRows("uk", [36, 84]).map((r) => r.quadrant), [4, 3, 8]);
  assert.equal(toothRanges([13, 11, 12, 15, 21, 22]), "11–13, 15, 21, 22");
});

test("Antippen: Ziffer nach Wurzelzahl, 14 bleibt offen bis zur Angabe", () => {
  let st = tapped([11, 16, 14]);
  assert.equal(codeAt(11, ZST, st.answered), "4050");
  assert.equal(codeAt(16, ZST, st.answered), "4055");
  assert.deepEqual(openTeeth(st, ZST), [14]);
  assert.throws(() => applyTap(PSI, ZST, st, CATALOG));
  st = answerRoot(st, 14, "4055");
  assert.deepEqual(openTeeth(st, ZST), []);
  assert.deepEqual(tapCounts(st, ZST), [{ code: "4050", count: 1 }, { code: "4055", count: 2 }]);
  assert.deepEqual(toggleTooth(st, 14), { teeth: [11, 16], answered: {} }); // herausnehmen vergisst die Angabe
  assert.equal(codeAt(14, ["2000"], {}), "2000"); // eine Ziffer: nie fragen
});

test("Übernehmen: je angetippter Zahn einmal, die Zeile ohne Zahn entfällt, Evident je Zahn eine Zeile", () => {
  const next = applyTap(PSI, ZST, answerRoot(tapped([11, 12, 14, 16, 36]), 14, "4050"), CATALOG);
  assert.deepEqual(codesOf(next), ["3x 4050", "2x 4055", "2100"]);
  assert.ok(next.every((x) => x.teeth.length === 1 && x.decide.length === 0));
  assert.ok(next.filter((x) => x.code !== "2100").every((x) => x.tapped && x.source === "hand" && x.count === 1));
  assert.deepEqual(copyLines(next, codesOf(next), new Set()), ["11,4050", "12,4050", "14,4050", "16,4055", "36,4055,2100"]);
});

test("Wieder öffnen: bisherige Zähne sind angetippt; an 14 gilt nur eine angetippte Angabe, nie die des Extraktors", () => {
  const dictated = [s("4055", [14]), s("4055", [16]), s("2100", [36])];
  assert.deepEqual(tapStart(dictated, ZST), { teeth: [14, 16], answered: {} });
  const after = applyTap(dictated, ZST, answerRoot(tapStart(dictated, ZST), 14, "4050"), CATALOG);
  assert.deepEqual(tapStart(after, ZST), { teeth: [14, 16], answered: { 14: "4050" } });
});

test("Zähne herausnehmen wirkt nur für diese Position", () => {
  const dictated = [s("4055", [16]), s("4055", [17]), s("2000", [16])];
  const next = applyTap(dictated, ZST, tapped([17]), CATALOG);
  assert.deepEqual(next.map((x) => `${x.code}@${x.teeth.join()}`), ["4055@17", "2000@16"]);
});

test("Nur Je-Zahn-Positionen bekommen „Zähne antippen“", () => {
  assert.deepEqual(tapTarget("4055", CATALOG), ZST);
  assert.deepEqual(tapTarget("2000", CATALOG), ["2000"]);
  assert.equal(tapTarget("2100", CATALOG), null);
  assert.equal(tapTarget("107", CATALOG), null);
});

test("Neu berechnen: angetippte Zähne bleiben, die Regel-Zeile ohne Zahn kommt nicht zurück", () => {
  const edited = applyTap(PSI, ZST, tapped([11, 16]), CATALOG);
  const fresh = [s("4050", [], { decide: ["Zahn nicht diktiert – 4050/4055 je Zahn wählen"] }), s("2100", [36])];
  const next = recompute(edited, fresh, CATALOG);
  assert.deepEqual(codesOf(next), ["2100", "4050", "4055"]);
  assert.ok(!next.some((x) => x.teeth.length === 0));
});

test("Neuer Abschnitt: die Position mit angetippten Zähnen kommt nicht noch einmal dazu", () => {
  const edited = applyTap(PSI, ZST, tapped([11, 16]), CATALOG);
  const section = [s("4050", [], { decide: ["Zahn nicht diktiert – 4050/4055 je Zahn wählen"] }), s("4055", [26]), s("2000", [17])];
  const next = [...edited, ...withoutTapped(edited, section, CATALOG)];
  assert.deepEqual(copyLines(next, codesOf(next), new Set()), ["11,4050", "16,4055", "36,2100", "17,2000"]);
  assert.deepEqual(withoutTapped(PSI, section, CATALOG), section); // ohne Antippen bleibt alles
});

test("Position entfernen: alle Zähne herausnehmen nimmt die angetippte Position ganz heraus", () => {
  const edited = applyTap(PSI, ZST, tapped([11, 16]), CATALOG);
  const next = applyTap(edited, ZST, toggleTooth(toggleTooth(tapStart(edited, ZST), 11), 16), CATALOG);
  assert.deepEqual(copyLines(next, codesOf(next), new Set()), ["36,2100"]);
});

test("Sammelblock: angetippte Zeilen je Leistung, Zahnblöcke behalten ihre volle Evident-Zeile", () => {
  const next = applyTap(PSI, ZST, tapped([11, 12, 16, 36]), CATALOG);
  const codes = codesOf(next);
  const lines = copyLines(next, codes, new Set());
  const { groups, collected } = collectTapped(buildGroups(next, codes, new Set(), lines));
  assert.deepEqual(groups.map((g) => [g.tooth, g.lines]), [[36, ["36,4055,2100"]]]);
  assert.equal(collected.length, 1);
  assert.equal(collected[0].label, "Zahnsteinentfernung");
  assert.equal(collected[0].teeth, 4);
  assert.deepEqual(collected[0].rows.map((r) => [r.row.s.code, r.teeth]), [["4050", [11, 12]], ["4055", [16, 36]]]);
});

test("Befund kopieren: eine Zeile je Zahn in FDI-Reihenfolge, ohne Zahn zuletzt", () => {
  const next = applyTap(PSI, ZST, tapped([11, 36]), CATALOG);
  const teeth = [{ tooth: 36, surfaces: "mod", findings: ["Karies profunda"] }, { tooth: null, surfaces: "", findings: ["Gingivitis"] }];
  const rows = findingRows(next, [s("2000", [17])], codesOf(next), new Set(), teeth);
  assert.equal(
    findingText(rows),
    [
      "11: Zahnsteinentfernung, einwurzeliger Zahn (4050)",
      "17: geplant – Fissurenversiegelung, je Zahn (2000)",
      "36 mod: Karies profunda – Zahnsteinentfernung, mehrwurzeliger Zahn (4055), Kompositfüllung adhäsiv, dreiflächig (2100)",
      "ohne Zahn: Gingivitis",
    ].join("\n"),
  );
  const shown = shownFindings(rows);
  assert.deepEqual(shown.rows.map((r) => [r.tooth, r.done.map((d) => d.code)]), [[17, []], [36, ["2100"]], [null, []]]);
  assert.deepEqual(shown.tapped, [{ label: "Zahnsteinentfernung", parts: [{ code: "4050", kind: "goz", teeth: "11" }, { code: "4055", kind: "goz", teeth: "36" }] }]);
});

test("Markierung: wer zahlt, geplant gestrichelt, Prüfhinweis, Befund ohne Leistung neutral", () => {
  const list = [s("2100", [36], { decide: ["prüfen"] }), s("107", [])];
  const kasse = { ...s("2100", [46]), kind: "bema" as const };
  const rows = findingRows([...list, kasse], [s("2000", [17])], ["2100", "107"], new Set(), [{ tooth: 21, surfaces: "", findings: ["Fraktur"] }]);
  const marks = chartMarks(rows);
  assert.deepEqual(marks.get(36), { tone: "privat", check: true, label: "2100" });
  assert.deepEqual(marks.get(46), { tone: "kasse", check: false, label: "2100" });
  assert.deepEqual(marks.get(17), { tone: "plan", check: false, label: "geplant" });
  assert.deepEqual(marks.get(21), { tone: "find", check: false, label: "" });
  assert.equal(marks.has(0), false);
});

test("Abgewählte Ziffern stehen weder im Befund noch im Schema", () => {
  const rows = findingRows([s("2100", [36]), s("107", [])], [], ["107"], new Set(), []);
  assert.deepEqual(rows.map((r) => r.tooth), [null]);
});

test("Mehrere Abschnitte: je Zahn einmal, Flächen und Befunde zusammengeführt", () => {
  const merged = mergeTeeth(
    [{ tooth: 36, surfaces: "o", findings: ["Karies"] }, { tooth: null, surfaces: "", findings: ["Gingivitis"] }],
    [{ tooth: 36, surfaces: "mo", findings: ["Karies", "Pulpitis"] }, { tooth: 16, surfaces: "", findings: [] }],
  );
  assert.deepEqual(merged, [
    { tooth: 36, surfaces: "om", findings: ["Karies", "Pulpitis"] },
    { tooth: 16, surfaces: "", findings: [] },
    { tooth: null, surfaces: "", findings: ["Gingivitis"] },
  ]);
});
