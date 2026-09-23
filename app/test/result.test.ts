// Ergebnisliste und Kopierformat mit Zuzahlungs-Optionen (E4) gegen die Anhang-B-Diktate.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import type { Suggestion, TranscribeResult } from "../src/api.ts";
import { billable, buildGroups, copyLines, countGroups, optionKey, type Group, type Item } from "../src/result.ts";

type Golden = Record<string, Record<string, { evident: string[]; numbers: string[] }>>;
const fixtures = JSON.parse(readFileSync(new URL("./fixtures/anhang-b.json", import.meta.url), "utf8")) as Record<
  string,
  TranscribeResult
>;
const golden = JSON.parse(readFileSync(new URL("./fixtures/evident-golden.json", import.meta.url), "utf8")) as Golden;
const none = new Set<string>();

function groupsOf(name: string, active?: string[], adopted: ReadonlySet<string> = none): Group[] {
  const r = fixtures[name];
  const codes = active ?? r.codes;
  return buildGroups(r.suggestions, codes, adopted, copyLines(r.suggestions, codes, adopted));
}

// Kurzform eines Eintrags für Vergleiche: "13c", "13c+[2100?]", "[13a|2150]", "[-|1040]", "?2100".
function sketch(item: Item): string {
  const opts = (o: { s: Suggestion; adopted: boolean }[]) =>
    o.length ? `+[${o.map((x) => x.s.code + (x.adopted ? "!" : "?")).join(",")}]` : "";
  if ("row" in item) return item.row.s.code + opts(item.row.options);
  if ("frame" in item) return `[${item.frame.basis?.s.code ?? "-"}|${item.frame.copay.s.code}]`;
  return `?${item.option.s.code}`;
}

for (const [name, r] of Object.entries(fixtures)) {
  test(`Kopierformat über die Ergebnisliste unverändert ohne Option: ${name}`, () => {
    const selections: Array<[string, string[]]> = [
      ["alle", r.codes],
      ...r.codes.map((c): [string, string[]] => [`ohne ${c}`, r.codes.filter((x) => x !== c)]),
    ];
    for (const [label, active] of selections) {
      assert.deepEqual(copyLines(r.suggestions, active, none), golden[name][label].evident, label);
      assert.deepEqual(copyLines(r.suggestions, active, none, false), golden[name][label].numbers, label);
    }
    assert.equal(billable(r.suggestions, none), r.suggestions);
  });

  test(`Ergebnisliste zeigt jeden Vorschlag genau einmal: ${name}`, () => {
    const groups = groupsOf(name);
    const shown: string[] = [];
    for (const g of groups) {
      for (const item of g.items) {
        if ("row" in item) shown.push(item.row.key, ...item.row.options.map((o) => o.key));
        else if ("frame" in item) {
          if (item.frame.basis) shown.push(item.frame.basis.key);
          shown.push(item.frame.copay.key);
        } else shown.push(item.option.key);
      }
    }
    const expected = new Set(
      r.suggestions.map((s) => (s.alternative ? optionKey(s) : `p|${s.teeth[0] ?? "-"}|${s.code}`)),
    );
    assert.equal(shown.length, expected.size);
    assert.deepEqual(new Set(shown), expected);
    // Blockköpfe tragen genau die kopierten Zeilen (ohne Zahn: ohne führendes Komma).
    const lines = copyLines(r.suggestions, r.codes, none).map((l) => l.replace(/^,/, ""));
    assert.deepEqual(groups.map((g) => g.line).filter((l) => l !== null), lines);
    assert.equal(groups.findIndex((g) => g.tooth === null), groups.some((g) => g.tooth === null) ? groups.length - 1 : -1);
  });
}

test("Kasse d01: Zuzahlungs-Option GOZ 2100 unter BEMA 13c, abgewählt voreingestellt", () => {
  const [g] = groupsOf("d01-kasse");
  assert.equal(g.tooth, 36);
  assert.deepEqual(g.items.map(sketch), ["13c+[2100?]", "25", "40", "12"]);
  assert.equal(g.line, "36,13c,25,40,12");
  const option = ("row" in g.items[0] && g.items[0].row.options[0]) || null;
  assert.ok(option && option.adoptable && !option.adopted);
});

test("Kasse d01: übernommene Option wird kopiert wie jede gewählte Position – nur nach Antippen", () => {
  const r = fixtures["d01-kasse"];
  const adopted = new Set(["2100@36"]);
  assert.deepEqual(copyLines(r.suggestions, r.codes, adopted), ["36,13c,2100,25,40,12"]);
  assert.deepEqual(copyLines(r.suggestions, r.codes, adopted, false), ["36,13c,2100,25,40,12"]);
  assert.deepEqual(copyLines(r.suggestions, ["25"], adopted), ["36,2100,25"]);
  const [g] = groupsOf("d01-kasse", r.codes, adopted);
  assert.deepEqual(g.items.map(sketch), ["13c+[2100!]", "25", "40", "12"]);
  assert.equal(g.line, "36,13c,2100,25,40,12");
  assert.equal(countGroups([g], r.planned ?? []).positions, 5);
});

test("Nur Zuzahlungs-Optionen sind übernehmbar; Privat-Alternativen bleiben Hinweis", () => {
  const s = (code: string, kind: Suggestion["kind"], alternative: boolean): Suggestion => ({
    code, system: kind === "bema" ? "BEMA" : "GOZ", title: "", kind, count: 1, teeth: [36], reason: "", decide: [], alternative,
  });
  const suggestions = [s("13c", "bema", false), s("2100", "goz", true)];
  const adopted = new Set(["2100@36"]);
  assert.deepEqual(copyLines(suggestions, ["13c"], adopted), ["36,13c"]);
  const [g] = buildGroups(suggestions, ["13c"], adopted, ["36,13c"]);
  const option = "row" in g.items[0] ? g.items[0].row.options[0] : null;
  assert.ok(option && !option.adoptable && !option.adopted);
});

test("Abnahme-Diktat Kasse: Mehrkosten-Rahmen 13a + 2150 an 46, ohne Zahn zuletzt", () => {
  const groups = groupsOf("abnahme-kasse");
  assert.deepEqual(groups.map((g) => g.tooth), [36, 46, null]);
  assert.deepEqual(groups.map((g) => g.items.map(sketch)), [["13c+[2100?]", "25"], ["8", "[13a|2150]"], ["40", "12", "107"]]);
  const frame = groups[1].items[1];
  assert.ok("frame" in frame && frame.frame.basis?.tag === "kassenanteil" && frame.frame.copay.tag === "zuzahlung");
  assert.deepEqual(groups.map((g) => g.line), ["36,13c,25", "46,8,13a,2150", "40,12,107"]);
  const r = fixtures["abnahme-kasse"];
  assert.deepEqual(countGroups(groups, r.planned ?? []), { positions: 8, options: 1, check: 0, planned: 1 });
});

test("Kasse d06/d11/d04/d05: Rahmen mit BEMA-Basis aus „zu BEMA …“, eigenständige Zuzahlung ohne Kassenzeile", () => {
  assert.deepEqual(groupsOf("d06-kasse")[0].items.map(sketch), ["[13c|2100]"]);
  assert.deepEqual(groupsOf("d11-kasse").map((g) => g.items.map(sketch)), [["[13a|2060]"], ["[13a|2060]"]]);
  assert.deepEqual(groupsOf("d04-kasse")[0].items.map(sketch), ["28", "[32|2400]", "34"]);
  assert.deepEqual(groupsOf("d05-kasse")[0].items.map(sketch), ["[-|1040]", "IP4", "MHU"]);
});

test("Privat d01: nur GOZ, keine Rahmen, keine Optionen, Prüfhinweise gezählt", () => {
  const groups = groupsOf("d01-privat");
  assert.deepEqual(groups[0].items.map(sketch), ["2100", "2330", "0090", "2040"]);
  assert.ok(groups[0].items.every((i) => "row" in i && i.row.tag === "goz"));
  assert.equal(countGroups(groups, []).check, 2);
});

test("Abgewählte Ziffer bleibt als Zeile stehen; Block ohne Auswahl hat keine Zeile", () => {
  const r = fixtures["d02-kasse"];
  const active = r.codes.filter((c) => c !== "01" && c !== "04");
  const groups = groupsOf("d02-kasse", active);
  const toothless = groups.find((g) => g.tooth === null)!;
  assert.equal(toothless.line, null);
  assert.ok(toothless.items.every((i) => "row" in i && !i.row.selected));
});

test("Gleiche Ziffer am selben Zahn aus zwei Abschnitten steht einmal, mit der höheren Anzahl", () => {
  const r = fixtures["d01-kasse"];
  const twice = [...r.suggestions, ...r.suggestions.map((s) => (s.code === "25" ? { ...s, count: 2 } : s))];
  const [g] = buildGroups(twice, r.codes, none, copyLines(twice, r.codes, none));
  assert.deepEqual(g.items.map(sketch), ["13c+[2100?]", "25", "40", "12"]);
  const row = g.items[1];
  assert.ok("row" in row && row.row.count === 2);
});
