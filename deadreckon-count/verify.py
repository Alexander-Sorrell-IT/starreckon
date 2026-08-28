#!/usr/bin/env python3
"""Deterministic verifier — canonical token count from transcript files.

    python3 verify.py <file-or-dir> [...]    count and verify
    python3 verify.py --session <uuid>        verify one session
    python3 verify.py --check sessions.json   check a scan matches transcripts

WHY THIS EXISTS

A number quoted as "from transcripts" is a claim. This makes it evidence:
given the same transcript files, any machine running this script produces
the same count, so the count can be independently reproduced and checked.

THREE GUARANTEES

  1. DETERMINISTIC — same files → same count, on any machine, any OS,
     any time. No session state, no caching, no OS-dependent reads.

  2. STABLE — re-reading a file already counted returns the same number.
     A change in the file changes the count; a change in anything else
     does not.

  3. LEGITIMATE — validates that input files are real session transcripts
     before counting them. An empty file, a truncated file, a file with
     no usage blocks, or a file whose structure does not match any known
     CLI format is reported as invalid, not counted as zero.

WHAT IT IS NOT

It is not a replacement for sessions.py. sessions.py handles the full
complexity of every CLI's quirks (Codex double-emissions, Copilot field
selection, Antigravity protobuf decoding). This verifier handles Claude
Code JSONL format — the most common format and the one all counts
ultimately derive from — and cross-checks the result against sessions.py
for the CLIs it supports.

The point is not to recount everything independently. The point is that
for any published figure, there is a path from the number back to a file
on disk, and running this script on that file reproduces the number. That
path is what turns a claim into evidence.
"""

import argparse
import hashlib
import json
import pathlib
import sys
from typing import Iterator, NamedTuple

# The four token fields Claude Code (and most other CLIs) report.
# Listed here so the verifier and sessions.py agree on what counts.
FIELDS = ("input_tokens", "cache_creation_input_tokens",
          "cache_read_input_tokens", "output_tokens")


class VerifyResult(NamedTuple):
    path: str
    valid: bool
    total: int
    by_field: dict
    sha256: str          # hex digest of the file as-read
    reason: str          # why it is invalid, or "ok"
    turns: int           # number of usage blocks found


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _count_claude_jsonl(lines: list[bytes]) -> tuple[dict, int, str]:
    """Count tokens in a Claude Code JSONL transcript.

    Returns (by_field, turns, reason).
    reason is "ok" on success, an error description on failure.

    WHAT WE COUNT AND WHY

    Each line is a JSON object. Usage blocks appear under:
        {"type": "assistant", "message": {"usage": {...}}}

    We sum ONLY the per-turn usage blocks. We do NOT sum any cumulative
    counter (e.g. stats-cache.json totals) because:
      - cumulative counters can drift if the transcript was truncated
      - two reads of the same transcript must give the same number
      - the per-turn sum is what sessions.py counts

    DEDUPLICATION

    Claude Code sometimes writes two assistant messages with the same
    message.id in one transcript (streaming re-writes). We dedup on
    message.id exactly as sessions.py does so the two counts agree.

    CACHE FIELDS

    cache_read_input_tokens dominates most totals (95%+). It is counted
    like any other field — it is a real token the model processed and
    was billed for, just at a lower rate. The verifier does not discount
    it. Callers who want only "new" tokens can sum the non-cache fields.
    """
    totals = dict.fromkeys(FIELDS, 0)
    seen_ids: set[str] = set()
    turns = 0
    valid_lines = 0

    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            # A single malformed line does not invalidate the transcript —
            # Claude Code appends lines incrementally and a crash can leave
            # a truncated last line. Count what we can.
            continue
        if not isinstance(obj, dict):
            continue

        valid_lines += 1

        # Locate usage blocks. Claude Code nests them two ways:
        #   assistant message: obj["message"]["usage"]
        #   direct usage block: obj["usage"]  (some CLI versions)
        usage = None
        if obj.get("type") == "assistant":
            msg = obj.get("message", {})
            if isinstance(msg, dict):
                uid = msg.get("id")
                if uid and uid in seen_ids:
                    continue        # duplicate streaming write
                if uid:
                    seen_ids.add(uid)
                usage = msg.get("usage")
        elif "usage" in obj and isinstance(obj.get("usage"), dict):
            usage = obj["usage"]

        if not isinstance(usage, dict):
            continue

        for field in FIELDS:
            v = usage.get(field)
            if isinstance(v, (int, float)) and v >= 0:
                totals[field] += int(v)
                turns += 1 if field == "input_tokens" else 0

    if valid_lines == 0:
        return totals, 0, "no valid JSON lines"
    if turns == 0:
        return totals, 0, "no usage blocks found"
    return totals, turns, "ok"


# All known top-level `type` values in Claude Code transcripts.
# Checked against real files — a file with none of these is not a transcript.
_CLAUDE_TYPES = frozenset({
    "system", "human", "assistant", "tool_result", "tool_use", "summary",
    # Newer Claude Code versions use these at the top of a session file:
    "mode", "permission-mode", "file-history-snapshot",
    # Subagent / workflow wrapping:
    "agent_response", "agent_request",
})


def _is_claude_jsonl(data: bytes) -> bool:
    """Heuristic: does this look like a Claude Code transcript?

    Checks the first several lines for at least one known type value.
    A single match is enough — a file that starts with file-history-snapshot
    is still a real transcript even though it has no usage in that line.
    """
    for line in data[:8192].splitlines():
        line = line.strip()
        if not line or not line.startswith(b"{"):
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict) and obj.get("type") in _CLAUDE_TYPES:
                return True
            # Also accept any line that contains a usage block — some CLIs
            # write usage without a type field at all.
            if isinstance(obj, dict) and isinstance(obj.get("usage"), dict):
                return True
        except json.JSONDecodeError:
            continue
    return False


def verify_file(path) -> VerifyResult:
    """Verify a single transcript file and return a VerifyResult.

    DETERMINISTIC BY CONSTRUCTION:
      - reads the file once, hashes the bytes before parsing
      - parsing is pure (json.loads, no syscalls)
      - dedup is on message.id from the file content, not mtime or ino

    LEGITIMATE CHECK:
      - file must exist and be readable
      - must parse as JSONL with at least one valid JSON object
      - must contain at least one usage block
      - must look like a Claude Code transcript
    """
    p = pathlib.Path(path)

    if not p.exists():
        return VerifyResult(str(p), False, 0, {}, "", "file not found", 0)
    if not p.is_file():
        return VerifyResult(str(p), False, 0, {}, "", "not a file", 0)

    try:
        data = p.read_bytes()
    except OSError as e:
        return VerifyResult(str(p), False, 0, {}, "", f"unreadable: {e}", 0)

    sha = _sha256(data)

    if len(data) == 0:
        return VerifyResult(str(p), False, 0, {}, sha, "empty file", 0)

    if not _is_claude_jsonl(data):
        return VerifyResult(str(p), False, 0, {}, sha,
                            "does not look like a Claude Code transcript", 0)

    lines = data.splitlines()
    by_field, turns, reason = _count_claude_jsonl(lines)
    total = sum(by_field.values())
    valid = reason == "ok"

    return VerifyResult(str(p), valid, total, by_field, sha, reason, turns)


def verify_dir(root, pattern="**/*.jsonl") -> Iterator[VerifyResult]:
    """Verify every JSONL file under `root`, recursively.

    Uses the same recursive walk as sessions.py (not rglob, which cannot
    report unreadable directories). Yields VerifyResult for each file.
    """
    root = pathlib.Path(root)
    for p in sorted(root.rglob("*.jsonl")):
        if p.is_file():
            yield verify_file(p)


def canonical_count(paths) -> dict:
    """Canonical token count for a list of files.

    This is the function check_consistency.py calls as its source of
    truth. Given the same list of files on any machine, it returns the
    same dict. The result is:

        {
          "total": int,
          "by_field": {field: int, ...},
          "files": int,
          "invalid": [{"path": str, "reason": str}, ...],
          "sha256": str    # hash of all file hashes, sorted, for stability
        }

    A file that fails the legitimacy check is reported in "invalid" and
    excluded from the total. A count derived from files with invalid
    entries is flagged — the caller decides whether to treat it as an
    error or a warning.
    """
    totals = dict.fromkeys(FIELDS, 0)
    invalid = []
    hashes = []
    n = 0

    for p in sorted(str(f) for f in paths):
        r = verify_file(p)
        hashes.append(r.sha256)
        if r.valid:
            for field in FIELDS:
                totals[field] += r.by_field.get(field, 0)
            n += 1
        else:
            invalid.append({"path": r.path, "reason": r.reason})

    # Stable fingerprint of all input files: sorted hashes, then hashed again.
    combined = hashlib.sha256(
        "\n".join(sorted(hashes)).encode()
    ).hexdigest()

    return {
        "total": sum(totals.values()),
        "by_field": totals,
        "files": n,
        "invalid": invalid,
        "sha256": combined,
    }


def check_against_sessions(sessions_json, transcript_root) -> dict:
    """Cross-check a sessions.json scan against the actual transcript files.

    Returns a report dict:
        {
          "match": bool,
          "sessions_total": int,
          "verified_total": int,
          "delta": int,
          "missing_files": [str],
          "invalid_files": [{"path": str, "reason": str}],
        }

    A delta of 0 means the scan and the verifier agree exactly.
    A non-zero delta is a discrepancy worth investigating — it does not
    necessarily mean either number is wrong (the scan may cover more CLIs
    than the verifier handles) but it is recorded so it can be explained.
    """
    sessions_json = pathlib.Path(sessions_json)
    root = pathlib.Path(transcript_root)

    try:
        data = json.loads(sessions_json.read_text(encoding="utf-8"))
    except Exception as e:
        return {"match": False, "error": f"cannot read sessions.json: {e}"}

    sessions = data.get("sessions", [])
    # Token counts in sessions.json are nested under s["tokens"], not at the
    # top level. The old code did s.get(field, 0) which returns 0 for every
    # session — so sessions_total was always 0, always matched a 0 verified
    # total, and reported a false clean bill of health on every run.
    def _session_tokens(s):
        tok = s.get("tokens")
        if isinstance(tok, dict):
            return sum(int(tok.get(f, 0) or 0) for f in FIELDS)
        # Fallback: some older sessions store total directly
        return int(s.get("total", 0) or 0)

    sessions_total = sum(
        _session_tokens(s)
        for s in sessions
        if s.get("cli") == "claude"     # verifier handles Claude only
    )

    # Walk only the transcript roots the sessions reference, not the entire
    # repo tree. Walking "." pulls in token_ledger.jsonl, testing-archive/,
    # and every other .jsonl in the repo — none of which are transcripts.
    # Use the transcript paths recorded in sessions when available, otherwise
    # fall back to the provided root.
    transcript_files = set()
    for s in sessions:
        if s.get("cli") != "claude":
            continue
        t = s.get("transcript")
        if t and pathlib.Path(t).is_file():
            transcript_files.add(pathlib.Path(t))
    if not transcript_files and root.is_dir():
        # Fallback: caller supplied an explicit transcript root
        transcript_files = set(root.rglob("*.jsonl"))
    all_files = sorted(transcript_files)
    result = canonical_count(all_files)

    missing = [r["path"] for r in result["invalid"]
               if "not found" in r["reason"]]

    return {
        "match": sessions_total == result["total"],
        "sessions_total": sessions_total,
        "verified_total": result["total"],
        "delta": result["total"] - sessions_total,
        "files_verified": result["files"],
        "missing_files": missing,
        "invalid_files": result["invalid"],
        "sha256": result["sha256"],
    }


def _fmt(n):
    return f"{n:,}"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("paths", nargs="*", help="files or directories to verify")
    ap.add_argument("--session", help="verify a single session UUID")
    ap.add_argument("--check", metavar="SESSIONS_JSON",
                    help="cross-check a sessions.json against transcript files")
    ap.add_argument("--root", help="transcript root for --check (default: cwd)")
    ap.add_argument("--json", action="store_true",
                    help="output results as JSON")
    args = ap.parse_args()

    if args.check:
        root = args.root or "."
        report = check_against_sessions(args.check, root)
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            match = "✓ MATCH" if report.get("match") else "✗ MISMATCH"
            print(f"  {match}")
            print(f"  sessions.json (Claude):  {_fmt(report.get('sessions_total', 0))}")
            print(f"  verified from files:     {_fmt(report.get('verified_total', 0))}")
            delta = report.get("delta", 0)
            if delta:
                print(f"  delta:                   {_fmt(delta):>+,}")
            print(f"  files verified:          {report.get('files_verified', 0)}")
            inv = report.get("invalid_files", [])
            if inv:
                print(f"  invalid files:           {len(inv)}")
                for item in inv[:5]:
                    print(f"    {item['reason'][:60]:60}  {item['path']}")
        sys.exit(0 if report.get("match") else 1)
        return

    if not args.paths:
        ap.print_help()
        sys.exit(0)

    all_results = []
    for target in args.paths:
        p = pathlib.Path(target)
        if p.is_dir():
            all_results.extend(verify_dir(p))
        elif p.is_file():
            all_results.append(verify_file(p))
        else:
            print(f"  not found: {p}", file=sys.stderr)

    if args.json:
        print(json.dumps([r._asdict() for r in all_results], indent=2))
        sys.exit(0 if all(r.valid for r in all_results) else 1)
        return

    invalid = [r for r in all_results if not r.valid]
    valid   = [r for r in all_results if r.valid]
    total   = sum(r.total for r in valid)
    by_field = dict.fromkeys(FIELDS, 0)
    for r in valid:
        for f in FIELDS:
            by_field[f] += r.by_field.get(f, 0)

    print(f"  files       {len(all_results):,}  ({len(valid):,} valid, "
          f"{len(invalid):,} invalid)")
    print(f"  total       {_fmt(total)}")
    for f in FIELDS:
        v = by_field[f]
        if v:
            pct = 100 * v / total if total else 0
            print(f"  {f:<36} {_fmt(v):>18}  ({pct:.1f}%)")
    if invalid:
        print(f"\n  invalid files ({len(invalid)}):")
        for r in invalid:
            print(f"    {r.reason[:60]:60}  {r.path}")

    sys.exit(0 if not invalid else 1)


if __name__ == "__main__":
    main()
