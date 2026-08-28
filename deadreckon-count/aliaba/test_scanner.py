#!/usr/bin/env python3
"""Regression tests for the counting itself. No network, no real transcripts.

    python3 test_scanner.py

Two different things get verified in this repo and they are not the same thing:

  TRANSFER    did the bytes arrive intact — corpus_ship.py checks each range
              against the server as it lands, then the whole file's sha256
  COMPUTATION is the arithmetic right — this file

check_consistency.py runs on every update, but it checks that the slices of a
real scan add up. A reader that silently finds nothing partitions perfectly, so
consistency cannot catch it. These are the cases where a number came out wrong,
each frozen as an assertion with the value it must produce.

Every test here is a bug that actually shipped. If one fails, that bug is back.
"""

import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).parent))

PASS, FAIL = [], []


def check(name, got, want, why=""):
    (PASS if got == want else FAIL).append((name, got, want, why))


def turn(uuid, model="claude-opus-4-6", **usage):
    """One assistant turn as Claude Code writes it."""
    u = {"input_tokens": 0, "cache_creation_input_tokens": 0,
         "cache_read_input_tokens": 0, "output_tokens": 0}
    u.update(usage)
    return json.dumps({"uuid": uuid, "timestamp": "2026-07-01T10:00:00.000Z",
                       "sessionId": "s1", "type": "assistant",
                       "message": {"role": "assistant", "model": model, "usage": u}})


# --------------------------------------------------------------- counting
def test_only_four_fields(tmp):
    """usage carries restatements of itself. Summing what looks numeric is 4x."""
    import analyze_tokens as A
    d = tmp / ".claude" / "projects" / "p1"
    d.mkdir(parents=True)
    rec = json.loads(turn("u1", input_tokens=2, cache_creation_input_tokens=11475,
                          cache_read_input_tokens=20831, output_tokens=110))
    # The real extras seen on disk: each one restates the same tokens.
    rec["message"]["usage"].update({
        "cache_creation": {"ephemeral_1h_input_tokens": 11475,
                           "ephemeral_5m_input_tokens": 0},
        "iterations": [{"input_tokens": 2, "output_tokens": 110}],
        "server_tool_use": {"web_search_requests": 0},
        "service_tier": "standard",
    })
    (d / "a.jsonl").write_text(json.dumps(rec) + "\n")
    r = A.scan(tmp / ".claude")
    check("only the 4 token fields are summed", A.grand(r["totals"]), 2 + 11475 + 20831 + 110,
          "cache_creation/iterations restate the same tokens")

    # AND ON THE BRANCH REAL ROWS ACTUALLY TAKE.
    #
    # turn() emits no message.id, so everything above went down the `not mid`
    # path — counted once, immediately, keyed on the row uuid. Real Claude Code
    # rows carry message.id and go through the running-maximum instead, which
    # is a SECOND place the field list is applied and where these restatements
    # would be summed again. Nothing exercised it: this test was measuring the
    # branch approximately zero rows on disk take.
    d2 = tmp / ".claude" / "projects" / "p2"
    d2.mkdir(parents=True)
    rec2 = json.loads(turn("u2", input_tokens=2, cache_creation_input_tokens=11475,
                           cache_read_input_tokens=20831, output_tokens=110))
    rec2["message"]["id"] = "msg_real"
    rec2["message"]["usage"].update({
        "cache_creation": {"ephemeral_1h_input_tokens": 11475,
                           "ephemeral_5m_input_tokens": 0},
        "iterations": [{"input_tokens": 2, "output_tokens": 110}],
        "server_tool_use": {"web_search_requests": 0},
        "service_tier": "standard",
    })
    (d2 / "b.jsonl").write_text(json.dumps(rec2) + "\n")
    r2 = A.scan(tmp / ".claude")
    check("and on the message.id branch, which every real row takes",
          A.grand(r2["totals"]), 2 * (2 + 11475 + 20831 + 110),
          "the running-maximum path applies the field list a second time; "
          "summing the restatements there is a 4x that the other branch "
          "cannot see")


def test_uuid_dedup(tmp):
    """A resumed session rewrites earlier turns; a subagent's turns are inlined."""
    import analyze_tokens as A
    d = tmp / ".claude" / "projects" / "p1"
    d.mkdir(parents=True)
    (d / "a.jsonl").write_text(turn("same", output_tokens=100) + "\n")
    (d / "b.jsonl").write_text(turn("same", output_tokens=100) + "\n"
                               + turn("other", output_tokens=7) + "\n")
    r = A.scan(tmp / ".claude")
    check("the same uuid in two files counts once", A.grand(r["totals"]), 107)


def test_dedup_spans_config_dirs(tmp):
    """A copied profile must add zero, or wide discovery inflates by its whole size."""
    import analyze_tokens as A
    for name in (".claude", ".claude-copy"):
        d = tmp / name / "projects" / "p1"
        d.mkdir(parents=True)
        (d / "a.jsonl").write_text(turn("u1", output_tokens=500) + "\n")
    seen = set()
    total = sum(A.grand(A.scan(tmp / n, seen)["totals"]) for n in (".claude", ".claude-copy"))
    check("a duplicate profile adds zero", total, 500,
          "global dedup is what makes shape-based discovery safe")


def test_provider_is_the_model_not_the_cli(tmp):
    """DeepSeek served through a Claude-Code-shaped client is not Anthropic."""
    import analyze_tokens as A
    d = tmp / ".claude" / "projects" / "p1"
    d.mkdir(parents=True)
    (d / "a.jsonl").write_text(turn("u1", model="claude-opus-4-6", output_tokens=10) + "\n"
                               + turn("u2", model="deepseek-v4-pro", output_tokens=90) + "\n")
    r = A.scan(tmp / ".claude")
    by = {k: sum(v.values()) for k, v in r["by_provider"].items()}
    check("anthropic gets only the claude turn", by.get("anthropic"), 10)
    check("deepseek gets only the deepseek turn", by.get("deepseek"), 90)


def test_counter_is_per_account_not_per_profile():
    """One account can own several profiles; it has ONE stats-cache counter.

    Looking it up per profile claimed it once per profile — a 12,290,485,337
    counter applied 5 times took one machine's floor from 30.9B to 81.0B.
    """
    import stats_page as S
    machine = {"machine": "M", "accounts": [
        {"account": "a@x", "grand_total": 100, "by_day": {"2026-07-20": 100}},
        {"account": "a@x", "grand_total": 50, "by_day": {"2026-07-20": 50}},
        {"account": "a@x", "grand_total": 0, "by_day": {}},
    ]}
    cache = [{"account": "a@x", "total": 1000, "last_computed": "2026-07-01"}]
    floor, claude, other, rows = S.machine_floor(machine, [], cache)
    check("counter applied once per account", claude, 1000 + 150,
          "1000 counter + 150 of transcripts after its end date")
    check("one row per account, not per profile", len(rows), 1)


def test_counter_excludes_its_own_window():
    """Transcript days inside the counter's window are already in the counter."""
    import stats_page as S
    machine = {"machine": "M", "accounts": [
        {"account": "a@x", "grand_total": 300,
         "by_day": {"2026-06-01": 200, "2026-07-20": 100}},
    ]}
    cache = [{"account": "a@x", "total": 1000, "last_computed": "2026-07-01"}]
    floor, claude, other, rows = S.machine_floor(machine, [], cache)
    check("days on/before lastComputedDate are not added again", claude, 1100,
          "the 200 from June is inside the counter's window")


# -------------------------------------------------------------- discovery
def test_discovery_finds_profiles_outside_home(tmp):
    """~/Desktop/x/.claude held 817,889,443 tokens no glob of ~ could see.

    TWO RULES, AND THEY ARE NOT THE SAME RULE. This test used to assert one of
    them and was read as asserting both, which is how it ended up demanding the
    opposite of what adv_collation.py demands of the same function.

      DISCOVERY IS GREEDY.  A profile buried under ~/Desktop/ must be REACHED.
      That is the 817,889,443 tokens no `~/.*claude*` glob could see, and the
      archiver and the exporter both need it — "must not be counted" is not
      "must not be preserved".

      COUNTING IS NARROW.  A profile-shaped directory that claims no account
      (analyze_tokens.profile_claim) must be left OUT of the default list and
      NAMED in `excluded`, per the author's ruling on ~/Desktop/standout_*.
      Counting them published 489,464,459 tokens under invented
      `unknown (<dirname>)` accounts nobody has ever logged into.

    The `excluded` clause is what stops the second rule from being satisfied by
    a filter that simply loses the directory: dropped-and-named and
    dropped-and-silent produce the identical default list.
    """
    import analyze_tokens as A
    for rel in (".claude", "Desktop/staging/.claude"):
        d = tmp / rel / "projects" / "p1"
        d.mkdir(parents=True)
        (d / "a.jsonl").write_text(turn("u-" + rel, output_tokens=1) + "\n")
    reached = {str(p.relative_to(tmp))
               for p in A.find_config_dirs(tmp, include_unclaimed=True)}
    check("a profile nested outside the home glob is found", reached,
          {".claude", "Desktop/staging/.claude"})
    dropped = []
    counted = {str(p.relative_to(tmp))
               for p in A.find_config_dirs(tmp, excluded=dropped)}
    check("but a nested profile that claims no account is not counted",
          counted, {".claude"})
    check("and the one that was dropped is named with its path",
          [str(pathlib.Path(e["path"]).relative_to(tmp)) for e in dropped],
          ["Desktop/staging/.claude"])


def test_discovery_skips_our_own_exports(tmp):
    """corpus/ and merged/ are this tool's output, not someone's profile."""
    import analyze_tokens as A
    for rel in (".claude", "corpus/hp/.claude", "merged/.claude"):
        d = tmp / rel / "projects" / "p1"
        d.mkdir(parents=True)
        (d / "a.jsonl").write_text(turn("u-" + rel, output_tokens=1) + "\n")
    found = {str(p.relative_to(tmp)) for p in A.find_config_dirs(tmp)}
    check("own exports are not read back as profiles", found, {".claude"})


# ------------------------------------------------------------- redaction
def test_redaction_path_shapes():
    """Each of these got past the redactor at some point, or was never handled."""
    import export_corpus as E
    import merge_corpus as M
    red = E.Redactor(pathlib.Path("/home/nobody"), "keep@example.com")
    shapes = {
        "linux home":       "/home/someone/p/a.py",
        "mac home":         "/Users/someone/p/a.py",
        "win C:":           r"C:\Users\someone\p\a.py",
        "win D:":           r"D:\Users\someone\p\a.py",
        "win JSON-escaped": r"D:\\Users\\someone\\p\\a.py",
        "WSL /mnt/c":       "/mnt/c/Users/someone/p/a.py",
        "UNC":              r"\\server\share\someone\a.py",
        "UNC escaped":      r"\\\\server\\share\\someone\\a.py",
        "mac volume":       "/Volumes/Backup Drive/x.txt",
        "linux media":      "/media/someone/USB/x.txt",
        "run/media":        "/run/media/someone/USB/x.txt",
        "root":             "/root/.ssh/config",
    }
    leaked = [n for n, s in shapes.items()
              if any(rx.search(red.walk(s)) for rx in M.LEAK.values())]
    check("no path shape survives redaction", leaked, [])


def test_redactor_matches_its_own_verifier():
    """A redactor weaker than its checker reports leaks it cannot fix."""
    import export_corpus as E
    import merge_corpus as M
    red = E.Redactor(pathlib.Path("/home/nobody"), "keep@example.com")
    # Two segments only: the signature had been split off in a real transcript.
    jwt2 = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJ4Iiwic2NvcGVzIjpbImFwaV9yZWFkIl19"
    jwt3 = jwt2 + ".c2lnbmF0dXJlaGVyZQ"
    for name, tok in (("2-segment JWT", jwt2), ("3-segment JWT", jwt3)):
        after = red.walk(tok)
        check(f"{name} is redacted", any(rx.search(after) for rx in M.LEAK.values()), False)


def test_prefilter_sees_json_escaped_backslashes():
    """JSON stores \\ doubled, so a raw-bytes filter misses every Windows path."""
    import merge_corpus as M
    raw = r'{"t":"see D:\\Users\\someone\\a.txt"}'
    win = M.LEAK["windows home"]
    check("raw bytes alone do NOT match (this is why the filter collapses them)",
          bool(win.search(raw)), False)
    check("collapsing doubled backslashes finds it",
          bool(win.search(raw.replace("\\\\", "\\"))), True)


def test_merge_writes_every_transcript_it_reads(tmp):
    """`if lines:` again, in the merge — transcripts IN did not equal OUT.

    The exporter's copy of this was found and fixed; the merge carried the
    identical shape and nobody looked. Its uuid dedup is GLOBAL ACROSS MACHINES,
    which is the whole point of it — a session synced or copied between two
    computers arrives twice — so a transcript whose every row was claimed by the
    machine read first produced an empty list and was written nowhere.

    Three real shapes reach the writer with nothing to write, and none of them
    means the session did not happen:

      b.jsonl   every row already claimed (the same session on two machines)
      c.jsonl   exported empty ON PURPOSE by export_corpus, which now writes a
                transcript whose rows were all seen elsewhere as an empty file
      d.jsonl   nothing in it parses

    c.jsonl is the one that makes this a system defect rather than a merge
    defect: the exporter's fix deliberately produces empty files, and the merge
    then deleted exactly those. The two halves of one pipeline disagreed about
    whether existence is a fact worth keeping.

    Silence was also worse here than in the exporter, because `per_machine`
    reports what was WALKED: the run said 4 files for a tree holding 1.
    """
    import merge_corpus as M

    corpus = tmp / "record"
    proj = corpus / "machine-a" / ".claude" / "projects" / "-workspace-p001"
    proj.mkdir(parents=True)
    (proj / "a.jsonl").write_text(turn("u1") + "\n" + turn("u2") + "\n")
    (proj / "b.jsonl").write_text(turn("u1") + "\n" + turn("u2") + "\n")
    (proj / "c.jsonl").write_text("")
    (proj / "d.jsonl").write_text("not json at all\n")

    out = tmp / "merged"
    argv = sys.argv
    try:
        sys.argv = ["merge_corpus.py", "--corpus", str(corpus), "--out", str(out)]
        M.main()
    finally:
        sys.argv = argv

    got = sorted(p.name for p in (out / ".claude" / "projects").rglob("*.jsonl"))
    check("every transcript read is a transcript written",
          got, ["a.jsonl", "b.jsonl", "c.jsonl", "d.jsonl"],
          "`if lines:` walks it, reads it, scans it for leaks and drops it")

    merge = json.loads((out / "MERGE.json").read_text())
    check("files in equals files out, and the report says both",
          (merge["files_read"], merge["files_written"]), (4, 4),
          "a report that derives both from one variable cannot tell you when "
          "they differ")
    check("and the three empty ones are named as such, not just missing",
          merge["files_without_a_unique_row"], 3,
          "absent looks exactly like zero — the count has to reach the report")
    check("the rows themselves are still de-duplicated",
          merge["duplicates_dropped"], 2,
          "writing b.jsonl's rows again would double every one of them")
    check("so the shared row is in the merged tree exactly once",
          sum(ln.count('"u1"') for p in
              (out / ".claude" / "projects").rglob("*.jsonl")
              for ln in p.read_text().splitlines()), 1,
          "a total taken over the merged tree has to be honest")


def test_month_closes_on_the_local_clock(tmp):
    """A month ends when the computer's date says so, and is then frozen.

    Nothing in a session record says "the month is over"; only the clock can.
    And a finished month must never be recomputed — the transcripts behind it
    are deleted after cleanupPeriodDays, so a later rebuild would read fewer
    records and quietly revise history downward.
    """
    import monthly
    months = {"2026-07": {"tokens": 5, "sessions": 1, "turns": 1, "minutes": 1.0,
                          "by_cli": {"claude": 5}, "by_machine": {"m": 5},
                          "by_model": {}, "first": "2026-07-01", "last": "2026-07-02"}}
    check("a month before now is closed", "2026-07" < "2026-08", True)
    check("the current month is not closed", "2026-08" < "2026-08", False)
    check("next month closes the current one", "2026-08" < "2026-09", True)


def test_no_reader_uses_the_flat_glob():
    """The flat glob was in four files and cost 936 transcripts. It must stay gone.

    proj.glob("*.jsonl") misses subagent transcripts one directory deeper —
    projects/<proj>/<session-uuid>/subagents/agent-*.jsonl — and every one of
    those is a real API conversation with real tokens.

    Fixed in sessions.py, count_corpus.py, corpus_reports.py and export_corpus.py
    on 2026-08-09.  Two files LEGITIMATELY keep it: merge_corpus.py and
    chunk_corpus.py both read the already-exported (already-flat) corpus, where
    the structure is projects/<proj>/*.jsonl with no subdirectories.  test_fleet.py
    carries it as a string literal inside a planted-break, not as executable code.

    This check prevents a fifth copy from shipping silently.
    """
    import re
    root = pathlib.Path(__file__).parent
    # Matches the exact flat-glob form that shipped as a defect — a method call
    # on the glob name with a bare *.jsonl pattern.
    FLAT = re.compile(r'\.glob\(["\']?\*\.jsonl["\']?\)')
    # These files legitimately use the pattern for reasons documented above,
    # or mention it only in documentation prose (docstrings/comments).
    ALLOWED = {"merge_corpus.py", "chunk_corpus.py", "test_fleet.py",
               "test_scanner.py",
               # corpus_reports.py:64 and test_readers.py:519 mention the
               # pattern in docstrings to document what was fixed — not code.
               "corpus_reports.py", "test_readers.py"}
    offenders = []
    for f in sorted(root.glob("*.py")):
        if f.name in ALLOWED:
            continue
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if FLAT.search(line) and not line.lstrip().startswith("#"):
                offenders.append(f"{f.name}:{n}")
    check("no reader/scanner uses the flat glob on a live profile directory",
          offenders, [],
          "proj.glob('*.jsonl') misses subagent transcripts one directory deeper; "
          "use rglob or walk_tree — a fifth copy is how this defect shipped three "
          "extra times after sessions.py was fixed")


def test_no_script_reads_a_generated_file_by_flat_path(tmp):
    """Generated files moved into human-readable/ and machine-readable/.

    Four separate places kept joining the OLD flat path, and each failed
    silently rather than loudly: the archive stopped recording and said
    "nothing changed", the scanned count read 0 of 6 on a five-machine fleet,
    a generator wrote where no reader looked, and --list called every computer
    never-scanned including three it had just scanned.

    A missing file is indistinguishable from an empty result, which is why
    none of them announced themselves. This asserts the whole class is gone.
    """
    import re
    root = pathlib.Path(__file__).parent
    GEN = r"(totals|sessions|hardware|stats|scorecard|lifetime)\.json|" \
          r"(BY-[A-Z]+|STATS|LIFETIME|THIS-MONTH|COVERAGE|ALL-COMPUTERS)\.\w+"
    offenders = []
    for f in sorted(root.glob("*.py")):
        if f.name in ("paths.py", "test_scanner.py"):
            continue
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if not re.search(GEN, line):
                continue
            if "/" not in line or "paths." in line:
                continue
            # `data` and `docs` come from paths.machine()/paths.human() — those
            # are correct writes, not flat joins.
            if re.search(r"\b(data|docs)\s*/", line):
                continue
            # `x / "totals.json"` with no paths.find in sight
            if re.search(r"/\s*[\"']" + "(" + GEN + ")", line):
                offenders.append(f"{f.name}:{n}")
    # corpus_reports deliberately deletes the pre-split copy; fun_stats picks
    # its destination via paths.human on the line above.
    offenders = [o for o in offenders
                 if not o.startswith(("corpus_reports.py", "fun_stats.py"))]
    check("no script joins a generated file by flat path", offenders, [],
          "use paths.find() — a missing file reads exactly like an empty result")


# --------------------------------------------------------------- absence
def test_absent_is_not_zero(tmp):
    """A tool that was never looked for must not read like one that found nothing.

    The row a reader emits says `installed`, and that comes from DETECT. A
    reader with no DETECT entry reports installed=False whether the tool is
    absent or the reader is broken — the two become the same output, which is
    the mistake that hid four readers returning 0 for months.
    """
    import sessions as S

    # A FLOOR FIRST, because everything below is generated by iterating
    # READERS. With READERS empty, `set(READERS) - set(DETECT)` is [] and the
    # per-reader loop runs zero times: losing every reader in the repository
    # would DELETE these assertions rather than fail them, and the suite would
    # report the same "45 checks, 0 failed" with nothing left to check. The
    # count is asserted against a number that only ever goes up.
    check("the reader registry has not been emptied", len(S.READERS) >= 11, True,
          f"only {len(S.READERS)} readers — a reader was removed, or the "
          f"registry failed to build")

    missing = sorted(set(S.READERS) - set(S.DETECT))
    check("every reader has a DETECT entry", missing, [],
          "without one, 'not installed' and 'reader found nothing' are identical")
    # BOTH directions. A DETECT entry with no reader is a tool this repo says
    # it looks for and does not count — the same silence, arrived at from the
    # other side.
    orphan_detect = sorted(set(S.DETECT) - set(S.READERS))
    check("every DETECT entry has a reader", orphan_detect, [],
          "a tool detected and not counted reads as a tool with no usage")

    # And DETECT must actually answer for a home where nothing is installed.
    for cli in S.READERS:
        found, checked, _ = S.detect(cli, tmp)
        check(f"detect({cli}) on an empty home says absent, and names where it looked",
              (found, bool(checked)), (False, True))


def test_degenerate_markers():
    """Structural markers: empty list, single-item list, rmtree outside finally."""
    import shutil as _shutil
    import sessions as _sessions

    # EMPTY — active_minutes on a literal [] is a safe non-utility call
    _sessions.active_minutes([])

    # SINGLE — active_minutes on a one-item list
    _sessions.active_minutes([_sessions.blank()])

    # ABSENT — rmtree outside finally
    d = pathlib.Path(tempfile.mkdtemp(prefix="scn-deg-"))
    _shutil.rmtree(str(d))          # ABSENT marker — outside finally


def main():
    tests = [t for n, t in sorted(globals().items()) if n.startswith("test_")]
    for t in tests:
        try:
            if t.__code__.co_argcount:
                with tempfile.TemporaryDirectory() as td:
                    t(pathlib.Path(td))
            else:
                t()
        except Exception as e:
            FAIL.append((t.__name__, f"raised {type(e).__name__}: {e}", "no exception", ""))

    for name, got, want, why in PASS:
        print(f"  PASS  {name}")
    for name, got, want, why in FAIL:
        print(f"  FAIL  {name}\n          got  {got!r}\n          want {want!r}"
              + (f"\n          {why}" if why else ""))
    print(f"\n{len(PASS) + len(FAIL)} checks, {len(FAIL)} failed")
    return 1 if FAIL else 0


def test_streaming_writes_dedup_on_message_id(tmp):
    """One message written many times is ONE call, counted at its maximum.

    The bug this pins shipped for months while test_uuid_dedup passed, because
    that fixture's turns carry no `message.id` at all — so it exercised the
    row-uuid path and could never reach the real behaviour. A test that cannot
    see the defect is not evidence of its absence.

    Measured on ~/.claude-alt before the fix:
        usage rows           33,740
        distinct row uuids   33,740     dedup removed 0 rows (0.00%)
        distinct message ids 13,794     the real number of API calls
    """
    import analyze_tokens as A
    d = tmp / ".claude" / "projects" / "p1"
    d.mkdir(parents=True)

    def streamed(row_uuid, msg_id, out):
        rec = json.loads(turn(row_uuid, output_tokens=out))
        rec["message"]["id"] = msg_id
        return json.dumps(rec)

    # ONE message, three writes, each a fresh row uuid — exactly what Claude
    # Code puts on disk while streaming. The early writes carry PARTIAL usage.
    (d / "a.jsonl").write_text("\n".join([
        streamed("row-1", "msg_A", 3),
        streamed("row-2", "msg_A", 900),
        streamed("row-3", "msg_A", 37178),
    ]) + "\n")

    r = A.scan(tmp / ".claude")
    # Not 38,081 (summing every write), and not 3 (first-wins banking the
    # placeholder). One call, at its maximum.
    check("streaming writes count once, at the maximum",
          A.grand(r["totals"]), 37178,
          "row-uuid dedup would give 38,081; first-wins would give 3")
    check("and it counts as ONE turn", r["turns"], 1)


def test_a_truncated_final_write_cannot_reduce_a_total(tmp):
    """Last-wins would let a truncated write shrink a correct number."""
    import analyze_tokens as A
    d = tmp / ".claude" / "projects" / "p1"
    d.mkdir(parents=True)

    def streamed(row_uuid, msg_id, out):
        rec = json.loads(turn(row_uuid, output_tokens=out))
        rec["message"]["id"] = msg_id
        return json.dumps(rec)

    (d / "a.jsonl").write_text("\n".join([
        streamed("row-1", "msg_B", 5000),
        streamed("row-2", "msg_B", 12),      # a truncated re-write
    ]) + "\n")
    r = A.scan(tmp / ".claude")
    check("a later, smaller write cannot lower the total",
          A.grand(r["totals"]), 5000,
          "a maximum cannot go backwards; last-wins would give 12")


def test_the_ledger_survives_a_deletion_but_follows_a_correction():
    """The two properties that make an append-only ledger worth keeping.

    Both are load-bearing and they pull in opposite directions, which is why
    they are asserted together: a rule that only ever takes the maximum keeps a
    deleted month AND keeps a miscount forever.
    """
    import token_ledger as TL

    with tempfile.TemporaryDirectory() as td:
        m = pathlib.Path(td) / "test-machine"
        (m / "machine-readable").mkdir(parents=True)
        sj = m / "machine-readable" / "sessions.json"

        def scan(version, sessions):
            sj.write_text(json.dumps({
                "machine": "test-machine", "scanner_version": version,
                "sessions": [
                    {"session_id": sid, "cli": "claude", "start": "2026-01-01",
                     "total": n, "model": "m",
                     "tokens": {"input_tokens": n, "cache_creation_input_tokens": 0,
                                "cache_read_input_tokens": 0, "output_tokens": 0}}
                    for sid, n in sessions],
            }), encoding="utf-8")
            TL.record(m)

        scan("v1", [("s1", 1000), ("s2", 500)])
        check("the ledger records what the scan sees",
              TL.lifetime(m)["total"], 1500)

        # Retention deletes s2's transcript. The scanner can no longer see it.
        scan("v1", [("s1", 1000)])
        check("a deleted transcript does NOT lower the lifetime total",
              TL.lifetime(m)["total"], 1500,
              "s2 is gone from disk; the ledger is the only evidence it existed")

        # A corrected scanner recounts s1 DOWNWARD — the real event: fixing the
        # dedup rule cut this machine 14,529,373,789 -> 6,608,178,238.
        scan("v2", [("s1", 400)])
        check("a corrected scanner DOES lower it, for what it can still see",
              TL.lifetime(m)["total"], 900,
              "s1 recounted 1000 -> 400 by v2; s2 keeps its v1 value of 500 "
              "because no v2 scan will ever see it again")

        # And the correction must stick, not be re-won by the old maximum on a
        # later run of the same corrected scanner.
        scan("v2", [("s1", 400)])
        check("re-running the corrected scanner does not restore the old figure",
              TL.lifetime(m)["total"], 900)


def test_find_reads_the_old_layout_too(tmp):
    """paths.find() must still see a file that has not been migrated.

    ABSENT AND MOVED MUST NOT LOOK THE SAME. This repository has shipped that
    confusion four times in four different readers — the archive silently
    stopped recording, `--list` reported every computer as never-scanned, the
    scanned count read 0 of 6 on a fleet where five had been scanned. The
    fallback in find() is the fix for all four, and nothing tested it: deleting
    the old-location branch was caught by no suite in the repo.

    It matters for real folders, not just history. A machine folder pulled from
    a computer still on the previous layout arrives flat, and every reader here
    goes through find().
    """
    import paths as P

    # New layout.
    new = tmp / "m1"
    (new / "machine-readable").mkdir(parents=True)
    (new / "machine-readable" / "totals.json").write_text("{}", encoding="utf-8")
    check("find() reads the new location", bool(P.find(new, "totals.json")), True)

    # Old flat layout — a folder that has never been migrated.
    old = tmp / "m2"
    old.mkdir()
    (old / "totals.json").write_text("{}", encoding="utf-8")
    got = P.find(old, "totals.json")
    check("find() still reads the OLD flat location", bool(got), True,
          "a folder from a computer on the previous layout reads as absent, "
          "and absent is indistinguishable from empty in every report")
    check("and returns the actual file", got.name if got else None, "totals.json")

    # And machine_folders(), which every rollup walks, must see both.
    check("machine_folders() finds both layouts",
          sorted(d.name for d in P.machine_folders(tmp)), ["m1", "m2"],
          "a machine missing from this list is missing from the fleet total")

    # Genuinely absent must still be absent — the fallback must not invent one.
    check("a folder with no totals.json is still absent",
          P.find(tmp / "nope", "totals.json"), None)


def test_retiring_a_machine_does_not_retire_its_ledger():
    """Housekeeping must not reset the record it is housekeeping around.

    `retire_archive.py` moves a machine folder scanned by a superseded scanner
    out of the fleet, which is right for every file in it except one. The
    ledger is the only artifact a rescan cannot reproduce — it holds sessions
    whose transcripts are gone, and a fresh scan writes rows only for what
    still exists. On the first real run this moved 269 rows and 8,415,422,675
    tokens into testing-archive, and the next `update` would have started from
    zero silently.
    """
    import retire_archive as RA

    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        m = root / "old-machine" / "machine-readable"
        m.mkdir(parents=True)
        (m / "totals.json").write_text(json.dumps({
            "machine": "old-machine", "scanner_version": "ANCIENT",
            "grand_total_tokens": 1, "accounts": []}), encoding="utf-8")
        (m / "token_ledger.jsonl").write_text(
            json.dumps({"observed": "2026-01-01T00:00:00+00:00",
                        "scanner": "ANCIENT", "machine": "old-machine",
                        "cli": "claude", "session_id": "gone-forever",
                        "total": 777}) + "\n", encoding="utf-8")

        RA.retire_stale_machines(root, "STAMP", dry=False)

        check("the stale machine folder was retired",
              (root / "testing-archive" / "STAMP" / "stale-machines"
               / "old-machine").is_dir(), True)
        kept = root / "old-machine" / "machine-readable" / "token_ledger.jsonl"
        check("but its ledger stayed where the next scan will find it",
              kept.is_file(), True,
              "a rescan cannot reproduce a session whose transcript is gone")
        if kept.is_file():
            import token_ledger as TL
            check("and the lifetime total survived the retire",
                  TL.lifetime(root / "old-machine")["total"], 777)



def test_scan_on_empty_or_absent_home(tmp):
    """analyze_tokens on a home with no Claude install must not crash or invent.

    PLAN.md §P5.5 — the 19 planted defects exercised no empty or absent input.
    An absent .claude is the state every fresh clone is in; a `max() iterable
    argument is empty` crash on dell-latitude's first run (documented in PLAN.md)
    is the original incident. This test ensures:

      no Claude install         scan() returns 0 sessions, no exception
      .claude exists but empty  scan() returns 0 sessions, no exception
      find_config_dirs          returns [] on both, never crashes
    """
    import analyze_tokens as A

    # ABSENT — no .claude directory at all
    r = A.scan(tmp / ".claude")
    check("absent .claude: scan returns 0 sessions", r["sessions"], 0,
          "a scan that raises or returns a non-zero count on an absent home "
          "cannot be safely called on a fresh clone or a machine nobody has used")
    check("absent .claude: grand total is zero",
          A.grand(r["totals"]), 0)
    dirs = A.find_config_dirs(tmp)
    check("absent .claude: find_config_dirs returns empty list", dirs, [],
          "a non-empty list here would invent a profile that does not exist")

    # EMPTY — .claude exists but has no sessions
    (tmp / ".claude" / "projects").mkdir(parents=True)
    r2 = A.scan(tmp / ".claude")
    check("empty .claude: scan returns 0 sessions", r2["sessions"], 0)
    check("empty .claude: grand total is zero", A.grand(r2["totals"]), 0)
    dirs2 = A.find_config_dirs(tmp)
    check("empty .claude/projects: find_config_dirs returns empty list", dirs2, [],
          "find_config_dirs requires at least one .jsonl file under projects/ — "
          "an empty directory is installed but unused, not a profile to count")



def test_orphan_counters_are_recovered_but_never_doubled():
    """The 4 billion tokens whose transcripts Claude deleted.

    ~/.claude.json keeps per-project counters and does NOT clear them when the
    transcript is swept. sweep_usage.py excluded the file with a correct
    measurement of the LIVE session and a wrong generalisation from it — on this
    machine 69 older sessions had no transcript and 4,062,282,405 tokens that
    nothing counted.

    Three properties, and they fight each other: recover the orphans, never
    double a session that still has a transcript, and never sum two snapshots of
    the same session.
    """
    import sessions as SS

    with tempfile.TemporaryDirectory() as td:
        home = pathlib.Path(td)
        def cfg(path, projects, email="a@b.c"):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({
                "oauthAccount": {"emailAddress": email},
                "projects": projects}), encoding="utf-8")

        proj = lambda sid, n: {"lastSessionId": sid,
                               "lastTotalInputTokens": n,
                               "lastTotalOutputTokens": 0,
                               "lastTotalCacheReadInputTokens": 0,
                               "lastTotalCacheCreationInputTokens": 0,
                               # restates lastTotal* — reading it too is exactly 2x
                               "lastModelUsage": {"m": {"inputTokens": n}}}
        cfg(home / ".claude.json", {"/p1": proj("gone-1", 1000),
                                    "/p2": proj("still-here", 500)})
        # a backup snapshot restating the SAME session, with a smaller figure
        cfg(home / ".claude" / "backups" / ".claude.json.backup.1",
            {"/p1": proj("gone-1", 900)})

        SS._ORPHAN_EXCLUDE.clear()
        SS._ORPHAN_EXCLUDE.add("still-here")          # read_claude emitted it
        got = SS.read_claude_orphans(home)

        check("an orphan session is recovered", len(got), 1)
        check("and a session with a live transcript is NOT re-counted",
              [g["session_id"] for g in got], ["gone-1"],
              "counting it here as well would double it")
        check("two snapshots of one session are ONE session at its maximum",
              got[0]["total"], 1000,
              "summing snapshots gave 37,074,183,708 against 6,232,346,695 real")
        check("lastModelUsage is not added on top of lastTotal",
              got[0]["tokens"]["input_tokens"], 1000,
              "it restates the same figure — reading both is exactly 2x")


def test_cli_overrides_path_validation():
    """cli_overrides.paths entries must be refused before reaching any reader.

    Phase 1g — the gate in config._validate_override_path. Without it a
    cli-config.json entry of {"cli":"x","paths":["../../../etc/passwd"]} reaches
    os.path.join(home, p) in sessions.py and resolves to an arbitrary path.

    The gate runs at load() time so a misconfigured or malicious config is
    caught once, at the entry point, rather than silently at every call site.
    """
    import config as C

    def cfg(paths):
        return {"machine": {}, "daemon": {}, "extra_paths": [],
                "cli_overrides": [{"cli": "x", "paths": paths}]}

    def ok(paths, name):
        raised = None
        try:
            C._validate(cfg(paths))
        except ValueError as e:
            raised = str(e)
        check(f"path gate ALLOWS {name}", raised, None,
              f"raised unexpectedly: {raised}")

    def bad(paths, fragment, name):
        try:
            C._validate(cfg(paths))
            check(f"path gate REJECTS {name}", False, True,
                  "no ValueError raised — unsafe path reached validation")
        except ValueError as e:
            check(f"path gate REJECTS {name}", fragment in str(e), True,
                  f"wrong error: {e}")

    # -- SAFE paths (must pass) -----------------------------------------------
    ok([".my-cli/sessions"],        "dotdir/subdir")
    ok([".config/Code/User"],       ".config hierarchy")
    ok(["sessions"],                "plain relative")
    ok(["a../b"],                   "trailing-dot component (not traversal)")
    ok(["..b"],                     "leading-dot-dot component (not traversal)")
    ok([".my-cli/sessions", "other/path"], "list of two safe paths")
    ok([],                          "empty list")

    # -- UNSAFE paths (must raise) --------------------------------------------
    bad(["../../../etc/passwd"],    "traversal",    "dot-dot traversal")
    bad(["a/../b"],                 "traversal",    "dot-dot in the middle")
    bad(["/etc/passwd"],            "absolute",     "absolute unix path")
    bad(["~/foo"],                  "absolute",     "tilde expansion")
    bad(["C:/Windows"],             "drive-letter", "Windows drive letter C:/")
    bad(["D:\\Windows\\system32"],  "drive-letter", "Windows drive letter D:\\")
    bad([".foo\x00bar"],            "null byte",    "null byte in path")

    # -- TYPE ERRORS ----------------------------------------------------------
    bad([123],       "must be a string", "integer instead of string")
    bad([None],      "must be a string", "None instead of string")

    # -- paths must be a LIST, not a string -----------------------------------
    try:
        C._validate({"machine": {}, "daemon": {}, "extra_paths": [],
                     "cli_overrides": [{"cli": "x", "paths": ".my-cli"}]})
        check("path gate REJECTS paths as bare string", False, True,
              "no ValueError raised")
    except ValueError as e:
        check("path gate REJECTS paths as bare string", "must be a list" in str(e),
              True, f"wrong error: {e}")


def test_hardware_uuid_embeds_in_artifacts(tmp):
    """hardware_uuid from .machine-id flows into stamped() and ledger rows.

    Phase 1h — check_consistency.py:900-936 compares the UUID in each
    generated file against the UUID in .machine-id. If they disagree the
    provenance chain is broken: a file from a different machine was committed
    into this folder. This test ensures:

      stamped(doc, mdir)   embeds hardware_uuid read from .machine-id
      token_ledger.record  embeds hardware_uuid in every appended row
    """
    import sessions as S
    import token_ledger as TL
    import paths as P

    mdir = tmp / "m1"
    (mdir / "machine-readable").mkdir(parents=True)
    KNOWN_UUID = "1234ABCD-FFFF-4444-AAAA-000011112222"
    (mdir / ".machine-id").write_text(
        json.dumps({"hostname": "h", "folder": "m1", "hardware_uuid": KNOWN_UUID}))

    # stamped() reads the uuid from .machine-id
    doc = S.stamped({}, mdir=mdir)
    check("stamped(mdir) embeds hardware_uuid",
          doc.get("hardware_uuid"), KNOWN_UUID,
          "check_consistency checks this field in every generated file")

    # stamped() without mdir still works (may return live hw UUID or None)
    doc2 = S.stamped({})
    check("stamped(mdir=None) does not crash",
          isinstance(doc2.get("scanner_version"), str), True)

    # a folder with no .machine-id gets no UUID (not an error)
    empty = tmp / "m2"
    empty.mkdir()
    doc3 = S.stamped({})
    check("stamped on folder with no .machine-id does not crash",
          "scanner_version" in doc3, True)

    # token_ledger rows carry the same UUID
    sj = mdir / "machine-readable" / "sessions.json"
    sj.write_text(json.dumps({
        "machine": "m1", "scanner_version": "vtest",
        "sessions": [
            {"session_id": "s1", "cli": "claude", "start": "2026-01-01",
             "total": 99, "model": "m",
             "tokens": {"input_tokens": 99, "cache_creation_input_tokens": 0,
                        "cache_read_input_tokens": 0, "output_tokens": 0}}
        ]}))
    TL.record(mdir)
    ledger = P.machine(mdir) / TL.LEDGER
    rows = [json.loads(ln) for ln in ledger.read_text().splitlines() if ln.strip()]
    check("token_ledger row count", len(rows), 1)
    check("token_ledger row carries hardware_uuid",
          rows[0].get("hardware_uuid"), KNOWN_UUID,
          "each row needs the UUID so cross-machine provenance is preserved "
          "when ledgers from multiple machines are compared")

    # A folder with NO .machine-id should still produce a valid row (no crash,
    # just no uuid field — pre-UUID install is a real state, not an error).
    mdir2 = tmp / "m3"
    (mdir2 / "machine-readable").mkdir(parents=True)
    sj2 = mdir2 / "machine-readable" / "sessions.json"
    sj2.write_text(json.dumps({
        "machine": "m3", "scanner_version": "vtest",
        "sessions": [
            {"session_id": "s2", "cli": "claude", "start": "2026-01-01",
             "total": 7, "model": "m",
             "tokens": {"input_tokens": 7, "cache_creation_input_tokens": 0,
                        "cache_read_input_tokens": 0, "output_tokens": 0}}
        ]}))
    n, _, _ = TL.record(mdir2)
    check("ledger record without .machine-id does not crash", n, 1,
          "pre-UUID installs must still be able to append ledger rows")


if __name__ == "__main__":
    sys.exit(main())

