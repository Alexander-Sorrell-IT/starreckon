#!/usr/bin/env python3
"""One command with eight verbs. Acts on BOTH repositories.

    python3 run.py update      scan this computer, export, rebuild everything
    python3 run.py rebuild     no scan — delete every derived file and recompute
    python3 run.py archive     snapshot today into archive/, then rescan
    python3 run.py retire      move everything to testing-archive/, start clean
    python3 run.py reset       retire, PLUS the working directories — production start
    python3 run.py status      what state is all of this in
    python3 run.py sync        pull, scan, rebuild, commit, push — the daemon's verb
    python3 run.py combine     rebuild the rollups from the folders already here

Twelve scripts is not an interface. These are the things anyone actually
does, and each one does the whole job across `deadreckon-count` and `deadreckon-record`
rather than leaving half of it for you to remember.

WHY `rebuild` DELETES FIRST

It removes every generated file before regenerating, instead of overwriting in
place. Twice today a generator was changed to write somewhere new while a reader
still looked at the old location, and the stale copy won — a scan sat next to a
file from hours earlier and nothing noticed. Deleting first makes that
impossible: a file that is not rewritten is simply gone, which is loud.

Authored files are never touched: machines.json, accounts.json, README.md, and
anything under a machine's own scan output that a rebuild cannot recreate.
"""

import argparse
import datetime
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT))
import paths

CORPUS = pathlib.Path.home() / "deadreckon-record"

# Who owns both repositories. Every push and every corpus upload must go through
# this account. With a different account active `gh` returns 404 for a repo that
# exists, and that 404 looks byte-identical to the repo having been deleted.
# That mistake was actually made here — conclusion drawn: "the corpus does not
# exist, there is no offsite copy" — about a 1.49 GB repo holding all five
# machines' archives.
REPO_OWNER = "matrixbuilderops"
COUNT_REPO = f"{REPO_OWNER}/deadreckon-count"
RECORD_REPO = f"{REPO_OWNER}/deadreckon-record"


def _gh(args, **kw):
    return subprocess.run(["gh"] + args, capture_output=True, text=True, **kw)


def _git(repo_path, *args):
    return subprocess.run(
        ["git", "-C", str(repo_path)] + list(args),
        capture_output=True, text=True).stdout.strip()


def who_am_i():
    """Print who is about to push — OS user, git identity, gh account — for
    each repo, as one readable block.

    FOUR LAYERS, ALL SHOWN.

      OS user    whoami — the process owner. Matters on shared machines and
                 inside containers where the home directory may not be whose
                 you think it is.

      git name   user.name in the repo's own config (not the global fallback,
                 which can differ per repo). What appears in the commit object.

      git email  user.email — the identity git signs the commit with.

      gh account the GitHub login that will do the API call, the push and the
                 corpus upload. On a machine with two gh logins, the active one
                 is whatever the last `gh auth switch` left it at.

    Shown unconditionally, not only on failure. A correct identity printed
    and read is evidence; one that is assumed is not.
    """
    import getpass, os as _os

    os_user = getpass.getuser()
    gh_active = "—"
    if shutil.which("gh"):
        r = _gh(["api", "user", "-q", ".login"])
        if r.returncode == 0:
            gh_active = r.stdout.strip() or "—"
        else:
            gh_active = "(not authenticated)"

    print(f"  {'':4}{'OS user':<14} {'git name':<22} {'git email':<32} gh account")
    for label, repo_path in (
        ("deadreckon-count ", ROOT),
        ("deadreckon-record", CORPUS),
    ):
        if not (repo_path / ".git").is_dir():
            print(f"  {label}  — not a checkout")
            continue
        name  = _git(repo_path, "config", "user.name")  or "(not set)"
        email = _git(repo_path, "config", "user.email") or "(not set)"
        remote = _git(repo_path, "remote", "get-url", "origin")
        print(f"  {label}  {os_user:<14} {name:<22} {email:<32} {gh_active}")
        # Flag anything that doesn't look right — but always print the line
        # above first so you can see what is actually set.
        norm = remote.lower().replace("git@", "").replace(":", "/")
        norm = norm.removesuffix(".git").strip("/")
        expected = f"github.com/{REPO_OWNER}/"
        if norm and expected.lower() not in norm:
            print(f"    !! remote origin is {remote!r}")
            print(f"       expected something under github.com/{REPO_OWNER}/")
            print(f"       fix:  git -C {repo_path} remote set-url origin "
                  f"https://github.com/{REPO_OWNER}/{repo_path.name}.git")
        if "(not set)" in (name, email):
            print(f"    !! git identity incomplete for {label}")
            if name == "(not set)":
                print(f"       fix:  git -C {repo_path} config user.name 'Your Name'")
            if email == "(not set)":
                print(f"       fix:  git -C {repo_path} config user.email 'you@example.com'")
    if gh_active in ("—", "(not authenticated)"):
        print(f"    !! gh is not authenticated — corpus push/pull will fail")
        print(f"       fix:  gh auth login")
    elif gh_active.lower() != REPO_OWNER.lower():
        print(f"    !! gh active account is {gh_active!r}, not {REPO_OWNER!r}")
        print(f"       both repos are private — a 404 from the wrong account")
        print(f"       looks identical to the repo not existing")
        print(f"       fix:  gh auth switch --user {REPO_OWNER}")


def account_check():
    """Collect warnings about identity mismatches, for callers that need a list.

    who_am_i() is the human-readable version. This returns the same findings
    as a list of strings so callers can decide whether to block or just warn.
    """
    warnings = []

    if shutil.which("gh"):
        r = _gh(["api", "user", "-q", ".login"])
        active = r.stdout.strip() if r.returncode == 0 else None
        if active and active.lower() != REPO_OWNER.lower():
            warnings.append(
                f"gh active account is {active!r}, not {REPO_OWNER!r}.\n"
                f"  Fix:  gh auth switch --user {REPO_OWNER}")
        elif not active:
            warnings.append(
                f"gh is not authenticated — fix:  gh auth login")
    else:
        warnings.append("gh is not installed")

    for label, repo_path, expected_remote in (
        ("deadreckon-count",  ROOT,   f"github.com/{COUNT_REPO}"),
        ("deadreckon-record", CORPUS, f"github.com/{RECORD_REPO}"),
    ):
        if not (repo_path / ".git").is_dir():
            continue
        name  = _git(repo_path, "config", "user.name")
        email = _git(repo_path, "config", "user.email")
        remote = _git(repo_path, "remote", "get-url", "origin")
        norm = remote.lower().replace("git@", "").replace(":", "/")
        norm = norm.removesuffix(".git").strip("/")
        if norm and expected_remote.lower() not in norm:
            warnings.append(
                f"{label}: remote is {remote!r}, expected {expected_remote!r}")
        if not email:
            warnings.append(
                f"{label}: git user.email not set")

    return warnings

# Derived by some generator, safe to delete because `rebuild` recreates them.
# Deliberately NOT here: totals/sessions/hardware (a scan produces those and a
# rebuild cannot), .machine-id, and the CSVs that come with a scan.
DERIVED_ROOT = ["BY-COMPUTER.md", "BY-ACCOUNT.md", "BY-COMPANY.md", "BY-CLI.md",
                "STATS.md", "LIFETIME.md", "THIS-MONTH.md", "COVERAGE.md",
                "ALL-COMPUTERS.json", "stats.json", "lifetime.json"]
DERIVED_MACHINE = ["STATS.md", "SCORECARD.md", "stats.json", "scorecard.json"]


def sh(cmd, where=ROOT, quiet=False):
    r = subprocess.run([sys.executable] + cmd, cwd=where,
                       capture_output=True, text=True)
    if r.returncode and not quiet:
        sys.stdout.write(r.stdout[-1500:])
        sys.stderr.write(r.stderr[-800:])
        raise SystemExit(f"FAILED: {' '.join(cmd)}")
    return r.stdout


def wipe_derived(root, label, hold=None):
    """Remove every derived file. With `hold`, move rather than delete.

    WHY `hold` EXISTS

    `rebuild` deletes before it regenerates, for the reason at the top of this
    file. What was never true is that it finishes. The gate can FAIL between the
    delete and the write, and when it does the run aborts having removed twelve
    per-machine documents and written none — a tree in a state no verb produced
    and no verb repairs. That happened, and the recovery was `git checkout` on a
    list of paths read out of `git status`, by hand.

    So the files are moved into a holding directory instead of unlinked, and
    `rebuild` puts them back if the regenerate step raises. Deleting first is
    still what the tree sees; it is only the failure path that changed.
    """
    n = 0

    def take(p):
        nonlocal n
        if hold is None:
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
        else:
            dest = hold / p.relative_to(root)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), str(dest))
        n += 1

    for name in DERIVED_ROOT:
        p = paths.find(root, name)
        if p and p.is_file():
            take(p)
    for mdir in paths.machine_folders(root):
        for name in DERIVED_MACHINE:
            p = paths.find(mdir, name)
            if p and p.is_file():
                take(p)
    md = paths.machine(root) / "months"
    if md.is_dir():
        take(md)
    print(f"  {label:14} removed {n} derived file(s)")
    return n


def restore_held(hold, root, label):
    """Put back what `wipe_derived` moved aside.

    Every held path is a file under the same relative path it came from —
    `months/` was moved as a directory, but its contents arrive here as files,
    so recreating the parents restores it too. A file the regenerate step
    already wrote is NOT overwritten: that one is newer than what we hold.
    """
    n = 0
    for src in sorted(p for p in hold.rglob("*") if p.is_file()):
        dest = root / src.relative_to(hold)
        if dest.exists():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        n += 1
    print(f"  {label:14} restored {n} derived file(s) — the tree is as it was")
    return n


def rebuild(scan=False, machine=None, label=None):
    if scan:
        cmd = ["update.py"]
        if machine:
            cmd += ["--machine", machine]
        if label:
            cmd += ["--label", label]
        out = sh(cmd)
        for line in out.strip().splitlines():
            if any(k in line for k in ("checks", "scorecard", "archived", "of 6",
                                       "of 5", "lifetime", "corpus holds")):
                print("  " + line.strip())
    else:
        # Held aside rather than deleted, so a gate FAIL leaves the tree as it
        # was found instead of stripped. See wipe_derived().
        hold = pathlib.Path(tempfile.mkdtemp(prefix="deadreckon-rebuild-"))
        try:
            wipe_derived(ROOT, "deadreckon-count", hold / "count")
            if CORPUS.is_dir():
                wipe_derived(CORPUS, "deadreckon-record", hold / "record")
            out = sh(["update.py", "--combine-only"])
        except BaseException:
            print("\n  rebuild did not finish — putting the derived files back\n")
            if (hold / "count").is_dir():
                restore_held(hold / "count", ROOT, "deadreckon-count")
            if (hold / "record").is_dir():
                restore_held(hold / "record", CORPUS, "deadreckon-record")
            raise
        finally:
            shutil.rmtree(hold, ignore_errors=True)
        for line in out.strip().splitlines():
            if any(k in line for k in ("checks", "wrote", "lifetime", "corpus holds")):
                print("  " + line.strip())


# WORKING DIRECTORIES — regenerable, and none of them is small.
#
# `retire` was written to clear the DOCUMENTS: archive/, the derived reports,
# machine folders left on a superseded scanner. It never touched the working
# directories, because on the machine it was written on they were empty. They
# are not empty now — 3.8 GB on this one — and every byte of it is output that
# some verb writes again on demand. A production start that leaves them in
# place is a production start carrying an afternoon of development exports.
REGENERABLE = {
    "corpus":  "export_corpus.py output, staged for `corpus_ship.py pack`",
    "dist":    "the .tar.zst archives `pack` builds from corpus/",
    "merged":  "merge_corpus.py output",
    "__pycache__": "bytecode",
}

# EVIDENCE — regenerable only by re-running the thing that produced it, and in
# one case not at all. Moved into testing-archive/ rather than deleted.
PRESERVED = {
    "capture":  "payload captures — what a vendor's client WOULD have sent",
    "digests":  "snapshot digests: what the archive compared against",
}


def dir_size(p):
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.is_dir() else 0


def human_bytes(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n/1:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def dirty_repos():
    """Both checkouts, and whether either has uncommitted work.

    `reset` deletes gigabytes and moves the rest. Doing that over uncommitted
    work means the only copy of it was the working tree, and there is no verb
    that brings it back. So this refuses rather than asking — a prompt answered
    'yes' by someone who did not look is the same as no check at all.
    """
    out = []
    for label, path in (("deadreckon-count", ROOT), ("deadreckon-record", CORPUS)):
        if not (path / ".git").is_dir():
            continue
        n = len(_git(path, "status", "--porcelain").splitlines())
        if n:
            out.append((label, path, n))
    return out


def reset(apply=False):
    """Clear everything development left behind, and start the operating record.

    `retire` handles the documents. This handles the working directories too,
    and refuses to run over uncommitted work. Dry by default: nothing moves
    until --yes, because the dry run IS the review step.
    """
    dirty = dirty_repos()
    if dirty:
        print("REFUSING — uncommitted work in:\n")
        for label, path, n in dirty:
            print(f"  {label:20} {n} change(s)   {path}")
        print("\nCommit or stash first. reset deletes regenerable output and moves\n"
              "the rest into testing-archive/; neither step can recover a file that\n"
              "only ever existed in the working tree.")
        return 1

    stamp = datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H-%M-%S")
    from update import stamp_path
    dest = ROOT / "testing-archive" / stamp_path(stamp)

    print(f"{'DELETE — regenerable' if apply else 'WOULD DELETE — regenerable'}\n")
    freed = 0
    for name, why in REGENERABLE.items():
        for root in (ROOT, CORPUS):
            p = root / name
            if not p.is_dir():
                continue
            size = dir_size(p)
            freed += size
            print(f"  {name:14} {human_bytes(size):>10}   {why}")
            if apply:
                shutil.rmtree(p, ignore_errors=True)

    print(f"\n{'PRESERVE into' if apply else 'WOULD PRESERVE into'} "
          f"testing-archive/{stamp_path(stamp)}/\n")
    from update import write_ledgers
    write_ledgers(ROOT / "testing-archive")
    kept = 0
    for name, why in PRESERVED.items():
        p = ROOT / name
        if not p.is_dir():
            continue
        size = dir_size(p)
        kept += size
        print(f"  {name:14} {human_bytes(size):>10}   {why}")
        if apply:
            dest.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), str(dest / name))

    print(f"\n  {human_bytes(freed)} freed, {human_bytes(kept)} preserved")
    print("\nTHEN the documents — `retire`'s job, run as part of this:\n")
    if not apply:
        # PRINTED, not just run. sh() captures stdout and only writes it out on
        # failure, so a dry run that succeeded showed nothing at all — the one
        # command whose entire purpose is to show you what it would do.
        print(sh(["retire_archive.py"]).rstrip())
        print("\n  nothing has changed. Re-run with:  python3 run.py reset --yes")
        return 0

    sh(["retire_archive.py", "--yes"], quiet=True)
    wipe_derived(ROOT, "deadreckon-count")
    if CORPUS.is_dir():
        wipe_derived(CORPUS, "deadreckon-record")
    print("\n  reset. This tree now holds only what a scan produces.")
    print("  Next:  python3 run.py update")
    return 0


def this_machine():
    """The folder this computer owns, by .machine-id.

    UUID is the primary anchor — survives OS reinstalls and hostname changes.
    Hostname is the fallback for machines enrolled before UUID tracking.
    """
    import json, platform
    from install import hardware_uuid
    uuid = hardware_uuid()
    host = platform.node()
    hostname_match = None
    for d in paths.machine_folders(ROOT):
        f = d / ".machine-id"
        if f.is_file():
            try:
                info = json.loads(f.read_text(encoding="utf-8"))
                stored_uuid = info.get("hardware_uuid")
                if uuid and stored_uuid and stored_uuid.lower() == uuid.lower():
                    return d
                if info.get("hostname") == host and hostname_match is None:
                    hostname_match = d
            except Exception:
                pass
    return hostname_match


                # Shared and derived, owned by no single machine. Anything
                # staged under one of these is a rollup of whatever this
                # computer happened to have pulled.
SHARED_DIRS = {"human-readable", "machine-readable", "archive", "testing-archive",
               "corpus", "merged", "digests", "dist", "docker", "submission",
               "capture", "vendor", "__pycache__"}


def foreign_staged(root, mine):
    """Staged paths that belong to a DIFFERENT machine's folder.

    The rule "machines own their own folder" was written down, obeyed by
    run.py's own `git add`, and enforced by nothing. Found in ~/deadreckon-record
    with 20,311 files staged:

        16,520  dell-latitude-7480-linux     not this machine
         2,179  macbook-air-m1               not this machine
         1,610  hp-laptop-linux              this machine
         2,194  staged DELETIONS, all other machines', already gone from disk

    A commit there would have removed 2,194 of another computer's transcripts.
    One `git add -A` puts the index in that state and nothing said so.

    Everything not under a machine folder — the derived root documents, the
    archive — is reported separately by the caller: those are TRACKED on
    purpose, so a reader sees current numbers, and simply must not be committed
    by a machine that holds only part of the fleet.
    """
    r = subprocess.run(["git", "diff", "--cached", "--name-only"],
                       cwd=root, capture_output=True, text=True)
    if r.returncode:
        return [], []
    foreign, shared = [], []
    for line in r.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        top = line.split("/")[0]
        if top == mine:
            continue
        if top in SHARED_DIRS or "/" not in line:
            shared.append(line)          # derived, or a root-level file
        else:
            foreign.append(line)
    return foreign, shared


def status():
    import json
    who_am_i()
    print()

    print(f"  {'repo':16}{'commit':10}{'dirty':>7}{'ahead':>7}")
    for name, d in (("deadreckon-count", ROOT), ("deadreckon-record", CORPUS)):
        if not (d / ".git").is_dir():
            print(f"  {name:16}{'—':10}{'—':>7}{'—':>7}   not a checkout")
            continue
        g = lambda *a: subprocess.run(["git", "-C", str(d)] + list(a),
                                      capture_output=True, text=True).stdout.strip()
        print(f"  {name:16}{g('rev-parse','--short','HEAD'):10}"
              f"{len(g('status','--porcelain').splitlines()):>7}"
              f"{g('rev-list','--count','origin/main..HEAD') or '?':>7}")
    print()
    import sessions
    cur = sessions.scanner_version()
    print(f"  current scanner {cur}")
    print(f"  {'machine':30}{'scanner':16}{'scanned':18}")
    for d in paths.machine_folders(ROOT):
        t = json.loads(paths.find(d, "totals.json").read_text(encoding="utf-8"))
        v = t.get("scanner_version", "pre-versioning")
        mark = "" if v == cur else "   <- older scanner"
        print(f"  {d.name:30}{v[:14]:16}{str(t.get('generated_at'))[:16]:18}{mark}")
    arc = ROOT / "archive"
    snaps = sorted(p.name for p in (arc / "reports").iterdir()) if (arc / "reports").is_dir() else []
    print(f"\n  archive      {len(snaps)} report snapshot(s)"
          + (f", newest {snaps[-1]}" if snaps else " — empty"))
    ta = ROOT / "testing-archive"
    print(f"  testing      {len(list(ta.iterdir())) if ta.is_dir() else 0} retired set(s)")

    # THE DAEMON, WHERE SOMEONE ALREADY LOOKS.
    #
    # `!! NOT ARCHIVED` fired 204 times in the journal before anyone noticed —
    # it is one of the three lines the README says to send over rather than
    # re-run, and it accumulated where nothing reads. And the unit runs a COPY
    # at ~/.local/bin/retention_guard.py, so a `git pull` that changes the
    # guard leaves the daemon on stale code silently. The guard is what
    # protects the transcripts; both of those are worth a line here.
    import hashlib
    import shutil as _sh
    try:
        act = subprocess.run(["systemctl", "--user", "is-active",
                              "retention-guard.service"],
                             capture_output=True, text=True).stdout.strip()
        ling = subprocess.run(["loginctl", "show-user", os.environ.get("USER", ""),
                               "-p", "Linger", "--value"],
                              capture_output=True, text=True).stdout.strip()
        print(f"\n  daemon       {act}"
              + (f", linger={ling}" if ling else ""))
    except Exception:  # noqa: BLE001
        print("\n  daemon       (systemctl unavailable)")

    def _h(p_):
        try:
            return hashlib.sha256(pathlib.Path(p_).read_bytes()).hexdigest()[:12]
        except Exception:  # noqa: BLE001
            return None
    installed = pathlib.Path.home()/".local"/"bin"/"retention_guard.py"
    a, b = _h(installed), _h(ROOT/"retention_guard.py")
    if a and b:
        print(f"               guard copy {'matches the repo' if a == b else 'DIFFERS from the repo — the daemon is running stale code'}"
              + ("" if a == b else f"  ({a} vs {b}; cp retention_guard.py {installed})"))
    elif b and not a:
        print("               guard copy MISSING at ~/.local/bin/retention_guard.py")

    if _sh.which("journalctl"):
        try:
            j = subprocess.run(["journalctl", "--user", "-u",
                                "retention-guard.service", "--no-pager",
                                "--since", "-7d"],
                               capture_output=True, text=True).stdout
            fails = [l for l in j.splitlines() if "could NOT be archived" in l]
            print(f"               {len(fails)} archive failure(s) logged in the last 7 days"
                  + (f"\n               newest: {fails[-1].split(':', 3)[-1].strip()[:90]}"
                     if fails else ""))
        except Exception:  # noqa: BLE001
            pass

    # THE DOCUMENTS, and whether they still describe this tree. PLAN P5.8.
    #
    # A rollup generated from 2 machines sat on the front page, committed, while
    # 5 machine folders sat committed beside it with complete scans dated
    # EARLIER than the rollup. Every check passed, because every check asked
    # whether the parts summed to the whole they were told to sum — and they
    # did. Nothing asked WHICH parts, and a timestamp cannot answer that.
    #
    # So every derived document carries the input fingerprint it was built from,
    # and this recomputes that fingerprint from the tree and prints the
    # difference. It belongs in `status` because the moment to see it is BEFORE
    # anyone publishes, not in a gate that runs after.
    print("\n  documents")
    try:
        import doc_render
        rows = doc_render.survey(ROOT)
        if not rows:
            print("    none expected — no machine folders in this checkout")
        bad = 0
        for r in rows:
            print(f"    {r['state']:<12} {r['document']}")
            if r["state"] in (doc_render.STALE, doc_render.MISSING):
                bad += 1
                for w in r["why"]:
                    print(f"                 - {w}")
        if rows:
            print(f"    {len(rows)} derived document(s), {bad} that no longer "
                  f"describe this tree")
            if bad:
                print("    Regenerate with `python3 doc_render.py render`, or move "
                      "them aside\n    with `python3 doc_render.py archive --yes`. "
                      "Do not publish them as they are.")
    except Exception as e:  # noqa: BLE001 - say why; silence would read as clean
        print(f"    !! could not read the documents: {e.__class__.__name__}: {e}")
        print("    A document check that could not run is not a document check")
        print("    that passed. This line is here so the two never look alike.")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("verb", choices=["update", "rebuild", "archive", "retire", "reset",
                                     "status", "sync", "combine"])
    ap.add_argument("--machine", help="folder for this computer, first run only")
    ap.add_argument("--label", help="display name, first run only")
    ap.add_argument("--yes", action="store_true", help="required by `retire`")
    ap.add_argument("--dry-run", action="store_true",
                    help="show what sync/combine would do, change nothing")
    args = ap.parse_args()

    if args.verb == "status":
        return status()

    if args.verb == "reset":
        return reset(apply=args.yes)

    if args.verb == "update":
        # WHAT MACHINE IS THIS — first, before anything is measured.
        #
        # Every step after this asks a platform question: whether hard links
        # work, whether there is a /proc, whether a second operating system on
        # the same disk holds a second copy of every profile. Answering them
        # inline, wherever each script happens to need one, is how a tool ends
        # up correct on the machine it was written on and quietly wrong
        # everywhere else. The warnings are printed BEFORE the scan so a run
        # that cannot archive says so first rather than after.
        try:
            import platform_detect
            _pi = platform_detect.detect()
            _c = _pi["capabilities"]
            print(f"  {_pi['system']}/{_pi['flavour']}  shell {_pi['shell']}  "
                  f"hardlinks {'yes' if _c['hardlinks'] else 'NO'}  "
                  f"service {_pi['service_manager'] or 'none'}")
            for _w in _pi["warnings"]:
                print(f"  !! {_w}")
            print()
        except Exception as e:  # noqa: BLE001 - never block a scan on this
            print(f"  platform detection skipped ({e})\n")

        print("scanning this computer\n")
        rebuild(scan=True, machine=args.machine, label=args.label)

        # Ask the machine whether anything it did went uncounted.
        #
        # Every other check here verifies that the numbers we HAVE are
        # internally consistent — machines partition the grand total, buckets
        # sum to their session. None of them can see a CLI nobody wrote a reader
        # for: its absence is indistinguishable from a zero, on every report.
        #
        # sweep_usage.py searches by CONTENT instead, so a tool that appears on
        # one machine and not this one is reported rather than silently missed.
        # It is advisory: a finding is a prompt to look, not a failed check,
        # because the honest answer is usually "that is a derived report" and
        # the tool says so with numbers rather than guessing.
        # quiet=True is load-bearing, not tidiness: sweep_usage.py exits 1 when
        # it FINDS something, and sh() raises SystemExit on a non-zero return.
        # Without it, the one outcome worth acting on — uncounted usage — would
        # abort the scan that reported it.
        try:
            out = sh(["sweep_usage.py"], quiet=True)
            head = [l for l in out.splitlines() if "scanned" in l]
            tail = [l for l in out.splitlines() if "token(s) carried" in l]
            if head:
                print("  " + head[0].strip())
            if tail:
                print("  UNCOUNTED: " + tail[0].strip())
                print("    -> a large figure means a CLI needs a reader in sessions.py")
            else:
                print("  uncounted usage: none — every numeric token field sits in")
                print("  a path a reader already reads")
        except Exception as e:  # noqa: BLE001 - advisory only, never blocks a scan
            print(f"  sweep skipped ({e})")
        # Record the ledger while the scan is fresh.
        #
        # It lived only in the retention daemon, which meant a scan you ran by
        # hand did not reach the lifetime record until the next 6-hour tick —
        # and if the machine went down in between, that scan's sessions were
        # never observed by anything. The daemon is the guarantee that it
        # happens unattended; this is the guarantee that it happens NOW, when
        # the numbers were just measured.
        #
        # Advisory: a ledger that raises must not fail a scan that succeeded.
        try:
            import token_ledger
            mdir = token_ledger.this_machine(ROOT)
            if mdir:
                n, seen, _ = token_ledger.record(mdir)
                lt = token_ledger.lifetime(mdir)
                print(f"\n  ledger  +{n} observation(s) of {seen} session(s); "
                      f"lifetime {lt['total']:,} across {lt['sessions']:,}")
        except Exception as e:  # noqa: BLE001 - advisory, never blocks a scan
            print(f"\n  ledger skipped ({e})")

        if CORPUS.is_dir():
            print("\nexporting transcripts")
            sh(["export_corpus.py"])
            # The machine's folder goes INTO the corpus repo. Moving the
            # transport to release archives accidentally replaced this step
            # instead of adding to it, so two computers uploaded a .tar.zst
            # and created no folder at all. The archive is how you FETCH the
            # corpus quickly; the folder is what the corpus IS.
            src = ROOT / "corpus"
            if src.is_dir():
                import shutil as _sh
                for m in sorted(d for d in src.iterdir() if d.is_dir()):
                    _sh.copytree(m, CORPUS / m.name, dirs_exist_ok=True)
                    print(f"  copied {m.name}/ into deadreckon-record")
                sh(["corpus_reports.py"], quiet=True)

        # Stage ONLY this computer's folder. The root documents are derived
        # from every machine folder, so a machine that commits them is
        # committing a rollup of whatever it happened to have pulled — and
        # every machine writing the same six files is exactly why two
        # computers scanning at once collide on push. Machines own their own
        # folder; the collective is regenerated by whoever wants it, with
        # `run.py rebuild`, from folders that never conflict.
        mine = this_machine()
        if mine:
            subprocess.run(["git", "add", str(mine.name)], cwd=ROOT)
            # COUNT WHAT WAS STAGED UNDER THIS MACHINE, not the whole index.
            # This counted every staged path and called the total "this
            # computer only", so an index holding 18,699 of other machines'
            # files would have printed
            #   staged 20311 file(s) under hp-laptop-linux/ — this computer only
            # which is the sentence you would read instead of noticing.
            staged = subprocess.run(["git", "diff", "--cached", "--name-only"],
                                    cwd=ROOT, capture_output=True,
                                    text=True).stdout.splitlines()
            n = sum(1 for f in staged if f.startswith(mine.name + "/"))
            print(f"\n  staged {n} file(s) under {mine.name}/ — this computer only")
            for label, where in (("deadreckon-count", ROOT), ("deadreckon-record", CORPUS)):
                if not (where / ".git").is_dir():
                    continue
                foreign, shared = foreign_staged(where, mine.name)
                if foreign:
                    by = {}
                    for f in foreign:
                        by[f.split("/")[0]] = by.get(f.split("/")[0], 0) + 1
                    print(f"\n  !! {label}: {len(foreign)} staged file(s) belong to "
                          f"ANOTHER machine")
                    for m, c in sorted(by.items(), key=lambda kv: -kv[1]):
                        print(f"       {c:>7,}  {m}")
                    print(f"     Committing this publishes a rollup of whatever "
                          f"this computer happened\n     to have pulled, and any "
                          f"staged DELETION removes that machine's data.")
                    print(f"     Fix:  git -C {where} reset")
                if shared:
                    print(f"\n  !! {label}: {len(shared)} derived/root file(s) staged: "
                          f"{', '.join(shared[:4])}"
                          f"{' ...' if len(shared) > 4 else ''}")
                    print(f"     These are rebuilt from EVERY machine folder. Commit "
                          f"them from a\n     checkout that has the whole fleet, "
                          f"after `python3 run.py rebuild`.")
            # WHO IS ABOUT TO PUSH — OS user, git identity, gh account, remote
            # URL — for both repos. Shown before the commit instructions so you
            # see the answer before you copy the command.
            print()
            who_am_i()

            print(f"\n  git commit -m 'scan {mine.name}' && git pull --rebase && git push")
            print(f"\n  cd ~/deadreckon-record")
            print(f"  git add {mine.name} && git commit -m 'corpus {mine.name}'"
                  f" && git pull --rebase && git push")
            print(f"  cd - && python3 corpus_ship.py pack && python3 corpus_ship.py push")
            print(f"\n  The root reports were rebuilt locally so you can read them,")
            print(f"  but are deliberately NOT staged. Anyone can regenerate them")
            print(f"  with `python3 run.py rebuild` once every machine is in.")
        return

    if args.verb == "rebuild":
        print("deleting every derived file, then recomputing from the machine folders\n")
        rebuild(scan=False)
        if CORPUS.is_dir():
            print(sh(["corpus_reports.py"]).strip().splitlines()[-1])
        return

    if args.verb == "archive":
        print("snapshotting the current state, then rescanning\n")
        stamp = datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H-%M-%S")
        sh(["archive_all.py", "--yes"], quiet=True)
        print(f"  snapshot {stamp} written to archive/")
        rebuild(scan=True)
        return

    if args.verb == "retire":
        if not args.yes:
            print("This moves EVERYTHING into testing-archive/ and clears the\n"
                  "derived documents in both repositories. Machine folders scanned\n"
                  "by an older version are retired too — they come back when that\n"
                  "computer runs `update` again.\n")
            # sh() only writes captured output on failure, so this dry run
            # printed its warning and then nothing at all.
            print(sh(["retire_archive.py"]).rstrip())
            print("\n  re-run with:  python3 run.py retire --yes")
            return
        sh(["retire_archive.py", "--yes"], quiet=True)
        wipe_derived(ROOT, "deadreckon-count")
        if CORPUS.is_dir():
            wipe_derived(CORPUS, "deadreckon-record")
        print("\n  retired. Now:  python3 run.py update")
        return

    if args.verb == "sync":
        # Job 1 of the daemon, run once manually.
        # git pull + run.py update + commit own folder + push + combine.
        import sync_job
        result = sync_job.sync(dry=args.dry_run)
        sys.exit(0 if result.ok else 1)
        return

    if args.verb == "combine":
        # Rebuild root reports from all machine folders and commit them.
        # Any machine can run this after pulling everyone else's scan.
        import sync_job
        result = sync_job.sync(dry=args.dry_run, combine_only=True)
        sys.exit(0 if result.ok else 1)
        return


if __name__ == "__main__":
    main()
