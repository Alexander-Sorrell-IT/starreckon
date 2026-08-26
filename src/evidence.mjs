// Source evidence for a counted session — ported from deadreckon-count:
// sessions.source_evidence / sessions.add_source_evidence, and the three
// consumers in token_ledger.py (_sources, _merge_sources, _evidence_matches).
//
// WHY THIS EXISTS
//
// ledger.mjs lets a NEWER scanner correct an OLDER one's inflated number, by
// taking the max per field within the newest scanner_version that ever saw a
// session. That is right when the scanner was fixed, and wrong when the
// transcript was simply deleted: both look like "the new scan says less".
// Without evidence the two are indistinguishable, so a partial transcript loss
// silently rewrites history as if it were a correction.
//
// Evidence makes them distinguishable. Each observation records the files that
// supplied its tokens — masked path, size, and SHA-256. A LOWER recount is then
// only accepted when every earlier contributing file is proven to have
// survived: same path, and either strictly larger (the file grew) or identical
// size AND identical hash (the file is untouched). A file that shrank, changed
// content at the same size, or vanished fails the test, and the historic
// high-water value is kept instead.
//
// Nothing here reads file CONTENT into the record — only length and digest, so
// the evidence is stable, cheap to compare, and discloses nothing.
import { createHash } from "node:crypto";
import { readFileSync, realpathSync, statSync } from "node:fs";
import { relative, resolve, sep } from "node:path";

// Same ordering rule as the Python: (path, bytes, sha256), so two runs that saw
// the same files produce byte-identical evidence arrays.
function bySourceKey(a, b) {
  return (
    a.path.localeCompare(b.path) ||
    a.bytes - b.bytes ||
    a.sha256.localeCompare(b.sha256)
  );
}

function sameItem(a, b) {
  return a.path === b.path && a.bytes === b.bytes && a.sha256 === b.sha256;
}

function pushUnique(out, item) {
  if (!out.some((x) => sameItem(x, item))) out.push(item);
}

// A path under $HOME becomes "~/rest"; anything else keeps its resolved path.
// Mirrors source_evidence's relative_to(home) with its ValueError fallback.
function maskUnderHome(resolved, home) {
  if (!home) return resolved;
  const rel = relative(home, resolved);
  if (!rel || rel.startsWith("..") || rel.includes(`..${sep}`)) return resolved;
  return `~/${rel.split(sep).join("/")}`;
}

/**
 * Stable, non-content evidence for the files that supplied a session's tokens.
 * Unreadable or vanished files are skipped, never guessed at — the Python
 * swallows OSError per file for the same reason: a corrupt snapshot costs one
 * file, not the whole scan.
 */
export function sourceEvidence(home, files) {
  let root = null;
  if (home) {
    try {
      root = realpathSync(home);
    } catch {
      root = resolve(home);
    }
  }
  const out = [];
  for (const f of files ?? []) {
    let resolved;
    try {
      resolved = realpathSync(f);
    } catch {
      continue;
    }
    let bytes, sha256;
    try {
      bytes = statSync(resolved).size;
      sha256 = createHash("sha256").update(readFileSync(resolved)).digest("hex");
    } catch {
      continue;
    }
    pushUnique(out, { path: maskUnderHome(resolved, root), bytes, sha256 });
  }
  return out.sort(bySourceKey);
}

/**
 * Add every contributing file once; merged sessions retain every contributor.
 */
export function addSourceEvidence(rec, home, ...files) {
  const sources = (rec.sources ??= []);
  for (const item of sourceEvidence(home, files)) pushUnique(sources, item);
  sources.sort(bySourceKey);
  return rec;
}

/**
 * Return only COMPLETE source evidence from a session or ledger row.
 * A half-written item cannot prove anything, so it is dropped rather than
 * trusted: path non-empty string, bytes a non-negative non-boolean integer,
 * sha256 exactly 64 hex characters.
 */
export function normalizeSources(value) {
  const out = [];
  for (const item of value ?? []) {
    if (!item || typeof item !== "object" || Array.isArray(item)) continue;
    const { path, bytes, sha256 } = item;
    if (typeof path !== "string" || !path) continue;
    if (typeof bytes !== "number" || !Number.isInteger(bytes) || bytes < 0) continue;
    if (typeof sha256 !== "string" || sha256.length !== 64) continue;
    if (!/^[0-9a-fA-F]{64}$/.test(sha256)) continue;
    pushUnique(out, { path, bytes, sha256 });
  }
  return out.sort(bySourceKey);
}

/**
 * Keep every source identity at its largest observed size.
 *
 * Equal-size, different-hash observations are deliberately BOTH retained: a
 * same-sized rewrite is evidence of a changed contributor, not a replacement
 * that may erase the earlier evidence.
 */
export function mergeSources(...groups) {
  const largest = new Map();
  const hashes = new Map();
  for (const group of groups) {
    for (const { path, bytes, sha256 } of normalizeSources(group)) {
      const cur = largest.has(path) ? largest.get(path) : -1;
      if (bytes > cur) {
        largest.set(path, bytes);
        hashes.set(path, new Set([sha256]));
      } else if (bytes === cur) {
        hashes.get(path).add(sha256);
      }
    }
  }
  const out = [];
  for (const path of [...largest.keys()].sort()) {
    for (const sha256 of [...hashes.get(path)].sort()) {
      out.push({ path, bytes: largest.get(path), sha256 });
    }
  }
  return out;
}

/**
 * Whether one observation proves every earlier contributing file survived.
 *
 * No previous evidence means nothing to contradict, so the lower value is
 * allowed — ledger rows written before evidence existed must not all become
 * unfalsifiable high-water marks.
 */
export function evidenceMatches(current, previous) {
  const now = normalizeSources(current);
  const before = mergeSources(previous);
  if (!before.length) return true;
  return before.every((old) =>
    now.some(
      (fresh) =>
        fresh.path === old.path &&
        (fresh.bytes > old.bytes ||
          (fresh.bytes === old.bytes && fresh.sha256 === old.sha256)),
    ),
  );
}
