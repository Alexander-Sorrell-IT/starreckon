#!/usr/bin/env python3
"""Write the three root reports, one per question people actually ask.

    BY-COMPUTER.md   what is on each machine, and everything it did
    BY-ACCOUNT.md    what each login spent, across every machine
    BY-COMPANY.md    what each vendor was actually paid for

    python3 stats_page.py            # reads */totals.json + */sessions.json

Three files rather than one, because these are three different questions and a
single page made you scroll past two of them to reach the third. They are
generated from the same aggregation in one pass, so they cannot disagree.

THE ONE THING THIS FILE IS CAREFUL ABOUT

There are two data sources and they overlap. Adding them is the easiest possible
way to publish a wrong number, so they are never mixed:

  A. CLAUDE CODE      every machine ever scanned, per account, from totals.json
  B. EVERY CLI        only machines that have run sessions.py, per session,
                      from sessions.json — includes Claude Code again, plus
                      Gemini, Copilot, Codex, Kilo Code and Grok

B contains A for the machines in both. So a "grand total" that sums them
double-counts every Claude Code token on any machine that ran both scanners.
Every section below is labelled with which universe it belongs to, the two are
never added, and where they can be compared the document shows the comparison
rather than hiding it.
"""

import datetime
import json
import pathlib
import sys
import paths
from collections import defaultdict

from analyze_tokens import provider_of

FIELDS = ("input_tokens", "cache_creation_input_tokens",
          "cache_read_input_tokens", "output_tokens")

# Which company actually gets paid for a given provider tag.
COMPANY = {"anthropic": "Anthropic", "openai": "OpenAI", "google": "Google",
           "deepseek": "DeepSeek", "xai": "xAI", "meta": "Meta",
           "mistral": "Mistral", "qwen": "Alibaba", "moonshot": "Moonshot",
           "zhipu": "Zhipu", "copilot": "GitHub", "synthetic": "— (no API call)",
           "other": "— (unidentified)"}


# What company a CLI's name implies. Where the actual provider differs, the
# reports say so: ~/.my-claude is Claude Code the program wired to DeepSeek, so
# "claude 1.41B" in a token table is true about the interface and false about
# every token in it.
EXPECT = {"claude": "anthropic", "codex": "openai", "gemini": "google",
          "antigravity": "google", "grok": "xai"}
# copilot and kilocode are deliberately absent: both are multi-vendor by design,
# so there is no implied company for their name to contradict.


def human(n):
    for unit, size in (("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if n >= size:
            return f"{n / size:.2f}{unit}"
    return f"{int(n)}"


def hm(minutes):
    h, m = divmod(int(round(minutes or 0)), 60)
    return f"{h:,}h {m:02d}m" if h else f"{m}m"


def bar(part, whole, width=28):
    if not whole:
        return ""
    n = max(1, round(part / whole * width)) if part else 0
    return "█" * n + "·" * (width - n)


def load(root):
    machines, sessions, have, known, inv, prov_meta, ledger, statscache = [], [], set(), {}, {}, {}, [], []
    for mdir, f in paths.iter_machine_files(root, "totals.json"):
        try:
            m = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        m["folder"] = mdir.name
        machines.append(m)
    for mdir, f in paths.iter_machine_files(root, "sessions.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        name = d.get("machine", mdir.name)
        have.add(name)
        for r in d.get("readers") or []:
            known.setdefault(r["cli"], False)
            if r.get("installed"):
                known[r["cli"]] = True
        inv[name] = d.get("inventory") or []
        for e in d.get("history_ledger") or []:
            e["machine"] = name
            ledger.append(e)
        for e in d.get("stats_cache") or []:
            e["machine"] = name
            statscache.append(e)
        prov_meta[name] = {
            "scanner": d.get("scanner_version"),
            "scanned": d.get("generated_at"),
            # A reader that found the tool's storage and read nothing from it.
            # That is the signature of a scanner too old to know the layout.
            "gaps": [r["cli"] for r in (d.get("readers") or [])
                     if r.get("installed") and not r.get("sessions")],
        }
        for s in d.get("sessions", []):
            s["machine"] = name
            sessions.append(s)
    machines.sort(key=lambda m: -m["grand_total_tokens"])
    return machines, sessions, have, known, inv, prov_meta, ledger, statscache


def table(rows, headers, aligns=None):
    aligns = aligns or (["---"] * len(headers))
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(aligns) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return out


def token_split(t):
    """The four billed buckets, so a total is never just one opaque number."""
    return (t.get("input_tokens", 0), t.get("cache_creation_input_tokens", 0),
            t.get("cache_read_input_tokens", 0), t.get("output_tokens", 0))


def as_of(machines, statscache=None):
    """One line saying when an aggregate figure was true, and over what span.

    A fleet number is assembled from scans taken at different moments, so it is
    never true "now" — it is true as of a range. Printing the range under every
    collective figure stops it reading as a single instant.
    """
    times = sorted(m.get("generated_at") or "" for m in machines)
    times = [t for t in times if t]
    if not times:
        return "_scan times not recorded_"
    lo, hi = times[0][:19].replace("T", " "), times[-1][:19].replace("T", " ")
    miss = sum(1 for m in machines if not m.get("generated_at"))
    span = f"scans taken {lo}" + (f" .. {hi}" if lo != hi else "")
    if miss:
        span += f" · {miss} machine(s) with no recorded scan time"
    return f"_{span}_"


def relabel_profiles(machines, sessions, profile_labels):
    """Rename bare `user:<uid>` rows to what accounts.json says the profile is.

    BOTH sides, because two files carry that name. totals.json and sessions.json
    identify a login-less profile by the same truncated uid, and renaming only
    the totals side left machine_floor() looking `DeepSeek backend
    (~/.my-claude)` up in a session map still keyed `user:73ae64bf180b`. The
    lookup missed, `seen` fell back to totals.json's grand_total, and
    BY-COMPUTER.md published a floor of 520,497,793 for a profile whose
    sessions measure 529,474,038 — 8,976,245 BELOW the measured figure, which is
    the contradiction the comment in machine_floor() says the per-account
    session sum exists to prevent. HP Laptop Linux's floor was 32,260,807,673
    against a tree holding 32,269,783,918, and the fleet floor 81,881,141,212
    against 81,890,117,457.

    The uid in the account string is truncated, so match on prefix.
    """
    def label_for(name):
        if not isinstance(name, str) or not name.startswith("user:"):
            return None
        uid = name[5:]
        for full, lab in profile_labels.items():
            if full.startswith(uid):
                return lab
        return None

    for m in machines:
        for a in m.get("accounts", []):
            lab = label_for(a.get("account"))
            if lab:
                a["account"] = lab
    for x in sessions:
        lab = label_for(x.get("account"))
        if lab:
            x["account"] = lab


def machine_floor(m, sessions_here, statscache_here):
    """The most defensible single figure for one machine.

    Two sources describe Claude Code usage and neither contains the other:
    stats-cache.json accumulates from a profile's first session up to its own
    lastComputedDate and then stops; the transcripts hold whatever has not been
    deleted, which includes days after that date.

    Subtracting them is meaningless — an earlier version of this report did it
    and published a number that was arithmetic across two different windows.
    But CONCATENATING them is exact: the counter owns everything up to its end
    date, the transcripts own the days strictly after it, and no token is in
    both. That gives a real floor rather than an estimate.

    Profiles with no counter contribute only their surviving transcripts, and
    every non-Claude tool the same, because nothing else on disk remembers usage
    after its records are gone.

    Returns (floor, claude_part, other_part, detail-rows).
    """
    def val(v):
        return v if isinstance(v, int) else sum(v.values()) if isinstance(v, dict) else 0

    # Guard against malformed entries: a stats-cache list that somehow contains
    # a non-dict value (e.g. a string) would crash the dict comprehension with
    # TypeError. Silently skip non-dicts — they hold no usable counter data.
    # ONE COUNTER PER PROFILE, NOT PER ACCOUNT. Keying this dict by account
    # kept the LAST profile and silently dropped every earlier one. On the
    # machine this was found on, .claude (25,359,992,209 over 16,965 sessions)
    # and .claude-it (2,442,457,035 over 55) are the same login in two separate
    # installs, each with its own stats-cache over a DISJOINT set of sessions.
    # The account key collapsed them to the last, and the floor published
    # 5,873,327,825 against Anthropic's own 27,829,225,308 — 78.9% under the
    # one number this report is not allowed to be under.
    #
    # Distinct counters are summed. The SAME counter seen twice is not: the
    # inflation described above (30.9B -> 81.0B, one counter reached through
    # five mirror paths and added five times) is prevented by deduping on the
    # counter's CONTENT rather than on the profile's path, because a mirror
    # arrives under a different path and identical content.
    by_acct, _seen = {}, set()
    for e in statscache_here:
        if not isinstance(e, dict):
            continue
        ident = (e.get("account"), e.get("total"), e.get("last_computed"),
                 e.get("first_session"), e.get("sessions"), e.get("messages"))
        if ident in _seen:
            continue                      # a mirror of a counter already held
        _seen.add(ident)
        prev = by_acct.get(e["account"])
        if prev is None:
            by_acct[e["account"]] = dict(e)
            continue
        prev["total"] = prev.get("total", 0) + e.get("total", 0)
        # Two counters jointly own days only up to the LATER end date; taking
        # the earlier one would let `after` re-add transcript days the other
        # counter already covered. A floor may understate. It may not overstate.
        if (e.get("last_computed") or "") > (prev.get("last_computed") or ""):
            prev["last_computed"] = e.get("last_computed")
    # Per-account session totals, so a floor is never below what was measured.
    # totals.json and sessions.json are produced by different scanners moments
    # apart, so on a live machine they disagree slightly — taking the account's
    # grand_total alone put the MacBook's floor 80,005,100 BELOW its measured
    # figure, which is a contradiction in terms.
    per_acct_sess = defaultdict(int)
    for x in sessions_here:
        if x.get("cli") == "claude":
            per_acct_sess[x.get("account")] += x.get("total", 0)
    # Fold every profile belonging to one account together BEFORE the counter is
    # applied. One account can own several profiles — ~/.claude and a copy of it
    # elsewhere are both signed into the same login — but there is only ONE
    # stats-cache counter for that account. Iterating profiles and looking the
    # counter up per profile re-claimed it every time: on the machine this was
    # written on, five profiles resolved to one account and its 12,290,485,337
    # counter was added five times, inflating that machine's floor from 30.9B to
    # 81.0B and the fleet's from 66.5B to 166.2B. The counter is per account, so
    # it is applied per account, exactly once.
    merged = {}
    for a in m.get("accounts", []):
        g = merged.setdefault(a["account"], {"days": defaultdict(int), "grand": 0})
        for k, v in (a.get("by_day") or {}).items():
            g["days"][k] += val(v)
        g["grand"] += a["grand_total"]

    # A measured claude account that matches NO totals.json row is not zero, it
    # is unmatched: `per_acct_sess.get(name, 0)` below can never reach it, so it
    # is in no row of the table and in no floor. That is the shape the
    # profile-label bug took — `merged` held "DeepSeek backend (~/.my-claude)"
    # while per_acct_sess still held "user:73ae64bf180b", 529,474,038 measured
    # tokens went unconsulted, and the floor published 520,497,793. It is named
    # rather than folded in, because when the two names are the same profile
    # adding it would count that profile twice; the point is that a dropped
    # source must not look like a correct smaller number.
    # An account measured ONLY as orphans cannot be double-counted by folding
    # it in, and that is what makes this safe where the general case is not.
    # analyze_tokens reads transcripts; an orphan has none, so it is absent
    # from totals.json BY CONSTRUCTION rather than by a naming accident. The
    # ambiguous case the warning below exists for — one profile appearing
    # under two different labels — always has transcripts on at least one
    # side, so it never lands here and is still only reported.
    #
    # `source` is written by sessions.py from 2026-08-21. A folder scanned
    # before that has no such field, orphan_only is empty, and this behaves
    # exactly as it did — a stale folder is reported, never silently folded.
    per_acct_orphan = defaultdict(int)
    for x in sessions_here:
        if x.get("cli") == "claude" and x.get("source") == "claude-orphans":
            per_acct_orphan[x.get("account")] += x.get("total", 0)
    orphan_only = {k: v for k, v in per_acct_sess.items()
                   if k not in merged and v and per_acct_orphan.get(k) == v}

    stray = {k: v for k, v in per_acct_sess.items()
             if k not in merged and v and k not in orphan_only}
    if stray:
        print(f"WARNING {m.get('machine') or '?'}: "
              + "; ".join(f"{k!r} measures {v:,} claude tokens and matches no "
                          f"account in totals.json"
                          for k, v in sorted(stray.items(), key=lambda kv: -kv[1]))
              + " — those tokens are in no row of this machine's floor",
              file=sys.stderr)

    claude, rows = 0, []
    for name, part in sorted(orphan_only.items(), key=lambda kv: -kv[1]):
        # No counter and no by_day: the transcripts are gone. The measured
        # figure IS the floor for this account.
        rows.append((name, None, None, part, part))
        claude += part
    for name, g in merged.items():
        days = g["days"]
        # per_acct_sess is already an account-level sum, so it is compared
        # against the account's combined profiles, not against one of them.
        seen = max(g["grand"], per_acct_sess.get(name, 0))
        e = by_acct.get(name)
        if e and e.get("last_computed"):
            after = sum(v for k, v in days.items() if k > e["last_computed"])
            part = max(e["total"] + after, seen)
            rows.append((name, e["total"], e["last_computed"], after, part))
        else:
            part = seen
            rows.append((name, None, None, part, part))
        claude += part
    rows.sort(key=lambda r: -r[4])
    other = sum(x.get("total", 0) for x in sessions_here if x.get("cli") != "claude")
    return claude + other, claude, other, rows


def main():
    root = pathlib.Path(__file__).parent
    machines, S, scanned, known_clis, inv, prov_meta, ledger, statscache = load(root)
    if not machines:
        raise SystemExit("no */totals.json — run analyze_tokens.py first")

    _, profile_labels = load_registry(root)
    owners = cli_owners(root)
    # Attribute each non-Claude session to the account that owns that tool.
    # Sessions from a tool with no declared owner keep their placeholder, so an
    # unattributed CLI stays visible instead of being silently spread around.
    for x in S:
        c = x.get("cli")
        if c in owners:
            x["account"] = owners[c][0]
            x["account_evidence"] = owners[c][1]
    # S as well as machines: machine_floor() compares the two by account name.
    relabel_profiles(machines, S, profile_labels)

    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    grand_cc = sum(m["grand_total_tokens"] for m in machines)
    grand_cli = sum(s.get("total", 0) for s in S)

    # ---------- aggregate once, slice many times ----------
    acct = defaultdict(lambda: {"total": 0, "sessions": 0, "turns": 0,
                                "machines": defaultdict(int),
                                "providers": defaultdict(int),
                                "models": defaultdict(int),
                                "fields": [0, 0, 0, 0], "days": set()})
    prov = defaultdict(lambda: {"total": 0, "machines": defaultdict(int),
                                "accounts": defaultdict(int),
                                "models": defaultdict(int)})
    mach = defaultdict(lambda: {"total": 0, "accounts": defaultdict(int),
                                "providers": defaultdict(int),
                                "sessions": 0, "turns": 0})
    for m in machines:
        mn = m["machine"]
        mach[mn]["total"] = m["grand_total_tokens"]
        for a in m["accounts"]:
            name = a["account"]
            A = acct[name]
            A["total"] += a["grand_total"]
            A["sessions"] += a["sessions"]
            A["turns"] += a["turns"]
            A["machines"][mn] += a["grand_total"]
            A["days"] |= set(a.get("by_day", {}))
            for i, k in enumerate(FIELDS):
                A["fields"][i] += a["totals"][k]
            mach[mn]["accounts"][name] += a["grand_total"]
            mach[mn]["sessions"] += a["sessions"]
            mach[mn]["turns"] += a["turns"]
            for model, v in a.get("by_model", {}).items():
                n = sum(v[k] for k in FIELDS)
                p = provider_of(model)
                A["providers"][p] += n
                A["models"][model] += n
                prov[p]["total"] += n
                prov[p]["machines"][mn] += n
                prov[p]["accounts"][name] += n
                prov[p]["models"][model] += n
                mach[mn]["providers"][p] += n

    cli = defaultdict(lambda: {"total": 0, "sessions": 0, "min": 0.0,
                               "machines": defaultdict(int),
                               "providers": defaultdict(int)})
    cli_prov = defaultdict(lambda: {"total": 0, "min": 0.0, "sessions": 0,
                                    "clis": defaultdict(int)})
    for c in known_clis:
        cli[c]                 # seed at zero so a CLI cannot vanish from the page
    for s in S:
        c, p = s.get("cli", "?"), s.get("provider", "?")
        for tgt, key in ((cli[c], p),):
            tgt["total"] += s.get("total", 0)
            tgt["sessions"] += 1
            tgt["min"] += s.get("duration_min", 0)
            tgt["machines"][s["machine"]] += s.get("total", 0)
            tgt["providers"][key] += s.get("total", 0)
        cli_prov[p]["total"] += s.get("total", 0)
        cli_prov[p]["min"] += s.get("duration_min", 0)
        cli_prov[p]["sessions"] += 1
        cli_prov[p]["clis"][c] += s.get("total", 0)

    # ---------------- shared header ----------------
    def header(title, sub):
        h = [f"# {title}", "", f"_{sub}_", "",
             f"_Generated {now} by `stats_page.py`. Do not edit by hand._", "",
             f"**{grand_cc:,}** tokens of Claude Code across {len(machines)} "
             f"scanned computer(s) · **{grand_cli:,}** across every CLI on the "
             f"{len(scanned)} that ran `sessions.py`.", "",
             "Those two are not added: the second contains the first. See "
             "[BY-COMPUTER.md](BY-COMPUTER.md) for the reconciliation.", "",
             "Reports: [computers](BY-COMPUTER.md) · [accounts](BY-ACCOUNT.md) · "
             "[companies](BY-COMPANY.md) · [how it works](README.md)", "", "---", ""]
        return h

    ranked = sorted(acct.items(), key=lambda kv: -kv[1]["total"])
    provs = [p for p, _ in sorted(prov.items(), key=lambda kv: -kv[1]["total"])
             if prov[p]["total"]]

    # =============================================================== COMPUTERS
    L = header("By computer", "Every machine, and everything on it")
    L += ["## Totals", "", as_of(machines), "",
          "Each row carries the moment that computer was scanned. Machines are "
          "scanned independently, so a total is a snapshot of several different "
          "instants, never one.", "",
          "| Computer | Folder | Accounts | Tokens | Share | Scanned |",
          "|---|---|---:|---:|---:|---|"]
    for m in machines:
        w = m.get("generated_at")
        L.append(f"| **{m['machine']}** | `{m['folder']}/` | {len(m['accounts'])} | "
                 f"{m['grand_total_tokens']:,} | {m['grand_total_tokens']/grand_cc:.1%} | "
                 + (w[:19].replace("T", " ") if w else "⚠️ not recorded") + " |")
    L += [f"| **All** | | | **{grand_cc:,}** | 100% | |", ""]

    if S:
        cc_on_scanned = sum(m["grand_total_tokens"] for m in machines
                            if m["machine"] in scanned)
        claude_cli = sum(s.get("total", 0) for s in S if s.get("cli") == "claude")
        delta = cc_on_scanned - claude_cli
        L += ["### The two scopes, reconciled", "",
              "```",
              f"Claude Code, per account (totals.json)  : {cc_on_scanned:>16,}",
              f"Claude Code, per session (sessions.json): {claude_cli:>16,}",
              f"difference                              : {delta:>+16,}",
              f"non-Claude-Code CLIs, additional        : {grand_cli - claude_cli:>16,}",
              "```", ""]
        L += (["The first two agree exactly. They come from different code reading "
               "the same transcripts by different units, so a match is a real "
               "cross-check rather than a restatement. If this stops reading `+0`, "
               "one scanner has drifted.", ""] if delta == 0 else
              [f"**These should agree and differ by {abs(delta):,}.** The usual "
               "innocent cause is a session still being written during the scan; "
               "anything larger is a bug worth finding before quoting these.", ""])

    for m in machines:
        mn = m["machine"]
        M = mach[mn]
        here = [s for s in S if s["machine"] == mn]
        meta0 = prov_meta.get(mn) or {}
        when = m.get("generated_at") or meta0.get("scanned")
        sess_when = meta0.get("scanned")
        stamp = (f"scanned **{when[:19].replace('T', ' ')}**" if when
                 else "**scan time not recorded** (pre-timestamp scanner)")
        if sess_when and when and sess_when[:19] != when[:19]:
            stamp += f" · sessions {sess_when[:19].replace('T', ' ')}"
        L += ["---", "", f"## {mn}", "", stamp, "",
              f"`{m['folder']}/` · {len(m['accounts'])} account(s) · "
              f"{M['sessions']:,} sessions · {M['turns']:,} turns · "
              f"**{M['total']:,} tokens** ({M['total']/grand_cc:.1%} of all Claude Code)"]
        meta = prov_meta.get(mn) or {}
        vers = {v.get("scanner") for v in prov_meta.values() if v.get("scanner")}
        newest = max(vers) if vers else None
        if meta:
            note = []
            if not meta.get("scanner"):
                note.append("scanned before the scanner recorded its version")
            elif newest and meta["scanner"] != newest:
                note.append(f"scanner `{meta['scanner']}`, fleet is on `{newest}`")
            for g in meta.get("gaps") or []:
                note.append(f"**{g} is installed here and read 0 sessions** — its "
                            "usage is missing from every total below")
            if note:
                L += ["", "> ⚠️ " + " · ".join(note) + ". These figures are a floor "
                          "for this machine, not a total. `update.py` on it settles it."]
        hw = (m.get("hw") or {}).get("hardware") or {}
        if hw:
            bits = [hw.get("chip"), f"{hw['cpu_logical']} cores" if hw.get("cpu_logical") else None,
                    f"{hw['memory_gb']:g} GB" if hw.get("memory_gb") else None, hw.get("os")]
            L += ["", " · ".join(str(b) for b in bits if b)]
        L += ["", "### Accounts on this computer", "",
              "| Account | Tokens | Share of machine |", "|---|---:|---:|"]
        for a, v in sorted(M["accounts"].items(), key=lambda kv: -kv[1]):
            L.append(f"| {a} | {v:,} | {v/M['total']:.1%} |" if M["total"] else f"| {a} | {v:,} | — |")
        L += ["", "### Companies on this computer", "", "| Company | Tokens | Share |",
              "|---|---:|---:|"]
        for p, v in sorted(M["providers"].items(), key=lambda kv: -kv[1]):
            L.append(f"| {COMPANY.get(p, p)} | {v:,} | {v/M['total']:.1%} |")
        if here:
            per = defaultdict(lambda: [0, 0, 0.0])
            for s in here:
                e = per[s.get("cli", "?")]
                e[0] += 1
                e[1] += s.get("total", 0)
                e[2] += s.get("duration_min", 0)
            L += ["", "### CLIs on this computer", "",
                  "| CLI | Sessions | Active | Tokens |", "|---|---:|---:|---:|"]
            for c, (n, t, mm) in sorted(per.items(), key=lambda kv: -kv[1][1]):
                L.append(f"| {c} | {n:,} | {hm(mm)} | {t:,} |")
        else:
            L += ["", "> `sessions.py` has not run here — only Claude Code is counted."]
        tools = inv.get(mn) or []
        if tools:
            L += ["", f"### Installed here — {len(tools)} tool(s)", "",
                  "Presence is separate from usage: a tool with no token column is "
                  "installed and not counted, which is different from unused.", "",
                  "| Tool | Kind | Counted | Sessions | Tokens | Usage |",
                  "|---|---|---|---:|---:|---|"]
            order = {"cli": 0, "agent": 1, "editor": 2, "runtime": 3}
            for t in sorted(tools, key=lambda t: (order.get(t.get("kind"), 9),
                                                  -(t.get("tokens") or 0))):
                if t.get("counted"):
                    L.append(f"| {t['tool']} | {t['kind']} | yes | "
                             f"{t.get('sessions_count', 0):,} | {t.get('tokens', 0):,} | "
                             f"{(t.get('first_used') or '?')[:10]} → "
                             f"{(t.get('last_used') or '?')[:10]} |")
                else:
                    when = (f"{t.get('launches')} launches, {t.get('workspaces', 0)} "
                            f"workspaces, {t.get('active_days', 0)} day(s): "
                            f"{(t.get('first_launch') or '?')[:10]} → "
                            f"{(t.get('last_launch') or '?')[:10]}"
                            if t.get("launches") else
                            (f"last touched {(t.get('last_seen') or '')[:10]}"
                             if t.get("last_seen") else "installed"))
                    why = t.get("no_tokens_because")
                    L.append(f"| {t['tool']} | {t['kind']} | "
                             + (f"no — {why}" if why else "—") + f" | — | — | {when} |")
        L.append("")

    unbilled = [x for x in S if x.get("billed") is False]
    if unbilled:
        ub = sum(x.get("total", 0) for x in unbilled)
        per = defaultdict(lambda: [0, 0])
        for x in unbilled:
            e = per[(x.get("cli"), x.get("model"))]
            e[0] += 1
            e[1] += x.get("total", 0)
        L += ["---", "", "## Tokens nobody was billed for", "",
              f"**{ub:,} tokens** across {len(unbilled):,} sessions ran on this "
              "hardware. They are counted in every total in these reports, because a "
              "token is a token regardless of who pays for it. What differs is the "
              "invoice, and there isn't one.", "",
              "That is a third dimension, independent of the other two:", "",
              "| Dimension | Question | Example |",
              "|---|---|---|",
              "| `cli` | which tool did you pay for | Copilot running a Claude model is GitHub spend |",
              "| `provider` | whose model actually ran | …and Anthropic service |",
              "| `billed` | did money change hands | Ollama running llama is neither |", "",
              "| CLI | Model | Sessions | Tokens |", "|---|---|---:|---:|"]
        for (c, m), (n, t) in sorted(per.items(), key=lambda kv: -kv[1][1]):
            L.append(f"| {c} | `{m}` | {n:,} | {t:,} |")
        L += ["",
              f"Every figure elsewhere includes these. To read spend rather than "
              f"volume, subtract them: {sum(x.get('total',0) for x in S) - ub:,} of the "
              f"{sum(x.get('total',0) for x in S):,} total was billed to someone.", ""]

    # Per-machine floors, and the fleet floor built from them.
    floors = {}
    for m in machines:
        mn = m["machine"]
        floors[mn] = machine_floor(
            m, [x for x in S if x.get("machine") == mn],
            [e for e in statscache if e.get("machine") == mn])
    fleet_floor = sum(v[0] for v in floors.values())
    L += ["---", "", "## The floor: the most defensible figure per machine", "",
          f"**{fleet_floor:,} tokens across {len(floors)} scanned computer(s).**", "",
          as_of(machines), "",
          "Two sources describe Claude Code usage and neither contains the other. "
          "`stats-cache.json` accumulates from a profile's first session to its own "
          "`lastComputedDate` and stops; the transcripts hold whatever has not been "
          "deleted, which includes days after that date.", "",
          "Subtracting them is meaningless. **Concatenating them is exact** — the "
          "counter owns everything up to its end date, the transcripts own the days "
          "strictly after it, and no token falls in both. Profiles with no counter, "
          "and every non-Claude tool, contribute only their surviving records, because "
          "nothing else on disk remembers usage once its records are gone.", "",
          "| Computer | Claude Code | Other tools | Floor | Measured on disk |",
          "|---|---:|---:|---:|---:|"]
    for mn, (fl, cl, oth, _rows) in sorted(floors.items(), key=lambda kv: -kv[1][0]):
        meas = sum(x.get("total", 0) for x in S if x.get("machine") == mn) or \
               next((m["grand_total_tokens"] for m in machines if m["machine"] == mn), 0)
        L.append(f"| {mn} | {cl:,} | {oth:,} | **{fl:,}** | {meas:,} |")
    L.append(f"| **All** | | | **{fleet_floor:,}** | |")
    L += ["", "It is a floor and not a total for three reasons, all measured rather "
              "than assumed: profiles without a counter lose anything pruned before "
              "the scan; the counter's own window has gaps where transcripts were "
              "deleted before it froze; and no non-Claude tool keeps a counter at all.", ""]
    for mn, (fl, cl, oth, rows) in sorted(floors.items(), key=lambda kv: -kv[1][0]):
        if not any(r[1] for r in rows):
            continue
        L += [f"<details><summary>{mn} — how its floor is built</summary>", "",
              "| Account | Counter | Counter ends | Transcripts after | Floor |",
              "|---|---:|---|---:|---:|"]
        for name, ctr, end, after, part in rows:
            L.append(f"| {name} | " + (f"{ctr:,}" if ctr else "_none_") + " | "
                     + (end or "—") + f" | {after:,} | {part:,} |")
        L += ["", "</details>", ""]

    if statscache:
        acct_tot = defaultdict(int)
        for m in machines:
            for a in m["accounts"]:
                acct_tot[(m["machine"], a["account"])] += a["grand_total"]
        rows, gap = [], 0
        for e in sorted(statscache, key=lambda e: -e["total"]):
            t = acct_tot.get((e["machine"], e["account"]), 0)
            d_ = e["total"] - t
            gap += max(0, d_)
            rows.append((e, t, d_))
        L += ["---", "", "## Claude Code's own counter, versus the transcripts", "",
              "Every profile keeps `stats-cache.json`. It is not a transcript, so the "
              "cleanup sweep never touches it, and it accumulates from that profile's "
              "first session — including sessions whose transcripts were deleted months "
              "ago.", "",
              "| Profile | Account | Own counter | Counter covers | From transcripts |",
              "|---|---|---:|---|---:|"]
        for e, t, d_ in rows:
            L.append(f"| `{e['profile']}` | {e['account']} | {e['total']:,} | "
                     f"{e.get('first_session') or '?'} → {e.get('last_computed') or '?'}"
                     f" | {t:,} |")
        L += ["",
              "**Do not subtract these columns.** The two cover different periods: the "
              "counter runs from the first session to its own `lastComputedDate` and "
              "then stops, while the transcripts hold whatever has not expired, which "
              "includes days after that date. Neither contains the other — each holds "
              "usage the other lacks — so their difference is not a quantity of "
              "anything.", "",
              "An earlier version of this report published exactly that subtraction as "
              "\"tokens the transcripts can no longer see\". It was arithmetic on two "
              "incomparable windows, and it is removed rather than reworded.", "",
              "The overlap cannot be resolved either: the cache's only per-day "
              "breakdown is input+output, excluding cache reads, which are around 95% "
              "of the volume. What the comparison honestly shows is that far more "
              "usage happened than the surviving transcripts record, with both figures "
              "and both windows stated so a reader can see the shape of the gap "
              "without being handed a false number for it.", ""]

    if ledger:
        lost = [e for e in ledger if not e.get("transcript")]
        days = sorted(e["first_day"] for e in ledger if e.get("first_day"))
        tdays = sorted((x.get("start") or "")[:10] for x in S
                       if x.get("cli") == "claude" and x.get("start"))
        L += ["---", "", "## Sessions that no longer have a transcript", "",
              f"**{len(ledger):,} Claude Code sessions have existed across the scanned "
              f"machines. {len(lost):,} of them — {len(lost)/len(ledger):.0%} — no longer "
              "have a transcript on disk.**", "",
              "Claude Code deletes transcripts older than `cleanupPeriodDays`, but it "
              "does not delete `history.jsonl`. That file records one entry per prompt "
              "with a session id, a timestamp and a project, and it reaches much further "
              "back than the transcripts do:", "",
              "```",
              f"ledger reaches back to     {days[0] if days else '?'}",
              f"oldest surviving transcript {tdays[0] if tdays else '?'}",
              "```", "",
              "It carries **no token counts**, so a lost session's cost is gone for good. "
              "What survives is proof the session happened, when, and in which project — "
              "which turns an unquantified loss into a number. The ledger is committed "
              "with each scan, so it accumulates permanently even as its own source "
              "expires. Prompt text is deliberately not stored.", "",
              "| Account | Sessions ever | Transcript gone | Span |",
              "|---|---:|---:|---|"]
        per = defaultdict(lambda: [0, 0, [], []])
        for e in ledger:
            a = per[e.get("account") or "?"]
            a[0] += 1
            a[1] += 0 if e.get("transcript") else 1
            if e.get("first_day"):
                a[2].append(e["first_day"])
                a[3].append(e.get("last_day") or e["first_day"])
        for a, (n, l, f0, f1) in sorted(per.items(), key=lambda kv: -kv[1][0]):
            L.append(f"| {a} | {n:,} | {l:,} | "
                     + (f"{min(f0)} → {max(f1)}" if f0 else "—") + " |")
        L.append("")

    L += ["---", "", "## Cross-tabs", "", as_of(machines), "",
          "### Computer x company", "",
          "| Computer | " + " | ".join(COMPANY.get(p, p) for p in provs) + " | Total |",
          "|---" * (len(provs) + 2) + "|"]
    for m in machines:
        row = mach[m["machine"]]["providers"]
        L.append(f"| {m['machine']} | "
                 + " | ".join(human(row.get(p, 0)) if row.get(p) else "—" for p in provs)
                 + f" | **{m['grand_total_tokens']:,}** |")
    L.append("| **All** | " + " | ".join(f"**{human(prov[p]['total'])}**" for p in provs)
             + f" | **{grand_cc:,}** |")
    if S:
        clis = [c for c, _ in sorted(cli.items(), key=lambda kv: -kv[1]["total"])]
        L += ["", "### Computer x CLI", "",
              "| Computer | " + " | ".join(clis) + " | Total |",
              "|---" * (len(clis) + 2) + "|"]
        for mn in sorted(scanned):
            row = {c: cli[c]["machines"].get(mn, 0) for c in clis}
            L.append(f"| {mn} | " + " | ".join(human(row[c]) if row[c] else "—" for c in clis)
                     + f" | **{sum(row.values()):,}** |")
        L.append("| **All** | " + " | ".join(f"**{human(cli[c]['total'])}**" for c in clis)
                 + f" | **{grand_cli:,}** |")

    if S:
        mins = sum(s.get("duration_min", 0) for s in S)
        withtight = [s for s in S if "duration_tight_min" in s]
        tight = sum(s["duration_tight_min"] for s in withtight)
        loose = sum(s.get("duration_min", 0) for s in withtight)
        L += ["", "---", "", "## Sessions", "",
              f"{len(S):,} sessions · {hm(mins)} active · {grand_cli:,} tokens", "",
              "Gaps over 15 minutes are treated as idle and dropped. First-to-last "
              "timestamp instead produced a *436-hour day* on this data.", ""]
        if withtight:
            L += [f"**The 15 minutes is a judgement call.** On the {len(withtight):,} "
                  f"session(s) measured both ways, counting only gaps under one minute "
                  f"gives **{hm(tight)}** against **{hm(loose)}**. The {hm(loose-tight)} "
                  "between is where reading output and walking away look identical. "
                  "Read it as a range."
                  + ("" if len(withtight) == len(S) else
                     f" The other {len(S)-len(withtight):,} predate this and are "
                     "counted only at fifteen minutes."), ""]
        for label, key in (("Twenty longest", "duration_min"), ("Twenty heaviest", "total")):
            L += [f"### {label}", "",
                  "| When | Computer | CLI | Active | Tokens | Turns | Model |",
                  "|---|---|---|---:|---:|---:|---|"]
            for s in sorted(S, key=lambda s: s.get(key, 0), reverse=True)[:20]:
                L.append(f"| {(s.get('start') or '?')[:10]} | {s['machine']} | "
                         f"{s.get('cli')} | {hm(s.get('duration_min', 0))} | "
                         f"{s.get('total', 0):,} | {s.get('turns', 0):,} | "
                         f"`{s.get('model', '?')}` |")
            L.append("")
        per_day = defaultdict(lambda: [0, 0.0])
        for s in S:
            if s.get("start"):
                e = per_day[s["start"][:10]]
                e[0] += s.get("total", 0)
                e[1] += s.get("duration_min", 0)
        L += ["### Busiest days", "", "| Day | Tokens | Active |", "|---|---:|---:|"]
        for d, (t, mm) in sorted(per_day.items(), key=lambda kv: -kv[1][0])[:15]:
            L.append(f"| {d} | {t:,} | {hm(mm)} |")
        L += ["", "Session-hours can exceed 24 in a day: parallel agents overlap, and "
                  "that overlap is real work, so it is summed rather than clamped.", ""]
    (paths.human(root) / "BY-COMPUTER.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    # ================================================================ ACCOUNTS
    L = header("By account", "What each login spent, across every computer")
    L += [as_of(machines), "",
          "The per-account total across computers is the number that matters: the "
          "same login gets driven from several machines and no machine can see "
          "another's sessions.", "",
          "| Account | Tokens | Share | Computers | Sessions | Turns | |",
          "|---|---:|---:|---:|---:|---:|---|"]
    for n, a in ranked:
        L.append(f"| **{n}** | {a['total']:,} | {a['total']/grand_cc:.1%} | "
                 f"{len(a['machines'])} | {a['sessions']:,} | {a['turns']:,} | "
                 f"{bar(a['total'], grand_cc)} |")
    L += [f"| **All** | **{grand_cc:,}** | 100% | | | | |", ""]

    # Every CLI's usage, folded onto the account that owns the tool.
    per_email = defaultdict(lambda: {"total": 0, "sessions": 0, "clis": defaultdict(int),
                                     "evidence": {}})
    unowned = defaultdict(lambda: [0, 0])
    for x in S:
        a = x.get("account") or "?"
        if "@" in a:
            e = per_email[a]
            e["total"] += x.get("total", 0)
            e["sessions"] += 1
            e["clis"][(x.get("cli"), x.get("provider"))] += x.get("total", 0)
            if x.get("account_evidence"):
                e["evidence"][x.get("cli")] = x["account_evidence"]
        else:
            u = unowned[(x.get("cli"), x.get("provider"))]
            u[0] += 1
            u[1] += x.get("total", 0)
    if per_email:
        tot = sum(v["total"] for v in per_email.values())
        L += ["## Across every CLI, by account", "",
              "The table above is Claude Code only, because it is the one tool that "
              "writes its account email to disk. This one folds in every other CLI "
              "using the ownership declared in "
              "[`accounts.json`](accounts.json).", "",
              "| Account | Tokens | Sessions | Via |", "|---|---:|---:|---|"]
        for e, v in sorted(per_email.items(), key=lambda kv: -kv[1]["total"]):
            via = ", ".join(
                (f"{c}" + (f" → {COMPANY.get(pv, pv)}"
                          if c in EXPECT and pv and pv != EXPECT[c] else "")
                 + f" {human(t)}"
                 + (f" _{v['evidence'].get(c)}_" if c in v["evidence"] else ""))
                for (c, pv), t in sorted(v["clis"].items(), key=lambda kv: -kv[1]) if t)
            L.append(f"| **{e}** | {v['total']:,} | {v['sessions']:,} | {via} |")
        L += [f"| **All attributed** | **{tot:,}** | | |", ""]
        L += ["`file` means the email was read out of that tool's own account file. "
              "`owner` means it was stated by the account holder and cannot be "
              "checked against anything on disk. Claude Code rows carry neither "
              "because the email is in the session record itself.", ""]
    if unowned:
        s_tot = sum(v[1] for v in unowned.values())
        L += [f"> ⚠️ **{s_tot:,} tokens have no account.** These tools record no "
              "identity on disk and none is declared for them yet:", "",
              "| CLI | Company that served it | Sessions | Tokens |",
              "|---|---|---:|---:|"]
        for (c, pv), (n, t) in sorted(unowned.items(), key=lambda kv: -kv[1][1]):
            mark = " ⚠️" if c in EXPECT and pv and pv != EXPECT[c] else ""
            L.append(f"| {c}{mark} | {COMPANY.get(pv, pv)} | {n:,} | {t:,} |")
        L += ["", "⚠️ marks a row where the tool's name and the company that served "
                  "the tokens disagree. `claude` served by DeepSeek is a Claude Code "
                  "build pointed at a DeepSeek backend: the interface is Claude "
                  "Code, every token is DeepSeek, and Anthropic was paid nothing. "
                  "Reading the CLI column alone would count it as Claude usage.", ""]
        L += ["", "Add a `services` entry to the right account in "
              "`accounts.json` to fold any of these in. They are left under a "
              "placeholder rather than split across accounts by proportion, "
              "because that would invent numbers that look measured.", ""]

    known_emails, _ = load_registry(root)
    seen = " ".join(list(dict(ranked)) + list(per_email)).lower()
    missing = [e for e in known_emails if e.get("email", "").lower() not in seen]
    if missing:
        L += ["> ⚠️ **Known account(s) with no usage found anywhere:** "
              + ", ".join(f"`{e['email']}`" for e in missing) + ".", ""]

    L += ["### Account x computer", "",
          "| Account | " + " | ".join(m["machine"] for m in machines) + " | Total |",
          "|---" * (len(machines) + 2) + "|"]
    for n, a in ranked:
        L.append(f"| {n} | " + " | ".join(
            human(a["machines"].get(m["machine"], 0)) if a["machines"].get(m["machine"])
            else "—" for m in machines) + f" | **{a['total']:,}** |")
    L.append("| **All** | " + " | ".join(f"**{human(m['grand_total_tokens'])}**"
                                         for m in machines) + f" | **{grand_cc:,}** |")
    L.append("")

    for n, a in ranked:
        L += ["---", "", f"## {n}", "",
              f"**{a['total']:,} tokens** ({a['total']/grand_cc:.1%}) · "
              f"{a['sessions']:,} sessions · {a['turns']:,} turns · "
              f"{len(a['days'])} active days", "",
              "| Computer | Tokens | Share of this account |", "|---|---:|---:|"]
        for mn, v in sorted(a["machines"].items(), key=lambda kv: -kv[1]):
            L.append(f"| {mn} | {v:,} | {v/a['total']:.1%} |" if a["total"]
                     else f"| {mn} | {v:,} | — |")
        L += ["", "| Company | Tokens |", "|---|---:|"]
        for p, v in sorted(a["providers"].items(), key=lambda kv: -kv[1]):
            L.append(f"| {COMPANY.get(p, p)} | {v:,} |")
        L += ["", "| Model | Tokens |", "|---|---:|"]
        for mo, v in sorted(a["models"].items(), key=lambda kv: -kv[1])[:12]:
            L.append(f"| `{mo}` | {v:,} |")
        i, cw, cr, o = a["fields"]
        L += ["", "| Input | Cache write | Cache read | Output |",
              "|---:|---:|---:|---:|",
              f"| {i:,} | {cw:,} | {cr:,} | {o:,} |", "",
              "All four are billed. Cache reads dominate because every turn re-reads "
              "the whole conversation, so a session's context is billed once per turn.", ""]
    # Computer-first. The sections above are account-first; this answers "which
    # logins are on the MacBook", which is the question after a machine scans.
    peracct = defaultdict(lambda: defaultdict(int))
    for m in machines:
        for a in m.get("accounts", []):
            peracct[m["machine"]][a["account"]] += a.get("grand_total", 0)
    if peracct:
        L += ["---", "", "## Each computer", "",
              "_The same accounts, grouped by machine. One login is usually "
              "driven from several computers, and no computer can see another's "
              "sessions — which is why the account totals above exist at all._", ""]
        for mn in sorted(peracct, key=lambda n: -sum(peracct[n].values())):
            tot_ = sum(peracct[mn].values())
            L += [f"### {mn}", "",
                  f"**{tot_:,} tokens** across {len(peracct[mn])} login(s)", "",
                  "| Account | Tokens | Share |", "|---|---:|---:|"]
            for an, v in sorted(peracct[mn].items(), key=lambda kv: -kv[1]):
                L.append(f"| {an} | {v:,} | {v/max(1,tot_)*100:5.1f}% |")
            L.append("")
    (paths.human(root) / "BY-ACCOUNT.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    # =============================================================== COMPANIES
    L = header("By company", "What each vendor was actually paid for")
    L += [as_of(machines), "",
          "Claude Code can be pointed at a non-Anthropic backend and the transcripts "
          "look identical, so a raw total is not an Anthropic total. Split on the "
          "model id.", "",
          "| Company | Tag | Tokens | Share | |", "|---|---|---:|---:|---|"]
    for p in provs:
        L.append(f"| **{COMPANY.get(p, p)}** | `{p}` | {prov[p]['total']:,} | "
                 f"{prov[p]['total']/grand_cc:.1%} | {bar(prov[p]['total'], grand_cc)} |")
    L += [f"| **All** | | **{grand_cc:,}** | 100% | |", ""]

    if S:
        L += ["### Who served it, versus who was paid for the tool", "",
              "Different questions. Copilot runs Claude models: that is GitHub spend "
              "and Anthropic service.", "",
              "| Company | Sessions | Active | Tokens | Via |", "|---|---:|---:|---:|---|"]
        for p, d in sorted(cli_prov.items(), key=lambda kv: -kv[1]["total"]):
            via = ", ".join(f"{c} {human(v)}" for c, v in
                            sorted(d["clis"].items(), key=lambda kv: -kv[1]) if v)
            L.append(f"| {COMPANY.get(p, p)} | {d['sessions']:,} | {hm(d['min'])} | "
                     f"{d['total']:,} | {via or '—'} |")
        L.append("")

    for p in provs:
        d = prov[p]
        L += ["---", "", f"## {COMPANY.get(p, p)}", "",
              f"**{d['total']:,} tokens** ({d['total']/grand_cc:.1%} of all Claude Code)",
              "", "| Model | Tokens |", "|---|---:|"]
        for mo, v in sorted(d["models"].items(), key=lambda kv: -kv[1]):
            L.append(f"| `{mo}` | {v:,} |")
        L += ["", "| Computer | Tokens |", "|---|---:|"]
        for mn, v in sorted(d["machines"].items(), key=lambda kv: -kv[1]):
            L.append(f"| {mn} | {v:,} |")
        L += ["", "| Account | Tokens |", "|---|---:|"]
        for an, v in sorted(d["accounts"].items(), key=lambda kv: -kv[1]):
            L.append(f"| {an} | {v:,} |")
        L.append("")
    # The same data, computer-first. The sections above are company-first and
    # list machines inside each; that answers "who did Anthropic serve" but not
    # "what did the MacBook use", and the second is the question asked when a
    # machine has just been scanned. A new computer adds a section here.
    percomp = defaultdict(lambda: defaultdict(int))
    for p_, d_ in prov.items():
        for mn, v in d_["machines"].items():
            percomp[mn][p_] += v
    if percomp:
        L += ["---", "", "## Each computer", "",
              "_The same tokens, grouped by machine instead of by vendor._", ""]
        for mn in sorted(percomp, key=lambda n: -sum(percomp[n].values())):
            tot_ = sum(percomp[mn].values())
            L += [f"### {mn}", "",
                  f"**{tot_:,} tokens** from {len(percomp[mn])} company(s)", "",
                  "| Company | Tokens | Share |", "|---|---:|---:|"]
            for p_, v in sorted(percomp[mn].items(), key=lambda kv: -kv[1]):
                L.append(f"| {COMPANY.get(p_, p_)} | {v:,} | {v/max(1,tot_)*100:5.1f}% |")
            L.append("")
    (paths.human(root) / "BY-COMPANY.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    print(f"wrote BY-COMPUTER.md, BY-ACCOUNT.md, BY-COMPANY.md — "
          f"{len(machines)} computers, {len(acct)} accounts, {len(provs)} companies, "
          f"{len(cli)} CLIs, {len(S):,} sessions")


def load_registry(root):
    """Known accounts, and labels for the profiles that have no email.

    The same file combine.py reads, so a profile is named identically in every
    report. Two reports calling the same thing `user:73ae64bf180b` and "DeepSeek
    backend" would be two reports the reader has to reconcile by hand.
    """
    f = root / "accounts.json"
    if not f.is_file():
        return [], {}
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return [], {}
    labels = {x["userID"]: x.get("label") or x["userID"]
              for x in (d.get("profiles") or []) if x.get("userID")}
    return (d.get("accounts") or []), labels


def cli_owners(root):
    """{cli: (email, evidence)} — who each non-Claude tool belongs to.

    Only Claude Code writes its account email to disk. Everything else records
    no identity at all, so this map is the only thing that can put 5.56 billion
    tokens - 11.9% of everything measured - under the person who paid for them
    instead of under a placeholder like "grok (local)".
    """
    f = root / "accounts.json"
    if not f.is_file():
        return {}
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out = {}
    for a in d.get("accounts") or []:
        for svc in a.get("services") or []:
            if svc.get("cli") and svc["cli"] != "claude":
                out[svc["cli"]] = (a["email"], svc.get("evidence", "?"))
    return out


if __name__ == "__main__":
    main()
