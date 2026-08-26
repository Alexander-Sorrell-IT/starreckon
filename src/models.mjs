// The Cisco model layers — all four, in one registry.
//
// Ported from deadreckon-count/install.py, which keeps one venv per model
// because their dependency sets genuinely conflict: the forecaster wants torch
// from the CPU wheel index plus cisco-tsm, search wants sentence-transformers,
// Antares wants transformers + torch, and NER wants ModernBERT. One environment
// holding all four is a resolver fight that ends with whichever was installed
// last winning.
//
//   .venv-search    cisco-ai/SecureBERT2.0-biencoder      candidate retrieval
//                   cisco-ai/SecureBERT2.0-cross_encoder  reranking
//                   cisco-ai/SecureBERT2.0-NER            entity extraction
//   .venv-forecast  cisco-ai/cisco-time-series-model-1.0  the forecast witness
//   .venv-antares   fdtn-ai/antares-350m                  vulnerability scan
//
// WHY A REGISTRY RATHER THAN THREE INSTALLERS. The paths already had to agree
// across files — series.mjs states it plainly: "two files that must agree about
// where a directory lives are two files that will one day disagree, and the
// disagreement would surface here as a permanent false `not installed`". So the
// forecaster's path is IMPORTED from series.mjs, never restated here, and the
// other two are declared once and read everywhere.
//
// Nothing in this file downloads anything on its own. install() is only ever
// reached from a door the user opened, and every layer is optional: a machine
// without any of them still scans, still counts, still writes its folder.
import { existsSync, mkdirSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { WITNESS_VENV_BASENAME } from "./series.mjs";

// The registry is DATA, in spec/models.json beside spec/sources.json.
//
// Not merely tidier: this file is on verify.mjs's static allowlist, and an
// allowlisted file may not name an egress destination — the only one permitted
// there is the positive-control probe. That rule is right, because a URL
// literal inside allowlisted code is exactly how egress gets smuggled past a
// reviewer. So the package index is declared in spec/, where it is diffable and
// cannot hide, and this file reads it.
// LAZY, like sources.mjs's loadSources(). Reading at module load means merely
// IMPORTING this file throws when spec/ is absent — which is every test fixture
// that copies src/ alone, and any tree where the data file was lost. A registry
// that cannot be read is a real failure, but it belongs to the caller that
// wanted the registry, not to everyone who imported the module.
let _spec = null;
function spec() {
  if (_spec) return _spec;
  _spec = JSON.parse(
    readFileSync(new URL("../spec/models.json", import.meta.url), "utf-8"),
  );
  return _spec;
}

// The four models, and the three environments they live in — built from
// spec/models.json. `venvFrom` is resolved here rather than written into the
// data, so the forecaster's directory stays BOUND to series.mjs's exported
// constant: series.mjs asks for exactly that, because "two files that must
// agree about where a directory lives are two files that will one day
// disagree", and here the disagreement would read as a permanent false
// `not installed`.
const VENV_BINDINGS = { "series.WITNESS_VENV_BASENAME": WITNESS_VENV_BASENAME };

let _layers = null;

/** The four models, across three environments. Reads spec/models.json once. */
export function modelLayers() {
  if (_layers) return _layers;
  const sp = spec();
  _layers = Object.freeze(
    sp.layers.map((l) =>
      Object.freeze({
        ...l,
        venv: l.venvFrom ? VENV_BINDINGS[l.venvFrom] : l.venv,
        pipIndex: l.pipIndexFrom ? sp[l.pipIndexFrom] : l.pipIndex,
        pip: Object.freeze([...l.pip]),
        repos: Object.freeze([...l.repos]),
      }),
    ),
  );
  return _layers;
}

export function pytorchCpuIndex() {
  return spec().pytorch_cpu_index;
}

export function layerByName(name) {
  return modelLayers().find((l) => l.name === name) ?? null;
}

export function venvPath(layer, home) {
  return join(home ?? homedir(), ".starreckon", layer.venv);
}

// A venv is INSTALLED when it holds an interpreter — the same test
// forecast_check.py:infer() uses. A directory with no python in it is a failed
// install, not an installed layer, and calling it installed would make every
// later run skip the repair.
export function venvPython(layer, home) {
  const v = venvPath(layer, home);
  return [join(v, "bin", "python"), join(v, "Scripts", "python.exe")]
    .find((p) => existsSync(p)) ?? null;
}

export function layerState(layer, home) {
  return venvPython(layer, home) ? "installed" : "ready";
}

/** Every layer with its state — what `--models-status` prints. */
export function modelsStatus(home) {
  return modelLayers().map((l) => ({
    name: l.name,
    title: l.title,
    state: layerState(l, home),
    venv: venvPath(l, home),
    repos: [...l.repos],
    purpose: l.purpose,
  }));
}

// LAZY, NEVER AT MODULE LOAD.
//
// cli.mjs imports this file for the registry — the names, paths and states,
// none of which spawn anything. By then the tripwire is armed, and a top-level
// `import ... from "node:child_process"` would trip it on every run, including
// runs that never open the models door. Same rule cli.mjs already documents for
// its own five spawn sites.
async function run(cmd, args, timeoutMs) {
  const { spawnSync } = await import("node:child_process");
  const r = spawnSync(cmd, args, { encoding: "utf-8", timeout: timeoutMs });
  if (r.error) return { ok: false, why: r.error.message };
  if (r.status !== 0) {
    const tail = (r.stderr || r.stdout || "").trim().split("\n").slice(-2).join(" ");
    return { ok: false, why: `exit ${r.status}${tail ? ": " + tail : ""}` };
  }
  return { ok: true };
}

/**
 * Create one layer's environment and pre-pull its weights.
 *
 * WHY PRE-PULL RATHER THAN LAZY-LOAD, from deadreckon _download_model: the
 * consumers set HF_HUB_OFFLINE=1 before importing the model library, which is
 * right for a running system — no network on every inference — but means the
 * FIRST run after install fails with a missing-model error even though the venv
 * is fine. Install is the one step expected to hit the network, so it is the
 * step that should do the download.
 *
 * Returns { ok, state, why } and never throws: a model layer that fails to
 * install must not take down a scan that already worked without it.
 */
export async function installLayer(layer, { home, python = "python3", onStep = () => {} } = {}) {
  if (layer.installer === "search-setup") {
    return { ok: false, state: "delegated", why: "installed by `starreckon search --search-setup`" };
  }
  const venv = venvPath(layer, home);
  if (venvPython(layer, home)) return { ok: true, state: "already", why: venv };

  mkdirSync(join(home ?? homedir(), ".starreckon"), { recursive: true });
  onStep(`creating ${layer.venv}`);
  let r = await run(python, ["-m", "venv", venv], 300_000);
  if (!r.ok) return { ok: false, state: "failed", why: r.why };

  const pip = [join(venv, "bin", "pip"), join(venv, "Scripts", "pip.exe")]
    .find((p) => existsSync(p));
  if (!pip) return { ok: false, state: "failed", why: "venv has no pip" };

  // torch first and from the CPU index, so the forecaster does not drag a CUDA
  // build onto a laptop that will never use it.
  if (layer.pipTorch) {
    onStep("installing torch (cpu wheels)");
    r = await run(pip, ["install", "--quiet", "torch", "--index-url", pytorchCpuIndex()], 3_600_000);
    if (!r.ok) return { ok: false, state: "failed", why: r.why };
  }
  onStep(`installing ${layer.pip.join(", ")}`);
  const pipArgs = ["install", "--quiet", ...layer.pip];
  if (layer.pipIndex) pipArgs.push("--index-url", layer.pipIndex);
  r = await run(pip, pipArgs, 3_600_000);
  if (!r.ok) return { ok: false, state: "failed", why: r.why };

  const py = venvPython(layer, home);
  for (const repo of layer.repos) {
    onStep(`downloading ${repo}`);
    r = await run(py, [
      "-c",
      "import sys;from huggingface_hub import snapshot_download;snapshot_download(sys.argv[1])",
      repo,
    ], 3_600_000);
    if (!r.ok) return { ok: false, state: "failed", why: `${repo}: ${r.why}` };
  }
  return { ok: true, state: "done", why: venv };
}
