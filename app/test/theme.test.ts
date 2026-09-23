import assert from "node:assert/strict";
import { test } from "node:test";
import { nextTheme, parseTheme, themeAttr } from "../src/theme.ts";

test("parseTheme: unbekannte Werte gelten als Auto", () => {
  assert.equal(parseTheme("hell"), "hell");
  assert.equal(parseTheme("dunkel"), "dunkel");
  assert.equal(parseTheme(null), "auto");
  assert.equal(parseTheme("dark"), "auto");
});

test("nextTheme: Auto → Hell → Dunkel → Auto", () => {
  assert.equal(nextTheme("auto"), "hell");
  assert.equal(nextTheme("hell"), "dunkel");
  assert.equal(nextTheme("dunkel"), "auto");
});

test("themeAttr: nur feste Wahl setzt data-theme", () => {
  assert.equal(themeAttr("auto"), null);
  assert.equal(themeAttr("hell"), "light");
  assert.equal(themeAttr("dunkel"), "dark");
});
