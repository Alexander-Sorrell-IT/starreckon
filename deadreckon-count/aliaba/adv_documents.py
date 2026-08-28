#!/usr/bin/env python3
"""Attacks on the derived documents and the input fingerprint. PLAN P5.8.

    python3 adv_documents.py

WHAT IT IS TRYING TO PROVE WRONG

The defect this exists for is on the record: a rollup generated from 2 machines
sat on the front page, committed, while 5 machine folders sat committed beside
it with complete scans dated EARLIER than the rollup itself. The front page
understated the fleet by 78,967,248,634 tokens and every check passed. Nothing
that ran asked WHICH inputs a document had been built from — only whether the
numbers inside it summed to each other, which they did.

So the questions here are not "does the renderer produce a file".

    1  Change a machine folder. Does the ROOT TOTAL's fingerprint go stale, and
       does the reason NAME the machine that moved?
    2  Does `run.py status` SAY SO, in its own output, before anyone publishes?
    3  Regenerate. Does it match again — is REGENERATED reachable, or is the
       check simply always-fail, which is a check that cannot pass and is worth
       exactly as much as one that cannot fail?
    4  Add an input that is OLDER than the document. A timestamp comparison
       passes this; only an input SET comparison fails it. This is the shape of
       the real defect and it is check 4 for that reason.
    5  Is a document ever silently deleted? Archiving must MOVE — verified byte
       for byte in testing-archive — and a document removed by hand must be
       reported MISSING rather than passing quietly.
    6  Absent vs zero. A machine folder whose totals.json cannot be read must
       not be summed as zero; the total must say INCOMPLETE and name it.

Everything runs in a temporary directory. Nothing here writes into the
repository, starts anything, or touches a live profile.
"""

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paths                                                     # noqa: E402

FAILED = []

# Every section this file contains and how many checks each one holds, declared
# up front and asserted at the bottom by audit_check_count().
#
# WHY: this suite died on a KeyError in section 6 — `fp["inputs"]` against a
# fingerprint that read `{"_malformed": True}` — and took the rest of section 6
# and the whole of section 7 with it, ELEVEN CHECKS THAT NEVER RAN. Nothing
# said so. The file printed its failures, exited non-zero for the reasons it had
# already found, and the eleven were invisible: "did not run" and "passed" look
# identical from outside a suite that reports only what it reached. A section
# that is never entered is missing from SECTIONS; one that dies part way through
# is short. Both are failures here.
PLAN = (
    ("1  changing a machine folder makes the root TOTAL stale", 7),
    ("3  a regenerated document matches again", 3),
    ("3b per-machine document: derived from the folder, not from a list", 7),
    ("2  `run.py status` reports it, before anyone publishes", 9),
    ("4  an input older than the document — the 78,967,248,634-token shape", 5),
    ("5  a document is moved, never deleted", 12),
    ("6  a folder that cannot be read is not a computer that spent nothing", 10),
    ("7  the fingerprint is self-describing", 9),
)
PLANNED = dict(PLAN)
SECTIONS = []            # [title, declared, actually ran], in the order reached


def section(title):
    """Open a section. Its declared check count comes from PLAN."""
    print(f"\n{title}")
    SECTIONS.append([title, PLANNED.get(title), 0])


def set_totals(root, machine, blob):
    """Put a machine's totals where `paths.find()` looks for it.

    Through paths.machine() rather than a hand-joined "machine-readable", for
    the reason test_scanner asserts about every script here: four places joined
    the old flat path and each failed SILENTLY, because a file that is not
    where you looked reads exactly like a file with nothing in it. A fixture
    that writes to the wrong place would make this whole suite pass against a
    tree the code under test cannot see.
    """
    data = paths.machine(pathlib.Path(root) / machine)
    body = blob if isinstance(blob, str) else json.dumps(blob, indent=2)
    (data / "totals.json").write_text(body, encoding="utf-8")


def check(name, got, want, why="", counted=True):
    ok = got == want
    if counted and SECTIONS:
        SECTIONS[-1][2] += 1
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        print(f"        got {got!r}, want {want!r}" + (f" — {why}" if why else ""))
        FAILED.append(name)


def check_true(name, got, why=""):
    check(name, bool(got), True, why)


def documents_block(stdout):
    """Only the `documents` section of `run.py status`.

    Searching the whole of stdout is how a check passes for the wrong reason:
    `status` already prints a table of every machine, so "beta-linux appears in
    the output" was TRUE against a status that says nothing about documents at
    all. Measured, not guessed — that check passed against the unmodified
    run.py, which is exactly the class of worthless test this repository keeps
    shipping. The block, or "" if there is no block.
    """
    lines = stdout.splitlines()
    for i, ln in enumerate(lines):
        if ln.strip() == "documents":
            return "\n".join(lines[i + 1:])
    return ""


def stale_reasons(stdout, document):
    """The `- reason` lines `status` prints UNDER the STALE row for `document`.

    Narrowing to the documents block was not enough. `status` prints one row per
    derived document, and every machine owns a document under its own folder
    name — so `beta-linux/human-readable/FOLDER.md` puts the string "beta-linux"
    in the block whatever status has decided about staleness. "beta-linux" in
    block was therefore TRUE against a status that printed no reason for
    anything, which is the check it was written to make impossible. Measured:
    with the reason lines removed from run.py the assertion still passed.

    A machine is NAMED AS THE CAUSE only in the reason lines under the row for
    the document it made stale. Those are what this returns, and nothing else.
    """
    out, under = [], False
    for ln in documents_block(stdout).splitlines():
        s = ln.strip()
        if s.startswith("- "):
            if under:
                out.append(s[2:])
            continue
        under = s.startswith("STALE") and s.endswith(document)
    return out


# ---------------------------------------------------------------------------
# A fleet on disk, small enough to reason about and shaped like the real one.

TOTALS = {
    "alpha-linux": {"machine": "Alpha Linux", "generated_at": "2026-08-01T10:00:00-05:00",
                    "scanner_version": "aaaaaaaaaaaa", "grand_total_tokens": 1_000_000,
                    "accounts": []},
    "beta-linux": {"machine": "Beta Linux", "generated_at": "2026-08-02T11:00:00-05:00",
                   "scanner_version": "aaaaaaaaaaaa", "grand_total_tokens": 2_000_000,
                   "accounts": []},
}


def build(root, machines=("alpha-linux", "beta-linux"), roster_extra=("gamma-windows",)):
    root = pathlib.Path(root)
    (root / "machines.json").write_text(json.dumps({"machines": [
        {"folder": f, "label": f} for f in list(machines) + list(roster_extra)]}),
        encoding="utf-8")
    for m in machines:
        data = paths.machine(root / m)
        docs = paths.human(root / m)
        set_totals(root, m, TOTALS[m])
        (data / "by_day.csv").write_text("account,date,total\na,2026-08-01,5\n",
                                         encoding="utf-8")
        (data / "token_ledger.jsonl").write_text(json.dumps({
            "observed": "2026-08-01T10:00:05-05:00", "scanner": "aaaaaaaaaaaa",
            "machine": m, "cli": "claude", "session_id": "s1", "total": 5}) + "\n",
            encoding="utf-8")
        (docs / "REPORT.md").write_text("# report\n", encoding="utf-8")
        (root / m / ".machine-id").write_text(json.dumps({"hostname": "h", "folder": m}),
                                              encoding="utf-8")
    return root


def fixture(**kw):
    d = pathlib.Path(tempfile.mkdtemp(prefix="advdocs-"))
    build(d, **kw)
    return d


# ---------------------------------------------------------------------------

def run_sections():
    import doc_render as D

    # -- 1. a machine folder changes; the root total goes stale, by name -----
    section("1  changing a machine folder makes the root TOTAL stale")
    root = fixture()
    try:
        D.render_all(root, log=root / "no-such-boot-log.jsonl")
        fleet = root / "human-readable" / "FLEET.md"
        check_true("the root document exists", fleet.is_file())
        st, why = D.document_state(fleet, root, "root")
        check("fresh from render, the root document is REGENERATED", st, D.REGENERATED,
              f"{why}")

        text = fleet.read_text(encoding="utf-8")
        check_true("the TOTAL section carries the sum of the folders present",
                   "3,000,000" in text, text[-400:])

        # The change a rollup is most likely to miss: one machine rescanned.
        t = dict(TOTALS["alpha-linux"])
        t["grand_total_tokens"] = 99_000_000
        t["generated_at"] = "2026-08-03T09:00:00-05:00"
        set_totals(root, "alpha-linux", t)

        st, why = D.document_state(fleet, root, "root")
        check("after a machine folder changes, the root document is STALE",
              st, D.STALE)
        check_true("and the reason names the machine that moved",
                   any("alpha-linux" in w for w in why), why)
        check_true("the stale document still holds the OLD total — it was not "
                   "quietly corrected in place",
                   "3,000,000" in fleet.read_text(encoding="utf-8"))
        check_true("stale_documents() lists it",
                   any(r["document"].endswith("FLEET.md")
                       for r in D.stale_documents(root)))

        # -- 3. REGENERATED is reachable: this check can pass, not only fail --
        section("3  a regenerated document matches again")
        D.render_all(root, log=root / "no-such-boot-log.jsonl")
        st, why = D.document_state(fleet, root, "root")
        check("after regeneration the root document is REGENERATED", st, D.REGENERATED,
              f"{why}")
        check_true("and now carries the new total",
                   "99,000,000" in fleet.read_text(encoding="utf-8"))
        check("nothing is stale once everything is regenerated",
              len(D.stale_documents(root, log=root / "no-such-boot-log.jsonl")), 0,
              str(D.stale_documents(root, log=root / "no-such-boot-log.jsonl")))

        # -- the per-machine document is derived from the folder --------------
        section("3b per-machine document: derived from the folder, not from a list")
        folder_doc = root / "alpha-linux" / "human-readable" / "FOLDER.md"
        check_true("the machine document exists", folder_doc.is_file())
        ftext = folder_doc.read_text(encoding="utf-8")
        check_true("it names the log", "token_ledger.jsonl" in ftext)
        check_true("it names a generator for a file it found",
                   "analyze_tokens.py" in ftext, ftext[:600])
        (root / "alpha-linux" / "machine-readable" / "mystery.json").write_text(
            "{}", encoding="utf-8")
        st, why = D.document_state(folder_doc, root, "machine",
                                   machine=root / "alpha-linux")
        check("a new file in the folder makes the machine document STALE",
              st, D.STALE, f"{why}")
        (root / "alpha-linux" / "machine-readable"
         / "token_ledger.jsonl.lock").write_text("", encoding="utf-8")
        D.render_machine(root, root / "alpha-linux")
        ftext = folder_doc.read_text(encoding="utf-8")
        check_true("regenerated, the unclaimed file is reported UNATTRIBUTED "
                   "rather than omitted",
                   "mystery.json" in ftext and "UNATTRIBUTED" in ftext)
        check_true("a lock file is named RESIDUE, not silently attributed and "
                   "waved through",
                   "token_ledger.jsonl.lock" in ftext and "RESIDUE" in ftext)
        check_true("both are counted as not belonging",
                   "2 that do not belong" in ftext,
                   [l for l in ftext.splitlines() if "file(s);" in l])
    finally:
        shutil.rmtree(root, ignore_errors=True)

    # -- 2. run.py status SAYS SO -------------------------------------------
    section("2  `run.py status` reports it, before anyone publishes")
    root = fixture()
    try:
        # EVERY module, not a hand-kept list of seven. `stores.py` grew an
        # `import platform_detect` and the list did not, so `run.py status` died
        # on ModuleNotFoundError inside the fixture and all nine checks in this
        # section failed for a reason that has nothing to do with what they ask.
        # A fixture that is missing a file is not evidence about the code under
        # test. adv_published_gate.build() already copies the whole directory.
        for p in HERE.iterdir():
            if p.suffix == ".py":
                shutil.copy2(p, root / p.name)
        D.render_all(root, log=root / "no-such-boot-log.jsonl")

        env = dict(os.environ, HOME=str(root))     # keep the real home out of it
        r = subprocess.run([sys.executable, "run.py", "status"], cwd=root,
                           capture_output=True, text=True, env=env)
        check("status runs at all", r.returncode, 0, r.stderr[-600:])
        check_true("status has a documents section at all",
                   documents_block(r.stdout).strip(), r.stdout[-800:])
        check_true("status reports the documents when they are current",
                   "FLEET.md" in documents_block(r.stdout), r.stdout[-800:])

        t = dict(TOTALS["beta-linux"])
        t["grand_total_tokens"] = 7
        set_totals(root, "beta-linux", t)

        r = subprocess.run([sys.executable, "run.py", "status"], cwd=root,
                           capture_output=True, text=True, env=env)
        check("status still runs after a machine folder changes", r.returncode, 0,
              r.stderr[-600:])
        block = documents_block(r.stdout)
        check_true("status SAYS STALE", "STALE" in block, r.stdout[-1200:])
        check_true("status names the document", "FLEET.md" in block, r.stdout[-1200:])
        # THE STALENESS IS NAMED, NOT THE MACHINE. See stale_reasons(): the
        # block lists beta-linux's own FOLDER.md, so `"beta-linux" in block`
        # holds for a status that gives no reason for anything.
        why = stale_reasons(r.stdout, "human-readable/FLEET.md")
        check_true("status says WHY the rollup is stale, not only THAT it is",
                   why, block or r.stdout[-1200:])
        check_true("and the reason names the machine that moved",
                   any("beta-linux" in w for w in why),
                   why or block or r.stdout[-1200:])

        # A document removed by hand is MISSING, not silence.
        (root / "beta-linux" / "human-readable" / "FOLDER.md").unlink()
        r = subprocess.run([sys.executable, "run.py", "status"], cwd=root,
                           capture_output=True, text=True, env=env)
        check_true("status reports a hand-deleted document as MISSING",
                   "MISSING" in documents_block(r.stdout), r.stdout[-1200:])
    finally:
        shutil.rmtree(root, ignore_errors=True)

    # -- 4. an input OLDER than the document. A timestamp check passes this. --
    section("4  an input older than the document — the 78,967,248,634-token shape")
    root = fixture(machines=("alpha-linux",), roster_extra=())
    try:
        D.render_all(root, log=root / "no-such-boot-log.jsonl")
        fleet = root / "human-readable" / "FLEET.md"
        st, _ = D.document_state(fleet, root, "root")
        check("built from one machine, it is REGENERATED", st, D.REGENERATED)
        fp = D.read_fingerprint(fleet)
        # The same shape as section 6, and the one that actually fired FIRST: a
        # document whose fence does not parse reads as {"_malformed": True}, and
        # `fp["generated_at"]` raised KeyError here — killing sections 4, 5, 6
        # and 7 outright. Every subscript of a fingerprint in this file is a
        # `.get`, and the emptiness it can return is asserted rather than
        # assumed. `""` sorts below every real timestamp, so the comparison
        # below FAILS on a missing one instead of being skipped with the crash.
        doc_at = fp.get("generated_at", "") if isinstance(fp, dict) else ""

        # A second machine, complete, scanned BEFORE the rollup was written —
        # exactly what was sitting committed beside the front page.
        old = dict(TOTALS["beta-linux"])
        old["generated_at"] = "2020-01-01T00:00:00-05:00"
        set_totals(root, "beta-linux", old)
        check_true("the new machine really is OLDER than the document",
                   old["generated_at"] < doc_at, f"{old['generated_at']} vs {doc_at}")

        st, why = D.document_state(fleet, root, "root")
        check("a rollup missing a machine older than itself is STALE", st, D.STALE,
              "a timestamp comparison alone returns REGENERATED here")
        check_true("and the reason names the machine it never saw",
                   any("beta-linux" in w for w in why), why)
        check_true("the stale total still reads the one-machine figure",
                   "1,000,000" in fleet.read_text(encoding="utf-8"))
    finally:
        shutil.rmtree(root, ignore_errors=True)

    # -- 5. never silently deleted ------------------------------------------
    section("5  a document is moved, never deleted")
    root = fixture()
    try:
        D.render_all(root, log=root / "no-such-boot-log.jsonl")
        fleet = root / "human-readable" / "FLEET.md"
        before = fleet.read_bytes()
        t = dict(TOTALS["alpha-linux"])
        t["grand_total_tokens"] = 5
        set_totals(root, "alpha-linux", t)
        st, _ = D.document_state(fleet, root, "root")
        check("the document is stale to begin with", st, D.STALE)

        # A dry run must not remove anything.
        r = subprocess.run([sys.executable, str(HERE / "doc_render.py"), "archive",
                            "--root", str(root),
                            "--daemon-log", str(root / "no-such-boot-log.jsonl")],
                           capture_output=True, text=True)
        check("archive without --yes exits 0", r.returncode, 0, r.stderr[-400:])
        check_true("archive without --yes removes nothing", fleet.is_file())

        stamp, moved = D.archive_stale(root, log=root / "no-such-boot-log.jsonl")
        check_true("the stale document is gone from the working tree",
                   not fleet.is_file())
        copies = D.archived_copies(root, "human-readable/FLEET.md")
        check("exactly one archived copy", len(copies), 1, str(copies))
        check_true("the archived copy is byte-identical to what was removed",
                   copies and copies[0].read_bytes() == before)
        note = root / "testing-archive" / stamp / "documents" / "MOVED.md"
        check_true("a MOVED.md records what was relocated and why",
                   note.is_file() and "FLEET.md" in note.read_text(encoding="utf-8"))

        st, why = D.document_state(fleet, root, "root")
        check("a document that was archived reads as ARCHIVED, a legal state",
              st, D.ARCHIVED, f"{why}")
        check("ARCHIVED is not counted as stale",
              [r for r in D.stale_documents(root, log=root / "no-such-boot-log.jsonl")
               if r["document"].endswith("FLEET.md")], [])

        # And the other direction: removed with no copy anywhere. beta-linux,
        # deliberately — alpha's folder document went stale with alpha's
        # totals.json and was archived a moment ago, so deleting THAT one would
        # read as ARCHIVED and prove nothing about deletion.
        fd = root / "beta-linux" / "human-readable" / "FOLDER.md"
        check("beta's document was not archived — it was never stale",
              D.archived_copies(root, "beta-linux/human-readable/FOLDER.md"), [])
        # missing_ok, because the line above is a CHECK and not a guarantee.
        # When it fails — beta's document was archived after all, which is what
        # happens the moment every document reads as stale — a bare unlink()
        # raises FileNotFoundError and ends the run, and the two checks below it
        # are neither passed nor failed. The premise being wrong must make the
        # checks that rest on it FAIL, not disappear.
        fd.unlink(missing_ok=True)
        st, why = D.document_state(fd, root, "machine", machine=root / "beta-linux")
        check("a document deleted with no archived copy is MISSING", st, D.MISSING)
        check_true("MISSING is reported, not swallowed",
                   any(r["state"] == D.MISSING for r in
                       D.stale_documents(root, log=root / "no-such-boot-log.jsonl")))
    finally:
        shutil.rmtree(root, ignore_errors=True)

    # -- 6. absent is not zero ----------------------------------------------
    section("6  a folder that cannot be read is not a computer that spent nothing")
    root = fixture()
    try:
        set_totals(root, "beta-linux", "{ this is not json")
        D.render_all(root, log=root / "no-such-boot-log.jsonl")
        text = (root / "human-readable" / "FLEET.md").read_text(encoding="utf-8")
        check_true("the unreadable machine is UNCOUNTED", "UNCOUNTED" in text)
        check_true("the total says INCOMPLETE", "INCOMPLETE" in text)
        check_true("the unreadable machine is named", "beta-linux" in text)
        check_true("the rostered machine with no folder at all is named too",
                   "gamma-windows" in text)
        check_true("the total is the readable machine only, not a silent sum "
                   "with zeros in it", "1,000,000 tokens" in text, text[-1500:])
        check_true("and it does not claim to be complete",
                   "**COMPLETE**" not in text)

        fp = D.read_fingerprint(root / "human-readable" / "FLEET.md")
        # `read_fingerprint` has three answers and only one of them is a
        # fingerprint: None when the document carries no fence, and
        # {"_malformed": True} when the fenced JSON does not parse. `fp["inputs"]`
        # raised KeyError on the second and KILLED THE RUN — the rest of this
        # section and the whole of section 7 never executed, eleven checks that
        # were neither passed nor failed but simply not reached. A document that
        # cannot state its inputs is a FAILING CHECK here; it is never an
        # exception, because an exception ends the suite and a failure does not.
        inputs = fp.get("inputs") if isinstance(fp, dict) else None
        check_true("the document carries a readable input fingerprint",
                   isinstance(inputs, list), repr(fp)[:300])
        states = {e.get("id"): e.get("state") for e in (inputs or [])}
        check("the fingerprint distinguishes unreadable from absent",
              [states.get("beta-linux"), states.get("gamma-windows")],
              ["unreadable", "absent"])

        # The daemon report: absent log and empty log must not read the same.
        d1 = D.render_daemon(root, log=root / "no-such-boot-log.jsonl")
        check_true("an absent daemon log reports ABSENT",
                   "ABSENT" in d1.read_text(encoding="utf-8"))
        (root / "boots.jsonl").write_text("", encoding="utf-8")
        d2 = D.render_daemon(root, log=root / "boots.jsonl")
        check_true("an empty daemon log reports EMPTY, not ABSENT",
                   "EMPTY" in d2.read_text(encoding="utf-8"))
    finally:
        shutil.rmtree(root, ignore_errors=True)

    # -- the fingerprint is readable by something that is not this file ------
    section("7  the fingerprint is self-describing")
    root = fixture()
    try:
        D.render_all(root, log=root / "no-such-boot-log.jsonl")
        raw = (root / "human-readable" / "FLEET.md").read_text(encoding="utf-8")
        check_true("it is in a fenced block a gate can find without importing "
                   "anything", "```input-fingerprint" in raw)
        # A document with no fence, or a fence that is not JSON, is what the
        # check above is FOR. Reading it must not raise here: an exception would
        # delete the seven checks below from the run, and this file has already
        # lost eleven that way once.
        try:
            body = raw.split("```input-fingerprint", 1)[1].split("```", 1)[0]
            fp = json.loads(body)
        except Exception as e:  # noqa: BLE001
            fp = {"_unreadable": f"{type(e).__name__}: {e}"}
        check("fingerprint_version is present", fp.get("fingerprint_version"), 1)
        check_true("it says which document it belongs to",
                   fp.get("document", "").endswith("FLEET.md"))
        check_true("it carries a digest", str(fp.get("digest", "")).startswith("sha256:"))
        # Same shape as section 6: no `inputs` key is a failing check, not a
        # KeyError that removes the rest of this section from the run. The count
        # declared in PLAN is what makes a short loop here visible at all.
        inputs = fp.get("inputs") if isinstance(fp, dict) else None
        check_true("the fenced fingerprint lists its inputs",
                   isinstance(inputs, list), repr(fp)[:300])
        for e in (inputs or []):
            check_true(f"input {e.get('id')} carries the three fields PLAN "
                       f"P5.8 names",
                       {"id", "state", "scanner_version", "generated_at"} <= set(e))
        check("the digest recomputed from the tree matches",
              fp.get("digest"), D.tree_fingerprint(root, "root")["digest"])
    finally:
        shutil.rmtree(root, ignore_errors=True)


def audit_check_count():
    """Did every section run, and did each run every check it declares?

    THE GUARD THAT WOULD HAVE CAUGHT THE KeyError. Its own three checks are
    `counted=False` — they belong to no section, and both totals below are taken
    before any of them runs, so the guard cannot pad its own arithmetic.
    """
    reached = {s[0] for s in SECTIONS}
    never = [t for t, _ in PLAN if t not in reached]
    short = {t: (ran, declared) for t, declared, ran in SECTIONS
             if ran != declared}
    ran_total = sum(ran for _, _, ran in SECTIONS)
    want_total = sum(declared for _, declared in PLAN)

    print("\ncount  the suite ran every check it declares")
    check("every section in the plan was reached", never, [],
          "a section that never ran has not passed the checks inside it; this "
          "is the line that turns a crash from silence into a failure",
          counted=False)
    check("every section ran the number of checks it declares", short, {},
          "got {section: (ran, declared)} — a section that died part way "
          "through comes up short here and nowhere else", counted=False)
    check("and the suite ran the number of checks the plan declares in total",
          ran_total, want_total, "", counted=False)


def main():
    try:
        import doc_render                                       # noqa: F401
    except Exception as e:  # noqa: BLE001
        print("  FAIL  doc_render.py is importable")
        print(f"        {e.__class__.__name__}: {e}")
        print("\n  The document structure does not exist. Nothing below can run.")
        print("\n1 failed check")
        return 1
    try:
        run_sections()
    except BaseException as e:  # noqa: BLE001 - a crash must not end the report
        import traceback
        traceback.print_exc()
        FAILED.append(f"the suite crashed before it finished: "
                      f"{type(e).__name__}: {e}")
    audit_check_count()

    print()
    if FAILED:
        print(f"{len(FAILED)} failed check(s):")
        for f in FAILED:
            print(f"  - {f}")
        return 1
    print("every check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
