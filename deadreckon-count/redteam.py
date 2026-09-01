#!/usr/bin/env python3
"""redteam.py — the adversarial run, committed to the repo.

P5.3: The workflow used on 2026-08-09 (133 agents, 8M tokens, 45 findings)
as a committed script. Run on demand before any publication, and after any
significant change.

    python3 redteam.py              # run every claim through its attack suite
    python3 redteam.py --fast       # skip the slow suites (test_fleet, corpus)
    python3 redteam.py --list       # show what would run

WHAT IT DOES

  1. Loads every registered claim from claims.py
  2. Runs each document's adversarial suite (the C* checks in adv_reports.py,
     the structural suites in adversarial_*.py, and the reader/fleet suites)
  3. Reports which claims survived and which were falsified
  4. Exits non-zero if any claim was falsified

WHAT IT IS NOT

This is not an automated LLM red-team. It is the structural/arithmetic half:
the checks that can be run without a model. The LLM half — giving attackers
the CLAIMS and asking them to refute each one by any method they choose — is
a separate operation that requires API access and human review of results.
This script is what you run first to confirm the code is clean before spending
money on the LLM pass.

THE RULE

Every check here was written to FAIL against an unfixed version of the code.
A check that passes on a broken repo is not a check — it is noise that erodes
trust in the passing ones. The docstring of each function quotes the failure
it produced before the fix.
"""

import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).parent

# ---------------------------------------------------------------------------
# The attack plan: suite -> what it tests
# ---------------------------------------------------------------------------

SUITES = [
    # structural red-team — arithmetic, document reading, degenerate inputs
    ("adversarial_meta.py",    "meta: every suite can fail and is green on healthy code"),
    ("adversarial_daemon.py",  "daemon: archive, ledger, push-retry, credentials"),
    ("adversarial_platform.py","platform: detect(), service manager, hardlinks"),
    ("adv_reports.py",         "reports: C1–C8, generators write correct figures"),
    ("adv_collation.py",       "collation: dedup, boilerplate, sandbox profiles"),
    ("adv_copilot_ids.py",     "copilot: session ID extraction"),
    ("adv_documents.py",       "documents: export paths, field names"),
    ("adv_export_walk.py",     "export: unreadable dirs, symlinks, path budgets"),
    ("adv_forged_stamp.py",    "ledger: forged scanner_version cannot erase tokens"),
    ("adv_gate_git_blind.py",  "gate: git-blind scenarios"),
    ("adv_install_folder.py",  "install: UUID match, slug, claimed_folder"),
    ("adv_orphan_merge.py",    "orphan: merge dedup, counter recovery"),
    ("adv_platform_behaviour.py", "platform behaviour: store resolution, env"),
    ("adv_profile_claim.py",   "profile: account attribution, read_claude"),
    ("adv_published_gate.py",  "published gate: document figures certified"),
    ("adv_store_locations.py", "stores: resolve, rel_paths, platform forms"),
    ("adv_statscache_floor.py", "statscache floor: lifetime floor logic, gaps 1-4"),
    ("adv_suite_integrity.py", "suite integrity: vacuous assertions, shapes"),
    ("adv_vendor_and_identical.py", "vendor: identical-session dedup, provider"),
    # reader/fleet suites — every CLI reader, fleet arithmetic
    ("test_readers.py",        "readers: every CLI reader on absent/empty/single"),
    ("test_scanner.py",        "scanner: analyze_tokens field counting"),
    ("test_platform_paths.py", "platform paths: store resolution per OS"),
    ("test_gate.py",           "gate: check_consistency failure modes"),
    ("test_migrate_rename.py", "migrate: rename logic, rule identity"),
]

SLOW_SUITES = {
    "test_fleet.py",           # builds a full multi-machine fixture (~5s)
    "test_fleet_merge.py",     # same
    "adv_archive_dirstore.py", # real fs operations
}

SLOW_SUITES_WITH_DESC = [
    ("test_fleet.py",          "fleet: absent vs empty, per-machine arithmetic"),
    ("test_fleet_merge.py",    "fleet merge: stale machine column handling"),
    ("adv_archive_dirstore.py","archive dirstore: hard-link correctness"),
]


def run_suite(script, desc, verbose=False):
    """Run one suite. Returns (ok, duration_s, output)."""
    t0 = time.monotonic()
    r = subprocess.run(
        [sys.executable, str(ROOT / script)],
        capture_output=True, text=True, cwd=str(ROOT))
    dt = time.monotonic() - t0
    ok = r.returncode == 0
    out = (r.stdout + r.stderr).strip()
    return ok, dt, out


def extract_summary(out):
    """Pull the last meaningful summary line from suite output."""
    for line in reversed(out.splitlines()):
        line = line.strip()
        if any(k in line for k in ("passed", "failed", "checks", "attacks",
                                   "FAILED", "every suite", "of 7", "of 8")):
            return line
    return out.splitlines()[-1] if out else "(no output)"


def main():
    ap = __import__("argparse").ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fast", action="store_true",
                    help="skip slow suites (test_fleet, archive_dirstore)")
    ap.add_argument("--list", action="store_true",
                    help="show which suites would run and exit")
    ap.add_argument("--suite", metavar="SCRIPT",
                    help="run a single suite by filename")
    args = ap.parse_args()

    suites = list(SUITES)
    if not args.fast:
        suites += SLOW_SUITES_WITH_DESC

    if args.suite:
        suites = [(s, d) for s, d in suites if s == args.suite]
        if not suites:
            print(f"  unknown suite: {args.suite}")
            return 1

    if args.list:
        print(f"\n  {len(suites)} suite(s) would run:\n")
        for s, d in suites:
            slow = "  [slow]" if s in SLOW_SUITES else ""
            print(f"    {s:40s}  {d}{slow}")
        return 0

    print(f"\n  RED TEAM — {len(suites)} suite(s)\n")

    passed, failed = [], []
    total_t = 0.0

    for script, desc in suites:
        if not (ROOT / script).is_file():
            print(f"  SKIP  {script:40s}  (not found)")
            continue
        print(f"  ....  {script}", end="", flush=True)
        ok, dt, out = run_suite(script, desc)
        total_t += dt
        summary = extract_summary(out)
        status = "PASS" if ok else "FAIL"
        print(f"\r  {status}  {script:40s}  {summary}  ({dt:.1f}s)")
        if ok:
            passed.append(script)
        else:
            failed.append((script, desc, out))

    print(f"\n  {len(passed)} passed, {len(failed)} failed  "
          f"({total_t:.1f}s total)\n")

    if failed:
        print("  FAILURES:\n")
        for script, desc, out in failed:
            print(f"  ── {script}  ({desc})")
            for line in out.splitlines()[-12:]:
                print(f"     {line}")
            print()
        return 1

    print("  every claim survived the red team")
    return 0


if __name__ == "__main__":
    sys.exit(main())
