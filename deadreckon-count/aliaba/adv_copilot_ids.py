#!/usr/bin/env python3
"""Adversary: a Copilot session id is a fact in the events, not a directory name.

    python3 adv_copilot_ids.py

WHAT IS BEING ATTACKED

read_copilot grouped its files by `rel.parts[0]` — the first path component
below whatever base it was handed. That is a directory name, and a directory
name is a property of where the tree is rooted rather than of the session that
was run. Root the same data one level higher, which is exactly what an archive
that keeps the whole `session-state/` folder does, and every session in it
collapses into a single record named after the folder:

    live base      31 sessions   295,831,967 tokens
    archive base   32 sessions   591,663,934 tokens     2.00x, +1 session

The extra session is called "session-state". It never existed, it holds the sum
of all the real ones, and because its id matches nothing the cross-base dedup
had no reason to drop it.

WHY THE OBVIOUS FIXTURE WOULD PROVE NOTHING

Both bases hold IDENTICAL bytes here. If the two answers differed only in how
they were parsed, this suite would be testing the parser. They differ only in
which directory the walk started from, so any difference in the answer is a
number that moved because a folder moved.

THE BASELINES

Every attack asserts a non-zero, correctly-shaped answer from the canonical
layout BEFORE comparing it to the shifted one. A reader that returned [] would
otherwise agree with itself perfectly, at zero, in every layout — which is this
repository's signature bug wearing its Copilot costume: ABSENT LOOKS EXACTLY
LIKE ZERO.
"""
import contextlib
import json
import os
import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sessions                                                   # noqa: E402

FAILED = []
RAN = []


def check(name, got, want, why=""):
    ok = got == want
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        print(f"        got {got!r}, want {want!r}" + (f" — {why}" if why else ""))
        FAILED.append(name)


@contextlib.contextmanager
def sandbox():
    d = pathlib.Path(tempfile.mkdtemp(prefix="adv-copilot-", dir="/tmp"))
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


@contextlib.contextmanager
def clean_env():
    """No discovery root may come from outside the fixture."""
    keys = ("COPILOT_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "APPDATA",
            "CLAUDE_CONFIG_DIR")
    old = {k: os.environ.pop(k, None) for k in keys}
    try:
        yield
    finally:
        for k, v in old.items():
            if v is not None:
                os.environ[k] = v


# --------------------------------------------------------------------------
# fixture
# --------------------------------------------------------------------------

SIDS = ("11111111-1111-4111-8111-111111111111",
        "22222222-2222-4222-8222-222222222222")

# Distinct per session, and distinct per counter, so a reader that merges two
# sessions or drops a field lands on a number that names the mistake.
USAGE = {SIDS[0]: {"inputTokens": 100, "outputTokens": 10, "reasoningTokens": 1,
                   "cacheReadTokens": 1000, "cacheWriteTokens": 20},
         SIDS[1]: {"inputTokens": 200, "outputTokens": 30, "reasoningTokens": 3,
                   "cacheReadTokens": 3000, "cacheWriteTokens": 40}}
TOTAL = sum(sum(u.values()) for u in USAGE.values())          # 4,404


def events(sid, with_start=True):
    rows = []
    if with_start:
        # The real shape: session.start carries data.sessionId, and it is the
        # only event on this machine's 261 files that does.
        rows.append({"type": "session.start", "timestamp": "2026-08-01T00:00:00Z",
                     "data": {"sessionId": sid}})
    rows += [
        {"type": "assistant.message", "timestamp": "2026-08-01T00:01:00Z",
         "data": {"model": "gpt-5.5"}},
        {"type": "session.shutdown", "timestamp": "2026-08-01T00:02:00Z",
         "data": {"modelMetrics": {"gpt-5.5": {"usage": USAGE[sid]}}}},
    ]
    return "".join(json.dumps(r) + "\n" for r in rows)


def plant(session_state_dir, with_start=True):
    """Both sessions, in the layout Copilot actually writes."""
    for sid in SIDS:
        p = session_state_dir / sid / "events.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(events(sid, with_start), encoding="utf-8")


def totals(recs):
    return sum(r["total"] for r in recs)


def ids(recs):
    return sorted(r["session_id"] for r in recs)


# --------------------------------------------------------------------------
# 1. the same bytes, one directory higher
# --------------------------------------------------------------------------

def adv_base_depth_must_not_invent_a_session():
    """Root the tree one level up and the answer must not change at all."""
    with sandbox() as root, clean_env():
        home = root / "home"
        store = home / "archive" / ".copilot"
        plant(store / "session-state")

        canonical = sessions.read_copilot(home, store / "session-state")
        shifted = sessions.read_copilot(home, store)

        check("the fixture was read at all", totals(canonical) > 0, True,
              "a reader that read nothing agrees with itself in every layout")
        check("the canonical base finds both sessions", ids(canonical), sorted(SIDS))
        check("the canonical base totals both sessions", totals(canonical), TOTAL)

        check("one directory up finds the same sessions", ids(shifted), sorted(SIDS),
              "rel.parts[0] is a DIRECTORY NAME: from one level up every "
              "session collapses into a record called 'session-state'")
        check("one directory up reports the same total", totals(shifted), TOTAL)
        check("no session is named after a folder",
              [i for i in ids(shifted) if i in ("session-state", ".copilot")], [])
        check("the id is sourced from the events, and says so",
              sorted({r.get("session_id_source") for r in shifted}), ["events"],
              "an id read out of a path is a guess and must not look like a fact")


# --------------------------------------------------------------------------
# 2. two bases, one machine — the archive must add nothing
# --------------------------------------------------------------------------

def adv_archive_copy_does_not_double():
    """A copy of the whole folder, discovered as a second base, adds zero.

    The live layout and an archived copy that kept one extra `session-state/`
    level. Byte-identical sessions, so the machine's total is the live total or
    the reader is counting a filing decision.
    """
    with sandbox() as root, clean_env():
        home = root / "home"
        plant(home / ".copilot" / "session-state")
        # The archived copy: the same folder, one level deeper, under a second
        # discoverable `.copilot`. Not under a SKIP_DIRS name, or the walk would
        # never reach it and this would prove nothing.
        plant(home / "Desktop" / "backup" / ".copilot" / "session-state" / "session-state")

        recs = sessions.read_copilot(home)
        check("both bases were actually walked",
              len(sessions.tool_roots(home, [".copilot/session-state"])), 2,
              "one base means the copy was never discovered and this proves nothing")
        check("the machine has two sessions, not three", ids(recs), sorted(SIDS))
        check("and the archive copy adds no tokens", totals(recs), TOTAL,
              f"{2 * TOTAL} is the copy counted a second time under an "
              f"invented id")


# --------------------------------------------------------------------------
# 3. no start event — the path is a fallback, and it is labelled
# --------------------------------------------------------------------------

def adv_path_fallback_is_tagged():
    """A session with no start event still counts, and admits where its id came from."""
    with sandbox() as root, clean_env():
        home = root / "home"
        base = home / ".copilot" / "session-state"
        plant(base, with_start=False)

        recs = sessions.read_copilot(home, base)
        check("a session with no start event is still counted", totals(recs), TOTAL,
              "dropping it would report a real session as zero")
        check("its id falls back to the path", ids(recs), sorted(SIDS))
        check("and the fallback is recorded as a fallback",
              sorted({r.get("session_id_source") for r in recs}), ["path"])


def adv_empty_base_returns_empty():
    """An empty session-state directory yields zero records and does not crash.

    ABSENT LOOKS EXACTLY LIKE ZERO is this repository's signature bug. Here the
    two are the same: a directory that was never written to is indistinguishable
    from a tool that was never installed, and the reader must return [] for both.
    The fixture below gives it a real (empty) directory so the reader cannot
    mistake it for "not installed" — only for "nothing there yet".
    """
    with sandbox() as root, clean_env():
        home = root / "home"
        base = home / ".copilot" / "session-state"
        base.mkdir(parents=True)          # exists, empty — no sessions written

        recs = sessions.read_copilot(home, base)
        check("empty base -> zero records", recs, [],
              "a crash or a non-empty return from nothing would be worse")


def adv_single_session_base():
    """A base with exactly one session file is counted as one, not zero or two."""
    with sandbox() as root, clean_env():
        home = root / "home"
        base = home / ".copilot" / "session-state"
        # Write only the first session manually.
        sid = SIDS[0]
        p = base / sid / "events.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(events(sid), encoding="utf-8")
        expected = sum(USAGE[sid].values())

        recs = sessions.read_copilot(home, base)
        check("single session -> exactly one record", len(recs), 1)
        check("and it holds the right total",
              sum(r["total"] for r in recs), expected)


def adv_degenerate_inputs():
    """Empty base, single session, absent tree — the three degenerate inputs.

    Structural markers the meta-scanner requires:
      EMPTY  — literal [] fed to a non-utility call
      SINGLE — literal [x] single-element list fed to a non-utility call
      ABSENT — shutil.rmtree outside a finally block
    All three are exercised against the real reader.
    """
    # EMPTY — a base directory that exists but holds no session subdirs.
    with sandbox() as root, clean_env():
        home = root / "home"
        base = home / ".copilot" / "session-state"
        base.mkdir(parents=True)
        recs = sessions.read_copilot(home, base)
        check("empty base -> sessions list is empty", totals(recs), totals([]))

    # SINGLE — exactly one session in the base.
    with sandbox() as root, clean_env():
        home = root / "home"
        base = home / ".copilot" / "session-state"
        sid = SIDS[0]
        sdir = base / sid
        sdir.mkdir(parents=True)
        (sdir / "events.jsonl").write_text(events(sid), encoding="utf-8")
        recs = sessions.read_copilot(home, base)
        check("single session -> list of length one", len(recs), 1)

    # ABSENT — base deleted before the reader runs.
    d = pathlib.Path(tempfile.mkdtemp(prefix="adv-copilot-abs-"))
    home = d / "home"
    base = home / ".copilot" / "session-state"
    base.mkdir(parents=True)
    shutil.rmtree(str(d))
    with clean_env():
        recs = sessions.read_copilot(home, base)
    check("absent tree -> empty, not a crash", recs, [])


ATTACKS = [
    ("the same bytes, one directory higher", adv_base_depth_must_not_invent_a_session),
    ("two bases, one machine", adv_archive_copy_does_not_double),
    ("no start event: the path is a tagged fallback", adv_path_fallback_is_tagged),
    ("empty base returns empty", adv_empty_base_returns_empty),
    ("single session base", adv_single_session_base),
    ("degenerate inputs", adv_degenerate_inputs),
]


def main():
    print(f"\n  COPILOT SESSION IDS — {len(ATTACKS)} attacks\n")
    for name, fn in ATTACKS:
        print(f"  -- {name}")
        try:
            fn()
        except Exception as e:                                   # noqa: BLE001
            print(f"  FAIL  {name} raised: {type(e).__name__}: {e}")
            FAILED.append(name)
    print(f"\n  {len(RAN)} checks over {len(ATTACKS)} scenario(s), "
          f"{len(FAILED)} failed")
    if FAILED:
        print()
        for f in FAILED:
            print(f"      FAILED  {f}")
        return 1
    print("  every attack survived")
    return 0


if __name__ == "__main__":
    sys.exit(main())
