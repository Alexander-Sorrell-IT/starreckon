#!/usr/bin/env python3
"""Read and validate cli-config.json. One call, used by everything.

    python3 config.py            print this machine's config
    python3 config.py --check    validate only, exit non-zero on error

WHY ONE FILE

The daemon interval, the machine identity, extra search paths, and CLI
overrides were previously scattered: machine identity in .machine-id,
daemon interval hardcoded in retention_guard.py, extra paths not
supported at all, new CLIs requiring Python edits. A person setting up
a new machine had to know which files to touch and in what order.

One JSON file, committed per machine, answers all of it. The system
works with an empty or absent config — all fields are optional and have
safe defaults — so a machine that has not set one up yet is not broken,
it is just using defaults.

WHAT IT DOES NOT DO

It does not replace stores.py or sessions.py for built-in CLIs. Those
are the canonical definitions. cli_overrides supplements them for CLIs
nobody has written a reader for yet, and for non-standard install paths.
"""

import datetime
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent
CONFIG_FILE = ROOT / "cli-config.json"

# Defaults used when a field is absent.
DEFAULTS = {
    "machine": {
        "folder": None,
        "label": None,
    },
    "daemon": {
        "sync_interval_hours": 6,
        "ledger_interval_hours": 6,
        "started": None,
    },
    "extra_paths": [],
    "cli_overrides": [],
}


def _merge(base, override):
    """Shallow-merge override into base, returning a new dict."""
    out = dict(base)
    for k, v in override.items():
        if k.startswith("_"):
            continue          # _comment, _example — skip
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load(path=None):
    """Load, validate and return the config as a plain dict.

    Missing fields are filled from DEFAULTS so every caller can assume
    every key exists. Unknown top-level keys are preserved — forward
    compatibility for fields added later.

    Raises ValueError with a human-readable message on hard errors
    (malformed JSON, wrong types for required fields). Never raises on
    missing optional fields.
    """
    p = pathlib.Path(path) if path else CONFIG_FILE
    raw = {}
    if p.is_file():
        try:
            text = p.read_text(encoding="utf-8")
            raw = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"cli-config.json is not valid JSON: {e}") from e

    cfg = _merge(DEFAULTS, raw)

    # Strip _example entries from cli_overrides so they never reach a reader.
    cfg["cli_overrides"] = [
        c for c in cfg["cli_overrides"]
        if not c.get("_example") and not any(k.startswith("_") for k in c)
    ]

    _validate(cfg)
    return cfg


def _validate_override_path(p, label):
    """Raise ValueError if a cli_overrides path entry is unsafe.

    WHY THIS EXISTS

    cli_overrides.paths entries are written by the operator into cli-config.json
    and passed through to sessions.py as home-relative search roots. Without a
    gate they reach os.path.join(home, p) and could point anywhere on disk:

        ../../../etc/passwd     home-relative traversal
        /absolute/path          bypasses home entirely
        C:\\Windows\\...        Windows absolute

    The gate runs at load() time — before any entry reaches a reader — so a
    misconfigured or malicious config is caught once, at the entry point, rather
    than silently resolved to an arbitrary path in every reader that uses it.

    WHAT IS ALLOWED

    A safe path is home-relative: it has no leading separator, no drive letter,
    no `..` components, and no null bytes. Tilde-prefixed paths (`~/foo`) are
    rejected — expand them in the config if needed. Environment variables
    are not expanded here either; that is extra_paths' job.

    Leading-dot names (`.claude`, `.config/Code`) are fine — that is the normal
    form for dotdir stores.
    """
    if not isinstance(p, str):
        raise ValueError(f"{label} must be a string, got {type(p).__name__}")
    if "\x00" in p:
        raise ValueError(f"{label} contains a null byte")
    # Normalise to forward slashes for the checks below so Windows paths
    # spelled with either separator are both caught.
    norm = p.replace("\\", "/")
    if norm.startswith("/") or norm.startswith("~"):
        raise ValueError(
            f"{label} must be a home-relative path, not absolute: {p!r}")
    # Drive-letter absolute (C:/, D:\, …)
    if len(norm) >= 2 and norm[1] == ":" and (len(norm) == 2 or norm[2] in "/\\"):
        raise ValueError(
            f"{label} must be a home-relative path, not a drive-letter path: {p!r}")
    # Component-level traversal. "a../b" is fine; "a/..b" is fine; "a/../b" is not.
    components = norm.split("/")
    for comp in components:
        if comp == "..":
            raise ValueError(
                f"{label} contains a '..' traversal component: {p!r}")


def _validate(cfg):
    """Raise ValueError for any field that is wrong enough to act on."""
    m = cfg.get("machine", {})
    if m.get("folder") and not isinstance(m["folder"], str):
        raise ValueError("machine.folder must be a string")

    d = cfg.get("daemon", {})
    for key in ("sync_interval_hours", "ledger_interval_hours"):
        v = d.get(key)
        if v is not None and (not isinstance(v, (int, float)) or v <= 0):
            raise ValueError(f"daemon.{key} must be a positive number, got {v!r}")

    extra = cfg.get("extra_paths", [])
    if not isinstance(extra, list):
        raise ValueError("extra_paths must be a list")
    for p in extra:
        if not isinstance(p, str):
            raise ValueError(f"extra_paths entries must be strings, got {p!r}")

    overrides = cfg.get("cli_overrides", [])
    if not isinstance(overrides, list):
        raise ValueError("cli_overrides must be a list")
    for i, ov in enumerate(overrides):
        if not isinstance(ov, dict):
            raise ValueError(f"cli_overrides[{i}] must be an object")
        if "cli" not in ov:
            raise ValueError(f"cli_overrides[{i}] is missing required field 'cli'")
        fields = ov.get("token_fields")
        if fields is not None and not isinstance(fields, list):
            raise ValueError(
                f"cli_overrides[{i}].token_fields must be a list")
        paths = ov.get("paths")
        if paths is not None:
            if not isinstance(paths, list):
                raise ValueError(f"cli_overrides[{i}].paths must be a list")
            for j, p in enumerate(paths):
                _validate_override_path(p, f"cli_overrides[{i}].paths[{j}]")


def extra_paths(cfg=None):
    """Absolute paths from extra_paths, expanded and deduped.

    Expands ~ and environment variables. Skips entries that do not exist
    so callers can iterate without checking.
    """
    cfg = cfg or load()
    seen = set()
    out = []
    for raw in cfg.get("extra_paths", []):
        p = pathlib.Path(os.path.expandvars(os.path.expanduser(raw)))
        key = str(p.resolve()) if p.exists() else str(p)
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def cli_overrides(cfg=None):
    """CLI override blocks from config, stripped of example/comment entries.

    Returns a list of dicts. Each dict has at minimum 'cli'. Optional keys:
      label          str
      paths          list of home-relative strings
      token_fields   list of field name strings
      walk_depth     int
    """
    cfg = cfg or load()
    return list(cfg.get("cli_overrides", []))


def machine_folder(cfg=None):
    """The folder name for this machine, or None if not set."""
    cfg = cfg or load()
    return cfg.get("machine", {}).get("folder")


def daemon_intervals(cfg=None):
    """(sync_hours, ledger_hours) from config."""
    cfg = cfg or load()
    d = cfg.get("daemon", {})
    return (
        float(d.get("sync_interval_hours", DEFAULTS["daemon"]["sync_interval_hours"])),
        float(d.get("ledger_interval_hours", DEFAULTS["daemon"]["ledger_interval_hours"])),
    )


def record_daemon_start(path=None):
    """Write the daemon start timestamp into cli-config.json.

    Called once when the daemon starts. Sets daemon.started to an ISO
    timestamp if it is not already set — the first start is the baseline
    for the † (non-Claude) lifetime figures. Subsequent restarts do not
    overwrite it so the baseline stays anchored to when monitoring began.
    """
    p = pathlib.Path(path) if path else CONFIG_FILE
    raw = {}
    if p.is_file():
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return      # malformed JSON — do not corrupt it further

    daemon = raw.setdefault("daemon", {})
    if daemon.get("started"):
        return          # already set — do not move the baseline

    daemon["started"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    tmp = str(p) + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(raw, fh, indent=2)
            fh.write("\n")
        os.replace(tmp, p)
    except Exception:
        try:
            os.unlink(tmp)
        except Exception:
            pass


def daemon_started(cfg=None):
    """ISO timestamp when the daemon first started, or None.

    This is the † baseline for CLIs that have no vendor lifetime counter.
    None means the daemon has never run on this machine.
    """
    cfg = cfg or load()
    return cfg.get("daemon", {}).get("started")


def show(cfg=None):
    """Print a human-readable summary of the active config."""
    cfg = cfg or load()
    m = cfg.get("machine", {})
    d = cfg.get("daemon", {})
    ep = extra_paths(cfg)
    ov = cli_overrides(cfg)

    print(f"  config file    {CONFIG_FILE}")
    print(f"  machine        {m.get('folder') or '(not set)'}"
          f"  {m.get('label') or ''}")
    print(f"  daemon sync    every {d.get('sync_interval_hours', 6)}h")
    print(f"  daemon ledger  every {d.get('ledger_interval_hours', 6)}h")
    started = d.get("started")
    if started:
        print(f"  daemon start   {started[:19]}  "
              f"(† baseline for non-Claude CLIs)")
    else:
        print(f"  daemon start   not yet started")
    if ep:
        print(f"  extra paths    {len(ep)}")
        for p in ep:
            print(f"    {'exists' if p.exists() else 'missing':8}  {p}")
    else:
        print(f"  extra paths    none")
    if ov:
        print(f"  cli overrides  {len(ov)}")
        for o in ov:
            print(f"    {o['cli']:<18} paths={o.get('paths', [])}  "
                  f"fields={o.get('token_fields', '(default)')}")
    else:
        print(f"  cli overrides  none  (built-in CLIs only)")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="validate only, exit non-zero on error")
    ap.add_argument("--file", help="path to config file (default: cli-config.json)")
    args = ap.parse_args()
    try:
        cfg = load(args.file)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    if not args.check:
        show(cfg)
