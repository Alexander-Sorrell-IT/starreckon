#!/usr/bin/env python3
"""One command: scan this computer, then rebuild every root document.

    python3 update.py

That is the whole interface. It works out which machine folder belongs to this
computer, runs the three scanners into it, then re-derives the three root
reports, the data file and the README tables from every machine folder present.

    python3 update.py --machine dell-desktop-linux --label "Dell Desktop Linux"
    python3 update.py --combine-only     # someone else's folders changed
    python3 update.py --list             # which folder would this computer use?

WHICH FOLDER IS THIS COMPUTER?

Guessed, then remembered. The first run matches the hostname against the folders
in machines.json; once a folder exists it carries a `.machine-id` naming the host
that owns it, and later runs match on that instead. Guessing every time would
silently write one computer's numbers into another computer's folder the moment a
hostname changed, and the wrong-folder failure is invisible in the output — the
totals just quietly belong to the wrong machine.

If it cannot tell, it refuses and asks for --machine rather than picking.
"""

import argparse
import json
import paths
import pathlib
import platform
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).parent


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


def registered():
    f = ROOT / "machines.json"
    if not f.is_file():
        return []
    try:
        return json.loads(f.read_text(encoding="utf-8")).get("machines") or []
    except Exception:
        return []


def owned_folder(host):
    """A folder that has already claimed this host, by UUID first, then hostname.

    UUID match is tried first: a machine keeps its folder across OS reinstalls
    and hostname changes as long as the hardware UUID is stable (macOS) or the
    OS install is the same (Linux /etc/machine-id). Hostname match is kept as
    a fallback for folders written before the UUID field existed.
    """
    try:
        import install as _install
        current_uuid = _install.hardware_uuid()
    except Exception:
        current_uuid = None

    for d in sorted(p for p in ROOT.iterdir() if p.is_dir()):
        f = d / ".machine-id"
        if not f.is_file():
            continue
        try:
            info = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        # UUID match — strongest signal; survives hostname changes
        if current_uuid and info.get("hardware_uuid"):
            if info["hardware_uuid"].lower() == current_uuid.lower():
                return d.name
        # Hostname fallback — for folders written before UUID was added
        if info.get("hostname") == host:
            return d.name
    return None


def guess(host):
    """Best folder for this host: hardware UUID, registry lookup, or dynamic host slug."""
    claimed = owned_folder(host)
    if claimed:
        return claimed, "claimed by .machine-id (UUID or hostname)"
    
    # Check machine_registry.json for unique hardware UUID
    try:
        import install as _install
        current_uuid = _install.hardware_uuid()
    except Exception:
        current_uuid = None

    reg_file = ROOT / "machine_registry.json"
    if reg_file.is_file() and current_uuid:
        try:
            reg_data = json.loads(reg_file.read_text(encoding="utf-8"))
            if current_uuid in reg_data.get("machines", {}):
                return reg_data["machines"][current_uuid]["folder"], "registered by hardware UUID"
        except Exception:
            pass

    reg = registered()
    hs = slug(host)
    for e in reg:
        if current_uuid and e.get("hardware_uuid") == current_uuid:
            return e.get("folder"), "registered in machines.json by hardware UUID"
        f = e.get("folder", "")
        if hs and (hs in f or f in hs):
            return f, f"hostname {host!r} matches folder"

    # Default to 5-part dynamic unique hardware slug: <user>-<chassis>-<arch>-<os>-<uuid8>
    try:
        import platform_detect as _pd
        pi = _pd.detect()
        mid = (current_uuid[:8].lower() if current_uuid else None)
        dynamic_slug = _install._suggest_folder(pi, machine_id=mid)
    except Exception:
        dynamic_slug = hs or slug(f"{platform.node()}-{platform.system().lower()}")
    return dynamic_slug, "derived dynamically from 5-part hardware, user, and UUID uniqueifier"

def stamp_path(stamp):
    """`2026-08-21T17-08-14` -> `2026/08/W34/21/17-08-14` (or flat ISO if parsing fails)."""
    import datetime
    try:
        d = datetime.datetime.strptime(stamp, "%Y-%m-%dT%H-%M-%S")
        return f"{d.year:04d}/{d.month:02d}/W{d.isocalendar()[1]:02d}/{d.day:02d}/{d:%H-%M-%S}"
    except Exception:
        return stamp


def archive(_folder, stamp):
    """Snapshot this scan and the reports it produced, under archive/.

    The transcripts these numbers come from are deleted after
    cleanupPeriodDays, so a scan is the only durable record of what a session
    cost. Git already holds that history, but reading it means archaeology
    through diffs; this keeps each scan as a plain dated folder you can open.

    Skips writing when the content is byte-identical to the previous snapshot,
    so re-running update.py on an idle machine does not fill the archive with
    copies. Only real change is recorded.
    """
    import hashlib
    import shutil
    root = ROOT / "archive"
    out = []

    def snap(src_files, dest_dir):
        payload = b""
        for f in src_files:
            if f.is_file():
                payload += f.name.encode() + f.read_bytes()
        if not payload:
            return None
        digest = hashlib.sha256(payload).hexdigest()[:12]
        parent = dest_dir.parent
        if parent.is_dir():
            prev = sorted(d for d in parent.iterdir() if d.is_dir())
            if prev and (prev[-1] / ".digest").is_file():
                if (prev[-1] / ".digest").read_text().strip() == digest:
                    return None          # nothing changed since the last snapshot
        dest_dir.mkdir(parents=True, exist_ok=True)
        for f in src_files:
            if f.is_file():
                shutil.copy2(f, dest_dir / f.name)
        (dest_dir / ".digest").write_text(digest + "\n")
        return dest_dir

    # Every machine folder present, not just the one scanned. Pulling another
    # computer's scan brings data that exists nowhere else once its transcripts
    # expire, so it gets archived here too rather than only on the machine that
    # produced it. The digest check means an unchanged folder costs nothing.
    # paths.find, not a flat join: after the human/machine split these live in
    # <machine>/machine-readable/, so the old path matched nothing and the
    # archive silently stopped recording anything at all. It reported "nothing
    # changed since the last snapshot" — which is what an empty loop looks like.
    for mf in paths.machine_folders(ROOT):
        got = snap([p for p in (paths.find(mf, n) for n in
                                ("totals.json", "sessions.json", "hardware.json")) if p],
                   root / mf.name / stamp)
        if got:
            out.append(f"archive/{mf.name}/{stamp}")
    got = snap([p for p in (paths.find(ROOT, n) for n in
                            ("BY-COMPUTER.md", "BY-ACCOUNT.md", "BY-COMPANY.md",
                             "STATS.md", "LIFETIME.md", "ALL-COMPUTERS.json")) if p],
               root / "reports" / stamp)
    if got:
        out.append(f"archive/reports/{stamp}")
    return out


def run(cmd):
    print(f"  $ {' '.join(cmd)}")
    r = subprocess.run([sys.executable] + cmd, cwd=ROOT,
                       capture_output=True, text=True)
    if r.returncode:
        sys.stderr.write(r.stdout[-2000:] + r.stderr[-2000:])
        raise SystemExit(f"FAILED: {' '.join(cmd)} (exit {r.returncode})")
    return r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", help="folder for this computer")
    ap.add_argument("--label", help="display name, first run only")
    ap.add_argument("--combine-only", action="store_true",
                    help="skip scanning; just re-derive the root documents")
    ap.add_argument("--list", action="store_true",
                    help="show which folder this computer resolves to and exit")
    args = ap.parse_args()

    host = platform.node()
    folder, why = (args.machine, "given on the command line") if args.machine else guess(host)

    if args.list:
        print(f"hostname : {host}")
        print(f"folder   : {folder or '(undetermined)'}   {why}")
        print("registered:")
        for e in registered():
            d = ROOT / e["folder"]
            # paths.find, not a flat join. This read the pre-split location
            # and so reported every computer as never-scanned, including the
            # three that had just been scanned — the same mistake that had
            # already been fixed in archive() and the scanned-count line, in a
            # third place nobody had looked.
            print(f"  {'[scanned]' if paths.find(d, 'totals.json') else '[ never ]'} "
                  f"{e['folder']:32s} {e.get('label','')}")
        return

    # Before anything is measured. check_consistency.py runs at the END and
    # proves a scan's slices add up — but a reader that silently finds nothing
    # partitions perfectly, so consistency cannot catch broken code. These are
    # the cases where a number came out wrong, frozen as assertions. Running
    # them first means a regression stops the run instead of publishing.
    #
    # test_readers.py is the second of the two, and it is the one that covers
    # sessions.py. test_scanner.py tests analyze_tokens.py — a different
    # implementation of Claude-only counting — so for a long time nothing here
    # ever executed a READER: `read_copilot -> return []` scored 45 checks, 0
    # failed, and so did dropping either of read_claude's two dedups.
    for suite, what in (("test_scanner.py", "analyze_tokens"),
                        ("test_readers.py", "the sessions.py readers")):
        t = subprocess.run([sys.executable, suite], cwd=ROOT,
                           capture_output=True, text=True)
        if t.returncode:
            sys.stdout.write(t.stdout)
            raise SystemExit(
                f"\nSELF-TEST FAILED ({suite}, {what}) — a bug this repo "
                f"already fixed has come back.\nNothing was scanned. Fix the "
                f"failure above before trusting any number.")
        print(t.stdout.strip().splitlines()[-1] if t.stdout.strip()
              else f"{suite} ok")

    if not args.combine_only:
        if not folder:
            raise SystemExit(
                f"Cannot tell which folder belongs to this computer (hostname "
                f"{host!r}).\nRe-run with:  python3 update.py --machine "
                f"<folder> --label \"<Name>\"\nRegistered folders: "
                + ", ".join(e["folder"] for e in registered()))
        label = args.label
        if not label:
            for e in registered():
                if e.get("folder") == folder:
                    label = e.get("label")
            existing = paths.find(ROOT / folder, "totals.json")
            if not label and existing and existing.is_file():
                try:
                    label = json.loads(existing.read_text(encoding="utf-8")).get("machine")
                except Exception:
                    pass
            label = label or folder

        print(f"scanning this computer -> {folder}/  ({why}; label {label!r})")
        (ROOT / folder).mkdir(exist_ok=True)
        run(["analyze_tokens.py", "--out", folder, "--label", label])
        run(["sessions.py", "--out", folder])
        run(["check_hardware.py", "--out", folder])
        # Claim the folder so later runs never have to guess again.
        # UUID is included so identity survives OS reinstalls and hostname
        # changes. Hostname is kept for backward compatibility with machines
        # that check it directly.
        import install as _install
        _uuid = _install.hardware_uuid()
        mid = {"hostname": host, "folder": folder, "label": label,
               "platform": platform.platform()}
        if _uuid:
            mid["hardware_uuid"] = _uuid
        (ROOT / folder / ".machine-id").write_text(
            json.dumps(mid, indent=1) + "\n", encoding="utf-8")
    else:
        print("skipping scan (--combine-only)")

    print("re-deriving root documents from every machine folder")
    run(["combine.py"])
    print(run(["stats_page.py"]).strip())
    run(["fun_stats.py"])
    run(["by_cli_report.py"])
    print(run(["monthly.py"]).strip().splitlines()[-1])
    try:
        print(run(["corpus_reports.py"]).strip().splitlines()[-1])
    except SystemExit:
        print("  corpus reports skipped (no ~/deadreckon-record)")

    # Publishing a wrong number is the failure this repo exists to prevent, so
    # every rebuild proves its own arithmetic before claiming to be done.
    print("\nverifying the published numbers add up")
    v = subprocess.run([sys.executable, "check_consistency.py"], cwd=ROOT,
                       capture_output=True, text=True)
    sys.stdout.write(v.stdout)
    if v.returncode:
        raise SystemExit("\nCONSISTENCY CHECK FAILED — the documents were written "
                         "but a slice does not add up. Do not quote these numbers "
                         "until the failure above is explained.")

    import datetime
    stamp = datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H-%M-%S")
    wrote = archive(folder, stamp)
    if wrote:
        print("\narchived: " + ", ".join(wrote))
    else:
        print("\narchive: nothing changed since the last snapshot")

    # After the archive, not before: the scorecard checks that a dated
    # snapshot exists, and running it first made it report the truth ("0
    # snapshots") and then abort the run that was about to write one.
    #
    # And it reports, it does not gate. check_consistency.py is the gate — it
    # refuses to publish arithmetic that does not add up. A scorecard failing
    # means something about this run is worth looking at, which is exactly when
    # you want the rest of the output rather than an aborted command.
    if not args.combine_only:
        sc = subprocess.run([sys.executable, "scorecard.py"], cwd=ROOT,
                            capture_output=True, text=True)
        tail = [l for l in sc.stdout.strip().splitlines() if "checks" in l]
        print("\nscorecard: " + (tail[-1].strip() if tail else "did not run"))
        if sc.returncode:
            for line in sc.stdout.splitlines():
                if line.strip().startswith("\u274c"):
                    print("  " + line.strip())

    # Same stale path: this read 0 of 6 scanned on a fleet where five had
    # been scanned, because it looked for the pre-split location.
    have = sum(1 for e in registered() if paths.find(ROOT / e["folder"], "totals.json"))
    total = len(registered()) or have
    print("\ndone. BY-COMPUTER.md, BY-ACCOUNT.md, BY-COMPANY.md, ALL-COMPUTERS.json\n"
          "      and the README tables are current.")
    print(f"{have} of {total} registered computers scanned."
          + ("" if have == total else "  Totals are a floor until the rest are in."))
    print("commit and push so the other computers pick it up.")


if __name__ == "__main__":
    main()
