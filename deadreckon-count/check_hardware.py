#!/usr/bin/env python3
"""Record what hardware this machine is, and which accounts ran on it.

Token counts mean little without the machine behind them: the same account moves
between computers, and a folder of numbers with no hardware attached can't be
compared to anything. This writes `hardware.json` into a machine folder so each
set of token numbers says what produced it.

The account list comes from the same place analyze_tokens.py reads it — each
config directory's own .claude.json — so hardware and usage always agree on who
was signed in.

Usage:
    python3 check_hardware.py                     # print only
    python3 check_hardware.py --out macbook-air-m1
"""

import argparse
import json
import pathlib
import paths
import platform
import shutil
import subprocess
import sys

try:
    from analyze_tokens import find_config_dirs, account_for
except ImportError:
    sys.exit("run this from the repo root (analyze_tokens.py must be importable)")


def sh(*cmd):
    """Run a probe, or return None. A missing tool is not an error here."""
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return out.stdout.strip() or None
    except Exception:
        return None


def sysctl(key):
    return sh("sysctl", "-n", key)


def as_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def gb(n_bytes):
    return round(n_bytes / 1024 ** 3, 1) if n_bytes else None


def mac_hardware():
    """macOS hardware, via sysctl and system_profiler."""
    hw = {
        "model_identifier": sysctl("hw.model"),
        "chip": sysctl("machdep.cpu.brand_string"),
        "cpu_logical": as_int(sysctl("hw.ncpu")),
        "cpu_performance_cores": as_int(sysctl("hw.perflevel0.physicalcpu")),
        "cpu_efficiency_cores": as_int(sysctl("hw.perflevel1.physicalcpu")),
        "memory_gb": gb(as_int(sysctl("hw.memsize"))),
    }

    # Apple Silicon reports the GPU only through system_profiler.
    disp = sh("system_profiler", "-json", "SPDisplaysDataType")
    if disp:
        try:
            cards = json.loads(disp).get("SPDisplaysDataType") or []
            if cards:
                c = cards[0]
                hw["gpu"] = c.get("sppci_model")
                hw["gpu_cores"] = as_int(c.get("sppci_cores"))
                hw["metal"] = c.get("spdisplays_mtlgpufamilysupport")
        except Exception:
            pass

    hw["os"] = f"macOS {sh('sw_vers', '-productVersion') or '?'}"
    hw["os_build"] = sh("sw_vers", "-buildVersion")
    return hw


def generic_hardware():
    """Fallback for anything that is not macOS."""
    hw = {
        "model_identifier": platform.machine(),
        "chip": platform.processor() or platform.machine(),
        "cpu_logical": None,
        "memory_gb": None,
        "os": f"{platform.system()} {platform.release()}",
    }
    try:
        import os as _os
        hw["cpu_logical"] = _os.cpu_count()
        if hasattr(_os, "sysconf") and "SC_PAGE_SIZE" in _os.sysconf_names:
            hw["memory_gb"] = gb(_os.sysconf("SC_PAGE_SIZE") * _os.sysconf("SC_PHYS_PAGES"))
    except Exception:
        pass
    return hw


def disk():
    """Capacity of the volume the home directory lives on.

    On macOS the root filesystem is a sealed read-only snapshot, so measuring `/`
    reports almost no usage. The data volume is the one that actually fills up.
    """
    target = pathlib.Path.home()
    try:
        total, used, free = shutil.disk_usage(target)
        return {"volume": str(target), "total_gb": gb(total),
                "used_gb": gb(used), "free_gb": gb(free)}
    except Exception:
        return {}


def accounts(home):
    """Every Claude Code account with sessions on this machine.

    Reported whether or not it has usage — an account signed in but unused is a
    real finding, not an absence of data.
    """
    out = []
    for d in find_config_dirs(home):
        root = d / "projects"
        files = list(root.rglob("*.jsonl"))
        main = [f for f in files
                if "subagents" not in f.relative_to(root).parts]
        out.append({
            "account": account_for(d, home),
            "config_dir": str(d),
            "profile_env": "unset (default)" if d.name == ".claude"
                           else f"CLAUDE_CONFIG_DIR={d}",
            "sessions": len(main),
            "transcript_files": len(files),
            "projects": sum(1 for p in root.iterdir() if p.is_dir()),
        })
    out.sort(key=lambda a: -a["transcript_files"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="machine folder to write hardware.json into")
    ap.add_argument("--label", default=None, help="machine name")
    ap.add_argument("--home", default=str(pathlib.Path.home()))
    args = ap.parse_args()

    home = pathlib.Path(args.home)
    hw = mac_hardware() if platform.system() == "Darwin" else generic_hardware()
    acct = accounts(home)

    label = args.label
    if not label and args.out:
        # Reuse the label the token scan already chose, so the two files agree.
        # paths.find: totals.json moved into machine-readable/, so the flat
        # join stopped finding it and this machine silently lost its label.
        t = paths.find(pathlib.Path(args.out), "totals.json")
        if t and t.exists():
            try:
                label = json.loads(t.read_text(encoding="utf-8")).get("machine")
            except Exception:
                pass
    label = label or platform.node()

    # THE ONE FACT THAT SEPARATES "MOVED" FROM "NEVER INSTALLED".
    # Every path in stores.py is home-relative, and $CODEX_HOME, $COPILOT_HOME,
    # $GEMINI_CLI_HOME, $CLAUDE_CONFIG_DIR, $XDG_CONFIG_HOME and %APPDATA% each
    # move a store off home. stores.resolve() now follows them, but a machine
    # whose scan reports zero for a tool is unreadable without knowing whether
    # any of them was set at the time — and four of this fleet's five machines
    # have never been scanned by anything that recorded it. Written per machine,
    # beside the hostname, because that is the scope of the fact.
    import stores as _stores
    report = {
        "machine": label,
        "hostname": platform.node(),
        "hardware": hw,
        "disk": disk(),
        "python": platform.python_version(),
        "store_env": _stores.environment(str(home)),
        "accounts": acct,
    }

    print(f"{label}")
    print(f"  {hw.get('chip')} · {hw.get('model_identifier')}")
    cores = hw.get("cpu_logical")
    if hw.get("cpu_performance_cores"):
        cores = (f"{cores} cores "
                 f"({hw['cpu_performance_cores']}P + {hw.get('cpu_efficiency_cores')}E)")
    print(f"  {cores} · {hw.get('memory_gb')} GB RAM"
          + (f" · {hw['gpu_cores']}-core GPU" if hw.get("gpu_cores") else ""))
    print(f"  {hw.get('os')} ({hw.get('os_build') or '-'})")
    d = report["disk"]
    if d:
        print(f"  disk {d['free_gb']} GB free of {d['total_gb']} GB")
    print(f"\n  {len(acct)} account(s) on this machine:")
    for a in acct:
        print(f"    {a['account']:34} {a['sessions']:>4} sessions  "
              f"{a['transcript_files']:>5} transcripts  {a['profile_env']}")

    if args.out:
        out = pathlib.Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        import sessions
        (paths.machine(out) / "hardware.json").write_text(
            json.dumps(sessions.stamped(report, mdir=out), indent=2), encoding="utf-8")
        sys.stderr.write(f"\nwrote {out}/hardware.json\n")


if __name__ == "__main__":
    main()
