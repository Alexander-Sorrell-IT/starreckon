// Tests for the muse-code reader (Muse, muse.dev CLI) in src/scanners.mjs.
// Synthetic fixtures in os.tmpdir(); no dependence on machine data.
import test from "node:test";
import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { scanProvider } from "../src/scanners.mjs";

function mkHome() {
  return mkdtempSync(join(tmpdir(), "starreckon-musecode-"));
}

function put(path, content) {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, content);
}

const J = (o) => JSON.stringify(o);

function urow(over = {}) {
  return {
    schema_version: 1, id: "rec-1",
    stream: { kind: "session", id: "sess-1" },
    sequence: 49, recorded_at: 1791663964913639, // microseconds
    record_type: "event", durability: "durable",
    payload_type: "runtime.session",
    payload: {
      event: {
        kind: "goal_usage_attribution",
        record: {
          usage_id: "usage-1", usage_family: "muse",
          quantity: {
            input_tokens: 1000, output_tokens: 100,
            reasoning_tokens: 50, cached_tokens: 200,
            main_llm_steps: 1, reported: true, unit: "tokens",
          },
        },
      },
    },
    ...over,
  };
}

function machinery(over = {}) {
  return {
    schema_version: 1, id: "rec-0", recorded_at: 1791663900000000,
    record_type: "event", payload_type: "runtime.session.permission_format_declared",
    payload: { format: "profile_v1" },
    ...over,
  };
}

test("muse-code: counts usage rows, ignores machinery, dedupes usage_id", () => {
  const home = mkHome();
  const base = join(home, ".local", "share", "muse", "sessions", "2026", "10", "10", "sess-1");
  put(join(base, "session.jsonl"),
    J(machinery()) + "\n" + J(urow()) + "\n" + J(urow()) + "\n"); // dup id
  const { providers, perSession } = scanProvider("muse-code", [home]);
  const row = providers["muse-code"];
  assert.equal(row.sessions, 1);
  assert.equal(row.turns ?? perSession[0].turns, 1); // dup usage_id dropped
  assert.equal(row.input, 1000); // exclusive of cache (Anthropic convention)
  assert.equal(row.cacheRead, 200);
  assert.equal(row.output, 150); // output + reasoning
  assert.equal(row.state, "counted");
  assert.equal(perSession[0].provider, "muse-code");
});

test("muse-code: groups by session dir, timestamps from microseconds", () => {
  const home = mkHome();
  for (const sid of ["sess-1", "sess-2"]) {
    const base = join(home, ".local", "share", "muse", "sessions", "2026", "10", "10", sid);
    put(join(base, "session.jsonl"), J(urow({
      id: `rec-${sid}`, payload: { event: { kind: "goal_usage_attribution",
        record: { usage_id: `usage-${sid}`, quantity: {
          input_tokens: 10, output_tokens: 5, reasoning_tokens: 0,
          cached_tokens: 0, main_llm_steps: 1, reported: true, unit: "tokens",
        } } } },
    })) + "\n");
  }
  const { providers, perSession } = scanProvider("muse-code", [home]);
  assert.equal(providers["muse-code"].sessions, 2);
  assert.equal(perSession.length, 2);
  assert.equal(perSession[0].month, "2026-10"); // microsecond ts normalizes
});

test("muse-code: zero-usage rows and bad lines skipped, empty home is zero rows", () => {
  const home = mkHome();
  const base = join(home, ".local", "share", "muse", "sessions", "2026", "10", "10", "sess-9");
  put(join(base, "session.jsonl"),
    "not json\n" + J(urow({ payload: { event: { kind: "goal_usage_attribution",
      record: { usage_id: "usage-0", quantity: {
        input_tokens: 0, output_tokens: 0, reasoning_tokens: 0,
        cached_tokens: 0, main_llm_steps: 1, reported: true, unit: "tokens",
      } } } } })) + "\n");
  const r = scanProvider("muse-code", [home]);
  assert.equal(r.perSession.length, 0);
  const empty = scanProvider("muse-code", [mkHome()]);
  assert.equal(empty.perSession.length, 0);
});

// ---- disabled_sources wiring (both scan paths) ------------------------------

import { scanAllProviders, scanPortedReaders } from "../src/scanners.mjs";

test("disabled registry source renders disabled zeros without opening files", () => {
  const home = mkHome();
  const base = join(home, ".local", "share", "muse", "sessions", "2026", "10", "10", "sess-1");
  put(join(base, "session.jsonl"), J(urow()) + "\n");
  const on = scanAllProviders([home]);
  assert.equal(on.providers["muse-code"].sessions, 1);
  const off = scanAllProviders([home], { disabled: ["muse-code"] });
  const row = off.providers["muse-code"];
  assert.equal(row.state, "disabled");
  assert.equal(row.sessions, 0);
  assert.equal(row.input, 0);
  assert.equal(off.perSession.length, 0);
  assert.equal(row.installed, true); // presence probes, content untouched
});

test("disabled ported source skipped, others unaffected", async () => {
  const home = mkHome();
  const r = await scanPortedReaders([home], {
    knownClaudeIds: new Set(), disabled: ["bob", "history"],
  });
  assert.equal(r.providers.bob.state, "disabled");
  assert.equal(r.providers.history.state, "disabled");
  assert.equal(r.providers.history.counts_tokens, false);
  assert.notEqual(r.providers.aider.state, "disabled");
});
