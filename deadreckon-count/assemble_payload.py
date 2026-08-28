#!/usr/bin/env python3
"""One payload carrying the whole fleet: full-run numbers, sliced-run writing.

    python3 assemble_payload.py --full capture --chunks cap-01 cap-02 cap-03 cap-04
    python3 assemble_payload.py ... --out assembled/payload.json

THE PROBLEM THIS SOLVES

A full-fleet run POSTs 4,019,936 bytes of which 99.7% is one telemetry row per
session — 16,800 rows at ~256 bytes each. standout's `capPayload` shrinks an
oversized payload by emptying `exchanges`, then `prompt_samples`, then
`conversation_samples`; the loop ends when there is nothing left to drop rather
than when the payload fits, and it never touches `sessions`. Result: every
prompt and every conversation deleted, still over the cap, and what survives is
counts with nothing to read.

Trimming the corpus would have "fixed" it by sending less. That is backwards —
the corpus exists because more data is the point.

WHAT THIS DOES INSTEAD

  numbers   from the FULL run. `all_time` already carries total_sessions,
            active_days, total_duration_hours and every token counter in about
            2,243 bytes. Those totals are computed over everything and do not
            depend on shipping the session rows, so nothing is lost by not
            shipping them all.

  writing   from the SLICED runs. Each quarter-corpus slice comes in around
            2.05 MB and fills every sample cap — 500 exchanges, 50 prompt
            samples, 160 conversation samples. Unioning across slices and then
            selecting means the samples are drawn from the whole corpus rather
            than from whichever quarter happened to run.

  sessions  as many rows as the remaining budget allows, most recent first,
            and the number dropped is REPORTED. Silently sending fewer is how
            the original bug read as success.

Every value here comes from a real run of the tool over real transcripts. This
assembles the tool's own output in the tool's own schema; it does not invent
fields or numbers.
"""

import argparse
import json
import pathlib

MAX_BODY_BYTES = 4_000_000
# The tool's own ceilings, observed maxed-out in a single slice.
CAPS = {"exchanges": 500, "prompt_samples": 50, "conversation_samples": 160}
TOOLS = ("claude_code", "cowork", "codex", "cursor")


def load_payload(capture):
    """The POST body from a capture directory (the biggest request in it)."""
    best = None
    for f in sorted(pathlib.Path(capture).glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("body") and (best is None or d.get("body_bytes", 0) > best[0]):
            best = (d.get("body_bytes", 0), d["body"])
    if best is None:
        raise SystemExit(f"no POST body found in {capture}")
    return best[1]


def key_of(item):
    """Stable identity for dedup across slices.

    Slices are disjoint by transcript, but a session split on a 15-minute gap
    can surface near-identical text, and the same sample arriving twice would
    spend cap on a duplicate.
    """
    if isinstance(item, dict):
        for k in ("id", "session_id", "prompt", "text", "content"):
            v = item.get(k)
            if isinstance(v, str) and v:
                return v[:400]
        return json.dumps(item, sort_keys=True)[:400]
    return str(item)[:400]


def gather_samples(chunk_payloads):
    """Union each sample list across slices, round-robin so no slice dominates."""
    per_tool = {}
    for payload in chunk_payloads:
        au = (payload.get("profile") or {}).get("ai_usage") or {}
        for tool in TOOLS:
            t = au.get(tool)
            if not isinstance(t, dict):
                continue
            for field in CAPS:
                vals = t.get(field)
                if isinstance(vals, list) and vals:
                    per_tool.setdefault(tool, {}).setdefault(field, []).append(vals)
    out, stats = {}, {}
    for tool, fields in per_tool.items():
        out[tool] = {}
        for field, lists in fields.items():
            merged, seen = [], set()
            collected = sum(len(x) for x in lists)
            # Round-robin: take one from each slice in turn, so a cap that
            # fills early is filled from ACROSS the corpus, not from slice 1.
            for i in range(max(len(x) for x in lists)):
                for lst in lists:
                    if i < len(lst):
                        k = key_of(lst[i])
                        if k not in seen:
                            seen.add(k)
                            merged.append(lst[i])
            out[tool][field] = merged[:CAPS[field]]
            # Report the dedup. conversation_samples collapse ~640 -> 40
            # because the same system prompt recurs across hundreds of
            # sessions and the samples are truncated to ~400 chars, so many
            # are byte-identical. Forty DISTINCT conversations carry more
            # than a hundred and sixty copies of four — but a 94% collapse
            # that nobody is told about is indistinguishable from a bug.
            stats[f"{tool}.{field}"] = (collected, len(merged), len(out[tool][field]))
    return out, stats


def assemble(full, chunks, out_path):
    base = load_payload(full)
    chunk_payloads = [load_payload(c) for c in chunks]

    profile = base.get("profile")
    if not isinstance(profile, dict):
        raise SystemExit("full capture has no 'profile' object")

    samples, dedup = gather_samples(chunk_payloads)
    au = profile.setdefault("ai_usage", {})

    report = []
    for tool, fields in samples.items():
        t = au.get(tool)
        if not isinstance(t, dict):
            continue
        for field, vals in fields.items():
            before = len(t.get(field) or [])
            t[field] = vals
            report.append((tool, field, before, len(vals)))

    # Sessions last: fill whatever budget is left, newest first.
    sessions = au.get("sessions")
    dropped = 0
    if isinstance(sessions, list) and sessions:
        def when(s):
            return (s or {}).get("month") or ""
        ordered = sorted(sessions, key=when, reverse=True)
        kept = ordered
        au["sessions"] = kept
        while len(json.dumps(base)) > MAX_BODY_BYTES and kept:
            # Halve rather than pop: 16,800 one-at-a-time re-serialisations of a
            # 4 MB document is minutes of work for the same answer.
            cut = max(1, len(kept) // 10)
            kept = kept[:-cut]
            dropped += cut
            au["sessions"] = kept

    size = len(json.dumps(base))
    out_path = pathlib.Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Written in docker/sink.js's capture envelope, not as a bare body, so the
    # gate reads an assembled payload exactly the way it reads a captured one.
    # One artifact shape, one verifier — an assembled payload that could not be
    # audited by the same tool would be an assembled payload nobody audits.
    out_path.write_text(json.dumps({
        "seq": 1,
        "method": "POST",
        "url": "/api/public/wrapped",
        "headers": {},
        "body_bytes": size,
        "body_is_json": True,
        "body": base,
        "_assembled_from": {"full": str(full), "chunks": [str(c) for c in chunks]},
    }, indent=1), encoding="utf-8")

    print(f"\n  full run      {len(json.dumps(load_payload(full))):>12,} bytes")
    for i, c in enumerate(chunks, 1):
        print(f"  slice {i}       {len(json.dumps(chunk_payloads[i-1])):>12,} bytes  ({c})")
    print(f"\n  samples restored from the slices"
          f"   (collected -> distinct -> kept at cap):")
    for tool, field, before, after in sorted(report):
        c, d, k = dedup.get(f"{tool}.{field}", (0, 0, 0))
        dup = c - d
        print(f"    {tool}.{field:24} {before:>4} -> {after:<5}"
              f"  [{c} collected, {dup} duplicate(s) dropped, {d} distinct]")
    if isinstance(sessions, list):
        print(f"\n  sessions      {len(sessions):,} available, "
              f"{len(au.get('sessions') or []):,} kept, {dropped:,} dropped for size")
    print(f"\n  assembled     {size:,} bytes of {MAX_BODY_BYTES:,} cap"
          f"   {'OK' if size <= MAX_BODY_BYTES else 'STILL OVER'}")
    print(f"  wrote         {out_path}")
    print(f"\n  audit it:  python3 verify_payload.py --capture {out_path.parent}")
    return size <= MAX_BODY_BYTES


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--full", required=True, help="capture dir of the full-corpus run")
    ap.add_argument("--chunks", nargs="+", required=True, help="capture dirs of the slices")
    ap.add_argument("--out", default="assembled/0001-POST-assembled.json")
    a = ap.parse_args()
    ok = assemble(a.full, a.chunks, a.out)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
