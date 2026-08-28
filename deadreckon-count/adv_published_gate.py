#!/usr/bin/env python3
"""Can the gate see a wrong PUBLISHED number?

    python3 adv_published_gate.py
    python3 adv_published_gate.py --gate /path/to/other/check_consistency.py

check_consistency.py compared totals.json to totals.json. A grep of it for
ALL-COMPUTERS, BY-COMPUTER, README, STATS, LIFETIME returned nothing — it had
never opened a published document — and that single fact is why five mutually
exclusive fleet totals sat at one commit under a banner reading "38 checks, 0
failed". Every one of those checks was true. The parts summed to the whole they
were told to sum. Nothing compared the whole to what got PUBLISHED.

WHY THE DOCUMENTS HERE ARE GENERATED AND NOT WRITTEN BY HAND

A fixture whose Markdown I typed myself would prove only that the parser reads
MY format. So every scenario builds machine folders and then runs the repo's own
`combine.py`, `stats_page.py`, `fun_stats.py` and `monthly.py` over them — the
same four `update.py` runs, in the same order. The documents under test are the
real ones, in the real shape, and the CONTROL scenario asserts the gate finds
nothing wrong with them. Without that control an attack scenario proves nothing:
a gate that failed on every document would pass every attack here and be
useless, and a check that fires on correct data is the false alarm this project
has already had to remove twice.

Then one thing is changed, and only one:

    a figure is edited            a total in ALL-COMPUTERS.json is lowered
    a row is deleted              one machine's row leaves a table, the All
                                  row keeps the full sum, so every partition
                                  still adds up
    a machine arrives late        a folder is committed AFTER the documents
                                  were generated — nothing is edited at all,
                                  and this is P2.1 verbatim
    a document is deleted         it was committed once and is gone
    a document's shape moves      the headline sentence is removed, so the
                                  parser can no longer find the figure

The last one is the one that matters most in a year's time. A parser that
returns nothing for a document it cannot read reports agreement, which is this
repository's signature bug wearing the gate's own clothes: ABSENT LOOKS EXACTLY
LIKE ZERO.

Two more scenarios cover the assertions that used to restate their own premise —
`chk(name, 0, 0)` inside an `if` that had already decided the answer:

    a hollow retire               the machine is "safe in testing-archive" and
                                  the archived copy holds less than git does
    a recount that lost sessions  the scanner_version changed, so the drop was
                                  called a recount; the session inventory fell
                                  too, which re-counting cannot do

Neither needs a real git repository: both ask git a question, so git is stubbed
on PATH with a script that answers from a JSON script. That makes the answer the
variable under test rather than a side effect of how the fixture was committed.
"""

import argparse
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

PASS, FAIL, ERROR = [], [], []

# Which scenario is running, how many checks each recorded, and which of them
# could not run at all. See EXPECTED_CHECKS.
CURRENT = None
BY_SCENARIO = {}
ERRORED = set()


def check(name, got, want, why=""):
    BY_SCENARIO[CURRENT] = BY_SCENARIO.get(CURRENT, 0) + 1
    (PASS if got == want else FAIL).append((name, got, want, why))


# --------------------------------------------------------------------------
# a fleet, planted


def _split(total):
    """Four buckets that add to `total`, the way a real account's do."""
    out = int(total * 0.02)
    cc = int(total * 0.03)
    inp = int(total * 0.01)
    return {"input_tokens": inp, "cache_creation_input_tokens": cc,
            "cache_read_input_tokens": total - inp - cc - out,
            "output_tokens": out}


def plant_machine(root, folder, label, *, account, total, extra_cli=0,
                  day="2026-01-05", stamp="2026-01-06T00:00:00+00:00"):
    """One machine folder: totals.json, sessions.json, by_account.csv.

    Every internal invariant the gate already checked holds by construction —
    models sum to the account, buckets sum to the account, accounts sum to the
    machine, sessions sum to the same figure. That is deliberate: the defects
    this file plants have to survive all of those, because in the real repository
    they did.
    """
    f = _split(total)
    totals = {
        "machine": label, "generated_at": stamp, "scanner_version": "adv",
        "grand_total_tokens": total,
        "accounts": [{
            "account": account, "config_dir": f"/home/op/{folder}/.claude",
            "grand_total": total, "sessions": 1, "turns": 3,
            "totals": f, "by_model": {"claude-opus-5": f},
            "by_day": {day: total},
        }],
    }
    (paths.machine(root / folder) / "totals.json").write_text(
        json.dumps(totals, indent=1), encoding="utf-8")

    sess = [{
        "cli": "claude", "session_id": f"{folder}-claude", "account": account,
        "project": "p", "start": f"{day}T01:00:00Z", "end": f"{day}T02:00:00Z",
        "turns": 3, "tokens": f, "duration_min": 60.0,
        "duration_tight_min": 60.0, "elapsed_min": 60.0, "total": total,
        "sent": total - f["output_tokens"], "received": f["output_tokens"],
        "model": "claude-opus-5", "provider": "anthropic", "billed": True,
    }]
    if extra_cli:
        g = _split(extra_cli)
        sess.append({
            "cli": "gemini", "session_id": f"{folder}-gemini",
            "account": "gemini (local)", "project": "p",
            "start": f"{day}T03:00:00Z", "end": f"{day}T04:00:00Z",
            "turns": 2, "tokens": g, "duration_min": 60.0,
            "duration_tight_min": 60.0, "elapsed_min": 60.0,
            "total": extra_cli, "sent": extra_cli - g["output_tokens"],
            "received": g["output_tokens"], "model": "gemini-3-pro-preview",
            "provider": "google", "billed": True,
        })
    (paths.machine(root / folder) / "sessions.json").write_text(
        json.dumps({"machine": label, "generated_at": stamp,
                    "scanner_version": "adv", "stats_cache": [],
                    "readers": [{"cli": "claude", "installed": True},
                                {"cli": "gemini", "installed": bool(extra_cli)}],
                    "sessions": sess}, indent=1), encoding="utf-8")

    (paths.machine(root / folder) / "by_account.csv").write_text(
        "account,config_dir,sessions,turns,input_tokens,"
        "cache_creation_input_tokens,cache_read_input_tokens,output_tokens,total\n"
        f"{account},/home/op/{folder}/.claude,1,3,{f['input_tokens']},"
        f"{f['cache_creation_input_tokens']},{f['cache_read_input_tokens']},"
        f"{f['output_tokens']},{total}\n", encoding="utf-8")
    (paths.machine(root / folder) / "hardware.json").write_text(
        json.dumps({"hostname": f"host-{folder}", "scanner_version": "adv",
                    "hardware": {"cpu_logical": 4, "memory_gb": 8}}),
        encoding="utf-8")


FLEET = (("alpha", "Alpha", "one@x", 1_000_000_000, 200_000_000),
         ("bravo", "Bravo", "two@x", 400_000_000, 0),
         ("charlie", "Charlie", "three@x", 25_000_000, 3_000_000))

README_STUB = """# fixture

<!-- BEGIN OVERVIEW -->
<!-- END OVERVIEW -->

<!-- BEGIN CLI -->
<!-- END CLI -->

<!-- BEGIN ACCOUNTS -->
<!-- END ACCOUNTS -->
"""


def build(tmp, fleet=FLEET, git=None):
    """A repository with `fleet` planted and the real documents generated."""
    root = tmp / "repo"
    root.mkdir(parents=True)
    for p in SRC.iterdir():
        if p.suffix == ".py":
            shutil.copy2(p, root / p.name)
    (root / "README.md").write_text(README_STUB, encoding="utf-8")
    (root / "accounts.json").write_text(json.dumps({"accounts": [],
                                                    "profiles": []}),
                                        encoding="utf-8")
    (root / "machines.json").write_text(json.dumps(
        {"machines": [{"folder": f, "label": l} for f, l, *_ in fleet]}),
        encoding="utf-8")
    for folder, label, account, total, extra in fleet:
        plant_machine(root, folder, label, account=account, total=total,
                      extra_cli=extra)
    generate(root)
    if git is not None:
        (tmp / "gitscript.json").write_text(json.dumps(git), encoding="utf-8")
    return root


def generate(root):
    """The four generators `update.py` runs, in the order it runs them."""
    for script in ("combine.py", "stats_page.py", "fun_stats.py", "monthly.py"):
        r = subprocess.run([sys.executable, script], cwd=root,
                           capture_output=True, text=True, timeout=900)
        if r.returncode:
            raise RuntimeError(f"{script} failed in the fixture:\n"
                               f"{r.stdout[-800:]}\n{r.stderr[-800:]}")


# --------------------------------------------------------------------------
# a stubbed git, so "what did the last commit say" is an input

GIT_STUB = r'''#!/usr/bin/env python3
"""Answers the three questions check_consistency.py asks git, from a script."""
import json, os, pathlib, sys

spec = json.loads(pathlib.Path(os.environ["ADV_GIT_SCRIPT"]).read_text())
a = sys.argv[1:]
if a[:1] == ["log"] and "--diff-filter=A" in a:
    paths = [x for x in a[a.index("--") + 1:]] if "--" in a else []
    out = []
    for p in paths:
        out += spec.get("added", {}).get(p, [])
    print("\n".join(out))
    sys.exit(0)
if a[:2] == ["log", "-1"]:
    p = a[a.index("--") + 1] if "--" in a else ""
    v = spec.get("last_commit", {}).get(p)
    if v is None:
        sys.exit(1)
    print(v)
    sys.exit(0)
if a[:1] == ["show"]:
    v = spec.get("show", {}).get(a[1])
    if v is None:
        sys.exit(1)
    print(json.dumps(v) if not isinstance(v, str) else v)
    sys.exit(0)
sys.exit(1)
'''


def with_git_stub(tmp, spec):
    """A PATH whose `git` answers from `spec`. Nothing real is committed."""
    binp = tmp / "bin"
    binp.mkdir(exist_ok=True)
    (binp / "git").write_text(GIT_STUB, encoding="utf-8")
    (binp / "git").chmod(0o755)
    f = tmp / "gitscript.json"
    f.write_text(json.dumps(spec), encoding="utf-8")
    return dict(os.environ, PATH=f"{binp}{os.pathsep}{os.environ['PATH']}",
                ADV_GIT_SCRIPT=str(f))


# --------------------------------------------------------------------------
# running the gate


def gate(root, env=None, gate_src=None):
    """{check name: PASS|FAIL|WARN} plus the raw output.

    The summary line is looked for FIRST. `grep -c FAIL` on a file that does not
    exist returns 0, and reading a pass out of an empty result is a mistake this
    project has made inside this very session — so a run that did not reach its
    own summary is reported as an ERROR and never as agreement.
    """
    if gate_src:
        shutil.copy2(gate_src, root / "check_consistency.py")
    r = subprocess.run([sys.executable, "check_consistency.py"], cwd=root,
                       capture_output=True, text=True, timeout=1800,
                       env=env or os.environ)
    out = r.stdout + r.stderr
    if " checks, " not in out:
        return None, out
    tags = {}
    for line in out.splitlines():
        s = line.strip()
        for t in ("PASS", "FAIL", "WARN"):
            if s.startswith(t + " "):
                tags.setdefault(s[len(t):].strip(), t)
                break
    return tags, out


def verdict(tags, fragment):
    """The tag of the first check whose name contains `fragment`, or None."""
    for name, tag in tags.items():
        if fragment in name:
            return tag
    return None


def fails(tags, fragment):
    return verdict(tags, fragment) in ("FAIL", "WARN")


# --------------------------------------------------------------------------
# scenarios


def s_control(tmp, gate_src):
    """Documents straight out of the generators must satisfy the gate.

    Run FIRST and reported first. Every scenario below is "the gate now
    complains", and that is worth nothing from a gate that complains always.
    """
    root = build(tmp)
    tags, out = gate(root, gate_src=gate_src)
    if tags is None:
        ERROR.append(("control", out[-1200:]))
        return
    # NON-EMPTY FIRST, THEN PASSING. This control used to be one line —
    #
    #     wrong = [n for n, t in tags.items()
    #              if t == "FAIL" and "matches the machine folders" in n]
    #     check(..., wrong, [])
    #
    # — and it CERTIFIED NOTHING. Delete published_gate() from
    # check_consistency.py and no check carries that name, so nothing matches,
    # so `wrong` is empty, so the control PASSES: the gate that opens no
    # published document at all is signed off by the one scenario written to
    # prove the gate works. ABSENT LOOKS EXACTLY LIKE ZERO, inside the suite
    # that exists to hunt it. Never assert "none of X failed" without first
    # asserting there is an X.
    matched = sorted(n for n in tags if "matches the machine folders" in n)
    check("CONTROL: the gate opened the published documents at all", bool(matched),
          True,
          f"no check is named '<document> matches the machine folders'; the "
          f"gate ran {len(tags)} check(s) and not one of them compared a "
          f"published figure to the machine folders")
    check("CONTROL: generated documents pass the gate",
          sorted(n for n in matched if tags[n] == "FAIL"), [],
          "the generators wrote these from the same folders the gate reads; "
          "anything failing here is the gate crying wolf")
    check("CONTROL: the gate ran to its summary", tags is not None, True)


def s_edited_figure(tmp, gate_src):
    """One figure lowered in ALL-COMPUTERS.json, nothing else touched."""
    root = build(tmp)
    f = paths.machine(root) / "ALL-COMPUTERS.json"
    d = json.loads(f.read_text(encoding="utf-8"))
    d["grand_total_tokens"] = d["grand_total_tokens"] - 500_000_000
    f.write_text(json.dumps(d, indent=2), encoding="utf-8")
    tags, out = gate(root, gate_src=gate_src)
    if tags is None:
        ERROR.append(("edited figure", out[-1200:]))
        return
    check("a lowered grand_total_tokens is reported",
          fails(tags, "ALL-COMPUTERS.json matches"), True,
          "500 M removed from the fleet total the front page derives from")


def s_deleted_row(tmp, gate_src):
    """A machine's row leaves BY-COMPUTER's table; the All row keeps the sum.

    The document still adds up — every remaining row is right and the total is
    right — which is exactly how a machine disappears from a report without any
    figure moving.
    """
    root = build(tmp)
    f = paths.human(root) / "BY-COMPUTER.md"
    kept = [l for l in f.read_text(encoding="utf-8").splitlines()
            if not l.startswith("| **Bravo** |")]
    f.write_text("\n".join(kept) + "\n", encoding="utf-8")
    tags, out = gate(root, gate_src=gate_src)
    if tags is None:
        ERROR.append(("deleted row", out[-1200:]))
        return
    check("a machine deleted from a published table is reported",
          fails(tags, "every figure the gate certifies was found"), True,
          "Bravo's row is gone and the All row still carries its tokens")


def s_stale_after_new_machine(tmp, gate_src):
    """P2.1 verbatim: a machine arrives AFTER the documents were generated.

    Nothing is edited. Every document is exactly what the generators wrote. The
    tree simply moved on, which is the entire mechanism behind "3 of 6 computers
    scanned" sitting on the front page above five scanned folders.
    """
    root = build(tmp, fleet=FLEET[:2])
    plant_machine(root, "charlie", "Charlie", account="three@x",
                  total=25_000_000, extra_cli=3_000_000)
    (root / "machines.json").write_text(json.dumps(
        {"machines": [{"folder": f, "label": l} for f, l, *_ in FLEET]}),
        encoding="utf-8")
    tags, out = gate(root, gate_src=gate_src)
    if tags is None:
        ERROR.append(("stale after new machine", out[-1200:]))
        return
    check("documents that predate a new machine are reported",
          fails(tags, "README.md matches") or
          fails(tags, "every figure the gate certifies was found"), True,
          "charlie is scanned and committed; every published rollup still "
          "describes a two-machine fleet")


def s_deleted_document(tmp, gate_src):
    """A document that was committed once and is gone."""
    root = build(tmp)
    (paths.human(root) / "STATS.md").unlink()
    env = with_git_stub(tmp, {"added": {f"{paths.HUMAN}/STATS.md":
                                        [f"{paths.HUMAN}/STATS.md"]}})
    tags, out = gate(root, env=env, gate_src=gate_src)
    if tags is None:
        ERROR.append(("deleted document", out[-1200:]))
        return
    check("a published document that vanished is reported",
          fails(tags, "every published document is on disk"), True,
          "STATS.md was committed here once and is not on disk")


def s_shape_moved(tmp, gate_src):
    """The headline sentence is removed, so the parser cannot find the figure.

    The document is otherwise untouched and still looks entirely reasonable. A
    parser that quietly finds nothing here reports agreement, and the gate goes
    back to certifying a document it is no longer reading.
    """
    root = build(tmp)
    f = paths.human(root) / "BY-COMPUTER.md"
    kept = [l for l in f.read_text(encoding="utf-8").splitlines()
            if "tokens of Claude Code across" not in l]
    f.write_text("\n".join(kept) + "\n", encoding="utf-8")
    tags, out = gate(root, gate_src=gate_src)
    if tags is None:
        ERROR.append(("shape moved", out[-1200:]))
        return
    check("a figure the parser can no longer find is reported",
          fails(tags, "every figure the gate certifies was found"), True,
          "the headline is gone; not finding it must not read as agreeing "
          "with it")


def s_unreadable_document(tmp, gate_src):
    """A published document that is on disk and does not parse.

    The trap the section closing this hole could most easily have fallen into
    itself: `except: return None` produces no claims for the file, and no claims
    is exactly what a document in perfect agreement produces too. Present and
    unreadable has to look different from present and right.
    """
    root = build(tmp)
    (paths.machine(root) / "lifetime.json").write_text(
        '{"tokens": 123, "sessi', encoding="utf-8")
    tags, out = gate(root, gate_src=gate_src)
    if tags is None:
        ERROR.append(("unreadable document", out[-1200:]))
        return
    check("a published document that does not parse is reported",
          fails(tags, "every figure the gate certifies was found"), True,
          "lifetime.json is truncated mid-key; skipping it would read as "
          "agreeing with it")


def s_edited_markdown_figure(tmp, gate_src):
    """A figure edited inside a Markdown table, every other row left alone.

    The JSON rollups are the easy case. What actually gets read is the Markdown,
    and a single number changed in a table is invisible to any check that only
    asks whether the parts sum to the whole — because the whole was changed too.
    """
    root = build(tmp)
    f = paths.human(root) / "BY-ACCOUNT.md"
    body = f.read_text(encoding="utf-8")
    body = body.replace("1,000,000,000", "700,000,000")
    f.write_text(body, encoding="utf-8")
    tags, out = gate(root, gate_src=gate_src)
    if tags is None:
        ERROR.append(("edited markdown figure", out[-1200:]))
        return
    check("a figure edited inside a Markdown table is reported",
          fails(tags, "BY-ACCOUNT.md matches"), True,
          "alpha's account row and every total derived from it now say "
          "700,000,000 where the folder says 1,000,000,000")


def s_csv_disagrees(tmp, gate_src):
    """by_account.csv and totals.json disagree — one scan, two writers."""
    root = build(tmp)
    c = paths.machine(root / "alpha") / "by_account.csv"
    lines = c.read_text(encoding="utf-8").splitlines()
    cols = lines[1].split(",")
    cols[-1] = str(int(cols[-1]) - 90_000_000)
    c.write_text(lines[0] + "\n" + ",".join(cols) + "\n", encoding="utf-8")
    tags, out = gate(root, gate_src=gate_src)
    if tags is None:
        ERROR.append(("csv disagrees", out[-1200:]))
        return
    check("a second artifact that disagrees with the total is reported",
          fails(tags, "re-adds from a second artifact"), True,
          "the CSV is 90 M short of the JSON it was written beside")


def s_csv_missing(tmp, gate_src):
    """A machine contributes to the grand total with nothing to corroborate it."""
    root = build(tmp)
    (paths.machine(root / "alpha") / "by_account.csv").unlink()
    tags, out = gate(root, gate_src=gate_src)
    if tags is None:
        ERROR.append(("csv missing", out[-1200:]))
        return
    check("an uncorroborated machine total is reported",
          fails(tags, "second artifact to check it against"), True,
          "alpha's 1 B is in the fleet total and nothing else on disk says so")


def s_hollow_retire(tmp, gate_src):
    """The retire exemption, with an archive that does not hold the machine.

    `mkdir` plus a stub totals.json is the whole forgery. The old assertion was
    chk(name, 0, 0) inside `if was_retired:` and could not see it — nor could
    anything else, because a retire is the one absence the gate is told to
    forgive.
    """
    root = build(tmp)
    shutil.rmtree(root / "bravo")
    arc = root / "testing-archive" / "2099-01-01T00-00-00" / "stale-machines" / "bravo"
    (paths.machine(arc) / "totals.json").write_text(
        json.dumps({"machine": "Bravo", "grand_total_tokens": 0,
                    "accounts": []}), encoding="utf-8")
    # The commit that retired bravo is the one that REMOVED it, so HEAD does not
    # hold the file and only its parent does. That is the real shape of a retire,
    # and a check that asked HEAD alone would find nothing and exempt the
    # forgery.
    env = with_git_stub(tmp, {
        "last_commit": {f"bravo/{paths.MACHINE}/totals.json":
                        "abc1234 2026-01-07T00:00:00+00:00"},
        "show": {f"abc1234^:bravo/{paths.MACHINE}/totals.json":
                 json.dumps({"machine": "Bravo",
                             "grand_total_tokens": 400_000_000})},
    })
    tags, out = gate(root, env=env, gate_src=gate_src)
    if tags is None:
        ERROR.append(("hollow retire", out[-1200:]))
        return
    check("a retire whose archive holds nothing is reported",
          fails(tags, "absent by RETIRE"), True,
          "the archived copy holds 0 where git last committed 400,000,000")


def s_recount_lost_sessions(tmp, gate_src):
    """A drop labelled RECOUNT that also lost sessions.

    scanner_version says the counting changed. It cannot say whether the
    transcripts are still there, and a deletion moves the total the same way.
    The old assertion restated the branch it was already inside.
    """
    root = build(tmp)
    tf = paths.machine(root / "alpha") / "totals.json"
    before = json.loads(tf.read_text(encoding="utf-8"))
    before["grand_total_tokens"] *= 2
    before["accounts"][0]["grand_total"] *= 2
    before["scanner_version"] = "older"
    sf = paths.machine(root / "alpha") / "sessions.json"
    prev_sessions = json.loads(sf.read_text(encoding="utf-8"))
    prev_sessions["sessions"] = prev_sessions["sessions"] * 6   # 12 -> now 2
    env = with_git_stub(tmp, {
        "show": {f"HEAD:alpha/{paths.MACHINE}/totals.json": json.dumps(before),
                 f"HEAD:alpha/{paths.MACHINE}/sessions.json":
                     json.dumps(prev_sessions)},
        "last_commit": {}, "added": {},
    })
    tags, out = gate(root, env=env, gate_src=gate_src)
    if tags is None:
        ERROR.append(("recount lost sessions", out[-1200:]))
        return
    check("a RECOUNT that also lost sessions is reported",
          fails(tags, "RECOUNT, not a loss"), True,
          "half the tokens and five-sixths of the sessions went away; "
          "re-counting cannot lose a session")


SCENARIOS = (s_control, s_edited_figure, s_deleted_row,
             s_stale_after_new_machine, s_deleted_document, s_shape_moved,
             s_unreadable_document, s_edited_markdown_figure,
             s_csv_disagrees, s_csv_missing, s_hollow_retire,
             s_recount_lost_sessions)

# How many checks each scenario records when it runs to the END, asserted below.
#
# Every scenario here has the same early exit — `if tags is None: return` — and
# that branch is taken whenever the gate fails to reach its own summary, which
# is exactly when something is most wrong. Without this, the run prints
# "12 scenarios, 0 failed" while eleven of them recorded no verdict at all. A
# suite that exited early has not passed the checks it never reached, and the
# summary line cannot tell the difference: it counts what RAN.
EXPECTED_CHECKS = {
    "s_control": 3,
    "s_edited_figure": 1,
    "s_deleted_row": 1,
    "s_stale_after_new_machine": 1,
    "s_deleted_document": 1,
    "s_shape_moved": 1,
    "s_unreadable_document": 1,
    "s_edited_markdown_figure": 1,
    "s_csv_disagrees": 1,
    "s_csv_missing": 1,
    "s_hollow_retire": 1,
    "s_recount_lost_sessions": 1,
}


def audit_check_count():
    """Did every scenario record every verdict it declares?

    A scenario already reported as ERROR declares 0 — it announced that it could
    not run, which is reported and is not silence. These two checks are
    deliberately outside EXPECTED_CHECKS: both totals are taken before either
    of them runs.
    """
    global CURRENT
    want = {s.__name__: (0 if s.__name__ in ERRORED
                         else EXPECTED_CHECKS[s.__name__]) for s in SCENARIOS}
    got = {s.__name__: BY_SCENARIO.get(s.__name__, 0) for s in SCENARIOS}
    CURRENT = "audit_check_count"
    check("every scenario recorded every check it declares",
          {k: (got[k], want[k]) for k in want if got[k] != want[k]}, {},
          "got {scenario: (recorded, declared)}; a scenario that returned early "
          "records fewer verdicts than it has, and one that crashed records none")
    check("and the suite recorded the number of checks it declares in total",
          sum(got.values()), sum(want.values()),
          "the summary line counts what ran; this is what should have run")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", help="run the scenarios against THIS "
                                   "check_consistency.py instead of the one "
                                   "in the repo (used to prove the adversary "
                                   "was red before the fix)")
    a = ap.parse_args()
    global CURRENT
    src = pathlib.Path(a.gate).resolve() if a.gate else None
    for s in SCENARIOS:
        CURRENT = s.__name__
        before = len(ERROR)
        with tempfile.TemporaryDirectory(prefix="advpub-") as d:
            try:
                s(pathlib.Path(d), src)
            except Exception as e:                              # noqa: BLE001
                ERROR.append((s.__name__, f"{type(e).__name__}: {e}"))
        if len(ERROR) > before:
            ERRORED.add(s.__name__)
    audit_check_count()
    for name, got, want, why in PASS:
        print(f"  PASS  {name}")
    for name, got, want, why in FAIL:
        print(f"  FAIL  {name}\n        got {got!r}, want {want!r}"
              + (f"\n        {why}" if why else ""))
    for name, why in ERROR:
        print(f"  ERROR {name}\n        {why}")
    print(f"\n{len(PASS) + len(FAIL) + len(ERROR)} scenarios, "
          f"{len(FAIL)} failed, {len(ERROR)} could not run")
    return 1 if FAIL or ERROR else 0


if __name__ == "__main__":
    sys.exit(main())
