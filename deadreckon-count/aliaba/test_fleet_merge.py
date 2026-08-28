#!/usr/bin/env python3
"""Does a FIVE-machine fleet add up? Nobody had ever checked.

    python3 test_fleet_merge.py

Every machine-level check in this repository is internal to one machine, and
one machine is all that has ever run this code. `check_consistency.py` opened
with

    grand = sum(m["grand_total_tokens"] for m in machines)
    ...
    chk("machines partition the grand total",
        sum(m["grand_total_tokens"] for m in machines), grand)

— the same expression twice — so the one check whose NAME claims to test the
fleet total compared a value with itself and reported PASS forever.

This file works from `fleet_merge_fixture.py`: five machines whose totals are CHOSEN,
not measured, with disjoint digits so that a dropped, doubled or half-counted
machine names itself in the sum.

    alpha 1,000,000,000  bravo 200,000,000  charlie 30,000,000
    delta     4,000,000  echo       500,000        = 1,234,500,000

Every attack here was verified to go RED against the code as it stood before
the fix beside it. The full list is in the docstring of each one.
"""

import json
import os
import pathlib
import shutil
import subprocess
import sys

import paths

COVERAGE, ALL_COMPUTERS = "COVERAGE.md", "ALL-COMPUTERS.json"
SESSIONS, STATS = "sessions.json", "stats.json"

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import fleet_merge_fixture as fx                                   # noqa: E402
import sessions as sessions_mod                                    # noqa: E402

VER = sessions_mod.scanner_version()
TMP = pathlib.Path(os.environ.get("TMPDIR", "/tmp")) / f"test-fleet-{os.getpid()}"
PASS, FAIL = [], []


def check(name, got, want, why=""):
    (PASS if got == want else FAIL).append((name, got, want, why))


def build(tag, **kw):
    """A fleet, with THIS computer owning alpha — the real ownership rule.

    Without a .machine-id match, corpus_reports rewrites every machine's
    stats.json with the current reader version, which silently repairs the
    version skew these attacks are about.
    """
    import platform
    c, r = fx.build(TMP / tag, version=VER, **kw)
    for f in ROOT.iterdir():
        if f.suffix == ".py" and not (c / f.name).exists():
            os.symlink(f.resolve(), c / f.name)
    (c / "alpha" / ".machine-id").write_text(
        json.dumps({"hostname": platform.node(), "folder": "alpha"}),
        encoding="utf-8")
    return c, r


def run(root, script, *a):
    p = subprocess.run([sys.executable, str(pathlib.Path(root) / script), *a],
                       capture_output=True, text=True, cwd=str(root))
    return p.stdout + p.stderr, p.returncode


def cov_rows(record):
    """The COVERAGE table as [(computer, scanned, held, gap, why)]."""
    out = []
    for line in (pathlib.Path(record) / paths.HUMAN /
                 COVERAGE).read_text(encoding="utf-8").splitlines():
        if not line.startswith("| "):
            continue
        c = [x.strip() for x in line.strip("|").split("|")]
        if len(c) == 5 and c[0] not in ("computer",) and "---" not in c[1]:
            out.append(tuple(c))
    return out


def num(s):
    s = s.replace("*", "").replace(",", "").replace("+", "").strip()
    try:
        return int(s)
    except ValueError:
        return None


# --------------------------------------------------------------------------
# Q1 — the sum nobody had ever taken
# --------------------------------------------------------------------------
def t_five_machines_sum_exactly():
    """Both derivations, five machines, exact — not "within tolerance"."""
    c, r = build("q1")
    run(c, "combine.py")
    d = json.loads((c / paths.MACHINE / ALL_COMPUTERS)
                   .read_text(encoding="utf-8"))
    check("combine.py: five machines sum to the planted fleet total",
          d["grand_total_tokens"], fx.FLEET_TOTAL)
    check("combine.py: the machine rows sum to the total it published",
          sum(m["total"] for m in d["machines"]), d["grand_total_tokens"])
    o, _ = run(c, "corpus_reports.py", "--corpus", str(r))
    check("corpus_reports: five machines sum to the planted fleet total",
          f"{fx.FLEET_TOTAL:,} tokens" in o, True, o[-400:])


# --------------------------------------------------------------------------
# Q2 — the same computer in two folders
# --------------------------------------------------------------------------
def t_duplicate_folder_is_not_added_twice():
    """RED before the fix: grand 2,234,500,000 for a planted 1,234,500,000.

    A machine folder gets duplicated for ordinary reasons — a rename that left
    the old name (migrate_rename.py), a restore beside the live one. HEAD added
    both, printed two rows with one name, and check_consistency said
    `28 checks, 0 failed`.
    """
    c, r = build("q2")
    shutil.copytree(c / "alpha", c / "alpha-old")
    os.remove(c / "alpha-old" / paths.MACHINE / SESSIONS)
    o, rc = run(c, "combine.py")
    check("combine.py refuses a fleet with one computer in two folders",
          rc != 0, True, o[-300:])
    check("combine.py names both folders", "alpha-old" in o and "alpha" in o,
          True, o[-300:])
    check("combine.py wrote no total it could not justify",
          (c / paths.MACHINE / ALL_COMPUTERS).exists(), False)
    o, rc = run(c, "check_consistency.py")
    check("check_consistency fails on a doubled computer", rc, 1,
          [l for l in o.splitlines() if "checks," in l])
    check("check_consistency names the check", "no two folders claim the same "
          "computer" in o, True)


# --------------------------------------------------------------------------
# Q3 — a machine that disappears
# --------------------------------------------------------------------------
def t_a_machine_that_disappears_keeps_its_row():
    """RED before the fix: the row vanished and the gap went back to +0.

    `rm -rf charlie` in deadreckon-count took charlie out of COVERAGE entirely —
    numerator and denominator together — so the report that exists to say what
    is missing said everything reconciles, on a fleet that had just lost
    30,000,000 tokens.
    """
    c, r = build("q3")
    shutil.rmtree(c / "charlie")
    run(c, "corpus_reports.py", "--corpus", str(r))
    rows = {x[0]: x for x in cov_rows(r)}
    check("a machine present in the corpus and gone from the scans still has "
          "a COVERAGE row", "charlie" in rows, True, sorted(rows))
    check("and it is not reported as reconciling", "NOT SCANNED" in
          rows.get("charlie", ("", "", "", "", ""))[4], True)


def t_the_all_row_equals_the_sum_of_its_own_rows():
    """The invariant HEAD broke: a total that contradicts its own table.

    RED before the fix, two of five machines excluded:

        | charlie |    30,000,000 |    30,000,000 | +0 | **STALE** |
        | delta   |     4,000,000 |     4,000,000 | +0 | **STALE** |
        | **all** | 1,234,500,000 | 1,200,500,000 | **-34,000,000** |

    Every row +0, the total -34,000,000. `ts += sc` ran unconditionally and
    `tc += cc` was guarded, so a machine left one side of a comparison and not
    the other.

    Driven by `corpus_unread` for the reason spelled out in
    t_stale_machines_leave_both_sides: the exclusion this invariant is about is
    no longer triggered by a reader_version stamp, so a fixture that plants one
    no longer reaches the branch and the invariant holds for free.
    """
    c, r = build("q3b", corpus_unread=("charlie", "delta"))
    run(c, "corpus_reports.py", "--corpus", str(r))
    rows = cov_rows(r)
    body = [x for x in rows if not x[0].startswith("**all")]
    allr = [x for x in rows if x[0].startswith("**all")][0]
    for i, col in ((1, "scanned"), (2, "in this corpus")):
        check(f"the all row's `{col}` is the sum of the rows above it",
              num(allr[i]), sum(num(x[i]) or 0 for x in body
                                if num(x[i]) is not None and num(x[3]) is not None),
              [x[:3] + (x[3],) for x in rows])
    check("the fleet gap is the sum of the per-machine gaps",
          num(allr[3]), sum(num(x[3]) or 0 for x in body))


# --------------------------------------------------------------------------
# Q4 — a machine this run could not read
# --------------------------------------------------------------------------
def t_stale_machines_leave_both_sides():
    """2 of 5 unread, every real gap zero. The fleet gap must be zero too.

    RED before the fix: -34,000,000, exactly charlie + delta, presented as
    transcripts the corpus does not hold. On the real record's own metadata the
    same defect prints -16,482,383,637 against a true gap of -39,995,929.

    WHAT THIS ATTACK MEASURES, AND WHY THE FIXTURE MOVED.

    It was driven by `corpus_versions={"charlie": "older", ...}` — a
    reader_version stamp planted in the corpus's own stats.json — because the
    exclusion it attacks used to be triggered by VERSION SKEW. It is not any
    more, and it should not be: corpus_reports.py now counts the transcripts
    itself, in this process, in the same second, so a leftover stamp says
    nothing about whether the figure is comparable. Version skew stopped
    excluding anything, the attack stopped reaching the branch it was written
    for, and `no phantom gap` began passing because all five machines were
    comparable rather than because the guard held.

    The exclusion that exists now is the one that was always the real case: a
    corpus folder that is PRESENT and holds no transcripts in this checkout, so
    read_machine() returns None and this run computed nothing for it. That is
    dell-inspiron, whose leftover figure was entered into both totals as
    `-824,886`. So the fixture builds that state (`corpus_unread`) and all four
    assertions below are unchanged.

    UNREAD IS NOT EMPTY, and t_empty_machine_is_not_an_absent_machine holds the
    other side of it: a folder that was exported and came out empty IS a
    reading, of zero, and must stay in both columns.
    """
    c, r = build("q4", corpus_unread=("charlie", "delta"))
    o, _ = run(c, "corpus_reports.py", "--corpus", str(r))
    rows = {x[0]: x for x in cov_rows(r)}
    allr = rows["**all**"]
    check("no phantom gap when two machines could not be read", num(allr[3]), 0,
          [x for x in cov_rows(r)])
    check("the unread machines are excluded from the SCANNED column too",
          num(allr[1]), fx.FLEET_TOTAL - 30_000_000 - 4_000_000)
    check("their scanned tokens are reported rather than dropped",
          "34,000,000 scanned tokens are not represented" in
          (r / paths.HUMAN / COVERAGE).read_text(encoding="utf-8"),
          True)
    check("an unread row does not print a gap it cannot compute",
          rows["charlie"][3], "—")


# --------------------------------------------------------------------------
# Q5 — one session id, two computers
# --------------------------------------------------------------------------
def t_a_session_on_two_machines_is_reported():
    """RED before the fix: 27 checks, 0 failed, exit 0.

    combine.py asserts "Sessions on different computers are disjoint, so these
    add without any risk of double-counting" and nothing tested it. A synced
    home directory or a machine folder copied to seed another puts one
    conversation on two computers, and both derivations add it twice.
    """
    c, r = build("q5", shared_sid="SHARED-SESSION-0001")
    o, rc = run(c, "check_consistency.py")
    check("check_consistency fails when one session id is on two computers",
          rc, 1, [l for l in o.splitlines() if "checks," in l])
    check("it names the shared id", "SHARED-SESSION-0001" in o, True)
    check("it says how many tokens are counted twice",
          "720,000,000 tokens counted on more than one machine" in o, True,
          [l for l in o.splitlines() if "session id" in l])


def t_disjoint_sessions_do_not_trip_it():
    """And the check must be quiet on a fleet that is fine, or it is noise."""
    c, r = build("q5b")
    o, rc = run(c, "check_consistency.py")
    check("a healthy five-machine fleet passes check_consistency", rc, 0,
          [l for l in o.splitlines() if "checks," in l])


# --------------------------------------------------------------------------
# Q6 — count_corpus across five machines
# --------------------------------------------------------------------------
def t_count_corpus_reconciles_all_five():
    c, r = build("q6")
    o, rc = run(c, "count_corpus.py", "--corpus", str(r))
    check("count_corpus reconciles five machines at 0.00%",
          o.count("0.00% ok"), 5, o[-600:])
    check("count_corpus exits 0 on a clean fleet", rc, 0)
    check("count_corpus says how many machines it compared",
          "across 5 machine(s)" in o, True, o[-200:])


def t_count_corpus_cannot_silently_skip_a_machine():
    """RED before the fix: `4 per-CLI comparison(s), ... present`, exit 0.

    The roster is `d.is_dir() and paths.find(d, "MANIFEST.json")`, so an export
    that was interrupted before writing its MANIFEST is not skipped — it is
    invisible, and four machines out of five reads as everything.
    """
    c, r = build("q6b")
    os.remove(r / "charlie" / "machine-readable" / "MANIFEST.json")
    o, rc = run(c, "count_corpus.py", "--corpus", str(r))
    check("count_corpus names a corpus folder it could not check",
          "charlie" in o, True, o[-400:])
    check("count_corpus exits non-zero rather than reporting four as five",
          rc, 1, o[-400:])


# --------------------------------------------------------------------------
# Q7 — empty is not absent
# --------------------------------------------------------------------------
def t_empty_machine_is_not_an_absent_machine():
    """RED before the fix: both printed nothing, both said "never exported".

    charlie exported and holds zero transcripts; delta has no corpus folder at
    all. HEAD dropped both from the rollup — `on 3 computer(s)` for a five
    machine fleet — and gave them the identical COVERAGE sentence.
    """
    c, r = build("q7", corpus_skip=("delta",), corpus_empty=("charlie",))
    o, _ = run(c, "corpus_reports.py", "--corpus", str(r))
    rows = {x[0]: x for x in cov_rows(r)}
    check("an EMPTY export and an ABSENT machine do not share a sentence",
          rows["charlie"][4] != rows["delta"][4], True,
          (rows["charlie"][4], rows["delta"][4]))
    check("the empty machine is named as exported",
          "holds nothing" in rows["charlie"][4], True, rows["charlie"])
    check("the absent machine is named as having no folder",
          "no folder in the corpus" in rows["delta"][4], True, rows["delta"])
    check("the empty machine still gets a line in the rollup",
          "charlie" in o and "0 conversations" in o, True, o[:600])
    check("the rollup counts it in the computer count",
          "on 4 computer(s)" in o, True, [l for l in o.splitlines()
                                          if "computer(s)" in l])
    sj = r / "charlie" / paths.MACHINE / STATS
    check("an export that emptied has its stats.json rewritten to zero",
          json.loads(sj.read_text(encoding="utf-8"))["tokens"], 0)


def t_a_roster_machine_that_never_ran_is_on_the_report():
    """dell-latitude-7480-windows has never been scanned. Neither had this row.

    A machine in machines.json and in neither tree contributed 0 to COVERAGE
    and appeared nowhere in it, which is the same output a fleet of four would
    produce.
    """
    c, r = build("q7b")
    (c / "machines.json").write_text(json.dumps({"machines": [
        {"folder": f, "label": l} for f, l, _ in fx.FLEET]
        + [{"folder": "foxtrot", "label": "Foxtrot"}]}), encoding="utf-8")
    run(c, "corpus_reports.py", "--corpus", str(r))
    rows = {x[0]: x for x in cov_rows(r)}
    check("a roster machine in neither tree is on the coverage report",
          "foxtrot" in rows, True, sorted(rows))
    check("and it is not printed as zero usage",
          num(rows.get("foxtrot", ("", "0"))[1]), None, rows.get("foxtrot"))


TESTS = [t_five_machines_sum_exactly,
         t_duplicate_folder_is_not_added_twice,
         t_a_machine_that_disappears_keeps_its_row,
         t_the_all_row_equals_the_sum_of_its_own_rows,
         t_stale_machines_leave_both_sides,
         t_a_session_on_two_machines_is_reported,
         t_disjoint_sessions_do_not_trip_it,
         t_count_corpus_reconciles_all_five,
         t_count_corpus_cannot_silently_skip_a_machine,
         t_empty_machine_is_not_an_absent_machine,
         t_a_roster_machine_that_never_ran_is_on_the_report]


def main():
    print(f"\n  FLEET — five machines, planted totals ({fx.FLEET_TOTAL:,})\n")
    try:
        for t in TESTS:
            print(f"  -- {t.__name__}")
            t()
        for n, g, w, why in PASS:
            print(f"  PASS  {n}")
        for n, g, w, why in FAIL:
            print(f"  FAIL  {n}\n        got {g!r}, want {w!r}"
                  + (f"\n        {why}" if why else ""))
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
    print(f"\n  {len(PASS) + len(FAIL)} checks, {len(FAIL)} failed\n")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
