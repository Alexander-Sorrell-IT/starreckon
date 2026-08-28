#!/usr/bin/env python3
"""What does the gate say when it cannot ask git, and when there is nothing
to corroborate a total with?

    python3 adv_gate_git_blind.py
    python3 adv_gate_git_blind.py --gate /path/to/other/check_consistency.py

check_consistency.py leans on git for the one distinction the filesystem cannot
make: a machine folder that was never here, versus one that was here and is
gone. A document this checkout never writes, versus one it committed and lost.
That distinction is the whole reason `no machine folders — nothing to check`
does not exit 0 on a repository somebody emptied.

It asks git by running `git log` and reading `returncode == 0`. Three call sites
then collapse "git said nothing" and "git could not answer" into one answer, and
the answer they pick is the innocent one:

    main(), empty tree      known = [...] if ever.returncode == 0 else []
    vanished machines       if r.returncode != 0 ...: continue
    published_gate          ever = r.returncode == 0 and any(...)

Outside a git repository every one of those calls returns 128. Nothing here is
hypothetical about that: `docker/`, `dist/`, the corpus export and every tarball
of this tree are copies without `.git`, and the gate is meant to run before
publication wherever the publication is assembled.

So this file runs the real gate in a directory that is not a git repository —
no stub, no mock, the actual `git` binary answering the way it actually answers —
and asks what the gate reports about losses it can no longer see.

    an emptied fleet        every folder gone, git cannot say whether they were
                            ever committed. "none was ever committed" is a fact
                            the gate did not establish.
    a vanished folder       on the roster, absent from disk, history unreadable
    lost documents          README.md and the rest absent, and the gate cannot
                            tell "never written here" from "written and lost"

And one more that needs no git at all:

    nothing to corroborate  every by_account.csv removed, so the check named
                            `the fleet total re-adds from a second artifact`
                            adds nothing on both sides and compares 0 to 0

THE CONTROL IS THE POINT. The same fleet, in a real git repository with
everything committed, must produce none of those reports. A gate that fails
outside git AND inside it has not learned the distinction, it has just moved
from asserting innocence to asserting guilt — and a check that fires on correct
data is the false alarm this project has already had to remove twice.
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


def check(name, got, want, why=""):
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


def plant_machine(root, folder, label, account, total, *, csv=True,
                  day="2026-01-05", stamp="2026-01-06T00:00:00+00:00"):
    """One machine folder that satisfies every invariant the gate already had.

    Models sum to the account, buckets sum to the account, accounts sum to the
    machine, and sessions reach the same figure. The defects planted below have
    to survive all of that, because in the real repository they did.
    """
    f = _split(total)
    md = paths.machine(root / folder)
    md.joinpath("totals.json").write_text(json.dumps({
        "machine": label, "generated_at": stamp, "scanner_version": "adv",
        "grand_total_tokens": total,
        "accounts": [{
            "account": account, "config_dir": f"/home/op/{folder}/.claude",
            "grand_total": total, "sessions": 1, "turns": 3,
            "totals": f, "by_model": {"claude-opus-5": f},
            "by_day": {day: total},
        }],
    }, indent=1), encoding="utf-8")

    md.joinpath("sessions.json").write_text(json.dumps({
        "machine": label, "generated_at": stamp, "scanner_version": "adv",
        "stats_cache": [], "readers": [{"cli": "claude", "installed": True}],
        "sessions": [{
            "cli": "claude", "session_id": f"{folder}-claude",
            "account": account, "project": "p",
            "start": f"{day}T01:00:00Z", "end": f"{day}T02:00:00Z",
            "turns": 3, "tokens": f, "duration_min": 60.0,
            "duration_tight_min": 60.0, "elapsed_min": 60.0, "total": total,
            "sent": total - f["output_tokens"], "received": f["output_tokens"],
            "model": "claude-opus-5", "provider": "anthropic", "billed": True,
        }],
    }, indent=1), encoding="utf-8")

    md.joinpath("hardware.json").write_text(json.dumps(
        {"hostname": f"host-{folder}", "scanner_version": "adv",
         "hardware": {"cpu_logical": 4, "memory_gb": 8}}), encoding="utf-8")

    if csv:
        md.joinpath("by_account.csv").write_text(
            "account,config_dir,sessions,turns,input_tokens,"
            "cache_creation_input_tokens,cache_read_input_tokens,"
            "output_tokens,total\n"
            f"{account},/home/op/{folder}/.claude,1,3,{f['input_tokens']},"
            f"{f['cache_creation_input_tokens']},{f['cache_read_input_tokens']},"
            f"{f['output_tokens']},{total}\n", encoding="utf-8")


FLEET = (("alpha", "Alpha", "one@x", 1_000_000_000),
         ("bravo", "Bravo", "two@x", 400_000_000))


def build(tmp, name, fleet=FLEET, roster=None, csv=True, gate_src=None):
    """A tree with `fleet` planted, `roster` in machines.json, and no .git."""
    root = tmp / name
    root.mkdir(parents=True)
    for p in SRC.iterdir():
        if p.suffix == ".py":
            shutil.copy2(p, root / p.name)
    if gate_src:
        shutil.copy2(gate_src, root / "check_consistency.py")
    (root / "accounts.json").write_text(
        json.dumps({"accounts": [], "profiles": []}), encoding="utf-8")
    listed = roster if roster is not None else [f for f, *_ in fleet]
    (root / "machines.json").write_text(json.dumps(
        {"machines": [{"folder": f, "label": f.title()} for f in listed]}),
        encoding="utf-8")
    for folder, label, account, total in fleet:
        plant_machine(root, folder, label, account, total, csv=csv)
    return root


def commit_everything(root):
    """Turn the tree into a real git repository with one commit in it.

    The control. Nothing is stubbed: the same `git` binary that returns 128 in
    the scenarios above returns 0 here, and the gate is asked the same
    questions.
    """
    env = dict(os.environ, GIT_AUTHOR_NAME="adv", GIT_AUTHOR_EMAIL="a@b",
               GIT_COMMITTER_NAME="adv", GIT_COMMITTER_EMAIL="a@b",
               GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull)
    for args in (["init", "-q", "-b", "main"], ["add", "-A"],
                 ["commit", "-q", "-m", "fixture"]):
        r = subprocess.run(["git"] + args, cwd=root, env=env,
                           capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(f"git {args[0]} failed: {r.stdout}{r.stderr}")


# --------------------------------------------------------------------------
# running the gate


def gate(root):
    """({check name: PASS|FAIL|WARN}, exit status, raw output).

    The summary line is looked for FIRST. Reading a pass out of a run that
    never reached its own summary is the mistake this project made inside the
    session that produced this file, so a run without one is an ERROR and never
    agreement.
    """
    r = subprocess.run([sys.executable, "check_consistency.py"], cwd=root,
                       capture_output=True, text=True, timeout=1800)
    out = r.stdout + r.stderr
    tags = {}
    for line in out.splitlines():
        s = line.strip()
        for t in ("PASS", "FAIL", "WARN"):
            if s.startswith(t + " "):
                tags.setdefault(s[len(t):].strip(), t)
                break
    return tags, r.returncode, out


def tag_of(tags, fragment):
    """The tag of the first check whose name contains `fragment`, or None.

    None means the gate never printed a check by that name — which is the
    outcome most of these scenarios are about, and it must not be confused with
    a check that ran and passed.
    """
    for name, t in tags.items():
        if fragment in name:
            return t
    return None


def reported(tags, fragment):
    return tag_of(tags, fragment) in ("FAIL", "WARN")


# --------------------------------------------------------------------------
# scenarios


def s_control(tmp):
    """A real repository with everything committed: none of this may fire."""
    root = build(tmp, "control", gate_src=GATE)
    commit_everything(root)
    tags, code, out = gate(root)
    if not tags:
        ERROR.append(("control", out[-1500:]))
        return
    noise = sorted(n for n, t in tags.items()
                   if t in ("FAIL", "WARN")
                   and ("git" in n or "history could be read" in n
                        or "second artifact" in n))
    check("CONTROL: git works, so nothing is reported as unreadable", noise, [],
          "the same checks in a real repository with the fleet committed; "
          "anything here is the gate crying wolf outside its own evidence")


def s_emptied_fleet(tmp):
    """Every machine folder gone, and git cannot say whether they ever existed.

    The gate's own comment: "on a clone with one machine, rm -rf hp-laptop-linux
    produced exactly `no machine folders — nothing to check` and exit status 0.
    Deleting the entire fleet passed the audit that exists to notice deletion."
    That hole was closed by asking git. Outside a git repository the question
    cannot be asked, and the innocent answer is assumed again.
    """
    root = build(tmp, "emptied", fleet=(),
                 roster=["alpha", "bravo"], gate_src=GATE)
    tags, code, out = gate(root)
    check("an emptied fleet is not called clean when git cannot answer",
          code != 0, True,
          "machines.json lists two computers, no folder is on disk, and git "
          "cannot be asked whether they were ever committed. Exit 0 here "
          "states as fact something the gate did not establish")
    check("the run says git could not answer",
          "git" in out.lower() and "never committed" not in out, True,
          f"printed instead: {out.strip()[:160]!r}")


def s_vanished_folder(tmp):
    """A roster machine absent from disk, with its history unreadable.

    `no machine folder has disappeared` skips any folder git will not talk
    about — `if r.returncode != 0 ...: continue`, commented "never committed, so
    never scanned". Outside git that is every folder, so the check surveys
    nothing and passes.
    """
    root = build(tmp, "vanished", fleet=FLEET[:1],
                 roster=["alpha", "bravo"], gate_src=GATE)
    tags, code, out = gate(root)
    if not tags:
        ERROR.append(("vanished folder", out[-1500:]))
        return
    check("a folder the gate cannot check the history of is reported",
          reported(tags, "history could be read")
          or reported(tags, "no machine folder has disappeared"), True,
          "bravo is on the roster and not on disk; git cannot say whether it "
          "was committed once, and the gate reported neither fact")


def s_lost_documents(tmp):
    """Every published document absent, and git cannot say if they were here.

    `every published document is on disk` is fatal, and the escape hatch beside
    it — WARN, "never committed here, so this gate has never certified them" —
    exists for COVERAGE.md, which really is written into another checkout.
    Outside git every document falls into that hatch, so a rebuild that wrote
    nothing at all downgrades to a warning.
    """
    root = build(tmp, "lostdocs", gate_src=GATE)
    tags, code, out = gate(root)
    if not tags:
        ERROR.append(("lost documents", out[-1500:]))
        return
    check("missing documents are not waved through as 'written elsewhere'",
          tag_of(tags, "every published document is on disk") == "FAIL"
          or reported(tags, "history could be read")
          or reported(tags, "could not be asked"), True,
          "README.md, STATS.md and the rest are absent and the gate cannot "
          "establish that they belong to another checkout")


def s_nothing_to_corroborate(tmp):
    """No by_account.csv anywhere, so the corroboration check adds 0 to 0.

    `the fleet total re-adds from a second artifact` sums the CSVs on one side
    and the totals.json figures of the machines that HAD a CSV on the other.
    Remove every CSV and both sides are empty. It passes, fatally-named and
    having compared nothing — ABSENT LOOKS EXACTLY LIKE ZERO, inside the check
    written to corroborate a total from outside itself.
    """
    root = build(tmp, "nocsv", csv=False, gate_src=GATE)
    tags, code, out = gate(root)
    if not tags:
        ERROR.append(("nothing to corroborate", out[-1500:]))
        return
    check("a corroboration with nothing to corroborate does not read as PASS",
          tag_of(tags, "re-adds from a second artifact") != "PASS"
          or reported(tags, "was re-added from a second artifact"), True,
          "every by_account.csv is gone, so the check summed nothing on both "
          "sides and reported agreement")


def s_csv_disagrees(tmp):
    """One CSV lowered, so the two artifacts of one scan disagree.

    The other half of the corroboration question. Making the check fail when
    there is nothing to compare is worth nothing if it cannot also fail when
    there IS something and the two disagree — that would be a check made
    honest about its scope and still unable to fire. This is the successor to
    `machines partition the grand total`, which compared `sum(m[...] for m in
    machines)` to a `grand` computed four lines earlier by the same expression,
    and it has to earn the name.
    """
    root = build(tmp, "csvdrift", gate_src=GATE)
    c = paths.machine(root / "alpha") / "by_account.csv"
    lines = c.read_text(encoding="utf-8").splitlines()
    cells = lines[1].split(",")
    cells[-1] = str(int(cells[-1]) - 500_000_000)
    c.write_text("\n".join([lines[0], ",".join(cells)]) + "\n", encoding="utf-8")
    tags, code, out = gate(root)
    if not tags:
        ERROR.append(("csv disagrees", out[-1500:]))
        return
    check("a second artifact that disagrees is reported",
          tag_of(tags, "re-adds from a second artifact"), "FAIL",
          "by_account.csv is 500 M below the totals.json it was written beside")


def s_duplicate_folder(tmp):
    """One computer's folder copied under a second name, so it is added twice.

    The defect the original `machines partition the grand total` was named for
    and could not see: on a planted fleet with alpha's folder duplicated the
    grand total read 2,234,500,000 against a planted 1,234,500,000 and the file
    reported 28 checks, 0 failed. Nothing here asserts WHICH check catches it —
    only that a fleet total inflated by a copied folder does not pass.
    """
    root = build(tmp, "dupfolder",
                 fleet=FLEET + (("alpha-copy", "Alpha", "one@x",
                                 1_000_000_000),),
                 gate_src=GATE)
    # Committed, so git answers and the exit status is about the duplicate and
    # not about a gate that cannot read its own history. An assertion on `code`
    # in a tree where something else already fails is an assertion about the
    # something else.
    commit_everything(root)
    tags, code, out = gate(root)
    if not tags:
        ERROR.append(("duplicate folder", out[-1500:]))
        return
    check("a folder copied under a second name is named",
          tag_of(tags, "no two folders claim the same computer"), "FAIL",
          "alpha is counted twice in the fleet total, once per folder")
    check("a folder copied under a second name does not pass", code != 0, True,
          "the run must not exit 0 with a duplicated computer in the fleet")


def s_deleted_after_commit(tmp):
    """The fleet committed, then every folder deleted, with git still working.

    The control for the branch this file added. `if not answered:` was inserted
    directly after `if known:` in the empty-tree path, and an ordering mistake
    there would swap the two reports: a real deletion, which git CAN describe,
    coming out as "the history could not be read". So the same deletion is run
    where git answers, and the answer has to be the one that names the machines.

    Green before this session's change and green after it — the point of a
    control is that it does not move. It is here because the branch it guards
    is new, not because it caught anything.
    """
    root = build(tmp, "deleted", gate_src=GATE)
    commit_everything(root)
    for folder, *_ in FLEET:
        shutil.rmtree(root / folder)
    tags, code, out = gate(root)
    check("a committed fleet that was deleted is reported as a loss",
          code != 0 and "committed once" in out, True,
          f"exit {code}; printed {out.strip()[:200]!r}")
    check("and the deleted machines are named",
          all(f in out for f, *_ in FLEET), True,
          "the report has to say which computers are gone, not that some are")


SCENARIOS = (s_control, s_emptied_fleet, s_vanished_folder, s_lost_documents,
             s_nothing_to_corroborate, s_csv_disagrees, s_duplicate_folder,
             s_deleted_after_commit)
GATE = None


def main():
    global GATE
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", default=str(SRC / "check_consistency.py"),
                    help="the check_consistency.py under test")
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()
    GATE = pathlib.Path(a.gate).resolve()
    if not GATE.is_file():
        print(f"no gate at {GATE}")
        return 2

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="adv-gitblind-"))
    try:
        for s in SCENARIOS:
            try:
                s(tmp)
            except Exception as e:                              # noqa: BLE001
                ERROR.append((s.__name__, f"{type(e).__name__}: {e}"))
    finally:
        if a.keep:
            print(f"kept: {tmp}")
        else:
            shutil.rmtree(tmp, ignore_errors=True)

    for name, got, want, why in PASS:
        print(f"  PASS  {name}")
    for name, got, want, why in FAIL:
        print(f"  FAIL  {name}\n          got {got!r}, want {want!r}"
              + (f"\n          {why}" if why else ""))
    for name, detail in ERROR:
        print(f"  ERROR {name}\n          {detail}")
    n = len(PASS) + len(FAIL)
    print(f"\n{n} checks, {len(FAIL)} failed"
          + (f", {len(ERROR)} error(s)" if ERROR else ""))
    if not n:
        print("\nNo check ran at all, which is not a pass.")
        return 2
    return 1 if (FAIL or ERROR) else 0


if __name__ == "__main__":
    sys.exit(main())
