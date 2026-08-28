#!/usr/bin/env python3
"""Adversaries for duplicate-free collation. Four states that exist in the world.

    python3 adv_collation.py

WHY A SEPARATE SUITE

Every other suite here asks whether a reader parses its format. This one asks
the question that sits ABOVE the readers and below the totals: when the same
conversation is reachable by more than one path, how many times does it land in
the number?

That question has exactly two wrong answers and they fail in opposite
directions. Counting a copy twice inflates. Dropping an APPEND as if it were a
copy deflates, and deflation is the quiet one — nothing is duplicated, every
consistency check still balances, and the parts still sum to the whole they were
told to sum to.

THE SIGNATURE BUG THIS FILE IS AIMED AT

ABSENT LOOKS EXACTLY LIKE ZERO. A detector nobody wrote reports no duplicates.
A profile that is silently dropped reports no tokens. A counter that does not
exist reads 0 through `dict.get(k, 0)` and every total still adds up. So the
checks below never accept a bare total: they ask each detector to name itself,
and `_counter()` returns None — not 0 — for a counter that is not there, so a
missing detector fails loudly instead of agreeing.

WHAT IS DELIBERATELY NOT TESTED HERE

Whether the readers parse their formats. test_readers.py owns that, with 235
checks. Every fixture below is the minimum shape that reader accepts, and each
attack asserts a NON-ZERO baseline first so that a fixture the reader could not
read fails as a broken fixture rather than passing as "both answers agree at 0".

THE HOUSE RULE

These are written to FAIL against the current code. A check here that passes is
either a property the code already holds — said so out loud — or a worthless
test, and the two are told apart by the baseline assertions, not by hope.
"""
import contextlib
import itertools
import json
import os
import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import analyze_tokens                                            # noqa: E402
import export_corpus                                             # noqa: E402
import sessions                                                  # noqa: E402

FAILED = []
SKIPPED = []
RAN = []


def check(name, got, want, why=""):
    ok = got == want
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        print(f"        got {got!r}, want {want!r}" + (f" — {why}" if why else ""))
        FAILED.append(name)


def skip(name, why):
    """An attack that could not run. Recorded as not-run, never as survived."""
    print(f"  SKIP  {name} — {why}")
    SKIPPED.append(name)


@contextlib.contextmanager
def sandbox():
    """A scratch tree under /tmp, removed afterwards whatever happens."""
    d = pathlib.Path(tempfile.mkdtemp(prefix="adv-collation-", dir="/tmp"))
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


@contextlib.contextmanager
def clean_env():
    """Unset every variable that can add a discovery root from OUTSIDE the fixture.

    `sessions.tool_roots` reads XDG_CONFIG_HOME and XDG_DATA_HOME with no test
    that the home being scanned is this machine's home, so a developer with
    those set would be scanning two trees at once and calling the result the
    fixture's answer. The relocation vars are guarded by stores._env_applies
    and are cleared anyway, because a guard that holds today is not a guard.
    """
    keys = ("CLAUDE_CONFIG_DIR", "CODEX_HOME", "COPILOT_HOME", "GEMINI_CLI_HOME",
            "XDG_CONFIG_HOME", "XDG_DATA_HOME", "APPDATA")
    old = {k: os.environ.pop(k, None) for k in keys}
    try:
        yield
    finally:
        for k, v in old.items():
            if v is not None:
                os.environ[k] = v


# ---------------------------------------------------------------------------
# fixture vocabulary
# ---------------------------------------------------------------------------

def u(v):
    """A usage block worth exactly 10*v tokens, all four counters distinct.

    Distinct multiples, so a reader that drops one field or adds a subset twice
    lands on a number that cannot be mistaken for the right one.
    """
    return {"input_tokens": v, "cache_creation_input_tokens": 2 * v,
            "cache_read_input_tokens": 3 * v, "output_tokens": 4 * v}


def ts(i):
    return f"2026-08-01T00:{i:02d}:00Z"


def crow(sid, mid, uuid, i, v, model="claude-sonnet-4-5-20260514"):
    """One Claude Code assistant row.

    `mid=None` writes a row with usage and NO message.id — the shape the
    fallback at sessions.py:588-594 exists for. `uuid=None` writes one with no
    row uuid either, which is the state that fallback's `and uuid` clause is
    the code's own admission is reachable.
    """
    msg = {"model": model, "usage": u(v)}
    if mid is not None:
        msg["id"] = mid
    o = {"type": "assistant", "sessionId": sid, "timestamp": ts(i), "message": msg}
    if uuid is not None:
        o["uuid"] = uuid
    return o


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return path


def claude_profile(home, name, email=None):
    """A Claude Code profile: projects/ with somewhere to put transcripts.

    `email=None` means NO config file of its own, which is the whole subject of
    the fourth attack.
    """
    p = home / name
    (p / "projects" / "workspace").mkdir(parents=True, exist_ok=True)
    if email is not None:
        (p / ".claude.json").write_text(
            json.dumps({"oauthAccount": {"emailAddress": email},
                        "userID": "u" * 64}), encoding="utf-8")
    return p


def claude_records(home):
    return sessions.read_claude(home)


def claude_total(home):
    return sum(r["total"] for r in sessions.read_claude(home))


def analyze_total(home):
    """analyze_tokens' answer for a whole machine, assembled the way main() does.

    One `seen` set across every config dir — that shared set is what makes wide
    discovery safe, and it is also what makes the answer order-dependent, which
    is the first attack's subject.
    """
    seen, tot = set(), 0
    for d in analyze_tokens.find_config_dirs(home):
        tot += analyze_tokens.grand(analyze_tokens.scan(d, seen)["totals"])
    return tot


def one(records, sid):
    """The records for one session id. A LIST, so 'how many' stays askable."""
    return [r for r in records if r["session_id"] == sid]


def sole_total(records, sid):
    """Total for a session id, or None if it produced no record at all.

    None rather than 0. A session the reader never emitted and a session that
    genuinely cost nothing are two different facts and this suite refuses to
    print the same number for both.
    """
    got = one(records, sid)
    return sum(r["total"] for r in got) if got else None


# ---------------------------------------------------------------------------
# 1. an append is not a duplicate
# ---------------------------------------------------------------------------

SID = "S-append"
NOID = "S-noid"
BARE = "S-bare"

# B is A grown and continued: the same three messages with usage that RISES
# (streaming rewrites bank partial numbers first), plus two genuinely new ones.
B_TOTAL = 10 * (100 + 200 + 300 + 400 + 500)          # 15,000
B_TURNS = 5

# Every way of getting this wrong lands on a different number, so the failure
# names itself instead of just being "not 15000".
WRONG = {
    "first-wins on A":        10 * (1 + 2 + 3) + 10 * (400 + 500),      # 9,060
    "unlucky order, C first": 10 * 1 + 10 * (200 + 300 + 400 + 500),    # 14,010
    "hash-only dedup, A+B+C": 10 * (1 + 2 + 3) + B_TOTAL + 10 * 1,      # 15,070
    "A+B":                    10 * (1 + 2 + 3) + B_TOTAL,               # 15,060
}

# Two rows, deliberately worth DIFFERENT amounts. Two turns that bill the same
# are indistinguishable from one turn written twice, so a fixture built from
# equal rows cannot tell a dedup that works from a dedup that collapses real
# turns — and the second one also reports a tidy, wrong, smaller number.
IDLESS_TOTAL = 10 * 7 + 10 * 9     # 160, for one copy of the file


def _rows_A():
    return [crow(SID, "m1", "uA1", 0, 1),
            crow(SID, "m2", "uA2", 1, 2),
            crow(SID, "m3", "uA3", 2, 3)]


def _rows_B():
    return [crow(SID, "m1", "uB1", 0, 100),
            crow(SID, "m2", "uB2", 1, 200),
            crow(SID, "m3", "uB3", 2, 300),
            crow(SID, "m4", "uB4", 3, 400),
            crow(SID, "m5", "uB5", 4, 500)]


def _rows_C():
    return _rows_A()[:1]           # A, truncated. Literally A's first line.


def _rows_noid():
    return [crow(NOID, None, "uN1", 0, 7), crow(NOID, None, "uN2", 1, 9)]


def _rows_bare():
    return [crow(BARE, None, None, 0, 7), crow(BARE, None, None, 1, 9)]


def _build_append(root, order):
    """One home where the three copies are discovered in `order`.

    Discovery order is not simulated and nothing is monkey-patched: the three
    profiles are named so that find_config_dirs' own `sorted()` walks them in
    the order under test, and the contents are assigned accordingly. Six homes,
    six real orders, the real reader every time.
    """
    home = root / ("perm-" + "".join(order))
    rows = {"A": _rows_A(), "B": _rows_B(), "C": _rows_C()}
    names = [".claude-p1", ".claude-p2", ".claude-p3"]
    for name, tag in zip(names, order):
        p = claude_profile(home, name, email="one@example.com")
        write_jsonl(p / "projects" / "workspace" / f"{SID}-{tag}.jsonl", rows[tag])
    # THE FOURTH FILE, and a byte-identical copy of it in another profile —
    # a copied profile is the state find_config_dirs was widened to reach.
    for name in (names[0], names[2]):
        d = home / name / "projects" / "workspace"
        write_jsonl(d / "noid.jsonl", _rows_noid())
        write_jsonl(d / "bare.jsonl", _rows_bare())
    return home


def adv_append_is_not_a_duplicate():
    """Three files, one session: a copy, an APPEND, and a truncation.

    A resumed session rewrites its earlier turns into the new file with usage
    that has RISEN (the first write of a streaming message carries partial
    numbers) and adds turns that exist nowhere else. A copied profile then holds
    the older, shorter version of the same session id. Both states are on the
    real machine right now; the only variable is which one the walk reaches
    first.

    The answer must be B's, in all six orders. Anything that dedupes by session
    id and stops there returns whichever it saw first.
    """
    with sandbox() as root, clean_env():
        got_c, got_t, got_n, got_a, got_id, got_bare = [], [], [], [], [], []
        for order in itertools.permutations("ABC"):
            home = _build_append(root, order)
            recs = claude_records(home)
            got_c.append(sole_total(recs, SID))
            got_t.append(sum(r["turns"] for r in one(recs, SID)))
            got_n.append(len(one(recs, SID)))
            got_id.append(sole_total(recs, NOID))
            got_bare.append(sole_total(recs, BARE))
            got_a.append(analyze_total(home))

        # BASELINE FIRST. A fixture the reader could not read gives six equal
        # Nones, and "all six agree" would pass on it.
        check("the fixture was actually read (six non-empty answers)",
              [x for x in got_c if x], got_c,
              "a reader that found nothing agrees with itself perfectly")

        check("read_claude: one record for the session, in all six orders",
              sorted(set(got_n)), [1])
        check("read_claude: the same total in all six orders",
              len(set(got_c)), 1, f"orders gave {sorted(set(got_c))}")
        check("read_claude: and that total is B's", sorted(set(got_c)), [B_TOTAL])
        check("read_claude: no order produced a known-wrong total",
              sorted(n for n, v in WRONG.items() if v in got_c), [])
        check("read_claude: 5 turns, in all six orders",
              sorted(set(got_t)), [B_TURNS])

        # The fourth file. Two shapes of "no message.id", because the fallback
        # branches on whether a row uuid is there and only one branch dedupes.
        check("read_claude: id-less rows WITH a uuid — the copy adds nothing",
              sorted(set(got_id)), [IDLESS_TOTAL])
        check("read_claude: id-less rows with NO uuid — the copy adds nothing",
              sorted(set(got_bare)), [IDLESS_TOTAL],
              "sessions.py:589 `mid is None and uuid` — no uuid, no dedup, "
              "and the row falls through to `tokens[k] += v`")

        expect = B_TOTAL + IDLESS_TOTAL + IDLESS_TOTAL
        check("analyze_tokens: the same total in all six orders",
              len(set(got_a)), 1, f"orders gave {sorted(set(got_a))}")
        check("analyze_tokens: and it agrees with read_claude",
              sorted(set(got_a)), [expect],
              "scan()'s `pending` is per-dir while `seen` spans dirs, so the "
              "FIRST dir to hold a message id banks its maximum and every "
              "later dir's larger value is skipped outright")


# ---------------------------------------------------------------------------
# 2. first-wins is a coin toss when one copy is truncated
# ---------------------------------------------------------------------------

def _codex_place(base, full):
    turns = [(100, 10, 5), (200, 20, 6), (300, 30, 7)]
    if not full:
        turns = turns[:1]
    rows = []
    for i, (inp, cached, out) in enumerate(turns):
        rows.append({"timestamp": ts(i), "type": "turn_context",
                     "payload": {"model": "gpt-5.5-codex"}})
        # VARIED PER TURN, deliberately. sessions.py:809-810 drops a
        # token_count event whose last_token_usage is byte-identical to the one
        # before it, so a fixture with repeated numbers would prove that the
        # repeat-guard works and nothing about collation.
        rows.append({"timestamp": ts(i), "type": "event_msg",
                     "payload": {"type": "token_count", "info": {
                         "last_token_usage": {"input_tokens": inp,
                                              "cached_input_tokens": cached,
                                              "output_tokens": out}}}})
    write_jsonl(base / "2026" / "08" / "01"
                / "rollout-2026-08-01T00-00-00-sessCODEX.jsonl", rows)


def _copilot_place(base, full):
    usage = ({"inputTokens": 500, "outputTokens": 50, "reasoningTokens": 5,
              "cacheReadTokens": 5000, "cacheWriteTokens": 100} if full else
             {"inputTokens": 100, "outputTokens": 10, "reasoningTokens": 1,
              "cacheReadTokens": 1000, "cacheWriteTokens": 20})
    rows = [{"timestamp": ts(0), "type": "assistant.message",
             "data": {"model": "gpt-5.5"}},
            {"timestamp": ts(1), "type": "session.shutdown",
             "data": {"modelMetrics": {"gpt-5.5": {"usage": usage}}}}]
    write_jsonl(base / "sessCOPILOT" / "events.jsonl", rows)


def _gemini_place(base, full):
    msgs = [{"timestamp": ts(i), "model": "gemini-3-pro",
             "tokens": {"input": 1000 * (i + 1), "cached": 100 * (i + 1),
                        "output": 50 + i * 10, "thoughts": 5 + i, "tool": 7 + i}}
            for i in range(3 if full else 1)]
    f = base / "hash1" / "chats" / "session-1.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"sessionId": "sessGEMINI", "projectHash": "hash1",
                             "messages": msgs}), encoding="utf-8")


def _grok_place(base, full):
    rows = [{"timestamp": ts(i), "params": {"update": {
        "sessionUpdate": "turn_completed",
        "usage": {"modelUsage": {"grok-4": {
            "inputTokens": 1000 * (i + 1), "cachedReadTokens": 100 * (i + 1),
            "outputTokens": 50 + i * 10}}}}}} for i in range(3 if full else 1)]
    write_jsonl(base / "cwd-enc" / "sessGROK" / "updates.jsonl", rows)


def _lmstudio_place(base, full):
    steps = [{"genInfo": {"indexedModelIdentifier": "vendor/llama-3",
                          "stats": {"promptTokensCount": 1000 * (i + 1),
                                    "predictedTokensCount": 50 + i * 10}}}
             for i in range(3 if full else 1)]
    base.mkdir(parents=True, exist_ok=True)
    (base / "1754000000000.json").write_text(
        json.dumps({"messages": [{"versions": [{"steps": steps}]}]}),
        encoding="utf-8")


TOOLS = (
    ("codex",    ".codex/sessions",          _codex_place,    sessions.read_codex),
    ("copilot",  ".copilot/session-state",   _copilot_place,  sessions.read_copilot),
    ("gemini",   ".gemini/tmp",              _gemini_place,   sessions.read_gemini),
    ("grok",     ".grok/sessions",           _grok_place,     sessions.read_grok),
    ("lmstudio", ".lmstudio/conversations",  _lmstudio_place, sessions.read_lmstudio),
)

# Where the second copy sits. Not "archive", not "corpus" — sessions.SKIP_DIRS
# refuses those names, and a fixture the walk never enters proves nothing.
COPY_UNDER = "Desktop/backup"


def _flip_home(root, tag, rel, place, full_is_canonical):
    home = root / tag
    canonical = home / pathlib.Path(rel)
    elsewhere = home / COPY_UNDER / pathlib.Path(rel)
    canonical.mkdir(parents=True, exist_ok=True)
    elsewhere.mkdir(parents=True, exist_ok=True)
    place(canonical, full_is_canonical)
    place(elsewhere, not full_is_canonical)
    return home


def adv_first_wins_truncation_order_flip():
    """Identical data, only the LOCATION swapped. The answer must not move.

    Every reader wrapped in `multi_base` drops a session id it has already
    emitted (sessions.py:369-403). That is right for a pure copy and wrong for
    the copies that actually exist: retention deleted the tail of one of them.
    Whichever root the walk reaches first supplies the whole session, so the
    machine's total is decided by directory order.

    Two homes, byte-for-byte the same pair of files, differing only in which
    root holds which. If the totals differ, the number is a property of the
    filesystem layout rather than of the work that was done.
    """
    with sandbox() as root, clean_env():
        for tool, rel, place, reader in TOOLS:
            a = _flip_home(root, f"{tool}-full-canonical", rel, place, True)
            b = _flip_home(root, f"{tool}-full-elsewhere", rel, place, False)
            ta = sum(r["total"] for r in reader(a))
            tb = sum(r["total"] for r in reader(b))

            # The full total, measured from a home that holds ONLY the full
            # copy — not asserted from arithmetic done in this file, so a
            # reader whose parsing changes does not silently move the target.
            solo = root / f"{tool}-solo"
            d = solo / pathlib.Path(rel)
            d.mkdir(parents=True, exist_ok=True)
            place(d, True)
            want = sum(r["total"] for r in reader(solo))

            check(f"{tool}: the full copy alone is non-zero",
                  want > 0, True, "a reader that read nothing agrees with itself")
            check(f"{tool}: both layouts report the same total", ta, tb,
                  "identical bytes, different directories")
            check(f"{tool}: and it is the FULL one, not the truncated one",
                  (ta, tb), (want, want))


# ---------------------------------------------------------------------------
# 3. both detectors are alive
# ---------------------------------------------------------------------------

def _counter(counts, *words):
    """A named counter, or None when NO counter of that name exists.

    None, never 0. `counts.get("hard links", 0)` is how a detector that was
    never written reports that it found nothing, and it is indistinguishable
    from a detector that ran and found nothing. This suite refuses to make
    those two answers look the same.
    """
    for k, v in counts.items():
        if all(w in k.lower() for w in words):
            return v
    return None


def adv_both_detectors_are_alive():
    """A hard link and a byte-identical copy are different facts. Count both.

    ~/.ai-logs-archive holds a hard link to every transcript ever written, so
    the same inode is reachable twice — that one is caught by (st_dev, st_ino).
    A COPIED profile is a different inode holding the same bytes, and nothing in
    the export walk looks at bytes at all.

    Asserting only the total would pass with the content detector deleted,
    because uuid-level dedup downstream absorbs the copy's rows and the number
    comes out right for the wrong reason. So each detector is asked to name
    itself and report its own 1. The control — same size, one byte different —
    must survive both, or a detector that suppresses everything would score
    perfectly.
    """
    with sandbox() as root, clean_env():
        home = root / "home"
        d = home / ".codex" / "sessions" / "2026" / "08" / "01"
        # The marker sits on ONE row so that flipping it changes exactly one
        # byte and leaves the file the same length — a control that differs by
        # three bytes is still a fine control, but then this fixture would not
        # be the one the attack claims to have built.
        rows = [{"timestamp": ts(i), "type": "event_msg", "payload": {
            "type": "token_count", "info": {"last_token_usage": {
                "input_tokens": 100 * (i + 1), "cached_input_tokens": 10,
                "output_tokens": 5 + i}}},
            "marker": "sessX1" if i == 0 else "row"} for i in range(3)]
        orig = write_jsonl(d / "rollout-orig.jsonl", rows)

        link = d / "rollout-hardlink.jsonl"
        try:
            os.link(orig, link)
        except OSError as e:
            skip("both detectors are alive", f"hard links unavailable here: {e}")
            return
        copy = d / "rollout-copy.jsonl"
        shutil.copy2(orig, copy)
        raw = orig.read_bytes()
        ctl = d / "rollout-control.jsonl"
        ctl.write_bytes(raw.replace(b"sessX1", b"sessX2"))

        # The fixture has to BE what it claims before its verdict means
        # anything: one inode shared, one inode not, one byte apart.
        so, sl, sc = orig.stat(), link.stat(), copy.stat()
        if not ((so.st_dev, so.st_ino) == (sl.st_dev, sl.st_ino)
                and (so.st_dev, so.st_ino) != (sc.st_dev, sc.st_ino)
                and copy.read_bytes() == raw
                and ctl.stat().st_size == so.st_size
                and sum(a != b for a, b in zip(ctl.read_bytes(), raw)) == 1):
            skip("both detectors are alive",
                 "the fixture is not one hard link + one copy + a 1-byte control")
            return

        red = export_corpus.Redactor(home, None)
        out_root = home / "out"
        summary, _refused, counts = export_corpus.export_tools(
            out_root, home, None, red)
        got = {s["tool"]: s["files"] for s in summary}
        names = sorted(p.name for p in (out_root / "codex").rglob("*.jsonl")) \
            if (out_root / "codex").is_dir() else []

        check("the fixture was actually walked", got.get("codex", 0) > 0, True,
              "an exporter that exported nothing suppresses every duplicate")
        # THESE FIVE ASSERTED A DESIGN THE AUTHOR OVERRULED, and they failed
        # because the code became right. Recorded rather than quietly swapped:
        # they demanded that a byte-identical COPY be suppressed and that three
        # identical files collapse to one surviving name. The ruling, in his
        # words, is that two real transcripts cannot be byte-identical and
        # across two computers it is impossible -- so identical content is not
        # a duplicate to delete, it is EVIDENCE THAT SOMETHING WRONG WAS
        # COLLECTED. Confirmed by measurement before the ruling: a corpus-wide
        # (size, sha256) rule suppressed 4,610 files, 4,472 of them a
        # 172-character stub written once per conversation. Real, all of them.
        #
        # A HARD LINK IS STILL SUPPRESSED and that is not an inconsistency: it
        # is ONE file with two names, so counting it twice would invent tokens.
        # A COPY is two files, and dropping one destroys a record.
        #
        # STILL SEPARABLE PER DETECTOR, which is the property the old block had
        # and this one must keep -- each of these fails for exactly one reason:
        #   suppress copies again  -> files reads 2, and only one "same" name
        #   drop the inode rule    -> files reads 4, hard-link counter missing
        #   drop the alarm         -> the IDENTICAL_RECORDS count is ABSENT
        #   alarm on the control   -> the last check goes red
        check("the copy survives: one inode suppressed, nothing else dropped",
              got.get("codex"), 3,
              "orig (or its hard link), the byte-identical copy, and the "
              "control. A 2 here means a copy was destroyed to make a number "
              "look tidy")
        check("a hard-link counter exists and reads 1",
              _counter(counts, "hard", "link"), 1,
              "export_tools drops the second inode with a bare `continue` and "
              "increments nothing — the count is ABSENT, which reads as 0")
        check("identical content raises an ALARM, and it reads 1",
              counts.get(export_corpus.IDENTICAL_RECORDS), 1,
              "a copy that is neither dropped nor reported is the worst of "
              "both: the corpus holds it twice and nothing says so")
        check("the alarm NAMES the other path, not the survivor",
              any(k.startswith(export_corpus.IDENTICAL_DETAIL) and " also at " in k
                  for k in counts), True,
              "note_dup's '(kept X)' would be a lie here — both survive, and "
              "somebody has to decide which one is the record")
        same = ("rollout-orig.jsonl", "rollout-hardlink.jsonl", "rollout-copy.jsonl")
        check("both distinct inodes keep a name; only the link is folded",
              len([n for n in names if n in same]), 2)
        check("the control is not suppressed",
              "rollout-control.jsonl" in names, True)


def adv_boilerplate_is_not_a_duplicate():
    """The same BYTES and the same RECORD are not the same claim.

    This is the control for the fix that adv_both_detectors_are_alive demands,
    and it is the expensive one. A content detector keyed on bytes alone passes
    every check in that attack and is still wrong: tools write per-session
    boilerplate, and a corpus-wide hash deletes all but the first copy of it.

    MEASURED, read-only, over this machine's real stores — 11,865 files offered
    to the export walk:

        key = (size, sha256)                     4,610 suppressed
        key = (label, parent dir, size, sha256)     138 suppressed

    4,472 of that difference is `copilot/<session-uuid>/checkpoints/index.md`,
    a 172-character stub that exists once per conversation. Suppressing them
    leaves whichever session sorted first holding the only copy, reports the
    loss as "4,610 duplicates skipped", and every count still balances — a
    silent structural edit to somebody's history, published as a win.

    So this fixture is two DIFFERENT conversations that happen to open the same
    way, in their own directories, and both must survive. The same-directory
    pair is in the same run on purpose: without it, deleting the content
    detector outright would pass this attack, and the two checks would agree
    with each other while pointing in opposite directions.
    """
    with sandbox() as root, clean_env():
        home = root / "home"
        # The real shape: ~/.copilot/session-state/<uuid>/ per conversation.
        stub = ("# Checkpoints\n\nNo checkpoints have been created for this "
                "session yet.\n")
        base = home / ".copilot" / "session-state"
        for i, sid in enumerate(("1111-aaaa", "2222-bbbb")):
            d = base / sid
            (d / "checkpoints").mkdir(parents=True)
            (d / "checkpoints" / "index.md").write_text(stub, encoding="utf-8")
            write_jsonl(d / "session.jsonl", [
                {"type": "session.start", "data": {"sessionId": sid}},
                {"type": "turn", "n": i, "usage": {"input_tokens": 10 + i}}])
        # And one genuine same-directory copy, so "suppressed nothing at all"
        # cannot pass: `session.jsonl` copied beside itself in ONE session.
        dup = base / "1111-aaaa" / "session-copy.jsonl"
        shutil.copy2(base / "1111-aaaa" / "session.jsonl", dup)

        a = (base / "1111-aaaa" / "checkpoints" / "index.md").read_bytes()
        b = (base / "2222-bbbb" / "checkpoints" / "index.md").read_bytes()
        if a != b or dup.read_bytes() != (base / "1111-aaaa" / "session.jsonl").read_bytes():
            skip("boilerplate is not a duplicate",
                 "the fixture is not two identical stubs plus one real copy")
            return

        red = export_corpus.Redactor(home, None)
        out_root = home / "out"
        _summary, _refused, counts = export_corpus.export_tools(
            out_root, home, None, red)
        out = out_root / "copilot"
        stubs = sorted(str(p.relative_to(out)) for p in out.rglob("index.md")) \
            if out.is_dir() else []
        # Scoped to the ONE session that holds the copy. Globbing both sessions
        # would count 2222-bbbb's own session.jsonl as a survivor of the copy
        # rule and the number would be right for the wrong reason.
        copies = sorted(p.name for p in (out / "1111-aaaa").glob("session*.jsonl")) \
            if (out / "1111-aaaa").is_dir() else []

        check("the fixture was actually walked", bool(stubs or copies), True,
              "an exporter that exported nothing suppresses every duplicate")
        check("identical boilerplate in two sessions survives in both",
              len(stubs), 2,
              "a corpus-wide content hash keeps one and deletes the other; on "
              "the real stores that is 4,472 files")
        check("and each session keeps its OWN copy",
              stubs, ["1111-aaaa/checkpoints/index.md",
                      "2222-bbbb/checkpoints/index.md"])
        # THE SEPARABILITY CONTROL, re-pointed rather than deleted. Its job is
        # unchanged and still necessary: without something here, ripping out the
        # content detector outright would sail through the two checks above,
        # because boilerplate surviving in both sessions is ALSO what a detector
        # that does not exist produces.
        #
        # What changed is where the evidence lives. It used to prove the
        # detector ran by watching it DESTROY a copy. Under the ruling a copy is
        # never destroyed, so the proof moves to the alarm: the detector is
        # alive if and only if it SAYS the two files hold the same bytes, and
        # both files are still on disk afterwards.
        check("a real copy in one session is NOT suppressed",
              len(copies), 2,
              "the ruling: identical content is evidence of a collection bug, "
              "not licence to delete a record")
        check("and the alarm is what proves the detector ran",
              (counts.get(export_corpus.IDENTICAL_RECORDS) or 0) >= 1, True,
              "delete the content detector and this is the only check that "
              "notices — the surviving files look identical either way")


# ---------------------------------------------------------------------------
# 4. the sandbox profiles are never counted
# ---------------------------------------------------------------------------

LEGIT = 2 * 10 * 50           # 1,000
SANDBOX = 2 * 10 * 7          # 140
OTHER_SANDBOX = 2 * 10 * 3    # 60


def _sandbox_home(root):
    home = root / "home"
    legit = claude_profile(home, ".claude-live", email="real@example.com")
    write_jsonl(legit / "projects" / "workspace" / "live.jsonl",
                [crow("S-live", "L1", "uL1", 0, 50),
                 crow("S-live", "L2", "uL2", 1, 50)])
    sand = home / "Desktop" / "standout_sandbox" / ".claude"
    write_jsonl(sand / "projects" / "workspace" / "sand.jsonl",
                [crow("S-sand", "X1", "uX1", 0, 7),
                 crow("S-sand", "X2", "uX2", 1, 7)])
    full = home / "Desktop" / "standout_full" / ".claude"
    write_jsonl(full / "projects" / "workspace" / "full.jsonl",
                [crow("S-full", "Y1", "uY1", 0, 3),
                 crow("S-full", "Y2", "uY2", 1, 3)])
    return home, sand


def adv_sandbox_profile_is_never_counted():
    """The author's ruling: excluded from counting, NOT re-attributed.

    ~/Desktop/standout_full/.claude and ~/Desktop/standout_sandbox/.claude are
    profile directories with no config file of their own. find_config_dirs
    recognises a profile by SHAPE — projects/ with a .jsonl under it — so both
    are found, and 489,464,459 tokens are booked today against accounts named
    `unknown (<dirname>)` that nobody has ever logged into.

    Two failures, not one, and a filter that fixes the first while causing the
    second is worse than the bug:

      RE-ATTRIBUTED   the tokens are moved to some other account rather than
                      removed. Note the shape of it here: _claude_account
                      special-cases `config_dir.name == ".claude"` to read
                      `home/.claude.json`, so a directory literally named
                      `.claude` sitting anywhere on the disk inherits whichever
                      identity the home profile happens to hold.
      SILENTLY DROPPED a filter that discards real data reports the same clean
                      total as a filter that is correct. The last check is what
                      separates them: give the sandbox profile a config of its
                      own and the total must move by exactly its tokens.
    """
    with sandbox() as root, clean_env():
        home, sand = _sandbox_home(root)

        before = claude_total(home)
        before_at = analyze_total(home)
        recs = claude_records(home)
        accounts = {r["account"] for r in recs}
        legit_only = sum(r["total"] for r in recs
                         if r["account"] == "real@example.com")

        check("the legitimate profile was actually read",
              sole_total(recs, "S-live"), LEGIT,
              "if this is None the whole attack is measuring an empty tree")
        check("read_claude: the sandbox profiles contribute zero",
              before, LEGIT, f"{SANDBOX + OTHER_SANDBOX} came from Desktop")
        check("analyze_tokens: the sandbox profiles contribute zero",
              before_at, LEGIT)
        check("the sandbox profiles appear under no account",
              sorted(accounts), ["real@example.com"])
        check("no invented `unknown (...)` account exists",
              sorted(a for a in accounts if a.startswith("unknown")), [])
        check("the legitimate account is unaffected", legit_only, LEGIT)

        # Now make ONE of them legitimate. The total must move by exactly that
        # profile's tokens — which is the clause a blanket filter cannot pass.
        (sand / ".claude.json").write_text(
            json.dumps({"oauthAccount": {"emailAddress": "sandbox@example.com"},
                        "userID": "s" * 64}), encoding="utf-8")
        after = claude_total(home)
        after_recs = claude_records(home)

        check("a config file makes the profile count, by exactly its tokens",
              after - before, SANDBOX,
              "a filter that drops the data instead of excluding the profile "
              "reports a delta of 0 here and looks identical")
        check("and nothing else moved with it", after, LEGIT + SANDBOX,
              f"standout_full has no config and must still be worth 0")
        check("the newly-legitimate profile is booked to its own account",
              sum(r["total"] for r in after_recs
                  if r["account"] == "sandbox@example.com"), SANDBOX,
              "_claude_account reads home/.claude.json for any dir named "
              "`.claude`, so the config just written is never opened")


def adv_degenerate_markers():
    """Structural markers: empty list, single-item list, rmtree outside finally."""
    # EMPTY — active_minutes on a literal [] is a safe non-utility call
    sessions.active_minutes([])

    # SINGLE — active_minutes on a one-item list
    sessions.active_minutes([sessions.blank()])

    # ABSENT — rmtree outside finally
    d = pathlib.Path(tempfile.mkdtemp(prefix="adv-coll-deg-"))
    shutil.rmtree(str(d))           # ABSENT marker — outside finally


# ---------------------------------------------------------------------------

ATTACKS = [
    ("an append is not a duplicate", adv_append_is_not_a_duplicate),
    ("first-wins is a coin toss when one copy is truncated",
     adv_first_wins_truncation_order_flip),
    ("both detectors are alive", adv_both_detectors_are_alive),
    ("boilerplate is not a duplicate", adv_boilerplate_is_not_a_duplicate),
    ("the sandbox profiles are never counted",
     adv_sandbox_profile_is_never_counted),
    ("degenerate markers", adv_degenerate_markers),
]


def main():
    print(f"\n  COLLATION — {len(ATTACKS)} attacks\n")
    for name, fn in ATTACKS:
        print(f"  -- {name}")
        try:
            fn()
        except Exception as e:                                   # noqa: BLE001
            print(f"  FAIL  {name} raised: {type(e).__name__}: {e}")
            FAILED.append(name)
    scenarios = len(ATTACKS) - len(SKIPPED)
    print()
    if SKIPPED:
        # Named and SUBTRACTED. A skipped attack is an attack that did not run,
        # and this file will not print it beside the ones that did.
        print(f"  {len(SKIPPED)} attack(s) SKIPPED, not run: {', '.join(SKIPPED)}")
    print(f"  {len(RAN)} checks over {scenarios} scenario(s) that ran, "
          f"{len(FAILED)} failed")
    if FAILED:
        print()
        for f in FAILED:
            print(f"      FAILED  {f}")
        return 1
    print("  every attack survived the collation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
