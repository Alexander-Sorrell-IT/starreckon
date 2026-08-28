#!/usr/bin/env python3
"""Put each defect back, one at a time, and confirm test_fleet_merge.py goes RED.

A test that passes against reverted code proves nothing. Each entry below is
the ORIGINAL line, replanted in a throwaway copy; the suite must fail, and it
must fail on the checks named.
"""
import os, pathlib, re, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent

REVERTS = [
    ("empty corpus folder skipped like an absent one", [
        ("corpus_reports.py", "        if ses is None:", "        if not ses:")]),
    # ANCHOR REWRITTEN. The exclusion this revert attacks used to be triggered
    # by a reader_version stamp (`stale = bool(cc) and ver != now_ver`), and
    # corpus_reports.py no longer works that way: it counts the transcripts
    # itself, so a leftover stamp says nothing about comparability. The line
    # that decides it now is the `unread` branch, and the defect is the same
    # one — the machine leaves the corpus column and stays in the scanned one,
    # which invents a gap the size of the machine.
    ("COVERAGE guard on one side only (ts += sc unconditional)", [
        ("corpus_reports.py",
         "        if mdir.name in corpus_dirs and mdir.name not in held:\n"
         "            unread.append(mdir.name)",
         "        if mdir.name in corpus_dirs and mdir.name not in held:\n"
         "            ts += sc\n"
         "            unread.append(mdir.name)")]),
    ("'never exported' said for a folder that WAS exported and is empty", [
        ("corpus_reports.py",
         '        if mdir.name not in corpus_dirs:\n'
         '            why = "**never exported — no folder in the corpus**"\n'
         '        elif cc == 0:\n'
         '            why = "**exported, holds nothing**"',
         '        if cc == 0:\n'
         '            why = "**never exported**"\n'
         '        elif False:\n'
         '            why = "**exported, holds nothing**"')]),
    ("a machine gone from the scans drops out of COVERAGE", [
        ("corpus_reports.py", "    for name in sorted(corpus_dirs - counted):",
         "    for name in ():")]),
    ("a roster machine in neither tree is not reported", [
        ("corpus_reports.py", "    for name in never:", "    for name in ():")]),
    ("combine.py adds two folders that are one computer", [
        ("combine.py", "    if dupes:", "    if False:")]),
    # ANCHOR REWRITTEN. `machines partition the grand total` no longer exists
    # under that name: the fleet total is now re-added from by_account.csv, a
    # second artifact written by a second writer, precisely so the check cannot
    # compare the sum with itself again. The revert restores the shape of the
    # original defect — a fleet check whose two sides are the same expression —
    # on the check that replaced it.
    ("'the fleet total re-adds from a second artifact' compares a value with itself", [
        ("check_consistency.py",
         'chk("the fleet total re-adds from a second artifact", csv_sum, csv_json,',
         'chk("the fleet total re-adds from a second artifact", csv_json, csv_json,'),
        ("check_consistency.py",
         'chk("no two folders claim the same computer", len(twice), 0,',
         'chk("no two folders claim the same computer", 0, 0,')]),
    ("no cross-machine session-id check", [
        ("check_consistency.py",
         'chk("no session id appears on two computers", len(shared), 0,',
         'chk("no session id appears on two computers", 0, 0,')]),
    ("count_corpus drops a corpus folder with no MANIFEST", [
        ("count_corpus.py", "    skipped = sorted(d.name for d in present",
         "    skipped = [] and sorted(d.name for d in present")]),
]


FLEET = "test_fleet_merge.py"
# Reverts whose defect is not fleet arithmetic. Only the exceptions are listed,
# so adding a revert without thinking about it still gets a suite rather than
# an exemption.
SUITE = {
    "'the fleet total re-adds from a second artifact' compares a value with "
    "itself": "adv_published_gate.py",
}


def sandbox():
    d = pathlib.Path(tempfile.mkdtemp(prefix="revert-"))
    for f in ROOT.iterdir():
        if f.suffix == ".py" or f.name in ("machines.json", "accounts.json"):
            shutil.copy2(f, d / f.name)
    return d


bad = []
for name, plants in REVERTS:
    d = sandbox()
    try:
        for fn, old, new in plants:
            p = d / fn
            s = p.read_text(encoding="utf-8")
            if old not in s:
                print(f"  ANCHOR MISSING  {name}: {fn}\n    {old!r}")
                bad.append(name)
                break
            p.write_text(s.replace(old, new, 1), encoding="utf-8")
        else:
            # THE SUITE THAT OWNS THE DEFECT, NOT ALWAYS THE SAME ONE.
            #
            # Every revert used to be run against test_fleet_merge.py, which
            # is right for the eight that are about fleet arithmetic and wrong
            # for the one that is about the publication gate corroborating
            # itself. That one came out GREEN, and a GREEN here reads as "no
            # suite would catch this" when the truth was "the wrong suite was
            # asked" — adv_gate_git_blind.py and adv_published_gate.py both go
            # red on it, measured. A revert whose suite is not named still
            # defaults to the fleet suite, so nothing is silently exempted.
            r = subprocess.run([sys.executable, SUITE.get(name, FLEET)], cwd=d,
                               capture_output=True, text=True, timeout=900)
            fails = [l.strip()[6:] for l in r.stdout.splitlines()
                     if l.startswith("  FAIL  ")]
            tally = ([l for l in r.stdout.splitlines() if "checks," in l]
                     or ["no summary"])[-1].strip()
            ok = r.returncode != 0 and fails
            print(f"  {'RED  ' if ok else 'GREEN'}  {name}")
            print(f"          exit {r.returncode}, {tally}")
            for f in fails:
                print(f"          - {f}")
            if not ok:
                bad.append(name)
                print("          " + r.stdout[-500:])
    finally:
        shutil.rmtree(d, ignore_errors=True)

print(f"\n  {len(REVERTS)} reverts, {len(bad)} the suite did NOT catch"
      + (f": {bad}" if bad else ""))
raise SystemExit(1 if bad else 0)
