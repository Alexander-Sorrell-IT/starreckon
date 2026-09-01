#!/usr/bin/env python3
"""STATS.md — the fleet at human scale, across every CLI.

    python3 fun_stats.py                 # -> STATS.md here and in the corpus
    python3 fun_stats.py --out DIR

The three root reports answer "how much and whose". This answers "what does
that even mean", which is a different question and the only one anybody reads
out loud. Longest session, biggest day, most expensive single conversation, and
what 117 billion tokens is if you try to picture it.

EVERY CLI, not just Claude Code. The per-account reports are Claude-only because
only Claude Code records an account and keeps a lifetime counter; everything
here comes from sessions.json, which covers all eight.

ON THE COMPARISONS

A token is roughly 0.75 English words — the ratio varies by language and by how
much of the text is code, so every derived figure here is approximate and says
so. The counts themselves are exact; the analogies are not, and the file marks
which is which. A number dressed up as something it cannot support is worse than
no analogy at all.
"""

import argparse
import datetime
import json
import pathlib
import paths
from collections import defaultdict

WORDS_PER_TOKEN = 0.75

# Things with a published, checkable size. Word counts are the common editions.
ANCHORS = [
    ("War and Peace",            587_287),
    ("the King James Bible",     783_137),
    ("the Harry Potter series",  1_084_170),
    ("the complete works of Shakespeare", 884_647),
    ("English Wikipedia",        4_700_000_000),
]
SPEAK_WPM = 130          # unhurried speech
TYPE_WPM = 40            # sustained typing


def human(n):
    for unit, size in (("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if n >= size:
            return f"{n / size:.2f}{unit}"
    return f"{n:,}"


def dur(minutes):
    d, rem = divmod(int(minutes), 1440)
    h, m = divmod(rem, 60)
    return (f"{d}d {h}h {m}m" if d else f"{h}h {m}m" if h else f"{m}m")


FIELDS = ("input_tokens", "cache_creation_input_tokens",
          "cache_read_input_tokens", "output_tokens")


def load_fields(root):
    """The four counters fleet-wide, so cache re-reads can be named as such."""
    agg = dict.fromkeys(FIELDS, 0)
    for mdir, f in paths.iter_machine_files(root, "totals.json"):
        try:
            t = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        for a in t.get("accounts", []):
            for k, v in (a.get("totals") or {}).items():
                if k in agg and isinstance(v, int):
                    agg[k] += v
    return agg


def load_seen(root):
    """First/last use per CLI, merged across machines."""
    out = {}
    for mdir, f in paths.iter_machine_files(root, "sessions.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        for cli, e in (d.get("first_last_seen") or {}).items():
            g = out.setdefault(cli, {"first": None, "last": None, "sources": set()})
            for k in ("first", "last"):
                v = e.get(k)
                if not v:
                    continue
                if k == "first" and (g["first"] is None or v < g["first"]):
                    g["first"] = v
                if k == "last" and (g["last"] is None or v > g["last"]):
                    g["last"] = v
            g["sources"].update(e.get("sources") or [])
    return out


def load(root):
    sessions, machines = [], {}
    for mdir, f in paths.iter_machine_files(root, "sessions.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        name = d.get("machine", mdir.name)
        machines[name] = d.get("generated_at")
        for s in d.get("sessions", []):
            s["machine"] = name
            sessions.append(s)
    return sessions, machines


def render(sessions, fields, machines, scope, seen=None, claude_only_cc=None):
    """One STATS document. Same code for the fleet and for one computer.

    Called once per machine and once for everything, so a per-computer file
    cannot drift from the collective one — they are the same renderer over a
    different slice, not two implementations that have to agree.
    """
    total = sum(s.get("total", 0) for s in sessions)
    words = total * WORDS_PER_TOKEN
    by_cli = defaultdict(lambda: [0, 0, 0.0])
    by_day = defaultdict(int)
    by_model = defaultdict(int)
    for s in sessions:
        c = by_cli[s.get("cli", "?")]
        c[0] += 1
        c[1] += s.get("total", 0)
        c[2] += s.get("duration_min", 0) or 0
        # A session record has start/end, not a per-day split, so a session is
        # attributed to the day it BEGAN. One that runs past midnight lands
        # entirely on the earlier date — noted where the figure is printed
        # rather than silently.
        if s.get("start"):
            by_day[str(s["start"])[:10]] += s.get("total", 0)
        # `model` singular. Reading `models` produced an empty table that looked
        # like "no models recorded" rather than "wrong key".
        m = s.get("model")
        if isinstance(m, str) and m:
            by_model[m] += s.get("total", 0)
        elif isinstance(m, dict):
            for name, n in m.items():
                by_model[name] += n if isinstance(n, int) else 0

    # A machine that reported NOTHING still gets a document. `max()` on an
    # empty list raises, and the previous guard against that was to skip the
    # machine entirely — which is how "reported nothing" came to look exactly
    # like "never asked". The Records section is omitted instead; a section
    # with nothing to rank is the only thing missing.
    longest = biggest = talky = None
    if sessions:
        longest = max(sessions, key=lambda s: s.get("duration_min", 0) or 0)
        biggest = max(sessions, key=lambda s: s.get("total", 0))
        talky = max(sessions, key=lambda s: s.get("turns", 0) or 0)
    hours = sum((s.get("duration_min", 0) or 0) for s in sessions) / 60

    L = []
    L.append(f"# {scope}, at human scale")
    L.append("")
    L.append(f"**{total:,} tokens** across {len(sessions):,} sessions on "
             f"{len(machines)} computer(s), every CLI.")
    L.append("")
    L.append("_Counts are exact — they are what each provider's API reported. "
             "Everything phrased as a comparison is approximate: a token is "
             "roughly 0.75 English words, and that ratio moves with language and "
             "with how much of the text is code._")
    L.append("")
    L.append("### Three totals, and why they differ")
    L.append("")
    L.append("They are not competing answers; they answer different questions, "
             "and adding them together would be meaningless.")
    L.append("")
    L.append("| number | what it counts | where |")
    L.append("|---:|---|---|")
    L.append(f"| **{total:,}** | every CLI, per session, still on disk | this file |")
    # Use totals.json grand_total_tokens when available (matches check_consistency's
    # t["cc"] = sum(grand_total_tokens)). Falls back to sessions sum if not passed.
    claude_only = claude_only_cc if claude_only_cc is not None else by_cli.get("claude", [0, 0, 0])[1]
    L.append(f"| **{claude_only:,}** | Claude Code only, per account | BY-ACCOUNT.md |")
    L.append("| **higher still** | + the frozen lifetime counter, for work whose "
             "transcripts were deleted | the floor table in BY-COMPUTER.md |")
    L.append("")
    L.append("This file counts what survives on disk. Claude Code deletes "
             "transcripts after `cleanupPeriodDays`, so the real usage is larger "
             "than anything here — the floor table is the closest defensible "
             "figure, and it is still a floor.")
    L.append("")

    L.append("## Where the tokens went")
    L.append("")
    L.append("Every one of these is token usage. A conversation resends its "
             "history on each turn and those resends are billed as `cache_read` "
             "— they are tokens used, exactly like the rest, and the total below "
             "is the total.")
    L.append("")
    L.append("The split is here because the four buckets answer different "
             "questions, not because some of them count less. The one thing it "
             "should NOT be used for is comparing the total to books or novels: "
             "that measures DISTINCT TEXT, and re-reading the same page a "
             "thousand times is a thousand pages read and one page written. An "
             "earlier version made that comparison against the whole total and "
             "overstated the distinct text by 22x.")
    L.append("")
    L.append("| | tokens | share |")
    L.append("|---|---:|---:|")
    for k, label in (("cache_read_input_tokens", "re-read from cache"),
                     ("cache_creation_input_tokens", "written to cache"),
                     ("input_tokens", "sent fresh"),
                     ("output_tokens", "**generated by the model**")):
        v = fields.get(k, 0)
        L.append(f"| {label} | {v:,} | {v/max(1,sum(fields.values()))*100:5.1f}% |")
    L.append("")
    fresh = sum(fields.get(k, 0) for k in
                ("input_tokens", "cache_creation_input_tokens", "output_tokens"))
    L.append(f"**{fresh:,} tokens were new content** — everything else is the "
             f"conversation being re-sent. On the machine this was written on, one "
             f"chat of 2,613 turns cost 1,301,790,690 tokens, of which 3,089,179 "
             f"(0.24%) was generated text.")
    L.append("")

    L.append("## If you tried to read it")
    L.append("")
    fresh_words = fresh * WORDS_PER_TOKEN
    L.append(f"Counting only the **new** content — {fresh_words/1e9:.2f} billion "
             f"words. The billed total would give a figure about "
             f"{sum(fields.values())/max(1,fresh):.0f}× larger, and would be "
             f"counting the same sentences over and over.")
    L.append("")
    L.append("| that is | roughly |")
    L.append("|---|---:|")
    for name, wc in ANCHORS:
        r = fresh_words / wc
        # "0×" is not an answer. Below one, say the fraction.
        L.append(f"| {name} | **{r:,.0f}×** |" if r >= 1
                 else f"| {name} | **{r*100:.1f}% of it** |")
    L.append(f"| read aloud at {SPEAK_WPM} words/min, without stopping | "
             f"**{fresh_words/SPEAK_WPM/60/24/365:,.1f} years** |")
    L.append(f"| typed at {TYPE_WPM} words/min, without stopping | "
             f"**{fresh_words/TYPE_WPM/60/24/365:,.1f} years** |")
    L.append("")

    if longest:
        L.append("## Records")
        L.append("")
        L.append("| | session | machine | figure |")
        L.append("|---|---|---|---:|")
        L.append(f"| longest | `{str(longest.get('session_id'))[:18]}` "
                 f"({longest.get('cli')}) | {longest.get('machine')} | "
                 f"**{dur(longest.get('duration_min', 0) or 0)}** |")
        L.append(f"| most tokens | `{str(biggest.get('session_id'))[:18]}` "
                 f"({biggest.get('cli')}) | {biggest.get('machine')} | "
                 f"**{biggest.get('total', 0):,}** |")
        L.append(f"| most turns | `{str(talky.get('session_id'))[:18]}` "
                 f"({talky.get('cli')}) | {talky.get('machine')} | "
                 f"**{talky.get('turns', 0):,}** |")
        if by_day:
            d, n = max(by_day.items(), key=lambda x: x[1])
            L.append(f"| busiest day | {d} | all | **{n:,}** |")
        L.append("")
        L.append("_Busiest day counts each session on the date it STARTED; a session running past midnight lands entirely on the earlier date._")
        L.append("")
    else:
        L.append("_No session survives on disk for this scope, so there is "
                 "nothing to rank. That is a reading of zero, not a missing "
                 "reading — the scan ran and returned no sessions._")
        L.append("")
    L.append(f"Total measured session time: **{hours:,.0f} hours** "
             f"({hours/24/365:.2f} years of wall clock).")
    L.append("")
    L.append("_Duration is a judgement call, not a measurement — it is the span "
             "between a session's first and last message, and a session left "
             "open overnight counts the night. Treat it as an upper bound._")
    L.append("")

    if seen:
        L.append("## First and last seen")
        L.append("")
        L.append("Two sources. The transcripts are precise but only as old as "
                 "whatever has not been deleted; the editor's own state records "
                 "dates **without** tokens, and therefore outlives what it "
                 "describes. Where the second is earlier, the gap is usage no "
                 "surviving session can account for.")
        L.append("")
        L.append("| CLI | first seen | last seen | from |")
        L.append("|---|---|---|---|")
        for cli, e in sorted(seen.items(), key=lambda x: x[1]["first"] or "z"):
            src = ", ".join(sorted(e["sources"])) if isinstance(e["sources"], (set, list)) else ""
            L.append(f"| {cli} | {str(e['first'])[:10]} | {str(e['last'])[:10]} | {src} |")
        L.append("")

    # One section per computer under the fleet document, so a machine that
    # scans for the first time ADDS a section rather than silently moving a
    # total. Built from the same session records the fleet figure uses.
    if len(machines) >= 1:
        permach = defaultdict(lambda: [0, 0, 0.0, defaultdict(int)])
        # SEEDED FROM THE MACHINES, NOT FROM THE SESSIONS. Built from sessions
        # alone, a computer whose scan returned nothing had no key here and no
        # section below — it left the fleet document entirely, and the only
        # trace was the fleet total being smaller. Measured: emptying asus's
        # sessions.json from 36 sessions to 0 removed 146,981,095 tokens and
        # every mention of asus in one run, exit 0.
        for _name in machines:
            permach[_name]
        for s_ in sessions:
            e = permach[s_.get("machine", "?")]
            e[0] += 1
            e[1] += s_.get("total", 0)
            e[2] += s_.get("duration_min", 0) or 0
            e[3][s_.get("cli", "?")] += s_.get("total", 0)
        L.append("## Each computer")
        L.append("")
        for name in sorted(permach, key=lambda n: -permach[n][1]):
            n_, t_, m_, clis = permach[name]
            L.append(f"### {name}")
            L.append("")
            L.append(f"**{t_:,} tokens** · {n_:,} sessions · {dur(m_)}"
                     f" · {t_/max(1,total)*100:.1f}% of the fleet")
            L.append("")
            L.append("| CLI | tokens | share |")
            L.append("|---|---:|---:|")
            # NOT [:8]. A hard cap silently dropped copilot-chat and lmstudio
            # off HP Laptop Linux's table — real, nonzero, just small — and
            # check_consistency.py caught it as "figure not found", which is
            # this repository's own signature bug: absent reads exactly like
            # zero. Every CLI a machine actually has gets a row.
            for k, v in sorted(clis.items(), key=lambda x: -x[1]):
                L.append(f"| {k} | {v:,} | {v/max(1,t_)*100:5.1f}% |")
            L.append("")

    L.append("## Every CLI")
    L.append("")
    L.append("| CLI | sessions | tokens | share | time |")
    L.append("|---|---:|---:|---:|---:|")
    for cli, (n, t, mins) in sorted(by_cli.items(), key=lambda x: -x[1][1]):
        L.append(f"| {cli} | {n:,} | {t:,} | {t/total*100:5.1f}% | {dur(mins)} |")
    L.append(f"| **all** | **{len(sessions):,}** | **{total:,}** | 100% | "
             f"**{dur(hours*60)}** |")
    L.append("")

    if by_model:
        L.append("## Models")
        L.append("")
        L.append("| model | tokens |")
        L.append("|---|---:|")
        for m, n in sorted(by_model.items(), key=lambda x: -x[1])[:15]:
            L.append(f"| `{m}` | {n:,} |")
        L.append("")

    stamp = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    L.append("---")
    L.append("")
    L.append(f"_Generated by `fun_stats.py` {stamp} from "
             f"{len(machines)} machine scan(s). Do not edit by hand._")
    L.append("")
    L.append("Scans, per machine:")
    L.append("")
    seen_counts = defaultdict(int)
    for s in sessions:
        seen_counts[s.get("machine")] += 1
    for name, when in sorted(machines.items()):
        n = seen_counts.get(name, 0)
        L.append(f"- {name} — {when or 'no recorded scan time'} — "
                 f"{n:,} session(s)"
                 + ("  ⚠️ **scanned and reported nothing** — not the same as "
                    "never scanned, which would leave it off this list entirely"
                    if not n else ""))
    L.append("")

    data = {
        "scope": scope, "generated_at": stamp,
        "total_tokens": total, "sessions": len(sessions),
        "fields": dict(fields), "new_content_tokens": fresh,
        "hours": round(hours, 1),
        "by_cli": {k: {"sessions": v[0], "tokens": v[1], "minutes": round(v[2], 1)}
                   for k, v in by_cli.items()},
        "by_model": dict(sorted(by_model.items(), key=lambda x: -x[1])[:20]),
        # null, not a zero-valued record. There is no longest session when
        # there are no sessions, and inventing one with id None and 0 minutes
        # would put a fabricated row where the absence belongs.
        "records": {
            "longest_session": longest and {"id": longest.get("session_id"),
                                            "cli": longest.get("cli"),
                                            "machine": longest.get("machine"),
                                            "minutes": longest.get("duration_min")},
            "most_tokens": biggest and {"id": biggest.get("session_id"),
                                        "cli": biggest.get("cli"),
                                        "machine": biggest.get("machine"),
                                        "tokens": biggest.get("total")},
            "most_turns": talky and {"id": talky.get("session_id"),
                                     "cli": talky.get("cli"),
                                     "machine": talky.get("machine"),
                                     "turns": talky.get("turns")},
        },
        "scans": machines,
        "first_last_seen": {k: {"first": v["first"], "last": v["last"],
                                "sources": sorted(v.get("sources") or [])}
                            for k, v in (seen or {}).items()},
    }
    return "\n".join(L), data


def main():
    import argparse as _a
    ap = _a.ArgumentParser()
    ap.add_argument("--out", action="append", default=None)
    ap.add_argument("--all-machines", action="store_true",
                    help="write EVERY machine folder, not just this computer's "
                         "— for deliberately rebuilding the whole fleet view "
                         "from one place")
    args = ap.parse_args()
    root = pathlib.Path(__file__).parent
    sessions, machines = load(root)
    if not sessions:
        raise SystemExit("no sessions.json anywhere — run update.py first")
    fields = load_fields(root)

    # ---- the fleet
    seen = load_seen(root)
    # claude_only_cc: sum of grand_total_tokens from totals.json files — this
    # is what check_consistency.py uses as t["cc"] and what BY-ACCOUNT.md
    # publishes. It differs from the sessions.json claude sum because orphan/
    # counter-recovery tokens are in sessions but not in totals.json accounts.
    import pathlib as _pl
    _cc = 0
    for _mdir, _tf in paths.iter_machine_files(_pl.Path(__file__).parent, "totals.json"):
        try:
            _cc += json.loads(_tf.read_text(encoding="utf-8")).get("grand_total_tokens", 0)
        except Exception:
            pass
    text, data = render(sessions, fields, machines, "The fleet", seen,
                        claude_only_cc=_cc or None)
    # Only this repo. publish.py copies the finished documents into the
    # corpus, so there is one writer per file and no chance of the two
    # repos being written by different code paths.
    outs = [pathlib.Path(o) for o in (args.out or [str(root)])]
    for o in outs:
        if not o.is_dir():
            print(f"  skipped {o} (not present)")
            continue
        dest = paths.human(o) if (o / paths.MACHINE).is_dir() else o
        (dest / "STATS.md").write_text(text, encoding="utf-8")
        if (o / paths.MACHINE).is_dir():
            import sessions
            (paths.machine(o) / "stats.json").write_text(
                json.dumps(sessions.stamped(data), indent=1) + "\n", encoding="utf-8")
        print(f"  wrote {dest}/STATS.md")

    # ---- and the same document per computer, from the same renderer
    #
    # A MACHINE WRITES ITS OWN FOLDER AND NOBODY ELSE'S.
    #
    # This loop wrote STATS.md and stats.json into every folder it could see.
    # Together with monthly.py that put 12 tracked files belonging to four
    # other computers into git, reaching commit 4a5b42c — each one a file
    # another machine is the author of, rewritten from data this computer
    # merely happens to have a copy of. The fleet documents above still read
    # every folder, because that is what a rollup is, and they are written to
    # the root, which is derived. Only the per-machine files are restricted.
    #
    # `token_ledger.this_machine` rather than a fourth copy of the .machine-id
    # walk: corpus_reports.py has one, token_ledger.py has one, and a rule this
    # repository has already shipped wrong in four duplicated files does not
    # need a third home.
    import token_ledger
    owned = token_ledger.this_machine(root)
    if owned is None and not args.all_machines:
        print("  no .machine-id here names this host — no per-machine file "
              "written. --all-machines rebuilds every folder deliberately.")
    for mdir in paths.machine_folders(root):
        sf = paths.find(mdir, "sessions.json")
        if not sf:
            # NOT SCANNED. No sessions.json at all, so there is no figure of
            # any kind — which is a different sentence from a figure of zero,
            # and both used to print nothing.
            print(f"  {mdir.name:30} no sessions.json — never scanned, "
                  f"no figure of any kind")
            continue
        d = json.loads(sf.read_text(encoding="utf-8"))
        name = d.get("machine", mdir.name)
        mine = [dict(x, machine=name) for x in d.get("sessions", [])]
        if not (args.all_machines or (owned is not None
                                      and mdir.name == owned.name)):
            print(f"  {mdir.name:30} {len(mine):>6} session(s) — another "
                  f"computer's folder, read but not written")
            continue
        # `mine == []` FLOWS THROUGH. `if not mine: continue` treated a machine
        # that scanned and found nothing exactly as it treated one that was
        # never scanned: no output line, and — worse — no rewrite, so the
        # stats.json kept whatever figure it last had, forever. Measured:
        # emptying asus's sessions.json from 36 sessions to 0 left its
        # stats.json at 146,981,095 with rc=0, and asus was named nowhere.
        mf = {}
        tf = paths.find(mdir, "totals.json")
        if tf:
            t = json.loads(tf.read_text(encoding="utf-8"))
            mf = dict.fromkeys(FIELDS, 0)
            for a in t.get("accounts", []):
                for k, v in (a.get("totals") or {}).items():
                    if k in mf and isinstance(v, int):
                        mf[k] += v
        mseen = {k: dict(v, sources=set(v.get("sources") or []))
                 for k, v in (d.get("first_last_seen") or {}).items()}
        mtext, mdata = render(mine, mf, {name: d.get("generated_at")}, name, mseen)
        (paths.human(mdir) / "STATS.md").write_text(mtext, encoding="utf-8")
        import sessions
        (paths.machine(mdir) / "stats.json").write_text(
            json.dumps(sessions.stamped(mdata), indent=1) + "\n", encoding="utf-8")
        print(f"  wrote {mdir.name}/human-readable/STATS.md")

    print(f"\n  fleet: {data['total_tokens']:,} tokens · "
          f"{data['sessions']:,} sessions · {data['new_content_tokens']:,} new "
          f"({data['new_content_tokens']/max(1,sum(fields.values()))*100:.1f}%)")


if __name__ == "__main__":
    main()
