#!/usr/bin/env python3
"""Reduce a machine's transcripts to one small file per 30-day window.

    python3 digest.py                       # from this machine's live profiles
    python3 digest.py --corpus ~/deadreckon-record/<machine>
    python3 digest.py --days 30 --out digests

Written because the corpus outgrew what can be moved around. It is ~480 MB for
one computer and roughly a gigabyte for three; a plain `git clone` of it failed
here with `fatal: fetch-pack: invalid index-pack output`, and the blobless
fallback then failed to lazily fetch during a merge. Anything that needs the
whole corpus to answer a question does not scale past a few machines.

Almost nothing needs the whole corpus. The reports want totals, rankings and
distributions; those are additive over a window and survive being computed once.
So each window is reduced to a few KB of counts here, committed alongside the
numbers, and read instead of the transcripts.

WHAT IS KEPT, AND WHY IT IS SAFE TO COMMIT

Counts and distributions, never text. Message *lengths* rather than messages,
tool *names* rather than arguments, the first word of a user turn rather than
the turn. That is enough to characterise how a machine is used — rhythm,
directness, which tools, how often work gets corrected — without carrying any
content, which is the whole reason the corpus is a separate private repository
in the first place. A digest is meant to be cheap to pull; it must not quietly
become a second copy of the conversations.

WHAT IT CANNOT REPLACE

The corpus itself, for anything that needs the actual text. Digests are lossy on
purpose. `deadreckon-record` stays the source of truth and `count_corpus.py` still
cross-checks the scanner against it; this is a smaller thing to carry around,
not a replacement for having the records.
"""

import argparse
import collections
import datetime
import json
import pathlib
import re

FIELDS = ("input_tokens", "cache_creation_input_tokens",
          "cache_read_input_tokens", "output_tokens")

# Markers that a turn is pushing back on the previous answer. Deliberately crude
# and deliberately counted rather than quoted: the useful signal is how often
# work gets corrected, not what the correction said.
PUSHBACK = re.compile(
    r"\b(no|nope|wrong|incorrect|actually|instead|revert|undo|stop|"
    r"don'?t|shouldn'?t|why (did|are|is)|that'?s not)\b", re.I)

# A "user" turn in a transcript is not always something a person typed. The
# harness injects background-task notifications, interrupt notices, hook output
# and system reminders under the same role. Counting those as typed input put
# `tasknotification` and `request` among the most common opening words on this
# machine — 99 turns of style signal that no human wrote. Style is meant to
# describe the person, so these are excluded from every style measure.
INJECTED = re.compile(
    r"^\s*(\[Request interrupted|\[SYSTEM NOTIFICATION|<task-notification|"
    r"<system-reminder|<command-name|<local-command|Caveat: The messages below|"
    r"This is how Claude Code surfaces|UserPromptSubmit hook|"
    r"SessionStart hook|\[System\])", re.I)


def text_of(msg):
    c = msg.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return " ".join(b.get("text", "") for b in c
                        if isinstance(b, dict) and b.get("type") == "text")
    return ""


def tools_in(msg):
    c = msg.get("content")
    if not isinstance(c, list):
        return []
    return [b.get("name") for b in c
            if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name")]


def window_of(stamp, days, epoch):
    """Which fixed-width bucket a timestamp falls in, as an ISO start date."""
    try:
        d = datetime.date.fromisoformat(stamp[:10])
    except Exception:
        return None
    n = (d - epoch).days // days
    return (epoch + datetime.timedelta(days=n * days)).isoformat()


def blank():
    return {
        "tokens": dict.fromkeys(FIELDS, 0),
        "by_model": collections.defaultdict(int),
        "by_project": collections.defaultdict(int),
        "sessions": set(), "assistant_turns": 0, "user_turns": 0,
        "user_chars": [], "assistant_chars": [],
        "tools": collections.defaultdict(int),
        "hours": collections.defaultdict(int),
        "pushbacks": 0, "first_words": collections.defaultdict(int),
        "injected_turns": 0,
        "first_seen": None, "last_seen": None,
    }


def scan(trees, days, epoch):
    wins = collections.defaultdict(blank)
    seen_uuid = set()
    for tree in trees:
        for f in sorted(tree.rglob("*.jsonl")):
            project = f.parent.name
            for line in f.open(encoding="utf-8", errors="ignore"):
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                ts = o.get("timestamp") or ""
                w = window_of(ts, days, epoch)
                if not w:
                    continue
                uid = o.get("uuid")
                if uid:
                    if uid in seen_uuid:
                        continue
                    seen_uuid.add(uid)
                W = wins[w]
                if W["first_seen"] is None or ts < W["first_seen"]:
                    W["first_seen"] = ts
                if W["last_seen"] is None or ts > W["last_seen"]:
                    W["last_seen"] = ts
                if o.get("sessionId"):
                    W["sessions"].add(o["sessionId"])
                try:
                    W["hours"][int(ts[11:13])] += 1
                except Exception:
                    pass

                msg = o.get("message") or {}
                role = msg.get("role") or o.get("type")
                usage = msg.get("usage")
                if isinstance(usage, dict):
                    for k in FIELDS:
                        v = usage.get(k)
                        if isinstance(v, int):
                            W["tokens"][k] += v
                    tot = sum(v for k, v in usage.items()
                              if k in FIELDS and isinstance(v, int))
                    W["by_model"][msg.get("model") or "unknown"] += tot
                    W["by_project"][project] += tot

                if role == "assistant":
                    W["assistant_turns"] += 1
                    txt = text_of(msg)
                    # Only turns that actually said something. A tool-only turn
                    # has no text, and including it as length 0 dragged the
                    # median to 0 — which reads as "says nothing" rather than
                    # "acted instead of talking".
                    if txt.strip():
                        W["assistant_chars"].append(len(txt))
                    for t in tools_in(msg):
                        W["tools"][t] += 1
                elif role == "user":
                    t = text_of(msg)
                    if not t.strip():
                        continue          # tool results, not typed input
                    if INJECTED.match(t):
                        W["injected_turns"] += 1
                        continue          # harness-generated, not the person
                    W["user_turns"] += 1
                    W["user_chars"].append(len(t))
                    if PUSHBACK.search(t[:400]):
                        W["pushbacks"] += 1
                    first = re.sub(r"[^a-z']", "", t.strip().split(" ")[0].lower())
                    if first:
                        W["first_words"][first[:16]] += 1
    return wins


def pct(xs, p):
    if not xs:
        return 0
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(len(xs) * p / 100))]


def finish(W, top=12):
    u, a = W["user_chars"], W["assistant_chars"]
    return {
        "first_seen": W["first_seen"], "last_seen": W["last_seen"],
        "tokens": W["tokens"],
        "total_tokens": sum(W["tokens"].values()),
        "sessions": len(W["sessions"]),
        "assistant_turns": W["assistant_turns"], "user_turns": W["user_turns"],
        "injected_turns": W["injected_turns"],
        "by_model": dict(sorted(W["by_model"].items(), key=lambda x: -x[1])[:top]),
        "by_project": dict(sorted(W["by_project"].items(), key=lambda x: -x[1])[:top]),
        "tools": dict(sorted(W["tools"].items(), key=lambda x: -x[1])[:top]),
        "hours": {str(h): W["hours"][h] for h in sorted(W["hours"])},
        # Style, as shape rather than content.
        "style": {
            "user_chars_median": pct(u, 50), "user_chars_p90": pct(u, 90),
            "assistant_chars_median": pct(a, 50), "assistant_chars_p90": pct(a, 90),
            "assistant_turns_with_text": len(a),
            "pushback_turns": W["pushbacks"],
            "pushback_rate": round(W["pushbacks"] / W["user_turns"], 4) if W["user_turns"] else 0,
            "tools_per_assistant_turn": round(
                sum(W["tools"].values()) / W["assistant_turns"], 3) if W["assistant_turns"] else 0,
            "opening_words": dict(sorted(W["first_words"].items(),
                                         key=lambda x: -x[1])[:top]),
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", help="a machine folder under deadreckon-record")
    ap.add_argument("--home", default=str(pathlib.Path.home()))
    ap.add_argument("--out", default="digests")
    ap.add_argument("--machine", help="label; defaults to the corpus folder name")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--epoch", default="2026-01-01",
                    help="window boundaries are anchored here so every machine "
                         "buckets identically and windows can be added together")
    args = ap.parse_args()

    if args.corpus:
        c = pathlib.Path(args.corpus).expanduser()
        trees = [c / ".claude" / "projects"]
        machine = args.machine or c.name
        source = "corpus"
    else:
        from analyze_tokens import find_config_dirs
        home = pathlib.Path(args.home)
        trees = [d / "projects" for d in find_config_dirs(home)]
        machine = args.machine or pathlib.Path.cwd().name
        source = "live profiles"
    trees = [t for t in trees if t.is_dir()]
    if not trees:
        raise SystemExit("nothing to digest")

    epoch = datetime.date.fromisoformat(args.epoch)
    wins = scan(trees, args.days, epoch)

    out = pathlib.Path(args.out) / machine
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    total = 0
    index = []
    for w in sorted(wins):
        d = finish(wins[w])
        d.update({"machine": machine, "window_start": w, "window_days": args.days,
                  "generated_at": stamp, "source": source})
        f = out / f"{w}.json"
        f.write_text(json.dumps(d, indent=1) + "\n", encoding="utf-8")
        total += d["total_tokens"]
        index.append((w, d["total_tokens"], d["sessions"], f.stat().st_size))

    (out / "INDEX.json").write_text(json.dumps({
        "machine": machine, "generated_at": stamp, "source": source,
        "window_days": args.days, "epoch": args.epoch,
        "windows": [w for w, _, _, _ in index], "total_tokens": total,
    }, indent=1) + "\n", encoding="utf-8")

    print(f"  machine   {machine}   from {source}")
    print(f"  {'window':14}{'tokens':>18}{'sessions':>10}{'size':>9}")
    for w, t, s, b in index:
        print(f"  {w:14}{t:>18,}{s:>10}{b/1024:>8.1f}K")
    print(f"  {'total':14}{total:>18,}{'':>10}{sum(b for *_, b in index)/1024:>8.1f}K")
    print(f"\n  wrote {out}/ — {len(index)} window(s)")


if __name__ == "__main__":
    main()
