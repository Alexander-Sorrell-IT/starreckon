#!/usr/bin/env python3
"""Find deadreckon-count data on this machine that the scanners do not read.

    python3 sweep_usage.py            # report
    python3 sweep_usage.py --json     # machine-readable

WHY THIS EXISTS

sessions.py and analyze_tokens.py look where they already know to look. Asking
them what exists can only ever confirm what they already read — a CLI nobody
wrote a reader for is invisible, and its absence looks exactly like a zero.

So this searches by CONTENT. It opens candidate files anywhere under $HOME and
asks whether they carry usage data, then reports which of those NO reader claims.

WHY IT REQUIRES A NUMBER, NOT A FIELD NAME

The first version matched field names and was wrong three times in one session:

  .gemini/extensions      404 MB      matched `input_tokens` — in gemini's own
                                      SOURCE CODE
  .config/google-chrome    29 MB      matched `total_tokens` — in a MetaMask
                                      locale file
  .clawspring              85 files   matched nothing real: an event log of
                                      session_id/end_reason/timestamp

Each was reported as uncounted usage data. None of it was. A tool's source names
the fields it parses, so the name alone proves nothing — the value does. This
matches `"field": <digits>` and sums what it finds, so a hit is a claim about
tokens rather than about vocabulary.

WHAT A FINDING MEANS

A directory listed under NOT COVERED with a non-zero total is usage this machine
performed and no report counts. That is the only kind of hit worth acting on;
everything else is noise, and this prints the totals so the difference is visible
rather than asserted.
"""
import argparse
import json
import os
import re
import sys

HOME = os.path.expanduser("~")

# "field": 12345 — the NUMBER is what makes it evidence.
NUMERIC = re.compile(
    r'"(input_tokens|output_tokens|cache_read_input_tokens|'
    r'cache_creation_input_tokens|inputTokens|outputTokens|cachedReadTokens|'
    r'promptTokenCount|candidatesTokenCount|totalTokenCount|'
    r'cached_input_tokens|promptTokensCount|predictedTokensCount|'
    r'prompt_tokens|completion_tokens|total_tokens|tokensIn|tokensOut|'
    r'eval_count|prompt_eval_count)"\s*:\s*([0-9]+)')

# Everything a reader already claims. Anything under these is COVERED.
#
# The tool paths come from stores.py rather than being listed again here. They
# were listed again here, and in sessions.DETECT, and in
# retention_guard.OTHER_SOURCES — one fact in three files. A store added to
# stores.py now stops being reported by this sweep automatically, which is the
# behaviour you want: the sweep should flag what nothing claims, not what
# somebody forgot to copy into a third list.
COVERED = [
    # ~/.claude.json is the default profile's config. It carries lastModelUsage
    # and lastTotalCacheReadInputTokens — the MOST RECENT session's counters,
    # kept as scratch state. Those tokens are already in that session's
    # transcript, so treating this file as uncounted usage would double-count
    # the last conversation. Measured: 38,080,832 across inputTokens and
    # outputTokens, all of it a duplicate.
    ".claude.json",
    # The profile directories themselves. stores.py holds `.*claude*/projects`
    # because that is where the RECORDS are; the sweep claims the whole profile,
    # because todos/, plans/ and shell-snapshots/ beside it are also Claude's and
    # also already accounted for.
    ".claude", ".claude-alt", ".claude-alt-api", ".claude-it", ".my-claude",
    # The antigravity stores nest under one directory; claiming the parent
    # covers conversations/, brain/ and cache/ in one line.
    ".gemini/antigravity-cli",
    # `"claude" not in p`, NOT `startswith(".claude")`. This filter's job is to
    # let the hand-written profile list above win over the store map's narrower
    # `projects` path, and it did it by matching the FIRST CHARACTER — the same
    # assumption that made the store glob miss ~/.my-claude. Widening that glob
    # to `.*claude*/projects` slipped straight past this test.
    #
    # BE PRECISE ABOUT WHAT THIS FIXES, BECAUSE IT IS NOT covered()'s ANSWER.
    # Measured: covered() returns the same value for every path with the old
    # test and with this one, on this machine and on any other — the hand-
    # written profile list two lines up already claims every claude path, and
    # `.*claude*/projects` could not have claimed one anyway. covered() is
    # `rel == c or rel.startswith(c + "/")`, a LITERAL comparison, so a `c`
    # holding a glob metacharacter never equals a real path.
    #
    # What it fixes is COVERED's MEMBERSHIP, and that is worth a line of code
    # here for one reason: an entry in COVERED that can never match is a claim
    # this file makes and cannot keep. The sweep exists to say "no reader
    # claims this path"; a dead pattern sitting in the covered list reads to
    # the next person like the profiles are claimed, and the day the hand-
    # written list goes stale that misreading is what stops them looking. The
    # invariant is asserted — `no glob reaches sweep_usage's literal COVERED
    # test` in test_readers.py — so it fails loudly for ANY store path with a
    # `*`, not just this one.
] + [p for p in __import__("stores").covered_paths() if "claude" not in p]

# Not usage stores, and expensive to walk. Each exclusion is a measurement.
SKIP = {
    ".cache", ".npm", ".gradle", ".wine", ".zoom", ".git", "node_modules",
    "__pycache__", ".venv", "venv", "site-packages", ".rustup", ".cargo",
    ".pki", ".gnupg", ".ssh", ".mozilla", ".thunderbird", ".local/share/Trash",
    ".ai-logs-archive",      # hard links to files counted at their real path
    ".basilisk",             # 239,591 files / 26 GB workspace, not conversations
    "models",                # lmstudio's model weights
    ".creds-profile", ".creds-profile-ff", ".melius_browser_session",
    # This repository and its copies: the corpus is a redacted EXPORT of data
    # already counted at source. Counting it here would double every machine.
    "deadreckon-record", "deadreckon-count", "deadreckon-count", "corpus",
    "archive", "testing-archive", "dist",
    # DERIVED OUTPUT — reports ABOUT tokens, not records OF them.
    #
    # These are the second false-positive class, and it is subtler than the
    # first: a report naturally contains large token numbers, so requiring a
    # numeric value does not filter it out. Left in, they dominated the result —
    # starforge-submission and starforge-out/reports alone claimed 38,999,584,751
    # "uncounted" tokens that are simply this fleet's own totals, written down.
    ".starforge", "starforge-out", "starforge-out-dev", "starforge-submission",
    "reports", "snapshots",
    # Corpora built for the submission work. Measured by message.id: 25,092 of
    # 25,099 API calls in them are already counted at source. They are renamed
    # copies, not additional work.
    "standout_max", "standout_full", "standout_clean", "standout_sandbox",
}

HEAD_BYTES = 2_000_000
EXTS = (".json", ".jsonl", ".ndjson", ".log")


def covered(path):
    """Is this file inside a store some reader already counts?

    Both sides normalised to "/". COVERED comes from stores.py, where every
    path is written with forward slashes, and `rel` comes from os.path.relpath,
    which uses os.sep. On Linux they are the same character and this worked.
    On Windows `.config\\Code\\User\\...` was compared against
    `.config/Code/User/...` + "\\", so 9 of 11 stores read as UNCOVERED on
    every run — burying the one finding this file exists to surface. Noise
    rather than loss, but an alarm that is wrong every run is one people stop
    reading. The same idiom is already used at retention_guard.py:567.
    """
    rel = os.path.relpath(path, HOME).replace(os.sep, "/")
    return any(rel == c or rel.startswith(c + "/") for c in COVERED)


def sweep():
    hits = {}
    scanned = 0
    for base, dirs, files in os.walk(HOME, topdown=True):
        dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith(".Trash")]
        for f in files:
            if not f.endswith(EXTS):
                continue
            p = os.path.join(base, f)
            try:
                if os.path.getsize(p) == 0:
                    continue
                with open(p, "rb") as fh:
                    head = fh.read(HEAD_BYTES)
            except OSError:
                continue
            scanned += 1
            text = head.decode("utf-8", "replace")
            total = 0
            n = 0
            for m in NUMERIC.finditer(text):
                total += int(m.group(2))
                n += 1
            if not n:
                continue
            rel = os.path.relpath(p, HOME)
            parts = rel.split(os.sep)
            key = os.sep.join(parts[:2]) if len(parts) > 1 else parts[0]
            e = hits.setdefault(key, {"files": 0, "fields": 0, "tokens": 0,
                                      "covered": covered(p)})
            e["files"] += 1
            e["fields"] += n
            e["tokens"] += total
    return scanned, hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    scanned, hits = sweep()
    cov = {k: v for k, v in hits.items() if v["covered"]}
    unc = {k: v for k, v in hits.items() if not v["covered"]}

    if args.json:
        json.dump({"scanned": scanned, "covered": cov, "not_covered": unc},
                  sys.stdout, indent=1)
        print()
        return 0 if not unc else 1

    print(f"  scanned {scanned:,} files for NUMERIC token fields\n")
    print(f"  {'COVERED — a reader already counts these':<50}{'files':>7}{'tokens':>18}")
    for k, v in sorted(cov.items(), key=lambda kv: -kv[1]["tokens"])[:12]:
        print(f"    {k:<48}{v['files']:>7}{v['tokens']:>18,}")
    print()
    if not unc:
        print("  NOT COVERED — nothing. Every numeric token field on this")
        print("  machine sits in a path a reader already reads.")
        return 0
    print(f"  {'NOT COVERED — usage no report counts':<50}{'files':>7}{'tokens':>18}")
    tot = 0
    for k, v in sorted(unc.items(), key=lambda kv: -kv[1]["tokens"]):
        tot += v["tokens"]
        print(f"    {k:<48}{v['files']:>7}{v['tokens']:>18,}")
    print(f"\n  {tot:,} token(s) carried by files no reader claims.")
    print("  A large number here means a CLI needs a reader in sessions.py.")
    print("  A small one is usually a tool that logs events, not usage.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
