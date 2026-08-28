#!/usr/bin/env python3
"""Move the corpus as resumable archives instead of through git.

    python3 corpus_ship.py pack           # this machine -> dist/<machine>.tar.zst
    python3 corpus_ship.py push           # upload it as a release asset
    python3 corpus_ship.py pull           # fetch every machine's archive, resumably
    python3 corpus_ship.py unpack         # expand what was pulled into ~/deadreckon-record

WHY NOT GIT

A git fetch is one pack over one connection and it cannot resume. Half a
gigabyte in, a dropped connection is not a slow transfer, it is a failed one
that starts over — which is exactly what happened here:

    fatal: fetch-pack: invalid index-pack output
    fatal: could not fetch <oid> from promisor remote

Neither was a disk or memory problem; there were 184 GB and 47 GB free. The
transfer simply never finished, and index-pack was handed a truncated stream.
The corpus is also the wrong shape for git: ~120,000 small files that will never
be diffed, in a repository that only ever grows.

Release assets are plain HTTP objects that honour Range requests, so a download
resumes from where it stopped — the same reason model weights are fetched that
way rather than cloned. And the archive is 5.5x smaller than the tree: 463 MB of
transcripts becomes 84 MB in about three seconds.

WHAT STILL LIVES IN GIT

The numbers, the digests, and the scripts — all small, all worth diffing. Only
the transcripts move this way.
"""

import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

REPO = "matrixbuilderops/deadreckon-record"
TAG = "corpus"
LEVEL = "10"          # -19 saves 5 MB and costs 40 seconds; not worth it


def _pipe(first, second):
    """Run `first | second` and return BOTH exit statuses, plus stderr.

    A shell pipeline reports only the LAST command's status, so
    `tar -cf - … | zstd -o out` returns zstd's — and zstd succeeds at
    compressing a truncated stream. Reproduced with one unreadable file in a
    301-file tree:

        shell returncode: 0        <- the status the old code checked
        tar said:  Exiting with failure status due to previous errors
        members inside: 300 of 301

    The sha256 was then taken FROM the short archive, so `pull` verified it and
    `push --clobber` had already replaced the good offsite copy. `set -o
    pipefail` would fix it in bash and is not in POSIX sh, which is what
    `shell=True` runs; two processes and two `wait`s work everywhere.

    stderr goes to a temp file rather than a pipe, because a pipe nobody drains
    until after `wait` deadlocks the moment tar has more than a pipe buffer of
    complaints — which is precisely the failing case this exists to catch.
    """
    with tempfile.TemporaryFile() as errf:
        p1 = subprocess.Popen(first, stdout=subprocess.PIPE, stderr=errf)
        p2 = subprocess.Popen(second, stdin=p1.stdout, stderr=errf)
        p1.stdout.close()          # so p1 sees EPIPE if p2 dies first
        p2.wait()
        p1.wait()
        errf.seek(0)
        return p1.returncode, p2.returncode, errf.read().decode("utf-8", "replace")


def _members(arc):
    """How many regular files are actually inside the finished archive.

    Read back from the written file, not from what was sent — that is the whole
    point. Directory entries end in "/" and are not counted, so this compares
    like with like against a source-tree file count.
    """
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as errf:
        d = subprocess.Popen(["zstd", "-dc", str(arc)],
                             stdout=subprocess.PIPE, stderr=errf)
        t = subprocess.Popen(["tar", "-tf", "-"], stdin=d.stdout,
                             stdout=out, stderr=errf)
        d.stdout.close()
        t.wait()
        d.wait()
        if d.returncode or t.returncode:
            raise SystemExit(f"cannot list {arc.name} after writing it — "
                             f"zstd {d.returncode}, tar {t.returncode}")
        out.seek(0)
        return sum(1 for line in out
                   if line.strip() and not line.rstrip().endswith(b"/"))


def run(cmd, **kw):
    return subprocess.run(cmd, text=True, capture_output=True, **kw)


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def machine_name(root):
    for d in sorted(root.iterdir()):
        if (d / ".machine-id").is_file():
            try:
                return json.loads((d / ".machine-id").read_text())["folder"]
            except Exception:
                pass
    return None


def _this_machine_folder(root):
    """The corpus folder this computer owns, by .machine-id. None if unknown."""
    import platform
    host = platform.node()
    for d in sorted(pathlib.Path(root).iterdir()):
        if not d.is_dir():
            continue
        f = d / ".machine-id"
        if f.is_file():
            try:
                if json.loads(f.read_text(encoding="utf-8")).get("hostname") == host:
                    return d.name
            except Exception:  # noqa: BLE001
                pass
    return None


def cmd_pack(args, root):
    src = pathlib.Path(args.corpus_dir) if args.corpus_dir else root / "corpus"
    if not src.is_dir():
        raise SystemExit(f"no corpus at {src} — run export_corpus.py first")
    # THIS MACHINE ONLY, BY DEFAULT — a machine must not ship another's archive.
    #
    # Packing every folder under corpus/ was safe on the one computer that had
    # everybody's transcripts on disk. It stops being safe the moment
    # .claude/projects/ and tools/ are gitignored, which they now are: a fresh
    # clone gives you the other machines' NUMBERS and none of their history. So
    # a second computer would pack their folders as empty and `push --clobber`
    # would replace the real assets with them. Measured:
    #
    #     a transcript-less asus-laptop-linux packs to        139 bytes
    #     the real asset offsite is                     1,763,716 bytes
    #
    # That is the offsite copy of four machines destroyed by running the
    # documented command on the fifth. Each computer owns its own folder, in
    # this repository and in the release, exactly as it does in git.
    folders = [d for d in sorted(src.iterdir()) if (d / ".claude").is_dir()]
    if not folders:
        raise SystemExit(f"no machine folder under {src}")
    if not getattr(args, "all_machines", False):
        mine = _this_machine_folder(root)
        if mine:
            folders = [d for d in folders if d.name == mine]
            if not folders:
                raise SystemExit(
                    f"no corpus folder for this computer ({mine}) under {src} — "
                    "run `python3 run.py update` first")
        else:
            raise SystemExit(
                "cannot tell which folder belongs to this computer.\n"
                "  Run `python3 run.py update` first, or pass --all-machines if\n"
                "  you really do hold every machine's transcripts locally.")
    if not shutil.which("zstd"):
        raise SystemExit("zstd is not installed:  sudo apt install zstd")

    dist = root / "dist"
    dist.mkdir(exist_ok=True)
    out = []
    for f in folders:
        arc = dist / f"{f.name}.tar.zst"
        want = sum(1 for x in f.rglob("*") if x.is_file())
        # -T0 uses every core; the archive is written straight from tar so the
        # uncompressed copy never touches disk.
        rc_tar, rc_zstd, err = _pipe(
            ["tar", "-cf", "-", "-C", str(src), f.name],
            ["zstd", f"-{LEVEL}", "-T0", "-q", "-o", str(arc), "-f"])
        if rc_tar:
            raise SystemExit(f"pack failed for {f.name}: tar exited {rc_tar}\n"
                             f"{err[-400:]}")
        if rc_zstd:
            raise SystemExit(f"pack failed for {f.name}: zstd exited {rc_zstd}\n"
                             f"{err[-400:]}")
        got = _members(arc)
        if got < want:
            arc.unlink(missing_ok=True)
            raise SystemExit(
                f"pack refused for {f.name}: archive holds {got:,} files, the "
                f"folder has {want:,}.\n"
                f"  {want - got:,} went missing while tar was reading. The "
                f"archive has been deleted;\n"
                f"  nothing was hashed or uploaded. Re-run pack.")
        digest = sha256(arc)
        (dist / f"{f.name}.sha256").write_text(f"{digest}  {arc.name}\n")
        raw = sum(x.stat().st_size for x in f.rglob("*") if x.is_file())
        out.append((f.name, raw, arc.stat().st_size, digest))

    print(f"  {'machine':30}{'raw':>12}{'archive':>12}{'ratio':>8}")
    for name, raw, got, digest in out:
        print(f"  {name:30}{raw/1e6:>11.1f}M{got/1e6:>11.1f}M{raw/got:>7.1f}x")
        print(f"  {'':30}sha256 {digest[:32]}…")
    print(f"\n  wrote {dist}/")
    return 0


def cmd_push(args, root):
    require_repo_access()
    dist = root / "dist"
    files = sorted(dist.glob("*.tar.zst")) + sorted(dist.glob("*.sha256"))
    if not getattr(args, "all_machines", False):
        mine = _this_machine_folder(root)
        if mine:
            skipped = [f.name for f in files if not f.name.startswith(mine + ".")]
            files = [f for f in files if f.name.startswith(mine + ".")]
            if skipped:
                # Named, not silently dropped. A dist/ holding someone else's
                # archive is usually a leftover, and leftovers are how the wrong
                # thing gets uploaded.
                print(f"  not mine, left alone: {', '.join(sorted(skipped))}")
    if not files:
        raise SystemExit("nothing of this machine's in dist/ — run `pack` first")
    if not shutil.which("gh"):
        raise SystemExit("gh is not installed")

    # One release, reused. Assets are replaced with --clobber so a rescan
    # overwrites that machine's archive and nobody else's.
    if run(["gh", "release", "view", TAG, "-R", REPO]).returncode:
        r = run(["gh", "release", "create", TAG, "-R", REPO, "--notes",
                 "Redacted transcript archives, one per computer. "
                 "Fetched with `corpus_ship.py pull`, which resumes."])
        if r.returncode:
            raise SystemExit(f"could not create release: {r.stderr[-400:]}")
        print(f"  created release {TAG}")

    for f in files:
        r = run(["gh", "release", "upload", TAG, str(f), "-R", REPO, "--clobber"])
        if r.returncode:
            raise SystemExit(f"upload failed for {f.name}: {r.stderr[-400:]}")
        print(f"  uploaded {f.name}  ({f.stat().st_size/1e6:.1f} MB)")
    return 0


def assets(repo=None, tag=None, missing_ok=False):
    repo, tag = repo or REPO, tag or TAG
    r = run(["gh", "api", f"repos/{repo}/releases/tags/{tag}"])
    if r.returncode:
        if missing_ok:
            return []
        raise SystemExit(f"no release {tag!r} on {repo}: {r.stderr[-300:]}")
    return json.loads(r.stdout).get("assets", [])


def require_repo_access(repo=None):
    """Fail loudly when the ACTIVE gh account cannot see the corpus repo.

    `gh auth token` returns whichever account is active, and more than one can
    be logged in at once. deadreckon-record is PRIVATE and owned by the
    matrixbuilderops account; with Alexander-Sorrell-IT active, every call here
    returns:

        {"message": "Not Found", "status": "404"}

    which is byte-identical to the repo having been deleted. That mistake was
    actually made — the conclusion drawn was "the repo does not exist, there is
    no offsite copy of the corpus", about a 1.49 GB private repo holding all
    five machines' archives. A permission error that reads as absence is worse
    than an error, because it gets believed.

    So: check first, and name the fix.
    """
    repo = repo or REPO
    r = run(["gh", "api", f"repos/{repo}", "-q", ".full_name"])
    if r.returncode == 0 and r.stdout.strip():
        return
    who = run(["gh", "api", "user", "-q", ".login"]).stdout.strip() or "unknown"
    owner = repo.split("/")[0]
    raise SystemExit(
        f"the active gh account ({who}) cannot see {repo}.\n"
        f"  A 404 here means NO ACCESS or NO REPO — they look the same.\n"
        f"  If the repo exists and is private, switch accounts first:\n"
        f"      gh auth switch --user {owner}\n"
        f"  Check which accounts are logged in with:  gh auth status"
    )


def token():
    r = run(["gh", "auth", "token"])
    if r.returncode or not r.stdout.strip():
        raise SystemExit("no gh token — run `gh auth login`")
    return r.stdout.strip()


def chunk_ok(dest, url, tok, start, end):
    """Re-request one byte range and compare it to what landed on disk.

    Closing the loop per chunk rather than only at the end. sha256 over the
    whole file says a 90 MB download is wrong; it does not say which part, and
    re-pulling all of it to find out is the cost this design exists to avoid.
    Checking each range against the server as it lands means a bad chunk is
    known immediately and only that chunk is fetched again.

    A range request also proves the server and the file still agree mid-transfer
    — an asset replaced by another machine's `push` halfway through a pull would
    otherwise produce a file that is internally consistent and wrong.
    """
    r = subprocess.run(
        ["curl", "-fsSL", "-H", f"Authorization: Bearer {tok}",
         "-H", "Accept: application/octet-stream",
         "-H", f"Range: bytes={start}-{end}", "--output", "-", url],
        capture_output=True)
    if r.returncode or not r.stdout:
        return None                       # could not verify; not the same as bad
    with open(dest, "rb") as fh:
        fh.seek(start)
        local = fh.read(end - start + 1)
    return hashlib.sha256(local).digest() == hashlib.sha256(r.stdout).digest()


def fetch_asset(a, dest, tok, repo, chunk_mb, retries):
    """Download one release asset in verified, resumable chunks.

    Extracted from cmd_pull so the raw-transcript shipper uses this same
    implementation rather than a second copy of it — the chunk-verify and the
    -L redirect handling below were both bought with a failure, and a parallel
    implementation would have to buy them again.

    Fetch one chunk, land it, verify it against the server, then move on. Each
    range is its own request, so a dropped connection costs one chunk rather
    than the file, and nothing is carried forward unverified.
    """
    size = a["size"]
    url = f"https://api.github.com/repos/{repo}/releases/assets/{a['id']}"
    step = chunk_mb * 1024 * 1024
    print(f"  {a['name']}  {size/1e6:.1f} MB in {chunk_mb} MB chunks")

    pos = dest.stat().st_size if dest.exists() else 0
    if pos > size:
        dest.unlink()
        pos = 0
    while pos < size:
        end = min(pos + step, size) - 1
        for attempt in range(1, retries + 1):
            # -L is not optional: the asset API answers 302 to storage, and
            # without following it curl succeeds with an empty body, which
            # looks like a failed chunk forever. curl drops the auth header
            # across the redirect by design; the storage URL is pre-signed.
            r = subprocess.run(
                ["curl", "-fsSL", "-H", f"Authorization: Bearer {tok}",
                 "-H", "Accept: application/octet-stream",
                 "-H", f"Range: bytes={pos}-{end}",
                 "--retry", "2", "--retry-delay", "2",
                 "--speed-limit", "1024", "--speed-time", "60",
                 "--output", "-", url],
                capture_output=True)
            if r.returncode == 0 and len(r.stdout) == end - pos + 1:
                with open(dest, "r+b" if dest.exists() else "wb") as fh:
                    fh.seek(pos)
                    fh.write(r.stdout)
                break
            print(f"     bytes {pos}-{end}: attempt {attempt} failed, retrying")
        else:
            print(f"     bytes {pos}-{end}: gave up after {retries}")
            return False

        v = chunk_ok(dest, url, tok, pos, end)
        if v is False:
            print(f"     bytes {pos}-{end}: MISMATCH against source — refetching")
            continue                  # same range again, pos unchanged
        pos = end + 1
        print(f"     {pos/1e6:>7.1f}/{size/1e6:.1f} MB  {pos/size*100:5.1f}%"
              f"  {'verified' if v else 'landed (range check unavailable)'}",
              end="\r", flush=True)
    print()

    got = dest.stat().st_size if dest.exists() else 0
    if got != size:
        print(f"  {a['name']:34} INCOMPLETE {got/1e6:.1f}/{size/1e6:.1f} MB")
        return False
    return True


def cmd_pull(args, root):
    require_repo_access()
    dist = root / "dist"
    dist.mkdir(exist_ok=True)
    tok = token()
    want = [a for a in assets() if a["name"].endswith(".tar.zst")]
    if args.machine:
        want = [a for a in want if a["name"].startswith(args.machine)]
    if not want:
        raise SystemExit("no archives on the release")

    sums = {a["name"]: a for a in assets() if a["name"].endswith(".sha256")}
    ok = True
    for a in want:
        dest = dist / a["name"]
        if not fetch_asset(a, dest, tok, REPO, args.chunk, args.retries):
            ok = False
            continue

        # Whole-file check as well: the chunks were each right, this says they
        # were also assembled in the right order.
        note = "size ok"
        sa = sums.get(a["name"].replace(".tar.zst", ".sha256"))
        if sa:
            r = run(["curl", "-fsSL",
                     "-H", f"Authorization: Bearer {tok}",
                     "-H", "Accept: application/octet-stream",
                     f"https://api.github.com/repos/{REPO}/releases/assets/{sa['id']}"])
            expect = r.stdout.split()[0] if r.stdout.strip() else None
            if expect:
                if sha256(dest) != expect:
                    print(f"  {a['name']:34} CHECKSUM MISMATCH — delete and re-pull")
                    ok = False
                    continue
                note = "sha256 ok"
        print(f"  {a['name']:34} {dest.stat().st_size/1e6:>8.1f} MB  {note}")
    print()
    print("  all archives verified" if ok else "  SOME ARCHIVES FAILED — re-run pull")
    return 0 if ok else 1


def cmd_unpack(args, root):
    dist = root / "dist"
    dest = pathlib.Path(args.into).expanduser()
    dest.mkdir(parents=True, exist_ok=True)
    arcs = sorted(dist.glob("*.tar.zst"))
    if not arcs:
        raise SystemExit("nothing in dist/ — run `pull` first")
    for a in arcs:
        p = subprocess.run(f"zstd -dc {a} | tar -xf - -C {dest}",
                           shell=True, text=True, capture_output=True)
        if p.returncode:
            raise SystemExit(f"unpack failed for {a.name}: {p.stderr[-400:]}")
        print(f"  {a.name:34} -> {dest}/{a.name.replace('.tar.zst','')}")
    print(f"\n  {len(arcs)} machine(s) expanded into {dest}")
    return 0


# ---------------------------------------------------------------------------
# LFS PUSH / PULL — deadreckon-transcripts (3rd repo, GitHub LFS)
#
# The release-asset transport above remains intact for deadreckon-record.
# LFS is the long-term home: pointer files in git, bytes in LFS storage,
# same gh auth, resumable, no size limit per file, no 2 GB asset cap.
#
# Structure on disk (local clone of deadreckon-transcripts):
#   <machine>/<YYYY-MM>/<cli>.tar.zst
#   <machine>/<YYYY-MM>/MANIFEST.json
#
# Each push copies dist/<machine>.tar.zst into the per-month structure,
# commits the LFS pointer, and pushes. The pointer is tiny; LFS handles
# the bytes.
# ---------------------------------------------------------------------------

LFS_REPO = "matrixbuilderops/deadreckon-transcripts"
LFS_CLONE_DIR = pathlib.Path.home() / "deadreckon-transcripts"


def _lfs_clone_or_pull():
    """Ensure a local clone of deadreckon-transcripts exists and is current."""
    if not shutil.which("git"):
        raise SystemExit("git is required for LFS operations")
    if not LFS_CLONE_DIR.is_dir():
        r = subprocess.run(
            ["gh", "repo", "clone", LFS_REPO, str(LFS_CLONE_DIR)],
            capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f"could not clone {LFS_REPO}: {r.stderr.strip()[:200]}")
        print(f"  cloned {LFS_REPO} -> {LFS_CLONE_DIR}")
    else:
        r = subprocess.run(
            ["git", "-C", str(LFS_CLONE_DIR), "pull", "--rebase", "--autostash"],
            capture_output=True, text=True)
        summary = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "up to date"
        print(f"  pull {LFS_REPO}: {summary}")
    # Ensure LFS is initialised in the clone
    subprocess.run(["git", "lfs", "install"],
                   cwd=str(LFS_CLONE_DIR), capture_output=True)


def _lfs_month():
    """Current YYYY-MM string."""
    import datetime
    return datetime.datetime.now().strftime("%Y-%m")


def cmd_lfs_push(args, root):
    """Push this machine's packed archives into deadreckon-transcripts via LFS.

    Reads dist/<machine>-<something>.tar.zst, slots them into the per-month
    directory structure, commits the LFS pointer, and pushes.
    """
    import datetime

    _lfs_clone_or_pull()

    dist = root / "dist"
    arcs = sorted(dist.glob("*.tar.zst"))
    if not arcs:
        raise SystemExit("nothing in dist/ — run `pack` first")

    month = _lfs_month()
    committed = []

    for arc in arcs:
        # Derive machine + cli from filename: <machine>.tar.zst or
        # <machine>-<cli>.tar.zst. Simple: the machine is what pack() named it.
        machine = arc.stem.replace(".tar", "")   # strip .tar from .tar.zst
        dest_dir = LFS_CLONE_DIR / machine / month
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / arc.name

        shutil.copy2(arc, dest)
        print(f"  copied {arc.name} -> {dest.relative_to(LFS_CLONE_DIR)}")

        # Write sha256 alongside
        cksum = sha256(arc)
        (dest_dir / (arc.stem + ".sha256")).write_text(cksum + "\n")

        # MANIFEST.json for this machine/month
        manifest_path = dest_dir / "MANIFEST.json"
        manifest = {}
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        manifest[arc.name] = {
            "sha256": cksum,
            "size": arc.stat().st_size,
            "month": month,
        }
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n",
                                 encoding="utf-8")

        subprocess.run(["git", "-C", str(LFS_CLONE_DIR), "add",
                        str(dest.relative_to(LFS_CLONE_DIR)),
                        str((dest_dir / (arc.stem + ".sha256")).relative_to(LFS_CLONE_DIR)),
                        str(manifest_path.relative_to(LFS_CLONE_DIR))],
                       capture_output=True)
        committed.append(machine)

    if not committed:
        print("  nothing to commit")
        return 0

    msg = f"transcripts {', '.join(set(committed))} {month}"
    r = subprocess.run(
        ["git", "-C", str(LFS_CLONE_DIR), "commit", "-m", msg],
        capture_output=True, text=True)
    if r.returncode and "nothing to commit" not in r.stdout:
        print(f"  commit: {r.stderr.strip()[:200]}")
    else:
        print(f"  committed: {msg}")

    r = subprocess.run(
        ["git", "-C", str(LFS_CLONE_DIR), "push"],
        capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"push failed: {r.stderr.strip()[:300]}")
    print(f"  pushed to {LFS_REPO} (LFS bytes transferred automatically)")
    return 0


def cmd_lfs_pull(args, root):
    """Pull all (or one machine's) archives from deadreckon-transcripts via LFS."""
    _lfs_clone_or_pull()

    # LFS pull fetches the actual bytes for LFS pointer files
    machine_filter = args.machine or ""
    lfs_args = ["git", "-C", str(LFS_CLONE_DIR), "lfs", "pull"]
    if machine_filter:
        lfs_args += ["--include", f"{machine_filter}/**"]
    r = subprocess.run(lfs_args, capture_output=True, text=True)
    if r.returncode:
        print(f"  lfs pull warning: {r.stderr.strip()[:200]}")
    else:
        print("  LFS objects pulled")

    # Copy to dist/ so unpack works unchanged
    dist = root / "dist"
    dist.mkdir(exist_ok=True)
    n = 0
    for arc in sorted(LFS_CLONE_DIR.rglob("*.tar.zst")):
        if machine_filter and machine_filter not in str(arc):
            continue
        dest = dist / arc.name
        shutil.copy2(arc, dest)
        print(f"  {arc.name} -> dist/")
        n += 1
    print(f"\n  {n} archive(s) ready in dist/ — run `unpack` to expand")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action",
                    choices=["pack", "push", "pull", "unpack",
                             "lfs-push", "lfs-pull"])
    ap.add_argument("--corpus-dir", help="where export_corpus.py wrote (default ./corpus)")
    ap.add_argument("--into", default=str(pathlib.Path.home() / "deadreckon-record"),
                    help="unpack destination")
    ap.add_argument("--machine", help="pull only this machine's archive")
    ap.add_argument("--all-machines", action="store_true",
                    help="pack/push EVERY machine folder found locally, not just "
                         "this computer's. Only correct if you genuinely hold "
                         "everyone's transcripts — otherwise it uploads empty "
                         "archives over real ones")
    ap.add_argument("--retries", type=int, default=8)
    ap.add_argument("--chunk", type=int, default=16,
                    help="MB per range request; each one is verified before the next")
    args = ap.parse_args()
    root = pathlib.Path(__file__).parent
    sys.exit({"pack": cmd_pack, "push": cmd_push,
              "pull": cmd_pull, "unpack": cmd_unpack,
              "lfs-push": cmd_lfs_push,
              "lfs-pull": cmd_lfs_pull}[args.action](args, root))


if __name__ == "__main__":
    main()
