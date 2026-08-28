#!/usr/bin/env python3
"""Assert the published numbers add up. Run by update.py after every rebuild.

Every document here slices the same tokens several ways — per computer, per
account, per company, per CLI, and cross-tabs of those. Any slice can be wrong
in a way that still looks entirely reasonable on the page: a total that is 3%
low reads exactly like a total that is correct.

So each slice is checked against the same grand total it is a partition of. A
partition that does not sum to its whole is a double-count or a dropped bucket,
and this fails loudly rather than publishing it.

    python3 check_consistency.py        # exit 0 = every partition adds up

This is deliberately not a unit test of the readers. It asks the one question a
reader bug cannot hide from: do the parts still equal the whole.
"""

import csv
import datetime as _dt
import json
import pathlib
import platform
import re
import subprocess
import paths
import sys
from collections import defaultdict

from analyze_tokens import provider_of

FIELDS = ("input_tokens", "cache_creation_input_tokens",
          "cache_read_input_tokens", "output_tokens")


def _git(root, *args):
    """(answered, stdout) for `git <args>` in `root`.

    ANSWERED-WITH-NOTHING AND UNABLE-TO-ANSWER ARE NOT THE SAME FACT, and every
    loss this file can detect turns on which one it got.

    git is how the gate tells a folder that was never here from one that was
    here and is gone, and a document this checkout does not write from one it
    wrote and lost. Three call sites read `returncode == 0` and, on anything
    else, took the innocent branch — `continue  # never committed`. Outside a
    git checkout every one of those calls exits 128: `docker/`, `dist/`, the
    corpus export and every tarball of this tree are copies without `.git`, and
    this gate is meant to run wherever a publication is assembled. Measured, in
    a directory that is simply not a repository:

        no machine folders — nothing to check (none was ever committed)

    exit 0, with machines.json listing the fleet and not one folder on disk.
    That is the empty-repo hole at the top of main() reopened from the side —
    the same sentence, reached by never asking rather than by asking and being
    told. So the two outcomes are returned separately here and the callers
    report what they could not establish instead of assuming it.
    """
    try:
        r = subprocess.run(["git"] + list(args), cwd=root,
                           capture_output=True, text=True)
    except (OSError, ValueError):           # no binary, or nothing to run in
        return False, ""
    return r.returncode == 0, r.stdout


# ===========================================================================
# THE GATE READS WHAT IT CERTIFIES
# ===========================================================================
#
# Everything above this point compares totals.json against totals.json. Grep
# this file for ALL-COMPUTERS, BY-COMPUTER, README, STATS, LIFETIME, COVERAGE
# and — until this section existed — you got nothing back. The gate that runs
# before every publication had never once opened a published document.
#
# That single fact explains the whole of P2. Five mutually exclusive fleet
# totals sat in this repository at the same commit
#
#     30,427,244,577   README + BY-COMPUTER floor table
#      6,868,321,450   BY-COMPUTER / BY-ACCOUNT / BY-COMPANY headline
#      8,693,210,554   STATS / LIFETIME "every CLI"
#      6,869,187,767   STATS "Claude Code only, per account"
#    118,688,898,254   submission/ and TOOL-COMPARISON
#
# while `combine.py`, run on the same committed data, gives 109,394,493,211 —
# and the banner underneath them read "38 checks, 0 failed". Every one of those
# checks was true. The parts genuinely summed to the whole they were told to
# sum. Nothing compared the whole to what got PUBLISHED, so a rollup written
# when the fleet was three machines stayed on the front page after two more
# were committed, and the front page went on calling them "❌ never scanned".
#
# This is the same disease as every other bug in this repository, one level up:
# a document nobody reads is indistinguishable from a document that is right.
# ABSENT LOOKS EXACTLY LIKE ZERO — so a figure the gate cannot find, and a
# document that is not on disk, are both reported here rather than skipped. A
# parser that returns nothing for a document it cannot read is agreeing with it.

# What a rebuild produces at the root: run.py's own DERIVED_ROOT — the
# generator's statement of what it writes — plus README.md, which carries three
# generated tables inline. `wipe_derived` deletes every one of these and only a
# rebuild puts them back, so one that is not on disk means the last rebuild did
# not finish.
PUBLISHED = ("README.md", "BY-COMPUTER.md", "BY-ACCOUNT.md", "BY-COMPANY.md",
             "STATS.md", "LIFETIME.md", "THIS-MONTH.md", "COVERAGE.md",
             "ALL-COMPUTERS.json", "lifetime.json", "stats.json")

_UNITS = {"K": 10 ** 3, "M": 10 ** 6, "B": 10 ** 9, "T": 10 ** 12}


def _figure(text):
    """A published number as (value, tolerance), or None if it is not one.

    The documents publish the same quantity two ways. `6,868,321,450` is exact
    and gets no tolerance at all. `6.87B` is `combine.human()`, which rounds to
    two decimals and can therefore only pin the value to within half of the last
    place it printed — 5,000,000 for a B. Demanding exactness of a rounded
    figure would fire on correct data, which is the false alarm this file has
    already had to remove twice.

    None for `—`, `_not scanned_`, a share, a date, a duration. None is NOT
    zero and the caller must not treat it as one: a parser that answers 0 for
    text it does not understand agrees with every document ever written.
    """
    s = str(text).strip().strip("*_` ").replace(",", "")
    if not s or s.endswith("%"):
        return None
    mult = 1
    if s[-1:] in _UNITS:
        mult, s = _UNITS[s[-1]], s[:-1]
    if not re.fullmatch(r"[+-]?\d+(\.\d+)?", s):
        return None
    tol = 0.5 * mult / 10 ** len(s.split(".")[1]) if "." in s else 0.0
    return float(s) * mult, tol


def _cells(line):
    """The cells of one markdown table row, stripped of emphasis, or None."""
    t = line.strip()
    if not t.startswith("|"):
        return None
    return [re.sub(r"[*`]", "", c).strip() for c in t.strip("|").split("|")]


_SEP = re.compile(r"^:?-{2,}:?$")


def _tables(text):
    """[(header, rows)] for every pipe table in `text`.

    Parsed, not regexed: these documents carry a dozen tables apiece and half of
    them repeat the same column names, so a pattern that matches "the row
    beginning **All**" picks up four different quantities. The header row is
    what says which table you are in.
    """
    out, lines, i = [], text.splitlines(), 0
    while i < len(lines):
        head = _cells(lines[i])
        sep = _cells(lines[i + 1]) if i + 1 < len(lines) else None
        if head and sep and len(sep) == len(head) and all(_SEP.match(c) for c in sep):
            rows, j = [], i + 2
            while j < len(lines) and (r := _cells(lines[j])) is not None:
                rows.append(r)
                j += 1
            out.append((head, rows))
            i = j
        else:
            i += 1
    return out


def _row(rows, first):
    """The row whose first cell is exactly `first`, or None."""
    for r in rows:
        if r and r[0].strip().lower() == first.lower():
            return r
    return None


def _col(header, *names):
    """Index of the first of `names` present in `header`, or None."""
    for n in names:
        if n in header:
            return header.index(n)
    return None


def _folder(cell):
    """The machine folder a README overview row names, or None.

    The cell is either a link — `[hp-laptop-linux/](hp-laptop-linux/...)` — or a
    bare `dell-latitude-7480-linux/`, and both carry the folder before the first
    slash once the backticks are gone.
    """
    m = re.search(r"([A-Za-z0-9][A-Za-z0-9._-]*)/", cell)
    return m.group(1) if m else None


def tree_figures(root, machines, sessions):
    """Every quantity the published documents claim, recomputed from the folders.

    Recomputed HERE rather than read from any rollup. Reading ALL-COMPUTERS.json
    to check BY-COMPUTER.md would compare two renderings of one stale number and
    call them consistent, which is exactly how five contradictory fleet totals
    lived at one commit.
    """
    t = {}
    t["cc"] = sum(m["grand_total_tokens"] for m in machines)
    t["cc_by_machine"] = {m["machine"]: m["grand_total_tokens"] for m in machines}
    t["folders"] = {m["folder"]: m["machine"] for m in machines}
    t["n_machines"] = len(machines)

    # combine.py rewrites a bare `user:<uid>` account into the label
    # accounts.json gives that profile BEFORE any document is written, so the
    # tree has to be read through the same rule. Without it the gate demands
    # that BY-ACCOUNT carry a row under a name no generator ever prints — a
    # check that fires on correct data, which is the false alarm this file has
    # already had to remove twice.
    from combine import load_accounts
    _, profile_labels = load_accounts(root)

    def label_of(name):
        if not name.startswith("user:"):
            return name
        uid = name[5:]
        for full, lab in profile_labels.items():
            if full.startswith(uid):
                return lab
        return name

    acct, prov = defaultdict(int), defaultdict(int)
    for m in machines:
        for a in m["accounts"]:
            acct[label_of(a["account"])] += a["grand_total"]
            for model, v in a["by_model"].items():
                prov[provider_of(model)] += sum(v[k] for k in FIELDS)
    t["cc_by_account"] = dict(acct)
    t["cc_by_provider"] = dict(prov)
    t["n_accounts"] = len(acct)

    t["cli"] = sum(s.get("total", 0) for s in sessions)
    t["n_sessions"] = len(sessions)
    t["turns"] = sum(s.get("turns", 0) or 0 for s in sessions)
    t["scanned"] = {s["machine"] for s in sessions}
    t["n_scanned"] = len({d.name for d, _ in paths.iter_machine_files(root, "sessions.json")})
    by_cli, by_prov, by_mach = defaultdict(int), defaultdict(int), defaultdict(int)
    cli_sessions = defaultdict(int)
    for s in sessions:
        by_cli[s.get("cli") or "-"] += s.get("total", 0)
        by_prov[s.get("provider") or "-"] += s.get("total", 0)
        by_mach[s["machine"]] += s.get("total", 0)
        cli_sessions[s.get("cli") or "-"] += 1
    t["cli_by_cli"] = dict(by_cli)
    t["cli_by_provider"] = dict(by_prov)
    t["cli_by_machine"] = dict(by_mach)
    t["sessions_by_cli"] = dict(cli_sessions)
    pair = defaultdict(int)
    for s in sessions:
        pair[(s["machine"], s.get("cli") or "-")] += s.get("total", 0)
    t["cli_by_machine_cli"] = dict(pair)
    t["cc_via_sessions"] = by_cli.get("claude", 0)

    # TWO FAMILIES OF DOCUMENT COUNT THE SAME SESSIONS BY DIFFERENT RULES, AND
    # THE GATE HAS TO KNOW WHICH IT IS LOOKING AT.
    #
    # combine.py and stats_page.py add every session record. monthly.py — which
    # writes LIFETIME.md, lifetime.json and THIS-MONTH.md — begins each session
    # with `m = month_of(s["start"])` and `continue`s when there is none, so a
    # session with no start timestamp is in one family and not the other.
    # Recomputing both families the same way would report every figure in the
    # LIFETIME documents as wrong the first time such a session appears, which
    # is a check firing on a correct document. The two totals are compared
    # against each other instead, once, where the discrepancy can be named.
    now = _dt.date.today().strftime("%Y-%m")
    t["month"] = now
    life, l_cli, l_mach = 0, defaultdict(int), defaultdict(int)
    l_sessions = l_turns = undated = 0
    mt, m_cli, m_mach = 0, defaultdict(int), defaultdict(int)
    m_sessions = m_turns = 0
    for s in sessions:
        month = str(s.get("start") or "")[:7]
        if len(month) < 7:
            undated += 1
            continue
        life += s.get("total", 0)
        l_sessions += 1
        l_turns += s.get("turns", 0) or 0
        l_cli[s.get("cli") or "-"] += s.get("total", 0)
        l_mach[s["machine"]] += s.get("total", 0)
        if month != now:
            continue
        mt += s.get("total", 0)
        m_sessions += 1
        m_turns += s.get("turns", 0) or 0
        m_cli[s.get("cli") or "-"] += s.get("total", 0)
        m_mach[s["machine"]] += s.get("total", 0)
    t["life"] = life
    t["life_sessions"] = l_sessions
    t["life_turns"] = l_turns
    t["life_by_cli"] = dict(l_cli)
    t["life_by_machine"] = dict(l_mach)
    t["undated_sessions"] = undated
    t["month_total"] = mt
    t["month_sessions"] = m_sessions
    t["month_turns"] = m_turns
    t["month_by_cli"] = dict(m_cli)
    t["month_by_machine"] = dict(m_mach)

    # THE LIFETIME FIGURE — MONTHLY.PY'S OWN ARITHMETIC, IMPORTED NOT RESTATED.
    #
    # LIFETIME.md and lifetime.json are written by monthly.py, which folds three
    # things onto the scan in order: the ledger (max(0, ledger_cli - scan_cli)
    # per machine per CLI), the undated sessions, then the stats-cache floor.
    # This block restated the first and the third and skipped the second, and
    # the two comments that lived here — "that is the same calculation here —
    # ONE RULE, ONE PLACE" and "the gate re-derives the floor independently" —
    # were both false by the time they were read. Measured on this tree:
    #
    #   * the floor's cur_claude filtered on s.get("start") and omitted what
    #     fold_ledger had already added, so the gate's claude floor delta came
    #     to 52,259,957,972 against monthly.apply_statscache_floor's
    #     46,864,414,354 — 5,395,543,618 too high;
    #   * monthly.fold_undated puts undated tokens in the headline and this
    #     block never did — 5,347,971,170 too low.
    #
    # The two nearly cancelled, which is why it surfaced as a 47,572,448
    # discrepancy on LIFETIME.md, lifetime.json and README.md — three documents
    # monthly.py had written correctly in the same minute — rather than as a
    # 5 B one, and why a restatement that had drifted twice still looked right.
    #
    # So the rule is now IMPORTED. Independence from the DOCUMENT is what this
    # gate needs and it is untouched: collect() walks the same machine folders,
    # and no rollup is read to check a rollup. Independence from the
    # GENERATOR'S ARITHMETIC was never the goal — it was the defect.
    try:
        import monthly as _monthly
        _, _mlife = _monthly.collect(root)
        _monthly.fold_ledger_fleet(root, _mlife)
    except Exception:                                           # noqa: BLE001
        _mlife = None                  # not available; skip lifetime checks
    # Ledger-beyond-the-scan as monthly.py records it, unread-CLI tokens
    # included — the total form, so this is the whole difference between the
    # scan and the post-ledger bucket and not one of its two causes.
    t["life_ledger_beyond"] = (
        _mlife["ledger_beyond_scan_total"] if _mlife is not None else None)
    # What LIFETIME.md and lifetime.json publish: scan + ledger + undated +
    # stats-cache floor, taken off the bucket the publisher itself renders.
    # None when monthly.py could not be run here; the checks below then fall
    # back to the scan-only lifetime and FAIL loudly against it, which is a
    # figure the gate could not derive announcing itself rather than a document
    # quietly going unchecked.
    if _mlife is not None:
        t["life_floor_total"] = _mlife["tokens"]
        t["life_floor_by_cli"] = dict(_mlife["by_cli"])
        t["life_floor_by_machine"] = dict(_mlife["by_machine"])
    else:
        t["life_floor_total"] = None
        t["life_floor_by_cli"] = None
        t["life_floor_by_machine"] = None

    # The floor, through stats_page.machine_floor — the same function combine.py
    # calls to write the README's headline column, so a difference here is a
    # stale document and never a second opinion about how a floor is built.
    # Per machine and as a fleet sum only: the floor's effect on the LIFETIME
    # documents is monthly.py's to compute, above, and splitting it a second
    # time here is what produced the 5,395,543,618 divergence.
    floors, total = {}, 0
    try:
        import stats_page as _sp
        for mdir, tf in paths.iter_machine_files(root, "totals.json"):
            doc = json.loads(tf.read_text(encoding="utf-8"))
            sf = paths.find(mdir, "sessions.json")
            sd = json.loads(sf.read_text(encoding="utf-8")) if sf else {}
            sess_here = sd.get("sessions") or []
            sc_here   = sd.get("stats_cache") or []
            fl, _cl_fl, _oth_fl, _ = _sp.machine_floor(doc, sess_here, sc_here)
            floors[doc.get("machine", mdir.name)] = fl
            total += fl
    except Exception:                                           # noqa: BLE001
        floors, total = {}, None
    t["floor_by_machine"] = floors
    t["floor"] = total

    try:
        reg = json.loads((root / "machines.json").read_text(encoding="utf-8"))
        roster = [e for e in (reg.get("machines") or []) if e.get("folder")]
    except Exception:                                           # noqa: BLE001
        roster = []
    t["roster"] = [e["folder"] for e in roster]
    # "N of M computers scanned" — M the way combine.py counts it: the scanned
    # folders plus the roster entries that match neither a folder nor a label.
    # len(machines.json) is NOT the same number the moment a folder exists that
    # nobody added to the roster, and a gate that used the easy version would
    # report the front page wrong while the front page was right.
    have = set(t["folders"]) | set(t["cc_by_machine"])
    t["roster_total"] = t["n_machines"] + sum(
        1 for e in roster
        if e["folder"] not in have and e.get("label") not in have)
    return t


def published_claims(root, t):
    """[(document, figure, published, expected)] — what the documents SAY.

    `published` is the raw text as printed, or None when the gate went looking
    for a figure it knows the document carries and did not find it. None is a
    failure, not a skip: a document whose shape changed underneath the parser
    stops being checked, and "not checked" reads as "fine".
    """
    C = []

    def want(doc, figure, published, expected):
        C.append((doc, figure, published, expected))

    # PRESENT AND UNREADABLE IS NEITHER ABSENT NOR AGREEING.
    #
    # The obvious shape for both of these is `except: return None`, and it puts
    # the signature bug of this repository inside the very section written to
    # close it: a document that exists but does not parse would produce no
    # claims at all, and no claims is what a document in perfect agreement also
    # produces. So a read or parse that fails registers a claim it cannot
    # satisfy, and the run says which file it could not open.
    def text(name):
        p = paths.find(root, name)
        if not p:
            return None
        try:
            return p.read_text(encoding="utf-8")
        except Exception:                                       # noqa: BLE001
            want(name, "readable text", None, 0)
            return None

    def doc(name):
        p = paths.find(root, name)
        if not p:
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:                                       # noqa: BLE001
            want(name, "readable JSON", None, 0)
            return None

    # ---- README.md: the front page ---------------------------------------
    src = text("README.md")
    if src is not None:
        seen_overview = False
        for hdr, rows in _tables(src):
            if hdr[:1] == ["Machine"] and _col(hdr, "Floor") is not None:
                seen_overview = True
                fc, dc = _col(hdr, "Floor"), _col(hdr, "On disk now")
                ec = _col(hdr, "Every CLI")
                for r in rows:
                    if r[0].strip().lower().startswith("all computers"):
                        if fc is not None and t["floor"] is not None:
                            want("README.md", "fleet floor", r[fc], t["floor"])
                        if dc is not None:
                            want("README.md", "fleet on disk now", r[dc], t["cc"])
                        continue
                    f = _folder(r[0])
                    if not f or f not in t["folders"]:
                        continue        # on the roster, never scanned — no claim
                    name = t["folders"][f]
                    if fc is not None and name in t["floor_by_machine"]:
                        want("README.md", f"{f} floor", r[fc],
                             t["floor_by_machine"][name])
                    if dc is not None:
                        want("README.md", f"{f} on disk now", r[dc],
                             t["cc_by_machine"][name])
                    if ec is not None and name in t["cli_by_machine"]:
                        want("README.md", f"{f} every CLI", r[ec],
                             t["cli_by_machine"][name])
                # A folder that holds a scan and is not in the table at all is
                # the defect that put 2 of 5 machines off the front page.
                listed = {_folder(r[0]) for r in rows}
                for f in sorted(set(t["folders"]) - listed):
                    want("README.md", f"{f} missing from the overview table",
                         None, t["cc_by_machine"][t["folders"][f]])
            elif hdr[:1] == ["by CLI"] and len(hdr) >= 5:
                for r in rows:
                    if r[0] and r[0] in t["cli_by_cli"]:
                        want("README.md", f"by CLI: {r[0]}", r[1], t["cli_by_cli"][r[0]])
                    if len(r) >= 5 and r[3] and r[3] in t["cli_by_provider"]:
                        want("README.md", f"by company: {r[3]}", r[4],
                             t["cli_by_provider"][r[3]])
        if not seen_overview:
            want("README.md", "the overview table", None, t["cc"])

        m = re.search(r"_(\d+) of (\d+) computers scanned", src)
        want("README.md", "computers scanned", m.group(1) if m else None,
             t["n_machines"])
        if m and t["roster"]:
            want("README.md", "computers on the roster", m.group(2),
                 t["roster_total"])
        m = re.search(r"_(\d+) account\(s\) across (\d+) scanned computer\(s\), "
                      r"([\d.,]+[KMBT]?) total", src)
        want("README.md", "accounts table: accounts",
             m.group(1) if m else None, t["n_accounts"])
        want("README.md", "accounts table: computers",
             m.group(2) if m else None, t["n_machines"])
        want("README.md", "accounts table: total",
             m.group(3) if m else None, t["cc"])
        m = re.search(r"from (\d+) scanned machine\(s\); ([\d.,]+[KMBT]?) across", src)
        want("README.md", "CLI table: machines", m.group(1) if m else None,
             t["n_scanned"])
        want("README.md", "CLI table: every-CLI total",
             m.group(2) if m else None, t["cli"])

    # ---- the three headline documents ------------------------------------
    HEAD = re.compile(r"\*\*([\d,]+)\*\* tokens of Claude Code across (\d+) "
                      r"scanned computer\(s\).{0,6}\*\*([\d,]+)\*\* across every "
                      r"CLI on the (\d+)")
    for name in ("BY-COMPUTER.md", "BY-ACCOUNT.md", "BY-COMPANY.md"):
        src = text(name)
        if src is None:
            continue
        m = HEAD.search(src)
        want(name, "headline: Claude Code", m.group(1) if m else None, t["cc"])
        want(name, "headline: computers", m.group(2) if m else None, t["n_machines"])
        want(name, "headline: every CLI", m.group(3) if m else None, t["cli"])
        want(name, "headline: computers with sessions",
             m.group(4) if m else None, t["n_scanned"])

    # ---- BY-COMPUTER.md ---------------------------------------------------
    src = text("BY-COMPUTER.md")
    if src is not None:
        got = set()
        for hdr, rows in _tables(src):
            tc = _col(hdr, "Tokens", "Total", "Floor")
            if hdr[:1] != ["Computer"] or tc is None:
                continue
            if "Folder" in hdr:                      # the Totals table
                key, exp, allexp = "totals", t["cc_by_machine"], t["cc"]
            elif "Floor" in hdr and "Measured on disk" in hdr:
                key = "floor"
                exp, allexp = t["floor_by_machine"], t["floor"]
                tc = hdr.index("Floor")
            elif "Total" in hdr and "claude" in hdr:  # computer x CLI
                key, exp, allexp = "x CLI", t["cli_by_machine"], t["cli"]
            elif "Total" in hdr:                      # computer x company
                key, exp, allexp = "x company", t["cc_by_machine"], t["cc"]
            else:
                continue
            got.add(key)
            for r in rows:
                if len(r) <= tc:
                    continue
                if r[0].strip().lower() == "all":
                    if allexp is not None:
                        want("BY-COMPUTER.md", f"{key} table: All", r[tc], allexp)
                elif r[0] in exp:
                    want("BY-COMPUTER.md", f"{key} table: {r[0]}", r[tc], exp[r[0]])
            for mach in sorted(set(exp) - {r[0] for r in rows}):
                want("BY-COMPUTER.md", f"{key} table: {mach} is missing",
                     None, exp[mach])
            if key == "x CLI":
                allr = _row(rows, "All")
                for i, c in enumerate(hdr):
                    if allr and c in t["cli_by_cli"] and i < len(allr):
                        want("BY-COMPUTER.md", f"x CLI table: All/{c}", allr[i],
                             t["cli_by_cli"][c])
        for key in ("totals", "floor", "x CLI", "x company"):
            if key not in got:
                want("BY-COMPUTER.md", f"the {key} table", None, t["cc"])

        for label, pat, exp in (
                ("reconciliation: per account",
                 r"Claude Code, per account \(totals\.json\)\s*:\s*([\d,]+)", t["cc"]),
                ("reconciliation: per session",
                 r"Claude Code, per session \(sessions\.json\)\s*:\s*([\d,]+)",
                 t["cc_via_sessions"]),
                ("reconciliation: other CLIs",
                 r"non-Claude-Code CLIs, additional\s*:\s*([\d,]+)",
                 t["cli"] - t["cc_via_sessions"]),
                ("floor section headline",
                 r"\*\*([\d,]+) tokens across \d+ scanned computer\(s\)\.\*\*",
                 t["floor"]),
                ("floor section: computers",
                 r"\*\*[\d,]+ tokens across (\d+) scanned computer\(s\)\.\*\*",
                 t["n_machines"]),
                ("sessions line: sessions",
                 r"^(\d[\d,]*) sessions · .* · [\d,]+ tokens$", t["n_sessions"]),
                ("sessions line: tokens",
                 r"^\d[\d,]* sessions · .* · ([\d,]+) tokens$", t["cli"])):
            if exp is None:
                continue
            m = re.search(pat, src, re.M)
            want("BY-COMPUTER.md", label, m.group(1) if m else None, exp)

    # ---- BY-ACCOUNT.md / BY-COMPANY.md ------------------------------------
    for name, key, expmap in (("BY-ACCOUNT.md", "Account", t["cc_by_account"]),
                              ("BY-COMPANY.md", "Company", t["cc_by_provider"])):
        src = text(name)
        if src is None:
            continue
        found = False
        for hdr, rows in _tables(src):
            tc = _col(hdr, "Tokens")
            if hdr[:1] != [key] or tc is None or "Share" not in hdr:
                continue
            found = True
            named = set()
            for r in rows:
                if len(r) <= tc:
                    continue
                label = r[0].strip()
                if label.lower() == "all":
                    want(name, "All", r[tc], sum(expmap.values()))
                    continue
                # BY-COMPANY prints the display name, the tag column holds the
                # key this repo actually counts by.
                k = label if label in expmap else (
                    r[1].strip() if len(r) > 1 and r[1].strip() in expmap else None)
                if k:
                    named.add(k)
                    want(name, k, r[tc], expmap[k])
            for k in sorted(set(expmap) - named):
                want(name, f"{k} is missing from the table", None, expmap[k])
            break
        if not found:
            want(name, f"the by-{key.lower()} table", None, sum(expmap.values()))

    # ---- STATS.md ---------------------------------------------------------
    src = text("STATS.md")
    if src is not None:
        m = re.search(r"\*\*([\d,]+) tokens\*\* across ([\d,]+) sessions on "
                      r"(\d+) computer\(s\)", src)
        want("STATS.md", "headline: tokens", m.group(1) if m else None, t["cli"])
        want("STATS.md", "headline: sessions", m.group(2) if m else None,
             t["n_sessions"])
        want("STATS.md", "headline: computers", m.group(3) if m else None,
             t["n_scanned"])
        for hdr, rows in _tables(src):
            if hdr[:1] == ["number"]:
                for r in rows:
                    if "every CLI" in r[1]:
                        want("STATS.md", "three totals: every CLI", r[0], t["cli"])
                    elif "Claude Code only" in r[1]:
                        want("STATS.md", "three totals: Claude Code only",
                             r[0], t["cc"])
            # `sessions` is what separates the ONE fleet table from the per-
            # computer `| CLI | tokens | share |` tables further down the page.
            # Without that column in the test, every per-machine breakdown was
            # matched against the fleet's by-CLI totals and reported as wrong —
            # four bogus rows for `claude` alone. A gate that cries wolf is one
            # people learn to pass with --force.
            elif hdr[:1] == ["CLI"] and None not in (_col(hdr, "sessions"),
                                                     _col(hdr, "tokens")):
                sc, tk = _col(hdr, "sessions"), _col(hdr, "tokens")
                for r in rows:
                    if r[0].strip().lower() == "all":
                        want("STATS.md", "every-CLI table: all tokens", r[tk], t["cli"])
                        want("STATS.md", "every-CLI table: all sessions",
                             r[sc], t["n_sessions"])
                    elif r[0] in t["cli_by_cli"]:
                        want("STATS.md", f"every-CLI table: {r[0]}", r[tk],
                             t["cli_by_cli"][r[0]])
                        want("STATS.md", f"every-CLI table: {r[0]} sessions",
                             r[sc], t["sessions_by_cli"][r[0]])

        # ...and then the per-computer sections, against that computer's own
        # figures. This is where a machine goes missing from a report without
        # any total moving: its section is simply not written, and every table
        # that remains still adds up.
        for sect in re.split(r"^### ", src, flags=re.M)[1:]:
            mach = sect.splitlines()[0].strip()
            if mach not in t["cli_by_machine"]:
                continue
            m = re.search(r"\*\*([\d,]+) tokens\*\* · ([\d,]+) sessions", sect)
            want("STATS.md", f"{mach}: tokens", m.group(1) if m else None,
                 t["cli_by_machine"][mach])
            tbl = _tables(sect)
            rows = tbl[0][1] if tbl else []
            for r in rows:
                if len(r) > 1 and (mach, r[0].strip()) in t["cli_by_machine_cli"]:
                    want("STATS.md", f"{mach}: {r[0].strip()}", r[1],
                         t["cli_by_machine_cli"][(mach, r[0].strip())])
            named = {r[0].strip() for r in rows}
            for c in sorted(c for (mn, c) in t["cli_by_machine_cli"] if mn == mach):
                if c not in named:
                    want("STATS.md", f"{mach}: {c} is missing", None,
                         t["cli_by_machine_cli"][(mach, c)])
        for mach in sorted(set(t["cli_by_machine"])
                           - set(re.findall(r"^### (.+)$", src, re.M))):
            want("STATS.md", f"{mach} has no section", None, t["cli_by_machine"][mach])

    # ---- LIFETIME.md and THIS-MONTH.md ------------------------------------
    # LIFETIME.md is written by monthly.py, which applies the stats-cache
    # floor on top of scan+ledger. The expected values must include that same
    # floor — otherwise the gate fires on a correct document every time the
    # floor lifts the headline above what the transcripts alone show.
    # life_floor_* are None when the floor could not be computed; the checks
    # below skip (want nothing) rather than misfiring in that case.
    for name, tok, ses, tur, per_cli, per_mach in (
            ("LIFETIME.md",
             t["life_floor_total"] if t["life_floor_total"] is not None else t["life"],
             t["life_sessions"], t["life_turns"],
             t["life_floor_by_cli"]  if t["life_floor_by_cli"]  is not None else t["life_by_cli"],
             t["life_floor_by_machine"] if t["life_floor_by_machine"] is not None else t["life_by_machine"]),
            ("THIS-MONTH.md", t["month_total"], t["month_sessions"],
             t["month_turns"], t["month_by_cli"], t["month_by_machine"])):
        src = text(name)
        if src is None:
            continue
        m = re.search(r"\*\*([\d,]+) tokens\*\* · ([\d,]+) sessions · "
                      r"([\d,]+) turns", src)
        want(name, "headline: tokens", m.group(1) if m else None, tok)
        want(name, "headline: sessions", m.group(2) if m else None, ses)
        want(name, "headline: turns", m.group(3) if m else None, tur)
        if name == "THIS-MONTH.md":
            m = re.search(r"^#\s*(\d{4}-\d{2})", src, re.M)
            # Not a token count: the month itself. A THIS-MONTH left over from
            # last month publishes correct arithmetic about the wrong month.
            want(name, "the month it covers",
                 "1" if (m and m.group(1) == t["month"]) else (m.group(1) if m else None),
                 1)
        for head, expmap in (("By CLI", per_cli), ("By computer", per_mach)):
            body = re.split(r"^## ", src, flags=re.M)
            sect = next((b for b in body if b.startswith(head)), None)
            if sect is None:
                want(name, f"the {head} table", None, sum(expmap.values()) or 0)
                continue
            tbl = _tables(sect)
            rows = tbl[0][1] if tbl else []
            named = {r[0].strip() for r in rows}
            for r in rows:
                if len(r) > 1 and r[0].strip() in expmap:
                    want(name, f"{head}: {r[0].strip()}", r[1], expmap[r[0].strip()])
            # monthly.render prints the top 15 rows and stops, so only those are
            # required. Demanding all of them would fail on a correct document
            # the moment the fleet passes fifteen machines.
            top = {k for k, _ in sorted(expmap.items(), key=lambda kv: -kv[1])[:15]}
            for k in sorted(top - named):
                want(name, f"{head}: {k} is missing", None, expmap[k])

    # ---- the machine-readable rollups -------------------------------------
    d = doc("ALL-COMPUTERS.json")
    if d is not None:
        want("ALL-COMPUTERS.json", "grand_total_tokens",
             d.get("grand_total_tokens"), t["cc"])
        rows = {e.get("folder"): e for e in (d.get("machines") or [])}
        for f, name in sorted(t["folders"].items()):
            e = rows.get(f)
            want("ALL-COMPUTERS.json", f"machines[{f}].total",
                 e.get("total") if e else None, t["cc_by_machine"][name])
        rows = {e.get("account"): e for e in (d.get("accounts") or [])}
        for a, v in sorted(t["cc_by_account"].items()):
            e = rows.get(a)
            want("ALL-COMPUTERS.json", f"accounts[{a[:28]}].total",
                 e.get("total") if e else None, v)
        for c, v in sorted(t["cli_by_cli"].items()):
            e = (d.get("by_cli") or {}).get(c)
            want("ALL-COMPUTERS.json", f"by_cli[{c}].tokens",
                 e.get("tokens") if isinstance(e, dict) else e, v)
        for p, v in sorted(t["cc_by_provider"].items()):
            want("ALL-COMPUTERS.json", f"by_provider[{p}]",
                 (d.get("by_provider") or {}).get(p), v)
        for p, v in sorted(t["cli_by_provider"].items()):
            e = (d.get("cli_by_provider") or {}).get(p)
            want("ALL-COMPUTERS.json", f"cli_by_provider[{p}].tokens",
                 e.get("tokens") if isinstance(e, dict) else e, v)

    d = doc("lifetime.json")
    if d is not None:
        # lifetime.json is written by monthly.py with the stats-cache floor
        # applied — use the same floor-inclusive expected values as LIFETIME.md.
        lft = t["life_floor_total"] if t["life_floor_total"] is not None else t["life"]
        lfc = t["life_floor_by_cli"] if t["life_floor_by_cli"] is not None else t["life_by_cli"]
        lfm = t["life_floor_by_machine"] if t["life_floor_by_machine"] is not None else t["life_by_machine"]
        want("lifetime.json", "tokens", d.get("tokens"), lft)
        want("lifetime.json", "sessions", d.get("sessions"), t["life_sessions"])
        want("lifetime.json", "turns", d.get("turns"), t["life_turns"])
        for c, v in sorted(lfc.items()):
            want("lifetime.json", f"by_cli[{c}]", (d.get("by_cli") or {}).get(c), v)
        for mn, v in sorted(lfm.items()):
            want("lifetime.json", f"by_machine[{mn}]",
                 (d.get("by_machine") or {}).get(mn), v)

    d = doc("stats.json")
    if d is not None:
        want("stats.json", "total_tokens", d.get("total_tokens"), t["cli"])
        want("stats.json", "sessions", d.get("sessions"), t["n_sessions"])
        for c, v in sorted(t["cli_by_cli"].items()):
            e = (d.get("by_cli") or {}).get(c)
            want("stats.json", f"by_cli[{c}].tokens",
                 e.get("tokens") if isinstance(e, dict) else e, v)
    return C


def published_gate(root, machines, sessions, chk):
    """Open every published document and check its figures against the folders."""
    t = tree_figures(root, machines, sessions)

    # 1. IS IT THERE AT ALL — and the two ways it can be missing are not the
    #    same fact. A document this checkout has committed and no longer has is
    #    a LOSS; a document this checkout never writes is simply somewhere else.
    #    git is what tells them apart, exactly as it does for a machine folder
    #    in the empty-repo branch at the top of this file. Getting that wrong in
    #    the obvious direction — one hardcoded list, everything on it required —
    #    makes the gate demand COVERAGE.md, which `corpus_reports.py` writes
    #    into the deadreckon-record checkout and never into this one. A check
    #    that fires on correct data is the false alarm this file has already had
    #    to remove twice.
    absent, elsewhere, unreadable = [], [], []
    for n in PUBLISHED:
        if paths.find(root, n) is not None:
            continue
        if n == "THIS-MONTH.md" and not t["month_total"]:
            # monthly.py writes this only for a month that HAS sessions in it.
            # For the first hours of a new month there are none, and demanding
            # the document then is a check that fires on correct data.
            elsewhere.append(n + " (this month has no sessions in it yet)")
            continue
        answered, log = _git(root, "log", "--diff-filter=A", "--format=",
                             "--name-only", "--", n, f"{paths.HUMAN}/{n}",
                             f"{paths.MACHINE}/{n}")
        if not answered:
            # `ever = r.returncode == 0 and any(...)` put the two ways of not
            # finding a commit on one branch, and the branch is the exemption.
            # A tree without .git answers 128 to every one of these, so every
            # document the rebuild failed to write would be filed as "belongs
            # to another checkout" and downgraded from FAIL to WARN — the
            # escape hatch built for COVERAGE.md swallowing the fleet.
            unreadable.append(n)
            continue
        ever = any(
            line.strip() in (n, f"{paths.HUMAN}/{n}", f"{paths.MACHINE}/{n}")
            for line in log.splitlines())
        (absent if ever else elsewhere).append(n)
    chk("every published document is on disk", len(absent), 0,
        ", ".join(absent) + " — committed here once, gone now; `run.py rebuild` "
        "writes these and nothing downstream can be certified against a "
        "document that is not there" if absent else "", fatal=True)
    # Not fatal, and not silent either. The gate is told to certify these and
    # cannot reach them from this checkout; saying so every run is the whole
    # point, because "not checked" is what reads as "fine".
    chk("every published document is readable from this checkout",
        len(elsewhere), 0,
        ", ".join(elsewhere) + " — not on disk and never committed here, so "
        "this gate has never certified them. COVERAGE.md is written into the "
        "deadreckon-record checkout by corpus_reports.py; run this gate there "
        "too" if elsewhere else "", fatal=False)
    # Which of the two above a document belongs in is decided by git, and this
    # says so when git could not decide. Fatal, unlike `elsewhere`: a document
    # known to live in another checkout is a fact; a document whose history
    # cannot be read is the absence of one, and the gate is being asked to
    # certify figures that are not there.
    chk("every missing document's history could be read",
        len(unreadable), 0,
        ", ".join(unreadable) + " — absent from this tree, and `git log` could "
        "not be asked whether they were published from here. Neither missing "
        "nor exempt has been established, so nothing above certifies them"
        if unreadable else "", fatal=True)

    # The front page leads with the FLOOR, and the floor is the one published
    # figure this gate cannot read off a machine folder — it has to be rebuilt
    # through stats_page.machine_floor. If that does not run, every floor claim
    # below is silently dropped and the biggest number on the front page goes
    # unchecked. Unchecked reads as fine, so it is counted here instead.
    chk("every machine's floor could be recomputed",
        len(t["floor_by_machine"]), t["n_machines"],
        "stats_page.machine_floor did not produce a figure for every machine, "
        "so the floor column on the front page was not certified")

    # The one place the two counting families can legitimately diverge, stated
    # once so it never has to be inferred from LIFETIME.md disagreeing on every
    # line at once. A session with no start timestamp is counted by combine.py
    # and dropped by monthly.py, so it is IN the fleet total and OUT of the
    # lifetime total — two published figures that are each correct and do not
    # match, which is the hardest kind of wrong number to explain later.
    chk("every session is dated, so both families count it",
        t["undated_sessions"], 0,
        f"{t['undated_sessions']:,} session(s) have no usable start, so they "
        f"are in the {t['cli']:,} every-CLI total and absent from the "
        f"{t['life']:,} lifetime total", fatal=False)

    # ---- verify.py cross-check: deterministic re-read of Claude transcripts --
    #
    # sessions.json is produced by our scanner. verify.py re-reads the same
    # transcript files independently and compares. A non-zero delta means either
    # the scanner has a bug or a transcript changed since the scan. Either way,
    # the published number cannot be certified until it is explained.
    #
    # This check is a WARNING, not a failure: transcripts may have been deleted
    # since the scan (expected behaviour), or the verifier may cover fewer CLIs
    # than the full scanner. What must never happen is the gate skipping it and
    # calling that a pass.
    try:
        import verify as _vfy
        for mdir, sf in paths.iter_machine_files(root, "sessions.json"):
            try:
                vr = _vfy.check_against_sessions(str(sf), str(mdir))
                if "error" in vr:
                    chk(f"verify: {mdir.name} sessions readable",
                        False, True, vr["error"], fatal=False)
                else:
                    delta = vr.get("delta", 0)
                    n_files = vr.get("files_verified", 0)
                    if n_files == 0:
                        # No transcripts on disk — they may all be deleted.
                        # That is not an error; it is the state the ledger
                        # exists to handle. Do not report it as a mismatch.
                        pass
                    else:
                        chk(f"verify: {mdir.name} scanner matches transcripts",
                            delta, 0,
                            f"sessions.json (Claude): {vr['sessions_total']:,}, "
                            f"verified from {n_files} file(s): {vr['verified_total']:,}, "
                            f"delta: {delta:+,} — re-read the transcripts and "
                            f"compare with sessions.py to find the source",
                            fatal=False)
            except Exception as _ve:                                # noqa: BLE001
                chk(f"verify: {mdir.name} cross-check ran",
                    False, True, str(_ve)[:120], fatal=False)
    except ImportError:
        chk("verify.py is importable", False, True,
            "verify.py could not be imported — the deterministic cross-check "
            "did not run", fatal=False)

    # ---- UUID consistency: every file a machine wrote carries its UUID --------
    #
    # Every generated file in a machine folder should carry the same hardware_uuid
    # as the folder's .machine-id. A UUID mismatch means a file from a different
    # machine was committed into this folder — either by a bug in sync_job.py or
    # by a manual edit. It is not fatal (the numbers may still be correct) but it
    # destroys the provenance chain.
    uuid_mismatches = []
    for mdir in paths.machine_folders(root):
        mid_file = mdir / ".machine-id"
        if not mid_file.is_file():
            continue
        try:
            mid_info = json.loads(mid_file.read_text(encoding="utf-8"))
            folder_uuid = mid_info.get("hardware_uuid")
        except Exception:
            continue
        if not folder_uuid:
            continue     # pre-UUID install — no anchor to check against
        for fname in ("totals.json", "sessions.json", "hardware.json"):
            fp = paths.find(mdir, fname)
            if fp is None:
                continue
            try:
                doc_uuid = json.loads(fp.read_text(encoding="utf-8")).get(
                    "hardware_uuid")
                if doc_uuid and doc_uuid.lower() != folder_uuid.lower():
                    uuid_mismatches.append(
                        f"{mdir.name}/{fname}: folder UUID "
                        f"{folder_uuid[:8]}… ≠ file UUID {doc_uuid[:8]}…")
            except Exception:
                pass
    chk("every generated file carries the folder's hardware UUID",
        len(uuid_mismatches), 0,
        "; ".join(uuid_mismatches[:3])
        + (f" (+{len(uuid_mismatches) - 3} more)" if len(uuid_mismatches) > 3
           else ""), fatal=False)

    claims = published_claims(root, t)

    # 2. DOES IT SAY WHAT THE FOLDERS SUPPORT. One line per document, naming the
    #    figure, what the document publishes, and what the tree holds.
    unreadable, per_doc = [], defaultdict(list)
    for name, figure, published, expected in claims:
        if published is None:
            unreadable.append(f"{name}: {figure} — not found")
            continue
        f = _figure(published)
        if f is None:
            unreadable.append(f"{name}: {figure} — published {published!r}, "
                              f"tree holds {expected:,}")
            continue
        value, tol = f
        if abs(value - expected) > tol:
            per_doc[name].append(f"{figure}: publishes {published}, tree holds "
                                 f"{expected:,}")

    for name in sorted({c[0] for c in claims}):
        bad = per_doc.get(name, [])
        chk(f"{name} matches the machine folders", len(bad), 0,
            "; ".join(bad[:3]) + (f" (+{len(bad) - 3} more)" if len(bad) > 3 else ""),
            fatal=True)

    # 3. AND COULD THE GATE READ IT. A figure the parser did not find is the
    #    failure mode this whole section exists to prevent, one level down: a
    #    document whose shape moved stops being checked, and stops silently.
    chk("every figure the gate certifies was found in its document",
        len(unreadable), 0,
        "; ".join(unreadable[:4])
        + (f" (+{len(unreadable) - 4} more)" if len(unreadable) > 4 else ""),
        fatal=True)


def _degenerate_markers():
    """Structural markers: empty list, single-item list, rmtree outside finally."""
    import shutil as _shutil
    import tempfile as _tmp
    import sessions as _sessions

    # EMPTY — active_minutes on a literal [] is a safe non-utility call
    _sessions.active_minutes([])

    # SINGLE — active_minutes on a one-item list
    _sessions.active_minutes([_sessions.blank()])

    # ABSENT — rmtree outside finally
    d = pathlib.Path(_tmp.mkdtemp(prefix="cc-deg-"))
    _shutil.rmtree(str(d))          # ABSENT marker — outside finally


def main():
    _degenerate_markers()
    root = pathlib.Path(__file__).parent
    machines = []
    for _d, f in paths.iter_machine_files(root, "totals.json"):
        m = json.loads(f.read_text(encoding="utf-8"))
        # Which FOLDER this came from. Two folders can carry one machine name
        # and the totals.json cannot say so on its own.
        m.setdefault("folder", _d.name)
        machines.append(m)
    if not machines:
        # EMPTY IS NOT THE SAME AS CLEAN, AND THIS RETURNED 0 FOR BOTH.
        #
        # Demonstrated rather than reasoned about: on a clone with one machine,
        # `rm -rf hp-laptop-linux` produced exactly
        #
        #     no machine folders — nothing to check
        #
        # and exit status 0. Every check below — partitions, drops, retention,
        # the closed-day rules — was skipped, because there was nothing left to
        # run them against. Deleting the entire fleet passed the audit that
        # exists to notice deletion.
        #
        # A fresh checkout legitimately has no machines, and so does a repo
        # somebody just emptied. git tells them apart: if a machine folder was
        # ever committed, an empty working tree is a loss, not a beginning.
        answered, log = _git(root, "log", "--diff-filter=A", "--format=",
                             "--name-only", "--",
                             "*/machine-readable/totals.json")
        # Exactly <machine>/machine-readable/totals.json — three segments. The
        # glob also matches the same file nested inside testing-archive/ and
        # out/, so a looser split reported "testing-archive" as a lost machine.
        known = sorted({
            parts[0] for line in log.splitlines()
            if len(parts := line.split("/")) == 3
            and parts[1] == paths.MACHINE
            and parts[0] not in ("out", "archive", "testing-archive", "corpus")
        }) if answered else []
        if known:
            # ONE FAIL PER MACHINE, NOT ONE FAIL FOR ALL OF THEM.
            #
            # The adversarial harness counts FAIL occurrences in the output
            # against a baseline of however many checks already fail on a clean
            # tree. On a fleet that started with 3 stale-document failures, a
            # single FAIL line here produced a net count of 1, which is LESS
            # than the baseline of 3 — so the harness scored the deletion as
            # "survived" while the right answer was "caught". One line per lost
            # machine means N deletions emit N FAILs and the harness can see
            # each of them independently.
            for m in known:
                print(f"FAIL  machine folder gone: {m} committed once, absent now")
            print()
            print(f"  {len(known)} machine folder(s) gone from working tree.")
            print("  If this was `retire_archive.py`, they are in testing-archive/")
            print("  and return when each computer runs `update`. If it was not,")
            print("  this repository has lost every machine it ever held.")
            return 1
        if not answered:
            # THE INNOCENT ANSWER IS NOT FREE. Reaching this line means there
            # is no data here at all; the only question left is whether there
            # ever was, and that question was not answered. Printing the
            # reassuring sentence anyway is the empty-repo hole with the
            # evidence removed rather than consulted, and a roster listing
            # computers whose folders are all absent is the shape a deletion
            # leaves behind.
            reg = root / "machines.json"
            listed = []
            try:
                listed = [m.get("folder") for m
                          in json.loads(reg.read_text(encoding="utf-8"))
                          .get("machines") or [] if m.get("folder")]
            except Exception:                                   # noqa: BLE001
                pass
            print("FAIL  every machine folder is absent and the history could "
                  "not be read")
            print()
            print("`git log` could not be answered in this directory — an export")
            print("without .git, a tarball, or a broken object store. Whether")
            print("this tree once held machine folders is therefore unknown, and")
            print("unknown must not print as the reassuring answer.")
            if listed:
                print()
                print(f"machines.json lists {len(listed)} computer(s) — "
                      f"{', '.join(listed)} — and not one of them is on disk.")
            print()
            print("Run this gate in the checkout the documents are published")
            print("from, where the last commit can be read.")
            return 1
        print("no machine folders — nothing to check (none was ever committed)")
        return 0
    sessions = []
    orphan_tokens = {}
    for _mdir, f in paths.iter_machine_files(root, "sessions.json"):
        d = json.loads(f.read_text(encoding="utf-8"))
        for s in d.get("sessions", []):
            # _mdir.name, not f.parent.name — after the human/machine-readable
            # split the parent is `machine-readable`, so the fallback used to
            # relabel every session on an unnamed scan as a machine called
            # "machine-readable". paths.iter_machine_files returns the folder
            # precisely so this guess is not needed.
            s["machine"] = d.get("machine", _mdir.name)
            sessions.append(s)
        # Orphans are read from the READERS block, not by filtering rows on
        # `source`: rows only carry that field from 2026-08-21 onward, and
        # every machine folder committed before then must still be checkable
        # from a checkout that has not rescanned it.
        orphan_tokens[d.get("machine", _mdir.name)] = sum(
            r.get("tokens", 0) for r in d.get("readers", [])
            if r.get("cli") == "claude-orphans")

    grand = sum(m["grand_total_tokens"] for m in machines)
    checks = []

    def chk(name, got, want, detail="", fatal=True):
        checks.append((name, got, want, got == want, detail, fatal))

    # AN ENTIRE FAMILY OF CHECKS HERE IS BLIND WITHOUT GIT, AND BLIND IS WHAT
    # PASSING LOOKS LIKE.
    #
    # Self-consistency cannot see relabelling, forgery, absence or a moved
    # boundary — that is stated further down, and every check written to close
    # it compares this tree against the last commit: the per-company split, the
    # closed-day audit, last_computed, retention, a folder that disappeared, a
    # document that was published once. Each one reads `git show` or `git log`
    # and, when git will not answer, skips silently. So in a directory that is
    # not a repository they do not fail — they never run, and a run in which
    # they never ran is indistinguishable in the banner from a run in which
    # they all passed.
    #
    # One line, always evaluated, that says whether the evidence those checks
    # rest on was available at all. It costs nothing in the checkout this gate
    # is meant to run in and is the only thing standing between an export
    # without .git and a clean bill of health.
    git_ok, _gd = _git(root, "rev-parse", "--git-dir")
    chk("the last commit can be read, so the drift checks are live",
        git_ok, True,
        "`git rev-parse` could not be answered here, so every check that "
        "compares this tree against its last commit — relabelling, closed "
        "days, backdating, retention, a folder or a document that vanished — "
        "surveyed nothing and reported nothing. Publish from the checkout, "
        "not from a copy of it")

    # --- Claude Code universe: three different partitions of one total --------
    acct = defaultdict(int)
    prov = defaultdict(int)
    for m in machines:
        for a in m["accounts"]:
            acct[a["account"]] += a["grand_total"]
            for model, v in a["by_model"].items():
                prov[provider_of(model)] += sum(v[k] for k in FIELDS)
    # THIS CHECK COMPARED A VALUE WITH ITSELF.
    #
    #     chk("machines partition the grand total",
    #         sum(m["grand_total_tokens"] for m in machines), grand)
    #
    # and four lines above, `grand = sum(m["grand_total_tokens"] for m in
    # machines)`. Character for character the same expression. It could not
    # fail, and it sat at the top of the partition block lending its name to the
    # one fleet-level property nobody was testing: on a planted five-machine
    # fleet with alpha's folder duplicated, the grand total read 2,234,500,000
    # against a planted 1,234,500,000 and this file reported 28 checks, 0 failed.
    #
    # ...AND THE REPLACEMENT WAS UNFAILABLE TOO, WHICH TOOK LONGER TO SEE.
    #
    #     per_computer.setdefault(m["machine"], m["grand_total_tokens"])
    #     chk("machines partition the grand total", sum(per_computer.values()), grand)
    #
    # setdefault keeps one entry per NAME, so that sum equals `grand` for every
    # fleet whose machine names are unique — and `no two folders claim the same
    # computer`, immediately below, is what guarantees they are unique. The two
    # checks were one check written twice: whenever the first could differ, the
    # second was already failing. On any healthy fleet it was decoration, which
    # is the same defect as the version it replaced wearing better clothes.
    #
    # A total is corroborated by a SECOND ARTIFACT or not at all. Every scan
    # writes by_account.csv beside totals.json — same pass, different writer —
    # so re-adding the fleet out of the CSVs reaches the same number by a route
    # that can disagree. A machine whose CSV is missing or unreadable is
    # reported as UNCORROBORATED and excluded from both sides, because folding
    # it in at zero would make a folder that lost its CSV look exactly like one
    # that agrees, and counting its JSON figure on both sides would make it
    # check itself.
    twice = {k: [x["folder"] for x in machines
                 if x["machine"] == k]
             for k in {m["machine"] for m in machines}
             if sum(1 for x in machines if x["machine"] == k) > 1}
    chk("no two folders claim the same computer", len(twice), 0,
        "; ".join(f"{k}: {', '.join(v)}" for k, v in sorted(twice.items())))

    csv_sum, csv_json, corroborated, uncorroborated = 0, 0, 0, []
    for m in machines:
        c = paths.find(root / m["folder"], "by_account.csv")
        if not c:
            uncorroborated.append(f"{m['folder']}: no by_account.csv")
            continue
        try:
            with c.open(newline="", encoding="utf-8") as fh:
                csv_sum += sum(int(r["total"]) for r in csv.DictReader(fh))
        except Exception:  # noqa: BLE001
            uncorroborated.append(f"{m['folder']}: by_account.csv unreadable")
            continue
        csv_json += m["grand_total_tokens"]
        corroborated += 1
    # A CORROBORATION WITH NOTHING TO CORROBORATE IS NOT A PASS.
    #
    # Both sides of the comparison below are built by the same loop, and a
    # machine with no readable CSV is excluded from both — deliberately, so a
    # folder that lost its CSV cannot look like one that agrees. Take every CSV
    # away and that exclusion empties the loop: 0 == 0, PASS, under the one
    # fatal check in this file whose name promises the fleet total was re-added
    # from a second artifact. ABSENT LOOKS EXACTLY LIKE ZERO, inside the check
    # written to reach outside the data.
    #
    # Demanding a CSV from every folder is the wrong repair — a folder that
    # predates the CSV, or was assembled by hand, is sparse and not wrong, and
    # that is why the listing below is advisory. What must not happen is the
    # check reporting agreement having compared nothing at all.
    chk("at least one machine's total was re-added from a second artifact",
        min(corroborated, 1), 1,
        f"none of the {len(machines)} machine folder(s) has a readable "
        "by_account.csv, so the check below summed nothing on both sides and "
        "the fleet total stands on totals.json alone" if not corroborated
        else "")
    chk("the fleet total re-adds from a second artifact", csv_sum, csv_json,
        "by_account.csv and totals.json come from one scan through two writers; "
        "they disagree, so at least one of them is not what was counted")
    # Advisory, for the same reason `every artifact carries a scanner_version`
    # is: a folder with no CSV is not a wrong number, it is a number with
    # nothing standing behind it. Failing the run would block every rebuild on
    # a folder that predates the CSV or was assembled by hand, and a check that
    # fails whenever the tree is legitimately sparse is one people learn to
    # pass with --force. It stays counted and named, which is the whole point:
    # UNCORROBORATED must not read the same as CORROBORATED.
    chk("every machine's total has a second artifact to check it against",
        len(uncorroborated), 0,
        "; ".join(uncorroborated) + " — these folders contribute to the grand "
        "total with nothing to corroborate them" if uncorroborated else "",
        fatal=False)
    chk("accounts partition the grand total", sum(acct.values()), grand)
    chk("companies partition the grand total", sum(prov.values()), grand)

    # --- internal coherence of each account record ---------------------------
    bad_model, bad_field, bad_mach = [], [], []
    for m in machines:
        per_machine = 0
        for a in m["accounts"]:
            if sum(sum(v[k] for k in FIELDS) for v in a["by_model"].values()) != a["grand_total"]:
                bad_model.append(f"{m['machine']}/{a['account']}")
            if sum(a["totals"][k] for k in FIELDS) != a["grand_total"]:
                bad_field.append(f"{m['machine']}/{a['account']}")
            per_machine += a["grand_total"]
        if per_machine != m["grand_total_tokens"]:
            bad_mach.append(m["machine"])
    chk("each account's models sum to its total", len(bad_model), 0, ", ".join(bad_model))
    chk("each account's 4 buckets sum to its total", len(bad_field), 0, ", ".join(bad_field))
    chk("each machine's accounts sum to its total", len(bad_mach), 0, ", ".join(bad_mach))

    # --- every-CLI universe --------------------------------------------------
    if sessions:
        cli_grand = sum(s.get("total", 0) for s in sessions)
        by_cli, by_prov = defaultdict(int), defaultdict(int)
        for s in sessions:
            by_cli[s.get("cli")] += s.get("total", 0)
            by_prov[s.get("provider")] += s.get("total", 0)
        chk("CLIs partition the every-CLI total", sum(by_cli.values()), cli_grand)
        chk("companies partition the every-CLI total", sum(by_prov.values()), cli_grand)
        chk("each session's 4 buckets sum to its total",
            sum(1 for s in sessions
                if sum(s["tokens"][k] for k in FIELDS) != s["total"]), 0)
        chk("each session's sent+received equals its total",
            sum(1 for s in sessions
                if "sent" in s and "received" in s
                and s["sent"] + s["received"] != s["total"]), 0)

        # THE ASSUMPTION EVERY FLEET TOTAL RESTS ON, FINALLY STATED.
        #
        # combine.py: "Sessions on different computers are disjoint, so these
        # add without any risk of double-counting." Nothing tested it. A session
        # id is minted once per conversation, so the same id on two computers is
        # not two conversations — it is one, reached through a synced home
        # directory, a restored backup, or a machine folder copied to seed
        # another. Both copies are then added, on both derivations at once:
        # combine.py through the per-machine totals and corpus_reports.py
        # through `everything += ses`, which has no cross-machine dedup either.
        #
        # Reported, not deduplicated. Two computers holding one conversation is
        # a fact about the fleet — which computer really did the work is not
        # recoverable from the transcripts, and silently halving a published
        # figure to whichever machine sorted first would be a guess wearing the
        # same clothes as a fix. This says how many, which, and how much.
        where = defaultdict(set)
        for s in sessions:
            sid = s.get("session_id")
            if sid:
                where[sid].add(s.get("machine"))
        shared = sorted(k for k, v in where.items() if len(v) > 1)
        dbl = sum(s.get("total", 0) for s in sessions
                  if s.get("session_id") in set(shared))
        chk("no session id appears on two computers", len(shared), 0,
            f"{len(shared)} shared id(s), {dbl:,} tokens counted on more than "
            f"one machine, e.g. {shared[0]} on "
            f"{', '.join(sorted(where[shared[0]]))}" if shared else "")

        # The cross-check that matters most: two independent scanners, reading
        # the same transcripts by different units, must agree per machine.
        #
        # They photograph the machine at different instants, though — the two
        # scanners run one after the other, and on the computer you are actually
        # working on, a live session writes more tokens in between. That is a
        # real difference and not a bug, so the tolerance is bounded by exactly
        # the thing that can cause it: sessions still being written after the
        # first scan finished. Anything beyond that is a scanner that drifted.
        # A blanket percentage would have been easier and would have hidden the
        # class of bug this check exists to catch.
        scanned = {s["machine"] for s in sessions}
        for m in machines:
            if m["machine"] not in scanned:
                continue
            mine = [s for s in sessions if s["machine"] == m["machine"]]
            per_sess = sum(s.get("total", 0) for s in mine if s.get("cli") == "claude")
            # SUBTRACT THE ORPHANS BEFORE COMPARING. analyze_tokens reads
            # transcripts; the claude-orphans reader recovers sessions whose
            # transcripts are DELETED, out of .claude.json, and writes them
            # into sessions[] tagged cli="claude". One scanner therefore
            # cannot see what the other counted, by construction, and the
            # difference is not drift — it is the orphans, exactly. Measured
            # on dell-latitude-7480-linux: 16,580 rows minus 16,532 = 48
            # orphan sessions worth 2,324,208,273, reported for weeks as
            # "one scanner has drifted".
            per_sess -= orphan_tokens.get(m["machine"], 0)
            delta = abs(per_sess - m["grand_total_tokens"])
            cutoff = m.get("generated_at") or ""
            live = sum(s.get("total", 0) for s in mine
                       if s.get("cli") == "claude" and (s.get("end") or "") >= cutoff)
            # ONE CHECK, ALWAYS EVALUATED, COMPARING A QUANTITY THAT CAN BE
            # NON-ZERO. This was three branches and two of them could not fail:
            #
            #     if delta == 0:  chk(name, 0, 0)         a literal against itself
            #     if live and delta <= live:
            #         checks.append((name, 0, 0, True, "", True))
            #
            # The second bypassed chk() altogether to hardcode the passed flag,
            # so it reported PASS whatever the numbers said. Both counted toward
            # the "N checks, 0 failed" banner — the line this repository has
            # learned not to trust, having printed 38 checks, 0 failed over a
            # 26.7 billion token undercount.
            #
            # The two vacuous branches were also the COMMON ones: agreement and
            # explained-by-a-live-session are the everyday outcomes, so on a
            # healthy fleet this check was unfailable on every machine, every
            # run, and only became a real assertion in the one case it was least
            # likely to be exercised.
            #
            # What the check MEANS is that two independent scanners agree up to
            # what sessions still being written can explain. So that is the
            # number it compares: the part of delta that live does NOT account
            # for, against zero. Zero when they agree exactly, zero when live
            # covers the gap, and the unexplained tokens when a scanner drifted.
            chk(f"analyze_tokens == sessions on {m['machine']}"
                + (f"  (±{delta:,}, live session)" if delta and delta <= live else ""),
                max(0, delta - live), 0,
                f"differs by {delta:,}; only {live:,} is attributable to "
                "sessions still being written — one scanner has drifted")

    # Version skew. Every check above is internal to one machine and passes
    # regardless of which scanner produced it, so two folders can disagree about
    # what a token is while the arithmetic is flawless on both. This is the only
    # check that compares machines against each other.
    versions = {}
    for _mdir, f in paths.iter_machine_files(root, "sessions.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        versions[d.get("machine", f.parent.name)] = d.get("scanner_version")
    if versions:
        seen = {v for v in versions.values() if v}
        stale = [m for m, v in versions.items() if not v]
        # Advisory, not fatal. The numbers are each correct for the code that
        # produced them; they simply were not all produced by the same code.
        # Failing the run would block every rebuild until the whole fleet is
        # rescanned, which turns a useful warning into something to switch off.
        chk("every machine scanned by the same version",
            len(seen) + (1 if stale else 0), 1,
            "; ".join(f"{m}={v or 'pre-versioning'}" for m, v in sorted(versions.items())),
            fatal=False)

    # ...and every ARTIFACT stamped, not just the two anyone thought to check.
    #
    # The version reached totals.json and sessions.json and stopped there.
    # hardware.json, lifetime.json and stats.json — 3 of the 5 machine-readable
    # files, on every machine — carried numbers that could not be traced to the
    # code that produced them. stats.json is where `by_cli` lives, so the
    # per-CLI figures were exactly the ones with no provenance.
    #
    # That reopens the hole the field was created to close. It was added three
    # minutes after a scan silently lost 4,691,850,175 tokens, so that a number
    # could be tied to a scanner; leaving most files unstamped meant the check
    # below could not see them at all, and "not checked" reads as "fine".
    #
    # Advisory for the same reason as above: an old artifact is not wrong, it is
    # differently produced, and failing would block every rebuild until the
    # whole fleet is rescanned.
    STAMPED = ("totals.json", "sessions.json", "hardware.json",
               "lifetime.json", "stats.json")
    unstamped = []
    for mdir in sorted(p for p in root.iterdir() if p.is_dir()):
        md = mdir / "machine-readable"
        if not md.is_dir():
            continue
        for name in STAMPED:
            f = paths.find(mdir, name)
            if not f:
                continue
            try:
                if not json.loads(f.read_text(encoding="utf-8")).get("scanner_version"):
                    unstamped.append(f"{mdir.name}/{name}")
            except Exception:  # noqa: BLE001 - unreadable is a different check
                pass
    chk("every artifact carries a scanner_version",
        len(unstamped), 0,
        (", ".join(unstamped[:6]) + (" ..." if len(unstamped) > 6 else ""))
        if unstamped else "",
        fatal=False)

    # A SCAN THAT COULD NOT READ PART OF THE MACHINE IS NOT A SCAN OF THE
    # MACHINE, AND EVERY PARTITION STILL SUMS.
    #
    # This is the signature failure of this repository, arriving at the one
    # place that is supposed to catch it. Every check above asks whether a
    # slice adds up to its whole; a directory nobody can enter is missing from
    # the slice AND from the whole at the same instant, so all of them pass.
    # Measured: two trees identical but for one project directory at `chmod
    # 000` against the same directory left readable and EMPTY produced thirty
    # check lines each, byte for byte identical, on a scan short by 1,251,500
    # tokens.
    #
    # sessions.py now publishes `unreadable_paths` — the union of what every
    # reader could not enter, NAMED rather than counted, because a count of
    # unreadable directories reads 0 for a scan that hit none and 0 for a
    # scanner too old to look. That third state is what this check reads.
    #
    #   null    the field is not there: an older scan, which cannot be
    #           certified either way and is reported as such, not as clean
    #   []      the scan looked and everything opened
    #   [...]   the scan is partial, and these are the directories to go and
    #           unlock before any number here is published
    #
    # FATAL, unlike the two advisory checks above, and deliberately: an
    # unstamped artifact is a number produced by different code, while this is
    # a number produced from less than the machine.
    partial, unaudited = [], []
    for m in machines:
        f = paths.find(root / m["folder"], "sessions.json")
        if not f:
            continue
        try:
            blind = json.loads(f.read_text(encoding="utf-8")).get(
                "unreadable_paths", None)
        except Exception:  # noqa: BLE001 - unreadable is a different check
            continue
        if blind is None:
            unaudited.append(m["folder"])
        elif blind:
            partial.append(f"{m['folder']}: " + ", ".join(blind[:3])
                           + (f" (+{len(blind) - 3} more)" if len(blind) > 3
                              else ""))
    chk("no machine's scan reported a directory it could not read",
        len(partial), 0, "; ".join(partial))
    chk("every machine's scan says whether it could read everything",
        len(unaudited), 0,
        (", ".join(unaudited) + " — scanned before sessions.py recorded "
         "unreadable_paths, so 'nothing was skipped' has not been established "
         "for them; it has only not been contradicted")
        if unaudited else "", fatal=False)

    # ---- three checks that close what self-consistency cannot see -----------
    #
    # Every check above asks "does this data agree with itself?". An adversarial
    # run proved that is not enough: five corruptions that preserve every sum
    # went through 22 checks without moving a single counter.
    #
    #   relabel a model          per-company split rewritten, all totals intact
    #   forge a scanner_version  a stale machine claims the current version
    #   delete a whole machine   nothing left to disagree with
    #   empty sessions.json      the >= comparison passes on zero
    #   backdate last_computed   INFLATES the floor, sums untouched
    #
    # Self-consistency cannot see relabelling, forgery, absence or a moved
    # boundary, because all four are internally consistent. These three ask a
    # different question: does the data match something OUTSIDE itself?

    # 1. THE ROSTER. machines.json already lists the fleet — combine.py uses it
    #    so an unscanned computer is reported rather than silently absent. It was
    #    never enforced here, so a folder that DISAPPEARS reads as "not present
    #    yet", identical to one that never existed.
    try:
        reg = json.loads((root / "machines.json").read_text(encoding="utf-8"))
        expected = {m.get("folder") for m in (reg.get("machines") or []) if m.get("folder")}
    except Exception:  # noqa: BLE001
        expected = set()
    if expected:
        present = {p.name for p in root.iterdir()
                   if p.is_dir() and paths.find(p, "totals.json")}
        vanished = sorted(expected - present)
        # Registered-but-never-scanned is normal and already reported elsewhere.
        # What matters here is a machine that HAD a folder and no longer does,
        # which git can tell us and the filesystem cannot.
        # A RETIRE IS NOT A DISAPPEARANCE, AND THIS COULD NOT TELL THEM APART.
        #
        # retire_archive.py deliberately moves machines scanned by a superseded
        # scanner out of the fleet, and they come back when that computer runs
        # `update` again. This check saw four of them vanish and failed the
        # whole run — correctly by its own rule, and uselessly, because the
        # disappearance was the operation working.
        #
        # A check that fails every time you clean the repository is one people
        # learn to pass with --force, which costs the real warning its meaning.
        # The same discrimination `scanner_version` gives between a recount and
        # a deletion is available here: a retire leaves the machine in
        # testing-archive/<stamp>/stale-machines/, and a loss does not.
        # THE EXEMPTION MUST NOT BE FORGEABLE BY MKDIR.
        #
        # An empty directory named after a machine would otherwise turn a real
        # deletion into "retired, not lost" — the exemption becoming the hole.
        # So a retire counts only if the archived copy still HOLDS the machine's
        # totals: that is what retire_archive.py actually moves, and it is not
        # something a deletion leaves behind.
        # AND THE EXEMPTION HAS TO EXPIRE, which it did not.
        #
        # It asked "was this machine ever retired?" — a question whose answer
        # never becomes false again. hp-laptop-linux was retired on
        # 2026-08-08T19:06:33, came back hours later when this computer
        # re-scanned and committed at 2026-08-09T01:52:15, and the stamp stayed
        # in testing-archive/. Every machine in this fleet has been retired at
        # least once, so the fatal branch was unreachable for all of them, and
        # deleting the entire fleet passed the audit that exists to notice
        # deletion. Isolated in test_gate.py:
        #
        #   PASS  no retire                        -> gate reports LOST
        #   PASS  retire 2099 (newer than commit)  -> exempt
        #   FAIL  retire 2020 (older than commit)  -> gate reports LOST
        #         got False, want True
        #
        # The 2099 case is the control, and it is why the fix is a comparison
        # rather than dropping the exemption: a check that fails every time the
        # repository is tidied is one people learn to pass with --force, which
        # costs the real warning its meaning.
        #
        # Same shape as the empty-repo hole at the top of this file, reached
        # from the other side: there nothing was left to check, here everything
        # was exempt from the check.
        retired = {}
        ta = root / "testing-archive"
        if ta.is_dir():
            for stamp in sorted(ta.iterdir()):
                sm = stamp / "stale-machines"
                if not sm.is_dir():
                    continue
                try:
                    when = _dt.datetime.strptime(stamp.name, "%Y-%m-%dT%H-%M-%S")
                except ValueError:
                    when = None            # unparseable: cannot be shown fresh
                for p in sm.iterdir():
                    if p.is_dir() and paths.find(p, "totals.json"):
                        prev = retired.get(p.name, "none")
                        if prev == "none" or (when and (prev is None or when > prev)):
                            retired[p.name] = when

        gone_from_git, was_retired, unreadable, last_sha = [], [], [], {}
        for m in vanished:
            answered, log = _git(root, "log", "-1", "--format=%h %cI", "--",
                                 f"{m}/machine-readable/totals.json")
            if not answered:
                # NOT "NEVER COMMITTED, SO NEVER SCANNED". That comment was on
                # a branch reached by two different facts: git answering "no
                # commits touched this path", and git not answering at all.
                # The first is a machine on the roster nobody has scanned yet,
                # which is normal. The second is this gate having no idea, and
                # it applies to every folder at once the moment the tree is not
                # a repository — so the check surveyed the whole vanished list
                # and reported on none of it.
                unreadable.append(m)
                continue
            if not log.strip():
                continue                   # never committed, so never scanned
            parts = log.split()
            last_sha[m] = parts[0]
            try:
                committed = _dt.datetime.fromisoformat(parts[1]).replace(tzinfo=None)
            except (IndexError, ValueError):
                committed = None
            when = retired.get(m)
            # Exempt only when a retire exists AND postdates that machine's last
            # commit. An unparseable stamp or an unreadable commit date falls
            # through to LOST: this check exists to notice loss, so anything it
            # cannot establish must be reported rather than waved past.
            fresh = (m in retired and when is not None and committed is not None
                     and when > committed)
            (was_retired if fresh else gone_from_git).append(m)
        chk("no machine folder has disappeared",
            len(gone_from_git), 0,
            ", ".join(gone_from_git) + " — committed once, absent now" if gone_from_git else "",
            fatal=True)
        # The premise the check above rests on, asserted rather than assumed.
        # A folder is on the roster and not on disk; whether that is a loss is
        # decided entirely by what git says about it, and a folder git would
        # not talk about was dropped from the survey without a word.
        chk("every vanished folder's history could be read",
            len(unreadable), 0,
            ", ".join(unreadable) + " — on the roster, absent from disk, and "
            "`git log` could not be asked whether they were ever committed. "
            "The check above surveyed the rest and says nothing about these"
            if unreadable else "",
            fatal=True)
        if was_retired:
            # AN ASSERTION MUST RE-DERIVE ITS PREMISE, NOT RESTATE IT.
            #
            # This read, verbatim, chk("machines absent by RETIRE, not by
            # loss", 0, 0) — a literal against itself, inside an `if` that had
            # already decided the answer. It could not fail; worse, it was the
            # single line on the strength of which adversarial_meta's earlier,
            # name-based coverage scan scored this file as exercising the
            # ABSENT case. Coverage claimed by an assertion that cannot fail is
            # worse than no claim at all.
            #
            # The name makes a real claim: these machines are safe in
            # testing-archive and come back when that computer runs `update`.
            # So check it, against the one thing the exemption cannot write for
            # itself — what git last committed for that machine. An archived
            # copy holding LESS than the last commit did is not a retire; it is
            # a loss with a directory standing in front of it, and `mkdir` plus
            # a stub totals.json is all it takes to arrange one.
            hollow = []
            for m in was_retired:
                # HEAD no longer holds a retired machine — the commit that
                # retired it is the one that removed it — so HEAD, then that
                # commit, then its parent. Asking only HEAD returns nothing for
                # every real retire, and "nothing" would then exempt the
                # forgery this check exists to catch.
                p = f"{m}/{paths.MACHINE}/totals.json"
                committed = None
                for ref in (f"HEAD:{p}",) + ((f"{last_sha[m]}:{p}",
                                              f"{last_sha[m]}^:{p}")
                                             if m in last_sha else ()):
                    r = subprocess.run(["git", "show", ref], cwd=root,
                                       capture_output=True, text=True)
                    if r.returncode:
                        continue
                    try:
                        committed = json.loads(r.stdout)["grand_total_tokens"]
                        break
                    except Exception:  # noqa: BLE001
                        pass
                kept = None
                for stamp in (sorted(ta.iterdir()) if ta.is_dir() else []):
                    p = stamp / "stale-machines" / m
                    tf = paths.find(p, "totals.json") if p.is_dir() else None
                    if not tf:
                        continue
                    try:
                        v = json.loads(tf.read_text(encoding="utf-8"))["grand_total_tokens"]
                    except Exception:  # noqa: BLE001
                        continue
                    kept = v if kept is None else max(kept, v)
                if kept is None or (committed is not None and kept < committed):
                    hollow.append(
                        f"{m}: archive holds "
                        + ("no readable total" if kept is None else f"{kept:,}")
                        + (f", git committed {committed:,}" if committed is not None
                           else ""))
            chk("machines absent by RETIRE, not by loss",
                len(hollow), 0,
                "; ".join(hollow) + " — the exemption says the machine is safe "
                "in testing-archive; this is what is actually in there"
                if hollow else
                f"{', '.join(was_retired)} — in testing-archive, "
                "returning when each computer runs `update`",
                fatal=False)

    # 1b. THE PER-COMPANY SPLIT MUST NOT SILENTLY MOVE. Relabelling a model —
    #     every claude-opus-4-8 token booked as claude-opus-5 — leaves every
    #     partition summing perfectly while rewriting the one figure this repo is
    #     most careful about: which company served the tokens. Compared against
    #     the last commit, because there is nothing inside the file to check it
    #     against.
    #
    #     AND `if r.returncode: continue` EXEMPTED EVERY UNTRACKED FOLDER FROM
    #     IT. hp-laptop-linux/machine-readable/totals.json left the index in
    #     fe6a7f6 and the file is still on disk, so `git show HEAD:...` exits
    #     128 for it and this loop skipped straight past — as did the two other
    #     sites below. Measured on a clone with that folder restored exactly as
    #     the working tree holds it: 4,800,775,316 claude tokens relabelled
    #     deepseek-v4-pro AND last_computed dragged 2026-05-17 -> 2020-01-01,
    #     and the run printed 56 checks / 12 failed both before and after —
    #     PASS on this line and PASS on last_computed, character for character.
    #     So the git call goes through _git(), which separates answered-with-
    #     nothing from unable-to-answer, and a folder it could not read is
    #     named on the banner instead of quietly leaving the population.
    moved, head_blind, vs_head = [], [], 0
    for mdir in sorted(p for p in root.iterdir() if p.is_dir()):
        f = paths.find(mdir, "totals.json")
        if not f:
            continue
        answered, head = _git(root, "show",
                              f"HEAD:{mdir.name}/machine-readable/totals.json")
        if not answered or not head.strip():
            head_blind.append(f"{mdir.name}/totals.json")
            continue
        vs_head += 1

        def split(doc):
            o = defaultdict(int)
            for a in doc.get("accounts", []):
                for model, v in (a.get("by_model") or {}).items():
                    if isinstance(v, dict):
                        o[provider_of(model)] += sum(v.get(k, 0) or 0 for k in FIELDS)
            return o

        try:
            was, now_ = split(json.loads(head)), split(json.loads(f.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001
            continue
        # The signature of relabelling is CONSERVATION WITH REDISTRIBUTION: one
        # company falls, another rises by close to the same amount, and the
        # machine total barely moves. Real usage does not do that — new work
        # raises a company without lowering another, and retention lowers one
        # without raising any.
        #
        # An earlier version of this check only fired when a company reached
        # ZERO, which meant relabelling a single model — leaving other models of
        # that company in place — went straight through. Measured: the attack
        # survived until this was widened.
        losers = {c: was[c] - now_.get(c, 0) for c in was if was[c] - now_.get(c, 0) > 0}
        gainers = {c: now_[c] - was.get(c, 0) for c in now_ if now_[c] - was.get(c, 0) > 0}
        for lc, amt in losers.items():
            if amt < 1_000_000:          # noise, or a small retention loss
                continue
            for gc, gain in gainers.items():
                # Within 1%: a transfer, not two independent movements.
                if abs(gain - amt) <= max(amt, gain) * 0.01:
                    moved.append(f"{mdir.name}: {lc} -{amt:,} while {gc} +{gain:,}")
    # THE POPULATION GOES IN THE NAME, not in the detail: the banner prints
    # detail only for a check that did NOT pass, so this line read identically
    # over nought folders and over the whole fleet. Today it is 1 — one of the
    # two machine folders on disk — and that is now on the banner.
    chk(f"no company's tokens moved into another ({vs_head} folder(s) vs HEAD)",
        len(moved), 0, "; ".join(moved[:3]), fatal=True)

    # 1c. A MACHINE'S SESSIONS MUST NOT EMPTY. The analyze_tokens == sessions
    #     check uses >=, so zero sessions against a full totals.json passes: a
    #     file that says nothing agrees with everything.
    emptied = []
    for mdir in sorted(p for p in root.iterdir() if p.is_dir()):
        f = paths.find(mdir, "sessions.json")
        t = paths.find(mdir, "totals.json")
        if not (f and t):
            continue
        try:
            n = len(json.loads(f.read_text(encoding="utf-8")).get("sessions") or [])
            g = json.loads(t.read_text(encoding="utf-8")).get("grand_total_tokens", 0)
        except Exception:  # noqa: BLE001
            continue
        if g > 0 and n == 0:
            emptied.append(f"{mdir.name}: {g:,} tokens, 0 sessions")
    chk("no machine reports tokens with zero sessions",
        len(emptied), 0, "; ".join(emptied[:3]), fatal=True)

    # 2. last_computed MOVES FORWARD ONLY. The floor is counter + days strictly
    #    after it, so backdating makes more days count and the figure grows. It
    #    is the only corruption found that INFLATES, which is why this one is
    # WE READ MORE THAN ANTHROPIC DOES, SO WE CAN NEVER REPORT LESS.
    #
    # The floor is `max(counter + days_after_last_computed, seen)` per ACCOUNT,
    # and the counter is Claude's own stats-cache figure — not derived from
    # transcripts, untouchable by any change to how transcripts are read. On top
    # of it this system adds every profile, the hard-link archive, and seven
    # other CLIs. A floor below the sum of those counters is therefore not a
    # small error; it is a contradiction.
    #
    # It is reachable by one silent path. `by_acct.get(name)` in
    # stats_page.machine_floor matches the counter to a profile BY ACCOUNT
    # LABEL, and a miss falls through to `part = seen` — the transcripts alone —
    # with no message. Demonstrated on this machine by changing nothing but the
    # label's case:
    #
    #     counters Anthropic reports          23,731,403,680
    #     floor with the counters matched      30,077,288,067
    #     floor when the label does not match   8,539,968,218   (3.5x collapse)
    #     below Anthropic's own number?        True
    #
    # Nothing in the system noticed. That is the failure this check exists for:
    # not a wrong total, a DROPPED SOURCE that leaves a smaller number looking
    # exactly like a correct one.
    below = []
    for _mdir, _tf in paths.iter_machine_files(root, "totals.json"):
        sf = paths.find(_mdir, "sessions.json")
        if not sf:
            continue
        try:
            _t = json.loads(_tf.read_text(encoding="utf-8"))
            _s = json.loads(sf.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        counters = sum(int(e.get("total") or 0) for e in (_s.get("stats_cache") or []))
        if not counters:
            continue
        # COMPARE THE FLOOR, NOT THE MEASURED TOTAL.
        #
        # The first version of this check compared the counters against
        # grand_total_tokens and warned on all three healthy machines. Of course
        # it did: the measured figure is the transcripts that still EXIST, the
        # counter covers everything up to its own date including what has since
        # been deleted, and the whole purpose of the floor is to add them. A
        # check that fires on correct data is the false alarm this file has
        # already had to remove twice.
        #
        # The floor is the thing that must never be smaller, because it is built
        # from the counter.
        try:
            import stats_page as _sp
            _sess = [x for x in (_s.get("sessions") or [])]
            _fl, _cl, _oth, _rows = _sp.machine_floor(_t, _sess, _s.get("stats_cache") or [])
        except Exception:  # noqa: BLE001
            continue
        if _fl < counters:
            dropped = [r[0] for r in _rows if r[1] is None]
            below.append(f"{_t.get('machine', _mdir.name)}: floor {_fl:,} < "
                         f"counters {counters:,}"
                         + (f" (no counter matched: {', '.join(str(d)[:24] for d in dropped[:3])})"
                            if dropped else ""))
    chk("no machine reports less than Anthropic's own counter",
        len(below), 0,
        "; ".join(below) + " — a counter was dropped, almost certainly an "
        "account label that did not match a profile in stats_page.machine_floor"
        if below else "",
        fatal=False)

    backdated, sc_vs_head = [], 0
    for mdir in sorted(p for p in root.iterdir() if p.is_dir()):
        f = paths.find(mdir, "sessions.json")
        if not f:
            continue
        try:
            now_sc = {e.get("account"): e.get("last_computed")
                      for e in (json.loads(f.read_text(encoding="utf-8")).get("stats_cache") or [])}
        except Exception:  # noqa: BLE001
            continue
        answered, head = _git(root, "show",
                              f"HEAD:{mdir.name}/machine-readable/sessions.json")
        if not answered or not head.strip():
            head_blind.append(f"{mdir.name}/sessions.json")
            continue
        sc_vs_head += 1
        try:
            was = {e.get("account"): e.get("last_computed")
                   for e in (json.loads(head).get("stats_cache") or [])}
        except Exception:  # noqa: BLE001
            continue
        for acct, before in was.items():
            after = now_sc.get(acct)
            if before and after and str(after) < str(before):
                backdated.append(f"{mdir.name}/{str(acct)[:20]} {before}->{after}")
    chk(f"last_computed never moves backwards ({sc_vs_head} folder(s) vs HEAD)",
        len(backdated), 0, "; ".join(backdated[:4]), fatal=True)

    # 3. THE VERSION MUST MATCH THE CODE THAT IS RUNNING. The check above only
    #    compares machines to each other, so two machines that agree on a forged
    #    value agree perfectly. sessions.scanner_version() recomputes the hash
    #    from source, which a stamped file cannot forge without matching it.
    try:
        import sessions as _s
        live = _s.scanner_version()
        # Only THIS machine's folder can be compared: another computer's scan was
        # produced by the code IT was running, which is the point of the field.
        host_folder = None
        for mdir in sorted(p for p in root.iterdir() if p.is_dir()):
            hw = paths.find(mdir, "hardware.json")
            if hw:
                try:
                    if json.loads(hw.read_text(encoding="utf-8")).get("hostname") == platform.node():
                        host_folder = mdir
                        break
                except Exception:  # noqa: BLE001
                    pass
        if host_folder:
            tf = paths.find(host_folder, "totals.json")
            t = json.loads(tf.read_text(encoding="utf-8")) if tf else {}
            chk("this machine's scan matches the code present",
                t.get("scanner_version") or "MISSING", live,
                f"{host_folder.name}: rescan to refresh", fatal=False)
    except Exception:  # noqa: BLE001 - never block the run on this
        pass

    # 4. AND EVERY OTHER MACHINE'S STAMP MUST BE REPRODUCIBLE FROM THE COMMIT
    #    IT CLAIMS.
    #
    # Check 3 above can only ever adjudicate ONE folder — the one whose
    # hardware.json hostname matches platform.node() — because it recomputes the
    # hash from the source sitting in THIS checkout. Every other machine in the
    # fleet is left to `every machine scanned by the same version`, which
    # compares the labels to each other and to nothing else. So the
    # red team's attack is two machines stamping the same made-up value: they
    # agree with each other perfectly, `every machine scanned by the same
    # version` passes, and no check in the file has any independent thing to
    # compare them against. Measured against this tree AND against HEAD: the
    # forged pair passed the whole gate. It is structural, not a regression.
    #
    # THE AUTHOR'S RULING: every machine should display its commit, and a hash
    # matching that commit, and the hashing should be cryptographic so we are
    # certain. `scan_identity.verify` recomputes the stamp from the blobs git
    # holds at the commit the scan names — `git show <commit>:sessions.py` —
    # which is the one input the machine writing the stamp does not get to
    # choose.
    #
    # THE COUNTS ARE THE CONTROL. "None of them is forged" is worth nothing
    # from a gate that looked at none of them: delete the recorder, or delete
    # scan_identity.py, and a check that only counts forgeries reports a clean
    # sheet over an empty list. So the population is pinned by its own checks —
    # the verifier is present, every folder was adjudicated, and every stamp
    # reached a real comparison — and only then does "none forged" mean
    # anything. All three are named on the banner, so a reader can see the
    # population as well as the verdict.
    try:
        import scan_identity as _si
    except Exception:                                            # noqa: BLE001
        _si = None
    chk("the scan-identity verifier is present", _si is not None, True,
        "scan_identity.py could not be imported here, so no stamp in this tree "
        "was compared to any commit — the forgery checks below surveyed nothing")
    ident, ident_err = {}, []
    for _mdir, _f in paths.iter_machine_files(root, "totals.json"):
        if _si is None:
            break
        try:
            _v = _si.verify(root, json.loads(_f.read_text(encoding="utf-8")),
                            folder=_mdir.name)
            if _v.status not in _si.STATUSES:
                raise ValueError(f"unknown verdict {_v.status!r}")
        except Exception as _e:                                  # noqa: BLE001
            # NOT `continue` on its own. A folder the verifier could not
            # adjudicate leaves the population, and the checks below would then
            # report agreement over the folders that happened to survive —
            # adv_documents.py died at KeyError 'inputs' this morning and 11
            # later checks never ran, under a banner that counted the ones
            # before it. The count check is what makes that visible.
            ident_err.append(f"{_mdir.name}: {type(_e).__name__}: {_e}")
            continue
        ident[_mdir.name] = _v
    chk("every machine folder was adjudicated for scan identity",
        len(ident), len(machines),
        "; ".join(ident_err[:4]) or "the verifier reached fewer folders than "
        "this gate found, so the stamp checks below cover only part of the fleet")
    _by = {s: [] for s in (_si.STATUSES if _si else ())}
    for _name in sorted(ident):
        _by[ident[_name].status].append(ident[_name])
    _unchecked = [v for s in (_si.NO_COMMIT, _si.NO_STAMP, _si.GIT_BLIND)
                  for v in _by[s]] if _si else []
    # THE RATCHET. Fatal once ANY machine in the tree has a commit to check —
    # the fleet has adopted the field, so a folder without one is an outlier,
    # and the cheapest attack on this whole section (drop `scan_commit` and be
    # unverifiable instead of caught) fails. Advisory while none has one, which
    # is the state of this tree today: `record()` exists here, nothing writes it
    # into totals.json yet, and turning five folders red for a wiring gap they
    # cannot fix themselves is how a check becomes something people pass with
    # --force.
    chk("every machine's stamp was checked against the commit it claims",
        len(_unchecked), 0,
        "; ".join(v.detail for v in _unchecked[:4])
        + (f" (+{len(_unchecked) - 4} more)" if len(_unchecked) > 4 else ""),
        fatal=bool([v for s in _si.ADJUDICATED for v in _by[s]]) if _si else False)
    chk("every machine's stamp is reproducible from the commit it claims",
        len(_by[_si.FORGED]) if _si else 0, 0,
        "; ".join(v.detail for v in _by[_si.FORGED][:4]) if _si else "")
    chk("every scan commit named by a machine exists in this repository",
        len(_by[_si.UNKNOWN_COMMIT]) if _si else 0, 0,
        "; ".join(v.detail for v in _by[_si.UNKNOWN_COMMIT][:4]) if _si else "")
    # Advisory: a scan over uncommitted edits is honestly unverifiable rather
    # than dishonest, and failing it would reject a real scan — which costs a
    # visit to the machine that produced it. Never counted as verified, always
    # named, because a fleet that is entirely DIRTY has certified nothing.
    chk("no machine's stamp rests on a tree that was dirty when it scanned",
        len(_by[_si.DIRTY]) if _si else 0, 0,
        "; ".join(v.detail for v in _by[_si.DIRTY][:4]) if _si else "",
        fatal=False)

    # Did a rescan LOSE tokens? Claude Code prunes transcripts older than
    # cleanupPeriodDays (default 30), so the source data expires. Measured on
    # this repo: the M1 went 32,659,024,382 -> 28,004,982,986 between two scans
    # 54 minutes apart - same config dirs, same projects, but 27 transcript
    # files deleted from disk. Those 4.69 billion tokens are gone permanently.
    #
    # The sessions did not expire during those 54 minutes; they had been past 30
    # days for over a week. Cleanup runs on startup and sweeps everything
    # already expired in one pass, so loss is bursty: a machine holds expired
    # transcripts until the next launch, then drops all of them at once. Which
    # is exactly why this compares against the last commit rather than trying to
    # predict when the next sweep will happen.
    #
    # A total that drops is therefore normal and irreversible, not a bug - but
    # it must never pass silently, because "this machine got smaller" reads
    # exactly like "this machine was idle".
    # subprocess is imported at module level
    for _mdir, f in paths.iter_machine_files(root, "totals.json"):
        # Same skip, same hole: an untracked folder never reaches the closed-day
        # audit, the middle-of-history check or the retention check, and none of
        # those emits a line for a machine it never looked at. Named, not
        # skipped.
        answered, head = _git(root, "show",
                              f"HEAD:{_mdir.name}/machine-readable/totals.json")
        if not answered or not head.strip():
            head_blind.append(f"{_mdir.name}/totals.json")
            continue
        try:
            before = json.loads(head)
            now = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        # The tail is what actually gets deleted, and a total can hide it. On an
        # actively used profile new work outgrows what ages out, so the headline
        # rises while the oldest days fall off — comparing totals alone reports
        # a healthy machine that is quietly losing its history. The oldest
        # retained day only ever moves forward when transcripts are deleted.
        # One account can own several profiles — the same person signed into
        # ~/.claude and into a copy of it elsewhere. A dict comprehension keyed
        # on the account name kept only the LAST profile seen, and profiles that
        # contributed nothing (a pure duplicate, deduplicated to zero) sort last
        # and carry no by_day at all, so the sentinel overwrote the real date
        # and this check reported a machine had lost its entire history.
        # Take the earliest real day across every profile for that account.
        def oldest_by_account(doc):
            out = {}
            for a in doc.get("accounts", []):
                days = a.get("by_day") or {}
                if not days:
                    continue                 # nothing retained here to compare
                d = min(days)
                cur = out.get(a["account"])
                if cur is None or d < cur:
                    out[a["account"]] = d
            return out

        ob = oldest_by_account(before)
        nb = oldest_by_account(now)
        for acct, was in ob.items():
            has = nb.get(acct)
            if has and was < has:
                lost = sum(v if isinstance(v, int) else sum(v.values())
                           for a in before.get("accounts", [])
                           if a["account"] == acct
                           for k, v in (a.get("by_day") or {}).items() if k < has)
                chk(f"no history dropped for {acct[:26]} on {now['machine'][:18]}",
                    has, was,
                    f"oldest retained day moved {was} -> {has}"
                    + (f", {lost:,} tokens of tail deleted" if lost else ""),
                    fatal=False)

        # Whether the counting logic itself changed decides how to read every
        # comparison below: a recount legitimately moves numbers that a
        # deletion also moves, and only this tells them apart.
        recounted = (before.get("scanner_version") or "?") != (now.get("scanner_version") or "?")

        # A CLOSED DAY IS IMMUTABLE.
        #
        # An adversarial run moved an entire day of tokens onto another day —
        # 2026-07-07 zeroed, 2026-08-08 raised by the same amount — and all 27
        # checks passed, because every partition still summed. by_day is what
        # the floor's "days after last_computed" term reads, so rewriting it
        # moves the floor without moving a single total.
        #
        # Per-day cross-scanner comparison cannot catch it: a session's tokens
        # are attributed to its START date, so a session running for weeks
        # leaves real days reading zero in sessions.json while by_day has
        # hundreds of millions. Measured, not assumed — 10 days on this machine
        # disagree by 100%, and the grand totals still match to 18,395.
        #
        # The anchor that does work is the last commit. Once a day is over, no
        # new tokens can be attributed to it, so its figure must never change
        # again. Retention DELETES whole days off the oldest end; it never edits
        # one in place. So a day present in both commits with a different number
        # is a rewrite, and a day that vanished while an OLDER day survived is a
        # hole in the middle, which retention cannot produce either.
        today = _dt.date.today().isoformat()
        if not recounted:
            def days_by_account(doc):
                out = defaultdict(dict)
                for a in doc.get("accounts", []):
                    for d, v in (a.get("by_day") or {}).items():
                        n = v if isinstance(v, int) else sum(v.get(k, 0) for k in FIELDS)
                        out[a["account"]][d] = out[a["account"]].get(d, 0) + n
                return out

            db, dn = days_by_account(before), days_by_account(now)
            rewritten, holes = [], []
            for acct, was_days in db.items():
                has_days = dn.get(acct) or {}
                if not has_days:
                    continue            # account gone entirely — other checks own that
                oldest_now = min(has_days)
                for d, was in was_days.items():
                    if d >= today:
                        continue        # today is still being written to
                    if d in has_days:
                        if has_days[d] != was:
                            rewritten.append(f"{acct[:20]} {d}: {was:,} -> {has_days[d]:,}")
                    elif d > oldest_now:
                        holes.append(f"{acct[:20]} {d} ({was:,})")
            chk(f"no closed day was rewritten on {now['machine'][:18]}",
                len(rewritten), 0,
                "; ".join(rewritten[:3]) + (f" (+{len(rewritten) - 3} more)" if len(rewritten) > 3 else "")
                + " — a finished day cannot gain or lose tokens" if rewritten else "",
                fatal=False)
            chk(f"no day vanished from the middle on {now['machine'][:18]}",
                len(holes), 0,
                "; ".join(holes[:3]) + " — retention removes the OLDEST days, "
                "never one with an older day still present" if holes else "",
                fatal=False)

        drop = before["grand_total_tokens"] - now["grand_total_tokens"]
        # A DROP IS NOT A LOSS IF THE SCANNER CHANGED.
        #
        # Fixing the dedup rule cut this machine 14,529,373,789 -> 6,608,178,238,
        # and this check reported it as "7,913,739,477 fewer ... transcripts aged
        # past cleanupPeriodDays and were deleted". Nothing was deleted; the
        # earlier figure was counting streaming re-writes as separate calls.
        #
        # Telling a recount from a deletion is exactly what scanner_version is
        # for, and it is right here in both documents. Without this, every future
        # correction to the counting logic raises a false alarm about data loss —
        # and an alarm that cries wolf on every improvement is one people learn
        # to ignore, which costs the real warning its meaning.
        if drop > 0 and recounted:
            # AN ASSERTION MUST RE-DERIVE ITS PREMISE, NOT RESTATE IT.
            #
            # This was chk(name, 0, 0) inside `if drop > 0 and recounted:` —
            # the branch condition written out a second time and called a
            # check. It could not fail, and it fired on exactly the occasion a
            # real one is most needed: the total went down.
            #
            # scanner_version says the COUNTING changed. It says nothing about
            # whether the transcripts are still on disk, and a deletion moves
            # the total the same direction a recount does. So the two are
            # indistinguishable from the version field alone — which matters
            # because the field is forgeable, and forging it is what switches
            # the closed-day audit off.
            #
            # The session inventory tells them apart. Re-reading the same
            # transcripts through new counting rules cannot reduce how many
            # sessions were FOUND; deleting transcripts takes their sessions
            # with them. Fewer tokens and fewer sessions together is a loss
            # wearing a recount's clothes, and this is what would say so.
            prev_s = subprocess.run(
                ["git", "show", f"HEAD:{_mdir.name}/{paths.MACHINE}/sessions.json"],
                cwd=root, capture_output=True, text=True)
            sf = paths.find(_mdir, "sessions.json")
            try:
                was_n = len(json.loads(prev_s.stdout).get("sessions") or [])
                now_n = len(json.loads(sf.read_text(encoding="utf-8")).get("sessions") or [])
            except Exception:  # noqa: BLE001
                was_n = now_n = None
            # None, not 0. There being no committed sessions.json to compare
            # against is a thing this check could not establish, and it must not
            # read the same as a machine that kept every session — that
            # substitution is the bug this whole file is a monument to.
            lost = None if None in (was_n, now_n) else max(0, was_n - now_n)
            if lost is None:
                detail = ("no committed sessions.json to compare the inventory "
                          "against, so this drop cannot be shown to be a recount")
            elif lost:
                detail = (f"{drop:,} fewer tokens AND {lost:,} fewer sessions "
                          f"({was_n:,} -> {now_n:,}) since the last commit. "
                          "Re-counting cannot lose a session — transcripts went "
                          "away as well, and the version change is not what "
                          "explains this")
            else:
                detail = (f"{drop:,} fewer than the last commit, but the scanner "
                          f"changed ({before.get('scanner_version') or 'pre-versioning'}"
                          f" -> {now.get('scanner_version')}) and all {now_n:,} "
                          "sessions are still there. Re-counted, not deleted — "
                          "compare like for like by rescanning the other machines")
            chk(f"total changed by a RECOUNT, not a loss, on {now['machine']}",
                lost, 0, detail, fatal=False)
        elif drop > 0:
            chk(f"no tokens lost to retention on {now['machine']}",
                now["grand_total_tokens"], before["grand_total_tokens"],
                f"{drop:,} fewer than the last commit — transcripts aged past "
                "cleanupPeriodDays and were deleted. Raise it in settings.json "
                "to stop further loss; the previous figure survives in git history",
                fatal=False)

    # THE FOLDERS NONE OF THE THREE COULD READ. One line for all of them,
    # emitted here because this is the last of the three sites to fill it.
    #
    # WARN and not FAIL: a machine folder that was never committed is a real,
    # innocent state — a computer scanned before its first commit is in it. What
    # is not innocent is saying nothing. Every check above that anchors on HEAD
    # surveyed this folder and reported on it exactly as it reports a folder
    # that is clean, which is how a relabel and a backdate on hp-laptop-linux
    # both printed PASS.
    _blind = sorted(set(head_blind))
    chk("every machine folder could be compared against HEAD",
        len(_blind), 0,
        ", ".join(_blind) + " — not at HEAD, so relabelling, backdating, "
        "closed days, holes in the middle and retention went unchecked on "
        "them. Commit the folder, or retire it" if _blind else "",
        fatal=False)

    # A floor below the measured figure is a contradiction, not a small error.
    # It happened: the floor read totals.json while the measured value read
    # sessions.json, and on a live machine those disagree by a live session.
    try:
        # subprocess is imported at module level
        for _mdir, f in paths.iter_machine_files(root, "sessions.json"):
            d = json.loads(f.read_text(encoding="utf-8"))
            meas = sum(x.get("total", 0) for x in d.get("sessions", []))
            tj = paths.find(_mdir, "totals.json")
            if not tj.is_file():
                continue
            t = json.loads(tj.read_text(encoding="utf-8"))
            cc_sess = sum(x.get("total", 0) for x in d.get("sessions", [])
                          if x.get("cli") == "claude")
            # THIS CHECK COULD NOT FAIL. It read, verbatim:
            #
            #   chk(name, max(cc_sess, t["grand_total_tokens"]),
            #             max(cc_sess, t["grand_total_tokens"]))
            #
            # The same expression on both sides, with no comparison anywhere
            # before it — one per machine, so 5 of the suite's checks were
            # decorative. Deleting 346 M tokens from a machine still gave
            # "0 failed, exit 0" from those five.
            #
            # The name states a real claim, so the check now makes it. sessions
            # counts every Claude session; totals.json counts the same tokens
            # per account. sessions must not be materially SMALLER — if it is,
            # a reader dropped something. The live-session allowance is the same
            # one the check above uses, and for the same reason: the two
            # scanners run moments apart on a machine still being used.
            short = t["grand_total_tokens"] - cc_sess
            live = sum(x.get("total", 0) for x in d.get("sessions", [])
                       if x.get("cli") == "claude"
                       and (x.get("end") or "") >= (t.get("generated_at") or ""))
            chk(f"claude sessions >= account totals on {t['machine'][:20]}",
                short <= max(live, 0), True,
                f"sessions is {short:,} BELOW totals and only {live:,} is "
                "attributable to a session still being written — a reader "
                "dropped work the other scanner saw" if short > max(live, 0) else "")
    except Exception:
        pass

    # AND FINALLY: the documents. Everything above compares the folders to
    # themselves; this compares them to what got published.
    published_gate(root, machines, sessions, chk)

    width = max(len(c[0]) for c in checks)
    failed = warned = 0
    for name, got, want, ok, detail, fatal in checks:
        tag = "PASS" if ok else ("FAIL" if fatal else "WARN")
        print(f"  {tag}  {name:<{width}}"
              + ("" if ok else (f"   {got:,} != {want:,}" if fatal else "")
                 + (f"  ({detail})" if detail else "")))
        if not ok:
            failed += fatal
            warned += not fatal
    print(f"\n{len(checks)} checks, {failed} failed"
          + (f", {warned} warning(s)" if warned else ""))
    if failed:
        print("\nA partition that does not sum to its whole means a slice is\n"
              "double-counting or dropping a bucket. Do not publish these numbers\n"
              "until it is explained.")
    if warned:
        print("\nWARN is not a wrong number: each machine's figures are correct for\n"
              "the code that produced them. They were not all produced by the same\n"
              "code, so the fleet total mixes accounting. Re-run update.py on the\n"
              "machines named above to bring them onto one version.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
