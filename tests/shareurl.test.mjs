// tests/shareurl.test.mjs — unit tests for src/shareurl.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { buildShareUrl, parseShareUrl, PAGES_BASE, QR_BUDGET_BYTES } from "../src/shareurl.mjs";

const ARMS = 5, MAX_LV = 7;
const levels = [4.8, 4.6, 4.5, 4.7, 4.4];
const agg = {
  total_sessions: 142,
  total_duration_hours: 318,
  active_days: 89,
  longest_streak_days: 21,
  total_input_tokens: 1e9,
  total_output_tokens: 2e8,
  total_cache_read_tokens: 5e8,
  total_cache_write_tokens: 1e8,
};

// ── buildShareUrl ─────────────────────────────────────────────────────────────

test("buildShareUrl returns a string starting with PAGES_BASE", () => {
  const url = buildShareUrl(levels, agg, null);
  assert.ok(typeof url === "string");
  assert.ok(url.startsWith(PAGES_BASE), `expected ${PAGES_BASE}, got ${url}`);
});

test("buildShareUrl URL contains a fragment (#)", () => {
  const url = buildShareUrl(levels, agg, null);
  assert.ok(url.includes("#"), "no fragment in URL");
});

test("buildShareUrl encodes score param s", () => {
  const url = buildShareUrl(levels, agg, null);
  const hash = url.split("#")[1];
  const p = new URLSearchParams(hash);
  const s = parseFloat(p.get("s"));
  const expected = levels.reduce((a, b) => a + b, 0);
  assert.ok(Math.abs(s - expected) < 0.05, `s=${s} expected ~${expected}`);
});

test("buildShareUrl encodes axis levels param v", () => {
  const url = buildShareUrl(levels, agg, null);
  const p = new URLSearchParams(url.split("#")[1]);
  const v = p.get("v").split(",").map(Number);
  assert.equal(v.length, ARMS);
  levels.forEach((lv, i) => assert.ok(Math.abs(v[i] - lv) < 0.05));
});

test("buildShareUrl encodes sessions param ss", () => {
  const url = buildShareUrl(levels, agg, null);
  const p = new URLSearchParams(url.split("#")[1]);
  assert.equal(parseInt(p.get("ss"), 10), agg.total_sessions);
});

test("buildShareUrl encodes hours param h", () => {
  const url = buildShareUrl(levels, agg, null);
  const p = new URLSearchParams(url.split("#")[1]);
  assert.equal(parseInt(p.get("h"), 10), Math.round(agg.total_duration_hours));
});

test("buildShareUrl encodes streak param k when non-zero", () => {
  const url = buildShareUrl(levels, agg, null);
  const p = new URLSearchParams(url.split("#")[1]);
  assert.equal(parseInt(p.get("k"), 10), agg.longest_streak_days);
});

test("buildShareUrl omits streak param k when streak is 0", () => {
  const noStreak = { ...agg, longest_streak_days: 0 };
  const url = buildShareUrl(levels, noStreak, null);
  const p = new URLSearchParams(url.split("#")[1]);
  assert.equal(p.get("k"), null);
});

test("buildShareUrl encodes optional name param n", () => {
  const url = buildShareUrl(levels, agg, "Alexander");
  const p = new URLSearchParams(url.split("#")[1]);
  assert.equal(p.get("n"), "Alexander");
});

test("buildShareUrl omits name when null", () => {
  const url = buildShareUrl(levels, agg, null);
  const p = new URLSearchParams(url.split("#")[1]);
  assert.equal(p.get("n"), null);
});

test("buildShareUrl truncates name at 32 chars", () => {
  const long = "A".repeat(50);
  const url = buildShareUrl(levels, agg, long);
  const p = new URLSearchParams(url.split("#")[1]);
  assert.equal(p.get("n").length, 32);
});

test("buildShareUrl returns null for empty levels", () => {
  assert.equal(buildShareUrl([], agg, null), null);
});

test("buildShareUrl returns null for null levels", () => {
  assert.equal(buildShareUrl(null, agg, null), null);
});

test("buildShareUrl works without agg (null)", () => {
  const url = buildShareUrl(levels, null, null);
  assert.ok(typeof url === "string");
  assert.ok(url.startsWith(PAGES_BASE));
});

test("buildShareUrl URL fits in 271 bytes (QR v10 L capacity)", () => {
  const url = buildShareUrl(levels, agg, "Alexander Sorrell");
  const bytes = new TextEncoder().encode(url).length;
  assert.ok(bytes <= 271, `URL is ${bytes} bytes, exceeds 271`);
});

test("buildShareUrl clamps axis levels to 0..MAX_LV", () => {
  const crazy = [100, -5, 3.5, 7.001, 0];
  const url = buildShareUrl(crazy, agg, null);
  const p = new URLSearchParams(url.split("#")[1]);
  const v = p.get("v").split(",").map(Number);
  v.forEach((lv) => {
    assert.ok(lv >= 0 && lv <= MAX_LV, `level ${lv} out of range`);
  });
});

// ── parseShareUrl ─────────────────────────────────────────────────────────────

test("parseShareUrl round-trips buildShareUrl", () => {
  const url = buildShareUrl(levels, agg, "Tester");
  const d = parseShareUrl(url);
  assert.ok(d !== null);
  assert.ok(Math.abs(d.total - levels.reduce((a,b)=>a+b,0)) < 0.05);
  assert.equal(d.sessions, agg.total_sessions);
  assert.equal(d.hours, Math.round(agg.total_duration_hours));
  assert.equal(d.streak, agg.longest_streak_days);
  assert.equal(d.name, "Tester");
  assert.equal(d.levels.length, ARMS);
});

test("parseShareUrl accepts just the fragment string (no base URL)", () => {
  const url = buildShareUrl(levels, agg, null);
  const hash = url.split("#")[1];
  const d = parseShareUrl(hash);
  assert.ok(d !== null);
  assert.equal(d.levels.length, ARMS);
});

test("parseShareUrl returns null on completely invalid input", () => {
  // URLSearchParams won't throw but levels will be empty/NaN
  const d = parseShareUrl("not-a-url-at-all");
  // levels will be empty — callers treat that as invalid
  assert.ok(d === null || !d.levels.length);
});

test("parseShareUrl decodes archetype underscores as spaces", () => {
  const url = buildShareUrl(levels, agg, null);
  const d = parseShareUrl(url);
  assert.ok(!d.archetype.includes("_"), "underscores not decoded to spaces");
});

// ---- contact in the share URL ---------------------------------------------
// The [R] menu's heading reads "reach out (shown in QR)". It was not: the only
// path that encoded contact fields sat on the right of
// `buildShareUrl(...) ?? sharePayload(...)`, and buildShareUrl returns null only
// for an empty levels array — which lv5() cannot produce. Every field typed into
// that screen was written to disk and shown nowhere. These pin the fix.

test("contact fields ride in the share URL, so the QR still opens a page", () => {
  const url = buildShareUrl(levels, agg, {
    name: "Alexander Sorrell", github: "matrixbuilderops", email: "you@example.com",
  });
  const p = new URLSearchParams(url.split("#")[1]);
  assert.equal(p.get("n"), "Alexander Sorrell");
  assert.equal(p.get("gh"), "matrixbuilderops");
  assert.equal(p.get("em"), "you@example.com");
  assert.ok(url.startsWith("https://"), "must stay a clickable URL, not raw text");
});

test("a bare string is still treated as the name", () => {
  const p = new URLSearchParams(buildShareUrl(levels, agg, "Solo Name").split("#")[1]);
  assert.equal(p.get("n"), "Solo Name");
});

test("an empty contact object adds nothing, and a full one adds something", () => {
  // The first assertion alone passed with the ENTIRE contact loop deleted —
  // it only ever exercised the zero-input path. Paired with the second, the
  // test now fails if the feature is removed, which is the only reason to
  // have it.
  assert.equal(buildShareUrl(levels, agg, {}), buildShareUrl(levels, agg, null));
  assert.notEqual(
    buildShareUrl(levels, agg, { github: "someone" }),
    buildShareUrl(levels, agg, null),
    "a set contact field must change the URL");
});

test("a full contact still fits the QR byte cap", () => {
  const url = buildShareUrl(levels, agg, {
    name: "Alexander Sorrell", github: "matrixbuilderops", email: "you@example.com",
    phone: "+1-555-0100", website: "signalcore.dev", linkedin: "alexsorrell",
    twitter: "asorrell",
  });
  assert.ok(Buffer.byteLength(url, "utf8") <= QR_BUDGET_BYTES,
    `${Buffer.byteLength(url, "utf8")} bytes exceeds the ${QR_BUDGET_BYTES}-byte cap`);
});

test("over budget: whole fields are dropped, lowest priority first — never truncated", () => {
  const long = (n) => "x".repeat(n);
  const url = buildShareUrl(levels, agg, {
    name: "Alexander Sorrell", github: long(30), email: `${long(20)}@${long(10)}.com`,
    phone: long(30), website: long(30), linkedin: long(30), twitter: long(30),
  });
  const p = new URLSearchParams(url.split("#")[1]);
  assert.ok(Buffer.byteLength(url, "utf8") <= QR_BUDGET_BYTES, "must respect the cap");
  // name is first in CONTACT_FIELDS, so it is the last thing to go.
  assert.equal(p.get("n"), "Alexander Sorrell", "name must survive a tight budget");
  // and nothing that DID make it may be a fragment: every value is whole.
  for (const [, v] of p) assert.ok(!v.endsWith("�"), "no half-encoded value");
  assert.equal(p.get("tw"), null, "lowest-priority field drops when over budget");
});

test("the URL round-trips: every contact field encoded comes back out", () => {
  // parseShareUrl returned `name` and silently dropped github/email/phone/
  // website/linkedin/twitter, so any consumer reading a shared link back lost
  // the contact without an error.
  const ct = { name: "Alexander Sorrell", github: "matrixbuilderops",
               email: "you@example.com", phone: "+1-555-0100" };
  const back = parseShareUrl(buildShareUrl(levels, agg, ct));
  assert.equal(back.name, ct.name);
  for (const [f, v] of Object.entries(ct)) {
    if (f === "name") continue;
    assert.equal(back.contact[f], v, `${f} did not survive the round trip`);
  }
});

test("budget holds for characters URLSearchParams encodes but encodeURIComponent does not", () => {
  // ! ( ) ~ and an apostrophe are 1 byte under encodeURIComponent and 3 under
  // URLSearchParams. Estimating with the first and writing with the second
  // UNDER-counted, so the cap could be blown by a name like O'Brien (Alex).
  const nasty = "'".repeat(8) + "!".repeat(8) + "(".repeat(8) + ")".repeat(8);
  const url = buildShareUrl(levels, agg, {
    name: nasty, github: nasty, email: nasty, phone: nasty,
    website: nasty, linkedin: nasty, twitter: nasty,
  });
  assert.ok(Buffer.byteLength(url, "utf8") <= QR_BUDGET_BYTES,
    `${Buffer.byteLength(url, "utf8")} bytes exceeds the ${QR_BUDGET_BYTES}-byte cap`);
});

test("budget holds for multi-byte values", () => {
  const cjk = "\u6771\u4eac\u90fd\u6e0b\u8c37\u533a".repeat(5);
  const url = buildShareUrl(levels, agg, {
    name: cjk, github: cjk, email: cjk, phone: cjk,
    website: cjk, linkedin: cjk, twitter: cjk,
  });
  assert.ok(Buffer.byteLength(url, "utf8") <= QR_BUDGET_BYTES,
    `${Buffer.byteLength(url, "utf8")} bytes exceeds the ${QR_BUDGET_BYTES}-byte cap`);
});

// ---------------------------------------------------------------------------
// The budget must be the ENCODER's capacity, not a number written beside it.
// A hand-written 260 sat 11 bytes under qr.mjs's 271, and those 11 bytes were
// the email: priority puts email ahead of phone, email needed 36 to reach 267,
// was skipped for being 7 over, and phone then fit in the room email could not
// use — so the card carried a phone number and no address.
// ---------------------------------------------------------------------------

test("the URL budget is the encoder's real capacity, not a second copy of it", async () => {
  const { QR_BUDGET_BYTES } = await import("../src/shareurl.mjs");
  const { MAX_BYTES } = await import("../src/qr.mjs");
  assert.equal(QR_BUDGET_BYTES, MAX_BYTES);
});

test("a full contact puts the email in the QR, and the payload still encodes", async () => {
  const { buildShareUrl, QR_BUDGET_BYTES } = await import("../src/shareurl.mjs");
  const { encodeQR } = await import("../src/qr.mjs");
  const agg = {
    total_sessions: 14264, total_duration_hours: 1272,
    active_days: 74, longest_streak_days: 49,
    total_input_tokens: 2_800_000_000, total_output_tokens: 33_733_206,
  };
  const contact = {
    name: "Alexander Sorrell",
    github: "Alexander-Sorrell-IT",
    linkedin: "alex-sorrell-computers",
    email: "alexander.sorrell.it@gmail.com",
    phone: "(817) 996-6123",
    website: "https://github.com/Alexander-Sorrell-IT",
  };
  const url = buildShareUrl([7, 6.6, 6.1, 5.1, 5.3], agg, contact, QR_BUDGET_BYTES,
    { onDisk: 23_177_513_548, floor: 109_394_493_211 });
  assert.ok(url, "a URL must be built");
  assert.ok(url.length <= QR_BUDGET_BYTES, `${url.length} exceeds ${QR_BUDGET_BYTES}`);
  assert.match(url, /[#&]em=/, `email missing from:\n${url}`);
  // A skipped field is skipped whole — never a fragment of an address.
  assert.ok(!/[#&]em=[^&]*%40[^&]*$/.test(url) || url.includes("%40gmail.com"),
    "a partial email must never be written");
  assert.equal(encodeQR(url).size, 57, "must still be a version-10 symbol");
});
