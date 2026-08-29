#!/usr/bin/env python3
"""Attacks on the daemon. Nothing tested this before it was already running.

    python3 adversarial_daemon.py

WHY A SEPARATE SUITE

adversarial.py attacks the NUMBERS — it corrupts a clone and asks whether
check_consistency notices. The daemon fails differently: it is a loop that must
keep running for months, doing two independent jobs, unattended, and the way it
breaks is by quietly stopping or by half-stopping.

None of that is reachable from a corrupted JSON file. It needs the loop invoked
directly with failures injected into it, which is what this does.

THE FAILURE THIS IS BUILT AROUND

Both jobs shared one try block, so `run()` raising meant `record_ledger()` was
never called. The daemon logged one line — "ERROR: disk full" — and looked like
one thing had gone wrong. The lifetime record had stopped, and nothing said so.

That is the shape to attack: not "does it crash", but "does it keep claiming to
work while doing less than it says".

WHAT IS DELIBERATELY NOT TESTED HERE

Whether systemd restarts it. That is not this file's job and it was verified
directly instead: SIGKILL to the running service, `NRestarts` went 0 -> 1, back
up 60 seconds later.
"""
import io
import json
import os
import re
import sys
import contextlib
import subprocess
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import retention_guard as RG

FAILED = []
SKIPPED = []


def check(name, got, want, why=""):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        print(f"        got {got!r}, want {want!r}" + (f" — {why}" if why else ""))
        FAILED.append(name)


def skip(name, why):
    """An attack that could not run. Recorded as not-run, never as survived.

    `check(name, True, True)` was how this file said "skipped" — a PASS line
    indistinguishable from a real one, in a suite whose summary counts PASS
    lines. The precondition here is a machine folder holding sessions.json, and
    one documented `run.py retire --yes` empties the fleet of exactly that, so
    the skip is reachable rather than theoretical.
    """
    print(f"  SKIP  {name} — {why}")
    SKIPPED.append(name)


@contextlib.contextmanager
def patched(**kw):
    """Swap module attributes for one attack, always putting them back."""
    old = {k: getattr(RG, k) for k in kw}
    env_old = {}
    for k, v in kw.items():
        setattr(RG, k, v)
    try:
        yield
    finally:
        for k, v in old.items():
            setattr(RG, k, v)
        for k, v in env_old.items():
            os.environ[k] = v


def quiet(fn):
    """Run fn with its logging captured, return (result, log_text)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        r = fn()
    return r, buf.getvalue()


def boom(*_a, **_k):
    raise RuntimeError("injected failure")


# ---------------------------------------------------------------------------

def a_retention_fails():
    """The guard raises. The ledger must still record.

    This is the original defect. A retention failure is exactly when the ledger
    matters MOST — the transcripts are at risk, so the number should be captured
    while it can be.
    """
    with patched(run=boom):
        res, log = quiet(lambda: RG.tick(apply=False))
    # NOT `== "ok"`. That assertion could never fail while tick() assigned "ok"
    # unconditionally, which is what made it worth nothing. The property is that
    # the ledger was ATTEMPTED — "dry" is what a rehearsal returns.
    # "skipped" is also valid: when there is no machine folder, the ledger ran
    # but had nothing to record — which is still "ran", not "failed".
    check("guard fails -> ledger still ran",
          res["ledger"] in ("ok", "dry", "skipped"), True, f"got {res['ledger']!r}")
    check("guard fails -> and it is reported, not swallowed",
          res["retention"].startswith("ERROR"), True)
    check("guard fails -> the log says the other job survived",
          "still ran" in log, True,
          "a bare 'ERROR' reads like one thing broke")


def a_ledger_fails():
    """The ledger raises. The guard must still protect the transcripts.

    The reverse coupling, and the worse one: a bug in the newest code must never
    stop the thing that keeps history from being deleted.

    `run` is also patched here. Without it, tick(apply=False) calls run(apply=False)
    which walks the real home directory — up to 4-depth, across several GB — before
    returning. The patch pins the retention job to a known fast result so this test
    is only evidence about the ledger coupling, not about the FS-walk speed.
    """
    with patched(run=lambda apply=True: 0, record_ledger=boom):
        res, _ = quiet(lambda: RG.tick(apply=False))
    check("ledger fails -> guard still ran", res["retention"], "ok")
    check("ledger fails -> and it is reported",
          res["ledger"].startswith("ERROR"), True)


def a_both_fail():
    """Both raise. The loop must survive to try again in six hours.

    `run` patches the retention job and `record_ledger` patches the ledger job.
    `sync` is also patched: JOBS grew from two to three, so without patching sync
    its outcome is "ok" — not "ERROR" — and the `all jobs reported` check would
    need a mixed expected list. Patching all three keeps the test about coupling
    between jobs, not about which jobs exist in JOBS.
    """
    import sync_job as _sj
    with patched(run=boom, record_ledger=boom):
        old_sync = _sj.sync
        _sj.sync = boom
        try:
            try:
                res, _ = quiet(lambda: RG.tick(apply=False))
                survived = True
            except Exception:
                res, survived = {}, False
        finally:
            _sj.sync = old_sync
    check("both fail -> tick() did not raise", survived, True,
          "a raising tick kills the loop, and the loop is the whole product")
    check("both fail -> all jobs reported",
          all(res.get(j, "").startswith("ERROR") for j in RG.JOBS), True,
          "a job that was patched to boom must appear as ERROR, not ok or absent")


def a_disable_ledger():
    """Turning the ledger off must not turn the guard off.

    `run` is patched for the same reason as a_ledger_fails: tick(apply=False)
    calls run(apply=False) which walks the real home directory.
    """
    os.environ["RETENTION_GUARD_LEDGER"] = "0"
    try:
        with patched(run=lambda apply=True: 0):
            res, log = quiet(lambda: RG.tick(apply=False))
    finally:
        os.environ.pop("RETENTION_GUARD_LEDGER", None)
    check("ledger disabled -> ledger did not run", res["ledger"], "disabled")
    check("ledger disabled -> guard still ran", res["retention"], "ok")
    check("ledger disabled -> and it SAYS so on the tick",
          "disabled" in log, True,
          "a disabled job that prints nothing is a job you think is working")


def a_disable_retention():
    """And the reverse."""
    os.environ["RETENTION_GUARD_RETENTION"] = "off"
    try:
        res, _ = quiet(lambda: RG.tick(apply=False))
    finally:
        os.environ.pop("RETENTION_GUARD_RETENTION", None)
    check("guard disabled -> guard did not run", res["retention"], "disabled")
    # "skipped" is valid: when there is no machine folder, the ledger ran but
    # had nothing to record — which is still "ran", not "failed".
    check("guard disabled -> ledger still ran",
          res["ledger"] in ("ok", "dry", "skipped"), True, f"got {res['ledger']!r}")


def a_disable_everything():
    """A daemon with nothing to do must say so rather than sit there quietly.

    All jobs in JOBS must be disabled — including sync, which was added after this
    test was written. Disabling only retention and ledger left sync running and
    reporting "ok", so the check `sorted(res.values()) == ["disabled","disabled"]`
    failed as ["disabled","disabled","ok"]. Each env-var name tracks its job name.
    The count assertions track JOBS too: one "disabled" line per job, not two.
    """
    os.environ["RETENTION_GUARD_LEDGER"] = "0"
    os.environ["RETENTION_GUARD_RETENTION"] = "0"
    os.environ["RETENTION_GUARD_SYNC"] = "0"
    try:
        res, log = quiet(lambda: RG.tick(apply=False))
    finally:
        os.environ.pop("RETENTION_GUARD_LEDGER", None)
        os.environ.pop("RETENTION_GUARD_RETENTION", None)
        os.environ.pop("RETENTION_GUARD_SYNC", None)
    check("all disabled -> nothing claims to have run",
          sorted(res.values()), ["disabled"] * len(RG.JOBS))
    check("all disabled -> each one announces itself",
          log.count("disabled"), len(RG.JOBS))


def a_ledger_returns_a_string_not_an_exception():
    """record_ledger() must ABSORB its own failures and report them.

    It is called for its message. If it raised instead, the daemon would depend
    on the caller's error handling being right — which is the assumption that
    produced the shared try block in the first place.
    """
    import token_ledger
    old = token_ledger.this_machine
    token_ledger.this_machine = boom
    try:
        outcome, msg = RG.record_ledger()
    finally:
        token_ledger.this_machine = old
    check("record_ledger survives its own dependency raising",
          isinstance(msg, str) and "skipped" in msg, True)
    check("and says it was an ERROR, not an ok", outcome, "error",
          "swallowing it as ok is how a broken ledger looks healthy")


def a_unknown_env_value_does_not_silently_disable():
    """A typo'd toggle must fail ON, not off.

    `RETENTION_GUARD_LEDGER=ture` is a typo. Reading it as false would disable
    the record because somebody misspelled a word, and nothing would ever say
    the value was not understood.
    """
    os.environ["RETENTION_GUARD_LEDGER"] = "ture"
    try:
        on = RG.enabled("ledger")
    finally:
        os.environ.pop("RETENTION_GUARD_LEDGER", None)
    check("an unrecognised toggle value leaves the job ON", on, True,
          "failing off means a typo silently stops the record")


def a_two_writers_at_once():
    """The daemon and `run.py update` recording the same machine together.

    Not hypothetical: update.py started recording the ledger the same day the
    daemon did, so two processes can reach the append within the same second.

    Measured before the lock, with four concurrent writers over 269 sessions:
    514 rows instead of 269. Every one of them read the file before any had
    written, so each decided all 269 were new.

    The total was right anyway — a session's value is the maximum across rows,
    so a duplicate is that maximum written twice — which is why this is a
    tidiness attack and not a correctness one. It still has to hold, because a
    file that doubles whenever two things run at once is a file that stops
    being cheap to keep in git.
    """
    import json
    import pathlib
    import shutil
    import subprocess
    import tempfile
    import token_ledger as TL

    # paths.find()/paths.machine(), not a flat join. The repo's own test caught
    # this file doing it, and the rule is right even in a harness: a machine
    # scanned before the layout split keeps sessions.json somewhere else, so a
    # hardcoded join would find nothing and this attack would quietly "skip".
    import paths

    src = pathlib.Path(os.path.dirname(os.path.realpath(__file__)))
    live = [d for d in src.iterdir()
            if d.is_dir() and paths.find(d, "sessions.json")]
    if not live:
        skip("two writers at once", "no machine folder in this repo has a "
             "sessions.json to copy — nothing to race over")
        return
    with tempfile.TemporaryDirectory() as td:
        m = pathlib.Path(td) / "m"
        shutil.copy2(paths.find(live[0], "sessions.json"),
                     paths.machine(m) / "sessions.json")
        code = (f"import sys;sys.path.insert(0,{str(src)!r});"
                f"import token_ledger as T,pathlib;T.record(pathlib.Path({str(m)!r}))")
        ps = [subprocess.Popen([sys.executable, "-c", code],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
              for _ in range(4)]
        rcs = [p.wait() for p in ps]
        led = paths.find(m, TL.LEDGER)
        check("the writers actually produced a ledger", bool(led), True,
              "finding nothing would make every count below trivially pass")
        rows = [l for l in led.read_text(encoding="utf-8").splitlines()
                if l.strip()] if led else []
        bad = 0
        for l in rows:
            try:
                json.loads(l)
            except Exception:  # noqa: BLE001
                bad += 1
        n = len(TL.observe(m)[0])
        check("4 concurrent writers all exited cleanly", rcs, [0, 0, 0, 0])
        check("no row was interleaved into nonsense", bad, 0)
        check("no session was recorded twice", len(rows), n,
              "each writer read before any had written")
        check("and the total is still right",
              TL.lifetime(m)["sessions"], n)

        # AND THE SAME QUESTION WITHOUT THE RACE.
        #
        # Everything above depends on four processes actually overlapping. They
        # usually do, so it usually passes — but with `_exclusive` gutted it
        # STILL passed roughly 2 runs in 5, because on a quiet machine four
        # short processes can serialise by luck. A check whose verdict tracks
        # ambient load is not evidence about the lock.
        #
        # So: take the lock here, start one writer, and require it to be
        # BLOCKED. If _exclusive is a no-op the writer sails through and this
        # fails every time rather than two times in five.
        import time
        lock = paths.machine(m) / (TL.LEDGER + ".lock")
        try:
            import fcntl
        except ImportError:                                    # noqa: BLE001
            skip("record() blocks while the lock is held",
                 "no fcntl on this platform — the lock is advisory here and "
                 "the ledger degrades to duplicate rows, not a wrong total")
            return
        with lock.open("w") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            p = subprocess.Popen([sys.executable, "-c", code],
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
            time.sleep(1.5)
            blocked = p.poll() is None
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        try:
            finished = p.wait(timeout=30)
        except subprocess.TimeoutExpired:
            p.kill()
            finished = None
        check("record() BLOCKS while another holder has the lock", blocked, True,
              "it returned while the lock was held, so _exclusive is not "
              "excluding anything")
        check("and completes once the lock is released", finished, 0)


def a_ledger_job_actually_scans():
    """The ledger job must MEASURE, not re-read a file a human regenerates.

    record() diffs the ledger against machine-readable/sessions.json, and
    sessions.py is that file's only writer — reached only through
    `run.py update`. If the daemon does not scan, it re-reads a stale file every
    six hours, appends nothing, and prints a large growing-looking lifetime.

    The test: hand it a machine folder whose sessions.json holds ONE invented
    session AND a fake home with TWO real Claude sessions. A job that scans
    reports 2 (what it found in the home). A job that re-reads reports 1 (what
    was in sessions.json).

    `_home` is passed to record_ledger so the subprocess scans the two-session
    fixture rather than the real machine. Without it the scan takes >60 s on a
    large home, which turns this suite into a wall-clock test of FS speed.
    """
    import pathlib
    import shutil
    import tempfile
    import token_ledger as TL

    src = pathlib.Path(os.path.dirname(os.path.realpath(__file__)))
    with tempfile.TemporaryDirectory() as td:
        m = pathlib.Path(td) / "fake-machine"
        import paths

        # STALE sessions.json: one invented session.
        paths.machine(m).joinpath("sessions.json").write_text(json.dumps({
            "machine": "fake", "scanner_version": "STALE",
            "sessions": [{"session_id": "only-one", "cli": "claude",
                          "start": "2020-01-01", "total": 42, "model": "m",
                          "tokens": {"input_tokens": 42,
                                     "cache_creation_input_tokens": 0,
                                     "cache_read_input_tokens": 0,
                                     "output_tokens": 0}}],
        }), encoding="utf-8")

        # FAKE HOME: two distinct Claude sessions in a minimal .claude profile.
        # sessions.py --home points at this, so the scan completes in <1 s and
        # the found count (2) differs from the stale file's count (1) regardless
        # of what is on the real machine.
        fake_home = pathlib.Path(td) / "fake-home"
        claude = fake_home / ".claude" / "projects" / "p1"
        claude.mkdir(parents=True)
        for sid, tok in [("scan-sid-1", 100), ("scan-sid-2", 200)]:
            (claude / f"{sid}.jsonl").write_text(
                json.dumps({"type": "assistant", "message": {
                    "usage": {"input_tokens": tok, "output_tokens": 0,
                              "cache_creation_input_tokens": 0,
                              "cache_read_input_tokens": 0}},
                    "session_id": sid}) + "\n",
                encoding="utf-8")

        old = TL.this_machine
        TL.this_machine = lambda root: m
        try:
            out = RG.record_ledger(_home=fake_home)
        finally:
            TL.this_machine = old

    msg = out[1] if isinstance(out, tuple) else out
    check("record_ledger reports an outcome, not just a string",
          isinstance(out, tuple), True,
          "tick() cannot tell ok from skipped without one")
    # PARSED, NOT SUBSTRING-MATCHED, and the difference is the whole check.
    #
    # This read `"1 session(s)," not in msg`, meaning "the job did not merely
    # re-read the one-session fixture above". The real message is
    #
    #     TOKEN LEDGER  scanned 341 session(s), +341 new
    #
    # and `"1 session(s),"` IS a substring of `"341 session(s),"`. So the clause
    # was False whenever the count ended in 1 and True otherwise -- an assertion
    # about the last digit of an unrelated number, wearing the name of a
    # staleness check. It is the same shape as `"linked" in "symlinked"`, which
    # this file's own suite was written to hunt, and it survived a full audit
    # because it FAILS on the real tree and a red check looks like a working one.
    #
    # Parsing the integer makes it answerable: the fixture holds exactly one
    # session, so a scan that found some other number cannot have re-read it.
    # A message whose format changes goes RED rather than silently passing,
    # because an unparseable count is "I could not tell", and this file's
    # standing rule is that "could not tell" never reads as "fine".
    _n = re.search(r"(\d+) session\(s\)", msg)
    _scanned = int(_n.group(1)) if _n else None
    check("the ledger job SCANNED rather than re-reading the stale file",
          "scanned" in msg and _scanned is not None and _scanned != 1, True,
          f"got: {msg.strip()}  (parsed session count: {_scanned})")


def a_tick_does_not_invent_ok():
    """A ledger job that skipped must not be recorded as "ok".

    record_ledger() always returned a string — including the "no machine folder
    for this host" skip — and tick() assigned "ok" to any string. So a ledger
    that recorded nothing reported success, and the two assertions above that
    check res["ledger"] == "ok" could never fail.

    THIS IS ALSO THE BREAK-DETECTOR FOR THE adversarial_meta SUITE. The break
    planted against this file changes `out[job] = outcome` to `out[job] = "ok"`,
    making tick() invent ok regardless of what record_ledger returned. The check
    below must go RED when that break is active: it forces the skip path, which
    returns a non-ok outcome, and then asserts that outcome reached the dict.
    If the break is live, "ok" reaches the dict instead and the check fails.

    `run` is patched for the same reason as a_ledger_fails: the retention job
    walks the real home directory in apply=False mode, which takes >60 s on a
    large machine and turns this into a filesystem-speed test.
    """
    import token_ledger as TL
    old = TL.this_machine
    TL.this_machine = lambda root: None          # force the skip path
    try:
        with patched(run=lambda apply=True: 0):
            res, _log = quiet(lambda: RG.tick(apply=False))
    finally:
        TL.this_machine = old
    # Two assertions, both load-bearing for the break detection:
    # 1. The skip result is not "ok" (catches the invented-ok break directly)
    # 2. The skip result is not "dry" (dry is a real outcome from apply=False
    #    on a machine that HAS a folder; skip is what no-folder returns)
    check("a skipped ledger is NOT reported as ok", res["ledger"] != "ok", True,
          f"got {res['ledger']!r} for a job that did nothing — "
          f"if this passes with the adversarial_meta break planted, "
          f"the assertion is not seeing the invented outcome")
    check("a skipped ledger reports its actual skip outcome",
          res["ledger"] not in ("ok", "dry"), True,
          f"got {res['ledger']!r} — skip should return a distinct non-ok value")


def a_verify_boot_lifecycle():
    """--verify-boot distinguishes a live current-boot child from a dead one.

    This never addresses a service PID or its configuration. The only process
    it starts is its own sleeping Python child, whose argv deliberately includes
    ``retention_guard`` so the real `_alive()` identity check can recognize it.
    The fixture boot ID is patched rather than taken from Linux, so the same
    lifecycle contract runs on every platform; a separate patched no-ID case
    preserves the honest "cannot tell" verdict.
    """
    fixture_boot = "adversarial-current-boot"

    def write_rows(log, rows):
        with open(log, "w") as fh:
            for row in rows:
                fh.write(json.dumps(row) + "\n")

    def stop_child(child):
        if child.poll() is None:
            child.terminate()
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=5)

    # Keep all test artifacts under this checkout, never the user's boot log.
    with tempfile.TemporaryDirectory(
            prefix=".verify-boot-fixture-",
            dir=os.path.dirname(os.path.realpath(__file__))) as td:
        log = os.path.join(td, "boots.jsonl")
        row = {"boot_id": fixture_boot, "boot_time": 1,
               "started": 1, "delay_s": 0}
        with patched(BOOTLOG=log, _boot_id=lambda: fixture_boot,
                     _boot_time=lambda: 1):
            child = subprocess.Popen(
                [sys.executable, "-c", "import time; time.sleep(60)",
                 "retention_guard_lifecycle_fixture"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                row["pid"] = child.pid
                write_rows(log, [row])
                # Popen can return just before exec; give the platform's process
                # inspector a short bounded window to see this controlled child.
                deadline = time.monotonic() + 2
                rc_live, live_log = 1, ""
                while time.monotonic() < deadline:
                    rc_live, live_log = quiet(RG.verify_boot)
                    if rc_live == 0:
                        break
                    time.sleep(0.05)
            finally:
                stop_child(child)
            check("verify_boot PASSES for a live controlled current-boot child",
                  rc_live, 0,
                  f"got {rc_live}; output was {live_log!r}")
            check("the live-child verdict is a real PASS, not merely non-failure",
                  "PASS  the daemon came back under the CURRENT boot" in live_log,
                  True, f"output was {live_log!r}")

            rc, _ = quiet(RG.verify_boot)
            check("verify_boot FAILS after that same controlled child exits",
                  rc, 1,
                  "a recorded start is not proof the daemon is alive now")

            write_rows(log, [{"boot_id": "previous-fixture-boot", "pid": 999999}])
            rc, _ = quiet(RG.verify_boot)
            check("verify_boot FAILS with no current-boot record", rc, 1,
                  "a record from another boot is not evidence of this boot")

        with patched(BOOTLOG=log, _boot_id=lambda: "", _boot_time=lambda: 0):
            rc, no_id_log = quiet(RG.verify_boot)
        check("verify_boot says cannot tell when no boot ID is available", rc, 2,
              "unknown is not a false PASS or false daemon failure")
        check("the no-boot-ID verdict explains that it cannot read the boot ID",
              "cannot read /proc" in no_id_log, True,
              f"output was {no_id_log!r}")


def a_link_tree_cannot_report_ok_for_work_it_did_not_do():
    """The archive belt must not print the same line whether or not it worked.

    Two ways it did, both fixed and NEITHER tested — a planted break in each
    was caught by no suite in the repository:

      a FAILED link      note was hardcoded "ok", so a store whose every link
                         failed returned (0, 0, "ok") — quieter than a store
                         that worked, because n and sk were both zero.
      an UNREADABLE dir  os.walk's default onerror is None, which discards the
                         exception and walks on. One chmod 700 project folder
                         and the subtree is never read, never linked, and the
                         walk finishes reporting "ok".

    Both are reachable: protected_hardlinks=1 makes any file not owned by this
    user fail permanently, an ext4 error-remount-ro routes every link into the
    first, and the second needs one directory you cannot read.
    """
    import os
    import pathlib
    import shutil
    import tempfile

    d = pathlib.Path(tempfile.mkdtemp(prefix="linktree-"))
    try:
        (d / "src" / "good").mkdir(parents=True)
        (d / "src" / "good" / "a.txt").write_text("a", encoding="utf-8")
        (d / "src" / "locked").mkdir()
        (d / "src" / "locked" / "b.txt").write_text("b", encoding="utf-8")
        src, dst = str(d / "src"), str(d / "dst")

        RG.FAILED_LINKS.clear()
        healthy = RG.link_tree(src, dst, True)
        check("a healthy tree reports ok", healthy[2], "ok")
        check("and links every file it found", healthy[0], 2,
              "2 files in 2 directories")

        # 1. every link fails.
        shutil.rmtree(dst, ignore_errors=True)
        RG.FAILED_LINKS.clear()
        real_link = os.link
        os.link = lambda *a, **k: (_ for _ in ()).throw(
            OSError(1, "Operation not permitted"))
        try:
            failed = RG.link_tree(src, dst, True)
        finally:
            os.link = real_link
        check("a store whose links all FAILED does not report ok",
              failed[2] != "ok", True,
              f"got {failed!r} — identical to a store that had nothing to do")
        check("and the failure reaches FAILED_LINKS, which tick() reads",
              bool(RG.FAILED_LINKS), True,
              "the daemon reports 'ok' for the whole job otherwise")

        # 2. a subtree that cannot be read.
        # Skip this test when running as root, because root bypasses permission
        # checks and the test would always fail regardless of link_tree's logic.
        if os.geteuid() == 0:
            skip("an UNREADABLE subtree is not reported as ok",
                 "running as root — chmod 000 does not prevent directory access")
        else:
            shutil.rmtree(dst, ignore_errors=True)
            RG.FAILED_LINKS.clear()
            os.chmod(d / "src" / "locked", 0o000)
            try:
                blind = RG.link_tree(src, dst, True)
            finally:
                os.chmod(d / "src" / "locked", 0o755)
            check("an UNREADABLE subtree is not reported as ok",
                  blind[2] != "ok", True,
                  f"got {blind!r} — a half-read tree and a fully-read one were "
                  f"the same tuple")
            check("and it says how many it could not read",
                  "UNREADABLE" in blind[2], True)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def a_the_windows_side_is_never_written():
    """--apply must not edit a Windows settings.json through the WSL mount.

    The guard reports Windows-side profiles on purpose — the other half of the
    machine has its own install, its own cleanupPeriodDays and its own
    transcripts, and the whole value of that report is saying so. Writing to
    them is the part that must not happen: /mnt/c is writable from WSL, this
    runs unattended every six hours, and a Windows config silently rewritten
    through a Linux mount is exactly the surprise the docstring promises not to
    spring.

    Two vectors, and the symlink is the one that hides: the path the caller
    holds says nothing about where the bytes are.

    And a THIRD assertion that matters as much: a genuine Linux profile must
    still be raised. A refusal that refuses everything protects nothing.
    """
    import os
    import pathlib
    import shutil
    import tempfile

    root = pathlib.Path(tempfile.mkdtemp(prefix="winside-"))
    try:
        mounts = (str(root / "mnt"),)
        win = root / "mnt" / "c" / "Users" / "bob" / ".claude"
        (win / "projects").mkdir(parents=True)
        (win / "settings.json").write_text('{"cleanupPeriodDays": 30}\n',
                                           encoding="utf-8")
        home = root / "home"
        home.mkdir()
        os.symlink(win, home / ".claude-win")
        lin = home / ".claude"
        (lin / "projects").mkdir(parents=True)
        (lin / "settings.json").write_text('{"cleanupPeriodDays": 30}\n',
                                           encoding="utf-8")

        sym = RG.raise_period(str(home / ".claude-win"), True, mounts)
        direct = RG.raise_period(str(win), True, mounts)
        native = RG.raise_period(str(lin), True, mounts)

        check("a symlink into the Windows mount is refused", sym[0], False,
              "realpath is the only thing that can see through it")
        check("the mount path itself is refused", direct[0], False)
        check("and the Windows settings.json is byte-for-byte unchanged",
              (win / "settings.json").read_text(encoding="utf-8").strip(),
              '{"cleanupPeriodDays": 30}')
        check("a genuine Linux profile IS still raised", native[0], True,
              "a refusal that refuses everything protects nothing")

        # And the drive-letter test must not swallow an ordinary mount.
        check("/mnt/c is Windows-side", RG.is_windows_side("/mnt/c/Users/b"), True)
        check("/mnt/data is NOT", RG.is_windows_side("/mnt/data/x"), False,
              "a data disk mounted under /mnt is not a Windows install")
        check("an ordinary home is NOT",
              RG.is_windows_side(str(pathlib.Path.home() / ".claude")), False)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def a_credentials_are_never_linked():
    """A root_files store takes RECORDS. It took everything, credentials included.

    Measured on the live machine before the fix: 48 loose root files across 10
    root_files stores, 8 records and 40 config, and 39 of that config already
    hard-linked into ~/.ai-logs-archive at the SAME INODE as the live original:

        other/gemini-root/oauth_creds.json   ino=42500290 nlink=3
                                             (access_token, refresh_token, id_token)
        other/devvit/token                   ino=42205535 nlink=2

    export_corpus had carried the test that tells a record from config since the
    first full export, and its comment names those two files as the reason — in
    the past tense. It was never applied to the archiver.

    The last assertion is the one that stops the fix going too far: a store whose
    path names ONE FILE names it because that file IS the record. ~/.claude.json
    is the only surviving evidence of 4,062,282,405 tokens whose transcripts are
    gone, and it fails every test built for "which of these loose files is
    history".

    AND EVERY CALL HERE PASSED top_only=True, WHICH IS THE 10 STORES OF 49
    THAT WERE ALREADY SAFE. run() passes top_only only for ROOT_FILE_SOURCES;
    the 39 OTHER_SOURCES conversation stores are walked RECURSIVELY, and the
    refusal was gated on `top_only and only is None`, so none of them had any
    config test at all. This function asserted an invariant the code did not
    establish, and passed on every run while a conversation store holding
    proj/oauth_creds.json linked it at the live inode. The recursive case below
    is the one that had to exist.
    """
    import pathlib
    import shutil
    import tempfile

    d = pathlib.Path(tempfile.mkdtemp(prefix="creds-"))
    try:
        store = d / "store"
        store.mkdir()
        records = ["history.jsonl", "input_history.txt"]
        # SECRET AND CONFIG ARE TWO LISTS, AND THE ARCHIVER REFUSES ONE OF THEM.
        #
        # They were one list, and that is the defect this fixture used to pin
        # in place. The archiver imported the EXPORTER's rule, NEVER_EXPORT,
        # which matches `state` — and Copilot Chat names its editing-session
        # record `state.json`, so 196 files / 494,067,931 bytes stopped being
        # archived, one of them holding linearHistory with 369 entries.
        #
        # The exporter is right to refuse both: it SHIPS bytes into a corpus,
        # so anything it cannot vouch for stays out, and _is_config still
        # guards both of its call sites. The archiver ships nothing and deletes
        # nothing, so a refusal here is only ever a record that never got a
        # second name. Same question, two callers, two correct answers.
        secrets = ["oauth_creds.json", "token", "session-id", "installation_id"]
        config = ["settings.json", "config.json"]
        for f in records + secrets + config:
            (store / f).write_text("x", encoding="utf-8")

        RG.FAILED_LINKS.clear()
        RG.REFUSED_CONFIG.clear()
        RG.UNRECOGNISED.clear()
        n, _sk, note = RG.link_tree(str(store), str(d / "arch"), True, top_only=True)

        got = sorted(p.name for p in (d / "arch").iterdir())
        check("every record and no secret is linked", got,
              sorted(records + config),
              "a root_files store takes history, and leaves the credentials")
        check("the OAuth credential is not in the archive at all",
              (d / "arch" / "oauth_creds.json").exists(), False)
        check("and the live credential still has exactly one name",
              (store / "oauth_creds.json").stat().st_nlink, 1,
              "nlink 2 is the archive holding the same inode as the original")
        check("the store still reports ok — refusing a secret is not a failure",
              (n, note), (4, "ok"))
        check("and every refusal is named, not silently dropped",
              sorted(f for _l, f, _p in RG.REFUSED_CONFIG), sorted(secrets))

        # AND THE TWO CALLERS DISAGREE, ON PURPOSE. This is the assertion the
        # old fixture was missing, and its absence is what let the archiver
        # inherit a rule built for shipping.
        import export_corpus as EC
        for f in config:
            check(f"the archiver keeps {f}", RG._refuse(f, False), False)
            check(f"and the exporter still refuses it", EC._is_config(pathlib.Path(f)),
                  True, "config must never reach the corpus, only the archive")
        for f in secrets:
            check(f"both refuse {f}",
                  (RG._refuse(f, False), bool(EC._is_config(pathlib.Path(f)))),
                  (True, True))

        # AND THE OPPOSITE MISTAKE. A store whose path IS a file.
        lone = d / "lone"
        lone.mkdir()
        (lone / ".claude.json").write_text("4,062,282,405 tokens", encoding="utf-8")
        RG.REFUSED_CONFIG.clear()
        n2, _s2, note2 = RG.link_tree(str(lone / ".claude.json"),
                                      str(d / "arch2"), True)
        check("a store that NAMES one file still archives it", (n2, note2),
              (1, "ok"),
              ".claude.json is config by name and the last copy of 4.06 B tokens")
        check("and nothing was refused on its way through", RG.REFUSED_CONFIG, [])

        # ------------------------------------------------------------------
        # THE 39 STORES THIS FUNCTION NEVER TOUCHED. top_only=False, exactly
        # how run() calls link_tree for every entry in OTHER_SOURCES.
        #
        # Against the shipped file, verbatim:
        #     link_tree(src, 'other/probe', apply=True) -> (4, 0, 'ok')
        #     other/probe/proj/oauth_creds.json     nlink(live)=2
        #     other/probe/proj/.credentials.json    nlink(live)=2
        #     other/probe/proj/mcp-secrets/gh.json  nlink(live)=2
        #     REFUSED_CONFIG == []
        conv = d / "conv"
        proj = conv / "proj"
        proj.mkdir(parents=True)
        (proj / "session.jsonl").write_text('{"role":"user"}\n', encoding="utf-8")
        (proj / "oauth_creds.json").write_text("ya29.SECRET", encoding="utf-8")
        # The dotted spelling. NEVER_EXPORT is anchored with ^ and lists
        # `credentials?`, so `credentials.json` is refused and this one is not —
        # and this is the name Claude Code actually uses. Four live copies on
        # this machine, one per profile, each holding an OAuth token.
        (proj / ".credentials.json").write_text("sk-SECRET", encoding="utf-8")
        secrets = proj / "mcp-secrets"          # SECRET_DIRS, at depth 2
        secrets.mkdir()
        (secrets / "gh.json").write_text("ghp_SECRET", encoding="utf-8")

        RG.FAILED_LINKS.clear()
        RG.REFUSED_CONFIG.clear()
        RG.UNRECOGNISED.clear()
        n3, _s3, note3 = RG.link_tree(str(conv), str(d / "arch3"), True)

        arch3 = d / "arch3"
        got3 = sorted(str(p.relative_to(arch3)) for p in arch3.rglob("*")
                      if p.is_file())
        check("a CONVERSATION store archives the record and nothing else",
              got3, ["proj/session.jsonl"],
              "top_only=False is how 39 of the 49 stores are walked")
        check("nested oauth_creds.json is refused at depth",
              (arch3 / "proj" / "oauth_creds.json").exists(), False)
        check("nested .credentials.json is refused too — the dot is not a "
              "different file",
              (arch3 / "proj" / ".credentials.json").exists(), False)
        check("a file inside a SECRET_DIRS directory is refused",
              (arch3 / "proj" / "mcp-secrets" / "gh.json").exists(), False)
        check("and none of the three live credentials gained a second name",
              [(proj / "oauth_creds.json").stat().st_nlink,
               (proj / ".credentials.json").stat().st_nlink,
               (secrets / "gh.json").stat().st_nlink],
              [1, 1, 1],
              "nlink 2 is the archive holding the same inode as the original")
        check("the record still got through", (n3, note3), (1, "ok"))
        check("and every nested refusal is named with its path",
              sorted(f for _l, f, _p in RG.REFUSED_CONFIG),
              [os.path.join("proj", ".credentials.json"),
               os.path.join("proj", "mcp-secrets", "gh.json"),
               os.path.join("proj", "oauth_creds.json")])
        check("a recursive store has no UNRECOGNISED bucket — that is a "
              "root-file idea", RG.UNRECOGNISED, [])

        # AND THE SAME DIRECTORY UNDER EVERY SPELLING IT CAN HAVE ON DISK.
        #
        # `set(rel.split(os.sep)) & SECRET_DIRS` was an exact, case-sensitive,
        # dot-sensitive intersection against a lowercase literal set, so of
        #
        #     mcp-secrets/gh.json   refused
        #     MCP-Secrets/gh.json   ARCHIVED
        #     Credentials/gh.json   ARCHIVED
        #     .credentials/gh.json  ARCHIVED
        #
        # exactly one spelling was caught, and the test that claimed to cover
        # this used that one spelling. Two of the five machines run
        # case-insensitive filesystems (APFS, NTFS), where those are not four
        # directories at all — they are ONE directory whose stored spelling
        # happens to differ, so the rule matched a name the tool never wrote.
        #
        # Both blocks below (spellings and trailing) create directories whose
        # names differ only in case — separate dirs on Linux, the SAME dir on
        # APFS and NTFS. The test cannot create them on a case-insensitive FS,
        # so we detect and skip.
        _probe = d / "_case_probe"
        _probe.mkdir()
        (_probe / "ProBeFile").write_text("x", encoding="utf-8")
        _case_insensitive = (_probe / "probefile").exists()
        (_probe / "ProBeFile").unlink()
        _probe.rmdir()

        if _case_insensitive:
            skip("no spelling of a secret directory reaches the archive",
                 "case-insensitive filesystem (APFS/NTFS) — spellings that are "
                 "distinct directories on Linux are the same directory here; the "
                 "case-fold rule is tested on this platform by the "
                 "t_platform_expansion tests in test_fleet.py instead")
            skip("no trailing-dot or trailing-space spelling reaches the archive",
                 "same case-insensitive FS — trailing-modified spellings collide "
                 "with their base names at mkdir time on APFS/NTFS")
        else:
            conv2 = d / "conv2"
            proj2 = conv2 / "proj"
            proj2.mkdir(parents=True)
            (proj2 / "session.jsonl").write_text('{"m":1}\n', encoding="utf-8")
            spellings = ["mcp-secrets", "MCP-Secrets", "Mcp-Secrets",
                         "credentials", "Credentials", "CREDENTIALS",
                         ".credentials", ".ssh", "SSH", "Auth", "Keys", "CERTS"]
            for name in spellings:
                sd = proj2 / name
                sd.mkdir()
                (sd / "gh.json").write_text("ghp_SECRET", encoding="utf-8")

            RG.FAILED_LINKS.clear()
            RG.REFUSED_CONFIG.clear()
            RG.UNRECOGNISED.clear()
            n4, _s4, note4 = RG.link_tree(str(conv2), str(d / "arch4"), True)

            arch4 = d / "arch4"
            got4 = sorted(str(p.relative_to(arch4)) for p in arch4.rglob("*")
                          if p.is_file())
            check("no spelling of a secret directory reaches the archive",
                  got4, ["proj/session.jsonl"],
                  "one of these spellings used to be refused and eleven were not")
            check("and not one of the twelve live credentials gained a second name",
                  sorted({(proj2 / s / "gh.json").stat().st_nlink
                          for s in spellings}), [1])
            check("the record still got through, all twelve times",
                  (n4, note4), (1, "ok"))
            check("and every spelling is named in the refusal list",
                  sorted(f for _l, f, _p in RG.REFUSED_CONFIG),
                  sorted(os.path.join("proj", s, "gh.json") for s in spellings))

            # AND THE SPELLING PAST THE END OF THE NAME.
            #
            # The fold above was `name.lower().lstrip(".")` — case and a LEADING
            # dot. The TRAILING end was untouched, and measured against that file:
            #
            #     secret_dir('mcp-secrets')  True   secret_dir('mcp-secrets.') False
            #                                       secret_dir('mcp-secrets ') False
            #                                       secret_dir('credentials.')  False
            #                                       secret_dir('credentials ')  False
            #
            # Win32 strips trailing dots and spaces from every path component, so on
            # the two non-Linux machines `mcp-secrets.` is not a lookalike of
            # `mcp-secrets` — it IS `mcp-secrets`, reached under a spelling the rule
            # did not match. On Linux they are separate directories and nothing
            # stops a tool from writing one.
            #
            # The archiver's cost here is not the corpus, it is that these bytes get
            # a SECOND NAME under ~/.ai-logs-archive: an OAuth token hard-linked
            # into the tree the exporter later walks.
            conv3 = d / "conv3"
            proj3 = conv3 / "proj"
            proj3.mkdir(parents=True)
            (proj3 / "session.jsonl").write_text('{"m":1}\n', encoding="utf-8")
            # sorted(set(...)) because `.ssh` is the one SECRET_DIRS entry that
            # already carries its dot, so `base + " "` and `"." + base.lstrip(".")
            # + " "` are the same string for it — and two mkdir calls on one name
            # is a fixture bug, not a finding.
            trailing = sorted({s for base in EC.SECRET_DIRS
                               for s in (base + ".", base + " ", base + ". . ",
                                         base.upper() + ".",
                                         "." + base.lstrip(".") + " ")})
            for name in trailing:
                sd = proj3 / name
                sd.mkdir()
                (sd / "gh.json").write_text("ghp_SECRET", encoding="utf-8")
            # The other direction, and it is the one that costs records: this
            # function is the ARCHIVER's refusal too, so a fold that reached into or
            # past the middle of a name would silently stop preserving these.
            innocent = ["authors", "auth-backup", "keys-backup", "certsigner",
                        "sshd", "my.credentials.old", "credentials-export"]
            for name in innocent:
                sd = proj3 / name
                sd.mkdir()
                (sd / "chat.jsonl").write_text('{"m":2}\n', encoding="utf-8")

            RG.FAILED_LINKS.clear()
            RG.REFUSED_CONFIG.clear()
            RG.UNRECOGNISED.clear()
            n5, _s5, note5 = RG.link_tree(str(conv3), str(d / "arch5"), True)

            arch5 = d / "arch5"
            got5 = sorted(str(p.relative_to(arch5)) for p in arch5.rglob("*")
                          if p.is_file())
            check("no trailing-dot or trailing-space spelling reaches the archive",
                  [g for g in got5 if g.endswith("gh.json")], [],
                  "trailing dots and spaces are stripped by Windows, so each of "
                  "these IS the secret directory the rule already guards")
            check("and not one of those credentials gained a second name",
                  sorted({(proj3 / s / "gh.json").stat().st_nlink
                          for s in trailing}), [1],
                  "nlink 2 is the archive holding the same inode as the original")
            check("while every innocent lookalike directory was still archived",
                  sorted(g for g in got5 if g.endswith("chat.jsonl")),
                  sorted(os.path.join("proj", s, "chat.jsonl") for s in innocent),
                  "the archiver ships nothing and deletes nothing, so a wrongful "
                  "refusal here is a record that never gets a second name")
            check("the record beside them still got through",
                  (n5, note5), (1 + len(innocent), "ok"))
            check("and every trailing spelling is named in the refusal list",
                  sorted(f for _l, f, _p in RG.REFUSED_CONFIG),
                  sorted(os.path.join("proj", s, "gh.json") for s in trailing))
    finally:
        shutil.rmtree(d, ignore_errors=True)


def a_a_real_record_is_never_dropped_for_its_name():
    """The whitelist refused 1.8 MB of sessions and admitted a 0-byte WAL.

    `_is_loose_record` is a filename WHITELIST — history, conversation, chat,
    thread, message, transcript, prompt, or a .jsonl suffix. Round one used it
    as the archiver's admission gate, and on this machine that means:

        ~/.copilot/session-store.db              1,822,720 B   REFUSED
                                                 38 sessions, 370 turns,
                                                 already archived at nlink=3
        ~/.gemini/antigravity-cli/
              conversation_summaries.db-shm         32,768 B   ADMITTED
              conversation_summaries.db-wal              0 B   ADMITTED

    The two that got in carry no record at all; they are sqlite's scratch files.
    They got in because their SIBLING is named for a conversation.

    The exporter is right to whitelist — it ships bytes into a public corpus.
    The archiver ships nothing: a hard link is 0 bytes and nothing in
    retention_guard deletes. Keeping a non-record costs nothing; dropping a
    record costs the only copy. So the refusal is the config/secret test, and
    the whitelist only decides what gets NAMED.

    And the two refusals must not share a printed line. One line reading
    "config/credential file(s) refused" over a list whose bulk is ADVISOR.md,
    cli.log and GEMINI.md is how the two entries that ARE credentials get read
    past.
    """
    import pathlib
    import shutil
    import tempfile

    d = pathlib.Path(tempfile.mkdtemp(prefix="record-"))
    try:
        store = d / "copilot"
        store.mkdir()
        record = "session-store.db"              # the real one, 38 sessions
        sidecars = ["session-store.db-shm", "session-store.db-wal"]
        known = ["command-history-state.json"]   # matches the whitelist
        # Split for the same reason as above: the archiver refuses secrets, and
        # keeps config, because a refusal here costs a record and buys nothing.
        secrets = ["oauth_creds.json"]
        config = ["config.json", "settings.json", "permissions-config.json"]
        for f in [record] + sidecars + known + secrets + config:
            (store / f).write_text("x", encoding="utf-8")

        RG.FAILED_LINKS.clear()
        RG.REFUSED_CONFIG.clear()
        RG.UNRECOGNISED.clear()
        n, _sk, note = RG.link_tree(str(store), str(d / "arch"), True,
                                    top_only=True)

        arch = d / "arch"
        check("the 1.8 MB record with 38 sessions IS archived",
              (arch / record).exists(), True,
              "a name no rule recognises is not a reason to lose a record")
        check("the credential is still refused", (arch / "oauth_creds.json").exists(),
              False, "widening must not reopen the hole it was widened around")
        check("and the live credential still has exactly one name",
              (store / "oauth_creds.json").stat().st_nlink, 1)
        check("every non-secret file got through", (n, note), (7, "ok"))

        refused = sorted(f for _l, f, _p in RG.REFUSED_CONFIG)
        unknown = sorted(f for _l, f in RG.UNRECOGNISED)
        check("REFUSED_CONFIG holds secrets and ONLY secrets", refused,
              sorted(secrets),
              "config is kept: the archiver ships nothing, so refusing it "
              "only ever costs a record")
        check("the unrecognised names are a SEPARATE bucket", unknown,
              sorted([record] + sidecars + config),
              "refused-because-credential must not share a line with "
              "refused-because-I-did-not-recognise-the-name. config is now in "
              "the second bucket: ARCHIVED, and reported as a name nobody "
              "recognised — which is the honest thing to say about it")
        check("and no name is in both", set(refused) & set(unknown), set())

        # And the print itself, because a split that only exists in memory is
        # not a split. run() is what an operator reads.
        RG.FAILED_LINKS.clear()
        home = d / "home"
        (home / ".copilot").mkdir(parents=True)
        for f in [record, "oauth_creds.json"]:
            (home / ".copilot" / f).write_text("x", encoding="utf-8")
        os.environ["RETENTION_GUARD_LEDGER"] = "0"
        try:
            with patched(HOME=str(home), ARCHIVE=str(d / "arch5"),
                         OTHER_SOURCES={},
                         ROOT_FILE_SOURCES={"copilot-root": [".copilot"]},
                         claude_profiles=lambda: [],
                         windows_side_profiles=lambda: []):
                _rc, log = quiet(lambda: RG.run(apply=True))
        finally:
            os.environ.pop("RETENTION_GUARD_LEDGER", None)
        cred_line = [ln for ln in log.splitlines() if "REFUSED" in ln]
        arch_line = [ln for ln in log.splitlines() if "ARCHIVED whose name" in ln]
        check("run() prints the credential refusal on its own line",
              len(cred_line), 1, f"got {cred_line!r}")
        check("and the unrecognised names on a different one",
              len(arch_line), 1, f"got {arch_line!r}")
        check("the credential line does not claim the record",
              "1 config/credential" in cred_line[0] if cred_line else False, True,
              f"got {cred_line!r} — session-store.db is not a credential")
        check("and the credential is NAMED, not just counted",
              "oauth_creds.json" in log, True,
              "200 of these were being linked and not one was printed")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def a_a_store_that_vanished_is_not_a_store_that_never_existed():
    """(0, 0, 'absent') meant both, so the run it broke looked like every other.

    link_tree returned "absent" for a directory that is not there, and run()
    suppresses "absent" entirely. So a tool that was never installed and a store
    the belt used to catch and can no longer reach printed the same thing:
    nothing. The archive is the only witness that can tell them apart, and it is
    a reliable one, because nothing in retention_guard ever deletes.

    Deliberately NOT a FAILED_LINK. Uninstalling a tool is allowed, and this
    file already knows what a permanently-wrong alarm costs: "an alarm that is
    wrong every time is one people stop reading, which costs the real one its
    meaning."
    """
    import pathlib
    import shutil
    import tempfile

    d = pathlib.Path(tempfile.mkdtemp(prefix="vanish-"))
    try:
        with patched(ARCHIVE=str(d / "arch")):
            store = d / "store"
            store.mkdir()
            (store / "history.jsonl").write_text("r\n", encoding="utf-8")
            RG.FAILED_LINKS.clear()
            RG.VANISHED.clear()
            first = RG.link_tree(str(store), "other/vanishing", True)
            check("the belt caught it once", first, (1, 0, "ok"))

            shutil.rmtree(store)               # the tool is uninstalled
            RG.FAILED_LINKS.clear()
            RG.VANISHED.clear()
            gone = RG.link_tree(str(store), "other/vanishing", True)
            never = RG.link_tree(str(d / "nothing-here"), "other/never", True)

            check("a store that vanished does not say 'absent'",
                  gone[2].startswith("SOURCE GONE"), True, f"got {gone[2]!r}")
            check("a store nobody ever installed still says 'absent'", never,
                  (0, 0, "absent"))
            check("the two are distinguishable", gone[2] != never[2], True,
                  "a belt that stopped catching a store read identically to "
                  "one that never had it")
            check("the vanished store is named", [l for l, _p, _h in RG.VANISHED],
                  ["other/vanishing"])
            check("it counts what the archive still holds",
                  [h for _l, _p, h in RG.VANISHED], [1])
            check("and it is NOT counted as a link failure", RG.FAILED_LINKS, [],
                  "uninstalling a tool is allowed; an alarm that is always "
                  "wrong is one people stop reading")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def a_already_archived_is_identity_not_a_path():
    """A destination that exists is not proof the LIVE file is archived.

    `if os.path.exists(d): skipped += 1` compares NAMES. Every atomic rename
    gives the file a new inode under the same name, which is how ~/.claude.json
    is written — so the orphan sits in the archive, the live file is linked
    nowhere, and the guard reports it protected on every run from then on.

    Six of them on this machine the day this was written, 15,203 destinations
    already present:

        ~/.claude.json   live ino=42210401 nlink=1   archive ino=42216256
        ~/.claude-alt/projects/-home-phantomcore/memory/MEMORY.md
        ~/.gemini/antigravity-cli/conversation_summaries.db-wal   ... and 3 more

    nlink=1 is the whole finding: the live file has one name, and it is not in
    the archive. This rewrites the file exactly the way Claude Code does.
    """
    import os
    import pathlib
    import shutil
    import tempfile

    d = pathlib.Path(tempfile.mkdtemp(prefix="ghost-"))
    try:
        src, dst = d / "src", d / "dst"
        src.mkdir()
        (src / "claude.json").write_text("v1", encoding="utf-8")
        RG.FAILED_LINKS.clear()
        RG.GHOSTS.clear()
        RG.link_tree(str(src), str(dst), True)

        tmp = src / "claude.json.tmp"
        tmp.write_text("v2", encoding="utf-8")
        os.replace(tmp, src / "claude.json")        # new inode, same path
        RG.GHOSTS.clear()
        n, sk, note = RG.link_tree(str(src), str(dst), True)

        check("the rewritten file is archived, not called 'already there'",
              (src / "claude.json").stat().st_nlink, 2,
              "nlink 1 means the live file is archived nowhere and the guard "
              "said it was protected")
        check("it counts as work done, not as a skip", (n, sk, note),
              (1, 0, "ok"))
        check("and the ghost is named", len(RG.GHOSTS), 1)
        check("the older inode is KEPT — nothing is replaced",
              sorted((p.name, p.read_text(encoding="utf-8"))
                     for p in dst.iterdir()),
              [("claude.ino%d.json" % (src / "claude.json").stat().st_ino, "v2"),
               ("claude.json", "v1")])

        # AND IT MUST SETTLE. A re-link that runs again every tick would grow the
        # archive by one name every six hours forever.
        RG.GHOSTS.clear()
        again = RG.link_tree(str(src), str(dst), True)
        check("running it again links nothing new", again, (0, 1, "ok"))
        check("and finds no ghost the second time", RG.GHOSTS, [])

        # A HARD LINK COPIES THE ENTRY, NOT THE TARGET. ~/.claude-alt/debug/latest
        # is a symlink that has dangled since February, nlink=3. Comparing
        # identity with stat() follows it, both sides raise, the archived copy
        # reads as a different file, and the re-link hits EEXIST — a FAILED link
        # on every tick, forever.
        (src / "target.txt").write_text("t", encoding="utf-8")
        os.symlink(str(src / "target.txt"), str(src / "latest"))
        RG.link_tree(str(src), str(dst), True)
        os.replace(src / "target.txt", src / "gone.txt")     # now dangling
        RG.FAILED_LINKS.clear()
        dead = RG.link_tree(str(src), str(dst), True)
        check("a dangling symlink already archived is not re-linked forever",
              dead[2], "ok",
              "stat() follows the link, lstat() compares the entry that was "
              "actually hard-linked")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def a_a_dead_belt_cannot_report_ok():
    """0 of 4 files archived, and the daemon logged retention: ok.

    The DIFFERENT FILESYSTEM branch returned before FAILED_LINKS was touched, so
    the one condition that makes hard links impossible was the one condition
    nothing counted. Reproduced with a tmpfs source (/dev/shm, dev=29) and an
    ext4 archive (dev=66306):

        link_tree    -> (0, 0, 'DIFFERENT FILESYSTEM — hard links impossible here')
        FAILED_LINKS -> []
        run()        -> exit 0
        tick()       -> {'retention': 'ok'}

    And --check could not see it either, for a deeper reason: it counts what it
    WOULD do and never calls os.link, so no link failure of any kind was
    reachable from the mode documented as "report exposure".

    A REAL mount boundary when there is one to use. /dev/shm is tmpfs on every
    Linux, and a fabricated same_filesystem() would be testing the mock.
    """
    import os
    import pathlib
    import shutil
    import tempfile

    shm = "/dev/shm"
    try:
        cross = (os.path.isdir(shm) and os.access(shm, os.W_OK)
                 and os.stat(shm).st_dev != os.stat(tempfile.gettempdir()).st_dev)
    except OSError:
        cross = False
    if not cross:
        skip("a dead belt cannot report ok",
             "no second filesystem reachable without root — /dev/shm is either "
             "absent or the same device as the temp dir")
        return

    home = pathlib.Path(tempfile.mkdtemp(prefix="xdev-home-", dir=shm))
    arch = pathlib.Path(tempfile.mkdtemp(prefix="xdev-arch-"))
    try:
        store = home / ".proteus"
        store.mkdir()
        for i in range(4):
            (store / f"history{i}.jsonl").write_text(f"r{i}\n", encoding="utf-8")

        RG.FAILED_LINKS.clear()
        applied = RG.link_tree(str(store), "other/proteus-root", True,
                               top_only=True)
        applied_failed = list(RG.FAILED_LINKS)
        RG.FAILED_LINKS.clear()
        checked = RG.link_tree(str(store), "other/proteus-root", False,
                               top_only=True)
        check_failed = list(RG.FAILED_LINKS)

        check("--apply says the store was NOT archived", applied[2] != "ok", True,
              f"got {applied!r}")
        check("and it reaches FAILED_LINKS, which tick() reads",
              bool(applied_failed), True,
              "returning early meant a whole filesystem away was not a failure")
        check("--check sees it too — it is the mode that reports exposure",
              bool(check_failed) and checked[2] != "ok", True,
              f"got {checked!r}, FAILED_LINKS={check_failed!r}")

        os.environ["RETENTION_GUARD_LEDGER"] = "0"
        try:
            with patched(HOME=str(home), ARCHIVE=str(arch), OTHER_SOURCES={},
                         ROOT_FILE_SOURCES={"proteus-root": [".proteus"]},
                         claude_profiles=lambda: [],
                         windows_side_profiles=lambda: []):
                rc, _ = quiet(lambda: RG.run(apply=True))
                res, _ = quiet(lambda: RG.tick(apply=True))
        finally:
            os.environ.pop("RETENTION_GUARD_LEDGER", None)

        n_arch = sum(len(f) for _r, _d, f in os.walk(arch))
        check("nothing was archived", n_arch, 0,
              "if this is 4 the fixture is not crossing a mount boundary")
        check("run() exits non-zero when the belt archived nothing", rc, 1)
        check("and the daemon does NOT log retention: ok",
              res["retention"].startswith("INCOMPLETE"), True,
              f"got {res.get('retention')!r} for a tick that archived 0 of 4")
    finally:
        shutil.rmtree(home, ignore_errors=True)
        shutil.rmtree(arch, ignore_errors=True)


def a_the_archiver_reads_records():
    """The archiver never read `records` at all, so a credential was a CANDIDATE.

        grep -c "is_record\\|\\.records" retention_guard.py   ->   0

    ROOT_FILE_SOURCES carried paths and nothing else, and link_tree filtered
    with `_refuse` alone. That is a deny-list: every loose file beside a tool's
    program directories was admitted unless its NAME was recognised as a
    credential — which is how ~/.gemini/oauth_creds.json and ~/.devvit/token
    came to be in the archive at the same inode as the live original, from
    before `_refuse` existed. A rule that says what a store's records ARE
    cannot be surprised by a credential nobody has heard of yet.

    FOUR THINGS ARE UNDER ATTACK HERE, AND THE LAST TWO ARE THE DANGEROUS ONES:

      1. that the allow-list narrows at all, and `()` narrows to nothing
      2. that `_refuse` still runs FIRST, so a credential is still NAMED — put
         the allow-list first and REFUSED_CONFIG goes empty, and the run where
         a new credential appears in a tool's root reads exactly like the run
         before it
      3. that a store whose path names ONE FILE is never filtered — that is
         ~/.ollama/history and ~/.claude.json, the last surviving evidence of
         4,062,282,405 tokens, and neither is a "record name"
      4. that this is applied to ROOT_FILES STORES ONLY. A root_files store's
         records are a short list of names at depth 0 and everything else there
         is configuration, so an allow-list is the whole truth about it. A
         conversation store is the opposite: copilot-chat's root is 4.5 GB of
         other extensions' state, its tuple names the two shapes anyone has
         thought to write down, and the archiver ships nothing — so the cost of
         wiring the tuple into OTHER_SOURCES is every record shape NOBODY HAS
         NOTICED YET, dropped silently, forever. That is not hypothetical: the
         tuple said `*/chatSessions/*.json` and nothing else for as long as it
         existed, while 196 files / 494,067,931 B of
         `*/chatEditingSessions/*/state.json` — one holding linearHistory with
         369 entries — sat beside it unnamed. The tuple has since been widened
         to name them; the NEXT one has not been discovered yet, and the
         archiver keeps it either way only because no allow-list runs here.
    """
    import pathlib
    import shutil
    import tempfile

    d = pathlib.Path(tempfile.mkdtemp(prefix="records-"))
    try:
        store = d / "store"
        store.mkdir()
        named = ["history.jsonl", "session-store.db"]
        # Not in the tuple. `cli.log` and `settings.json` are the shapes this
        # narrows away; `oauth_creds.json` is the one it exists for.
        others = ["cli.log", "settings.json"]
        secret = "oauth_creds.json"
        for f in named + others + [secret]:
            (store / f).write_text("x", encoding="utf-8")

        RG.FAILED_LINKS.clear()
        RG.REFUSED_CONFIG.clear()
        RG.UNRECOGNISED.clear()
        RG.NOT_A_RECORD.clear()
        n, _sk, note = RG.link_tree(str(store), str(d / "arch"), True,
                                    top_only=True, records=tuple(named))

        got = sorted(p.name for p in (d / "arch").iterdir())
        check("only the files the store names are archived", got, sorted(named),
              "records= was decorative: the archiver read the map for paths "
              "and for nothing else")
        check("a name the whitelist does not know is still archived when the "
              "store names it", (d / "arch" / "session-store.db").exists(), True,
              "1,822,720 B, 38 sessions, 370 turns — the allow-list must not "
              "become the same whitelist the exporter uses")
        check("the credential gained no second name",
              (store / secret).stat().st_nlink, 1)
        check("and _refuse still ran FIRST, so it is NAMED as a credential",
              sorted(f for _l, f, _p in RG.REFUSED_CONFIG), [secret],
              "narrow-then-refuse drops it anonymously and REFUSED_CONFIG "
              "goes empty — the run a new credential appears reads like every "
              "run before it")
        check("what the allow-list dropped is a SEPARATE, named bucket",
              sorted(f for _l, f in RG.NOT_A_RECORD), sorted(others),
              "this is the only narrowing in a program whose doctrine is that "
              "a link costs 0 bytes and a missed record is permanent, so it "
              "is never silent")
        check("no name is in both buckets",
              {f for _l, f, _p in RG.REFUSED_CONFIG} & {f for _l, f in RG.NOT_A_RECORD},
              set())
        check("the store still reports ok", (n, note), (2, "ok"))

        # `()` IS A SENTENCE. `if not records` made it the same as None.
        RG.NOT_A_RECORD.clear()
        RG.REFUSED_CONFIG.clear()
        n2, _s2, _nt2 = RG.link_tree(str(store), str(d / "arch-empty"), True,
                                     top_only=True, records=())
        got2 = sorted(p.name for p in (d / "arch-empty").iterdir())
        check("records=() archives nothing from that root", (n2, got2), (0, []),
              "() and None were the same sentence, so `gemini-root` saying it "
              "has no loose records was byte-for-byte the current sweep")
        check("and every dropped file is named", len(RG.NOT_A_RECORD), len(named + others))

        # None IS THE OTHER SENTENCE, AND IT MUST NOT CHANGE.
        RG.NOT_A_RECORD.clear()
        RG.REFUSED_CONFIG.clear()
        n3, _s3, _nt3 = RG.link_tree(str(store), str(d / "arch-none"), True,
                                     top_only=True, records=None)
        got3 = sorted(p.name for p in (d / "arch-none").iterdir())
        check("a store that has not said keeps everything but the credential",
              got3, sorted(named + others),
              "the default has to stay 'keep it' — a refusal here is a record "
              "that never got a second name")
        check("and nothing lands in the narrowed bucket", RG.NOT_A_RECORD, [])

        # A STORE WHOSE PATH NAMES ONE FILE. No tuple can filter it.
        lone = d / "lone"
        lone.mkdir()
        (lone / ".claude.json").write_text("4,062,282,405 tokens", encoding="utf-8")
        RG.NOT_A_RECORD.clear()
        n4, _s4, note4 = RG.link_tree(str(lone / ".claude.json"),
                                      str(d / "arch-lone"), True,
                                      records=("history.jsonl",))
        check("a store that NAMES one file is archived whatever the tuple says",
              (n4, note4), (1, "ok"),
              "~/.ollama/history and ~/.claude.json fail every test built for "
              "'which of these loose files is history'")
        check("and it is not reported as narrowed away", RG.NOT_A_RECORD, [])

        # AND THE TUPLES REACH ONLY THE ROOT_FILES STORES.
        check("no conversation store is wired to a records allow-list",
              sorted(set(RG.ROOT_FILE_RECORDS) &
                     {s.label for s in RG.stores.conversation_stores()}), [])
        check("copilot-chat above all", "copilot-chat" in RG.ROOT_FILE_RECORDS,
              False,
              "its root is 4.5 GB of other extensions' state and its tuple "
              "names only the shapes somebody has already noticed — for "
              "as long as it existed it missed 196 chatEditingSessions "
              "state.json files, 494,067,931 B")
        conv = d / "conv"
        edit = conv / "ws" / "chatEditingSessions" / "s1"
        edit.mkdir(parents=True)
        (edit / "state.json").write_text('{"linearHistory":[1]}', encoding="utf-8")
        RG.NOT_A_RECORD.clear()
        RG.REFUSED_CONFIG.clear()
        n5, _s5, _nt5 = RG.link_tree(str(conv), str(d / "arch-conv"), True)
        check("so a record the tuple has never heard of is still archived",
              n5, 1,
              "the archiver keeps what no allow-list names — which is the "
              "only reason the 494 MB of chatEditingSessions survived the "
              "whole time the tuple did not mention it")

        # AND THE SHIPPED MAP, not just the mechanism. The map is the part
        # that gets edited.
        check("the three credential-only stores are gone from the map",
              [l for l in ("devvit", "nanobot-root", "deepseek-code-root")
               if l in RG.ROOT_FILE_SOURCES], [])
        # THE TUPLES THEMSELVES, PINNED. Everything above tests the mechanism
        # with tuples this file wrote, which says nothing about the map — and
        # the map is the part that gets edited. Deleting a `records=` from
        # stores.py leaves every mechanism check green.
        check("and the shipped tuples are exactly these", RG.ROOT_FILE_RECORDS, {
            "gemini-antigravity-root": ("history.jsonl",
                                        "conversation_summaries.db"),
            "clawspring-root": ("input_history.txt",),
            "proteus-root": ("history.jsonl", "stats-cache.json"),
            # wider than the one file on this machine, because macbook-air-m1
            # exported 3 files / 21,603 B out of ~/.codex and nobody knows
            # their names
            "codex-root": ("history.jsonl", "*.jsonl", "*.ndjson"),
            # -wal is in (445 pages against a 1000-page autocheckpoint, so a
            # session can sit un-checkpointed in it); -shm is out, zero rows
            "copilot-root": ("command-history-state.json", "session-store.db",
                             "session-store.db-wal"),
            "gemini-root": (),           # no loose record ever observed
            "jules": ("history.txt",),
            # -wal is in (may hold unflushed turns); -shm is out (zero rows)
            "bob": ("bob.db", "bob.db-wal"),
        }, "a tuple deleted or narrowed here is a record that stops being "
           "archived, silently, on five machines")
        check("~/.devvit is skipped by discovery, or its removal becomes an "
              "alarm that is wrong on every run",
              ".devvit" in RG.DISCOVER_SKIP, True)
        check("and ~/.proteus/.claude.json kept a store of its own",
              RG.OTHER_SOURCES.get("proteus-claude-config"),
              [".proteus/.claude.json"],
              "proteus-root now names its records and that is not one of "
              "them, so the counter file would have stopped being archived")

        # AND THE PRINT. A bucket that only exists in memory is not a report,
        # and this is the one bucket that costs something.
        home = d / "home"
        (home / ".probe").mkdir(parents=True)
        for f in ["history.jsonl", "cli.log", "oauth_creds.json"]:
            (home / ".probe" / f).write_text("x", encoding="utf-8")
        os.environ["RETENTION_GUARD_LEDGER"] = "0"
        try:
            with patched(HOME=str(home), ARCHIVE=str(d / "arch6"),
                         OTHER_SOURCES={},
                         ROOT_FILE_SOURCES={"probe-root": [".probe"]},
                         ROOT_FILE_RECORDS={"probe-root": ("history.jsonl",)},
                         claude_profiles=lambda: [],
                         windows_side_profiles=lambda: []):
                _rc, log = quiet(lambda: RG.run(apply=True))
        finally:
            os.environ.pop("RETENTION_GUARD_LEDGER", None)
        check("run() prints what the allow-list dropped, on its own line",
              len([ln for ln in log.splitlines() if "NOT ARCHIVED" in ln]), 1,
              f"got {log!r}")
        check("and names the file", any("probe-root/cli.log" in ln
                                        for ln in log.splitlines()), True)
        check("the credential is still on the REFUSED line, not that one",
              len([ln for ln in log.splitlines() if "REFUSED" in ln]), 1)
        check("and the record was archived",
              (d / "arch6" / "other" / "probe-root" / "history.jsonl").exists(),
              True)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def a_preserve_false_is_the_exporters_flag_not_the_archivers():
    """`preserve=False` means COUNTED, NEVER SHIPPED. The archiver still links it.

    THIS SCENARIO EXISTS BECAUSE THE OPPOSITE READING IS ONE LINE AWAY AND
    LOOKS LIKE A FIX. `conversation_stores()` and `root_file_stores()` have no
    preserve filter, so ~/.claude.json — which carries oauthAccount,
    emailAddress, organizationUuid, userID and machineID — is hard-linked into
    ~/.ai-logs-archive/other/claude-config/. Reading that as a leak and adding
    `if not s.preserve: continue` to the archiver's two loops is a wrongful
    REFUSAL, and in this program a wrongful refusal is the expensive one.

    MEASURED ON THE LIVE ARCHIVE, and this is the whole argument:

        other/claude-config/.claude.json            161,216 B  nlink=1
        other/claude-config/.claude.ino42210401.json 161,203 B  nlink=1
        other/claude-config/.claude.ino42216275.json 161,235 B  nlink=2

    nlink=1 on two of three. Claude Code rewrites ~/.claude.json by atomic
    rename, so each rewrite makes a NEW inode and the previous one survives at
    exactly one name: the archive's. Those two versions of the file holding
    4,071,258,650 tokens of orphan counters exist NOWHERE ELSE ON THIS MACHINE.
    A preserve filter in the archiver would not have created them.

    THE FLAG ALREADY HAS ONE HONEST CONSUMER, and the split is deliberate:

      export_corpus._tool_roots  `skip = {s.label for s in STORES if not
                                 s.preserve}`, applied to the LIVE roots and
                                 again to the ARCHIVE directories it walks by
                                 name. That is the ship path, and it is closed
                                 at both ends.
      retention_guard            links. 0 bytes, 0 deletions, nothing leaves
                                 the machine, and the second name is the only
                                 copy the moment the first one is replaced.

    stores.py says it in the map itself — proteus-claude-config's own
    no_preserve_because is "kept because nothing counts it and the archive is
    its only copy", which a preserve filter in the archiver would make false.

    So: four things under attack, and the middle two are the ones a "fix" breaks.
    """
    import pathlib
    import shutil
    import tempfile

    import export_corpus as E

    d = pathlib.Path(tempfile.mkdtemp(prefix="preserve-"))
    probe = RG.stores.Store("probe-config", ".probe.json", cli="probe-orphans",
                            preserve=False,
                            no_preserve_because="test fixture — counted, never shipped")
    RG.stores.STORES.append(probe)
    RG.stores.BY_LABEL[probe.label] = probe
    try:
        # 1. THE SOURCE MAP. A filter inside conversation_stores() would be
        #    invisible to every check below that patches OTHER_SOURCES by hand.
        sources = {s.label: s.rel_paths() for s in RG.stores.conversation_stores()}
        check("a preserve=False store is still in the archiver's source map",
              sources.get("probe-config"), [".probe.json"],
              "conversation_stores() must not filter on preserve — the "
              "exporter shares it and so does the discovery `known` set")

        home = d / "home"
        home.mkdir()
        arch = d / "arch"
        (home / ".probe.json").write_text('{"lastTotalInputTokens": 5}',
                                          encoding="utf-8")
        live_ino_1 = (home / ".probe.json").stat().st_ino

        os.environ["RETENTION_GUARD_LEDGER"] = "0"
        try:
            with patched(HOME=str(home), ARCHIVE=str(arch),
                         OTHER_SOURCES={"probe-config": [".probe.json"]},
                         ROOT_FILE_SOURCES={}, ROOT_FILE_RECORDS={},
                         claude_profiles=lambda: [],
                         windows_side_profiles=lambda: []):
                quiet(lambda: RG.run(apply=True))

                # 2. IT IS LINKED, AT THE LIVE INODE. This is the check that
                #    fails the moment either loop learns to read `preserve`.
                arch_dir = arch / "other" / "probe-config"
                got = sorted(p.name for p in arch_dir.iterdir()) \
                    if arch_dir.is_dir() else []
                check("the archiver links it anyway — a link is 0 bytes and "
                      "ships nothing", got, [".probe.json"],
                      "an archiver that honours preserve=False drops the only "
                      "surviving copy of a counter file whose live inode is "
                      "replaced on every rewrite")
                # `.exists() else None` so a filtered archive reports every
                # check it knows about instead of raising on the first one and
                # taking the remaining four down with it.
                check("and at the SAME inode, not a copy",
                      (arch_dir / ".probe.json").stat().st_ino
                      if (arch_dir / ".probe.json").exists() else None,
                      live_ino_1)

                # 3. AND ACROSS A REWRITE, which is the case the whole archive
                #    exists for. Atomic rename => new inode => the old version
                #    lives on at exactly one name, this one.
                tmp = home / ".probe.json.tmp"
                tmp.write_text('{"lastTotalInputTokens": 9}', encoding="utf-8")
                os.replace(tmp, home / ".probe.json")
                live_ino_2 = (home / ".probe.json").stat().st_ino
                quiet(lambda: RG.run(apply=True))
                got2 = sorted(p.name for p in arch_dir.iterdir()) \
                    if arch_dir.is_dir() else []
                check("a rewritten counter file keeps BOTH versions",
                      got2, [".probe.ino%d.json" % live_ino_2, ".probe.json"],
                      f"live inode went {live_ino_1} -> {live_ino_2}; the "
                      f"first version now exists only here, and that is the "
                      f"3 files sitting in other/claude-config today")
        finally:
            os.environ.pop("RETENTION_GUARD_LEDGER", None)

        # 4. AND THE EXPORTER REFUSES IT, live AND archived. If this check is
        #    the one that goes red, the flag has stopped meaning anything and
        #    the archiver is not where to fix it.
        roots = E._tool_roots(home, arch / "other")
        check("the exporter takes no live root for it",
              [r[2] for r in roots if r[0] == "probe-config" and r[2] == "live"],
              [], "preserve=False is honoured HERE — this is the ship path")
        check("nor the archive directory the archiver just filled",
              [r[2] for r in roots if r[0] == "probe-config"], [],
              "the archive is walked by directory NAME, so the same skip set "
              "has to be applied to it — that is how oauth_creds.json got out "
              "the first time")

        # 5. THE SHIPPED MAP, not the fixture. The map is the part that gets
        #    edited, and all three of these are the counter file.
        check("and the three real counter-file stores are still handed to the "
              "archiver",
              sorted(l for l in ("claude-config", "claude-config-profiles",
                                 "proteus-claude-config")
                     if l in RG.OTHER_SOURCES),
              ["claude-config", "claude-config-profiles",
               "proteus-claude-config"],
              "dropping any of these from the archiver's map is silent: run() "
              "prints nothing for a label it was never given")
        check("every one of them says WHY it is never shipped",
              [l for l in ("claude-config", "claude-config-profiles",
                           "proteus-claude-config")
               if not RG.stores.BY_LABEL[l].no_preserve_because], [])
    finally:
        RG.stores.STORES.remove(probe)
        RG.stores.BY_LABEL.pop(probe.label, None)
        shutil.rmtree(d, ignore_errors=True)


def a_the_profile_root_records_are_archived():
    """history.jsonl and stats-cache.json sit at a profile's ROOT and nothing took them.

    460 sessionIds appear in the five history.jsonl files with NO transcript on
    disk and none in the archive: cleanupPeriodDays took the transcript and left
    the prompt. All five files were nlink=1 — one name, no copy, unrecoverable.
    The per-profile loop walked CLAUDE_CLEANED and CLAUDE_CLEANED only, so the
    records BESIDE those directories belonged to no rule in either program.

    Four properties, and the last two are the ones that make the obvious fix
    wrong rather than merely incomplete:

      1. the two records reach the archive — asserted by NLINK on the live file,
         not by the archived path existing. A path can exist holding a DIFFERENT
         inode, which is exactly what _archive_name was written for, and
         `exists()` cannot tell those apart.
      2. .credentials.json is still refused. All five profiles hold one and they
         are live Claude OAuth tokens.
      3. .claude.json is NOT admitted. Pointing a store at `.*claude*` resolves
         onto ~/.claude.json as a FILE, and link_tree's file branch sets `only`,
         which disables the records allow-list — re-admitting under a new label
         the bytes claude-config carries preserve=False for.
      4. a profile path that is not there CANNOT return a quiet zero. Every
         other caller suppresses "absent"; here the path came from
         claude_profiles() and absent means it vanished mid-run. `~/.*claude*`
         is neither file nor directory, so the glob store returns
         (0, 0, 'absent') and both print gates drop it — archives nothing, says
         nothing, and reads exactly like a healthy run.
    """
    import pathlib
    import shutil
    import tempfile

    d = pathlib.Path(tempfile.mkdtemp(prefix="profroot-"))
    try:
        home = d / "home"
        prof = home / ".claude"
        (prof / "projects").mkdir(parents=True)
        (prof / "projects" / "a.jsonl").write_text("{}\n", encoding="utf-8")
        records = ["history.jsonl", "stats-cache.json"]
        kept_out = [".credentials.json", ".claude.json", "settings.local.json"]
        for f in records + kept_out:
            (prof / f).write_text("x", encoding="utf-8")
        (prof / "settings.json").write_text("{}", encoding="utf-8")

        os.environ["RETENTION_GUARD_LEDGER"] = "0"
        try:
            with patched(HOME=str(home), ARCHIVE=str(d / "arch"),
                         OTHER_SOURCES={}, ROOT_FILE_SOURCES={},
                         claude_profiles=lambda: [str(prof)],
                         windows_side_profiles=lambda: []):
                _rc, log = quiet(lambda: RG.run(apply=True))

                for f in records:
                    check(f"{f} has a second name after the run",
                          (prof / f).stat().st_nlink, 2,
                          "nlink=1 is the whole finding: no copy anywhere")
                for f in kept_out:
                    check(f"{f} still has exactly one name",
                          (prof / f).stat().st_nlink, 1,
                          "the profile root is full of credentials and config; "
                          "taking the records must not take those")
                check("the archived record is the SAME INODE, not a look-alike",
                      (d / "arch" / "claude" / "claude" / "history.jsonl")
                      .stat().st_ino,
                      (prof / "history.jsonl").stat().st_ino)
                check("and the run names the profile root as covered",
                      "<root>" in log, True,
                      "a pass that archives silently is a pass nobody can "
                      "confirm ran")

                # 4. THE SILENT ZERO. A profile that is not there.
                RG.FAILED_LINKS.clear()
                with patched(claude_profiles=lambda: [str(home / ".gone")]):
                    _rc2, log2 = quiet(lambda: RG.run(apply=True))
                check("a profile that is not there is REPORTED, not skipped",
                      "<root>: absent" in log2, True,
                      "`~/.*claude*` as a store path returns (0,0,'absent') and "
                      "both print gates drop it — the silent zero this repo has "
                      "shipped seven times")
        finally:
            os.environ.pop("RETENTION_GUARD_LEDGER", None)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def a_archiving_a_thread_does_not_move_it_out_of_the_belt():
    """codex ARCHIVES by MOVING, and the destination was in no store.

    archive_thread.rs is `archive_folder.join(&file_name)` — FLAT, none of the
    YYYY/MM/DD structure sessions/ has. So archiving a thread takes a rollout
    out of Store("codex") and puts it somewhere Store("codex-root") cannot
    reach either: that one is kind="root_files", which is never recursed. grok
    has had the sessions/archived_sessions pair since it was written; codex is
    the half nobody added.

    Codex keeps NO lifetime counter. Claude's `.claude.json` is why a deleted
    transcript can still be counted; there is no equivalent here, so a rollout
    that moves while the destination is uncovered leaves nothing behind at all.

    THE DIRECTORY IS NOT ON THIS MACHINE, AND THAT IS THE HARD PART. A store
    that is not there yet must stay distinguishable from a store the belt used
    to catch and no longer can — link_tree's _archive_holds/VANISHED branch is
    the only thing that can tell them apart, and it is only reached from
    OTHER_SOURCES. Both halves are asserted: the quiet one BEFORE the move, and
    the named one after.
    """
    import pathlib
    import shutil
    import tempfile

    d = pathlib.Path(tempfile.mkdtemp(prefix="codex-arch-"))
    try:
        check("~/.codex/archived_sessions is claimed by a store",
              RG.OTHER_SOURCES.get("codex-archived"), [".codex/archived_sessions"],
              "Store('codex') is the sessions/ sibling and codex-root is "
              "root_files, which is never recursed — the move landed nowhere")
        check("and it is not narrowed by a records allow-list",
              RG.ROOT_FILE_RECORDS.get("codex-archived", "absent"), "absent",
              "a rollout filename is on no whitelist; records=None is the "
              "default 'the store has not said', and a link costs 0 bytes")

        with patched(ARCHIVE=str(d / "arch")):
            sess = d / "home" / ".codex" / "sessions" / "2026" / "08" / "10"
            arch_src = d / "home" / ".codex" / "archived_sessions"
            sess.mkdir(parents=True)
            roll = sess / "rollout-2026-08-10T04-58-00-abc.jsonl"
            roll.write_text('{"type":"token_count"}\n', encoding="utf-8")

            RG.VANISHED.clear()
            RG.FAILED_LINKS.clear()
            before = RG.link_tree(str(arch_src), "other/codex-archived", True)
            check("a machine that has never archived a thread says only "
                  "'absent'", before, (0, 0, "absent"),
                  "the directory is created on the first archive; an alarm "
                  "that is wrong on every run is one people stop reading")
            check("and that is not a link failure", RG.FAILED_LINKS, [])

            # codex archives the thread: MOVE, flat, no date path.
            arch_src.mkdir(parents=True)
            moved = arch_src / roll.name
            roll.rename(moved)

            n, _sk, note = RG.link_tree(str(arch_src), "other/codex-archived", True)
            got = sorted(p.name for p in
                         (d / "arch" / "other" / "codex-archived").iterdir())
            check("the moved rollout is caught where it landed",
                  (n, note, got), (1, "ok", [moved.name]),
                  "codex has no lifetime counter, so a rollout that moves out "
                  "of a covered path leaves no number behind to miss it by")
            check("and it is the SAME inode, not a copy",
                  moved.stat().st_nlink, 2)

            # AND THE OTHER HALF OF THE DISTINCTION. Now that the archive holds
            # its history, the source going away is a different sentence.
            shutil.rmtree(arch_src)
            RG.VANISHED.clear()
            after = RG.link_tree(str(arch_src), "other/codex-archived", True)
            check("once it has been caught, the source going away is NAMED",
                  after[2].startswith("SOURCE GONE"), True, f"got {after[2]!r}")
            check("and 'not installed yet' and 'stopped being caught' are "
                  "still two different sentences", before[2] != after[2], True,
                  "run() suppresses 'absent' entirely, so a store that fell "
                  "off the belt would print exactly what it printed the day "
                  "before the directory existed")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def a_the_shipped_records_map_survives_a_real_walk():
    """The SHIPPED map, on a REAL walk, by INODE. Not a probe store, not a dict.

    a_the_archiver_reads_records proves two things SEPARATELY and neither of
    them is this one:

        the mechanism   link_tree(records=("history.jsonl", ...)) narrows —
                        with a tuple this test file wrote, against a store this
                        test file invented, and (for run()) with
                        ROOT_FILE_SOURCES and ROOT_FILE_RECORDS PATCHED OUT.
        the map         RG.ROOT_FILE_RECORDS == {...literal...}

    "A dict that exists and is never consulted" is this repository's signature
    failure, and two proofs either side of the join are exactly how it hides:
    the mechanism check passes against a fake map, and the equality check passes
    against a dict nothing reads. Neither one walks ~/.codex and asks what
    ended up in the archive.

    So this builds a fixture HOME at the REAL store paths and calls the REAL
    run() with ROOT_FILE_SOURCES, ROOT_FILE_RECORDS and OTHER_SOURCES LEFT
    ALONE. Only HOME, ARCHIVE and the two Claude-profile finders are patched.

    AND IT ASSERTS ON st_ino, NOT ON exists(). A hard link is a SECOND NAME FOR
    ONE INODE — that is the entire reason this program is free. os.path.exists()
    is equally true of a copy, and a copy of ~/.copilot/session-store.db is 1.8
    MB that stops tracking the live file the moment it is written.

    FIVE THINGS, AND THEY ARE THE FIVE QUESTIONS:

      1. is a file the tuple does not name archived anyway?  (records ignored)
      2. is a file the tuple DOES name dropped?              (tuple misapplied)
      3. does the `only` branch — a store whose path names ONE FILE, and that is
         ~/.ollama/history — still get through, with its siblings left alone?
      4. does records=None still take EVERYTHING? Six of the seven root_files
         stores have a CONVERSATION store nested inside them —
         .gemini/antigravity-cli/brain is 396 files / 62,320,844 B fleet-wide,
         and .gemini has records=(), the narrowest sentence in the map. If the
         narrowing ever reached the nested store, that is the loss.
      5. does _refuse still run, at depth, as the LAST LINE OF DEFENCE? It has
         to, because of 4: 39 of the 46 stores pass records=None, so for most
         of the files walked it is the only credential test there is.
    """
    import pathlib
    import shutil
    import tempfile

    # rel -> True if the live inode must appear in the archive after the walk.
    LIVE = {
        # -------- root_files stores: the shipped tuples, exercised by name
        ".gemini/antigravity-cli/history.jsonl": True,
        ".gemini/antigravity-cli/conversation_summaries.db": True,
        ".gemini/antigravity-cli/settings.json": False,     # not in the tuple
        ".gemini/antigravity-cli/oauth_creds.json": False,  # refused first
        ".clawspring/input_history.txt": True,
        ".clawspring/config.toml": False,
        ".proteus/history.jsonl": True,
        ".proteus/stats-cache.json": True,
        ".proteus/cli.log": False,
        ".codex/history.jsonl": True,
        # the glob is wider than the one file on this machine ON PURPOSE:
        # macbook-air-m1 exported 3 files / 21,603 B out of ~/.codex and
        # nobody knows their names
        ".codex/rollout-2026.jsonl": True,
        ".codex/notes.ndjson": True,
        ".codex/config.toml": False,
        ".copilot/command-history-state.json": True,
        ".copilot/session-store.db": True,
        ".copilot/session-store.db-wal": True,   # 445 pages can sit in it
        ".copilot/session-store.db-shm": False,  # zero rows
        ".copilot/config.json": False,
        ".gemini/settings.json": False,          # gemini-root records=()
        ".gemini/oauth_creds.json": False,
        ".jules/history.txt": True,
        ".jules/config.json": False,
        # -------- conversation stores NESTED INSIDE those same roots.
        # records=None, so all of these must survive in full.
        ".gemini/antigravity-cli/brain/a/b/notes.md": True,
        ".gemini/antigravity-cli/conversations/c1.json": True,
        ".gemini/tmp/sess/logs.json": True,
        ".copilot/session-state/s1/state.json": True,
        ".codex/sessions/2026/s.jsonl": True,
        ".proteus/sessions/p1.json": True,
        ".clawspring/sessions/s.json": True,
        # -------- the `only` branch, and its sibling
        ".ollama/history": True,
        ".ollama/id_ed25519": False,
        ".claude.json": True,
        # -------- _refuse at depth, inside a store that names no records
        ".copilot/session-state/mcp-secrets/gh.json": False,
    }

    d = pathlib.Path(tempfile.mkdtemp(prefix="shipped-"))
    try:
        home = d / "home"
        for rel in LIVE:
            p = home / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("x", encoding="utf-8")

        RG.FAILED_LINKS.clear()
        RG.REFUSED_CONFIG.clear()
        RG.UNRECOGNISED.clear()
        RG.NOT_A_RECORD.clear()
        os.environ["RETENTION_GUARD_LEDGER"] = "0"
        try:
            # ROOT_FILE_SOURCES / ROOT_FILE_RECORDS / OTHER_SOURCES ARE NOT IN
            # THIS LIST, and that is the whole point of the scenario.
            with patched(HOME=str(home), ARCHIVE=str(d / "arch"),
                         claude_profiles=lambda: [],
                         windows_side_profiles=lambda: []):
                _rc, log = quiet(lambda: RG.run(apply=True))
        finally:
            os.environ.pop("RETENTION_GUARD_LEDGER", None)

        archived = set()
        for root, _dn, files in os.walk(d / "arch"):
            for f in files:
                archived.add(os.stat(os.path.join(root, f)).st_ino)
        got = {rel: ((home / rel).stat().st_ino in archived) for rel in LIVE}

        dropped = sorted(r for r in LIVE if LIVE[r] and not got[r])
        check("every record the shipped map names got a SECOND NAME for its "
              "inode", dropped, [],
              "a record dropped here is the only copy — nothing in this "
              "program ever writes it back")
        taken = sorted(r for r in LIVE if not LIVE[r] and got[r])
        check("and nothing the shipped map does not name was archived", taken, [],
              "records= was decorative once: the archiver read the store map "
              "for PATHS and for nothing else, and every loose file beside a "
              "tool's program directories was a CANDIDATE")

        # 3. THE `only` BRANCH, ON A REAL WALK.
        check("~/.ollama/history is archived — a store that NAMES one file is "
              "never narrowed", got[".ollama/history"], True)
        check("and ~/.claude.json with it",
              got[".claude.json"], True,
              "the last surviving evidence of 4,062,282,405 tokens")
        check("while the key beside it is not even considered",
              got[".ollama/id_ed25519"], False,
              "`only` is what keeps the file case from degenerating into "
              "top_only over ~/.ollama")

        # 4. records=None STILL TAKES EVERYTHING — from inside the very roots
        #    that are narrowed.
        nested = [r for r in LIVE if LIVE[r] and "/" in r.rstrip("/")
                  and r.count("/") >= 2]
        check("the conversation stores nested inside the narrowed roots keep "
              "everything",
              sorted(r for r in nested if not got[r]), [],
              "top_only is what keeps a root tuple off them; .gemini says "
              "records=() and .gemini/tmp must not hear it")
        check("nothing from a nested conversation store reached the narrowed "
              "bucket",
              [f for _l, f in RG.NOT_A_RECORD if "/" in f], [],
              "NOT_A_RECORD is a depth-0 sentence; a path with a separator in "
              "it means a records tuple escaped onto a conversation store")

        # 5. _refuse IS STILL THE LAST LINE OF DEFENCE, AT DEPTH.
        check("the credentials are NAMED as credentials, not as non-records",
              sorted(f for _l, f, _p in RG.REFUSED_CONFIG),
              ["mcp-secrets/gh.json", "oauth_creds.json", "oauth_creds.json"],
              "narrow-then-refuse drops them anonymously and the run a new "
              "credential appears reads like every run before it")
        check("and none of them is in the narrowed bucket instead",
              {f for _l, f in RG.NOT_A_RECORD} &
              {os.path.basename(f) for _l, f, _p in RG.REFUSED_CONFIG}, set())

        # AND THE REPORT. A bucket that only exists in memory is not a report.
        check("run() names every narrowed file on the NOT ARCHIVED report",
              sorted(f.split("/")[-1] for _l, f in RG.NOT_A_RECORD),
              sorted(os.path.basename(r) for r in LIVE
                     if not LIVE[r] and "creds" not in r and "gh.json" not in r
                     and "id_ed25519" not in r),
              f"got {[f for _l, f in RG.NOT_A_RECORD]!r}")
        check("and prints it", any("NOT ARCHIVED" in ln
                                   for ln in log.splitlines()), True)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def a_naming_a_file_in_a_store_does_not_disable_the_credential_test():
    """`only` switched off `_refuse` ENTIRELY, so a store path was a bypass.

    link_tree turns a store whose path names ONE FILE into a walk of its parent
    plus `only`, and the credential test read

        if only is None and _refuse(f, in_secret_dir):

    so for those stores there was no credential test at all. Verbatim, against
    the shipped file:

        link_tree('<tmp>/.ollama/id_ed25519', arch, apply=True) -> (1, 0, 'ok')
        arch/id_ed25519                       nlink(live) = 2
        REFUSED_CONFIG == []

    The comment defending `only is None` is RIGHT and is not what changed. A
    store whose path names one file names it BECAUSE THAT FILE IS THE RECORD —
    ~/.ollama/history is a 4,422-byte FILE that read as "absent" for the whole
    life of the rule, and ~/.claude.json is the last surviving evidence of
    4,062,282,405 tokens. Neither can pass a test built for "which of these
    loose files is history". But "this named file is a record" is an answer to
    WHICH FILE, not to IS IT A CREDENTIAL, and one flag was answering both.

    Reachable, and measured rather than assumed. THREE shipped store paths take
    this branch today — `.claude.json`, `.ollama/history` and
    `.proteus/.claude.json`, the last added hours ago — so the only thing
    between a credential and the archive is that nobody has written its path
    down yet. `.copilot/mcp-secrets/gh.json` written into stores.py arrives here
    with the SECRET_DIRS test blinded as well: `only` makes src the file's
    PARENT, so `rel` is "." and the component naming the directory is gone
    before the per-component test runs. Scenario 5 below drives that through
    run() and ROOT_FILE_SOURCES, which is where such a path is actually written.

    NOT the route to worry about: retention_guard never globs a store path.
    run() joins them literally (`os.path.join(HOME, *rel.split("/"))`), so a
    pattern like `.claude*/.claude.json` reaches link_tree with the `*` intact
    and returns "absent". The `.*claude*` glob in claude_profiles() cannot
    produce ~/.claude.json either — looks_like_profile() requires a projects/
    directory holding .jsonl.

    The four things that must still hold are all asserted below: history
    archived, .claude.json archived AND still counted by read_claude_orphans,
    and id_ed25519 beside them never a candidate either way.
    """
    import json as _json
    import pathlib
    import shutil
    import tempfile

    d = pathlib.Path(tempfile.mkdtemp(prefix="only-"))
    try:
        # ~/.ollama, exactly as it sits on this machine: a record that is a
        # FILE, with a private key for company.
        ollama = d / ".ollama"
        ollama.mkdir()
        (ollama / "history").write_text("what is a hard link\n", encoding="utf-8")
        (ollama / "id_ed25519").write_text("-----BEGIN OPENSSH PRIVATE KEY-----",
                                           encoding="utf-8")
        (ollama / "oauth_creds.json").write_text('{"refresh_token":"x"}',
                                                 encoding="utf-8")

        # 1. THE RECORD STILL GETS THROUGH, and nothing else in that directory
        #    comes with it. This is what `only` is for and it is unchanged.
        RG.REFUSED_CONFIG.clear()
        n, _sk, note = RG.link_tree(str(ollama / "history"), str(d / "a1"), True)
        got = sorted(p.name for p in (d / "a1").iterdir())
        check("a store that NAMES ~/.ollama/history still archives it",
              (n, note, got), (1, "ok", ["history"]),
              "it is a FILE, not a directory, and it read as 'absent' for the "
              "entire life of the rule")
        check("nothing was refused on its way through", RG.REFUSED_CONFIG, [])
        check("and the private key beside it is not a candidate",
              [(ollama / "id_ed25519").stat().st_nlink,
               (ollama / "oauth_creds.json").stat().st_nlink], [1, 1],
              "nlink 2 is the archive holding the same inode as the original")

        # 2. AND THE SAME MECHANISM POINTED AT THE KEY. This is the hole.
        for cred in ("id_ed25519", "oauth_creds.json"):
            RG.REFUSED_CONFIG.clear()
            arch = d / f"a2-{cred}"
            n2, _s2, note2 = RG.link_tree(str(ollama / cred), str(arch), True)
            check(f"a store whose path NAMES {cred} archives nothing",
                  (n2, note2), (0, "ok"),
                  "naming a file in the store map is not a reason to stop "
                  "asking whether it is a credential")
            check(f"{cred} is not in the archive at all",
                  (arch / cred).exists(), False)
            check(f"and the live {cred} still has exactly one name",
                  (ollama / cred).stat().st_nlink, 1)
            check(f"and the {cred} refusal is NAMED, not a silent drop",
                  [f for _l, f, _p in RG.REFUSED_CONFIG], [cred],
                  "a credential dropped anonymously reads like a clean run")

        # 3. A STORE PATH THAT REACHES INTO A SECRET DIRECTORY. `only` makes
        #    src the file's PARENT, so the component that names the directory
        #    is gone before the per-component test ever runs.
        sd = d / ".copilot" / "MCP-Secrets"
        sd.mkdir(parents=True)
        (sd / "gh.json").write_text("ghp_SECRET", encoding="utf-8")
        RG.REFUSED_CONFIG.clear()
        n3, _s3, note3 = RG.link_tree(str(sd / "gh.json"), str(d / "a3"), True)
        check("a store path that names a file inside a SECRET_DIRS directory "
              "archives nothing", (n3, note3), (0, "ok"),
              "the directory component is chopped off the walk root, so it has "
              "to be asked where it is still visible")
        check("gh.json did not reach the archive",
              (d / "a3" / "gh.json").exists(), False)
        check("and it still has exactly one name",
              (sd / "gh.json").stat().st_nlink, 1)
        check("in a spelling the case-sensitive test used to miss",
              [f for _l, f, _p in RG.REFUSED_CONFIG], ["gh.json"])

        # 4. ~/.claude.json — 4,062,282,405 tokens, and config by every name
        #    test there is. It must survive BOTH rules: still archived, and
        #    still counted. A "fix" that refuses it would pass every check
        #    above and delete this machine's oldest record from the belt.
        home = d / "home"
        home.mkdir()
        (home / ".claude.json").write_text(_json.dumps({
            "oauthAccount": {"emailAddress": "a@b.c"},
            "projects": {"/p": {"lastSessionId": "sid-orphan",
                                "lastTotalInputTokens": 4062282405}}}),
            encoding="utf-8")
        RG.REFUSED_CONFIG.clear()
        n4, _s4, note4 = RG.link_tree(str(home / ".claude.json"),
                                      str(d / "a4"), True)
        check("~/.claude.json is still archived by a store that names it",
              (n4, note4, (d / "a4" / ".claude.json").exists()),
              (1, "ok", True),
              "config by name, and the only surviving evidence of 4.06 B tokens")
        check("and nothing was refused on its way through", RG.REFUSED_CONFIG, [])

        import sessions as SESS
        orph = SESS.read_claude_orphans(home)
        check("and read_claude_orphans still counts it",
              [(r["session_id"], r["tokens"]["input_tokens"]) for r in orph],
              [("sid-orphan", 4062282405)],
              "the archiver and the reader are two layers over one file; "
              "narrowing one must not be done by narrowing the other")

        # 5. AND THROUGH run(), WHICH IS THE ONLY CALLER THAT EXISTS. The
        #    store map is where a path like this is written, so the reachable
        #    version of this attack is a ROOT_FILE_SOURCES entry.
        h2 = d / "home2"
        (h2 / ".ollama").mkdir(parents=True)
        (h2 / ".ollama" / "history").write_text("q\n", encoding="utf-8")
        (h2 / ".ollama" / "id_ed25519").write_text("KEY", encoding="utf-8")
        os.environ["RETENTION_GUARD_LEDGER"] = "0"
        try:
            with patched(HOME=str(h2), ARCHIVE=str(d / "a5"),
                         OTHER_SOURCES={},
                         ROOT_FILE_SOURCES={"ollama": [".ollama/history"],
                                            "strays": [".ollama/id_ed25519"]},
                         ROOT_FILE_RECORDS={},
                         claude_profiles=lambda: [],
                         windows_side_profiles=lambda: []):
                _rc, log = quiet(lambda: RG.run(apply=True))
        finally:
            os.environ.pop("RETENTION_GUARD_LEDGER", None)
        check("run() archives the record named by a store path",
              (d / "a5" / "other" / "ollama" / "history").exists(), True)
        check("and does not archive the key named by a store path",
              (d / "a5" / "other" / "strays" / "id_ed25519").exists(), False)
        check("the live key still has exactly one name",
              (h2 / ".ollama" / "id_ed25519").stat().st_nlink, 1)
        check("and run() prints the refusal rather than swallowing it",
              "id_ed25519" in log and "REFUSED" in log, True, f"got {log!r}")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def a_the_only_branch_sees_every_ancestor_not_just_the_parent():
    """The `only` branch's directory test saw the PARENT. One subdir was a bypass.

    The credential test on this branch is two questions, and closing the first
    left the second open at depth 2. `_refuse(f, in_secret_dir)` asks

        is the FILE's NAME a credential      _is_secret  — depth-independent
        is it INSIDE a secret DIRECTORY      only_dir_secret

    and `only_dir_secret = secret_dir(os.path.basename(src))` is the immediate
    parent alone, because link_tree chops the file off the walk root and the
    per-component test over `rel` then has nothing left to see. Measured against
    the shipped file, one store path per line:

        .copilot/mcp-secrets/gh.json            parent 'mcp-secrets'  refused
        .copilot/mcp-secrets/sub/history.jsonl  parent 'sub'          ARCHIVED
        .copilot/mcp-secrets/a/b/history.jsonl  parent 'b'            ARCHIVED

    A single subdirectory switched the directory rule off, and the file names
    that get through are the ones NOTHING else can catch: `history.jsonl` is
    what `_is_loose_record` exists to admit and what `_is_secret` is guaranteed
    not to match, so on that branch the ancestry was the only rule in the way.

    THE BOUNDARY IS HOME, AND THE BOUNDARY IS THE HARD PART. Walking to `/`
    closes the hole and opens a worse one in the other direction: this is the
    ARCHIVER, where a wrongful refusal is a record that never gets a second name
    and the archive is the only copy for 7 of the 8 CLIs. A user whose HOME is
    /home/keys, or a machine mounting /Volumes/certs, would have
    ~/.ollama/history refused by a component nobody in this program chose. run()
    builds every path that reaches this branch as os.path.join(HOME, *rel), so
    the components the STORE MAP named are exactly the ones below HOME. Both
    directions are asserted here — the depth cases below, and the two HOME
    fixtures at the end that must still archive.

    THE FOUR THINGS THAT MUST NOT BREAK are asserted rather than assumed, since
    every one of them is a file this change could newly refuse: ~/.ollama/history
    (a FILE store that once read as "absent", which is indistinguishable from
    ollama not being installed), ~/.claude.json (still archived AND still
    counted by read_claude_orphans, which on this machine finds 107 sessions
    with no transcript left anywhere), and id_ed25519 beside them (ino 43133463,
    nlink=1), which must stay at exactly one name.

    Measured on the real HOME with ARCHIVE redirected and apply=False, before
    and after, identical both ways:

        ~/.ollama/history     (n=1, 'ok')  ino 43127031 nlink 2
        ~/.ollama/id_ed25519  (n=0, 'ok')  ino 43133463 nlink 1  refused
        ~/.claude.json        (n=1, 'ok')  ino 42216275 nlink 2
        read_claude_orphans   107 orphan session(s)
        profile roots         .claude, .claude-alt -> history.jsonl +
                              stats-cache.json; .claude-alt-api, .claude-it,
                              .my-claude -> history.jsonl (they have no
                              stats-cache.json to take)
    """
    import json as _json
    import pathlib
    import shutil
    import tempfile

    d = pathlib.Path(tempfile.mkdtemp(prefix="depth-"))
    try:
        home = d / "home"

        def build(rel, body="q\n"):
            p = home.joinpath(*rel.split("/"))
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body, encoding="utf-8")
            return p

        # Depth 1, 2 and 3 below a documented OAuth directory, all wearing the
        # name the loose-record whitelist is built to ADMIT, plus the dotted /
        # mixed-case spelling of a second secret directory at depth 2.
        blocked = {
            "depth 1": build(".copilot/mcp-secrets/gh.json", "ghp_SECRET"),
            "depth 2": build(".copilot/mcp-secrets/sub/history.jsonl"),
            "depth 3": build(".copilot/mcp-secrets/a/b/history.jsonl"),
            "depth 2, dotted + mixed case":
                build(".copilot/.Credentials/x/history.jsonl"),
        }
        # And the control: the SAME depth, the same file name, a directory that
        # is not a secret one. A fix that refuses this is not a fix.
        allowed = {
            "depth 3 control": build(".copilot/session-state/a/b/history.jsonl"),
            "depth 1 control": build(".ollama/history", "what is a hard link\n"),
        }
        # The private key that lives beside the ollama record on this machine
        # (ino 43133463, nlink=1, zero archive hits today).
        key = build(".ollama/id_ed25519", "-----BEGIN OPENSSH PRIVATE KEY-----")

        with patched(HOME=str(home)):
            for i, (name, p) in enumerate(blocked.items()):
                RG.REFUSED_CONFIG.clear()
                arch = d / f"blocked-{i}"
                n, _sk, note = RG.link_tree(str(p), str(arch), True)
                check(f"a store path naming a file at {name} inside a secret "
                      f"directory archives nothing", (n, note), (0, "ok"),
                      "the secret component is above the walk root, so it is "
                      "only visible before the walk starts")
                check(f"{name}: it did not reach the archive",
                      (arch / p.name).exists(), False)
                check(f"{name}: the live file still has exactly one name",
                      p.stat().st_nlink, 1,
                      "nlink 2 is the archive holding the same inode")
                check(f"{name}: and the refusal is NAMED, not a silent drop",
                      [f for _l, f, _p in RG.REFUSED_CONFIG], [p.name],
                      "a credential dropped anonymously reads like a clean run")

            for name, p in allowed.items():
                RG.REFUSED_CONFIG.clear()
                arch = d / f"ok-{name.split()[1]}"
                n, _sk, note = RG.link_tree(str(p), str(arch), True)
                check(f"{name}: a legitimate record at that depth is still "
                      f"archived", (n, note, p.stat().st_nlink), (1, "ok", 2),
                      "a refusal here is a record that never gets a second "
                      "name, and for 7 of 8 CLIs the file IS the only evidence")
                check(f"{name}: and nothing was refused on its way through",
                      RG.REFUSED_CONFIG, [])

            check("the private key beside the ollama record is still not a "
                  "candidate", key.stat().st_nlink, 1)

            # ~/.claude.json: config by every name test there is, and the last
            # surviving evidence of the sessions whose transcripts Claude Code
            # already deleted. Both layers, because narrowing the archiver by
            # narrowing the reader would pass every check above.
            (home / ".claude.json").write_text(_json.dumps({
                "oauthAccount": {"emailAddress": "a@b.c"},
                "projects": {"/p": {"lastSessionId": "sid-orphan",
                                    "lastTotalInputTokens": 4071258650}}}),
                encoding="utf-8")
            RG.REFUSED_CONFIG.clear()
            n4, _s4, note4 = RG.link_tree(str(home / ".claude.json"),
                                          str(d / "a-claude"), True)
            check("~/.claude.json is still archived by a store that names it",
                  (n4, note4, (d / "a-claude" / ".claude.json").exists()),
                  (1, "ok", True))
            check("and nothing was refused on its way through",
                  RG.REFUSED_CONFIG, [])

        import sessions as SESS
        orph = SESS.read_claude_orphans(home)
        check("and read_claude_orphans still counts ~/.claude.json",
              [(r["session_id"], r["tokens"]["input_tokens"]) for r in orph],
              [("sid-orphan", 4071258650)],
              "the archiver and the reader are two layers over one file")

        # THE OTHER DIRECTION, WHICH IS WHY THE WALK STOPS AT HOME. Two
        # fixtures whose SECRET component is HOME itself and an ancestor of it.
        # A walk to `/` refuses both, and each refusal is pure record loss.
        boundaries = {
            # HOME itself is a secret directory name — /home/keys.
            "HOME is named 'keys'": d / "b1" / "keys",
            # and one ABOVE HOME — /Volumes/certs/someone.
            "HOME sits under 'certs'": d / "b2" / "certs" / "someone",
        }
        for i, (why, h) in enumerate(boundaries.items()):
            rec = h / ".ollama" / "history"
            rec.parent.mkdir(parents=True, exist_ok=True)
            rec.write_text("q\n", encoding="utf-8")
            with patched(HOME=str(h)):
                RG.REFUSED_CONFIG.clear()
                n5, _s5, note5 = RG.link_tree(str(rec), str(d / f"bnd-{i}"), True)
                refused = list(RG.REFUSED_CONFIG)
            check(f"{why}: ~/.ollama/history is still archived",
                  (n5, note5, rec.stat().st_nlink), (1, "ok", 2),
                  "components at or above HOME were chosen by the account and "
                  "the mount table, not by the store map — walking to / turns "
                  "this fix into record loss")
            check(f"{why}: and it produced no refusal", refused, [])

        # AND THROUGH run(), WHICH IS THE ONLY CALLER THAT EXISTS. A store map
        # entry is how such a path actually gets written.
        h2 = d / "home2"
        for rel in (".copilot/mcp-secrets/sub/history.jsonl", ".ollama/history"):
            p = h2.joinpath(*rel.split("/"))
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("q\n", encoding="utf-8")
        os.environ["RETENTION_GUARD_LEDGER"] = "0"
        try:
            with patched(HOME=str(h2), ARCHIVE=str(d / "a-run"),
                         OTHER_SOURCES={},
                         ROOT_FILE_SOURCES={
                             "ollama": [".ollama/history"],
                             "deep": [".copilot/mcp-secrets/sub/history.jsonl"]},
                         ROOT_FILE_RECORDS={},
                         claude_profiles=lambda: [],
                         windows_side_profiles=lambda: []):
                _rc, log = quiet(lambda: RG.run(apply=True))
        finally:
            os.environ.pop("RETENTION_GUARD_LEDGER", None)
        check("run() still archives the record named by a store path",
              (d / "a-run" / "other" / "ollama" / "history").exists(), True)
        check("run() does not archive a file two levels inside a secret "
              "directory", (d / "a-run" / "other" / "deep" / "history.jsonl"
                            ).exists(), False)
        check("the live file inside the secret directory has exactly one name",
              (h2 / ".copilot" / "mcp-secrets" / "sub" / "history.jsonl"
               ).stat().st_nlink, 1)
        check("and run() prints the refusal rather than swallowing it",
              "REFUSED" in log and "history.jsonl" in log, True, f"got {log!r}")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def a_push_retries_on_non_fast_forward():
    """step_push retries after a non-fast-forward rejection.

    The race: two machines both scan, both commit, machine A pushes first.
    Machine B's push is rejected with 'non-fast-forward'. Without the retry
    loop, machine B's scan is silently lost — the commit sits unreachable in
    its local repo and the daemon reports FAIL, which nobody reads until the
    next sync window.

    With the retry loop, machine B pulls --rebase and pushes again. The test
    plants a fake git that rejects the first push and accepts the second, then
    asserts the result is ok, not FAIL.
    """
    import sync_job as SJ

    # Simulate: first push → rejected (non-fast-forward), second → ok
    call_log = []

    original_git = SJ._git

    def fake_git(repo, *args, check=False):
        call_log.append(list(args))
        cmd = args[0] if args else ""
        if cmd == "rev-list":
            return True, "1", ""            # 1 commit ahead
        if cmd == "push":
            push_count = sum(1 for c in call_log if c == ["push"])
            if push_count == 1:             # first push → reject
                return False, "", "rejected (non-fast-forward)"
            return True, "", ""             # subsequent push → ok
        if cmd == "pull":
            return True, "Already up to date.", ""
        return True, "", ""

    import pathlib, tempfile
    d = pathlib.Path(tempfile.mkdtemp(prefix="adv-push-retry-"))
    (d / ".git").mkdir()                    # convince step_push it's a repo
    SJ._git = fake_git
    try:
        res = SJ.SyncResult(dry=False)
        SJ.step_push(res, [("test-repo", d)], retries=2, backoff=0)
        check("push retry on non-fast-forward -> result is ok", res.ok, True,
              f"lines: {res.lines}")
        pushed = [c for c in call_log if c == ["push"]]
        check("push retry on non-fast-forward -> push was called twice",
              len(pushed), 2,
              "only one push attempt means the retry loop is not running")
        rebased = [c for c in call_log if c[:2] == ["pull", "--rebase"]]
        check("push retry on non-fast-forward -> a rebase was attempted",
              len(rebased) >= 1, True,
              "no rebase means the retry loop pulled without rebasing, which "
              "would leave a merge commit in a repo that expects linear history")
    finally:
        SJ._git = original_git
        import shutil
        shutil.rmtree(str(d), ignore_errors=True)


ATTACKS = [
    ("retention fails, ledger must not", a_retention_fails),
    ("ledger fails, retention must not", a_ledger_fails),
    ("both fail, the loop must live", a_both_fail),
    ("disable the ledger only", a_disable_ledger),
    ("disable retention only", a_disable_retention),
    ("disable everything", a_disable_everything),
    ("record_ledger absorbs its own errors", a_ledger_returns_a_string_not_an_exception),
    ("a typo must not disable a job", a_unknown_env_value_does_not_silently_disable),
    ("two writers at once", a_two_writers_at_once),
    ("the ledger job must actually scan", a_ledger_job_actually_scans),
    ("tick must not invent ok", a_tick_does_not_invent_ok),
    ("verify-boot lifecycle proves live and dead verdicts", a_verify_boot_lifecycle),
    ("link_tree cannot report ok for nothing",
     a_link_tree_cannot_report_ok_for_work_it_did_not_do),
    ("the Windows side is never written", a_the_windows_side_is_never_written),
    ("credentials are never linked", a_credentials_are_never_linked),
    ("a real record is never dropped for its name",
     a_a_real_record_is_never_dropped_for_its_name),
    ("a vanished store is not a store that never existed",
     a_a_store_that_vanished_is_not_a_store_that_never_existed),
    ("already archived means the same inode",
     a_already_archived_is_identity_not_a_path),
    ("a dead belt cannot report ok", a_a_dead_belt_cannot_report_ok),
    ("the archiver reads the store's records", a_the_archiver_reads_records),
    ("preserve=False is the exporter's flag, not the archiver's",
     a_preserve_false_is_the_exporters_flag_not_the_archivers),
    ("a profile's loose records are archived",
     a_the_profile_root_records_are_archived),
    ("archiving a thread must not move it off the belt",
     a_archiving_a_thread_does_not_move_it_out_of_the_belt),
    ("the shipped records map survives a real walk",
     a_the_shipped_records_map_survives_a_real_walk),
    ("naming a file does not disable the credential test",
     a_naming_a_file_in_a_store_does_not_disable_the_credential_test),
    ("the `only` branch sees every ancestor, not just the parent",
     a_the_only_branch_sees_every_ancestor_not_just_the_parent),
    ("push retries on non-fast-forward rejection",
     a_push_retries_on_non_fast_forward),
]


def main():
    print(f"\n  DAEMON — {len(ATTACKS)} attacks\n")
    for name, fn in ATTACKS:
        print(f"  -- {name}")
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            print(f"  FAIL  {name} raised: {e}")
            FAILED.append(name)
    print()
    if SKIPPED:
        # Named and subtracted. "12 scenarios" over a run where five never
        # executed is the sentence this file exists to stop other files writing.
        print(f"  {len(SKIPPED)} attack(s) SKIPPED, not run: {', '.join(SKIPPED)}")
    if FAILED:
        print(f"  {len(FAILED)} check(s) FAILED: {', '.join(FAILED)}")
        return 1
    ran = len(ATTACKS) - len(SKIPPED)
    print(f"  every attack survived by the daemon, across {ran} scenario(s) that "
          f"ran" + (f" ({len(SKIPPED)} skipped)" if SKIPPED else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
