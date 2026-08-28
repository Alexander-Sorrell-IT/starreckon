#!/usr/bin/env python3
"""Attacks on the attacker's attacker. Does the vacuous-assertion scan work?

    python3 adv_suite_integrity.py

WHY THIS FILE EXISTS

`adversarial_meta.a_no_assertion_is_vacuous` printed

    PASS  no assertion compares a literal to itself

for the entire life of this repository, over a tree in which
`check_consistency.py` held two assertions that do exactly that — and had held
five more, one per machine, before they were fixed by hand. It could not have
seen any of them, for two independent reasons:

    the regex   check\\(\\s*"[^"]*"\\s*,\\s*(True|False)\\s*,\\s*(True|False)
                knows the words True and False and nothing else, so
                `chk(name, 0, 0)` and `chk(name, max(a,b), max(a,b))` were
                invisible;
    the file set was the hand-maintained SUITES list, which has never named
                check_consistency.py — the gate `update.py` actually runs.

A green "no assertion compares a literal to itself", printed over assertions
that do, IS the suite-that-cannot-fail pattern, sitting inside the file whose
entire job is to find it. Replacing the regex with an AST scan is not enough on
its own, because the new scan reports the same clean sheet whether it works or
is broken: nobody can tell a checker that FOUND NOTHING from a checker that
LOOKED AT NOTHING. This repository has made that exact mistake seven times —
`grep -c FAIL` on a file that was never written returns 0 and everything downstream
agrees with it.

So every question the scanner answers is asked here twice: once with a defect
planted, where the answer must be FOUND, and once with a genuine assertion,
where the answer must be NOT FOUND. Both directions, always. The planted
sources are string constants — the scanner parses them, nothing executes them,
and nothing here writes outside a temporary directory.
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import adversarial_meta as meta                                  # noqa: E402

FAILED = []


def check(name, got, want, why=""):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        print(f"        got {got!r}, want {want!r}" + (f" — {why}" if why else ""))
        FAILED.append(name)


# ---------------------------------------------------------------------------
# PLANTED SOURCES. Each is a whole module, so helper discovery has something to
# discover; none of them runs.

SELF_COMPARE_NUMERIC = '''
def chk(name, got, want, detail=""):
    checks.append((name, got, want, got == want, detail))

checks = []
chk("machines absent by RETIRE, not by loss", 0, 0, "in testing-archive")
'''

SELF_COMPARE_BOOL = '''
def check(name, got, want, why=""):
    ok = got == want
    if not ok:
        FAILED.append(name)

FAILED = []
check("the ledger recorded the run", True, True)
'''

SELF_COMPARE_EXPR = '''
def chk(name, got, want, detail=""):
    checks.append((name, got, want, got == want, detail))

checks = []
chk("claude sessions >= account totals",
    max(cc_sess, t["grand_total_tokens"]),
    max(cc_sess, t["grand_total_tokens"]))
'''

RENAMED_HELPER = '''
def verify(label, saw, expected, note=""):
    outcome = saw == expected
    results.append((label, outcome, note))

results = []
verify("the fleet total is unchanged", 0, 0)
'''

GENUINE = '''
def chk(name, got, want, detail=""):
    checks.append((name, got, want, got == want, detail))

checks = []
rows = [1, 2, 3]
chk("three rows survived the merge", len(rows), 3)
chk("the two scanners agree", sum(a), sum(b))
chk("nothing was dropped", max(a, b), max(b, a))
'''

BYPASS = '''
def chk(name, got, want, detail="", fatal=True):
    checks.append((name, got, want, got == want, detail, fatal))

checks = []
if live and delta <= live:
    checks.append((name, 0, 0, True, "", True))
'''

GENUINE_APPEND = '''
def check(name, got, want, why=""):
    if got != want:
        FAILED.append(name)

FAILED = []
FAILED.append("the scanner really did drift")
'''

# The `except` arm every suite here is required to have: an attack that raised
# is recorded as a FAILURE, by hand, because there is no comparison left to
# make. It appends onto the helper's own list with a boolean literal in it, so
# a rule that flags "any hardcoded flag" flags this — and flagging it tells
# four other attacks in adversarial_meta.py to stop demanding it.
CRASH_IS_A_FAILURE = '''
def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))

RESULTS = []
try:
    fn()
except Exception:
    RESULTS.append((f"{name} ran to completion", False, ""))
'''

FIXTURES = '''
def build(machines, sessions):
    return machines, sessions

import shutil
root = "/tmp/x"
build([], [])
build([{"machine": "alpha"}], ["one"])
shutil.rmtree(root + "/m1")
'''

NO_FIXTURES = '''
def build(machines, sessions):
    return machines, sessions

build(load_every_machine(), load_every_session())
print("this suite would survive a clone of the repository")
'''

CLONES = '''
import subprocess
subprocess.run(["git", "clone", "-q", "--local", SRC, d + "/repo"], check=True)
'''


def sites(src):
    """The scanner's verdict on one planted module: the KINDS it found."""
    shapes = meta.assertion_shapes([("planted.py", src)])
    return sorted(k for _l, _n, k, _t in meta.vacuous_sites(src, "planted.py", shapes))


def tree(files):
    d = tempfile.mkdtemp(prefix="suite-integrity-")
    for rel, body in files.items():
        p = os.path.join(d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8").write(body)
    return d


SELF = "compares a value with itself"
FLAG = "hardcodes the passed flag"


# ---------------------------------------------------------------------------

def a_the_api_exists():
    """Nothing below means anything if the scanner is not there to call."""
    need = ("assertion_shapes", "vacuous_sites", "scan_repo", "repo_py_files",
            "degenerate_evidence", "suite_coverage", "QUESTIONS")
    check("adversarial_meta exposes the scanner",
          [n for n in need if not hasattr(meta, n)], [],
          "the AST scan is not there — this file is testing a regex that "
          "cannot see a numeric literal")


def a_planted_vacuous_assertions_are_found():
    """Each shape that has actually shipped in this repository, planted."""
    check("a numeric literal against itself is found", sites(SELF_COMPARE_NUMERIC),
          [SELF], "chk(name, 0, 0) — the shape the regex could not see, and the "
                  "shape both live sites in check_consistency.py have")
    check("a boolean literal against itself is found", sites(SELF_COMPARE_BOOL),
          [SELF], "the one shape the old regex did cover — the control")
    check("an EXPRESSION against itself is found", sites(SELF_COMPARE_EXPR),
          [SELF], "max(a, b) vs max(a, b): five of these ran, one per machine")
    check("a helper the scanner was never told about is found",
          sites(RENAMED_HELPER), [SELF],
          "helper names are discovered by shape; a hand-kept list of names is "
          "the same disease as a hand-kept list of files")
    check("an append that hardcodes the passed flag is found", sites(BYPASS),
          [FLAG], "checks.append((name, 0, 0, True, ...)) never touches the "
                  "comparison, so the self-compare rule cannot see it")


def a_genuine_assertions_are_not_flagged():
    """The other direction. A checker that flags everything is also useless."""
    check("a genuine assertion is not flagged", sites(GENUINE), [],
          "len(rows) vs 3, sum(a) vs sum(b), max(a,b) vs max(b,a) — same "
          "functions, different arguments, all of them can fail")
    check("appending a real failure is not flagged", sites(GENUINE_APPEND), [],
          "FAILED.append(name) carries no hardcoded verdict")
    check("recording a CRASH as a failure by hand is not flagged",
          sites(CRASH_IS_A_FAILURE), [],
          "a hardcoded False cannot manufacture a green; flagging it would "
          "argue against the four attacks that demand a crash be non-zero")


def a_the_file_set_is_walked_not_listed():
    """check_consistency.py escaped by not being on a list. Nothing may."""
    d = tree({"top.py": GENUINE, "deeper/nested.py": SELF_COMPARE_NUMERIC})
    try:
        found, scanned, unreadable = meta.scan_repo(d)
        check("a vacuous assertion in a subdirectory is found",
              [f"{lab}:{kind}" for lab, _n, kind, _t in found],
              [f"deeper{os.sep}nested.py:{SELF}"],
              "os.walk, not a curated list")
        check("and both files were read", sorted(scanned),
              sorted(["top.py", f"deeper{os.sep}nested.py"]))
        check("with nothing unreadable", unreadable, [])
    finally:
        shutil.rmtree(d, ignore_errors=True)


def a_found_nothing_differs_from_looked_at_nothing():
    """THE SIGNATURE BUG. Absent must not look like clean.

    A tree with no Python in it, a file that cannot be parsed, and a genuinely
    clean tree all produce zero findings. If the scan reports only the finding
    count, all three are the same sentence.
    """
    clean = tree({"a.py": GENUINE, "b.py": GENUINE_APPEND})
    empty = tree({})
    broken = tree({"good.py": GENUINE, "half_written.py": "def f(:\n    pass\n"})
    # A tree that WAS there and is not any more. Deleted here, on purpose, in
    # the body and not in the teardown: an absent root is the third thing that
    # produces zero findings, and os.walk over one raises nothing at all.
    gone = tree({"a.py": GENUINE})
    shutil.rmtree(gone)
    try:
        cs, cscan, cbad = meta.scan_repo(clean)
        es, escan, ebad = meta.scan_repo(empty)
        bs, bscan, bbad = meta.scan_repo(broken)
        gs, gscan, gbad = meta.scan_repo(gone)

        check("a clean tree: no findings, and the files were read",
              (cs, sorted(cscan), cbad), ([], ["a.py", "b.py"], []))
        check("an EMPTY tree does not report the same as a clean one",
              (len(es), len(escan), ebad), (0, 0, []),
              "zero findings over zero files is not a clean bill of health, "
              "and the scanned count is what says so")
        check("clean and empty are distinguishable at all",
              len(cscan) == len(escan), False,
              "if the only number reported were the finding count, these two "
              "trees would be the same report")
        check("an ABSENT tree does not report the same as an empty one",
              (gs, gscan, len(gbad)) == (es, escan, len(ebad)), False,
              "os.walk over a path that does not exist yields nothing and "
              "raises nothing: ([], [], []) for a deleted repository")
        check("and the absent root is named", "not a directory" in "".join(gbad),
              True, str(gbad))
        check("a file that does not parse is REPORTED, not scored clean",
              (bs, sorted(bscan), len(bbad)), ([], ["good.py"], 1),
              "it contributes no findings, which is exactly what a clean file "
              "contributes")
        check("and it is named", "half_written.py" in (bbad[0] if bbad else ""),
              True, bbad[0] if bbad else "nothing was reported")
    finally:
        for d in (clean, empty, broken):
            shutil.rmtree(d, ignore_errors=True)


def a_the_gate_that_escaped_is_in_the_scan():
    """The regression for reason (b), asked of the real tree.

    Not "the scan is wider than SUITES" — wider by any file would pass that.
    The file that escaped is named.
    """
    _sites, scanned, _bad = meta.scan_repo(meta.ROOT)
    check("check_consistency.py is scanned", "check_consistency.py" in scanned,
          True, "the gate update.py runs was outside the old scan entirely")
    check("and so is every suite the SUITES list names",
          sorted(s for s, *_ in meta.SUITES if s not in scanned), [])


def a_the_degenerate_input_report_can_be_wrong():
    """Question 3's detector, in both directions.

    A per-suite coverage report that says PRESENT for everything is a green
    that lies, and one that says ABSENT for everything is noise. Planted:
    a module that feeds an empty fixture, a one-item fixture and a deleted
    tree, and one that feeds neither.
    """
    yes = meta.degenerate_evidence(FIXTURES, "planted.py")
    no = meta.degenerate_evidence(NO_FIXTURES, "planted.py")
    check("an empty fixture is seen", bool(yes["EMPTY"]), True, str(yes["EMPTY"]))
    check("a one-item fixture is seen", bool(yes["SINGLE"]), True, str(yes["SINGLE"]))
    check("a deleted tree is seen", bool(yes["ABSENT"]), True, str(yes["ABSENT"]))
    check("a suite with none of the three claims none of them",
          {q: no[q] for q in meta.QUESTIONS},
          {q: [] for q in meta.QUESTIONS},
          "reporting coverage that is not there is the failure mode that "
          "matters here — and NO_FIXTURES prints the word `clone`, which an "
          "earlier version of the detector counted as exercising one")
    check("a real git clone is seen",
          bool(meta.degenerate_evidence(CLONES, "planted.py")["ABSENT"]), True,
          "subprocess.run([\"git\", \"clone\", ...]) — a process, not a word")


ATTACKS = [
    ("the scanner API is present", a_the_api_exists),
    ("planted vacuous assertions are found", a_planted_vacuous_assertions_are_found),
    ("genuine assertions are left alone", a_genuine_assertions_are_not_flagged),
    ("the file set is walked, not listed", a_the_file_set_is_walked_not_listed),
    ("found-nothing differs from looked-at-nothing",
     a_found_nothing_differs_from_looked_at_nothing),
    ("the gate that escaped is in the scan", a_the_gate_that_escaped_is_in_the_scan),
    ("the degenerate-input report can be wrong",
     a_the_degenerate_input_report_can_be_wrong),
]


def main():
    print(f"\n  SUITE INTEGRITY — can the meta-checker fail? "
          f"{len(ATTACKS)} groups\n")
    for name, fn in ATTACKS:
        print(f"  -- {name}")
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            print(f"  FAIL  {name} raised: {type(e).__name__}: {e}")
            FAILED.append(name)
        if fn is a_the_api_exists and FAILED:
            print("\n  the scanner is not there to test — stopping\n")
            return 1
    print()
    if FAILED:
        print(f"  {len(FAILED)} FAILED: {', '.join(FAILED)}")
        return 1
    print("  the scanner finds what is planted, ignores what is genuine, and\n"
          "  says how many files it read when it finds nothing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
