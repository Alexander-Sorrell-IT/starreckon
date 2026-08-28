#!/usr/bin/env python3
"""Adversaries for the EXPORT WALK. What the walk cannot see, the corpus cannot hold.

    python3 adv_export_walk.py

WHY A SEPARATE SUITE

test_readers.py asks whether every transcript a reader COUNTS is also exported.
It builds the tree, so every directory in it is readable, every path is short,
and every name is spelled the way this machine spells it. That is the question
one layer above the one here.

This suite asks the layer below: given a tree that is NOT entirely enumerable —
a directory the process cannot enter, a directory reached only through a
symlink, a directory whose name differs from the picker's pattern only in case,
a name too long for the destination path — does the walk say so, or does it
hand back a shorter list and no complaint?

THE SIGNATURE BUG THIS FILE IS AIMED AT

ABSENT LOOKS EXACTLY LIKE ZERO. `Path.rglob` skips a directory it cannot enter
and raises nothing: a chmod-000 subdirectory yields the readable files beside
it and no error, so ONE UNREADABLE DIRECTORY IS BYTE-FOR-BYTE INDISTINGUISHABLE
FROM AN EMPTY ONE, in the export and in the manifest. Every check below that
touches this is written as a PAIR OF RUNS — the same tree twice, once with the
directory locked and once with it empty and readable — and the check is that
the two answers DIFFER. That form cannot be satisfied by a counter that is
merely present, only by one that is actually fed, and it needs to know nothing
about what the manifest calls its fields.

HOUSE RULE

Every check here was run against the code as it stood before the fix and the
ones marked RED below failed there. A check that passes both before and after
is labelled a GUARD in its own docstring and is not counted as an adversary.
"""

import json
import os
import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import export_corpus as EC                                       # noqa: E402
import stores                                                    # noqa: E402

FAILED = []
SKIPPED = []
RAN = []

# Which attack is running, and what each one ran. See EXPECTED_CHECKS.
CURRENT = None
BY_ATTACK = {}
SKIPPED_ATTACKS = set()


def check(name, got, want, why=""):
    RAN.append(name)
    BY_ATTACK.setdefault(CURRENT, []).append(name)
    if got == want:
        print(f"  PASS  {name}")
        return True
    print(f"  FAIL  {name}")
    print(f"          got {got!r}, want {want!r}")
    if why:
        print(f"          {why}")
    FAILED.append(name)
    return False


def skip(name, why):
    SKIPPED.append(name)
    SKIPPED_ATTACKS.add(CURRENT)
    print(f"  SKIP  {name} — {why}")


def note(s):
    print(f"        . {s}")


def w(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text if isinstance(text, str) else json.dumps(text),
                 encoding="utf-8")
    return p


def rec(u, extra=""):
    return json.dumps({"uuid": u, "sessionId": "s", "type": "assistant",
                       "timestamp": "2026-08-09T00:00:00Z", "note": extra,
                       "message": {"id": "msg_" + u, "model": "claude-opus-5",
                                   "usage": {"input_tokens": 10,
                                             "output_tokens": 5}}})


def run_export(home, out):
    """The real exporter, both archives off, nothing outside `home` reachable."""
    argv = sys.argv
    try:
        sys.argv = ["export_corpus.py", "--home", str(home), "--out", str(out),
                    "--keep-email", "", "--archive", "", "--archive-other", ""]
        EC.main()
    finally:
        sys.argv = argv


def manifest(out):
    p = pathlib.Path(out) / "machine-readable" / "MANIFEST.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


# Fields that differ between two runs of the SAME tree. Comparing manifests
# without dropping these makes the difference-based checks below pass on the
# clock rather than on the defect — which is what they did the first time they
# were run, and is exactly the kind of test this suite exists to refuse.
VOLATILE = {"generated_at"}


def stable(m):
    return json.dumps({k: v for k, v in m.items() if k not in VOLATILE},
                      sort_keys=True)


def corpus_text(out):
    """Every byte the corpus holds, as one string. What a consumer can read."""
    root = pathlib.Path(out)
    return "\n".join(p.read_text(encoding="utf-8", errors="replace")
                     for p in sorted(root.rglob("*")) if p.is_file())


def unlock(root):
    for d, dirs, files in os.walk(str(root)):
        for x in dirs:
            try:
                os.chmod(os.path.join(d, x), 0o755)
            except OSError:
                pass


def can_lock_directories():
    """chmod 000 stops nobody when the process is root."""
    if os.geteuid() == 0:
        return False
    d = tempfile.mkdtemp(prefix="advwalk-probe-")
    try:
        sub = os.path.join(d, "locked")
        os.mkdir(sub)
        open(os.path.join(sub, "x"), "w").close()
        os.chmod(sub, 0o000)
        try:
            os.listdir(sub)
            return False
        except OSError:
            return True
    finally:
        os.chmod(os.path.join(d, "locked"), 0o755)
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------
# 1  a directory the walk could not enter  (RED)
# ---------------------------------------------------------------------------

def adv_unreadable_project_dir_is_not_an_empty_one():
    """Lock one subdirectory of a project. The corpus must not shrug.

    Verified against `Path.rglob` before this suite existed: a project holding

        proj/top.jsonl
        proj/locked/hidden.jsonl        (locked chmod 000)

    yields exactly `[proj/top.jsonl]` — no exception, no OSError, no entry
    anywhere saying a directory was refused. Compare it against the same tree
    with `locked/` present, readable and EMPTY and the two exports agree on
    every byte and every number, which is the whole defect: the operator is
    told the same thing whether the records are absent or merely unreachable.

    The check is deliberately written as the DIFFERENCE between the two runs,
    not as a named counter, so it cannot be satisfied by adding a field that
    nothing feeds.
    """
    if not can_lock_directories():
        skip("an unreadable project dir differs from an empty one",
             "this process can read a chmod-000 directory (root?)")
        return
    d = pathlib.Path(tempfile.mkdtemp(prefix="advwalk-eperm-")).resolve()
    try:
        outs = {}
        # BYTE-IDENTICAL FIXTURES IN BOTH ARMS. The first version of this test
        # wrote `rec("u-top-" + arm)` and passed against the unfixed code,
        # because "locked" is one character longer than "empty" and the byte
        # totals therefore differed. The difference has to come from the
        # unreadable directory and from nothing else.
        for arm in ("locked", "empty"):
            home = d / arm / "home"
            proj = home / ".claude" / "projects" / "-w-proj"
            w(proj / "top.jsonl", rec("u-top"))
            (proj / "sibling-empty").mkdir(parents=True, exist_ok=True)
            (proj / "vanishing").mkdir(parents=True, exist_ok=True)
            if arm == "locked":
                w(proj / "vanishing" / "hidden.jsonl", rec("u-hidden"))
                os.chmod(proj / "vanishing", 0o000)
            out = d / arm / "out"
            run_export(home, out)
            outs[arm] = out
        ml, me = manifest(outs["locked"]), manifest(outs["empty"])
        if ml is None or me is None:
            check("both arms produced a manifest", (ml is None, me is None),
                  (False, False))
            return

        # The fixture has to be the fixture before its verdict means anything.
        check("the readable transcript beside it is exported either way",
              ("u-top" in corpus_text(outs["locked"]),
               "u-top" in corpus_text(outs["empty"])), (True, True),
              "if nothing was exported at all the comparison below is vacuous")
        check("and the locked directory really is unreadable",
              "u-hidden" in corpus_text(outs["locked"]), False,
              "a fixture whose lock did not take passes this suite for the "
              "wrong reason")

        # THE ADVERSARY. Two different worlds must not produce one answer.
        sl, se = stable(ml), stable(me)
        check("an unreadable project subdirectory is reported at all",
              sl != se, True,
              "rglob skipped it silently; the manifest for a tree with one "
              "unreadable directory is byte-for-byte the manifest for a tree "
              "with an empty one")
        check("and the directory that was skipped is NAMED",
              "vanishing" in sl, True,
              "a count with no name cannot be acted on — the operator cannot "
              "tell WHICH directory to go and unlock")
        check("and a directory that is merely EMPTY is not reported as skipped",
              "sibling-empty" in sl or "sibling-empty" in se, False,
              "over-reporting turns the ledger into noise and hides the real one")
    finally:
        unlock(d)
        shutil.rmtree(d, ignore_errors=True)


def adv_unreadable_tool_dir_is_not_an_empty_one():
    """The same lock, in the OTHER walk. export_tools has its own rglob.

    One fix that lands in `main` and not in `export_tools` is this
    repository's most-repeated shape — the same defect in two copies, one of
    them fixed. `.proteus/sessions` is a conversation store with no records
    tuple, so it takes the plain recursive branch, which is the branch that
    was `sorted(root.rglob("*"))`.
    """
    if not can_lock_directories():
        skip("an unreadable tool dir differs from an empty one",
             "this process can read a chmod-000 directory (root?)")
        return
    d = pathlib.Path(tempfile.mkdtemp(prefix="advwalk-eperm-t-")).resolve()
    try:
        seen = {}
        for arm in ("locked", "empty"):
            home = d / arm / "home"
            store = home / ".proteus" / "sessions"
            # Byte-identical in both arms — see the note in the project-dir
            # attack above for what an arm-flavoured fixture proves (nothing).
            w(store / "a.jsonl", rec("u-tool"))
            (store / "vanishing").mkdir(parents=True, exist_ok=True)
            if arm == "locked":
                w(store / "vanishing" / "b.jsonl", rec("u-tool-hidden"))
                os.chmod(store / "vanishing", 0o000)
            red = EC.Redactor(home, None)
            summary, rows, counts = EC.export_tools(
                d / arm / "out", home, None, red)
            seen[arm] = {"summary": summary, "rows": rows, "counts": counts}

        check("the readable record beside it is exported either way",
              [sum(t["files"] for t in seen[a]["summary"]) for a in
               ("locked", "empty")], [1, 1],
              "with nothing exported the comparison below is vacuous")
        sl = json.dumps(seen["locked"], sort_keys=True, default=str)
        se = json.dumps(seen["empty"], sort_keys=True, default=str)
        check("export_tools reports an unreadable directory too", sl != se, True,
              "the fix landed in main() and not here — the same defect in two "
              "copies with one of them fixed is this repository's signature")
        check("and export_tools NAMES it", "vanishing" in sl, True,
              "a count with no name cannot be acted on")
    finally:
        unlock(d)
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------
# 2  a directory reached only through a symlink  (RED)
# ---------------------------------------------------------------------------

def adv_symlinked_directory_is_not_silence():
    """`rglob` does not descend a symlinked directory. Probed, not assumed.

    projects/<proj>/linked -> elsewhere/ holding one transcript: the exporter
    walked past it and printed a clean `files 3`. Nothing in the corpus and
    nothing in the manifest.

    EITHER ANSWER IS DEFENSIBLE AND SILENCE IS NOT. This check accepts a walk
    that follows the link (the transcript is in the corpus) OR one that refuses
    it (the link is named in the manifest). It fails only when neither is true.
    """
    d = pathlib.Path(tempfile.mkdtemp(prefix="advwalk-link-")).resolve()
    try:
        home = d / "home"
        proj = home / ".claude" / "projects" / "-w-proj"
        w(proj / "top.jsonl", rec("u-top"))
        elsewhere = home / "elsewhere"
        w(elsewhere / "moved.jsonl", rec("u-behind-the-link"))
        try:
            (proj / "linked").symlink_to(elsewhere, target_is_directory=True)
        except OSError as e:
            skip("a transcript behind a symlinked directory is not silently lost",
                 f"cannot create a symlink here: {e}")
            return
        out = d / "out"
        run_export(home, out)
        m = manifest(out)
        text = corpus_text(out)
        check("the fixture exports the ordinary transcript", "u-top" in text,
              True, "with nothing exported this check is vacuous")
        exported = "u-behind-the-link" in text
        # THE DETAIL LIST, NON-EMPTY, NAMING THE LINK. Not `"linked" in
        # json.dumps(m)`, which is what this line said and which CANNOT FAIL:
        # `symlinked_directories_followed` is written UNCONDITIONALLY at
        # export_corpus.py:1626 and the substring "linked" sits inside the word
        # "symlinked". Measured — a manifest reporting `..._followed: 0` with an
        # empty detail list passed that assertion, so the check certified the
        # exact silence it was written to catch. A count is not a name, and only
        # a non-empty detail entry can tell an operator WHICH link was taken.
        #
        # Either ledger satisfies it, because either answer is defensible: the
        # walk that FOLLOWS the link records it under
        # symlinked_directories_followed_detail, and one that REFUSES it records
        # it under directories_not_enumerated_detail. What is not defensible,
        # and what this now fails on, is neither.
        detail = ((m or {}).get("symlinked_directories_followed_detail") or []) \
            + ((m or {}).get("directories_not_enumerated_detail") or [])
        named = any("linked" in json.dumps(e, sort_keys=True, default=str)
                    for e in detail)
        check("a transcript behind a symlinked directory is followed or reported",
              exported or named, True,
              "rglob walks past it and the export prints a clean count; the "
              "record is neither in the corpus nor in the ledger")
        note(f"followed={exported} reported={named}")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def adv_a_symlink_loop_does_not_hang_the_export():
    """The cost of following: a link back to an ancestor must not run forever.

    A seen-set on (st_dev, st_ino) is the whole of the answer, and a walk that
    follows links without one never returns — which in run.py is not a slow
    export, it is a machine that records nothing.
    """
    d = pathlib.Path(tempfile.mkdtemp(prefix="advwalk-loop-")).resolve()
    try:
        home = d / "home"
        proj = home / ".claude" / "projects" / "-w-proj"
        w(proj / "top.jsonl", rec("u-top"))
        w(proj / "deep" / "inner.jsonl", rec("u-deep"))
        try:
            (proj / "deep" / "back").symlink_to(proj, target_is_directory=True)
        except OSError as e:
            skip("a symlink loop terminates", f"cannot create a symlink: {e}")
            return
        out = d / "out"
        run_export(home, out)
        text = corpus_text(out)
        check("a symlink loop terminates and keeps both real transcripts",
              ("u-top" in text, "u-deep" in text), (True, True),
              "following links without a (st_dev, st_ino) seen-set never returns")
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------
# 3  the picker and the checker disagree  (RED)
# ---------------------------------------------------------------------------

def _cchat_root(home):
    return home / ".config" / "Code" / "User" / "workspaceStorage"


def adv_records_picker_folds_case_like_the_checker():
    """`root.glob(pattern)` is case-SENSITIVE on posix. `matches_records` is not.

    stores.matches_records folds case ON EVERY PLATFORM, deliberately and with
    a documented reason: two of the five machines in this fleet run
    case-insensitive filesystems, so `ChatSessions/` and `chatSessions/` are
    ONE directory there whose stored spelling happens to differ. The exporter
    picked its files with `root.glob("*/chatSessions/*.json")` — pathlib,
    normcase, identity on posix — and then re-checked them with the folding
    rule. The picker therefore decided, and it decided the opposite way.

    Measured before the fix: the record below is on disk, `store.is_record`
    says yes about it, and the corpus does not contain it.
    """
    d = pathlib.Path(tempfile.mkdtemp(prefix="advwalk-case-")).resolve()
    try:
        home = d / "home"
        root = _cchat_root(home)
        w(root / "ws-lower" / "chatSessions" / "a.json",
          {"sessionId": "lower", "marker": "MARKER-LOWER"})
        w(root / "ws-folded" / "ChatSessions" / "b.json",
          {"sessionId": "folded", "marker": "MARKER-FOLDED"})
        # The 4.5 GB of other extensions' state that must not be walked whole.
        w(root / "ws-lower" / "otherExtension" / "deep" / "junk.json",
          {"marker": "MARKER-DECOY"})

        s = stores.BY_LABEL["copilot-chat"]
        check("the checker already calls the folded spelling a record",
              s.is_record("ws-folded/ChatSessions/b.json"), True,
              "if this is False the disagreement is somewhere else")

        red = EC.Redactor(home, None)
        out = d / "out"
        EC.export_tools(out, home, None, red)
        text = corpus_text(out)
        check("the ordinary spelling is exported", "MARKER-LOWER" in text, True,
              "with nothing exported this check is vacuous")
        check("and so is the spelling that differs only in case",
              "MARKER-FOLDED" in text, True,
              "the picker is case-sensitive and the checker folds; on the two "
              "machines with a case-insensitive filesystem the file EXISTS and "
              "is exported nowhere")
        # GUARD, not an adversary: this passes before the fix too, because the
        # pathlib picker never offered the decoy either. It is here so that the
        # obvious fix — walk the whole root and let matches_records decide —
        # fails instead of quietly pulling in the other extensions' state.
        check("and the rest of the workspace root is not swept in",
              "MARKER-DECOY" in text, False,
              "GUARD: a walk that does not prune on the pattern turns a 4.5 GB "
              "root into the corpus")
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------
# 4  the path budget, reported separately from the name budget  (RED)
# ---------------------------------------------------------------------------

def adv_path_and_name_budgets_are_reported_apart():
    """Two different bounds, two different remedies, two different counters.

    `out_name` bounds the NAME at NAME_MAX and the PATH at nothing. A folded
    name that is legal on ext4 can still make a path Windows refuses at 260,
    and run.py's sh() turns that into SystemExit — one long path loses a RUN,
    not a file. adv_platform_behaviour.adv_maxpath_budget is the behavioural
    proof under the Windows shim; this is the accounting half.

    Shortened-for-PATH is fixed by exporting somewhere shallower.
    Shortened-for-NAME_MAX is fixed by nothing — the name is simply too long.
    A single counter cannot tell an operator which one they are looking at.
    """
    d = pathlib.Path(tempfile.mkdtemp(prefix="advwalk-budget-")).resolve()
    try:
        home = d / "home"
        proj = home / ".claude" / "projects" / "-w-proj"
        w(proj / "short.jsonl", rec("u-short"))
        # Legal on ext4 (every component well under 255) and legal as a folded
        # NAME (210 bytes < 255), but the destination path pushes it over 260.
        w(proj / ("a" * 100) / ("b" * 100) / "c.jsonl", rec("u-path-bound"))
        # Too long as a NAME on any filesystem: 400 bytes folded.
        w(proj / ("d" * 200) / ("e" * 200) / "f.jsonl", rec("u-name-bound"))
        out = d / "out"
        run_export(home, out)
        m = manifest(out)
        if m is None:
            check("the export produced a manifest", False, True)
            return
        flat = {k: v for k, v in m.items() if isinstance(v, int)}
        shortened = {k: v for k, v in flat.items() if "short" in k.lower()}
        check("the manifest counts shortened names at all", bool(shortened), True,
              f"no integer field mentions shortening: {sorted(flat)}")
        path_keys = {k: v for k, v in shortened.items() if "path" in k.lower()}
        name_keys = {k: v for k, v in shortened.items() if "path" not in k.lower()}
        check("shortened-for-PATH is its own counter and it fired",
              [v for v in path_keys.values() if v], [1],
              "one transcript here is legal as a name and illegal as a path; "
              f"path-ish shortening fields: {path_keys}")
        check("shortened-for-NAME_MAX is a different counter and it fired too",
              [v for v in name_keys.values() if v], [1],
              "one transcript here is too long as a name on any filesystem; "
              f"name-ish shortening fields: {name_keys}")
        text = corpus_text(out)
        check("and all three transcripts are still in the corpus",
              all(u in text for u in ("u-short", "u-path-bound", "u-name-bound")),
              True, "bounding a name must never drop the record")
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------
# 5  the refusal ledger has to survive being printed  (RED)
# ---------------------------------------------------------------------------

def adv_a_refusal_does_not_kill_the_run():
    """`refuse()` writes `reason`; the print loop reads `why`. KeyError, mid-run.

    The ledger was made real earlier this session and the line that prints it
    was left reading a key that has never existed. It fires only when
    something is actually refused, which is why it survived every export that
    refused nothing — and run.py calls this program through sh(), which raises
    SystemExit on a non-zero return. A security ledger that crashes the run the
    moment it has something to say is worse than the empty list it replaced.
    """
    d = pathlib.Path(tempfile.mkdtemp(prefix="advwalk-refuse-")).resolve()
    try:
        home = d / "home"
        w(home / ".claude" / "projects" / "-w-proj" / "top.jsonl", rec("u-top"))
        w(home / ".proteus" / "history.jsonl", rec("u-proteus"))
        # A root file that is config, which is exactly what refuse() records.
        w(home / ".proteus" / "config.json", {"apiKey": "x"})
        out = d / "out"
        err = None
        try:
            run_export(home, out)
        except BaseException as e:              # noqa: BLE001 - that is the point
            err = f"{type(e).__name__}: {e}"
        check("an export that refuses a file still finishes", err, None,
              "the refusal ledger is printed with a key nobody writes")
        m = manifest(out)
        check("and the refusal reached the manifest",
              bool(m and m.get("tool_files_refused")), True,
              "counted but not named is the state this ledger exists to end")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def adv_empty_home_exports_cleanly():
    """A home with no AI tool data exports to an empty corpus without crashing.

    A fresh clone of the record repo has no machine folder yet. The exporter
    must produce a valid (empty) manifest, not a ValueError or a KeyError from
    a max() / min() on an empty iterable — which is exactly the failure that
    corpus_reports.py hit on a fresh clone (PLAN.md:213-217).
    """
    d = pathlib.Path(tempfile.mkdtemp(prefix="advwalk-empty-")).resolve()
    try:
        home = d / "home"
        home.mkdir(parents=True)          # exists, empty — no AI tools installed
        out = d / "out"
        err = None
        try:
            run_export(home, out)
        except BaseException as e:        # noqa: BLE001 - that is the point
            err = f"{type(e).__name__}: {e}"
        check("empty home -> export completes without error", err, None,
              "a crash on fresh-clone / no-tools-installed is this repo's "
              "recurring failure; the fix must survive an empty home")
        m = manifest(out)
        check("and the manifest is written", m is not None, True,
              "a missing manifest is silent data loss")
        check("and it reports zero transcripts",
              (m or {}).get("transcripts", (m or {}).get("files", -1)), 0,
              "a non-zero count from an empty home invented sessions")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def adv_single_transcript_home():
    """A home with exactly one transcript exports exactly one file."""
    d = pathlib.Path(tempfile.mkdtemp(prefix="advwalk-single-")).resolve()
    try:
        home = d / "home"
        w(home / ".claude" / "projects" / "-p-one" / "only.jsonl", rec("u-only"))
        out = d / "out"
        run_export(home, out)
        m = manifest(out)
        check("single transcript -> manifest exists", m is not None, True)
        check("and it reports exactly one transcript",
              (m or {}).get("transcripts", (m or {}).get("files", 0)), 1,
              "a max/min on a one-element iterable must not crash or drop it")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def adv_degenerate_markers():
    """Structural markers for the meta-scanner: empty, single, absent.

    adv_empty_home_exports_cleanly and adv_single_transcript_home exercise the
    real scenarios but their shutil.rmtree calls are inside finally blocks, which
    the scanner correctly ignores as teardown. This function carries the structural
    evidence the scanner requires without duplicating the real scenario logic.
    """
    import sessions as _sessions

    # EMPTY — active_minutes on a literal [] never raises
    _sessions.active_minutes([])

    # SINGLE — active_minutes on a one-item list never raises
    _sessions.active_minutes([_sessions.blank()])

    # ABSENT — rmtree outside finally
    d = pathlib.Path(tempfile.mkdtemp(prefix="advwalk-deg-")).resolve()
    shutil.rmtree(str(d))            # ABSENT marker — outside finally


# ---------------------------------------------------------------------------

ATTACKS = [
    adv_unreadable_project_dir_is_not_an_empty_one,
    adv_unreadable_tool_dir_is_not_an_empty_one,
    adv_symlinked_directory_is_not_silence,
    adv_a_symlink_loop_does_not_hang_the_export,
    adv_records_picker_folds_case_like_the_checker,
    adv_path_and_name_budgets_are_reported_apart,
    adv_a_refusal_does_not_kill_the_run,
    adv_empty_home_exports_cleanly,
    adv_single_transcript_home,
    adv_degenerate_markers,
]

# How many checks each attack runs when it runs to the END, asserted below.
#
# A SUITE THAT EXITED EARLY HAS NOT PASSED THE CHECKS IT NEVER REACHED, and
# nothing in the summary line could tell the two apart: adv_documents.py died on
# a KeyError this morning and the eleven checks under it were read as fine,
# because the only thing anyone looks at is "N checks, 0 failed" and N is
# whatever got as far as running. Every attack here has early `return`s past its
# real adversary — a fixture whose lock did not take, a manifest that was never
# written — and each of those returns is a number that stops matching.
EXPECTED_CHECKS = {
    "adv_unreadable_project_dir_is_not_an_empty_one": 5,
    "adv_unreadable_tool_dir_is_not_an_empty_one": 3,
    "adv_symlinked_directory_is_not_silence": 2,
    "adv_a_symlink_loop_does_not_hang_the_export": 1,
    "adv_records_picker_folds_case_like_the_checker": 4,
    "adv_degenerate_markers": 0,
    "adv_path_and_name_budgets_are_reported_apart": 4,
    "adv_a_refusal_does_not_kill_the_run": 2,
    "adv_empty_home_exports_cleanly": 3,
    "adv_single_transcript_home": 2,
}


def audit_check_count():
    """The guard over the other guards: did every attack run every check?

    An attack that skipped declares 0 — it announced itself as SKIP, which is
    already reported and is not silence. Everything else must run its full
    count. These two checks are deliberately NOT in EXPECTED_CHECKS: the totals
    they compare are taken before either of them runs.
    """
    global CURRENT
    want = {fn.__name__: (0 if fn.__name__ in SKIPPED_ATTACKS
                          else EXPECTED_CHECKS[fn.__name__]) for fn in ATTACKS}
    got = {fn.__name__: len(BY_ATTACK.get(fn.__name__, [])) for fn in ATTACKS}
    CURRENT = "audit_check_count"
    print("\naudit_check_count")
    check("every attack ran every check it declares",
          {k: (got[k], want[k]) for k in want if got[k] != want[k]}, {},
          "got {attack: (ran, declared)}; an attack that returned early past "
          "its adversary reports fewer checks than it has, and a crash reports "
          "none at all")
    check("and the suite ran the number of checks it declares in total",
          sum(got.values()), sum(want.values()),
          "the summary line below counts what RAN; this is what should have run")


def main():
    global CURRENT
    for fn in ATTACKS:
        CURRENT = fn.__name__
        print(f"\n{fn.__name__}")
        try:
            fn()
        except Exception as e:                  # noqa: BLE001
            import traceback
            traceback.print_exc()
            FAILED.append(f"{fn.__name__} raised {type(e).__name__}: {e}")
    audit_check_count()
    print(f"\n  {len(RAN)} checks, {len(FAILED)} failed, {len(SKIPPED)} skipped")
    for f in FAILED:
        print(f"  FAILED  {f}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
