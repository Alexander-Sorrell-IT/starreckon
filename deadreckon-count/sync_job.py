#!/usr/bin/env python3
"""Daemon Job 1 — repo sync. Runs unattended on a timer.

    python3 sync_job.py               one sync pass, then exit
    python3 sync_job.py --dry-run     show what would happen, change nothing
    python3 sync_job.py --combine     rebuild root reports only, no scan

WHAT IT DOES (in order)

  1. Pull the latest from origin (both repos, if deadreckon-record exists)
  2. Scan this computer: run.py update
  3. Commit this machine's own folder — never another machine's
  4. Push
  5. Rebuild root reports (combine.py) and commit them

WHY THIS IS A SEPARATE FILE

retention_guard.py's daemon loop handles Job 2 (lifetime ledger). Job 1
(repo sync) is the same schedule but a completely different kind of work:
git operations, network I/O, potentially long-running scans. Keeping them
separate means the ledger job keeps running if a scan hangs, and a failed
push does not stop the transcript archive from being updated.

They share tick() in retention_guard.py — that function calls both.

THE ONE RULE ABOUT MACHINE FOLDERS

A machine commits ONLY its own folder. The root reports (BY-COMPUTER.md,
LIFETIME.md etc.) are derived from all machine folders and are committed
separately via --combine, which any machine can run once it has pulled
everyone else's scan. A machine that commits root reports from a partial
pull is publishing a rollup of whatever it happened to have, not the fleet.

WHAT "COMBINE" MEANS

After a machine pushes its own folder, any machine that pulls will see the
update. --combine re-derives the root reports from all machine folders
currently in the checkout and commits them. The daemon calls --combine
after every successful push so root reports stay current automatically.
Any machine can also run `python3 run.py --combine` manually at any time.
"""

import argparse
import datetime
import json
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT))
import config as _cfg
import paths

CORPUS = pathlib.Path.home() / "deadreckon-record"
REPO_OWNER = "matrixbuilderops"
COUNT_REPO  = f"{REPO_OWNER}/deadreckon-count"
RECORD_REPO = f"{REPO_OWNER}/deadreckon-record"


# ------------------------------------------------------------------ helpers

def _git(repo, *args, check=False):
    """Run git in `repo`, return (ok, stdout, stderr)."""
    r = subprocess.run(
        ["git", "-C", str(repo)] + list(args),
        capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(
            f"git {' '.join(args)} failed in {repo}: {r.stderr.strip()[:200]}")
    return r.returncode == 0, r.stdout.strip(), r.stderr.strip()


def _py(*args, cwd=ROOT):
    """Run a Python script in the repo, return (ok, stdout)."""
    r = subprocess.run(
        [sys.executable] + list(args),
        cwd=str(cwd), capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr).strip()


def _gh(*args):
    """Run a gh CLI command, return (ok, stdout)."""
    import shutil
    if not shutil.which("gh"):
        return False, "gh not found"
    r = subprocess.run(["gh"] + list(args), capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr).strip()


def _this_machine():
    """The folder name this computer owns, by .machine-id.

    UUID is the primary anchor — survives OS reinstalls and hostname changes.
    Hostname is the fallback for machines enrolled before UUID tracking.
    Falls back to cli-config.json machine.folder for first-run (no .machine-id yet).
    """
    import platform
    try:
        from install import hardware_uuid
        uuid = hardware_uuid()
    except Exception:
        uuid = None
    host = platform.node()
    hostname_match = None
    for d in paths.machine_folders(ROOT):
        f = d / ".machine-id"
        if f.is_file():
            try:
                info = json.loads(f.read_text(encoding="utf-8"))
                stored_uuid = info.get("hardware_uuid")
                if uuid and stored_uuid and stored_uuid.lower() == uuid.lower():
                    return d.name
                if info.get("hostname") == host and hostname_match is None:
                    hostname_match = d.name
            except Exception:
                pass
    return hostname_match or _cfg.machine_folder()


def _stamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


# ------------------------------------------------------------------ steps

class SyncResult:
    """Accumulates outcome lines for one sync pass."""
    def __init__(self, dry):
        self.dry = dry
        self.lines = []
        self.ok = True

    def log(self, msg):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {'DRY ' if self.dry else ''}{msg}"
        self.lines.append(line)
        print(line)

    def fail(self, msg):
        self.ok = False
        self.log(f"FAIL  {msg}")

    def summary(self):
        return ("ok" if self.ok else "FAILED") + f"  ({len(self.lines)} steps)"


def step_pull(res, repos):
    """Pull the latest from origin for every repo that exists."""
    for label, path in repos:
        if not (path / ".git").is_dir():
            res.log(f"pull  {label}  — not a checkout, skipped")
            continue
        if res.dry:
            res.log(f"pull  {label}  — would: git pull --rebase")
            continue
        ok, out, err = _git(path, "pull", "--rebase", "--autostash")
        if ok:
            summary = out.splitlines()[-1] if out else "up to date"
            res.log(f"pull  {label}  {summary}")
        else:
            res.fail(f"pull  {label}  {err[:120]}")


def step_scan(res, machine):
    """Scan this machine: run.py update."""
    if not machine:
        res.fail("scan  — no machine folder identified; "
                 "set machine.folder in cli-config.json or run "
                 "python3 run.py update --machine <name> first")
        return False
    if res.dry:
        res.log(f"scan  {machine}  — would: python3 run.py update")
        return True
    ok, out = _py("run.py", "update")
    # Extract the meaningful lines rather than all output
    for line in out.splitlines():
        if any(k in line for k in ("ledger", "staged", "lifetime", "scanned",
                                   "uncounted", "FAIL", "ERROR", "checks")):
            res.log(f"scan  {line.strip()}")
    if ok:
        res.log(f"scan  {machine}  done")
    else:
        res.fail(f"scan  {machine}  run.py update returned non-zero")
    return ok


def step_commit_own(res, machine, repo, label):
    """Stage and commit this machine's own folder only."""
    if not machine:
        res.log(f"commit  {label}  — no machine folder, skipped")
        return False
    if not (repo / ".git").is_dir():
        res.log(f"commit  {label}  — not a checkout, skipped")
        return False

    # Check for foreign-staged files before committing
    ok, staged, _ = _git(repo, "diff", "--cached", "--name-only")
    if ok:
        foreign = [f for f in staged.splitlines()
                   if f and not f.startswith(machine + "/")]
        if foreign:
            res.fail(
                f"commit  {label}  — {len(foreign)} foreign file(s) staged "
                f"(run git -C {repo} reset to clear)")
            return False

    if res.dry:
        res.log(f"commit  {label}/{machine}  — would: git add + commit")
        return True

    # Stage only this machine's folder
    _git(repo, "add", machine)
    ok, diff, _ = _git(repo, "diff", "--cached", "--name-only")
    staged_count = len([f for f in diff.splitlines()
                        if f.startswith(machine + "/")])
    if staged_count == 0:
        res.log(f"commit  {label}/{machine}  — nothing new to commit")
        return True     # not a failure — machine may not have changed

    msg = f"scan {machine} {_stamp()}"
    ok, out, err = _git(repo, "commit", "-m", msg)
    if ok:
        res.log(f"commit  {label}/{machine}  {staged_count} file(s)  '{msg}'")
        return True
    res.fail(f"commit  {label}/{machine}  {err[:120]}")
    return False


def step_push(res, repos, retries=4, backoff=15):
    """Push each repo that has commits ahead of origin.

    On non-fast-forward rejection (two machines pushed concurrently) we pull
    --rebase --autostash and retry up to `retries` times with `backoff` second
    waits. This is the local half of the serializer; the GitHub Actions workflow
    (.github/workflows/serialize.yml) is the remote half — it queues concurrent
    workflow runs so only one combine/push lands at a time.
    """
    import time
    for label, path in repos:
        if not (path / ".git").is_dir():
            continue
        _, ahead, _ = _git(path, "rev-list", "--count", "origin/main..HEAD")
        n = int(ahead) if ahead.isdigit() else 0
        if n == 0:
            res.log(f"push  {label}  — nothing ahead of origin")
            continue
        if res.dry:
            res.log(f"push  {label}  — would push {n} commit(s)")
            continue
        for attempt in range(1, retries + 2):   # retries+1 total attempts
            ok, out, err = _git(path, "push")
            if ok:
                res.log(f"push  {label}  {n} commit(s) pushed"
                        + (f" (attempt {attempt})" if attempt > 1 else ""))
                break
            # Non-fast-forward: another machine pushed while we were scanning.
            # Pull --rebase to incorporate their work, then retry.
            nff = ("non-fast-forward" in err or "fetch first" in err
                   or "rejected" in err)
            if nff and attempt <= retries:
                res.log(f"push  {label}  rejected (non-fast-forward), "
                        f"rebasing and retrying ({attempt}/{retries})...")
                time.sleep(backoff * attempt)   # exponential-ish backoff
                pull_ok, _, pull_err = _git(path, "pull", "--rebase",
                                            "--autostash")
                if not pull_ok:
                    res.fail(f"push  {label}  rebase after rejection failed: "
                             f"{pull_err[:120]}")
                    break
            else:
                res.fail(f"push  {label}  {err[:120]}")
                break


def step_combine(res, machine=None):
    """Rebuild root reports from all machine folders and commit them.

    This is what keeps BY-COMPUTER.md, LIFETIME.md etc. current after
    any machine pushes. Any machine can run this — it only reads from
    machine folders and writes the root documents.

    The --combine flag on run.py triggers this step alone.
    """
    if res.dry:
        res.log("combine  — would: python3 update.py --combine-only + commit root docs")
        return

    ok, out = _py("update.py", "--combine-only")
    if not ok:
        res.fail(f"combine  update.py --combine-only failed: {out[-200:]}")
        return
    res.log("combine  root reports rebuilt")

    # Commit the root derived documents
    if not (ROOT / ".git").is_dir():
        return
    root_docs = [
        "human-readable/BY-COMPUTER.md",
        "human-readable/BY-ACCOUNT.md",
        "human-readable/BY-COMPANY.md",
        "human-readable/BY-CLI.md",
        "human-readable/STATS.md",
        "human-readable/LIFETIME.md",
        "human-readable/THIS-MONTH.md",
        "human-readable/COVERAGE.md",
        "machine-readable/ALL-COMPUTERS.json",
        "machine-readable/stats.json",
        "machine-readable/lifetime.json",
        "README.md",
    ]
    for doc in root_docs:
        p = ROOT / doc
        if p.is_file():
            _git(ROOT, "add", doc)

    ok, diff, _ = _git(ROOT, "diff", "--cached", "--name-only")
    staged = [f for f in diff.splitlines() if f]
    if not staged:
        res.log("combine  — root docs unchanged, nothing to commit")
        return

    msg = f"reports {_stamp()}"
    if machine:
        msg = f"reports after {machine} {_stamp()}"
    ok, _, err = _git(ROOT, "commit", "-m", msg)
    if ok:
        res.log(f"combine  committed {len(staged)} root doc(s): '{msg}'")
        # Push the root doc commit immediately
        ok2, _, err2 = _git(ROOT, "push")
        if ok2:
            res.log("combine  pushed root docs")
        else:
            res.fail(f"combine  push failed: {err2[:120]}")
    else:
        res.fail(f"combine  commit failed: {err[:120]}")


# ------------------------------------------------------------------ main entry

def step_health(res, repos):
    """Verify the daemon is running. If not, re-pull both repos.

    TWO DISTINCT PROBLEMS, ONE RESPONSE.

    If the daemon is not running the guard is not running, which means
    transcripts may be expiring unprotected. The most common cause after
    a working install is that an OS update rewrote the service file or the
    repo was moved and the ExecStart path is now stale. A re-pull makes
    sure the script on disk matches what the service expects — it does not
    re-enable the daemon (that requires a human), but it removes the most
    common cause of the drift.

    This runs every sync pass, not just on --verify, so a daemon that dies
    between manual checks is caught within one tick (6h) rather than the
    next time somebody runs install.py --verify.
    """
    import platform as _plat
    sysname = _plat.system()
    # Inline the same check install.py uses so we do not import install.py
    # (which would drag in its global side-effects).
    running = None
    detail = ""
    try:
        if sysname == "Linux":
            r = subprocess.run(
                ["systemctl", "--user", "is-active", "retention-guard.service"],
                capture_output=True, text=True, timeout=10)
            running = r.returncode == 0 and r.stdout.strip() == "active"
            detail = r.stdout.strip()
        elif sysname == "Darwin":
            r = subprocess.run(
                ["launchctl", "list", "com.deadreckon.retention-guard"],
                capture_output=True, text=True, timeout=10)
            running = r.returncode == 0
            detail = "loaded" if running else "not loaded"
        elif sysname == "Windows":
            r = subprocess.run(
                ["schtasks", "/query", "/tn", "deadreckon-retention-guard",
                 "/fo", "list"],
                capture_output=True, text=True, shell=True, timeout=10)
            running = r.returncode == 0 and "Running" in r.stdout
            detail = "running" if running else r.stdout.strip()[:60]
    except Exception:  # noqa: BLE001
        running = None
        detail = "check could not run"

    if running is None:
        res.log(f"health  daemon status unknown ({detail}) — skipped")
        return
    if running:
        res.log(f"health  daemon is running ({detail})")
        return

    # Not running — re-pull both repos so the service file and script stay
    # in sync, then report loudly.
    res.log("health  !! DAEMON IS NOT RUNNING — re-pulling repos to sync service files")
    if not res.dry:
        for label, path in repos:
            if not (path / ".git").is_dir():
                continue
            ok, out, err = _git(path, "pull", "--rebase", "--autostash")
            summary = (out.splitlines()[-1] if out.strip() else "up to date") if ok else err[:80]
            res.log(f"health  re-pull {label}: {summary}")
    res.fail("health  daemon not running — re-enable it: "
             "systemctl --user enable --now retention-guard.service  "
             "(Linux) | launchctl load ~/Library/LaunchAgents/"
             "com.deadreckon.retention-guard.plist  (macOS)")


def sync(dry=False, combine_only=False):
    """One full sync pass. Returns SyncResult.

    Called by retention_guard.tick() as Job 1 of the daemon, and
    directly by `python3 sync_job.py`.
    """
    res = SyncResult(dry=dry)
    cfg = _cfg.load()
    machine = _this_machine()

    repos = [("deadreckon-count", ROOT)]
    if CORPUS.is_dir():
        repos.append(("deadreckon-record", CORPUS))

    if combine_only:
        step_pull(res, repos)
        step_combine(res, machine)
        return res

    step_pull(res, repos)
    step_health(res, repos)

    scan_ok = step_scan(res, machine)

    if scan_ok or dry:
        # Commit deadreckon-count own folder
        step_commit_own(res, machine, ROOT, "deadreckon-count")
        # Commit deadreckon-record own folder (corpus export)
        if CORPUS.is_dir():
            step_commit_own(res, machine, CORPUS, "deadreckon-record")

    step_push(res, repos)

    # Rebuild and commit root reports after pushing own folder
    if scan_ok or dry:
        step_combine(res, machine)

    return res


def outcome_line(res):
    """One-line summary for the daemon log."""
    return f"SYNC  {res.summary()}"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true",
                    help="show what would happen, change nothing")
    ap.add_argument("--combine", action="store_true",
                    help="rebuild root reports only, no scan")
    args = ap.parse_args()
    result = sync(dry=args.dry_run, combine_only=args.combine)
    sys.exit(0 if result.ok else 1)
