#!/usr/bin/env python3
"""Generate human-readable/BY-CLI.md — per-CLI totals across every machine.

    python3 by_cli_report.py           write human-readable/BY-CLI.md
    python3 by_cli_report.py --check   verify the file is current, exit 1 if not

WHY THIS REPORT EXISTS

BY-COMPUTER.md answers "how many tokens on each machine."
BY-ACCOUNT.md answers "how many tokens per Claude account."
BY-COMPANY.md answers "which AI provider served how much."

None of them answers "how does Copilot's token use compare across machines" or
"which machines have Gemini data at all." BY-CLI.md answers that: one row per
CLI, one column per machine, totals on the right.

THE ★ / † DISTINCTION

Claude Code has a vendor lifetime counter on disk (stats-cache.json) that
survives transcript deletion, so its figure is a TRUE LIFETIME (★).

Every other CLI has no persistent counter: the ledger is the only record, and
it starts from when the daemon was first run on each machine (†). The report
makes this explicit in every row so a reader never conflates the two.

WHAT IS NOT IN THIS REPORT

Provider attribution (Anthropic / Google / OpenAI / DeepSeek): that is
BY-COMPANY.md's job. CLI and provider are deliberately kept separate — Copilot
runs Claude models, so a copilot row in this report is Copilot spend, while the
same tokens appear under Anthropic in BY-COMPANY.md.
"""

import datetime
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT))
import paths
import token_ledger

OUTPUT = "BY-CLI.md"
FINGERPRINT_KEY = "by_cli_report_inputs"


def _human(n):
    if n >= 1e9:
        return f"{n/1e9:.2f}B"
    if n >= 1e6:
        return f"{n/1e6:.1f}M"
    if n >= 1e3:
        return f"{n/1e3:.0f}K"
    return str(n)


def _load_sessions(root):
    """sessions.json per machine: {machine_folder: {cli: tokens}}"""
    by_machine = {}
    for mdir, f in paths.iter_machine_files(root, "sessions.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        per_cli = {}
        for s in d.get("sessions", []):
            cli = s.get("cli") or "unknown"
            per_cli[cli] = per_cli.get(cli, 0) + s.get("total", 0)
        by_machine[mdir.name] = {
            "label": d.get("machine", mdir.name),
            "generated_at": d.get("generated_at", ""),
            "by_cli": per_cli,
        }
    return by_machine


def _load_ledger_starts(root):
    """daemon_started per machine from their cli-config.json."""
    out = {}
    for mdir in paths.machine_folders(root):
        cfg_file = mdir / "cli-config.json"
        if not cfg_file.is_file():
            # Also check repo root (this machine's config lives there)
            cfg_file = root / "cli-config.json"
        if cfg_file.is_file():
            try:
                cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
                started = cfg.get("daemon", {}).get("started")
                if started:
                    out[mdir.name] = started[:10]
            except Exception:
                pass
    return out


def _fingerprint(by_machine):
    """Stable string summarising the inputs — changes when any scan changes."""
    parts = []
    for folder in sorted(by_machine):
        m = by_machine[folder]
        parts.append(f"{folder}:{m.get('generated_at', '')}:"
                     f"{sum(m['by_cli'].values())}")
    return "|".join(parts)


def _current_fingerprint_in_file(p):
    """Read the fingerprint comment from an existing BY-CLI.md."""
    if not p.is_file():
        return None
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.startswith("<!-- fingerprint:"):
            return line.split(":", 1)[1].strip().rstrip(" -->")
    return None


def build(root):
    """Build BY-CLI.md content. Returns (text, fingerprint)."""
    by_machine = _load_sessions(root)
    daemon_starts = _load_ledger_starts(root)

    if not by_machine:
        return None, None

    # All CLIs seen across any machine
    all_clis = set()
    for m in by_machine.values():
        all_clis.update(m["by_cli"].keys())
    all_clis.discard("unknown")

    # Sort CLIs by fleet total descending
    fleet_total = {cli: sum(m["by_cli"].get(cli, 0)
                            for m in by_machine.values())
                   for cli in all_clis}
    sorted_clis = sorted(all_clis, key=lambda c: -fleet_total[c])

    # Machines sorted by total tokens descending
    machine_order = sorted(by_machine.keys(),
                           key=lambda f: -sum(by_machine[f]["by_cli"].values()))

    fp = _fingerprint(by_machine)
    generated = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")

    lines = [
        f"<!-- fingerprint: {fp} -->",
        "# BY-CLI — token usage per tool across the fleet",
        "",
        "_Each row is one AI coding tool. Each column is one machine. "
        "The total column is the fleet sum for that tool._",
        "",
        "**★ Claude Code** — true lifetime: the vendor's own counter on disk "
        "(stats-cache.json) survives transcript deletion. The ledger adds "
        "sessions the vendor counter may not have seen.",
        "",
        "**† All other CLIs** — from daemon start on each machine. No vendor "
        "counter exists; the ledger is the only record. The date shown is when "
        "monitoring began on that machine.",
        "",
    ]

    # Table header: CLI | Machine1 | Machine2 | ... | Fleet total
    header_machines = [by_machine[f]["label"] for f in machine_order]
    lines.append("| CLI | " + " | ".join(header_machines) + " | Fleet total |")
    lines.append("|---|" + "---:|" * (len(machine_order) + 1))

    fleet_grand = 0
    machine_totals = {f: 0 for f in machine_order}

    for cli in sorted_clis:
        marker = token_ledger.cli_marker(cli)
        row_total = fleet_total[cli]
        fleet_grand += row_total
        cells = []
        for folder in machine_order:
            v = by_machine[folder]["by_cli"].get(cli, 0)
            machine_totals[folder] += v
            cells.append(_human(v) if v else "—")
        lines.append(f"| {cli} {marker} | " + " | ".join(cells) +
                     f" | **{_human(row_total)}** |")

    # Fleet total row
    total_cells = [_human(machine_totals[f]) for f in machine_order]
    lines.append("| **Total** | " + " | ".join(total_cells) +
                 f" | **{_human(fleet_grand)}** |")
    lines.append("")

    # Per-machine scanned timestamps
    lines += ["## When each machine was last scanned", ""]
    lines.append("| Machine | Last scan | Daemon start (†) |")
    lines.append("|---|---|---|")
    for folder in machine_order:
        m = by_machine[folder]
        scanned = (m.get("generated_at") or "")[:10] or "unknown"
        started = daemon_starts.get(folder, "—")
        lines.append(f"| {m['label']} | {scanned} | {started} |")
    lines.append("")

    # Per-machine CLI breakdown
    lines += ["## Per-machine breakdown", ""]
    for folder in machine_order:
        m = by_machine[folder]
        label = m["label"]
        started = daemon_starts.get(folder)
        lines += [f"### {label}", ""]
        if started:
            lines.append(f"_Daemon running since {started[:10]} "
                         f"(† baseline for non-Claude CLIs on this machine)_")
            lines.append("")
        cli_rows = sorted(m["by_cli"].items(), key=lambda x: -x[1])
        if cli_rows:
            machine_sum = sum(v for _, v in cli_rows)
            lines += ["| CLI | Tokens | Share | |",
                      "|---|---:|---:|---|"]
            for cli, v in cli_rows:
                if not v:
                    continue
                marker = token_ledger.cli_marker(cli)
                pct = v / machine_sum * 100 if machine_sum else 0
                lines.append(f"| {cli} | {v:,} | {pct:.1f}% | {marker} |")
            lines.append("")

    lines += [
        "---",
        f"_Generated by `by_cli_report.py` on {generated}. "
        f"Source: `sessions.json` from each machine folder. "
        f"Do not edit by hand — regenerate with `python3 run.py rebuild`._",
    ]

    return "\n".join(lines) + "\n", fp


def write(root=None):
    root = pathlib.Path(root) if root else ROOT
    text, fp = build(root)
    if text is None:
        print("  BY-CLI.md: no sessions.json found — skipped", file=sys.stderr)
        return False
    out = paths.human(root) / OUTPUT
    out.write_text(text, encoding="utf-8")
    print(f"  wrote {out.relative_to(root)}", file=sys.stderr)
    return True


def check(root=None):
    """Return True if BY-CLI.md is current, False if stale or missing."""
    root = pathlib.Path(root) if root else ROOT
    _, fp = build(root)
    if fp is None:
        return True   # no data, nothing to check
    out = paths.human(root) / OUTPUT
    return _current_fingerprint_in_file(out) == fp


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="verify BY-CLI.md is current, exit 1 if stale")
    ap.add_argument("--root", help="repo root (default: this file's directory)")
    args = ap.parse_args()

    r = pathlib.Path(args.root) if args.root else ROOT
    if args.check:
        ok = check(r)
        print("  BY-CLI.md: " + ("current" if ok else "STALE or MISSING"))
        sys.exit(0 if ok else 1)

    ok = write(r)
    sys.exit(0 if ok else 1)
