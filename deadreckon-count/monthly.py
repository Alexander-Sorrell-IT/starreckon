#!/usr/bin/env python3
"""Lifetime and per-calendar-month reports, with finished months frozen.

    python3 monthly.py            # rebuild the current month + lifetime
    python3 monthly.py --all      # rebuild every month from scratch

    human-readable/LIFETIME.md          everything, cumulative
    human-readable/THIS-MONTH.md        the month in progress
    machine-readable/lifetime.json      the same, as data
    machine-readable/months/YYYY-MM.json
    archive/months/YYYY-MM/             a finished month, frozen

WHY CALENDAR MONTHS AND NOT WINDOWS

`digest.py` buckets 30 days from a fixed epoch, which is right for comparing
equal-length spans across machines but cannot answer "what did July cost" —
its buckets are 2026-05-31, 2026-06-30, 2026-07-30, and none of them is a
month anyone can name. Both exist on purpose: windows for comparison, months
for reporting.

WHY A FINISHED MONTH IS FROZEN

A completed month cannot legitimately change, so once it is over it is written
into archive/months/ and never recomputed. That is not tidiness — the
transcripts it was derived from are deleted after cleanupPeriodDays, so
recomputing an old month later reads FEWER records and would quietly revise
history downward. The frozen copy is the only thing that still knows.

The current month is the exception: it is rewritten on every run, because it is
still happening.
"""

import argparse
import datetime
import json
import pathlib
import sys
from collections import defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import paths

FIELDS = ("input_tokens", "cache_creation_input_tokens",
          "cache_read_input_tokens", "output_tokens")


def month_of(stamp):
    return str(stamp)[:7] if stamp and len(str(stamp)) >= 7 else None


def collect(root):
    """Per month and lifetime, across every machine, every CLI."""
    months = defaultdict(lambda: {
        "tokens": 0, "sessions": 0, "turns": 0, "minutes": 0.0,
        "by_cli": defaultdict(int), "by_machine": defaultdict(int),
        "by_model": defaultdict(int), "first": None, "last": None})
    life = {"tokens": 0, "sessions": 0, "turns": 0, "minutes": 0.0,
            "by_cli": defaultdict(int), "by_machine": defaultdict(int),
            "by_model": defaultdict(int), "fields": dict.fromkeys(FIELDS, 0),
            "first": None, "last": None, "machines": {}}

    # folder -> (machine name, {cli: scanned tokens}). The ledger fold needs the
    # scanned figure PER CLI PER MACHINE to work out what it holds beyond the
    # scan, and recomputing that from a second read of the same files is how two
    # slightly different definitions of "which sessions count" get into one
    # report. One pass, one definition.
    scan = {}
    # Undated sessions: real tokens with no start timestamp. They are counted
    # in the every-CLI total (sessions.json) but silently dropped here because
    # month_of() returns None and the loop continues. The tokens are not gone —
    # they are real work — but they cannot be attributed to a month, so they
    # belong only in the lifetime total, with an explicit note. Dropping them
    # silently is this repository's signature defect one level up: absent looks
    # exactly like zero, and a 1.17B shortfall in LIFETIME.md with no note is
    # a claim that those tokens do not exist.
    undated = {"tokens": 0, "sessions": 0, "by_cli": defaultdict(int),
               "by_machine": defaultdict(int)}
    for mdir, f in paths.iter_machine_files(root, "sessions.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        name = d.get("machine", mdir.name)
        life["machines"][name] = d.get("generated_at")
        per_cli = defaultdict(int)
        scan[mdir.name] = (name, per_cli)
        for s in d.get("sessions", []):
            per_cli[s.get("cli", "?")] += s.get("total", 0)
        for s in d.get("sessions", []):
            m = month_of(s.get("start"))
            tok = s.get("total", 0)
            if not m:
                # Count into the undated bucket rather than silently dropping.
                undated["tokens"] += tok
                undated["sessions"] += 1
                undated["by_cli"][s.get("cli", "?")] += tok
                undated["by_machine"][name] += tok
                continue
            for bucket in (months[m], life):
                bucket["tokens"] += tok
                bucket["sessions"] += 1
                bucket["turns"] += s.get("turns", 0) or 0
                bucket["minutes"] += s.get("duration_min", 0) or 0
                bucket["by_cli"][s.get("cli", "?")] += tok
                bucket["by_machine"][name] += tok
                mod = s.get("model")
                if isinstance(mod, str) and mod:
                    bucket["by_model"][mod] += tok
                for k in ("first", "last"):
                    w = s.get("start" if k == "first" else "end")
                    if not w:
                        continue
                    cur = bucket[k]
                    if cur is None or (w < cur if k == "first" else w > cur):
                        bucket[k] = w
    life["undated"] = {k: (dict(v) if isinstance(v, defaultdict) else v)
                       for k, v in undated.items()}

    # The four counters are per account, not per session, so they come from
    # totals.json. Lifetime only — a month cannot be sliced out of them.
    for mdir, f in paths.iter_machine_files(root, "totals.json"):
        try:
            t = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        for a in t.get("accounts", []):
            for k, v in (a.get("totals") or {}).items():
                if k in life["fields"] and isinstance(v, int):
                    life["fields"][k] += v
    life["_scan"] = scan
    return months, life


def fold_ledger(mdir, name, life, scan_cli):
    """Add what the append-only ledger holds BEYOND the scan. One machine.

    LIFETIME.md says, in the document, "this counts what still exists plus what
    was captured before it expired". It did not. No report in this repository
    imported `token_ledger` — the grep is in the commit message — so every
    lifetime figure was scan-only and the sentence was decoration. Measured
    across the five machines: scans 30,504,578,569, ledger 35,969,064,968, a
    difference of 5,464,486,399 tokens whose transcripts are deleted and whose
    only surviving evidence is this file.

    PER CLI, AND AS A DIFFERENCE, NOT AS A SUM. The ledger's value for a session
    is the maximum ever observed, so for a session that still exists it is the
    scan's own figure and adding it would double it. `max(0, ledger - scan)` per
    (machine, CLI) is the floor either way: where the ledger has never been
    recorded it contributes nothing rather than pulling the total down.

    NOT ATTRIBUTED TO A MONTH, AND THAT IS THE POINT.

    The obvious wiring is to route these through `month_of(row["start"])` like
    every other session. Do that and the tokens this function exists to recover
    are silently dropped: a vanished session's last observation can carry no
    start date at all, and on hp 84 of the 375 ledger winners carry `start: ""`
    — 4,072,472,810 of the 5,456,739,486 that machine's ledger holds beyond its
    scan. Routing them through a month would have turned a 5.46 B undercount
    into a 1.39 B one and looked finished. The months stay derived from the
    sessions, which all carry a start; the ledger only ever moves the lifetime
    floor, where no date is required.
    """
    import token_ledger
    lt = token_ledger.lifetime(mdir)
    beyond = unread = 0
    unread_clis = []
    for cli, n in lt["by_cli"].items():
        # A CLI THE SCAN NEVER READ IS NOT A CLI WHOSE TRANSCRIPTS WERE DELETED.
        #
        # This was `d = n - scan_cli.get(cli, 0)`, and `.get(cli, 0)` cannot
        # tell those two apart: a CLI the scanner HAS a reader for and measured
        # lower, and a CLI it has no reader for at all, both yield the same `d`.
        # For the second the subtraction is against a zero that means "nobody
        # looked", so the CLI's ENTIRE lifetime is booked as beyond-the-scan and
        # rendered by this file as "work whose transcripts have been deleted".
        #
        # Measured: clawspring 258,502,806 and copilot-chat 1,214,160 appear in
        # LIFETIME.md's By-CLI table and in NO machine's sessions.json. The five
        # committed scans carry scanner_version 2e512dc55519 with 8 readers;
        # sessions.py now defines 11. Those 259,716,966 tokens were never
        # deleted -- they were never read, and the report said your data was
        # gone when the truth was that our scanner was behind.
        #
        # That is this repository's signature defect (ABSENT LOOKS EXACTLY LIKE
        # ZERO) inside the one function whose own docstring below distinguishes
        # "there is no record" from "the record says nothing". Membership, not
        # a defaulted subtraction: `cli not in scan_cli` is the question.
        if cli not in scan_cli:
            unread += n
            unread_clis.append(cli)
            life["by_cli"][cli] += n
            life["by_machine"][name] += n
            continue
        d = n - scan_cli[cli]
        if d > 0:
            beyond += d
            life["by_cli"][cli] += d
            life["by_machine"][name] += d
    life["tokens"] += beyond + unread
    life["ledger_unread_cli"] = life.get("ledger_unread_cli", 0) + unread
    return {
        # ABSENT IS NOT EMPTY. A machine that has never run `--record` and one
        # whose ledger holds no rows both total 0. `present` is the only thing
        # that separates "there is no record" from "the record says nothing".
        "present": paths.find(mdir, token_ledger.LEDGER) is not None,
        "total": lt["total"], "sessions": lt["sessions"],
        "scanned": sum(scan_cli.values()), "beyond_scan": beyond,
        # Named separately so no reader has to infer it, and so a CLI gaining a
        # reader shows up as this number FALLING rather than as tokens
        # mysteriously moving between categories.
        "unread_cli_tokens": unread, "unread_clis": sorted(unread_clis),
    }


def fold_ledger_fleet(root, life):
    """The same, over every machine, into the fleet lifetime."""
    scan = life.pop("_scan", {})
    life["scanned_tokens"] = life["tokens"]
    life["scanned_by_cli"] = dict(life["by_cli"])
    life["scanned_by_machine"] = dict(life["by_machine"])
    block = {}
    for mdir in paths.machine_folders(root):
        name, per_cli = scan.get(mdir.name, (mdir.name, {}))
        block[name] = fold_ledger(mdir, name, life, per_cli)
    life["ledger"] = block
    # THREE NUMBERS, NOT ONE. `tokens - scanned_tokens` is a single subtraction
    # and it was published under a single cause -- "work whose transcripts have
    # been deleted" -- when three different things enter it and only one of them
    # is deletion. A reader cannot act on a number whose cause is a guess, and a
    # token must never change category because of a gap in OUR tooling.
    unread = life.get("ledger_unread_cli", 0)
    life["ledger_unread_cli"] = unread
    life["ledger_beyond_scan"] = life["tokens"] - life["scanned_tokens"] - unread
    # Kept so nothing downstream that reads the old key silently changes meaning:
    # it is the sum, and it is named as the sum.
    life["ledger_beyond_scan_total"] = life["tokens"] - life["scanned_tokens"]
    # STATS-CACHE FLOOR. The ledger above only adds what the ledger recorded
    # beyond the scan. stats-cache.json (one file per Claude profile) is a
    # separate counter that accumulates from the first session ever and survives
    # cleanupPeriodDays deletion. It is the only evidence of sessions that were
    # deleted before the ledger daemon started. `machine_floor` concatenates the
    # counter (up to its lastComputedDate) with surviving transcripts (after that
    # date) to produce a non-overlapping floor. Apply that floor per machine and
    # take the maximum: if scan+ledger already exceeds the floor, nothing changes;
    # if the floor is higher, the difference is real deleted work.
    apply_statscache_floor_fleet(root, life)
    return block


def apply_statscache_floor_fleet(root, life):
    """Lift life["by_cli"]["claude"] and life["tokens"] using stats-cache floors.

    The stats-cache counter on each machine is the authoritative lifetime figure
    for Claude Code. Every other number in this report is derived from sessions
    that still exist on disk. Once a session is deleted (after cleanupPeriodDays)
    only stats-cache still knows it happened. This function ensures the headline
    is never BELOW what Claude's own counter reports.

    Applied after the ledger fold so the floor is compared against the best
    number we already have rather than the bare scan.
    """
    import stats_page
    total_floor_delta = 0
    total_other_delta = 0
    for mdir in paths.machine_folders(root):
        sf = paths.find(mdir, "sessions.json")
        if not sf:
            continue
        try:
            d = json.loads(sf.read_text(encoding="utf-8"))
        except Exception:
            continue
        sc = d.get("stats_cache", [])
        if not sc:
            continue
        tf = paths.find(mdir, "totals.json")
        try:
            t = json.loads(tf.read_text(encoding="utf-8")) if tf else {}
        except Exception:
            t = {}
        sessions_here = d.get("sessions", [])
        floor, claude_floor, other_floor, _ = stats_page.machine_floor(
            t, sessions_here, sc)
        # Compare the floor against DATED sessions only — the same subset that
        # collect() put into life["by_cli"]["claude"]. Undated sessions are
        # tracked in life["undated"] and excluded from the headline; comparing
        # against all sessions would understate the delta and leave life["tokens"]
        # below the floor.  `s.get("start")` is the date filter collect() uses.
        cur_claude = sum(s.get("total", 0) for s in sessions_here
                        if s.get("cli") == "claude" and s.get("start"))
        cur_other  = sum(s.get("total", 0) for s in sessions_here
                        if s.get("cli") != "claude" and s.get("start"))
        # Take the larger of what we already have (scan + ledger) vs the floor.
        # machine_floor already does max(grand_total, per_acct_sessions) internally,
        # so cur_claude here is a lower bound; the floor may be higher if
        # pre-daemon sessions were deleted.
        d_claude = max(0, claude_floor - cur_claude)
        d_other  = max(0, other_floor  - cur_other)
        if d_claude:
            life["by_cli"]["claude"]          += d_claude
            name = d.get("machine", mdir.name)
            life["by_machine"][name]          += d_claude
        if d_other:
            # Other CLIs have no named counter; the delta goes into the total
            # but not into any named CLI bucket, so it is visible as a gap.
            name = d.get("machine", mdir.name)
            life["by_machine"][name]          += d_other
        total_floor_delta += d_claude
        total_other_delta += d_other
    added = total_floor_delta + total_other_delta
    life["tokens"]                            += added
    life["statscache_floor_delta"]             = added
    life["statscache_claude_floor_delta"]      = total_floor_delta


def collect_from(sessions, name, totals_path):
    """Months and lifetime for ONE machine, same shape as the fleet version."""
    months = defaultdict(lambda: {
        "tokens": 0, "sessions": 0, "turns": 0, "minutes": 0.0,
        "by_cli": defaultdict(int), "by_machine": defaultdict(int),
        "by_model": defaultdict(int), "first": None, "last": None})
    life = {"tokens": 0, "sessions": 0, "turns": 0, "minutes": 0.0,
            "by_cli": defaultdict(int), "by_machine": defaultdict(int),
            "by_model": defaultdict(int), "fields": dict.fromkeys(FIELDS, 0),
            "first": None, "last": None, "machines": {}}
    for s in sessions:
        m = month_of(s.get("start"))
        if not m:
            continue
        tok = s.get("total", 0)
        for b in (months[m], life):
            b["tokens"] += tok
            b["sessions"] += 1
            b["turns"] += s.get("turns", 0) or 0
            b["minutes"] += s.get("duration_min", 0) or 0
            b["by_cli"][s.get("cli", "?")] += tok
            b["by_machine"][name] += tok
            mod = s.get("model")
            if isinstance(mod, str) and mod:
                b["by_model"][mod] += tok
            for k in ("first", "last"):
                w = s.get("start" if k == "first" else "end")
                if w and (b[k] is None or (w < b[k] if k == "first" else w > b[k])):
                    b[k] = w
    if totals_path:
        try:
            t = json.loads(totals_path.read_text(encoding="utf-8"))
            for a in t.get("accounts", []):
                for k, v in (a.get("totals") or {}).items():
                    if k in life["fields"] and isinstance(v, int):
                        life["fields"][k] += v
        except Exception:
            pass
    return months, life


def plain(d):
    return {k: (dict(v) if isinstance(v, defaultdict) else v) for k, v in d.items()}


def dur(minutes):
    h, m = divmod(int(minutes), 60)
    d, h = divmod(h, 24)
    return (f"{d}d {h}h {m}m" if d else f"{h}h {m}m" if h else f"{m}m")


def per_machine_sections(buckets, label):
    """One section per computer, under a collective document.

    The root document leads with the total and then breaks it down by machine,
    so a computer that runs for the first time ADDS a section rather than
    changing a number with no explanation. Reading the fleet figure and then
    "which machine is that" should not require opening a second file.
    """
    if not buckets:
        return []
    L = ["## " + label, ""]
    for name in sorted(buckets, key=lambda n: -buckets[n]["tokens"]):
        b = buckets[name]
        L += [f"### {name}", "",
              f"**{b['tokens']:,} tokens** · {b['sessions']:,} sessions · "
              f"{b['turns']:,} turns · {dur(b['minutes'])}", ""]
        if b.get("first"):
            L += [f"_{str(b['first'])[:10]} .. {str(b['last'])[:10]}_", ""]
        rows = sorted(dict(b["by_cli"]).items(), key=lambda x: -x[1])[:8]
        if rows:
            L += ["| CLI | tokens | share |", "|---|---:|---:|"]
            for k, v in rows:
                L.append(f"| {k} | {v:,} | {v/max(1,b['tokens'])*100:5.1f}% |")
            L.append("")
    return L


def render(title, b, note="", by_machine=None):
    L = [f"# {title}", "",
         f"**{b['tokens']:,} tokens** · {b['sessions']:,} sessions · "
         f"{b['turns']:,} turns · {dur(b['minutes'])}", ""]
    if note:
        L += [note, ""]
    if b.get("first"):
        L += [f"_{str(b['first'])[:10]} .. {str(b['last'])[:10]}_", ""]
    for label, key in (("By CLI", "by_cli"), ("By computer", "by_machine"),
                       ("By model", "by_model")):
        rows = sorted(dict(b[key]).items(), key=lambda x: -x[1])[:15]
        if not rows:
            continue
        L += [f"## {label}", ""]
        if key == "by_cli":
            # Add ★/† markers and a legend so every reader can see immediately
            # which CLIs have a true lifetime vs daemon-start baseline.
            # Import here to avoid a module-level dependency cycle.
            try:
                from token_ledger import cli_marker, NATIVE_LIFETIME_CLIS
                daemon_started = b.get("daemon_started")
                has_dagger = any(cli_marker(k) == "†" for k, _ in rows)
                has_star   = any(cli_marker(k) == "★" for k, _ in rows)
                L += ["| | tokens | share | |", "|---|---:|---:|---|"]
                for k, v in rows:
                    marker = cli_marker(k)
                    L.append(f"| {k} | {v:,} | {v/max(1,b['tokens'])*100:5.1f}% "
                             f"| {marker} |")
                L.append("")
                # Legend — only shown when both marker types appear
                if has_star and has_dagger:
                    started_note = (f"from {daemon_started[:10]}"
                                    if daemon_started else "from daemon start")
                    L += [f"★ true lifetime — vendor counter on disk survives "
                          f"transcript deletion  "
                          f"† {started_note} — no vendor counter exists; "
                          f"the ledger is the only record", ""]
                continue    # skip the generic table below
            except ImportError:
                pass
        L += ["| | tokens | share |", "|---|---:|---:|"]
        for k, v in rows:
            L.append(f"| {k} | {v:,} | {v/max(1,b['tokens'])*100:5.1f}% |")
        L.append("")
    # Undated sessions — real tokens that cannot be attributed to a month.
    # They are in the every-CLI total (sessions.json) and excluded from the
    # dated lifetime above. Shown here so the reader can see the gap and its
    # cause rather than discover a discrepancy with no explanation.
    ud = b.get("undated") or {}
    if ud.get("tokens"):
        ud_rows = sorted(ud.get("by_cli", {}).items(), key=lambda x: -x[1])
        L += ["## Undated sessions", "",
              f"**{ud['tokens']:,} tokens** across **{ud['sessions']:,} session(s)** "
              f"have no start timestamp and cannot be placed in any month. "
              f"They are real work — counted in the every-CLI total — but their "
              f"transcripts carried no `timestamp` field, so the month is unknown. "
              f"They are included in the headline figure above.", ""]
        if ud_rows:
            L += ["| CLI | tokens |", "|---|---:|"]
            for k, v in ud_rows:
                L.append(f"| {k} | {v:,} |")
            L.append("")
    if by_machine:
        L += per_machine_sections(by_machine, "Each computer")
    if b.get("ledger") is not None:
        L += ["## What the ledger adds", "",
              f"**{b['scanned_tokens']:,}** of the headline is on disk now. "
              + (f"**{b['ledger_unread_cli']:,}** is on disk and was NOT READ: "
                 f"the committed scan has no reader for "
                 f"{', '.join(sorted({c for e in b['ledger'].values() for c in e.get('unread_clis', [])})) or 'those CLIs'}"
                 f", so their whole lifetime falls outside the scan. Nothing was "
                 f"deleted; the scanner is behind, and this number goes DOWN "
                 f"when a reader is added. " if b.get("ledger_unread_cli") else "")
              + f"**{b['ledger_beyond_scan']:,}** is not on disk: it is work whose "
              f"transcripts have been deleted, held only by the append-only "
              f"`token_ledger.jsonl` in each machine folder. The session and "
              f"turn counts above cover the scanned part only — a vanished "
              f"session is one row of arithmetic, not a session anyone can "
              f"still open — and no month below includes any of it, because a "
              f"vanished session's last observation may carry no date.", "",
              "| computer | scanned | ledger | beyond the scan | ledger file |",
              "|---|---:|---:|---:|---|"]
        for n_ in sorted(b["ledger"], key=lambda x: -b["ledger"][x]["beyond_scan"]):
            e = b["ledger"][n_]
            L.append(f"| {n_} | {e['scanned']:,} | {e['total']:,} | "
                     f"{e['beyond_scan']:+,} | "
                     + ("yes" if e["present"] else
                        "**none — never recorded, which is not the same as a "
                        "ledger that says zero**") + " |")
        L.append("")
    if b.get("statscache_floor_delta"):
        sc_delta = b["statscache_floor_delta"]
        sc_cl    = b.get("statscache_claude_floor_delta", sc_delta)
        L += ["## What stats-cache adds", "",
              f"**{sc_delta:,}** tokens are added by the stats-cache floor. "
              f"Claude Code writes `stats-cache.json` into each profile and "
              f"accumulates every session there, including ones whose transcripts "
              f"have since been deleted by `cleanupPeriodDays`. The counter "
              f"survives deletion; the transcript does not. "
              f"**{sc_cl:,}** of that is Claude Code; "
              f"{sc_delta - sc_cl:,} is attributed to other tools. "
              f"The floor is applied per account: `max(counter_total + "
              f"transcripts_after_counter_date, scan_total)`, so it never "
              f"contradicts work already on disk.", ""]
    if b.get("fields"):
        L += ["## What the tokens were", "", "| | tokens | share |", "|---|---:|---:|"]
        tot = max(1, sum(b["fields"].values()))
        for k, lab in (("cache_read_input_tokens", "re-read from cache"),
                       ("cache_creation_input_tokens", "written to cache"),
                       ("input_tokens", "sent fresh"),
                       ("output_tokens", "**generated**")):
            v = b["fields"].get(k, 0)
            L.append(f"| {lab} | {v:,} | {v/tot*100:5.1f}% |")
        L += ["", "Most of any total is the conversation being re-sent, not new "
              "writing. Read that share before quoting the headline.", ""]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true",
                    help="rewrite every month, including finished ones")
    ap.add_argument("--now", help="pretend it is this YYYY-MM (for testing the "
                                  "rollover; the real run uses the local clock)")
    ap.add_argument("--all-machines", action="store_true",
                    help="write EVERY machine folder, not just this computer's "
                         "— for deliberately rebuilding the whole fleet view "
                         "from one place")
    args = ap.parse_args()
    root = pathlib.Path(__file__).parent
    months, life = collect(root)
    if not months:
        raise SystemExit("no sessions found — run update.py first")
    fold_ledger_fleet(root, life)

    # The LOCAL clock decides when a month is over. Nothing else can: the
    # computer that runs this may not be the one that produced the sessions,
    # and no record carries "the month has ended". As soon as the date rolls
    # into the next month, the previous one satisfies `m < now` and is frozen
    # on the very next run, without anyone asking for it.
    now = args.now or datetime.datetime.now().strftime("%Y-%m")
    mdir = paths.machine(root) / "months"
    mdir.mkdir(parents=True, exist_ok=True)
    adir = root / "archive" / "months"

    frozen = new_frozen = 0
    repaired, protected = [], []
    for m in sorted(months):
        data = plain(months[m])
        data["month"] = m
        blob = json.dumps(data, indent=1) + "\n"
        (mdir / f"{m}.json").write_text(blob, encoding="utf-8")

        if m < now:                       # the month is over and cannot change
            dest = adir / m
            # A FROZEN MONTH FROZE FROM WHATEVER ONE CHECKOUT HELD, AND THE
            # FAILURE RAN THE OTHER WAY.
            #
            # `if dest.is_dir() and not args.all: continue` never looked inside
            # the file it was protecting. Whatever the first machine to roll
            # over that month happened to hold became the permanent answer, and
            # every scan afterwards — a second computer, a CLI that had no
            # reader yet, a fixed dedup rule — was locked out. Measured against
            # the real archive, all nine frozen months:
            #
            #     2026-07   archive 2,844,482,973   here now 16,918,232,160
            #     total     archive 8,070,430,372   here now 26,854,961,634
            #
            # Short by 18,784,531,262, and short in EVERY month. Not one of them
            # was short in the direction the freeze exists to protect: the
            # docstring justifies freezing by saying a recount reads FEWER
            # records, and every recount read more.
            #
            # So the test is the direction, not the existence of the file. More
            # records than the frozen copy is new evidence and replaces it; FEWER
            # is the retention case the freeze was built for and is refused. The
            # frozen copy stops being "whoever got here first" and starts being
            # "the largest set of records anyone has ever had".
            was = None
            fp = dest / "month.json"
            if fp.is_file():
                try:
                    was = json.loads(fp.read_text(encoding="utf-8")).get("tokens")
                except Exception:                                # noqa: BLE001
                    was = None                # unreadable: rewrite it, do not trust it
            here = data["tokens"]
            if was is not None and not args.all:
                if was > here:
                    protected.append((m, was, here))
                    frozen += 1
                    continue
                if was == here:
                    frozen += 1
                    continue
            note = ("_This month is over. Frozen from the largest set of records "
                    "anyone has held: it is rewritten only when a rescan finds "
                    "MORE than the frozen copy, and never when it finds fewer — "
                    "the transcripts behind it are deleted after "
                    "`cleanupPeriodDays`, so a smaller recount is loss, not a "
                    "correction._")
            if was is not None and here > was:
                repaired.append((m, was, here))
                note = (f"_This month was frozen at {was:,} tokens and repaired to "
                        f"{here:,} when {here - was:,} more were scanned. A frozen "
                        f"month is rewritten only upward: a recount that reads "
                        f"FEWER records is retention deleting transcripts, and "
                        f"that is refused._")
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "month.json").write_text(blob, encoding="utf-8")
            (dest / "REPORT.md").write_text(render(f"{m}", months[m], note),
                                            encoding="utf-8")
            new_frozen += 1

    # Per-computer buckets for the collective documents. Built from the same
    # collect_from() the per-machine files use, so a section here and that
    # machine's own LIFETIME.md cannot disagree.
    fleet_life, fleet_month = {}, {}
    for _md in paths.machine_folders(root):
        _sf = paths.find(_md, "sessions.json")
        if not _sf:
            continue
        try:
            _d = json.loads(_sf.read_text(encoding="utf-8"))
        except Exception:
            continue
        _n = _d.get("machine", _md.name)
        _mm, _ml = collect_from(_d.get("sessions", []), _n,
                                paths.find(_md, "totals.json"))
        if _ml["tokens"]:
            fleet_life[_n] = _ml
        if _mm.get(now):
            fleet_month[_n] = _mm[now]

    cur = months.get(now)
    if cur:
        (paths.human(root) / "THIS-MONTH.md").write_text(
            render(f"{now} so far", cur,
                   "_Still in progress. Rewritten on every run until the month "
                   "closes, then frozen into `archive/months/`._",
                   by_machine=fleet_month),
            encoding="utf-8")
    (paths.human(root) / "LIFETIME.md").write_text(
        render("Lifetime", life,
               "_Everything ever recorded on any computer in this fleet, across "
               "every CLI. This counts what still exists plus what was captured "
               "before it expired._", by_machine=fleet_life), encoding="utf-8")
    import sessions
    (paths.machine(root) / "lifetime.json").write_text(
        json.dumps(sessions.stamped(plain(life)), indent=1) + "\n", encoding="utf-8")

    # The SAME documents per machine, from that machine's own sessions. A
    # computer's folder should answer every question the root does, for itself
    # — otherwise you have to read a fleet report to learn one machine's
    # months, and the per-machine folder is only half a record.
    #
    # A MACHINE WRITES ITS OWN FOLDER AND NOBODY ELSE'S.
    #
    # This loop wrote LIFETIME.md, THIS-MONTH.md, lifetime.json, months/*.json,
    # BY-ACCOUNT.md and BY-COMPANY.md into every folder it could see. With
    # fun_stats.py it put 12 tracked files belonging to four other computers
    # into git, reaching commit 4a5b42c — files another machine is the author
    # of, rewritten from a copy this computer happens to hold. The fleet
    # documents above still read every folder, because that is what a rollup
    # is, and they are written to the root, which is derived.
    #
    # `token_ledger.this_machine` rather than a fourth copy of the .machine-id
    # walk. corpus_reports.py has one, token_ledger.py has one, and a rule this
    # repository has already shipped wrong in four duplicated files does not
    # need another home.
    import token_ledger
    owned = token_ledger.this_machine(root)
    if owned is None and not args.all_machines:
        print("  no .machine-id here names this host — no per-machine file "
              "written. --all-machines rebuilds every folder deliberately.")
    per = 0
    for md in paths.machine_folders(root):
        sf = paths.find(md, "sessions.json")
        if not sf:
            print(f"  {md.name:30} no sessions.json — never scanned, "
                  f"no figure of any kind")
            continue
        try:
            d = json.loads(sf.read_text(encoding="utf-8"))
        except Exception:
            print(f"  {md.name:30} sessions.json UNREADABLE — not zero, unknown")
            continue
        if not (args.all_machines or (owned is not None
                                      and md.name == owned.name)):
            print(f"  {md.name:30} {len(d.get('sessions', [])):>6} session(s) "
                  f"— another computer's folder, read but not written")
            continue
        name = d.get("machine", md.name)
        mm, ml = collect_from(d.get("sessions", []), name,
                              paths.find(md, "totals.json"))
        ml["scanned_tokens"] = ml["tokens"]
        ml["ledger"] = {name: fold_ledger(md, name, ml, dict(ml["by_cli"]))}
        ml["ledger_beyond_scan"] = ml["tokens"] - ml["scanned_tokens"]
        # STATS-CACHE FLOOR — same logic as the fleet path. Apply after the
        # ledger fold so the floor is compared against scan+ledger together.
        _sc = d.get("stats_cache", [])
        if _sc:
            import stats_page
            _tf = paths.find(md, "totals.json")
            try:
                _t = json.loads(_tf.read_text(encoding="utf-8")) if _tf else {}
            except Exception:
                _t = {}
            _floor, _claude_floor, _other_floor, _ = stats_page.machine_floor(
                _t, d.get("sessions", []), _sc)
            # Dated sessions only — same subset as collect_from() used to build ml.
            _cur_claude = sum(s.get("total", 0) for s in d.get("sessions", [])
                              if s.get("cli") == "claude" and s.get("start"))
            _cur_other  = sum(s.get("total", 0) for s in d.get("sessions", [])
                              if s.get("cli") != "claude" and s.get("start"))
            _d_claude = max(0, _claude_floor - _cur_claude)
            _d_other  = max(0, _other_floor  - _cur_other)
            if _d_claude:
                ml["by_cli"]["claude"]     += _d_claude
                ml["by_machine"][name]     += _d_claude
            if _d_other:
                ml["by_machine"][name]     += _d_other
            _added = _d_claude + _d_other
            ml["tokens"]                   += _added
            ml["statscache_floor_delta"]    = _added
            ml["statscache_claude_floor_delta"] = _d_claude
        (paths.human(md) / "LIFETIME.md").write_text(
            render(f"{name} — lifetime", ml,
                   "_Everything this computer has ever recorded, across every CLI._"),
            encoding="utf-8")
        cur_m = mm.get(now)
        if cur_m:
            (paths.human(md) / "THIS-MONTH.md").write_text(
                render(f"{name} — {now} so far", cur_m,
                       "_Still in progress. Rewritten on every run._"),
                encoding="utf-8")
        import sessions
        (paths.machine(md) / "lifetime.json").write_text(
            json.dumps(sessions.stamped(plain(ml)), indent=1) + "\n", encoding="utf-8")
        mdir_m = paths.machine(md) / "months"
        mdir_m.mkdir(parents=True, exist_ok=True)
        for k, v in mm.items():
            dd = plain(v); dd["month"] = k
            (mdir_m / f"{k}.json").write_text(json.dumps(dd, indent=1) + "\n",
                                              encoding="utf-8")
        # BY-ACCOUNT and BY-COMPANY for this machine alone. The root versions
        # answer "across the fleet"; these answer the same question about one
        # computer, which is not derivable from the fleet report.
        try:
            t = json.loads(paths.find(md, "totals.json").read_text(encoding="utf-8"))
        except Exception:
            t = {}
        accts = sorted(t.get("accounts", []), key=lambda a: -a.get("grand_total", 0))
        tot = sum(a.get("grand_total", 0) for a in accts) or 1
        L = [f"# {name} — by account", "",
             f"**{tot:,} tokens** across {len(accts)} login(s) on this computer.",
             "", "_Claude Code only: it is the one tool that records which account "
             "a session belonged to._", "",
             "| account | tokens | share | sessions |", "|---|---:|---:|---:|"]
        for a in accts:
            L.append(f"| {a.get('account')} | {a.get('grand_total', 0):,} | "
                     f"{a.get('grand_total', 0)/tot*100:5.1f}% | {a.get('sessions', 0):,} |")
        (paths.human(md) / "BY-ACCOUNT.md").write_text("\n".join(L) + "\n",
                                                       encoding="utf-8")

        prov = defaultdict(int)
        for x in d.get("sessions", []):
            prov[x.get("provider") or "— (unidentified)"] += x.get("total", 0)
        ptot = sum(prov.values()) or 1
        L = [f"# {name} — by company", "",
             f"**{ptot:,} tokens**, split by who actually served them.", "",
             "_Attributed by model id, not by which CLI wrote the file — a "
             "DeepSeek model served through a Claude-Code-shaped client is "
             "DeepSeek._", "",
             "| company | tokens | share |", "|---|---:|---:|"]
        for k, v in sorted(prov.items(), key=lambda x: -x[1]):
            L.append(f"| {k} | {v:,} | {v/ptot*100:5.1f}% |")
        (paths.human(md) / "BY-COMPANY.md").write_text("\n".join(L) + "\n",
                                                       encoding="utf-8")
        per += 1
    print(f"  per-machine      {per} computer(s) got the full document set")

    print(f"  months seen      {len(months)}  ({min(months)} .. {max(months)})")
    print(f"  frozen already   {frozen}")
    print(f"  frozen this run  {new_frozen}")
    for m, was, here in repaired:
        print(f"  repaired         {m}  {was:,} -> {here:,}  "
              f"(+{here - was:,}, more records than the frozen copy held)")
    for m, was, here in protected:
        print(f"  held             {m}  {was:,} kept; a recount now reads "
              f"{here:,}, {was - here:,} fewer — retention, not a correction")
    if life.get("ledger_beyond_scan"):
        print(f"  ledger adds      {life['ledger_beyond_scan']:,} tokens whose "
              f"transcripts are gone")
    noledger = [n for n, e in (life.get("ledger") or {}).items()
                if not e["present"]]
    if noledger:
        print(f"  no ledger file   {', '.join(noledger)} — never recorded, "
              f"which is not a ledger reading zero")
    print(f"  current month    {now}  "
          f"{cur['tokens']:,} tokens" if cur else f"  current month    {now}  (nothing yet)")
    print(f"  lifetime         {life['tokens']:,} tokens, "
          f"{life['sessions']:,} sessions")


if __name__ == "__main__":
    main()
