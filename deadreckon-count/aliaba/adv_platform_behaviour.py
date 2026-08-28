#!/usr/bin/env python3
"""Platform attacks that run on Linux, and one canary that proves they can fail.

    python3 adv_platform_behaviour.py

Four adversaries. Each was written to FAIL against the code as it stands, and
each was run against that code first — a test written beside a fix asserts what
the fix does, which is not the same thing as catching the defect.

  1  adv_shim_canary        every profile's canary FAILS bare and PASSES shimmed
  2  adv_windows_newlines   the manifest's two byte accountings disagree under
                            newline translation, in opposite directions
  3  adv_maxpath_budget     the folded output name is bounded by NAME_MAX and
                            nothing bounds the PATH, which is what Windows caps
  4  adv_eperm_is_not_enoent   a store that cannot be read and a store that was
                            deleted produce the same number, and every
                            consistency check still passes

WHY 1 COMES FIRST

2 and 3 depend on `platform_sim` actually shimming. On a Linux host a shim that
quietly stopped installing makes every Windows assertion pass, because the
un-shimmed answer is the answer the code was written for. So the canary runs
first and its failure is reported as a failure of the SUITE, not of the code
under test: without it the rest is theatre.

WHY 4 IS SHIMLESS

EACCES is real here. `chmod 000` on Linux is the genuine article, and the bug it
exposes — a directory that cannot be entered counted as a directory holding
nothing — needs no simulation and would be weakened by one.
"""

import contextlib
import json
import os
import ast
import pathlib
import shutil
import stat
import subprocess
import sys
import tempfile
import traceback

REPO = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, REPO)

import export_corpus                 # noqa: E402
import platform_sim as PS            # noqa: E402
import stores                        # noqa: E402

WIN_PREFIX = r"C:\Users\phantomcore"
MAX_PATH = 260

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if detail:
        for line in str(detail).splitlines():
            print(f"          {line}")
    return bool(ok)


def note(text):
    for line in str(text).splitlines():
        print(f"        . {line}")


# ---------------------------------------------------------------------------
# 1  adv_shim_canary
# ---------------------------------------------------------------------------

def adv_shim_canary():
    """Every profile's canary must FAIL bare and PASS shimmed.

    Both halves are load-bearing and they catch opposite breakages.

      PASSES BARE   the probe is not probing. A canary that holds on plain
                    Linux is asserting something the shim never had to provide,
                    so it cannot notice the shim being gone.
      FAILS SHIMMED the shim is broken, or CPython moved the call site out from
                    under it — pathlib.Path.open going through something other
                    than io.open would do exactly this and nothing else in the
                    suite would say a word.
    """
    root = os.path.realpath(tempfile.mkdtemp(prefix="advplat-canary-"))
    try:
        for name in sorted(PS.PROFILES):
            bare_ok, bare_bad = PS.run_canary(name, os.path.join(root, name, "bare"))
            with PS.shim(name, root, WIN_PREFIX):
                on_ok, on_bad = PS.run_canary(name, os.path.join(root, name, "on"))
            check(f"canary {name}: FAILS bare", not bare_ok,
                  "" if not bare_ok else
                  "the probe passed with no shim installed — it is not testing "
                  "the shim, and cannot notice the shim disappearing")
            check(f"canary {name}: PASSES shimmed", on_ok,
                  "\n".join(on_bad))
            if not bare_ok:
                note(f"{name} bare, {len(bare_bad)} probe(s) refused: "
                     + "; ".join(b.split(";")[0] for b in bare_bad[:3])
                     + (" ..." if len(bare_bad) > 3 else ""))
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------------------
# the export driver, run in a child process
# ---------------------------------------------------------------------------
#
# A child, not this process, for two reasons. platform_sim replaces io.open for
# the whole interpreter, and this harness has to keep writing its own files
# with its own line endings while the export runs under Windows rules. And the
# export is driven through export_corpus.main() with --home and --out both
# under a temp directory and both archives disabled, so nothing it does can
# reach a real profile or the repository's own corpus/.

_DRIVER = r'''
import contextlib, json, os, sys, traceback
REPO = sys.argv[1]
sys.path.insert(0, REPO)
profile, root, home, out, recfile = sys.argv[2:7]
import platform_sim as PS
import export_corpus as EC

calls = []
_real = EC.out_name
def spy(rel, limit, taken=()):
    n = _real(rel, limit, taken)
    calls.append({"rel": rel.as_posix(), "limit": limit, "name": n})
    return n
EC.out_name = spy

sys.argv = ["export_corpus.py", "--home", home, "--out", out,
            "--keep-email", "", "--archive", "", "--archive-other", ""]
err = None
ctx = PS.shim(profile, root) if profile != "bare" else contextlib.nullcontext()
with ctx:
    try:
        EC.main()
    except BaseException:
        err = traceback.format_exc()
# written OUTSIDE the shim root on purpose: this file is the harness talking to
# itself and must not be translated by the platform under test.
with open(recfile, "w") as fh:
    json.dump({"out_name_calls": calls, "error": err}, fh)
'''


def _run_export(profile, root, home, out, recfile, quiet=True):
    drv = os.path.join(os.path.dirname(recfile), "driver.py")
    with open(drv, "w") as fh:
        fh.write(_DRIVER)
    r = subprocess.run([sys.executable, drv, REPO, profile, str(root),
                        str(home), str(out), str(recfile)],
                       capture_output=True, text=True, cwd=REPO)
    with open(recfile) as fh:
        rec = json.load(fh)
    rec["rc"] = r.returncode
    rec["stderr"] = r.stderr
    if not quiet and r.returncode:
        note(r.stderr[-800:])
    return rec


def _manifest(out):
    p = pathlib.Path(out) / "machine-readable" / "MANIFEST.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def _byte_counts(m):
    """Every number in the manifest that claims to be a count of bytes."""
    out = {"MANIFEST.bytes": m.get("bytes")}
    for t in m.get("tools") or []:
        out[f"tools[{t['tool']}].bytes"] = t.get("bytes")
        out[f"tools[{t['tool']}].not_exported_bytes"] = t.get("not_exported_bytes")
    return out


def _small_home(home):
    import fleet_fixture as FF
    FF.build_linux_a(home)


# ---------------------------------------------------------------------------
# 2  adv_windows_newlines
# ---------------------------------------------------------------------------

def adv_windows_newlines():
    """Export the same bytes twice, bare and as Windows. The numbers must match.

    export_corpus counts bytes two ways and neither knows about the other:

        export_tools   per_tool[label]["bytes"] += len(text.encode("utf-8"))
        main           size = sum(f.stat().st_size for f in dst.rglob("*.jsonl"))

    The first measures the string it is about to hand to write_text; the second
    measures what the filesystem ended up holding. On Linux those are the same
    number, which is why one file can carry both. On Windows a text-mode write
    with newline=None turns every \\n into \\r\\n, so st_size grows by one byte
    per line while len(text.encode()) does not move at all. The manifest then
    reports two byte totals for one corpus, one of which is short by exactly the
    line count — and both look entirely reasonable on the page.

    The CRLF itself is the second half: the corpus is JSONL, consumed line by
    line by whoever receives it, and a redaction audit that greps raw bytes is
    reading a different file than the one that was written.
    """
    d = pathlib.Path(tempfile.mkdtemp(prefix="advplat-nl-")).resolve()
    try:
        root = d / "sim"
        root.mkdir()
        home = root / "home"
        home.mkdir()
        _small_home(home)

        runs = {}
        for profile in ("bare", "win"):
            out = root / f"out-{profile}"
            rec = _run_export(profile, root, home, out, str(d / f"{profile}.json"))
            m = _manifest(out)
            if m is None:
                check(f"the {profile} export produced a manifest", False,
                      (rec.get("error") or rec.get("stderr") or "")[-800:])
                return
            crlf = [p for p in out.rglob("*")
                    if p.is_file() and b"\r\n" in p.read_bytes()]
            runs[profile] = {"manifest": m, "crlf": crlf, "out": out, "rec": rec}

        bare, win = runs["bare"], runs["win"]

        check("the two runs read the same input",
              bare["manifest"]["files"] == win["manifest"]["files"]
              and bare["manifest"]["lines_kept"] == win["manifest"]["lines_kept"],
              f"files {bare['manifest']['files']} vs {win['manifest']['files']}, "
              f"lines_kept {bare['manifest']['lines_kept']} vs "
              f"{win['manifest']['lines_kept']}")

        b, w = _byte_counts(bare["manifest"]), _byte_counts(win["manifest"])
        moved = {k: (b[k], w[k]) for k in b if b[k] != w[k]}
        held = {k: b[k] for k in b if b[k] == w[k]}
        check("every byte count in the manifest is identical between runs",
              not moved,
              "\n".join(f"{k}: bare {v[0]:,} -> win {v[1]:,} "
                        f"({v[1] - v[0]:+,})" for k, v in sorted(moved.items()))
              + ("\n" if moved else "")
              + (f"and {len(held)} other byte count(s) did NOT move, which is "
                 "the divergence: st_size grew, len(text.encode()) could not"
                 if moved and held else ""))

        check("no CRLF anywhere in the Windows output tree",
              not win["crlf"],
              f"{len(win['crlf'])} of "
              f"{sum(1 for p in win['out'].rglob('*') if p.is_file())} files "
              "hold b'\\r\\n'" if win["crlf"] else "")
        check("no CRLF anywhere in the bare output tree", not bare["crlf"],
              f"{len(bare['crlf'])} file(s)" if bare["crlf"] else "")

        for profile in ("bare", "win"):
            err = runs[profile]["rec"].get("error")
            if err:
                note(f"the {profile} export raised after writing its manifest:\n"
                     + err.strip().splitlines()[-1])
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------
# 3  adv_maxpath_budget
# ---------------------------------------------------------------------------

_FALLBACK_PROJECT = (
    "-media-phantomcore-AI-DRIVE-hackathons-H0--Hack-the-Zero-Stack-with-"
    "Vercel-v0-and-AWS-Databases-Track-3---Million-scale-Global-App")
_FALLBACK_REL = ("e7efb5a1-c65a-422c-9303-a7a4302313b2/subagents/workflows/"
                 "wf_154a917b-d63/agent-a355bdbffbd0c4849.jsonl")


def _real_longest_project(profile):
    r = pathlib.Path.home() / profile / "projects"
    best = ""
    try:
        for p in r.iterdir():
            if p.is_dir() and len(p.name) > len(best):
                best = p.name
    except OSError:
        pass
    return best


def _real_deepest_rel(profile):
    """The session-relative path whose FOLDED name is longest, from a real profile."""
    r = pathlib.Path.home() / profile / "projects"
    best = None
    try:
        projs = [p for p in r.iterdir() if p.is_dir()]
    except OSError:
        return None
    for proj in projs:
        try:
            files = list(proj.rglob("*.jsonl"))
        except OSError:
            continue
        for f in files:
            rel = f.relative_to(proj)
            folded = (rel.name if rel.parent == pathlib.Path(".")
                      else "__".join(rel.parts))
            if best is None or len(folded) > len(best[0]):
                best = (folded, rel.as_posix())
    return best


def _row(uuid, mid, ts):
    return json.dumps({
        "uuid": uuid, "timestamp": ts, "type": "assistant",
        "message": {"id": mid, "model": "claude-opus-4-6",
                    "usage": {"input_tokens": 10, "output_tokens": 20,
                              "cache_creation_input_tokens": 0,
                              "cache_read_input_tokens": 0}}})


def adv_maxpath_budget():
    """The folded name is bounded by NAME_MAX. Windows caps the PATH.

    `out_name(rel, limit, taken)` is handed `_name_max(dst)` — os.pathconf's
    PC_NAME_MAX, 255 on ext4, and 255 as the fallback when pathconf is absent,
    which on Windows it always is. That is a per-COMPONENT limit and it is the
    right limit for the bug it was written for. It is not the limit Windows
    enforces: MAX_PATH is 260 for the whole path, so a legal 255-byte component
    is illegal the moment it sits more than four characters below the drive.

    The fixture is not invented. It is the real 130-character project directory
    that exists under ~/.claude-alt today, holding a transcript at the real
    session/subagents/workflows/wf_*/agent-*.jsonl depth whose folded name is
    106 characters — also measured, from the same fleet. Only the home prefix is
    substituted: C:\\Users\\phantomcore, twenty characters, which is as short as
    a real Windows home gets.

    THREE CLAUSES, and the second is there to block the fix that would otherwise
    pass this:

      max windows-form OUTPUT path <= 260
                                       the actual budget, on the only paths
                                       this program chooses
      the limit passed to out_name is strictly below 255 whenever the
                                       destination directory is longer than
                                       five characters — i.e. the caller
                                       subtracted the directory it is writing
                                       into, rather than trimming harder and
                                       hoping
      files in == files out            truncating harder collides names, and a
                                       collision in this program is silent data
                                       loss; 111 files in the real corpus share
                                       a basename already

    THE FIRST CLAUSE IS SCOPED TO OUTPUT PATHS, AND THAT IS A CORRECTION.

    It used to measure `home.rglob("*")` and `out.rglob("*")` together and fail
    on either. The only path over 260 was the fixture's own INPUT — the real
    275-character transcript this fixture is built from, which the exporter
    reads and cannot rename. A profile path that long simply cannot exist on
    Windows, so it is a fact about how Claude Code names project directories on
    Linux and not a defect in export_corpus.py. Failing the exporter for it is
    an alarm nobody can act on, and this repository has already had to delete
    two of those. The source measurement is kept as a NOTE below, with its
    count, so it is reported rather than dropped; `files in == files out` is
    what holds the line that a long source is exported and not lost.

    AND THE OUTPUT CLAUSE HAD TO BE MADE ABLE TO FAIL. With the real 106-char
    folded name it passes whether or not the path budget is applied at all —
    92 + 1 + 106 = 199, comfortably inside 260 — so it was asserting something
    the fix was not needed for. `over-budget.jsonl` below folds to a 201-char
    name: legal as a component on any filesystem, illegal as a path the moment
    it sits in the destination directory. It is the file that separates
    `min(name_max, path_limit(od))` from `name_max` alone.
    """
    d = pathlib.Path(tempfile.mkdtemp(prefix="advplat-maxpath-")).resolve()
    try:
        proj_name = _real_longest_project(".claude-alt") or _FALLBACK_PROJECT
        deep = _real_deepest_rel(".claude-alt")
        deep_rel = deep[1] if deep else _FALLBACK_REL
        folded = deep[0] if deep else _FALLBACK_REL.replace("/", "__")
        note(f"real project directory: {len(proj_name)} chars")
        note(f"real deepest transcript folds to a {len(folded)}-char name")

        home = d / "home"
        # The two Windows roots this program straddles. The home directory is
        # C:\Users\phantomcore; the corpus is written into a checkout that on a
        # real Windows box sits inside it. Both are spelled out rather than
        # derived from one temp path, so no fixture-only component (\home, a
        # mkdtemp suffix) leaks into a length that is being asserted on.
        WIN_HOME = WIN_PREFIX
        WIN_OUT = WIN_PREFIX + r"\deadreckon-count\corpus\hp-laptop-linux"
        proj = home / ".claude-alt" / "projects" / proj_name
        deep_file = proj / deep_rel
        deep_file.parent.mkdir(parents=True, exist_ok=True)
        deep_file.write_text(_row("u-deep", "m-deep", "2026-08-01T00:00:00Z") + "\n",
                             encoding="utf-8")
        for i in range(3):
            (proj / f"session-{i}.jsonl").write_text(
                _row(f"u-{i}", f"m-{i}", "2026-08-01T00:00:00Z") + "\n",
                encoding="utf-8")

        # THE FILE THAT MAKES THE OUTPUT CLAUSE FALSIFIABLE. Three 64-character
        # components fold (see export_corpus.folded_name, "__".join) to a
        # 201-character name — under NAME_MAX 255 on every filesystem here, and
        # over the path budget of 260 - 92 - 1 = 167 the moment it is written
        # into the destination directory. Without min(name_max, path_limit(od))
        # it lands whole and the windows-form output path is 293 characters.
        over = proj
        for _ in range(2):
            over = over / ("d" * 64)
        over.mkdir(parents=True, exist_ok=True)
        over_file = over / ("over-budget-" + "z" * 51 + ".jsonl")
        over_file.write_text(
            _row("u-over", "m-over", "2026-08-01T00:00:00Z") + "\n",
            encoding="utf-8")
        note(f"the over-budget transcript folds to a "
             f"{len(export_corpus.folded_name(over_file.relative_to(proj)))}"
             f"-char name")

        # The destination as it is on the real fleet: <repo>/corpus/<machine>.
        out = d / "deadreckon-count" / "corpus" / "hp-laptop-linux"
        rec = _run_export("bare", d, home, out, str(d / "rec.json"))
        m = _manifest(out)
        if m is None:
            check("the export produced a manifest", False,
                  (rec.get("error") or rec.get("stderr") or "")[-800:])
            return

        def win(p, base, prefix):
            rel = os.path.relpath(str(p), str(base))
            return prefix + "\\" + rel.replace(os.sep, "\\")

        def win_out(p):
            return win(p, out, WIN_OUT)

        sources, outputs = [], []
        for p in home.rglob("*"):
            if p.is_file():
                sources.append(("source", p, win(p, home, WIN_HOME)))
        for p in out.rglob("*"):
            if p.is_file():
                outputs.append(("output", p, win_out(p)))
        long_out = [t for t in outputs if len(t[2]) > MAX_PATH]
        longest_out = max(outputs, key=lambda t: len(t[2]), default=None)
        check(f"no windows-form OUTPUT path exceeds MAX_PATH {MAX_PATH}",
              outputs and not long_out,
              (f"{len(long_out)} of {len(outputs)} written paths are over; "
               f"longest is {len(longest_out[2])} chars\n{longest_out[2]}"
               if long_out else
               "the export wrote nothing, so this clause measured nothing"
               if not outputs else ""))
        # NOT A CHECK. A source path over 260 means that profile could not
        # exist on Windows at all; the exporter reads it and cannot rename it,
        # so failing here would indict this program for somebody else's naming.
        # Reported with its count so it is a measurement and not a silence.
        long_src = [t for t in sources if len(t[2]) > MAX_PATH]
        if long_src:
            worst = max(long_src, key=lambda t: len(t[2]))
            note(f"{len(long_src)} of {len(sources)} SOURCE path(s) exceed "
                 f"{MAX_PATH} in windows form — a property of the profile "
                 f"layout, not of the exporter; longest {len(worst[2])} chars")

        outdirs = {p.parent for p in out.rglob("*.jsonl")}
        dirlens = sorted(len(win_out(x)) for x in outdirs) or [0]
        limits = [c["limit"] for c in rec["out_name_calls"]]
        precondition = dirlens[0] > 5
        bad_limits = sorted({l for l in limits if l >= 255})
        check("out_name is given a limit below 255 when the destination "
              "directory is longer than 5 characters",
              precondition and limits and not bad_limits,
              (f"the shallowest destination directory is {dirlens[0]} chars in "
               f"windows form, so the widest legal name is "
               f"{MAX_PATH - dirlens[0] - 1}; out_name was called "
               f"{len(limits)} time(s) with limit(s) {bad_limits} — a "
               "per-component NAME_MAX, which is not the budget that binds"
               if bad_limits else
               ("no destination directory was deep enough to make the clause "
                "meaningful" if not precondition else "")))

        files_in = set()
        for p in home.rglob("*.jsonl"):
            st = p.stat()
            files_in.add((st.st_dev, st.st_ino))
        files_out = list((out / ".claude" / "projects").rglob("*.jsonl"))
        check("files in == files out", len(files_in) == len(files_out),
              f"{len(files_in)} transcripts read, {len(files_out)} written "
              "— a shortened name collided and overwrote"
              if len(files_in) != len(files_out) else "")
        if longest_out:
            note(f"longest OUTPUT path is {len(longest_out[2])} chars: "
                 f"{longest_out[2][:60]}...{longest_out[2][-40:]}")
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------
# 4  adv_eperm_is_not_enoent
# ---------------------------------------------------------------------------

def _plant_probe(home, store):
    """A record for a store the fleet fixture does not cover. Returns a path."""
    rel = store.rel_paths()[0]
    if "*" in rel:
        return None
    p = home.joinpath(*rel.split("/"))
    last = p.name
    if store.kind == "root_files":
        names = [g for g in (store.records or ()) if "*" not in g] or ["history.jsonl"]
        p.mkdir(parents=True, exist_ok=True)
        target = p / names[0]
    elif "." in last[1:]:
        # A name with an extension is a file, not a directory. `.claude.json`.
        p.parent.mkdir(parents=True, exist_ok=True)
        target = p
    else:
        p.mkdir(parents=True, exist_ok=True)
        target = p / f"probe-{store.label}.jsonl"
    if not target.exists():
        target.write_text(_row(f"u-{store.label}", f"m-{store.label}",
                               "2026-08-01T00:00:00Z") + "\n", encoding="utf-8")
    return target


def _build_store_home(home):
    import fleet_fixture as FF
    FF.build_linux_a(home)
    planted = 0
    for s in stores.STORES:
        if not stores.resolve(s, str(home)):
            if _plant_probe(home, s):
                planted += 1
    return planted


def scan_home(home):
    """Every number this repository would publish about one home directory.

    Deliberately wide: the store map, profile discovery, the token totals and
    every session reader. The question this adversary asks is whether ANY of
    them can tell "I could not read it" from "there was nothing there", so
    narrowing the answer to one reader would be answering an easier question.
    """
    import analyze_tokens as AT
    import sessions
    out = {"stores": {}, "profiles": [], "tokens": 0, "files": {},
           "readers": {}, "errors": {}}
    # THE THREE-STATE ANSWER, as the SCAN PUBLISHES IT -- not a boolean.
    #
    # This read `bool(stores.resolve(...))`, and that is the defect rather than
    # a shortcut in the test: a boolean has two values for a question with three
    # answers, so a store that exists and cannot be read collapsed onto the same
    # False as one that was never installed. 22 of 45 stores were
    # indistinguishable that way.
    #
    # Asking `stores.scan()` here would have made this check green while the
    # published artifact stayed blind, which is the shape of test this suite
    # exists to reject. So sessions.py now carries `store_state` in the payload
    # itself, and this reads the same call the artifact does. If that field is
    # ever dropped from the payload, this goes red.
    out["store_state"] = stores.scan(str(home))
    for s in stores.STORES:
        try:
            out["stores"][s.label] = bool(stores.resolve(s, str(home)))
        except OSError as e:
            out["errors"][f"store:{s.label}"] = f"{e.__class__.__name__}:{e.errno}"
    try:
        dirs = AT.find_config_dirs(pathlib.Path(home))
        out["profiles"] = sorted(str(p.relative_to(home)) for p in dirs)
        seen = set()
        for cd in dirs:
            r = AT.scan(cd, seen)
            out["tokens"] += AT.grand(r["totals"])
            for k, v in r["files"].items():
                out["files"][k] = out["files"].get(k, 0) + v
    except OSError as e:
        out["errors"]["scan"] = f"{e.__class__.__name__}:{e.errno}"
    for name, fn in sessions.READERS.items():
        try:
            rows = fn(pathlib.Path(home))
            out["readers"][name] = [len(rows),
                                    sum(int(r.get("total") or 0) for r in rows)]
        except Exception as e:  # noqa: BLE001
            out["errors"][f"reader:{name}"] = f"{e.__class__.__name__}:{e}"
    return out


@contextlib.contextmanager
def _unreadable(target):
    """chmod 000 — the input is present and cannot be read."""
    old = stat.S_IMODE(os.stat(target).st_mode)
    os.chmod(target, 0)
    try:
        yield
    finally:
        os.chmod(target, old)


@contextlib.contextmanager
def _emptied(target, stash):
    """Everything under `target` moved aside — the input is genuinely empty.

    The control has to be EMPTY rather than DELETED, and the difference is the
    whole design of this attack. Deleting `target` would also delete its own
    directory entry, and "the folder is not there" is a distinction the code
    might make for reasons that have nothing to do with permissions. Emptying it
    holds every other fact constant: same path, same parent, same mode, same
    siblings. The only thing that differs between the two runs is WHY the
    contents cannot be seen.
    """
    os.makedirs(stash, exist_ok=True)
    moved = []
    for name in os.listdir(target):
        src = os.path.join(target, name)
        dst = os.path.join(stash, name)
        shutil.move(src, dst)
        moved.append((dst, src))
    try:
        yield
    finally:
        for dst, src in moved:
            shutil.move(dst, src)


def _blocking(target):
    """Does chmod 000 actually block here. It does not for root."""
    with _unreadable(target):
        try:
            os.listdir(target)
            return False
        except PermissionError:
            return True
        except OSError:
            return True


def adv_eperm_is_not_enoent():
    """A store nobody can read reports the same as a store holding nothing.

    Every reader in this repository walks its store with rglob, glob or
    os.walk, and all three swallow EACCES and yield nothing. `os.path.exists`
    catches OSError and answers False. `find_config_dirs` catches OSError in
    `is_dir` and answers False — with a comment explaining that it must, because
    one unreadable folder anywhere under $HOME used to take the whole scan down.
    Every one of those is the right local decision and the sum of them is the
    signature bug of this codebase: absent looks exactly like zero.

    The assertion is an INEQUALITY between two runs of the same function on the
    same tree, so it cannot be satisfied by printing a constant, by adding a
    field, or by reporting a number that happens to be right. Something,
    anywhere in the published output, has to differ.
    """
    d = pathlib.Path(tempfile.mkdtemp(prefix="advplat-eperm-")).resolve()
    try:
        home = d / "home"
        home.mkdir()
        planted = _build_store_home(home)
        note(f"fixture home: {len(stores.STORES)} stores, {planted} planted "
             "beyond what fleet_fixture covers")

        probe = home / ".claude"
        if not _blocking(str(probe)):
            check("chmod 000 blocks this user", False,
                  "chmod 000 did not stop a read — running as root? every "
                  "assertion below would be vacuous")
            return

        stash = d / "stash"
        indistinguishable = []
        skipped = []
        for s in stores.STORES:
            paths = stores.resolve(s, str(home))
            if not paths:
                skipped.append(s.label)
                continue
            p = pathlib.Path(paths[0])
            victim = p.parent if p.parent != home else p
            if not victim.is_dir():
                skipped.append(s.label)
                continue
            with _unreadable(str(victim)):
                a = scan_home(home)
            with _emptied(str(victim), str(stash)):
                b = scan_home(home)
            shutil.rmtree(stash, ignore_errors=True)
            if a == b:
                indistinguishable.append((s.label, str(victim.relative_to(home))))

        # AND THE PAYLOAD ITSELF CARRIES IT. Without this the check below is
        # satisfied by a distinction that never leaves memory: scan_home() calls
        # stores.scan() directly, so deleting `store_state` from sessions.py's
        # published payload left this suite at 19 checks, 0 failed. Measured, in
        # a copy, after I claimed in a comment that it would go red. It did not.
        #
        # A distinction the code can make and the ARTIFACT does not carry is not
        # a distinction any consumer downstream can act on, and the consumers
        # are the whole reason the three states exist. Asserted against the
        # source that builds the payload, because the payload is assembled
        # inside main() and there is no function to call for it.
        _src = pathlib.Path(__file__).with_name("sessions.py").read_text(
            encoding="utf-8", errors="replace")
        _tree = ast.parse(_src)
        _published = set()
        for _n in ast.walk(_tree):
            if isinstance(_n, ast.Dict):
                for _k in _n.keys:
                    if isinstance(_k, ast.Constant) and isinstance(_k.value, str):
                        _published.add(_k.value)
        check("the published payload carries store_state, not just memory",
              "store_state" in _published,
              "" if "store_state" in _published else
              "sessions.py builds its artifact without the per-store state, so "
              "a consumer reading the scan still cannot tell unreadable from "
              "absent — the distinction dies at the file boundary")

        check("scan(unreadable store) != scan(empty store), for every store",
              not indistinguishable,
              (f"{len(indistinguishable)} of "
               f"{len(stores.STORES) - len(skipped)} stores report byte-for-byte "
               "the same thing when their directory cannot be entered as when "
               "it is empty:\n"
               + "\n".join(f"{lbl:<28} {v}" for lbl, v in indistinguishable[:8])
               + (f"\n... and {len(indistinguishable) - 8} more"
                  if len(indistinguishable) > 8 else ""))
              if indistinguishable else "")
        if skipped:
            note(f"{len(skipped)} store(s) had no resolvable directory in the "
                 f"fixture and were not tested: {', '.join(skipped[:6])}"
                 + (" ..." if len(skipped) > 6 else ""))

        # The second shape: the store is readable, one project inside it is not.
        projects = home / ".claude" / "projects"
        subs = sorted(p for p in projects.iterdir() if p.is_dir())
        if subs:
            victim = subs[0]
            with _unreadable(str(victim)):
                a = scan_home(home)
            with _emptied(str(victim), str(stash)):
                b = scan_home(home)
            shutil.rmtree(stash, ignore_errors=True)
            check("scan(unreadable project dir) != scan(empty project dir)",
                  a != b,
                  f"the store is readable and {victim.name} inside it is not; "
                  f"the scan reports {a['tokens']:,} tokens either way")

        _consistency_distinguishes(d, home)
    finally:
        # chmod anything back that a failure left unreadable, or the rmtree
        # below quietly leaves a tree on the disk.
        for dirpath, dirnames, _ in os.walk(str(d)):
            for name in dirnames:
                with contextlib.suppress(OSError):
                    os.chmod(os.path.join(dirpath, name), 0o755)
        shutil.rmtree(d, ignore_errors=True)


def _build_fixture_repo(home, repo, machine="hp-laptop-linux"):
    """A repository holding one machine's published numbers, from `home`.

    Returns (machine dir, {scanner: return code}, [artifacts written]).
    """
    mdir = repo / machine
    mdir.mkdir(parents=True, exist_ok=True)
    rcs = {}
    for mod in ("analyze_tokens", "sessions"):
        r = subprocess.run([sys.executable, os.path.join(REPO, mod + ".py"),
                            "--home", str(home), "--out", str(mdir),
                            "--label", machine],
                           capture_output=True, text=True, cwd=REPO)
        rcs[mod] = (r.returncode, r.stderr.strip().splitlines()[-1:] or [""])
    (mdir / ".machine-id").write_text(json.dumps({"hostname": machine}))
    wrote = sorted(p.name for p in (mdir / "machine-readable").glob("*.json")) \
        if (mdir / "machine-readable").is_dir() else []
    return mdir, rcs, wrote


def _run_consistency(repo):
    """check_consistency against a fixture root instead of the real repo.

    It reads `pathlib.Path(__file__).parent`, so the module's own `__file__` is
    pointed at the fixture. The code under test is the real file, unmodified —
    only the root it audits is substituted.
    """
    drv = repo / "_cc_driver.py"
    drv.write_text(
        "import sys\n"
        f"sys.path.insert(0, {REPO!r})\n"
        "import check_consistency as C\n"
        f"C.__file__ = {str(repo / 'check_consistency.py')!r}\n"
        "sys.exit(C.main())\n")
    r = subprocess.run([sys.executable, str(drv)], capture_output=True,
                       text=True, cwd=str(repo))
    lines = [ln.rstrip() for ln in (r.stdout + r.stderr).splitlines()
             if ln.strip().startswith(("PASS", "FAIL", "WARN"))]
    return r.returncode, lines


def _consistency_pair(d, home, victim, tag):
    """Run the whole publish pipeline over both trees and audit each."""
    stash = d / f"cc-stash-{tag}"
    got = {}
    for kind, ctx in (("unreadable", _unreadable(str(victim))),
                      ("empty", _emptied(str(victim), str(stash)))):
        repo = d / f"repo-{tag}-{kind}"
        with ctx:
            _, rcs, wrote = _build_fixture_repo(home, repo)
        shutil.rmtree(stash, ignore_errors=True)
        rc, lines = _run_consistency(repo)
        got[kind] = {"rcs": rcs, "wrote": wrote, "rc": rc, "lines": lines}
    return got


def _consistency_distinguishes(d, home):
    """40 checks that pass on both trees have not checked anything.

    Run twice, because the two shapes fail differently and only one of them is
    quiet. An unreadable PROFILE takes sessions.py down before it writes
    anything, so the audit sees a missing artifact — loud, and not the bug. An
    unreadable PROJECT DIRECTORY inside a readable profile is walked by rglob,
    which swallows EACCES, so every artifact is written, every number is short
    by exactly that project, and every check still adds up.
    """
    projects = home / ".claude" / "projects"
    subs = sorted(p for p in projects.iterdir() if p.is_dir())
    shapes = [("store", home / ".claude")]
    if subs:
        shapes.append(("project", subs[0]))

    for tag, victim in shapes:
        got = _consistency_pair(d, home, victim, tag)
        a, b = got["unreadable"], got["empty"]
        crashed = [f"{k} exited {v[0]} ({v[1][0][:70]})"
                   for kind in ("unreadable", "empty")
                   for k, v in got[kind]["rcs"].items() if v[0]]
        check(f"the scanners complete on both trees ({tag})", not crashed,
              "\n".join(crashed) + "\n"
              f"artifacts written: unreadable {a['wrote']}, empty {b['wrote']}"
              if crashed else "")
        if not a["lines"] or not b["lines"]:
            check(f"check_consistency produced checks on both trees ({tag})",
                  False,
                  f"unreadable {len(a['lines'])} line(s) rc={a['rc']}; "
                  f"empty {len(b['lines'])} line(s) rc={b['rc']} — a suite "
                  "that printed nothing cannot have distinguished anything")
            continue
        diff = [(x, y) for x, y in zip(a["lines"], b["lines"]) if x != y]
        extra = abs(len(a["lines"]) - len(b["lines"]))
        distinguished = bool(diff or extra)
        why = ""
        if distinguished and a["wrote"] != b["wrote"]:
            why = ("\nand the difference is an ARTIFACT THAT IS NOT THERE, not "
                   "a check that noticed: " + f"{a['wrote']} vs {b['wrote']}")
        check(f"at least one consistency check distinguishes unreadable from "
              f"empty ({tag})", distinguished,
              (f"{len(a['lines'])} checks on the unreadable tree and "
               f"{len(b['lines'])} on the empty one, line for line identical, "
               f"exit {a['rc']} both times — the scan is short by one whole "
               "project and every partition still sums to its whole"
               if not distinguished else
               (f"{len(diff)} line(s) differ / {extra} extra" + why)))


# ---------------------------------------------------------------------------

ADVERSARIES = [
    ("adv_shim_canary", adv_shim_canary),
    ("adv_windows_newlines", adv_windows_newlines),
    ("adv_maxpath_budget", adv_maxpath_budget),
    ("adv_eperm_is_not_enoent", adv_eperm_is_not_enoent),
]


def main():
    only = sys.argv[1:]
    for name, fn in ADVERSARIES:
        if only and name not in only:
            continue
        print(f"\n{name}")
        try:
            fn()
        except Exception:  # noqa: BLE001
            RESULTS.append((f"{name} ran to completion", False, ""))
            print(f"  FAIL  {name} raised")
            for line in traceback.format_exc().splitlines():
                print(f"          {line}")
    failed = [r for r in RESULTS if not r[1]]
    print(f"\n{len(RESULTS)} checks, {len(failed)} failed")
    for name, _, _ in failed:
        print(f"  FAILED  {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
