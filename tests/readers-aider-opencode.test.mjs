// Tests for the aider and opencode readers in src/readers.mjs — synthetic
// fixtures in os.tmpdir(). The aider fixture mirrors aider's own writer
// (io.py append_chat_history shapes, base_coder.py Tokens report); the
// opencode fixture mirrors the live session_v2 schema. No dependence on
// machine-specific data.
import { test } from "node:test";
import assert from "node:assert/strict";
import { linkSync, mkdirSync, mkdtempSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { readAider, readOpencode } from "../src/readers.mjs";

let DatabaseSync = null;
try {
  ({ DatabaseSync } = await import("node:sqlite"));
} catch {}

function mkHome() {
  return mkdtempSync(join(tmpdir(), "starreckon-aider-opencode-"));
}

function put(path, content) {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, content);
}

const J = (o) => JSON.stringify(o);

// ---- aider ----------------------------------------------------------------

const AIDER_MD = `# aider chat started at 2026-10-01 08:00:00

#### add a login form
Done. I added the form.

> Tokens: 999 sent, 100 received.
> Tokens: 1.2k sent, 200 received.
> Tokens: 12k sent, 1.1k cache write, 2.0k cache hit, 300 received.
> Cost: $0.01 message, $0.02 session.

# aider chat started at 2026-10-02 09:00:00

#### second session
> Tokens: 500 sent, 50 received.
`;

test("aider: per-exchange lines sum across sessions, k-suffixes parse, cache split", () => {
  const home = mkHome();
  put(join(home, ".aider", ".aider.chat.history.md"), AIDER_MD);
  const r = readAider(home);
  assert.equal(r.state, "counted");
  assert.equal(r.sessions.length, 2);
  // Session 1: sent 999+1200+12000, recv 100+200+300, cw 1100, ch 2000.
  const s1 = r.sessions[0];
  assert.equal(s1.tokens.input, 999 + 1200 + 12000 - 1100);
  assert.equal(s1.tokens.cacheWrite, 1100);
  assert.equal(s1.tokens.cacheRead, 2000);
  assert.equal(s1.tokens.output, 600);
  assert.equal(s1.turns, 3);
  assert.equal(s1.start, "2026-10-01T08:00:00");
  assert.equal(s1.end, null);
  // Session 2 is one plain exchange.
  assert.deepEqual(r.sessions[1].tokens,
    { input: 500, cacheWrite: 0, cacheRead: 0, output: 50 });
  assert.equal(r.total, r.tokens.input + r.tokens.cacheWrite + r.tokens.cacheRead + r.tokens.output);
  assert.equal(r.approximate, true); // aider rounds the counts itself
});

test("aider: only blockquoted report lines count — prose, pastes and cost ignored", () => {
  const home = mkHome();
  put(join(home, ".aider", ".aider.chat.history.md"), [
    "# aider chat started at 2026-10-03 10:00:00",
    "",
    "#### paste this: Tokens: 5 sent, 5 received.",
    "The model mused: Tokens: 7 sent, 7 received.",
    "> Tokens: 100 sent, 10 received.",   // a real report
    // The single-line cost append: "0.02 session" must not match as "sent".
    "> Tokens: 200 sent, 20 received. Cost: $0.01 message, $0.02 session.",
    "> the question was about Tokens: 9 sent, 9 received, roughly.", // quoted prose
    "> Cost: $9.99 message, $99.99 session.",
    "> Tokens: 50 sent.",                  // half-line: no received, ignored
    "> Tokens: 60 received.",              // half-line: no sent, ignored
    "",
  ].join("\n"));
  const r = readAider(home);
  assert.equal(r.sessions.length, 1);
  assert.deepEqual(r.sessions[0].tokens,
    { input: 300, cacheWrite: 0, cacheRead: 0, output: 30 });
  assert.ok(!J(r).includes("9.99"), "cost figures must never enter the output");
  assert.ok(!J(r).includes("99.99"), "cost figures must never enter the output");
});

test("aider: per-project histories are walked, archive copies and skips are not", () => {
  const home = mkHome();
  const repo = join(home, "work", "org", "repo", ".aider.chat.history.md");
  put(repo, "# aider chat started at 2026-10-04 11:00:00\n\n> Tokens: 200 sent, 20 received.\n");
  // A protect-tick hard link of the same file: same inode, must add nothing.
  const archived = join(home, ".ai-logs-archive", "aider", ".aider.chat.history.md");
  put(archived, "# placeholder\n");
  try { linkSync(repo, archived + ".link"); } catch { /* fs without links */ }
  // A decoy a full archive copy would double-count, plus a skipped tree.
  put(join(home, ".ai-logs-archive", "other", ".aider.chat.history.md"),
    "# aider chat started at 2026-10-04 11:00:00\n\n> Tokens: 99999 sent, 99999 received.\n");
  put(join(home, "proj", "node_modules", "dep", ".aider.chat.history.md"),
    "# aider chat started at 2026-10-04 11:00:00\n\n> Tokens: 88888 sent, 88888 received.\n");
  const r = readAider(home);
  assert.equal(r.sessions.length, 1);
  assert.deepEqual(r.sessions[0].tokens,
    { input: 200, cacheWrite: 0, cacheRead: 0, output: 20 });
  assert.equal(r.sessions[0].project, join("work", "org", "repo"));
});

test("aider: the walk never descends through a symlink", () => {
  const home = mkHome();
  put(join(home, "repo", ".aider.chat.history.md"),
    "# aider chat started at 2026-10-06 13:00:00\n\n> Tokens: 300 sent, 30 received.\n");
  // A stranger's history outside the scanned root, linked back under it
  // (wine's dosdevices/ does exactly this with whole drives).
  const outside = mkdtempSync(join(tmpdir(), "aider-outside-"));
  put(join(outside, ".aider.chat.history.md"),
    "# aider chat started at 2026-10-06 13:00:00\n\n> Tokens: 44444 sent, 44444 received.\n");
  try {
    symlinkSync(outside, join(home, "linked"));
  } catch {
    return; // fs without symlinks: nothing to prove
  }
  const r = readAider(home);
  assert.equal(r.sessions.length, 1);
  assert.deepEqual(r.sessions[0].tokens,
    { input: 300, cacheWrite: 0, cacheRead: 0, output: 30 });
});

test("aider: input bucket floors at zero; input history alone is empty", () => {
  const home = mkHome();
  put(join(home, ".aider", ".aider.chat.history.md"),
    "# aider chat started at 2026-10-05 12:00:00\n\n> Tokens: 100 sent, 5.0k cache write, 10 received.\n");
  const r = readAider(home);
  assert.equal(r.sessions[0].tokens.input, 0); // 100 - 5000 floored
  assert.equal(r.sessions[0].tokens.cacheWrite, 5000);

  const home2 = mkHome();
  put(join(home2, ".aider", ".aider.input.history"), "print(1)\n");
  const r2 = readAider(home2);
  assert.equal(r2.state, "empty");
  assert.equal(r2.sessions.length, 0);
});

test("aider: absent store says absent, not zero", () => {
  const r = readAider(mkHome());
  assert.equal(r.state, "absent");
  assert.equal(r.sessions.length, 0);
});

// ---- opencode ---------------------------------------------------------------

const OPENCODE_SCHEMA = `create table session_v2 (
  id text primary key, project_id text not null, workspace_id text,
  parent_id text, fork_session_id text, fork_boundary text, slug text not null,
  directory text not null, path text, title text, version text not null,
  share_url text, cost real default 0 not null,
  tokens_input integer default 0 not null, tokens_output integer default 0 not null,
  tokens_reasoning integer default 0 not null, tokens_cache_read integer default 0 not null,
  tokens_cache_write integer default 0 not null,
  agent text, model text, time_created integer not null, time_updated integer not null)`;

function makeOpenDb(dir, sessions) {
  mkdirSync(dir, { recursive: true });
  const db = new DatabaseSync(join(dir, "opencode.db"));
  db.exec(OPENCODE_SCHEMA);
  const ins = db.prepare(`insert into session_v2
    (id, project_id, slug, directory, version, cost, tokens_input, tokens_output,
     tokens_reasoning, tokens_cache_read, tokens_cache_write, model, time_created, time_updated)
    values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)`);
  for (const s of sessions) {
    ins.run(s.id, "p1", s.id, s.directory ?? "/home/me/proj", "v",
      1.23, // cost: present in the fixture, must never be read
      s.input ?? 0, s.output ?? 0, s.reasoning ?? 0,
      s.cacheRead ?? 0, s.cacheWrite ?? 0,
      s.model ?? "", s.created ?? 1791119331896, s.updated ?? 1791119332132);
  }
  // The restating per-message table and the credential tables the reader must
  // never touch.
  db.exec("create table session_message (id text primary key, session_id text, data text)");
  db.prepare("insert into session_message values (?,?,?)").run(
    "m1", sessions[0]?.id ?? "x", J({ tokens: { input: 77777, output: 77777 } }));
  db.exec("create table account (id text primary key, access_token text, refresh_token text)");
  db.prepare("insert into account values (?,?,?)").run("a1", "SECRET-ACCESS", "SECRET-REFRESH");
  db.exec("create table credential (id text primary key, value text)");
  db.prepare("insert into credential values (?,?)").run("c1", "SECRET-CRED");
  db.close();
}

test("opencode: rollup buckets — reasoning alongside output, input net of cache", async (t) => {
  if (!DatabaseSync) return t.skip("node:sqlite not available");
  const home = mkHome();
  makeOpenDb(join(home, ".local", "share", "opencode"), [
    // Mirrors the live row: output 12 < reasoning 24 proves alongside.
    { id: "ses_one", input: 2538, output: 12, reasoning: 24, cacheRead: 4352,
      model: J({ id: "longcat-2.5", providerID: "opencode" }) },
    { id: "ses_zero" }, // all zeros: not a session
  ]);
  const r = await readOpencode(home);
  assert.equal(r.state, "counted");
  assert.equal(r.sessions.length, 1);
  const s = r.sessions[0];
  assert.deepEqual(s.tokens, { input: 2538, cacheWrite: 0, cacheRead: 4352, output: 12 + 24 });
  assert.equal(s.model, "longcat-2.5");
  assert.equal(s.project, "/home/me/proj");
  assert.equal(s.start, new Date(1791119331896).toISOString());
  assert.equal(s.end, new Date(1791119332132).toISOString());
  assert.ok(!J(r).includes("77777"), "message rows restate the rollup and must be ignored");
  for (const secret of ["SECRET-ACCESS", "SECRET-REFRESH", "SECRET-CRED"])
    assert.ok(!J(r).includes(secret), "credential tables must never be read");
  assert.ok(!J(r).includes("1.23"), "the cost column must never be read");
});

test("opencode: XDG_DATA_HOME override is honoured, copies merge by max", async (t) => {
  if (!DatabaseSync) return t.skip("node:sqlite not available");
  const home = mkHome();
  const xdg = mkdtempSync(join(tmpdir(), "oc-xdg-"));
  makeOpenDb(join(xdg, "opencode"), [
    { id: "ses_x", input: 100, output: 10 },
  ]);
  const prev = process.env.XDG_DATA_HOME;
  process.env.XDG_DATA_HOME = xdg;
  try {
    const r = await readOpencode(home);
    assert.equal(r.state, "counted");
    assert.equal(r.sessions.length, 1);
    assert.equal(r.sessions[0].tokens.input, 100);
  } finally {
    if (prev === undefined) delete process.env.XDG_DATA_HOME;
    else process.env.XDG_DATA_HOME = prev;
  }
});

test("opencode: absent, empty and corrupt stores stay distinct", async (t) => {
  if (!DatabaseSync) return t.skip("node:sqlite not available");
  const r1 = await readOpencode(mkHome());
  assert.equal(r1.state, "absent");

  const home2 = mkHome();
  mkdirSync(join(home2, ".local", "share", "opencode"), { recursive: true });
  const r2 = await readOpencode(home2);
  assert.equal(r2.state, "empty");

  const home3 = mkHome();
  put(join(home3, ".local", "share", "opencode", "opencode.db"), "not a database");
  const r3 = await readOpencode(home3);
  assert.equal(r3.state, "unreadable");
});
