// Adversarial tests for the model layer installer
//
// PURPOSE: The model layers are the one part of starreckon whose failures the
// program cannot see. Every other subsystem produces a number that some other
// subsystem cross-checks. A venv is checked by whether an interpreter EXISTS in
// it — `venvPython()` is a filesystem test — and an empty venv exists exactly
// as hard as a correct one. So a layer can install nothing, report "installed",
// and only be contradicted much later by a subprocess whose output nobody reads.
//
// THE TWO DEFECTS THIS FILE WAS WRITTEN FOR, both real:
//
// 1. TORCH FROM AN EXCLUSIVE INDEX. models.mjs installed torch with
//    `--index-url <cpu wheels>`. The exclusive form makes that host the ONLY
//    place pip may look, and download.pytorch.org/whl/cpu publishes no macOS
//    arm64 wheel — there is no CUDA build to avoid on Apple silicon, so the
//    CPU index has nothing to serve it. Every Apple silicon install failed with
//    "no matching distribution", which in a captured-output installer is
//    indistinguishable from a network error. The intent — prefer CPU wheels —
//    is `--extra-index-url`. The same line existed in deadreckon's install.py
//    and was fixed there first; this copy was missed, which is the whole
//    argument for testing the property rather than the line.
//
// 2. A LAYER THAT STOPS INSTALLING WHAT IT IMPORTS. deadreckon's forecaster
//    venv lost `cisco-tsm` when two pip calls were collapsed into one. The
//    venv built green and died at import. starreckon declares the same layer in
//    spec/models.json, so the same class of edit is one keystroke away here.
//
// PRINCIPLE, borrowed from deadreckon's adv_suite_integrity.py: every question
// is asked twice — once against the real tree, where the answer must be clean,
// and once with the defect planted, where it must be FOUND. A checker that
// found nothing and a checker that looked at nothing print the same clean
// sheet, so each test also asserts how much it actually examined.
//
// Nothing here runs pip or writes outside a temp dir: the install commands are
// read as source text, never executed.
//
// Run: node --test tests/adversarial-model-layers.test.mjs

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const SRC = join(HERE, "..", "src");
const SPEC = join(HERE, "..", "spec");

const modelsSrc = readFileSync(join(SRC, "models.mjs"), "utf-8");
const spec = JSON.parse(readFileSync(join(SPEC, "models.json"), "utf-8"));

// ── The detector, used by BOTH directions ────────────────────────────────────
//
// One function, called by the real-tree test and by the planted-defect test, so
// a future weakening cannot pass one while failing the other.

/** pip invocations that install torch through an EXCLUSIVE index. */
function exclusiveTorchIndexes(src) {
  const hits = [];
  let seen = 0;
  // Each `run(pip, [...])` argument list, as written.
  for (const m of src.matchAll(/\[([^[\]]*?"install"[^[\]]*?)\]/gs)) {
    const args = [...m[1].matchAll(/"([^"]*)"/g)].map((a) => a[1]);
    if (!args.includes("torch")) continue;
    seen += 1;
    if (args.includes("--index-url")) hits.push(args.join(" "));
  }
  return { hits, seen };
}

test("torch is never installed from an exclusive index", () => {
  const { hits, seen } = exclusiveTorchIndexes(modelsSrc);
  // Say what was examined BEFORE the verdict: zero commands found would make
  // the assertion below pass without asking anything.
  assert.ok(seen > 0, "no torch install command was found in models.mjs — the "
    + "scan read nothing, so a clean result means nothing");
  assert.deepEqual(hits, [], "--index-url makes the CPU wheel index the only "
    + "place pip may look, and it has no macOS arm64 wheel for torch. Use "
    + "--extra-index-url so PyPI remains a fallback.");
});

test("PLANTED: an exclusive torch index is detected", () => {
  const broken = modelsSrc.replace(/"--extra-index-url"/g, '"--index-url"');
  assert.notEqual(broken, modelsSrc, "models.mjs no longer contains "
    + "--extra-index-url, so nothing was planted and the next assertion would "
    + "pass against unmodified source");
  const { hits } = exclusiveTorchIndexes(broken);
  assert.ok(hits.length > 0, "the detector cannot see the defect this file "
    + "was written for");
});

// ── Layer declarations ───────────────────────────────────────────────────────

/** Layers whose declared pip set is empty — a venv that installs nothing. */
function emptyPipLayers(layers) {
  return layers
    .filter((l) => !Array.isArray(l.pip) || l.pip.length === 0)
    .map((l) => l.name);
}

test("every declared layer installs at least one package", () => {
  assert.ok(spec.layers.length > 0, "spec/models.json declares no layers — "
    + "the scan read nothing");
  assert.deepEqual(emptyPipLayers(spec.layers), [], "a layer with an empty pip "
    + "set builds a venv that exists and contains nothing, and venvPython() "
    + "reports it installed");
});

test("PLANTED: a layer that installs nothing is detected", () => {
  const broken = structuredClone(spec.layers);
  broken[0].pip = [];
  assert.deepEqual(emptyPipLayers(broken), [broken[0].name],
    "the detector cannot see a layer stripped of its packages");
});

// The forecast layer is the one shared with deadreckon, and the one whose
// package set was actually lost there. Naming it explicitly means a silent
// drop here fails on the name rather than on a count that could be padded by
// an unrelated layer gaining a package.
test("the forecast layer still declares cisco-tsm", () => {
  const forecast = spec.layers.find((l) => l.name === "forecast");
  assert.ok(forecast, "no layer named 'forecast' in spec/models.json");
  assert.ok(forecast.pip.includes("cisco-tsm"),
    "cisco-tsm is what the forecaster IS. deadreckon's copy of this layer lost "
    + "it when two pip calls were collapsed into one; the venv reported DONE "
    + "and the forecaster died at import.");
  assert.equal(forecast.pipTorch, true,
    "the forecast layer needs torch installed ahead of its own packages");
});

test("every layer's venv is distinct", () => {
  // One venv per layer is the reason this registry exists: the layers'
  // dependency sets conflict, and a shared venv is a resolver fight where the
  // last install wins — silently, with no failed step anywhere.
  const venvs = spec.layers.map((l) => l.venv ?? l.venvFrom);
  assert.ok(venvs.length > 0, "no layers read");
  assert.equal(new Set(venvs).size, venvs.length,
    `two layers share a venv: ${venvs.join(", ")}`);
});

// ── The declared index is a real index ───────────────────────────────────────

test("the pytorch cpu index is declared once, in the spec, as https", () => {
  assert.equal(typeof spec.pytorch_cpu_index, "string");
  assert.ok(spec.pytorch_cpu_index.startsWith("https://"),
    "an install index reached over plaintext is a package-substitution door");
  // src/models.mjs is on verify.mjs's static allowlist, where a URL literal is
  // exactly how egress gets smuggled past a reviewer. The index must be READ
  // from spec/, never restated in the source.
  assert.ok(!modelsSrc.includes(spec.pytorch_cpu_index),
    "models.mjs restates the index URL instead of reading it from spec/, which "
    + "is both a second place to update and a literal on an allowlisted file");
});
