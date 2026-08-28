#!/usr/bin/env python3
"""Re-run the current redactor over a corpus that was exported by an older one.

    python3 scrub_corpus.py --dry-run        # what it would change
    python3 scrub_corpus.py --yes            # change it

An export is only as good as the rules in force the day it ran. When a rule is
tightened — and two were, after `merge_corpus.py` refused a merge — every corpus
produced before that day still carries what the old rule missed. Waiting for
each machine to re-export leaves the gap open for as long as that takes, and the
machine that produced it may not be reachable today.

This applies the current rules to an existing corpus in place, and reports
exactly what changed and where.

WHY THIS IS NOT IN merge_corpus.py

merge_corpus deliberately does not re-redact: doing it silently there would mask
an export that had skipped redaction entirely, and the merge would look clean
while the machine's own copy stayed dirty. This is the explicit version — run on
purpose, on a named tree, printing what it touched. The difference is that a
silent fix hides a broken exporter, and a loud one does not.

WHAT IT CANNOT DO

Git history. Rewriting a file does not remove what previous commits still hold;
that needs the history rewritten and every clone re-fetched. If a credential
reached a repository, rotating it is the fix and this is only cleanup.
"""

import argparse
import json
import pathlib
import sys
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from export_corpus import Redactor, SPANS, EMAIL      # the CURRENT rules
import merge_corpus                                   # the CURRENT checker


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(pathlib.Path.home() / "deadreckon-record"))
    ap.add_argument("--home", default=str(pathlib.Path.home()))
    ap.add_argument("--keep-email", default="alexander.sorrell.it@gmail.com")
    ap.add_argument("--yes", action="store_true", help="write; default is a dry run")
    ap.add_argument("--dry-run", action="store_true", help="explicit no-op default")
    args = ap.parse_args()
    dry = not args.yes

    corpus = pathlib.Path(args.corpus)
    machines = sorted(d for d in corpus.iterdir()
                      if (d / ".claude" / "projects").is_dir())
    if not machines:
        raise SystemExit(f"no machine folders under {corpus}")

    print(f"{'DRY RUN' if dry else 'SCRUBBING'}  {len(machines)} machine(s)  "
          f"({len(SPANS)} span rules)\n")

    # Find the files worth opening before opening them. Re-redacting every file
    # took longer than the 10 minutes it was given, on 18,037 files of which
    # exactly 3 contained anything — the work is all in the 99.98% that are
    # already clean. A raw-text pass over the bytes is cheap and only has to be
    # over-inclusive: a false positive costs one file being rewritten
    # identically, which is free, while a false negative would miss a leak. So
    # the filter runs the checker's own patterns against the undecoded text,
    # which matches strictly more than the decoded scan the verifier uses.
    def candidates(tree):
        # merge_corpus.LEAK has no email rule — its scan_leaks() even takes a
        # `keep` allowlist it never consults, which is the fingerprint of the
        # omission. export_corpus DOES strip third-party emails, so a file
        # whose only leak was an address matched nothing here, was never
        # opened, and was never re-redacted: this script reported `clean` on a
        # corpus holding a real one. The filter is documented directly above as
        # safe to be over-inclusive — a false positive rewrites a file
        # identically, for free — while a false negative is the failure a
        # filter in front of a security check must not have. So the redactor's
        # own EMAIL joins the checker's patterns.
        pats = list(merge_corpus.LEAK.values()) + [EMAIL]
        for f in sorted(tree.rglob("*.jsonl")):
            try:
                blob = f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            # Test the raw bytes AND the same text with JSON's doubled
            # backslashes collapsed. `D:\Users\x` is stored as `D:\\Users\\x`,
            # so the pattern the checker uses never matches the raw form — the
            # first version of this filter reported two machines clean that the
            # verifier had already flagged, which is the exact failure a filter
            # in front of a security check must not have. Collapsing is cheaper
            # than decoding every line and cannot miss what decoding would find.
            if any(p.search(blob) for p in pats):
                yield f
                continue
            if "\\\\" in blob:
                flat = blob.replace("\\\\", "\\")
                if any(p.search(flat) for p in pats):
                    yield f

    grand = Counter()
    for m in machines:
        red = Redactor(pathlib.Path(args.home), args.keep_email)
        changed_files = 0
        before = Counter()
        after = Counter()
        for f in candidates(m / ".claude" / "projects"):
            out, dirty = [], False
            for line in f.open(encoding="utf-8", errors="ignore"):
                line = line.rstrip("\n")
                if not line:
                    continue
                try:
                    o = json.loads(line)
                except Exception:
                    out.append(line)
                    continue
                # Count what the CHECKER sees, before and after re-redacting.
                merge_corpus.scan_leaks(o, before, args.keep_email)
                new = red.walk(o)
                merge_corpus.scan_leaks(new, after, args.keep_email)
                s = json.dumps(new, ensure_ascii=False)
                if s != line:
                    dirty = True
                out.append(s)
            if dirty:
                changed_files += 1
                if not dry:
                    f.write_text("\n".join(out) + "\n", encoding="utf-8")

        fixed = {k: before[k] - after.get(k, 0) for k in before if before[k]}
        left = {k: v for k, v in after.items() if v}
        grand.update(before)
        status = "clean" if not before else \
                 (", ".join(f"{k} -{v}" for k, v in fixed.items()) or "no change")
        print(f"  {m.name:30} files touched {changed_files:>5}   {status}")
        if left:
            print(f"  {'':30} STILL FLAGGED: {left}")

    print()
    if not grand:
        print("  nothing the current rules would remove — this corpus is already current")
    elif dry:
        print("  re-run with --yes to write.  Rotating anything that reached a")
        print("  repository is still required: this cleans the files, not the history.")
    else:
        print("  written. Git history still holds the old content — rotate, do not")
        print("  rely on this having removed it from previous commits.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
