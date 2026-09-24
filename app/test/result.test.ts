// Ergebnisliste und Kopierformat mit Zuzahlungs-Optionen (E4) gegen die Anhang-B-Diktate.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import type { Suggestion, TranscribeResult } from "../src/api.ts";
import { billable, buildGroups, copyLines, countGroups, optionKey, positionsOf, type Group, type Item, type Row } from "../src/result.ts";

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

// Kurzform eines Eintrags für Vergleiche: "13c", "13c+[2100?]", "[13a|2150]", "[32+[2420?]|2400]", "[-|1040]", "?2100".
function sketch(item: Item): string {
  const opts = (o: { s: Suggestion; adopted: boolean }[]) =>
    o.length ? `+[${o.map((x) => x.s.code + (x.adopted ? "!" : "?")).join(",")}]` : "";
  const row = (r: Row) => r.s.code + opts(r.options);
  if ("row" in item) return row(item.row);
  if ("frame" in item) return `[${item.frame.basis ? row(item.frame.basis) : "-"}|${row(item.frame.copay)}]`;
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
        const row = (r: Row) => shown.push(r.key, ...r.options.map((o) => o.key));
        if ("row" in item) row(item.row);
        else if ("frame" in item) {
          if (item.frame.basis) row(item.frame.basis);
          row(item.frame.copay);
        } else shown.push(item.option.key);
      }
    }
    const expected = new Set(
      r.suggestions.map((s) => (s.alternative ? optionKey(s) : `p|${s.teeth[0] ?? "-"}|${s.code}`)),
    );
    assert.equal(shown.length, expected.size);
    assert.deepEqual(new Set(shown), expected);
    // Blockköpfe tragen genau die kopierten Zeilen (ohne Zahn: ohne führendes Komma); beim Kassenpatienten
    // kann ein Zahn eine Kassen- und eine Privatzeile haben, die Leerzeile zwischen den Blöcken fehlt.
    const lines = copyLines(r.suggestions, r.codes, none).filter((l) => l !== "");
    const heads = groups.flatMap((g) => g.lines);
    assert.deepEqual(new Set(heads), new Set(lines.map((l) => l.replace(/^,/, ""))));
    assert.equal(heads.length, lines.length);
    assert.equal(groups.findIndex((g) => g.tooth === null), groups.some((g) => g.tooth === null) ? groups.length - 1 : -1);
  });
}

test("Kasse d01: Zuzahlungs-Option GOZ 2100 unter BEMA 13c, abgewählt voreingestellt", () => {
  const [g] = groupsOf("d01-kasse");
  assert.equal(g.tooth, 36);
  assert.deepEqual(g.items.map(sketch), ["13c+[2100?]", "25", "40", "12"]);
  assert.deepEqual(g.lines, ["36,13c,25,40,bmf"]);
  const option = ("row" in g.items[0] && g.items[0].row.options[0]) || null;
  assert.ok(option && option.adoptable && !option.adopted);
});

test("Kasse d01: übernommene Option wird kopiert wie jede gewählte Position – nur nach Antippen", () => {
  const r = fixtures["d01-kasse"];
  const adopted = new Set(["2100@36"]);
  // Evident setzt nach einer Privatposition alles Folgende auf privat: die Zuzahlung steht im Privatblock zuletzt.
  assert.deepEqual(copyLines(r.suggestions, r.codes, adopted), ["36,13c,25,40,bmf", "", "36,2100"]);
  assert.deepEqual(copyLines(r.suggestions, r.codes, adopted, false), ["36,13c,25,40,12", "", "36,2100"]);
  assert.deepEqual(copyLines(r.suggestions, ["25"], adopted), ["36,25", "", "36,2100"]);
  const [g] = groupsOf("d01-kasse", r.codes, adopted);
  assert.deepEqual(g.items.map(sketch), ["13c+[2100!]", "25", "40", "12"]);
  assert.deepEqual(g.lines, ["36,13c,25,40,bmf", "36,2100"]);
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
  assert.deepEqual(groups.map((g) => g.lines), [["36,13c,25"], ["46,8,13a", "46,2150"], ["40,bmf,107"]]);
  const r = fixtures["abnahme-kasse"];
  assert.deepEqual(countGroups(groups, r.planned ?? []), { positions: 8, options: 1, check: 0, planned: 1 });
});

test("Kasse d06/d11/d04/d05: Rahmen mit BEMA-Basis aus „zu BEMA …“, eigenständige Zuzahlung ohne Kassenzeile", () => {
  assert.deepEqual(groupsOf("d06-kasse")[0].items.map(sketch), ["[13c|2100]"]);
  assert.deepEqual(groupsOf("d11-kasse").map((g) => g.items.map(sketch)), [["[13a|2060]"], ["[13a|2060]"]]);
  // Endo-Zuzahlungs-Optionen (PR #24): 2420 unter BEMA 32 im Rahmen, 2197 und 2430 unter BEMA 34.
  assert.deepEqual(groupsOf("d04-kasse")[0].items.map(sketch), ["28", "[32+[2420?]|2400]", "34+[2197?,2430?]"]);
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
  assert.deepEqual(toothless.lines, []);
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

test("positionsOf: Patient zahlt/Kasse zahlt für die Rezeption, nur gewählte und übernommene Positionen", () => {
  const r = fixtures["abnahme-kasse"];
  assert.deepEqual(positionsOf(groupsOf("abnahme-kasse", r.codes.filter((c) => c !== "12"), new Set(["2100@36"]))), [
    { tooth: 36, code: "13c", kind: "bema" },
    { tooth: 36, code: "2100", kind: "zuzahlung" },
    { tooth: 36, code: "25", kind: "bema" },
    { tooth: 46, code: "8", kind: "bema" },
    { tooth: 46, code: "13a", kind: "kassenanteil" },
    { tooth: 46, code: "2150", kind: "zuzahlung" },
    { tooth: null, code: "40", kind: "bema" },
    { tooth: null, code: "107", kind: "bema" },
  ]);
});

test("Übernommene Option bringt eine abgewählte Position mit derselben Ziffer nicht zurück (d06 + d01)", () => {
  const d06 = fixtures["d06-kasse"];
  const d01 = fixtures["d01-kasse"];
  const suggestions = [...d06.suggestions, ...d01.suggestions];
  const active = [...d06.codes, ...d01.codes].filter((c) => c !== "2100");
  const adopted = new Set(["2100@36"]);
  const lines = copyLines(suggestions, active, adopted);
  assert.deepEqual(lines, ["14,13c", "36,13c,25,40,bmf", "", "36,2100"]);
  assert.deepEqual(copyLines(suggestions, active, adopted, false), ["14,13c", "36,13c,25,40,12", "", "36,2100"]);
  const groups = buildGroups(suggestions, active, adopted, lines);
  const at14 = groups.find((g) => g.tooth === 14)!;
  const frame = at14.items[0];
  assert.ok("frame" in frame && !frame.frame.copay.selected);
  assert.deepEqual(at14.lines, ["14,13c"]);
  assert.deepEqual(
    positionsOf(groups).filter((p) => p.code === "2100"),
    [{ tooth: 36, code: "2100", kind: "zuzahlung" }],
  );
});
