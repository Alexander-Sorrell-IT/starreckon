// tests/models.test.mjs — the four Cisco models and the three venvs they need.
//
// Nothing here downloads anything. These test the registry, the paths, and the
// refusals — the parts that can be wrong silently. An install that actually
// pulls weights is a network operation and belongs to a human running the door.
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import {
  modelLayers, installLayer, layerByName, layerState, modelsStatus,
  venvPath, venvPython, pytorchCpuIndex,
} from "../src/models.mjs";
import { witnessPaths, WITNESS_VENV_BASENAME } from "../src/series.mjs";

const tmp = () => mkdtempSync(join(tmpdir(), "starreckon-models-"));

test("all four Cisco models are declared, across three environments", () => {
  const repos = modelLayers().flatMap((l) => l.repos);
  assert.deepEqual(repos.sort(), [
    "cisco-ai/SecureBERT2.0-biencoder",
    "cisco-ai/SecureBERT2.0-cross_encoder",
    "cisco-ai/cisco-time-series-model-1.0",
    "fdtn-ai/antares-350m",
  ]);
  assert.equal(new Set(modelLayers().map((l) => l.venv)).size, 3,
    "one venv per layer — their dependency sets conflict");
});

test("the forecaster path is BOUND to series.mjs, never restated", () => {
  // series.mjs exports this constant specifically so the installer binds to it:
  // "two files that must agree about where a directory lives are two files that
  // will one day disagree", and the disagreement would show up as a permanent
  // false `not installed`. This test is that promise.
  const home = tmp();
  assert.equal(layerByName("forecast").venv, WITNESS_VENV_BASENAME);
  assert.equal(venvPath(layerByName("forecast"), home), witnessPaths(home).venv);
});

test("a venv with no interpreter is a FAILED install, not an installed layer", () => {
  // The same test forecast_check.py:infer() uses. Calling an empty directory
  // "installed" would make every later run skip the repair.
  const home = tmp();
  const forecast = layerByName("forecast");
  mkdirSync(venvPath(forecast, home), { recursive: true });
  assert.equal(venvPython(forecast, home), null);
  assert.equal(layerState(forecast, home), "ready");
});

test("an interpreter present means installed", () => {
  const home = tmp();
  const antares = layerByName("antares");
  const bin = join(venvPath(antares, home), "bin");
  mkdirSync(bin, { recursive: true });
  writeFileSync(join(bin, "python"), "");
  assert.equal(layerState(antares, home), "installed");
  assert.equal(modelsStatus(home).find((l) => l.name === "antares").state, "installed");
});

test("installLayer is a no-op when the layer is already installed", async () => {
  const home = tmp();
  const antares = layerByName("antares");
  const bin = join(venvPath(antares, home), "bin");
  mkdirSync(bin, { recursive: true });
  writeFileSync(join(bin, "python"), "");
  const r = await installLayer(antares, { home });
  assert.equal(r.ok, true);
  assert.equal(r.state, "already", "must not re-run pip on an installed layer");
});

test("the search layer is delegated to search.py, not installed twice", async () => {
  // search.py owns its setup because it builds the index as well as pulling
  // weights. The registry still lists it, so the registry is the whole truth
  // about which models exist rather than only the ones this file installs.
  const r = await installLayer(layerByName("search"), { home: tmp() });
  assert.equal(r.state, "delegated");
  assert.match(r.why, /--search-setup/);
});

test("installLayer reports failure instead of throwing", async () => {
  // A model layer that cannot install must not take down a scan that already
  // worked without it.
  const home = tmp();
  const r = await installLayer(layerByName("antares"), {
    home,
    python: "definitely-not-a-real-python-binary",
  });
  assert.equal(r.ok, false);
  assert.equal(r.state, "failed");
  assert.ok(r.why && typeof r.why === "string");
});

test("torch comes from the CPU wheel index, not the default CUDA build", () => {
  // A laptop that will never use CUDA should not download one.
  assert.match(pytorchCpuIndex(), /download\.pytorch\.org\/whl\/cpu/);
  assert.equal(layerByName("forecast").pipTorch, true);
  assert.equal(layerByName("antares").pipIndex, pytorchCpuIndex());
});
