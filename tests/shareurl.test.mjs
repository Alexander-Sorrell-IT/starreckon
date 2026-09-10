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
  // AN EXPLICIT BUDGET, NOT THE SHIPPING ONE. This test asserts the DROP
  // MECHANISM, and it was written against whatever QR_BUDGET_BYTES happened to
  // be — so it had to be resized when the budget went 271 -> 512, and it broke
  // again at 512 -> 704 because the fixture then fit and nothing dropped. A test
  // for what happens when the budget is exceeded should name a budget it exceeds.
  const TIGHT = 300;
  const contact = {
    name: "Alexander Sorrell", github: long(30), email: `${long(20)}@${long(10)}.com`,
    phone: long(30), website: long(30), linkedin: long(30), twitter: long(30),
  };
  for (let i = 1; i <= 5; i++) contact[`social${i}`] = `${long(30)}.example/${long(14)}`;
  const url = buildShareUrl(levels, agg, contact, TIGHT);
  const p = new URLSearchParams(url.split("#")[1]);
  assert.ok(Buffer.byteLength(url, "utf8") <= TIGHT, "must respect the cap it was given");
  // name is first in CONTACT_FIELDS, so it is the last thing to go.
  assert.equal(p.get("n"), "Alexander Sorrell", "name must survive a tight budget");
  // and nothing that DID make it may be a fragment: every value is whole.
  for (const [, v] of p) assert.ok(!v.endsWith("�"), "no half-encoded value");
  // twitter is last in CONTACT_FIELDS, so it is the first thing to go.
  assert.equal(p.get("tw"), null, "lowest-priority field drops when over budget");
  // and the drop is per-field and whole: something got in, something did not.
  const present = [...p.keys()].filter((k) => ["n","gh","li","em","tel","web","tw","s1","s2","s3","s4","s5"].includes(k));
  assert.ok(present.length > 0, "a tight budget must still carry the top fields");
  assert.ok(present.length < 12, "an over-budget contact must not carry every field");
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

test("the card's budget is a printable size, and never past what the encoder can hold", async () => {
  const { QR_BUDGET_BYTES } = await import("../src/shareurl.mjs");
  const { MAX_BYTES, encodeQR } = await import("../src/qr.mjs");
  // These were briefly the same number, and that was the bug: raising the
  // encoder to version 40 silently raised the RESUME QR to 2,953 bytes and a
  // 177x177 grid, which prints at about 0.14mm a module and cannot be read.
  // What the encoder can carry and what this card should spend are separate
  // decisions.
  assert.ok(QR_BUDGET_BYTES <= MAX_BYTES, "the budget must be encodable");
  assert.ok(QR_BUDGET_BYTES < MAX_BYTES, "the budget must be a deliberate choice, not the ceiling");

  // ASSERT THE PHYSICAL RULE, NOT A MODULE COUNT. This read `size <= 89`, which
  // is version 18 written as a magic number — so the check said nothing about
  // why 18 was the limit, and it failed the moment the budget moved for a good
  // reason. The real constraint is the printed module size.
  const PRINT_MM = 36.7;   // the 104pt box the resume templates give the code
  const MIN_MM   = 0.33;   // what a phone camera resolves
  const atBudget = encodeQR("x".repeat(QR_BUDGET_BYTES));
  const mmPerModule = PRINT_MM / (atBudget.size + 4);   // +4 = quiet zone
  assert.ok(mmPerModule >= MIN_MM,
    `a full card must still print: ${atBudget.size}x${atBudget.size} at ${PRINT_MM}mm ` +
    `is ${mmPerModule.toFixed(3)}mm a module, under the ${MIN_MM}mm floor`);

  // And the budget must not be pointlessly small either: the whole reason the EC
  // tables were extended past version 10 was to fit a full contact. A contact
  // with every field at its cap must fit with nothing dropped.
  const { buildShareUrl } = await import("../src/shareurl.mjs");
  const { FIELDS, SOCIAL_FIELDS } = await import("../src/contact.mjs");
  const maxed = {};
  for (const f of FIELDS) {
    maxed[f] = SOCIAL_FIELDS.includes(f) || f === "website"
      ? `https://${"w".repeat(40)}.example/${"u".repeat(40)}`
      : "X".repeat(40);
  }
  const skipped = [];
  buildShareUrl([7, 6.6, 6.1, 5.1, 5.3],
    { total_sessions: 14265, total_duration_hours: 1288, active_days: 75, longest_streak_days: 49,
      total_input_tokens: 2.8e9, total_cache_read_tokens: 56e9 },
    maxed, QR_BUDGET_BYTES, { onDisk: 1, floor: 109_394_493_211 },
    { onSkip: (f) => skipped.push(f) });
  assert.deepEqual(skipped, [],
    `the budget must carry a fully maxed contact; dropped: ${skipped.join(", ")}`);
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
  // The card budget is 512 bytes, sized so a FULL contact travels with nothing
  // dropped and still prints readably. Assert it is scannable-sized, not that
  // it is one exact version.
  assert.ok(encodeQR(url).size <= 89, `symbol grew to ${encodeQR(url).size}, past a printable size`);
});

// ---------------------------------------------------------------------------
// Personal identity comes from the contact file or it does not appear. The
// github line fell back to a hardcoded "Alexander-Sorrell-IT", so any user who
// had not filled in "reach out" got the AUTHOR's profile printed under their
// own QR as though it were theirs.
// ---------------------------------------------------------------------------

test("no contact means no github line — never the author's profile", async () => {
  const { shareQrLines } = await import("../src/wrapped.mjs");
  const agg = { total_sessions: 10, total_input_tokens: 1e6, total_output_tokens: 1e5 };
  for (const contact of [null, undefined, {}, { name: "Someone Else" }, { github: "   " }]) {
    const out = shareQrLines([3, 3, 3, 3, 3], agg, undefined, contact).join("\n");
    assert.ok(!/Alexander-Sorrell-IT/.test(out.replace(/github\.com\/Alexander-Sorrell-IT\/starreckon/g, "")),
      `author identity leaked for contact=${JSON.stringify(contact)}`);
    assert.ok(!/github:\s*https:\/\/github\.com\/\s*$/m.test(out), "empty github line rendered");
  }
});

test("a contact's own github is the one that renders", async () => {
  const { shareQrLines } = await import("../src/wrapped.mjs");
  const agg = { total_sessions: 10, total_input_tokens: 1e6, total_output_tokens: 1e5 };
  const out = shareQrLines([3, 3, 3, 3, 3], agg, undefined, { name: "Someone Else", github: "someone-else" }).join("\n");
  assert.match(out, /github:.*github\.com\/someone-else/);
  assert.ok(!out.includes("github.com/Alexander-Sorrell-IT/"), "author identity leaked");
});

// ---------------------------------------------------------------------------
// A URL is never cut. `website` sat on the 32-character path built for handles,
// so a real profile URL was written truncated — a link that goes nowhere, in a
// code whose only job is to be followed. It hid while the field was being
// dropped for budget anyway; raising the budget made it reachable and wrong.
// ---------------------------------------------------------------------------

test("a URL field is written whole or not at all — never cut mid-link", async () => {
  const { buildShareUrl, QR_BUDGET_BYTES } = await import("../src/shareurl.mjs");
  const { compactSocial, SOCIAL_FIELDS, URL_KEYS } = await import("../src/contact.mjs");
  const site = "https://a-fairly-long-domain-name.example/a-real-path";
  const contact = { name: "Someone", website: site };
  SOCIAL_FIELDS.forEach((f, i) => { contact[f] = `https://n${i}.example/profile-path`; });

  const url = buildShareUrl([3, 3, 3, 3, 3], { total_sessions: 5 }, contact, QR_BUDGET_BYTES);
  const p = new URLSearchParams(url.split("#")[1]);

  for (const f of ["website", ...SOCIAL_FIELDS]) {
    const got = p.get(URL_KEYS[f]);
    if (got == null) continue;                    // skipped whole: allowed
    assert.equal(got, compactSocial(contact[f]),
      `${f} must be written whole, got a fragment: ${got}`);
  }
});

test("a full contact — every field populated — travels with nothing dropped", async () => {
  const { buildShareUrl, QR_BUDGET_BYTES } = await import("../src/shareurl.mjs");
  const { FIELDS, URL_KEYS } = await import("../src/contact.mjs");
  const contact = {
    name: "Alexander Sorrell", github: "Alexander-Sorrell-IT",
    linkedin: "alex-sorrell-computers", email: "someone@a.example",
    phone: "(817) 996-6123", website: "https://a.example/profile", twitter: "someone",
    social1: "https://b.example/one", social2: "https://c.example/two",
    social3: "https://d.example/three", social4: "https://e.example/four",
    social5: "https://f.example/five",
  };
  const agg = { total_sessions: 14264, total_duration_hours: 1272, active_days: 74,
    longest_streak_days: 49, total_input_tokens: 2833733206, total_output_tokens: 0 };
  const url = buildShareUrl([7, 6.6, 6.1, 5.1, 5.3], agg, contact, QR_BUDGET_BYTES);
  const p = new URLSearchParams(url.split("#")[1]);
  const missing = FIELDS.filter((f) => contact[f] && p.get(URL_KEYS[f]) == null);
  assert.deepEqual(missing, [], `the budget must carry a full contact; dropped: ${missing.join(", ")}`);
  assert.ok(Buffer.byteLength(url, "utf8") <= QR_BUDGET_BYTES, "and still respect the cap");
});

// ── a dropped field is NAMED, never silent ────────────────────────────────────
// The budget carries a realistic full contact (the test above), but the field
// caps allow 40-character handles and 48-byte social paths, and that payload
// runs past 512. Four fields came off the end with nothing said: the card
// printed, the code scanned, and the phone number simply was not in it.
test("onSkip names every contact field the budget drops", async () => {
  const { buildShareUrl, QR_BUDGET_BYTES } = await import("../src/shareurl.mjs");
  const { FIELDS, SOCIAL_FIELDS, URL_KEYS } = await import("../src/contact.mjs");
  const contact = {};
  for (const f of FIELDS) {
    contact[f] = SOCIAL_FIELDS.includes(f) || f === "website"
      ? `https://${"w".repeat(40)}.example/${"u".repeat(40)}`
      : "X".repeat(40);
  }
  const agg = { total_sessions: 153, total_duration_hours: 344, active_days: 29 };
  const skipped = [];
  // An explicit tight budget, for the same reason the drop test above uses one:
  // this asserts the REPORTING of a skip, so it must name a budget it exceeds
  // rather than riding on whatever the shipping budget currently is. At 704 the
  // maxed contact fits and nothing is skipped, which is the point of that budget.
  const TIGHT = 300;
  const url = buildShareUrl([5, 5, 5, 5, 5], agg, contact, TIGHT, null, {
    onSkip: (f) => skipped.push(f),
  });
  assert.ok(skipped.length > 0, "this payload must overflow, or the test proves nothing");
  const p = new URLSearchParams(url.split("#")[1]);
  // Every field absent from the URL was reported, and every field reported is
  // genuinely absent — the report matches the output exactly, both directions.
  const absent = FIELDS.filter((f) => contact[f] && p.get(URL_KEYS[f]) == null);
  assert.deepEqual(skipped.slice().sort(), absent.slice().sort(),
    "the skipped list must match what the URL actually lost");
});

test("onSkip is not called when the whole contact fits", async () => {
  const { buildShareUrl, QR_BUDGET_BYTES } = await import("../src/shareurl.mjs");
  const contact = { name: "A Name", github: "a-handle", email: "someone@a.example" };
  const skipped = [];
  buildShareUrl([5, 5, 5, 5, 5], { total_sessions: 1 }, contact, QR_BUDGET_BYTES, null, {
    onSkip: (f) => skipped.push(f),
  });
  assert.deepEqual(skipped, []);
});

test("buildShareUrl works with no opts argument at all", async () => {
  const { buildShareUrl } = await import("../src/shareurl.mjs");
  const url = buildShareUrl([5, 5, 5, 5, 5], { total_sessions: 1 }, { name: "A Name" });
  assert.ok(typeof url === "string" && url.includes("n=A+Name"));
});

// ── the floor must reach the URL, or the page understates the total ──────────
// The HTML page's share URL was built three arguments wide — no floorData — so
// buildShareUrl fell back to (work + cache). On a --fleet run printing a 109.4B
// floor, the page's QR carried tok=59.1B while the terminal QR beside it carried
// 109.4B. Same run, same command, and the number that travels to other people
// was the low one.
test("floorData raises tok to the floor when on-disk is lower", async () => {
  const { buildShareUrl, QR_BUDGET_BYTES } = await import("../src/shareurl.mjs");
  const agg = {
    total_sessions: 14265, total_duration_hours: 1287, active_days: 75,
    total_input_tokens: 2_833_733_206, total_output_tokens: 0,
    total_cache_read_tokens: 56_000_000_000, total_cache_write_tokens: 300_000_000,
  };
  const levels = [7, 6.6, 6.1, 5.1, 5.3];
  const tok = (u) => new URLSearchParams(u.split("#")[1]).get("tok");
  const floorData = { onDisk: 23_177_513_548, floor: 109_394_493_211 };

  const without = tok(buildShareUrl(levels, agg, { name: "A" }, QR_BUDGET_BYTES));
  const withFloor = tok(buildShareUrl(levels, agg, { name: "A" }, QR_BUDGET_BYTES, floorData));

  assert.equal(without, "59.1B", "on-disk only, the value the defect produced");
  assert.equal(withFloor, "109.4B", "the floor must win when it is higher");
});

test("a floor LOWER than on-disk never shrinks the total", async () => {
  const { buildShareUrl, QR_BUDGET_BYTES } = await import("../src/shareurl.mjs");
  const agg = { total_sessions: 1, total_input_tokens: 90_000_000_000, total_output_tokens: 0 };
  const tok = (u) => new URLSearchParams(u.split("#")[1]).get("tok");
  const u = buildShareUrl([5, 5, 5, 5, 5], agg, { name: "A" }, QR_BUDGET_BYTES,
    { onDisk: 1, floor: 2_000_000_000 });
  assert.equal(tok(u), "90.0B", "Math.max, not replacement");
});

// ── the page must read the socials the QR carries ────────────────────────────
// buildShareUrl writes the five slots as s1..s5. docs/index.html never read
// them, so every social a user entered rode inside the QR and was discarded on
// arrival — the one feature that was asked for by name.
test("docs/index.html parses s1..s5 and renders them", async () => {
  const { readFileSync } = await import("node:fs");
  const html = readFileSync(new URL("../docs/index.html", import.meta.url), "utf8");
  for (const k of ["s1", "s2", "s3", "s4", "s5"]) {
    assert.ok(html.includes(`"${k}"`), `the page must know about ${k}`);
  }
  assert.ok(/socials:\s*\[/.test(html), "parseState must expose a socials array");
  assert.ok(html.includes("d.socials"), "render must actually use it");
  assert.ok(html.includes("socialLabel"), "each social must be labelled from its host");
});

// The page cannot import contact.mjs, so the host table is copied into it. A
// copy that drifts is worse than no copy: a link would label correctly in the
// terminal and wrongly on the page it opens.
test("the page's social host table matches SOCIAL_HOSTS exactly", async () => {
  const { readFileSync } = await import("node:fs");
  const { SOCIAL_HOSTS } = await import("../src/contact.mjs");
  const html = readFileSync(new URL("../docs/index.html", import.meta.url), "utf8");
  const block = html.match(/const PAGE_SOCIAL_HOSTS = \[([\s\S]*?)\n\];/);
  assert.ok(block, "the page must carry a PAGE_SOCIAL_HOSTS table");
  const pageRows = [...block[1].matchAll(/\[(\/.*?\/[a-z]*),\s*"(.*?)"\]/g)]
    .map((m) => [m[1], m[2]]);
  const srcRows = SOCIAL_HOSTS.map(([re, label]) => [re.toString(), label]);
  assert.deepEqual(pageRows, srcRows,
    "docs/index.html's host table has drifted from src/contact.mjs");
});
