#!/usr/bin/env python3
"""A five-machine fleet with PLANTED totals, built somewhere disposable.

TWO FIXTURES, KEPT ON PURPOSE, AND THIS NOTE IS THE MERGE RECORD.

This was written when `fleet_fixture.py` had not landed, under the assumption
that one of the two would be deleted. Neither was, and the reason is that they
are not two versions of one thing — they build different trees for different
layers, and each one's suite is the only cover the other's layer does not have:

    fleet_fixture.py       five synthetic HOME directories full of real CLI
                           records, so the READERS can be run across three
                           platform layouts. Answers "does this reader find and
                           count what is on disk". 182 checks in test_fleet.py.

    fleet_merge_fixture.py (this file) a count REPO and a CORPUS with planted
                           per-machine totals, so combine.py, corpus_reports.py,
                           count_corpus.py and check_consistency.py can be run
                           over five machine folders. Answers "do five machines
                           sum correctly, and can a missing one be seen".
                           34 checks in test_fleet_merge.py.

Deleting this one would delete the only coverage of the merge arithmetic —
including the guard on the 16,482,383,637 phantom gap. Deleting the other would
delete the only coverage of the readers off Linux. So the collision was in the
FILENAME and nowhere else, and only the filename was resolved.

WHY A FIXTURE AND NOT THE REAL FLEET

Four of the five machine folders in this repository were produced somewhere
else and one was produced here. Nobody can say what the fleet total OUGHT to
be, so every fleet arithmetic bug is unfalsifiable against real data: whatever
the code prints is the only candidate answer. Here the answer is chosen first —

    alpha    1,000,000,000
    bravo      200,000,000
    charlie     30,000,000
    delta        4,000,000
    echo           500,000
    -------------------------
    FLEET    1,234,500,000

— and the digits are deliberately disjoint, so a dropped, doubled or partly
counted machine names itself in the total rather than merely changing it.

The fixture builds TWO trees, because the two derivations this repo compares
live in two repositories:

    <dest>/count     a repo root: every .py symlinked, machines.json,
                     accounts.json, and <folder>/machine-readable/{totals,
                     sessions}.json per machine
    <dest>/record    a corpus: <folder>/.claude/projects/<p>/<sid>.jsonl
                     carrying real usage rows, plus MANIFEST.json

Symlinks, not copies: `pathlib.Path(__file__).parent` is the root every script
uses, and it resolves from the path the script was INVOKED by, so
`python3 <dest>/count/combine.py` treats <dest>/count as the fleet while still
executing the code under test.
"""

import datetime
import json
import os
import pathlib
import shutil
import subprocess

import paths

# Bare names, so the layout constant is the only thing joined to a path.
TOTALS, SESSIONS = "totals.json", "sessions.json"
MANIFEST, STATS = "MANIFEST.json", "stats.json"

FIELDS = ("input_tokens", "cache_creation_input_tokens",
          "cache_read_input_tokens", "output_tokens")

MODEL = "claude-sonnet-4-5-20260101"
ACCOUNT = "fixture@example.com"
STAMP = "2026-01-02T03:04:05+00:00"

# folder, label, planted machine total
FLEET = [
    ("alpha",   "Alpha",   1_000_000_000),
    ("bravo",   "Bravo",     200_000_000),
    ("charlie", "Charlie",    30_000_000),
    ("delta",   "Delta",       4_000_000),
    ("echo",    "Echo",          500_000),
]
FLEET_TOTAL = sum(t for _, _, t in FLEET)          # 1,234,500,000


def _split(total):
    """total -> two session amounts that add back to it exactly."""
    a = total * 6 // 10
    return [a, total - a]


def _fields(n):
    """One number as the four billed buckets, summing to exactly n."""
    d = dict.fromkeys(FIELDS, 0)
    d["input_tokens"] = n
    return d


def _totals_json(label, total, sess_n, version):
    acct = {
        "account": ACCOUNT,
        "config_dir": "~/.claude",
        "sessions": sess_n,
        "turns": sess_n,
        "grand_total": total,
        "totals": _fields(total),
        "by_model": {MODEL: _fields(total)},
        "by_day": {"2026-01-01": _fields(total)},
        "by_project": {"p": _fields(total)},
        "by_provider": {"anthropic": _fields(total)},
    }
    return {
        "machine": label,
        "generated_at": STAMP,
        "scanner_version": version,
        "anthropic_only_tokens": total,
        "by_provider": {"anthropic": total},
        "other_tools": [],
        "grand_total_tokens": total,
        "accounts": [acct],
    }


def _sessions_json(label, sids, amounts, version):
    rows = []
    for sid, n in zip(sids, amounts):
        rows.append({
            "cli": "claude", "session_id": sid, "account": ACCOUNT,
            "project": "p", "model": MODEL, "provider": "anthropic",
            "start": "2026-01-01T00:00:00+00:00",
            "end": "2026-01-01T00:10:00+00:00",
            "turns": 1, "duration_min": 10.0,
            "tokens": _fields(n), "total": n, "sent": n, "received": 0,
        })
    return {
        "machine": label,
        "generated_at": STAMP,
        "scanner_version": version,
        "scanner_features": ["claude"],
        "uncountable_tools": [],
        "readers": [{"cli": "claude", "sessions": len(rows),
                     "tokens": sum(amounts), "active_min": 10.0 * len(rows),
                     "installed": True, "looked_in": ["~/.claude"],
                     "error": None}],
        "first_last_seen": {}, "inventory": [], "history_ledger": [],
        "stats_cache": [], "sessions": rows,
    }


def _jsonl(sid, n):
    """One transcript row read_claude will count as exactly n tokens."""
    return json.dumps({
        "type": "assistant",
        "uuid": f"row-{sid}",
        "sessionId": sid,
        "timestamp": "2026-01-01T00:00:00.000Z",
        "message": {"id": f"msg-{sid}", "model": MODEL,
                    "usage": _fields(n)},
    })


def build(dest, fleet=None, version="fixture-1", corpus_versions=None,
          corpus_skip=(), corpus_empty=(), shared_sid=None, commit=True,
          corpus_unread=()):
    """Build <dest>/count and <dest>/record. Returns (count_root, corpus_root).

    fleet            [(folder, label, total)], defaults to FLEET
    version          scanner_version written into every totals/sessions.json
    corpus_versions  {folder: reader_version} for the planted corpus stats.json
                     (None = do not plant one, let corpus_reports write it)
    corpus_skip      folders with NO corpus directory at all  (ABSENT)
    corpus_empty     folders with a corpus directory holding no transcripts
                     (EMPTY — the pair that this repo keeps confusing)
    corpus_unread    folders with a corpus directory and NO .claude/projects at
                     all, so read_machine() returns None and this run computes
                     nothing for them  (UNREAD — a third state, and the one the
                     phantom gap comes out of). Distinct from corpus_empty on
                     purpose: EMPTY is a reading of zero, UNREAD is no reading.
                     Reproduces dell-inspiron, whose leftover stats.json was
                     entered into both totals as `-824,886` against transcripts
                     nobody had counted.
    shared_sid       if set, alpha's and bravo's first session get this same id
    commit           make <dest>/count a real git repository with one commit,
                     so check_consistency's drift checks are live (see _commit)
    """
    fleet = fleet or FLEET
    src = pathlib.Path(__file__).resolve().parent
    dest = pathlib.Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    count = dest / "count"
    record = dest / "record"
    count.mkdir(parents=True)
    record.mkdir(parents=True)

    for f in src.iterdir():
        if f.suffix == ".py" or f.name in ("accounts.json",):
            os.symlink(f.resolve(), count / f.name)
    (count / "machines.json").write_text(json.dumps(
        {"machines": [{"folder": f, "label": l} for f, l, _ in fleet]},
        indent=1), encoding="utf-8")
    if not (count / "accounts.json").exists():
        (count / "accounts.json").write_text(
            json.dumps({"accounts": [ACCOUNT], "profiles": []}), encoding="utf-8")

    for folder, label, total in fleet:
        amounts = _split(total)
        sids = [f"{folder}-s1", f"{folder}-s2"]
        if shared_sid and folder in ("alpha", "bravo"):
            sids[0] = shared_sid
        md = count / folder / paths.MACHINE
        md.mkdir(parents=True)
        (md / TOTALS).write_text(
            json.dumps(_totals_json(label, total, len(sids), version), indent=1),
            encoding="utf-8")
        (md / SESSIONS).write_text(
            json.dumps(_sessions_json(label, sids, amounts, version), indent=1),
            encoding="utf-8")
        # THE SECOND WRITER. analyze_tokens writes by_account.csv beside
        # totals.json in the same pass through a different writer, and
        # check_consistency re-adds the fleet out of the CSVs so the total
        # stands on two artifacts rather than one. A fixture with no CSV does
        # not merely skip that check — it empties both sides of it, which is
        # the "at least one machine was corroborated" hole adv_gate_git_blind
        # exists to hold. Written from the SAME `total` on purpose: the
        # attacks that disagree the two artifacts do it themselves.
        f = _fields(total)
        (md / "by_account.csv").write_text(
            "account,config_dir,sessions,turns,input_tokens,"
            "cache_creation_input_tokens,cache_read_input_tokens,"
            "output_tokens,total\n"
            f"{ACCOUNT},~/.claude,{len(sids)},{len(sids)},"
            f"{f['input_tokens']},{f['cache_creation_input_tokens']},"
            f"{f['cache_read_input_tokens']},{f['output_tokens']},{total}\n",
            encoding="utf-8")

        if folder in corpus_skip:
            continue
        cm = record / folder
        if folder not in corpus_unread:
            proj = cm / ".claude" / "projects" / "p"
            proj.mkdir(parents=True)
            if folder not in corpus_empty:
                for sid, n in zip(sids, amounts):
                    (proj / f"{sid}.jsonl").write_text(_jsonl(sid, n) + "\n",
                                                       encoding="utf-8")
        cmd = cm / paths.MACHINE
        cmd.mkdir(parents=True)
        (cmd / MANIFEST).write_text(json.dumps(
            {"machine": folder, "generated_at": STAMP, "tools": []}, indent=1),
            encoding="utf-8")
        cv = (corpus_versions or {}).get(folder, version)
        if cv is not None:
            held = 0 if folder in corpus_empty else total
            (cmd / STATS).write_text(json.dumps(
                {"machine": folder, "generated_at": STAMP,
                 "reader_version": cv, "tokens": held,
                 "sessions": 0 if held == 0 else len(sids)}, indent=1),
                encoding="utf-8")
    if commit:
        _commit(count)
    return count, record


def _commit(root):
    """One real commit, so the gate's drift checks are LIVE rather than skipped.

    check_consistency.py leans on git for the one distinction the filesystem
    cannot make: a machine folder that was RETIRED against one that was LOST, a
    published document that belongs to another checkout against one that was
    deleted. Outside a git repository every one of those questions returns 128,
    and the gate now says so out loud — `the last commit can be read, so the
    drift checks are live` is fatal, deliberately, because a run in which they
    never ran used to be indistinguishable in the banner from one in which they
    all passed.

    So a fixture that is not a checkout cannot ask this gate anything. Three of
    its checks were failing here for that reason alone and the suite read it as
    a fleet-arithmetic defect. Nothing is stubbed: the same `git` binary, one
    real commit, and GIT_CONFIG_GLOBAL/SYSTEM pointed at /dev/null so this
    machine's git config cannot change the answer.
    """
    env = dict(os.environ,
               GIT_AUTHOR_NAME="fixture", GIT_AUTHOR_EMAIL="f@f",
               GIT_COMMITTER_NAME="fixture", GIT_COMMITTER_EMAIL="f@f",
               GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull)
    for args in (["init", "-q", "-b", "main"], ["add", "-A"],
                 ["commit", "-q", "-m", "fixture"]):
        r = subprocess.run(["git"] + args, cwd=root, env=env,
                           capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(f"git {args[0]} failed: {r.stdout}{r.stderr}")


if __name__ == "__main__":
    import sys
    c, r = build(sys.argv[1] if len(sys.argv) > 1 else "/tmp/fleet-fixture")
    print(f"count  {c}\nrecord {r}\nplanted fleet total {FLEET_TOTAL:,}")
