#!/usr/bin/env python3
"""Split the merged corpus into slices the profile tool can actually digest.

    python3 chunk_corpus.py --merged merged --out chunks --chunks 4

WHY SLICE AT ALL — IT IS NOT ABOUT MAKING THE CORPUS SMALLER

A full-fleet run produces a 4,019,936-byte payload of which **99.7% is one
telemetry row per session** — 16,800 rows at ~256 bytes. standout's
`capPayload` shrinks an oversized payload by emptying `exchanges`, then
`prompt_samples`, then `conversation_samples`, and its loop stops when there is
nothing left to drop rather than when the payload fits. It never touches
`sessions`. So on this fleet it deleted every prompt and every conversation —
the only qualitative content, and the only part a human at the other end reads
— and was STILL over the cap.

Slicing does not throw anything away. Each slice is small enough that the
samples survive, and the totals do not come from the slices at all: `all_time`
in a full-corpus run already carries total_sessions, active_days,
total_duration_hours and every token counter in about 2,243 bytes. Session rows
are raw detail duplicating an aggregate that is already computed.

So the pipeline is: full run for the NUMBERS, sliced runs for the WRITING.

WHY IT SPLITS WITHIN A PROJECT

One project holds 81.1% of the transcripts (16,402 of 20,217). Slicing
per-project would produce one slice as oversized as the original and 400 empty
ones. Files are distributed individually and the `projects/<dir>/<file>.jsonl`
shape is preserved inside every slice, because the tool reads exactly two
levels and silently finds nothing if the depth is wrong.

Hardlinks, not copies: the corpus is 4 GB and the slices are read-only inputs.
"""

import argparse
import json
import os
import pathlib
import shutil


def slices(merged, out, n):
    src = pathlib.Path(merged) / ".claude" / "projects"
    if not src.is_dir():
        raise SystemExit(f"no corpus at {src}")

    files = []
    for proj in sorted(p for p in src.iterdir() if p.is_dir()):
        for f in sorted(proj.glob("*.jsonl")):
            files.append((proj.name, f, f.stat().st_size))
    if not files:
        raise SystemExit(f"no transcripts under {src}")

    # Biggest first into the currently-lightest bin. Round-robin would balance
    # the COUNT while leaving one slice carrying every large session, and it is
    # bytes that decide whether the samples survive.
    files.sort(key=lambda r: -r[2])
    bins = [{"files": [], "bytes": 0} for _ in range(n)]
    for proj, f, size in files:
        b = min(bins, key=lambda x: x["bytes"])
        b["files"].append((proj, f))
        b["bytes"] += size

    out = pathlib.Path(out)
    if out.exists():
        shutil.rmtree(out)          # regenerate, never overwrite in place
    manifest = []
    for i, b in enumerate(bins, 1):
        root = out / f"chunk-{i:02d}" / ".claude" / "projects"
        for proj, f in b["files"]:
            d = root / proj
            d.mkdir(parents=True, exist_ok=True)
            dst = d / f.name
            try:
                os.link(f, dst)
            except OSError:
                shutil.copy2(f, dst)   # different filesystem
        projects = len(list(root.iterdir())) if root.is_dir() else 0
        manifest.append({"chunk": f"chunk-{i:02d}", "transcripts": len(b["files"]),
                         "bytes": b["bytes"], "projects": projects})
        print(f"  chunk-{i:02d}   {len(b['files']):>7,} transcripts"
              f"   {b['bytes']/1e6:>9.1f} MB   {projects:>4} projects")

    (out / "CHUNKS.json").write_text(json.dumps({
        "source": str(pathlib.Path(merged).resolve()),
        "chunks": manifest,
        "total_transcripts": len(files),
    }, indent=1), encoding="utf-8")
    print(f"\n  {len(files):,} transcripts over {n} slice(s) -> {out}")
    print("  each slice is a complete corpus root; mount one at a time:")
    print(f"    ./submit_gate.sh --merged {out}/chunk-01 --skip-vendor")
    return manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--merged", default="merged")
    ap.add_argument("--out", default="chunks")
    ap.add_argument("--chunks", type=int, default=4)
    a = ap.parse_args()
    if a.chunks < 1:
        raise SystemExit("--chunks must be >= 1")
    slices(a.merged, a.out, a.chunks)


if __name__ == "__main__":
    main()
