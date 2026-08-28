#!/usr/bin/env python3
"""Rename this computer's checkouts to deadreckon-count / deadreckon-record.

    python3 migrate_rename.py            # show what it WOULD do, change nothing
    python3 migrate_rename.py --yes      # do it

Run once per machine, after `git pull`. Safe to run again: every step checks
whether it is already done, so a second run reports "already renamed" rather
than half-applying anything.

WHY A SCRIPT AND NOT FOUR COMMANDS

Because the four commands are not the same on every machine, and getting the
ORDER wrong leaves a computer with a daemon pointing at a directory that no
longer exists — which fails silently, because a systemd unit whose ExecStart is
missing stays "loaded" and the transcripts it was protecting start expiring
again at the next Claude Code startup.

  1. FIND the checkouts. Not by name — this machine calls the count repo
     `token-usage-backup`, another may have cloned it as `token-usage`. Both are
     found by asking git which remote each directory points at, so a directory
     named anything at all is matched correctly and a directory that merely
     LOOKS like one is not.
  2. STOP the daemon first. It runs out of the checkout; renaming underneath a
     live process is how you get a half-written archive.
  3. RENAME the count repo, then repoint the remote, then relink.
  4. RE-CLONE the record repo. NOT a pull. See below.
  5. RESTART and VERIFY.

THE RECORD REPO IS RE-CLONED, NOT PULLED, AND THE DIFFERENCE IS 4.9 GB

Transcripts were untracked from that repository today — they ship as release
assets instead, which is what the .gitignore has said since git hung for 25
minutes twice. Untracking changes the TIP. It does not remove a single blob
from history, so an existing checkout keeps carrying all of them:

    existing checkout .git     4.9 GB
    fresh clone .git           232 KB      (3 seconds)

A `git pull` there gets you the new tip AND keeps the 4.9 GB, which is exactly
the state that made a single `git reset` run for 63 minutes and fail. It also
deletes the transcripts from the working tree — because the commit records them
as deleted — so pulling is strictly worse than cloning: same file loss, none of
the speed.

Nothing is lost either way. A machine's OWN transcripts are re-exported by the
very next step (`run.py update`), and every machine's are on the release as
<machine>.tar.zst. The old checkout is MOVED ASIDE rather than deleted, so it is
still there until you are satisfied.

The count repo is only 23 MB and has no such history, so it is renamed in place
and `git pull` is correct for it.

THE SYMLINK IS THE PART PEOPLE MISS

The service does not run the repo copy directly. It runs
~/.local/bin/retention_guard.py, which is a SYMLINK into the checkout —
deliberately, so the daemon always executes committed code rather than a stale
copy someone made months ago. That means a directory rename needs the symlink
repointed and NOT a unit edit, and it means the unit file itself never has to
change. If the symlink is missing (some machines were set up before it), this
says so instead of guessing.

MACOS

launchd, not systemd. The plist is loaded by label, so the same stop/start
logic applies with different commands. If neither service manager is present
the rename still happens and the script says the daemon was not running, which
is a real answer rather than a failure.

"DAEMON STARTED" USED TO MEAN "WE REACHED THAT LINE"

The restart was `sh(["systemctl","--user","start",SERVICE])` with the return
code thrown away, and the message printed underneath it unconditionally. On
this machine that produced a guard-shaped hole: the service was stopped at
20:45:03, the start failed, and it did not come back until 23:42:55 — two hours
fifty-seven minutes with the retention guard down — while the script printed
"daemon started", then "ok daemon active (active)", then exited 0.

Three things have to be true before a restart can be called a restart, and only
the first two are about systemd at all:

  1. the start command returns 0
  2. the manager says active, with a MainPID that is DIFFERENT from the pid
     recorded before the stop. The same pid is not a restart; it is a stale
     read of the state from before the stop, and that is precisely what
     reported "active" for a service that was down. `is-active` on its own is
     the weakest of the three — it also says "activating" while a unit sits in
     Restart= backoff, never having run a line of Python.
  3. that pid is a RUNNING retention guard, by retention_guard._alive — which
     is IMPORTED here rather than restated, whole. A pid that merely exists is
     not enough: pids are reused, and the cmdline is the only thing that makes
     a number this daemon rather than whatever inherited it.

If any of the three fails the script says so, prints the platform's own
remediation commands, and exits non-zero. It does not print success.

THE INSTALLED UNIT IS A COPY

    repo       ~/deadreckon-count/retention-guard.service
    installed  ~/.config/systemd/user/retention-guard.service

systemd loads the second one. Editing the first never reaches the running
system, so the repo unit can say `deadreckon-count` while the loaded unit still
says `token-usage-backup` — harmless in Documentation=, silent and dangerous
the day ExecStart= or Environment= differ. The drift is DETECTED and REPORTED
with the exact three commands to refresh it. It is not fixed here: installing a
unit and reloading the manager is a change to the running system, and this
script's job is the rename.

NOTHING IS DELETED. Directories are moved, never removed; git history is
untouched; no file inside either repository is edited.
"""

import argparse

import os
import pathlib
import platform
import shutil
import subprocess
import sys
import time

HOME = pathlib.Path.home()

# IMPORTED AT MODULE LOAD, ON PURPOSE — which is BEFORE anything is moved.
# By the time the restart is verified this file's own directory has been
# renamed out from under sys.path[0], so an import deferred to that moment
# would fail on exactly the run that needs it. Python caches it here instead.
#
# _alive is the WHOLE liveness rule and it is taken whole: not "the pid exists"
# (pids are reused — /proc/<pid> alone answers yes for whatever inherited the
# number), and not the Linux branch only (this script runs on the Macs too, and
# there the rule is `ps -o command=`). _remediation comes with it because the
# failure message has to name commands that exist on THIS platform; the four
# Linux ones printed on a Mac are how that check got stranded once already.
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
try:
    from retention_guard import _alive as pid_is_the_daemon
    from retention_guard import _remediation as daemon_remediation
    LIVENESS_IMPORT_ERROR = None
except Exception as e:  # noqa: BLE001 - reported, never swallowed
    pid_is_the_daemon = daemon_remediation = None
    LIVENESS_IMPORT_ERROR = f"{type(e).__name__}: {e}"

# (old remote name, new remote name, new local directory)
REPOS = [
    ("token-usage", "deadreckon-count", "deadreckon-count"),
    ("token-corpus", "deadreckon-record", "deadreckon-record"),
]
OWNER = "matrixbuilderops"
SERVICE = "retention-guard.service"
PLIST_LABEL = "com.tokenusage.retention-guard"
LINK = HOME / ".local" / "bin" / "retention_guard.py"
UNIT_REPO_NAME = "retention-guard.service"
# How long a restart is given to become observable before it is called failed.
RESTART_SETTLE_S = 5.0
UNIT_INSTALLED = HOME / ".config" / "systemd" / "user" / SERVICE
# Directives whose drift changes what the daemon DOES. Documentation= and
# Description= drifting is untidy; these drifting is a different program.
UNIT_LOAD_BEARING = ("ExecStart", "ExecStop", "ExecReload", "Environment",
                     "EnvironmentFile", "Restart", "RestartSec", "Type",
                     "User", "WorkingDirectory", "StandardOutput",
                     "StandardError", "WantedBy", "RequiredBy")


def sh(cmd, cwd=None, check=False):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        raise SystemExit(f"FAILED: {' '.join(cmd)}\n{r.stderr[-400:]}")
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def find_checkout(old_name, new_name):
    """The directory whose git remote points at this repo, whatever it is called.

    By REMOTE, not by directory name. Machines were cloned at different times
    under different names, and a name test would both miss those and match an
    unrelated directory that happened to be called the right thing.
    """
    seen = []
    for d in sorted(p for p in HOME.iterdir() if p.is_dir()):
        if not (d / ".git").exists():
            continue
        rc, url, _ = sh(["git", "remote", "get-url", "origin"], cwd=str(d))
        if rc:
            continue
        u = url.rstrip("/").removesuffix(".git")
        if u.endswith(f"/{old_name}") or u.endswith(f"/{new_name}") or \
           u.endswith(f":{OWNER}/{old_name}") or u.endswith(f":{OWNER}/{new_name}"):
            seen.append((d, url))
    return seen


def service_pid():
    """The service manager's own idea of the daemon's pid right now. 0 = none.

    Read once BEFORE the stop and again after the start, because a different
    number is the only cheap proof that a restart happened. Nothing here trusts
    it on its own — see restart_took.
    """
    if platform.system() == "Darwin":
        rc, out, _ = sh(["launchctl", "list"])
        if rc:
            return 0
        for line in out.splitlines():
            f = line.split()
            # PID  Status  Label — a job that is loaded but not running has "-".
            if len(f) >= 3 and f[-1] == PLIST_LABEL:
                try:
                    return int(f[0])
                except ValueError:
                    return 0
        return 0
    # Not --value: that option is systemd >= 230 and these machines are not all
    # the same vintage. "MainPID=1234" parses either way.
    rc, out, _ = sh(["systemctl", "--user", "show", "-p", "MainPID", SERVICE])
    if rc:
        return 0
    try:
        return int(out.rsplit("=", 1)[-1].strip())
    except ValueError:
        return 0


def daemon_stop():
    """Stop it. Returns (callable that starts it again, pid before the stop).

    (None, 0) if nothing was running. The pid is half the verification: after
    the start, the same pid means nothing restarted.
    """
    if platform.system() == "Darwin":
        plist = HOME / "Library" / "LaunchAgents" / f"{PLIST_LABEL}.plist"
        rc, out, _ = sh(["launchctl", "list"])
        if rc or PLIST_LABEL not in out:
            return None, 0
        before = service_pid()
        sh(["launchctl", "unload", str(plist)])
        return (lambda: sh(["launchctl", "load", str(plist)])), before
    rc, out, _ = sh(["systemctl", "--user", "is-active", SERVICE])
    if out != "active":
        return None, 0
    before = service_pid()
    sh(["systemctl", "--user", "stop", SERVICE])
    return (lambda: sh(["systemctl", "--user", "start", SERVICE])), before


def restart_took(pid_before, settle=None):
    """Did the daemon actually come back? Returns (ok, why) — why either way.

    Polls until SETTLE seconds have passed, because `systemctl start` returns
    for a Type=simple unit as soon as the child is FORKED. For the few
    milliseconds before it execs python, /proc/<pid>/cmdline still holds the
    argv it inherited from systemd, and the liveness rule would correctly say
    "that is not a retention guard" about a daemon that is starting perfectly
    well. Only success ends the wait early: every failure is re-asked until the
    window is closed, so the answer is about the daemon and not about timing.
    """
    deadline = time.monotonic() + (RESTART_SETTLE_S if settle is None else settle)
    while True:
        ok, why = restart_state(pid_before)
        if ok or time.monotonic() >= deadline:
            return ok, why
        time.sleep(0.25)


def restart_state(pid_before):
    """One look. All three questions, because each alone has already lied here:

      active?      the whole of the old check, and it printed "ok  daemon
                   active (active)" over a service that had been down 2h57m
      new pid?     the same MainPID is a stale read of the pre-stop state, not
                   a restart
      is it US?    _alive from retention_guard, unmodified: a pid that exists
                   is not a daemon, because pids are reused and the cmdline is
                   what tells them apart
    """
    if pid_is_the_daemon is None:
        return False, ("the liveness rule did not import "
                       f"(retention_guard: {LIVENESS_IMPORT_ERROR}) — refusing "
                       "to call a restart verified by a rule that is not loaded")
    if platform.system() == "Darwin":
        rc, out, _ = sh(["launchctl", "list"])
        active = rc == 0 and PLIST_LABEL in out
        state = "loaded" if active else "not loaded"
    else:
        _, state, _ = sh(["systemctl", "--user", "is-active", SERVICE])
        active = state == "active"
    pid_now = service_pid()
    if not active:
        return False, f"the service manager says {state or '(nothing)'}"
    if not pid_now:
        return False, f"{state}, but there is no pid — nothing is running under it"
    if pid_now == pid_before:
        return False, (f"{state}, but the pid is still {pid_now} — the one from "
                       "BEFORE the stop. That is a stale read, not a restart")
    if not pid_is_the_daemon(pid_now):
        return False, (f"{state}, pid {pid_before or '(none)'} -> {pid_now}, but "
                       f"{pid_now} is not a running retention guard")
    return True, (f"{state}, pid {pid_before or '(none)'} -> {pid_now}, and "
                  f"{pid_now} is a live retention guard")


def unit_drift(repo_unit, dest):
    """systemd loads a COPY of the unit. Report when it no longer matches.

    ~/.config/systemd/user/retention-guard.service is what runs; the repo's
    file is what people edit. They drift silently and only the copy has any
    effect. Returns the lines to print, empty when they agree or when there is
    no installed unit to compare against (a Mac, or a machine set up with cron).

    Nothing is installed or reloaded from here — that is a change to the
    running system, and `dest` is used only to spell the command out.
    """
    if not repo_unit.is_file() or not UNIT_INSTALLED.is_file():
        return []
    want = repo_unit.read_text().splitlines()
    have = UNIT_INSTALLED.read_text().splitlines()
    if want == have:
        return []
    real = lambda ls: [x for x in ls if x.strip() and not x.lstrip().startswith("#")]
    only_repo = [x for x in real(want) if x not in have]
    only_inst = [x for x in real(have) if x not in want]
    risky = [x for x in only_repo + only_inst
             if x.split("=", 1)[0].strip() in UNIT_LOAD_BEARING]

    out = ["", "  UNIT DRIFT — systemd is not running this file:",
           f"    repo       {repo_unit}",
           f"    installed  {UNIT_INSTALLED}   <- the one that is loaded"]
    for x in only_repo:
        out.append(f"      repo only   {x}")
    for x in only_inst:
        out.append(f"      loaded only {x}")
    if not only_repo and not only_inst:
        out.append("      (comments only — no directive differs)")
    out.append("    " + ("!! LOAD-BEARING: " + ", ".join(
        sorted({x.split('=', 1)[0].strip() for x in risky}))
        + " differ, so the running daemon is not the one this repo describes"
        if risky else
        "no directive that changes behaviour differs — untidy today, and the "
        "next edit to ExecStart= or Environment= would be silent"))
    out += ["    refresh it yourself when you are ready — this script does not "
            "touch the running system:",
            f"      cp {dest / UNIT_REPO_NAME} {UNIT_INSTALLED}",
            "      systemctl --user daemon-reload",
            f"      systemctl --user restart {SERVICE}"]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true", help="actually do it")
    a = ap.parse_args()
    act = a.yes

    print(f"\n  {platform.system()} · {platform.node()}\n")
    plan, problems = [], []

    for old, new, target in REPOS:
        found = find_checkout(old, new)
        dest = HOME / target
        if not found:
            problems.append(f"no checkout of {old}/{new} found under {HOME}")
            continue
        if len(found) > 1:
            problems.append(f"{len(found)} checkouts point at {new}: "
                            + ", ".join(str(d) for d, _ in found)
                            + " — rename by hand, this cannot choose")
            continue
        d, url = found[0]
        want_url = f"https://github.com/{OWNER}/{new}.git"
        is_count = new == "deadreckon-count"
        git_dir = d / ".git"
        bloat = 0
        if git_dir.is_dir():
            for r, _, fs in os.walk(git_dir):
                for f in fs:
                    try:
                        bloat += os.path.getsize(os.path.join(r, f))
                    except OSError:
                        pass
        plan.append({
            "dir": d, "dest": dest, "url": url, "want_url": want_url,
            "move": d != dest, "repoint": url.rstrip("/").removesuffix(".git")
                                          != want_url.removesuffix(".git"),
            "is_count": is_count,
            # The record repo is re-cloned. Its history holds every transcript
            # blob ever committed, and untracking them changed only the tip.
            "reclone": not is_count,
            "git_bytes": bloat,
        })

    for p in plan:
        print(f"  {p['dir'].name}   .git {p['git_bytes']/1e6:.0f} MB")
        if p["reclone"]:
            print(f"    RE-CLONE  {p['dir']}  ->  {p['dest']}")
            print(f"              old moved aside, not deleted; a fresh clone is "
                  f"~0.2 MB against {p['git_bytes']/1e9:.1f} GB")
            continue
        print(f"    move    {p['dir']}  ->  {p['dest']}" if p["move"]
              else "    move    already at the new path")
        print(f"    remote  {p['url']}  ->  {p['want_url']}" if p["repoint"]
              else "    remote  already correct")
        if p["dest"].exists() and p["move"]:
            problems.append(f"{p['dest']} already exists — refusing to move "
                            f"{p['dir']} on top of it")

    link_target = None
    for p in plan:
        if p["is_count"]:
            link_target = p["dest"] / "retention_guard.py"
    if LINK.is_symlink():
        cur = os.readlink(LINK)
        print(f"\n  symlink {LINK}\n    {cur}  ->  {link_target}")
    elif LINK.exists():
        problems.append(f"{LINK} exists and is NOT a symlink — the daemon is "
                        f"running a COPY, which is the thing the symlink "
                        f"exists to prevent. Fix that before renaming.")
    else:
        print(f"\n  symlink {LINK} does not exist — will be created")

    # Reported in both modes, before anything is touched, because it is a
    # finding about the machine rather than a step of the rename.
    drift = []
    for p in plan:
        if p["is_count"]:
            drift = unit_drift(p["dir"] / UNIT_REPO_NAME, p["dest"])
    for line in drift:
        print(line)

    if problems:
        print("\n  PROBLEMS — nothing was changed:")
        for x in problems:
            print(f"    !! {x}")
        return 1

    if not act:
        print("\n  dry run. Re-run with --yes to apply.")
        return 0

    print()
    restart, pid_before = daemon_stop()
    print(f"  daemon stopped (pid {pid_before or 'unknown'})" if restart
          else "  daemon was not running")

    for p in plan:
        if p["reclone"]:
            stamp = __import__("time").strftime("%Y%m%d-%H%M%S")
            aside = HOME / f"{p['dest'].name}.old-{stamp}"
            shutil.move(str(p["dir"]), str(aside))
            print(f"  moved aside  {p['dir'].name} -> {aside.name}  "
                  f"({p['git_bytes']/1e9:.1f} GB of history)")
            rc, _, err = sh(["git", "clone", "-q", p["want_url"], str(p["dest"])])
            if rc:
                # Put it back rather than leave the machine with neither.
                shutil.move(str(aside), str(p["dir"]))
                raise SystemExit(f"clone failed, original restored: {err[-300:]}")
            new_git = sum(os.path.getsize(os.path.join(r, f))
                          for r, _, fs in os.walk(p["dest"] / ".git") for f in fs)
            print(f"  cloned       {p['dest'].name}  .git {new_git/1e6:.1f} MB")
            print(f"               your transcripts come back on the next "
                  f"`run.py update`;\n               delete {aside.name} once "
                  f"that has succeeded.")
            continue
        if p["move"]:
            shutil.move(str(p["dir"]), str(p["dest"]))
            print(f"  moved   {p['dir'].name} -> {p['dest'].name}")
        if p["repoint"]:
            sh(["git", "remote", "set-url", "origin", p["want_url"]],
               cwd=str(p["dest"]), check=True)
            print(f"  remote  {p['dest'].name} -> {p['want_url']}")

    if link_target and link_target.is_file():
        LINK.parent.mkdir(parents=True, exist_ok=True)
        if LINK.is_symlink() or LINK.exists():
            LINK.unlink()
        LINK.symlink_to(link_target)
        print(f"  symlink {LINK} -> {link_target}")

    restart_ok, restart_why = True, ""
    if restart:
        rc, _, err = restart()
        if rc:
            # The return code was thrown away here, and "daemon started" was
            # printed for having reached the line. 2h57m.
            restart_ok = False
            restart_why = (f"the start command exited {rc}: "
                           + ((err.splitlines() or ["(no stderr)"])[0]))
        else:
            restart_ok, restart_why = restart_took(pid_before)
        print("  daemon started" if restart_ok else "  DAEMON DID NOT START")

    # VERIFY, rather than assume. Each of these has failed in this project.
    print("\n  verifying")
    ok = True
    for p in plan:
        good = p["dest"].is_dir()
        print(f"    {'ok  ' if good else 'FAIL'} {p['dest']} exists")
        ok &= good
    if LINK.is_symlink():
        good = pathlib.Path(os.readlink(LINK)).is_file()
        print(f"    {'ok  ' if good else 'FAIL'} symlink resolves to a real file")
        ok &= good
    count = HOME / "deadreckon-count"
    if (count / "test_readers.py").is_file():
        rc, _, _ = sh([sys.executable, "test_readers.py"], cwd=str(count))
        print(f"    {'ok  ' if rc == 0 else 'FAIL'} test_readers.py from the new path")
        ok &= rc == 0
    if restart:
        print(f"    {'ok  ' if restart_ok else 'FAIL'} daemon restarted — {restart_why}")
        ok &= restart_ok

    if restart and not restart_ok:
        # Loudly, and last, because this is the one failure the machine will
        # not report by itself: the rename succeeded, so everything looks done.
        print("\n  !! THE RENAME IS DONE AND THE GUARD IS NOT RUNNING.")
        print("     Transcripts start expiring again at the next Claude Code")
        print("     startup and nothing else here will say so. Bring it back:")
        for line in (daemon_remediation("running") if daemon_remediation else
                     [f"check: systemctl --user status {SERVICE}"]):
            print(f"       {line}")

    print("\n  " + ("done — now: cd ~/deadreckon-count && python3 run.py update"
                    if ok else "SOMETHING FAILED ABOVE. Fix it before scanning."))
    if drift:
        print("  the installed unit is still a copy — see UNIT DRIFT above.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
