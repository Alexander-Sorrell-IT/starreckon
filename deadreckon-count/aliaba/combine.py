#!/usr/bin/env python3
"""Roll every machine folder up into the root data file and README tables.

Each machine folder holds a totals.json written by analyze_tokens.py. This walks
all of them and produces ALL-COMPUTERS.json plus the generated tables inside
README.md. The human-readable report is STATS.md, written by stats_page.py.

This also wrote ALL-COMPUTERS.md until it was noticed that the file was a strict
SUBSET of STATS.md - the same five sections, minus the cross-tabs and the
session rankings. Two documents saying the same thing is two documents that can
disagree, and one of them has to be the stale one.

The number worth having is the per-account total ACROSS machines: the same
account gets used from several computers, and no single machine's session files
can see the others. Only this rollup gives the real figure per account.

Usage:
    python3 combine.py            # scan ./*/totals.json, write the root data
"""

import datetime
import json
import pathlib
import paths
import sys
from collections import defaultdict

# Imported rather than copied: a second definition of "which vendor is this
# model" would drift from the scanner's, and this repo has already been bitten
# by the same logic living in two files.
from analyze_tokens import provider_of

# THE ROLLUP NEVER OPENED THE ONE FILE THAT OUTLIVES A DELETED TRANSCRIPT.
#
# Every figure below comes from totals.json and sessions.json, both of which are
# recomputed from whatever is on disk at that moment. `token_ledger.jsonl` is
# append-only and is the only record of usage whose transcript retention has
# already deleted; no report in this repository imported it. Measured across the
# five machines: the scans hold 30,504,578,569 and the ledgers hold
# 35,969,064,968, so 5,464,486,399 tokens existed in exactly one place and no
# published document had ever looked there.
import token_ledger

FIELDS = ("input_tokens", "cache_creation_input_tokens",
          "cache_read_input_tokens", "output_tokens")


def human(n):
    for unit, size in (("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if n >= size:
            return f"{n / size:.2f}{unit}"
    return str(n)


def hm(minutes):
    h, m = divmod(int(round(minutes)), 60)
    return f"{h}h {m:02d}m" if h else f"{m}m"


def load_sessions(root):
    """Every session record from every machine that has been through sessions.py.

    Returns (sessions, uncountable). A machine folder without sessions.json is
    skipped rather than treated as having none — absent and zero are different
    facts, and the report says which.
    """
    sessions, uncountable, have = [], {}, set()
    # Every CLI any machine has a reader for, even where it found nothing —
    # so a tool that is absent on this computer is still a zero row rather than
    # missing from the report entirely.
    all_clis = {}
    for mdir, f in paths.iter_machine_files(root, "sessions.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        name = d.get("machine", mdir.name)
        have.add(name)
        for r in d.get("readers") or []:
            e = all_clis.setdefault(r["cli"], {"installed_on": [], "absent_on": []})
            (e["installed_on"] if r.get("installed") else e["absent_on"]).append(name)
        for s in d.get("sessions", []):
            s["machine"] = name
            sessions.append(s)
        for u in d.get("uncountable_tools") or []:
            # Same tool on two machines: keep the one that found more, so a
            # machine where it was merely installed does not mask a machine
            # where it was actually used.
            k = u.get("tool")
            if k not in uncountable or (u.get("files", 0) > uncountable[k].get("files", 0)):
                uncountable[k] = dict(u, machine=name)
    return sessions, uncountable, have, all_clis


def load_fleet(root):
    """Machines that are supposed to exist, scanned or not.

    Everything else in this report is derived from whatever machine folders are
    present, which means a computer that has never been scanned does not show up
    as missing — it is simply absent, and the grand total quietly understates by
    whatever that machine holds. This file is the only place the fleet is stated
    rather than inferred, so those gaps can be named.

    Optional: with no machines.json, the report is exactly what the folders say.
    """
    f = root / "machines.json"
    if not f.is_file():
        return []
    try:
        return json.loads(f.read_text(encoding="utf-8")).get("machines") or []
    except Exception:
        return []


def load_accounts(root):
    """Accounts that are supposed to exist, and labels for the emailless ones.

    Same reasoning as the fleet: accounts are discovered from whatever machines
    have been scanned, so one that lives only on an unscanned computer is not
    reported as missing — it is simply not there. Stating them makes that gap
    visible. Returns (known_emails, {userID: label}).
    """
    f = root / "accounts.json"
    if not f.is_file():
        return [], {}
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return [], {}
    labels = {p["userID"]: p.get("label") or p["userID"]
              for p in (d.get("profiles") or []) if p.get("userID")}
    return (d.get("accounts") or []), labels


def load_ledger_only(root, scanned):
    """Machine folders holding a ledger and no scan — the state between the two.

    Every ledger figure in this file was read inside the loop over
    `iter_machine_files(root, "totals.json")`, and that function — like
    `paths.machine_folders` under it — decides what a machine folder IS by
    asking for totals.json. So a folder whose scan has not been committed, has
    been retired, or was pulled from a computer mid-export carried its
    append-only ledger and contributed nothing at all. Measured on this tree:

        asus-laptop-linux                 146,981,095      36 sessions
        dell-inspiron-desktop-linux        11,292,220       7 sessions
        dell-latitude-7480-linux        4,464,394,318  13,378 sessions
                                        -------------
                                        4,622,667,633   read as zero

    and all three printed "❌ never scanned" on the front page — the one state
    they are demonstrably not in. At one HEAD hp-laptop-linux was here too,
    with a committed ledger of 13,367,051,701 across 374 sessions, and the
    front page called it never scanned for the same reason.

    Existence is tested by the ledger being on disk, not by totals.json being
    on disk: the content-for-existence mistake `corpus_machine_folders` was
    written to undo. `total` and `scanned` come back None, never 0 — there is
    no scan, which is not a scan that found nothing.
    """
    out = []
    for d in sorted(p for p in pathlib.Path(root).iterdir() if p.is_dir()):
        if (d.name in paths.NOT_A_MACHINE or d.name.startswith(".")
                or d.name in scanned):
            continue
        if paths.find(d, token_ledger.LEDGER) is None:
            continue
        # The name every other table uses is the LABEL — totals.json's
        # "machine" key is "HP Laptop Linux", not "hp-laptop-linux". Without a
        # scan the label is only in .machine-id, so a ledger-only row would
        # otherwise be the one row in the report named by its folder.
        label = d.name
        mid = d / ".machine-id"
        if mid.is_file():
            try:
                label = json.loads(mid.read_text(encoding="utf-8")).get("label") or d.name
            except Exception:
                pass
        lt = token_ledger.lifetime(d)
        out.append({"machine": label, "folder": d.name, "state": "ledger-only",
                    "total": None, "scanned": None, "sessions_scanned": False,
                    "ledger_total": lt["total"], "ledger_sessions": lt["sessions"],
                    "ledger_present": True, "ledger_beyond_scan": None})
    return out


def main():
    root = pathlib.Path(__file__).parent
    machines = []
    for mdir, f in paths.iter_machine_files(root, "totals.json"):
        with open(f, encoding="utf-8") as fh:
            m = json.load(fh)
        m["folder"] = mdir.name
        # What the ledger stands behind for this machine, and — separately —
        # whether there is a ledger at all. A machine that has never run
        # `token_ledger.py --record` and one whose ledger holds no rows both
        # total 0; `ledger_present` is the only thing that keeps "there is no
        # record" from being published as "the record says nothing".
        lt = token_ledger.lifetime(mdir)
        m["ledger_total"] = lt["total"]
        m["ledger_sessions"] = lt["sessions"]
        m["ledger_present"] = paths.find(mdir, token_ledger.LEDGER) is not None
        # Optional — a machine folder is still valid without check_hardware.py
        # having been run on it.
        hwf = paths.find(mdir, "hardware.json")
        if hwf and hwf.exists():
            try:
                m["hw"] = json.loads(hwf.read_text(encoding="utf-8"))
            except Exception:
                pass
        machines.append(m)

    # A ledger is read wherever one EXISTS. The loop above can only reach a
    # folder that has totals.json, so this is the rest of them.
    ledger_only = load_ledger_only(root, {m["folder"] for m in machines})

    if not machines:
        sys.exit("no <machine>/totals.json found — run analyze_tokens.py first"
                 + ("" if not ledger_only else
                    "\n\n  A token ledger IS present on "
                    + ", ".join(f"{e['folder']} ({e['ledger_total']:,})"
                                for e in ledger_only)
                    + f"\n  — {sum(e['ledger_total'] for e in ledger_only):,} recorded "
                      "tokens this run wrote nothing about, because the report\n"
                      "  needs one scanned machine to be built at all."))

    # TWO FOLDERS CLAIMING ONE COMPUTER WERE ADDED TOGETHER.
    #
    # Everything below sums `grand_total_tokens` over whatever folders exist.
    # Nothing asked whether two of them are the same machine, and a machine
    # folder gets copied for ordinary reasons — a rename that left the old name
    # behind (migrate_rename.py), a folder restored from a backup beside the
    # live one, a corpus checkout unpacked into the repo. Measured on a planted
    # five-machine fleet, alpha's folder duplicated as alpha-old:
    #
    #     grand_total_tokens 2,234,500,000   planted 1,234,500,000
    #     rows: Alpha/alpha, Alpha/alpha-old, Bravo/bravo, ...
    #
    # +81%, two rows with the same name in the by-computer table, and
    # check_consistency reported 28 checks, 0 failed, exit 0 — its "machines
    # partition the grand total" compares that sum against itself.
    #
    # NOT resolved automatically, and that is a decision. The two folders are
    # either one scan twice (dedupe) or two scans of one computer taken at
    # different times with different stores (keep the newer, lose the other's
    # coverage), and nothing in the files says which. Guessing produces a
    # plausible total that nobody can reproduce, which is the failure this
    # repository exists to avoid. It names both folders and stops.
    dupes = defaultdict(list)
    for m in machines:
        dupes[m["machine"]].append(m["folder"])
    dupes = {k: v for k, v in dupes.items() if len(v) > 1}
    if dupes:
        sys.exit("two folders claim the same computer, and their tokens would "
                 "be added together:\n" +
                 "\n".join(f"  {k}: {', '.join(sorted(v))}" for k, v in
                           sorted(dupes.items())) +
                 "\n\nRemove or rename the folder that is not the current one. "
                 "Nothing was written.")

    fleet = load_fleet(root)
    known_accounts, profile_labels = load_accounts(root)
    machines.sort(key=lambda m: -m["grand_total_tokens"])

    # Replace bare user:<uid> rows with what that profile actually is.
    #
    # Sessions are loaded here rather than further down so they can be renamed in
    # the same pass. This file had its own copy of the rename that touched
    # machines only, and stats_page.machine_floor — called below for the README's
    # Floor column — then looked "DeepSeek backend (~/.my-claude)" up in a
    # session map still keyed "user:73ae64bf180b", missed, and fell back to
    # grand_total: 520,497,793 published for a profile whose sessions measure
    # 529,474,038. Imported rather than copied for the same reason provider_of
    # is; the rename and the lookup that depends on it now live in one file.
    import stats_page as _sp
    S, uncountable, scanned, all_clis = load_sessions(root)
    _sp.relabel_profiles(machines, S, profile_labels)

    # Per-account totals across every machine. Sessions on different computers
    # are disjoint, so these add without any risk of double-counting.
    # "machines" is keyed by machine name and ACCUMULATED, not appended to.
    # One account can own several profiles on one computer — the same login used
    # from ~/.claude and from a copy of it elsewhere — and appending per profile
    # counted that computer once per profile: the account table reported one
    # account as spanning 9 computers on a 5-computer fleet, and by_machine kept
    # only whichever profile happened to be built last.
    per_account = defaultdict(lambda: {
        "total": 0, "sessions": 0, "turns": 0, "machines": defaultdict(int),
        "fields": dict.fromkeys(FIELDS, 0),
        "models": defaultdict(int), "days": set(),
    })
    for m in machines:
        for a in m["accounts"]:
            acct = per_account[a["account"]]
            acct["total"] += a["grand_total"]
            acct["sessions"] += a["sessions"]
            acct["turns"] += a["turns"]
            acct["machines"][m["machine"]] += a["grand_total"]
            for k in FIELDS:
                acct["fields"][k] += a["totals"][k]
            for model, v in a["by_model"].items():
                acct["models"][model] += sum(v[k] for k in FIELDS)
            acct["days"].update(a["by_day"].keys())

    grand = sum(m["grand_total_tokens"] for m in machines)
    accounts = sorted(per_account.items(), key=lambda kv: -kv[1]["total"])
    all_days = set()
    for a in per_account.values():
        all_days |= a["days"]

    generated_at = datetime.datetime.now().astimezone().isoformat(timespec="seconds")

    L = [f"# All computers — {human(grand)} tokens", "",
         f"_Generated {generated_at}_", "",
         f"## Overall total: {grand:,} tokens ({human(grand)})", ""]
    L += [f"**{human(grand)}** across {len(machines)} computer(s), "
          f"{len(accounts)} account(s), "
          f"{sum(m['grand_total_tokens'] and sum(a['sessions'] for a in m['accounts']) or 0 for m in machines):,} sessions, "
          f"{sum(sum(a['turns'] for a in m['accounts']) for m in machines):,} assistant turns"]
    if all_days:
        L.append(f"over {len(all_days)} active days "
                 f"({min(all_days)} → {max(all_days)}).")
    L += ["", "Counted from `message.usage` in the local Claude Code session JSONL on each",
          "machine — the API's own accounting, deduplicated by message uuid. See",
          "[README](README.md) for the method.", ""]

    L += ["## By computer", "",
          "| Computer | Hardware | Accounts | Tokens | Share | Scanned |",
          "|---|---|---:|---:|---:|---|"]
    for m in machines:
        hw = (m.get("hw") or {}).get("hardware") or {}
        bits = [hw.get("chip") or "",
                f"{hw['cpu_logical']} cores" if hw.get("cpu_logical") else "",
                f"{hw['memory_gb']:g} GB" if hw.get("memory_gb") else ""]
        spec = " · ".join(b for b in bits if b) or "—"
        # A folder scanned before the current scanner is a floor, not a total.
        when = m.get("generated_at") or "—  ⚠️ pre-timestamp, rescan"
        L.append(f"| [{m['machine']}]({m['folder']}/human-readable/REPORT.md) | {spec} | "
                 f"{len(m['accounts'])} | {m['grand_total_tokens']:,} | "
                 f"{m['grand_total_tokens'] / grand:.0%} | {when} |")

    # Registered but never scanned. These contribute 0 to every number above,
    # which is the point of naming them: the total is a floor until they are in.
    have = {m["folder"] for m in machines} | {m["machine"] for m in machines}
    unscanned = [e for e in fleet
                 if e.get("folder") not in have and e.get("label") not in have]
    for e in unscanned:
        L.append(f"| {e.get('label') or e.get('folder')} | — | — | — | — | "
                 f"❌ **never scanned** |")
    if unscanned:
        L += ["",
              f"> **{len(unscanned)} of {len(machines) + len(unscanned)} computers have "
              f"never been scanned** — {', '.join(e.get('label') or e['folder'] for e in unscanned)}. "
              f"Every total in this report is a floor, not a total, until they are. "
              f"To add one: run the scanners on it with "
              f"`--out {unscanned[0].get('folder')}`, then `combine.py`."]

    if any(m.get("hw") for m in machines):
        L += ["", "<details><summary>Full hardware</summary>", ""]
        for m in machines:
            h = m.get("hw")
            if not h:
                continue
            hw, dk = h.get("hardware") or {}, h.get("disk") or {}
            L += [f"**{m['machine']}** — `{h.get('hostname')}`", "",
                  f"- {hw.get('chip')} · {hw.get('model_identifier')}"]
            if hw.get("cpu_performance_cores"):
                L.append(f"- {hw.get('cpu_logical')} cores "
                         f"({hw['cpu_performance_cores']}P + "
                         f"{hw.get('cpu_efficiency_cores')}E)")
            elif hw.get("cpu_logical"):
                L.append(f"- {hw['cpu_logical']} cores")
            if hw.get("memory_gb"):
                L.append(f"- {hw['memory_gb']:g} GB RAM")
            if hw.get("gpu_cores"):
                L.append(f"- {hw['gpu_cores']}-core GPU ({hw.get('gpu')})")
            L.append(f"- {hw.get('os')} ({hw.get('os_build') or '-'})")
            if dk.get("total_gb"):
                L.append(f"- disk {dk['free_gb']:g} GB free of {dk['total_gb']:g} GB")
            L.append("")
        L += ["</details>"]

    # Per provider, for EVERY machine. Derived from each totals.json's by_model,
    # so a machine that has not run sessions.py still appears here — the earlier
    # version took providers only from sessions.json and silently credited two
    # of three machines with nothing.
    prov = defaultdict(int)
    prov_machine = defaultdict(lambda: defaultdict(int))
    for m in machines:
        for a in m["accounts"]:
            for model, v in a["by_model"].items():
                p = provider_of(model)
                n = sum(v[k] for k in FIELDS)
                prov[p] += n
                prov_machine[m["machine"]][p] += n
    prov_order = [p for p, _ in sorted(prov.items(), key=lambda kv: -kv[1]) if prov[p]]

    L += ["", "## By provider — whose model actually ran", "",
          "Claude Code can be pointed at a non-Anthropic backend and the transcripts",
          "look identical, so a raw total is not an Anthropic total. Split on the model",
          "id, across every machine:", "",
          "| Provider | Tokens | Share |", "|---|---:|---:|"]
    for p in prov_order:
        L.append(f"| {p} | {prov[p]:,} | {prov[p] / grand:.1%} |")

    L += ["", "### Per computer, per provider", "",
          "| Computer | " + " | ".join(prov_order) + " | Total |",
          "|---" * (len(prov_order) + 2) + "|"]
    for m in machines:
        row = prov_machine[m["machine"]]
        L.append(f"| {m['machine']} | "
                 + " | ".join(human(row.get(p, 0)) if row.get(p) else "—" for p in prov_order)
                 + f" | **{m['grand_total_tokens']:,}** |")
    L.append("| **All** | " + " | ".join(f"**{human(prov[p])}**" for p in prov_order)
             + f" | **{grand:,}** |")

    L += ["", "## By account, across every computer", "",
          "| Account | Computers | Sessions | Turns | Tokens | Share |",
          "|---|---|---:|---:|---:|---:|"]
    for name, a in accounts:
        where = ", ".join(f"{mn} {human(t)}" for mn, t in
                          sorted(a["machines"].items(), key=lambda x: -x[1]))
        L.append(f"| {name} | {where} | {a['sessions']:,} | {a['turns']:,} | "
                 f"**{a['total']:,}** | {a['total'] / grand:.0%} |")

    # Known accounts that have not turned up in any scanned machine's data.
    seen_names = " ".join(n for n, _ in accounts).lower()
    missing_accounts = [a for a in known_accounts
                        if a.get("email", "").lower() not in seen_names]
    if missing_accounts:
        L += ["",
              f"> ⚠️ **{len(missing_accounts)} known account(s) not found in any scanned "
              f"machine:** " + ", ".join(f"`{a['email']}`" for a in missing_accounts) +
              ". Accounts are discovered from the machines that have been scanned, so "
              "this one is signed in somewhere that has not been, and none of its usage "
              "is in any total above."]

    L += ["", "### Token type", "",
          "All four are billed. Cache reads dominate because every turn re-reads the",
          "whole conversation, so a session's context is billed once per turn.", "",
          "| Account | Input | Cache write | Cache read | Output |", "|---|---:|---:|---:|---:|"]
    for name, a in accounts:
        L.append(f"| {name} | " + " | ".join(human(a["fields"][k]) for k in FIELDS) + " |")

    L += ["", "### Models", "", "| Account | Model | Tokens |", "|---|---|---:|"]
    for name, a in accounts:
        for model, tot in sorted(a["models"].items(), key=lambda kv: -kv[1]):
            if tot:
                L.append(f"| {name} | {model} | {human(tot)} |")

    # WHAT THE LEDGER HOLDS BEYOND THE SCAN, AGAINST THE SAME BASIS.
    #
    # The ledger is keyed by session and covers every CLI. `grand_total_tokens`
    # is Claude Code only and is aggregated per ACCOUNT. Subtracting the second
    # from the first compares two different populations and calls the leftover
    # "lost history": on this fleet that arithmetic reads 12,791,551,420 where
    # the like-for-like figure is 5,464,486,399, and the 7.3 B difference is
    # simply the CLIs that totals.json never counted.
    #
    # The every-CLI per-session total is the figure that matches, and this file
    # already computes it for the README. A machine that has never run
    # sessions.py has no such figure: it gets None, not 0, or its entire ledger
    # would be published as recovered history.
    cli_by_machine = defaultdict(int)
    for s in S:
        cli_by_machine[s.get("machine")] += s.get("total", 0)
    ledger_beyond = {m["machine"]:
                     (max(0, m["ledger_total"] - cli_by_machine[m["machine"]])
                      if m["machine"] in scanned else None)
                     for m in machines}
    beyond_total = sum(v for v in ledger_beyond.values() if v)
    beyond_unknown = sorted(k for k, v in ledger_beyond.items() if v is None)

    # Every ledger there is, not every ledger that happens to sit beside a scan.
    # The scanned machines hold 35,054,910,068; the three ledger-only folders
    # hold 4,622,667,633 more, and that 4.62 B appeared in no published figure.
    # Their share of `beyond_total` is not added: that quantity is the ledger
    # minus the every-CLI scan, and a machine with no scan has no such
    # subtraction — unknown, not the whole ledger and not zero.
    ledger_only_total = sum(e["ledger_total"] for e in ledger_only)
    ledger_fleet = sum(m["ledger_total"] for m in machines) + ledger_only_total

    cli_rows, prov_rows = [], []
    if S:
        by_cli = defaultdict(lambda: [0, 0, 0.0])
        by_prov = defaultdict(lambda: [0, 0, 0.0])
        for c in all_clis:
            by_cli[c]          # seed at zero so it cannot vanish from the table
        for s in S:
            for agg, key in ((by_cli, s.get("cli")), (by_prov, s.get("provider"))):
                e = agg[key or "-"]
                e[0] += 1
                e[1] += s.get("total", 0)
                e[2] += s.get("duration_min", 0)
        cli_rows = sorted(by_cli.items(), key=lambda kv: -kv[1][1])
        prov_rows = sorted(by_prov.items(), key=lambda kv: -kv[1][1])

        missing = sorted({m["machine"] for m in machines} - scanned)
        s_tok = sum(s.get("total", 0) for s in S)
        s_min = sum(s.get("duration_min", 0) for s in S)
        claude_tok = sum(s.get("total", 0) for s in S if s.get("cli") == "claude")

        L += ["", "## Across every CLI", "",
              f"{len(S):,} sessions, {hm(s_min)} of active time, {human(s_tok)} tokens "
              f"— from `sessions.py` on {len(scanned)} machine(s)."]
        if missing:
            L.append("")
            L.append("> ⚠️ Not in this section: **" + ", ".join(missing) +
                     "** — `sessions.py` has not been run there, so the CLI totals "
                     "below cover fewer machines than the token totals above.")
        others = [k for k, _ in cli_rows if k != "claude"]
        other_tok = s_tok - claude_tok
        L += ["",
              "**These do not add to the totals above.** The `claude` row is the same "
              f"usage counted a second way ({human(claude_tok)} here), not extra tokens. "
              f"The other {len(others)} — {', '.join(others)} — are "
              f"{human(other_tok)} of usage the account totals never covered at all.", "",
              "| CLI | Sessions | Active time | Tokens |", "|---|---:|---:|---:|"]
        for k, (n, t, mn) in cli_rows:
            note = ""
            if not n:
                info = all_clis.get(k) or {}
                note = (" — installed, no usage recorded" if info.get("installed_on")
                        else " — not installed on any scanned computer")
            L.append(f"| {k}{note} | {n:,} | {hm(mn)} | {human(t)} |")

        L += ["", "### By provider — whose model actually ran", "",
              "A different question from the table above: Copilot runs Claude models, "
              "so that usage is Copilot *spend* but Anthropic *service*.", "",
              "| Provider | Sessions | Active time | Tokens |", "|---|---:|---:|---:|"]
        for k, (n, t, mn) in prov_rows:
            L.append(f"| {k} | {n:,} | {hm(mn)} | {human(t)} |")

        ranked = sorted(S, key=lambda s: s.get("duration_min", 0), reverse=True)[:10]
        L += ["", "### Ten longest sessions", "",
              "Ranked by active time, the way Claude Code ranks its own — gaps over 15 "
              "minutes are idle and dropped, so this is work done, not calendar span.", "",
              "| When | Machine | CLI | Active | Tokens | Turns | Project |",
              "|---|---|---|---:|---:|---:|---|"]
        for s in ranked:
            L.append(f"| {(s.get('start') or '?')[:10]} | {s.get('machine','-')} | "
                     f"{s.get('cli','-')} | {hm(s.get('duration_min', 0))} | "
                     f"{human(s.get('total', 0))} | {s.get('turns', 0):,} | "
                     f"{(s.get('project') or '-')[:40]} |")

        L += ["", "Query any slice of this with `stats.py`:", "",
              "```bash", "python3 stats.py --machine hp-laptop-linux",
              "python3 stats.py --cli copilot --by tokens",
              "python3 stats.py --provider anthropic --top 10", "```"]

        if uncountable:
            L += ["", "### Installed but not counted here", "",
                  "Presence and countability are separate facts — \"no usage recorded\" "
                  "and \"never used\" are not the same thing.", "",
                  "| Tool | Files | Records token usage |", "|---|---:|---|"]
            for k, u in sorted(uncountable.items()):
                note = "yes" if u.get("records_token_usage") else "no"
                if u.get("conversation_dbs"):
                    note += f" — {u['conversation_dbs']} conversation DBs"
                L.append(f"| {k} | {u.get('files', 0):,} | {note} |")

    # Keep the README's headline table generated rather than typed. It listed
    # three machines and two hand-copied totals, which is exactly the kind of
    # thing that is right on the day it is written and wrong by the next scan.
    readme = root / "README.md"
    if readme.is_file():
        BEG, END = "<!-- BEGIN OVERVIEW -->", "<!-- END OVERVIEW -->"
        text = readme.read_text(encoding="utf-8")
        if BEG in text and END in text:
            # The FLOOR leads, not the measured figure. Three separate times
            # someone read "Claude Code" here as this computer's usage and was
            # surprised it had halved — because that column is only what is
            # still on disk, and most of the history has been deleted by
            # retention. Showing measured alone invites the wrong reading every
            # time; showing both makes the gap the point.
            import stats_page as _sp
            # stats_cache lives in each machine's sessions.json. Reading it is
            # what makes the floor a floor; without it machine_floor returns the
            # measured figure and the new column would silently duplicate the
            # old one — a column that always agrees is worse than no column.
            _cache = {}
            for _md, _sf in paths.iter_machine_files(root, "sessions.json"):
                try:
                    _d = json.loads(_sf.read_text(encoding="utf-8"))
                except Exception:
                    continue
                _cache[_d.get("machine", _md.name)] = _d.get("stats_cache") or []
            floors = {}
            for _m in machines:
                _ses = [x for x in S if x.get("machine") == _m["machine"]]
                try:
                    floors[_m["machine"]] = _sp.machine_floor(
                        _m, _ses, _cache.get(_m["machine"], []))[0]
                except Exception:
                    floors[_m["machine"]] = None
            rows = ["| Machine | Hardware | Accounts | Floor | On disk now | Every CLI | Scanned |",
                    "|---|---|---:|---:|---:|---:|---|"]
            for m in machines:
                hw = (m.get("hw") or {}).get("hardware") or {}
                bits = [hw.get("chip") or "",
                        f"{hw['cpu_logical']} cores" if hw.get("cpu_logical") else "",
                        f"{hw['memory_gb']:g} GB" if hw.get("memory_gb") else ""]
                spec = " · ".join(b for b in bits if b) or "—"
                cli = sum(s.get("total", 0) for s in S if s.get("machine") == m["machine"])
                fl = floors.get(m["machine"])
                rows.append(
                    f"| [`{m['folder']}/`]({m['folder']}/human-readable/REPORT.md) | {spec} | "
                    f"{len(m['accounts'])} | **{human(fl) if fl else '—'}** | "
                    f"{human(m['grand_total_tokens'])} | "
                    f"{human(cli) if cli else '_not scanned_'} | "
                    f"{(m.get('generated_at') or '⚠️ stale')[:10]} |")
            # "❌ never" and "📒 ledger only" are different facts, and every
            # roster entry without a scan was printed as the first one.
            # dell-latitude-7480-linux carried 4,464,394,318 tokens over 13,378
            # sessions under that ❌; dell-latitude-7480-windows has no folder
            # at all and is the only one of the four the word is true of.
            lo_by_folder = {e["folder"]: e for e in ledger_only}
            for e in unscanned:
                lo = lo_by_folder.pop(e.get("folder"), None)
                rows.append(f"| `{e.get('folder')}/` | — | — | — | — | — | "
                            + (f"📒 **ledger only** — {human(lo['ledger_total'])}, "
                               f"{lo['ledger_sessions']:,} sessions |" if lo
                               else "❌ never |"))
            # A ledger folder nobody added to machines.json. It is in no other
            # list this file builds, so without this row it is in no document.
            for lo in lo_by_folder.values():
                rows.append(f"| `{lo['folder']}/` | — | — | — | — | — | "
                            f"📒 **ledger only, off-roster** — "
                            f"{human(lo['ledger_total'])}, "
                            f"{lo['ledger_sessions']:,} sessions |")
            _tf = sum(v for v in floors.values() if v)
            rows += ["| **All computers** | | | **" + human(_tf) + "** | **"
                     + human(grand) + "** | | |", "",
                     "",
                     "**Floor** is the defensible figure: what is still on disk PLUS what "
                     "Claude Code's own frozen counter remembers of work whose transcripts "
                     "have since been deleted. **On disk now** is only what survived "
                     "retention — it is always the smaller number, and it drops over time "
                     "even when usage does not.",
                     "",
                     # The ledger is not folded into the Floor column here: that
                     # column is produced by stats_page.machine_floor and the
                     # consistency gate recomputes it through the same function,
                     # so moving it in one place without the other would make the
                     # gate compare two different definitions and call the
                     # document wrong. Published as its own sentence instead, and
                     # in full in machine-readable/ALL-COMPUTERS.json.
                     f"The append-only token ledgers stand behind "
                     f"**{human(ledger_fleet)}** across the fleet, of which "
                     f"**{human(beyond_total)}** is usage "
                     "no scan can still see, because the transcripts behind it "
                     "have been deleted. `LIFETIME.md` counts it; the columns "
                     "above do not."
                     + ("" if not ledger_only else
                        f" **{human(ledger_only_total)}** of that is on machines "
                        "with a ledger and no scan at all — "
                        + ", ".join(f"`{e['folder']}`" for e in ledger_only)
                        + " — which is not the state above and not never scanned: "
                          "the tokens are recorded, they are in no column here, and "
                          "how much of them a scan could still see is unknown "
                          "rather than zero.")
                     + ("" if not beyond_unknown else
                        " Not included in that figure: "
                        + ", ".join(f"`{b}`" for b in beyond_unknown)
                        + " — `sessions.py` has never run there, so there is no "
                          "every-CLI total to compare the ledger against and the "
                          "answer is unknown rather than zero.")
                     + ("" if all(m["ledger_present"] for m in machines) else
                        " **No ledger exists at all on "
                        + ", ".join(f"`{m['folder']}`" for m in machines
                                    if not m["ledger_present"])
                        + "** — never recorded, which is not a ledger that reads "
                          "zero: nothing there is protected from the next "
                          "retention sweep."),
                     "",
                     f"_{len(machines)} of {len(machines) + len(unscanned)} computers scanned; "
                     f"generated by `combine.py` {generated_at[:10]}. Do not edit by hand._"]
            text = text[:text.index(BEG) + len(BEG)] + "\n" + "\n".join(rows) + "\n" + text[text.index(END):]
            readme.write_text(text, encoding="utf-8")

        # The by-CLI / by-provider table, generated for the same reason: it was
        # typed by hand and every figure in it went stale the moment anything
        # was scanned again. Nothing in this README should be a number a human
        # keeps in sync.
        B2, E2 = "<!-- BEGIN CLI -->", "<!-- END CLI -->"
        text = readme.read_text(encoding="utf-8")
        if B2 in text and E2 in text and cli_rows:
            n = max(len(cli_rows), len(prov_rows))
            t = ["| by CLI | | | by company | |", "|---|---:|---|---|---:|"]
            for i in range(n):
                a = (f"| {cli_rows[i][0]} | {human(cli_rows[i][1][1])} |"
                     if i < len(cli_rows) else "| | |")
                b = (f" | {prov_rows[i][0]} | {human(prov_rows[i][1][1])} |"
                     if i < len(prov_rows) else " | | |")
                t.append(a + b)
            t += ["",
                  f"_Generated by `combine.py` from {len(scanned)} scanned machine(s); "
                  f"{human(s_tok)} across {len(cli_rows)} CLI(s). Do not edit by hand._"]
            text = text[:text.index(B2) + len(B2)] + "\n" + "\n".join(t) + "\n" + text[text.index(E2):]
            readme.write_text(text, encoding="utf-8")

        # Per-account totals. This replaced a paragraph naming one machine and
        # its five profiles by hand — which was not merely stale but WRONG on
        # any other computer, and this README is read on six of them.
        B3, E3 = "<!-- BEGIN ACCOUNTS -->", "<!-- END ACCOUNTS -->"
        text = readme.read_text(encoding="utf-8")
        if B3 in text and E3 in text:
            t = ["| Account | Tokens | Share | Computers |", "|---|---:|---:|---|"]
            for name, a in accounts:
                t.append(f"| {name} | {human(a['total'])} | {a['total'] / grand:.1%} | "
                         f"{len(a['machines'])} |")
            t += ["",
                  f"_{len(accounts)} account(s) across {len(machines)} scanned computer(s), "
                  f"{human(grand)} total. Generated by `combine.py`. Do not edit by hand._"]
            text = text[:text.index(B3) + len(B3)] + "\n" + "\n".join(t) + "\n" + text[text.index(E3):]
            readme.write_text(text, encoding="utf-8")

    summary = {
        "generated_at": generated_at,
        "grand_total_tokens": grand,
        # grand_total_tokens and machines[].total stay exactly what they were:
        # the scan. No ledger figure is folded into either, so nothing that
        # already reads this file starts comparing a floor against a scan
        # without being changed to say so.
        # Every ledger on disk, which is a CHANGE of this key: it summed only
        # the folders that also had a totals.json, so on this tree it published
        # 35,054,910,068 where the ledgers hold 39,677,577,701. Both partitions
        # are still derivable — machines[] and ledger_only_machines[] each carry
        # their own ledger_total — so nothing has to trust this sum.
        "ledger_total": ledger_fleet,
        "ledger_beyond_scan": beyond_total,
        # Ledger, no scan. A separate list rather than extra machines[] rows:
        # machines[].total is a scan figure and these have none, and publishing
        # 0 there would say the computer did nothing. Every row carries
        # "state", so the two lists can be concatenated without losing which.
        "ledger_only_machines": ledger_only,
        # null, not 0. A machine with no session scan has no comparable figure,
        # and publishing 0 there would say its ledger recovers nothing.
        "ledger_beyond_scan_unknown_on": beyond_unknown,
        "machines_without_ledger": [m["folder"] for m in machines
                                    if not m["ledger_present"]],
        "machines": [{"machine": m["machine"], "folder": m["folder"],
                      "state": "scanned",
                      "total": m["grand_total_tokens"],
                      "ledger_total": m["ledger_total"],
                      "ledger_sessions": m["ledger_sessions"],
                      "ledger_present": m["ledger_present"],
                      "ledger_beyond_scan": ledger_beyond[m["machine"]],
                      "scanned": m.get("generated_at"),
                      "sessions_scanned": m["machine"] in scanned} for m in machines],
        "accounts": [{"account": n, "total": a["total"], "sessions": a["sessions"],
                      "turns": a["turns"],
                      "by_machine": dict(a["machines"]),
                      "totals": a["fields"]} for n, a in accounts],
        # Kept out of grand_total_tokens on purpose: the claude rows are the same
        # usage as `accounts` above, counted per session instead of per account.
        "by_cli": {k: {"sessions": n, "tokens": t, "active_min": round(mn, 1)}
                   for k, (n, t, mn) in cli_rows},
        # Claude Code only, but every machine.
        "by_provider": {p: prov[p] for p in prov_order},
        "by_machine_provider": {mn: dict(v) for mn, v in prov_machine.items()},
        # Cross-CLI, but only machines that have run sessions.py.
        "cli_by_provider": {k: {"sessions": n, "tokens": t, "active_min": round(mn, 1)}
                            for k, (n, t, mn) in prov_rows},
        "uncountable_tools": list(uncountable.values()),
    }
    (paths.machine(root) / "ALL-COMPUTERS.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    sys.stderr.write("wrote ALL-COMPUTERS.json and the README tables\n")
    sys.stderr.write(f"  ledger stands behind {summary['ledger_total']:,} "
                     f"tokens, {summary['ledger_beyond_scan']:,} of them beyond "
                     f"what any scan can still see\n")
    if beyond_unknown:
        sys.stderr.write(
            "  not comparable on: " + ", ".join(beyond_unknown)
            + " — no sessions.py scan there, so how much of their ledger is\n"
              "  lost history is UNKNOWN, not zero\n")
    if ledger_only:
        sys.stderr.write(
            "  LEDGER ONLY — a ledger and no scan on: "
            + ", ".join(f"{e['folder']} ({e['ledger_total']:,} over "
                        f"{e['ledger_sessions']:,} sessions)"
                        for e in ledger_only)
            + f"\n  {ledger_only_total:,} tokens. Read as zero by every run before "
              "this line existed, and\n"
              "  printed on the front page as never scanned, which they are not.\n")
    if summary["machines_without_ledger"]:
        sys.stderr.write(
            "  NO token_ledger.jsonl at all on: "
            + ", ".join(summary["machines_without_ledger"])
            + " — never recorded, which is not a ledger reading zero. Their\n"
              "  history is unprotected: when retention deletes a transcript "
              "there, the tokens go with it.\n")


if __name__ == "__main__":
    main()
