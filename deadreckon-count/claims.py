#!/usr/bin/env python3
"""claims.py — every published statement is a registered claim.

P5.1: A document with no registered claim is a finding. A claim with no
document is a lie. This file is the machine-readable contract between the
generators that write the documents and the gate that reads them.

    python3 claims.py           # list all claims and whether each doc exists
    python3 claims.py --check   # exit 1 if any claim is unverifiable

STRUCTURE

Each claim has:
    doc         relative path to the published document
    generator   script that writes it (the one responsible for its truth)
    what        human-readable description of what the document asserts
    field       optional: the key or regex the gate checks in check_consistency

A document with no claim registered here is itself a finding — it makes
assertions nobody has contracted to verify.
"""

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent

# ---------------------------------------------------------------------------
# The registry
# ---------------------------------------------------------------------------

CLAIMS = [
    # ---- README.md --------------------------------------------------------
    {
        "doc": "README.md",
        "generator": "combine.py",
        "what": "Fleet grand total matches sum of machine totals.json",
        "field": "fleet on disk now",
    },
    {
        "doc": "README.md",
        "generator": "combine.py",
        "what": "Per-machine table lists every machine folder present",
        "field": "CLI table: machines",
    },

    # ---- human-readable/BY-COMPUTER.md ------------------------------------
    {
        "doc": "human-readable/BY-COMPUTER.md",
        "generator": "stats_page.py",
        "what": "Headline Claude Code total matches sum of grand_total_tokens",
        "field": "headline: Claude Code",
    },
    {
        "doc": "human-readable/BY-COMPUTER.md",
        "generator": "stats_page.py",
        "what": "Per-machine floor table row matches each machine's grand_total",
        "field": "totals",
    },

    # ---- human-readable/BY-ACCOUNT.md -------------------------------------
    {
        "doc": "human-readable/BY-ACCOUNT.md",
        "generator": "stats_page.py",
        "what": "Grand total matches sum of grand_total_tokens across machines",
        "field": "headline: Claude Code",
    },
    {
        "doc": "human-readable/BY-ACCOUNT.md",
        "generator": "stats_page.py",
        "what": "Per-account rows sum to the headline total",
        "field": "reconciliation: per account",
    },

    # ---- human-readable/BY-COMPANY.md -------------------------------------
    {
        "doc": "human-readable/BY-COMPANY.md",
        "generator": "stats_page.py",
        "what": "Headline total matches sum of grand_total_tokens",
        "field": "headline: every CLI",
    },

    # ---- human-readable/BY-CLI.md ----------------------------------------
    {
        "doc": "human-readable/BY-CLI.md",
        "generator": "by_cli_report.py",
        "what": "Per-CLI token totals match fleet sessions.json CLI sums",
        "field": None,
    },

    # ---- human-readable/STATS.md ------------------------------------------
    {
        "doc": "human-readable/STATS.md",
        "generator": "fun_stats.py",
        "what": "Every-CLI total matches fleet sessions.json sum",
        "field": "three totals: every CLI",
    },
    {
        "doc": "human-readable/STATS.md",
        "generator": "fun_stats.py",
        "what": "Claude Code only row matches sum of grand_total_tokens",
        "field": "three totals: Claude Code only",
    },
    {
        "doc": "human-readable/STATS.md",
        "generator": "fun_stats.py",
        "what": "Per-machine section exists for every machine with sessions",
        "field": "<machine> has no section",
    },

    # ---- human-readable/LIFETIME.md ---------------------------------------
    {
        "doc": "human-readable/LIFETIME.md",
        "generator": "monthly.py",
        "what": "Lifetime total is at least as large as the scan total",
        "field": "headline: tokens",
    },

    # ---- human-readable/THIS-MONTH.md -------------------------------------
    {
        "doc": "human-readable/THIS-MONTH.md",
        "generator": "monthly.py",
        "what": "Current-month total matches sessions in the current calendar month",
        "field": "headline: tokens",
    },

    # ---- machine-readable/ALL-COMPUTERS.json ------------------------------
    {
        "doc": "machine-readable/ALL-COMPUTERS.json",
        "generator": "combine.py",
        "what": "JSON array of machine objects whose totals match totals.json files",
        "field": None,
    },

    # ---- machine-readable/lifetime.json -----------------------------------
    {
        "doc": "machine-readable/lifetime.json",
        "generator": "monthly.py",
        "what": "lifetime.total >= scan total (ledger floor)",
        "field": None,
    },

    # ---- machine-readable/stats.json --------------------------------------
    {
        "doc": "machine-readable/stats.json",
        "generator": "fun_stats.py",
        "what": "total_tokens matches fleet sessions.json sum",
        "field": None,
    },
]

# ---------------------------------------------------------------------------

def check(root=ROOT):
    """Return (ok, findings) where findings is a list of problem strings."""
    findings = []
    for c in CLAIMS:
        p = root / c["doc"]
        if not p.is_file():
            findings.append(
                f"MISSING  {c['doc']}  "
                f"(generator: {c['generator']}, claim: {c['what']})"
            )
    # A document on disk with no claim is also a finding.
    published = {
        "README.md",
        "human-readable/BY-COMPUTER.md",
        "human-readable/BY-ACCOUNT.md",
        "human-readable/BY-COMPANY.md",
        "human-readable/BY-CLI.md",
        "human-readable/STATS.md",
        "human-readable/LIFETIME.md",
        "human-readable/THIS-MONTH.md",
        "machine-readable/ALL-COMPUTERS.json",
        "machine-readable/lifetime.json",
        "machine-readable/stats.json",
    }
    claimed = {c["doc"] for c in CLAIMS}
    unclaimed = sorted(published - claimed)
    for doc in unclaimed:
        if (root / doc).is_file():
            findings.append(f"UNCLAIMED  {doc}  — no registered claim")
    return not findings, findings


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if any claim is unverifiable or any doc unclaimed")
    ap.add_argument("--json", action="store_true",
                    help="print claims as JSON")
    args = ap.parse_args()

    if args.json:
        print(json.dumps(CLAIMS, indent=2))
        return 0

    ok, findings = check()

    print(f"\n  {len(CLAIMS)} registered claim(s) across "
          f"{len({c['doc'] for c in CLAIMS})} document(s)\n")
    for c in CLAIMS:
        p = ROOT / c["doc"]
        status = "✓" if p.is_file() else "✗ MISSING"
        print(f"  {status:10}  {c['doc']:45}  {c['what'][:55]}")

    if findings:
        print(f"\n  {len(findings)} finding(s):")
        for f in findings:
            print(f"    {f}")
    else:
        print("\n  every registered document is present")

    if args.check:
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
