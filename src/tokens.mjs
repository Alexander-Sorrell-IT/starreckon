// One rule for what counts as a token count, used by every reader.
//
// scan.mjs creditUsage, readers.mjs, and scanners.mjs each had their own guard
// and the three disagreed: scan.mjs and readers.mjs coerced numeric strings via
// Number() — which also accepts " 9 ", "1e3" and "0x10", contrary to the
// comments claiming they are refused — while scanners.mjs dropped every
// non-integer to 0. The same malformed value counted in one reader and vanished
// in another. There is now one function, and this file is the only place the
// rule is written.
//
// THE RULE: a token count is a non-negative safe integer, or a string of ASCII
// digits naming one. A string carrying anything else — whitespace, a sign, a
// decimal point, an exponent, hex — is not a count, because a serialiser that
// emits " 9 " or "1e3" where a count belongs is a malformed row, and crediting
// it invents tokens no counter measured. Clean digit strings ("500", "9") are
// still accepted: real serialisers emit those, and real rows must not be
// dropped.
//
// tokenCount returns null for anything that is not a count, so a caller that
// must distinguish "absent" from "zero" can. tokenOr0 folds that to 0 for
// callers accumulating into a total.
//
// NOTE on the deadreckon agreement: tests/token-count.test.mjs documents a
// cross-program table shared with deadreckon's test_token_count.py. The TABLE
// there is unchanged by this rule; the padded-string case (" 7 " counted as 7)
// is the one behaviour this tightens, and deadreckon must adopt the same rule
// before the two agree on it again.

/**
 * A token count, or null if the value is not one.
 */
export function tokenCount(v) {
  if (typeof v === "boolean" || v === null || v === undefined) return null;
  let n;
  if (typeof v === "string") {
    // Digits and nothing else. Number() would also take " 9 ", "1e3", "0x10",
    // "+5" and "Infinity" — every one of those is a shape a count never has.
    if (!/^[0-9]+$/.test(v)) return null;
    n = Number(v);
  } else if (typeof v === "number") {
    n = v;
  } else {
    return null;
  }
  // SAFE integer, not merely integer. Above 2**53 JavaScript cannot hold the
  // value exactly and Python can, so the two programs are guaranteed to
  // disagree on anything larger. A number no one can agree on is not a count.
  if (!Number.isSafeInteger(n) || n < 0) return null;
  return n;
}

/**
 * tokenCount folded to 0: for readers accumulating into a running total, where
 * a malformed field contributes nothing rather than poisoning the sum.
 */
export function tokenOr0(v) {
  const n = tokenCount(v);
  return n === null ? 0 : n;
}
