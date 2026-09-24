// Korrektur am iPad: Ersetzen nur an einem Zahn (Zuzahlung wandert mit), Ergänzen aus dem Katalog,
// Neu berechnen ohne Doppelzählung, und was Streifen und Büro als Änderung zeigen.
import assert from "node:assert/strict";
import { test } from "node:test";
import type { Suggestion, SuggestionKind } from "../src/api.ts";
import { byCode, codesOf, filterCatalog, mainPositions, type CatalogEntry } from "../src/catalog.ts";
import { addPosition, keepAdopted, recompute, remapDeselected, replaceFamily } from "../src/correction.ts";
import { buildGroups, copyLines, optionKey } from "../src/result.ts";
import { codeChanges, describe, excerpt, wordDiff } from "../src/textdiff.ts";

const FILL = ["13a", "13b", "13c", "13d"];
const COMPOSITE = ["2060", "2080", "2100", "2120"];
const INLAY = ["2150", "2160", "2170", "2170"];

function entry(code: string, system: string, kind: SuggestionKind, family: string[] = [], evident: string | null = null): CatalogEntry {
  return { code, system, title: `Titel ${code}`, area: family.length ? "Konservierend" : "Prophylaxe", points: null, kind, evident, family };
}

const ENTRIES: CatalogEntry[] = [
  ...FILL.map((c) => entry(c, "BEMA", "bema", FILL)),
  ...COMPOSITE.map((c) => entry(c, "GOZ", "zuzahlung", COMPOSITE)),
  ...["2150", "2160", "2170"].map((c) => entry(c, "GOZ", "zuzahlung", INLAY)),
  entry("25", "BEMA", "bema"),
  entry("12", "BEMA", "bema", [], "bmf"),
  entry("107", "BEMA", "bema"),
];
const CATALOG = byCode(ENTRIES);
const none = new Set<string>();

function s(code: string, teeth: number[], extra: Partial<Suggestion> = {}): Suggestion {
  const e = CATALOG.get(code)!;
  return {
    code, system: e.system, title: e.title, kind: e.kind, count: 1, points: null, teeth, reason: "wegen: diktiert",
    decide: [], alternative: false, evident: e.evident ?? null, ...extra,
  };
}

// Kassenpatient: 13b an 36 (mit Option 2080) und 13b an 46.
const TWO_TEETH: Suggestion[] = [
  s("13b", [36], { decide: ["Flächen „mod“ an 36 diktiert, Ziffer nach 2 Flächen gewählt – prüfen"] }),
  s("2080", [36], { alternative: true, kind: "zuzahlung", reason: "Zuzahlung möglich zu BEMA 13b: Mehrkosten – wegen: x" }),
  s("12", [36]),
  s("13b", [46]),
];

function lines(list: Suggestion[], adopted: ReadonlySet<string> = none, deselected: string[] = []): string[] {
  return copyLines(list, codesOf(list).filter((c) => !deselected.includes(c)), adopted);
}

test("Ersetzen wirkt nur an diesem Zahn, die Zuzahlungs-Option wandert mit", () => {
  const adopted = [optionKey(TWO_TEETH[1])];
  const out = replaceFamily(TWO_TEETH, adopted, 36, "13b", CATALOG.get("13c")!, CATALOG);
  assert.deepEqual(out.suggestions.map((x) => `${x.code}@${x.teeth.join("+")}`), ["13c@36", "2100@36", "12@36", "13b@46"]);
  assert.deepEqual(out.adopted, ["2100@36"]);
  const [main, option] = out.suggestions;
  assert.equal(main.source, "geaendert");
  assert.equal(main.replaced, "13b");
  assert.deepEqual(main.decide, []); // Flächenzahl ist damit entschieden
  assert.match(option.reason, /^Zuzahlung möglich zu BEMA 13c:/);
  assert.deepEqual(lines(out.suggestions, new Set(out.adopted)), ["36,13c,bmf", "46,13b", "", "36,2100"]);
  assert.deepEqual(lines(TWO_TEETH), ["36,13b,bmf", "46,13b"]); // ohne Korrektur unverändert
});

test("Mehrkosten-Rahmen bleibt beim Ersetzen verbunden", () => {
  const frame = [
    s("13a", [46], { reason: "Kassenanteil: Basis der Zuzahlung GOZ 2060 – wegen: x" }),
    s("2060", [46], { kind: "zuzahlung", reason: "Zuzahlung zu BEMA 13a: Mehrkosten – wegen: x" }),
  ];
  const out = replaceFamily(frame, [], 46, "13a", CATALOG.get("13b")!, CATALOG).suggestions;
  assert.deepEqual(out.map((x) => x.code), ["13b", "2080"]);
  const groups = buildGroups(out, codesOf(out), none, lines(out));
  const item = groups[0].items[0];
  assert.ok("frame" in item && item.frame.basis?.s.code === "13b" && item.frame.copay.s.code === "2080");
  assert.deepEqual(lines(out), ["46,13b", "", "46,2080"]);
});

test("Inlay 2170 (drei oder vier Flächen): die BEMA-Basis wandert nicht auf Verdacht", () => {
  const inlay = [s("13b", [16]), s("2160", [16], { kind: "zuzahlung" })];
  const out = replaceFamily(inlay, [], 16, "2160", CATALOG.get("2170")!, CATALOG).suggestions;
  assert.deepEqual(out.map((x) => x.code), ["13b", "2170"]);
});

test("Ergänzte Position erscheint in der Evident-Zeile, erneutes Antippen zählt 2×", () => {
  let list = addPosition(TWO_TEETH, CATALOG.get("107")!, null);
  assert.equal(list.at(-1)?.source, "hand");
  assert.deepEqual(lines(list), ["36,13b,bmf", "46,13b", ",107"]);
  list = addPosition(list, CATALOG.get("12")!, 36);
  assert.deepEqual(lines(list), ["36,13b,bmf*2", "46,13b", ",107"]);
  list = addPosition(list, CATALOG.get("12")!, 36);
  assert.deepEqual(lines(list), ["36,13b,bmf*3", "46,13b", ",107"]);
  assert.equal(list.filter((x) => x.source === "hand" && x.code === "12").length, 1);
  const groups = buildGroups(list, codesOf(list), none, lines(list));
  const row = groups[0].items.find((i) => "row" in i && i.row.s.code === "12");
  assert.ok(row && "row" in row && row.row.count === 3 && row.row.source === "geaendert");
});

test("Neu berechnen: Hand-Position zählt neben gleichem Regel-Vorschlag nicht doppelt", () => {
  const edited = addPosition(TWO_TEETH, CATALOG.get("107")!, null);
  const fresh = [...TWO_TEETH, s("107", [])]; // „Zahnsteinentfernung“ berichtigt: der Extraktor findet 107 selbst
  const out = recompute(edited, fresh, CATALOG);
  assert.deepEqual(lines(out), ["36,13b,bmf", "46,13b", ",107"]);
});

test("Neu berechnen: Ersetzung gilt wieder, wo die ersetzte Ziffer wiederkommt, sonst entfällt sie sichtbar", () => {
  const replaced = replaceFamily(TWO_TEETH, [], 36, "13b", CATALOG.get("13c")!, CATALOG).suggestions;
  assert.deepEqual(lines(recompute(replaced, TWO_TEETH, CATALOG)), ["36,13c,bmf", "46,13b"]);
  const vierflaechig = [s("13d", [36]), s("12", [36]), s("13b", [46])];
  const out = recompute(replaced, vierflaechig, CATALOG);
  assert.deepEqual(lines(out), ["36,13d,bmf", "46,13b"]); // nie 13c und 13d an einem Zahn
  const changes = codeChanges(mainPositions(replaced), mainPositions(out), CATALOG);
  assert.equal(describe(changes, "neu"), "13c → 13d an Zahn 36");
});

test("Abwahlen bleiben je Ziffer, auch bei anderer Anzahl; verschwundene Ziffern fallen heraus", () => {
  assert.deepEqual(remapDeselected(["13b", "25"], ["2x 13b", "12"]), ["2x 13b"]);
  assert.deepEqual(keepAdopted(["2080@36", "9999@1"], TWO_TEETH), ["2080@36"]);
});

test("Zeile „von Hand“ wird immer kopiert; die Abwahl derselben Ziffer an anderen Zähnen bleibt", () => {
  const list = addPosition(TWO_TEETH, CATALOG.get("12")!, 46);
  const deselected = remapDeselected(["12"], codesOf(list));
  assert.deepEqual(lines(list, none, deselected), ["36,13b", "46,13b,bmf"]);
  const active = codesOf(list).filter((c) => !deselected.includes(c));
  const rows = buildGroups(list, active, none, lines(list, none, deselected)).flatMap((g) =>
    g.items.flatMap((i) => ("row" in i ? [i.row] : [])),
  );
  const at = (tooth: number) => rows.find((r) => r.s.code === "12" && r.s.teeth[0] === tooth);
  assert.equal(at(36)?.selected, false);
  assert.equal(at(46)?.selected, true);
  assert.equal(at(46)?.source, "hand");
  // Am Zahn mit Regel-Vorschlag derselben Ziffer zählt die Hand-Position mit und folgt der Abwahl.
  const more = addPosition(TWO_TEETH, CATALOG.get("12")!, 36);
  assert.deepEqual(lines(more, none, remapDeselected(["12"], codesOf(more))), ["36,13b", "46,13b"]);
});

test("Streifen und Büro nennen die Ziffernänderungen je Zahn", () => {
  const before = mainPositions(TWO_TEETH);
  const after = mainPositions(addPosition(replaceFamily(TWO_TEETH, [], 36, "13b", CATALOG.get("13c")!, CATALOG).suggestions, CATALOG.get("107")!, null));
  const changes = codeChanges(before, after, CATALOG);
  assert.equal(describe(changes, "neu"), "13b → 13c an Zahn 36 · neu 107 (ohne Zahn)");
  assert.equal(describe(changes, "ergänzt"), "13b → 13c an Zahn 36 · 107 ergänzt");
  assert.equal(describe(codeChanges(before, mainPositions(TWO_TEETH.slice(0, 3)), CATALOG), "ergänzt"), "13b entfällt an Zahn 46");
});

test("Wortvergleich fürs Original: nur die geänderten Stellen mit Umfeld", () => {
  const a = "Zahn 36 Kompositfüllung in Adhäsivtechnik, zweiflächig, Kofferdam gelegt. Zahn 46 okklusal Karies. Zahn steinentfernung. Zahn 16 planen.";
  const b = a.replace("zweiflächig", "dreiflächig").replace("Zahn steinentfernung", "Zahnsteinentfernung");
  const parts = excerpt(wordDiff(a, b));
  assert.deepEqual(parts, [
    { kind: "same", text: "… Kompositfüllung in Adhäsivtechnik," },
    { kind: "del", text: "zweiflächig," },
    { kind: "ins", text: "dreiflächig," },
    { kind: "same", text: "Kofferdam gelegt. Zahn 46 okklusal Karies." },
    { kind: "del", text: "Zahn steinentfernung." },
    { kind: "ins", text: "Zahnsteinentfernung." },
    { kind: "same", text: "Zahn 16 planen." },
  ]);
  assert.deepEqual(wordDiff("gleich bleibt", "gleich bleibt"), [{ kind: "same", text: "gleich bleibt" }]);
  const long = (w: string) => Array.from({ length: 2100 }, (_, i) => `${w}${i}`).join(" ");
  assert.deepEqual(wordDiff(`A ${long("x")} Z`, `A ${long("y")} Z`).map((p) => p.kind), ["same", "del", "ins", "same"]);
});

test("Katalog-Suche: Ziffer, Kurzform oder Wort, dazu der Fachbereich", () => {
  assert.deepEqual(filterCatalog(ENTRIES, "107", null).map((e) => e.code), ["107"]);
  assert.deepEqual(filterCatalog(ENTRIES, "BMF", null).map((e) => e.code), ["12"]);
  assert.deepEqual(filterCatalog(ENTRIES, "", "Prophylaxe").map((e) => e.code), ["25", "12", "107"]);
  assert.equal(filterCatalog(ENTRIES, "titel 2080", "Konservierend").length, 1);
});
