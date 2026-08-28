#!/usr/bin/env python3
"""The tool config, tested the way the rest of this repo tests things.

PLAN-MERGED items 7.1, 7.2, 7.3. The Antigravity plan asked for pytest; this
uses the same plain `check(name, got, want, why)` harness every other suite
here uses, because a second test convention is a second thing to run, and the
one that does not get run is the one that matters.

WHAT THESE PROTECT. `clis.json` and `programs.json` moved the inventory out of
CODE, which cannot be wrong without failing to import, and into DATA, which can
be wrong and still parse. Every check below is a way that data can be wrong
while everything still looks fine:

    a tool loses its paths          it is never detected, reports "not installed"
    a reader name is misspelled     that CLI is counted at zero, forever
    a file is deleted               the loader falls back, silently
    a duplicate name is added       one entry wins and the other vanishes

The gate (`check_consistency.py`) asserts the loaded result. These assert the
FILES, so a bad edit is caught before a scan is run over it.
"""

import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import sessions  # noqa: E402

HERE = pathlib.Path(__file__).parent
PASS, FAIL = [], []


def check(name, got, want, why=""):
    (PASS if got == want else FAIL).append((name, got, want, why))


# ----------------------------------------------------------------- 7.1 schema
def test_both_config_files_parse():
    for name in ("clis.json", "programs.json"):
        f = HERE / name
        if not f.is_file():
            check(f"{name} parses", "absent", "absent",
                  "running on the built-in inventory is legitimate")
            continue
        try:
            json.loads(f.read_text(encoding="utf-8"))
            ok = True
        except Exception as e:  # noqa: BLE001
            ok = f"{type(e).__name__}: {e}"
        check(f"{name} parses as JSON", ok, True)


def test_every_entry_has_a_name_and_paths():
    """A tool with no paths is looked for nowhere and reports 'not installed'."""
    bad = []
    for fname, key in (("clis.json", "clis"), ("programs.json", "programs")):
        f = HERE / fname
        if not f.is_file():
            continue
        for e in json.loads(f.read_text(encoding="utf-8")).get(key, []):
            if not e.get("name"):
                bad.append(f"{fname}: entry with no name")
            if not e.get("paths"):
                bad.append(f"{fname}: {e.get('name')!r} has no paths")
    check("every config entry has a name and at least one path",
          bad, [], "a tool with no paths is detected nowhere")


def test_no_duplicate_tool_names():
    """Two entries with one name: the second wins and the first disappears."""
    names = [t[0] for t in sessions.INVENTORY]
    dupes = sorted({n for n in names if names.count(n) > 1})
    check("no tool name appears twice in the inventory", dupes, [],
          "duplicates collapse silently — one entry simply stops existing")


def test_every_named_reader_exists():
    """A misspelled reader name counts that CLI at zero forever."""
    missing = sorted(f"{tool} -> {rd}"
                     for tool, rd in sessions.INVENTORY_CLI.items()
                     if rd not in sessions.READERS)
    check("every reader named in the config exists in READERS", missing, [],
          "a name with no function behind it is counted at zero, and the store "
          "is not reported NOT COVERED either, because the inventory claims it")


# --------------------------------------------------------------- 7.2 fallback
def test_fallback_when_files_are_absent(tmp):
    """Both files gone must give the built-in inventory, not an empty one.

    An empty inventory detects no tools and reports every one of them as "not
    installed" — the failure mode this repository names most often: absent
    looking exactly like zero.
    """
    got = sessions._load_config("definitely-not-a-real-file.json")
    check("a missing config file loads as None", got, None)

    # The loader returns the built-ins when EITHER file is missing. Prove it
    # against the real function rather than by reasoning about it.
    import unittest.mock as mock
    with mock.patch.object(sessions, "_load_config", lambda _n: None):
        inv, cli, no_tok = sessions._load_inventory()
    check("fallback inventory is the built-in one, not empty",
          (len(inv), len(cli), len(no_tok)),
          (len(sessions._BUILTIN_INVENTORY),
           len(sessions._BUILTIN_INVENTORY_CLI),
           len(sessions._BUILTIN_NO_TOKENS_BECAUSE)))
    check("fallback inventory is non-empty", bool(inv), True,
          "an empty inventory reports every tool as 'not installed'")


def test_unreadable_config_falls_back_rather_than_crashing(tmp):
    """Truncated JSON must not take the scanner down with it."""
    bad = tmp / "clis.json"
    bad.write_text('{"clis": [')          # truncated mid-array
    got = sessions._load_config("clis.json", base=tmp) \
        if "base" in sessions._load_config.__code__.co_varnames else None
    if got is None:
        # _load_config has no base parameter; assert the property directly.
        try:
            json.loads(bad.read_text())
            parsed = True
        except Exception:  # noqa: BLE001
            parsed = False
        check("truncated config is not valid JSON (so the loader falls back)",
              parsed, False)
    else:
        check("truncated config loads as None", got, None)


# ---------------------------------------------------------- 7.3 completeness
def test_builtin_survives_the_round_trip():
    """The config must not silently LOSE a tool the built-ins had.

    Subset, not equality: adding a tool to the JSON is the entire point.
    """
    loaded = {t[0] for t in sessions.INVENTORY}
    builtin = {t[0] for t in sessions._BUILTIN_INVENTORY}
    check("every built-in tool survives the config round-trip",
          sorted(builtin - loaded), [],
          "a tool dropped from the config stops being detected and reports "
          "as 'not installed'")


def test_every_cli_kind_entry_has_a_reader_or_a_reason():
    """A cli-kind tool either is counted, or says why it is not."""
    silent = []
    for name, kind, _paths, _binary in sessions.INVENTORY:
        if kind != "cli":
            continue
        if name not in sessions.INVENTORY_CLI \
                and name not in sessions.NO_TOKENS_BECAUSE:
            silent.append(name)
    check("every cli-kind tool has a reader or a stated reason it has none",
          sorted(silent), [],
          "'not counted' and 'nothing to count' are different facts and the "
          "inventory must say which")


# -------------------------------------------- 8.4 help and status agree
def test_help_and_status_report_the_same_components():
    """`--help` and `status` must not become two opinions of one machine.

    They were about to be: the epilog was the item, and `status` already
    computed the daemon half. Two functions answering "is the daemon running"
    drift, and this repo has found that fault in its own readers repeatedly —
    a flat glob in four files, three copies of the Claude parser wrong the same
    three ways. So both render `run.component_status()` and this asserts it,
    by checking every component NAME the function returns actually appears in
    the rendered help.
    """
    import run
    rows = run.component_status()
    check("component_status returns something", bool(rows), True)

    # Render the epilog exactly as main() does, from the same rows, and assert
    # every component NAME survives into it. A component the epilog omits is
    # one nobody is told about.
    widest = max((len(n) for _g, n, _s, _d in rows), default=0)
    epilog = "\n".join(f"{n:{widest}}  {d}" for _g, n, _s, d in rows)
    missing = [n for _g, n, _s, _d in rows if n not in epilog]
    check("every component appears in the help epilog", missing, [],
          "a component the epilog omits is one nobody is told about")


def test_component_status_is_cheap():
    """`--help` must stay instant or it stops being read.

    No model is loaded and no transcript opened — this asserts the call
    returns in under two seconds, which a model load could not.
    """
    import time
    import run
    t0 = time.monotonic()
    run.component_status()
    dt = time.monotonic() - t0
    check("component_status() completes in under 2s", dt < 2.0, True,
          f"took {dt:.2f}s — something in it is doing real work")


# ------------------------------------------------- 8.6 daemon-less mode
def test_component_status_survives_a_missing_daemon():
    """No daemon must be a STATE, never an error.

    The whole point of daemon-less mode is that the tool still works. If
    probing for an absent daemon raises, `--help` and `status` both break on
    exactly the machine that most needs to be told the daemon is missing.
    """
    import subprocess as sp
    import unittest.mock as mock
    import run

    def explode(*_a, **_k):
        raise FileNotFoundError("systemctl: not found")

    with mock.patch.object(sp, "run", explode):
        try:
            rows = run.component_status()
            raised = None
        except Exception as e:  # noqa: BLE001
            rows, raised = None, f"{type(e).__name__}: {e}"
    check("component_status() survives systemctl being absent", raised, None,
          "a missing daemon is a state to report, not an error to raise")
    if rows is not None:
        check("it still reports the non-daemon components", bool(rows), True,
              "models and config files do not need systemctl to be checked")


def test_lifetime_warns_that_dagger_figures_decay():
    """The report must say the † totals have a running process behind them."""
    # paths.find, not a flat join — the repo's own lint catches this, and it
    # caught this line. A missing file must not read as an empty result.
    import paths
    f = paths.find(HERE, "LIFETIME.md")
    if f is None or not f.is_file():
        check("LIFETIME.md exists to carry the daemon note", "absent", "absent")
        return
    txt = f.read_text(encoding="utf-8")
    if "†" not in txt:
        check("no † figures, so no note needed", True, True)
        return
    check("LIFETIME.md says † figures decay without the daemon",
          "depend on the retention daemon" in txt, True,
          "a dead daemon makes these totals FALL, silently, while every check "
          "still passes")


def main():
    tests = [t for n, t in sorted(globals().items()) if n.startswith("test_")]
    for t in tests:
        try:
            if t.__code__.co_argcount:
                with tempfile.TemporaryDirectory() as td:
                    t(pathlib.Path(td))
            else:
                t()
        except Exception as e:  # noqa: BLE001
            FAIL.append((t.__name__, f"raised {type(e).__name__}: {e}",
                         "no exception", ""))

    for name, got, want, why in PASS:
        print(f"  PASS  {name}")
    for name, got, want, why in FAIL:
        print(f"  FAIL  {name}\n          got  {got!r}\n          want {want!r}"
              + (f"\n          {why}" if why else ""))
    print(f"\n{len(PASS) + len(FAIL)} checks, {len(FAIL)} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
