#!/usr/bin/env python3
"""Snapshot both repos and reset the collective, before a fleet-wide rescan.

    python3 archive_all.py              # show what it would do
    python3 archive_all.py --yes        # do it

Run this ONCE, on one computer, when every machine is about to rescan. It
freezes the current state under archive/ and marks the derived documents stale
so the next `update.py` rebuilds them from whatever the machines report, rather
than leaving last week's figures sitting in the tables looking current.

WHAT IT DOES NOT DO

It never deletes a machine folder. Those `totals.json` files are the only
surviving record of usage whose transcripts have already been swept — deleting
one to get a "clean slate" destroys evidence that cannot be regenerated, and a
machine that then fails to rescan would silently vanish from the fleet total
instead of showing up as stale. Everything here is additive: archive, then
flag.

The three root reports and ALL-COMPUTERS.json are regenerated from the machine
folders on every run of `update.py`, so they are safe to mark stale — nothing
in them is a source.
"""

import argparse
import datetime
import hashlib
import json
import pathlib
import paths
import shutil

ROOT = pathlib.Path(__file__).parent
REPORTS = ("BY-COMPUTER.md", "BY-ACCOUNT.md", "BY-COMPANY.md", "ALL-COMPUTERS.json")
PER_MACHINE = ("totals.json", "sessions.json", "hardware.json", ".machine-id")


def digest(files):
    payload = b""
    for f in files:
        if f.is_file():
            payload += f.name.encode() + f.read_bytes()
    return hashlib.sha256(payload).hexdigest()[:12] if payload else None


def snap(files, dest, dry):
    d = digest(files)
    if not d:
        return None
    prev = sorted(p for p in dest.parent.iterdir() if p.is_dir()) if dest.parent.is_dir() else []
    if prev and (prev[-1] / ".digest").is_file():
        if (prev[-1] / ".digest").read_text().strip() == d:
            return "unchanged"
    if dry:
        return "would write"
    dest.mkdir(parents=True, exist_ok=True)
    for f in files:
        if f.is_file():
            shutil.copy2(f, dest / f.name)
    (dest / ".digest").write_text(d + "\n")
    return "written"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true", help="actually write; default is a dry run")
    ap.add_argument("--corpus", default=str(pathlib.Path.home() / "deadreckon-record"))
    args = ap.parse_args()
    dry = not args.yes
    stamp = datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H-%M-%S")
    iso = datetime.datetime.now().astimezone().isoformat(timespec="seconds")

    print(f"{'DRY RUN — nothing written' if dry else 'ARCHIVING'}   stamp {stamp}\n")

    machines = paths.machine_folders(ROOT)
    for m in machines:
        r = snap([p for p in (paths.find(m, n) for n in PER_MACHINE) if p],
                 ROOT / "archive" / m.name / stamp, dry)
        print(f"  {m.name:32} {r}")

    r = snap([p for p in (paths.find(ROOT, n) for n in REPORTS) if p],
             ROOT / "archive" / "reports" / stamp, dry)
    print(f"  {'(root reports)':32} {r}")

    # The corpus lives in another repo and is far too large to copy here. What
    # is worth keeping is each machine's MANIFEST — what was exported, when,
    # how much was redacted — which is small and is the part you would want to
    # compare against after a rescan.
    corpus = pathlib.Path(args.corpus)
    # Both locations. A glob for */MANIFEST.json alone stops finding it the
    # moment the export writes to machine-readable/, and an archive that
    # silently stops archiving is the failure this repo keeps having.
    mans = sorted(list(corpus.glob("*/MANIFEST.json"))
                  + list(corpus.glob("*/machine-readable/MANIFEST.json"))) \
        if corpus.is_dir() else []
    if mans:
        dest = ROOT / "archive" / "corpus-manifests" / stamp
        if not dry:
            dest.mkdir(parents=True, exist_ok=True)
        for f in mans:
            print(f"  corpus manifest: {f.parent.name:22} {'would copy' if dry else 'copied'}")
            if not dry:
                shutil.copy2(f, dest / f"{f.parent.name}.json")
    else:
        print(f"  corpus manifests                 none found at {corpus}")

    # Mark the derived documents stale. Only these — never a machine folder.
    pending = {
        "reset_at": iso,
        "reason": "fleet-wide rescan requested; figures below predate it",
        "machines_at_reset": {
            m.name: json.loads(paths.find(m, "totals.json").read_text(encoding="utf-8")).get("generated_at")
            for m in machines},
    }
    if not dry:
        (ROOT / ".fleet-reset.json").write_text(json.dumps(pending, indent=1) + "\n",
                                                encoding="utf-8")
    print(f"\n  .fleet-reset.json                {'would write' if dry else 'written'} "
          f"({len(machines)} machines flagged as pre-reset)")

    print(f"\n{'Would archive' if dry else 'Archived'} {len(machines)} machine folder(s), "
          f"the root reports, and {len(mans)} corpus manifest(s).")
    print("No machine folder was deleted — a totals.json is the only surviving")
    print("record of usage whose transcripts have already been swept.")
    if dry:
        print("\nRe-run with --yes to write.")
        return
    print("\nNow, on every computer:")
    print("    git pull && python3 update.py && python3 export_corpus.py")
    print("    git add -A && git commit -m rescan && git push")
    print("    cp -r corpus/* ~/deadreckon-record/ && cd ~/deadreckon-record")
    print("    git add -A && git commit -m rescan && git pull --rebase && git push")
    print("\nThen once, here:  python3 merge_corpus.py")


if __name__ == "__main__":
    main()
