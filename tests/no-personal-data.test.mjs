// The package must never carry the author's real machine records.
//
// This existed because it already happened: `feat: sync multi-machine fleet
// fixtures from deadreckon-count` (2026-08-26) copied six real machines'
// archives into tests/fixtures/machines/, and `files[]` already shipped
// tests/ on purpose — PROVE-IT §5 tells you to run the suite from the
// tarball. Two defensible decisions composed into publishing the author's
// logs: versions 0.19.0 through 0.25.0 each carried 1,382 files of real
// machine data, 90% of the tarball, to a registry, from a tool whose whole
// argument is that it never uploads your data.
//
// Excluding that one directory in files[] fixes that one directory. This
// asserts the PROPERTY instead: whatever npm would actually pack, right now,
// contains no real machine records. A future fixture walking into a shipped
// directory fails here instead of on the registry.
import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";

// The author's real machines, named explicitly. A guessed pattern misses:
// `-(laptop|desktop)-linux` does not match `dell-latitude-7480-linux`, which is
// one of the six that actually shipped. Enumerate, do not infer.
const REAL_MACHINES = [
  "asus-laptop-linux",
  "dell-inspiron-desktop-linux",
  "dell-latitude-7480-linux",
  "hp-laptop-linux",
  "macbook-air-m1",
];

const FORBIDDEN = [
  { re: /tests\/fixtures\/machines\//, why: "real multi-machine fleet archives" },
  { re: /deadreckon-count\//,          why: "a private program's records" },
  { re: /deadreckon-record\//,         why: "a private program's records" },
  { re: /\.machine-id$/,               why: "a machine identity file" },
  ...REAL_MACHINES.map((m) => ({ re: new RegExp(m.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), why: `the real machine "${m}"` })),
];

function packedFiles() {
  const out = execFileSync("npm", ["pack", "--dry-run", "--json"], {
    encoding: "utf8", stdio: ["ignore", "pipe", "ignore"],
  });
  return JSON.parse(out)[0].files.map((f) => f.path);
}

test("the published package carries no real machine records", () => {
  const files = packedFiles();
  assert.ok(files.length > 0, "npm pack reported no files at all");
  const leaks = [];
  for (const path of files) {
    for (const { re, why } of FORBIDDEN) {
      if (re.test(path)) leaks.push(`${path} — ${why}`);
    }
  }
  assert.deepEqual(leaks, [], `these would be PUBLISHED:\n  ${leaks.join("\n  ")}`);
});

test("tests/ still ships, because PROVE-IT tells you to run it from the tarball", () => {
  const files = packedFiles();
  assert.ok(
    files.some((f) => f.startsWith("tests/") && f.endsWith(".test.mjs")),
    "PROVE-IT §5 documents `node --test package/tests/` — the suite must ship"
  );
});
