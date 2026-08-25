// Tests for readClaudeOrphans — the four double-counting traps, each with a
// fixture that fails loudly if the guard against it is removed.
//
// Verified against deadreckon's Python reader on the author's machine:
// 48 sessions / 2,324,208,273 tokens, field for field. These fixtures are
// synthetic so the suite does not depend on that machine.
import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { readClaudeOrphans } from "../src/accounts.mjs";

const tmp = () => mkdtempSync(join(tmpdir(), "starreckon-orphans-"));

function writeConfig(home, rel, doc) {
  const p = join(home, rel);
  mkdirSync(join(p, ".."), { recursive: true });
  writeFileSync(p, JSON.stringify(doc));
  return p;
}

// A .claude.json projects entry, in Claude's own field names.
function project(sid, { input = 0, output = 0, cacheRead = 0, cacheCreate = 0, models } = {}) {
  const pr = {
    lastSessionId: sid,
    lastTotalInputTokens: input,
    lastTotalOutputTokens: output,
    lastTotalCacheReadInputTokens: cacheRead,
    lastTotalCacheCreationInputTokens: cacheCreate,
  };
  if (models) pr.lastModelUsage = models;
  return pr;
}

const one = (rows, sid) => rows.find((r) => r.session_id === sid);
const withHome = (fn) => {
  const home = tmp();
  try { return fn(home); } finally { rmSync(home, { recursive: true, force: true }); }
};

test("recovers a session that has counters but no transcript", () => {
  withHome((home) => {
    writeConfig(home, ".claude.json", {
      oauthAccount: { emailAddress: "a@example.com" },
      projects: { "/w/x": project("s1", { input: 10, output: 5, cacheRead: 100 }) },
    });
    const rows = readClaudeOrphans(home, new Set());
    assert.equal(rows.length, 1);
    assert.equal(rows[0].session_id, "s1");
    assert.equal(rows[0].account, "a@example.com");
    assert.equal(rows[0].total, 115);
    assert.equal(rows[0].transcript, false);
  });
});

test("REPEATED: snapshots of one session take the per-field MAX, never a sum", () => {
  withHome((home) => {
    const doc = (n) => ({
      oauthAccount: { emailAddress: "a@example.com" },
      projects: { "/w/x": project("s1", { input: n, cacheRead: n * 10 }) },
    });
    // Same session restated in four snapshots — a per-file sum would be 4x.
    writeConfig(home, ".claude.json", doc(100));
    writeConfig(home, ".claude.json.backup", doc(80));
    writeConfig(home, ".claude/backups/.claude.json.backup.1", doc(60));
    writeConfig(home, ".claude/backups/.claude.json.backup.2", doc(90));

    const rows = readClaudeOrphans(home, new Set());
    assert.equal(rows.length, 1, "four snapshots are one session");
    assert.equal(rows[0].tokens.input_tokens, 100, "max, not 100+80+60+90");
    assert.equal(rows[0].tokens.cache_read_input_tokens, 1000);
  });
});

test("per-field max, not max-of-the-sum: a field held only by the smaller snapshot survives", () => {
  withHome((home) => {
    // A wins on total, B alone holds cache_read. Winner-takes-all on the sum
    // would silently drop B's 150.
    writeConfig(home, ".claude.json", {
      projects: { "/w/x": project("s1", { output: 100, cacheRead: 0 }) },
    });
    writeConfig(home, ".claude.json.backup", {
      projects: { "/w/x": project("s1", { output: 0, cacheRead: 150 }) },
    });
    const r = one(readClaudeOrphans(home, new Set()), "s1");
    assert.equal(r.tokens.output_tokens, 100);
    assert.equal(r.tokens.cache_read_input_tokens, 150);
    assert.equal(r.total, 250);
  });
});

test("SUBSET: lastModelUsage names the model but never contributes counters", () => {
  withHome((home) => {
    writeConfig(home, ".claude.json", {
      projects: {
        "/w/x": project("s1", {
          input: 10,
          cacheRead: 90,
          // Restates lastTotal* field for field. Reading both is exactly 2x.
          models: { "claude-opus-5": { inputTokens: 10, cacheReadInputTokens: 90 } },
        }),
      },
    });
    const r = one(readClaudeOrphans(home, new Set()), "s1");
    assert.equal(r.total, 100, "lastModelUsage must not be added on top");
    assert.equal(r.model, "claude-opus-5", "but the model name IS kept");
  });
});

test("DOUBLE: a session the transcript scan already emitted is excluded", () => {
  withHome((home) => {
    writeConfig(home, ".claude.json", {
      projects: {
        "/w/x": project("live", { input: 500 }),
        "/w/y": project("expired", { input: 700 }),
      },
    });
    const rows = readClaudeOrphans(home, new Set(["live"]));
    assert.deepEqual(rows.map((r) => r.session_id), ["expired"]);
  });
});

test("the exclusion set is a parameter, so runs cannot leak into each other", () => {
  withHome((home) => {
    writeConfig(home, ".claude.json", {
      projects: { "/w/x": project("s1", { input: 1 }) },
    });
    assert.equal(readClaudeOrphans(home, new Set(["s1"])).length, 0);
    // A module-level exclusion set would keep s1 suppressed here.
    assert.equal(readClaudeOrphans(home, new Set()).length, 1);
  });
});

test("archived configs are read — that is where an expired counter survives", () => {
  withHome((home) => {
    writeConfig(home, ".ai-logs-archive/claude/prof/backups/.claude.json.backup.7", {
      oauthAccount: { emailAddress: "a@example.com" },
      projects: { "/w/x": project("archived", { input: 42 }) },
    });
    const rows = readClaudeOrphans(home, new Set());
    assert.deepEqual(rows.map((r) => r.session_id), ["archived"]);
  });
});

test("entries with no tokens are skipped, not emitted as zero sessions", () => {
  withHome((home) => {
    writeConfig(home, ".claude.json", {
      projects: {
        "/w/x": project("empty", {}),
        "/w/y": project("real", { input: 1 }),
      },
    });
    assert.deepEqual(readClaudeOrphans(home, new Set()).map((r) => r.session_id), ["real"]);
  });
});

test("a nameless config is labelled by PROFILE, never by $HOME or backups/", () => {
  withHome((home) => {
    // ~/.claude.json is the DEFAULT profile's state, kept beside ~/.claude.
    // Naming it after its parent would book it to the user's login name.
    writeConfig(home, ".claude.json", {
      projects: { "/w/x": project("s1", { input: 1 }) },
    });
    assert.equal(one(readClaudeOrphans(home, new Set()), "s1").account, "unknown (.claude)");
  });

  withHome((home) => {
    // EVERY profile has a backups/, so labelling by it would collapse two
    // nameless profiles into one account that does not exist.
    writeConfig(home, ".claude-alt/backups/.claude.json.backup.1", {
      projects: { "/w/x": project("s2", { input: 1 }) },
    });
    assert.equal(one(readClaudeOrphans(home, new Set()), "s2").account, "unknown (.claude-alt)");
  });
});

test("userID is used before falling back to a profile name", () => {
  withHome((home) => {
    writeConfig(home, ".claude.json", {
      userID: "abcdef0123456789",
      projects: { "/w/x": project("s1", { input: 1 }) },
    });
    assert.equal(one(readClaudeOrphans(home, new Set()), "s1").account, "user:abcdef012345");
  });
});

test("a corrupt snapshot costs one file, not the scan", () => {
  withHome((home) => {
    mkdirSync(join(home, ".claude", "backups"), { recursive: true });
    writeFileSync(join(home, ".claude", "backups", ".claude.json.backup.1"), "{not json");
    writeConfig(home, ".claude.json", {
      projects: { "/w/x": project("s1", { input: 5 }) },
    });
    assert.deepEqual(readClaudeOrphans(home, new Set()).map((r) => r.session_id), ["s1"]);
  });
});

test("every contributing config is recorded as source evidence", () => {
  withHome((home) => {
    const doc = { projects: { "/w/x": project("s1", { input: 5 }) } };
    writeConfig(home, ".claude.json", doc);
    writeConfig(home, ".claude.json.backup", doc);
    const r = one(readClaudeOrphans(home, new Set()), "s1");
    assert.equal(r.sources.length, 2, "both snapshots contributed");
    for (const s of r.sources) {
      assert.match(s.path, /^~\//, "paths are masked under home");
      assert.equal(s.sha256.length, 64);
      assert.ok(s.bytes > 0);
    }
  });
});
