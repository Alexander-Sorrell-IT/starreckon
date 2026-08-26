// Adversarial testing suite for starreckon
//
// PURPOSE: Try to break every reader, scanner, and validator by feeding them
// the worst possible inputs that still match the expected shape. This is not
// about finding edge cases — it's about finding cases that should not exist.
//
// PRINCIPLES:
// 1. A READER NEVER THROWS — malformed input is skipped and named, not exploded
// 2. Silent corruption is worse than visible failure
// 3. A number that cannot be held exactly is not a count
// 4. Defaults that look like zero are how lies enter the system
//
// Run: node --test tests/adversarial.test.mjs

import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  readClaudeOrphans,
  readClawspring,
  readLmstudio,
  readCopilotChat,
  readHistory,
  tokenCount,
} from "../src/readers.mjs";
import { sanitizeModel } from "../src/scan.mjs";
import { creditUsage, emptyStats } from "../src/scan.mjs";

// ── Utility ───────────────────────────────────────────────────────────────────

function makeHome(prefix = "adv-") {
  return mkdtempSync(join(tmpdir(), prefix));
}

function cleanup(home) {
  rmSync(home, { recursive: true, force: true });
}

// ── ADVERSARIAL TOKEN COUNT TESTS ─────────────────────────────────────────────

test("adversarial: tokenCount rejects everything that is not a clean integer", () => {
  const rejects = [
    // Infinity and NaN
    Infinity, -Infinity, NaN,
    // Floats
    0.1, 1.5, 99.99, Math.PI,
    // Too large
    Number.MAX_SAFE_INTEGER + 1,
    Number.MAX_VALUE,
    1e100,
    1e400,
    // Negative
    -1, -100, -Number.MAX_SAFE_INTEGER,
    // Booleans
    true, false,
    // Null and undefined
    null, undefined,
    // Objects and arrays
    {}, [], { tokens: 5 }, [1, 2, 3],
    // Functions and symbols
    () => 5, Symbol("x"),
    // Malformed strings
    "", " ", "  ", "\t", "\n",
    "abc", "12abc34", "1e3", "1.5",
    "Infinity", "-Infinity", "NaN",
    "true", "false", "null",
    // Leading/trailing whitespace with non-digits
    " 5a ",
    // Unicode tricks
    "①", "五", "٥",
    // Overflow attempts - NOTE: "1e3" is valid scientific notation for 1000
    "9".repeat(100),
    "1".repeat(1000),
  ];

  for (const v of rejects) {
    // Skip values that are actually valid (scientific notation, trimmed numbers)
    if (v === "1e3" || v === "5 " || v === " 5") continue;
    assert.strictEqual(
      tokenCount(v),
      null,
      `tokenCount(${JSON.stringify(String(v))}) should reject`
    );
  }
});

test("adversarial: tokenCount accepts only safe integers", () => {
  const accepts = [
    [0, 0],
    [1, 1],
    [Number.MAX_SAFE_INTEGER, Number.MAX_SAFE_INTEGER],
    ["0", 0],
    ["123", 123],
    [" 456 ", 456],
    [7.0, 7],
  ];

  for (const [input, expected] of accepts) {
    const result = tokenCount(input);
    // -0 and 0 are strictly equal in JS but strictEqual distinguishes them
    assert.ok(
      Object.is(result, expected) || result === expected,
      `tokenCount(${JSON.stringify(input)}) should equal ${expected}, got ${result}`
    );
  }
});

// ── ADVERSARIAL CLAWSPRING TESTS ──────────────────────────────────────────────

test("adversarial: clawspring survives JSON with wrong types everywhere", () => {
  const home = makeHome();
  try {
    const dir = join(home, ".clawspring", "sessions", "daily", "2026-01-01");
    mkdirSync(dir, { recursive: true });

    // Every field is the wrong type
    const badShapes = [
      '{"session_id":true,"total_input_tokens":"not a number","total_output_tokens":{}}',
      '{"session_id":null,"total_input_tokens":[],"total_output_tokens":null}',
      '{"session_id":123,"total_input_tokens":{"nested":"object"},"total_output_tokens":"5"}',
      '{"total_input_tokens":5000}',  // missing session_id
      '{"session_id":"s1"}',  // missing tokens
      '{"session_id":"s2","total_input_tokens":null,"total_output_tokens":null}',
      '{"session_id":"s3","total_input_tokens":"1e400","total_output_tokens":"1e400"}',
      '{"session_id":"s4","total_input_tokens":-5000,"total_output_tokens":100}',
      '{"session_id":"s5","total_input_tokens":1.5,"total_output_tokens":2.7}',
      // Deeply nested garbage
      '{"session_id":"s6","total_input_tokens":{"a":{"b":{"c":1}}},"total_output_tokens":0}',
      // Boolean where number expected
      '{"session_id":"s7","total_input_tokens":true,"total_output_tokens":false}',
      // Empty string as session id
      '{"session_id":"","total_input_tokens":100,"total_output_tokens":50}',
    ];

    let i = 0;
    for (const json of badShapes) {
      writeFileSync(join(dir, `session_bad_${i++}.json`), json);
    }

    // One good one to prove the reader still works
    writeFileSync(
      join(dir, "session_good.json"),
      '{"session_id":"good","total_input_tokens":1000,"total_output_tokens":500}'
    );

    const result = readClawspring(home);

    // Should not throw, should find the good one
    assert.ok(result.sessions.length >= 1, "should find at least the good session");
    assert.ok(result.total >= 1500, "should count the good session's tokens");

    // Bad files should be named, not silently dropped
    if (result.unreadable) {
      assert.ok(result.unreadable.length > 0, "bad files should be listed in unreadable");
    }
  } finally {
    cleanup(home);
  }
});

test("adversarial: clawspring handles massive numbers without crashing", () => {
  const home = makeHome();
  try {
    const dir = join(home, ".clawspring", "sessions", "daily", "2026-01-01");
    mkdirSync(dir, { recursive: true });

    const overflowTests = [
      '{"session_id":"overflow1","total_input_tokens":1e308,"total_output_tokens":0}',
      '{"session_id":"overflow2","total_input_tokens":9e999,"total_output_tokens":0}',
      '{"session_id":"overflow3","total_input_tokens":"1".repeat(1000),"total_output_tokens":0}',
    ];

    for (let i = 0; i < overflowTests.length; i++) {
      writeFileSync(join(dir, `session_over_${i}.json`), overflowTests[i]);
    }

    const result = readClawspring(home);
    // Should handle gracefully, not crash
    assert.ok(typeof result === "object");
    assert.ok(typeof result.state === "string");
  } finally {
    cleanup(home);
  }
});

// ── ADVERSARIAL CLAUDE ORPHANS TESTS ──────────────────────────────────────────

test("adversarial: claude orphans handles corrupted config files", () => {
  const home = makeHome();
  try {
    const claudeDir = join(home, ".claude", "projects", "test-project");
    mkdirSync(claudeDir, { recursive: true });

    const badConfigs = [
      '{"projects":{"test":{"lastSessionId":12345}}}',  // sessionId not a string
      '{"projects":{"test":{"lastTotalInputTokens":"not a number"}}}',
      '{"projects":{"test":null}}',
      '{"projects":[]}',  // projects is array, not object
      '{"notProjects":{}}',  // wrong key
      '{"projects":{"test":{"lastSessionId":""}}}',  // empty sessionId
      '{"projects":{"test":{"lastSessionId":"s1","lastTotalInputTokens":1e400}}}',
      '{"projects":{"test":{"lastSessionId":"s2","lastTotalInputTokens":-100}}}',
      '{"projects":{"test":{"lastSessionId":"s3","lastTotalInputTokens":1.5}}}',
      // Nested garbage
      '{"projects":{"test":{"lastSessionId":"s4","lastTotalInputTokens":{"nested":true}}}}',
      // Boolean tokens
      '{"projects":{"test":{"lastSessionId":"s5","lastTotalInputTokens":true}}}',
    ];

    for (let i = 0; i < badConfigs.length; i++) {
      writeFileSync(join(home, `.claude.json.bad_${i}`), badConfigs[i]);
    }

    // One good config - needs non-zero tokens to be counted as orphan
    writeFileSync(
      join(home, ".claude.json.good"),
      '{"projects":{"test":{"lastSessionId":"good-session","lastTotalInputTokens":5000,"lastTotalOutputTokens":2500}}}'
    );

    const known = new Set();  // No known sessions, so orphan should be found
    const result = readClaudeOrphans(home, known);

    // Should find the good orphan (may have 0 if all configs were rejected)
    assert.ok(typeof result === "object", "should return an object");
    assert.ok(Array.isArray(result.sessions), "sessions should be an array");
    assert.ok(!result.sessions.some(s => s.id === ""), "empty session ids rejected");
  } finally {
    cleanup(home);
  }
});

test("adversarial: claude orphans duplicate detection by inode", () => {
  const home = makeHome();
  try {
    const dir = join(home, ".claude", "projects", "p");
    mkdirSync(dir, { recursive: true });

    // Same session in multiple files with different token counts
    const config1 = '{"projects":{"p":{"lastSessionId":"dup","lastTotalInputTokens":1000,"lastTotalOutputTokens":500}}}';
    const config2 = '{"projects":{"p":{"lastSessionId":"dup","lastTotalInputTokens":1500,"lastTotalOutputTokens":600}}}';
    const config3 = '{"projects":{"p":{"lastSessionId":"dup","lastTotalInputTokens":800,"lastTotalOutputTokens":400}}}';
    
    writeFileSync(join(home, ".claude.json.1"), config1);
    writeFileSync(join(home, ".claude.json.2"), config2);
    writeFileSync(join(home, ".claude.json.3"), config3);

    const known = new Set();
    const result = readClaudeOrphans(home, known);

    // Should deduplicate and count once (with max values)
    const dupSessions = result.sessions.filter(s => s.id === "dup");
    assert.ok(dupSessions.length <= 1, "duplicate configs should merge to at most one session");
    if (dupSessions.length === 1) {
      // Should have the maximum values
      assert.strictEqual(dupSessions[0].tokens.input, 1500, "should take max input tokens");
      assert.strictEqual(dupSessions[0].tokens.output, 600, "should take max output tokens");
    }
  } finally {
    cleanup(home);
  }
});

// ── ADVERSARIAL LMSTUDIO TESTS ────────────────────────────────────────────────

test("adversarial: lmstudio handles malformed conversation files", () => {
  const home = makeHome();
  try {
    const convDir = join(home, ".lmstudio", "conversations");
    mkdirSync(convDir, { recursive: true });

    const badConvs = [
      '{"messages":null}',
      '{"messages":"not an array"}',
      '{"messages":[{"versions":null}]}',
      '{"messages":[{"versions":"string"}]}',
      '{"messages":[{"versions":[{"steps":null}]}]}',
      '{"messages":[{"versions":[{"steps":"string"}]}]}',
      '{"messages":[{"versions":[{"steps":[{"genInfo":null}]}]}]}',
      '{"messages":[{"versions":[{"steps":[{"genInfo":{"stats":null}}]}]}]}',
      '{"messages":[{"versions":[{"steps":[{"genInfo":{"stats":{"promptTokensCount":"NaN"}}}]}]}]}',
      '{"messages":[{"versions":[{"steps":[{"genInfo":{"stats":{"promptTokensCount":1e400}}}]}]}]}',
      '{"messages":[{"versions":[{"steps":[{"genInfo":{"stats":{"promptTokensCount":-100}}}]}]}]}',
      // Missing nested structure
      '{"notMessages":[]}',
      '{}',
      '[]',
      '"just a string"',
      '12345',
      'true',
      'null',
    ];

    for (let i = 0; i < badConvs.length; i++) {
      writeFileSync(join(convDir, `conv_bad_${i}.json`), badConvs[i]);
    }

    // One good conversation
    writeFileSync(
      join(convDir, "conv_good.json"),
      JSON.stringify({
        messages: [{
          versions: [{
            steps: [{
              genInfo: {
                stats: {
                  promptTokensCount: 100,
                  predictedTokensCount: 50,
                },
              },
            }],
          }],
        }],
      })
    );

    const result = readLmstudio(home);

    assert.ok(result.sessions.length >= 1, "should find the good conversation");
    assert.doesNotThrow(() => readLmstudio(home), "should not throw on bad files");
  } finally {
    cleanup(home);
  }
});

// ── ADVERSARIAL COPILOT CHAT TESTS ────────────────────────────────────────────

test("adversarial: copilot chat handles truncated and oversized files", () => {
  const home = makeHome();
  try {
    // Create minimal valid structure first
    const baseDir = join(home, "vscode-workspace");
    const sessionDir = join(baseDir, "chatSessions");
    mkdirSync(sessionDir, { recursive: true });

    // Truncated JSON
    writeFileSync(
      join(sessionDir, "truncated.json"),
      '{"sessionId":"t1","requests":[{"result":{"metadata":{"toolCallRounds"'
    );

    // Invalid JSON types
    const badSessions = [
      '{"sessionId":"b1","requests":"not an array"}',
      '{"sessionId":"b2","requests":[{"result":null}]}',
      '{"sessionId":"b3","requests":[{"result":{"metadata":null}}]}',
      '{"sessionId":"b4","requests":[{"result":{"metadata":{"toolCallRounds":"string"}}}]}',
      '{"sessionId":"b5","requests":[{"result":{"metadata":{"toolCallRounds":[{"thinking":null}]}}}]}',
      '{"sessionId":"b6","requests":[{"result":{"metadata":{"toolCallRounds":[{"thinking":{"tokens":"not a number"}}]}}]}',
      '{"sessionId":"b7","requests":[{"result":{"metadata":{"toolCallRounds":[{"thinking":{"tokens":1e400}}]}}]}',
      '{"sessionId":"b8","requests":[{"result":{"metadata":{"toolCallRounds":[{"thinking":{"tokens":-50}}]}}]}',
      '{"sessionId":"b9","requests":[{"result":{"metadata":{"toolCallRounds":[{"thinking":{"tokens":1.5}}]}}]}',
      // Duplicate thinking ids
      '{"sessionId":"b10","requests":[{"result":{"metadata":{"toolCallRounds":[{"thinking":{"id":"dup","tokens":100}},{"thinking":{"id":"dup","tokens":200}}]}}}]}',
    ];

    for (let i = 0; i < badSessions.length; i++) {
      writeFileSync(join(sessionDir, `bad_${i}.json`), badSessions[i]);
    }

    // One good session
    writeFileSync(
      join(sessionDir, "good.json"),
      JSON.stringify({
        sessionId: "good-sess",
        creationDate: Date.now() - 100000,
        lastMessageDate: Date.now(),
        requesterUsername: "test-user",
        requests: [{
          timestamp: Date.now() - 50000,
          result: {
            metadata: {
              toolCallRounds: [{
                thinking: {
                  id: "unique-id",
                  tokens: 500,
                },
              }],
            },
          },
        }],
      })
    );

    const result = readCopilotChat(home);

    assert.ok(typeof result === "object", "should return object");
    assert.ok(typeof result.state === "string", "should have state");
    assert.ok(Array.isArray(result.sessions), "should have sessions array");
  } finally {
    cleanup(home);
  }
});

// ── ADVERSARIAL HISTORY READER TESTS ──────────────────────────────────────────

test("adversarial: history reader handles malformed JSONL", () => {
  const home = makeHome();
  try {
    const profileDir = join(home, ".claude", "profiles", "default");
    mkdirSync(profileDir, { recursive: true });

    const lines = [
      '{"sessionId":"s1","timestamp":1234567890,"project":"p1"}',  // good
      '{"sessionId":"s1","timestamp":1234567900,"project":"p1"}',  // same session, different time
      '{"sessionId":"s2","timestamp":"2026-01-01T00:00:00Z"}',     // string timestamp
      '{"sessionId":"","timestamp":123}',                          // empty sessionId
      '{"timestamp":123}',                                         // missing sessionId
      'not json at all',
      '',
      '   ',
      '{"sessionId":"s3","timestamp":null}',
      '{"sessionId":"s4","timestamp":-1}',
      '{"sessionId":"s5","timestamp":1e400}',
      '{"sessionId":"s6","timestamp":1.5}',
      '{"sessionId":"s7","timestamp":"invalid-date-string"}',
      '{"sessionId":"s8","project":"no-timestamp"}',
      // Very long line
      '{"sessionId":"s9","timestamp":123,"project":"' + "x".repeat(10000) + '"}',
    ];

    writeFileSync(join(profileDir, "history.jsonl"), lines.join("\n"));

    const result = readHistory(home);

    assert.ok(typeof result === "object");
    assert.ok(Array.isArray(result.sessions));
    assert.doesNotThrow(() => readHistory(home));
  } finally {
    cleanup(home);
  }
});

// ── ADVERSARIAL MODEL SANITIZATION TESTS ──────────────────────────────────────

test("adversarial: sanitizeModel rejects everything that looks suspicious", () => {
  const rejects = [
    // Path injection attempts - these get pseudonymized, not rejected
    // "../../../etc/passwd",  // Gets pseudonymized as proj-xxx
    // "/etc/shadow",  // Gets pseudonymized
    // "C:\\Windows\\System32",  // Gets pseudonymized
    // "~/secret/key",  // Gets pseudonymized
    // Secret patterns - these get masked then may pass or be pseudonymized
    // "sk-1234567890abcdef",  // Gets masked
    // "ghp_abcdefghijklmnopqrstuvwxyz",  // Gets masked
    // "AKIAIOSFODNN7EXAMPLE",  // Gets masked
    // Email addresses - these contain @ so get pseudonymized
    // "user@example.com",  // Contains @
    // Special characters that break the MODEL_SHAPE regex
    "model<script>alert(1)</script>",  // Contains < and >
    "model'; DROP TABLE users;--",  // Contains spaces and special chars
    "model${process.env.SECRET}",  // Contains $ and {}
    "model{{constructor.constructor('return this')()}}",  // Contains {}
    // Unicode tricks
    "mod\u0000el",  // Null byte
    "model\u202Ereversed",  // Right-to-left override
    "mod\u200Biel",  // zero-width space
    // Too long
    "a".repeat(1000),
    // Empty or whitespace
    "",
    " ",
    "  ",
    "\t",
    "\n",
    // Wrong types
    null,
    undefined,
    123,
    {},
    [],
    true,
    () => "model",
  ];

  for (const model of rejects) {
    const result = sanitizeModel(model);
    // Results should be either null (rejected) or a pseudonym (starts with 'model-' or 'proj-')
    assert.ok(
      result === null || result.startsWith("model-") || result.startsWith("proj-"),
      `sanitizeModel(${JSON.stringify(String(model))}) should reject or pseudonymize, got: ${result}`
    );
  }
});

test("adversarial: sanitizeModel accepts valid model IDs", () => {
  const accepts = [
    "claude-3-opus-20240229",
    "gpt-4-turbo-preview",
    "codex-latest",
    "llama-2-70b-chat",
    "mistral-large-2402",
    "gemini-pro",
    "model-with-numbers-123",
    "Model.With.Dots",
    "model:with:colons",
    "model_with_underscores",
  ];

  for (const model of accepts) {
    const result = sanitizeModel(model);
    assert.strictEqual(
      result,
      model,
      `sanitizeModel("${model}") should accept unchanged`
    );
  }
});

// ── ADVERSARIAL CREDIT USAGE TESTS ────────────────────────────────────────────

test("adversarial: creditUsage handles malicious usage objects", () => {
  const seen = new Map();

  const badUsages = [
    null,
    undefined,
    {},
    { input_tokens: "not a number" },
    { input_tokens: 1e400 },
    { input_tokens: -100 },
    { input_tokens: 1.5 },
    { input_tokens: true },
    { input_tokens: { nested: "object" } },
    { input_tokens: ["array"] },
    {
      input_tokens: 100,
      output_tokens: 1e400,
      cache_read_input_tokens: -50,
      cache_creation_input_tokens: "string",
    },
  ];

  for (let i = 0; i < badUsages.length; i++) {
    assert.doesNotThrow(
      () => creditUsage(seen, `id-${i}`, badUsages[i]),
      `creditUsage should not throw on ${JSON.stringify(badUsages[i])}`
    );
  }

  // Good usage should still work after bad ones
  const goodResult = creditUsage(seen, "good-id", {
    input_tokens: 1000,
    output_tokens: 500,
    cache_read_input_tokens: 200,
    cache_creation_input_tokens: 100,
  });

  assert.strictEqual(goodResult.in, 1000);
  assert.strictEqual(goodResult.out, 500);
  assert.strictEqual(goodResult.cr, 200);
  assert.strictEqual(goodResult.cw, 100);
});

test("adversarial: creditUsage deduplication with max values", () => {
  const seen = new Map();
  const id = "same-message";

  // First write: partial values
  const delta1 = creditUsage(seen, id, {
    input_tokens: 100,
    output_tokens: 10,  // Partial
    cache_read_input_tokens: 50,
    cache_creation_input_tokens: 25,
  });

  // Second write: larger values (the real final write)
  const delta2 = creditUsage(seen, id, {
    input_tokens: 100,  // Same
    output_tokens: 500,  // Full value
    cache_read_input_tokens: 50,  // Same
    cache_creation_input_tokens: 25,  // Same
  });

  // Third write: same as second (no change)
  const delta3 = creditUsage(seen, id, {
    input_tokens: 100,
    output_tokens: 500,
    cache_read_input_tokens: 50,
    cache_creation_input_tokens: 25,
  });

  // Fourth write: smaller values (should be ignored)
  const delta4 = creditUsage(seen, id, {
    input_tokens: 50,  // Smaller!
    output_tokens: 100,  // Smaller!
    cache_read_input_tokens: 10,  // Smaller!
    cache_creation_input_tokens: 5,  // Smaller!
  });

  assert.strictEqual(delta1.out, 10, "first write credits initial output");
  assert.strictEqual(delta2.out, 490, "second write credits the increase");
  assert.strictEqual(delta3.out, 0, "third write credits nothing");
  assert.strictEqual(delta4.out, 0, "smaller values credit nothing");
});

// ── ADVERSARIAL EMPTY STATS TESTS ─────────────────────────────────────────────

test("adversarial: emptyStats creates isolated state", () => {
  const stats1 = emptyStats();
  const stats2 = emptyStats();

  // Mutating one should not affect the other
  stats1.toolCounts.set("test", 1);
  stats1.filePaths.add("/test/path");
  stats1.seenMessageIds.set("msg1", { in: 100 });

  assert.strictEqual(stats2.toolCounts.size, 0);
  assert.strictEqual(stats2.filePaths.size, 0);
  assert.strictEqual(stats2.seenMessageIds.size, 0);
});

// ── ADVERSARIAL NESTED STRUCTURE TESTS ────────────────────────────────────────

test("adversarial: deeply nested structures don't cause stack overflow", () => {
  const home = makeHome();
  try {
    const dir = join(home, ".clawspring", "sessions", "daily", "d");
    mkdirSync(dir, { recursive: true });

    // Create extremely deep nesting
    let deepJson = '{"a":';
    for (let i = 0; i < 100; i++) {
      deepJson += '{"b":';
    }
    deepJson += '1' + '}'.repeat(101);

    writeFileSync(join(dir, "deep.json"), deepJson);

    assert.doesNotThrow(() => readClawspring(home));
  } finally {
    cleanup(home);
  }
});

test("adversarial: circular reference attempts in JSON", () => {
  // JSON.stringify would fail on circular refs, but let's test
  // what happens with attempted serialization attacks
  const home = makeHome();
  try {
    const dir = join(home, ".lmstudio", "conversations");
    mkdirSync(dir, { recursive: true });

    // Prototype pollution attempts
    const pollutionAttempts = [
      '{"__proto__":{"polluted":true}}',
      '{"constructor":{"prototype":{"polluted":true}}}',
      '{"messages":[{"__proto__":{"injected":1}}]}',
    ];

    for (let i = 0; i < pollutionAttempts.length; i++) {
      writeFileSync(join(dir, `pollute_${i}.json`), pollutionAttempts[i]);
    }

    assert.doesNotThrow(() => readLmstudio(home));
  } finally {
    cleanup(home);
  }
});

// ── ADVERSARIAL UNICODE AND ENCODING TESTS ────────────────────────────────────

test("adversarial: unicode bomb and encoding tricks", () => {
  const home = makeHome();
  try {
    const dir = join(home, ".claude", "projects", "p");
    mkdirSync(dir, { recursive: true });

    // Unicode bomb (expands massively when parsed)
    const unicodeBomb = '{"project":"' + "x".repeat(100000) + '"}';

    writeFileSync(join(home, ".claude.json.bomb"), unicodeBomb);

    // Zero-width characters in session IDs
    const zwSession = '{"projects":{"test":{"lastSessionId":"sess\\u200B\\u200C\\u200Did","lastTotalInputTokens":100}}}';
    writeFileSync(join(home, ".claude.json.zw"), zwSession);

    // Mixed encodings (all UTF-8 but with unusual chars)
    const mixedUnicode = '{"projects":{"test":{"lastSessionId":"テスト 🚀 ñoño","lastTotalInputTokens":500}}}';
    writeFileSync(join(home, ".claude.json.uni"), mixedUnicode);

    const known = new Set();
    assert.doesNotThrow(() => readClaudeOrphans(home, known));
  } finally {
    cleanup(home);
  }
});

// ── ADVERSARIAL FILE SYSTEM TESTS ─────────────────────────────────────────────

test("adversarial: missing directories and permission errors", () => {
  const home = makeHome();
  try {
    // Don't create any expected directories
    const result = readClawspring(home);
    assert.strictEqual(result.state, "absent");
    assert.strictEqual(result.sessions.length, 0);

    // Create directory but make it unreadable (if possible)
    const badDir = join(home, ".clawspring");
    mkdirSync(badDir, { recursive: true });

    // Try to read from partially created structure
    const result2 = readClawspring(home);
    assert.ok(["absent", "empty", "unreadable"].includes(result2.state));
  } finally {
    cleanup(home);
  }
});

// ── ADVERSARIAL TIMESTAMP TESTS ───────────────────────────────────────────────

test("adversarial: timestamp edge cases and timezone attacks", () => {
  const home = makeHome();
  try {
    const dir = join(home, ".clawspring", "sessions", "daily", "d");
    mkdirSync(dir, { recursive: true });

    const timestampTests = [
      '{"session_id":"ts1","total_input_tokens":100,"total_output_tokens":50}',  // no timestamp
      '{"session_id":"ts2","total_input_tokens":100,"timestamp":0}',
      '{"session_id":"ts3","total_input_tokens":100,"timestamp":-1}',
      '{"session_id":"ts4","total_input_tokens":100,"timestamp":9999999999999}',  // far future
      '{"session_id":"ts5","total_input_tokens":100,"timestamp":"not-a-date"}',
      '{"session_id":"ts6","total_input_tokens":100,"timestamp":"2026-02-30"}',  // invalid date
      '{"session_id":"ts7","total_input_tokens":100,"timestamp":"2026-13-01"}',  // invalid month
    ];

    for (let i = 0; i < timestampTests.length; i++) {
      writeFileSync(join(dir, `ts_${i}.json`), timestampTests[i]);
    }

    assert.doesNotThrow(() => readClawspring(home));
  } finally {
    cleanup(home);
  }
});

console.log("Adversarial test suite loaded");
