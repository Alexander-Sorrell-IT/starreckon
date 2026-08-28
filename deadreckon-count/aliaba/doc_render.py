#!/usr/bin/env python3
"""The documents, and the fingerprint that stops them lying.

    python3 doc_render.py render      write every derived document
    python3 doc_render.py check       what state each one is in (exit 1 if any is bad)
    python3 doc_render.py archive     MOVE the bad ones into testing-archive/<stamp>/

THREE DOCUMENTS

    <machine>/human-readable/FOLDER.md   what is in that machine's folder: the
                                        log, and every other file, with what
                                        generated it and what it asserts
    human-readable/FLEET.md             a section per computer, and a TOTAL
    human-readable/DAEMON.md            what the retention daemon has recorded

Each is derived purely from inputs that live on disk — the machine folder's own
contents plus GENERATORS below, the set of machine folders, the daemon's boot
log. Nothing here is typed by a person, so nothing here can be right on the day
it was written and wrong by the next scan.

WHY THE FINGERPRINT EXISTS (PLAN.md P5.8)

A rollup generated from 2 machines sat on the front page, committed, while 5
machines sat committed beside it with complete scans dated EARLIER than the
rollup itself. The front page understated the fleet by 78,967,248,634 tokens and
every check passed, because every check asked whether the parts summed to the
whole they had been told to sum — and they did. Nothing asked WHICH parts.

A timestamp cannot answer that. A document generated at noon from two machines
is newer than five scans from the morning and still wrong. So every document
here carries the INPUT FINGERPRINT it was built from: which machine folders were
present, each one's scanner_version and generated_at, and a digest of each
folder's contents. `check` recomputes that fingerprint from the tree and reports
the difference, naming the machines that moved.

A derived document is in exactly one of two legal states:

    REGENERATED   its fingerprint matches the tree it claims to describe
    ARCHIVED      moved into testing-archive/<stamp>/documents/, gone from here

never STALE, and never DELETED. `archive` copies, verifies the copy byte for
byte, and only then unlinks — a stale report is EVIDENCE of what the system
believed, and destroying the wrong number destroys the proof of how it got that
way. A document that simply vanishes is reported as MISSING, loudly, because a
file nobody wrote and a file somebody removed must not look the same.

ABSENT IS NOT ZERO

The failure this repository keeps making is a store that cannot be read
returning 0 and every consistency check still passing. So: a machine folder with
no readable totals.json is not summed as zero — it is listed as UNCOUNTED and
the TOTAL is stamped INCOMPLETE. A ledger file that does not exist does not
report zero rows; it reports ABSENT. A file no generator claims is not omitted
from the folder document; it is listed as UNATTRIBUTED.

THE FINGERPRINT FORMAT, for anything that wants to read it

A fenced block, at the end of every document:

    ```input-fingerprint
    { "fingerprint_version": 1, "kind": "root", "digest": "sha256:...",
      "inputs": [ {"id": "hp-laptop-linux", "state": "scanned",
                   "scanner_version": "...", "generated_at": "...",
                   "files": 21, "content": "sha256:..."}, ... ] }
    ```

json.loads of the text between the fences, or `doc_render.read_fingerprint(p)`.
`doc_render.document_state(path, root)` returns the verdict directly.
"""

import argparse
import datetime
import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import paths                                                     # noqa: E402

FINGERPRINT_FENCE = "input-fingerprint"
FINGERPRINT_VERSION = 1
GENERATOR = "doc_render.py"

MACHINE_DOC = "FOLDER.md"          # under <machine>/human-readable/
FLEET_DOC = "FLEET.md"             # under human-readable/
DAEMON_DOC = "DAEMON.md"           # under human-readable/

# Written by this file, so excluded from the digests this file computes.
# Named, not pattern-matched, and reported inside the fingerprint itself so a
# reader can see exactly what was left out rather than inferring it.
SELF_WRITTEN = (f"{paths.HUMAN}/{MACHINE_DOC}",)

DEFAULT_BOOTLOG = pathlib.Path.home() / ".local" / "share" / "retention_guard.boots.jsonl"


# ---------------------------------------------------------------------------
# THE GENERATOR REGISTRY.
#
# name -> (generator, what the file asserts). The folder document is derivable
# from the folder plus this table and nothing else, which is the property that
# keeps it honest: a file appears in the document because it is ON DISK, not
# because someone remembered to add a line about it.
#
# A file no entry claims is reported UNATTRIBUTED rather than skipped. That is
# PLAN P5.7 — residue written by an approach that was abandoned simply STAYS,
# and the only thing that would notice is a person who happens to look.

GENERATORS = {
    ".machine-id": (
        "update.py",
        "which computer owns this folder, by hostname"),
    f"{paths.MACHINE}/totals.json": (
        "sessions.py (scan) / analyze_tokens.py",
        "this machine's grand total, per account, with scanner_version and generated_at"),
    f"{paths.MACHINE}/sessions.json": (
        "sessions.py",
        "every session read on this machine, per CLI, and the frozen stats_cache"),
    f"{paths.MACHINE}/hardware.json": (
        "check_hardware.py",
        "what this computer is: chip, cores, memory"),
    f"{paths.MACHINE}/stats.json": (
        "fun_stats.py",
        "the STATS.md figures as data"),
    f"{paths.MACHINE}/lifetime.json": (
        "monthly.py",
        "lifetime totals rolled up from the months"),
    f"{paths.MACHINE}/scorecard.json": (
        "scorecard.py",
        "which artifacts this machine has, and which are missing"),
    f"{paths.MACHINE}/MANIFEST.json": (
        "export_corpus.py / count_corpus.py",
        "what the corpus export carried for this machine"),
    f"{paths.MACHINE}/token_ledger.jsonl": (
        "token_ledger.py",
        "THE LOG — append-only observations of every session, the lifetime total "
        "nothing can take away"),
    f"{paths.MACHINE}/by_account.csv": (
        "analyze_tokens.py", "tokens sliced by account"),
    f"{paths.MACHINE}/by_day.csv": (
        "analyze_tokens.py", "tokens sliced by day, attributed to session start"),
    f"{paths.MACHINE}/by_model.csv": (
        "analyze_tokens.py", "tokens sliced by model"),
    f"{paths.MACHINE}/by_project.csv": (
        "analyze_tokens.py", "tokens sliced by project"),
    f"{paths.HUMAN}/REPORT.md": (
        "analyze_tokens.py", "this machine's report, rendered"),
    f"{paths.HUMAN}/STATS.md": (
        "fun_stats.py", "the readable statistics for this machine"),
    f"{paths.HUMAN}/BY-ACCOUNT.md": (
        "stats_page.py", "this machine's tokens per account"),
    f"{paths.HUMAN}/BY-COMPANY.md": (
        "stats_page.py", "this machine's tokens per vendor"),
    f"{paths.HUMAN}/THIS-MONTH.md": (
        "monthly.py", "the current month for this machine"),
    f"{paths.HUMAN}/LIFETIME.md": (
        "monthly.py", "every month this machine has recorded"),
    f"{paths.HUMAN}/SCORECARD.md": (
        "scorecard.py", "the scorecard, rendered"),
    f"{paths.HUMAN}/{MACHINE_DOC}": (
        GENERATOR, "this document: the folder, described from its own contents"),
}

# Directory prefixes whose members share one entry.
GENERATOR_DIRS = {
    f"{paths.MACHINE}/months/": (
        "monthly.py", "one month of this machine, as data"),
    f"{paths.MACHINE}/tools/": (
        "export_corpus.py", "an exported tool store for this machine"),
}

UNATTRIBUTED = ("**UNATTRIBUTED**",
                "no generator in the registry claims this file — residue, PLAN P5.7")

# Attributable AND still wrong to have here. Naming the writer is more useful
# than "nobody claims this", but it must not stop the row being counted: a file
# that is explained is not a file that belongs. Found by this tool on the first
# real run — hp-laptop-linux carries a committed, empty token_ledger.jsonl.lock.
RESIDUE = {
    f"{paths.MACHINE}/token_ledger.jsonl.lock": (
        "token_ledger.py (its lock, not its output)",
        "**RESIDUE** — the lock `token_ledger.record()` takes while appending. "
        "It is not data, it is not read by anything, and a committed one is a "
        "development artifact that outlived the run that made it"),
}


def generator_of(rel):
    """(generator, assertion, needs_attention) for a machine-relative path."""
    if rel in RESIDUE:
        return (*RESIDUE[rel], True)
    if rel in GENERATORS:
        return (*GENERATORS[rel], False)
    for prefix, ent in GENERATOR_DIRS.items():
        if rel.startswith(prefix):
            return (*ent, False)
    if rel.endswith(".lock"):
        return ("a lock file", "**RESIDUE** — a lock left behind by whatever "
                "was writing here; not data", True)
    return (*UNATTRIBUTED, True)


# ---------------------------------------------------------------------------
# Fingerprints.

def _now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def _sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _digest(obj):
    return "sha256:" + hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def folder_files(mdir, exclude=SELF_WRITTEN):
    """Every file in a machine folder, relative path -> (size, sha256).

    Excludes only what THIS file writes, because a document cannot be an input
    to itself: including FOLDER.md would make every regeneration change the
    digest that regeneration was supposed to satisfy.
    """
    mdir = pathlib.Path(mdir)
    out = {}
    for p in sorted(mdir.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(mdir).as_posix()
        if rel in exclude:
            continue
        try:
            out[rel] = (p.stat().st_size, _sha_file(p))
        except OSError as e:
            # A file that cannot be READ is not a file that is not there.
            out[rel] = (-1, f"unreadable: {e.__class__.__name__}")
    return out


def _content_digest(files):
    return _digest([[rel, sz, sha] for rel, (sz, sha) in sorted(files.items())])


def _machine_input(mdir, name=None, files=None):
    """One input entry for a machine folder that EXISTS on disk."""
    mdir = pathlib.Path(mdir)
    files = folder_files(mdir) if files is None else files
    ent = {"id": name or mdir.name, "state": "scanned",
           "scanner_version": None, "generated_at": None,
           "files": len(files), "content": _content_digest(files)}
    tf = paths.find(mdir, "totals.json")
    if tf is None:
        # Present, but nothing says what scanner produced it or when.
        ent["state"] = "no-totals"
        return ent
    try:
        t = json.loads(tf.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001 - the reason is the point
        ent["state"] = "unreadable"
        ent["error"] = f"{e.__class__.__name__}: {e}"
        return ent
    ent["scanner_version"] = t.get("scanner_version")
    ent["generated_at"] = t.get("generated_at")
    ent["total_tokens"] = t.get("grand_total_tokens")
    ent["label"] = t.get("machine")
    return ent


def _roster(root):
    """Folders named in machines.json. The authored roster, not a guess."""
    f = pathlib.Path(root) / "machines.json"
    if not f.is_file():
        return []
    try:
        return [m.get("folder") for m in
                json.loads(f.read_text(encoding="utf-8")).get("machines", [])
                if m.get("folder")]
    except Exception:  # noqa: BLE001
        return []


_NOT_MACHINE = set(paths.NOT_A_MACHINE) | {"vendor", "node_modules", "tests"}


def candidate_machine_dirs(root):
    """Directories that are a machine folder, INCLUDING broken ones.

    `paths.machine_folders` asks for totals.json, which is a test of CONTENT
    being used as a test of EXISTENCE: a folder whose scan was interrupted, or
    whose totals.json is corrupt, is simply not returned, and a fleet document
    built from that list reports five of six machines and calls it every.

    A directory here is a machine folder if the roster names it, or it carries a
    .machine-id, or a totals.json, or one of the two split output folders. What
    is inside it is then classified separately, which is the only way "present
    but broken" and "not there" can read differently.
    """
    root = pathlib.Path(root)
    roster = set(_roster(root))
    out = []
    if not root.is_dir():
        return out
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        if d.name in _NOT_MACHINE or d.name.startswith("."):
            continue
        if (d.name in roster or (d / ".machine-id").is_file()
                or paths.find(d, "totals.json")
                or (d / paths.MACHINE).is_dir() or (d / paths.HUMAN).is_dir()):
            out.append(d)
    return out


def fleet_inputs(root):
    """Every input to a root document: present folders AND rostered absences."""
    root = pathlib.Path(root)
    dirs = candidate_machine_dirs(root)
    inputs = [_machine_input(d) for d in dirs]
    have = {d.name for d in dirs}
    for name in sorted(set(_roster(root)) - have):
        # In the roster, no folder on disk. Recorded as an INPUT so the document
        # says "never scanned" instead of the machine being invisible.
        inputs.append({"id": name, "state": "absent", "scanner_version": None,
                       "generated_at": None, "files": 0, "content": None})
    return sorted(inputs, key=lambda e: e["id"])


def _root_state(root):
    root = pathlib.Path(root)
    if not root.is_dir():
        return "missing"
    return "populated" if candidate_machine_dirs(root) else "empty"


def _daemon_inputs(log):
    log = pathlib.Path(log)
    ent = {"id": str(log), "state": "absent", "scanner_version": None,
           "generated_at": None, "files": 0, "content": None}
    if not log.exists():
        return [ent]
    try:
        raw = log.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        ent["state"] = "unreadable"
        ent["error"] = f"{e.__class__.__name__}"
        return [ent]
    rows = [ln for ln in raw.splitlines() if ln.strip()]
    ent["state"] = "present" if rows else "empty"
    ent["files"] = 1
    ent["rows"] = len(rows)
    ent["content"] = _digest([raw])
    return [ent]


def tree_fingerprint(root, kind, machine=None, log=None):
    """What the tree says right now, in the shape a document records."""
    root = pathlib.Path(root)
    if kind == "machine":
        mdir = pathlib.Path(machine)
        inputs = [_machine_input(mdir)] if mdir.is_dir() else [
            {"id": mdir.name, "state": "absent", "scanner_version": None,
             "generated_at": None, "files": 0, "content": None}]
        scope, state = mdir.name, ("populated" if mdir.is_dir() else "missing")
        doc = f"{mdir.name}/{paths.HUMAN}/{MACHINE_DOC}"
    elif kind == "root":
        inputs, scope, state = fleet_inputs(root), "fleet", _root_state(root)
        doc = f"{paths.HUMAN}/{FLEET_DOC}"
    elif kind == "daemon":
        log = DEFAULT_BOOTLOG if log is None else log
        inputs, scope = _daemon_inputs(log), "daemon"
        state = inputs[0]["state"]
        doc = f"{paths.HUMAN}/{DAEMON_DOC}"
    else:
        raise ValueError(f"unknown document kind {kind!r}")

    fp = {"fingerprint_version": FINGERPRINT_VERSION,
          "spec": "the inputs this document was built from; recompute with "
                  "doc_render.tree_fingerprint(root, kind) and compare 'digest'",
          "generator": GENERATOR,
          "document": doc,
          "kind": kind,
          "scope": scope,
          "generated_at": _now(),
          "tree_state": state,
          "excluded_from_digests": list(SELF_WRITTEN),
          "inputs": inputs}
    # The digest covers the INPUTS and the tree state, never generated_at — two
    # documents built from the same tree must agree, whatever the clock said.
    fp["digest"] = _digest({"tree_state": state, "inputs": inputs})
    return fp


def read_fingerprint(path):
    """The fingerprint a document carries, or None if it carries none."""
    p = pathlib.Path(path)
    if not p.is_file():
        return None
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    open_fence = "```" + FINGERPRINT_FENCE
    for i, ln in enumerate(lines):
        if ln.strip() == open_fence:
            body = []
            for ln2 in lines[i + 1:]:
                if ln2.strip() == "```":
                    try:
                        return json.loads("\n".join(body))
                    except Exception:  # noqa: BLE001 - malformed is not absent
                        return {"_malformed": True}
                body.append(ln2)
            return {"_malformed": True}
    return None


def compare(stored, current):
    """(matches, [reasons]). Reasons name the machines, not just 'differs'."""
    if stored is None:
        return False, ["the document carries no input fingerprint"]
    if stored.get("_malformed"):
        return False, ["the document's input fingerprint is not valid JSON"]
    if stored.get("fingerprint_version") != current["fingerprint_version"]:
        return False, [f"fingerprint_version {stored.get('fingerprint_version')} "
                       f"!= {current['fingerprint_version']}"]
    if stored.get("digest") == current["digest"]:
        return True, []

    why = []
    if stored.get("tree_state") != current["tree_state"]:
        why.append(f"tree state {stored.get('tree_state')} -> {current['tree_state']}")
    was = {e.get("id"): e for e in stored.get("inputs", [])}
    now = {e.get("id"): e for e in current["inputs"]}
    for i in sorted(set(now) - set(was)):
        why.append(f"{i}: present now, was not an input")
    for i in sorted(set(was) - set(now)):
        why.append(f"{i}: was an input, is gone")
    for i in sorted(set(was) & set(now)):
        a, b = was[i], now[i]
        for field in ("state", "scanner_version", "generated_at"):
            if a.get(field) != b.get(field):
                why.append(f"{i}: {field} {a.get(field)!r} -> {b.get(field)!r}")
        if a.get("content") != b.get("content"):
            # "(25 -> 25 file(s))" reads like nothing happened. A rescan that
            # rewrites the numbers in place changes no file count at all, and
            # that is the case this whole file exists for.
            why.append(f"{i}: folder contents changed — same {b.get('files')} "
                       f"file(s), different bytes"
                       if a.get("files") == b.get("files") else
                       f"{i}: folder contents changed "
                       f"({a.get('files')} -> {b.get('files')} file(s))")
    # A timestamp cannot say WHICH inputs, but it can still catch the case the
    # digest cannot see: an input newer than the document that claims it.
    doc_at = stored.get("generated_at") or ""
    for i, b in sorted(now.items()):
        at = b.get("generated_at") or ""
        if at and doc_at and at > doc_at:
            why.append(f"{i}: scanned {at}, AFTER this document was written {doc_at}")
    if not why:
        why.append("digest differs (no field-level difference isolated)")
    return False, why


# ---------------------------------------------------------------------------
# States.

REGENERATED, STALE, MISSING, ARCHIVED = "REGENERATED", "STALE", "MISSING", "ARCHIVED"


def archived_copies(root, rel):
    """Every testing-archive copy of a document, newest stamp last."""
    ta = pathlib.Path(root) / "testing-archive"
    if not ta.is_dir():
        return []
    out = []
    for stamp in sorted(p for p in ta.iterdir() if p.is_dir()):
        c = stamp / "documents" / rel
        if c.is_file():
            out.append(c)
    return out


def document_state(path, root, kind, machine=None, log=None):
    """(state, [reasons]) for one derived document."""
    path, root = pathlib.Path(path), pathlib.Path(root)
    rel = path.relative_to(root).as_posix()
    if not path.is_file():
        copies = archived_copies(root, rel)
        if copies:
            return ARCHIVED, [f"moved to {copies[-1].relative_to(root).as_posix()}"]
        return MISSING, ["never generated, and no copy in testing-archive"]
    ok, why = compare(read_fingerprint(path),
                      tree_fingerprint(root, kind, machine=machine, log=log))
    return (REGENERATED, []) if ok else (STALE, why)


def expected_documents(root, log=None):
    """Every document this structure requires: (path, kind, machine)."""
    root = pathlib.Path(root)
    out = [(root / paths.HUMAN / FLEET_DOC, "root", None),
           (root / paths.HUMAN / DAEMON_DOC, "daemon", None)]
    for d in candidate_machine_dirs(root):
        out.append((d / paths.HUMAN / MACHINE_DOC, "machine", d))
    return out


def survey(root, log=None):
    """[{document, state, why}] for every derived document, in report order."""
    rows = []
    for path, kind, mdir in expected_documents(root, log=log):
        state, why = document_state(path, root, kind, machine=mdir, log=log)
        rows.append({"document": pathlib.Path(path).relative_to(root).as_posix(),
                     "kind": kind, "state": state, "why": why})
    return rows


def stale_documents(root, log=None):
    """The rows `status` must shout about: STALE or MISSING, never ARCHIVED."""
    return [r for r in survey(root, log=log) if r["state"] in (STALE, MISSING)]


# ---------------------------------------------------------------------------
# Rendering.

def _fence(fp):
    return ["", "## Input fingerprint", "",
            f"Built from {len(fp['inputs'])} input(s); tree state "
            f"`{fp['tree_state']}`; digest `{fp['digest'][:23]}…`. A document "
            "whose fingerprint no longer matches the tree is STALE and "
            "`python3 run.py status` says so.", "",
            "| Input | State | Scanner | Scanned | Files |",
            "|---|---|---|---|---:|"] + [
        f"| `{e['id']}` | {e['state']} | `{e.get('scanner_version') or '—'}` | "
        f"{str(e.get('generated_at') or '—')[:19]} | {e.get('files', 0):,} |"
        for e in fp["inputs"]] + [
        "", "```" + FINGERPRINT_FENCE,
        json.dumps(fp, indent=2), "```", ""]


def _log_section(mdir):
    """The machine's log. ABSENT is a state, not a row count of zero."""
    L = ["## The log", ""]
    p = paths.find(mdir, "token_ledger.jsonl")
    if p is None:
        L += ["`machine-readable/token_ledger.jsonl` — **ABSENT**. No ledger has "
              "ever been written for this machine.", "",
              "That is not the same as a ledger holding zero observations. An "
              "absent log means nothing has ever recorded what this computer "
              "spent; an empty one means something looked and found nothing.", ""]
        return L
    try:
        raw = p.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        L += [f"`{p.name}` — **UNREADABLE** ({e.__class__.__name__}). The file is "
              "there and its contents could not be read, which is not zero.", ""]
        return L
    rows, bad = [], 0
    for ln in raw.splitlines():
        if not ln.strip():
            continue
        try:
            rows.append(json.loads(ln))
        except Exception:  # noqa: BLE001
            bad += 1
    sids = {(r.get("cli"), r.get("session_id")) for r in rows}
    obs = sorted(r.get("observed") for r in rows if r.get("observed"))
    scanners = sorted({r.get("scanner") for r in rows if r.get("scanner")})
    L += [f"`{p.relative_to(mdir).as_posix()}` — append-only, written by "
          "`token_ledger.py`. Every observation of every session; a deleted "
          "transcript cannot lower it, a corrected counter can.", "",
          "| | |", "|---|---:|",
          f"| observations | {len(rows):,} |",
          f"| distinct sessions | {len(sids):,} |",
          f"| unparseable lines | {bad:,} |",
          f"| first observed | {obs[0][:19] if obs else '—'} |",
          f"| last observed | {obs[-1][:19] if obs else '—'} |",
          f"| scanners that wrote it | {', '.join(f'`{s}`' for s in scanners) or '—'} |"]
    if not rows:
        L += ["", "The ledger is **EMPTY**: the file exists and holds no "
              "observations. Something wrote it and had nothing to record."]
    try:
        import token_ledger
        lt = token_ledger.lifetime(mdir)
        L += [f"| lifetime it stands behind | {lt['total']:,} across "
              f"{lt['sessions']:,} session(s) |"]
    except Exception as e:  # noqa: BLE001 - say why, never print a silent 0
        L += [f"| lifetime it stands behind | not computed: "
              f"{e.__class__.__name__}: {e} |"]
    L.append("")
    return L


def render_machine(root, mdir):
    """<machine>/human-readable/FOLDER.md — from the folder and the registry."""
    root, mdir = pathlib.Path(root), pathlib.Path(mdir)
    files = folder_files(mdir)
    fp = tree_fingerprint(root, "machine", machine=mdir)
    ent = fp["inputs"][0]
    label = ent.get("label") or mdir.name

    L = [f"# {label} — what is in `{mdir.name}/`", "",
         f"_Derived. Generated by `{GENERATOR}` from this folder's own contents "
         "plus the generator registry. Every row below is here because the file "
         "is on disk, not because anybody remembered to mention it. Do not edit "
         "by hand._", ""]
    if ent["state"] != "scanned":
        L += [f"> **This folder is `{ent['state']}`.** "
              + {"no-totals": "There is no readable `totals.json`, so nothing here "
                              "says which scanner produced these files or when. "
                              "The fleet document counts this machine as "
                              "UNCOUNTED rather than as zero.",
                 "unreadable": f"`totals.json` exists and could not be parsed "
                               f"({ent.get('error')}). Present and unreadable is "
                               f"not the same as absent, and neither is zero.",
                 "absent": "The folder is not on disk."}.get(ent["state"], ""), ""]
    else:
        L += ["| | |", "|---|---|",
              f"| scanner | `{ent['scanner_version']}` |",
              f"| scanned | {ent['generated_at']} |",
              f"| grand total | {(ent.get('total_tokens') or 0):,} tokens |",
              f"| files in this folder | {len(files):,} |", ""]

    L += _log_section(mdir)
    L += ["## The other files", "",
          "Every file in this folder, what generated it, and what it asserts. "
          "A file the registry does not claim is listed as UNATTRIBUTED — it is "
          "residue from an approach that was abandoned, and nothing else in this "
          "repository would ever mention it.", "",
          "| File | Bytes | Generated by | What it asserts |",
          "|---|---:|---|---|"]
    flagged = 0
    for rel, (size, sha) in sorted(files.items()):
        if rel == f"{paths.MACHINE}/token_ledger.jsonl":
            continue                                     # its own section above
        gen, says, attention = generator_of(rel)
        flagged += bool(attention)
        shown = f"{size:,}" if size >= 0 else "unreadable"
        L.append(f"| `{rel}` | {shown} | {gen} | {says} |")
    if not files:
        L.append("| _none_ | | | the folder holds no files at all |")
    L += ["", f"{len(files):,} file(s); {flagged:,} that do not belong to a "
          f"generator this folder should still be carrying."
          + (" Every file is attributable to a generator that still exists."
             if not flagged else
             " Each UNATTRIBUTED or RESIDUE row is either a generator this "
             "registry has not been told about, or an artifact a `retire` "
             "should relocate.")]
    L += _fence(fp)

    out = paths.human(mdir) / MACHINE_DOC
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    return out


def render_root(root):
    """human-readable/FLEET.md — a section per computer, and a TOTAL."""
    root = pathlib.Path(root)
    fp = tree_fingerprint(root, "root")
    inputs = fp["inputs"]

    L = ["# The fleet — a section per computer, and the total", "",
         f"_Derived. Generated by `{GENERATOR}` from every machine folder in "
         "this repository. The TOTAL below is recomputed from those folders "
         "every time this document is written, and the input fingerprint at the "
         "end names exactly which folders it was. Do not edit by hand._", ""]

    counted, uncounted = [], []
    for e in inputs:
        if e["state"] == "scanned" and isinstance(e.get("total_tokens"), int):
            counted.append(e)
        else:
            uncounted.append(e)

    uncounted_ids = {e["id"] for e in uncounted}
    for e in inputs:
        label = e.get("label") or e["id"]
        L += [f"## {label} (`{e['id']}/`)", ""]
        if e["id"] in uncounted_ids:
            L += [f"**UNCOUNTED — {e['state']}.** "
                  + {"absent": "The roster names this computer and there is no "
                               "folder for it. It has never been scanned. It "
                               "contributes nothing to the TOTAL, and the TOTAL "
                               "says so rather than treating it as zero.",
                     "no-totals": "The folder is here; there is no readable "
                                  "`totals.json` in it. A folder that cannot be "
                                  "read is not a computer that spent nothing.",
                     "unreadable": f"`totals.json` is present and could not be "
                                   f"parsed ({e.get('error')})."}.get(
                        e["state"], "This folder could not be counted."), ""]
        else:
            L += ["| | |", "|---|---|",
                  f"| tokens | {e['total_tokens']:,} |",
                  f"| scanner | `{e['scanner_version']}` |",
                  f"| scanned | {e['generated_at']} |",
                  f"| files | {e['files']:,} |", ""]
        doc = root / e["id"] / paths.HUMAN / MACHINE_DOC
        if (root / e["id"]).is_dir():
            st, why = document_state(doc, root, "machine", machine=root / e["id"])
            # AT RENDER TIME, and said so. This document's fingerprint covers
            # the machine folders, not the machine documents — a document is
            # not an input to a document about the same data. So this line is
            # a reading, not a guarantee; `run.py status` is the live answer
            # and reports each document on its own.
            L += [f"Folder document `{e['id']}/{paths.HUMAN}/{MACHINE_DOC}` was "
                  f"**{st}** when this was written"
                  + (f" ({'; '.join(why)})" if why else "") + ".", ""]

    total = sum(e["total_tokens"] for e in counted)
    complete = not uncounted
    L += ["## TOTAL", "",
          f"**{total:,} tokens** across **{len(counted)} of "
          f"{len(inputs)} computers**.", "",
          f"This is the sum of `grand_total_tokens` over the machine folders "
          f"named in the fingerprint below — the same field `combine.py` sums. "
          f"It changes whenever any of those folders changes, because this "
          f"document is regenerated from them and its fingerprint stops it "
          f"being read as current when it has not been.", ""]
    if complete:
        L += ["**COMPLETE** — every computer in the roster and on disk was "
              "counted.", ""]
    else:
        L += [f"**INCOMPLETE — {len(uncounted)} computer(s) contributed nothing "
              f"and were not counted as zero:**", ""]
        L += [f"- `{e['id']}` — {e['state']}" for e in uncounted]
        L += ["", "A total over a subset is a floor, not a fleet total. This is "
              "the exact shape of the failure that put a 2-machine rollup on the "
              "front page beside 5 committed scans and understated the fleet by "
              "78,967,248,634 tokens.", ""]
    L += _fence(fp)

    out = paths.human(root) / FLEET_DOC
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    return out


def render_daemon(root, log=None):
    """human-readable/DAEMON.md — what the retention daemon has recorded."""
    root = pathlib.Path(root)
    log = DEFAULT_BOOTLOG if log is None else pathlib.Path(log)
    fp = tree_fingerprint(root, "daemon", log=log)
    ent = fp["inputs"][0]

    L = ["# The retention daemon — what it has recorded", "",
         f"_Derived. Generated by `{GENERATOR}` from the daemon's own boot log. "
         "Do not edit by hand._", "",
         f"Boot log: `{ent['id']}`", ""]
    if ent["state"] == "absent":
        L += ["**ABSENT.** There is no boot log at that path.", "",
              "This is not a report of zero boots. A daemon that has never "
              "started and a daemon whose log cannot be found produce the same "
              "silence, and only one of them is a working system. "
              "`retention_guard.verify_boot()` swallows the error and shows an "
              "empty history for both.", ""]
    elif ent["state"] == "unreadable":
        L += [f"**UNREADABLE** ({ent.get('error')}). The log is there and could "
              "not be read. That is not zero boots.", ""]
    else:
        rows, bad = [], 0
        for ln in log.read_text(encoding="utf-8", errors="replace").splitlines():
            if not ln.strip():
                continue
            try:
                rows.append(json.loads(ln))
            except Exception:  # noqa: BLE001
                bad += 1
        boots = sorted({r.get("boot_id") for r in rows if r.get("boot_id")})
        starts = sorted(r.get("started") for r in rows if r.get("started"))
        delays = [r["delay_s"] for r in rows if isinstance(r.get("delay_s"), int)]
        fmt = lambda t: datetime.datetime.fromtimestamp(t).astimezone().isoformat(
            timespec="seconds")
        L += ["| | |", "|---|---:|",
              f"| start records | {len(rows):,} |",
              f"| unparseable lines | {bad:,} |",
              f"| distinct boots covered | {len(boots):,} |",
              f"| first start | {fmt(starts[0]) if starts else '—'} |",
              f"| last start | {fmt(starts[-1]) if starts else '—'} |",
              f"| slowest start after boot | "
              f"{max(delays) if delays else '—'} s |", ""]
        if not rows:
            L += ["**EMPTY.** The log exists and holds no start records: "
                  "something created it and the daemon has never come up under "
                  "any boot. Distinct from ABSENT above, deliberately.", ""]
    L += _fence(fp)

    out = paths.human(root) / DAEMON_DOC
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    return out


def render_all(root, log=None):
    root = pathlib.Path(root)
    written = [render_machine(root, d) for d in candidate_machine_dirs(root)]
    # The root document reads each machine document's state, so it is written
    # after them; otherwise it would report every folder document as STALE by
    # describing a tree one step older than the one it just built.
    written.append(render_root(root))
    written.append(render_daemon(root, log=log))
    return written


# ---------------------------------------------------------------------------
# Archiving. A relocation, never a deletion.

def archive_document(root, path, stamp=None, reason=""):
    """Copy into testing-archive/<stamp>/documents/, verify, THEN unlink.

    The order is the whole point. A move that fails halfway must leave the
    document where it was, not nowhere: a stale report is evidence of what the
    system believed, and this repository has already deleted one testing archive
    it had to restore from git.
    """
    root, path = pathlib.Path(root), pathlib.Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    stamp = stamp or datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H-%M-%S")
    rel = path.relative_to(root).as_posix()
    dest = root / "testing-archive" / stamp / "documents" / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    src_sha = _sha_file(path)
    dest.write_bytes(path.read_bytes())
    if not dest.is_file() or _sha_file(dest) != src_sha:
        raise OSError(f"archive copy of {rel} did not verify — original kept")
    note = root / "testing-archive" / stamp / "documents" / "MOVED.md"
    line = (f"- `{rel}` — sha256 `{src_sha[:16]}…`, moved "
            f"{_now()}{(' — ' + reason) if reason else ''}\n")
    if not note.is_file():
        note.write_text("# Documents moved here, not deleted\n\n"
                        "Each line is a derived document whose input "
                        "fingerprint no longer matched the tree. The content is "
                        "kept because it is the record of what the system "
                        "believed at that moment.\n\n", encoding="utf-8")
    with open(note, "a", encoding="utf-8") as fh:
        fh.write(line)
    path.unlink()
    return dest


def archive_stale(root, log=None, stamp=None):
    stamp = stamp or datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H-%M-%S")
    moved = []
    for r in survey(root, log=log):
        if r["state"] == STALE:
            moved.append(archive_document(root, pathlib.Path(root) / r["document"],
                                          stamp=stamp, reason="; ".join(r["why"])))
    return stamp, moved


# ---------------------------------------------------------------------------

def print_survey(root, log=None):
    rows = survey(root, log=log)
    if not rows:
        print("  no derived documents are expected here — no machine folders")
        return 0
    bad = 0
    for r in rows:
        mark = {REGENERATED: "", ARCHIVED: "  (in testing-archive)"}.get(r["state"], "")
        print(f"  {r['state']:<12} {r['document']}{mark}")
        for w in r["why"] if r["state"] in (STALE, MISSING) else []:
            print(f"                 - {w}")
        if r["state"] in (STALE, MISSING):
            bad += 1
    print(f"\n  {len(rows)} derived document(s), {bad} that do not describe this tree")
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("verb", choices=["render", "check", "archive"])
    ap.add_argument("--root", default=str(pathlib.Path(__file__).resolve().parent))
    ap.add_argument("--daemon-log", default=None)
    ap.add_argument("--yes", action="store_true", help="required by `archive`")
    a = ap.parse_args()
    root = pathlib.Path(a.root)

    if a.verb == "render":
        for p in render_all(root, log=a.daemon_log):
            print(f"  wrote {pathlib.Path(p).relative_to(root).as_posix()}")
        return 0
    if a.verb == "check":
        return print_survey(root, log=a.daemon_log)
    if a.verb == "archive":
        rows = [r for r in survey(root, log=a.daemon_log) if r["state"] == STALE]
        if not rows:
            print("  nothing stale — nothing to move")
            return 0
        if not a.yes:
            for r in rows:
                print(f"  would move {r['document']} -> testing-archive/<stamp>/documents/")
            print("\n  Nothing is deleted. Re-run with --yes to move them.")
            return 0
        stamp, moved = archive_stale(root, log=a.daemon_log)
        for m in moved:
            print(f"  moved {pathlib.Path(m).relative_to(root).as_posix()}")
        print(f"\n  {len(moved)} document(s) into testing-archive/{stamp}/documents/")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
