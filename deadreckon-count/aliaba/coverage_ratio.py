#!/usr/bin/env python3
"""What we COUNTED over what is ON DISK. It should be 1.0, and it is checkable.

    python3 coverage_ratio.py              this machine
    python3 coverage_ratio.py --json       machine-readable

WHY THIS EXISTS

Every check in this repository verifies that the parts sum to the whole they
were told to sum. None of them can notice that the whole is the wrong whole.
That is not a hypothetical failure -- it is the shape of most of the 45 findings:

    export reached 123 of 1,059 transcripts     "every conversation preserved"
    COVERAGE compared 5 machines against 1      "the gap"
    LIFETIME held 3 of 5 machines               "everything ever recorded"
    first-wins turned a 675-token session       into 110

Not one of those is a zero. They are partials, and a sum-check is blind to a
partial by construction, because the smaller number still adds up perfectly with
the other smaller numbers. `check_consistency` reported 38 checks, 0 failed over
a 26,700,000,000 token undercount for exactly this reason.

A ratio is not blind to it. Counted over present is 1.0 when nothing is missed
and 0.116 when the exporter reaches 123 of 1,059, and no history, threshold or
calibration is required to tell those apart.

THE ONE RULE THIS FILE MUST OBEY

The denominator is computed by an INDEPENDENT implementation. It does not import
sessions.py, it does not import analyze_tokens.py, it does not use stores.py to
find anything. That is the entire value: a second counter built from the
scanner's own parts would inherit the scanner's own defects and agree with it
enthusiastically while both were wrong. This repository has already produced
that exact artifact -- two scanners, one narrow glob copied into both, perfect
agreement, 936 of 1,059 transcripts invisible to the pair of them.

So the rules for the denominator are:

    walk EVERY directory that looks like a profile, by shape, not by a name
    list somebody maintains -- ~/.claude* misses ~/.my-claude, which holds 130
    files, and a store map can only contain the paths its author thought of

    recurse. The flat glob shipped in four files here and cost 936 transcripts;
    a denominator that repeats it would certify the numerator's own blindness

    count a message ONCE, by its own id, taking the LARGEST usage seen for it.
    Transcripts grow: the same message appears in a short early copy and a
    longer current one, and choosing first-seen loses the difference while
    summing both invents it

    a directory that cannot be read is COUNTED AND NAMED, never silently
    skipped. rglob walks past an unreadable directory without raising, which
    makes it byte-for-byte identical to an empty one -- the exact bug that has
    now appeared seven times here in four disguises

WHAT A LOW RATIO MEANS, AND WHAT IT DOES NOT

Below 1.0 means the scanner did not see something on disk. Above 1.0 means the
scanner counted something twice, or counted something this file cannot find.
Both are defects and neither is a threshold judgement -- which is why this needs
no model, no band, and no learned notion of normal. The correct value is known.
"""

import argparse
import json
import pathlib
import sys

HOME = pathlib.Path.home()

USAGE_FIELDS = ("input_tokens", "output_tokens",
                "cache_creation_input_tokens", "cache_read_input_tokens")


def profile_dirs():
    """Directories that ARE a profile, judged by shape.

    A profile is a directory containing projects/ full of .jsonl. That test
    finds ~/.my-claude, which no ~/.claude* glob reaches, and it finds the next
    one CLAUDE_CONFIG_DIR invents without anybody editing this file.
    """
    seen, out = set(), []
    for cand in list(HOME.glob(".*")) + list(HOME.glob("*")):
        try:
            if not cand.is_dir() or not (cand / "projects").is_dir():
                continue
        except OSError:
            continue
        r = cand.resolve()
        if r not in seen:
            seen.add(r)
            out.append(cand)
    return sorted(out)


def count_on_disk():
    """The denominator. Independent of every scanner in this repository."""
    largest = {}                 # message id -> largest usage total seen
    no_id = 0                    # rows carrying usage but no id, summed raw
    unreadable = []              # directories we could not enter, BY NAME
    files = rows = 0

    for prof in profile_dirs():
        stack = [prof / "projects"]
        while stack:
            d = stack.pop()
            try:
                entries = list(d.iterdir())
            except PermissionError as e:
                # NOT a skip. A directory that exists and cannot be read is a
                # different fact from a directory that is empty, and the whole
                # point of this file is that those two stop looking alike.
                unreadable.append(f"{d}: {e.strerror}")
                continue
            except OSError:
                continue
            for p in entries:
                try:
                    if p.is_dir():
                        stack.append(p)          # RECURSE. The flat glob cost 936.
                        continue
                    if p.suffix != ".jsonl":
                        continue
                except OSError:
                    continue
                files += 1
                try:
                    fh = p.open(encoding="utf-8", errors="replace")
                except OSError as e:
                    unreadable.append(f"{p}: {e.strerror}")
                    continue
                with fh:
                    for line in fh:
                        rows += 1
                        try:
                            rec = json.loads(line)
                        except ValueError:
                            continue
                        msg = rec.get("message")
                        if not isinstance(msg, dict):
                            continue
                        u = msg.get("usage")
                        if not isinstance(u, dict):
                            continue
                        tot = sum(int(u.get(k) or 0) for k in USAGE_FIELDS)
                        if not tot:
                            continue
                        mid = msg.get("id")
                        if mid:
                            # LARGEST, not first and not sum. A grown copy of
                            # the same message must replace the short one, and
                            # two copies of one message must not become two.
                            if tot > largest.get(mid, 0):
                                largest[mid] = tot
                        else:
                            no_id += tot
    return {"tokens": sum(largest.values()) + no_id,
            "messages": len(largest), "rows": rows, "files": files,
            "no_id_tokens": no_id, "unreadable": unreadable}


def counted_by_scanner(machine_dir):
    """The numerator: what this machine's own scan published."""
    for name in ("machine-readable/totals.json", "totals.json"):
        f = machine_dir / name
        if f.is_file():
            try:
                t = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            return t.get("grand_total_tokens"), t.get("generated_at")
    return None, None


def this_machine(root):
    import platform
    host = platform.node()
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        f = d / ".machine-id"
        if f.is_file():
            try:
                if json.loads(f.read_text(encoding="utf-8")).get("hostname") == host:
                    return d
            except (OSError, ValueError):
                pass
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    root = pathlib.Path(__file__).resolve().parent
    disk = count_on_disk()
    mine = this_machine(root)
    counted, when = counted_by_scanner(mine) if mine else (None, None)

    ratio = (counted / disk["tokens"]) if (counted and disk["tokens"]) else None
    out = {"machine": mine.name if mine else None,
           "counted": counted, "on_disk": disk["tokens"], "ratio": ratio,
           "scan_generated_at": when,
           "messages_on_disk": disk["messages"], "files": disk["files"],
           "rows": disk["rows"], "no_id_tokens": disk["no_id_tokens"],
           "unreadable": disk["unreadable"]}
    if args.json:
        print(json.dumps(out, indent=2))
        return 0

    print(f"\n  machine        {out['machine']}")
    print(f"  on disk        {disk['tokens']:>18,}   "
          f"({disk['messages']:,} messages, {disk['files']:,} files, {disk['rows']:,} rows)")
    if counted is None:
        print("  counted        -- no totals.json for this machine")
        print("\n  RATIO UNAVAILABLE -- that is not 1.0 and must not be read as 1.0.\n")
        return 1
    print(f"  counted        {counted:>18,}   (scan of {str(when)[:19]})")
    print(f"  RATIO          {ratio:>18.4f}")
    if disk["no_id_tokens"]:
        print(f"  ...of which    {disk['no_id_tokens']:,} came from rows with no message id")
    if disk["unreadable"]:
        # Printed before the verdict on purpose: a ratio computed over a
        # denominator that could not be fully read is not a ratio, it is a
        # lower bound wearing one.
        print(f"\n  {len(disk['unreadable'])} PATH(S) COULD NOT BE READ -- "
              f"the denominator is incomplete:")
        for u in disk["unreadable"][:8]:
            print(f"    {u}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
