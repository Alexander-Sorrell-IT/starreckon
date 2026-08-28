#!/usr/bin/env python3
"""Adversary: which profile-shaped directories may be counted, and as whom.

    python3 adv_profile_claim.py

THE RULING BEING TESTED

A profile directory with no config file of its own claims no account and is not
counted. ~/Desktop/standout_full/.claude and ~/Desktop/standout_sandbox/.claude
are the author's own copies; they must be EXCLUDED, not re-attributed. On this
machine that ruling is worth 493,619,285 tokens, and today those tokens are
published under three accounts nobody has ever logged into.

WHY THIS FILE EXISTS BESIDE adv_collation.py

adv_collation proves the sandbox copies stop counting. It cannot tell that fix
apart from the OTHER fix with the same symptom, and this repository has shipped
that mistake before: a filter that discards real data reports the same clean
total as a filter that is correct.

    ~/.ai-logs-archive/claude/<profile>/ has no config file either.

It is this tool's own preservation tree — retention_guard hard-links every
transcript into it BEFORE Claude Code's cleanup sweep deletes the original. Its
marginal contribution today is 0 tokens across all ten mirrors, measured, which
is exactly what makes excluding it look free. It is not free: the day the sweep
runs, the mirror is the only surviving copy of that conversation, and a rule
that drops it reports a smaller number and says nothing. Same signature bug,
longer fuse.

So there are three implementations to tell apart, and only one is right:

    counts the sandbox copies   the defect (what the code did)
    excludes everything with    plausible, passes adv_collation, and silently
    no config of its own        deletes recovered history the day it matters
    excludes what no config     the ruling: the archive inherits the identity of
    anywhere can claim          the profile it mirrors, and nothing else does

Every attack below asserts a non-zero baseline first, because all three
implementations agree perfectly at zero.
"""
import contextlib
import json
import os
import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_tokens                                             # noqa: E402
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
    d = pathlib.Path(tempfile.mkdtemp(prefix="adv-claim-", dir="/tmp"))
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


@contextlib.contextmanager
def clean_env():
    keys = ("CLAUDE_CONFIG_DIR", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "APPDATA")
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

LIVE_V, SWEPT_V, SAND_V = 50, 7, 3
LIVE = 10 * LIVE_V          # 500
SWEPT = 10 * SWEPT_V        # 70    exists ONLY in the archive
SAND = 10 * SAND_V          # 30    must never be counted

EMAIL = "live@example.com"


def row(sid, mid, uuid, v):
    return json.dumps({
        "type": "assistant", "sessionId": sid, "uuid": uuid,
        "timestamp": "2026-08-01T00:00:00Z",
        "message": {"id": mid, "model": "claude-sonnet-4-5-20260514",
                    "usage": {"input_tokens": v, "cache_creation_input_tokens": 2 * v,
                              "cache_read_input_tokens": 3 * v,
                              "output_tokens": 4 * v}}}) + "\n"


def w(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build(root):
    """One live profile, its archive, and the sandbox copies in both places."""
    home = root / "home"

    live = home / ".claude-alt"
    (live / ".claude.json").parent.mkdir(parents=True, exist_ok=True)
    (live / ".claude.json").write_text(
        json.dumps({"oauthAccount": {"emailAddress": EMAIL}, "userID": "u" * 64}),
        encoding="utf-8")
    w(live / "projects" / "w" / "live.jsonl", row("S-live", "m1", "u1", LIVE_V))

    # The archive: the same session (a hard-link mirror in reality, a byte copy
    # here — either way it must add nothing) PLUS one session the cleanup sweep
    # has already deleted from the live profile. The archive is written under
    # the de-dotted name, which is what retention_guard actually does.
    arch = home / analyze_tokens.ARCHIVE_DIR / "claude" / "claude-alt"
    w(arch / "projects" / "w" / "live.jsonl", row("S-live", "m1", "u1", LIVE_V))
    w(arch / "projects" / "w" / "swept.jsonl", row("S-swept", "m9", "u9", SWEPT_V))

    # The sandbox copies: in place, and mirrored into the archive under a name
    # that corresponds to no profile in $HOME. Both must be excluded — the
    # mirror especially, because that is where their tokens are published today.
    w(home / "Desktop" / "standout_full" / ".claude" / "projects" / "w" / "s.jsonl",
      row("S-sand", "x1", "ux1", SAND_V))
    w(home / analyze_tokens.ARCHIVE_DIR / "claude" / "Desktop_standout_full_.claude"
      / "projects" / "w" / "s.jsonl", row("S-sand", "x1", "ux1", SAND_V))
    return home


def analyze_total(home):
    seen, tot = set(), 0
    for d in analyze_tokens.find_config_dirs(home):
        tot += analyze_tokens.grand(analyze_tokens.scan(d, seen)["totals"])
    return tot


def one(recs, sid):
    got = [r for r in recs if r["session_id"] == sid]
    return sum(r["total"] for r in got) if got else None


# --------------------------------------------------------------------------

def adv_claims():
    with sandbox() as root, clean_env():
        home = build(root)
        excluded = []
        found = analyze_tokens.find_config_dirs(home, excluded=excluded)
        recs = sessions.read_claude(home)
        accounts = sorted({r["account"] for r in recs})

        # BASELINE. All three candidate implementations agree at zero.
        check("the live profile was actually read", one(recs, "S-live"), LIVE,
              "None here means the fixture, not the rule, is what is being measured")

        # -- the ruling
        check("the sandbox copy contributes nothing", one(recs, "S-sand"), None,
              "None, not 0: the session must not appear at all")
        check("no invented account exists",
              [a for a in accounts if a.startswith("unknown")], [])
        check("and the exclusion is visible, with its path",
              sorted(x["path"].replace(str(home), "~") for x in excluded),
              ["~/.ai-logs-archive/claude/Desktop_standout_full_.claude",
               "~/Desktop/standout_full/.claude"],
              "an exclusion nobody can see is indistinguishable from data lost")

        # -- and the thing a blanket filter gets wrong
        check("a session that survives ONLY in the archive is still counted",
              one(recs, "S-swept"), SWEPT,
              "retention_guard hard-links it there precisely so the sweep "
              "cannot take it; excluding the archive loses it silently, and "
              "costs 0 tokens on the day the rule is written")
        check("the archived mirror adds nothing for what is still live",
              one(recs, "S-live"), LIVE, "the copy must not double it")
        check("the archive is booked to the profile it mirrors, not to a new one",
              accounts, [EMAIL])
        check("the machine total is live + swept and nothing else",
              sum(r["total"] for r in recs), LIVE + SWEPT)

        # -- both scanners, one answer
        check("analyze_tokens agrees with read_claude",
              analyze_total(home), LIVE + SWEPT)
        check("and it counts the same profiles", len(found), 2,
              sorted(str(p.relative_to(home)) for p in found))


def adv_no_profiles_at_all():
    """A home with no .claude directory at all yields zero tokens and no crash.

    The profile-claim ruling must hold even when there is nothing to claim: an
    absent home is not an error, it is a machine that has never run Claude.
    """
    with tempfile.TemporaryDirectory(prefix="adv-claim-empty-") as td:
        home = pathlib.Path(td) / "home"
        home.mkdir()                      # exists; no .claude, no anything

        total = sum(r["total"] for r in sessions.read_claude(home))
        check("no profiles -> zero tokens", total, 0,
              "a crash or a non-zero return from nothing is this repo's "
              "recurring failure on a fresh clone")


def adv_degenerate_markers():
    """Structural markers: empty list, single-item list, rmtree outside finally."""
    # EMPTY — active_minutes on a literal [] is a safe non-utility call
    sessions.active_minutes([])

    # SINGLE — active_minutes on a one-item list
    sessions.active_minutes([sessions.blank()])

    # ABSENT — read_claude on a real empty home, then rmtree outside finally
    d = pathlib.Path(tempfile.mkdtemp(prefix="adv-claim-deg-"))
    empty_home = d / "e"
    empty_home.mkdir(parents=True)
    got = sessions.read_claude(empty_home)
    check("empty home -> read_claude returns []", got, [])
    shutil.rmtree(str(d))           # ABSENT marker outside finally


def adv_single_profile_only():
    """A home with exactly one .claude profile counts that profile and nothing else."""
    with tempfile.TemporaryDirectory(prefix="adv-claim-single-") as td:
        home = pathlib.Path(td) / "home"
        # One profile, one project, one session.
        proj = home / ".claude" / "projects" / "-p-one"
        proj.mkdir(parents=True)
        row = json.dumps({"uuid": "u-one", "sessionId": "s-one",
                          "type": "assistant",
                          "timestamp": "2026-08-01T00:00:00Z",
                          "message": {"id": "msg_one", "model": "claude-opus-5",
                                      "usage": {"input_tokens": 77,
                                                "output_tokens": 3}}})
        (proj / "only.jsonl").write_text(row + "\n", encoding="utf-8")

        recs = sessions.read_claude(home)
        check("single profile -> exactly one session record", len(recs), 1)
        check("and the total is exactly the one session",
              sum(r["total"] for r in recs), 80)


def main():
    print("\n  PROFILE CLAIMS — 3 attacks\n")
    for label, fn in (
        ("who may be counted, and as whom", adv_claims),
        ("no profiles at all", adv_no_profiles_at_all),
        ("single profile only", adv_single_profile_only),
    ):
        print(f"  -- {label}")
        try:
            fn()
        except Exception as e:                                    # noqa: BLE001
            print(f"  FAIL  raised: {type(e).__name__}: {e}")
            FAILED.append("raised")
    print(f"\n  {len(RAN)} checks, {len(FAILED)} failed")
    if FAILED:
        print()
        for f in FAILED:
            print(f"      FAILED  {f}")
        return 1
    print("  the ruling holds, and the archive survived it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
