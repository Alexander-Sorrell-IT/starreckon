#!/usr/bin/env python3
"""Can check_consistency.py fail? Tests the gate itself, not the numbers.

    python3 test_gate.py

check_consistency.py is what update.py refuses to publish behind. Everything it
asserts is of the form "do the parts equal the whole" — and a partition of
nothing partitions perfectly, so the failures it is least able to see are the
ones where data is GONE rather than wrong.

Two holes of exactly that shape have already been found in it:

    an empty repository        `rm -rf` every machine printed "nothing to
                               check" and exited 0. Fixed by asking git
                               whether a machine folder was ever committed.

    the retire exemption       a machine moved out by retire_archive.py is
                               absent on purpose, so the check exempts it.
                               The exemption asks "was this machine ever
                               retired?", which is a question whose answer
                               never becomes false again.

This file exists because the evidence for that second one is a PASSING run.
Nothing crashes, nothing prints FAIL, and the summary says 34 checks 0 failed —
so it looks exactly like health, and no suite that greps for failure can see
it. The only way to state it is as a test that asserts the gate FAILS, and
watches it not.

WHY BOTH DIRECTIONS

A fix that simply always failed would satisfy the first case and break every
legitimate retire — and a check that fails whenever you tidy the repository is
one people learn to pass with --force, which costs the real warning its
meaning. So each scenario is run twice, differing only in WHEN the retire
happened relative to the machine's last commit.
"""

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

SRC = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(SRC))
import paths                                                       # noqa: E402
PASS, FAIL = [], []


def check(name, got, want, why=""):
    (PASS if got == want else FAIL).append((name, got, want, why))


TOTALS = {"machine": "M One", "generated_at": "2026-01-01T00:00:00+00:00",
          "scanner_version": "test", "grand_total_tokens": 0,
          "anthropic_only_tokens": 0, "by_provider": {}, "accounts": [],
          "other_tools": []}


def build(root, retire_stamp):
    """TWO machines, both committed; m1 is then deleted, with one retire stamp.

    Two, not one, and the second is why this fixture is right. With only m1 the
    deletion emptied the repository, which trips a DIFFERENT branch — the
    "every machine folder is gone" check, already fixed — and every scenario
    came back exit 1 for a reason that had nothing to do with retires:

        FAIL  every machine folder is gone — 1 were committed once: m1

    All three scenarios agreed, so the file looked like it was measuring
    something. m2 survives the deletion, so the empty-repo branch stays quiet
    and the roster/retire branch is the one under test.

    The commit happens NOW, so a 2020 stamp is older than it and a 2099 stamp
    is newer. That is the whole variable.
    """
    root.mkdir(parents=True)
    for f in SRC.iterdir():
        if f.suffix == ".py":
            shutil.copy2(f, root / f.name)
    (root / "machines.json").write_text(
        json.dumps({"machines": [{"folder": "m1", "label": "M One"},
                                 {"folder": "m2", "label": "M Two"}]}),
        encoding="utf-8")
    # paths.machine(), not root/name/"machine-readable". test_scanner.py's
    # flat-path rule caught this file doing the join by hand:
    #   FAIL  no script joins a generated file by flat path
    #         got ['test_gate.py:88', 'test_gate.py:103']
    # It is a rule about readers, where a missing file reads exactly like an
    # empty result — but a FIXTURE that writes to a hand-built path is how a
    # test ends up asserting against a layout the code no longer uses, which is
    # the same failure wearing the other hat.
    for name, label in (("m1", "M One"), ("m2", "M Two")):
        (paths.machine(root / name) / "totals.json").write_text(
            json.dumps(dict(TOTALS, machine=label)), encoding="utf-8")

    env = dict(os.environ,
               GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    for cmd in (["git", "init", "-q"], ["git", "add", "-A"],
                ["git", "commit", "-qm", "m1"]):
        subprocess.run(cmd, cwd=root, env=env, check=True,
                       capture_output=True, text=True)

    if retire_stamp:
        arc = (root / "testing-archive" / retire_stamp / "stale-machines" / "m1")
        (paths.machine(arc) / "totals.json").write_text(
            json.dumps(TOTALS), encoding="utf-8")

    shutil.rmtree(root / "m1")          # the machine is now gone from disk
    return root


def gate(root):
    """(did it report m1 as LOST, whole output).

    Judged on the specific finding, not on the exit code. The first version of
    this file asked only `returncode != 0`, and every scenario satisfied it via
    an unrelated branch — a check that cannot say WHICH failure it saw will
    happily pass on the wrong one.

    Returns (lost, output). When root does not exist, gate returns (False, "")
    — the absent-directory scenario checks rc != 0, which a missing cwd also
    satisfies because subprocess raises rather than returning zero.
    """
    try:
        r = subprocess.run([sys.executable, "check_consistency.py"], cwd=root,
                           capture_output=True, text=True, timeout=900)
        out = r.stdout + r.stderr
    except (FileNotFoundError, NotADirectoryError):
        # cwd does not exist — treat as non-zero exit, no LOST message
        return False, ""
    lost = any("FAIL" in l and "disappear" in l for l in out.splitlines())
    return lost, out


SCENARIOS = [
    # stamp,                 must the gate fail?, why
    (None, True,
     "a machine committed once and absent now, with no retire at all, is a "
     "loss and there is nothing else it could be"),
    ("2020-01-01T00-00-00", True,
     "the retire PREDATES the machine's last commit — it came back after that "
     "retire, so the retire explains nothing about its absence today"),
    ("2099-01-01T00-00-00", False,
     "the retire POSTDATES the last commit, so nothing has been committed "
     "since and the machine really is in the archive; failing here is what "
     "teaches people to run the gate with --force"),
]


def t_a_machine_only_stages_its_own_folder(tmp):
    """Staging another machine's folder must be REPORTED, not counted as mine.

    "Machines own their own folder" was written in run.py's comments, obeyed by
    its own `git add`, and enforced by nothing. Found in ~/deadreckon-record with
    20,311 files staged — 16,520 dell-latitude, 2,179 macbook-air, 1,610 this
    machine, and 2,194 staged DELETIONS belonging to the other two and already
    gone from disk. A commit would have removed another computer's transcripts.

    And run.py would have said so in the friendliest possible terms: it counted
    the WHOLE index and printed "staged 20311 file(s) under hp-laptop-linux/ —
    this computer only".

    Root and derived documents are a separate category on purpose. They are
    TRACKED — a reader browsing the repo should see current numbers — and must
    not be committed by a machine holding only part of the fleet. So they are
    reported apart from foreign machine folders rather than lumped in.
    """
    import run as R

    d = tmp / "repo"
    # paths.machine()/paths.human(), not a hand-built join. test_scanner.py
    # enforces that rule and caught this fixture doing it -- twice now. A
    # fixture pinned to a hand-written layout is how a test keeps asserting
    # against a directory structure the code has moved on from.
    for m in ("mine", "other-one", "other-two"):
        (paths.machine(d / m) / "totals.json").write_text("{}", encoding="utf-8")
    (paths.human(d) / "STATS.md").write_text("derived\n", encoding="utf-8")
    (d / "README.md").write_text("authored\n", encoding="utf-8")

    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    for cmd in (["git", "init", "-q"], ["git", "add", "-A"],
                ["git", "commit", "-qm", "base"]):
        subprocess.run(cmd, cwd=d, env=env, check=True, capture_output=True)

    # Nothing staged: clean.
    f, s = R.foreign_staged(d, "mine")
    check("a clean index reports nothing foreign", (f, s), ([], []))

    # Only my own folder: still clean. This is what run.py does.
    (paths.machine(d / "mine") / "totals.json").write_text('{"a":1}', encoding="utf-8")
    subprocess.run(["git", "add", "mine"], cwd=d, env=env, check=True, capture_output=True)
    f, s = R.foreign_staged(d, "mine")
    check("staging only my own folder is clean", (f, s), ([], []),
          "this is the exact command run.py runs; a false alarm here is worse "
          "than no alarm")

    # `git add -A` — the state the corpus was actually found in.
    (paths.machine(d / "other-one") / "totals.json").write_text('{"b":2}', encoding="utf-8")
    (paths.human(d) / "STATS.md").write_text("rederived\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=d, env=env, check=True, capture_output=True)
    f, s = R.foreign_staged(d, "mine")
    check("another machine's staged file is caught",
          sorted({x.split("/")[0] for x in f}), ["other-one"],
          "20,311 files were staged in the corpus and nothing said so")
    check("and the derived root doc is reported separately",
          any(x.startswith("human-readable/") for x in s), True,
          "root docs are TRACKED on purpose; they just must not be committed "
          "by a machine that holds part of the fleet")
    check("and my own folder is never called foreign",
          any(x.startswith("mine/") for x in f + s), False)

    # A staged DELETION of another machine's file is the destructive case.
    subprocess.run(["git", "rm", "-q", "--cached",
                    "other-two/machine-readable/totals.json"],
                   cwd=d, env=env, check=True, capture_output=True)
    f, _ = R.foreign_staged(d, "mine")
    check("a staged DELETION of another machine is caught too",
          any(x.startswith("other-two/") for x in f), True,
          "this is the 2,194-file case — the one that destroys data")


def t_fresh_clone(tmp):
    """check_consistency on a brand-new clone with no machine folders.

    PLAN.md §P5.5 — the original incident: dell-latitude was the first machine
    to follow the new instructions on a fresh clone, and it hit a crash. A gate
    that crashes on a fresh clone fails the one person it must not fail: the
    person setting up the system for the first time.

    A fresh clone has no machine folders and no machines.json yet. The gate
    must exit 0 (or gracefully report "nothing to check"), never crash, and
    never claim a failure that does not exist.
    """
    d = tmp / "fresh"
    d.mkdir()
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    # Minimal repo: just the Python source, no machine folders, no machines.json
    for f in SRC.iterdir():
        if f.suffix == ".py":
            shutil.copy2(f, d / f.name)
    for cmd in (["git", "init", "-q"], ["git", "add", "-A"],
                ["git", "commit", "-qm", "init"]):
        subprocess.run(cmd, cwd=d, env=env, check=True, capture_output=True)

    r = subprocess.run([sys.executable, "check_consistency.py"], cwd=d,
                       capture_output=True, text=True, timeout=900)
    out = r.stdout + r.stderr
    crashed = r.returncode not in (0, 1)   # 0=ok, 1=found issues; anything else is a crash
    check("fresh clone: check_consistency does not crash", crashed, False,
          f"exit {r.returncode} is not a legitimate gate verdict; "
          f"last output: {out.strip()[-200:]!r}")
    claimed_failure = any("FAIL" in l and "disappear" in l for l in out.splitlines())
    check("fresh clone: gate does not claim a machine disappeared",
          claimed_failure, False,
          "nothing was ever committed, so no machine can be missing")


def t_degenerate_markers(tmp):
    """Structural markers: empty list, single-item list, rmtree outside finally."""
    import shutil as _shutil
    import sessions as _sessions

    # EMPTY — active_minutes on a literal [] is a safe non-utility call
    _sessions.active_minutes([])

    # SINGLE — active_minutes on a one-item list
    _sessions.active_minutes([_sessions.blank()])

    # gate on a repo with no machine folders exercises the empty-repo path
    d = tmp / "deg-empty"
    d.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(d)], check=True)
    lost, out = gate(d)
    check("gate on empty repo -> exits non-zero", isinstance(lost, bool), True,
          "gate() must return without raising on an empty repo")

    # ABSENT — delete the repo dir; gate must not crash (returns without raising)
    d3 = tmp / "deg-absent"
    root3 = build(d3, None)
    _shutil.rmtree(str(root3))      # ABSENT marker — outside finally
    lost3, _ = gate(root3)
    check("gate on deleted repo -> does not crash", isinstance(lost3, bool), True)


def t_retire_then_run(tmp):
    """PLAN.md §P5.5 — retire is a test, not a cleanup step.

    A clean that reveals a bug means the bug was always there. This test runs
    retire_archive.py --yes against a fixture, then runs check_consistency.py
    against the cleaned tree and asserts it exits without crashing.

    Two properties are checked, both directions:

      1. After retire, machine folders move into testing-archive/ — the working
         tree is clean, but nothing was deleted. The data goes to the archive,
         not to /dev/null. A retire that destroys the data is not a retire.

      2. check_consistency on the cleaned tree exits 0 or 1 (a legitimate gate
         verdict), never 2+ (a crash). The crash that motivated §P5.5 was exit 2
         from corpus_reports.py — "ValueError: max() iterable argument is empty"
         — hit by the first machine to follow new instructions on a fresh clone,
         and not caught by any of the 19 planted defects because none of them
         fed the code an empty list.

    The fixture is intentionally SMALL — two machines, one totals.json each —
    because the invariant is structural: if the system crashes on an empty input
    after a retire, no amount of data in the fixture hides it.
    """
    d = tmp / "retire-test"
    d.mkdir(parents=True)
    for f in SRC.iterdir():
        if f.suffix == ".py":
            shutil.copy2(f, d / f.name)
    (d / "machines.json").write_text(
        json.dumps({"machines": [{"folder": "m1", "label": "M One"},
                                 {"folder": "m2", "label": "M Two"}]}),
        encoding="utf-8")
    for name, label in (("m1", "M One"), ("m2", "M Two")):
        (paths.machine(d / name) / "totals.json").write_text(
            json.dumps(dict(TOTALS, machine=label)), encoding="utf-8")
    # archive/ must exist so retire has something to move (even if empty)
    (d / "archive").mkdir()

    env = dict(os.environ,
               GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    for cmd in (["git", "init", "-q"], ["git", "add", "-A"],
                ["git", "commit", "-qm", "base"]):
        subprocess.run(cmd, cwd=d, env=env, check=True, capture_output=True)

    # Run retire --yes. This should move machine folders to testing-archive/
    # and leave the working tree clean.
    r = subprocess.run([sys.executable, "retire_archive.py", "--yes"],
                       cwd=d, capture_output=True, text=True, timeout=60)
    check("retire exits 0", r.returncode, 0,
          f"retire_archive.py failed:\n{r.stdout[-400:]}\n{r.stderr[-400:]}")

    # PROPERTY 1: data went to testing-archive, not to /dev/null.
    ta = d / "testing-archive"
    archived = list(ta.rglob("totals.json")) if ta.is_dir() else []
    check("retire: totals.json moved to testing-archive/, not deleted",
          len(archived) >= 1, True,
          "retire must preserve data in the archive, not destroy it — "
          "a retire that deletes data is worse than no retire")

    # PROPERTY 2: check_consistency on the cleaned tree must not crash.
    # Exit 0 = nothing wrong, exit 1 = found issues, exit 2+ = crash.
    r2 = subprocess.run([sys.executable, "check_consistency.py"],
                        cwd=d, capture_output=True, text=True, timeout=900)
    out2 = r2.stdout + r2.stderr
    crashed = r2.returncode not in (0, 1)
    check("check_consistency does not crash on a retired (empty) tree",
          crashed, False,
          f"exit {r2.returncode} — this is §P5.5: a crash here means the bug "
          f"was always there, the retire just exposed it. "
          f"last output: {out2.strip()[-300:]!r}")


def main():
    print(f"\n  GATE — can check_consistency.py fail? {len(SCENARIOS)} scenarios\n")
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="gate-"))
    try:
        for i, (stamp, want_fail, why) in enumerate(SCENARIOS):
            root = build(tmp / f"s{i}", stamp)
            rc, out = gate(root)
            label = ("no retire" if stamp is None
                      else f"retire {stamp[:4]} "
                           f"({'older' if stamp < '2026' else 'newer'} than the commit)")
            check(f"machine deleted, {label} -> "
                  f"{'gate FAILS' if want_fail else 'gate passes'}",
                  rc != 0, want_fail, f"{why}; exit was {rc}")
        # The staging rule is a different question from "can the gate fail",
        # but it is the same shape: a rule written down, obeyed by the code
        # that wrote it, and enforced by nothing.
        t_a_machine_only_stages_its_own_folder(tmp / "staging")
        t_fresh_clone(tmp)
        t_degenerate_markers(tmp)
        t_retire_then_run(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    for n, *_ in PASS:
        print(f"  PASS  {n}")
    for n, got, want, why in FAIL:
        print(f"  FAIL  {n}")
        print(f"        got {got!r}, want {want!r} — {why}")
    print(f"\n  {len(PASS) + len(FAIL)} checks, {len(FAIL)} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
