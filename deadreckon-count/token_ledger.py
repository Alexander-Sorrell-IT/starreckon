#!/usr/bin/env python3
"""An append-only token ledger. The lifetime total nothing can take away.

    python3 token_ledger.py --record     observe now, append what is new
    python3 token_ledger.py              what the ledger says
    python3 token_ledger.py --compare    ledger vs the current scan

WHY, WHEN lifetime.json ALREADY EXISTS

`lifetime.json` is DERIVED. run.py lists it under DERIVED_ROOT and deletes it on
every rebuild, because it is recomputed from whatever transcripts are on disk at
that moment. That is correct for a report and useless as a record: when Claude's
cleanup deletes a month of transcripts, the next scan simply reports a smaller
lifetime, and nothing in the file says anything was lost.

`history_ledger` in sessions.json is closer — it remembers 567 sessions whose
transcript is already gone — but it carries PROMPT counts, not tokens. It can
tell you a session existed. It cannot tell you what it cost.

And the vendors do not fill the gap. Verified against their own documentation:

    Claude        stats-cache.json — a real lifetime counter, the only one
    Gemini        none. Telemetry is "enabled": false by default and there is
                  no default outfile, so nothing is written unless you turn it on
    Copilot       none locally. The quota lives on github.com, and GitHub's own
                  counter is a documented undercount
    Antigravity   counts are not persisted; they must be reconstructed from
                  protobuf BLOBs, which sessions.read_antigravity does

So for seven of the eight CLIs this repository counts, if this file does not
remember the number, nobody does.

WHY IT IS KEYED BY SESSION, NOT BY DAY

A session's token count is a fact about that session and never changes. A day's
is an aggregate that depends on how sessions are attributed to days — and they
are attributed to their START date, so a session running from the 7th to the 8th
puts everything on the 7th. Measured on this machine: ten days where by_day holds
hundreds of millions and the per-session view holds zero, with the grand totals
agreeing to 18,395. Keyed by session, there is nothing to disagree about.

WHY A RECOUNT MUST NOT BE OUTVOTED BY A STALE MAXIMUM

Taking the maximum ever seen is what makes a deletion harmless. It is also what
would make a CORRECTION permanent: fixing the dedup rule cut this machine from
14,529,373,789 to 6,608,178,238, because the old number counted streaming
re-writes as separate calls. A naive max would hold that wrong 14.5 billion
forever and call it "lifetime".

So every row carries the scanner_version that produced it, plus the normalized
path, byte count and SHA-256 of every input file that supplied the session. A
session's value is still the maximum among rows from the NEWEST scanner that has
ever seen it. A newer scanner may lower an older value only when one of its own
observations proves every previously observed source still exists unchanged (or
has grown). An older scanner's number is used only for sessions the current one
cannot see at all — which is exactly the case this file exists for: the
transcript is gone, so no newer scanner will ever read it again, and the last
observation is the only evidence left.

That rule gives both properties at once. Deleting or truncating a transcript
cannot lower the total. Fixing the counter can. Rows written before source
evidence was added deliberately retain the legacy scanner-ranking behavior:
their missing evidence does not freeze later corrections.
"""

import argparse
import contextlib
import datetime
import json
import os
import pathlib
import platform
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

LEDGER = "token_ledger.jsonl"
FIELDS = ("input_tokens", "cache_creation_input_tokens",
          "cache_read_input_tokens", "output_tokens")


def _sources(value):
    """Return only complete source evidence from a session or ledger row."""
    out = []
    for item in value or []:
        if not isinstance(item, dict):
            continue
        path, size, digest = item.get("path"), item.get("bytes"), item.get("sha256")
        if (not isinstance(path, str) or not path or isinstance(size, bool)
                or not isinstance(size, int) or size < 0
                or not isinstance(digest, str) or len(digest) != 64):
            continue
        try:
            int(digest, 16)
        except ValueError:
            continue
        item = {"path": path, "bytes": size, "sha256": digest.lower()}
        if item not in out:
            out.append(item)
    return sorted(out, key=lambda item: (item["path"], item["bytes"], item["sha256"]))


def _merge_sources(*groups):
    """Keep every source identity at its largest observed size.

    Equal-size, different-hash observations are deliberately both retained: a
    same-sized rewrite is evidence of a changed contributor, not a replacement
    that may erase the earlier evidence.
    """
    largest, hashes = {}, {}
    for group in groups:
        for item in _sources(group):
            path, size = item["path"], item["bytes"]
            if size > largest.get(path, -1):
                largest[path], hashes[path] = size, {item["sha256"]}
            elif size == largest.get(path):
                hashes.setdefault(path, set()).add(item["sha256"])
    return [{"path": path, "bytes": size, "sha256": digest}
           for path, size in sorted(largest.items())
           for digest in sorted(hashes[path])]


def _evidence_matches(current, previous):
    """Whether one observation proves every earlier contributing file survived."""
    current, previous = _sources(current), _merge_sources(previous)
    if not previous:
        return True
    for old in previous:
        if not any(new["path"] == old["path"]
                  and (new["bytes"] > old["bytes"]
                       or (new["bytes"] == old["bytes"]
                           and new["sha256"] == old["sha256"]))
                  for new in current):
            return False
    return True


def _max_row(rows):
    """Maximum per field, matching the historical same-scanner behavior."""
    out = {}
    for row in rows:
        for key in FIELDS + ("total",):
            out[key] = max(int(out.get(key, 0) or 0), int(row.get(key, 0) or 0))
    return out


def _rows(mdir):
    """Every observation ever appended, oldest first."""
    p = paths.find(mdir, LEDGER) or (paths.machine(mdir) / LEDGER)
    if not p.is_file():
        return []
    out = []
    # errors="replace", or the per-line try/except below never runs. Decoding
    # the whole file strictly raises before the loop starts, so ONE torn
    # multi-byte write makes every row unreadable and record() can never append
    # again. Reproduced: 3 good rows + 1 bad byte ->
    #   UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff
    # The docstring below promises a bad write costs one row. This is what
    # makes that true. ensure_ascii=False on the way out means non-ASCII is
    # written deliberately, and `model` comes from GGUF filenames.
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            # One malformed line must not discard the rest of the record. This
            # file is append-only precisely so a bad write costs one row.
            continue
    return out


def observe(mdir, scan_dir=None):
    """What a scan says, per session. {(cli, session_id): row}

    `scan_dir` is where to READ sessions.json from, when it is not the machine
    folder. The daemon scans into a scratch directory and passes it here: it
    must not write sessions.json into the machine folder, because that leaves it
    newer than totals.json and trips the fatal cross-check in
    check_consistency.py, and dirties git every six hours.
    """
    f = paths.find(scan_dir or mdir, "sessions.json")
    if not f:
        return {}, None
    d = json.loads(f.read_text(encoding="utf-8"))
    ver = d.get("scanner_version") or "pre-versioning"
    out = {}
    for s in d.get("sessions", []):
        sid = s.get("session_id")
        cli = s.get("cli")
        if not sid or not cli:
            continue
        tk = s.get("tokens") or {}
        row = {k: int(tk.get(k, 0) or 0) for k in FIELDS}
        if not any(row.values()) and not s.get("total"):
            continue
        row["total"] = int(s.get("total") or sum(row.values()))
        row["start"] = (s.get("start") or "")[:10]
        row["model"] = s.get("model") or "unknown"
        sources = _sources(s.get("sources"))
        if sources:
            row["sources"] = sources
        out[(cli, sid)] = row
    return out, ver


# CLIs that keep their own lifetime counter on disk, independently of this
# ledger. For these the ledger supplements the vendor counter; together they
# produce a TRUE lifetime figure (★). For every other CLI the ledger is the
# ONLY record, and it starts from when the daemon was first run (†).
#
# Verified against vendor documentation — see README.md "token_ledger.py":
#   Claude  stats-cache.json + .claude.json lastTotalCacheReadInputTokens
#   All others: no persistent counter exists on disk
NATIVE_LIFETIME_CLIS = frozenset({"claude"})


def cli_marker(cli):
    """★ for CLIs with a native lifetime counter, † for the rest.

    ★  Claude Code — true lifetime. The vendor's own counter on disk
       (stats-cache.json) tracks usage even for deleted transcripts, and
       the ledger adds sessions the vendor counter may not have seen.

    †  All other CLIs — from daemon start. No vendor counter exists, so
       the ledger is the only record. The figure is honest about when it
       starts: it covers from the first time the daemon ran on this machine,
       not from the beginning of time.

    Used in every report that quotes a lifetime figure so a reader can see
    immediately which numbers are comparable across machines.
    """
    return "★" if cli in NATIVE_LIFETIME_CLIS else "†"


def lifetime(mdir):
    """The number the ledger stands behind, and how it was reached.

    For each session: among every observation of it, keep only those from the
    newest scanner_version that ever saw it, and take the maximum per field.
    A lower result from that newest scanner needs one complete source-evidence
    observation; legacy rows without evidence retain the earlier behavior.

    Returns:
        total           int — grand total across all CLIs
        by_cli          {cli: int} — per-CLI totals
        by_cli_marked   {cli: {"total": int, "marker": "★"|"†"}}
        sessions        int — number of distinct sessions
        daemon_started  str|None — ISO timestamp from cli-config.json
    """
    best = {}                   # (cli, sid) -> (version_rank, row)
    # LAST appearance, not first. scanner_version is a CONTENT HASH of
    # sessions.py + analyze_tokens.py — it has no monotonicity, so a version can
    # come back. `git checkout -- sessions.py` resurrects an earlier hash, and
    # with setdefault it kept its old low rank forever: every row it wrote after
    # the rollback was discarded for any session an intervening version had seen.
    #
    # Reproduced: rows A=1000, B=2000, A=5000, A=9000 gave a lifetime of 2000.
    # Ranking by last appearance means "the scanner most recently used", which
    # is what a rollback intends. Verified a no-op on the real ledger, where no
    # version has ever reappeared.
    order = {}                  # version -> last-seen index
    rows = _rows(mdir)
    for i, r in enumerate(rows):
        v = r.get("scanner") or "pre-versioning"
        order[v] = i
    grouped = {}
    for r in rows:
        key = (r.get("cli"), r.get("session_id"))
        if None in key:
            continue
        rank = order.get(r.get("scanner") or "pre-versioning", -1)
        grouped.setdefault(key, []).append((rank, r))

    for key, observed in grouped.items():
        newest = max(rank for rank, _row in observed)
        current = [row for rank, row in observed if rank == newest]
        older = [row for rank, row in observed if rank < newest]
        historic = _max_row(older)
        historic_total = int(historic.get("total", 0) or 0)

        # A higher total is always additive. For a lower result, one *single*
        # current observation must account for every old contributing file. Do
        # not union separate partial observations here: A-only plus B-only must
        # never masquerade as one scan that read A and B together.
        allowed = current
        prior_sources = _merge_sources(*(row.get("sources") for row in older))
        if (older and int(_max_row(current).get("total", 0) or 0) < historic_total
                and prior_sources):
            allowed = [
                row for row in current
                if (int(row.get("total", 0) or 0) >= historic_total
                    or _evidence_matches(row.get("sources"), prior_sources))
            ]
        if allowed:
            best[key] = (newest, _max_row(allowed))
        else:
            # Existing source evidence makes the lower observation unsafe. Keep
            # the historic high-water value; rejected-row evidence remains
            # append-only for a later scanner to inspect.
            best[key] = (newest, historic)
    per_cli, total = {}, 0
    for (cli, _sid), (_rank, row) in best.items():
        n = int(row.get("total") or 0)
        per_cli[cli] = per_cli.get(cli, 0) + n
        total += n

    by_cli_marked = {
        cli: {"total": v, "marker": cli_marker(cli)}
        for cli, v in per_cli.items()
    }

    # Daemon start from cli-config.json — the † baseline timestamp
    daemon_started = None
    try:
        import config as _cfg
        daemon_started = _cfg.daemon_started()
    except Exception:
        pass

    return {
        "total": total,
        "by_cli": per_cli,
        "by_cli_marked": by_cli_marked,
        "sessions": len(best),
        "daemon_started": daemon_started,
    }


@contextlib.contextmanager
def _exclusive(mdir):
    """Serialise read-compute-append. Two writers is the normal case now.

    The daemon records on its own schedule and `run.py update` records while a
    scan is fresh, so two processes can reach this within the same second.
    Measured with four concurrent writers on 269 sessions: 514 rows written
    instead of 269 — 245 duplicates, because each one read the file before any
    of them had appended.

    Nothing was WRONG: no malformed rows, no errors, and the lifetime total came
    out identical, because a session's value is the maximum across rows and a
    duplicate is just that maximum written twice. This is about the file not
    doubling every time two things run at once.

    Advisory and best-effort. Windows has no fcntl, and the correctness of the
    total does not depend on the lock — only its tidiness does, so a platform
    without it degrades to duplicate rows rather than to a wrong number.
    """
    lock = paths.machine(mdir) / (LEDGER + ".lock")
    fh = None
    try:
        import fcntl
        fh = lock.open("w")
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
    except Exception:  # noqa: BLE001 - no fcntl, or no permission: proceed unlocked
        pass
    try:
        yield
    finally:
        if fh is not None:
            try:
                import fcntl
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except Exception:  # noqa: BLE001
                pass
            fh.close()


def record(mdir, apply=True, scan_dir=None):
    """Append every session whose numbers are new or larger. Never rewrites."""
    with _exclusive(mdir):
        return _record_locked(mdir, apply, scan_dir)


def _machine_uuid_from_mid(mdir):
    """Read hardware_uuid from .machine-id, or None."""
    try:
        import json as _json
        info = _json.loads(
            (pathlib.Path(mdir) / ".machine-id").read_text(encoding="utf-8"))
        return info.get("hardware_uuid") or None
    except Exception:
        return None


def _record_locked(mdir, apply=True, scan_dir=None):
    seen, ver = observe(mdir, scan_dir)
    if ver is None:
        return 0, 0, "no sessions.json — nothing to observe"
    known, known_evidence = {}, {}
    for r in _rows(mdir):
        key = (r.get("cli"), r.get("session_id"))
        if r.get("scanner") == ver:
            prior = known.get(key)
            if prior is None:
                known[key] = dict(r)
            else:
                known[key] = _max_row((prior, r))
            evidence = _sources(r.get("sources"))
            if evidence not in known_evidence.setdefault(key, []):
                known_evidence[key].append(evidence)

    new = []
    stamp = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    hw_uuid = _machine_uuid_from_mid(mdir)
    for (cli, sid), row in sorted(seen.items()):
        was = known.get((cli, sid))
        sources = _sources(row.get("sources"))
        if (was and all(int(was.get(k, 0) or 0) >= row[k] for k in FIELDS)
                and sources in known_evidence.get((cli, sid), [])):
            continue            # this scanner already recorded this exact evidence
        entry = {"observed": stamp, "scanner": ver, "machine": mdir.name,
                 "cli": cli, "session_id": sid, **row}
        if sources:
            entry["sources"] = sources
        if hw_uuid:
            entry["hardware_uuid"] = hw_uuid
        new.append(entry)
    if new and apply:
        p = paths.machine(mdir) / LEDGER
        with p.open("a", encoding="utf-8") as fh:
            for r in new:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(new), len(seen), "ok"


def this_machine(root):
    """Return the machine folder that belongs to this host, or None.

    UUID match is tried first (survives hostname changes and OS reinstalls),
    then hostname fallback for folders written before UUID support existed.
    Mirrors the logic in update.py:owned_folder so the two cannot disagree.
    """
    host = platform.node()
    try:
        from install import hardware_uuid as _hw_uuid
        current_uuid = _hw_uuid()
    except Exception:
        current_uuid = None

    for d in paths.machine_folders(root):
        f = d / ".machine-id"
        if not f.is_file():
            continue
        try:
            info = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if current_uuid and info.get("hardware_uuid"):
            if info["hardware_uuid"].lower() == current_uuid.lower():
                return d
        if info.get("hostname") == host:
            return d
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="store_true", help="observe and append")
    ap.add_argument("--compare", action="store_true",
                    help="ledger against the current scan")
    ap.add_argument("--machine", default=None)
    ap.add_argument("--root", default=str(pathlib.Path(__file__).parent))
    a = ap.parse_args()

    root = pathlib.Path(a.root)
    mdir = pathlib.Path(a.machine) if a.machine else this_machine(root)
    if not mdir:
        print("  no machine folder for this host — run `python3 run.py update` first")
        return 1

    if a.record:
        n, total, note = record(mdir)
        print(f"  {mdir.name}: {n} new observation(s) of {total} session(s) — {note}")

    lt = lifetime(mdir)
    if not lt["sessions"]:
        print("  ledger is empty — run with --record")
        return 0
    print(f"\n  LEDGER — {mdir.name}")
    print(f"  {'cli':<16}{'tokens':>20}")
    for cli, n in sorted(lt["by_cli"].items(), key=lambda kv: -kv[1]):
        print(f"  {cli:<16}{n:>20,}")
    print(f"  {'':<16}{'':>20}")
    print(f"  {'LIFETIME':<16}{lt['total']:>20,}   {lt['sessions']:,} sessions")

    if a.compare:
        seen, _ = observe(mdir)
        now = sum(int(r.get("total") or 0) for r in seen.values())
        d = lt["total"] - now
        print(f"\n  current scan sees  {now:>20,}   {len(seen):,} sessions")
        if d > 0:
            print(f"  ledger holds       {d:>20,} MORE")
            print("  -> that is history whose transcripts are gone. The ledger is")
            print("     the only remaining evidence of it.")
        elif d < 0:
            print(f"  the scan is        {-d:>20,} AHEAD — run --record")
        else:
            print("  they agree — nothing has been lost since the last record")
    return 0


if __name__ == "__main__":
    sys.exit(main())
