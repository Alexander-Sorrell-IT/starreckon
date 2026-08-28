#!/usr/bin/env python3
"""What machine is this, actually. Run FIRST; everything else adapts to it.

    python3 platform_detect.py            what this computer is
    python3 platform_detect.py --json     the same, as data

WHY THIS RUNS BEFORE ANYTHING ELSE

Every other part of this system asks a platform question sooner or later — where
the home directory is, whether hard links work, whether there is a /proc, which
service manager exists, whether there is a SECOND operating system on the same
disk holding a second copy of every profile. Answering those one at a time,
inline, at the point each script happens to need them, is how a tool ends up
correct on the machine it was written on and quietly wrong everywhere else.

So it is answered once, first, out loud.

WINDOWS IS NOT ONE TARGET. IT IS FOUR.

    native + PowerShell   C:\\Users\\me      schtasks, no /proc, no fcntl
    native + CMD          same paths, different quoting rules entirely
    WSL                   /home/me         a LINUX kernel with /proc and fcntl,
                          AND /mnt/c/Users/me — a whole second install
    Git Bash / MSYS       /c/Users/me      POSIX-ish paths over a Windows FS,
                          os.link often fails with EPERM

A machine running Claude Code in PowerShell AND in WSL has TWO independent
installations, two settings.json files, two cleanupPeriodDays, and two sets of
transcripts. Protecting one does nothing for the other, and the side you are not
looking at is reliably the one holding more.

WHAT "STRONG" MEANS HERE

Not "which name does platform.system() return". These are CAPABILITY questions,
and each is answered by TRYING IT, not by inferring it from the OS name:

    hard links      make one in a temp dir and stat it. exFAT, FAT32, CIFS and
                    sshfs all report a normal st_dev and then refuse. The
                    archive is worthless on those and must say so.
    fcntl           import it. Present on WSL, absent on native Windows.
    /proc           read it. Present on WSL, absent on macOS and Windows.
    case sensitivity   write Aa and aA and see if there are two files. A
                    case-insensitive home merges two profiles into one.
    service manager    check the binary exists AND that the user instance is
                    reachable — systemctl exists inside a container where it
                    cannot do anything.

A capability that was inferred rather than tested is a capability nobody has
checked.
"""

import argparse
import json
import os
import pathlib
import platform
import shutil
import subprocess
import sys
import tempfile


def real_home():
    """The OS-level home directory for the current user, ignoring $HOME.

    WHY THIS EXISTS

    Some environments (bob, sandbox launchers, IDE integrations) override $HOME
    to a profile subdirectory for isolation.  pathlib.Path.home(),
    os.path.expanduser and getpass all read $HOME, so every caller that used
    those got the profile path instead of the real home — wrong directory for
    protecting transcripts, installing the daemon, or naming the machine folder.

    PLATFORM STRATEGY — capability-tested, not inferred from the OS name:

      macOS / Linux / WSL      pwd.getpwuid(os.getuid()).pw_dir
                               reads the OS password database directly; ignores
                               $HOME entirely.  Works inside WSL, Git Bash,
                               MSYS, Cygwin, and any sandboxed launcher that
                               overrides $HOME but does not fake the passwd db.

      Windows native           USERPROFILE — set by Windows at login, not
      (os.name == "nt")        inherited from a spawning process the way $HOME
                               is.  Falls back to HOMEDRIVE+HOMEPATH, then the
                               standard expanduser.

    FALLBACK

    If every method above fails the function returns pathlib.Path.home() —
    existing behaviour, never worse than before.  Every probe is individually
    guarded so a broken passwd entry or missing env var never crashes the caller.
    """
    # macOS, Linux, WSL, Git Bash / MSYS / Cygwin — anything with a POSIX uid
    if os.name != "nt":
        try:
            import pwd as _pwd
            entry = _pwd.getpwuid(os.getuid())
            if entry.pw_dir:
                return pathlib.Path(entry.pw_dir)
        except Exception:   # noqa: BLE001
            pass

    # Windows native — USERPROFILE is the authoritative answer, set by Windows
    # at login and not inherited from a parent process the way $HOME is.
    up = os.environ.get("USERPROFILE", "")
    if up:
        return pathlib.Path(up)

    # Older Windows fallback: HOMEDRIVE + HOMEPATH
    hd = os.environ.get("HOMEDRIVE", "")
    hp = os.environ.get("HOMEPATH", "")
    if hd or hp:
        return pathlib.Path(hd + hp)

    # Last resort — existing behaviour on any platform
    return pathlib.Path.home()


def _run(cmd, timeout=8):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:  # noqa: BLE001
        return ""


# --------------------------------------------------------------- the OS

def family(name=None, osname=None):
    """linux | macos | windows — which FOLDER LAYOUT this machine files under.

    NOT the same question as `system` below, and the difference is why it is
    its own function. `system` is which operating system this is; this is where
    a program's data goes, and WSL answers "linux" to it while holding a whole
    second Windows install that answers "windows". Four files were each making
    their own version of this mapping — stores.vscode_bases()'s darwin/nt
    branch, test_platform_paths.SHAPES, fleet_fixture.PLATFORM_ENV and
    detect()'s own — which is the shape this repository has already shipped a
    defect through four times.

    Takes EITHER spelling, because its two callers hold different ones:
    `sys.platform` gives "darwin"/"win32"/"linux" and `platform.system()` gives
    "Darwin"/"Windows"/"Linux"/"MINGW64_NT-10.0". Passing them in rather than
    reading them here is what lets `stores` ask about a platform it is
    PRETENDING to be — its shims rebind its own `sys` and `os`, and a function
    that read the real ones would answer about this Linux box instead and every
    macOS assertion in the fleet suite would pass without testing anything.

    linux is the fallback ON PURPOSE. A machine this does not recognise —
    FreeBSD, Solaris, something new — files under XDG, which is the POSIX
    answer; guessing macOS or Windows there would be strictly worse.
    """
    p = str(platform.system() if name is None else name).lower()
    n = str(os.name if osname is None else osname).lower()
    if p.startswith(("darwin", "macos")):
        return "macos"
    if n == "nt" or p.startswith(("win", "cygwin", "mingw", "msys")):
        return "windows"
    return "linux"


def _wsl():
    """WSL, and which version. A Linux kernel with a Windows host underneath.

    /proc/version carries "microsoft" on both WSL1 and WSL2; WSL2 additionally
    sets WSL_INTEROP. Detected from the kernel rather than from an environment
    variable alone, because env vars do not survive a service.
    """
    try:
        with open("/proc/version") as fh:
            v = fh.read().lower()
    except OSError:
        return None
    if "microsoft" not in v:
        return None
    if os.environ.get("WSL_INTEROP") or "wsl2" in v:
        return 2
    return 1


def _windows_flavour():
    """Native Windows, or a POSIX layer sitting on top of one."""
    s = platform.system()
    if s.startswith("CYGWIN"):
        return "cygwin"
    if s.startswith("MINGW") or s.startswith("MSYS"):
        return "msys"
    if s == "Windows":
        # Git Bash runs a native python but sets MSYSTEM.
        return "git-bash" if os.environ.get("MSYSTEM") else "native"
    return None


def _shell():
    """Which shell this is running under. It changes the install instructions.

    PowerShell and CMD quote differently enough that one set of copy-paste
    commands cannot serve both, so the tool has to know which it is talking to.
    """
    if os.environ.get("PSModulePath"):
        # Present in PowerShell on every platform, including pwsh on Linux.
        return "powershell"
    if os.environ.get("PROMPT") and os.name == "nt":
        return "cmd"
    sh = os.environ.get("SHELL") or ""
    if sh:
        return pathlib.PurePath(sh).name
    if os.name == "nt":
        return "cmd"
    return "unknown"


# ------------------------------------------------------- capabilities, TESTED

def _can_hardlink(where):
    """Try it. st_dev matching is NOT proof — exFAT and CIFS lie about this.

    Returns True / False / None, and None means UNTESTED. It used to return
    False when it could not even create a temp directory, which turns "I could
    not run the experiment" into "the answer is no" — and the caller then
    reports hardlinks NO and the archiver is told to give up on a filesystem
    that may well support them. `_case_sensitive` returns None on the identical
    condition, so two probes sitting side by side answered the same wall in
    opposite directions, and the branch that exists to say UNVERIFIED was dead.
    """
    try:
        d = tempfile.mkdtemp(dir=str(where))
    except OSError as e:
        return None, f"could not test: {e.strerror or e}"
    a, b = os.path.join(d, "a"), os.path.join(d, "b")
    try:
        with open(a, "w") as fh:
            fh.write("x")
        os.link(a, b)
        ok = os.stat(b).st_nlink == 2
        return ok, "" if ok else "link made but nlink != 2"
    except OSError as e:
        return False, f"{e.strerror or e}"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _case_sensitive(where):
    """A case-INsensitive home folds two profiles into one. macOS default."""
    try:
        d = tempfile.mkdtemp(dir=str(where))
    except OSError:
        return None
    try:
        open(os.path.join(d, "Aa"), "w").close()
        return not os.path.exists(os.path.join(d, "aA"))
    except OSError:
        return None
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _service_manager(system=None):
    """Which one is present AND usable, for THIS platform.

    The order has to be platform-first. Asking "is systemctl on PATH" and
    stopping there reported systemd for macOS, Windows, Git Bash and Cygwin
    alike when the branches were exercised — because systemctl was on the PATH
    of the machine doing the asking. A Mac with nix-installed systemctl would
    have been told to install a systemd unit that nothing will ever start.

    Presence is also not usability: inside a container systemctl exists and can
    do nothing, so the user instance is queried rather than assumed.
    """
    system = system or platform.system().lower()
    if system in ("darwin", "macos"):
        return "launchd" if shutil.which("launchctl") else None
    if system.startswith(("windows", "cygwin", "mingw", "msys")) or os.name == "nt":
        return "schtasks" if (os.name == "nt" or shutil.which("schtasks")) else None
    if shutil.which("systemctl"):
        if _run(["systemctl", "--user", "is-system-running"]) or \
           _run(["systemctl", "--user", "show", "-p", "Version"]):
            return "systemd"
        return "systemd (present but the user instance is unreachable)"
    if shutil.which("cron") or shutil.which("crontab"):
        return "cron"
    return None


def _windows_homes():
    """Windows-side home directories, seen from WSL. A second whole install."""
    import glob as _g
    out = []
    for drive in sorted(_g.glob("/mnt/[a-z]")):
        for user in sorted(_g.glob(os.path.join(drive, "Users", "*"))):
            if os.path.basename(user) in ("Public", "Default", "Default User",
                                          "All Users", "desktop.ini"):
                continue
            if os.path.isdir(user):
                out.append(user)
    return out


# --------------------------------------------------------------- the answer

def detect():
    sysname = platform.system()
    wsl = _wsl()
    home = real_home()

    if sysname == "Darwin":
        system, flavour = "macos", "native"
    elif sysname == "Linux":
        system = "linux"
        flavour = f"wsl{wsl}" if wsl else "native"
    elif _windows_flavour():
        system, flavour = "windows", _windows_flavour()
    else:
        system, flavour = sysname.lower() or "unknown", "unknown"

    # EVERY PROBE IS GUARDED INDIVIDUALLY, because this runs before anything
    # else and a raise here blocks a machine that was working fine.
    #
    # Caught by its own attack suite: with every probe broken at once, detect()
    # propagated a RuntimeError out of the service-manager check and took the
    # whole run down. A probe that cannot answer must return "unknown" — which
    # is a third answer, and the honest one — not remove the report.
    def probe(fn, default, *a):
        try:
            return fn(*a)
        except Exception:  # noqa: BLE001
            return default

    hardlink_ok, hardlink_why = probe(_can_hardlink, (None, "probe failed"), home)
    fam = probe(family, "linux", sysname, os.name)
    info = {
        "system": system,
        "flavour": flavour,
        "family": fam,
        # WHERE A TOOL'S FOLDER WOULD BE ON THIS MACHINE, printed by the thing
        # that runs first, so that "we found nothing" can be read against
        # "here is everywhere we looked". The forty-odd store paths this
        # repository scans were COLLECTED on one Linux box; a Windows or macOS
        # operator whose tools file somewhere else got an empty report and no
        # way to see why. Derived, so it cannot disagree with the resolver.
        "store_forms": probe(_store_forms, [], fam),
        "shell": _shell(),
        "os_release": platform.release(),
        "python": sys.version.split()[0],
        "home": str(home),
        "is_wsl": bool(wsl),
        "wsl_version": wsl,
        "service_manager": probe(_service_manager, None, system),
        "capabilities": {
            "proc": probe(os.path.isdir, None, "/proc"),
            "fcntl": probe(_has, None, "fcntl"),
            "hardlinks": hardlink_ok,
            "hardlinks_why": hardlink_why,
            "case_sensitive_home": probe(_case_sensitive, None, home),
            "symlinks": probe(_can_symlink, None, home),
        },
        "other_homes": [],
        "warnings": [],
    }

    # THE SECOND INSTALL. On WSL this is not a curiosity, it is half the data.
    if wsl:
        info["other_homes"] = probe(_windows_homes, [])
        if info["other_homes"]:
            info["warnings"].append(
                "WSL: the Windows side has its own AI CLI installs, its own "
                "settings.json and its own transcripts. Run the guard natively "
                "in PowerShell too — this side cannot protect that one.")
    if hardlink_ok is None:
        info["warnings"].append(
            "could not test hard links here — the archive layer is UNVERIFIED "
            "on this machine, which is not the same as working.")
    elif not hardlink_ok:
        info["warnings"].append(
            f"hard links do not work in {home} ({hardlink_why}). The archive "
            "layer cannot function here; raise cleanupPeriodDays and export the "
            "corpus more often instead.")
    if info["capabilities"]["case_sensitive_home"] is False:
        info["warnings"].append(
            "the home filesystem is case-INSENSITIVE, so .Claude and .claude "
            "are one directory. Profile discovery may merge two profiles.")
    if system == "windows" and flavour in ("msys", "git-bash", "cygwin"):
        info["warnings"].append(
            f"{flavour} presents POSIX paths over a Windows filesystem. os.link "
            "commonly fails with EPERM here even when the drive supports it.")
    if not info["service_manager"]:
        info["warnings"].append(
            "no service manager found — the daemon can only be run by hand, "
            "and will not survive a reboot.")
    return info


def _store_forms(fam):
    """The derived folder forms for `fam`, asked of the file that owns them.

    Imported HERE rather than at module scope for two reasons: stores.py
    imports this module for `family()`, so a top-level import back is a cycle;
    and this file runs first, on a machine where anything may be broken, so it
    must not fail to report the platform because a map it only quotes could not
    be loaded.
    """
    import stores
    return [f.replace("{tool}", "<tool>") for f in stores.tool_forms(fam)]


def _has(mod):
    try:
        __import__(mod)
        return True
    except Exception:  # noqa: BLE001
        return False


def _can_symlink(where):
    try:
        d = tempfile.mkdtemp(dir=str(where))
    except OSError:
        return False
    try:
        os.symlink(d, os.path.join(d, "l"))
        return True
    except OSError:
        return False
    finally:
        shutil.rmtree(d, ignore_errors=True)


INSTALL = {
    "systemd": """cp retention-guard.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now retention-guard.service
loginctl enable-linger "$USER" """,
    # sed first: launchd does not expand ~ or $HOME inside ProgramArguments, so
    # a copied plist with USERNAME still in it loads and then fails to exec,
    # which launchd reports only in its own log.
    "launchd": """sed "s|USERNAME|$USER|g" com.tokenusage.retention-guard.plist \\
  > ~/Library/LaunchAgents/com.tokenusage.retention-guard.plist
launchctl load ~/Library/LaunchAgents/com.tokenusage.retention-guard.plist
launchctl list | grep retention-guard""",
    "cron": """# no service manager — cron is the fallback. @reboot runs it once at boot.
( crontab -l 2>/dev/null; echo "@reboot python3 $PWD/retention_guard.py --daemon" ) | crontab -""",
    # One line, no continuation character. "^" continues a line in CMD and is
    # not a continuation in PowerShell, which is the shell `detect()` reports
    # for a Windows box — pasted there it ended the command early and the task
    # was created without its /tr, or not at all.
    "schtasks": """schtasks /create /tn "retention-guard" /sc onlogon """
                """/rl highest /tr "python C:\\path\\to\\retention_guard.py --daemon" """,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    info = detect()
    if a.json:
        json.dump(info, sys.stdout, indent=1)
        print()
        return 0 if not info["warnings"] else 1

    c = info["capabilities"]
    print(f"\n  {info['system']} / {info['flavour']}"
          f"   shell {info['shell']}   python {info['python']}")
    print(f"  home {info['home']}")
    if info["store_forms"]:
        print("  a tool's data is looked for at  "
              + ", ".join(info["store_forms"]))
    print()
    print(f"  {'capability':<22}{'':4}note")
    def row(k, v, note=""):
        mark = "yes" if v is True else ("no" if v is False else "?")
        print(f"  {k:<22}{mark:<4}{note}")
    row("hard links", c["hardlinks"], c["hardlinks_why"] or "the archive layer needs this")
    row("/proc", c["proc"], "--verify-boot needs this; absent on macOS/Windows")
    row("fcntl", c["fcntl"], "ledger locking; absent on native Windows")
    row("symlinks", c["symlinks"])
    row("case-sensitive home", c["case_sensitive_home"],
        "" if c["case_sensitive_home"] else "two profiles can merge into one")
    print()
    print(f"  service manager  {info['service_manager'] or 'NONE'}")
    if info["service_manager"]:
        key = info["service_manager"].split()[0]
        if key in INSTALL:
            print()
            for line in INSTALL[key].splitlines():
                print(f"    {line}")
    if info["other_homes"]:
        print()
        print(f"  A SECOND OPERATING SYSTEM IS PRESENT — {len(info['other_homes'])} "
              f"Windows home(s):")
        for h in info["other_homes"][:4]:
            print(f"    {h}")
    if info["warnings"]:
        print()
        for w in info["warnings"]:
            print(f"  !! {w}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
