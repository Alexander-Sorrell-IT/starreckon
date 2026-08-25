// Tests for src/evidence.mjs — the guard that tells a scanner CORRECTION
// (accept the lower number) from TRANSCRIPT LOSS (keep the historic high).
// Without it those two are the same observation: "the new scan says less".
import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  addSourceEvidence,
  evidenceMatches,
  mergeSources,
  normalizeSources,
  sourceEvidence,
} from "../src/evidence.mjs";

const tmp = () => mkdtempSync(join(tmpdir(), "starreckon-evidence-"));
const write = (home, rel, body) => {
  const p = join(home, rel);
  mkdirSync(join(p, ".."), { recursive: true });
  writeFileSync(p, body);
  return p;
};

test("sourceEvidence masks under home, records size and sha256", () => {
  const home = tmp();
  try {
    const f = write(home, "projects/a.jsonl", "hello");
    const [item] = sourceEvidence(home, [f]);
    assert.equal(item.path, "~/projects/a.jsonl");
    assert.equal(item.bytes, 5);
    // sha256("hello")
    assert.equal(
      item.sha256,
      "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
    );
  } finally {
    rmSync(home, { recursive: true, force: true });
  }
});

test("sourceEvidence skips files that cannot be read, rather than guessing", () => {
  const home = tmp();
  try {
    const good = write(home, "a.jsonl", "x");
    const gone = join(home, "vanished.jsonl");
    assert.deepEqual(sourceEvidence(home, [good, gone]).map((i) => i.path), [
      "~/a.jsonl",
    ]);
  } finally {
    rmSync(home, { recursive: true, force: true });
  }
});

test("addSourceEvidence keeps every contributor once, sorted", () => {
  const home = tmp();
  try {
    const a = write(home, "a.jsonl", "aaa");
    const b = write(home, "b.jsonl", "bb");
    const rec = {};
    addSourceEvidence(rec, home, a, b);
    addSourceEvidence(rec, home, a); // a merged session re-contributing `a`
    assert.deepEqual(rec.sources.map((i) => i.path), ["~/a.jsonl", "~/b.jsonl"]);
  } finally {
    rmSync(home, { recursive: true, force: true });
  }
});

test("normalizeSources drops incomplete evidence instead of trusting it", () => {
  const ok = {
    path: "~/a",
    bytes: 1,
    sha256: "a".repeat(64),
  };
  const rows = [
    ok,
    { path: "", bytes: 1, sha256: "a".repeat(64) }, // empty path
    { path: "~/b", bytes: -1, sha256: "a".repeat(64) }, // negative size
    { path: "~/c", bytes: true, sha256: "a".repeat(64) }, // boolean is not a size
    { path: "~/d", bytes: 1, sha256: "a".repeat(63) }, // wrong length
    { path: "~/e", bytes: 1, sha256: "z".repeat(64) }, // not hex
    null,
    "nope",
  ];
  assert.deepEqual(normalizeSources(rows), [ok]);
});

test("mergeSources keeps a path at its largest size, and keeps BOTH hashes at a tie", () => {
  const a = { path: "~/a", bytes: 10, sha256: "1".repeat(64) };
  const aBigger = { path: "~/a", bytes: 20, sha256: "2".repeat(64) };
  assert.deepEqual(mergeSources([a], [aBigger]), [aBigger]);

  // Same size, different content: a rewrite. Both survive — discarding one
  // would erase evidence that the contributor changed.
  const tie = { path: "~/a", bytes: 10, sha256: "3".repeat(64) };
  const merged = mergeSources([a], [tie]);
  assert.equal(merged.length, 2);
  assert.deepEqual(merged.map((i) => i.sha256).sort(), ["1".repeat(64), "3".repeat(64)]);
});

test("a lower recount is ALLOWED when every earlier file survived", () => {
  const before = [{ path: "~/a", bytes: 10, sha256: "1".repeat(64) }];
  // identical file: a genuine scanner fix, nothing was lost
  assert.equal(evidenceMatches(before, before), true);
  // file grew: still proof it survived
  const grew = [{ path: "~/a", bytes: 99, sha256: "9".repeat(64) }];
  assert.equal(evidenceMatches(grew, before), true);
});

test("a lower recount is REJECTED when a file shrank, vanished, or was rewritten", () => {
  const before = [{ path: "~/a", bytes: 10, sha256: "1".repeat(64) }];

  // shrank — the transcript was truncated, not the scanner corrected
  assert.equal(
    evidenceMatches([{ path: "~/a", bytes: 4, sha256: "1".repeat(64) }], before),
    false,
  );
  // vanished — nothing in the new observation covers ~/a
  assert.equal(
    evidenceMatches([{ path: "~/b", bytes: 10, sha256: "1".repeat(64) }], before),
    false,
  );
  // same size, different content — a rewrite is not proof of survival
  assert.equal(
    evidenceMatches([{ path: "~/a", bytes: 10, sha256: "2".repeat(64) }], before),
    false,
  );
  // no evidence at all in the new observation
  assert.equal(evidenceMatches([], before), false);
});

test("no PRIOR evidence means the lower value is allowed", () => {
  // Ledger rows written before evidence existed must not become
  // unfalsifiable high-water marks that no later scanner can ever correct.
  assert.equal(evidenceMatches([], []), true);
  assert.equal(evidenceMatches([{ path: "~/a", bytes: 1, sha256: "1".repeat(64) }], []), true);
  // ...and junk prior evidence normalizes to nothing, so it also cannot block.
  assert.equal(evidenceMatches([], [{ path: "~/a", bytes: -5, sha256: "nope" }]), true);
});
