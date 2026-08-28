#!/usr/bin/env python3
"""Attacks on the four document generators, written to fail against the code
that shipped them.

    python3 adv_reports.py            # every check
    python3 adv_reports.py C3         # one check by id

WHY THIS FILE EXISTS AND WHY IT IS NOT test_reports.py

A test written beside a fix asserts what the fix does. Every check here was run
against the UNFIXED generator first and made to fail, and the failure it
produced is quoted in its docstring. If a check goes green on code that still
holds the defect, the check is worthless and the docstring is a lie you can
grep for.

Every check drives the REAL generator — `corpus_reports.main()`,
`fun_stats.main()`, `monthly.main()`, `combine.main()` — over a temp tree, and
reads the DOCUMENT that comes out. None of them calls the helper the fix lives
in. That is deliberate: the four defects below all had the property that every
internal consistency check passed while the published document said something
false, so a check that stops at the helper cannot see them.

THE FIXTURE IS WRITTEN BY HAND

Every expected number in this file is a literal constant written into a JSON
file two hundred lines below by the same arithmetic. Nothing here imports a
report to work out what a report should say.

    alpha    1,500,000 tokens   owned by THIS host (.machine-id)
    bravo      200,000 tokens   foreign
    charlie     30,000 tokens   foreign
    delta            —          on the roster, never scanned

ABSENT IS NOT ZERO — planted three ways, because it is the defect this
repository has now shipped seven times:

    C1  a ROOT that is not the count repo at all
    C2  a corpus machine folder this run could not READ
    C4  a machine whose sessions.json holds an empty list
    C6  a machine with NO token_ledger.jsonl, next to one whose ledger is empty
"""

import hashlib
import json
import os
import pathlib
import platform
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent

SCANNER = "adv-reports-fixture-v1"
FIELDS = ("input_tokens", "cache_creation_input_tokens",
          "cache_read_input_tokens", "output_tokens")

# ---- the planted arithmetic, spelled out ---------------------------------
ALPHA_S1 = 1_000_000          # 2026-07-05
ALPHA_S2 = 500_000            # 2026-08-02
ALPHA_SCAN = ALPHA_S1 + ALPHA_S2                      # 1,500,000
BRAVO_S1 = 200_000            # 2026-07-06
CHARLIE_S1 = 30_000           # 2026-07-07
JUNE_S1 = 100                 # 2026-06-09, alpha, so 2026-06 exists

FLEET_SCAN = ALPHA_SCAN + BRAVO_S1 + CHARLIE_S1 + JUNE_S1      # 1,730,100
JULY_TRUE = ALPHA_S1 + BRAVO_S1 + CHARLIE_S1                   # 1,230,000

# ledger: alpha's three live sessions PLUS one whose transcript is gone.
#
# The live three are in there on purpose. The ledger's value for a session that
# still exists IS the scan's value, so a ledger folded in by addition rather
# than by difference would double them, and a fixture whose ledger held only
# the vanished session could not tell the two apart.
ALPHA_GONE = 777_000          # start "" — the row month attribution drops
ALPHA_LEDGER = ALPHA_SCAN + JUNE_S1 + ALPHA_GONE               # 2,277,100
FLEET_LIFETIME = ALPHA_LEDGER + BRAVO_S1 + CHARLIE_S1          # 2,507,100


def _quarter(n):
    """Split a total into the four counters so they sum back to it exactly."""
    a = n // 4
    return {"input_tokens": a, "cache_creation_input_tokens": a,
            "cache_read_input_tokens": a, "output_tokens": n - 3 * a}


def _session(sid, total, start, end, cli="claude", model="claude-opus-4-6"):
    return {"session_id": sid, "cli": cli, "project": "proj", "provider":
            "anthropic", "model": model, "turns": 3, "total": total,
            "duration_min": 12.0, "start": start, "end": end,
            "tokens": _quarter(total)}


def gen(base, *parts):
    """A generated file at an exact, literal path.

    A fixture is the one thing that must name files by hand: it builds the tree
    a generator will write into, and then asserts what actually landed there.
    Everything else in this repository goes through `paths.find()`, because a
    flat join makes a moved file read exactly like an absent one — and
    `test_scanner.py` lints every script for that pattern by scanning for a
    quoted generated filename after a slash.

    So there are no slashes. Every literal path in this file comes through here,
    which gives the lint one place to look instead of twenty, and gives a reader
    one place to check that the fixture is addressing the layout the tools
    actually use.
    """
    p = pathlib.Path(base)
    for x in parts:
        p = p / x
    return p


MACHINE_DIR, HUMAN_DIR = "machine-readable", "human-readable"


def _write(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1) + "\n", encoding="utf-8")


def _sessions_json(mdir, name, sess, generated="2026-08-10T00:00:00-05:00"):
    _write(gen(mdir, MACHINE_DIR, "sessions.json"), {
        "machine": name, "generated_at": generated, "scanner_version": SCANNER,
        "readers": [{"cli": "claude", "installed": True}],
        "sessions": sess,
        "first_last_seen": {"claude": {"first": "2026-06-09T00:00:00Z",
                                       "last": "2026-08-02T00:00:00Z",
                                       "sources": ["transcripts"]}},
        "stats_cache": [], "uncountable_tools": [],
    })


def _totals_json(mdir, name, grand, generated="2026-08-10T00:00:00-05:00"):
    f = _quarter(grand)
    _write(gen(mdir, MACHINE_DIR, "totals.json"), {
        "machine": name, "generated_at": generated, "scanner_version": SCANNER,
        "anthropic_only_tokens": grand, "by_provider": {"anthropic": grand},
        "other_tools": {}, "grand_total_tokens": grand,
        "accounts": [{"account": f"{name}@example.test", "grand_total": grand,
                      "sessions": 1, "turns": 3, "totals": f,
                      "by_model": {"claude-opus-4-6": f},
                      "by_day": {"2026-07-05": grand}}],
    })


def _ledger(mdir, rows):
    p = gen(mdir, MACHINE_DIR, "token_ledger.jsonl")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def _ledger_row(machine, sid, total, start):
    r = {"observed": "2026-08-10T00:00:00-05:00", "scanner": SCANNER,
         "machine": machine, "cli": "claude", "session_id": sid}
    r.update(_quarter(total))
    r["total"] = total
    r["start"] = start
    r["model"] = "claude-opus-4-6"
    return r


# --------------------------------------------------------------------------
# the tree under test
# --------------------------------------------------------------------------

TOOLS = None                # cached list of repo files to copy


def _repo_files():
    global TOOLS
    if TOOLS is None:
        TOOLS = sorted(p.name for p in HERE.iterdir()
                       if p.is_file() and p.suffix == ".py")
    return TOOLS


def count_root(tmp, *, empty_machine=None, owned_empty=False,
               with_ledger=False, with_machines_json=True):
    """A deadreckon-count checkout: the tools, three machine folders, a roster.

    `empty_machine` gets a sessions.json holding ZERO sessions — present and
    readable and reporting nothing, which must not read as never-scanned.
    """
    root = pathlib.Path(tmp) / "count"
    root.mkdir(parents=True, exist_ok=True)
    for n in _repo_files():
        shutil.copy2(HERE / n, root / n)
    # A real checkout has both, and `fun_stats` picks where STATS.md goes from
    # whether machine-readable/ exists. Without them the fixture would exercise
    # a layout no machine is in.
    gen(root, HUMAN_DIR).mkdir(exist_ok=True)
    gen(root, MACHINE_DIR).mkdir(exist_ok=True)

    host = platform.node()
    plan = {
        "alpha": (ALPHA_SCAN + JUNE_S1, [
            _session("alpha-s1", ALPHA_S1, "2026-07-05T09:00:00Z",
                     "2026-07-05T09:30:00Z"),
            _session("alpha-s2", ALPHA_S2, "2026-08-02T09:00:00Z",
                     "2026-08-02T09:30:00Z"),
            _session("alpha-s3", JUNE_S1, "2026-06-09T09:00:00Z",
                     "2026-06-09T09:10:00Z"),
        ]),
        "bravo": (BRAVO_S1, [_session("bravo-s1", BRAVO_S1,
                                      "2026-07-06T09:00:00Z",
                                      "2026-07-06T09:30:00Z")]),
        "charlie": (CHARLIE_S1, [_session("charlie-s1", CHARLIE_S1,
                                          "2026-07-07T09:00:00Z",
                                          "2026-07-07T09:30:00Z")]),
    }
    for name, (grand, sess) in plan.items():
        md = root / name
        if name == empty_machine or (owned_empty and name == "alpha"):
            sess = []
        _sessions_json(md, name, sess)
        _totals_json(md, name, grand)
        _write(md / ".machine-id",
               {"hostname": host if name == "alpha" else f"{name}-host"})
        # A STALE per-machine figure, so "left alone" and "rewritten to zero"
        # are different observable states.
        _write(gen(md, MACHINE_DIR, "stats.json"),
               {"scope": name, "total_tokens": 146_981_095,
                "sessions": 36, "generated_at": "2026-08-09T00:00:00-05:00"})

    if with_ledger:
        _ledger(root / "alpha", [
            _ledger_row("alpha", "alpha-s1", ALPHA_S1, "2026-07-05"),
            _ledger_row("alpha", "alpha-s2", ALPHA_S2, "2026-08-02"),
            _ledger_row("alpha", "alpha-s3", JUNE_S1, "2026-06-09"),
            # THE ROW MONTH ATTRIBUTION DROPS. Its transcript is gone and the
            # observation that survived carries no start date.
            _ledger_row("alpha", "alpha-gone", ALPHA_GONE, ""),
        ])
        # bravo: NO ledger file at all.   charlie: a ledger file holding nothing.
        _ledger(root / "charlie", [])

    if with_machines_json:
        _write(root / "machines.json", {"machines": [
            {"folder": "alpha", "label": "Alpha"},
            {"folder": "bravo", "label": "Bravo"},
            {"folder": "charlie", "label": "Charlie"},
            {"folder": "delta", "label": "Delta"},
        ]})
    return root


def fake_root(tmp):
    """The tools, and nothing else. Not a count checkout."""
    root = pathlib.Path(tmp) / "not-the-repo"
    root.mkdir(parents=True, exist_ok=True)
    for n in _repo_files():
        shutil.copy2(HERE / n, root / n)
    return root


def corpus(tmp, *, host_owns="alpha"):
    """A deadreckon-record checkout with real transcripts for two machines.

    charlie's folder is there, holds a machine-readable/stats.json from an
    older run, and has NO .claude/projects — the export never landed. That is
    the state that used to publish "exported, holds nothing".
    """
    sys.path.insert(0, str(HERE))
    import fleet_fixture as ff
    import sessions as sm

    c = pathlib.Path(tmp) / "record"
    c.mkdir(parents=True, exist_ok=True)
    planted = {}
    for name, sid in (("alpha", "corpus-alpha-1"), ("bravo", "corpus-bravo-1")):
        p = ff.plant_claude(c / name, sid=sid, project="proj", tag=name)
        planted[name] = p.tokens
        _write(c / name / "MANIFEST.json", {"machine": name})
    # bravo's export wrote NINE record files. Two are here. That is the state
    # every real machine folder is in since the transcripts were untracked and
    # moved to release assets, and it is not "an export older than the scan".
    _write(gen(c, "bravo", "MANIFEST.json"), {"machine": "bravo", "files": 9})
    # bravo is a foreign machine: this run will not rewrite its stats.json, so
    # the figure COVERAGE reads is whatever is on disk. Stamp it CURRENT.
    _write(gen(c, "bravo", MACHINE_DIR, "stats.json"),
           {"machine": "bravo", "tokens": planted["bravo"],
            "reader_version": sm.scanner_version(),
            "generated_at": "2026-08-10T00:00:00-05:00"})
    # charlie: present, never exported, holding a leftover ZERO.
    _write(c / "charlie" / "MANIFEST.json", {"machine": "charlie"})
    _write(gen(c, "charlie", MACHINE_DIR, "stats.json"),
           {"machine": "charlie", "tokens": 0,
            "reader_version": sm.scanner_version(),
            "generated_at": "2026-08-09T00:00:00-05:00"})
    return c, planted


# --------------------------------------------------------------------------
# running the real thing
# --------------------------------------------------------------------------

def run(root, script, *args):
    r = subprocess.run([sys.executable, str(pathlib.Path(root) / script), *args],
                       capture_output=True, text=True, cwd=str(root),
                       env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    return r


def snapshot(*dirs):
    """path -> sha256, for every file under each directory."""
    out = {}
    for d in dirs:
        d = pathlib.Path(d)
        if not d.is_dir():
            continue
        for p in sorted(d.rglob("*")):
            if p.is_file():
                out[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def table_row(text, first_cell):
    """The markdown row whose first cell is `first_cell`, cells split out."""
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if cells and cells[0].replace("*", "").strip() == first_cell:
            return cells
    return None


def num(cell):
    d = "".join(ch for ch in (cell or "") if ch.isdigit() or ch == "-")
    return int(d) if d.strip("-") else None


# --------------------------------------------------------------------------
# C1 — a root that is not the count repo publishes zeros as measurements
# --------------------------------------------------------------------------

def C1(tmp):
    """COVERAGE.md written from a root that holds no scans at all.

    Run the generator from a directory that has the tools and nothing else —
    a temp clone, a copy of the scripts, a checkout of the wrong repository.
    `paths.iter_machine_files` yields nothing, and every branch downstream
    reads that as a measured zero:

        | alpha   | — | 1,145 | — | **NOT SCANNED — transcripts here, no
                                     totals.json in deadreckon-count** |
        | **all** | **0** | **0** | **+0** | 0 of 4 machine(s) comparable |
        exit 0

    Every one of those sentences is false: the scans exist, this process was
    simply not looking at them. The document cannot tell "I looked and found
    nothing" from "I never looked", and it publishes the first.
    """
    root = fake_root(tmp)
    c, _ = corpus(tmp)
    r = run(root, "corpus_reports.py", "--corpus", str(c))
    cov = gen(c, HUMAN_DIR, "COVERAGE.md")
    if r.returncode == 0 and cov.is_file():
        t = cov.read_text(encoding="utf-8")
        allrow = table_row(t, "all")
        if allrow and num(allrow[1]) == 0 and "NOT SCANNED" in t:
            return False, ("wrote COVERAGE.md claiming all|0|0|+0 and "
                           f"NOT SCANNED for every machine, exit {r.returncode}")
    if r.returncode == 0:
        return False, f"exit 0 from a root with no scans; wrote {cov.is_file()}"
    blob = (r.stdout + r.stderr).lower()
    if "root" not in blob and "count" not in blob:
        return False, f"refused but did not say why: {r.stderr.strip()[:200]}"
    if cov.is_file():
        return False, "refused and still wrote COVERAGE.md"
    return True, f"refused: {(r.stderr or r.stdout).strip().splitlines()[0][:120]}"


# --------------------------------------------------------------------------
# C2 — a corpus folder this run could not read is reported as holding nothing
# --------------------------------------------------------------------------

def C2(tmp):
    """charlie's corpus folder has no transcripts to read, and COVERAGE
    compares it anyway.

    read_machine() returns None for charlie — there is no .claude/projects, so
    nothing was read. The coverage loop never learns that: it opens the
    leftover stats.json, finds 0, and enters charlie into BOTH totals:

        | charlie | 30,000 | 0 | -30,000 | **exported, holds nothing** |
        | **all** | **1,230,000** | ... | 0 of ... |

    "exported, holds nothing" is a claim about the export. What actually
    happened is that this process could not read the folder, and a machine
    whose corpus figure was not computed by this run must leave BOTH sides of
    the comparison — the same rule the STALE branch already applies.
    """
    root = count_root(tmp)
    c, planted = corpus(tmp)
    r = run(root, "corpus_reports.py", "--corpus", str(c))
    cov = gen(c, HUMAN_DIR, "COVERAGE.md")
    if not cov.is_file():
        return False, f"no COVERAGE.md written (exit {r.returncode}): {r.stderr[:200]}"
    t = cov.read_text(encoding="utf-8")
    row = table_row(t, "charlie")
    allrow = table_row(t, "all")
    if row is None or allrow is None:
        return False, "charlie or all row missing from the table"
    if "holds nothing" in row[-1]:
        return False, f"charlie labelled {row[-1]!r} — that is a claim about the export"
    scanned = num(allrow[1])
    if scanned != ALPHA_SCAN + JUNE_S1 + BRAVO_S1:
        return False, (f"all-row scanned {scanned:,}; charlie's {CHARLIE_S1:,} "
                       f"must not be in it (expected "
                       f"{ALPHA_SCAN + JUNE_S1 + BRAVO_S1:,})")
    return True, f"charlie excluded from both totals; all-row scanned {scanned:,}"


# --------------------------------------------------------------------------
# C3 — the generators write into other computers' folders
# --------------------------------------------------------------------------

def C3(tmp):
    """fun_stats.py and monthly.py rewrite files inside machines they do not own.

    Both iterate `paths.machine_folders(root)` and write STATS.md, stats.json,
    LIFETIME.md, THIS-MONTH.md, lifetime.json, months/*.json, BY-ACCOUNT.md and
    BY-COMPANY.md into every folder they find. Measured on this fixture, one
    owned machine and two foreign:

        fun_stats  4 foreign files rewritten
        monthly   12 foreign files rewritten

    Same shape as commit 4a5b42c, which put 12 tracked files belonging to four
    other computers into git.
    """
    root = count_root(tmp)
    foreign = [root / "bravo", root / "charlie"]
    before = snapshot(*foreign)
    out = []
    for script in ("fun_stats.py", "monthly.py"):
        r = run(root, script)
        if r.returncode != 0:
            return False, f"{script} exit {r.returncode}: {r.stderr[-300:]}"
        after = snapshot(*foreign)
        changed = sorted(set(after) - set(before)) + \
                  sorted(k for k in set(after) & set(before) if after[k] != before[k])
        if changed:
            rel = [str(pathlib.Path(p).relative_to(root)) for p in changed]
            out.append(f"{script} touched {len(changed)}: {', '.join(rel[:4])}")
        before = after
    if out:
        return False, "; ".join(out)
    return True, "zero foreign paths created or modified by either generator"


# --------------------------------------------------------------------------
# C4 — a machine that reports nothing is indistinguishable from one not asked
# --------------------------------------------------------------------------

def C4(tmp):
    """`if not mine: continue` in fun_stats.py.

    charlie's sessions.json is present, readable, and holds an empty list. The
    generator skips it exactly as it skips a machine with no sessions.json:

        charlie never appears in stdout
        charlie has no row in the "Each computer" section of STATS.md
        charlie/machine-readable/stats.json still says 146,981,095

    Measured on the real fleet: emptying asus's sessions.json from 36 sessions
    to 0 left its stats.json at 146,981,095 with rc=0 and asus named nowhere.
    """
    root = count_root(tmp, empty_machine="charlie")
    r = run(root, "fun_stats.py")
    if r.returncode != 0:
        return False, f"exit {r.returncode}: {r.stderr[-300:]}"
    stats = gen(root, HUMAN_DIR, "STATS.md").read_text(encoding="utf-8")
    if "charlie" not in r.stdout:
        return False, "charlie reported nothing and was never named in the output"
    row = table_row(stats, "charlie")
    if "### charlie" not in stats and row is None:
        return False, "charlie has no row anywhere in the fleet STATS.md"

    # And the owned machine reporting nothing must have its own figure REWRITTEN
    # to zero, not left holding the last number it ever had.
    root2 = count_root(tmp + "/owned", owned_empty=True)
    r2 = run(root2, "fun_stats.py")
    if r2.returncode != 0:
        return False, f"owned-empty exit {r2.returncode}: {r2.stderr[-300:]}"
    sj = json.loads(gen(root2, "alpha", MACHINE_DIR, "stats.json")
                    .read_text(encoding="utf-8"))
    if sj.get("total_tokens") != 0:
        return False, (f"alpha is owned, reported 0 sessions, and its stats.json "
                       f"still says {sj.get('total_tokens'):,}")
    return True, "empty machine named in output and rewritten to zero"


# --------------------------------------------------------------------------
# C5 — a frozen month is never revisited, in the wrong direction
# --------------------------------------------------------------------------

def C5(tmp):
    """`if dest.is_dir() and not args.all: continue` in monthly.py.

    2026-07 was frozen from a checkout that held one session. Two more
    machines have been scanned since. Recomputing reads MORE records, not
    fewer — the opposite of the direction the docstring uses to justify
    freezing — and the frozen copy is simply short:

        archive/months/2026-07/month.json   1,000,000
        recomputed from what is here now    1,230,000

    Measured on the real archive: nine frozen months, every one short, total
    18,784,531,262 tokens, and not one of them short in the direction the
    freeze exists to protect.

    The other half of the check is that the protection still works: 2026-06 is
    frozen at a figure LARGER than anything on disk can now produce, and that
    one must not be lowered.
    """
    root = count_root(tmp)
    short = root / "archive" / "months" / "2026-07"
    _write(short / "month.json", {"month": "2026-07", "tokens": ALPHA_S1,
                                  "sessions": 1})
    (short / "REPORT.md").write_text("# 2026-07\n", encoding="utf-8")
    tall = root / "archive" / "months" / "2026-06"
    _write(tall / "month.json", {"month": "2026-06", "tokens": 5_000_000,
                                 "sessions": 40})
    (tall / "REPORT.md").write_text("# 2026-06\n", encoding="utf-8")

    r = run(root, "monthly.py")
    if r.returncode != 0:
        return False, f"exit {r.returncode}: {r.stderr[-300:]}"
    got = json.loads((short / "month.json").read_text(encoding="utf-8"))["tokens"]
    if got != JULY_TRUE:
        return False, (f"archive/months/2026-07 still says {got:,}; the records "
                       f"here support {JULY_TRUE:,} — short by {JULY_TRUE - got:,}")
    kept = json.loads((tall / "month.json").read_text(encoding="utf-8"))["tokens"]
    if kept != 5_000_000:
        return False, (f"archive/months/2026-06 was LOWERED from 5,000,000 to "
                       f"{kept:,} — that is the revision freezing exists to stop")
    return True, f"2026-07 repaired to {got:,}; 2026-06 held at {kept:,}"


# --------------------------------------------------------------------------
# C6 — the ledger is never opened
# --------------------------------------------------------------------------

def C6(tmp):
    """LIFETIME.md says it includes work whose transcripts are gone. It does not.

    No report imports token_ledger. alpha's ledger holds a session that is not
    in any sessions.json — its transcript was deleted and the ledger is the
    only remaining evidence of it — and LIFETIME.md omits it:

        LIFETIME.md            1,730,100
        with the ledger        2,507,100      (+777,000)

    On the real fleet that omission is 5,464,486,399 tokens.

    THE TRAP INSIDE THE FIX: the vanished session carries start "". Attribute
    ledger tokens to a month and it is dropped in silence — on hp that is
    4,072,472,810 of the 5,456,739,486 the ledger adds, so a wired-in ledger
    that goes through month_of() turns a large undercount into a smaller one
    and looks finished.

    And absent must not read as empty: bravo has NO token_ledger.jsonl, charlie
    has one holding zero rows. Both contribute 0. They are different facts.
    """
    root = count_root(tmp, with_ledger=True)
    r = run(root, "monthly.py")
    if r.returncode != 0:
        return False, f"monthly exit {r.returncode}: {r.stderr[-300:]}"
    life = gen(root, HUMAN_DIR, "LIFETIME.md").read_text(encoding="utf-8")
    head = life.splitlines()[2] if len(life.splitlines()) > 2 else ""
    got = num(head.split("tokens")[0]) if "tokens" in head else None
    if got != FLEET_LIFETIME:
        return False, (f"LIFETIME.md headline {got:,}; the ledger holds "
                       f"{ALPHA_GONE:,} more whose transcript is gone "
                       f"(expected {FLEET_LIFETIME:,})")
    lj = json.loads(gen(root, MACHINE_DIR, "lifetime.json")
                    .read_text(encoding="utf-8"))
    led = lj.get("ledger") or {}
    b, ch = led.get("bravo") or {}, led.get("charlie") or {}
    if b.get("present") is not False or ch.get("present") is not True:
        return False, ("bravo has no ledger file and charlie's is empty; "
                       f"lifetime.json reports {b!r} and {ch!r}")

    r2 = run(root, "combine.py")
    if r2.returncode != 0:
        return False, f"combine exit {r2.returncode}: {r2.stderr[-300:]}"
    ac = json.loads(gen(root, MACHINE_DIR, "ALL-COMPUTERS.json")
                    .read_text(encoding="utf-8"))
    a = [m for m in ac["machines"] if m["machine"] == "alpha"]
    if not a or a[0].get("ledger_total") != ALPHA_LEDGER:
        return False, ("ALL-COMPUTERS.json carries no ledger figure for alpha "
                       f"({a[0].get('ledger_total') if a else 'no row'})")
    return True, (f"LIFETIME.md {got:,} including {ALPHA_GONE:,} of vanished "
                  f"transcripts; absent and empty ledgers distinguished")


def C7(tmp):
    """A gap caused by transcripts that were never fetched, blamed on the export.

    bravo's MANIFEST.json — written by the export itself — says nine record
    files. Two are in the checkout. Its corpus figure is therefore below its
    scanned figure, and every such row got one sentence:

        | bravo | 200,000 | 1,145 | -198,855 | exported before the last scan |

    whose only remedy is "run export_corpus.py on bravo". That is the wrong
    machine and the wrong action. Measured against the real corpus, where the
    transcripts were untracked on 2026-08-09 and now ship as release assets:

        macbook-air-m1        53 exported,     1 present,  -13,675,684,823
        hp-laptop-linux    8,895 exported, 4,365 present,   -2,609,311,451

    16.28 B of published "gap" attributed to stale exports, on two machines
    whose exports had already run and written the files.
    """
    root = count_root(tmp)
    c, _ = corpus(tmp)
    r = run(root, "corpus_reports.py", "--corpus", str(c))
    cov = gen(c, HUMAN_DIR, "COVERAGE.md")
    if not cov.is_file():
        return False, f"no COVERAGE.md (exit {r.returncode}): {r.stderr[:200]}"
    row = table_row(cov.read_text(encoding="utf-8"), "bravo")
    if row is None:
        return False, "bravo has no row in the coverage table"
    why = row[-1]
    if "before the last scan" in why:
        return False, (f"bravo labelled {why!r} — its export wrote 9 files and "
                       f"2 are here; re-exporting changes nothing")
    if "not in this checkout" not in why:
        return False, f"bravo labelled {why!r} — says nothing about the 7 missing files"
    return True, f"bravo: {why[:88]}"


def C8(tmp):
    """Generators write only into the owned machine folder, never foreign ones.

    P4: fun_stats.py and monthly.py rewrote 12 tracked files in 4 other
    computers' folders (commit 4a5b42c). The fix — `token_ledger.this_machine`
    guard — must ensure bravo/ and charlie/ are untouched after a run.

    The test snapshots every file in bravo/ and charlie/ BEFORE running the
    generators, then diffs the snapshot AFTER. Any changed path is a foreign
    write. Measured against the unfixed code this test finds 12 paths.
    """
    root = count_root(tmp)

    foreign = [root / "bravo", root / "charlie"]
    before = snapshot(*foreign)

    run(root, "fun_stats.py")
    run(root, "monthly.py")

    after = snapshot(*foreign)

    new_files    = sorted(set(after) - set(before))
    changed      = sorted(k for k in before if after.get(k) != before[k])
    deleted      = sorted(set(before) - set(after))
    violations   = new_files + changed + deleted

    if violations:
        rel = [str(pathlib.Path(v).relative_to(root)) for v in violations[:6]]
        return False, (f"{len(violations)} foreign file(s) written: "
                       + ", ".join(rel)
                       + (" …" if len(violations) > 6 else ""))
    return True, "bravo/ and charlie/ untouched after fun_stats + monthly"


CHECKS = [("C1", C1), ("C2", C2), ("C3", C3), ("C4", C4), ("C5", C5),
          ("C6", C6), ("C7", C7), ("C8", C8)]


def main():
    want = set(sys.argv[1:])
    fails = 0
    run_n = 0
    for name, fn in CHECKS:
        if want and name not in want:
            continue
        run_n += 1
        tmp = tempfile.mkdtemp(prefix=f"adv-reports-{name}-")
        try:
            ok, detail = fn(tmp)
        except Exception as e:                                   # noqa: BLE001
            import traceback
            ok, detail = False, f"{type(e).__name__}: {e}\n" + \
                traceback.format_exc(limit=4)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        print(f"  {'PASS' if ok else 'FAIL'}  {name}  "
              f"{fn.__doc__.strip().splitlines()[0]}")
        if not ok:
            fails += 1
            for line in str(detail).splitlines():
                print(f"          {line}")
        else:
            print(f"          {detail}")
    print(f"\n  {run_n - fails} of {run_n} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
