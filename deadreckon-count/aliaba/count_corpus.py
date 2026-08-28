#!/usr/bin/env python3
"""Recount tokens from the corpus, per CLI, using the scanner's own readers.

    python3 count_corpus.py                    # ~/deadreckon-record vs this repo
    python3 count_corpus.py --corpus DIR
    python3 count_corpus.py --tolerance 5.0

The two repositories hold the same usage twice. `deadreckon-count` holds what the
scanner computed; `deadreckon-record` holds the transcripts it computed them from,
redacted — and redaction never touches usage fields, so the corpus can be added
up on its own.

WHY THIS RUNS THE READERS INSTEAD OF SUMMING THE FILES

The previous version walked `*.jsonl` and summed every `message.usage`,
deduplicating on the row's `uuid`. Its docstring said "exactly as the scanner
does". It did not. Claude Code writes one row per streaming chunk; those rows
share a `message.id` and carry a DIFFERENT `uuid` each, with the usage block
repeated byte-identically. Deduplicating on `uuid` therefore removes nothing,
and the "independent recount" was the streaming inflation:

    hp-laptop-linux    corpus 14,066,208,990 vs scanner 6,734,300,954   +108.87%

2.09×, which is the repeat factor, reported as a machine that had merely been
"scanned at a different time". Three separate errors compounded into that
number: no streaming dedup, Claude-only counting compared against an all-CLI
`grand_total_tokens`, and never looking in `tools/` at all.

A second derivation whose disagreements are explained away is not a check. So
this file no longer parses anything itself — it aims `sessions.py`'s readers at
the corpus copy and compares PER CLI against the same readers' live numbers in
`sessions.json`. Same code, two different trees. That is a check the corpus can
actually fail, and the thing it is most likely to catch is not arithmetic: it is
a store that was counted and never preserved.

WHAT A ROW MEANS

    ok            corpus and scanner agree within tolerance
    CHECK         they differ by more, and the clock does not obviously explain it
    NOT EXPORTED  the reader found tokens live, and the corpus holds none of it
    binary        the store cannot be redacted, so it is deliberately not shipped
                  (MANIFEST records the file count; antigravity is all of it)

NOT EXPORTED is the failure this exists for. `stores.unpreserved_readers()` was
supposed to catch it and cannot: it asks whether a Store with that `cli` is in
the MAP, and copilot-chat is — at a correct path, holding 4.75 GB, exported
never. A map compared against itself agrees with itself.
"""

import argparse
import datetime
import json
import os
import pathlib

import paths
import sessions
import stores

FIELDS = sessions.FIELDS

# Readers the exporter is CORRECT to have nothing for, and why. Neither is a
# hole to go and fix; both would otherwise read as one, and a check that reports
# work nobody should do is a check people stop reading.
#
# ASKED, NOT ASSERTED. This was a literal dict here saying claude-orphans is
# "config, never exported" — written while the exporter was exporting it,
# because being in the store map at all meant being copied. The claim was true
# of the intent and false of the code, and a hardcoded restatement of another
# file's behaviour cannot tell the difference. stores.py now carries
# `preserve=False` and the exporter honours it, so this reads the answer.
BY_DESIGN = stores.counted_never_preserved()


def corpus_base(label, reader_name):
    """Sub-path under `tools/<label>/` that is this reader's base directory.

    The exporter writes `tools/<label>/<path relative to the store root>`, so a
    reader whose base IS the store root wants `tools/<label>` unchanged. Only
    where the reader looks deeper than the store does — clawspring's store is
    `.clawspring/sessions` and its reader reads `.clawspring/sessions/daily` —
    is there a suffix, and it is derived from the two declarations rather than
    written down a third time.
    """
    store = stores.BY_LABEL.get(label)
    fn = sessions.READERS.get(reader_name)
    if store is None or fn is None:
        return ""
    # Every platform expansion of the store, not `store.path` — that can carry
    # an unexpanded `{vscode}` token, which matches no reader rel at all and
    # silently returns "" for the VS Code stores.
    for rel in getattr(fn, "rels", None) or ():
        rel = rel.replace("\\", "/")
        for sp in store.rel_paths():
            sp = sp.replace("\\", "/")
            if rel == sp:
                return ""
            if rel.startswith(sp + "/"):
                return rel[len(sp) + 1:]
    return ""


def recount(mdir):
    """{cli: {"sessions": n, "tokens": t}} read out of one machine's corpus.

    Labels are merged per CLI and deduplicated on session_id, because several
    labels feed one reader — grok has a live and an archived store, kilocode and
    copilot-chat have one per VS Code channel — and `multi_base` does that dedup
    only when it supplies the bases itself.
    """
    out, seen = {}, {}
    tools = mdir / "tools"

    def add(cli, recs):
        d = out.setdefault(cli, {"sessions": 0, "tokens": 0})
        s = seen.setdefault(cli, set())
        for r in recs or []:
            sid = r.get("session_id")
            if sid is not None:
                if sid in s:
                    continue
                s.add(sid)
            d["sessions"] += 1
            d["tokens"] += sum(r["tokens"][k] for k in FIELDS)

    # Claude keeps the profile layout the reader already globs for.
    if (mdir / ".claude" / "projects").is_dir():
        add("claude", sessions.read_claude(mdir))

    if tools.is_dir():
        for d in sorted(p for p in tools.iterdir() if p.is_dir()):
            store = stores.BY_LABEL.get(d.name)
            if store is None or not store.cli:
                continue                      # preserved, nothing counts it
            fn = sessions.READERS.get(store.cli)
            if fn is None:
                continue
            sub = corpus_base(d.name, store.cli)
            base = d / sub if sub else d
            if not base.exists():
                continue
            try:
                add(store.cli, fn(mdir, base=base))
            except Exception as e:                              # noqa: BLE001
                out.setdefault(store.cli, {"sessions": 0, "tokens": 0})
                out[store.cli].setdefault("errors", []).append(f"{d.name}: {e}")
    return out


def unreadable(mdir):
    """{label: files} the exporter refused to ship because they are binary.

    Antigravity keeps conversations as SQLite and AES-GCM `.pb`. The reader gets
    token counts out of them; nothing can redact them. A store with 53 skipped
    files and 0 exported is not the same as a store nobody uses, and without
    this the corpus recount would read the second as the first.
    """
    mf = paths.find(mdir, "MANIFEST.json")
    if not mf:
        return {}
    try:
        doc = json.loads(mf.read_text(encoding="utf-8"))
    except Exception:                                           # noqa: BLE001
        return {}
    out = {}
    for t in doc.get("tools") or []:
        if t.get("not_exported_binary") and not t.get("files"):
            out[t.get("counted_by") or t.get("tool")] = t["not_exported_binary"]
    return out


def preserved_only(mdir):
    """Store labels in the corpus that no reader counts — preservation, not usage."""
    tools = mdir / "tools"
    if not tools.is_dir():
        return []
    out = []
    for d in sorted(p for p in tools.iterdir() if p.is_dir()):
        s = stores.BY_LABEL.get(d.name)
        if s is None or not s.cli or s.cli not in sessions.READERS:
            out.append(d.name)
    return out


def scanner_readers(repo, machine):
    """{cli: {"sessions": n, "tokens": t}} the scanner recorded for this machine."""
    sj = paths.find(repo / machine, "sessions.json")
    if not sj or not sj.is_file():
        return None, None
    doc = json.loads(sj.read_text(encoding="utf-8"))
    return ({r["cli"]: {"sessions": r.get("sessions") or 0,
                        "tokens": r.get("tokens") or 0}
             for r in doc.get("readers") or []},
            doc.get("generated_at"))


def when(s):
    try:
        return datetime.datetime.fromisoformat(s)
    except Exception:                                           # noqa: BLE001
        return None


def newest_manifest(mdir):
    """The export stamp, taking the NEWEST of every MANIFEST.json under a machine.

    There are two: one beside the machine folder and one in machine-readable/,
    and on this machine they are ten hours apart. Reading whichever `paths.find`
    reached first dated the export before the store map that produced it.
    """
    best = None
    for mf in mdir.rglob("MANIFEST.json"):
        try:
            g = json.loads(mf.read_text(encoding="utf-8")).get("generated_at")
        except Exception:                                       # noqa: BLE001
            continue
        d = when(g)
        if d and (best is None or d > best[0]):
            best = (d, g)
    return best[1] if best else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(pathlib.Path.home() / "deadreckon-record"))
    ap.add_argument("--tolerance", type=float, default=5.0,
                    help="percent difference tolerated when the clocks explain it")
    ap.add_argument("--machine", default=None, help="only this machine")
    args = ap.parse_args()

    repo = pathlib.Path(__file__).parent
    corpus = pathlib.Path(args.corpus)
    if not corpus.is_dir():
        raise SystemExit(f"no corpus at {corpus}")

    present = paths.corpus_machine_folders(corpus)
    machines = [d for d in present if paths.find(d, "MANIFEST.json")]
    # A MACHINE FOLDER WITH NO MANIFEST WAS NOT SKIPPED, IT WAS INVISIBLE.
    #
    # The line above is the whole roster this file works from, so a corpus
    # folder whose export never wrote a MANIFEST — interrupted, or copied by
    # hand — was dropped before the first print. On a planted five-machine
    # fleet with charlie's MANIFEST removed:
    #
    #     4 per-CLI comparison(s), every counted store present in the corpus.
    #     exit 0
    #
    # Four machines checked out of five, reported as everything, with a zero
    # exit. The reconciliation that exists to catch a store counted and never
    # preserved cannot see a whole computer counted and never checked.
    skipped = sorted(d.name for d in present if d not in machines)
    if args.machine:
        machines = [d for d in machines if d.name == args.machine]
        skipped = [n for n in skipped if n == args.machine]
    if not machines:
        # "no machine folders" is a different sentence from "no machine folder
        # got far enough to write a MANIFEST", and this printed the first for
        # both.
        print(f"{len(skipped)} machine folder(s) present and none holds a "
              f"MANIFEST.json: {', '.join(skipped)}" if skipped else
              "no machine folders in the corpus — nothing to check, which is "
              "itself the answer")
        return 1

    missing, stale, checks = [], [], 0
    for mdir in machines:
        name = mdir.name
        got = recount(mdir)
        want, scanned = scanner_readers(repo, name)
        exported = newest_manifest(mdir)
        binaries = unreadable(mdir)

        gap = ""
        a, b = when(scanned), when(exported)
        if a and b:
            mins = abs((a - b).total_seconds()) / 60
            gap = f"{mins:.0f} min apart, {'scan' if a > b else 'export'} later"

        print(f"\n{name}   {gap}")
        if want is None:
            print("  no sessions.json in deadreckon-count — cannot compare")
            continue

        print(f"  {'cli':16} {'corpus':>16} {'scanner':>16} {'diff':>14}")
        for cli in sorted(set(want) | set(got)):
            c = got.get(cli, {}).get("tokens", 0)
            s = want.get(cli, {}).get("tokens", 0)
            if not c and not s and cli in want:
                continue
            # A cli the saved scan never had a reader for is NOT a scanner that
            # counted zero, and printing it as a 100% disagreement would be the
            # absent-looks-like-zero bug in the tool that exists to catch it.
            # hp's scan lists 8 readers; clawspring was added three hours later.
            if cli not in want:
                print(f"  {cli:16} {c:>16,} {'—':>16} {'':>14}  NOT SCANNED "
                      f"(this machine's scan predates the reader)")
                stale.append((name, cli, c))
                continue
            checks += 1
            if not c and s:
                if cli in binaries:
                    print(f"  {cli:16} {'—':>16} {s:>16,} {'':>14}  binary, "
                          f"{binaries[cli]} files not shippable")
                elif cli in BY_DESIGN:
                    print(f"  {cli:16} {'—':>16} {s:>16,} {'':>14}  "
                          f"{BY_DESIGN[cli]}")
                else:
                    print(f"  {cli:16} {0:>16,} {s:>16,} {-s:>+14,}  NOT EXPORTED")
                    missing.append((name, cli, s))
                continue
            diff = c - s
            pct = abs(diff) / s * 100 if s else 100.0
            flag = "ok" if pct <= args.tolerance else "CHECK"
            print(f"  {cli:16} {c:>16,} {s:>16,} {diff:>+14,}  {pct:5.2f}% {flag}")
            err = got.get(cli, {}).get("errors")
            if err:
                print(f"  {'':16} reader errors: {'; '.join(err)}")

        po = preserved_only(mdir)
        if po:
            print(f"  preserved, no reader: {', '.join(po)}")
        if not (mdir / "tools").is_dir():
            print("  NO tools/ — this machine exported before the store map "
                  "covered anything but Claude. Re-run `run.py corpus` on it.")

    print()
    if skipped:
        print(f"{len(skipped)} corpus folder(s) have NO MANIFEST.json and were "
              f"not checked at all: {', '.join(skipped)}")
        print("An export that did not finish is not a machine that reconciles. "
              "Re-run\n`run.py corpus` there, or remove the folder.\n")
    if stale:
        tot = sum(t for _, _, t in stale)
        print(f"{len(stale)} store(s) the corpus holds and the saved scan has no "
              f"reader for, {tot:,} tokens:")
        for m, cli, t in stale:
            print(f"  {m:30} {cli:16} {t:>16,}")
        print("The transcripts are preserved; the number on file was computed "
              "before the\nreader existed. `run.py update` on that machine "
              "picks them up.\n")

    if missing:
        tot = sum(t for _, _, t in missing)
        print(f"{len(missing)} store(s) counted but NOT PRESERVED, {tot:,} tokens:")
        for m, cli, t in missing:
            print(f"  {m:30} {cli:16} {t:>16,}")
        print("\nThese are transcripts the numbers depend on and the corpus does "
              "not hold.\nRe-export the machine, or the number cannot be "
              "reproduced from the record.")
        return 1
    if skipped:
        return 1
    print(f"{checks} per-CLI comparison(s) across {len(machines)} machine(s), "
          f"every counted store present in the corpus.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
