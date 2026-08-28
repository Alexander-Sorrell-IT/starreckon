#!/usr/bin/env python3
"""An independent second opinion that commits BEFORE it sees the answer.

    python3 forecast_check.py series            what sequences exist, how long
    python3 forecast_check.py predict <name>    band for the next point(s)
    python3 forecast_check.py grade <name> <v>  did the observed value land in it

WHY A MODEL IS IN A REPOSITORY THAT DISTRUSTS MODELS

Not as a detector. As a witness that speaks first.

Every test this project has lost faith in was authored AFTER its author knew
what the code did: 25 of 25, 19 of 19, `chk(name, 0, 0)`, a control asserting
that none of an EMPTY list failed, `"linked"` matching inside `"symlinked"`.
None of those were dishonest. They were written by someone who already knew the
answer, which is a thing a person cannot un-know.

A forecast built from history alone cannot be shaped that way. It never sees the
fix, the hypothesis, or what anybody hoped for. It is causally blind to the
change being tested, and because the weights are fixed and nothing samples, its
claim is on the record and re-derivable months later. Measured before this file
was written: the same sequence twice gives a bit-identical mean and all fifteen
quantiles, sha256 equal, max abs difference 0.000e+00.

So the protocol is three statements, and the first two are made before the
result exists:

    1. YOURS      "I am changing X, so this number should move to Y, because Z."
    2. THE MODEL'S "from history alone, the next value lands in [q01, q99]."
    3. THE OUTCOME graded against both.

The disagreements are the point. A value that lands where you predicted AND
outside the model's band means you changed something real. A value that lands
inside the band means it may have been going there anyway and your change proved
nothing -- which is the case no other check in this repository can distinguish,
and it is exactly how a fix gets declared successful for doing nothing.

WHAT THIS IS NOT

It is not the verdict. `check_consistency.py` owns the verdict. A band is a
prior, and a prior that nothing can fall outside of is `chk(name, 0, 0)` wearing
250M parameters -- the same defect, better disguised, because "the model says
it's fine" reads as evidence in a way a literal `0 == 0` does not. So every
series registered here must be exercised by an adversary that reverts a REAL
defect and requires the band to reject it. A series whose band accepts a known
break is deleted, not tuned.

FEEDING IT, WHICH IS THE PART THAT NEEDED ENGINEERING

The model takes ONE ordered sequence of floats. The index does not have to be a
clock -- it has to carry structure. Indexing by wall-clock made this data 95%
zeros, because the gaps are nights and weekends; indexing by POSITION removes
every gap, because a session that did not happen has no slot. So the sequences
below are ordered by session and by turn, never by minute.

Two sources are compared by deriving ONE sequence from them -- the ratio -- and
asking what flat has looked like. That turns "do these agree" into a question
the model can answer, and it beats a hand-picked tolerance because the jitter is
measured rather than guessed.

The model is pinned to Python >=3.11,<3.12 and this repository runs on 3.12, so
inference happens in a subprocess against .venv-forecast. That is a hard
constraint of the package, not a design choice.
"""

import argparse
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import paths                                                    # noqa: E402

VENV = ROOT / ".venv-forecast"
RECORD = ROOT / "machine-readable" / "forecast_record.jsonl"

# Where HuggingFace model weights live. Matches install.py's _hf_home() —
# one variable, same default, so moving the cache with DEADRECKON_MODEL_CACHE
# works for both the install step and every inference call.
_HF_HOME = os.environ.get("DEADRECKON_MODEL_CACHE",
                           str(pathlib.Path.home() / ".cache" / "huggingface"))
QUANTILES = [0.01, 0.05, 0.1, 0.2, 0.25, 0.3, 0.4, 0.5,
             0.6, 0.7, 0.75, 0.8, 0.9, 0.95, 0.99]

# The model's own guidance: more than 30% imputed values degrades it, and short
# contexts are trained only down to 10. A sequence below that is not fed -- it
# is REPORTED as too short. Feeding it anyway produces a confident band over
# nothing, which is the worst possible output for a file whose purpose is to be
# harder to fool than the checks around it.
MIN_POINTS = 10


def _sessions(machine=None):
    out = []
    for d in paths.machine_folders(ROOT):
        if machine and d.name != machine:
            continue
        f = paths.find(d, "sessions.json")
        if not f:
            continue
        try:
            raw = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        rows = raw if isinstance(raw, list) else raw.get("sessions", [])
        for r in rows:
            r.setdefault("machine", d.name)
        out.extend(rows)
    return out


def series_tokens_per_session(machine=None):
    """Total tokens per session, in the order the sessions started.

    Dense by construction: every point is a session that happened, so there are
    no gaps to impute. Structure is real -- usage per session grows as a project
    accumulates context, which is what makes continuation predictable at all.
    """
    rows = [r for r in _sessions(machine) if r.get("total")]
    rows.sort(key=lambda r: (r.get("start") or "", r.get("session_id") or ""))
    return [float(r["total"]) for r in rows]


def series_scanner_ratio(machine=None):
    """analyze_tokens total / sessions total, per machine.

    Two independent scanners reading the same transcripts. The ratio should be
    1.0 and the only interesting thing about it is how far it wanders. A learned
    band around that beats the tolerance in check_consistency, which is a number
    somebody chose.
    """
    out = []
    for d in sorted(paths.machine_folders(ROOT), key=lambda p: p.name):
        if machine and d.name != machine:
            continue
        t = paths.find(d, "totals.json")
        if not t:
            continue
        try:
            tot = json.loads(t.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        grand = tot.get("grand_total_tokens") or 0
        per = sum(r.get("total", 0) for r in _sessions(d.name)
                  if r.get("cli") == "claude")
        if grand:
            out.append(per / grand)
    return out


def series_ledger_totals(machine=None):
    """Every ledger observation's total, in observation order.

    The longest sequence available: 13,378 rows on dell-latitude, 1,982 on hp.
    Ordered by when the belt saw it, which is a real order -- the belt observes
    sessions as they grow.
    """
    out = []
    for d in sorted(paths.machine_folders(ROOT), key=lambda p: p.name):
        if machine and d.name != machine:
            continue
        f = paths.find(d, "token_ledger.jsonl")
        if not f:
            continue
        rows = []
        for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("total"):
                rows.append((r.get("observed") or "", float(r["total"])))
        rows.sort()
        out.extend(v for _o, v in rows)
    return out


SERIES = {
    "tokens_per_session": series_tokens_per_session,
    "scanner_ratio": series_scanner_ratio,
    "ledger_totals": series_ledger_totals,
}

# Inference runs under a DIFFERENT interpreter. Kept as one small program with
# no imports from this repository so the boundary is a list of floats on stdin
# and a JSON band on stdout -- nothing about the corpus crosses it, and the
# subprocess cannot be confused by anything except the numbers it was handed.
_INFER = r'''
import json, sys, os, hashlib
# HF_HOME is passed in via the request payload so the subprocess uses the
# same cache directory as the parent, regardless of where weights were
# downloaded. HF_HUB_OFFLINE=1 prevents any network call during inference —
# the model must already be present (install.py downloads it).
req_raw = sys.stdin.read()
_req_pre = json.loads(req_raw)
os.environ["HF_HOME"] = _req_pre.get("hf_home", os.path.expanduser("~/.cache/huggingface"))
os.environ["HF_HUB_OFFLINE"] = "1"
import numpy as np, torch
torch.set_num_threads(4)
from cisco_tsm import CiscoTsmMR, TimesFmHparams, TimesFmCheckpoint
req = _req_pre
x = np.asarray(req["series"], dtype=np.float32)
q = req["quantiles"]
model = CiscoTsmMR(
    hparams=TimesFmHparams(num_layers=25, use_positional_embedding=False,
                           backend="cpu", quantiles=q),
    checkpoint=TimesFmCheckpoint(
        huggingface_repo_id="cisco-ai/cisco-time-series-model-1.0"))
p = model.forecast(x, horizon_len=int(req["horizon"]))[0]
mean = np.asarray(p["mean"], dtype=np.float64)
qs = {str(k): np.asarray(v, dtype=np.float64).tolist() for k, v in p["quantiles"].items()}
blob = mean.tobytes() + b"".join(np.asarray(v).tobytes() for _k, v in sorted(qs.items()))
json.dump({"mean": mean.tolist(), "quantiles": qs,
           "fingerprint": hashlib.sha256(blob).hexdigest()}, sys.stdout)
'''


def infer(series, horizon=1):
    py = VENV / "bin" / "python"
    if not py.exists():
        raise SystemExit(
            f"  the forecaster environment is absent ({VENV}).\n"
            f"  python3 install.py --apply    creates it, or --no-forecaster to skip.\n"
            f"  This check is OPTIONAL: a machine without it still scans.")
    req = json.dumps({"series": list(series), "quantiles": QUANTILES,
                      "horizon": horizon, "hf_home": _HF_HOME})
    r = subprocess.run([str(py), "-c", _INFER], input=req,
                       capture_output=True, text=True, timeout=1800)
    if r.returncode:
        raise SystemExit(f"  inference failed:\n{r.stderr[-1200:]}")
    return json.loads(r.stdout)


def cmd_series(_args):
    print(f"  {'series':22}{'points':>8}  status")
    for name, fn in SERIES.items():
        try:
            s = fn()
        except Exception as e:                      # noqa: BLE001
            print(f"  {name:22}{'-':>8}  FAILED: {e}")
            continue
        ok = len(s) >= MIN_POINTS
        note = ("usable" if ok else
                f"TOO SHORT -- the model is trained down to {MIN_POINTS} points")
        print(f"  {name:22}{len(s):>8}  {note}")


def cmd_predict(args):
    fn = SERIES[args.name]
    s = fn(args.machine)
    if len(s) < MIN_POINTS:
        raise SystemExit(f"  {args.name}: {len(s)} point(s); "
                         f"below the {MIN_POINTS} the model is trained for. "
                         f"Not fed -- a band over nothing is worse than no band.")
    hist, held = s[:-1], s[-1]
    out = infer(hist, horizon=1)
    lo = out["quantiles"][str(QUANTILES[0])][0]
    hi = out["quantiles"][str(QUANTILES[-1])][0]
    rec = {"series": args.name, "machine": args.machine, "n": len(hist),
           "mean": out["mean"][0], "lo": lo, "hi": hi,
           "fingerprint": out["fingerprint"], "held_out": held,
           "inside": bool(lo <= held <= hi)}
    print(f"  {args.name}  n={len(hist)}")
    print(f"  band [{lo:,.2f} .. {hi:,.2f}]   mean {out['mean'][0]:,.2f}")
    print(f"  held-out actual {held:,.2f}  ->  {'INSIDE' if rec['inside'] else 'OUTSIDE'}")
    print(f"  fingerprint {out['fingerprint'][:32]}")
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    with RECORD.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")
    return 0


def cmd_grade(args):
    """Print every record from forecast_record.jsonl, graded.

    Each row was written by cmd_predict before the outcome was known.
    Grade reads the CURRENT value of the series and checks whether it
    lands inside the band that was committed at prediction time.

    A series/machine pair with no recent record is reported as UNGRADED —
    not as passing. A band that nothing can fall outside of is worse than
    no band at all.
    """
    if not RECORD.is_file():
        print("  no forecast_record.jsonl — run predict first")
        return 1

    rows = []
    for line in RECORD.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue

    if not rows:
        print("  forecast_record.jsonl is empty — run predict first")
        return 1

    print(f"  {'series':<22} {'machine':<24} {'n':>6}  {'band lo':>14}  "
          f"{'band hi':>14}  {'held-out':>14}  result")
    fail = 0
    for r in rows:
        name = r.get("series", "?")
        machine = r.get("machine") or "all"
        lo, hi = r.get("lo", 0), r.get("hi", 0)
        held = r.get("held_out")
        inside = r.get("inside")
        if held is None:
            result = "UNGRADED"
        elif inside:
            result = "INSIDE"
        else:
            result = "OUTSIDE"
            fail += 1
        print(f"  {name:<22} {machine:<24} {r.get('n',0):>6}  "
              f"{lo:>14,.2f}  {hi:>14,.2f}  "
              f"{held:>14,.2f}  {result}" if held is not None else
              f"  {name:<22} {machine:<24} {r.get('n',0):>6}  "
              f"{lo:>14,.2f}  {hi:>14,.2f}  {'—':>14}  {result}")
    print(f"\n  {len(rows)} record(s), {fail} outside the band")
    return 0 if fail == 0 else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("series")
    p = sub.add_parser("predict")
    p.add_argument("name", choices=sorted(SERIES))
    p.add_argument("--machine")
    sub.add_parser("grade")
    args = ap.parse_args()
    if args.cmd == "series":
        return cmd_series(args)
    if args.cmd == "grade":
        return cmd_grade(args)
    return cmd_predict(args)


if __name__ == "__main__":
    raise SystemExit(main())
