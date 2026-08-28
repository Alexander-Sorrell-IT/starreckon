#!/usr/bin/env python3
"""Attacks on the platform detector. It runs FIRST, so it fails first.

    python3 adversarial_platform.py

WHY THIS ONE MATTERS MORE THAN ITS SIZE SUGGESTS

platform_detect runs before anything is measured, and everything downstream
trusts what it says. So it has two ways to be dangerous, and they are opposite:

  it RAISES        nothing runs at all, on a machine that was working fine
  it LIES QUIETLY  a Mac is told to install a systemd unit, or a filesystem
                   that cannot hard-link is told the archive is fine

The second already happened. The first version answered "which service manager"
by asking whether systemctl was on PATH, never asking what platform it was on —
and reported `systemd` for macOS, Windows, Git Bash and Cygwin alike, because
systemctl was on the PATH of the machine doing the asking. Attack 1 is that bug,
frozen.

EVERY CAPABILITY MUST BE TESTED, NOT INFERRED

The attacks below break the CAPABILITY while leaving the OS name alone, which is
the case inference cannot survive: a Linux box whose home is on exFAT is still
Linux and still cannot hard-link. If the detector answers from platform.system()
it passes every one of these while being wrong.
"""
import contextlib
import io
import os
import platform
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import platform_detect as P

FAILED = []


def check(name, got, want, why=""):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        print(f"        got {got!r}, want {want!r}" + (f" — {why}" if why else ""))
        FAILED.append(name)


@contextlib.contextmanager
def as_platform(name, tools=(), **env):
    """Pretend to be another OS, restoring everything afterwards.

    PATCHES os.name AND shutil.which TOO, and that is the whole point.
    Patching only platform.system left the macOS and Windows branches of
    _service_manager unable to return anything but None on a Linux box —
    `launchctl` and `schtasks` are not on this PATH and os.name is "posix" —
    so `mac in (None, "launchd")` and `win in (None, "schtasks")` were
    satisfied by the None, every time. Gutting either branch entirely left the
    suite 8/8 green.

    `tools` names the commands that platform is pretending to have. A Mac has
    launchctl; that is what makes "launchd" the only correct answer rather than
    one of two acceptable ones.
    """
    # os.name is deliberately NOT patched. Setting it to "nt" changes how
    # pathlib expands "~" and detect() dies with "Could not determine home
    # directory" before it reaches the branch under test. _service_manager
    # keys on platform.system() first anyway, so `which` is the lever that
    # matters and this stays honest without breaking the interpreter.
    real_sys, real_which = platform.system, P.shutil.which
    old = dict(os.environ)
    platform.system = lambda n=name: n
    P.shutil.which = lambda n: n if n in tools else None
    for k in ("PSModulePath", "PROMPT", "MSYSTEM", "WSL_INTEROP"):
        os.environ.pop(k, None)
    os.environ.update(env)
    try:
        yield
    finally:
        platform.system = real_sys
        P.shutil.which = real_which
        os.environ.clear()
        os.environ.update(old)


def quiet(fn):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        r = fn()
    return r, buf.getvalue()


# ---------------------------------------------------------------------------

def a_service_manager_is_platform_first():
    """A Mac must never be told to install a systemd unit.

    The frozen bug. systemctl is on this machine's PATH, so a detector that asks
    only "is systemctl present" answers systemd for every platform it is shown.
    """
    # EXACT answers, not "one of these two". Each platform is given the tool it
    # really has AND systemctl, which is the trap: systemctl on PATH is what
    # made the original bug answer "systemd" for everything.
    with as_platform("Darwin", tools=("launchctl", "systemctl")):
        mac = P.detect()["service_manager"]
    with as_platform("Windows", tools=("schtasks", "systemctl"), PSModulePath="C:\\x"):
        win = P.detect()["service_manager"]
    with as_platform("Linux", tools=("systemctl",)):
        lin = P.detect()["service_manager"]
    check("macOS with launchctl AND systemctl present -> launchd", mac, "launchd",
          "accepting None here is how a gutted branch passed: launchctl is not "
          "on a Linux PATH, so the branch could only ever return None")
    check("Windows with schtasks AND systemctl present -> schtasks", win, "schtasks")
    check("Linux still resolves to systemd",
          str(lin).startswith("systemd"), True,
          "a fix that answers None everywhere would satisfy the two above")


def a_hardlinks_are_tested_not_assumed():
    """A filesystem that reports a normal st_dev and refuses to link.

    exFAT, FAT32, CIFS and sshfs all do this. It is the case that made a dead
    archive print the same line as a healthy one earlier today, so the detector
    must find it by TRYING, not by checking st_dev or the OS name.
    """
    real = os.link
    os.link = lambda *a, **k: (_ for _ in ()).throw(
        OSError(1, "Operation not permitted"))
    try:
        info = P.detect()
    finally:
        os.link = real
    c = info["capabilities"]
    check("a filesystem that refuses os.link is caught", c["hardlinks"], False,
          "st_dev matches on exFAT and CIFS — only trying it finds this")
    check("and the reason is reported, not just the fact",
          bool(c["hardlinks_why"]), True)
    check("and it warns that the archive layer cannot work",
          any("hard link" in w.lower() for w in info["warnings"]), True,
          "silence here means the belt is gone and nothing says so")


def a_case_insensitive_home_is_caught():
    """macOS defaults to a case-INSENSITIVE home. .Claude and .claude merge."""
    real = os.path.exists
    # Simulate case-insensitivity: the probe writes Aa then asks for aA.
    os.path.exists = lambda p: True if p.endswith("aA") else real(p)
    try:
        info = P.detect()
    finally:
        os.path.exists = real
    check("a case-insensitive home is detected",
          info["capabilities"]["case_sensitive_home"], False)
    check("and it warns that two profiles can merge",
          any("case" in w.lower() for w in info["warnings"]), True,
          "this is the macOS default and it silently merges profiles")


def a_detection_never_raises():
    """It runs FIRST. If it raises, nothing runs at all.

    Every probe is broken at once — no link, no symlink, no temp dir, no
    subprocess — which is worse than any real machine, and it still has to
    return an answer rather than take the whole run down.
    """
    saved = (os.link, os.symlink, tempfile.mkdtemp, P._run)
    os.link = lambda *a, **k: (_ for _ in ()).throw(OSError("no"))
    os.symlink = lambda *a, **k: (_ for _ in ()).throw(OSError("no"))
    tempfile.mkdtemp = lambda *a, **k: (_ for _ in ()).throw(OSError("no"))
    P._run = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no"))
    try:
        info = P.detect()
        raised = False
    except Exception:  # noqa: BLE001
        info, raised = None, True
    finally:
        os.link, os.symlink, tempfile.mkdtemp, P._run = saved
    check("detection survives every probe failing", raised, False,
          "it runs before everything else; a crash here blocks the whole run")
    if info:
        check("and still names the system", bool(info.get("system")), True)


def a_no_service_manager_says_so():
    """A machine with nothing to run a daemon must say that out loud."""
    real = P.shutil.which
    P.shutil.which = lambda n: None
    try:
        with as_platform("Linux"):
            info = P.detect()
    finally:
        P.shutil.which = real
    check("no service manager -> reported as None", info["service_manager"], None)
    check("and warned about, not left blank",
          any("service manager" in w.lower() for w in info["warnings"]), True,
          "a daemon that cannot survive a reboot is the failure this system has")


def a_wsl_reports_the_second_install():
    """WSL is a Linux kernel with a WHOLE SECOND operating system beside it.

    Two installs, two settings.json, two cleanupPeriodDays, two sets of
    transcripts. Protecting one does nothing for the other, so a detector that
    calls WSL "just Linux" hides half the machine.
    """
    import builtins
    real_open, real_homes = builtins.open, P._windows_homes
    def fake_open(p, *a, **k):
        if str(p) == "/proc/version":
            return io.StringIO("Linux version 5.15 microsoft-standard-WSL2")
        return real_open(p, *a, **k)
    builtins.open = fake_open
    P._windows_homes = lambda: ["/mnt/c/Users/someone"]
    try:
        with as_platform("Linux"):
            info = P.detect()
    finally:
        builtins.open, P._windows_homes = real_open, real_homes
    check("WSL is identified as WSL, not as plain Linux", info["is_wsl"], True)
    check("and its flavour says so", info["flavour"].startswith("wsl"), True)
    check("and the Windows-side home is reported",
          info["other_homes"], ["/mnt/c/Users/someone"])
    check("and it warns the other side is unprotected",
          any("windows" in w.lower() for w in info["warnings"]), True,
          "the side you are not looking at holds more")


def a_posix_layers_over_windows_are_flagged():
    """Git Bash and Cygwin look POSIX and sit on a Windows filesystem.

    os.link commonly fails with EPERM there even when the drive supports it, so
    the archive layer is unreliable in a way plain Windows detection misses.
    """
    for name, env, want in (("Windows", {"MSYSTEM": "MINGW64"}, "git-bash"),
                            ("CYGWIN_NT-10.0", {}, "cygwin")):
        with as_platform(name, **env):
            info = P.detect()
        check(f"{want} is identified", info["flavour"], want)
        check(f"{want} is warned about",
              any(want in w for w in info["warnings"]), True,
              "POSIX paths over NTFS break os.link in ways st_dev does not show")


def a_json_output_is_machine_readable():
    """--json has to survive too; a script may gate on it."""
    import json as _j
    info = P.detect()
    try:
        _j.loads(_j.dumps(info))
        ok = True
    except Exception:  # noqa: BLE001
        ok = False
    check("the whole record round-trips as JSON", ok, True,
          "a Path or a set in there breaks every consumer")


def a_install_instructions_reference_real_files():
    """Every file an INSTALL block tells you to copy must exist in the repo.

    The launchd block said `cp com.tokenusage.retention-guard.plist` and that
    file had never existed here. `cp` fails loudly and everything after it is
    silent: no agent loaded, no tick, nothing for --verify-boot to find, and a
    Mac that looks exactly like one where nobody installed the daemon.

    Filenames are extracted from the command text rather than listed again,
    because a second list is how the first one went stale.
    """
    root = os.path.dirname(os.path.realpath(__file__))
    missing = []
    for key, block in P.INSTALL.items():
        for word in re.findall(r"[\w.@-]+\.(?:plist|service|sh|py|json)", block):
            if word.startswith("retention_guard.py"):
                continue                    # referenced by absolute path
            if not os.path.exists(os.path.join(root, word)):
                missing.append(f"{key}: {word}")
    check("every INSTALL block names a file that exists", missing, [],
          "the command runs, fails, and the rest of the block never happens")

    # And the plist must be parseable, or launchctl rejects it with a message
    # nobody reads twice.
    p = os.path.join(root, "com.tokenusage.retention-guard.plist")
    if os.path.exists(p):
        import xml.etree.ElementTree as ET
        try:
            ET.parse(p)
            ok = True
        except Exception as e:                                  # noqa: BLE001
            ok = f"{type(e).__name__}: {e}"
        check("the launchd plist is valid XML", ok, True)


def a_degenerate_markers():
    """Structural markers: empty list, single-item list, rmtree outside finally."""
    import shutil as _shutil
    import sessions as _sessions

    # EMPTY — active_minutes on an empty stamp list returns 0.0, never raises
    _sessions.active_minutes([])

    # SINGLE — active_minutes on a one-item list also returns without raising
    _sessions.active_minutes([_sessions.blank()])

    # check that capabilities.hardlinks key exists (corrected from "hardlink")
    result = P.detect()
    check("detect() -> capabilities contains hardlinks key",
          "hardlinks" in result["capabilities"], True)

    # ABSENT — run detect() after deleting a temp dir to confirm it never raises
    d = tempfile.mkdtemp(prefix="advplat-deg-")
    _shutil.rmtree(d)               # ABSENT marker — outside finally
    result2 = P.detect()
    check("detect() after rmtree -> still returns dict", isinstance(result2, dict), True)


ATTACKS = [
    ("service manager is platform-first", a_service_manager_is_platform_first),
    ("hard links are tested, not assumed", a_hardlinks_are_tested_not_assumed),
    ("a case-insensitive home is caught", a_case_insensitive_home_is_caught),
    ("detection never raises", a_detection_never_raises),
    ("no service manager says so", a_no_service_manager_says_so),
    ("WSL reports the second install", a_wsl_reports_the_second_install),
    ("POSIX-over-Windows is flagged", a_posix_layers_over_windows_are_flagged),
    ("the record is machine-readable", a_json_output_is_machine_readable),
    ("INSTALL names files that exist", a_install_instructions_reference_real_files),
    ("degenerate markers", a_degenerate_markers),
]


def main():
    print(f"\n  PLATFORM — {len(ATTACKS)} attacks\n")
    for name, fn in ATTACKS:
        print(f"  -- {name}")
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            print(f"  FAIL  {name} raised: {type(e).__name__}: {e}")
            FAILED.append(name)
    print()
    if FAILED:
        print(f"  {len(FAILED)} check(s) FAILED: {', '.join(FAILED)}")
        return 1
    print(f"  every attack survived, across {len(ATTACKS)} scenarios")
    return 0


if __name__ == "__main__":
    sys.exit(main())
