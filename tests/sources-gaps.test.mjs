// Declared gaps (audit section 1): every tool the program cannot count must be
// named in spec/sources.json with counted_by: [], so `sources` reports it as
// a gap instead of a silent zero — plus the VSCodium/Code-OSS channels the
// readers already scanned, and the CLI names the api_keys filter dropped.
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { loadSources, survey, render, probe } from "../src/sources.mjs";
import { KNOWN_CLI_NAMES, readConfig, configPath } from "../src/config.mjs";

const SPEC = loadSources();
const src = (n) => SPEC.sources.find((s) => s.name === n);

test("every readerless tool is a declared gap, not a silent zero", () => {
  for (const name of ["deepseek", "chatgpt", "cursor"]) {
    const s = src(name);
    assert.ok(s, `${name} is not declared — it reads as a tool nobody uses`);
    assert.deepEqual(s.counted_by, [], `${name} must say nobody counts it`);
  }
  // qwen, aider, opencode and muse HAVE starreckon readers now — claiming
  // nobody counts them would be the gap in reverse.
  for (const name of ["qwen", "aider", "opencode", "muse"]) {
    assert.deepEqual(src(name).counted_by, ["starreckon"],
      `${name} has a reader and must say so`);
  }
});

test("the gaps report as no reader, by name", () => {
  const rows = survey();
  for (const name of ["deepseek", "chatgpt", "cursor"]) {
    const row = rows.find((r) => r.name === name);
    assert.equal(row?.state, "no reader", `${name} must surface as a gap`);
  }
  for (const name of ["qwen", "aider", "opencode", "muse"]) {
    const row = rows.find((r) => r.name === name);
    assert.notEqual(row?.state, "no reader", `${name} has a reader`);
  }
  const out = render(rows, { color: false });
  for (const name of ["deepseek", "qwen", "aider", "opencode", "muse", "chatgpt", "cursor"]) {
    assert.ok(out.includes(name), `${name} must be named in the table`);
  }
});

test("gap stores point at the real paths, and aider's at files, not the dotdir", () => {
  const segs = (s) => (s.stores ?? []).map((st) => (st.segments ?? []).join("/"));
  assert.ok(segs(src("deepseek")).includes(".deepseek/sessions"));
  assert.ok(segs(src("deepseek")).includes(".deepseek-code/sessions"));
  // The countable qwen store is usage/, not tmp/ (logs only); the opencode
  // store is the XDG data dir, and no ~/.opencode/sessions exists.
  assert.deepEqual(segs(src("qwen")), [".qwen/usage"]);
  assert.deepEqual(segs(src("opencode")), [".local/share/opencode"]);
  // Session history only: the whole .aider directory holds credential
  // material the archive must never duplicate.
  assert.deepEqual(segs(src("aider")).sort(),
    [".aider/.aider.chat.history.md", ".aider/.aider.input.history"].sort());
  // chatgpt has no local session store — declared with none, and saying why.
  assert.deepEqual(src("chatgpt").stores, []);
  assert.match(src("chatgpt").note, /no local session store/i);
  assert.match(src("chatgpt").note, /[Cc]odex/);
});

test("aider's file stores probe present when the files exist", () => {
  const h = mkdtempSync(join(tmpdir(), "gap-"));
  mkdirSync(join(h, ".aider"), { recursive: true });
  writeFileSync(join(h, ".aider", ".aider.chat.history.md"), "# chat\n");
  const pr = probe(src("aider"), h, SPEC);
  assert.equal(pr.present, true, "a declared file store must probe, not just directories");
  rmSync(h, { recursive: true, force: true });
});

test("copilot-chat, kilocode and muse declare every channel the readers scan", () => {
  for (const name of ["copilot-chat", "kilocode", "muse"]) {
    const channels = new Set((src(name).stores ?? []).map((st) => st.channel));
    for (const ch of ["Code", "Code - Insiders", "VSCodium", "Code - OSS"]) {
      assert.ok(channels.has(ch), `${name} does not declare the ${ch} channel`);
    }
  }
  const museSegs = new Set((src("muse").stores ?? []).map((st) => (st.segments ?? []).join("/")));
  assert.equal(museSegs.size, 1);
  assert.ok([...museSegs][0].includes("saoudrizwan.claude-dev"));
});

test("KNOWN_CLI_NAMES keeps api_keys for the tools that have readers", () => {
  for (const cli of ["bob", "copilot-chat", "clawspring", "cowork",
                     "qwen", "muse", "aider", "opencode"]) {
    assert.ok(KNOWN_CLI_NAMES.has(cli), `${cli} was silently dropped from api_keys`);
  }
  const home = mkdtempSync(join(tmpdir(), "gap-config-"));
  mkdirSync(join(home, ".starreckon"), { recursive: true });
  writeFileSync(configPath(home), JSON.stringify({
    api_keys: { bob: "k1", "copilot-chat": "k2", clawspring: "k3", cowork: "k4",
                qwen: "k5", muse: "k6", aider: "k7", opencode: "k8", fakecli: "nope" },
  }));
  const cfg = readConfig(home);
  assert.deepEqual(cfg.api_keys, { bob: "k1", "copilot-chat": "k2", clawspring: "k3", cowork: "k4",
                                   qwen: "k5", muse: "k6", aider: "k7", opencode: "k8" });
  rmSync(home, { recursive: true, force: true });
});
