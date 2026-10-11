// Tests for the qwen and muse (Cline) readers in src/scanners.mjs — synthetic
// fixtures in os.tmpdir() per provider format. No dependence on
// machine-specific data.
import test from "node:test";
import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { scanProvider } from "../src/scanners.mjs";

function mkHome() {
  return mkdtempSync(join(tmpdir(), "starreckon-qwen-muse-"));
}

function put(path, content) {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, content);
}

const J = (o) => JSON.stringify(o);

// ---- qwen -----------------------------------------------------------------

function qrow(over = {}) {
  return {
    schemaVersion: 1, id: "r1", timestamp: "2026-10-01T06:38:30.532Z",
    localDate: "2026-10-01", localMonth: "2026-10", sessionId: "qs1",
    model: "qwen3-max", authType: "openai", source: "main",
    inputTokens: 4095, outputTokens: 6, cachedTokens: 1000,
    thoughtsTokens: 10, totalTokens: 5111, apiDurationMs: 130238,
    ...over,
  };
}

test("qwen: groups by sessionId across files, cached subset, thoughts to output, total ignored", () => {
  const home = mkHome();
  const usage = join(home, ".qwen", "usage");
  put(join(usage, "token-usage-2026-10.jsonl"), J(qrow()) + "\n");
  put(
    join(usage, "token-usage-2026-11.jsonl"),
    J(qrow({
      id: "r2", timestamp: "2026-11-02T00:00:00Z",
      inputTokens: 100, outputTokens: 5, cachedTokens: 100,
      thoughtsTokens: 0, totalTokens: 205,
    })) + "\n"
  );
  const { providers, perSession } = scanProvider("qwen", [home]);
  const row = providers.qwen;
  assert.equal(row.sessions, 1); // one session across two monthly files
  assert.equal(row.input, (4095 - 1000) + (100 - 100)); // cached is a SUBSET
  assert.equal(row.cacheRead, 1000 + 100);
  assert.equal(row.output, (6 + 10) + 5); // thoughts billed as output
  assert.ok(!J(row).includes("5111") && !J(perSession).includes("5111"),
    "totalTokens restates input+output and must be ignored");
  const s = perSession[0];
  assert.equal(s.turns, 2);
  assert.equal(s.model, "qwen3-max");
  assert.equal(s.vendor, "qwen");
  assert.equal(s.month, "2026-10");
  assert.equal(row.state, "counted");
  assert.equal(row.installed, true);
});

test("qwen: dedupes rows on id, skips zero/sessionless/malformed rows", () => {
  const home = mkHome();
  const usage = join(home, ".qwen", "usage");
  const dup = J(qrow()) + "\n";
  put(join(usage, "token-usage-2026-10.jsonl"), dup + dup); // same id twice
  put(
    join(usage, "token-usage-2026-11.jsonl"),
    [
      J(qrow({ id: "zero", sessionId: "qzero", inputTokens: 0, outputTokens: 0, cachedTokens: 0, thoughtsTokens: 0, totalTokens: 0 })),
      J(qrow({ id: "nosid", sessionId: "", inputTokens: 50, outputTokens: 50 })), // unattributable
      "{not json",
      "",
    ].join("\n")
  );
  const { providers, perSession } = scanProvider("qwen", [home]);
  const row = providers.qwen;
  assert.equal(row.sessions, 1); // zero-only session is not a session
  assert.equal(row.input, 4095 - 1000); // the dup row counted once
  assert.equal(row.output, 6 + 10);
  assert.equal(perSession[0].turns, 1);
  assert.equal(perSession[0].session_id, "qs1");
});

test("qwen: rollup, transcripts and tmp logs are never read alongside", () => {
  const home = mkHome();
  const usage = join(home, ".qwen", "usage");
  put(join(usage, "token-usage-2026-10.jsonl"), J(qrow()) + "\n");
  // The per-session rollup RESTATING the same call — reading it too is a 2x.
  put(join(home, ".qwen", "usage_record.jsonl"), J({
    version: 1, sessionId: "qs1", timestamp: 1790837346793,
    models: { "qwen3-max": { requests: 1, inputTokens: 4095, outputTokens: 6 } },
  }) + "\n");
  // A transcript SUBSET with per-message usageMetadata.
  put(join(home, ".qwen", "projects", "-home-me", "chats", "qs1.jsonl"), J({
    sessionId: "qs1", timestamp: "2026-10-01T06:38:30.532Z", type: "model",
    message: { role: "model", parts: [{ text: "hi" }] },
    usageMetadata: { promptTokenCount: 4095, candidatesTokenCount: 6 },
  }) + "\n");
  // tmp/ holds logs, not usage.
  put(join(home, ".qwen", "tmp", "logs.json"), J({ lines: [] }));
  const { providers } = scanProvider("qwen", [home]);
  assert.equal(providers.qwen.input, 4095 - 1000);
  assert.equal(providers.qwen.output, 6 + 10);
  assert.equal(providers.qwen.sessions, 1);
});

test("qwen: absent store says absent, not zero", () => {
  const { providers } = scanProvider("qwen", [mkHome()]);
  assert.equal(providers.qwen.sessions, 0);
  assert.equal(providers.qwen.state, "absent");
  assert.equal(providers.qwen.installed, false);
});

// ---- muse (cline) ---------------------------------------------------------

function museTask(home, channel, taskId) {
  return join(home, ".config", channel, "User", "globalStorage",
    "saoudrizwan.claude-dev", "tasks", taskId);
}

test("muse: same per-request shape as kilo — cache subtracted, placeholder skipped, model tag", () => {
  const home = mkHome();
  const tdir = museTask(home, "Code", "task-1");
  put(
    join(tdir, "ui_messages.json"),
    J([
      { ts: 1738368000000, say: "text", text: "hi" },
      {
        ts: 1738368060000,
        say: "api_req_started",
        text: J({ tokensIn: 1000, tokensOut: 50, cacheReads: 600, cacheWrites: 200 }),
      },
      { ts: 1738368120000, say: "api_req_started", text: J({ tokensIn: 0, tokensOut: 0 }) },
    ])
  );
  put(join(tdir, "api_conversation_history.json"), "stuff <model>anthropic/claude-sonnet-4-5</model> more");
  const { providers, perSession } = scanProvider("muse", [home]);
  const row = providers.muse;
  assert.equal(row.sessions, 1);
  assert.equal(row.input, 1000 - 600 - 200);
  assert.equal(row.cacheRead, 600);
  assert.equal(row.cacheWrite, 200);
  assert.equal(row.output, 50);
  const s = perSession[0];
  assert.equal(s.turns, 1);
  assert.equal(s.model, "claude-sonnet-4-5");
  assert.equal(s.vendor, "anthropic");
  assert.equal(s.month, "2025-02");
  assert.ok(s.account.includes("Code"));
  assert.equal(row.state, "counted");
  assert.equal(row.installed, true);
});

test("muse: same task id in two channels stays two sessions", () => {
  const home = mkHome();
  for (const ch of ["Code", "VSCodium"]) {
    const tdir = museTask(home, ch, "task-dup");
    put(
      join(tdir, "ui_messages.json"),
      J([{ ts: 1738368060000, say: "api_req_started", text: J({ tokensIn: 100, tokensOut: 10 }) }])
    );
  }
  const { providers } = scanProvider("muse", [home]);
  assert.equal(providers.muse.sessions, 2);
  assert.equal(providers.muse.input, 200);
});

test("muse: taskHistory rollup and non-request records are ignored", () => {
  const home = mkHome();
  const tdir = museTask(home, "Code", "task-1");
  put(
    join(tdir, "ui_messages.json"),
    J([
      { ts: 1738368060000, say: "api_req_started", text: J({ tokensIn: 100, tokensOut: 10 }) },
      // Newer Cline usage-bearing records: unverified restatement risk, ignored.
      { ts: 1738368070000, say: "deleted_api_reqs", text: J({ tokensIn: 5000, tokensOut: 500 }) },
      { ts: 1738368080000, say: "subagent_usage", text: J({ tokensIn: 7000, tokensOut: 700 }) },
    ])
  );
  // The per-task rollup restating the same request.
  put(join(home, ".config", "Code", "User", "globalStorage",
    "saoudrizwan.claude-dev", "state", "taskHistory.json"), J([{ id: "task-1", totalTokensIn: 99999 }]));
  const { providers } = scanProvider("muse", [home]);
  assert.equal(providers.muse.input, 100);
  assert.equal(providers.muse.output, 10);
  assert.equal(providers.muse.sessions, 1);
});

test("muse: absent store says absent, not zero", () => {
  const { providers } = scanProvider("muse", [mkHome()]);
  assert.equal(providers.muse.sessions, 0);
  assert.equal(providers.muse.state, "absent");
  assert.equal(providers.muse.installed, false);
});
