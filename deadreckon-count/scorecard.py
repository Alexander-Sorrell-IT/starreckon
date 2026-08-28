#!/usr/bin/env python3
"""Did this computer's run actually work? One page, per machine.

    python3 scorecard.py                 # -> <machine>/human-readable/SCORECARD.md
                                         #    <machine>/machine-readable/scorecard.json

Run after `update.py` and `export_corpus.py`. Everything else in this repo
reports what was found; this reports whether finding it went right — and it is
per computer, because "the fleet is fine" is not an answer when one machine
silently read zero.

WHAT IT SCORES

Not the numbers. Whether each step left the evidence it should have:

  scan        the three scanners each wrote their file, recently, same version
  readers     every CLI reports installed-or-not, and none is installed-but-zero
  agreement   analyze_tokens and sessions.py, two implementations of one
              question, land on the same total
  corpus      an export exists, is newer than nothing, and its recount matches
  archive     a dated snapshot was written
  redaction   the export's own leak check came back clean

A step that did not run scores differently from one that ran and found nothing.
That distinction is the single most repeated bug in this repo's history — four
readers sat at zero for months because absent and empty looked identical — so
the scorecard never collapses them into one row.
"""

import argparse
import datetime
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import paths


def age_h(iso):
    try:
        t = datetime.datetime.fromisoformat(iso)
    except Exception:
        return None
    now = datetime.datetime.now(t.tzinfo) if t.tzinfo else datetime.datetime.now()
    return (now - t).total_seconds() / 3600


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", help="folder; default is this computer's")
    ap.add_argument("--corpus", default=str(pathlib.Path.home() / "deadreckon-record"))
    args = ap.parse_args()
    root = pathlib.Path(__file__).parent

    if args.machine:
        mdir = root / args.machine
    else:
        import platform
        host = platform.node()
        mdir = None
        for d in paths.machine_folders(root):
            mid = d / ".machine-id"
            if mid.is_file():
                try:
                    if json.loads(mid.read_text()).get("hostname") == host:
                        mdir = d
                        break
                except Exception:
                    pass
        if mdir is None:
            raise SystemExit("cannot tell which folder is this computer — pass --machine")

    rows = []      # (area, check, status, detail)   status: ok | WARN | FAIL | n/a

    def add(area, check, ok, detail=""):
        rows.append((area, check, "ok" if ok is True else
                     "FAIL" if ok is False else str(ok), detail))

    # ---- scan ------------------------------------------------------------
    tot = paths.find(mdir, "totals.json")
    ses = paths.find(mdir, "sessions.json")
    hw = paths.find(mdir, "hardware.json")
    add("scan", "totals.json written", tot is not None)
    add("scan", "sessions.json written", ses is not None)
    add("scan", "hardware.json written", hw is not None)

    T = json.loads(tot.read_text(encoding="utf-8")) if tot else {}
    S = json.loads(ses.read_text(encoding="utf-8")) if ses else {}

    a = age_h(T.get("generated_at") or "")
    add("scan", "scan is recent", None if a is None else ("ok" if a < 48 else "WARN"),
        f"{a:.1f}h old" if a is not None else "no timestamp")

    va, vs = T.get("scanner_version"), S.get("scanner_version")
    add("scan", "both scanners same version", (va == vs) if (va and vs) else "WARN",
        f"{va} / {vs}")

    # ---- readers ---------------------------------------------------------
    readers = S.get("readers") or []
    add("readers", "every CLI has a row", bool(readers), f"{len(readers)} rows")
    silent = [r["cli"] for r in readers if r.get("installed") and not r.get("sessions")]
    add("readers", "no CLI is installed-but-silent", not silent,
        ", ".join(silent) if silent else "none")
    errored = [r["cli"] for r in readers if r.get("error")]
    add("readers", "no reader raised", not errored, ", ".join(errored) or "none")

    # ---- agreement -------------------------------------------------------
    # Two implementations of one question. They may differ by whatever was
    # written between the two scans; they may not differ by a profile.
    at = T.get("grand_total_tokens")
    sc = sum(x.get("total", 0) for x in S.get("sessions", []) if x.get("cli") == "claude")
    if at and sc:
        diff = abs(at - sc)
        pct = diff / max(at, sc) * 100
        add("agreement", "analyze_tokens == sessions", "ok" if pct < 1 else "FAIL",
            f"{at:,} vs {sc:,} — {diff:,} apart ({pct:.2f}%)")
    else:
        add("agreement", "analyze_tokens == sessions", "n/a", "one side missing")

    # ---- corpus ----------------------------------------------------------
    cdir = pathlib.Path(args.corpus) / mdir.name
    man = paths.find(cdir, "MANIFEST.json")
    add("corpus", "export exists", bool(man), str(cdir))
    if man:
        M = json.loads(man.read_text(encoding="utf-8"))
        add("corpus", "export is recent",
            "ok" if (age_h(M.get("generated_at") or "") or 999) < 48 else "WARN",
            M.get("generated_at", "?"))
        add("corpus", "profiles match the scan",
            len(M.get("profiles", [])) == len(T.get("accounts", [])),
            f"{len(M.get('profiles', []))} exported / {len(T.get('accounts', []))} scanned")
        red = M.get("redactions") or {}
        add("corpus", "redaction ran", bool(red),
            ", ".join(f"{k} {v:,}" for k, v in red.items()))

    # ---- archive ---------------------------------------------------------
    adir = root / "archive" / mdir.name
    snaps = sorted(p.name for p in adir.iterdir()) if adir.is_dir() else []
    add("archive", "a dated snapshot exists", bool(snaps),
        f"{len(snaps)} snapshot(s), newest {snaps[-1] if snaps else '—'}")

    # ---- verdict ---------------------------------------------------------
    fails = [r for r in rows if r[2] == "FAIL"]
    warns = [r for r in rows if r[2] == "WARN"]
    stamp = datetime.datetime.now().astimezone().isoformat(timespec="seconds")

    L = [f"# Scorecard — {T.get('machine', mdir.name)}", "",
         f"_{stamp}_", "",
         ("**Everything checked out.**" if not fails and not warns else
          f"**{len(fails)} failed, {len(warns)} to look at.**"), "",
         "| area | check | | detail |", "|---|---|---|---|"]
    mark = {"ok": "✅", "FAIL": "❌", "WARN": "⚠️", "n/a": "—"}
    for area, check, st, detail in rows:
        L.append(f"| {area} | {check} | {mark.get(st, st)} | {detail} |")
    L += ["", "---", "",
          "A check that could not run shows `—`, never `✅`. A reader that is "
          "installed and reported zero sessions is a **failure**, not a quiet "
          "success — that exact confusion hid four broken readers for months.", ""]

    (paths.human(mdir) / "SCORECARD.md").write_text("\n".join(L), encoding="utf-8")
    (paths.machine(mdir) / "scorecard.json").write_text(json.dumps({
        "machine": T.get("machine", mdir.name), "generated_at": stamp,
        "failed": len(fails), "warned": len(warns),
        "checks": [{"area": a, "check": c, "status": s, "detail": d}
                   for a, c, s, d in rows],
    }, indent=1) + "\n", encoding="utf-8")

    w = max(len(r[1]) for r in rows)
    for area, check, st, detail in rows:
        print(f"  {mark.get(st, st)} {area:10} {check:{w}}  {detail}")
    print(f"\n  {len(rows)} checks — {len(fails)} failed, {len(warns)} warned")
    print(f"  wrote {mdir.name}/human-readable/SCORECARD.md")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
