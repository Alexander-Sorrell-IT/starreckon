#!/usr/bin/env python3
"""One command to make a computer ready to be measured.

    python3 install.py            show what WOULD happen, change nothing
    python3 install.py --apply    do it
    python3 install.py --verify   check an existing install, change nothing

WHY THIS EXISTS AND WHY IT RUNS FIRST

The README described this as six numbered steps and every machine did them by
hand, in a different order, on a different day. Two of the six are ordered for a
reason nobody could see from the prose, and getting them backwards costs data
that cannot be recovered:

  * PROTECT BEFORE YOU MEASURE. Claude Code deletes transcripts at STARTUP, on
    cleanupPeriodDays. Raising that setting after a scan is too late for whatever
    the last launch already took. The archive holds 3,757 inodes against 1,171
    live on this machine -- roughly 2,586 conversations that exist in NO live
    profile and survive only because a hard link kept the inode alive.
  * GET THE CURRENT CODE FIRST. An older corpus_ship uploaded empty archives
    over other machines' real ones.

So this program does them in the order that is safe, and says which ones it did.

THE RULE THIS FILE IS WRITTEN UNDER

An installer is the easiest place in a system to ship a silent half-success: a
step that could not run looks exactly like a step that had nothing to do, and
the summary says "ready" either way. That is the defect this repository has
shipped seven times in four disguises, so every step here returns one of

    DONE      it happened, and here is what changed
    ALREADY   it was already true, verified, not assumed
    SKIPPED   deliberately not done, with the reason
    FAILED    it should have happened and did not

and a run containing any FAILED exits non-zero. There is no fifth state, and in
particular there is no state that means "probably fine".
"""

import argparse
import json
import os
import pathlib
import platform
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from platform_detect import real_home   # noqa: E402
HOME = real_home()

# How long Claude Code keeps a transcript before deleting it at launch. The
# default is 30 days. This is the single highest-value setting on the machine:
# every conversation older than it is gone from the live profile, and the hard
# link archive is the only reason any of them still exist.
RETENTION_DAYS = 999999

DONE, ALREADY, SKIPPED, FAILED = "DONE", "ALREADY", "SKIPPED", "FAILED"

results = []


def step(name, state, detail=""):
    results.append((name, state, detail))
    mark = {DONE: "+", ALREADY: "=", SKIPPED: "-", FAILED: "!"}[state]
    print(f"  {mark} {name:44} {state:8} {detail}")
    return state


# ----------------------------------------------------------------- machine folder

def _probe_machine(pi):
    """Ask the OS who and what this machine is.  Works on Linux, macOS, Windows.

    Returns a dict with the raw answers.  _suggest_folder() turns them into a
    slug.  Kept separate so the answers can be printed for the operator to see
    before the slug is accepted.

    WHY THIS IS PROBED, NOT ASSUMED
    Three things would give you a wrong slug if inferred rather than measured:

      chassis     A hostname like 'DESKTOP-ABC123' (Windows default) says
                  nothing about the hardware. The DMI chassis type says laptop
                  or desktop without any guessing.

      OS user     On a shared machine or inside a container, the user running
                  this script may not be the one who owns the AI CLI data.
                  getpass.getuser() is the OS answer; platform.node() is not.

      arch        arm64 vs x86_64 matters for the fleet: the MacBook Air M1
                  folder is named 'macbook-air-m1', not 'macbook-air-linux'.
                  platform.machine() gives the right answer on every platform.

    EVERY SUB-PROBE IS GUARDED INDIVIDUALLY. This runs before every step in
    install.py. If it raises, nothing runs — not the retention period raise,
    not the daemon write. A probe that cannot answer must return a safe
    fallback, not take the whole run down.
    """
    import getpass

    def _safe(fn, default):
        try:
            return fn()
        except Exception:   # noqa: BLE001
            return default

    sys_name = pi.get("system") or _safe(lambda: platform.system().lower(), "linux")
    result = {
        "os_user":      _safe(lambda: getpass.getuser(), "user"),
        "hostname":     _safe(lambda: platform.node(), "unknown"),
        "system":       sys_name,
        "is_wsl":       pi.get("is_wsl", False),
        "arch":         _safe(lambda: platform.machine().lower(), ""),
        "chassis":      _safe(lambda: _probe_chassis(sys_name), None),
        # hardware_uuid() is called here so the result is available to
        # _suggest_folder() without a second probe. It is defined below
        # _probe_machine() in the file, so the call is deferred through
        # a lambda to avoid a forward-reference at module load time.
        "hardware_uuid": _safe(lambda: hardware_uuid(), None),
    }
    return result


# Chassis types from DMI spec (Linux /sys/class/dmi/id/chassis_type) and
# their human labels.  macOS and Windows use different sources; see
# _probe_chassis().  The mapping covers the values observed on real hardware;
# anything unrecognised falls back to None (omitted from the slug).
_CHASSIS_TYPES = {
    # DMI integers (Linux, Windows WMI)
    "3":  "desktop", "4":  "desktop", "5":  "desktop", "6":  "desktop",
    "7":  "desktop", "8":  "laptop",  "9":  "laptop",  "10": "laptop",
    "14": "laptop",  "30": "tablet",  "31": "convertible",
    "11": "handheld","17": "server",  "23": "server",
    # macOS model strings
    "macbookpro": "laptop", "macbookair": "laptop", "macbook": "laptop",
    "imac": "desktop", "macpro": "desktop", "macmini": "desktop",
    "macstudio": "desktop",
}


def _probe_chassis(system):
    """Best-effort chassis type: 'laptop' | 'desktop' | 'server' | None.

    None means unknown — omitted from the slug rather than guessed wrong.
    A wrong chassis label (calling a desktop a laptop) is worse than no label
    because it becomes permanent once the folder is committed.
    """
    if system in ("linux", "wsl"):
        try:
            ct = pathlib.Path("/sys/class/dmi/id/chassis_type").read_text().strip()
            return _CHASSIS_TYPES.get(ct)
        except OSError:
            pass
        # Fallback: battery presence is a reliable laptop signal on Linux.
        try:
            bats = list(pathlib.Path("/sys/class/power_supply").iterdir())
            if any("BAT" in b.name.upper() for b in bats):
                return "laptop"
        except OSError:
            pass
        return None

    if system == "macos":
        try:
            r = subprocess.run(["sysctl", "-n", "hw.model"],
                               capture_output=True, text=True, timeout=5)
            model = r.stdout.strip().lower().replace(" ", "")
            for key, chassis in _CHASSIS_TYPES.items():
                if model.startswith(key):
                    return chassis
        except OSError:
            pass
        return None

    if system == "windows":
        try:
            r = subprocess.run(
                ["wmic", "computersystem", "get", "PCSystemType", "/value"],
                capture_output=True, text=True, timeout=8, shell=True)
            # PCSystemType=2 = mobile (laptop), 1 = desktop, 4 = server
            for line in r.stdout.splitlines():
                if line.startswith("PCSystemType="):
                    v = line.split("=", 1)[1].strip()
                    return {"1": "desktop", "2": "laptop", "4": "server"}.get(v)
        except OSError:
            pass
        return None

    return None


def hardware_uuid():
    """Read the hardware UUID for this machine. Returns a string or None.

    THE UUID IS THE IDENTITY ANCHOR. The folder name describes the machine
    (user + chassis + OS + short suffix); the UUID proves it. Two machines
    that produce the same derived name are disambiguated by their UUIDs, and
    a machine that is reinstalled keeps its folder because the UUID survives
    the reinstall.

    OS-SPECIFIC, NOT OS-INDEPENDENT. Linux on a machine and macOS on the
    same machine return different UUIDs from their respective OS facilities —
    /etc/machine-id on Linux is regenerated on install, while macOS reads
    the IOPlatformUUID which is hardware-bound. That asymmetry is correct:
    a dual-boot machine running both OSes has two independent token histories
    and they should live in two separate folders.

    EVERY PROBE IS GUARDED. A UUID probe that raises must return None, not
    crash install.py. Missing UUID is handled gracefully downstream.
    """
    def _safe(fn):
        try:
            return fn()
        except Exception:   # noqa: BLE001
            return None

    system = platform.system().lower()

    if system == "darwin":
        # IOPlatformUUID: hardware-bound, survives OS reinstall on the same
        # physical board. Available since the first Mac OS X release.
        def _mac():
            r = subprocess.run(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                capture_output=True, text=True, timeout=10)
            for line in r.stdout.splitlines():
                if "IOPlatformUUID" in line:
                    # Format: "IOPlatformUUID" = "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        return parts[1].strip().strip('"')
            return None
        return _safe(_mac)

    if system == "linux":
        # /etc/machine-id: generated at OS install, stable across reboots.
        # Different from the hardware UUID — it tracks the OS install, not
        # the hardware, which is exactly right: reinstall = new identity.
        def _linux():
            mid = pathlib.Path("/etc/machine-id")
            if mid.is_file():
                v = mid.read_text(encoding="utf-8").strip()
                if v and len(v) >= 16:
                    # Format as UUID for consistency: 8-4-4-4-12
                    h = v.replace("-", "").lower()
                    if len(h) >= 32:
                        return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"
                    return h
            # DMI fallback for containers / WSL
            dmi = pathlib.Path("/sys/class/dmi/id/product_uuid")
            if dmi.is_file():
                return _safe(lambda: dmi.read_text(encoding="utf-8").strip())
            return None
        return _safe(_linux)

    if system == "windows":
        def _win():
            r = subprocess.run(
                ["wmic", "csproduct", "get", "UUID", "/value"],
                capture_output=True, text=True, timeout=10, shell=True)
            for line in r.stdout.splitlines():
                if line.startswith("UUID="):
                    v = line.split("=", 1)[1].strip()
                    if v and v not in ("", "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF"):
                        return v
            return None
        return _safe(_win)

    return None


def _arch_tag(arch):
    """Normalise arch to the short tag used in folder names."""
    arch = arch.lower()
    if arch in ("arm64", "aarch64"):
        return "m1"     # matches existing 'macbook-air-m1' convention
    # x86_64, amd64, i686, i386 all mean "intel/amd x86" — no tag needed,
    # since that is the default and adding it would just be noise.
    return None


def _suggest_folder(pi):
    """Derive the folder slug by asking the machine, not by stripping the hostname.

    FIVE COMPONENTS, IN ORDER:
      1. OS user — the person running this; disambiguates shared machines
      2. chassis (laptop / desktop / server) — the hardware class
      3. arch — only appended when it is distinctive (arm = 'm1', x86 = nothing)
      4. OS (linux / macos / windows / wsl) — always present, always last
      5. UUID suffix — first 4 hex chars of the hardware UUID; makes the name
         collision-proof even when all four descriptive components are identical

    The hostname is NOT used. Hostnames change on rename, are auto-generated
    on many platforms (DESKTOP-ABC123), and carry no machine-type information.
    The five components above are stable, readable, and self-describing.

    Examples:
      phantomcore-laptop-linux-a3f7
      alex-laptop-m1-darwin-0b2c
      alex-desktop-linux-c91e

    NOT RANDOM, NOT FROM A FILE. Deterministic from the machine itself, so
    running install.py twice gives the same slug, and the operator can verify
    it before --apply commits it to machines.json.
    """
    try:
        probe = _probe_machine(pi)
    except Exception:   # noqa: BLE001
        probe = {}

    # OS tag — always present
    os_tag = probe.get("system") or pi.get("system") or "linux"
    if os_tag == "linux" and probe.get("is_wsl"):
        os_tag = "wsl"

    # User slug — lowercased OS username, hyphens preserved as separators,
    # other non-alphanumeric symbols stripped; "user" if blank.
    # Hyphens in the username (e.g. "broodierchip-m1air") become natural
    # slug separators rather than being collapsed into the adjacent text.
    raw_user = probe.get("os_user") or ""
    user = re.sub(r'[^a-z0-9-]', '', raw_user.lower()).strip('-') or "user"

    # Chassis
    chassis = probe.get("chassis")  # laptop | desktop | server | None

    # Arch tag — only when it distinguishes (arm/M1)
    arch = _arch_tag(probe.get("arch") or "")

    # UUID suffix — first 4 hex chars; collision-proof disambiguator
    uuid = probe.get("hardware_uuid") or hardware_uuid() or ""
    suffix = re.sub(r'[^0-9a-f]', '', uuid.lower())[:4] or None

    # Build: <user>-<chassis>-<arch>-<os>-<uuid4>  omitting None parts
    parts = [user]
    if chassis:
        parts.append(chassis)
    if arch:
        parts.append(arch)
    parts.append(os_tag)
    if suffix:
        parts.append(suffix)
    return "-".join(parts)


def _machines_json():
    """Load machines.json, or return an empty structure."""
    p = ROOT / "machines.json"
    if not p.is_file():
        return {"machines": []}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"machines": []}


def _save_machines_json(doc):
    p = ROOT / "machines.json"
    tmp = p.with_suffix(".json.installtmp")
    tmp.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    tmp.replace(p)


def _claimed_folder():
    """The folder this machine already owns, by .machine-id, or None.

    UUID is the primary anchor — it survives OS reinstalls and hostname changes.
    Hostname is the fallback for machines enrolled before UUID tracking was added.
    Hostname comparison is case-insensitive: the machine wrote 'HP-Phantom-Core'
    and platform.node() may return a different case across reboots.
    """
    uuid = hardware_uuid()
    host = platform.node().lower()
    hostname_match = None
    for d in sorted(ROOT.iterdir()):
        if not d.is_dir():
            continue
        mid = d / ".machine-id"
        if not mid.is_file():
            continue
        try:
            info = json.loads(mid.read_text(encoding="utf-8"))
            # UUID match — definitive; stops searching immediately
            stored_uuid = info.get("hardware_uuid")
            if uuid and stored_uuid and stored_uuid.lower() == uuid.lower():
                return d.name
            # Hostname match — fallback for pre-UUID installs
            if info.get("hostname", "").lower() == host:
                hostname_match = d.name
        except (OSError, ValueError, KeyError):
            continue
    return hostname_match


def machine_folder(apply_it, pi, folder_override=None):
    """Suggest (and optionally register) this machine's folder in machines.json.

    WHY MACHINES.JSON MATTERS FOR A NEW COMPUTER

    combine.py generates the fleet rollup from machine folders that exist on
    disk. A machine that has been scanned appears automatically. One that has
    NOT been scanned yet -- because we are setting it up right now -- would be
    completely invisible: not reported as missing, not counted in "N of M
    scanned", just absent. machines.json makes the gap visible instead.

    Registering here means that from the moment install.py runs, the fleet
    report shows this computer as "not yet scanned" rather than not mentioning
    it at all.

    THE FOLDER NAME IS A COMMITMENT. It becomes the directory name in both
    repos and cannot be renamed without a git history surgery. The suggested
    name is shown in --check so the operator can accept or override it with
    --machine before --apply commits it.

    CHECKS .machine-id FIRST. run.py update writes that file when it scans a
    machine. If this hostname already owns a folder that way, creating a new
    entry would produce a duplicate identity -- two folder names, one host,
    and combine.py would report both, one of them always empty.
    """
    # Check whether this machine already has a folder via .machine-id.
    claimed = _claimed_folder()
    if claimed:
        return step("machine folder in machines.json", ALREADY,
                    f"{claimed} (this host owns that folder — "
                    f"run: python3 run.py update --machine {claimed})")

    doc = _machines_json()
    existing = {m["folder"] for m in doc.get("machines", [])}

    if folder_override:
        suggested = folder_override.lower().strip()
        suggested = re.sub(r'[^a-z0-9-]', '-', suggested)
        suggested = re.sub(r'-+', '-', suggested).strip('-') or "unknown"
    else:
        suggested = _suggest_folder(pi)

    if suggested in existing:
        return step("machine folder in machines.json", ALREADY,
                    f"{suggested} (already listed — "
                    f"run: python3 run.py update --machine {suggested})")

    if not apply_it:
        return step("machine folder in machines.json", SKIPPED,
                    f"would add {suggested!r} — re-run with --apply to register it")

    label = " ".join(w.capitalize() for w in suggested.replace("-", " ").split())
    doc.setdefault("machines", []).append({"folder": suggested, "label": label})
    try:
        _save_machines_json(doc)
    except OSError as e:
        return step("machine folder in machines.json", FAILED, str(e))
    return step("machine folder in machines.json", DONE,
                f"added {suggested!r} to machines.json — "
                f"next: python3 run.py update --machine {suggested}")


# ----------------------------------------------------------------- daemon verify

def _daemon_running(sysname):
    """Is the retention-guard daemon actually running right now?

    WRITTEN IS NOT RUNNING. install.py writes the service artifact; enabling it
    is left to the operator. This checks whether the enable step was done and
    the daemon is live, which is the only state worth being in: a service file
    that exists but is not running protects nothing, and it looks identical to
    one that is -- both show ALREADY on the artifact check.

    Returns (running: bool | None, detail: str).
    None means UNKNOWN -- the check could not run.
    """
    if sysname == "Linux":
        r = subprocess.run(
            ["systemctl", "--user", "is-active", "retention-guard.service"],
            capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip() == "active":
            return True, "active"
        if r.returncode == 4:
            return False, "unit not found -- was it enabled?"
        return False, r.stdout.strip() or "not active"
    if sysname == "Darwin":
        r = subprocess.run(
            ["launchctl", "list", "com.deadreckon.retention-guard"],
            capture_output=True, text=True)
        if r.returncode == 0:
            return True, "loaded"
        return False, "not loaded"
    if sysname == "Windows":
        r = subprocess.run(
            ["schtasks", "/query", "/tn", "deadreckon-retention-guard", "/fo", "list"],
            capture_output=True, text=True, shell=True)
        if r.returncode == 0 and "Running" in r.stdout:
            return True, "running"
        if r.returncode == 0:
            return False, "task exists but not running"
        return False, "task not found"
    return None, f"no check for platform {sysname!r}"


def daemon_running_check():
    """Verify the daemon is actually up, not just that the artifact was written.

    --verify runs this; --apply skips it (the service was just written, not
    enabled yet, and checking immediately would always fail).
    """
    sysname = platform.system()
    running, detail = _daemon_running(sysname)
    if running is None:
        return step("daemon is running", SKIPPED, detail)
    if running:
        return step("daemon is running", ALREADY, detail)
    return step("daemon is running", FAILED,
                f"{detail} -- enable it with the command printed above, "
                f"then re-run python3 install.py --verify")


# ----------------------------------------------------------------- CLI / store scan

def cli_scan():
    """Report which AI CLIs are installed on this machine.

    A NEW COMPUTER RUNNING INSTALL.PY HAS NEVER BEEN SCANNED. The operator
    cannot tell which CLIs are present -- and more importantly, which CLIs have
    transcripts that need protecting -- without this. It is advisory: finding a
    CLI here is not a prerequisite for anything, and NOT finding one is not a
    failure. The value is making "what is on this machine" visible BEFORE the
    first scan, rather than after.

    Uses stores.scan() rather than a hand-rolled check so the answer is the same
    one the scanner will use -- the definition in one place principle.

    INSTALLED / ABSENT / UNREADABLE mirrors stores.state() exactly. UNREADABLE
    is the third state that answers "it is there but the process cannot see it",
    which is common on macOS where TCC blocks background processes from reaching
    Desktop and Documents even when those directories stat fine.
    """
    print("\n  AI CLI stores on this machine")
    print(f"  {'store':<28} {'state':<12} note")
    try:
        import stores as _stores
        scanned = _stores.scan()
        installed = [(k, v) for k, v in scanned.items()
                     if v["state"] == _stores.INSTALLED]
        absent = [(k, v) for k, v in scanned.items()
                  if v["state"] == _stores.ABSENT]
        unreadable = [(k, v) for k, v in scanned.items()
                      if v["state"] == _stores.UNREADABLE]

        for label, info in sorted(installed):
            s = _stores.STORES
            st = next((x for x in s if x.label == label), None)
            cli = (st.cli or "—") if st else "—"
            print(f"  {'  ' + label:<28} {'INSTALLED':<12} reader: {cli}")

        for label, info in sorted(unreadable):
            blocked = info.get("blocked", [])
            err = f"errno {blocked[0][1]}" if blocked else "unreadable"
            print(f"  {'  ' + label:<28} {'UNREADABLE':<12} {err}")

        counts = _stores.counts(scanned)
        print(f"\n  {counts[_stores.INSTALLED]} installed, "
              f"{counts[_stores.UNREADABLE]} unreadable, "
              f"{counts[_stores.ABSENT]} absent")
        if not installed:
            print("  No AI CLI stores found. If CLIs are installed, check paths "
                  "with: python3 stores.py")
    except Exception as e:  # noqa: BLE001
        print(f"  (store scan skipped: {e})")


def claude_profiles():
    """Every Claude config directory, found by SHAPE and not by a name glob.

    `ls -d ~/.claude*` misses ~/.my-claude, which holds 130 files. A glob rooted
    on the dotfile name can only find the spellings somebody thought of; a
    search for the thing a profile actually IS -- a directory containing
    projects/ -- finds the ones nobody wrote down. Five of them live here and
    CLAUDE_CONFIG_DIR can put the next one anywhere.
    """
    seen, out = set(), []
    for c in list(HOME.glob(".*claude*")) + list(HOME.glob("*claude*")):
        if c.is_dir() and (c / "projects").is_dir():
            r = c.resolve()
            if r not in seen:
                seen.add(r)
                out.append(c)
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    if env:
        p = pathlib.Path(env).expanduser()
        if p.is_dir() and p.resolve() not in seen:
            out.append(p)
    return sorted(out)


def protect(apply_it):
    """Raise cleanupPeriodDays in every profile. FIRST, before anything else."""
    profs = claude_profiles()
    if not profs:
        # Not "nothing to do" -- nothing FOUND. On a machine that runs Claude
        # those are different facts and only one of them is good news.
        return step("protect transcripts from cleanup", SKIPPED,
                    "no Claude profile found on this machine")
    changed, already, failed = [], [], []
    for prof in profs:
        s = prof / "settings.json"
        try:
            cfg = json.loads(s.read_text(encoding="utf-8")) if s.is_file() else {}
        except (OSError, ValueError) as e:
            failed.append(f"{prof.name}: {e}")
            continue
        if cfg.get("cleanupPeriodDays") == RETENTION_DAYS:
            already.append(prof.name)
            continue
        if not apply_it:
            changed.append(prof.name)
            continue
        cfg["cleanupPeriodDays"] = RETENTION_DAYS
        try:
            s.parent.mkdir(parents=True, exist_ok=True)
            tmp = s.with_suffix(".json.installtmp")
            tmp.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
            tmp.replace(s)          # atomic: never a half-written settings.json
            changed.append(prof.name)
        except OSError as e:
            failed.append(f"{prof.name}: {e}")
    if failed:
        return step("protect transcripts from cleanup", FAILED, "; ".join(failed))
    if changed:
        return step("protect transcripts from cleanup",
                    DONE if apply_it else SKIPPED,
                    f"{'set' if apply_it else 'would set'} {RETENTION_DAYS} on "
                    + ", ".join(changed))
    return step("protect transcripts from cleanup", ALREADY,
                f"{len(already)} profile(s) already at {RETENTION_DAYS}")


def unprotected_now(max_age_h=13.0):
    """Transcripts unlinked for LONGER THAN ONE TICK. Not merely unlinked.

    The first version of this asserted zero unlinked files and it was wrong in a
    way worth keeping written down. A transcript written thirty seconds ago has
    exactly one name until the belt next runs, so on a machine anybody actually
    uses the count is never zero and the check fails on every run forever. A
    check that always fails is ignored on exactly the same schedule as one that
    always passes, and this repository has now produced both.

    Measured here across one session: 52, then 58, then 16 -- the belt ticked in
    between and linked forty-odd files. The number is a GAUGE, not a constant,
    and the only thing worth alarming on is a file that has been exposed longer
    than the belt's own period.

    max_age_h is 13 rather than the configured 6 because the daemon's period is
    a time.sleep(21600) and sleep does not advance across suspend: the real gaps
    measured on this machine were 12h43m and 11h07m. Alarming at 6 would fire on
    every laptop that spent a night closed. This threshold is therefore a
    statement about the CURRENT daemon, and when the interval is fixed to use
    wall-clock deadlines this number should come down with it.
    """
    import time
    now, exposed, recent = time.time(), [], 0
    for prof in claude_profiles():
        for f in (prof / "projects").rglob("*.jsonl"):
            try:
                st = f.stat()
            except OSError:
                continue
            if st.st_nlink > 1:
                continue
            age_h = (now - st.st_mtime) / 3600.0
            if age_h > max_age_h:
                exposed.append((f, age_h))
            else:
                recent += 1
    return exposed, recent


def prereqs():
    have = {}
    for tool in ("git", "python3"):
        have[tool] = shutil.which(tool)
        step(f"prerequisite: {tool}", DONE if have[tool] else FAILED,
             have[tool] or "not on PATH")
    # 3.11 is OPTIONAL and only the forecaster needs it. Reported as SKIPPED
    # rather than FAILED so a machine without it still installs cleanly -- an
    # optional dependency that fails the run is how installers get ignored.
    p311 = shutil.which("python3.11") or ("/usr/bin/python3.11"
                                          if pathlib.Path("/usr/bin/python3.11").exists() else None)
    have["python3.11"] = p311
    step("prerequisite: python3.11 (forecaster only)",
         DONE if p311 else SKIPPED,
         p311 or "absent -- the forecast check will be unavailable here")
    return have


def daemon_artifact(apply_it):
    """WRITE the platform's service definition. Never enable it.

    Enabling is left to a human on purpose. An installer that starts a
    background job which reads every AI profile on the machine should be a
    decision somebody makes, not a side effect of running a setup script -- and
    the command is printed so it stays one step, not a research project.

    The audit that prompted this found the Windows half of the README describing
    a scheduled task that referenced no file at all, while the check meant to
    catch that derived filenames by regex from the prose: the block named
    nothing, so the check asserted nothing and printed PASS. Shipping a real
    artifact per platform is what makes that check able to fail.
    """
    sysname = platform.system()
    guard = ROOT / "retention_guard.py"
    if sysname == "Linux":
        target = HOME / ".config/systemd/user/retention-guard.service"
        body = f"""[Unit]
Description=deadreckon retention guard -- hard-link transcripts before the tool deletes them
Documentation={guard}

[Service]
Type=simple
ExecStart={sys.executable} {guard} --daemon
Restart=always
RestartSec=60

[Install]
WantedBy=default.target
"""
        enable = ("systemctl --user daemon-reload && "
                  "systemctl --user enable --now retention-guard.service && "
                  "loginctl enable-linger $USER")
    elif sysname == "Darwin":
        target = HOME / "Library/LaunchAgents/com.deadreckon.retention-guard.plist"
        body = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.deadreckon.retention-guard</string>
  <key>ProgramArguments</key>
  <array><string>{sys.executable}</string><string>{guard}</string><string>--daemon</string></array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardErrorPath</key><string>{HOME}/Library/Logs/deadreckon-retention.log</string>
</dict></plist>
"""
        enable = f"launchctl load -w {target}"
    elif sysname == "Windows":
        target = ROOT / "retention-guard.xml"
        body = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers><LogonTrigger><Enabled>true</Enabled></LogonTrigger></Triggers>
  <Settings><StartWhenAvailable>true</StartWhenAvailable>
    <RestartOnFailure><Interval>PT1M</Interval><Count>3</Count></RestartOnFailure></Settings>
  <Actions><Exec>
    <Command>{sys.executable}</Command>
    <Arguments>{guard} --daemon</Arguments>
  </Exec></Actions>
</Task>
"""
        enable = f'schtasks /Create /TN "deadreckon-retention-guard" /XML "{target}"'
    else:
        return step("daemon artifact", FAILED, f"no definition for platform {sysname!r}")

    if not guard.is_file():
        return step("daemon artifact", FAILED, f"{guard} does not exist")
    if target.is_file() and target.read_text(encoding="utf-8") == body:
        step("daemon artifact", ALREADY, str(target))
    elif apply_it:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        step("daemon artifact", DONE, str(target))
    else:
        step("daemon artifact", SKIPPED, f"would write {target}")
    print(f"\n    enable it yourself with:\n      {enable}\n")
    return None


# Where HuggingFace model weights are stored. Defaults to the standard HF cache
# (~/.cache/huggingface). Set DEADRECKON_MODEL_CACHE in the environment to keep
# all weights on a separate drive (e.g. an external SSD shared across machines).
# The same variable is read by forecast_check.py so both always agree.
def _hf_home():
    return os.environ.get("DEADRECKON_MODEL_CACHE",
                          str(HOME / ".cache" / "huggingface"))


def _download_model(py, repo_id, name):
    """Pre-pull a HuggingFace model into the local cache.

    WHY PRE-PULL RATHER THAN LAZY-LOAD

    forecast_check.py and search_corpus.py both set HF_HUB_OFFLINE=1 before
    importing the model library. That is correct for a running system — no
    network traffic on every inference — but it means the FIRST run after
    install fails with a missing-model error even though the venv and packages
    are fine. The install step is the right place to do the one-time download,
    because it is the only step that is expected to hit the network.

    Returns (state, detail) using the same DONE/ALREADY/FAILED vocabulary as
    every other install step.
    """
    # A model is present when its config.json exists under the cache.
    slug = repo_id.replace("/", "--")
    cache = pathlib.Path(_hf_home()) / "hub" / f"models--{slug}"
    if (cache / "snapshots").is_dir():
        return ALREADY, f"{repo_id} already in {_hf_home()}"
    try:
        env = dict(os.environ, HF_HOME=_hf_home(), HF_HUB_OFFLINE="0")
        subprocess.run(
            [str(py), "-c",
             f"from huggingface_hub import snapshot_download; "
             f"snapshot_download('{repo_id}')"],
            check=True, capture_output=True, timeout=3600, env=env)
        return DONE, f"{repo_id} downloaded to {_hf_home()}"
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as e:
        return FAILED, f"{repo_id}: {str(e)[:120]}"


def forecaster(apply_it, py311):
    """The optional CPU environment for the time-series check.

    Separate on purpose: cisco-tsm is pinned >=3.11,<3.12 and this repository
    runs on 3.12, so it CANNOT share the interpreter. Kept optional because a
    machine that cannot install it must still be able to scan -- the forecast is
    one extra sense, never a prerequisite for measuring anything.
    """
    venv = ROOT / ".venv-forecast"
    if not py311:
        return step("forecaster environment", SKIPPED, "python3.11 not present")
    venv_ok = (venv / "bin/python").exists() or (venv / "Scripts/python.exe").exists()
    if venv_ok and not apply_it:
        return step("forecaster environment", ALREADY, str(venv))
    if not venv_ok:
        if not apply_it:
            return step("forecaster environment", SKIPPED, f"would create {venv}")
        try:
            subprocess.run([py311, "-m", "venv", str(venv)], check=True,
                           capture_output=True, timeout=300)
            pip = (venv / "bin/pip") if (venv / "bin/pip").exists() else (venv / "Scripts/pip.exe")
            if platform.system() == "Darwin":
                torch_cmd = [str(pip), "install", "--quiet", "torch"]
            else:
                torch_cmd = [str(pip), "install", "--quiet", "torch",
                             "--extra-index-url", "https://download.pytorch.org/whl/cpu"]
            subprocess.run(torch_cmd, check=True, capture_output=True, timeout=3600)
            subprocess.run([str(pip), "install", "--quiet", "huggingface_hub"],
                           check=True, capture_output=True, timeout=3600)
            step("forecaster environment", DONE, str(venv))
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as e:
            return step("forecaster environment", FAILED, str(e)[:120])
    else:
        step("forecaster environment", ALREADY, str(venv))

    # Pre-download the model weights so HF_HUB_OFFLINE=1 works from first run.
    if apply_it:
        py = venv / "bin/python"
        state, detail = _download_model(py, "cisco-ai/cisco-time-series-model-1.0",
                                        "cisco-tsm")
        step("forecaster model weights", state, detail)
    return None


def search_corpus(apply_it):
    """The optional sentence-transformer environment for corpus search.

    Uses cisco-ai/SecureBERT2.0-biencoder (fast candidate retrieval) and
    cisco-ai/SecureBERT2.0-cross_encoder (precise reranking) to enable
    semantic search over exported transcripts in deadreckon-record.

    Runs on the standard interpreter (no version pin). Optional: a machine
    without it still scans and archives normally.
    """
    venv = ROOT / ".venv-search"
    py3 = shutil.which("python3") or shutil.which("python")
    if not py3:
        return step("search-corpus environment", SKIPPED, "no python3 on PATH")

    venv_ok = (venv / "bin/python").exists() or (venv / "Scripts/python.exe").exists()
    if venv_ok and not apply_it:
        return step("search-corpus environment", ALREADY, str(venv))
    if not venv_ok:
        if not apply_it:
            return step("search-corpus environment", SKIPPED, f"would create {venv}")
        try:
            subprocess.run([py3, "-m", "venv", str(venv)], check=True,
                           capture_output=True, timeout=300)
            pip = (venv / "bin/pip") if (venv / "bin/pip").exists() else (venv / "Scripts/pip.exe")
            subprocess.run([str(pip), "install", "--quiet",
                            "sentence-transformers", "huggingface_hub"],
                           check=True, capture_output=True, timeout=3600)
            step("search-corpus environment", DONE, str(venv))
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as e:
            return step("search-corpus environment", FAILED, str(e)[:120])
    else:
        step("search-corpus environment", ALREADY, str(venv))

    # Pre-download both models.
    if apply_it:
        py = venv / "bin/python"
        for repo_id in ("cisco-ai/SecureBERT2.0-biencoder",
                        "cisco-ai/SecureBERT2.0-cross_encoder"):
            name = repo_id.split("/")[1]
            state, detail = _download_model(py, repo_id, name)
            step(f"search model: {name}", state, detail)
    return None


def daemon_health(apply_it):
    """Check the daemon is running. If not, re-pull the repo and say so.

    TWO DISTINCT FAILURES, NOT ONE.

    A daemon that was never enabled needs the operator to run the enable
    command. A daemon that WAS running and stopped means something changed
    since install — an OS update reset the service, the repo moved, or the
    script drifted out of sync with what the service file points at.

    For the second case the most likely fix is a fresh pull: the service
    file references the script by absolute path, so a repo that was moved
    or re-cloned will have a stale path in the service artifact. Re-pulling
    does not help with a moved repo (the path is wrong regardless), but it
    is the right first step for a daemon that stopped working after an update.

    This runs as part of --verify only. --apply skips it because the daemon
    was just written, not yet enabled, and checking immediately always fails.
    """
    sysname = platform.system()
    running, detail = _daemon_running(sysname)
    if running is None:
        return step("daemon health", SKIPPED, detail)
    if running:
        return step("daemon health", ALREADY, f"running — {detail}")

    # Not running. Try a git pull so the service file and script stay in sync.
    if apply_it:
        try:
            r = subprocess.run(["git", "-C", str(ROOT), "pull", "--rebase",
                                 "--autostash"],
                               capture_output=True, text=True, timeout=120)
            pull_note = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
            pull_state = "re-pulled" if r.returncode == 0 else "pull failed"
        except (OSError, subprocess.TimeoutExpired) as e:
            pull_note = str(e)[:80]
            pull_state = "pull failed"
        return step("daemon health", FAILED,
                    f"NOT running ({detail}); {pull_state}: {pull_note} — "
                    f"re-enable with the command printed above")
    return step("daemon health", FAILED,
                f"NOT running ({detail}) — re-enable with the command printed above, "
                f"then re-run python3 install.py --verify")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", action="store_true", help="actually change things")
    ap.add_argument("--verify", action="store_true", help="check only, change nothing")
    ap.add_argument("--machine", metavar="FOLDER",
                    help="override the suggested machine folder name (letters, digits, hyphens)")
    ap.add_argument("--no-forecaster", action="store_true",
                    help="skip the optional time-series environment")
    args = ap.parse_args()
    apply_it = args.apply and not args.verify

    # Platform detection runs first, before anything else, so the right service
    # manager and store paths are known for all subsequent steps.
    try:
        import platform_detect
        pi = platform_detect.detect()
    except Exception as e:  # noqa: BLE001 - never block an install on this
        pi = {"system": platform.system().lower(), "is_wsl": False,
              "service_manager": None, "warnings": [],
              "capabilities": {}, "store_forms": []}
        print(f"  (platform detection failed: {e})\n")

    sysname = platform.system()
    print(f"\n{sysname} {platform.release()}  python {platform.python_version()}")
    print(f"  home  {HOME}")
    print(f"  repo  {ROOT}")
    fam = pi.get("family", "linux")
    forms = pi.get("store_forms") or []
    if forms:
        print(f"  tool data is looked for at: {', '.join(forms)}")
    svc = pi.get("service_manager")
    print(f"  service manager: {svc or 'NONE'}")
    for w in pi.get("warnings", []):
        print(f"  !! {w}")
    print()

    if not apply_it and not args.verify:
        print("  DRY RUN -- nothing will be changed. Re-run with --apply.\n")

    # ---- 0. Show what the machine probes returned, before any step runs ----
    #
    # The folder name is derived from these answers. Printing them here means
    # the operator can see "chassis=laptop, user=phantomcore" and confirm the
    # suggestion makes sense before --apply writes it to machines.json.
    # Printed unconditionally -- a correct reading seen and confirmed is
    # evidence; one that is assumed is not.
    try:
        probe = _probe_machine(pi)
        suggested = _suggest_folder(pi)
        uuid = probe.get("hardware_uuid") or "(unavailable)"
        print(f"  machine probe")
        print(f"    os user  : {probe['os_user']}")
        print(f"    hostname : {probe['hostname']}")
        print(f"    system   : {probe['system']}"
              + (" (WSL)" if probe['is_wsl'] else ""))
        print(f"    arch     : {probe['arch']}")
        print(f"    chassis  : {probe['chassis'] or '(unknown — omitted from slug)'}")
        print(f"    uuid     : {uuid}")
        print(f"    → folder : {suggested}")
        claimed = _claimed_folder()
        if claimed:
            print(f"      (already owns: {claimed})")
        elif suggested in {m['folder'] for m in _machines_json().get('machines', [])}:
            print(f"      (already in machines.json)")
        print()
    except Exception as e:  # noqa: BLE001
        print(f"  (machine probe failed: {e})\n")

    # ---- 1. PROTECT BEFORE YOU MEASURE (most important ordering constraint) ----
    protect(apply_it)

    # ---- 2. Prerequisites ----
    have = prereqs()

    # ---- 3. Machine folder -- register this computer in machines.json ----
    machine_folder(apply_it, pi, folder_override=args.machine)

    # ---- 4. Daemon artifact (written, not enabled) ----
    daemon_artifact(apply_it)

    # ---- 5. Forecaster (optional) ----
    if args.no_forecaster:
        step("forecaster environment", SKIPPED, "--no-forecaster")
        step("forecaster model weights", SKIPPED, "--no-forecaster")
    else:
        forecaster(apply_it, have.get("python3.11"))

    # ---- 5b. Search-corpus environment (optional) ----
    if args.no_forecaster:
        step("search-corpus environment", SKIPPED, "--no-forecaster")
        step("search model: SecureBERT2.0-biencoder", SKIPPED, "--no-forecaster")
        step("search model: SecureBERT2.0-cross_encoder", SKIPPED, "--no-forecaster")
    else:
        search_corpus(apply_it)

    # ---- 6. Transcript exposure check ----
    exposed, recent = unprotected_now()
    step("transcripts exposed longer than one tick",
         FAILED if exposed else DONE,
         (f"{len(exposed)} unlinked for over 13h, oldest {max(a for _f, a in exposed):.1f}h "
          f"-- the belt is not running" if exposed
          else f"none; {recent} written recently and awaiting the next tick"))

    # ---- 7. Daemon health: check running; if not, re-pull + report ----
    if args.verify:
        daemon_running_check()
        daemon_health(apply_it=True)
    elif apply_it:
        # --apply: daemon was just written, not yet enabled. Re-pull anyway
        # so the service file and the script are always in sync.
        daemon_health(apply_it=True)

    # ---- 8. CLI / store scan (informational, always) ----
    cli_scan()

    bad = [r for r in results if r[1] == FAILED]
    print(f"\n  {len(results)} step(s): "
          + ", ".join(f"{sum(1 for r in results if r[1] == s)} {s}"
                      for s in (DONE, ALREADY, SKIPPED, FAILED)))
    if bad:
        print("\n  FAILED:")
        for name, _s, detail in bad:
            print(f"    {name} -- {detail}")
        print("\n  This machine is NOT ready. Nothing above is a warning.")
        return 1

    # Suggest the next command, with the folder name filled in.
    doc = _machines_json()
    this_folder = None
    if args.machine:
        this_folder = args.machine
    else:
        suggested = _suggest_folder(pi)
        if suggested in {m["folder"] for m in doc.get("machines", [])}:
            this_folder = suggested
    if this_folder:
        print(f"\n  Ready. Next:  python3 run.py update --machine {this_folder}\n")
    else:
        print("\n  Ready. Next:  python3 run.py update\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
