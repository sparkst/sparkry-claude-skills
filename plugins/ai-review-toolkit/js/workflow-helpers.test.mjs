import { test } from "node:test";
import assert from "node:assert/strict";
import { ensureUniqueIds } from "./workflow-helpers.mjs";

test("leaves already-unique ids untouched", () => {
  const out = ensureUniqueIds([{ id: "P0-001" }, { id: "P1-002" }]);
  assert.deepStrictEqual(out.map((f) => f.id), ["P0-001", "P1-002"]);
});

test("suffixes colliding ids deterministically, preserving order", () => {
  // Two reviewers both emitted P0-001 and P0-002 for different findings.
  const out = ensureUniqueIds([
    { id: "P0-001", title: "divide" },
    { id: "P0-001", title: "sqli" },
    { id: "P0-002", title: "sqli-2" },
    { id: "P0-002", title: "divide-2" },
  ]);
  assert.deepStrictEqual(out.map((f) => f.id), [
    "P0-001",
    "P0-001-2",
    "P0-002",
    "P0-002-2",
  ]);
});

test("third collision gets -3; does not mutate the input objects", () => {
  const input = [{ id: "X" }, { id: "X" }, { id: "X" }];
  const out = ensureUniqueIds(input);
  assert.deepStrictEqual(out.map((f) => f.id), ["X", "X-2", "X-3"]);
  assert.strictEqual(input[1].id, "X", "input must not be mutated");
});

test("all four unique ids are now distinct — the fix-ALL gate can cover them", () => {
  const out = ensureUniqueIds([
    { id: "P0-001" }, { id: "P0-001" }, { id: "P0-002" }, { id: "P0-002" },
  ]);
  assert.strictEqual(new Set(out.map((f) => f.id)).size, 4);
});
