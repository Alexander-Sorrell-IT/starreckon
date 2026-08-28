#!/usr/bin/env python3
"""Source-level dispatch tests for PLAN-MERGED 8.7 installer modes.

These never call a real installer operation. Every operation that can write,
download, change service state, or pull the repository is replaced before
`install.main()` receives its arguments.
"""

import contextlib
import io
import pathlib
import sys
import unittest.mock as mock

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import install  # noqa: E402

PASS, FAIL = [], []


def check(name, got, want, why=""):
    (PASS if got == want else FAIL).append((name, got, want, why))


def invoke(argv, patches=()):
    """Run main with a controlled argv and no accumulated prior step results."""
    install.results.clear()
    with contextlib.ExitStack() as stack, \
            mock.patch.object(sys, "argv", ["install.py", *argv]), \
            contextlib.redirect_stdout(io.StringIO()), \
            contextlib.redirect_stderr(io.StringIO()):
        for patch in patches:
            stack.enter_context(patch)
        return install.main()


def recorder(calls, name):
    def record(*args, **_kwargs):
        calls.append((name, args))
    return record


def test_models_only_runs_model_components():
    calls = []
    patches = [
        mock.patch.object(install, name, recorder(calls, name))
        for name in ("forecaster", "search_corpus", "antares", "provenance_kit",
                     "daemon_artifact")
    ]
    code = invoke(["--models"], patches)
    called = [name for name, _args in calls]
    check("--models succeeds with controlled components", code, 0)
    check("--models calls every optional model component",
          called, ["forecaster", "search_corpus", "antares", "provenance_kit"])
    check("--models does not write a daemon artifact", "daemon_artifact" in called, False)


def test_daemon_only_runs_daemon_artifact():
    calls = []
    patches = [
        mock.patch.object(install, name, recorder(calls, name))
        for name in ("forecaster", "search_corpus", "antares", "provenance_kit",
                     "daemon_artifact")
    ]
    code = invoke(["--daemon"], patches)
    called = [name for name, _args in calls]
    check("--daemon succeeds with controlled artifact", code, 0)
    check("--daemon calls only its artifact", called, ["daemon_artifact"])


def test_all_runs_models_and_daemon_artifact():
    calls = []
    patches = [
        mock.patch.object(install, name, recorder(calls, name))
        for name in ("forecaster", "search_corpus", "antares", "provenance_kit",
                     "daemon_artifact")
    ]
    code = invoke(["--all"], patches)
    called = [name for name, _args in calls]
    check("--all succeeds with controlled components", code, 0)
    check("--all calls exactly models and daemon artifact",
          called, ["daemon_artifact", "forecaster", "search_corpus", "antares",
                   "provenance_kit"])


def test_check_has_no_installer_or_writer_side_effects():
    writers = ("protect", "machine_folder", "daemon_artifact", "forecaster",
               "search_corpus", "antares", "provenance_kit", "daemon_health",
               "cli_scan")

    def forbidden(name):
        def raise_if_called(*_args, **_kwargs):
            raise AssertionError(f"--check called side-effecting {name}")
        return raise_if_called

    patches = [
        mock.patch.object(install, name, forbidden(name))
        for name in writers
    ] + [
        mock.patch.object(install, "models_status"),
        mock.patch.object(install, "daemon_running_check"),
    ]
    code = invoke(["--check"], patches)
    check("--check invokes no installer or writer operation", code, 0)


def test_conflicting_modes_are_rejected():
    conflicts = (
        ["--models", "--daemon"],
        ["--check", "--apply"],
        ["--models", "--no-models"],
        ["--all", "--no-forecaster"],
    )
    codes = []
    for argv in conflicts:
        try:
            invoke(argv)
        except SystemExit as error:
            codes.append(error.code)
        else:
            codes.append(None)
    check("conflicting installer modes exit with argparse error", codes, [2] * len(conflicts))


def legacy_patches(calls):
    platform_info = {
        "family": "linux", "store_forms": [], "service_manager": None,
        "warnings": [],
    }
    patches = [
        mock.patch("platform_detect.detect", return_value=platform_info),
        mock.patch.object(install.platform, "system", return_value="TestOS"),
        mock.patch.object(install.platform, "release", return_value="1"),
        mock.patch.object(install.platform, "python_version", return_value="3"),
        mock.patch.object(install, "_probe_machine", return_value={
            "os_user": "test", "hostname": "test", "system": "test",
            "is_wsl": False, "arch": "test", "chassis": None,
            "hardware_uuid": None,
        }),
        mock.patch.object(install, "_suggest_folder", return_value="test-machine"),
        mock.patch.object(install, "_claimed_folder", return_value=None),
        mock.patch.object(install, "_machines_json", return_value={"machines": []}),
        mock.patch.object(install, "prereqs", return_value={"python3.11": "python3.11"}),
        mock.patch.object(install, "unprotected_now", return_value=([], 0)),
    ]
    for name in ("protect", "machine_folder", "daemon_artifact", "forecaster",
                 "search_corpus", "antares", "provenance_kit", "daemon_health",
                 "daemon_running_check", "cli_scan"):
        patches.append(mock.patch.object(install, name, recorder(calls, name)))
    return patches


def test_apply_and_verify_keep_their_legacy_full_paths():
    apply_calls = []
    check("--apply keeps the full setup path",
          invoke(["--apply"], legacy_patches(apply_calls)), 0)
    check("--apply still includes core setup, daemon, and models",
          {name for name, _args in apply_calls} >=
          {"protect", "machine_folder", "daemon_artifact", "forecaster",
           "search_corpus", "antares", "provenance_kit", "daemon_health", "cli_scan"},
          True)

    verify_calls = []
    check("--verify keeps the legacy verification path",
          invoke(["--verify"], legacy_patches(verify_calls)), 0)
    called = {name for name, _args in verify_calls}
    check("--verify still checks daemon running and daemon health",
          {"daemon_running_check", "daemon_health"} <= called, True)


def main():
    tests = [test for name, test in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        try:
            test()
        except Exception as error:  # noqa: BLE001
            FAIL.append((test.__name__, f"raised {type(error).__name__}: {error}",
                         "no exception", ""))

    for name, got, want, why in PASS:
        print(f"  PASS  {name}")
    for name, got, want, why in FAIL:
        print(f"  FAIL  {name}\n          got  {got!r}\n          want {want!r}"
              + (f"\n          {why}" if why else ""))
    print(f"\n{len(PASS) + len(FAIL)} checks, {len(FAIL)} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
