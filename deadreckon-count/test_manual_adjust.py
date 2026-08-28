#!/usr/bin/env python3
"""Hostile fixtures for manual adjustments. PLAN-MERGED item 10.3.

These do not check that the happy path works. They check that the three things
a manual adjustment MUST NOT be able to do are impossible, or — where a file on
disk makes "impossible" a lie — that they are loud:

    alter a measured total          the measured figure is computed without
                                    ever reading this file
    hide its provenance             author and reason are required; an entry
                                    cannot be written anonymously
    be silently revised or deleted  every entry hashes to its own content and
                                    names the one before it

The last one is the reason for the hash chain. A file on disk can always be
edited by whoever owns the disk, and a design claiming otherwise is worse than
one that notices — so the test is not "editing is prevented" but "editing is
detected and the tampered entry stops counting".
"""

import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import manual_adjust as MA  # noqa: E402

PASS, FAIL = [], []


def check(name, got, want, why=""):
    (PASS if got == want else FAIL).append((name, got, want, why))


def _seed(tmp):
    MA.append(tmp, author="alex", cli="claude", tokens=1_000,
              reason="pre-daemon usage, vendor invoice 2026-03")
    MA.append(tmp, author="alex", cli="gemini", tokens=2_000,
              reason="store wiped by a reinstall")
    return MA.load(tmp)


# ------------------------------------------------ cannot hide provenance
def test_an_entry_cannot_be_written_anonymously(tmp):
    for kwargs, what in (
            (dict(author="", cli="claude", tokens=1, reason="x"), "no author"),
            (dict(author="a", cli="claude", tokens=1, reason=""), "no reason")):
        try:
            MA.append(tmp, **kwargs)
            raised = None
        except ValueError:
            raised = "ValueError"
        check(f"an entry with {what} is refused", raised, "ValueError",
              "a number nobody signed and nobody explained has no provenance")


def test_tokens_must_be_an_integer(tmp):
    for bad in ("1000", 10.5, True):
        try:
            MA.append(tmp, author="a", cli="c", tokens=bad, reason="r")
            raised = None
        except ValueError:
            raised = "ValueError"
        check(f"tokens={bad!r} is refused", raised, "ValueError")


# ------------------------------------------- cannot be silently revised
def test_editing_an_entry_breaks_its_id(tmp):
    _seed(tmp)
    f = MA.path_for(tmp)
    lines = f.read_text().splitlines()
    e = json.loads(lines[0])
    e["tokens"] = 999_999_999          # the edit an attacker would want
    lines[0] = json.dumps(e)
    f.write_text("\n".join(lines) + "\n")

    problems = MA.verify(tmp)
    check("an edited entry is detected", bool(problems), True,
          "the id is a hash of the entry's own content")
    check("the detection names it as edited after writing",
          any("edited after it was written" in p for p in problems), True)

    _per, total = MA.totals(tmp)
    check("the edited entry does NOT count toward the total", total, 2_000,
          "a tampered file must make the figure smaller and say why, never "
          "larger and silently")


def test_deleting_an_entry_breaks_the_chain(tmp):
    _seed(tmp)
    f = MA.path_for(tmp)
    lines = f.read_text().splitlines()
    f.write_text(lines[1] + "\n")       # drop the FIRST entry

    problems = MA.verify(tmp)
    check("a deleted entry is detected", bool(problems), True,
          "each entry names the id before it, so a removal leaves a gap")
    check("the detection names it as removed or reordered",
          any("removed or reordered" in p for p in problems), True)


def test_reordering_is_detected(tmp):
    _seed(tmp)
    f = MA.path_for(tmp)
    lines = f.read_text().splitlines()
    f.write_text("\n".join(reversed(lines)) + "\n")
    check("reordering the file is detected", bool(MA.verify(tmp)), True)


def test_a_malformed_line_is_reported_not_skipped(tmp):
    _seed(tmp)
    f = MA.path_for(tmp)
    f.write_text(f.read_text() + "{not json\n")
    problems = MA.verify(tmp)
    check("a malformed line is reported", bool(problems), True,
          "skipping it would make corruption look like an entry that was "
          "never written")


# --------------------------------------- cannot alter a measured total
def test_measured_totals_never_read_this_file(tmp):
    """The strongest property, asserted the only way that means anything.

    Not "the number did not change" — that could be luck. `token_ledger` and
    `sessions` are the modules that produce measured figures, and neither may
    so much as mention this module or its filename.
    """
    here = pathlib.Path(__file__).parent
    offenders = []
    for name in ("token_ledger.py", "sessions.py", "analyze_tokens.py",
                 "combine.py", "stats_page.py"):
        f = here / name
        if not f.is_file():
            continue
        src = f.read_text(encoding="utf-8")
        if "manual_adjust" in src or MA.FILE in src:
            offenders.append(name)
    check("no measuring module reads the adjustments file", offenders, [],
          "measured must be computable with this file deleted; adjusted is "
          "measured PLUS manual, and never the other way round")


def test_a_valid_chain_verifies_clean(tmp):
    _seed(tmp)
    check("an untampered file has no problems", MA.verify(tmp), [])
    _per, total = MA.totals(tmp)
    check("and totals to what was written", total, 3_000)


def main():
    tests = [t for n, t in sorted(globals().items()) if n.startswith("test_")]
    for t in tests:
        try:
            with tempfile.TemporaryDirectory() as td:
                t(pathlib.Path(td))
        except Exception as e:  # noqa: BLE001
            FAIL.append((t.__name__, f"raised {type(e).__name__}: {e}",
                         "no exception", ""))
    for name, got, want, why in PASS:
        print(f"  PASS  {name}")
    for name, got, want, why in FAIL:
        print(f"  FAIL  {name}\n          got  {got!r}\n          want {want!r}"
              + (f"\n          {why}" if why else ""))
    print(f"\n{len(PASS) + len(FAIL)} checks, {len(FAIL)} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
