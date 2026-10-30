// Private tree names live in ~/.starreckon/local-dirs.json, never in this
// tree. The skip they buy must still happen, and a broken file must not crash.
import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const probe = `
  const { COPY_DIRS, PUBLIC_COPY_DIRS } = await import("./src/accounts.mjs");
  const { SKIP } = await import("./src/discover.mjs");
  console.log(JSON.stringify({ copy: COPY_DIRS.has("priv-a"), pub: PUBLIC_COPY_DIRS.has("priv-a"), skip: SKIP.has("priv-b") }));`;

function run(file) {
  const out = execFileSync(process.execPath, ["--input-type=module", "-e", probe],
    { env: { ...process.env, STARRECKON_LOCAL_DIRS: file }, encoding: "utf8" });
  return JSON.parse(out.trim().split("\n").pop());
}

test("local-dirs.json names join the skip lists without entering the public list", () => {
  const f = join(mkdtempSync(join(tmpdir(), "sr-local-")), "local-dirs.json");
  writeFileSync(f, JSON.stringify({ copyDirs: ["priv-a"], skipDirs: ["priv-b"] }));
  assert.deepEqual(run(f), { copy: true, pub: false, skip: true });
});

test("a missing or malformed local-dirs.json adds nothing and does not throw", () => {
  const d = mkdtempSync(join(tmpdir(), "sr-local-"));
  writeFileSync(join(d, "bad.json"), "{not json");
  for (const f of [join(d, "absent.json"), join(d, "bad.json")])
    assert.deepEqual(run(f), { copy: false, pub: false, skip: false });
});
