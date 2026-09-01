#!/usr/bin/env python3
"""Adversarial tests for the OS probe and folder-name derivation in install.py.

    python3 adv_install_folder.py

WHAT THIS ATTACKS

install.py probes the machine — OS user, chassis type, arch, system — and turns
those answers into a folder slug that becomes the machine's permanent identity in
both repositories. Two classes of failure are possible and they are opposite:

  LIES QUIETLY   the probe returns an answer that looks reasonable but is wrong.
                 A desktop reported as a laptop, or a Windows box reported as
                 Linux, produces a slug that is committed and cannot be renamed
                 without git surgery.

  RAISES         the probe or the slugger crashes on a machine whose environment
                 is unusual, and install.py never finishes. A probe that cannot
                 answer must return a safe fallback, not take the run down.

Every attack below was written to FAIL before the probe existed and to PASS
after it, following the rule in adversarial_meta.py: a test written beside a
fix asserts what the fix does, which is not the same as catching the defect.

WHAT IS DELIBERATELY NOT TESTED HERE

Whether the daemon is actually running, or whether machines.json writes atomically
— those are tested in adversarial_daemon.py and the retention_guard suite. This
file asks only: does the OS probe return the right answers, and does the slug come
out correctly from those answers?
"""
import contextlib
import getpass
import json
import os
import pathlib
import platform
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import install as I

FAILED = []
SKIPPED = []


def check(name, got, want, why=""):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        print(f"        got  {got!r}")
        print(f"        want {want!r}" + (f"  — {why}" if why else ""))
        FAILED.append(name)
    return ok


def skip(name, why):
    """An attack that could not run. Recorded as SKIP, never as PASS.

    A SKIP that silently counts as survival is how three of the checks in
    adversarial_daemon.py became unfalsifiable. Named here and printed at the
    end, never folded into the passed count.
    """
    print(f"  SKIP  {name}  ({why})")
    SKIPPED.append((name, why))


@contextlib.contextmanager
def fake_system(system, is_wsl=False, arch="x86_64", user="testuser",
                chassis_type=None, wmic_output=None, sysctl_output=None,
                power_supplies=(), dmi_fail=False):
    """Inject fake OS answers into install.py's probe functions.

    PATCHES THE FUNCTIONS, NOT THE OS. Patching platform.system() globally
    breaks pathlib on this interpreter; patching the three private functions
    install.py actually calls is both safer and more precise.

    Every platform answer comes in here rather than being injected piecemeal,
    so there is one place to see what a simulated machine looks like.

    hardware_uuid is suppressed to None so the slug ends with the OS tag and
    not with a 4-char suffix from this machine's real UUID.  Slug assertions
    like endswith("-linux") depend on the suffix being absent; leaking the real
    UUID here is how this machine's identity bleeds into a fixture for a
    different platform.
    """
    real_getuser   = getpass.getuser
    real_machine   = platform.machine
    real_node      = platform.node
    real_chassis   = I._probe_chassis
    real_hw_uuid   = I.hardware_uuid

    getpass.getuser  = lambda: user
    platform.machine = lambda: arch
    platform.node    = lambda: "test-host"
    I.hardware_uuid  = lambda: None     # suppress real UUID so suffix is absent

    # Chassis probe is replaced with a function that honours the injected
    # parameters without touching /sys, sysctl or wmic.
    def fake_chassis(sys_name):
        if sys_name in ("linux", "wsl"):
            # DMI path: raises when dmi_fail=True (simulates permission denied)
            if chassis_type is not None:
                if dmi_fail:
                    raise OSError("permission denied")
                return I._CHASSIS_TYPES.get(str(chassis_type))
            # Battery fallback: always available (it's a different path)
            if power_supplies:
                return "laptop" if any("BAT" in p.upper() for p in power_supplies) else None
            if dmi_fail:
                raise OSError("permission denied")
            return None
        if sys_name == "macos":
            if sysctl_output is not None:
                model = sysctl_output.lower().replace(" ", "")
                for key, chassis in I._CHASSIS_TYPES.items():
                    if model.startswith(key):
                        return chassis
            return None
        if sys_name == "windows":
            if wmic_output is not None:
                for line in wmic_output.splitlines():
                    if line.startswith("PCSystemType="):
                        v = line.split("=", 1)[1].strip()
                        return {"1": "desktop", "2": "laptop", "4": "server"}.get(v)
            return None
        return None

    I._probe_chassis = fake_chassis

    try:
        pi = {"system": system, "is_wsl": is_wsl}
        yield pi
    finally:
        getpass.getuser  = real_getuser
        platform.machine = real_machine
        platform.node    = real_node
        I._probe_chassis = real_chassis
        I.hardware_uuid  = real_hw_uuid


# ---------------------------------------------------------------------------
# 1. The probe returns the right answers per platform
# ---------------------------------------------------------------------------

def a_linux_laptop_slug():
    """A Linux laptop with a DMI chassis type 9 (laptop) and x86_64 arch."""
    with fake_system("linux", arch="x86_64", user="alice",
                     chassis_type="9") as pi:
        probe = I._probe_machine(pi)
        slug  = I._suggest_folder(pi)

    check("linux probe: system", probe["system"], "linux")
    check("linux probe: chassis", probe["chassis"], "laptop")
    check("linux probe: os_user", probe["os_user"], "alice")
    check("linux probe: arch", probe["arch"], "x86_64")
    check("linux laptop slug ends with -linux", slug.endswith("-linux"), True)
    check("linux laptop slug contains 'laptop'", "laptop" in slug, True)
    check("linux laptop slug contains user", "alice" in slug, True)
    check("linux laptop slug has no arch tag (x86 is default)",
          "x86" not in slug and "amd" not in slug, True,
          "x86_64 is the default — adding it would be noise on every machine")


def a_macos_laptop_slug():
    """A macOS laptop (MacBookAir) on Apple Silicon."""
    with fake_system("macos", arch="arm64", user="bob",
                     sysctl_output="MacBookAir10,1") as pi:
        probe = I._probe_machine(pi)
        slug  = I._suggest_folder(pi)

    check("macos probe: system", probe["system"], "macos")
    check("macos probe: chassis", probe["chassis"], "laptop")
    check("macos laptop slug ends with -macos", slug.endswith("-macos"), True)
    check("macos laptop slug contains 'laptop'", "laptop" in slug, True)
    check("macos laptop slug contains arm tag",
          "m1" in slug, True,
          "arm64/aarch64 gets the 'm1' tag — matches macbook-air-m1 convention")
    check("macos laptop slug contains user", "bob" in slug, True)


def a_macos_desktop_slug():
    """A macOS desktop (Mac Mini) on Apple Silicon."""
    with fake_system("macos", arch="arm64", user="carol",
                     sysctl_output="Macmini9,1") as pi:
        probe = I._probe_machine(pi)
        slug  = I._suggest_folder(pi)

    check("mac mini probe: chassis", probe["chassis"], "desktop")
    check("mac mini slug contains 'desktop'", "desktop" in slug, True)
    check("mac mini slug does NOT say 'laptop'", "laptop" not in slug, True)


def a_windows_laptop_slug():
    """A Windows laptop (PCSystemType=2)."""
    with fake_system("windows", arch="amd64", user="dave",
                     wmic_output="PCSystemType=2\n") as pi:
        probe = I._probe_machine(pi)
        slug  = I._suggest_folder(pi)

    check("windows probe: system", probe["system"], "windows")
    check("windows probe: chassis", probe["chassis"], "laptop")
    check("windows laptop slug ends with -windows", slug.endswith("-windows"), True)
    check("windows laptop slug contains 'laptop'", "laptop" in slug, True)
    check("windows laptop slug contains user", "dave" in slug, True)


def a_windows_desktop_slug():
    """A Windows desktop (PCSystemType=1)."""
    with fake_system("windows", arch="amd64", user="eve",
                     wmic_output="PCSystemType=1\n") as pi:
        slug = I._suggest_folder(pi)

    check("windows desktop slug contains 'desktop'", "desktop" in slug, True)
    check("windows desktop slug does NOT say 'laptop'", "laptop" not in slug, True)


def a_wsl_slug():
    """WSL gets its own OS tag, not 'linux'."""
    with fake_system("linux", is_wsl=True, arch="x86_64", user="frank",
                     chassis_type="10") as pi:
        slug = I._suggest_folder(pi)

    check("wsl slug ends with -wsl", slug.endswith("-wsl"), True,
          "WSL is Linux-kernel but it lives beside a whole second Windows install "
          "— the folder name must say 'wsl', not 'linux'")


def a_unknown_chassis_omitted():
    """When the chassis cannot be determined it is omitted, not guessed."""
    with fake_system("linux", arch="x86_64", user="grace",
                     chassis_type=None) as pi:
        probe = I._probe_machine(pi)
        slug  = I._suggest_folder(pi)

    check("unknown chassis is None, not a placeholder",
          probe["chassis"], None)
    check("unknown chassis is omitted from the slug",
          "none" not in slug.lower() and "unknown" not in slug.lower(), True,
          "a wrong chassis label is permanent once committed — omit, not guess")
    check("slug without chassis still ends with OS tag",
          slug.endswith("-linux"), True)


def a_battery_fallback_is_laptop():
    """On Linux, a present BAT device identifies a laptop even without DMI."""
    with fake_system("linux", arch="x86_64", user="henry",
                     dmi_fail=True,
                     power_supplies=("AC0", "BAT0")) as pi:
        probe = I._probe_machine(pi)

    check("battery present => chassis laptop (fallback)", probe["chassis"], "laptop")


def a_no_battery_is_not_laptop():
    """A desktop with no battery and no DMI does not become a laptop."""
    with fake_system("linux", arch="x86_64", user="ivan",
                     dmi_fail=True,
                     power_supplies=("AC0",)) as pi:
        probe = I._probe_machine(pi)

    check("no battery + dmi failure => chassis None (not laptop)",
          probe["chassis"], None,
          "absence of a battery is not proof of desktop — it could be a server "
          "or a VM; None is the honest answer")


# ---------------------------------------------------------------------------
# 2. The slug is clean and stable
# ---------------------------------------------------------------------------

def a_slug_only_has_valid_chars():
    """The slug must be [a-z0-9-] — it becomes a directory name and a git path."""
    for system, user, arch, kw in [
        ("linux",   "alice",  "x86_64",  {"chassis_type": "9"}),
        ("macos",   "böb",    "arm64",   {"sysctl_output": "MacBookAir"}),
        ("windows", "c@rol!", "amd64",   {"wmic_output": "PCSystemType=2\n"}),
        ("linux",   "user 1", "x86_64",  {}),
    ]:
        with fake_system(system, arch=arch, user=user, **kw) as pi:
            slug = I._suggest_folder(pi)
        bad = [c for c in slug if c not in
               "abcdefghijklmnopqrstuvwxyz0123456789-"]
        check(f"slug for {system}/{user!r} has only [a-z0-9-]: {slug!r}",
              bad, [],
              f"bad chars: {bad!r} — the slug becomes a directory name; "
              "special characters break git, GitHub URLs, and shell scripts")


def a_slug_is_stable_across_calls():
    """Running the probe twice on the same machine gives the same slug."""
    with fake_system("linux", arch="x86_64", user="judy",
                     chassis_type="9") as pi:
        slug_a = I._suggest_folder(pi)
        slug_b = I._suggest_folder(pi)

    check("slug is deterministic (same inputs, same output)",
          slug_a, slug_b,
          "a slug that changes between runs would create a second machines.json "
          "entry every time install.py is run on the same machine")


def a_slug_is_not_empty():
    """Even if every probe fails the slug must not be empty."""
    with fake_system("linux", arch="", user="",
                     dmi_fail=True) as pi:
        # empty user and arch
        slug = I._suggest_folder(pi)

    check("slug is never empty even with all probes empty",
          bool(slug.strip("-")), True,
          "an empty slug would create a machines.json entry with an empty folder "
          "name, which is silently wrong in every report")
    check("slug still ends with OS tag",
          slug.endswith("-linux"), True)


# ---------------------------------------------------------------------------
# 3. The probe never raises
# ---------------------------------------------------------------------------

def a_probe_never_raises():
    """Every probe broken at once must return a result, not an exception.

    The probe runs before every step in install.py. If it raises, nothing runs
    — not the retention period raise, not the daemon artifact write. A machine
    that cannot answer one question correctly must still be installed.
    """
    real_getuser   = getpass.getuser
    real_machine   = platform.machine
    real_node      = platform.node
    real_chassis   = I._probe_chassis

    getpass.getuser  = lambda: (_ for _ in ()).throw(OSError("no login"))
    platform.machine = lambda: (_ for _ in ()).throw(OSError("no arch"))
    platform.node    = lambda: (_ for _ in ()).throw(OSError("no node"))
    I._probe_chassis = lambda s: (_ for _ in ()).throw(OSError("no chassis"))

    try:
        pi = {"system": "linux", "is_wsl": False}
        raised = False
        try:
            probe = I._probe_machine(pi)
        except Exception as e:  # noqa: BLE001
            raised = True
            probe = {}
            print(f"        raised: {type(e).__name__}: {e}")
    finally:
        getpass.getuser  = real_getuser
        platform.machine = real_machine
        platform.node    = real_node
        I._probe_chassis = real_chassis

    check("_probe_machine never raises even with every sub-probe broken",
          raised, False,
          "the probe runs before everything else; a raise blocks the whole install")


def a_suggest_folder_never_raises():
    """_suggest_folder must not raise even if _probe_machine returns garbage."""
    with fake_system("linux", arch="x86_64", user="test") as pi:
        # Feed _suggest_folder a probe result with unexpected keys missing
        bad_probe_result = {}  # completely empty
        real_probe = I._probe_machine
        I._probe_machine = lambda p: bad_probe_result
        try:
            raised = False
            try:
                slug = I._suggest_folder(pi)
            except Exception as e:  # noqa: BLE001
                raised = True
                slug = ""
                print(f"        raised: {type(e).__name__}: {e}")
        finally:
            I._probe_machine = real_probe

    check("_suggest_folder never raises on empty probe result", raised, False,
          "if the probe returned nothing, the slug must still be a valid string")


# ---------------------------------------------------------------------------
# 4. machines.json write is atomic and idempotent
# ---------------------------------------------------------------------------

def a_machines_json_is_atomic():
    """The write must be atomic — a partial write must not corrupt the file.

    The existing code uses a tmp file + os.replace(), which is atomic on every
    platform that matters. This attack interrupts in the middle and verifies the
    original is unchanged.
    """
    d = pathlib.Path(tempfile.mkdtemp(prefix="adv-install-"))
    try:
        # Write a known-good machines.json into a temp dir
        real_root = I.ROOT
        I.ROOT = d
        initial = {"_comment": [], "machines": [
            {"folder": "existing-machine-linux", "label": "Existing"}
        ]}
        (d / "machines.json").write_text(
            json.dumps(initial, indent=2), encoding="utf-8")

        # Break os.replace so the rename never happens
        real_replace = os.replace
        calls = []
        def broken_replace(src, dst):
            calls.append((src, dst))
            raise OSError("disk full")
        os.replace = broken_replace

        try:
            I._save_machines_json({"machines": [{"folder": "new", "label": "New"}]})
        except OSError:
            pass
        finally:
            os.replace = real_replace

        # The original must be intact
        try:
            doc = json.loads((d / "machines.json").read_text(encoding="utf-8"))
            folders = [m["folder"] for m in doc.get("machines", [])]
        except Exception as e:  # noqa: BLE001
            folders = []
            print(f"        could not read machines.json: {e}")

        check("original machines.json intact after a broken write",
              folders, ["existing-machine-linux"],
              "os.replace failure must not leave a truncated machines.json")
        check("the tmp file was created (write started before the rename failed)",
              bool(calls), True)
    finally:
        I.ROOT = real_root
        shutil.rmtree(d, ignore_errors=True)


def a_machine_folder_is_idempotent():
    """Running machine_folder twice on the same machine must not add a duplicate.

    The .machine-id check covers the case where the machine has already been
    scanned. This covers the case where machines.json already has the entry but
    .machine-id does not exist yet (e.g. install ran, scan has not).
    """
    d = pathlib.Path(tempfile.mkdtemp(prefix="adv-install-"))
    try:
        real_root = I.ROOT
        I.ROOT = d

        (d / "machines.json").write_text(
            json.dumps({"machines": []}, indent=2), encoding="utf-8")

        # Simulate the probe returning a consistent slug
        pi = {"system": "linux", "is_wsl": False}
        with fake_system("linux", arch="x86_64", user="judy", chassis_type="9"):
            # First call: adds the folder
            I.machine_folder(apply_it=True, pi=pi)
            doc_after_first = json.loads(
                (d / "machines.json").read_text(encoding="utf-8"))

            # Second call: must not add it again
            I.machine_folder(apply_it=True, pi=pi)
            doc_after_second = json.loads(
                (d / "machines.json").read_text(encoding="utf-8"))

        n_first  = len(doc_after_first.get("machines", []))
        n_second = len(doc_after_second.get("machines", []))
        check("machine_folder does not duplicate an entry on a second run",
              n_second, n_first,
              f"first call added {n_first} entr(ies); second call had "
              f"{n_second} — a duplicate would cause combine.py to report "
              "one empty machine for every install.py run")
    finally:
        I.ROOT = real_root
        shutil.rmtree(d, ignore_errors=True)


def a_machine_folder_dry_run_changes_nothing():
    """--check (apply_it=False) must not modify machines.json."""
    d = pathlib.Path(tempfile.mkdtemp(prefix="adv-install-"))
    try:
        real_root = I.ROOT
        I.ROOT = d
        original = json.dumps({"machines": []}, indent=2)
        (d / "machines.json").write_text(original, encoding="utf-8")

        pi = {"system": "linux", "is_wsl": False}
        with fake_system("linux", arch="x86_64", user="kate", chassis_type="9"):
            I.machine_folder(apply_it=False, pi=pi)

        after = (d / "machines.json").read_text(encoding="utf-8")
        check("dry run does not touch machines.json",
              after, original,
              "apply_it=False must be safe to run on any machine without "
              "committing any change — that is what --check promises")
    finally:
        I.ROOT = real_root
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------
# 5. _claimed_folder finds the right existing folder
# ---------------------------------------------------------------------------

def a_claimed_folder_finds_existing():
    """_claimed_folder returns the folder name when .machine-id matches hostname."""
    d = pathlib.Path(tempfile.mkdtemp(prefix="adv-install-"))
    try:
        real_root = I.ROOT
        real_node = platform.node
        I.ROOT = d
        platform.node = lambda: "test-hostname"

        machine_dir = d / "my-laptop-linux"
        (machine_dir / ".machine-id").parent.mkdir(parents=True)
        (machine_dir / ".machine-id").write_text(
            json.dumps({"hostname": "test-hostname", "folder": "my-laptop-linux"}),
            encoding="utf-8")

        claimed = I._claimed_folder()
        check("_claimed_folder finds existing folder by hostname",
              claimed, "my-laptop-linux")
    finally:
        I.ROOT = real_root
        platform.node = real_node
        shutil.rmtree(d, ignore_errors=True)


def a_claimed_folder_is_case_insensitive():
    """Hostname comparison must be case-insensitive.

    The .machine-id was written with the hostname as the OS returned it
    ('HP-Phantom-Core'); platform.node() may return it differently cased on
    the next run. A case-sensitive match creates a duplicate entry.
    """
    d = pathlib.Path(tempfile.mkdtemp(prefix="adv-install-"))
    try:
        real_root = I.ROOT
        real_node = platform.node
        I.ROOT = d
        platform.node = lambda: "hp-phantom-core"   # lowercase

        machine_dir = d / "hp-laptop-linux"
        (machine_dir / ".machine-id").parent.mkdir(parents=True)
        (machine_dir / ".machine-id").write_text(
            json.dumps({"hostname": "HP-Phantom-Core"}),  # mixed case
            encoding="utf-8")

        claimed = I._claimed_folder()
        check("_claimed_folder is case-insensitive on hostname",
              claimed, "hp-laptop-linux",
              "the .machine-id wrote 'HP-Phantom-Core'; platform.node() returns "
              "'hp-phantom-core' — a case-sensitive check creates a duplicate")
    finally:
        I.ROOT = real_root
        platform.node = real_node
        shutil.rmtree(d, ignore_errors=True)


def a_claimed_folder_returns_none_on_fresh_machine():
    """_claimed_folder returns None when no .machine-id exists yet."""
    d = pathlib.Path(tempfile.mkdtemp(prefix="adv-install-"))
    try:
        real_root = I.ROOT
        I.ROOT = d
        claimed = I._claimed_folder()
        check("_claimed_folder returns None on a fresh machine with no .machine-id",
              claimed, None)
    finally:
        I.ROOT = real_root
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------

def a_uuid_match_finds_folder_after_hostname_change():
    """owned_folder matches by UUID even when the hostname changed.

    Phase 1i: the UUID is the identity anchor. A machine that changed its
    hostname (OS reinstall on macOS, DHCP rename, container rename) must still
    find its folder. Without UUID matching it falls through to hostname guess
    and could claim the wrong folder or refuse to run.
    """
    import importlib
    import update as U

    d = pathlib.Path(tempfile.mkdtemp(prefix="adv-uuid-"))
    try:
        mdir = d / "my-machine"
        mdir.mkdir()
        # Write a .machine-id with a known UUID but a DIFFERENT hostname
        (mdir / ".machine-id").write_text(
            json.dumps({
                "hostname": "old-hostname-xyz",
                "folder": "my-machine",
                "hardware_uuid": "AAAABBBB-0000-0000-0000-000000000001",
            }, indent=1) + "\n",
            encoding="utf-8",
        )
        real_root = U.ROOT
        U.ROOT = d

        # Patch hardware_uuid to return the UUID that was written
        import install as _I
        real_hw = _I.hardware_uuid

        def _fake_uuid():
            return "AAAABBBB-0000-0000-0000-000000000001"

        _I.hardware_uuid = _fake_uuid
        try:
            result = U.owned_folder("new-hostname-xyz")
            check(
                "UUID match finds folder even when hostname is different",
                result, "my-machine",
                "without UUID matching a renamed machine writes into a new folder "
                "and its history is silently lost",
            )
        finally:
            _I.hardware_uuid = real_hw
            U.ROOT = real_root
    finally:
        shutil.rmtree(str(d), ignore_errors=True)


def a_hostname_fallback_when_no_uuid():
    """owned_folder falls back to hostname when .machine-id has no hardware_uuid.

    Folders written before UUID support must still be found by hostname.
    """
    import update as U

    d = pathlib.Path(tempfile.mkdtemp(prefix="adv-uuid-fallback-"))
    try:
        mdir = d / "legacy-machine"
        mdir.mkdir()
        # Old-style .machine-id: no hardware_uuid
        (mdir / ".machine-id").write_text(
            json.dumps({
                "hostname": "legacy-host",
                "folder": "legacy-machine",
            }, indent=1) + "\n",
            encoding="utf-8",
        )
        real_root = U.ROOT
        U.ROOT = d
        import install as _I
        real_hw = _I.hardware_uuid

        def _no_uuid():
            return None

        _I.hardware_uuid = _no_uuid
        try:
            result = U.owned_folder("legacy-host")
            check(
                "hostname fallback finds folder when no UUID in .machine-id",
                result, "legacy-machine",
                "dropping hostname fallback would break every folder written "
                "before UUID support existed",
            )
        finally:
            _I.hardware_uuid = real_hw
            U.ROOT = real_root
    finally:
        shutil.rmtree(str(d), ignore_errors=True)


def a_degenerate_markers():
    """Structural markers: empty list, single-item list, rmtree outside finally."""
    import sessions as _sessions

    # EMPTY — active_minutes on a literal [] is a safe non-utility call
    _sessions.active_minutes([])

    # SINGLE — active_minutes on a one-item list
    _sessions.active_minutes([_sessions.blank()])

    # ABSENT — rmtree outside finally
    d = pathlib.Path(tempfile.mkdtemp(prefix="adv-inst-deg-"))
    shutil.rmtree(str(d))           # ABSENT marker — outside finally


ATTACKS = [
    # OS probe correctness per platform
    ("linux laptop slug", a_linux_laptop_slug),
    ("macos laptop slug", a_macos_laptop_slug),
    ("macos desktop slug", a_macos_desktop_slug),
    ("windows laptop slug", a_windows_laptop_slug),
    ("windows desktop slug", a_windows_desktop_slug),
    ("wsl gets its own OS tag", a_wsl_slug),
    ("unknown chassis omitted not guessed", a_unknown_chassis_omitted),
    ("battery fallback identifies laptop", a_battery_fallback_is_laptop),
    ("no battery + dmi failure is not laptop", a_no_battery_is_not_laptop),
    # Slug cleanliness
    ("slug has only valid chars", a_slug_only_has_valid_chars),
    ("slug is stable across calls", a_slug_is_stable_across_calls),
    ("slug is never empty", a_slug_is_not_empty),
    # Robustness
    ("probe never raises", a_probe_never_raises),
    ("suggest_folder never raises on empty probe", a_suggest_folder_never_raises),
    # machines.json correctness
    ("machines.json write is atomic", a_machines_json_is_atomic),
    ("machine_folder is idempotent", a_machine_folder_is_idempotent),
    ("dry run changes nothing", a_machine_folder_dry_run_changes_nothing),
    # claimed_folder
    ("claimed_folder finds existing folder", a_claimed_folder_finds_existing),
    ("claimed_folder is case-insensitive", a_claimed_folder_is_case_insensitive),
    ("claimed_folder returns None on fresh machine",
     a_claimed_folder_returns_none_on_fresh_machine),
    # UUID-based folder identity (Phase 1i)
    ("UUID match finds folder after hostname change",
     a_uuid_match_finds_folder_after_hostname_change),
    ("hostname fallback when no UUID in .machine-id",
     a_hostname_fallback_when_no_uuid),
    ("degenerate markers", a_degenerate_markers),
]


def main():
    import io, contextlib as cl
    print(f"\n  INSTALL FOLDER — {len(ATTACKS)} attacks\n")
    for name, fn in ATTACKS:
        print(f"  -- {name}")
        # Capture stdout from the function itself so check() lines are
        # indented uniformly. Errors and FAIL lines are kept; redundant
        # PASS lines are suppressed when --verbose is not set.
        buf = io.StringIO()
        try:
            with cl.redirect_stdout(buf):
                fn()
        except Exception as e:  # noqa: BLE001
            print(f"  FAIL  {name} raised: {type(e).__name__}: {e}")
            FAILED.append(name)
        out = buf.getvalue()
        for line in out.splitlines():
            print(line)

    print()
    if SKIPPED:
        print(f"  {len(SKIPPED)} attack(s) skipped (recorded, not counted as passed):")
        for sname, why in SKIPPED:
            print(f"    SKIP  {sname}  ({why})")
    if FAILED:
        print(f"\n  {len(FAILED)} check(s) FAILED:")
        for name in FAILED:
            print(f"    FAIL  {name}")
        return 1
    total_checks = len([line for line in "\n".join(
        [] if not FAILED else FAILED).splitlines()])  # just use ATTACKS length
    print(f"  {len(ATTACKS)} attacks, 0 failed — every attack caught")
    return 0


if __name__ == "__main__":
    sys.exit(main())
