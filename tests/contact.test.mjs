// Five social slots, each holding a URL and nothing else.
//
// The heading above a link is READ OFF the link, so there is no stored platform
// name that can drift from the URL beside it. That is the property under test.
//
// NO REAL HOST IS NAMED IN THIS FILE. The platform table lives in src/ because
// it is product data, not a fixture, and verify.mjs enforces that a shipped
// test may only name an unroutable documentation host (RFC 2606/6761) so a
// fixture can never become a live destination. Known-platform cases are driven
// FROM the exported table; everything else uses .example / .invalid.
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  labelForUrl, socialHost, compactSocial, socialsOf,
  SOCIAL_HOSTS, SOCIAL_FIELDS, SOCIAL_SLOTS, FIELDS, URL_KEYS,
  readContact, writeContact,
} from "../src/contact.mjs";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

test("every known platform in the table yields its own non-empty label", () => {
  const seen = new Set();
  for (const [re, name] of SOCIAL_HOSTS) {
    assert.ok(name && typeof name === "string", "a table entry must carry a label");
    assert.ok(re instanceof RegExp, "a table entry must carry a pattern");
    seen.add(name);
  }
  assert.ok(SOCIAL_HOSTS.length >= 20, "the table should cover the common networks");
  assert.ok(seen.size > 1, "labels must not all collapse to one name");
});

test("an unknown host is labelled with its own domain, not 'Other'", () => {
  assert.equal(labelForUrl("https://someone.example"), "someone.example");
  assert.equal(labelForUrl("https://www.someone.example/profile"), "someone.example");
  assert.equal(labelForUrl("https://deep.sub.someone.example"), "someone.example");
});

test("a value that is not a URL has no label and is dropped, never guessed at", () => {
  for (const bad of ["", "   ", "not a url at all", null, undefined, 42, {}]) {
    assert.equal(labelForUrl(bad), "", `${JSON.stringify(bad)} must have no label`);
    assert.equal(socialHost(bad), "", `${JSON.stringify(bad)} must have no host`);
  }
  const out = socialsOf({ social1: "https://a.example/x", social2: "   ", social3: "%%%" });
  assert.equal(out.length, 1, "only the parseable slot survives");
  assert.equal(out[0].field, "social1");
});

test("the QR form drops the scheme and a leading www., and keeps the path", () => {
  assert.equal(compactSocial("https://www.a.example/someone"), "a.example/someone");
  assert.equal(compactSocial("http://a.example/someone/"), "a.example/someone");
  assert.equal(compactSocial("a.example/someone"), "a.example/someone");
  // and it opens the same place: host and path are preserved
  assert.equal(socialHost(compactSocial("https://www.a.example/someone")), "a.example");
});

test("five slots exist, are wired into FIELDS, and each has a distinct URL key", () => {
  assert.equal(SOCIAL_SLOTS, 5);
  assert.equal(SOCIAL_FIELDS.length, 5);
  for (const f of SOCIAL_FIELDS) {
    assert.ok(FIELDS.includes(f), `${f} must be a real field`);
    assert.ok(URL_KEYS[f], `${f} must have a URL key`);
  }
  const keys = SOCIAL_FIELDS.map((f) => URL_KEYS[f]);
  assert.equal(new Set(keys).size, 5, "URL keys must be unique");
  const all = Object.values(URL_KEYS);
  assert.equal(new Set(all).size, all.length, "no social key may collide with an existing field key");
});

test("socials round-trip through the contact file and keep slot order", () => {
  const home = mkdtempSync(join(tmpdir(), "srk-contact-"));
  try {
    const c = { name: "Someone" };
    SOCIAL_FIELDS.forEach((f, i) => { c[f] = `https://a${i + 1}.example/profile`; });
    writeContact(home, c);
    const back = readContact(home);
    const s = socialsOf(back);
    assert.equal(s.length, 5, "all five slots survive a round-trip");
    assert.deepEqual(s.map((x) => x.url), SOCIAL_FIELDS.map((_, i) => `https://a${i + 1}.example/profile`));
    assert.deepEqual(s.map((x) => x.label), SOCIAL_FIELDS.map((_, i) => `a${i + 1}.example`));
  } finally {
    rmSync(home, { recursive: true, force: true });
  }
});

test("a social is skipped whole when it will not fit — never written as a fragment", async () => {
  const { buildShareUrl, QR_BUDGET_BYTES } = await import("../src/shareurl.mjs");
  const contact = { name: "Someone" };
  SOCIAL_FIELDS.forEach((f, i) => {
    contact[f] = `https://a-rather-long-network-name-${i}.example/a-long-profile-slug-here`;
  });
  const url = buildShareUrl([3, 3, 3, 3, 3], { total_sessions: 1 }, contact, QR_BUDGET_BYTES);
  assert.ok(Buffer.byteLength(url, "utf8") <= QR_BUDGET_BYTES, "must respect the budget");
  const p = new URLSearchParams(url.split("#")[1]);
  for (const f of SOCIAL_FIELDS) {
    const got = p.get(URL_KEYS[f]);
    if (got == null) continue;                       // skipped whole: correct
    assert.ok(socialHost(got), `a written social must still parse as a host: ${got}`);
    assert.ok(contact[f].includes(got.replace(/^https?:\/\//, "")) || compactSocial(contact[f]).startsWith(got.slice(0, 10)),
      `a written social must not be a mangled fragment: ${got}`);
  }
});
