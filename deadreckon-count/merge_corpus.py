#!/usr/bin/env python3
"""Merge every machine's corpus into one tree, for tools that read a single home.

Each computer exports its own folder into `deadreckon-record`. Nothing consumes those
separately — profile tools read ONE `~/.claude/projects`. This collapses all of
them into that shape, once, after the machines have reported.

    python3 merge_corpus.py                          # ~/deadreckon-record -> merged/
    python3 merge_corpus.py --corpus DIR --out DIR

Then point a tool at the result as if it were a home directory:

    cd merged && HOME=$(pwd) npx standout ...

TWO THINGS IT HAS TO GET RIGHT

Project directories collide. Every machine numbers its own `-workspace-p001`
upward, so a naive copy silently overwrites one machine's first project with
another's. They are renumbered globally here, and the mapping is recorded.

Sessions can appear twice. Within a machine that is already handled at export,
but a session synced or copied between machines would be counted twice in
anything derived from the merged tree. Message uuids are unique per API call, so
a second sighting of one is dropped and reported.

WHAT THIS IS NOT

It does not re-redact. Each machine's export already did that, and doing it again
here would hide an export that had skipped it. The verifier below reads the
merged tree and fails loudly instead — a merge is the last point where a leak is
still cheap to catch.
"""

import argparse
import json
import pathlib
import re
import shutil

LEAK = {
    "secret": re.compile(
        r"gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|"
        r"sk-ant-[A-Za-z0-9_-]{20,}|sk-(?:proj-)?[A-Za-z0-9]{32,}|"
        r"xai-[A-Za-z0-9]{20,}|A[KS]IA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}|"
        r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}|BEGIN[A-Z ]*PRIVATE KEY"),
    # Case-SENSITIVE, deliberately. Applying re.I here made /Users/ match
    # /users/ in URLs and reported 31 leaks that were all web paths:
    # api.github.com/users/<name>, docs.github.com/rest/users/users,
    # /api/v2/users/whoami. A home directory is /Users on macOS and /home on
    # Linux, both fixed case; a URL route is not a filesystem path.
    "home dir": re.compile(
        r"/home/[A-Za-z0-9._-]+|/Users/[A-Za-z0-9._-]+|/root/"),
    # Windows genuinely varies in case, so it gets its own pattern.
    "windows home": re.compile(r"[A-Za-z]:\\Users\\[A-Za-z0-9._-]+", re.I),
    # Kept in step with export_corpus.py's rule of the same shape. The leak it
    # was written for — an internal log server address, value deliberately not
    # repeated here — was caught by verify_payload.py, and a rule that lives in
    # only one of the three checks is the drift that produced every path/JWT
    # mismatch before it.
    "private ip": re.compile(
        r"\b(?:10\.\d{1,3}|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b"),
}


def scan_leaks(o, hits, keep):
    """Check decoded strings, never raw bytes.

    Scanning the file text reports `\\n@pytest.fixture` as an email address —
    a Python decorator after an escaped newline — and produced 613 false
    positives the first time this was done that way.
    """
    if isinstance(o, dict):
        for k, v in o.items():
            scan_leaks(k, hits, keep)
            scan_leaks(v, hits, keep)
    elif isinstance(o, list):
        for v in o:
            scan_leaks(v, hits, keep)
    elif isinstance(o, str):
        for name, rx in LEAK.items():
            for m in rx.findall(o):
                hits[name] = hits.get(name, 0) + 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(pathlib.Path.home() / "deadreckon-record"))
    ap.add_argument("--out", default=None, help="default: <repo>/merged")
    ap.add_argument("--keep-email", default="alexander.sorrell.it@gmail.com")
    args = ap.parse_args()

    corpus = pathlib.Path(args.corpus)
    if not corpus.is_dir():
        raise SystemExit(f"no corpus at {corpus} — clone deadreckon-record first")
    out = pathlib.Path(args.out) if args.out else pathlib.Path(__file__).parent / "merged"
    dst = out / ".claude" / "projects"
    if out.exists():
        shutil.rmtree(out)
    dst.mkdir(parents=True)

    machines = sorted(d for d in corpus.iterdir()
                      if d.is_dir() and (d / ".claude" / "projects").is_dir())
    if not machines:
        raise SystemExit(f"no machine folders in {corpus}")

    seq = 0
    seen = set()
    dupes = 0
    mapping = []
    per_machine = {}
    leaks = {}
    lines_total = 0

    for m in machines:
        kept_here = files_here = empty_here = 0
        for proj in sorted(p for p in (m / ".claude" / "projects").iterdir() if p.is_dir()):
            seq += 1
            od = dst / f"-workspace-p{seq:04d}"
            od.mkdir(parents=True, exist_ok=True)
            for f in sorted(proj.glob("*.jsonl")):
                files_here += 1
                lines = []
                for ln in f.open(encoding="utf-8", errors="ignore"):
                    ln = ln.strip()
                    if not ln:
                        continue
                    lines_total += 1
                    try:
                        o = json.loads(ln)
                    except Exception:
                        continue
                    u = o.get("uuid")
                    if u:
                        if u in seen:
                            dupes += 1
                            continue
                        seen.add(u)
                    scan_leaks(o, leaks, args.keep_email)
                    lines.append(ln)
                    kept_here += 1
                # WRITTEN WHETHER OR NOT `lines` IS EMPTY, for the same reason
                # the exporter is: a file's EXISTENCE and a file's CONTENT are
                # two different facts, and `if lines:` decided silently that
                # only one of them counts.
                #
                # It reaches here empty in three real shapes, and none of them
                # means the session did not happen: every row was already
                # claimed by a transcript this merge read earlier (the uuid
                # dedup is global across machines, and a session synced between
                # two machines is exactly what that dedup is FOR); every line
                # failed to parse; or the export wrote it empty on purpose,
                # which it now does deliberately. Measured on the fixture that
                # pins this: 3 transcripts in, 1 out.
                #
                # That silence was worse here than in the exporter, because
                # `per_machine[...]["files"]` counts what was WALKED — so the
                # report said 3 files for a tree holding 1, and nothing
                # anywhere said the other 2 had been dropped. Written empty and
                # COUNTED, so files in equals files out.
                #
                # A session id can exist on two machines; keep both by
                # qualifying the name rather than letting one win silently.
                name = f.name
                if (od / name).exists():
                    name = f"{f.stem}--{m.name}{f.suffix}"
                (od / name).write_text("\n".join(lines) + "\n" if lines else "",
                                       encoding="utf-8")
                if not lines:
                    empty_here += 1
            mapping.append({"machine": m.name, "source": proj.name, "merged_as": od.name})
        per_machine[m.name] = {"files": files_here, "lines": kept_here,
                               "empty": empty_here}

    written = sorted(dst.rglob("*.jsonl"))
    size = sum(f.stat().st_size for f in written)
    stamp = __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds")

    # `seen` holds message UUIDs, not lines. A transcript line without a uuid
    # (summaries, file-history snapshots) is still written — it just never
    # enters the set. Reporting len(seen) as "kept" therefore understated the
    # tree by 181,997 lines and read as though they had been dropped, while
    # `duplicates 0` said nothing had been. Count what was actually written.
    kept_total = sum(v["lines"] for v in per_machine.values())
    # files_read is what was walked; files_written is COUNTED OFF THE OUTPUT
    # TREE, not restated from the same variable. The two must be equal, and a
    # report that derives both from one number cannot tell you when they are
    # not — which is the whole reason `if lines:` went unnoticed here.
    files_total = sum(v["files"] for v in per_machine.values())
    empty_total = sum(v["empty"] for v in per_machine.values())

    (out / "MERGE.json").write_text(json.dumps({
        "generated_at": stamp, "machines": [m.name for m in machines],
        "projects": seq, "lines_read": lines_total, "lines_kept": kept_total,
        "files_read": files_total, "files_written": len(written),
        "files_without_a_unique_row": empty_total,
        "message_uuids": len(seen), "duplicates_dropped": dupes,
        "bytes": size, "leaks": leaks, "per_machine": per_machine,
        "mapping": mapping,
    }, indent=1), encoding="utf-8")

    rows = "\n".join(f"| `{k}` | {v['files']} | {v['lines']:,} |"
                     for k, v in sorted(per_machine.items()))
    (out / "README.md").write_text(f"""# Merged corpus — {len(machines)} computer(s)

Every machine's redacted transcripts collapsed into one `.claude/projects/`
tree, because profile tools read a single home directory. Generated {stamp}.

| machine | files | lines kept |
|---|---:|---:|
{rows}

**{seq} projects · {len(written):,} transcripts · {kept_total:,} lines · {len(seen):,} unique messages · {size/1e6:.1f} MB**
{f"· {dupes:,} duplicate messages dropped" if dupes else "· no duplicates found"}

{empty_total} of the merged transcripts are empty. Every transcript that exists in
any machine's export is in this tree, but message uuids are de-duplicated ACROSS
machines: a session synced or copied between two computers arrives twice, and
whichever machine is read first keeps its rows. A file whose every row was kept
under another name is still written, because it existed — empty rather than
absent, and no message counted twice.

Project folders are renumbered globally: every machine numbers its own from
`-workspace-p001`, so copying them together unchanged would have one machine's
first project overwrite another's. `MERGE.json` maps each merged folder back to
the machine and source folder it came from.

## Use

```bash
cd {out.name} && HOME=$(pwd) npx standout ...
```

## Leak check on the merged tree

{"**CLEAN** — no credentials or home directories found in " + f"{lines_total:,} decoded lines." if not leaks else "**LEAKS PRESENT — do not publish:** " + ", ".join(f"{k} x{v}" for k, v in leaks.items())}

Checked on the decoded JSON, not the file text. Scanning raw bytes reports
`\\n@pytest.fixture` as an email address — a decorator after an escaped newline —
and produced 613 false positives when it was first done that way.

This does not re-redact; each machine's export already did. Re-running redaction
here would mask an export that had skipped it.
""", encoding="utf-8")

    print(f"  machines       {len(machines)}  {[m.name for m in machines]}")
    print(f"  projects       {seq}")
    print(f"  files          {files_total:,} read, {len(written):,} written"
          f"  ({empty_total:,} had no unique row and are empty)")
    print(f"  lines          {lines_total:,} read, {kept_total:,} written"
          f"  ({len(seen):,} carry a message uuid)")
    print(f"  duplicates     {dupes:,} dropped")
    print(f"  size           {size/1e6:.1f} MB")
    print(f"  leak check     {'CLEAN' if not leaks else 'LEAKS: ' + str(leaks)}")
    print(f"  wrote          {out}")
    if leaks:
        raise SystemExit("merged tree contains leaks — do not use it")


if __name__ == "__main__":
    main()
