// Tests for the cross-CLI account inventory (src/identity.mjs).
// Synthetic fixture homes in os.tmpdir(); the live machine is never read.
import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { discoverIdentities, renderIdentities } from "../src/identity.mjs";

function tmp() {
  return mkdtempSync(join(tmpdir(), "starreckon-identity-"));
}
function put(path, content) {
  mkdirSync(join(path, ".."), { recursive: true });
  writeFileSync(path, content);
}
const J = (o) => JSON.stringify(o);

function claudeProfile(home, name, email) {
  mkdirSync(join(home, name, "projects", "p1"), { recursive: true });
  writeFileSync(join(home, name, "projects", "p1", "s1.jsonl"), '{"x":1}\n');
  writeFileSync(join(home, name, ".claude.json"),
    J({ oauthAccount: { emailAddress: email } }));
}

test("discovers gemini/copilot/codex identities plus claude profiles", async () => {
  const home = tmp();
  try {
    claudeProfile(home, ".claude-x", "a@example.com");
    put(join(home, ".gemini", "google_accounts.json"), J({ active: "g@example.com", old: [] }));
    put(join(home, ".copilot", "config.json"),
      "// header comment\n" + J({ lastLoggedInUser: { host: "https://github.com", login: "octo" } }));
    put(join(home, ".codex", "auth.json"), J({ email: "c@example.com", token: "sekrit" }));
    const rows = await discoverIdentities({ home, showAccounts: true });
    const byCli = Object.fromEntries(rows.map((r) => [r.cli, r.identity]));
    assert.equal(byCli.gemini, "g@example.com");
    assert.equal(byCli.copilot, "github.com:octo");
    assert.equal(byCli.codex, "c@example.com");
    assert.ok(rows.some((r) => r.cli === "claude" && r.identity === "a@example.com"));
    assert.ok(rows.every((r) => r.kind === "account" || r.kind === "local"));
  } finally {
    rmSync(home, { recursive: true, force: true });
  }
});

test("opencode reads email columns only; local stores earn local rows", async () => {
  const home = tmp();
  try {
    const { DatabaseSync } = await import("node:sqlite");
    mkdirSync(join(home, ".local", "share", "opencode"), { recursive: true });
    const db = new DatabaseSync(join(home, ".local", "share", "opencode", "opencode.db"));
    db.exec("CREATE TABLE account (id TEXT, email TEXT, access_token TEXT)");
    db.prepare("INSERT INTO account VALUES (?,?,?)").run("1", "o@example.com", "sekrit");
    db.close();
    mkdirSync(join(home, ".qwen", "usage"), { recursive: true });
    mkdirSync(join(home, ".bob", "db"), { recursive: true });
    const rows = await discoverIdentities({ home, showAccounts: true });
    const occ = rows.find((r) => r.cli === "opencode");
    assert.equal(occ.identity, "o@example.com");
    assert.equal(occ.kind, "account");
    assert.ok(rows.some((r) => r.cli === "qwen" && r.kind === "local"));
    assert.ok(rows.some((r) => r.cli === "bob" && r.kind === "local"));
    assert.ok(!rows.some((r) => r.cli === "aider"), "absent store = no row");
  } finally {
    rmSync(home, { recursive: true, force: true });
  }
});

test("aliases resolve, file rows never hold raw", async () => {
  const home = tmp();
  try {
    claudeProfile(home, ".claude-x", "a@example.com");
    put(join(home, ".gemini", "google_accounts.json"), J({ active: "g@example.com" }));
    const aliases = { "a@example.com": "Work" };
    const term = await discoverIdentities({ home, showAccounts: true, aliases });
    assert.ok(term.some((r) => r.identity === "a@example.com"), "terminal raw with flag");
    const file = await discoverIdentities({ home, showAccounts: false, aliases });
    const blob = JSON.stringify(file);
    assert.ok(!blob.includes("a@example.com") && !blob.includes("g@example.com"),
      "file rows must never hold raw identities");
    assert.ok(file.some((r) => r.identity === "Work"), "alias applied in file rows");
    assert.ok(file.some((r) => r.identity.startsWith("acct-")), "pseudonym fallback");
  } finally {
    rmSync(home, { recursive: true, force: true });
  }
});

test("renderIdentities lays out the table, empty home explains itself", async () => {
  const home = tmp();
  try {
    const rows = await discoverIdentities({ home });
    assert.match(renderIdentities(rows), /no CLI stores found/);
    claudeProfile(home, ".claude-x", "a@example.com");
    const rows2 = await discoverIdentities({ home });
    assert.match(renderIdentities(rows2), /claude/);
  } finally {
    rmSync(home, { recursive: true, force: true });
  }
});

test("repeat profiles dedupe with a count, handles pseudonymise", async () => {
  const home = tmp();
  try {
    claudeProfile(home, ".claude-a", "a@example.com");
    claudeProfile(home, ".claude-b", "a@example.com");
    put(join(home, ".copilot", "config.json"),
      J({ lastLoggedInUser: { host: "https://github.com", login: "octo" } }));
    const rows = await discoverIdentities({ home });
    const cl = rows.filter((r) => r.cli === "claude");
    assert.equal(cl.length, 1);
    assert.equal(cl[0].profiles, 2);
    const cp = rows.find((r) => r.cli === "copilot");
    assert.ok(cp.identity.startsWith("acct-"), "github login must not leak raw");
    const raw = await discoverIdentities({ home, showAccounts: true });
    assert.equal(raw.find((r) => r.cli === "copilot").identity, "github.com:octo");
  } finally {
    rmSync(home, { recursive: true, force: true });
  }
});
