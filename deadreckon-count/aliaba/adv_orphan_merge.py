#!/usr/bin/env python3
"""Two snapshots of one session, and which of them survives.

    python3 adv_orphan_merge.py

WHY THIS FILE EXISTS

`sessions.merge_session` merges two observations of one session by PER-FIELD
maximum, and its own docstring names the rule it is not:

    snapshot A {output:100, cache_read:0} against B {output:0, cache_read:150}
    makes B win wholesale under max-of-the-sum and the 100 is simply gone.

`sessions.read_claude_orphans` was that third rule, in code, shipping. It
scored each snapshot by `sum(tk.values())` and kept the winner's whole record,
so the pair above lost a field. Two things made it invisible:

  NOTHING DROVE IT.  Every assertion in this repository about the per-field
        maximum went through `multi_base` -> `merge_session`, and the one suite
        that does that (adv_collation) feeds nested pairs where a truncated
        copy is a SUBSET of the full one. Max-of-the-sum and per-field maximum
        return the same answer on a subset — the pair has to lead on DIFFERENT
        fields before the two rules can be told apart, and no fixture did.
  NOTHING CAN NOTICE.  These are sessions whose transcript Claude Code deleted.
        There is no second source to reconcile against; a field dropped here is
        dropped silently and forever.

So this file drives all three paths with the ONE pair that separates the rules,
and asserts the answer, never merely that nothing failed:

    1. merge_session directly            — the rule itself
    2. read_claude_orphans on real files — the copy of it that had drifted
    3. the account fallback, all three call sites, on ONE config document

Every check names a number computed from the fixture, so a reader that returns
nothing FAILS instead of agreeing with itself. Nothing here writes outside a
temporary directory and nothing here runs any part of the pipeline.
"""
import json
import os
import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import analyze_tokens as AT                                       # noqa: E402
import sessions as SS                                             # noqa: E402

RAN, FAILED = [], []

# EVERY check in this file, counted. adv_documents.py died at a KeyError after
# its real failures and 11 later checks never ran — a suite that exits early
# has not passed what it never reached, and a green over a short run is the
# same lie as a green over a broken assert. main() compares this with what
# actually ran and fails on a mismatch in EITHER direction.
EXPECTED_CHECKS = 37


def check(name, got, want, why=""):
    RAN.append(name)
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        print(f"        got {got!r}, want {want!r}" + (f"\n        {why}" if why else ""))
        FAILED.append(name)


def tk(**kw):
    """A token dict: every field named, so a zero is stated rather than absent."""
    t = dict.fromkeys(SS.FIELDS, 0)
    for k, v in kw.items():
        if k not in t:
            raise KeyError(f"{k} is not one of {SS.FIELDS}")
        t[k] = v
    return t


# ---------------------------------------------------------------------------
# THE PAIR. Two observations of one session that lead on DIFFERENT fields.
#
# Under a per-FIELD maximum the session is 200 output + 150 cache_read = 350.
# Under max-of-the-SUM, A (200) beats B (150), B is discarded whole, and the
# session reads 200 — short by 150 cache_read tokens, 42.9% of it.
#
# The two rules AGREE on every pair where one side is a subset of the other,
# which is every pair this repository had a fixture for. They differ here and
# only here, so this is the pair that has to exist.
A = tk(output_tokens=200)
B = tk(cache_read_input_tokens=150)
PER_FIELD = 350                     # 200 + 150
MAX_OF_SUM = 200                    # A wins wholesale; B's 150 is gone
LOSS = PER_FIELD - MAX_OF_SUM       # 150 cache_read tokens

# The literal pair from merge_session's docstring, which separates the rules the
# other way round: B's sum is the larger, so max-of-the-sum discards A's output.
# Both orders are asserted because a rule that is right in one direction and
# wrong in the other is decided by which file the glob reached first.
C = tk(output_tokens=100)
D = tk(cache_read_input_tokens=150)
CD_PER_FIELD = 250
CD_MAX_OF_SUM = 150


def session(sid, tokens, turns=1):
    return {"cli": "claude", "session_id": sid, "account": "a@b.c",
            "project": "/p", "start": "2026-01-01T00:00:00+00:00",
            "end": "2026-01-01T01:00:00+00:00", "turns": turns,
            "tokens": dict(tokens), "model": "m", "provider": "anthropic",
            "billed": True}


# ---------------------------------------------------------------------------
# 1. merge_session — the rule itself
# ---------------------------------------------------------------------------

def adv_merge_session_is_per_field_not_max_of_sum():
    """Merge the pair. The answer must be 350, and the same both ways round.

    RED against max-of-the-sum by construction: that rule returns 200 here and
    150 for the docstring's own pair, and both are asserted against a constant
    this file computes from the fixture rather than from the code under test.
    """
    got = SS.merge_session(session("S", A), session("S", B))
    check("A+B: the merged session is the per-field maximum",
          got["tokens"], tk(output_tokens=200, cache_read_input_tokens=150),
          "max-of-the-sum hands the record to whichever snapshot has the larger "
          "total and discards the other field entirely")
    check("A+B: and its total is the union, not the winner", got["total"],
          PER_FIELD, f"max-of-the-sum reports {MAX_OF_SUM}, short by {LOSS}")
    check("A+B: the discarded field is exactly the 150 cache_read tokens",
          got["tokens"]["cache_read_input_tokens"], 150)
    # What winner-takes-all costs, measured against the MERGED total the code
    # actually returned — not against this file's own constants, which would
    # compare two literals and could not fail whatever the code did.
    winner = max(sum(A.values()), sum(B.values()))        # max-of-the-sum's answer
    check("A+B: winner-takes-all is short by 42.9% of the session",
          round(100 * (got["total"] - winner) / (got["total"] or 1), 1), 42.9,
          "0.0 means the merge returned the winner's record and nothing else")

    # The same pair, swapped. Max-of-the-sum picks A either way; a per-field
    # maximum cannot depend on argument order at all.
    flipped = SS.merge_session(session("S", B), session("S", A))
    want = tk(output_tokens=200, cache_read_input_tokens=150)
    check("B+A: swapping the arguments does not move the answer",
          (flipped["tokens"], got["tokens"]), (want, want),
          "a total that moves with directory order is a property of the "
          "filesystem, not of the work that was done")
    check("B+A: and it is still the union", flipped["total"], PER_FIELD)

    # merge_session's own docstring pair, where the LOSER of the sum holds the
    # field that would be dropped.
    doc = SS.merge_session(session("T", C), session("T", D))
    check("the docstring's own pair keeps both fields", doc["tokens"],
          tk(output_tokens=100, cache_read_input_tokens=150),
          "{output:100} vs {cache_read:150} — B wins wholesale under "
          "max-of-the-sum and the 100 is simply gone")
    check("the docstring's own pair totals 250", doc["total"], CD_PER_FIELD,
          f"max-of-the-sum reports {CD_MAX_OF_SUM}")

    # AND THE RULE IT IS ALSO NOT. A per-field maximum must not become a sum:
    # the same snapshot seen twice is one session, not two.
    twice = SS.merge_session(session("U", A), session("U", A))
    check("one snapshot seen twice is not doubled", twice["total"], 200,
          "summing snapshots is the trap that read 37,074,183,708")

    # A subset pair — where the two rules AGREE. Asserted so this file states
    # what the existing fixtures could and could not see, rather than implying
    # they were wrong.
    sub = SS.merge_session(session("V", tk(output_tokens=200,
                                           cache_read_input_tokens=150)),
                           session("V", tk(output_tokens=200)))
    check("a truncated copy of one snapshot changes nothing", sub["total"],
          PER_FIELD,
          "both rules agree here, which is why five nested pairs could not "
          "tell them apart")


# ---------------------------------------------------------------------------
# 2. read_claude_orphans — the copy of the rule that had drifted
# ---------------------------------------------------------------------------

def _proj(sid, tokens):
    return {"lastSessionId": sid,
            "lastTotalInputTokens": tokens["input_tokens"],
            "lastTotalOutputTokens": tokens["output_tokens"],
            "lastTotalCacheReadInputTokens": tokens["cache_read_input_tokens"],
            "lastTotalCacheCreationInputTokens":
                tokens["cache_creation_input_tokens"],
            # Restates lastTotal* field for field. Reading it too is exactly 2x.
            "lastModelUsage": {"m": {"inputTokens": tokens["input_tokens"]}}}


def _snapshots(home, docs, email="a@b.c"):
    """A home holding N observations of the same projects.

    docs[0] is ~/.claude.json — the live state — and the rest are the backup
    snapshots beside it, which is the layout a real profile has. The list is
    explicit so the degenerate end of it is expressible: ONE observation, with
    no partner to merge against, is a case the reader has to answer too.
    """
    (home / ".claude.json").write_text(json.dumps(
        {"oauthAccount": {"emailAddress": email}, "projects": docs[0]}),
        encoding="utf-8")
    d = home / ".claude" / "backups"
    d.mkdir(parents=True, exist_ok=True)
    for i, doc in enumerate(docs[1:], start=1):
        (d / f".claude.json.backup.{i}").write_text(json.dumps(
            {"oauthAccount": {"emailAddress": email}, "projects": doc}),
            encoding="utf-8")


def _orphans(home):
    SS._ORPHAN_EXCLUDE.clear()
    return SS.read_claude_orphans(home)


def adv_orphan_snapshots_merge_per_field():
    """The same pair, through the reader, from files on disk.

    read_claude_orphans scored `sum(tk.values())` and kept the winner's whole
    record. Nothing else in the repository drives this reader with a pair that
    can tell that apart from merge_session's rule, and there is no transcript
    left for anything downstream to reconcile it against.
    """
    with tempfile.TemporaryDirectory(prefix="orphan-") as td:
        home = pathlib.Path(td)
        _snapshots(home, [{"/p": _proj("gone", A)}, {"/p": _proj("gone", B)}])
        got = _orphans(home)

        check("the orphan session is recovered at all", len(got), 1,
              "a reader that returns nothing agrees with every total")
        if len(got) != 1:
            return
        check("the orphan is the session with no transcript",
              got[0]["session_id"], "gone")
        check("two snapshots leading on different fields merge per FIELD",
              got[0]["tokens"], tk(output_tokens=200,
                                   cache_read_input_tokens=150),
              "winner-takes-all on the sum keeps A and drops B's 150")
        check("and the recovered total is the union", got[0]["total"],
              PER_FIELD,
              f"max-of-the-sum reports {MAX_OF_SUM} — {LOSS} tokens, "
              f"{round(100 * LOSS / PER_FIELD, 1)}% of the session, gone with "
              f"no second source that could ever notice")

    # The SAME two snapshots with the files swapped. Under winner-takes-all the
    # answer is 200 both ways; under a per-field maximum it is 350 both ways.
    # What must never happen is 200 one way and 350 the other, which is the
    # shape that made a reader's total depend on which directory it walked.
    with tempfile.TemporaryDirectory(prefix="orphan-flip-") as td:
        home = pathlib.Path(td)
        _snapshots(home, [{"/p": _proj("gone", B)}, {"/p": _proj("gone", A)}])
        flip = _orphans(home)
        check("swapping which file holds which snapshot recovers 1 session",
              len(flip), 1)
        if len(flip) != 1:
            return
        check("and the same 350 tokens", flip[0]["total"], PER_FIELD,
              "identical bytes, different files")


def adv_orphans_still_never_sum_snapshots():
    """The property the old rule DID have, kept.

    A per-field maximum that quietly became `+=` would pass every check above
    and restore the 37,074,183,708 restatement trap, so the guard against the
    fix is asserted next to the guard against the defect.
    """
    with tempfile.TemporaryDirectory(prefix="orphan-repeat-") as td:
        home = pathlib.Path(td)
        big = tk(input_tokens=1000, cache_read_input_tokens=4000)
        # Six restatements of ONE session, as a real backup directory holds.
        _snapshots(home, [{"/p": _proj("gone", big)}] * 6)
        got = _orphans(home)
        check("six restatements of one session are one session", len(got), 1)
        if len(got) != 1:
            return
        check("at its maximum, not its sum", got[0]["total"], 5000,
              "6x here and 23x on a machine with more snapshots")
        check("lastModelUsage is still not added on top of lastTotal",
              got[0]["tokens"]["input_tokens"], 1000,
              "it restates the same figure — reading both is exactly 2x")

    # ONE observation — the degenerate end of the same fixture. A session with
    # no partner to merge against must come back at exactly its own value: the
    # merge may neither need a second snapshot nor halve the only one there is.
    with tempfile.TemporaryDirectory(prefix="orphan-one-") as td:
        home = pathlib.Path(td)
        _snapshots(home, [{"/p": _proj("solo", big)}])
        check("a session seen in exactly one snapshot keeps its full value",
              [(g["session_id"], g["total"]) for g in _orphans(home)],
              [("solo", 5000)])

    with tempfile.TemporaryDirectory(prefix="orphan-live-") as td:
        home = pathlib.Path(td)
        _snapshots(home, [{"/p": _proj("gone", A), "/q": _proj("alive", B)},
                          {"/p": _proj("gone", B)}])
        SS._ORPHAN_EXCLUDE.clear()
        SS._ORPHAN_EXCLUDE.add("alive")           # read_claude emitted it
        got = SS.read_claude_orphans(home)
        check("a session whose transcript survives is not re-counted",
              sorted(g["session_id"] for g in got), ["gone"],
              "counting it here as well would double it")
        check("and the exclusion does not disturb the merge",
              sum(g["total"] for g in got), PER_FIELD)


# ---------------------------------------------------------------------------
# 3. the account fallback — copy #3, and whether the three still agree
# ---------------------------------------------------------------------------

UID = "9f3c1a77b2e4d5608899"
UID_ACCOUNT = "user:" + UID[:12]          # computed here, not read from the code
EMAIL = "someone@example.com"


def _three_answers(home, profile):
    """The account, from all three code paths, for ONE config document.

        1. analyze_tokens.account_for   the rule
        2. sessions._claude_account     read_claude's route to it
        3. sessions.read_claude_orphans copy #3, the one that drifted

    Copy #3 is reached only by producing an orphan record, which is why nothing
    reached it before: every existing assertion on 'account' goes through
    read_claude.
    """
    got = _orphans(home)
    accounts = sorted({g["account"] for g in got})
    return (AT.account_for(home / profile, home),
            SS._claude_account(home / profile, home),
            accounts[0] if len(accounts) == 1 else accounts)


def _profile(home, name, doc, sid):
    """A profile directory with its own config and one orphaned project."""
    p = home / name
    (p / "projects").mkdir(parents=True, exist_ok=True)
    doc = dict(doc)
    doc["projects"] = {"/q": _proj(sid, tk(input_tokens=700))}
    (p / ".claude.json").write_text(json.dumps(doc), encoding="utf-8")
    return p


def adv_the_account_fallback_has_three_copies_and_one_answer():
    """Same config document, three call sites, one answer — at every tier.

    Copy #3 had lost the userID tier entirely, so a profile with no email was
    booked to a DIRECTORY NAME while the other two called it `user:<id>`. The
    tier is back; this is the assertion that stops it drifting again, and it is
    asserted at all three tiers because a fix to one tier is not a fix to the
    rule.
    """
    # -- tier 1: email
    with tempfile.TemporaryDirectory(prefix="acct-mail-") as td:
        home = pathlib.Path(td)
        _profile(home, ".claude-mail", {"oauthAccount": {"emailAddress": EMAIL}},
                 "orphan-mail")
        a, b, c = _three_answers(home, ".claude-mail")
        check("tier 1 — read_claude_orphans reads the email", c, EMAIL,
              "the guard that drives copy #3 directly; every other assertion "
              "on 'account' goes through read_claude and never reaches here")
        check("tier 1 — and all three call sites agree", [a, b, c],
              [EMAIL, EMAIL, EMAIL])

    # -- tier 2: userID, the tier copy #3 did not have
    with tempfile.TemporaryDirectory(prefix="acct-uid-") as td:
        home = pathlib.Path(td)
        _profile(home, ".claude-nomail", {"userID": UID}, "orphan-uid")
        a, b, c = _three_answers(home, ".claude-nomail")
        check("tier 2 — a profile with no email is named by its userID", c,
              UID_ACCOUNT,
              "copy #3 answered `unknown (.claude-nomail)`: a directory name "
              "differs between machines, so one profile is reported as two")
        check("tier 2 — and all three call sites agree",
              [a, b, c], [UID_ACCOUNT] * 3,
              "three copies of a rule is three rules")

    # The reason tier 2 exists at all: the SAME nameless profile sits under a
    # different directory name on another machine. Keying on the name reports
    # one profile as two accounts, which is precisely what copy #3 did.
    with tempfile.TemporaryDirectory(prefix="acct-uid-renamed-") as td:
        home = pathlib.Path(td)
        _profile(home, ".claude-elsewhere", {"userID": UID}, "orphan-uid")
        renamed = sorted({g["account"] for g in _orphans(home)})
        check("tier 2 — a different directory, the same userID, one account",
              renamed, [UID_ACCOUNT],
              "`unknown (.claude-nomail)` and `unknown (.claude-elsewhere)` "
              "are two accounts for one profile, and no rollup can rejoin them")

    # -- tier 3: the last resort, where copy #3 named the wrong directory
    with tempfile.TemporaryDirectory(prefix="acct-fall-") as td:
        home = pathlib.Path(td)
        # THE DEFAULT PROFILE. Its state is ~/.claude.json, beside ~/.claude
        # rather than inside it, so `p.parent` is the HOME DIRECTORY and the
        # fallback read `unknown (<login name>)` — the drift the userID tier
        # covered up for every config that has a userID, which is most of them.
        (home / ".claude" / "projects").mkdir(parents=True)
        (home / ".claude.json").write_text(json.dumps(
            {"projects": {"/q": _proj("orphan-fallback", tk(input_tokens=700))}}),
            encoding="utf-8")
        a, b, c = _three_answers(home, ".claude")
        check("tier 3 — the default profile is named `.claude`, not $HOME", c,
              "unknown (.claude)",
              f"the home directory here is {home.name!r}; naming an account "
              f"after the login is the defect account_from was written to end")
        check("tier 3 — and all three call sites agree",
              [a, b, c], ["unknown (.claude)"] * 3)
        check("tier 3 — the answer does not name the home directory",
              home.name in str(c), False)

    # -- and two nameless profiles must not collapse into one account
    with tempfile.TemporaryDirectory(prefix="acct-collapse-") as td:
        home = pathlib.Path(td)
        for name, sid in ((".claude-x", "orphan-x"), (".claude-y", "orphan-y")):
            p = home / name
            (p / "backups").mkdir(parents=True)
            (p / "projects").mkdir()
            (p / "backups" / ".claude.json.backup.1").write_text(json.dumps(
                {"projects": {"/q": _proj(sid, tk(input_tokens=700))}}),
                encoding="utf-8")
        got = _orphans(home)
        check("both nameless profiles produce an orphan", len(got), 2,
              "with none of them recovered the collapse below is unmeasurable")
        check("and they are two accounts, not one",
              sorted({g["account"] for g in got}),
              ["unknown (.claude-x)", "unknown (.claude-y)"],
              "`p.parent.name` is `backups` for both, and every profile has "
              "one — so both collapse into `unknown (backups)` and unrelated "
              "usage is summed into an account nobody has logged into")


# ---------------------------------------------------------------------------
# 4. nothing, and the several different things it can mean
# ---------------------------------------------------------------------------

def adv_nothing_is_never_a_session():
    """A store that is absent, one that is empty, and a counter sitting at 0.

    All three answer `[]` here, and that is correct — this reader has no
    presence to report. So the direction worth asserting is the other one:
    none of them may INVENT a session. A phantom zero-token record adds nothing
    to any token total, which is exactly why it survives: it moves the session
    count in every rollup and there is no number anywhere that contradicts it.
    """
    with tempfile.TemporaryDirectory(prefix="orphan-nothing-") as td:
        home = pathlib.Path(td)
        check("a home with no config at all yields no orphans",
              _orphans(home), [])

        cfg = home / ".claude.json"
        cfg.write_text(json.dumps({"oauthAccount": {"emailAddress": EMAIL},
                                   "projects": {}}), encoding="utf-8")
        check("a config whose projects map is empty yields no orphans",
              _orphans(home), [], "the file is there and holds nothing")

        cfg.write_text(json.dumps(
            {"oauthAccount": {"emailAddress": EMAIL},
             "projects": {"/p": _proj("all-zero", tk())}}), encoding="utf-8")
        check("a project whose four counters are all 0 is not a session",
              _orphans(home), [],
              "it would add 0 tokens and one session to every rollup, and no "
              "token total anywhere would disagree with it")

        # A zeroed snapshot of a REAL session. It must not win, and it must not
        # blank the snapshot that has the numbers.
        cfg.write_text(json.dumps(
            {"oauthAccount": {"emailAddress": EMAIL},
             "projects": {"/p": _proj("gone", A)}}), encoding="utf-8")
        b = home / ".claude" / "backups"
        b.mkdir(parents=True, exist_ok=True)
        (b / ".claude.json.backup.1").write_text(json.dumps(
            {"oauthAccount": {"emailAddress": EMAIL},
             "projects": {"/p": _proj("gone", tk())}}), encoding="utf-8")
        check("a zeroed snapshot does not erase the one with the numbers",
              [(g["session_id"], g["total"]) for g in _orphans(home)],
              [("gone", 200)])

        # DELETED, not merely never present. The 350 above was real; nothing
        # may still be answering with it.
        os.remove(cfg)
        shutil.rmtree(home / ".claude")
        check("with every config deleted, no orphan survives",
              _orphans(home), [],
              "a reader holding state across calls would still answer 200")


# ---------------------------------------------------------------------------

ATTACKS = [
    ("merge_session is a per-field maximum",
     adv_merge_session_is_per_field_not_max_of_sum),
    ("read_claude_orphans applies the same rule",
     adv_orphan_snapshots_merge_per_field),
    ("and still never sums two snapshots",
     adv_orphans_still_never_sum_snapshots),
    ("the account fallback has three copies and one answer",
     adv_the_account_fallback_has_three_copies_and_one_answer),
    ("nothing is never a session", adv_nothing_is_never_a_session),
]


def main():
    print(f"\n  ORPHAN MERGE — {len(ATTACKS)} attacks, "
          f"{EXPECTED_CHECKS} checks\n")
    for name, fn in ATTACKS:
        print(f"  -- {name}")
        try:
            fn()
        except Exception as e:                                    # noqa: BLE001
            print(f"  FAIL  {name} raised: {type(e).__name__}: {e}")
            FAILED.append(f"{name} raised")

    # THE COUNT, both directions. A suite that dies partway through has not
    # passed the checks it never reached, and one that quietly stops running a
    # group still prints every PASS it did emit. Neither is a green here.
    print(f"\n  {len(RAN)} checks ran, {len(FAILED)} failed")
    if len(RAN) != EXPECTED_CHECKS:
        print(f"  FAIL  {len(RAN)} checks ran, {EXPECTED_CHECKS} expected — "
              f"a suite that exits early has not passed what it did not reach")
        FAILED.append("check count")
    if FAILED:
        print()
        for f in FAILED:
            print(f"      FAILED  {f}")
        return 1
    print("  two snapshots of one session merge field by field, in the rule and\n"
          "  in both copies of it, and one config document has one account name")
    return 0


if __name__ == "__main__":
    sys.exit(main())
