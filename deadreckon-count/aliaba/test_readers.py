#!/usr/bin/env python3
"""One fixture per reader in sessions.py, each asserting a known total.

    python3 test_readers.py

WHY THIS FILE EXISTS

Nothing in this repository executed a `sessions.py` reader. Six deliberate
breaks planted in `read_claude` — drop the streaming sum, drop either dedup,
read only the first profile, glob flat instead of recursively — every one of
them scored 45 checks, 0 failed. `read_copilot -> return []` scored 45/0 too.
And `update.py` runs that suite as a pre-scan release gate whose own comment
says it is there to catch a silently-wrong reader.

`test_scanner.py` covers `analyze_tokens.py`, which is a SECOND implementation
of Claude Code counting. The two are cross-checked against each other, and that
cross-check is the thing most likely to be quietly wrong: both flatten the
project glob identically, so a subagent transcript at depth 3 is invisible to
both and they agree perfectly about the wrong number. 4,224,787,878 tokens —
18.23% of this machine — live at that depth.

So every reader here gets a fixture built to its documented shape, with a total
worked out by hand in the docstring, plus the specific trap that reader's
docstring says it exists to avoid. A reader that returns [] fails. A reader that
stops deduplicating fails. A reader that sums the bookkeeping fields fails.

WHAT A FIXTURE IS NOT

It is not a claim about what the tool writes today. Formats drift, and a fixture
frozen against a format nobody writes any more passes forever while the reader
reads nothing. That is what `sessions.py`'s own `detect()` and the NOT SCANNED
row in `count_corpus.py` are for. This file answers a narrower question: given
input of the shape the reader documents, does it compute the number it claims.
"""

import collections
import json
import os
import pathlib
import shutil
import sys
import tempfile
import urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sessions                                                    # noqa: E402
import stores                                                      # noqa: E402

PASS, FAIL = [], []


def check(name, got, want, why=""):
    (PASS if got == want else FAIL).append((name, got, want, why))


def total(recs):
    return sum(sum(r["tokens"][k] for k in sessions.FIELDS) for r in recs or [])


def w(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text if isinstance(text, str) else json.dumps(text),
                 encoding="utf-8")


# --------------------------------------------------------------------- claude
def claude_row(uuid, mid, **usage):
    """One assistant row as Claude Code writes it.

    `mid=None` omits message.id entirely, which is a real shape and a different
    code path: those rows can only be deduplicated on the row uuid, and that is
    what `seen_uuid` is for.
    """
    u = dict.fromkeys(sessions.FIELDS, 0)
    u.update(usage)
    msg = {"role": "assistant", "model": "claude-opus-4-6", "usage": u}
    if mid is not None:
        msg["id"] = mid
    return json.dumps({
        "uuid": uuid, "timestamp": "2026-07-01T10:00:00.000Z",
        "sessionId": "s1", "type": "assistant", "message": msg})


def t_claude(home):
    """4 fields summed once per message.id, across profiles, at any depth.

    Rows:
      m1 twice (two streaming chunks, DIFFERENT uuid, SAME message.id)  -> 100
      m2 once                                                           ->  10
      m3 once, in a SUBAGENT transcript one directory deeper            ->   7
      NO message.id, uuid u5                                            ->   5
      m1 again in a SECOND profile (a copied ~/.claude-alt)             ->   0
      the SAME id-less row u5 again in that second profile              ->   0
      m4, UNIQUE to that second profile                                 ->  13
    Total 135.

    m4 is why the second profile is more than a copy. Without it that profile
    held duplicates only, so reading just the first one — `find_config_dirs(
    home)[:1]`, the break that loses every profile outside ~/.claude — changed
    the total by nothing and the suite passed. A fixture where discovery does
    not matter cannot test discovery.

    The two dedups are different code paths and each needs its own duplicate.
    A row WITH message.id is deduplicated on that id; a row WITHOUT one can
    only be deduplicated on the row uuid, which is what `seen_uuid` does. The
    first version of this fixture used id-carrying rows only, so deleting
    `seen_uuid.add(uuid)` changed nothing and the suite passed — the exact
    shape of blindness this file was written to end.

    Every wrong answer is a different break:
      235 = message.id dedup gone     140 = seen_uuid (id-less) dedup gone
      128 = the nested file not found 122 = only the first profile read
      135 = correct
    """
    p1 = home / ".claude" / "projects" / "proj"
    w(p1 / "a.jsonl", claude_row("u1", "m1", output_tokens=100) + "\n"
                      + claude_row("u2", "m1", output_tokens=100) + "\n"
                      + claude_row("u3", "m2", output_tokens=10) + "\n"
                      + claude_row("u5", None, output_tokens=5) + "\n")
    # Depth 3. A flat glob of projects/*/*.jsonl never sees this one, and the
    # fixture is the only thing standing between that and a silent 18% loss.
    w(p1 / "subagents" / "sub.jsonl", claude_row("u4", "m3", output_tokens=7) + "\n")
    p2 = home / ".claude-alt" / "projects" / "proj"
    w(p2 / "a.jsonl", claude_row("u9", "m1", output_tokens=100) + "\n"
                      + claude_row("u5", None, output_tokens=5) + "\n"
                      + claude_row("u6", "m4", output_tokens=13) + "\n")

    recs = sessions.read_claude(home)
    check("claude: both dedups hold across profiles and depth", total(recs), 135,
          "235 means the message.id dedup is gone; 140 means seen_uuid is gone; "
          "128 means the nested subagent transcript was never found; "
          "122 means only the first profile was read")
    check("claude: found sessions at all", bool(recs), True)


# -------------------------------------------------------------------- copilot
def t_copilot(home):
    """session.shutdown modelMetrics. reasoningTokens sits BESIDE outputTokens.

    input 5 + output 3 + reasoning 2 + cacheRead 7 + cacheWrite 1 = 18.
    A reader that drops reasoningTokens returns 16.
    """
    base = home / ".copilot" / "session-state"
    w(base / "sess1.jsonl", json.dumps({
        "timestamp": "2026-07-01T10:00:00Z", "type": "session.shutdown",
        "data": {"modelMetrics": {"gpt-5": {"usage": {
            "inputTokens": 5, "outputTokens": 3, "reasoningTokens": 2,
            "cacheReadTokens": 7, "cacheWriteTokens": 1}}}}}) + "\n")
    recs = sessions.read_copilot(home)
    check("copilot: reasoningTokens counted beside outputTokens", total(recs), 18,
          "16 means reasoning tokens were dropped")


# ---------------------------------------------------------------------- codex
def t_codex(home):
    """last_token_usage, never total_token_usage; cached_input is INSIDE input.

    input 100 of which 40 cached, output 9  ->  60 + 40 + 9 = 109.
    total_token_usage restates a running total and is 40.7x here if summed.
    """
    base = home / ".codex" / "sessions"
    w(base / "rollout-2026-07-01.jsonl", "\n".join([
        json.dumps({"timestamp": "2026-07-01T10:00:00Z", "type": "token_count",
                    "payload": {"type": "token_count", "info": {
                        "last_token_usage": {"input_tokens": 100,
                                             "cached_input_tokens": 40,
                                             "output_tokens": 9},
                        "total_token_usage": {"input_tokens": 999999,
                                              "output_tokens": 999999}}}}),
    ]) + "\n")
    recs = sessions.read_codex(home)
    check("codex: last_token_usage, and cached is inside input", total(recs), 109,
          "a much larger number means total_token_usage was summed")


# --------------------------------------------------------------------- gemini
def t_gemini(home):
    """tokens.{input,cached,output,thoughts,tool}; cached is INSIDE input.

    input 50 (20 cached) + tool 5 + output 8 + thoughts 4
      = (50-20) + 20 + 5 + 8 + 4 = 67
    """
    base = home / ".gemini" / "tmp" / "abc"
    w(base / "chats" / "session-1.json", {
        "sessionId": "g1", "projectHash": "abc", "messages": [
            {"timestamp": "2026-07-01T10:00:00Z",
             "tokens": {"input": 50, "cached": 20, "output": 8,
                        "thoughts": 4, "tool": 5}}]})
    recs = sessions.read_gemini(home)
    check("gemini: thoughts and tool counted, cached not double-counted",
          total(recs), 67, "87 means cached was added on top of input")


# ----------------------------------------------------------------------- grok
def t_grok(home):
    """<url-encoded-cwd>/<id>/updates.jsonl; turn_completed only.

    input 30 (10 cached) + output 6 = 20 + 10 + 6 = 36.
    The usage_snapshot row beside it carries the SAME field names mid-turn, so
    a reader that counts both returns 72 — and _meta.totalTokens is a running
    context counter, not usage, worth 999999 if swallowed.
    """
    base = home / ".grok" / "sessions"
    d = base / "ws" / "s1"
    usage = {"modelUsage": {"grok-4": {"inputTokens": 30, "cachedReadTokens": 10,
                                       "outputTokens": 6}}}
    w(d / "updates.jsonl", "\n".join([
        json.dumps({"timestamp": "2026-07-01T10:00:00Z",
                    "params": {"_meta": {"totalTokens": 999999},
                               "update": {"sessionUpdate": "usage_snapshot",
                                          "usage": usage}}}),
        json.dumps({"timestamp": "2026-07-01T10:00:01Z",
                    "params": {"_meta": {"totalTokens": 999999},
                               "update": {"sessionUpdate": "turn_completed",
                                          "usage": usage}}}),
    ]) + "\n")
    recs = sessions.read_grok(home)
    check("grok: turn_completed only, and cachedReadTokens is inside input",
          total(recs), 36,
          "72 means the mid-turn usage_snapshot was counted too; 46 means "
          "cached was added on top of input")


# ------------------------------------------------------------------ lm studio
def t_lmstudio(home):
    """messages[].versions[].steps[].genInfo.stats — prompt + predicted = 12."""
    base = home / ".lmstudio" / "conversations"
    w(base / "1751385600000.json", {
        "messages": [{"versions": [{"steps": [{"genInfo": {
            "indexedModelIdentifier": "qwen",
            "stats": {"promptTokensCount": 9, "predictedTokensCount": 3}}}]}]}]})
    recs = sessions.read_lmstudio(home)
    check("lmstudio: prompt + predicted", total(recs), 12)


# ----------------------------------------------------------------- clawspring
def t_clawspring(home):
    """daily/session_*.json rollups. history.json is a 20/20 restatement of these.

    total_input 40 + total_output 6 = 46. Reading history.json too doubles it.
    """
    sess = home / ".clawspring" / "sessions"
    w(sess / "daily" / "session_a.json",
      {"session_id": "c1", "turn_count": 3,
       "total_input_tokens": 40, "total_output_tokens": 6,
       "saved_at": "2026-07-01T10:00:00Z"})
    # The rollup that must NOT be read, at the store root rather than under
    # daily/. Two earlier versions of this decoy were both un-catchable:
    #   {"sessions": [...]}   no top-level total_input_tokens, so the reader
    #                         skipped it on SHAPE however wide the glob got
    #   session_id "c1"       same id as the daily file, so multi_base's own
    #                         session_id dedup dropped it before it counted
    # The second is a real guard doing its job, which is why the id here is
    # different: this check is about the glob boundary, and the decorator's
    # dedup already covers the same-id case. A decoy that another layer
    # neutralises tests that layer, not this one.
    w(sess / "session_rollup.json",
      {"session_id": "c2", "turn_count": 3,
       "total_input_tokens": 40, "total_output_tokens": 6,
       "saved_at": "2026-07-01T10:00:00Z"})
    recs = sessions.read_clawspring(home)
    check("clawspring: daily/ only, the rollup beside it is not counted twice",
          total(recs), 46, "92 means the store-root rollup was read as well")


# --------------------------------------------------------------- copilot chat
def t_copilot_chat(home):
    """requests[].result.metadata.toolCallRounds[].thinking.tokens.

    Two rounds, 64 + 128 = 192, banked as reasoning. The context-window
    advertisement beside it (maxInputTokens) is bookkeeping and gives 10.4x if
    summed, so a reader that finds 1,000,192 has swallowed it.
    """
    ws = home / ".config" / "Code" / "User" / "workspaceStorage" / "abc123"
    w(ws / "chatSessions" / "s.json", {
        "requests": [{
            "result": {"metadata": {"toolCallRounds": [
                {"thinking": {"id": "t1", "tokens": 64}},
                {"thinking": {"id": "t2", "tokens": 128}}]}}}],
        "inputState": {"selectedModel": {"metadata": {
            "maxInputTokens": 1000000, "maxOutputTokens": 64000}}}})
    recs = sessions.read_copilot_chat(home)
    check("copilot-chat: thinking.tokens only, not the context-window ads",
          total(recs), 192,
          "anything near a million means maxInputTokens was summed")


# ------------------------------------------------------------------- kilocode
def t_kilocode(home):
    """api_req_started rows. tokensIn ALREADY INCLUDES cacheReads/cacheWrites.

    tokensIn 100, cacheReads 30, cacheWrites 20, tokensOut 7
      -> uncached 50 + 30 + 20 + 7 = 107.  Adding them on top gives 157.
    """
    tasks = (home / ".config" / "Code" / "User" / "globalStorage"
             / "kilocode.kilo-code" / "tasks" / "task1")
    w(tasks / "ui_messages.json", [
        {"ts": 1751385600000, "say": "api_req_started",
         "text": json.dumps({"tokensIn": 100, "cacheReads": 30,
                             "cacheWrites": 20, "tokensOut": 7,
                             "inferenceProvider": "xai"})}])
    recs = sessions.read_kilocode(home)
    check("kilocode: tokensIn already includes the cache figures",
          total(recs), 107, "157 means cacheReads/cacheWrites were added on top")


# -------------------------------------------------------- every reader at all
def t_no_reader_silently_returns_nothing(home):
    """The break that scored 45/0: a reader replaced by `return []`.

    Not a format question — a wiring one. Every reader with a fixture above must
    have produced at least one record, and this asserts that as a set so a new
    reader added without a fixture is visible rather than assumed.

    FIX-PLAN #5: `set(READERS) - set(fixtured)` is `[]` when `READERS` is `{}`,
    and the per-reader checks are generated by iterating READERS — so losing ALL
    readers deletes the assertions rather than failing them.  The floor catches
    the empty case that both set-difference checks miss.
    """
    fixtured = {"claude", "copilot", "codex", "gemini", "grok", "lmstudio",
                "clawspring", "copilot-chat", "kilocode", "bob"}
    known = set(sessions.READERS)
    READER_FLOOR = 10         # fixtured set size; must equal len(fixtured)
    check("READERS has at least the expected number of entries",
          len(known) >= READER_FLOOR, True,
          f"expected >= {READER_FLOOR}, got {len(known)} — an empty registry "
          f"makes the two set-difference checks both pass vacuously")
    check("every fixtured reader is a real registered reader",
          sorted(fixtured - known), [],
          "a fixture naming a reader that does not exist tests nothing")
    missing = sorted(known - fixtured - {"antigravity", "claude-orphans"})
    check("no registered reader is left without a fixture", missing, [],
          "antigravity is SQLite+encrypted protobuf and claude-orphans reads "
          ".claude.json; both are exercised elsewhere, everything else needs one")


def t_sessions_total_counts_all_fields(home):
    """FIX-PLAN #7: sessions.total() had no assertion.

    Drop cache_read_input_tokens (95.23% of the fleet) and 45 checks still pass.
    The helper in this file bypasses sessions.total() and sums fields directly,
    so it would not catch that regression. This calls sessions.total() explicitly
    on a record with a known value in every field.
    """
    tok = {"input_tokens": 10, "cache_creation_input_tokens": 3,
           "cache_read_input_tokens": 200, "output_tokens": 7}
    t = sessions.total(tok)
    check("sessions.total() sums all four fields", t, 220,
          "210 means cache_read_input_tokens was dropped; "
          "17 means only input+output were summed; "
          "220 is input(10)+cache_create(3)+cache_read(200)+output(7)")
    check("sessions.total() and FIELDS are consistent",
          sessions.total(dict.fromkeys(sessions.FIELDS, 1)), len(sessions.FIELDS),
          "4 fields -> total of 4; a field added to FIELDS but not summed "
          "or a field summed but not in FIELDS produces a wrong number here")


# ------------------------------------------------- what must never be copied
def t_config_is_never_exported(home):
    """No store marked preserve=False may reach the corpus. Run the real thing.

    This class has escaped the filename rule TWICE. `~/.gemini/oauth_creds.json`
    got in from archive residue, which is why NEVER_EXPORT was made to apply at
    every depth rather than only at a store root. Then `~/.claude.json` got in
    anyway, because NEVER_EXPORT matches names — `config`, `credentials`,
    `auth` — and `.claude.json` is none of them. It carried oauthAccount,
    organizationUuid, userID and machineID into corpus/tools/claude-config/.

    So this does not test the regex. It builds a home containing exactly the
    files that leaked, runs `export_tools`, and asserts the output holds none of
    them — a question about what is on disk after an export, which is the only
    question that would have caught either one.
    """
    import export_corpus as E

    (home / ".claude.json").write_text(json.dumps({
        "oauthAccount": {"emailAddress": "a@b.c", "accountUuid": "u"},
        "userID": "deadbeef" * 8, "machineID": "cafe" * 16,
        "projects": {"/w": {"lastCost": 1}}}), encoding="utf-8")
    w(home / ".claude-alt" / ".claude.json", {"oauthAccount": {"emailAddress": "d@e.f"}})
    # A real record beside them, so a pass cannot come from exporting nothing.
    w(home / ".lmstudio" / "conversations" / "1751385600000.json", {
        "messages": [{"versions": [{"steps": [{"genInfo": {
            "stats": {"promptTokensCount": 9, "predictedTokensCount": 3}}}]}]}]})

    out = home / "out"
    red = E.Redactor(home, keep_email=None)
    E.export_tools(out, home, None, red)

    got = sorted(p.name for p in out.rglob("*") if p.is_file())
    check("no .claude.json is ever exported",
          [n for n in got if n == ".claude.json"], [],
          "config carrying oauthAccount/userID/machineID reached the corpus")
    check("the export still produced the real record", bool(got), True,
          "an empty export would pass the check above for the wrong reason")

    for s in stores.STORES:
        if not s.preserve:
            check(f"stores: {s.label} says why it is not preserved",
                  bool(s.no_preserve_because), True,
                  "a store excluded without a reason is indistinguishable "
                  "from one excluded by accident")


def t_vscode_paths_follow_the_platform(home):
    """A VS Code store must expand to where THAT platform keeps it.

    Eight store paths hardcoded `.config/Code`, sessions.vscode_roots() kept a
    second copy of the platform branch, and read_copilot_chat's @multi_base
    held four more literals. On macOS they disagreed by construction:
    kilocode was counted and preserved nowhere, copilot-chat was a zero on
    both sides. macbook-air-m1 is in the fleet, so it was live.

    Nothing tested the fix. Deleting the darwin branch from vscode_bases() was
    caught by no suite at all — this is that break, frozen.

    `vscode_bases()` reads sys.platform when CALLED, so patching it here is
    honest for the store map. The reader decorators freeze their bases at
    import, which is correct on a real Mac and is why the reader side is
    checked by importing under a patched platform instead (see the commit).
    """
    real = stores.sys.platform
    try:
        stores.sys.platform = "darwin"
        mac = stores.BY_LABEL["copilot-chat"].rel_paths()
        check("darwin expands to Library/Application Support",
              any(p.startswith("Library/Application Support/") for p in mac), True,
              f"got {mac} — a Mac would find no VS Code store at all")
        check("and keeps .config as a fallback", any(p.startswith(".config/") for p in mac),
              True, "a Mac with VS Code installed under .config must still be read")

        # And it must actually RESOLVE there, which is what the archiver asks.
        d = home / "Library/Application Support/Code/User/workspaceStorage/ws"
        d.mkdir(parents=True)
        got = stores.resolve(stores.BY_LABEL["copilot-chat"], str(home))
        check("a macOS store resolves under Library/Application Support",
              bool(got), True,
              "resolve() returning [] is how it was counted and never preserved")

        stores.sys.platform = "linux"
        lin = stores.BY_LABEL["copilot-chat"].rel_paths()
        check("linux expands to .config only", lin, [".config/Code/User/workspaceStorage"],
              "an extra base on Linux means the archiver walks a path that "
              "cannot exist, every run")
    finally:
        stores.sys.platform = real


def t_a_lone_surrogate_does_not_abort_the_export(home):
    """One unencodable character must not cost the whole run.

    JSON permits an unpaired \\udXXX escape and json.loads turns it into a real
    lone surrogate, which has no UTF-8 encoding. Three of them in 2.29 GB threw

        UnicodeEncodeError: 'utf-8' codec can't encode character '\\udc80'

    out of export_tools, and because run.py calls the exporter through sh(),
    which raises SystemExit on a non-zero return, the whole update aborted —
    no corpus, no ledger record. An hour of export was thrown away twice.

    Reading with errors="replace" does NOT prevent this: that handles bad bytes
    arriving, and these arrive as a well-formed escape.
    """
    import export_corpus as E

    # RAW JSON TEXT, not json.dumps of a Python string. The first version of
    # this fixture built the document with json.dumps, which escapes the
    # backslash — the file then held `\\udc80`, json.loads read it back as six
    # ordinary characters, and no surrogate ever reached the writer. The check
    # passed because nothing was wrong, which is the exact failure this file
    # was written to end. Caught by planting the break and watching nothing
    # happen.
    #
    # A JSON escape is the only way this arrives in practice: the bytes on disk
    # are valid UTF-8, so errors="replace" on the way in cannot help.
    raw = ('{"messages": [{"versions": [{"steps": [{"genInfo": '
           '{"stats": {"promptTokensCount": 9, "predictedTokensCount": 3}, '
           '"note": "- \\udc80 Intelligent Node Killer"}}]}]}]}')
    w(home / ".lmstudio" / "conversations" / "1751385600000.json", raw)
    reread = json.loads((home / ".lmstudio" / "conversations"
                         / "1751385600000.json").read_text(encoding="utf-8"))
    check("the fixture really does hold a lone surrogate",
          any(0xD800 <= ord(c) <= 0xDFFF
              for c in json.dumps(reread, ensure_ascii=False)), True,
          "without one, every assertion below passes for the wrong reason")

    out = home / "out"
    try:
        E.export_tools(out, home, None, E.Redactor(home, keep_email=None))
        raised = None
    except UnicodeEncodeError as e:                                # noqa: BLE001
        raised = str(e)
    check("an unpaired surrogate does not abort the export", raised, None,
          "one bad character costs the entire run, not one file")

    files = [p for p in out.rglob("*") if p.is_file()]
    check("and the file was still written", bool(files), True)
    for p in files:
        try:
            p.read_text(encoding="utf-8")
            ok = True
        except UnicodeDecodeError:
            ok = False
        check(f"and {p.name} is valid UTF-8 on disk", ok, True,
              "a corpus that cannot be read back is not a record")

    # The repair is COUNTED, not silent — a record that quietly edits itself
    # is worth less than one that says where it was damaged.
    clean, n = E._no_lone_surrogates("a\udc80b")
    check("the replacement is counted", n, 1)
    check("and a VALID surrogate pair is left alone",
          E._no_lone_surrogates("emoji \U0001F600")[1], 0,
          "replacing real emoji would corrupt every transcript that has one")


def t_every_transcript_the_readers_count_is_also_exported(home):
    """What the counters COUNT, the exporter must PRESERVE. Run the real thing.

    export_corpus.py exported `proj.glob("*.jsonl")` — flat — while every
    reader in this repo walks `rglob`. Subagent and workflow transcripts live
    at projects/<proj>/<session-uuid>/subagents/agent-*.jsonl and
    .../subagents/workflows/wf_*/agent-*.jsonl, so they were counted in every
    total and copied nowhere. Measured before the fix: 5,896 of 8,675 live
    transcripts exported, 68.0%; in .claude-alt, the profile in daily use, 30
    of 909 — 3.3%. 577 files with no copy under ~/deadreckon-record at all,
    124,692,204 bytes, 588,728,384 tokens, one cleanupPeriodDays launch from
    being gone for good.

    That was the FOURTH copy of this glob. sessions.py, count_corpus.py and
    corpus_reports.py were fixed on 2026-08-09 and this one was missed, so the
    check here is deliberately not "does the source say rglob". It builds a
    home, runs `export_corpus.main()`, and asks the only question that would
    have caught it: is every transcript that went in still on disk afterwards.

    The second half is the trap the obvious fix walks into. Recursing and then
    writing `f.name` collides: 111 files on this machine share a basename with
    another file in the SAME project, because agent-*.jsonl repeats across
    sessions. That version walks the whole tree and then silently overwrites
    111 of what it walked — the same loss, one layer further in — and a test
    that only counted output files would call it fixed. So the two agent
    records below share a basename and differ only in uuid, and both uuids are
    asserted present.
    """
    import export_corpus as E

    sid = "5b7c79c7-283a-439e-99e6-944194ecf4c3"
    proj = home / ".claude" / "projects" / "-w-proj"

    def rec(u):
        return json.dumps({"uuid": u, "sessionId": sid, "type": "assistant",
                           "timestamp": "2026-08-09T00:00:00Z",
                           "message": {"id": "msg_" + u, "model": "claude-opus-5",
                                       "usage": {"input_tokens": 10, "output_tokens": 5}}})

    # Depth 0, the only one the flat glob ever saw.
    w(proj / "main.jsonl", rec("u-root"))
    # Depth 2 and depth 4, SAME basename — a subagent and the workflow agent
    # beneath it. This is the shape actually on disk: 615 files at depth 2 and
    # 2,164 under subagents/workflows/wf_*/ across 23 profiles.
    w(proj / sid / "subagents" / "agent-a40ff046.jsonl", rec("u-subagent"))
    w(proj / sid / "subagents" / "workflows" / "wf_cbc5d1d2"
      / "agent-a40ff046.jsonl", rec("u-workflow"))

    nested = [p for p in proj.rglob("*.jsonl") if p.parent != proj]
    check("the fixture really does hold nested transcripts", len(nested), 2,
          "with none, a flat glob exports everything and this passes for the "
          "wrong reason")
    check("and two of them share a basename",
          len({p.name for p in nested}), 1,
          "without the collision, rglob + f.name looks correct")

    out = home / "out"
    argv = sys.argv
    try:
        sys.argv = ["export_corpus.py", "--home", str(home), "--out", str(out),
                    "--keep-email", "", "--archive", "", "--archive-other", ""]
        E.main()
    finally:
        sys.argv = argv

    got = sorted(p for p in (out / ".claude" / "projects").rglob("*.jsonl"))
    check("every transcript on disk is exported, not just the top level",
          len(got), 3,
          "the flat glob exports 1 of 3 — subagent and workflow transcripts "
          "are counted by every reader and preserved by nothing")

    uuids = {json.loads(ln)["uuid"]
             for p in got for ln in p.read_text(encoding="utf-8").splitlines() if ln}
    check("and no two of them overwrote each other", sorted(uuids),
          ["u-root", "u-subagent", "u-workflow"],
          "rglob with f.name silently drops the 111 same-named agent files")

    # The consuming tool reads projects/<proj>/*.jsonl and nothing deeper, so
    # depth is folded into the name rather than reproduced on disk.
    check("the corpus stays exactly two levels deep",
          sorted({str(p.relative_to(out / ".claude" / "projects")).count("/")
                  for p in got}), [1],
          "a nested corpus reads as empty to the tool it is exported for")
    check("and the depth-0 file keeps its exact name",
          "main.jsonl" in {p.name for p in got}, True,
          "renaming the 5,896 already in the corpus would churn all of it")


def _run_export(home):
    """Run the real exporter over `home` and hand back what a consumer sees."""
    import export_corpus as E

    out = home / "out"
    argv = sys.argv
    try:
        sys.argv = ["export_corpus.py", "--home", str(home), "--out", str(out),
                    "--keep-email", "", "--archive", "", "--archive-other", ""]
        E.main()
    finally:
        sys.argv = argv

    dst = out / ".claude" / "projects"
    got = sorted(dst.rglob("*.jsonl"))
    man = json.loads((out / "machine-readable" / "MANIFEST.json").read_text())
    # Real project names identify private repositories, so the output directory
    # is -workspace-pNNN and only the manifest knows which one is which.
    renamed = {m["source_project"]: m["exported_as"] for m in man["mapping"]}
    by_proj = {}
    for f in got:
        by_proj.setdefault(f.parent.name, []).append(f)
    return dst, got, man, renamed, by_proj


def _rec(u=None):
    o = {"sessionId": "s", "type": "assistant",
         "timestamp": "2026-08-09T00:00:00Z",
         "message": {"id": "msg", "model": "claude-opus-5",
                     "usage": {"input_tokens": 10, "output_tokens": 5}}}
    if u:
        o["uuid"] = u
        o["message"]["id"] = "msg_" + u
    return json.dumps(o)


def t_a_folded_name_can_never_exceed_name_max(home):
    """The crash the fold above introduced, and the collision a naive cut brings.

    `f.name` could not break NAME_MAX: it came OFF a filesystem and was bounded
    by construction. `"__".join(rel.parts)` is a name INVENTED here, and its
    length is the sum of every component on the path. Two legal 120-byte
    directories and a 20-byte file make a legal path and a 264-byte filename:

        OSError: [Errno 36] File name too long

    uncaught, mid-export, so one long path anywhere kills the whole corpus and
    not just the file that carries it.

    Truncation alone stops the crash and destroys the thing the fold was FOR.
    The two deep files here are byte-identical for their first 113 bytes and
    differ only at byte 119 — past any cut that fits in 255 — so a cut with no
    hash silently overwrites one with the other, which is the same data loss the
    fold was introduced to prevent. Both uuids are asserted, not just the file
    count, because two files with one uuid between them looks fine from outside.

    Bounded AND injective, or it is not fixed.
    """
    nm = home / ".claude" / "projects" / "-w-namemax"
    d1, d2, d3 = "a" * 120, "b" * 118 + "01", "b" * 118 + "02"
    w(nm / "main.jsonl", _rec("u-nm-root"))
    w(nm / d1 / d2 / "agent-a40ff046.jsonl", _rec("u-nm-deep-1"))
    w(nm / d1 / d3 / "agent-a40ff046.jsonl", _rec("u-nm-deep-2"))

    parts = (nm / d1 / d2 / "agent-a40ff046.jsonl").relative_to(nm).parts
    check("every component of the fixture path is a legal filename",
          max(len(x.encode()) for x in parts) <= 255, True,
          "a fixture the filesystem would itself refuse proves nothing")
    check("and the name the exporter folds them into is not",
          len("__".join(parts).encode()) > 255, True,
          "under the limit there is nothing here to crash on")
    check("and the two deep paths are identical past any cut that fits",
          "__".join(parts)[:235] == "__".join(
              (nm / d1 / d3 / "agent-a40ff046.jsonl").relative_to(nm).parts)[:235],
          True, "if they differed early, truncation alone would look correct")

    dst, got, man, renamed, by_proj = _run_export(home)   # raises OSError 36
    limit = min(int(os.pathconf(str(dst), "PC_NAME_MAX")), 255)
    check("no output name exceeds the destination's NAME_MAX",
          [f.name for f in got if len(f.name.encode()) > limit], [],
          "a name the exporter invents is not bounded by the filesystem the "
          "source came off")
    check("the long-path project exports all three of its transcripts",
          len(by_proj[renamed["-w-namemax"]]), 3,
          "OSError 36 on one file aborts the whole run")

    uuids = sorted(json.loads(ln)["uuid"]
                   for f in got
                   for ln in f.read_text(encoding="utf-8").splitlines()
                   if ln and "uuid" in json.loads(ln))
    check("and no two of them were folded onto one name",
          uuids, ["u-nm-deep-1", "u-nm-deep-2", "u-nm-root"],
          "a cut with no hash overwrites one deep file with the other")
    check("the corpus stays exactly two levels deep",
          sorted({str(f.relative_to(dst)).count("/") for f in got}), [1],
          "a nested corpus reads as empty to the tool it is exported for")


def t_a_transcript_that_exists_is_never_dropped(home):
    """Walked, read, redacted, written nowhere — and the rule that fixes it.

    The writer was guarded by `if lines:` against a row-level dedup that spans
    every file in every profile, so a transcript whose every row had already
    been claimed by a file read earlier produced an empty list and was never
    written. The shape here is a resumed session: Claude Code rewrites earlier
    turns into a NEW depth-0 file, and one hex digit decides whether that file
    sorts before the older session's directory. Measured on this machine, after
    the inode rule below has taken the hard links out of the count: 1,482
    distinct transcripts, 435,152,279 bytes, dropped on the floor.

    The decision the exporter now states out loud is that a file's EXISTENCE and
    its CONTENT are different facts and only one of them can be shared. So both
    halves are asserted: the nested transcript is THERE, and the row it shares
    with the resumed file is still in the corpus exactly ONCE.

    The second half of the fixture is the rule that makes the first half
    affordable — export_tools' (st_dev, st_ino) dedup, imported whole. These two
    files are one inode under two names, and their rows carry no uuid, which is
    a real shape and the only one that proves the inode rule is doing the work:
    there is nothing for the row dedup to match on, so without it the same bytes
    are written twice under two names. With existence alone now earning a file
    in the corpus, the alternative is 10,312 empty ones on this machine.
    """
    projects = home / ".claude" / "projects"

    rs = projects / "-w-resumed"
    old = "bbbb79c7-283a-439e-99e6-944194ecf4c3"
    w(rs / "aaaa-resumed.jsonl",
      "\n".join([_rec("u-rs-root"), _rec("u-rs-sub-1"), _rec("u-rs-sub-2")]))
    w(rs / old / "subagents" / "agent-a40ff046.jsonl",
      "\n".join([_rec("u-rs-sub-1"), _rec("u-rs-sub-2")]))
    check("the resumed file really is read before the nested one",
          [f.relative_to(rs).parts[0] for f in sorted(rs.rglob("*.jsonl"))],
          ["aaaa-resumed.jsonl", old],
          "read the other way round the nested file claims the rows first and "
          "the drop never happens")

    hl = projects / "-w-hardlink"
    w(hl / "dup-a.jsonl", "\n".join([_rec(), _rec()]))
    os.link(hl / "dup-a.jsonl", hl / "dup-b.jsonl")
    check("and the hard-link fixture is one inode under two names",
          (hl / "dup-a.jsonl").stat().st_ino == (hl / "dup-b.jsonl").stat().st_ino,
          True, "two inodes are two transcripts and the rule does not apply")

    dst, got, man, renamed, by_proj = _run_export(home)

    rs_out = sorted(f.name for f in by_proj[renamed["-w-resumed"]])
    check("the transcript whose every row was seen elsewhere is still exported",
          len(rs_out), 2,
          "`if lines:` walks it, reads it, redacts it and writes nothing")
    check("it is the nested one that survived, under its folded name",
          [n for n in rs_out if n.startswith(old)],
          [f"{old}__subagents__agent-a40ff046.jsonl"], "")
    check("and it is empty — existence preserved, rows not duplicated",
          [(dst / renamed["-w-resumed"] / n).stat().st_size
           for n in rs_out if n.startswith(old)], [0],
          "writing its rows again double-counts every one of them")

    uuids = collections.Counter(
        json.loads(ln)["uuid"] for f in got
        for ln in f.read_text(encoding="utf-8").splitlines()
        if ln and "uuid" in json.loads(ln))
    check("so the shared row is in the corpus exactly once",
          uuids["u-rs-sub-1"], 1,
          "the point of the row dedup is that a total taken over this corpus "
          "is honest")

    check("one inode under two names is exported once, not twice",
          len(by_proj[renamed["-w-hardlink"]]), 1,
          "rows with no uuid have nothing to dedup on, so without the inode "
          "rule the archive's hard links are written again under a second name")
    check("and the manifest says what was skipped and what came out empty",
          (man["hard_links_skipped"], man["files_without_a_unique_row"]), (1, 1),
          "a corpus that quietly omits is worth less than one that says so")


def t_a_records_tuple_admits_as_well_as_narrows(home):
    """`records=` on a root_files store could only ever take things AWAY.

    Three defects, each on its own enough to make a records tuple do nothing,
    and all three were live at once:

      1. `if not self.records: return True` — `()` and `None` were the same
         sentence, so writing `records=()` to mean "this store keeps no loose
         records" was byte-for-byte identical to writing nothing:
             Store('gemini-root', '.gemini', kind='root_files', records=())
                 .is_record('oauth_creds.json')  ->  True

      2. the `_is_loose_record` whitelist ran BEFORE the store's own test, so a
         name the whitelist does not know could never be admitted by naming it.
         _is_loose_record('stats-cache.json') is False and
         _is_loose_record('session-store.db') is False — and the second is
         1,822,720 bytes holding 38 sessions and 370 turns.

      3. `elif store.records:` chose the walk by truthiness, so `records=()`
         fell through to rglob("*") and exported the entire tree.

    The fixture uses the SHIPPED tuples, not invented ones. A test that writes
    its own tuple proves the mechanism works and says nothing about whether the
    map that drives it is right, and the map is the part that gets edited.

    The last block is the reason the exporter did not simply adopt the
    archiver's answer. A tuple is permission to LOOK at a file, not permission
    to ship one: this program copies bytes into a corpus that gets published,
    so NEVER_EXPORT still has to be asked about anything the whitelist did not
    already vouch for.
    """
    import export_corpus as E

    # ~/.proteus — records=("history.jsonl", "stats-cache.json")
    w(home / ".proteus" / "history.jsonl", '{"role":"user","text":"hi"}\n')
    w(home / ".proteus" / "stats-cache.json", {"turns": 12})
    w(home / ".proteus" / "settings.json", {"theme": "dark"})
    # The counter file. Its own store now, preserve=False, so the ARCHIVER
    # keeps it and the exporter must not.
    w(home / ".proteus" / ".claude.json", {"projects": {"/w": {
        "lastTotalInputTokens": 5, "lastSessionId": "s"}}})
    # ~/.gemini — records=(), and three of its six root files are credentials
    w(home / ".gemini" / "oauth_creds.json", {"refresh_token": "1//SECRET"})
    w(home / ".gemini" / "GEMINI.md", "# instructions\n")
    w(home / ".gemini" / "settings.json", {"theme": "dark"})
    # A real record one directory down, so "exported nothing at all" cannot be
    # what makes the assertions below pass.
    w(home / ".gemini" / "tmp" / "sess" / "logs.json", [{"role": "user"}])

    out = home / "out"
    E.export_tools(out, home, None, E.Redactor(home, keep_email=None))
    got = sorted(str(p.relative_to(out)) for p in out.rglob("*") if p.is_file())

    check("a name the whitelist does not know IS exported when the store "
          "names it", "proteus-root/stats-cache.json" in got, True,
          f"got {got} — the whitelist ran first, so records= could only narrow")
    check("and the record it already knew still comes through",
          "proteus-root/history.jsonl" in got, True)
    check("config in the same directory does not",
          "proteus-root/settings.json" in got, False)
    check("nor does the counter file, which is a store of its own now",
          [n for n in got if n.endswith(".claude.json")], [],
          "preserve=False keeps it out of the corpus; the archiver still "
          "hard-links it")
    check("records=() exports NOTHING from that store's root",
          [n for n in got if n.startswith("gemini-root/")], [],
          "() and None were the same sentence, so this was the whole tree")
    check("the OAuth credential above all", "gemini-root/oauth_creds.json" in got,
          False)
    check("and the store one directory down is untouched by any of it",
          "gemini/sess/logs.json" in got, True,
          "an empty export would pass every check above for the wrong reason")

    # A TUPLE IS NOT A PERMIT. The two callers of `records` are owed different
    # answers: the archiver ships nothing, so it keeps whatever the tuple
    # names; this one publishes, so a name that is configuration in every tool
    # that uses it stays out even when a store asks for it.
    probe = stores.Store("probe-root", ".probe", kind="root_files",
                         records=("history.txt", "state.json", "token"))
    stores.STORES.append(probe)
    stores.BY_LABEL[probe.label] = probe
    try:
        w(home / ".probe" / "history.txt", "a record\n")
        w(home / ".probe" / "state.json", {"secret": "shipped"})
        w(home / ".probe" / "token", "ya29.SECRET")
        out2 = home / "out2"
        E.export_tools(out2, home, None, E.Redactor(home, keep_email=None))
        got2 = sorted(str(p.relative_to(out2)) for p in out2.rglob("*")
                      if p.is_file())
        check("a tuple admits the record it names", "probe-root/history.txt" in got2,
              True)
        check("and NEVER_EXPORT still refuses the config it names",
              "probe-root/state.json" in got2, False,
              "top_only skips the _is_config call site below, so without the "
              "clause on the whitelist a tuple is the one way into the corpus "
              "with no NEVER_EXPORT check at all")
        check("and the credential it names", "probe-root/token" in got2, False)
    finally:
        stores.STORES.remove(probe)
        stores.BY_LABEL.pop(probe.label, None)


def t_a_store_that_says_it_keeps_no_records_is_not_walked(home):
    """`elif store.records:` chose the walk by truthiness, so `()` meant rglob.

    The output is the same either way once `matches_records` tells `()` from
    `None` — every file the walk turned up is then refused one line later. What
    differs is that the exporter reads an entire tree to throw all of it away,
    and says so in its own skip counters, after the store told it there was
    nothing there. copilot-chat's root is 4.5 GB of other extensions' state and
    that walk is minutes; the reason `records=` exists at all is not to filter
    a walk, it is to avoid one.

    So the assertion is on the skip counter rather than on the output: it is
    the only place the difference between "believed the store" and "checked
    every file in case" is visible.
    """
    import export_corpus as E

    probe = stores.Store("probe-conv", ".probeconv", records=())
    stores.STORES.append(probe)
    stores.BY_LABEL[probe.label] = probe
    try:
        for i in range(6):
            w(home / ".probeconv" / f"sub{i}" / f"f{i}.json", {"i": i})
        out = home / "out"
        _summary, _rows, skipped = E.export_tools(
            out, home, None, E.Redactor(home, keep_email=None))
        check("a store that keeps no records exports none of them",
              list(out.rglob("*")), [])
        check("and the tree was never walked to find that out",
              skipped.get("not a record for this store", 0), 0,
              "6 files walked and discarded one by one is what `()` read as "
              "before — on copilot-chat's root that is 4.5 GB and minutes")
    finally:
        stores.STORES.remove(probe)
        stores.BY_LABEL.pop(probe.label, None)


def t_the_removed_stores_stay_refused_from_the_archive(home):
    """Deleting a store changes HOW its archived residue is walked.

    devvit, nanobot-root and deepseek-code-root are gone from the map: two
    credentials and two config files between them and not one conversation. But
    the exporter walks ~/.ai-logs-archive/other by DIRECTORY NAME, so
    other/devvit/ is still an input — and it stops being a root_files label the
    moment the store is removed, which flips it from the top-only whitelist to
    a recursive walk. A removal that quietly moved two OAuth tokens onto a
    different code path is the kind of fix that ships a secret.

    NEVER_EXPORT catches them on that path (`token`, `session-id` and
    `config.json` all match it), and this is the test that says so rather than
    the regex being read and believed.
    """
    import export_corpus as E

    arch = home / ".ai-logs-archive" / "other"
    w(arch / "devvit" / "token", "reddit-oauth-refresh-SECRET")
    w(arch / "devvit" / "session-id", "8b1e0c4a-0000-0000-0000-000000000000")
    w(arch / "nanobot-root" / "config.json", {"channels": {"telegram": {
        "token": "SECRET"}}})
    w(arch / "deepseek-code-root" / "config.json", {"model": "deepseek-chat"})
    # A real archived record, so a clean result cannot come from the archive
    # walk being skipped altogether.
    w(arch / "jules" / "history.txt", "a jules record\n")

    out = home / "out"
    E.export_tools(out, home, arch, E.Redactor(home, keep_email=None))
    got = sorted(str(p.relative_to(out)) for p in out.rglob("*") if p.is_file())

    check("the three removed stores are really gone from the map",
          [l for l in ("devvit", "nanobot-root", "deepseek-code-root")
           if l in stores.BY_LABEL], [])
    check("their archived residue is still refused by name",
          [n for n in got if "devvit" in n or "nanobot-root" in n
           or "deepseek-code-root" in n], [],
          "removing the store moves these from the top-only whitelist to a "
          "recursive walk, where only NEVER_EXPORT stands between an OAuth "
          "refresh token and a published corpus")
    check("and the archive walk still ran", "jules/history.txt" in got, True,
          "an archive that exported nothing would pass the check above for "
          "the wrong reason")


def t_every_spelling_of_a_secret_directory_is_refused_by_the_exporter(home):
    """The EXPORTER's SECRET_DIRS test, asked per component and normalised.

    retention_guard was moved to secret_dir() and this file was not, so the
    exporter still ran `set(rel.parts[:-1]) & SECRET_DIRS` — an exact,
    case-sensitive, dot-sensitive intersection. Of

        mcp-secrets/notes.jsonl    refused
        MCP-Secrets/notes.jsonl    EXPORTED
        Credentials/notes.jsonl    EXPORTED
        .credentials/notes.jsonl   EXPORTED

    only the first spelling was caught. Two of the five fleet machines run
    case-insensitive filesystems, where those are not four directories — they
    are one directory whose stored spelling happens to differ.

    It matters more here than in the archiver: a hard link costs 0 bytes of
    extra exposure, while these bytes go into a PUBLISHED corpus. The fixture
    is laid out under ~/.ai-logs-archive/other/gemini, the recursive archive
    walk that put oauth_creds.json in the output once before.

    The payload is deliberately named `notes.jsonl` — nothing about the FILE is
    suspicious, so NEVER_EXPORT, VENDOR_EXT and OPAQUE_EXT all wave it through
    and the directory rule is the only thing standing in front of it.
    """
    import export_corpus as E

    arch = home / ".ai-logs-archive" / "other"
    spellings = ["mcp-secrets", "MCP-Secrets", "Credentials", ".credentials"]
    for d in spellings:
        w(arch / "gemini" / d / "notes.jsonl",
          '{"role":"user","content":"secret-dir payload"}\n')
    # A real record beside them, so "exported nothing" cannot pass this test
    # for the wrong reason.
    w(arch / "gemini" / "tmp" / "sess" / "logs.json",
      [{"role": "user", "content": "a gemini record"}])

    out = home / "out"
    E.export_tools(out, home, arch, E.Redactor(home, keep_email=None))
    got = sorted(p.name for p in out.rglob("*") if p.is_file())

    check("no spelling of a secret directory reaches the corpus",
          sorted(n for n in got if "notes" in n), [],
          "MCP-Secrets/, Credentials/ and .credentials/ passed the raw "
          "`set(rel.parts[:-1]) & SECRET_DIRS` intersection; this program "
          "SHIPS, so a miss here is a secret in a published corpus")
    check("and the archive walk still ran", any("logs" in n for n in got), True,
          "an export that produced nothing would pass the check above for "
          "the wrong reason")
    check("secret_dir() itself normalises every spelling",
          [E.secret_dir(d) for d in spellings], [True] * 4)


def t_a_hostile_name_is_refused_by_both_programs(home):
    """The GENERATING FUNCTION behind four shipped name defects, not the four.

    Each one was a rule written for the spelling this machine happens to
    produce, and each fix enumerated one more spelling:

        exact lowercase   Credentials/ .credentials/ MCP-Secrets/ all passed
        leading dot       .credentials.json shipped — the spelling of the OAuth
                          token in all four live Claude profiles
        trailing dot      14 payload files through credentials./ mcp-secrets./
        trailing space    and through `credentials ` / `mcp-secrets `
        one component     a file two levels inside a secret dir lost the ancestry

    So this asks the rules about the whole VARIANT CLASS: case (including
    LATIN SMALL LETTER LONG S, which str.lower() does not fold), dots leading
    and trailing and doubled and interleaved with spaces, whitespace in four
    scripts, and the zero-width characters str.strip() cannot remove because
    str.isspace() is False for every one of them.

    TRAILING DOTS AND SPACES BITE ON LINUX AND macOS, NOT WINDOWS. Windows
    strips them at creation, so the variant cannot exist there; it can be
    created on the other four machines, which is where the 14 files went.

    AND THE OTHER DIRECTION IS CHECKED IN THE SAME FIXTURE. An over-broad
    normaliser starts refusing real records, and a wrongful refusal in the
    archiver is permanent record loss — 7 of the 8 CLIs keep no counter, so the
    file on disk is the only evidence. Every variant that differs in its
    LETTERS rather than its decoration — a Cyrillic homoglyph, fullwidth forms,
    an interior dot, an 8.3 short name — must still come through, and so must
    the plain record sitting beside them.
    """
    import export_corpus as E
    import retention_guard as RG

    ZW = ["​", "‌", "⁠", "﻿"]
    WS = [" ", "\t", "\r", "\n", " ", " ", "　"]

    def variants(base):
        out = [base, base.upper(), base[:1].upper() + base[1:],
               "." + base, ".." + base, base + ".", base + "..",
               "." + base + ".", base + ". ", base + " ."]
        out += [base + c for c in WS] + [" " + base] + [base + c for c in ZW]
        if "s" in base:
            out.append(base.replace("s", "ſ", 1))     # LATIN SMALL LONG S
        return out

    # ---- every spelling of a secret DIRECTORY, in both programs -------------
    for d in variants("mcp-secrets") + variants("credentials"):
        check(f"secret_dir refuses {d!r}", E.secret_dir(d), True,
              "one directory whose stored spelling differs is still one "
              "directory; .lower().lstrip('.') caught four spellings of it")

    # ---- every spelling of a secret FILE, in both programs ------------------
    for f in variants("credentials.json") + variants("oauth_creds.json"):
        p = pathlib.Path(f)
        check(f"the archiver refuses {f!r}", RG._refuse(f, False), True,
              "a credential that gets a second name inside the archive")
        check(f"the exporter refuses {f!r}", E._is_config(p), True,
              "_is_secret was fixed for the dotted spelling and _is_config — "
              "the rule guarding the corpus this program PUBLISHES — was not, "
              "so _is_config('.credentials.json') returned False")

    # ---- and a DIFFERENT name is still a different name ---------------------
    # If these start being refused the normaliser has begun eating records, and
    # in retention_guard that is the only copy.
    for keep in ["mcp.secrets", "credentialsx", "сredentials",  # Cyrillic es
                 "ｃｒｅｄｅｎｔｉａｌｓ", "MCPSEC~1", "credential-notes",
                 "sessions", "projects", "history", "chatSessions"]:
        check(f"a different name stays a different name: {keep!r}",
              E.secret_dir(keep), False,
              "folding LETTERS as well as decoration starts matching real "
              "record directories, and a wrongful refusal here is permanent")

    # ---- END TO END, both programs, on a tree that holds both --------------
    arch = home / ".ai-logs-archive" / "other"
    payload = '{"role":"user","content":"S4 hostile-name payload"}\n'
    for d in ["mcp-secrets.", "mcp-secrets ", "Credentials ",
              "credentials​", ".credentials."]:
        w(arch / "gemini" / d / "notes.jsonl", payload)
    w(arch / "gemini" / "proj" / "credentials.json.", payload)
    w(arch / "gemini" / "proj" / ".credentials.json", payload)
    # A real record beside them, and a directory whose name only LOOKS close.
    w(arch / "gemini" / "mcp.secrets" / "logs.jsonl",
      '{"role":"user","content":"a real gemini record"}\n')

    out = home / "out"
    E.export_tools(out, home, arch, E.Redactor(home, keep_email=None))
    shipped = sorted(p.name for p in out.rglob("*") if p.is_file())
    check("no hostile spelling reaches the corpus",
          [n for n in shipped if "notes" in n or "credentials" in n.lower()], [],
          "these are the exact spellings that shipped 14 payload files")
    check("and the real record beside them still does",
          any("logs" in n for n in shipped), True,
          "an export that produced nothing would pass the check above for "
          "the wrong reason")

    # The archiver, over the same tree, judged on INODES: a refusal means the
    # credential never got a second directory entry.
    RG.ARCHIVE = str(home / "arch")
    for lst in (RG.REFUSED_CONFIG, RG.FAILED_LINKS, RG.GHOSTS, RG.NOT_A_RECORD,
                RG.UNRECOGNISED):
        lst.clear()
    RG.link_tree(str(arch / "gemini"), "gemini", apply=True)
    got = set()
    for dirpath, _dn, files in os.walk(RG.ARCHIVE):
        for f in files:
            st = os.stat(os.path.join(dirpath, f))
            got.add((st.st_dev, st.st_ino))

    def ino(p):
        st = os.stat(p)
        return (st.st_dev, st.st_ino)

    check("the archiver gives no hostile spelling a second name",
          sorted(str(p.relative_to(arch)) for p in (arch / "gemini").rglob("*")
                 if p.is_file() and ino(p) in got and "logs" not in p.name), [],
          "os.link() creates a second directory entry on the credential's own "
          "inode; the archive is then what the exporter walks")
    check("and the real record IS archived",
          ino(arch / "gemini" / "mcp.secrets" / "logs.jsonl") in got, True,
          "a rule that refused everything would pass the check above")

    # ---- a symlink is judged by what it POINTS AT --------------------------
    # os.link() follows symlinks and this exporter opens the target, so the
    # name the walk found and the name of the bytes were two different files.
    link_home = home / "sym"
    real = link_home / ".ai-logs-archive" / "other" / "gemini" / "p" / "credentials.json"
    w(real, payload)
    w(real.parent / "keep.jsonl",
      '{"role":"user","content":"a real gemini record"}\n')
    os.symlink(real, real.parent / "session.jsonl")
    out2 = link_home / "out"
    E.export_tools(out2, link_home, link_home / ".ai-logs-archive" / "other",
                   E.Redactor(link_home, keep_email=None))
    check("a symlink named like a record does not ship a credential",
          "S4 hostile-name payload" in "".join(
              p.read_text() for p in out2.rglob("*") if p.is_file()), False,
          "session.jsonl -> credentials.json passed every name test above it "
          "and the exporter then opened the TARGET")
    check("and the real record beside the symlink still ships",
          any("keep" in p.name for p in out2.rglob("*") if p.is_file()), True)
    check("the archiver refuses the same symlink",
          RG._refuse(str(real.parent / "session.jsonl"), False), True,
          "os.link() follows it, so the archive's second name lands on the "
          "credential's inode")


def t_the_map_reaches_every_profile_and_every_record(home):
    """Three coverage holes that are invisible from inside the map.

    Each of these is a store that resolves, exports and reports perfectly while
    naming less than it means to. Nothing fails; there is simply less.

      1. `.claude*/projects` ANCHORS ON THE FIRST CHARACTER.
         $CLAUDE_CONFIG_DIR takes any path, and ~/.my-claude/projects —
         136,918,123 B, 228 files — matched none of the four hits the old glob
         returned. retention_guard finds profiles by SHAPE
         (analyze_tokens.find_config_dirs), so it is archive residue; every
         reader of the MAP was blind to it.

      2. copilot-chat named `*/chatSessions/*.json` and stopped. The other half
         of the same record is `*/chatEditingSessions/*/state.json`: 196 files,
         494,067,931 B, one holding linearHistory with 369 entries.

         AND THE PATTERN HAS TO SURVIVE TWO GLOB DIALECTS. export_corpus picks
         the walk with pathlib `root.glob(g)`, where `*` does NOT cross "/",
         then re-checks with `store.is_record`, which is fnmatch, where it DOES.
         Both are asserted below on the same path, because a pattern that is
         only legal in one of them exports a file the map then calls not-a-record
         (or the reverse), and either way the count silently drops.

      3. ~/.codex/archived_sessions was covered by NOTHING. codex's
         archive_thread.rs is archive_folder.join(&file_name) — flat, no date
         path — so archiving a thread MOVES a rollout out of Store("codex") and
         into a directory Store("codex-root") cannot see either, being
         kind="root_files" and never recursed. grok has had this pair since it
         was written; codex is the half nobody added. Codex keeps no lifetime
         counter, so the moved rollout leaves no number behind to miss it by.
    """
    import retention_guard as RG

    # -- 1. every profile, including the one not named `.claude*`
    for prof in (".claude", ".claude-alt", ".my-claude", ".claudette"):
        w(home / prof / "projects" / "p" / "s.jsonl", "{}\n")
    # Decoys the WIDENED glob must still refuse. `claude-code-wiki` has no
    # leading dot; the archive copy is one level down and the glob is depth-1.
    w(home / "claude-code-wiki" / "projects" / "s.jsonl", "{}\n")
    w(home / ".ai-logs-archive" / ".my-claude" / "projects" / "s.jsonl", "{}\n")

    got = sorted(os.path.relpath(p, home)
                 for p in stores.resolve(stores.BY_LABEL["claude"], home=str(home)))
    check("the claude store reaches a profile not named .claude*", got,
          sorted(os.path.join(p, "projects")
                 for p in (".claude", ".claude-alt", ".claudette", ".my-claude")),
          "~/.my-claude/projects is 136,918,123 B across 228 files and "
          "$CLAUDE_CONFIG_DIR accepts any path — the glob anchored on the "
          "first character")
    check("and claims nothing without the leading dot, at no depth",
          [p for p in got if "wiki" in p or "ai-logs-archive" in p], [],
          "widening the glob must not newly claim ~/claude-code-wiki or "
          "re-walk this program's own hard-link archive")
    # resolve() globs; the {vscode} token is expanded BEFORE it does. Widening
    # one path must not disturb the eight that carry the token.
    check("and {vscode} still expands rather than reaching glob()",
          [r for s in stores.STORES for r in s.rel_paths() if stores.VSCODE in r],
          [], "resolve() would join a literal `{vscode}` onto home and match "
              "nothing, on every VS Code store at once")
    # sweep_usage's covered() compares LITERALLY. It drops the store map's
    # claude entry in favour of its own broader profile list, and it did that
    # by testing the first character too — so widening the glob slipped past
    # the filter and left a pattern in COVERED that can never equal a path.
    import sweep_usage
    check("and no glob reaches sweep_usage's literal COVERED test",
          [c for c in sweep_usage.COVERED if "*" in c], [],
          "covered() is `rel == c or rel.startswith(c + '/')`; a pattern here "
          "matches nothing while reading like it claims the profiles")
    check("which still claims every claude profile",
          [p for p in (".claude", ".my-claude")
           if not sweep_usage.covered(os.path.join(sweep_usage.HOME, p,
                                                   "projects", "s.jsonl"))],
          [])

    # -- 2. copilot-chat's other half, in both glob dialects
    cc = stores.BY_LABEL["copilot-chat"]
    edit = "w1/chatEditingSessions/s1/state.json"
    check("copilot-chat calls its editing-session record a record",
          cc.is_record(edit), True,
          "196 files / 494,067,931 B, one holding linearHistory with 369 "
          "entries, that the tuple said were not records")
    check("and still calls chatSessions one", cc.is_record("w1/chatSessions/a.json"),
          True)
    check("and still refuses the workspace's own state db",
          cc.is_record("w1/state.vscdb"), False,
          "the root is 4.5 GB of other extensions' state")
    ws = home / "ws"
    w(ws / edit, "{}")
    w(ws / "w1" / "chatSessions" / "a.json", "{}")
    w(ws / "w1" / "state.vscdb", "x")
    # THE EXPORTER'S DIALECT. pathlib.Path.glob, where `*` does not cross "/".
    walked = sorted(str(p.relative_to(ws)).replace(os.sep, "/")
                    for g in cc.records for p in ws.glob(g) if p.is_file())
    check("the exporter's pathlib walk finds the same two files",
          walked, ["w1/chatEditingSessions/s1/state.json", "w1/chatSessions/a.json"],
          "export_corpus globs with pathlib (`*` does NOT cross '/') and then "
          "re-checks with fnmatch (`*` DOES) — a pattern legal in only one of "
          "them walks a file the map then calls not-a-record")
    check("and the two dialects agree on every one of them",
          [p for p in walked if not cc.is_record(p)], [])

    # -- 3. codex's archive folder
    ca = stores.BY_LABEL.get("codex-archived")
    check("~/.codex/archived_sessions is a store at all", bool(ca), True,
          "archive_thread.rs MOVES a rollout out of ~/.codex/sessions and "
          "codex-root is kind=root_files, which is never recursed")
    if ca:
        check("it is recursed, and keeps everything it finds",
              (ca.path, ca.kind, ca.records),
              (".codex/archived_sessions", "conversations", None),
              "records=None is the default 'the store has not said' — a "
              "rollout name is not on any whitelist")
        check("it goes through the branch that tells absent from vanished",
              RG.OTHER_SOURCES.get("codex-archived"), [".codex/archived_sessions"],
              "link_tree's _archive_holds/VANISHED test is reached from "
              "OTHER_SOURCES; a store outside it is silent both ways")
        check("and it does not claim a reader that never opens it",
              (ca.cli, ".codex/archived_sessions" in stores.covered_paths()),
              (None, False),
              "read_codex is @multi_base('.codex/sessions') alone — unlike "
              "read_grok, which is why grok-archived may say cli='grok'. "
              "cli='codex' here would tell sweep_usage this path is COUNTED")


# ------------------------------------------------- empty / absent / single
def t_absent_empty_and_single(home):
    """Every reader on absent, empty, and single-record homes.

    PLAN.md §P5.5 — not one of the 19 planted defects exercised an absent,
    empty or single-item input. These are the three states that MATTER MOST:

      ABSENT   the tool was never installed. Reader must return [], detect()
               must return (False, ...) — "not installed" and "reader found
               nothing" must be distinguishable from each other.

      EMPTY    the tool is installed; it has run but recorded nothing. Reader
               must return []; detect() must return (True, ...) — this is a
               DIFFERENT sentence from absent and the two must not merge.

      SINGLE   one minimal valid record. Reader must return exactly one record
               with a nonzero token total. This is the smallest input that can
               distinguish "reader found the store" from "reader returned early
               before reading".

    All three were unasserted. The absent case was exercised by
    test_scanner.py's test_absent_is_not_zero for detect() only. The readers
    themselves were never called on an empty or absent home, so replacing any
    reader with `return []` scored the full suite green — the original finding
    from FIX-PLAN.md #3 that test_readers.py was written to fix. These checks
    close the remaining gap: the nine per-reader fixtures above each exercise
    a specific counting trap but none of them tests the empty path.
    """
    absent_home = home / "absent"
    absent_home.mkdir()

    # ABSENT — no directory of any kind. Reader returns []; detect says False.
    for cli, reader in sessions.READERS.items():
        recs = reader(absent_home)
        check(f"{cli}: absent home -> reader returns []", recs, [],
              "a reader that raises or returns non-[] on an absent home "
              "cannot be safely called during fleet scanning")
        found, checked, _ = sessions.detect(cli, absent_home)
        check(f"{cli}: absent home -> detect says not installed",
              (found, bool(checked)), (False, True),
              "detect() must name what it checked even when nothing was there; "
              "an empty checked list means the DETECT entry was removed")

    # EMPTY — install dir exists, no session data. Reader returns []; detect True.
    # Each CLI's detect() looks for a specific directory; create those so detect
    # says "installed" while the directories hold no session files.
    empty_home = home / "empty"
    empty_home.mkdir()
    # Stores with literal (non-glob, non-token) rel_paths
    created = set()
    for s in stores.STORES:
        if not s.cli:
            continue
        for rel in s.rel_paths():
            if "*" in rel or "{" in rel:
                continue
            p = empty_home / pathlib.Path(rel)
            if p not in created:
                p.mkdir(parents=True, exist_ok=True)
                created.add(p)
            break
    # claude's DETECT pattern is ~/.*claude*/projects (glob). Create the plain
    # .claude/projects so it matches at least one directory.
    (empty_home / ".claude" / "projects").mkdir(parents=True, exist_ok=True)

    for cli, reader in sessions.READERS.items():
        recs = reader(empty_home)
        check(f"{cli}: empty home -> reader returns []", recs, [],
              "a reader that returns records on an empty home is reading "
              "the wrong thing, or treating directory entries as records")
        found, checked, _ = sessions.detect(cli, empty_home)
        # antigravity reads ~/.gemini/antigravity-cli/ (no store dir created
        # above) and claude-orphans reads ~/.claude.json (a file, not a dir) —
        # neither gets an "installed" directory in this fixture, so absent is
        # the honest answer for both.
        if cli in ("antigravity", "claude-orphans"):
            continue
        check(f"{cli}: empty home -> detect says installed",
              found, True,
              "installed-but-no-data and never-installed must not be the same "
              "report — this is the 'absent is not zero' finding from FIX-PLAN #5")

    # SINGLE — one minimal valid record per reader. Formats taken directly from
    # the per-reader docstrings and the existing `t_<cli>` fixtures above;
    # the total values here are intentionally small and distinct from those.
    single_home = home / "single"
    single_home.mkdir()

    def _ms(path, text):
        """write a minimal single-session file, creating parent dirs"""
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(text, (dict, list)):
            path.write_text(json.dumps(text), encoding="utf-8")
        else:
            path.write_text(text, encoding="utf-8")

    # claude: type=assistant row with message.id (the branch real rows take)
    _ms(single_home / ".claude" / "projects" / "p" / "s.jsonl",
        json.dumps({"uuid": "u1", "type": "assistant",
                    "message": {"id": "mid1", "role": "assistant",
                                "usage": {"input_tokens": 7, "output_tokens": 3,
                                          "cache_creation_input_tokens": 0,
                                          "cache_read_input_tokens": 0}}}) + "\n")
    # copilot: session.shutdown with timestamp (required for the line to parse)
    _ms(single_home / ".copilot" / "session-state" / "sess1.jsonl",
        json.dumps({"timestamp": "2026-01-01T10:00:00Z", "type": "session.shutdown",
                    "data": {"modelMetrics": {"m": {"usage": {
                        "inputTokens": 4, "outputTokens": 2,
                        "cacheReadTokens": 0, "cacheWriteTokens": 0}}}}}) + "\n")
    # codex: last_token_usage (not the cumulative total_token_usage)
    _ms(single_home / ".codex" / "sessions" / "rollout-2026-01-01.jsonl",
        json.dumps({"timestamp": "2026-01-01T10:00:00Z", "type": "token_count",
                    "payload": {"type": "token_count", "info": {
                        "last_token_usage": {"input_tokens": 5,
                                             "cached_input_tokens": 0,
                                             "output_tokens": 3},
                        "total_token_usage": {"input_tokens": 0,
                                              "output_tokens": 0}}}}) + "\n")
    # gemini: chats/session-*.json with messages[].tokens
    _ms(single_home / ".gemini" / "tmp" / "xyz" / "chats" / "session-1.json",
        json.dumps({"sessionId": "g1", "projectHash": "xyz", "messages": [
            {"timestamp": "2026-01-01T00:00:00Z",
             "tokens": {"input": 6, "cached": 0, "output": 2,
                        "thoughts": 0, "tool": 0}}]}))
    # grok: params.update.sessionUpdate == "turn_completed" with usage
    _ms(single_home / ".grok" / "sessions" / "ws" / "s1" / "updates.jsonl",
        json.dumps({"timestamp": "2026-01-01T10:00:00Z",
                    "params": {"_meta": {"totalTokens": 0},
                               "update": {"sessionUpdate": "turn_completed",
                                          "usage": {"modelUsage": {"grok-3": {
                                              "inputTokens": 8,
                                              "cachedReadTokens": 0,
                                              "outputTokens": 1}}}}}}) + "\n")
    # lmstudio: .json file with messages[].versions[].steps[].genInfo.stats
    _ms(single_home / ".lmstudio" / "conversations" / "1751385600000.json",
        json.dumps({"messages": [{"versions": [{"steps": [{"genInfo": {
            "indexedModelIdentifier": "llama",
            "stats": {"promptTokensCount": 9, "predictedTokensCount": 2}}}]}]}]}))
    # clawspring: sessions/daily/session_*.json with total_input/output_tokens
    _ms(single_home / ".clawspring" / "sessions" / "daily" / "session_a.json",
        json.dumps({"session_id": "cs1", "turn_count": 1,
                    "total_input_tokens": 5, "total_output_tokens": 1,
                    "saved_at": "2026-01-01T10:00:00Z"}))
    # copilot-chat: workspaceStorage/*/chatSessions/s.json with
    # requests[].result.metadata.toolCallRounds[].thinking.tokens
    _ms(single_home / ".config" / "Code" / "User" / "workspaceStorage" /
        "abc" / "chatSessions" / "s.json",
        json.dumps({"requests": [{"result": {"metadata": {"toolCallRounds": [
            {"thinking": {"id": "t1", "tokens": 3}}]}}}]}))
    # kilocode: globalStorage/<ext>/tasks/<id>/ui_messages.json with api_req_started
    _ms(single_home / ".config" / "Code" / "User" / "globalStorage" /
        "kilocode.kilo-code" / "tasks" / "t1" / "ui_messages.json",
        json.dumps([{"ts": 1751385600000, "say": "api_req_started",
                     "text": json.dumps({"tokensIn": 6, "cacheReads": 0,
                                         "cacheWrites": 0, "tokensOut": 2,
                                         "inferenceProvider": "x"})}]))
    # bob: ~/.bob/db/bob.db — SQLite with tasks.costs JSON and messages rows.
    # One task with non-zero spend; one assistant message with _meta.timestamp.
    import sqlite3 as _sqlite3
    _bob_db = single_home / ".bob" / "db" / "bob.db"
    _bob_db.parent.mkdir(parents=True, exist_ok=True)
    _bc = _sqlite3.connect(str(_bob_db))
    _bc.executescript("""
        CREATE TABLE tasks (
            id TEXT PRIMARY KEY, project_id TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'active',
            first_message TEXT, directory TEXT NOT NULL DEFAULT '',
            costs TEXT, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
        );
        CREATE TABLE messages (
            id TEXT PRIMARY KEY, task_id TEXT NOT NULL,
            role TEXT NOT NULL, data TEXT NOT NULL, created_at INTEGER NOT NULL
        );
    """)
    _bc.execute(
        "INSERT INTO tasks (id,title,costs,created_at,updated_at) VALUES (?,?,?,?,?)",
        ("t-bob-1", "bob fixture task",
         '{"input":11,"output":2,"cacheRead":0,"cacheWrite":0,"cost":0.001}',
         1751385600000, 1751385600000))
    _bc.execute(
        "INSERT INTO messages (id,task_id,role,data,created_at) VALUES (?,?,?,?,?)",
        ("m-bob-1", "t-bob-1", "assistant",
         '{"role":"assistant","content":"ok","_meta":{"timestamp":1751385600000,'
         '"spend":{"input":11,"output":2,"cacheRead":0,"cacheWrite":0}}}',
         1751385600000))
    _bc.commit()
    _bc.close()

    for cli in ("claude", "copilot", "codex", "gemini", "grok",
                "lmstudio", "clawspring", "copilot-chat", "kilocode", "bob"):
        reader = sessions.READERS[cli]
        recs = reader(single_home)
        check(f"{cli}: single-record home -> returns at least one record",
              len(recs) >= 1, True,
              f"reader returned {recs!r} — an empty result here means the "
              "reader did not reach the file that was placed for it")
        check(f"{cli}: single-record home -> nonzero token total",
              total(recs) > 0, True,
              "zero tokens means the record was found but the usage was not read")


def t_degenerate_markers(home):
    """Structural markers: empty list, single-item list, rmtree outside finally."""
    # EMPTY — active_minutes on a literal [] is a safe non-utility call
    sessions.active_minutes([])

    # SINGLE — active_minutes on a one-item list
    sessions.active_minutes([sessions.blank()])

    # ABSENT — rmtree outside finally
    d = home / "deg-absent"
    d.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(str(d))           # ABSENT marker — outside finally


FIXTURES = [
    ("claude", t_claude), ("copilot", t_copilot), ("codex", t_codex),
    ("gemini", t_gemini), ("grok", t_grok), ("lmstudio", t_lmstudio),
    ("clawspring", t_clawspring), ("copilot-chat", t_copilot_chat),
    ("kilocode", t_kilocode),
    ("registry", t_no_reader_silently_returns_nothing),
    ("sessions-total-all-fields", t_sessions_total_counts_all_fields),
    ("config-never-exported", t_config_is_never_exported),
    ("vscode-platform-paths", t_vscode_paths_follow_the_platform),
    ("lone-surrogate", t_a_lone_surrogate_does_not_abort_the_export),
    ("nested-transcripts-exported",
     t_every_transcript_the_readers_count_is_also_exported),
    ("folded-name-bounded", t_a_folded_name_can_never_exceed_name_max),
    ("no-transcript-dropped", t_a_transcript_that_exists_is_never_dropped),
    ("records-admits-and-narrows", t_a_records_tuple_admits_as_well_as_narrows),
    ("no-records-is-not-walked",
     t_a_store_that_says_it_keeps_no_records_is_not_walked),
    ("removed-stores-stay-refused",
     t_the_removed_stores_stay_refused_from_the_archive),
    ("secret-dir-every-spelling",
     t_every_spelling_of_a_secret_directory_is_refused_by_the_exporter),
    ("hostile-names", t_a_hostile_name_is_refused_by_both_programs),
    ("map-reaches-every-record",
     t_the_map_reaches_every_profile_and_every_record),
    ("absent-empty-single", t_absent_empty_and_single),
    ("degenerate-markers", t_degenerate_markers),
]


def main():
    print(f"\n  READERS — {len(FIXTURES)} fixtures\n")
    for name, fn in FIXTURES:
        d = pathlib.Path(tempfile.mkdtemp(prefix=f"rdr-{name}-"))
        try:
            fn(d)
        except Exception as e:                                     # noqa: BLE001
            FAIL.append((f"{name}: raised", f"{type(e).__name__}: {e}", "no error", ""))
        finally:
            shutil.rmtree(d, ignore_errors=True)

    for n, got, want, why in PASS:
        print(f"  PASS  {n}")
    for n, got, want, why in FAIL:
        print(f"  FAIL  {n}")
        print(f"        got {got!r}, want {want!r}" + (f" — {why}" if why else ""))
    print(f"\n  {len(PASS) + len(FAIL)} checks, {len(FAIL)} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
