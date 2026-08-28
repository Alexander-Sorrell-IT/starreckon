#!/usr/bin/env python3
"""Manual historical adjustments — recorded beside the measurement, never inside it.

PLAN-MERGED items 10.1-10.3.

WHY THIS EXISTS. Some usage is real and was never measured: a machine scanned
before the daemon existed, a CLI whose store was wiped, work done on a computer
that has since been reinstalled. The number is known to a human and provable to
nobody. Today there is no way to record it at all, so it either gets typed into
a report by hand — which makes every figure in that report unciteable — or it
stays lost.

THE ONE RULE. A manual entry may never move a measured total. `measured` is
what the scanners, the ledger and the vendor counters produced; `adjusted` is
`measured + manual`. Both are published, always, side by side, and a report that
shows one without the other is a bug this module's own tests fail on.

That separation is the entire design. It is why the entries live in their own
file rather than as rows in `token_ledger.jsonl`: a ledger row is an
OBSERVATION, and an observation nobody made must not sit in the same list as
ones that were. `_sources()` in token_ledger.py would reject these anyway — they
have no file, no byte count and no digest, because there is nothing to hash.

IMMUTABILITY. Each entry carries `id`, the sha256 of its own canonical content.
Editing any field changes the id, so a silent revision is not silent: `verify()`
recomputes every id and reports the ones that no longer match. Deleting an entry
is caught the same way, by the `prev` chain — each entry names the id before it,
so a removal leaves a gap that does not link up. Neither is prevented; both are
made loud. A file on disk can always be edited, and a design that pretends
otherwise is worse than one that notices.
"""

import argparse
import datetime
import hashlib
import json
import pathlib
import sys

FILE = "manual_adjustments.jsonl"

# The fields that ARE the entry. `id` is derived from exactly these, in this
# order, so the digest cannot drift as the file format grows: a field added
# later is not part of the identity of an entry written before it existed.
SIGNED = ("ts", "author", "machine", "cli", "tokens", "reason", "prev")


def _canonical(entry):
    """The bytes an id is taken over. Order fixed, separators fixed."""
    return json.dumps({k: entry.get(k) for k in SIGNED},
                      sort_keys=False, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def entry_id(entry):
    return hashlib.sha256(_canonical(entry)).hexdigest()


def path_for(mdir):
    """Adjustments live in the machine folder, beside the numbers they qualify."""
    return pathlib.Path(mdir) / FILE


def load(mdir):
    """Every entry, in file order. A malformed line is returned, not skipped.

    Skipping it would make a corrupted entry indistinguishable from one that
    was never written, which is the failure this repository names most often.
    """
    f = path_for(mdir)
    out = []
    if not f.is_file():
        return out
    for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as e:
            out.append({"_malformed": f"line {n}: {e}", "_raw": line[:120]})
    return out


def append(mdir, author, cli, tokens, reason, machine=None, when=None):
    """Add one entry. Append-only: the file is opened "a" and never rewritten."""
    if not author or not reason:
        raise ValueError("author and reason are required — an adjustment "
                         "nobody signed and nobody explained is a number "
                         "with no provenance, which is what this file exists "
                         "to prevent")
    if not isinstance(tokens, int) or isinstance(tokens, bool):
        raise ValueError("tokens must be an int")
    existing = load(mdir)
    prev = existing[-1].get("id") if existing else None
    e = {
        "ts": (when or datetime.datetime.now().astimezone()).isoformat(
            timespec="seconds"),
        "author": author,
        "machine": machine or pathlib.Path(mdir).name,
        "cli": cli,
        "tokens": tokens,
        "reason": reason,
        "prev": prev,
    }
    e["id"] = entry_id(e)
    f = path_for(mdir)
    f.parent.mkdir(parents=True, exist_ok=True)
    with f.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    return e


def verify(mdir):
    """Every way this file can have been tampered with, named.

    Returns a list of strings. Empty means: every entry hashes to its own id,
    and every entry points at the one before it.
    """
    problems = []
    entries = load(mdir)
    prev_id = None
    for i, e in enumerate(entries, 1):
        if "_malformed" in e:
            problems.append(f"entry {i}: {e['_malformed']}")
            prev_id = None          # chain is broken here; do not cascade
            continue
        got = e.get("id")
        want = entry_id(e)
        if got != want:
            problems.append(
                f"entry {i} ({e.get('ts', '?')}): id {str(got)[:12]}… does not "
                f"match its content ({want[:12]}…) — it was edited after it "
                "was written")
        if e.get("prev") != prev_id:
            problems.append(
                f"entry {i} ({e.get('ts', '?')}): prev points at "
                f"{str(e.get('prev'))[:12]}…, expected {str(prev_id)[:12]}… — "
                "an entry before it was removed or reordered")
        prev_id = got
    return problems


def totals(mdir):
    """{cli: tokens} from valid entries only, and the sum.

    Entries that FAIL verification are excluded from the total and reported, so
    a tampered file cannot quietly change a published figure — it makes the
    figure smaller and says why, rather than larger and silently.
    """
    bad = set()
    for p in verify(mdir):
        try:
            bad.add(int(p.split()[1]))
        except (IndexError, ValueError):
            pass
    per, total = {}, 0
    for i, e in enumerate(load(mdir), 1):
        if i in bad or "_malformed" in e:
            continue
        n = e.get("tokens") or 0
        per[e.get("cli") or "unknown"] = per.get(e.get("cli") or "unknown", 0) + n
        total += n
    return per, total


def main():
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        epilog="A manual entry never moves a measured total. Reports publish\n"
               "`measured` and `adjusted` side by side, always.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("machine", help="machine folder these adjustments belong to")
    ap.add_argument("--add", action="store_true", help="append an entry")
    ap.add_argument("--author"), ap.add_argument("--cli")
    ap.add_argument("--tokens", type=int), ap.add_argument("--reason")
    ap.add_argument("--verify", action="store_true",
                    help="recompute every id and check the chain")
    a = ap.parse_args()
    mdir = pathlib.Path(a.machine)

    if a.add:
        if not all([a.author, a.cli, a.tokens is not None, a.reason]):
            ap.error("--add needs --author, --cli, --tokens and --reason")
        e = append(mdir, a.author, a.cli, a.tokens, a.reason)
        print(f"  recorded {e['tokens']:,} for {e['cli']} — id {e['id'][:12]}…")
        return 0

    problems = verify(mdir)
    per, total = totals(mdir)
    print(f"  {len(load(mdir))} entry(s), {total:,} adjusted tokens")
    for cli, n in sorted(per.items(), key=lambda kv: -kv[1]):
        print(f"    {cli:14} {n:>16,}")
    if problems:
        print(f"\n  {len(problems)} PROBLEM(S):")
        for p in problems:
            print(f"    {p}")
        return 1
    print("\n  every entry hashes to its own id and the chain is unbroken")
    return 0


if __name__ == "__main__":
    sys.exit(main())
