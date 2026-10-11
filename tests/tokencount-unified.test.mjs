// One strict token-count rule, shared by every reader (audit M2/M3).
//
// scan.mjs, readers.mjs and scanners.mjs each guarded malformed numbers their
// own way, so " 9 " counted in one reader and vanished in another. The rule
// now lives once, in src/tokens.mjs: a count is a non-negative safe integer,
// or a string of digits naming one.
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { tokenCount as shared, tokenOr0 } from "../src/tokens.mjs";
import { tokenCount as readersCount, readCopilotChat } from "../src/readers.mjs";
import { creditUsage } from "../src/scan.mjs";
import { scanProvider } from "../src/scanners.mjs";

test("readers.mjs uses the shared rule, not a copy of it", () => {
  assert.equal(readersCount, shared, "two copies of the rule will drift — there must be one");
});

test("the shared rule: digits count, notation does not", () => {
  for (const [v, want] of [
    ["500", 500], ["9", 9], [7, 7],
    [" 9 ", null], ["1e3", null], ["0x10", null], ["+5", null],
    [1.5, null], [-5, null], [1e308, null], [true, null], ["", null],
  ]) {
    assert.equal(shared(v), want, `tokenCount(${JSON.stringify(v)})`);
    assert.equal(tokenOr0(v), want ?? 0, `tokenOr0(${JSON.stringify(v)})`);
  }
});

test("creditUsage applies the shared rule", () => {
  // Clean digit strings still coerce (hardening + accounts pin this); padded
  // and exponent strings — which Number() used to take — are refused.
  assert.equal(creditUsage(new Map(), "a", { input_tokens: "500" }).in, 500);
  assert.equal(creditUsage(new Map(), "b", { input_tokens: " 9 " }).in, 0);
  assert.equal(creditUsage(new Map(), "c", { input_tokens: "1e3" }).in, 0);
  assert.equal(creditUsage(new Map(), "d", { input_tokens: 1e308 }).in, 0);
  assert.equal(creditUsage(new Map(), "e", { input_tokens: -5 }).in, 0);
});

test("scanners.mjs applies the shared rule", () => {
  // Gemini tokens arrive as strings when the writer serialised them that way.
  // "500" used to vanish here while creditUsage counted it; "1e3" is refused
  // in both now.
  const home = mkdtempSync(join(tmpdir(), "tc-gemini-"));
  const chats = join(home, ".gemini", "tmp", "h", "chats");
  mkdirSync(chats, { recursive: true });
  writeFileSync(join(chats, "s1.json"), JSON.stringify({
    sessionId: "g1",
    projectHash: "h",
    messages: [{
      timestamp: "2026-01-01T00:00:00Z",
      model: "gemini-2.5-pro",
      tokens: { input: "500", cached: 0, output: "1e3" },
    }],
  }));
  const { providers } = scanProvider("gemini", [home]);
  assert.equal(providers.gemini.input, 500);
  assert.equal(providers.gemini.output, 0);
});

test("copilot-chat takes the max turns across duplicate session files", () => {
  // One session opened in two workspaces: tokens were maxed while turns were
  // summed, inflating exactly the count the dedup was written to hold.
  const home = mkdtempSync(join(tmpdir(), "tc-copilot-"));
  const file = (ws, rounds, tid, tokens) => {
    const dir = join(home, ".config", "Code", "User", "workspaceStorage", ws, "chatSessions");
    mkdirSync(dir, { recursive: true });
    writeFileSync(join(dir, "s.json"), JSON.stringify({
      sessionId: "same-session",
      creationDate: 1700000000000,
      lastMessageDate: 1700000001000,
      requesterUsername: "u",
      requests: rounds.map((i) => ({
        timestamp: 1700000000000 + i,
        result: { metadata: { toolCallRounds: [{ thinking: { id: tid, tokens } }] } },
      })),
    }));
  };
  file("ws1", [1], "t1", 100);       // 1 turn, 100 tokens
  file("ws2", [1, 2, 3], "t2", 50);  // 3 turns, 50 tokens
  const r = readCopilotChat(home);
  assert.equal(r.sessions.length, 1);
  assert.equal(r.sessions[0].tokens.output, 100, "max output across copies");
  assert.equal(r.sessions[0].turns, 3, "max turns across copies, not their sum");
});
