#!/usr/bin/env python3
"""Ship the RAW transcripts to `deadreckon-transcripts`, over git LFS.

    python3 transcripts_ship.py pack     # this machine -> raw-dist/<machine>/<YYYY-MM>/<cli>.tar.zst
    python3 transcripts_ship.py push     # commit them into ~/deadreckon-transcripts via LFS
    python3 transcripts_ship.py pull     # fetch the LFS objects for a machine
    python3 transcripts_ship.py unpack   # expand what was pulled

WHY THIS EXISTS SEPARATELY FROM corpus_ship.py

They ship different things to different places and only look alike:

    corpus_ship.py     REDACTED transcripts, from ~/deadreckon-record,
                       one archive per machine, as a RELEASE ASSET on
                       deadreckon-record.

    this               RAW transcripts, read from the live profiles on this
                       disk via stores.py, one archive per CLI PER MONTH, as
                       LFS objects in deadreckon-transcripts.

The third repository was created on 2026-08-11 with a .gitattributes and a
README describing `corpus_ship.py pack && push --lfs`, and then nothing was
ever shipped to it, because no such flag was ever written and corpus_ship is
hardcoded to the record release. Three READMEs described a three-repository
system that had two. This is the missing third.

WHY PER MONTH, NOT PER MACHINE

The redacted corpus is packed whole because it is re-exported whole. The raw
side accumulates: a month that has already been shipped never changes again, so
partitioning by month means a re-run uploads only the months that moved. One
archive per machine would mean re-uploading a machine's entire history — 593 MB
on the largest one here — to add a week.

WHY IT REFUSES ON A PUBLIC REPOSITORY

These are unredacted working sessions. The redaction pass over the SAME files
pulled 559 secrets out of one machine, and what protects this repository is a
visibility flag, which is a policy control until something checks it. `push`
asks GitHub what the visibility actually is and refuses on anything but
private. That turns one setting nobody re-reads into a gate that runs every
time.
"""

import argparse
import datetime
import json
import pathlib
import shutil
import tempfile
import sys

ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT))
import stores
import corpus_ship
from corpus_ship import (_pipe, sha256, _members, run, assets,
                         require_repo_access)

REPO = "matrixbuilderops/deadreckon-transcripts"
TAG = "raw"
CLONE = pathlib.Path.home() / "deadreckon-transcripts"
LEVEL = "10"


def machine_name(root):
    mine = corpus_ship._this_machine_folder(root)
    if not mine:
        raise SystemExit(
            "cannot tell which folder belongs to this computer.\n"
            "  Run `python3 run.py update` first.")
    return mine


def collect(home):
    """Every raw transcript file this machine holds, by (cli label, YYYY-MM).

    The store map is stores.py — the same one the counter and the archiver
    read, so a CLI that is counted is a CLI that is shipped. A file outside
    $HOME is REPORTED rather than skipped quietly: a relocated profile that
    silently shipped nothing would look exactly like a machine that never used
    that tool.

    EVERY FILE GOES IN EXACTLY ONE ARCHIVE

    Store paths nest — `.gemini/` contains `.gemini/antigravity-cli/`, and both
    are stores — so walking each one independently listed 1,198 files two and
    three times over, 1.1 GB of duplicate bytes inside a 950 MB upload. The
    duplicates were invisible in the per-CLI table because each row was
    correct on its own; only the sum was wrong.

    So a file is claimed by the MOST SPECIFIC store that contains it — the
    longest resolved base path. That is deterministic, it needs no ordering
    assumption about the store list, and it puts each file under the label a
    reader would look for it under.
    """
    claim, outside = {}, []
    for s in list(stores.conversation_stores()) + list(stores.root_file_stores()):
        for p in stores.resolve(s, str(home)) or []:
            p = pathlib.Path(p)
            if not p.exists():
                continue
            files = [f for f in p.rglob("*") if f.is_file()] if p.is_dir() else [p]
            for f in files:
                try:
                    rel = f.relative_to(home)
                except ValueError:
                    outside.append(f)
                    continue
                prev = claim.get(rel)
                if prev is None or len(str(p)) > len(str(prev[1])):
                    claim[rel] = (s.label, p)

    groups = {}
    for rel, (label, _base) in claim.items():
        month = datetime.datetime.fromtimestamp(
            (home / rel).stat().st_mtime).strftime("%Y-%m")
        groups.setdefault((label, month), []).append(rel)
    return groups, outside


def cmd_pack(args, root):
    if not shutil.which("zstd"):
        raise SystemExit("zstd is not installed:  sudo apt install zstd")
    home = pathlib.Path.home()
    mine = machine_name(root)
    groups, outside = collect(home)
    if not groups:
        raise SystemExit("no transcripts found — nothing to pack")

    out_root = root / "raw-dist" / mine
    manifest = {}
    print(f"  {'cli / month':34}{'files':>8}{'raw':>12}{'archive':>12}")
    for (label, month), rels in sorted(groups.items()):
        dest = out_root / month
        dest.mkdir(parents=True, exist_ok=True)
        arc = dest / f"{label}.tar.zst"
        # The listing goes to a FILE, not tar's stdin. _pipe() gives tar's
        # stdout to zstd, so feeding the list in would mean writing to a pipe
        # while draining another — and a listing bigger than the pipe buffer
        # would block forever. A temp file cannot deadlock.
        with tempfile.NamedTemporaryFile("w", suffix=".list", delete=False) as lf:
            lf.write("\n".join(str(r) for r in rels) + "\n")
            listing = lf.name
        try:
            rc_tar, rc_zstd, err = _pipe(
                ["tar", "-cf", "-", "-C", str(home), "--files-from", listing],
                ["zstd", f"-{LEVEL}", "-T0", "-q", "-o", str(arc), "-f"])
        finally:
            pathlib.Path(listing).unlink(missing_ok=True)
        if rc_tar or rc_zstd:
            raise SystemExit(
                f"pack failed for {label} {month}: tar {rc_tar}, zstd {rc_zstd}\n"
                f"{err[-400:]}")
        got, want = _members(arc), len(rels)
        if got < want:
            arc.unlink(missing_ok=True)
            raise SystemExit(
                f"pack refused for {label} {month}: archive holds {got:,} files, "
                f"the group has {want:,}.\n"
                f"  The archive has been deleted; nothing was hashed. Re-run pack.")
        raw = sum((home / r).stat().st_size for r in rels)
        manifest.setdefault(month, {})[label] = {
            "files": want, "raw_bytes": raw,
            "archive_bytes": arc.stat().st_size, "sha256": sha256(arc),
        }
        print(f"  {label + ' ' + month:34}{want:>8,}{raw/1e6:>11.1f}M"
              f"{arc.stat().st_size/1e6:>11.1f}M")

    for month, entry in manifest.items():
        (out_root / month / "MANIFEST.json").write_text(
            json.dumps({"machine": mine, "month": month,
                        "generated_at": datetime.datetime.now()
                        .astimezone().isoformat(timespec="seconds"),
                        "archives": entry}, indent=2) + "\n")

    if outside:
        print(f"\n  !! {len(outside)} file(s) live outside $HOME and were NOT packed:")
        for f in sorted({str(f.parent) for f in outside})[:5]:
            print(f"     {f}")
        print("     A relocated profile ships nothing here. That is reported "
              "rather than\n     skipped, because silence would look like a "
              "tool nobody used.")
    print(f"\n  wrote {out_root}/")
    return 0


def require_private():
    """Refuse unless GitHub itself says the repository is private."""
    r = run(["gh", "api", f"repos/{REPO}", "-q", ".visibility"])
    if r.returncode:
        raise SystemExit(
            f"cannot read {REPO} — is the right gh account active?\n"
            f"  {r.stderr[-300:]}")
    vis = r.stdout.strip()
    if vis != "private":
        raise SystemExit(
            f"REFUSING — {REPO} visibility is {vis!r}, not 'private'.\n"
            "  These are unredacted transcripts. The redaction pass over the\n"
            "  same files found 559 secrets on one machine. Nothing is pushed\n"
            "  until this repository is private again.")
    return vis


def ensure_clone():
    """The checkout still matters — the MANIFESTS live in git.

    The archives do not: they are release assets, for the reasons in
    corpus_ship.py. What git holds here is the small, diffable half — which
    hash was authoritative for each machine, month and CLI, and when it
    changed. That is the record; the assets are the bytes it points at.
    """
    if not (CLONE / ".git").is_dir():
        raise SystemExit(
            f"{CLONE} is not a checkout. Clone it first:\n"
            f"  git clone https://github.com/{REPO}.git {CLONE}")
    return CLONE


def asset_name(machine, month, label, digest):
    """Content-addressed, so an upload can never destroy an earlier one.

    THE ONE THING RELEASE ASSETS LOSE TO LFS, GIVEN BACK

    `--clobber` overwrites, and overwriting is how the offsite copy of four
    machines was once destroyed by running the documented command on the
    fifth. LFS would have kept the old blob in history. So the hash goes in
    the NAME: different content is a different asset, uploaded ALONGSIDE what
    is already there, and nothing this tool does is ever destructive. The
    committed MANIFEST.json says which hash is current; every superseded one
    stays retrievable, named by what it contains.
    """
    return f"{machine}__{month}__{label}__{digest[:8]}.tar.zst"


def ensure_release():
    if assets(REPO, TAG, missing_ok=True):
        return
    if run(["gh", "release", "view", TAG, "-R", REPO]).returncode:
        r = run(["gh", "release", "create", TAG, "-R", REPO, "--notes",
                 "RAW transcript archives, one per CLI per month per computer. "
                 "Names carry the sha256 prefix: nothing is ever overwritten. "
                 "Fetched with `transcripts_ship.py pull`, which resumes."])
        if r.returncode:
            raise SystemExit(f"could not create release: {r.stderr[-400:]}")
        print(f"  created release {TAG} on {REPO}")


def cmd_push(args, root):
    require_private()
    require_repo_access(REPO)
    ensure_clone()
    mine = machine_name(root)
    src = root / "raw-dist" / mine
    if not src.is_dir():
        raise SystemExit(f"nothing packed for {mine} — run `pack` first")
    ensure_release()

    have = {a["name"]: a for a in assets(REPO, TAG, missing_ok=True)}
    todo, skipped, shrunk = [], 0, []
    for mf in sorted(src.rglob("MANIFEST.json")):
        m = json.loads(mf.read_text())
        month = m["month"]
        for label, e in sorted(m["archives"].items()):
            name = asset_name(mine, month, label, e["sha256"])
            arc = mf.parent / f"{label}.tar.zst"
            if name in have:
                skipped += 1
                continue
            # A MONTH THAT SHRANK IS EITHER A DELETION YOU MEANT OR THE BUG.
            #
            # Same shape as the 139-byte archive that replaced 1.7 MB: an
            # emptier pack of an already-shipped month means transcripts went
            # missing. Nothing can be overwritten here, so this cannot destroy
            # anything — but it can bury the good copy under a bad one that
            # the manifest then points at, so it stops and asks.
            prior = [a for n, a in have.items()
                     if n.startswith(f"{mine}__{month}__{label}__")]
            if prior and not args.allow_shrink:
                biggest = max(prior, key=lambda a: a["size"])
                if e["archive_bytes"] < biggest["size"] * 0.9:
                    shrunk.append((name, e["archive_bytes"], biggest["name"],
                                   biggest["size"]))
                    continue
            todo.append((name, arc, e))

    if shrunk:
        print("REFUSING — these are smaller than what is already shipped:\n")
        for name, size, was, wsize in shrunk:
            print(f"  {name}\n    {size/1e6:.1f} MB, but {was} is {wsize/1e6:.1f} MB")
        print("\nNothing has been overwritten — nothing here CAN overwrite. But a\n"
              "month that shrank usually means transcripts went missing rather\n"
              "than that you deleted them. Check, then re-run with --allow-shrink.")
        return 1

    if not todo:
        print(f"  nothing to ship — all {skipped} archive(s) already on the release")
    for name, arc, e in todo:
        tmp = arc.parent / name
        shutil.copy2(arc, tmp)
        r = run(["gh", "release", "upload", TAG, str(tmp), "-R", REPO])
        tmp.unlink(missing_ok=True)
        if r.returncode:
            raise SystemExit(f"upload failed for {name}: {r.stderr[-400:]}")
        print(f"  uploaded {name}  ({e['archive_bytes']/1e6:.1f} MB)")
    if skipped:
        print(f"  {skipped} already shipped, left alone")

    # THE MANIFESTS GO TO GIT — this machine's folder and nobody else's.
    dest = CLONE / mine
    for mf in sorted(src.rglob("MANIFEST.json")):
        out = dest / mf.parent.name
        out.mkdir(parents=True, exist_ok=True)
        shutil.copy2(mf, out / "MANIFEST.json")
    run(["git", "-C", str(CLONE), "add", mine])
    if not run(["git", "-C", str(CLONE), "status", "--porcelain", "--",
                mine]).stdout.strip():
        print("  manifests unchanged")
        return 0
    msg = f"raw transcripts {mine} {datetime.date.today().isoformat()}"
    if run(["git", "-C", str(CLONE), "commit", "-m", msg]).returncode:
        raise SystemExit("commit failed")
    run(["git", "-C", str(CLONE), "pull", "--rebase"])
    p = run(["git", "-C", str(CLONE), "push"])
    if p.returncode:
        raise SystemExit(f"push failed: {p.stderr[-400:]}")
    print(f"  manifests committed and pushed to {REPO}")
    return 0


def cmd_pull(args, root):
    require_private()
    require_repo_access(REPO)
    who = args.machine or machine_name(root)
    want = [a for a in assets(REPO, TAG) if a["name"].startswith(f"{who}__")]
    if not want:
        raise SystemExit(f"no archives for {who} on the {TAG!r} release")
    dest_dir = root / "raw-pulled" / who
    dest_dir.mkdir(parents=True, exist_ok=True)
    tok = corpus_ship.token()
    ok = True
    for a in want:
        dest = dest_dir / a["name"]
        if not corpus_ship.fetch_asset(a, dest, tok, REPO, args.chunk, args.retries):
            ok = False
            continue
        # The name carries the hash, so verification needs nothing else —
        # no sidecar to fetch, and no way for the two to disagree.
        want_prefix = a["name"].rsplit("__", 1)[1].split(".")[0]
        got = sha256(dest)[:8]
        if got != want_prefix:
            print(f"  {a['name']}  CHECKSUM MISMATCH (got {got}) — delete and re-pull")
            ok = False
            continue
        print(f"  {a['name']}  {dest.stat().st_size/1e6:>8.1f} MB  sha256 ok")
    print("\n  all archives verified" if ok else "\n  SOME FAILED — re-run pull")
    return 0 if ok else 1


def cmd_unpack(args, root):
    who = args.machine or machine_name(root)
    src = root / "raw-pulled" / who
    if not src.is_dir():
        raise SystemExit(f"nothing pulled for {who} — run `pull` first")
    dest = pathlib.Path(args.into) if args.into else root / "raw-unpacked" / who
    n = 0
    for arc in sorted(src.glob("*.tar.zst")):
        month = arc.name.split("__")[1]
        out = dest / month
        out.mkdir(parents=True, exist_ok=True)
        r = run(["tar", "--use-compress-program=zstd", "-xf", str(arc), "-C", str(out)])
        if r.returncode:
            raise SystemExit(f"unpack failed for {arc.name}: {r.stderr[-300:]}")
        n += 1
    print(f"  expanded {n} archive(s) into {dest}/")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("action", choices=["pack", "push", "pull", "unpack"])
    ap.add_argument("--machine", help="operate on this machine's folder")
    ap.add_argument("--into", help="unpack destination")
    ap.add_argument("--allow-shrink", action="store_true",
                    help="ship a month smaller than what is already on the release")
    ap.add_argument("--chunk", type=int, default=16, help="pull chunk size, MB")
    ap.add_argument("--retries", type=int, default=8)
    args = ap.parse_args()
    return {"pack": cmd_pack, "push": cmd_push,
            "pull": cmd_pull, "unpack": cmd_unpack}[args.action](args, ROOT)


if __name__ == "__main__":
    sys.exit(main())
