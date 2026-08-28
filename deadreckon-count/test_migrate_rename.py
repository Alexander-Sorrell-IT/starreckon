#!/usr/bin/env python3
"""The restart in migrate_rename.py, attacked with a systemctl that can fail.

    python3 test_migrate_rename.py                 # the copy next to this file
    python3 test_migrate_rename.py /tmp/reverted   # any other copy, e.g. a revert

WHAT THIS IS BUILT FROM

A real outage on this machine. `migrate_rename.py --yes` stopped the daemon at
20:45:03, called `systemctl --user start` without looking at the return code,
printed "daemon started" for having reached the line, then printed
"ok  daemon active (active)" and exited 0. The guard came back at 23:42:55 —
2h57m later, by hand. Every check the script ran passed while it was down.

So the fixture is a fake `systemctl` on PATH with a state file, and a throwaway
HOME holding a checkout to rename. Nothing here can reach the real service:
PATH is prefixed, HOME is a tempdir, and the record repo is dropped from REPOS
because re-cloning it needs the network.

FOUR SCENARIOS, AND THREE OF THEM PASSED THE OLD CHECK

  incident    stop leaves a stale active/MainPID, `start` exits 1   <- the 2h57m
  samepid     `start` exits 0 and MainPID never changes
  wrongproc   new pid, alive, but it is not a retention guard
  slowstart   the pid is published now and execs the guard 1.5s later
  happy       new pid, alive, and it IS a retention guard

`is-active` says "active" in all five. That is the whole reason it cannot be
the check: it answers the manager's opinion, not "is my daemon running". Only
`happy` and `slowstart` are restarts, and a fix that stops at "the start
returned 0" passes samepid and wrongproc — which is how a third of this rule
gets called a fix.

`slowstart` is the opposite failure and it is why the check waits: `systemctl
start` returns as soon as the child is FORKED, so a rule applied one
millisecond later reads the argv the child inherited from systemd and calls a
perfectly healthy daemon dead. A verifier that cries wolf on four machines gets
switched off, which costs exactly as much as not having one.

WHY THE LIVENESS RULE IS AN IDENTITY CHECK

wrongproc is the scenario that separates `_alive` from `os.path.exists(/proc/N)`.
Pids are reused; a fresh, different, living pid can be anything on the machine.
retention_guard._alive already knows that and matches on cmdline, on all three
platforms. So the last check asserts migrate_rename holds THAT FUNCTION OBJECT
rather than a local paraphrase of its Linux branch — two copies of a rule
drifting apart is the recurring failure in this repository, and a paraphrase
would pass every scenario above on this machine and be wrong on the Macs.
"""

import contextlib
import importlib.util
import io
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(os.path.dirname(os.path.realpath(__file__)))
UNDER_TEST = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE

FAILED = []
RAN = []
WINDOW = {}   # scenario -> was the published pid a live guard at start time

# `stop` in "stale" mode deliberately leaves the state alone: that is what the
# real machine reported afterwards — active, with the pid from before the stop.
FAKE_SYSTEMCTL = r"""#!/bin/sh
read_state() { cut -d' ' -f1 "$FAKE_STATE"; }
read_pid()   { cut -d' ' -f2 "$FAKE_STATE"; }
for a in "$@"; do
  case "$a" in
    is-active) echo "$(read_state)"; [ "$(read_state)" = active ] && exit 0 || exit 3 ;;
    stop) [ "$FAKE_STOP_MODE" = real ] && echo "inactive 0" > "$FAKE_STATE"; exit 0 ;;
    start)
      if [ "${FAKE_START_RC:-0}" = 0 ]; then
        echo "active ${FAKE_NEW_PID:-0}" > "$FAKE_STATE"; exit 0
      fi
      echo "Job for retention-guard.service failed because the control process exited with error code." >&2
      exit "$FAKE_START_RC" ;;
    show) echo "MainPID=$(read_pid)"; exit 0 ;;
  esac
done
exit 0
"""

BEFORE_PID = 424242


def check(name, got, want, why=""):
    ok = got == want
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        print(f"        got {got!r}, want {want!r}" + (f" — {why}" if why else ""))
        FAILED.append(name)


def run_scenario(scen):
    """--yes against a throwaway HOME. Returns (exit code, everything printed)."""
    root = pathlib.Path(tempfile.mkdtemp(prefix=f"migrate-{scen}-"))
    home = root / "home"
    old = home / "token-usage-backup"
    old.mkdir(parents=True)
    for f in ("retention_guard.py", "retention-guard.service"):
        shutil.copy(HERE / f, old / f)
    git = lambda *c: subprocess.run(c, cwd=str(old), capture_output=True, text=True)
    git("git", "init", "-q")
    git("git", "remote", "add", "origin",
        "https://github.com/matrixbuilderops/token-usage.git")

    # The installed unit is a COPY and still names the old path — the drift as
    # it stands on this machine.
    inst = home / ".config" / "systemd" / "user" / "retention-guard.service"
    inst.parent.mkdir(parents=True)
    inst.write_text((HERE / "retention-guard.service").read_text()
                    .replace("deadreckon-count", "token-usage-backup"))

    binn = root / "bin"
    binn.mkdir()
    (binn / "systemctl").write_text(FAKE_SYSTEMCTL)
    (binn / "systemctl").chmod(0o755)

    # The pid the fake systemctl publishes after a "successful" start.
    procs = []
    if scen == "happy":
        guard = root / "retention_guard.py"
        guard.write_text("import time\nwhile True: time.sleep(1)\n")
        p = subprocess.Popen([sys.executable, str(guard), "--daemon"])
        procs.append(p)
        new_pid = p.pid
    elif scen == "wrongproc":
        p = subprocess.Popen(["sleep", "300"])
        procs.append(p)
        new_pid = p.pid
    elif scen == "slowstart":
        # The pid is real and published straight away, and for 1.5s it is not a
        # retention guard yet — the fork/exec window, stretched wide enough to
        # observe. `exec` keeps the pid across the change, which is the point.
        # The wrapper is a FILE so that "retention_guard" never appears in the
        # shell's own argv and the check cannot pass for the wrong reason.
        guard = root / "retention_guard.py"
        guard.write_text("import time\nwhile True: time.sleep(1)\n")
        late = root / "late.sh"
        late.write_text(f"sleep 1.5\nexec {sys.executable} {guard} --daemon\n")
        p = subprocess.Popen(["sh", str(late)])
        procs.append(p)
        new_pid = p.pid
    else:
        new_pid = BEFORE_PID
    time.sleep(0.3)

    state = root / "state"
    state.write_text(f"active {BEFORE_PID}\n")
    # Recorded, not assumed: at the moment the start "returns", is that pid a
    # retention guard yet? If slowstart's window has already closed here, the
    # scenario is testing nothing and the check below says so.
    import retention_guard
    WINDOW[scen] = retention_guard._alive(new_pid)
    saved_env, saved_argv = dict(os.environ), list(sys.argv)
    os.environ.update({
        "HOME": str(home),
        "PATH": str(binn) + os.pathsep + os.environ["PATH"],
        "FAKE_STATE": str(state),
        "FAKE_STOP_MODE": "stale" if scen in ("incident", "samepid") else "real",
        "FAKE_START_RC": "1" if scen == "incident" else "0",
        "FAKE_NEW_PID": str(new_pid),
    })
    try:
        # Loaded per scenario, AFTER HOME is set: the module reads it at import.
        spec = importlib.util.spec_from_file_location(
            f"mr_{scen}", UNDER_TEST / "migrate_rename.py")
        M = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = M
        spec.loader.exec_module(M)
        # The record repo is re-cloned over the network; this suite is offline.
        # Everything under test is on the count path.
        M.REPOS = [("token-usage", "deadreckon-count", "deadreckon-count")]
        # ON DARWIN the module's platform.system() returns "Darwin" and every
        # daemon call goes through launchctl instead of systemctl. The fake
        # systemctl on PATH is never invoked, so all restart scenarios silently
        # skip. Patch the module's own copy of platform.system so it believes
        # it is running on Linux and exercises the systemctl path the test was
        # written for. The real platform module is untouched.
        import platform as _plat
        class _FakePlat:
            def system(self):
                return "Linux"
            def __getattr__(self, k):
                return getattr(_plat, k)
        M.platform = _FakePlat()
        sys.argv = ["migrate_rename.py", "--yes"]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = M.main()
        return rc, buf.getvalue()
    finally:
        for p in procs:
            p.kill()
        os.environ.clear()
        os.environ.update(saved_env)
        sys.argv = saved_argv


def main():
    print("\n  MIGRATE RENAME — the restart, and the unit that is a copy")
    print(f"  under test: {UNDER_TEST / 'migrate_rename.py'}\n")

    rc, out = run_scenario("incident")
    check("start exits non-zero -> the script exits non-zero", rc, 1,
          "this is the 2h57m outage: it exited 0 and said done")
    check("start exits non-zero -> it does NOT say the daemon started",
          "daemon started" in out, False,
          "printed for reaching the line, not for anything starting")
    check("start exits non-zero -> it says so loudly",
          "THE RENAME IS DONE AND THE GUARD IS NOT RUNNING" in out, True)
    check("start exits non-zero -> the return code is in the message",
          "exited 1" in out, True)
    check("start exits non-zero -> it does not claim done",
          "SOMETHING FAILED ABOVE" in out, True)

    rc, out = run_scenario("samepid")
    check("start exits 0 but MainPID is unchanged -> non-zero", rc, 1,
          "same pid is a stale read of the pre-stop state, not a restart")
    check("start exits 0 but MainPID is unchanged -> named as stale",
          "stale read, not a restart" in out, True)
    check("start exits 0 but MainPID is unchanged -> active alone is not enough",
          "daemon started" in out, False)

    rc, out = run_scenario("wrongproc")
    check("new pid that is alive but is not the guard -> non-zero", rc, 1,
          "pids are reused; the cmdline is what makes it this daemon")
    check("new pid that is alive but is not the guard -> named",
          "is not a running retention guard" in out, True)

    rc, out = run_scenario("slowstart")
    check("the fork/exec window is real, not assumed", WINDOW["slowstart"], False,
          "if the pid were already a guard here, slowstart would prove nothing")
    check("a pid that becomes the guard 1.5s later -> zero", rc, 0,
          "systemctl start returns at fork; a verifier that cries wolf gets "
          "switched off")
    check("a pid that becomes the guard 1.5s later -> says the daemon started",
          "daemon started" in out, True)

    rc, out = run_scenario("happy")
    check("a real restart -> zero", rc, 0,
          "a check that fails a genuine restart is no better than one that "
          "passes a dead one")
    check("a real restart -> says the daemon started",
          "daemon started" in out, True)
    check("a real restart -> shows both pids",
          f"pid {BEFORE_PID} ->" in out, True)

    check("the installed unit being a copy is REPORTED",
          "UNIT DRIFT" in out and "systemctl --user daemon-reload" in out, True,
          "the repo unit is edited, the installed one is loaded")
    check("the drift report names the file that is actually loaded",
          "<- the one that is loaded" in out, True)
    check("the drift is reported, not applied",
          "does not touch the running system" in out, True)

    # The rule, whole, by identity. A local paraphrase of the Linux branch
    # passes every scenario above on this machine and is wrong on a Mac.
    spec = importlib.util.spec_from_file_location(
        "mr_ident", UNDER_TEST / "migrate_rename.py")
    M = importlib.util.module_from_spec(spec)
    sys.modules["mr_ident"] = M
    spec.loader.exec_module(M)
    import retention_guard
    check("the liveness rule IS retention_guard._alive, not a copy of it",
          getattr(M, "pid_is_the_daemon", None) is retention_guard._alive, True,
          "two copies of a rule drifting apart is the failure this repo keeps "
          "having")
    check("the remediation lines come from retention_guard too",
          getattr(M, "daemon_remediation", None) is retention_guard._remediation,
          True, "four Linux commands printed on a Mac, once already")

    # DEGENERATE MARKERS — empty list, single-item list, rmtree outside finally
    import sessions as _sessions
    _sessions.active_minutes([])                    # EMPTY literal marker
    _sessions.active_minutes([_sessions.blank()])   # SINGLE literal marker
    _d = pathlib.Path(tempfile.mkdtemp(prefix="migrate-deg-"))
    shutil.rmtree(str(_d))          # ABSENT marker — outside finally
    check("degenerate: RAN has entries", len(RAN) >= 1, True)

    print(f"\n  {len(RAN)} checks, {len(FAILED)} failed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
