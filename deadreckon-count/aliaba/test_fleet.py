#!/usr/bin/env python3
"""Five machines, five shapes, and one number per CLI that nobody derived from
the code under test.

    python3 test_fleet.py

`test_readers.py` asks "given input of the shape this reader documents, does it
compute the number it claims" — one reader, one home, one platform. This asks
the question that has never been asked in this repository: does a FLEET sum
correctly, on layouts four of the five machines actually use.

Every `want` below comes from `fleet_fixture`, which computes it by arithmetic
over the same literal constants it wrote into the files. No expected value in
this file was produced by calling a reader.

WHAT IT CHECKS

  per machine, per CLI   the planted total comes back exactly, and so does the
                         per-field split — a reader that gets the total right by
                         moving cache_read into input is wrong in the way the
                         SUBSET rule exists to catch
  per machine, sessions  a session checkpointed across two files is ONE session;
                         a session synced to a second profile is ONE session
  absent vs empty        gemini on linux-b is installed and holds nothing, and
                         that is a different report from a CLI with no directory
  coverage               lmstudio exists on exactly one machine, so the fleet's
                         per-CLI table is asymmetric on purpose
  the fleet sum          five machines add up to the planted total
  the never-scanned      a machine in machines.json with no folder is missing,
                         not zero
  reader_version         one machine's artifacts were written by a different
                         reader, and a fleet total that adds them is mixing two
                         derivations

    python3 test_fleet.py --revert-proof

applies each of 17 deliberate defects to a copy of the source and re-runs this
whole suite against it. Every one must go RED. That is the only evidence any of
the above means anything — a test that passes against reverted code proves
nothing, and this repository has twice shipped "25/25 green" over 45 live
defects.

WHAT THIS CATCHES THAT test_readers.py DOES NOT

All 17 breaks were also run against `test_readers.py`. It caught 11 and went
GREEN — 80 checks, 0 failed — on six:

    claude-first-wins          the running MAXIMUM per message.id degraded to
                               first-wins. Its claude fixture's streaming rows
                               are all-or-nothing, so a partial first chunk
                               cannot be distinguished from a complete one.
    codex-no-repeat-drop       the byte-identical re-emission of a turn counted
                               twice. Its codex fixture has one turn.
    codex-flat-glob            rglob -> glob, so rollouts under YYYY/MM/DD stop
                               being found. Its fixture puts the rollout at the
                               top of the store.
    gemini-file-is-session     a session checkpointed across two files counted
                               as two sessions. Its fixture is one file.
    vscode-no-windows          the %APPDATA% branch deleted. Nothing in that
                               suite is a Windows layout.
    detect-always-installed    absent and installed-but-empty become the same
                               report. Nothing there asks detect() about a CLI
                               that is genuinely not there.

That is not a criticism of that suite — it answers a narrower question on
purpose. It is the measurement that says what this one is for: nesting,
grouping, platform and presence, which are exactly the four things a
five-machine fleet has and a single fixture home does not.
"""

import json
import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fleet_fixture                                               # noqa: E402
import paths                                                       # noqa: E402

PASS, FAIL = [], []


def check(name, got, want, why=""):
    (PASS if got == want else FAIL).append((name, got, want, why))


def _read(machine_dir, name):
    """A generated file, found the way every reader in this repo finds one.

    Through paths.find(), never `dir / "machine-readable" / name`. Four call
    sites in this repo joined the flat path instead and every one failed
    silently — a missing file reads exactly like an empty result.
    """
    p = paths.find(machine_dir, name)
    if p is None:
        raise AssertionError(f"{name} missing under {machine_dir}")
    return json.loads(p.read_text(encoding="utf-8"))


def totals(recs):
    """The four fields of a reader's output, summed. Same rule as test_readers."""
    out = dict.fromkeys(("input_tokens", "cache_creation_input_tokens",
                         "cache_read_input_tokens", "output_tokens"), 0)
    for r in recs or []:
        for k in out:
            out[k] += r["tokens"][k]
    return out


# --------------------------------------------------------------------------

def run_machine(m):
    """Every fixtured reader on one machine's home, under its own platform."""
    with fleet_fixture.platform_as(m.platform) as sessions:
        got = {}
        for cli in ("claude", "copilot", "codex", "gemini", "grok", "lmstudio",
                    "clawspring", "kilocode", "copilot-chat"):
            recs = sessions.READERS[cli](m.home)
            present, _, _ = sessions.detect(cli, m.home)
            got[cli] = {"records": recs, "fields": totals(recs),
                        "total": sum(totals(recs).values()),
                        "sessions": len(recs), "installed": present,
                        "ids": sorted(r["session_id"] for r in recs)}
        return got


def t_per_machine(fleet):
    """The planted total, per machine, per CLI, and the field split with it."""
    fleet_seen = 0
    for name, m in fleet.machines.items():
        got = run_machine(m)
        want_by_cli = m.expected_by_cli
        want_sessions = m.expected_sessions_by_cli

        for cli, g in got.items():
            want = want_by_cli.get(cli, 0)
            check(f"{name}/{cli}: planted total comes back exactly",
                  g["total"], want,
                  "the fixture computed this from the constants it wrote; a "
                  "reader that disagrees is reading a different number")
            check(f"{name}/{cli}: session count",
                  g["sessions"], want_sessions.get(cli, 0))

        # The field split, summed per CLI from the planters.
        by_cli_fields = {}
        for p in m.planted:
            tgt = by_cli_fields.setdefault(p.cli, dict.fromkeys(p.by_field, 0))
            for k, v in p.by_field.items():
                tgt[k] += v
        for cli, want_f in by_cli_fields.items():
            check(f"{name}/{cli}: per-field split, not just the total",
                  got[cli]["fields"], want_f,
                  "a right total with a wrong split means the cached/uncached "
                  "boundary moved — the SUBSET rule caught nothing")

        check(f"{name}: machine total", sum(g["total"] for g in got.values()),
              m.expected_total)
        fleet_seen += sum(g["total"] for g in got.values())

        # ABSENT IS NOT ZERO, part 1: installed and empty.
        for cli in m.installed_but_empty:
            check(f"{name}/{cli}: INSTALLED AND EMPTY reports installed",
                  got[cli]["installed"], True,
                  "a tool that has run and recorded nothing must not read as "
                  "a tool that was never installed")
            check(f"{name}/{cli}: INSTALLED AND EMPTY reports no sessions",
                  got[cli]["sessions"], 0)

        # ABSENT IS NOT ZERO, part 2: no directory at all.
        for cli in m.absent:
            check(f"{name}/{cli}: ABSENT reports not installed",
                  got[cli]["installed"], False,
                  "this CLI has no directory on this machine; detect() saying "
                  "otherwise makes absent and empty the same report")
            check(f"{name}/{cli}: ABSENT reports no sessions",
                  got[cli]["sessions"], 0)

    check("fleet: five machines sum to the planted fleet total",
          fleet_seen, fleet.expected_total,
          "this is the sum nobody in this repository has ever checked")


def t_coverage_is_asymmetric(fleet):
    """One CLI on exactly one machine. A per-CLI table cannot fill that with 0."""
    check("fleet: lmstudio exists on exactly one machine",
          fleet.only_on_one_machine.get("lmstudio"), "linux-a",
          "if every machine had every CLI, a report that invents zeros for the "
          "missing ones would look identical to a correct one")
    everyone = set()
    for m in fleet.machines.values():
        everyone |= set(m.expected_by_cli)
    check("fleet: not every CLI is on every machine",
          all(set(m.expected_by_cli) == everyone
              for m in fleet.machines.values()), False)


def t_never_scanned_is_missing_not_zero(fleet):
    """A machine in the roster with no folder is a GAP, not a zero."""
    roster = json.loads((fleet.records / "machines.json").read_text())
    folders = [m["folder"] for m in roster["machines"]]
    for n in fleet.never_scanned:
        check(f"roster lists the never-scanned machine {n}", n in folders, True)
        check(f"the never-scanned machine {n} has no folder on disk",
              (fleet.records / n).exists(), False,
              "listing it is the only reason its absence is visible at all; "
              "without the roster it would not be missing, it would be nothing")


def t_reader_version_skew(fleet):
    """One machine's artifacts were written by a different reader.

    corpus_reports.py refuses to add a figure whose reader_version is not the
    current one — "STALE, computed by an older reader, not totalled". That path
    needs a fleet where the versions actually differ, and until now no such
    fleet existed.
    """
    vers = {}
    for name, m in fleet.machines.items():
        vers[name] = _read(m.out, "stats.json").get("reader_version")
    distinct = set(vers.values())
    check("fleet: the machines do NOT all share one reader_version",
          len(distinct), 2,
          "a fleet where every version matches cannot exercise the staleness "
          "branch, and that branch guards a 2.0x-to-2.9x error")
    odd = [n for n, v in vers.items() if v == "ANCIENT00000"]
    check("fleet: exactly one machine is the stale one", odd, ["macos-m1"])
    current = [n for n, v in vers.items() if v != "ANCIENT00000"]
    stale_total = sum(fleet.machines[n].expected_total for n in odd)
    check("fleet: dropping the stale machine changes the total",
          sum(fleet.machines[n].expected_total for n in current)
          != fleet.expected_total, True,
          "if the stale machine held 0 the guard would be untestable")
    check("fleet: the stale machine is worth something", stale_total > 0, True)


def t_synced_session_is_reported_not_assumed(fleet):
    """A transcript synced to two machines. Report the behaviour; do not pick.

    The correct answer is a policy question this fixture deliberately does not
    settle. What it CAN settle is what the code does today, so that the answer
    is a measurement rather than an assumption:

      per machine   each reader sees its own home and counts the session in
                    full. Both machines' totals include it.
      per fleet     combine.py computes
                        grand = sum(m["grand_total_tokens"] for m in machines)
                    with no cross-machine identity check of any kind, so the
                    fleet total contains it TWICE.

    This test asserts the fact, not the desirability.
    """
    dupes = fleet.duplicate_session_ids
    check("fleet: exactly one session id appears on two machines",
          sorted(dupes), [fleet_fixture.SYNCED_SESSION_ID])
    where = dupes[fleet_fixture.SYNCED_SESSION_ID]
    check("fleet: the synced session is on linux-a and macos-m1",
          sorted(where), ["linux-a", "macos-m1"])

    # What the fleet total actually does with it. Read from the artifacts a
    # scan leaves behind, through paths.find() the same way combine.py reads
    # them — a flat join here would read a layout nothing writes.
    naive = sum(_read(m.out, "totals.json")["grand_total_tokens"]
                for m in fleet.machines.values())
    dup_worth = 0
    for n in where:
        for p in fleet.machines[n].planted:
            if fleet_fixture.SYNCED_SESSION_ID in p.session_ids:
                dup_worth += p.tokens
    check("fleet: the naive machine sum counts the synced session twice",
          naive - fleet.expected_total, 0,
          "the planted fleet total is itself the naive sum, so this is 0 by "
          "construction — the finding is that it is 0, i.e. nothing anywhere "
          "removes the duplicate")
    check("fleet: the synced session is worth a non-trivial amount twice over",
          dup_worth > 0 and dup_worth % 2 == 0, True)
    print(f"    [reported] session {fleet_fixture.SYNCED_SESSION_ID} is on "
          f"{', '.join(sorted(where))}; each machine counts it in full "
          f"({dup_worth // 2:,} tokens each) and the fleet sum "
          f"({naive:,}) contains it twice. Nothing deduplicates across "
          f"machines. Policy call, not a bug this fixture decides.")


def t_traps_are_actually_planted(fleet):
    """Every one of the four traps is on every machine that holds data.

    A fixture that quietly dropped a trap on one machine would pass forever
    while that machine's shape went untested. `Planted.traps` is recorded by
    each planter, so this is a check and not a docstring.
    """
    for name, m in fleet.machines.items():
        have = set()
        for p in m.planted:
            have |= set(p.traps)
        check(f"{name}: carries all four counting traps",
              sorted(have), sorted(fleet_fixture.ALL_TRAPS),
              "a machine missing a trap is a machine whose shape cannot fail")


def t_platform_expansion_is_frozen_at_import(fleet):
    """The finding that makes `platform_as` necessary rather than decorative.

    `read_copilot_chat`'s bases are baked by a decorator at IMPORT time, so a
    macOS tree is unreachable from a module imported on Linux however correct
    the reader is. `read_kilocode` resolves at RUNTIME and follows a patch
    without a reload. Asserted, because if either ever changed, a test that
    reloads for one and not the other would silently stop covering a platform.

    The two reload checks use `platform_as("linux")` rather than a bare
    `importlib.reload`. A bare reload bakes the CURRENT platform's paths —
    which is correct behaviour — so on macOS it produces macOS paths and the
    assertion "no Library/Application Support when imported on Linux" was
    vacuously wrong: we are not on Linux. `platform_as("linux")` shims
    `stores`' view of `sys.platform` before reloading, which is the exact
    mechanism the test was written to prove is necessary.
    """
    with fleet_fixture.platform_as("linux") as linux_sessions:
        check("copilot-chat bases are frozen at import (Linux module, Linux paths)",
              any(r.startswith(".config/") for r in linux_sessions.read_copilot_chat.rels),
              True)
        check("copilot-chat bases do NOT include the macOS layout when imported "
              "on Linux",
              any("Library/Application Support" in r
                  for r in linux_sessions.read_copilot_chat.rels), False,
              "this is why platform_as() reloads the module rather than patching "
              "and hoping")
    with fleet_fixture.platform_as("macos") as mac_sessions:
        check("after a reload under macOS, copilot-chat can see Library/",
              any("Library/Application Support" in r
                  for r in mac_sessions.read_copilot_chat.rels), True)
        # kilocode never had a frozen list; it asks at call time.
        labels = [n for n, _ in mac_sessions.vscode_roots(
            fleet.machines["macos-m1"].home)]
        check("kilocode's vscode_roots resolves at runtime under macOS",
              labels, ["Code"])


# --------------------------------------------------------------------------
# deliberate breaks — the only thing that makes any of the above evidence
# --------------------------------------------------------------------------

BREAKS = {
    # name -> (file, find, replace), applied to a COPY of the module source.
    #
    # Source substitution rather than monkeypatching, because every defect
    # worth planting lives INSIDE a reader's loop where no patch can reach —
    # and because the one break that a patch-based seam did hide
    # (`vscode-linux-only`) is the reason the seam was moved. See
    # fleet_fixture.platform_as.
    "claude-first-wins": (
        "sessions.py",
        "                            if isinstance(v, int) and v > cur[k]:\n"
        "                                cur[k] = v",
        "                            if isinstance(v, int) and cur[k] == 0:\n"
        "                                cur[k] = v"),
    "claude-no-uuid-dedup": (
        "sessions.py",
        "                        if uuid in seen_uuid:\n                            continue\n",
        "                        if False:\n                            continue\n"),
    "codex-sum-cumulative": (
        "sessions.py",
        '            last = ((p.get("info") or {}).get("last_token_usage")) or {}',
        '            last = ((p.get("info") or {}).get("total_token_usage")) or {}'),
    "codex-no-repeat-drop": (
        "sessions.py",
        "            if key == prev_usage:\n                continue",
        "            if False:\n                continue"),
    "gemini-cached-added": (
        "sessions.py",
        '                rec["tokens"]["input_tokens"] += max(0, inp - cached) + (t.get("tool", 0) or 0)',
        '                rec["tokens"]["input_tokens"] += inp + (t.get("tool", 0) or 0)'),
    "kilocode-cache-added": (
        "sessions.py",
        '                rec["tokens"]["input_tokens"] += max(0, tin - cr - cw)',
        '                rec["tokens"]["input_tokens"] += tin'),
    "copilot-chat-sums-ads": (
        "sessions.py",
        '                rec["tokens"]["output_tokens"] += n',
        '                rec["tokens"]["output_tokens"] += n + (((d.get("inputState") or {})'
        '.get("selectedModel") or {}).get("metadata") or {}).get("maxInputTokens", 0)'),
    "copilot-drop-reasoning": (
        "sessions.py",
        '                        tgt["output_tokens"] += u.get("reasoningTokens", 0) or 0',
        '                        tgt["output_tokens"] += 0'),
    "grok-counts-snapshots": (
        "sessions.py",
        '            if upd.get("sessionUpdate") != "turn_completed":',
        '            if upd.get("sessionUpdate") not in ("turn_completed", "usage_snapshot"):'),
    "copilot-returns-nothing": (
        "sessions.py",
        '    if not base.is_dir():\n        return []\n    # Compaction token keys',
        '    return []\n    if not base.is_dir():\n        return []\n    # Compaction token keys'),
    "vscode-linux-only": (
        "stores.py",
        '    if sys.platform == "darwin":\n        out.append("Library/Application Support")',
        '    if False:\n        out.append("Library/Application Support")'),
    "vscode-no-windows": (
        "stores.py",
        '    elif os.name == "nt":',
        '    elif False:'),
    "claude-flat-glob": (
        "sessions.py",
        '            for f in sorted(proj.rglob("*.jsonl")):',
        '            for f in sorted(proj.glob("*.jsonl")):'),
    "claude-first-profile-only": (
        "sessions.py",
        "    for cfg in find_config_dirs(home):",
        "    for cfg in find_config_dirs(home)[:1]:"),
    "codex-flat-glob": (
        "sessions.py",
        '    for f in sorted(base.rglob("rollout-*.jsonl")):',
        '    for f in sorted(base.glob("rollout-*.jsonl")):'),
    "gemini-file-is-session": (
        "sessions.py",
        '            sid = d.get("sessionId") or f.stem',
        '            sid = f.stem'),
    # The repo's most-repeated defect, planted directly: make "installed" always
    # true and an absent CLI becomes indistinguishable from an empty one.
    # ANCHOR: sessions.detect() now returns (found, checked, blind) — three
    # values. The break forces found=True so an absent CLI looks installed.
    # Updated from the two-value return when detect() grew the blind counter.
    "detect-always-installed": (
        "sessions.py",
        "        elif present(home / rel):\n            found = True\n    return found, checked, blind",
        "        elif present(home / rel):\n            found = True\n    return True, checked, blind"),
}


# Only these are needed to run this suite. Copying the whole tree also copies
# 3.5 GB of corpus and the machine folders, which turns an 11-break proof into
# a several-minute one for no benefit.
BREAK_FILES = ("sessions.py", "stores.py", "paths.py", "analyze_tokens.py",
               "token_ledger.py", "fleet_fixture.py", "test_fleet.py")


def break_source(name, workdir):
    """Copy the modules this suite needs into `workdir`, one defect applied."""
    here = pathlib.Path(__file__).resolve().parent
    dst = pathlib.Path(workdir) / "broken"
    dst.mkdir(parents=True, exist_ok=True)
    for f in BREAK_FILES:
        shutil.copy2(here / f, dst / f)
    fname, find, repl = BREAKS[name]
    p = dst / fname
    text = p.read_text(encoding="utf-8")
    if find not in text:
        sys.exit(f"break {name!r} no longer matches {fname} — the code moved")
    p.write_text(text.replace(find, repl, 1), encoding="utf-8")
    return dst


def revert_proof():
    """Run the whole suite against each deliberate break, in a subprocess.

    A break has to be applied to the module SOURCE — the defects worth planting
    live inside reader loops, where no monkeypatch can reach. So each one gets a
    copy of the tree, one substitution, and a fresh interpreter.
    """
    import subprocess
    here = pathlib.Path(__file__).resolve().parent
    print("\nREVERT PROOF — the suite must go RED for each of these\n")
    worst = 0
    with tempfile.TemporaryDirectory(prefix="fleet-break-") as tmp:
        for name in BREAKS:
            dst = break_source(name, pathlib.Path(tmp) / name)
            r = subprocess.run([sys.executable, str(dst / "test_fleet.py")],
                               capture_output=True, text=True, cwd=str(dst))
            line = next((l.strip() for l in r.stdout.splitlines()
                         if l.strip().startswith("RESULT")), "")
            red = r.returncode != 0
            worst += 0 if red else 1
            print(f"  {'RED  ' if red else 'GREEN'}  {name:26s}  {line}")
            if not red:
                print("          ^^ THIS BREAK WAS NOT CAUGHT. The fixture "
                      "cannot tell this defect from correct code.")
                print("             " + (r.stderr.strip()[-300:] or
                                         r.stdout.strip()[-300:]))
    print()
    if worst:
        print(f"  {worst} break(s) went unnoticed — the fixture cannot "
              f"distinguish them from correct code.")
    else:
        print(f"  all {len(BREAKS)} breaks caught.")
    return worst


# --------------------------------------------------------------------------

def main():
    if "--revert-proof" in sys.argv:
        sys.exit(1 if revert_proof() else 0)

    with tempfile.TemporaryDirectory(prefix="fleet-") as tmp:
        fleet = fleet_fixture.build_fleet(pathlib.Path(tmp))
        t_traps_are_actually_planted(fleet)
        t_per_machine(fleet)
        t_coverage_is_asymmetric(fleet)
        t_never_scanned_is_missing_not_zero(fleet)
        t_reader_version_skew(fleet)
        t_synced_session_is_reported_not_assumed(fleet)
        t_platform_expansion_is_frozen_at_import(fleet)

    for name, got, want, why in FAIL:
        print(f"FAIL  {name}\n        got  {got!r}\n        want {want!r}"
              + (f"\n        {why}" if why else ""))
    print(f"\nRESULT  {len(PASS)} passed, {len(FAIL)} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
