// Redaction audit fixes (2026-10-11): six bypasses, each verified by probe
// against the working copy before the fix. Every test below fails on the old
// rules and passes on the new ones.
import { test } from "node:test";
import assert from "node:assert/strict";
import { userInfo } from "node:os";
import {
  redactSecrets,
  maskPath,
  maskIdentities,
  findEmail,
  accountPseudonym,
  REDACTED,
  MIN_MASKABLE_USER_LEN,
} from "../src/redact.mjs";

const me = (() => {
  try {
    return userInfo().username;
  } catch {
    return "";
  }
})();

test("xAI keys are redacted", () => {
  // No pattern covered the xai- prefix while the tool scans grok (xAI) logs.
  const key = "xai-" + "a".repeat(24);
  const out = redactSecrets(`key=${key}`);
  assert.ok(!out.includes("xai-"), `xAI key survived: ${out}`);
  assert.ok(out.includes(REDACTED));
});

test("short explicitly-labeled secrets are redacted", () => {
  // The old 16-char floor let labeled passwords and tokens through.
  for (const s of ["password: hunter2abc", "api_key=hunter2abc", 'token: "abc123"']) {
    const out = redactSecrets(s);
    assert.ok(!out.includes("hunter2abc") && !out.includes("abc123"), `survived: ${out}`);
    assert.ok(out.includes(REDACTED), `no marker in: ${out}`);
  }
});

test("Authorization: Bearer redacts the credential, not the scheme word", () => {
  const out = redactSecrets("Authorization: Bearer abc123def");
  assert.ok(!out.includes("abc123def"), `credential survived: ${out}`);
  assert.equal(out, `Authorization: ${REDACTED}`);
});

test("a bare space is prose, not a label — our own headings survive", () => {
  // The separator must contain : = or =>. Without that line, the 6-char
  // floor eats "TOKEN ECONOMICS" (the stats page's own heading) and the
  // output scrub flags our own files.
  assert.equal(redactSecrets("TOKEN ECONOMICS"), "TOKEN ECONOMICS");
  assert.equal(redactSecrets("password hunter2abc"), "password hunter2abc");
});

test("=> separators are matched", () => {
  const out = redactSecrets('password => "supersecretvalue12345"');
  assert.ok(!out.includes("supersecretvalue"), `survived: ${out}`);
  assert.ok(out.startsWith("password => "), `label/separator mangled: ${out}`);
});

test("non-enumerated connection-string schemes leak no password", () => {
  for (const s of [
    "amqp://user:s3cr3tpass@host/vhost",
    "clickhouse://admin:hunter2secret@db.local:9000/x",
    "custom+scheme://u:p@h/",
  ]) {
    const out = redactSecrets(s);
    assert.ok(!out.includes("s3cr3tpass") && !out.includes("hunter2secret"),
      `password survived in: ${out}`);
    assert.ok(!out.includes(":p@"), `password survived in: ${out}`);
  }
});

test("passwordless URLs pass through untouched", () => {
  // The generic scheme rule requires user:pass (a colon AND an @).
  for (const s of ["https://example.com:8080/a", "https://user@host/x", "https://host/path"]) {
    assert.equal(redactSecrets(`see ${s} here`), `see ${s} here`);
  }
});

test("bare-host emails are pseudonymised when labeled", () => {
  const out = maskIdentities("email: bob@mailserver");
  assert.ok(!out.includes("bob@mailserver"), `identity survived: ${out}`);
  assert.equal(out, `email: ${accountPseudonym("bob@mailserver")}`);
});

test("bare-host emails are left alone when unlabeled", () => {
  // An unlabeled word@word is prose until proven otherwise.
  assert.equal(maskIdentities("meet me@home later"), "meet me@home later");
  assert.equal(maskIdentities("no @ here, and user@ alone"), "no @ here, and user@ alone");
});

test("bare-host emails owned by the OS user are pseudonymised", (t) => {
  if (!me || me.length < MIN_MASKABLE_USER_LEN) return t.skip("username too short to mask");
  const addr = `${me}@mailserver`;
  const out = maskIdentities(`reached at ${addr} today`);
  assert.ok(!out.includes(addr), `identity survived: ${out}`);
  assert.ok(out.includes(accountPseudonym(addr)));
});

test("the naked rule never eats the head of a dotted address", () => {
  const out = maskIdentities("email: bob@mail.example.com");
  assert.ok(!out.includes("bob@mail"), `double-masked or split: ${out}`);
  assert.equal(out, `email: ${accountPseudonym("bob@mail.example.com")}`);
});

test("findEmail finds bare-host identities for the scrub check", () => {
  const hit = findEmail("contact: bob@mailserver");
  assert.ok(hit, "the scrub must see what the masker removes");
  assert.equal(hit.value, "bob@mailserver");
  assert.equal(hit.index, 9);
  assert.equal(findEmail("nothing here"), null);
  assert.equal(findEmail("meet me@home later"), null);
});

test("Windows home paths collapse to ~", (t) => {
  if (!me) return t.skip("no username available");
  const out = maskPath(`C:\\Users\\${me}\\Docs\\x.ts`);
  assert.ok(out.startsWith("~"), `path not collapsed: ${out}`);
  assert.ok(!out.includes(me), `username survived: ${out}`);
  assert.ok(!out.includes("C:"), `drive layout survived: ${out}`);
});
