// Cache belongs to the volume axis (audit M1). The star priced input+output
// while the session totals on the same run summed all four buckets — and cache
// is routinely the largest bucket — so FIRST PRINCIPLES read low against its
// own report, and the MoM trend ignored the biggest mover.
import { test } from "node:test";
import assert from "node:assert/strict";
import { computeLevels, computeLevelsRaw, explainLevels } from "../src/star.mjs";
import { velocity } from "../src/snapshots.mjs";

test("a cached token counts exactly like a worked token on FIRST PRINCIPLES", () => {
  const viaInput = computeLevels({ total_input_tokens: 50e6 })[0];
  const viaCache = computeLevels({
    total_input_tokens: 10e6,
    total_cache_read_tokens: 40e6,
  })[0];
  assert.equal(viaCache, viaInput, "10M in + 40M cache must score as 50M");
  assert.ok(viaCache > computeLevels({ total_input_tokens: 10e6 })[0],
    "cache must move the arm, not sit beside it");
});

test("cache-only work still draws an arm", () => {
  const lv = computeLevels({ total_cache_read_tokens: 10e6, total_cache_write_tokens: 5e6 });
  assert.ok(lv[0] > 0, "15M cached tokens scored a zero arm");
});

test("month snapshots price their cache_tokens too", () => {
  const noCache = computeLevels({ input_tokens: 10e6, output_tokens: 0 })[0];
  const cached = computeLevels({ input_tokens: 10e6, output_tokens: 0, cache_tokens: 40e6 })[0];
  assert.equal(cached, computeLevels({ input_tokens: 50e6 })[0]);
  assert.ok(cached > noCache);
});

test("the raw level and the explanation agree with the scored level", () => {
  const agg = { total_input_tokens: 10e6, total_cache_read_tokens: 40e6 };
  const lv = computeLevels(agg);
  const raw = computeLevelsRaw(agg);
  assert.equal(raw[0], lv[0], "below the ceiling, raw is the level");
  const term = explainLevels(agg)[0].terms[0];
  assert.equal(term.label, "tokens");
  assert.equal(term.value, 50, "the card must show the 50M the arm was scored on");
  assert.equal(term.unit, "M");
});

test("a cache-heavy month saturates and says by how much", () => {
  const agg = { total_input_tokens: 10e6, total_cache_read_tokens: 3e9 };
  const lv = computeLevels(agg);
  const raw = computeLevelsRaw(agg);
  assert.equal(lv[0], 7, "3B cached tokens must pin the arm");
  assert.ok(raw[0] > 7, `raw must read past the ceiling, got ${raw[0]}`);
  const row = explainLevels(agg)[0];
  assert.equal(row.capped, true);
  assert.equal(row.raw, raw[0]);
});

test("velocity prices cache in the token trend", () => {
  // Flat input+output, 10x cache growth: the old trend read 0%.
  const v = velocity([
    { month: "2026-01", duration_hours: 1, sessions: 1, input_tokens: 100, output_tokens: 0, cache_tokens: 0 },
    { month: "2026-02", duration_hours: 1, sessions: 1, input_tokens: 100, output_tokens: 0, cache_tokens: 900 },
  ]);
  assert.equal(v.tokens_mom_pct, 900);
});

test("velocity without cache is unchanged", () => {
  const v = velocity([
    { month: "2026-01", duration_hours: 1, sessions: 1, input_tokens: 100, output_tokens: 0, cache_tokens: 0 },
    { month: "2026-02", duration_hours: 1, sessions: 1, input_tokens: 200, output_tokens: 0, cache_tokens: 0 },
  ]);
  assert.equal(v.tokens_mom_pct, 100);
  assert.equal(velocity([]), null);
});
