#!/usr/bin/env python3
"""Find AI tool stores by SHAPE, so a tool nobody wrote down is still found.

    python3 discover.py                 what is here, known and unknown
    python3 discover.py --unknown-only  only what no Store() covers
    python3 discover.py --json

WHY THIS EXISTS

stores.py is 47 hand-written Store() entries and it is the single source of
truth for where every CLI keeps its data. That works exactly as far as somebody
thought to write an entry, and no further. A CLI installed last week, on one
machine, by a tool nobody here has heard of, produces:

    counted tokens          0
    store state             absent
    sweep_usage             nothing to report
    every consistency check passes

which is byte-for-byte what a CLI you have never installed produces. That is the
signature defect of this repository -- ABSENT LOOKS EXACTLY LIKE ZERO -- moved
up one level, from "this file could not be read" to "this tool was never
imagined". It is the version no amount of care inside a reader can fix, because
the reader does not exist.

WHAT DISCOVERY MEANS HERE, AND WHAT IT DELIBERATELY DOES NOT

By SHAPE, not by name. A name list is the thing that failed; another name list
is not a fix. `~/.claude*` misses `~/.my-claude`, and every glob only finds the
spellings its author imagined. So this asks what a store IS:

    a directory holding files whose CONTENT is conversational -- rows carrying
    a usage/token accounting, or a database with session-shaped tables, or
    files named for what they hold rather than for the tool that wrote them

and it asks that of the whole home, at bounded depth, once.

It does NOT count tokens. count is sessions.py's job and it needs a reader that
understands the format. This answers the question BEFORE that one: is there
something here that nobody is counting? A number produced by guessing at an
unknown format would be worse than no number, because it would be believed.

It does NOT write a Store(). A tool found here is a prompt for a human to add
two things -- an entry and a reader -- and inventing either automatically is how
you get a reader that agrees with itself.

THE THREE ANSWERS

    KNOWN       a Store() already covers this path
    UNKNOWN     conversational content, covered by nothing
    AMBIGUOUS   shaped like a store, but the content could not be classified

AMBIGUOUS is not a failure and is not folded into either neighbour. A directory
that could not be read, or holds a format this cannot recognise, is a third
fact, and collapsing it into "known" hides a gap while collapsing it into
"unknown" cries wolf until the report is ignored.
"""

import argparse
import json
import os
import pathlib
import sqlite3
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import stores                                                   # noqa: E402

HOME = pathlib.Path.home()

# Depth 4 from home. Deep enough for ~/.config/<tool>/<profile>/sessions and for
# Library/Application Support/<tool>/<x>, shallow enough not to walk a source
# tree. Anything deeper is inside a store, not a store.
MAX_DEPTH = 4

# Skipped because they are OTHER PEOPLE'S DATA OR OURS. Not a name filter on
# tools -- a filter on trees that cannot contain one, kept short on purpose so
# it does not quietly become the name list this file exists to replace.
SKIP = {
    ".git", "node_modules", "__pycache__", ".cache", ".npm", ".cargo", ".rustup",
    "venv", ".venv", "site-packages", "dist-packages", "Trash", ".Trash",
    "snap", ".steam", "Steam", ".wine", "go", ".gradle", ".m2",
    # ours: the corpus is a COPY of stores, and rediscovering it would report
    # every tool twice, once real and once as its own backup
    "deadreckon-count", "deadreckon-record", ".ai-logs-archive",
}

# A row carrying one of these is an accounting of model usage. Deliberately
# broad: the point is to notice a format nobody has written a reader for, and a
# narrow list would only recognise the formats already handled.
USAGE_KEYS = {"usage", "tokens", "token_count", "tokenCount", "input_tokens",
              "output_tokens", "prompt_tokens", "completion_tokens",
              "total_tokens", "totalTokens", "cache_read_input_tokens"}

# Names that describe CONTENT rather than a vendor. A directory of files called
# these is holding a conversation whatever wrote it.
RECORD_WORDS = {"session", "sessions", "conversation", "conversations", "chat",
                "chats", "history", "transcript", "transcripts", "messages",
                "thread", "threads", "rollout", "rollouts", "checkpoints"}


def _known_paths():
    """Every path any Store() resolves to on this machine, absolute."""
    out = set()
    for s in stores.STORES:
        try:
            for p in stores.resolve(s, str(HOME)) or []:
                out.add(os.path.realpath(p))
        except OSError:
            pass
    return out


def _looks_conversational(path, budget=40):
    """Does this directory hold model-conversation records? Cheap, bounded.

    Returns (verdict, why) where verdict is True / False / None, and None means
    AMBIGUOUS -- could not tell. Three values, not two, and the third is the one
    that keeps this honest: a directory that raised EACCES is not empty.
    """
    seen = unreadable = 0
    for p in sorted(path.iterdir() if path.is_dir() else []):
        if seen >= budget:
            break
        try:
            if p.is_dir():
                continue
            suffix = p.suffix.lower()
            if suffix in (".jsonl", ".json"):
                seen += 1
                with p.open(encoding="utf-8", errors="replace") as fh:
                    for i, line in enumerate(fh):
                        if i > 30:
                            break
                        try:
                            rec = json.loads(line)
                        except ValueError:
                            continue
                        if not isinstance(rec, dict):
                            continue
                        flat = set(rec) | set(rec.get("message") or {} if
                                              isinstance(rec.get("message"), dict) else {})
                        if flat & USAGE_KEYS:
                            return True, f"{p.name}: usage accounting in the rows"
            elif suffix in (".db", ".sqlite", ".sqlite3"):
                seen += 1
                try:
                    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=2)
                    names = {r[0].lower() for r in con.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'")}
                    con.close()
                    if names & RECORD_WORDS:
                        return True, f"{p.name}: tables {sorted(names & RECORD_WORDS)}"
                except sqlite3.Error:
                    unreadable += 1
        except PermissionError:
            unreadable += 1
        except OSError:
            unreadable += 1
    if unreadable:
        return None, f"{unreadable} file(s) could not be read"
    return False, ""


# Where a tool's own directory sits. A conversational directory found anywhere
# below one of these belongs to the tool that owns that directory -- it is not a
# tool in its own right.
TOOL_BASES = ("", ".config", ".local/share", "Library/Application Support",
              "Library/Containers", "AppData/Roaming", "AppData/Local")


def _tool_root(path, home=HOME):
    """The TOOL a conversational directory belongs to, not the directory itself.

    The second thing this file got wrong. Version one was a name list; version
    two reported every directory holding records as a separate tool, so
    `.claude/projects/<one-project>` became a finding, and there are hundreds of
    those. 313 "undiscovered tools" of which nearly all were one known store's
    own internals.

    A store has children. Its children are not stores. So a hit is attributed
    upward to the first directory sitting directly under home or under one of
    the standard application bases, and the report is deduplicated on that.
    `~/Desktop/standout_clean/.claude/projects/x` attributes to
    `~/Desktop/standout_clean/.claude`, which is one answer instead of ninety.
    """
    try:
        rel = pathlib.Path(os.path.realpath(path)).relative_to(
            pathlib.Path(os.path.realpath(home)))
    except (OSError, ValueError):
        return path
    parts = rel.parts
    for base in sorted(TOOL_BASES, key=lambda b: -len(b)):
        bp = tuple(pathlib.PurePath(base).parts) if base else ()
        if parts[:len(bp)] == bp and len(parts) > len(bp):
            return home.joinpath(*parts[:len(bp) + 1])
    return home / parts[0] if parts else path


def walk(home=HOME):
    """Every candidate store under home, classified. One pass, bounded depth."""
    known = _known_paths()
    found, unreadable_dirs, seen_roots = [], [], set()
    stack = [(home, 0)]
    while stack:
        d, depth = stack.pop()
        if depth > MAX_DEPTH:
            continue
        try:
            entries = list(d.iterdir())
        except PermissionError as e:
            unreadable_dirs.append(f"{d}: {e.strerror}")
            continue
        except OSError:
            continue
        for p in entries:
            try:
                if not p.is_dir() or p.is_symlink():
                    continue
            except OSError:
                continue
            if p.name in SKIP:
                continue
            real = os.path.realpath(p)
            # CONTENT DECIDES. The name is a hint and nothing more.
            #
            # The first version of this read `if verdict or named:` -- a
            # directory called `sessions` became a candidate whatever was in it.
            # That is a NAME LIST, which is the exact failure this file was
            # written to replace, and the output said so immediately: 349
            # "undiscovered tools", of which the overwhelming majority were
            # Chrome profile directories --
            #
            #     ~/.claude/playwright-profiles/coupang_1/Default/Sessions
            #     ~/.creds-profile/Profile 2/Sessions
            #     ~/.vscode-insiders/extensions/ms-vscode.cpptools-*/bin/messages
            #
            # -- browser session state and a compiler's message catalogue. A
            # report where the true findings are buried under 340 false ones is
            # worse than no report: it gets skimmed once and never opened again,
            # and the one real tool in it is lost either way.
            #
            # So `named` now only annotates something content already proved.
            named = p.name.lower() in RECORD_WORDS
            verdict, why = _looks_conversational(p)
            if verdict:
                covered = any(real == k or real.startswith(k + os.sep) or
                              k.startswith(real + os.sep) for k in known)
                # ATTRIBUTED TO THE TOOL, and deduplicated there.
                root = _tool_root(p, home)
                rreal = os.path.realpath(root)
                covered = covered or any(
                    rreal == k or rreal.startswith(k + os.sep) or
                    k.startswith(rreal + os.sep) for k in known)
                if str(root) in seen_roots:
                    continue
                seen_roots.add(str(root))
                found.append({
                    "path": str(root), "hit": str(p), "state":
                        "KNOWN" if covered else
                        ("AMBIGUOUS" if verdict is None else "UNKNOWN"),
                    "why": why + (f" (dir named {p.name!r})" if named else ""),
                })
            elif verdict is None:
                found.append({"path": str(p), "state": "AMBIGUOUS", "why": why})
            stack.append((p, depth + 1))
    return {"candidates": found, "unreadable_dirs": unreadable_dirs,
            "known_store_paths": len(known)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--unknown-only", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    res = walk()
    if args.json:
        print(json.dumps(res, indent=2))
        return 0

    by = {}
    for c in res["candidates"]:
        by.setdefault(c["state"], []).append(c)

    print(f"\n  {res['known_store_paths']} path(s) covered by a Store()\n")
    for state in ("UNKNOWN", "AMBIGUOUS", "KNOWN"):
        rows = by.get(state, [])
        if args.unknown_only and state == "KNOWN":
            continue
        print(f"  {state:10} {len(rows)}")
        for c in rows[:12 if state != "KNOWN" else 4]:
            print(f"    {c['path'].replace(str(HOME), '~'):58} {c['why'][:44]}")
        if len(rows) > (12 if state != "KNOWN" else 4):
            print(f"    ... and {len(rows) - (12 if state != 'KNOWN' else 4)} more")
        print()

    if res["unreadable_dirs"]:
        # Before the verdict, because a sweep that could not read everything has
        # not answered the question -- it has answered a smaller one.
        print(f"  {len(res['unreadable_dirs'])} directory(ies) could not be read:")
        for u in res["unreadable_dirs"][:6]:
            print(f"    {u.replace(str(HOME), '~')}")
        print()

    n = len(by.get("UNKNOWN", []))
    print(f"  {n} tool(s) hold conversation records that NO Store() covers."
          if n else "  Every conversational directory found is covered by a Store().")
    if n:
        print("  Each needs two things: a Store() in stores.py and a reader in")
        print("  sessions.py. Until then their tokens read as zero, which is")
        print("  what a tool you never installed also reads as.")
    return 1 if n else 0


if __name__ == "__main__":
    raise SystemExit(main())
