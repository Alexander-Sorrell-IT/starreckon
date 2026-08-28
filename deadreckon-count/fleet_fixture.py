#!/usr/bin/env python3
"""A synthetic five-machine fleet, with the right answer computed by hand.

WHY THIS EXISTS

Four of the five machines in this fleet have never run this code. Every claim
the repo makes about macOS or Windows is a documentation sentence or the
ABSENCE of a platform branch in somebody's source, and nobody has ever checked
that five machines sum correctly. `test_readers.py` proves each reader computes
the number its docstring claims from ONE fixture in ONE home directory; it says
nothing about a fleet.

So this builds one. Five homes with genuinely different shapes, each carrying
per-CLI data, and — the whole point — the KNOWN-CORRECT total planted, returned
by the generator.

    THE EXPECTED VALUE IS COMPUTED HERE, FROM THE SAME LITERAL CONSTANTS THAT
    WERE WRITTEN INTO THE FILES, BY ARITHMETIC SPELLED OUT IN EACH PLANTER.

Nothing in this file imports a reader to work out what a reader should return.
A fixture whose expected value is derived from the thing under test proves
nothing — this repository has twice shipped "25/25 green" over 45 live defects
by exactly that route.

THE FOUR COUNTING TRAPS

Every planter says which of the four it carries, and `Planted.traps` records it
so a test can assert coverage rather than trust this docstring:

    CUMULATIVE   a field that is a RUNNING TOTAL for the session. Summing the
                 rows compounds — 40.7x on codex's total_token_usage.
    REPEATED     the same billed event written more than once: a streaming
                 rewrite (same message.id, new row uuid), a byte-identical
                 re-emission, an end-of-task rollup restating its own rows.
                 First-wins and last-wins are BOTH wrong for the streaming
                 case; the answer is a running MAXIMUM per field.
    SUBSET       a counter contained in another — cached_input inside input,
                 reasoning inside output. Adding it inflates; the split is kept
                 by MOVING it, not by adding it.
    BOOKKEEPING  a context-window advertisement (maxInputTokens, tokenLimit,
                 model_context_window). Not usage at all; 10.4x if summed.

Each planter carries every one of the four that its CLI's format can express,
and says in its docstring which ones the format cannot express and why. A
planter that silently omitted a trap would be a fixture that cannot fail.

ABSENT IS NOT ZERO

The defect this repository has shipped seven times in four disguises. Planted
deliberately, so a test can tell the three apart:

    linux-b       gemini is INSTALLED AND EMPTY. ~/.gemini/tmp exists, holds no
                  session file. A reader must return no records AND detect()
                  must return True, so "installed, no usage recorded" stays a
                  different sentence from "not installed".
    linux-b       lmstudio, clawspring, grok, copilot are ABSENT. No directory.
    lmstudio      exists on linux-a ONLY, so per-CLI fleet coverage is
                  asymmetric and a report that prints one row per CLI per
                  machine cannot fill the gaps with zeros and call it data.
    never-scanned a sixth machine appears in machines.json with NO folder at
                  all — present in the roster, absent from every total.

PLATFORM

Layout is a directory-name question, and ext4 holds any of these names, so the
macOS and Windows trees are built for real. What is NOT a directory-name
question is `stores.vscode_bases()`, which branches on `sys.platform` and
`os.name` at call time — and `sessions.py` freezes that branch AT IMPORT,
because `@multi_base(*stores.paths_for(...))` runs then. `platform_as()` fakes
the platform at `stores`' own view of `sys` and `os` and reloads `sessions`,
which is the only way a macOS or Windows VS Code tree is reachable from a Linux
test runner. It fakes it there and not by replacing `vscode_bases` itself
because replacing the function substitutes the code under test: a planted
defect that deleted the darwin branch went green until this was moved.

USAGE

    import fleet_fixture
    fleet = fleet_fixture.build_fleet(pathlib.Path(tmpdir))
    fleet.machines["linux-a"].expected_by_cli["codex"]     # a number nobody
                                                           # asked the code for
"""

import contextlib
import copy
import dataclasses
import importlib
import json
import pathlib
import sys
import urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import paths                                                       # noqa: E402
import stores                                                      # noqa: E402

CUMULATIVE, REPEATED, SUBSET, BOOKKEEPING = (
    "CUMULATIVE", "REPEATED", "SUBSET", "BOOKKEEPING")
ALL_TRAPS = (CUMULATIVE, REPEATED, SUBSET, BOOKKEEPING)


@dataclasses.dataclass
class Planted:
    """What one planter put on one machine, and what it is worth.

    `tokens` is the sum of the four FIELDS the reader should end up with, and
    it is arithmetic performed in the planter over the same constants the
    planter wrote. `by_field` keeps the split so a test can catch a reader that
    gets the total right by moving tokens between buckets — the exact failure
    the SUBSET rule is about.
    """
    cli: str
    tokens: int
    sessions: int
    by_field: dict
    session_ids: tuple
    traps: tuple
    note: str = ""


@dataclasses.dataclass
class Machine:
    name: str
    home: pathlib.Path
    out: pathlib.Path
    platform: str                      # linux | macos | windows
    planted: list
    reader_version: str
    installed_but_empty: tuple = ()
    absent: tuple = ()
    notes: str = ""

    @property
    def expected_by_cli(self):
        out = {}
        for p in self.planted:
            out[p.cli] = out.get(p.cli, 0) + p.tokens
        return out

    @property
    def expected_sessions_by_cli(self):
        out = {}
        for p in self.planted:
            out[p.cli] = out.get(p.cli, 0) + p.sessions
        return out

    @property
    def expected_total(self):
        return sum(p.tokens for p in self.planted)

    @property
    def session_ids_by_cli(self):
        out = {}
        for p in self.planted:
            out.setdefault(p.cli, set()).update(p.session_ids)
        return out


@dataclasses.dataclass
class Fleet:
    root: pathlib.Path
    records: pathlib.Path
    machines: dict
    never_scanned: tuple
    duplicate_session_ids: dict        # session_id -> (machine, machine, ...)
    only_on_one_machine: dict          # cli -> machine name

    @property
    def expected_by_cli(self):
        out = {}
        for m in self.machines.values():
            for cli, n in m.expected_by_cli.items():
                out[cli] = out.get(cli, 0) + n
        return out

    @property
    def expected_total(self):
        """The naive fleet sum: every machine's own total, added up.

        Deliberately naive, because that is what `combine.py` computes —
        `grand = sum(m["grand_total_tokens"] for m in machines)` with no
        cross-machine identity check of any kind. A session synced to two
        machines is inside this number twice. See `duplicate_session_ids`; that
        is a finding to report, not an assumption to bake in.
        """
        return sum(m.expected_total for m in self.machines.values())

    def as_json(self):
        return {
            "machines": {
                name: {"platform": m.platform,
                       "home": str(m.home),
                       "reader_version": m.reader_version,
                       "total": m.expected_total,
                       "by_cli": m.expected_by_cli,
                       "sessions_by_cli": m.expected_sessions_by_cli,
                       "installed_but_empty": list(m.installed_but_empty),
                       "absent": list(m.absent),
                       "notes": m.notes}
                for name, m in self.machines.items()},
            "fleet_total_naive_sum": self.expected_total,
            "fleet_by_cli": self.expected_by_cli,
            "never_scanned": list(self.never_scanned),
            "duplicate_session_ids": {k: list(v)
                                      for k, v in self.duplicate_session_ids.items()},
            "only_on_one_machine": self.only_on_one_machine,
        }


# --------------------------------------------------------------------------
# writing helpers
# --------------------------------------------------------------------------

def w(p, body):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body if isinstance(body, str) else json.dumps(body),
                 encoding="utf-8")
    return p


def jl(*rows):
    return "".join(json.dumps(r) + "\n" for r in rows)


def _fields(input=0, cache_creation=0, cache_read=0, output=0):
    return {"input_tokens": input, "cache_creation_input_tokens": cache_creation,
            "cache_read_input_tokens": cache_read, "output_tokens": output}


def _sum(f):
    return sum(f.values())


def _add(a, b):
    return {k: a[k] + b[k] for k in a}


# --------------------------------------------------------------------------
# claude
# --------------------------------------------------------------------------

def _claude_row(uuid, mid, ts, sid, project_model="claude-opus-4-6", **usage):
    u = _fields()
    u.update(usage)
    msg = {"role": "assistant", "model": project_model, "usage": u}
    if mid is not None:
        msg["id"] = mid
    return {"uuid": uuid, "timestamp": ts, "sessionId": sid,
            "type": "assistant", "message": msg}


def plant_claude(home, *, sid, project, profile=".claude", k=1, tag="a",
                 second_profile=None):
    """One Claude Code session, at depth, with a streaming rewrite.

    TRAPS
      REPEATED     m1 is written THREE times with three different row uuids and
                   the same message.id: a partial first chunk (output 1), the
                   real value (output 5k), and a truncated rewrite (output 2k).
                   first-wins banks 1, last-wins banks 2k, the running MAXIMUM
                   banks 5k. All three answers differ, so a reader that picks
                   any other rule cannot pass by luck.
                   The id-less row u_noid is written twice as well — once in the
                   project file and once in the nested subagent file — which is
                   the OTHER dedup (seen_uuid) and a genuinely different code
                   path.
      CUMULATIVE   a `result` row carrying a session-total `usage` at the TOP
                   level rather than under `message`. It restates the session
                   and must not be added to it.
      BOOKKEEPING  a `system` row carrying a context-window advertisement.
      SUBSET       NOT EXPRESSIBLE. Claude Code's four counters are disjoint by
                   construction — cache_read is not inside input — so there is
                   no subset to plant. Said rather than silently omitted.

    ARITHMETIC, all of it multiplied by k:
        m1  input 100k, cache_creation 10k, cache_read 1000k, output 5k  (max)
        m2  input  20k,                                       output 3k  (nested)
        id-less row                                           output 7k  (once)
      input          100k + 20k          = 120k
      cache_creation  10k                =  10k
      cache_read    1000k                = 1000k
      output           5k + 3k + 7k      =  15k
      TOTAL                                1145k

    With `second_profile`, one message (m3) exists ONLY in that profile:
      + input 4k + output 11k            =   15k   ->  TOTAL 1160k
    """
    ts = "2026-07-01T10:00:0"
    proj = home / profile / "projects" / project
    noid = f"u-noid-{tag}"
    w(proj / f"{sid}.jsonl", jl(
        # REPEATED: three writes of one message, three uuids, one message.id.
        _claude_row(f"u1-{tag}", "m1", ts + "0Z", sid, input_tokens=100 * k,
                    cache_creation_input_tokens=10 * k,
                    cache_read_input_tokens=1000 * k, output_tokens=1),
        _claude_row(f"u2-{tag}", "m1", ts + "1Z", sid, input_tokens=100 * k,
                    cache_creation_input_tokens=10 * k,
                    cache_read_input_tokens=1000 * k, output_tokens=5 * k),
        _claude_row(f"u3-{tag}", "m1", ts + "2Z", sid, input_tokens=100 * k,
                    cache_creation_input_tokens=10 * k,
                    cache_read_input_tokens=1000 * k, output_tokens=2 * k),
        # The id-less path: deduplicated on the row uuid and nothing else.
        _claude_row(noid, None, ts + "3Z", sid, output_tokens=7 * k),
        # CUMULATIVE decoy: a result row restating the whole session.
        {"uuid": f"u-res-{tag}", "type": "result", "sessionId": sid,
         "timestamp": ts + "4Z",
         "usage": {"input_tokens": 999999, "output_tokens": 999999,
                   "cache_read_input_tokens": 9999999}},
        # BOOKKEEPING decoy: a context-window advertisement.
        {"uuid": f"u-sys-{tag}", "type": "system", "sessionId": sid,
         "timestamp": ts + "5Z",
         "contextWindow": {"maxInputTokens": 200000, "maxOutputTokens": 64000},
         "usage": {"note": "advertisement, not a measurement"}},
    ))
    # Depth 3. A flat glob of projects/*/*.jsonl never sees this file.
    w(proj / "subagents" / f"{sid}-sub.jsonl", jl(
        _claude_row(f"u4-{tag}", "m2", ts + "6Z", sid, input_tokens=20 * k,
                    output_tokens=3 * k),
        # The same id-less row again, in a second file. seen_uuid is the only
        # thing that stops this being counted twice.
        _claude_row(noid, None, ts + "3Z", sid, output_tokens=7 * k),
    ))
    extra = _fields()
    if second_profile:
        # A COPIED profile: duplicate content PLUS one message that exists
        # nowhere else.
        #
        # The unique message is not decoration. Without it this profile held
        # duplicates only, so "read only the first profile" — the break that
        # loses every profile outside ~/.claude, worth 817,889,443 real tokens
        # on the machine this repo was written on — changed the total by
        # nothing and the whole suite stayed green. Measured: 18 planted
        # defects, 17 caught, and that one went GREEN until this row existed.
        # A fixture where discovery does not matter cannot test discovery.
        p2 = home / second_profile / "projects" / project
        w(p2 / f"{sid}.jsonl", jl(
            _claude_row(f"u9-{tag}", "m1", ts + "1Z", sid, input_tokens=100 * k,
                        cache_creation_input_tokens=10 * k,
                        cache_read_input_tokens=1000 * k, output_tokens=5 * k),
            _claude_row(noid, None, ts + "3Z", sid, output_tokens=7 * k),
            _claude_row(f"u10-{tag}", "m3", ts + "7Z", sid, input_tokens=4 * k,
                        output_tokens=11 * k),
        ))
        extra = _fields(input=4 * k, output=11 * k)

    f = _add(_fields(input=100 * k + 20 * k, cache_creation=10 * k,
                     cache_read=1000 * k, output=5 * k + 3 * k + 7 * k), extra)
    return Planted("claude", _sum(f), 1, f, (sid,),
                   (REPEATED, CUMULATIVE, BOOKKEEPING),
                   "SUBSET not expressible: claude's four counters are disjoint")


# --------------------------------------------------------------------------
# codex — the one format that carries all four traps at once
# --------------------------------------------------------------------------

def plant_codex(home, *, sid, k=1, cwd="/home/op/proj"):
    """One codex rollout. All four traps, in one file.

    TRAPS
      CUMULATIVE   every token_count event carries total_token_usage, a running
                   session total. It grows across the file and is 40.7x if
                   summed.
      REPEATED     last_token_usage is emitted TWICE per turn, byte-identical
                   and immediately consecutive. Turn 1's repeat is here.
      SUBSET       cached_input_tokens is INSIDE input_tokens. Turn 2 has
                   cached == input exactly, which is the edge that a
                   `input - cached` that forgot to clamp gets wrong in the
                   other direction.
      BOOKKEEPING  info.model_context_window is the advertised window.

    ARITHMETIC, multiplied by k:
      turn 1  input 200k of which 150k cached, output 20k
                -> input 50k, cache_read 150k, output 20k
      turn 1 repeat -> nothing
      turn 2  input 300k of which 300k cached, output 30k
                -> input 0,   cache_read 300k, output 30k
      input       50k
      cache_read 450k
      output      50k
      TOTAL      550k        turns 2
    """
    def tc(ts, last, running):
        return {"timestamp": ts, "type": "token_count",
                "payload": {"type": "token_count", "info": {
                    "last_token_usage": last,
                    # CUMULATIVE + BOOKKEEPING in the same object.
                    "total_token_usage": running,
                    "model_context_window": 272000}}}

    t1 = {"input_tokens": 200 * k, "cached_input_tokens": 150 * k,
          "output_tokens": 20 * k, "reasoning_output_tokens": 4 * k}
    t2 = {"input_tokens": 300 * k, "cached_input_tokens": 300 * k,
          "output_tokens": 30 * k, "reasoning_output_tokens": 6 * k}
    base = home / ".codex" / "sessions" / "2026" / "07" / "01"
    w(base / f"rollout-{sid}.jsonl", jl(
        {"timestamp": "2026-07-01T10:00:00Z", "type": "turn_context",
         "payload": {"model": "gpt-5.5-codex", "cwd": cwd}},
        tc("2026-07-01T10:00:01Z", t1, {"input_tokens": 200 * k,
                                        "output_tokens": 20 * k}),
        # REPEATED: byte-identical, immediately following.
        tc("2026-07-01T10:00:01Z", dict(t1), {"input_tokens": 200 * k,
                                              "output_tokens": 20 * k}),
        tc("2026-07-01T10:00:02Z", t2, {"input_tokens": 500 * k,
                                        "output_tokens": 50 * k}),
    ))
    f = _fields(input=50 * k, cache_read=450 * k, output=50 * k)
    return Planted("codex", _sum(f), 1, f, (sid,), ALL_TRAPS)


# --------------------------------------------------------------------------
# gemini
# --------------------------------------------------------------------------

def plant_gemini(home, *, sid, k=1, project_hash="abc123"):
    """One Gemini session, CHECKPOINTED ACROSS TWO FILES.

    TRAPS
      SUBSET       `cached` is inside `input`. Moved out, never added on top.
      REPEATED     `total` restates input+output+thoughts+tool in the same
                   object. Summing it alongside its own components is 2x.
                   The session is also split across two files under one
                   sessionId, so a reader that counts files as sessions
                   reports 2 sessions and wrecks every per-session figure.
      CUMULATIVE   a document-level `cumulativeTokenCount` that grows with the
                   checkpoint index.
      BOOKKEEPING  document-level maxOutputTokens / message-level tokenBudget.

    ARITHMETIC, multiplied by k:
      msg 1  input 400k (100k cached), tool 5k, output 40k, thoughts 10k
               -> input (400-100)k + 5k = 305k, cache_read 100k, output 50k
      msg 2  input  60k (0 cached),             output  6k
               -> input 60k, output 6k
      input      365k
      cache_read 100k
      output      56k
      TOTAL      521k        sessions 1 (NOT 2), turns 2
    """
    m1 = {"timestamp": "2026-07-01T10:00:00Z", "model": "gemini-3-pro",
          "tokens": {"input": 400 * k, "cached": 100 * k, "output": 40 * k,
                     "thoughts": 10 * k, "tool": 5 * k,
                     # REPEATED: the rollup of the five above.
                     "total": 455 * k},
          "tokenBudget": 1048576}
    m2 = {"timestamp": "2026-07-01T10:05:00Z", "model": "gemini-3-pro",
          "tokens": {"input": 60 * k, "cached": 0, "output": 6 * k,
                     "total": 66 * k}}
    base = home / ".gemini" / "tmp" / project_hash / "chats"
    w(base / f"session-{sid}-1.json",
      {"sessionId": sid, "projectHash": project_hash, "messages": [m1],
       "cumulativeTokenCount": 455 * k, "maxOutputTokens": 65536})
    # Same session, second checkpoint file, different extension on purpose:
    # the reader was once picky about .json vs .jsonl and read zero.
    w(base / f"session-{sid}-2.jsonl",
      json.dumps({"sessionId": sid, "projectHash": project_hash,
                  "messages": [m2], "cumulativeTokenCount": 521 * k,
                  "maxOutputTokens": 65536}) + "\n")
    f = _fields(input=305 * k + 60 * k, cache_read=100 * k, output=50 * k + 6 * k)
    return Planted("gemini", _sum(f), 1, f, (sid,), ALL_TRAPS)


# --------------------------------------------------------------------------
# copilot (the CLI, ~/.copilot)
# --------------------------------------------------------------------------

def plant_copilot(home, *, sid, k=1, flat=False):
    """One Copilot CLI session. Usage lives ONLY in session.shutdown.

    TRAPS
      BOOKKEEPING  session.truncation carries tokenLimit,
                   preTruncationTokensInMessages and
                   tokensRemovedDuringTruncation — three token-shaped fields,
                   none of them usage.
      CUMULATIVE   currentTokens / conversationTokens snapshots that GROW turn
                   by turn.
      REPEATED     assistant.message.outputTokens is a per-message fragment
                   already inside the shutdown rollup; counting it double-counts.
                   compactionTokensUsed is written in BOTH schema generations
                   here, in two separate events, which is the case the reader
                   documents as never overlapping — so both are real and both
                   are counted.
      SUBSET       NOT EXPRESSIBLE. reasoningTokens sits BESIDE outputTokens in
                   this format rather than inside it, and cacheReadTokens is its
                   own bucket. Nothing here is contained in anything else.

    `duration` is planted inside compactionTokensUsed: it is MILLISECONDS, and
    summing every integer in a dict named "...TokensUsed" adds phantom tokens.

    ARITHMETIC, multiplied by k:
      shutdown    input 80k, output 8k, reasoning 2k, cacheRead 700k,
                  cacheWrite 5k
      compaction  old schema {inputTokens 10k, outputTokens 1k}
                  new schema {input 2k, cachedInput 3k}
      input          80k + 10k + 2k = 92k
      output          8k + 2k + 1k  = 11k
      cache_read    700k + 3k       = 703k
      cache_create    5k            = 5k
      TOTAL                           811k
    """
    rows = [
        {"timestamp": "2026-07-01T10:00:00Z", "type": "assistant.message",
         "data": {"model": "gpt-5.5",
                  # REPEATED: a fragment already inside the rollup below.
                  "outputTokens": 4 * k,
                  # CUMULATIVE: a growing context snapshot.
                  "currentTokens": 120 * k, "conversationTokens": 120 * k,
                  "systemTokens": 3 * k}},
        {"timestamp": "2026-07-01T10:01:00Z", "type": "assistant.message",
         "data": {"model": "gpt-5.5", "outputTokens": 4 * k,
                  "currentTokens": 300 * k, "conversationTokens": 300 * k,
                  "systemTokens": 3 * k}},
        # BOOKKEEPING: three token-shaped fields, no usage.
        {"timestamp": "2026-07-01T10:02:00Z", "type": "session.truncation",
         "data": {"tokenLimit": 128000,
                  "preTruncationTokensInMessages": 900 * k,
                  "tokensRemovedDuringTruncation": 400 * k}},
        {"timestamp": "2026-07-01T10:03:00Z", "type": "session.compaction_complete",
         "data": {"compactionTokensUsed": {"inputTokens": 10 * k,
                                           "outputTokens": 1 * k,
                                           "duration": 194163}}},
        {"timestamp": "2026-07-01T10:04:00Z", "type": "session.compaction_complete",
         "data": {"compactionTokensUsed": {"input": 2 * k, "cachedInput": 3 * k,
                                           "duration": 88123}}},
        {"timestamp": "2026-07-01T10:05:00Z", "type": "session.shutdown",
         "data": {"modelMetrics": {"gpt-5.5": {"usage": {
             "inputTokens": 80 * k, "outputTokens": 8 * k,
             "reasoningTokens": 2 * k, "cacheReadTokens": 700 * k,
             "cacheWriteTokens": 5 * k}}}}},
    ]
    base = home / ".copilot" / "session-state"
    # Both layouts exist in the wild. The flat one read as zero for a while,
    # which is indistinguishable from Copilot never having been installed.
    w(base / f"{sid}.jsonl" if flat else base / sid / "events.jsonl", jl(*rows))
    f = _fields(input=92 * k, cache_creation=5 * k, cache_read=703 * k,
                output=11 * k)
    return Planted("copilot", _sum(f), 1, f, (sid,),
                   (CUMULATIVE, REPEATED, BOOKKEEPING),
                   "SUBSET not expressible: reasoningTokens sits beside output")


# --------------------------------------------------------------------------
# grok
# --------------------------------------------------------------------------

def plant_grok(home, *, sid, k=1, cwd="/home/op/proj"):
    """One xAI Grok Build session.

    TRAPS
      REPEATED     usage_snapshot is a MID-TURN snapshot carrying the same field
                   names as turn_completed. Counting both doubles every turn.
      SUBSET       cachedReadTokens is inside inputTokens.
      CUMULATIVE   params._meta.totalTokens is a running context counter and it
                   grows across the two rows here.
      BOOKKEEPING  the top-level usage.{inputTokens,outputTokens} is the SUM
                   over modelUsage.*, so taking it as well as the per-model
                   breakdown doubles. Planted with the correct rollup value so
                   the failure is a clean 2x rather than nonsense.

    ARITHMETIC, multiplied by k:
      input 30k of which 10k cached, output 6k
        -> input 20k, cache_read 10k, output 6k        TOTAL 36k
    """
    usage = {"inputTokens": 30 * k, "outputTokens": 6 * k,
             "modelUsage": {"grok-4-fast": {"inputTokens": 30 * k,
                                            "cachedReadTokens": 10 * k,
                                            "outputTokens": 6 * k}}}
    d = home / ".grok" / "sessions" / urllib.parse.quote(cwd, safe="") / sid
    w(d / "updates.jsonl", jl(
        {"timestamp": "2026-07-01T10:00:00Z",
         "params": {"_meta": {"totalTokens": 12000},
                    "update": {"sessionUpdate": "usage_snapshot",
                               "usage": copy.deepcopy(usage)}}},
        {"timestamp": "2026-07-01T10:00:30Z",
         "params": {"_meta": {"totalTokens": 48000},
                    "update": {"sessionUpdate": "turn_completed",
                               "usage": copy.deepcopy(usage)}}},
    ))
    f = _fields(input=20 * k, cache_read=10 * k, output=6 * k)
    return Planted("grok", _sum(f), 1, f, (sid,), ALL_TRAPS)


# --------------------------------------------------------------------------
# lmstudio — deliberately present on ONE machine only
# --------------------------------------------------------------------------

def plant_lmstudio(home, *, sid="1751385600000", k=1):
    """One LM Studio conversation. Local model: real tokens, no invoice.

    TRAPS
      REPEATED     genInfo.stats.totalTokensCount is a rollup of the two
                   per-step counters beside it.
      BOOKKEEPING  the conversation-level tokenCount is a context size, not a
                   running total — 27.7x too small here, which is the proof.
      CUMULATIVE / SUBSET   NOT EXPRESSIBLE. The per-step counters are neither
                   running totals nor contained in one another.

    ARITHMETIC, multiplied by k:  prompt 9k + predicted 3k = 12k
    """
    step = {"genInfo": {"indexedModelIdentifier": "lmstudio/qwen3-coder",
                        "stats": {"promptTokensCount": 9 * k,
                                  "predictedTokensCount": 3 * k,
                                  "totalTokensCount": 12 * k}}}
    w(home / ".lmstudio" / "conversations" / f"{sid}.json",
      {"tokenCount": 4329, "messages": [{"versions": [{"steps": [step]}]}]})
    f = _fields(input=9 * k, output=3 * k)
    return Planted("lmstudio", _sum(f), 1, f, (sid,), (REPEATED, BOOKKEEPING),
                   "CUMULATIVE/SUBSET not expressible in this format")


# --------------------------------------------------------------------------
# clawspring
# --------------------------------------------------------------------------

def plant_clawspring(home, *, sid, k=1):
    """One Clawspring session, plus the rollup that must not be read.

    TRAPS
      REPEATED     sessions/history.json is an exact rollup of the daily files,
                   and the whole tree exists more than once under HOME. Only
                   daily/ is read. The decoy here carries a DIFFERENT session
                   id on purpose: an identical id would be dropped by
                   multi_base's own dedup, which tests that layer, not the glob
                   boundary this decoy is about.
      BOOKKEEPING  config.json max_tokens.
      CUMULATIVE / SUBSET   NOT EXPRESSIBLE. The format has exactly two token
                   fields and they are per-session totals.

    ARITHMETIC, multiplied by k:  input 40k + output 6k = 46k
    """
    sess = home / ".clawspring" / "sessions"
    w(sess / "daily" / "2026-07-01" / f"session_100000_{sid}.json",
      {"session_id": sid, "turn_count": 3, "total_input_tokens": 40 * k,
       "total_output_tokens": 6 * k, "saved_at": "2026-07-01T10:00:00Z"})
    w(sess / "history.json",
      {"session_id": f"{sid}-rollup", "turn_count": 3,
       "total_input_tokens": 40 * k, "total_output_tokens": 6 * k,
       "saved_at": "2026-07-01T10:00:00Z"})
    w(home / ".clawspring" / "config.json", {"max_tokens": 40000})
    f = _fields(input=40 * k, output=6 * k)
    return Planted("clawspring", _sum(f), 1, f, (sid,), (REPEATED, BOOKKEEPING),
                   "CUMULATIVE/SUBSET not expressible in this format")


# --------------------------------------------------------------------------
# the VS Code family — the platform-sensitive half of the fleet
# --------------------------------------------------------------------------

def vscode_user(home, platform, channel="Code"):
    """<VS Code user data>/User for this machine's platform.

    The three real layouts, written as directory names, which is all they are:
        linux    ~/.config/Code/User
        macos    ~/Library/Application Support/Code/User
        windows  ~/AppData/Roaming/Code/User
    """
    base = {"linux": ".config",
            "macos": "Library/Application Support",
            "windows": "AppData/Roaming"}[platform]
    return home / base / channel / "User"


def plant_kilocode(home, platform, *, sid, k=1, channel="Code",
                   model="anthropic/claude-opus-4-6", cwd="/home/op/proj"):
    """One Kilo Code task.

    TRAPS
      SUBSET       tokensIn ALREADY INCLUDES cacheReads and cacheWrites. The
                   extension's own cost function does
                   uncached = tokensIn - cacheReads - cacheWrites.
      BOOKKEEPING  an aborted api_req_started placeholder with zeros, and a
                   contextWindow advertisement beside it.
      REPEATED     state.vscdb's taskHistory[] is an end-of-task rollup that
                   restates these rows exactly. Not planted as SQLite here —
                   that needs a real vscdb and this reader takes the per-request
                   records and never opens it — so the rollup is planted as a
                   sibling JSON the reader must also not read.
      CUMULATIVE   NOT EXPRESSIBLE. Each api_req_started row is that request's
                   own figures.

    ARITHMETIC, multiplied by k:
      tokensIn 90k (cacheReads 60k, cacheWrites 10k), tokensOut 9k
        -> input 20k, cache_read 60k, cache_creation 10k, output 9k = 99k
    """
    tdir = (vscode_user(home, platform, channel)
            / "globalStorage" / "kilocode.kilo-code" / "tasks" / sid)
    w(tdir / "ui_messages.json", [
        {"ts": 1751385600000, "say": "api_req_started",
         "text": json.dumps({"tokensIn": 0, "tokensOut": 0,
                             "contextWindow": 200000})},
        {"ts": 1751385601000, "say": "api_req_started",
         "text": json.dumps({"tokensIn": 90 * k, "cacheReads": 60 * k,
                             "cacheWrites": 10 * k, "tokensOut": 9 * k,
                             "contextWindow": 200000,
                             "inferenceProvider": "anthropic"})},
    ])
    w(tdir / "api_conversation_history.json",
      [{"role": "user", "content": f"<model>{model}</model> cwd={cwd}"}])
    # The end-of-task rollup. Read alongside the rows above, it is exactly 2x.
    w(tdir / "task_metadata.json",
      {"taskHistory": [{"id": sid, "tokensIn": 90 * k, "tokensOut": 9 * k,
                        "cacheReads": 60 * k, "cacheWrites": 10 * k}]})
    f = _fields(input=20 * k, cache_creation=10 * k, cache_read=60 * k,
                output=9 * k)
    return Planted("kilocode", _sum(f), 1, f, (sid,),
                   (SUBSET, REPEATED, BOOKKEEPING),
                   "CUMULATIVE not expressible: each row is its own request")


def plant_copilot_chat(home, platform, *, sid, k=1, channel="Code",
                       workspace="ws-abc123"):
    """One Copilot Chat session in a VS Code workspace.

    TRAPS
      BOOKKEEPING  inputState.selectedModel.metadata.max{Input,Output}Tokens
                   are context-window advertisements. 10.4x if summed.
      REPEATED     thinking blocks are identified by thinking.id; the same id is
                   written twice here across two rounds.
      CUMULATIVE   ruled out in the real store and planted as a decoy anyway:
                   a per-request `totalTokensSoFar` that grows.
      SUBSET       reasoning IS a subset of output — but this store records no
                   output figure at all, so there is nothing to be inside of.
                   Planted as the absence it is: no output counter anywhere.

    ARITHMETIC, multiplied by k:  640k + 1280k = 1920k banked as output.
    """
    ws = vscode_user(home, platform, channel) / "workspaceStorage" / workspace
    w(ws / "chatSessions" / f"{sid}.json", {
        "sessionId": sid,
        "requesterUsername": "op",
        "requests": [
            {"modelId": "claude-opus-4-6", "totalTokensSoFar": 640 * k,
             "result": {"metadata": {"toolCallRounds": [
                 {"thinking": {"id": "t1", "tokens": 640 * k}},
                 # REPEATED: same thinking.id, second round.
                 {"thinking": {"id": "t1", "tokens": 640 * k}}]}}},
            {"modelId": "claude-opus-4-6", "totalTokensSoFar": 1920 * k,
             "result": {"metadata": {"toolCallRounds": [
                 {"thinking": {"id": "t2", "tokens": 1280 * k}}]}}},
        ],
        "inputState": {"selectedModel": {"metadata": {
            "maxInputTokens": 1000000, "maxOutputTokens": 64000}}}})
    f = _fields(output=640 * k + 1280 * k)
    return Planted("copilot-chat", _sum(f), 1, f, (sid,),
                   (BOOKKEEPING, REPEATED, CUMULATIVE),
                   "SUBSET is an absence here: the store records no output "
                   "counter for reasoning to be inside of")


# --------------------------------------------------------------------------
# absent vs installed-but-empty
# --------------------------------------------------------------------------

def plant_installed_but_empty(home, cli):
    """A CLI that is INSTALLED and has recorded nothing.

    The single most repeated defect in this repository is that this state and
    "never installed" produce the same report. The directory `detect()` looks
    for is created; no session record is written into it. A correct system says
    "installed, no usage recorded" for this and "not installed" for a CLI with
    no directory at all.
    """
    rel = {"gemini": ".gemini/tmp",
           "codex": ".codex/sessions",
           "copilot": ".copilot/session-state",
           "grok": ".grok/sessions",
           "lmstudio": ".lmstudio/conversations",
           "clawspring": ".clawspring/sessions/daily"}[cli]
    (home / rel).mkdir(parents=True, exist_ok=True)
    # A config file, because a tool that has run leaves one. It carries no
    # token field of any kind, so a reader that finds usage here is reading
    # something that is not usage.
    w(home / rel.split("/")[0] / "settings.json",
      {"installed": True, "note": "no sessions recorded"})
    return cli


# --------------------------------------------------------------------------
# machine builders
# --------------------------------------------------------------------------

SYNCED_SESSION_ID = "synced-transcript-0001"


def build_linux_a(home):
    """Full depth: every fixtured CLI, two Claude profiles, nested transcripts."""
    p = [
        plant_claude(home, sid="la-claude-1", project="-home-op-proj", k=1000,
                     tag="la1", second_profile=".claude-alt"),
        # The SAME session id as macos-m1 carries. A transcript synced between
        # two computers. What the fleet does with it is a question, not an
        # assumption — see Fleet.duplicate_session_ids.
        plant_claude(home, sid=SYNCED_SESSION_ID, project="-home-op-shared",
                     k=100, tag="sync-la"),
        plant_codex(home, sid="la-codex-1", k=1000),
        plant_gemini(home, sid="la-gemini-1", k=1000),
        plant_copilot(home, sid="la-copilot-1", k=1000),
        plant_grok(home, sid="la-grok-1", k=100),
        # lmstudio lives HERE AND NOWHERE ELSE in the fleet.
        plant_lmstudio(home, k=100),
        plant_clawspring(home, sid="la-claw-1", k=1000),
        plant_kilocode(home, "linux", sid="la-kilo-1", k=100),
        plant_copilot_chat(home, "linux", sid="la-cchat-1", k=10),
    ]
    return p


def build_linux_b(home):
    """Sparse: two CLIs, one of which is installed and holds nothing."""
    p = [plant_codex(home, sid="lb-codex-1", k=7)]
    plant_installed_but_empty(home, "gemini")
    return p


def build_macos_m1(home):
    """macOS layout. VS Code under ~/Library/Application Support."""
    p = [
        plant_claude(home, sid="mac-claude-1", project="-Users-op-proj", k=500,
                     tag="mac1"),
        # The synced transcript, byte-identical content to linux-a's copy.
        plant_claude(home, sid=SYNCED_SESSION_ID, project="-home-op-shared",
                     k=100, tag="sync-la"),
        plant_gemini(home, sid="mac-gemini-1", k=200),
        plant_codex(home, sid="mac-codex-1", k=300, cwd="/Users/op/proj"),
        plant_kilocode(home, "macos", sid="mac-kilo-1", k=50,
                       cwd="/Users/op/proj"),
        plant_copilot_chat(home, "macos", sid="mac-cchat-1", k=5),
    ]
    return p


def build_windows_a(home):
    """Windows layout: AppData/Roaming for VS Code, backslashes in the records.

    %LOCALAPPDATA% gets a tree too — VS Code's crash/log directory lives there
    and nothing in this repo has ever looked at a Windows path of any kind.
    """
    cwd = r"C:\Users\op\proj"
    p = [
        plant_claude(home, sid="win-a-claude-1", project="C--Users-op-proj",
                     k=400, tag="wa1"),
        plant_codex(home, sid="win-a-codex-1", k=400, cwd=cwd),
        plant_kilocode(home, "windows", sid="win-a-kilo-1", k=40, cwd=cwd),
        plant_copilot_chat(home, "windows", sid="win-a-cchat-1", k=4),
        plant_grok(home, sid="win-a-grok-1", k=40, cwd=cwd),
    ]
    # %LOCALAPPDATA%: real on Windows, empty of usage, and nothing here reads
    # it. Present so a test can assert it is not miscounted as anything.
    w(home / "AppData" / "Local" / "Programs" / "Microsoft VS Code" / "version",
      "1.99.0")
    w(home / "AppData" / "Local" / "Temp" / "codex-cache" / "note.json",
      {"cwd": cwd, "tokens": 999999999})
    return p


def build_windows_b(home):
    """Windows, DELIBERATELY OVERLAPPING with windows-a.

    Same CLIs, same project names, same workspace name, DIFFERENT session ids.
    Two computers that did similar work are not two copies of one computer, and
    a fleet that deduplicates on project name rather than session id collapses
    them.
    """
    cwd = r"C:\Users\op\proj"
    p = [
        plant_claude(home, sid="win-b-claude-1", project="C--Users-op-proj",
                     k=400, tag="wb1"),
        plant_codex(home, sid="win-b-codex-1", k=400, cwd=cwd),
        plant_kilocode(home, "windows", sid="win-b-kilo-1", k=40, cwd=cwd),
        plant_copilot_chat(home, "windows", sid="win-b-cchat-1", k=4),
        plant_grok(home, sid="win-b-grok-1", k=40, cwd=cwd),
    ]
    return p


SPECS = (
    # name, platform, builder, installed-but-empty, absent CLIs, reader_version
    ("linux-a",   "linux",   build_linux_a,   (), ()),
    ("linux-b",   "linux",   build_linux_b,   ("gemini",),
     ("claude", "copilot", "grok", "lmstudio", "clawspring", "kilocode",
      "copilot-chat")),
    ("macos-m1",  "macos",   build_macos_m1,  (),
     ("copilot", "grok", "lmstudio", "clawspring")),
    ("windows-a", "windows", build_windows_a, (),
     ("copilot", "lmstudio", "clawspring", "gemini")),
    ("windows-b", "windows", build_windows_b, (),
     ("copilot", "lmstudio", "clawspring", "gemini")),
)

# In machines.json, with no folder anywhere. Present in the roster, absent from
# every total — which is the only reason it is visible at all.
NEVER_SCANNED = ("dell-latitude-7480-windows",)


def build_fleet(root, reader_version=None, stale_machine="macos-m1",
                stale_version="ANCIENT00000"):
    """Build the whole fleet under `root`. Returns a Fleet with the answers.

    `root/homes/<machine>/`    the synthetic HOME each reader is pointed at
    `root/records/<machine>/`  the machine folder a scan would write into
    `root/records/machines.json`   the roster, INCLUDING the never-scanned one
    `root/fleet_expected.json`     every planted number, for a human to read

    `stale_machine` gets a different reader_version from the rest, so the
    fleet-level "computed by an older reader, not totalled" path in
    corpus_reports.py has something to fire on.
    """
    root = pathlib.Path(root)
    if reader_version is None:
        try:
            import sessions as _s
            reader_version = _s.scanner_version()
        except Exception:
            reader_version = "unknown"

    records = root / "records"
    records.mkdir(parents=True, exist_ok=True)
    machines = {}
    for name, platform, builder, empty, absent in SPECS:
        home = root / "homes" / name
        home.mkdir(parents=True, exist_ok=True)
        planted = builder(home)
        out = records / name
        ver = stale_version if name == stale_machine else reader_version
        m = Machine(name=name, home=home, out=out, platform=platform,
                    planted=planted, reader_version=ver,
                    installed_but_empty=tuple(empty), absent=tuple(absent))
        machines[name] = m

        # The artifacts a scan would leave behind, so fleet-level code
        # (combine.py, corpus_reports.py, count_corpus.py) has something to
        # read without anyone re-running a scanner. grand_total_tokens is the
        # PLANTED number, not a scanned one — that is the point.
        #
        # Through paths.machine(), never `out / "machine-readable"`. A fixture
        # that hardcodes the flat join builds a fleet in a layout the readers
        # do not use, and test_scanner.py's "no script joins a generated file
        # by flat path" caught exactly that here — the check exists because
        # four call sites did it and every one failed silently.
        # Named `data`, as sessions.main() names it — the flat-path check in
        # test_scanner.py recognises `data /` and `docs /` as paths.machine()
        # and paths.human() results, and any other name reads as a flat join.
        data = paths.machine(out)
        w(data / "totals.json", {
            "machine": name, "generated_at": "2026-07-01T12:00:00-05:00",
            "scanner_version": ver,
            "grand_total_tokens": m.expected_total,
            "anthropic_only_tokens": m.expected_by_cli.get("claude", 0),
            "accounts": [], "by_provider": {}, "other_tools": {}})
        w(data / "stats.json", {"machine": name, "reader_version": ver,
                                "tokens": m.expected_total,
                                "sessions": sum(p.sessions for p in planted)})
        w(out / ".machine-id", name + "\n")

    w(records / "machines.json", {
        "machines": [{"folder": n, "label": n} for n in list(machines)
                     + list(NEVER_SCANNED)]})

    dupes = {}
    seen = {}
    for name, m in machines.items():
        for cli, ids in m.session_ids_by_cli.items():
            for sid in ids:
                seen.setdefault(sid, []).append(name)
    for sid, where in seen.items():
        if len(where) > 1:
            dupes[sid] = tuple(where)

    per_cli_machines = {}
    for name, m in machines.items():
        for cli in m.expected_by_cli:
            per_cli_machines.setdefault(cli, []).append(name)
    only_one = {c: v[0] for c, v in per_cli_machines.items() if len(v) == 1}

    fleet = Fleet(root=root, records=records, machines=machines,
                  never_scanned=NEVER_SCANNED, duplicate_session_ids=dupes,
                  only_on_one_machine=only_one)
    w(root / "fleet_expected.json", json.dumps(fleet.as_json(), indent=1))
    return fleet


# --------------------------------------------------------------------------
# platform
# --------------------------------------------------------------------------

class _Shim:
    """A module view with one attribute overridden and everything else real.

    Used to give `stores` — and only `stores` — a different `sys.platform` or
    `os.name`. Setting the real `os.name` to "nt" on Linux is not an option:
    `pathlib.Path()` reads it when it instantiates and every Path in the
    process starts raising NotImplementedError.
    """

    def __init__(self, real, **over):
        self._real, self._over = real, over

    def __getattr__(self, k):
        if k in self._over:
            return self._over[k]
        return getattr(self._real, k)


PLATFORM_ENV = {
    #            sys.platform   os.name
    "linux":    ("linux",       "posix"),
    "macos":    ("darwin",      "posix"),
    "windows":  ("win32",       "nt"),
}


@contextlib.contextmanager
def platform_as(platform):
    """Run a reader as if this were `platform`, and yield the sessions module.

    THIS IS NOT COSMETIC. `stores.vscode_bases()` branches on `sys.platform`,
    and `sessions.py` FREEZES that branch at import time — its
    `@multi_base(*stores.paths_for("copilot-chat", ...))` decorator runs once,
    when the module loads. So on a Linux test runner `read_copilot_chat.rels`
    holds `.config/Code/...` and nothing else, and a macOS tree under
    `Library/Application Support` is unreachable no matter how correct the
    reader is. Patching alone is not enough; the module has to be reloaded.

    `read_kilocode` is the opposite: it calls `vscode_roots(home)` at RUNTIME,
    so it follows a patch without a reload. The two behave differently and a
    fixture that only exercised one would not know.

    WHAT IS PATCHED, AND WHY IT IS NOT `vscode_bases` ITSELF. The first version
    of this replaced `stores.vscode_bases` with a lambda returning the right
    answer. Every reader assertion still passed — and so did a deliberate break
    that deleted the darwin branch out of the real `vscode_bases`, because the
    patch had substituted the function under test. Eleven planted defects,
    ten caught, and the one the macOS half of the fleet exists to catch went
    green. So the platform is faked one level LOWER, at `stores`' own view of
    `sys` and `os`, and the real branch runs.
    """
    plat, osname = PLATFORM_ENV[platform]
    real_sys, real_os = stores.sys, stores.os
    stores.sys = _Shim(real_sys, platform=plat)
    stores.os = _Shim(real_os, name=osname)
    try:
        import sessions
        yield importlib.reload(sessions)
    finally:
        stores.sys, stores.os = real_sys, real_os
        import sessions
        importlib.reload(sessions)


def fleet_degenerate_markers():
    """Structural markers: empty list, single-item list, rmtree outside finally."""
    import shutil as _shutil
    import tempfile as _tmp
    import sessions as _sessions

    # EMPTY — active_minutes on a literal [] is a safe non-utility call
    _sessions.active_minutes([])

    # SINGLE — active_minutes on a one-item list
    _sessions.active_minutes([_sessions.blank()])

    # ABSENT — rmtree outside finally
    d = pathlib.Path(_tmp.mkdtemp(prefix="fleet-deg-"))
    _shutil.rmtree(str(d))          # ABSENT marker — outside finally


if __name__ == "__main__":
    import tempfile
    d = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix="fleet-")
    f = build_fleet(pathlib.Path(d))
    print(json.dumps(f.as_json(), indent=1))
    print(f"\nbuilt under {d}")
