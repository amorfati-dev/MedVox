import assert from "node:assert/strict";
import { test } from "node:test";
import { routeFromPath } from "../src/router.ts";

test("routeFromPath ordnet die vier Ansichten zu", () => {
  assert.equal(routeFromPath("/"), "diktat");
  assert.equal(routeFromPath("/transfer"), "rezeption");
  assert.equal(routeFromPath("/transfer/"), "diktat");
  assert.equal(routeFromPath("/check"), "check");
  assert.equal(routeFromPath("/patienten"), "patienten");
  assert.equal(routeFromPath("/irgendwas"), "diktat");
});
