// QR hardening: max error correction, a print-size budget, and redaction that
// runs BEFORE the encode — proved with a live secret in the payload.
import { test } from "node:test";
import assert from "node:assert/strict";
import { encodeQR, MAX_BYTES_M } from "../src/qr.mjs";
import { buildShareUrl, QR_BUDGET_BYTES } from "../src/shareurl.mjs";
import { sharePayload, shareQrLines } from "../src/wrapped.mjs";
import { renderStatsPage } from "../src/statspage.mjs";
import { REDACTED } from "../src/redact.mjs";

const LEVELS = [5, 5, 5, 5, 5];
const AGG = { total_sessions: 10, total_input_tokens: 1e6, total_output_tokens: 1e5 };

// Synthetic, correct-shape fixtures — no real key material.
const SK = "sk-ant-" + "K".repeat(28);
const XAI = "xai-" + "Q".repeat(24);

test("a payload past M's ceiling refuses instead of silently downgrading", () => {
  assert.equal(encodeQR("x".repeat(2400)).level, "L", "premise: auto still falls back");
  assert.throws(
    () => encodeQR("x".repeat(2400), { level: "M" }),
    /refusing to downgrade/,
    "forced M must refuse what M cannot hold"
  );
  assert.ok(MAX_BYTES_M > 0 && MAX_BYTES_M < 2953);
  assert.equal(encodeQR("x".repeat(700), { level: "M" }).level, "M");
});

test("a caller budget is enforced at encode time", () => {
  assert.throws(
    () => encodeQR("x".repeat(QR_BUDGET_BYTES + 1), { maxBytes: QR_BUDGET_BYTES }),
    /exceeds the 704-byte budget/
  );
  assert.doesNotThrow(() => encodeQR("x".repeat(QR_BUDGET_BYTES), { maxBytes: QR_BUDGET_BYTES }));
});

test("an unknown EC level is rejected, not ignored", () => {
  assert.throws(() => encodeQR("abc", { level: "H" }), /unknown EC level/);
});

test("a real share URL fits level M inside the print budget", () => {
  // The share path encodes at forced M under the budget; if a realistic URL
  // ever needed L, every share QR would print the failure line instead.
  const url = buildShareUrl(LEVELS, AGG, { name: "Someone Else", github: "someone-else" });
  const q = encodeQR(url, { level: "M", maxBytes: QR_BUDGET_BYTES });
  assert.equal(q.level, "M");
});

test("buildShareUrl redacts a secret pasted into the contact file", () => {
  const url = buildShareUrl(LEVELS, AGG, { name: `x ${SK}` });
  assert.ok(url && !url.includes("sk-ant"), `secret traveled in the URL: ${url}`);
  assert.ok(url.includes("redacted"), `expected a redaction marker: ${url}`);
  // A value that was NOTHING BUT a secret is skipped, not packed as a marker.
  const bare = buildShareUrl(LEVELS, AGG, { name: SK });
  assert.ok(bare && !bare.includes("sk-ant"));
  assert.ok(!new URLSearchParams(bare.split("#")[1]).has("n"), "bare secret must not pack a name field");
});

test("sharePayload redacts a secret in the payload", () => {
  // Compact fixture: the text payload caps at 260 bytes and skips fields that
  // do not fit, so the secret needs budget room to prove it gets redacted
  // rather than merely dropped.
  const text = sharePayload(LEVELS, {}, "", { name: `x ${XAI}` });
  assert.ok(text.includes("x "), `fixture packed no contact line: ${text}`);
  assert.ok(!text.includes("xai-"), `secret survived the payload: ${text}`);
  assert.ok(text.includes(REDACTED));
});

test("redaction runs before the QR encode, not after", () => {
  // shareQrLines encodes and displays ONE string from one variable: the
  // printed link IS the encoded bytes. A secret in the contact therefore
  // proves the matrix never saw it iff the output carries no trace of it.
  const out = shareQrLines(LEVELS, AGG, undefined, { name: `x ${SK}`, email: "a@example.com" }).join("\n");
  assert.ok(!out.includes("sk-ant"), `secret reached the QR path:\n${out}`);
  assert.ok(out.includes("redacted"), "the redaction must be visible, not silent");
});

test("an over-budget page QR is dropped, never truncated, and the page stands", () => {
  const bad = renderStatsPage({
    profile: {}, agg: AGG, starSvg: "", name: "A", shareUrl: "x".repeat(800),
  });
  assert.ok(!bad.includes("tap it here"), "an unscannable QR must not render");
  const good = renderStatsPage({
    profile: {}, agg: AGG, starSvg: "", name: "A",
    shareUrl: buildShareUrl(LEVELS, AGG, { name: "A" }),
  });
  assert.ok(good.includes("tap it here"), "a fittable QR must still render");
});
