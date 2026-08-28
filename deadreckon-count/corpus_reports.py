#!/usr/bin/env python3
"""The same reports, derived from the conversations instead of from the scans.

    python3 corpus_reports.py                 # -> ~/deadreckon-record
    python3 corpus_reports.py --corpus DIR

`deadreckon-count` counts by reading each tool's session files and writing totals.
This reads the transcripts THEMSELVES — the ones sitting in `deadreckon-record` — and
produces the same documents, in the same folders, under the same names.

They are not copies. Nothing is transferred between the repositories; both are
computed, from different inputs, by different code. That is the entire point:

    deadreckon-count/human-readable/STATS.md    from the scanners
    deadreckon-record/human-readable/STATS.md   from the conversations

If those two disagree by more than the clock between them, one of them is
wrong, and the disagreement is visible instead of averaged away. Copying the
first into the second would have destroyed the only independent check the
system has.

WHAT THE CORPUS CAN AND CANNOT SAY

It has every message: uuid, sessionId, timestamp, model, and the four usage
counters. So sessions, turns, durations, models, projects, months and totals all
come straight out of it.

It cannot say which ACCOUNT a session belonged to — that lives in a config file
that is deliberately not exported — and it holds Claude Code only. So there is
no BY-ACCOUNT here and no every-CLI figure, and the documents say so rather than
printing a smaller number as though it were the same one.
"""

import argparse
import datetime
import json
import pathlib
import sys
from collections import defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import paths
# after the path insert, so a copy of this file run from elsewhere
# still finds the reader it now depends on.
import sessions as sessions_mod

FIELDS = ("input_tokens", "cache_creation_input_tokens",
          "cache_read_input_tokens", "output_tokens")


def read_machine(mdir):
    """Every session in one machine's corpus, via sessions.read_claude().

    THIS FILE HAD ITS OWN PARSER AND IT WAS THE THIRD COPY OF ONE THAT WAS
    ALREADY WRONG TWICE. It deduplicated on the row `uuid`, with the comment
    "same dedup rule as the scanner" — the identical false claim count_corpus.py
    carried until this morning. A row uuid is unique per row; Claude Code writes
    one row per streaming chunk, all sharing a `message.id` and each with a
    fresh uuid, so that dedup removed NOTHING:

        corpus total 40,777,650,377 across 16,804 conversations
        scans say 23,177,513,548; corpus holds 46,265,519,014 (+99.6%)

    Two more, from the same family: `proj.glob("*.jsonl")` is flat, so the
    subagent and workflow transcripts one directory deeper were never read —
    18.23% of this machine's tokens — and it looked only at .claude/projects,
    so the other CLIs in tools/ contributed nothing.

    All three are fixed by not having a third parser. sessions.read_claude()
    holds the streaming dedup, the cross-profile dedup and the recursive glob,
    it is the function the scanner itself uses, and test_readers.py catches ten
    planted breaks in it. The shape below is mapped to what these reports
    expect; the counting is not reimplemented.
    """
    tree = mdir / ".claude" / "projects"
    if not tree.is_dir():
        return None
    out = []
    for r in sessions_mod.read_claude(mdir) or []:
        tk = r.get("tokens") or {}
        total = sum(int(tk.get(k, 0) or 0) for k in FIELDS)
        out.append({
            "session_id": r.get("session_id"),
            "project": r.get("project") or "-",
            "cli": "claude",
            "turns": r.get("turns") or 0,
            "total": total,
            "start": r.get("start"),
            "end": r.get("end"),
            "fields": {k: int(tk.get(k, 0) or 0) for k in FIELDS},
            # read_claude reports the model it settled on for the session;
            # these reports want a per-model split, and one session is one
            # model in every record on disk.
            "models": {r.get("model") or "unknown": total},
            "duration_min": r.get("duration_min") or 0,
        })
    return out


def _records(ses):
    """(longest, biggest) — or (None, None) when there is nothing to rank.

    A corpus with no transcripts in it is now the NORMAL state of a fresh
    clone, not an error: transcripts were untracked from that repository today
    and ship as release assets instead, so `git clone` gives you 0 .jsonl files
    by design. This crashed on exactly that:

        longest = max(everything, key=lambda s: s.get("duration_min", 0))
        ValueError: max() iterable argument is empty

    It was invisible on any machine with an existing checkout and it hits every
    machine that follows the current instructions, because those instructions
    now say to clone. Found on dell-latitude, on the first machine to do it.

    render() already takes longest=None and omits the Records table, so the
    reports are simply written without a section that has nothing to say.
    """
    if not ses:
        return None, None
    return (max(ses, key=lambda s: s.get("duration_min", 0)),
            max(ses, key=lambda s: s["total"]))


def dur(minutes):
    h, m = divmod(int(minutes), 60)
    d, h = divmod(h, 24)
    return (f"{d}d {h}h {m}m" if d else f"{h}h {m}m" if h else f"{m}m")


def summarise(sessions):
    b = {"tokens": 0, "sessions": len(sessions), "turns": 0, "minutes": 0.0,
         "fields": dict.fromkeys(FIELDS, 0), "by_model": defaultdict(int),
         "by_project": defaultdict(int), "by_month": defaultdict(int),
         "first": None, "last": None}
    for s in sessions:
        b["tokens"] += s["total"]
        b["turns"] += s["turns"]
        b["minutes"] += s.get("duration_min", 0)
        for k in FIELDS:
            b["fields"][k] += s["fields"][k]
        for m, v in s["models"].items():
            b["by_model"][m] += v
        b["by_project"][s["project"]] += s["total"]
        if s["start"]:
            b["by_month"][s["start"][:7]] += s["total"]
        for k, w in (("first", s["start"]), ("last", s["end"])):
            if w and (b[k] is None or (w < b[k] if k == "first" else w > b[k])):
                b[k] = w
    for k in ("by_model", "by_project", "by_month"):
        b[k] = dict(sorted(b[k].items(), key=lambda x: -x[1]))
    return b


def render(title, b, note, longest=None, biggest=None):
    tot = max(1, sum(b["fields"].values()))
    fresh = sum(b["fields"][k] for k in FIELDS if k != "cache_read_input_tokens")
    L = [f"# {title}", "",
         f"**{b['tokens']:,} tokens** · {b['sessions']:,} conversations · "
         f"{b['turns']:,} turns · {dur(b['minutes'])}", "", note, ""]
    if b["first"]:
        L += [f"_{b['first'][:10]} .. {b['last'][:10]}_", ""]
    L += ["## What the tokens were", "", "| | tokens | share |", "|---|---:|---:|"]
    for k, lab in (("cache_read_input_tokens", "re-read from cache"),
                   ("cache_creation_input_tokens", "written to cache"),
                   ("input_tokens", "sent fresh"),
                   ("output_tokens", "**generated**")):
        L.append(f"| {lab} | {b['fields'][k]:,} | {b['fields'][k]/tot*100:5.1f}% |")
    L += ["", f"All of it is token usage. **{fresh:,} of it was DISTINCT text** — "
          f"the rest is the conversation re-sent on each turn, billed and counted "
          f"the same. The split is only there because comparing a total to books "
          f"measures distinct text, not tokens used.", ""]
    if longest:
        L += ["## Records", "", "| | conversation | figure |", "|---|---|---:|",
              f"| longest | `{longest['session_id'][:18]}` | "
              f"**{dur(longest.get('duration_min', 0))}** |",
              f"| most tokens | `{biggest['session_id'][:18]}` | "
              f"**{biggest['total']:,}** |",
              f"| most turns | `{max([longest, biggest], key=lambda x: x['turns'])['session_id'][:18]}` | "
              f"**{max(longest['turns'], biggest['turns']):,}** |", ""]
    for label, key in (("By month", "by_month"), ("By model", "by_model"),
                       ("By project", "by_project")):
        rows = list(b[key].items())[:15]
        if not rows:
            continue
        L += [f"## {label}", "", "| | tokens | share |", "|---|---:|---:|"]
        for k, v in rows:
            L.append(f"| {k} | {v:,} | {v/max(1,b['tokens'])*100:5.1f}% |")
        L.append("")
    L += ["---", "",
          "_Derived from the transcripts in this repository, not from the token "
          "scans. Claude Code only, and no per-account split — the account lives "
          "in a config file that is deliberately not exported._", ""]
    return "\n".join(L)


def _this_machine_folder(root):
    """The folder this computer owns, by .machine-id. None if it cannot tell.

    None means "write them all" — that is the right fallback for a machine that
    has not been registered yet, and for anyone deliberately rebuilding the
    whole fleet view from one place.
    """
    import platform
    host = platform.node()
    for d in sorted(pathlib.Path(root).iterdir()):
        if not d.is_dir():
            continue
        f = d / ".machine-id"
        if f.is_file():
            try:
                if json.loads(f.read_text(encoding="utf-8")).get("hostname") == host:
                    return d.name
            except Exception:  # noqa: BLE001
                pass
    return None


def _is_count_root(root):
    """Is this the deadreckon-count checkout, or a directory the tools sit in?

    THE COVERAGE TABLE HAD NO WAY TO ASK. `root` was the directory this file
    happens to live in, with no argument and no check, so running it from a
    temp clone, a copy of the scripts, or the wrong checkout gave
    `iter_machine_files` nothing to yield — and every branch downstream read
    that as a measured zero:

        | asus  | — | 0 | — | **NOT SCANNED — transcripts here, no
                               totals.json in deadreckon-count** |
        | **all** | **0** | **0** | **+0** | 0 of 6 machine(s) comparable |

    Written to disk at 17:29 with exit 0, over a tree that holds five
    totals.json — asus 133,195,610, dell-inspiron 824,886, dell-latitude
    2,353,868,873, hp 6,734,300,954, macbook 13,955,323,225 — and where
    `paths.iter_machine_files` finds every one of them. The scans were not
    missing; this process was not looking at them, and the document could not
    tell those apart because "I looked and found nothing" and "I never looked"
    both arrive here as an empty iterator.

    Two markers, either of which settles it: `machines.json` is authored and
    lives only at a count root, and a machine folder with a totals.json in it
    is what this report exists to read. Neither present means the answer is
    not zero, it is "wrong directory", and the report refuses rather than
    publishing a table of falsehoods.

    Returns None when it is one, and the reason it is not when it is not. A
    directory that cannot be ENTERED is the third answer and used to be the
    loudest possible version of the same bug: `machine_folders` raises
    PermissionError from inside `is_file()`, so "I am not allowed to look"
    arrived as a traceback with no mention of the root. It is reported as its
    own sentence, because "not a count root" and "could not read the count
    root" call for different actions.
    """
    root = pathlib.Path(root)
    if (root / "machines.json").is_file():
        return None
    try:
        if paths.machine_folders(root):
            return None
    except OSError as e:                                         # noqa: BLE001
        return f"{root} could not be read: {e}"
    return (f"{root} is not a deadreckon-count root: no machines.json and no "
            f"machine folder holding a totals.json")


def _export_shortfall(mdir):
    """(exported, present) record files — what the export wrote vs what is here.

    "EXPORTED BEFORE THE LAST SCAN" WAS A GUESS, AND IT SENT THE READER TO THE
    WRONG MACHINE.

    Any corpus figure below its scanned figure got that one sentence, whose only
    remedy is "run export_corpus.py there". But the transcripts were untracked
    from deadreckon-record on 2026-08-09 and ship as release assets instead, so a
    plain `git clone` holds none of them BY DESIGN — the docstring of `_records`
    in this same file says exactly that, three hundred lines up, and the coverage
    table never learned it. Measured against the real corpus, MANIFEST.json's
    own count against the files actually on disk:

        macbook-air-m1            53 exported,     1 present
        hp-laptop-linux        8,895 exported, 4,365 present
        dell-latitude-7480    16,516 exported,     0 present

    Re-running the export on those machines would change nothing; fetching the
    release asset is the whole remedy. The manifest is written by the export
    itself, so this is the export's own count against the tree, not an inference
    from a token total.
    """
    exported = None
    f = paths.find(mdir, "MANIFEST.json")
    if f:
        try:
            exported = json.loads(f.read_text(encoding="utf-8")).get("files")
        except Exception:                                        # noqa: BLE001
            exported = None
    present = 0
    for p in mdir.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(mdir)
        if rel.parts[0] in (paths.HUMAN, paths.MACHINE):
            continue
        if len(rel.parts) == 1 and rel.name in ("MANIFEST.json", "README.md"):
            continue
        present += 1
    return exported, present


def _roster(root):
    """(machines, note). Missing, unreadable and empty are three answers.

    `except Exception: roster = []` gave the same empty list for a machines.json
    that is absent, one that is corrupt, and one that genuinely lists nobody —
    and the third is the only one where the coverage footer's "on the roster
    only" section being empty means anything.
    """
    f = pathlib.Path(root) / "machines.json"
    if not f.is_file():
        return [], f"no machines.json at {root} — the fleet roster is unknown, " \
                    "so a computer that has never been scanned cannot be named here"
    try:
        return (json.loads(f.read_text(encoding="utf-8")).get("machines") or []), None
    except Exception as e:                                       # noqa: BLE001
        return [], f"machines.json at {root} could not be read ({e}) — the " \
                   "roster section below is missing, not empty"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(pathlib.Path.home() / "deadreckon-record"))
    ap.add_argument("--root", default=str(pathlib.Path(__file__).parent),
                    help="the deadreckon-count checkout to read scans from "
                         "(default: the directory this script is in)")
    args = ap.parse_args()
    root = pathlib.Path(args.root)
    corpus = pathlib.Path(args.corpus)
    if not corpus.is_dir():
        raise SystemExit(f"no corpus at {corpus}")
    why = _is_count_root(root)
    if why:
        raise SystemExit(
            f"{why}.\n"
            f"Every scanned figure would be 0 and COVERAGE.md would publish "
            f"that as a measurement. Pass --root <the deadreckon-count "
            f"checkout>. Nothing was written.")

    stamp = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    # A MACHINE WRITES ITS OWN FOLDER AND NOBODY ELSE'S.
    #
    # This loop wrote STATS.md and stats.json into EVERY machine folder it could
    # see, so `run.py update` on one computer left four others dirty:
    #
    #     MM asus-laptop-linux/machine-readable/stats.json
    #     MM dell-inspiron-desktop-linux/machine-readable/stats.json
    #
    # Nothing had broken yet only because the runbook says `git add <machine>`.
    # The ownership rule was being enforced by a command somebody has to
    # remember rather than by the code, and one `git add -A` would commit four
    # machines' files and hand the next computer a conflict in files it never
    # touched.
    #
    # The fleet rollup below still reads every folder — that is the point of a
    # rollup, and it is written to the corpus ROOT, which is derived and
    # regenerated by whoever wants it. Only the per-machine files are restricted.
    mine = _this_machine_folder(root)
    everything, rows, silent = [], [], []
    shortfall = {}
    for mdir in paths.corpus_machine_folders(corpus):
        shortfall[mdir.name] = _export_shortfall(mdir)
        ses = read_machine(mdir)
        # AN EMPTY EXPORT AND AN ABSENT MACHINE PRINTED THE SAME THING: NOTHING.
        #
        # `if not ses: continue` treated a machine folder holding zero
        # transcripts exactly as it treated a machine that was never exported —
        # no row here, no line in COVERAGE that could tell them apart, and the
        # footer counting "3 computer(s)" on a five-machine fleet. Measured on
        # planted data, one empty and one absent out of five:
        #
        #     corpus total 1,200,500,000 across 6 conversations on 3 computer(s)
        #     | charlie | 30,000,000 | 0 | -30,000,000 | **never exported** |
        #     | delta   |  4,000,000 | 0 |  -4,000,000 | **never exported** |
        #
        # charlie had been exported and held nothing; delta had no folder at
        # all. Two different facts, one sentence. Worse, skipping the machine
        # also skipped the stats.json write, so an export that emptied kept
        # whatever figure it last had, forever.
        #
        # `[]` now flows through: it is summarised, printed, and its stats.json
        # is rewritten to zero. Only `None` — no .claude/projects, so not a
        # Claude machine folder at all — is skipped, and it is named below
        # rather than dropped.
        if ses is None:
            if (mdir / paths.MACHINE).is_dir() or paths.find(mdir, "MANIFEST.json"):
                silent.append(mdir.name)
            continue
        everything += ses
        b = summarise(ses)
        longest, biggest = _records(ses)
        if mine is None or mdir.name == mine:
            (paths.human(mdir) / "STATS.md").write_text(
                render(mdir.name, b,
                       "_This computer, from its own conversations._", longest, biggest),
                encoding="utf-8")
            # STAMPED WITH THE CODE THAT PRODUCED IT. Machines own their own
            # folder, so only this computer's stats.json is rewritten here —
            # which is right, and which means COVERAGE below is reading four
            # other files written by whatever version those machines last ran.
            # Unstamped, it totalled them anyway: on the run that replaced this
            # file's parser, four stale files still held the old figures and the
            # coverage line reported 38,344,366,600 while the same run had just
            # computed 18,057,608,727 from the same transcripts. 2.0x to 2.9x
            # per machine, presented as one number.
            (paths.machine(mdir) / "stats.json").write_text(
                json.dumps({"machine": mdir.name, "generated_at": stamp,
                            "reader_version": sessions_mod.scanner_version(),
                            **{k: v for k, v in b.items()}}, indent=1) + "\n",
                encoding="utf-8")
        rows.append((mdir.name, b))
        print(f"  {mdir.name:30} {b['sessions']:>5} conversations  "
              f"{b['tokens']:>16,} tokens")

    b = summarise(everything)
    longest, biggest = _records(everything)
    (paths.human(corpus) / "STATS.md").write_text(
        render("The corpus", b,
               "_Every conversation in this repository, across every computer._",
               longest, biggest), encoding="utf-8")
    (paths.human(corpus) / "LIFETIME.md").write_text(
        render("Lifetime, from the conversations", b,
               "_Everything this corpus holds. Compare with `LIFETIME.md` in "
               "deadreckon-count: that one counts every CLI and includes usage whose "
               "transcripts are already deleted, so it is legitimately larger._"),
        encoding="utf-8")
    (paths.machine(corpus) / "stats.json").write_text(
        json.dumps({"generated_at": stamp, "machines": [n for n, _ in rows],
                    **b}, indent=1) + "\n", encoding="utf-8")

    old = corpus / "STATS.md"
    if old.is_file():
        old.unlink()
        print("  removed the flat STATS.md (now human-readable/STATS.md)")

    print(f"\n  corpus total  {b['tokens']:,} tokens across {b['sessions']:,} "
          f"conversations on {len(rows)} computer(s)")
    if silent:
        print(f"  {len(silent)} folder(s) present with no .claude/projects, "
              f"contributing nothing: {', '.join(silent)}")

    # The cross-check that only exists because these were computed separately.
    # Written into the corpus as a document, not printed and forgotten: a gap
    # between the two derivations is the most useful thing this system can
    # report, and it names which machine caused it.
    cov = ["# Coverage — corpus against scans", "",
           "Two independent derivations of the same quantity. `deadreckon-count`",
           "counts by reading each tool's session files; this repository holds",
           "the transcripts and is counted separately. A gap is not an error —",
           "it says what the corpus does not yet hold.", "",
           "| computer | scanned | in this corpus | gap | why |",
           "|---|---:|---:|---:|---|"]
    ts = tc = 0
    # WHAT THIS RUN COMPUTED, per machine, from the transcripts in this
    # checkout. `rows` is built above by summarise() over read_machine(), so a
    # machine missing from it produced no reading at all — and that is a
    # different fact from a reading of zero.
    held = {n: v["tokens"] for n, v in rows}
    # Which machines the corpus has a FOLDER for, whatever is inside it. This is
    # the only thing that tells "exported and holds nothing" from "never
    # exported", and both used to print the second sentence.
    corpus_dirs = {d.name for d in paths.corpus_machine_folders(corpus)}
    counted = set()
    unread, unread_scanned = [], 0
    for mdir, f in paths.iter_machine_files(root, "totals.json"):
        try:
            sc = json.loads(f.read_text(encoding="utf-8")).get("grand_total_tokens", 0)
        except Exception:
            continue
        counted.add(mdir.name)
        # A FIGURE THIS RUN DID NOT COMPUTE IS NOT COMPARABLE TO ONE IT DID,
        # AND MUST LEAVE BOTH SIDES OR NEITHER.
        #
        # THE GUARD WAS ON ONE SIDE ONLY, AND THAT INVENTED A GAP.
        #
        # `ts += sc` ran unconditionally while `tc += cc` was skipped for an
        # excluded machine, so the scanned figure stayed in the numerator after
        # the corpus figure had left it. Every row could read +0 and the total
        # still reported a deficit. Reproduced on planted data where the true
        # gap is provably zero, two of five machines excluded:
        #
        #     | alpha   | 1,000,000,000 | 1,000,000,000 | +0 | current |
        #     | charlie |    30,000,000 |    30,000,000 | +0 | **EXCLUDED** |
        #     | **all** | 1,234,500,000 | 1,200,500,000 | **-34,000,000** |
        #
        # -34,000,000 was exactly the excluded machines: the total contradicted
        # the sum of its own rows and named the shortfall as missing transcripts.
        #
        # WHAT THE COMPARISON USED TO READ, AND WHY IT WAS NOT A COMPARISON.
        #
        # The corpus figure came off disk, from <machine>/machine-readable/
        # stats.json. A machine writes its own folder and nobody else's, so four
        # of five of those files were written by another computer on another day
        # by whatever code it was running — the file's own comment above says
        # so. A `reader_version` stamp was supposed to catch the skew and only
        # caught version drift, never content drift, so a folder holding no
        # transcripts at all still contributed whatever figure it last had.
        # Measured against the real repositories:
        #
        #     | dell-inspiron | 824,886 | 0 | -824,886 | **exported, holds nothing** |
        #
        # dell-inspiron's corpus folder has no .claude/projects. read_machine()
        # returned None, this run counted nothing there, and the row reported a
        # deficit as though the export had come out empty. It had not been read.
        #
        # `held` is this process's own count, from the same transcripts, in the
        # same second. A machine it could not read is excluded and named below.
        exported, present = shortfall.get(mdir.name, (None, 0))
        if mdir.name in corpus_dirs and mdir.name not in held:
            unread.append(mdir.name)
            unread_scanned += sc
            cov.append(f"| {mdir.name} | {sc:,} | — | — | **NOT READ — folder "
                       f"present, no transcripts in this checkout"
                       + (f" ({exported:,} were exported, {present:,} are here)"
                          if exported else "")
                       + ", excluded from both totals** |")
            continue
        cc = held.get(mdir.name, 0)
        ts += sc
        tc += cc
        if mdir.name not in corpus_dirs:
            why = "**never exported — no folder in the corpus**"
        elif cc == 0:
            why = "**exported, holds nothing**"
        elif cc < sc and exported and present < exported:
            # NOT "older than the scan". The export ran and wrote more files
            # than are here, so the remedy is fetching them, not re-exporting.
            why = (f"**{exported - present:,} of {exported:,} exported "
                   f"transcripts are not in this checkout** — fetch the release "
                   f"asset; re-running the export will not close this")
        elif cc < sc:
            why = "exported before the last scan"
        else:
            why = "current"
        cov.append(f"| {mdir.name} | {sc:,} | {cc:,} | {cc - sc:+,} | {why} |")

    # A MACHINE THE CORPUS HOLDS AND THE SCANS DO NOT. Deleting a machine folder
    # from deadreckon-count removed it from this table entirely: its tokens left the
    # numerator AND the denominator together, the gap went back to +0, and the
    # fleet total quietly shrank by that machine. A row that is absent from a
    # coverage report is the one thing a coverage report must never produce.
    for name in sorted(corpus_dirs - counted):
        cov.append(f"| {name} | — | {held.get(name, 0):,} | — | **NOT SCANNED — "
                   f"transcripts here, no totals.json under {root}** |")

    # The roster, for machines that are in neither. Same reason machines.json
    # exists at all: a computer that has never run anything is not zero usage.
    roster, roster_note = _roster(root)
    never = [e.get("folder") for e in roster
             if e.get("folder") and e["folder"] not in counted | corpus_dirs]
    for name in never:
        cov.append(f"| {name} | — | — | — | **NEVER SCANNED, NEVER EXPORTED — "
                   f"on the roster only** |")

    known = len(counted | corpus_dirs) + len(never)
    cov += [f"| **all** | **{ts:,}** | **{tc:,}** | **{tc - ts:+,}** | "
            f"{len(counted) - len(unread)} of {known} machine(s) comparable |", ""]
    if not counted:
        cov += [f"**No totals.json was found under `{root}`.** The scanned "
                f"column is empty because nothing was read, not because "
                f"nothing was counted — every figure in it is missing, not "
                f"zero, and the `all` row above is not a measurement.", ""]
    if unread:
        cov += [f"**{len(unread)} machine(s) have a folder in the corpus that "
                f"this run could not read and are excluded from BOTH columns "
                f"above:** {', '.join(unread)} — {unread_scanned:,} scanned "
                f"tokens are not represented in the `all` row at all, on either "
                f"side. Their folders hold no transcripts in this checkout: "
                f"either the export never landed, or the transcripts ship as a "
                f"release asset and were never fetched here. Adding their last "
                f"known corpus figure in would compare a number this run "
                f"computed against one it did not; adding only the scanned "
                f"figure, which is what this file used to do, invents a gap the "
                f"size of the machine.", ""]
    if roster_note:
        cov += [f"**{roster_note}.**", ""]
    if never or (corpus_dirs - counted):
        cov += [f"**{len(never) + len(corpus_dirs - counted)} machine(s) "
                f"contribute to neither column** and are listed above so the "
                f"total is read as a floor.", ""]
    cov += ["",
            "**never exported** is counted in every token report and absent",
            "from every conversation here. **exported, holds nothing** is a",
            "folder that was written and came out empty, which is a different",
            "failure and used to print the same sentence. A machine exported",
            "before its last scan is simply older; running `export_corpus.py`",
            "there closes it.", "",
            "---", "", f"_Generated {stamp}. Do not edit by hand._", ""]
    (paths.human(corpus) / "COVERAGE.md").write_text("\n".join(cov), encoding="utf-8")
    print(f"  scans say {ts:,}; corpus holds {tc:,} ({tc - ts:+,}) — see COVERAGE.md")


if __name__ == "__main__":
    main()
