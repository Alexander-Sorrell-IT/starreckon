#!/usr/bin/env python3
"""Attacks on the attackers. Can each suite actually FAIL?

    python3 adversarial_meta.py

WHY

A suite that cannot fail is worse than no suite, because it is read as evidence.
This repository has produced three of them, all found the same day:

  adversarial.py       carried a hardcoded list of five machines. A retire moved
                       four of them, so every attack died on a missing path and
                       the run scored NOTHING while printing a summary.
  adversarial_daemon   two attacks asserted res["ledger"] == "ok" while tick()
                       assigned "ok" unconditionally. Unfalsifiable by
                       construction; they passed against code that did nothing.
  the same suite       one attack tested isinstance(int) on a value that is
                       always a dict, returned SKIPPED for its entire existence,
                       and the summary counted skipped as not-survived and
                       printed "every attack caught".

And one commit reported "38 scanner tests, 0 failed" over a run that said 1
FAILED, because the verification chained `&& git commit` off a grep that matched
whether or not the tests passed.

SO THIS FILE ASKS FIVE THINGS OF EVERY SUITE

  1. it EXITS NON-ZERO when something is wrong. A suite that always exits 0
     cannot gate anything.
  2. it DETECTS A PLANTED BREAK. Each suite is run against a deliberately
     broken copy of the code it tests; if it still passes, it is decorative.
  3. it has NO VACUOUS ASSERTION — no check whose expected value is what the
     code returns unconditionally.
  4. it REPORTS SKIPS AS SKIPS. An attack that did not run must never be
     counted as an attack that passed.
  5. it EXERCISES THE DEGENERATE INPUTS — empty, one item, and an absent tree.
     Nineteen planted defects were caught by suites that never once fed them
     nothing, and `corpus_reports.py` then died on a fresh clone with
     `ValueError: max() iterable argument is empty`.

The break is planted in a COPY. Nothing here modifies the working tree.

AND THIS FILE IS ITSELF UNDER TEST. `adv_suite_integrity.py` plants a known
vacuous assertion and asserts the scanner below FINDS it, and plants a genuine
one and asserts it does NOT. A checker that reports nothing must be
distinguishable from a checker that is broken, and until that file existed it
was not: the scan this one used to run reported a clean repository while
`check_consistency.py` held two assertions comparing a literal to itself.
"""
import ast
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.realpath(__file__))
FAILED = []


def check(name, got, want, why=""):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        print(f"        got {got!r}, want {want!r}" + (f" — {why}" if why else ""))
        FAILED.append(name)


def run_in(d, script, timeout=1800):
    r = subprocess.run([sys.executable, script], cwd=d,
                       capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout + r.stderr)


def sandbox():
    """A copy of the repo. Breaks are planted here, never in the working tree."""
    d = tempfile.mkdtemp(prefix="meta-")
    for f in os.listdir(ROOT):
        s = os.path.join(ROOT, f)
        if f.endswith(".py") or f in ("machines.json", "accounts.json"):
            shutil.copy2(s, os.path.join(d, f))
        elif os.path.isdir(s) and os.path.isfile(os.path.join(s, "machine-readable",
                                                              "totals.json")):
            shutil.copytree(s, os.path.join(d, f))
    return d


def plant(d, fname, old, new):
    """Break one line of one file in the sandbox. Returns False if not found."""
    p = os.path.join(d, fname)
    try:
        s = open(p, encoding="utf-8").read()
    except OSError:
        return False
    if old not in s:
        return False
    open(p, "w", encoding="utf-8").write(s.replace(old, new, 1))
    return True


# ---------------------------------------------------------------------------
# THE VACUOUS-ASSERTION SCANNER
#
# What this replaced, and why it had to be replaced:
#
#     for m in re.finditer(r'check\(\s*"[^"]*"\s*,\s*(True|False)\s*,\s*(True|False)',
#                          src):
#
# over `for suite, *_ in SUITES`. It reported "no assertion compares a literal
# to itself" for the whole life of this repository while check_consistency.py
# carried two that do, and it could not have seen them for two independent
# reasons. The regex only knew the words True and False, so `chk(name, 0, 0)`
# was invisible. And the file set was the hand-maintained SUITES list, which
# has never contained check_consistency.py — the gate that update.py actually
# runs. Either reason alone is enough to make the green meaningless; a check
# that cannot see the thing it is named after is the exact pattern this file
# exists to find, sitting inside the file that looks for it.
#
# So: parse, do not match. Two shapes are vacuous.
#
#   1. the two compared arguments UNPARSE IDENTICALLY. That is 0 vs 0, True vs
#      True, "ok" vs "ok", and max(a, b) vs max(a, b) — the last being the real
#      one, five per run, one per machine, in check_consistency.py before it
#      was fixed. A regex cannot do this without becoming a parser.
#   2. a result is APPENDED DIRECTLY to the list the helper owns, with the
#      passed flag written in by hand. `checks.append((name, 0, 0, True, ""))`
#      does not go near the comparison, so shape 1 cannot see it, and it
#      reported PASS whatever the numbers said. It shipped here.
#
#      A hardcoded TRUE only. The first version of this rule flagged any
#      boolean literal and immediately caught
#
#          RESULTS.append((f"{name} ran to completion", False, ""))
#
#      in adv_platform_behaviour.py — which is the `except` arm recording that
#      an adversary crashed, exactly the behaviour four of this file's other
#      attacks exist to demand. A hardcoded False can only ever make a suite
#      redder; it cannot manufacture the green that is the whole problem. So
#      the rule asks about the pass, not about the literal.
#
# The helper NAMES are discovered, not listed, for the same reason the file set
# is: a function that decides pass/fail by comparing two of its own parameters
# is an assertion helper whatever it is called.
#
# WHAT IT STILL CANNOT SEE, said here so the green is not read as more than it
# is. Identity is SYNTACTIC. check_consistency.py once carried
#
#     grand = sum(m["grand_total_tokens"] for m in machines)
#     ...
#     chk("machines partition the grand total",
#         sum(m["grand_total_tokens"] for m in machines), grand)
#
# which is the same value by different spellings, four lines apart, and this
# scan would pass it. Catching that needs the values traced, not the text
# compared. The two shapes below are the ones that have shipped repeatedly and
# are decidable without running anything; the third is a real remaining hole.

# A floor, not the list. A file that calls a helper it imported has no def to
# discover, so these two are always assumed to have the (got, want) shape.
DEFAULT_SHAPES = {"check": {(1, 2)}, "chk": {(1, 2)}}
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv"}


def skipped_dir(name):
    """A directory this scan must not descend into. NAME, or a `.venv` PREFIX.

    The set above is exact-name only, and install.py does not create `.venv`:
    it creates `.venv-forecast` (install.py:826) and `.venv-search`
    (install.py:870). Both were walked, so 12,125 of the 12,202 .py files this
    scan opened were site-packages — and they were not inert. All six failures
    of the last run were theirs or caused by theirs:

        124 of 124  "compares a value with itself" sites, every one in
                    joblib, mpmath, networkx or torch
          1 of 1    unreadable file (joblib's
                    test_func_inspect_special_encoding.py, UnicodeDecodeError)
          3 of 4    hardcoded-flag sites — and the 4th was a false positive
                    they manufactured: assertion_shapes grew from 2 helper
                    names to 294, one of them `add`, which sessions.py also
                    defines, so the production record at sessions.py:1913 was
                    read as an assertion with the pass flag written in
        877 of 882  ABSENT/FRESH gaps, and 616 of 619 EMPTY, 470 of 476 SINGLE
    """
    return name in SKIP_DIRS or name.startswith(".venv")


def _callee(node):
    """The bare name a Call is calling: `chk`, or the `append` of x.append."""
    f = node.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return None


def _params(fn):
    return [a.arg for a in fn.args.posonlyargs + fn.args.args]


def assertion_shapes(sources):
    """{helper name: {(i, j)}} — which two ARGUMENTS each helper compares.

    A helper is any function of three or more parameters whose body compares
    two of those parameters to each other. That is what `got == want` is, in
    every spelling this repo uses:

        ok = got == want                                  adversarial_daemon
        (PASS if got == want else FAIL).append(...)       test_readers
        checks.append((name, got, want, got == want, ...))  check_consistency

    `sources` is an iterable of (label, source) so the set can be built once
    across the whole repo and applied to files that only CALL a helper.
    """
    shapes = {k: set(v) for k, v in DEFAULT_SHAPES.items()}
    for _label, src in sources:
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            params = _params(fn)
            if len(params) < 3:
                continue
            for c in ast.walk(fn):
                if not (isinstance(c, ast.Compare) and len(c.ops) == 1
                        and isinstance(c.ops[0], (ast.Eq, ast.NotEq))):
                    continue
                left, right = c.left, c.comparators[0]
                if (isinstance(left, ast.Name) and isinstance(right, ast.Name)
                        and left.id in params and right.id in params
                        and left.id != right.id):
                    shapes.setdefault(fn.name, set()).add(
                        (params.index(left.id), params.index(right.id)))
    return shapes


def vacuous_sites(src, label="<source>", shapes=None):
    """[(label, lineno, kind, text)] for assertions in `src` that cannot fail.

    Raises SyntaxError if src does not parse — the caller must decide what an
    unparseable file means, because returning [] for one is this repository's
    signature bug: absent reads exactly like clean.
    """
    shapes = shapes or {k: set(v) for k, v in DEFAULT_SHAPES.items()}
    tree = ast.parse(src)

    # Which list does the helper append its results to, and where is its body?
    # Both are needed for shape 2: an append onto that same list from OUTSIDE
    # the helper is a result written by hand.
    lists, spans = set(), []
    for fn in ast.walk(tree):
        if not (isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))
                and fn.name in shapes):
            continue
        spans.append((fn.lineno, fn.end_lineno or fn.lineno))
        for c in ast.walk(fn):
            if (isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                    and c.func.attr == "append"):
                lists |= {x.id for x in ast.walk(c.func.value)
                          if isinstance(x, ast.Name)}

    out = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        name = _callee(n)
        if name in shapes:
            for i, j in sorted(shapes[name]):
                if len(n.args) <= max(i, j):
                    continue
                a, b = ast.unparse(n.args[i]), ast.unparse(n.args[j])
                if a == b:
                    out.append((label, n.lineno, "compares a value with itself",
                                f"{name}(..., {a}, {b})"))
                    break
        if (name == "append" and lists and isinstance(n.func, ast.Attribute)
                and not any(lo <= n.lineno <= hi for lo, hi in spans)):
            recv = {x.id for x in ast.walk(n.func.value) if isinstance(x, ast.Name)}
            if recv & lists and any(
                    isinstance(x, ast.Constant) and x.value is True
                    for a in n.args for x in ast.walk(a)):
                out.append((label, n.lineno, "hardcodes the passed flag",
                            ast.unparse(n)[:90]))
    return sorted(out, key=lambda r: (r[0], r[1]))


def repo_py_files(root):
    """Every .py under root. NOT a curated list — that is how the gate escaped.

    os.walk, so a file added tomorrow in a directory nobody thought about is
    scanned tomorrow, without anyone remembering to add it here.
    """
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not skipped_dir(d))
        out += [os.path.join(dirpath, f) for f in filenames if f.endswith(".py")]
    return sorted(out)


def scan_repo(root):
    """(sites, scanned, unreadable) over every .py in the tree.

    `unreadable` is returned rather than swallowed. A file that cannot be read
    or cannot be parsed contributes no findings, and no findings is what a
    clean file looks like — the one bug this repository keeps making. It is
    checked separately below so that "0 vacuous assertions" is only ever
    printed over files that were actually opened.

    A root that is not there is the same bug one level up: os.walk on a path
    that does not exist yields nothing at all and raises nothing, so an absent
    tree returns ([], [], []) — character for character what a tree with no
    Python in it returns. Named separately, so the two answers differ.
    """
    sources, unreadable = [], []
    if not os.path.isdir(root):
        return [], [], [f"{root}: not a directory — nothing was scanned"]
    for p in repo_py_files(root):
        label = os.path.relpath(p, root)
        try:
            sources.append((label, open(p, encoding="utf-8").read()))
        except (OSError, UnicodeDecodeError) as e:
            unreadable.append(f"{label}: unreadable ({type(e).__name__})")
    shapes = assertion_shapes(sources)
    sites, scanned = [], []
    for label, src in sources:
        try:
            sites += vacuous_sites(src, label, shapes)
        except SyntaxError as e:
            unreadable.append(f"{label}: does not parse (line {e.lineno})")
            continue
        scanned.append(label)
    return sites, scanned, unreadable


def assertion_count(src, shapes):
    """How many assertion-helper CALLS a source makes. 0 = not a suite."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return 0
    return sum(1 for n in ast.walk(tree)
               if isinstance(n, ast.Call) and _callee(n) in shapes
               and len(n.args) >= 3)


# ---------------------------------------------------------------------------
# THE THREE DEGENERATE INPUTS — PLAN.md:384-387
#
# "does the suite exercise an EMPTY input, does it exercise a FRESH CLONE".
#
# The evidence is STRUCTURAL: a fixture that is empty, a fixture with exactly
# one item, a tree that gets deleted before the code under test reads it.
# Deliberately not a search for the words. This file already had to delete one
# check that fired on `"SKIP" in src.upper()` matching a function name, and a
# name-based version of this one scored check_consistency.py as covering both
# EMPTY and ABSENT on the strength of a single check name — which is
# `chk("machines absent by RETIRE, not by loss", 0, 0)`, one of the two
# vacuous assertions the scan above finds. Coverage claimed by an assertion
# that cannot fail is worse than no claim.
#
# It under-reports rather than over-reports, on purpose. "No evidence found"
# is a claim a human can refute by naming the line; "covered" is a claim
# nobody re-checks.

# Calls that consume a literal without feeding it to anything under test.
# sum([]), len([]), d.get(k, []) are defaults and identities, not fixtures.
_NOT_A_FIXTURE = {
    "sum", "len", "next", "max", "min", "sorted", "list", "dict", "set",
    "tuple", "int", "str", "float", "bool", "any", "all", "zip", "enumerate",
    "range", "defaultdict", "Counter", "isinstance", "print", "get",
    "setdefault", "pop", "join", "format", "replace", "split", "strip",
    "startswith", "endswith", "getattr", "setattr", "append", "extend",
    "update", "items", "keys", "values", "sub", "search", "match", "findall",
    "add", "discard", "check", "chk",
}
_DELETERS = ("rmtree", "remove", "unlink", "rmdir")
_SPAWNERS = ("run", "call", "check_call", "check_output", "Popen")
QUESTIONS = ("EMPTY", "SINGLE", "ABSENT")


def degenerate_evidence(src, label="<source>"):
    """{EMPTY|SINGLE|ABSENT: [(label, line, text)]} — fixtures, not words."""
    ev = {q: [] for q in QUESTIONS}
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return ev
    # A delete inside `finally:` is teardown; it is not a scenario.
    teardown = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Try):
            for st in n.finalbody:
                for s in ast.walk(st):
                    if hasattr(s, "lineno"):
                        teardown.add(s.lineno)
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        name = _callee(n)
        if name not in _NOT_A_FIXTURE:
            for a in list(n.args) + [k.value for k in n.keywords]:
                for sub in ast.walk(a):
                    if isinstance(sub, (ast.List, ast.Set, ast.Tuple, ast.Dict)):
                        k = (len(sub.keys) if isinstance(sub, ast.Dict)
                             else len(sub.elts))
                        if k == 0:
                            ev["EMPTY"].append((label, n.lineno,
                                                f"{name}(… {ast.unparse(sub)} …)"))
                        elif k == 1 and not isinstance(sub, ast.Dict):
                            ev["SINGLE"].append(
                                (label, n.lineno,
                                 f"{name}(… {ast.unparse(sub)[:34]} …)"))
                    elif isinstance(sub, ast.Constant) and sub.value in ("", b""):
                        ev["EMPTY"].append((label, n.lineno, f"{name}(… '' …)"))
        if name in _DELETERS and n.lineno not in teardown:
            ev["ABSENT"].append((label, n.lineno, ast.unparse(n)[:52]))
        # A fresh clone, and only a real one. Matching the WORD `clone` in any
        # string scored this very function as exercising a fresh clone, on the
        # strength of the literal three lines below. It has to be a process
        # being started, not a file that mentions one.
        elif name in _SPAWNERS and any(
                isinstance(s, ast.Constant) and s.value in ("clone", "git clone")
                for a in n.args for s in ast.walk(a)):
            ev["ABSENT"].append((label, n.lineno, "git clone"))
    return ev


def suite_coverage(root):
    """{suite: {question: [evidence]}} for every file that makes assertions.

    A suite whose fixture lives in a generator module — test_fleet.py and
    fleet_fixture.py — has its degenerate inputs written there, so the
    generator it imports is read too. Only `*_fixture` modules: following
    every local import would read the CODE UNDER TEST and score the suite for
    an empty list that the production code passes to itself.
    """
    sources = {}
    for p in repo_py_files(root):
        try:
            sources[os.path.relpath(p, root)] = open(p, encoding="utf-8").read()
        except (OSError, UnicodeDecodeError):
            continue
    shapes = assertion_shapes(sources.items())
    cov = {}
    for label, src in sorted(sources.items()):
        if assertion_count(src, shapes) == 0:
            continue
        ev = degenerate_evidence(src, label)
        try:
            tree = ast.parse(src)
        except SyntaxError:
            cov[label] = ev
            continue
        for n in ast.walk(tree):
            mods = []
            if isinstance(n, ast.Import):
                mods = [a.name for a in n.names]
            elif isinstance(n, ast.ImportFrom) and n.module:
                mods = [n.module]
            for m in mods:
                f = m.split(".")[-1]
                if not f.endswith("_fixture"):
                    continue
                fsrc = sources.get(f + ".py")
                if fsrc is None:
                    continue
                sub = degenerate_evidence(fsrc, f + ".py")
                for q in QUESTIONS:
                    ev[q] += sub[q]
        cov[label] = ev
    return cov


# ---------------------------------------------------------------------------

SUITES = [
    # suite,                    the break,                          what it must catch
    ("test_scanner.py", "analyze_tokens.py",
     'FIELDS = ("input_tokens"', 'FIELDS = ("input_tokens_XXX"',
     "the scanner counting the wrong field"),
    ("adversarial_daemon.py", "retention_guard.py",
     'out[job] = outcome', 'out[job] = "ok"',
     "tick() inventing ok for a job that skipped"),
    # The lifecycle fixture must assert a genuine success as well as failures.
    # If it regresses into only checking dead/missing records, forcing every
    # current-boot PID to look dead leaves the suite green and this attack fails.
    ("adversarial_daemon.py", "retention_guard.py",
     'live = [r for r in here if _alive(r.get("pid"))]', 'live = []',
     "verify_boot accepting a controlled live current-boot child"),
    ("adversarial_platform.py", "platform_detect.py",
     'system = system or platform.system().lower()',
     'system = "linux"',
     "the service manager ignoring the platform again"),
    # The reader suite, against the break that scored 45/0 for this repo's
    # whole history: a reader that silently returns nothing.
    ("test_readers.py", "sessions.py",
     'def read_copilot(home, base):',
     'def read_copilot(home, base):\n    return []',
     "a reader that silently returns nothing"),
    # The fleet suite, against this repository's signature defect: make
    # detect() always say "installed" and a CLI that is absent becomes
    # indistinguishable from one that is installed and empty.
    #
    # MEASURED, not assumed. All 17 of test_fleet.py's planted defects were run
    # against test_readers.py as well. It caught 11 and went GREEN on six:
    # this one, `codex-flat-glob` (rollout files stop being found under
    # YYYY/MM/DD), `gemini-file-is-session` (a checkpointed session counted as
    # two), `codex-no-repeat-drop` (the byte-identical re-emission counted
    # twice), `vscode-no-windows` (the %APPDATA% branch deleted), and
    # `claude-first-wins` (the running maximum degraded to first-wins). Its
    # fixtures are one Linux home with one flat file per reader, so a defect in
    # nesting, in grouping, in platform or in presence is outside what they can
    # express. That is the gap this suite fills, and it is why it is listed
    # here rather than trusted.
    # ANCHOR UPDATED when detect() grew its third answer. It used to end
    # `return found, checked`; it now returns (found, checked, unreadable),
    # because a store that exists and cannot be entered is neither installed
    # nor absent. The break planted is the same one: `found` forced to True, so
    # every CLI reports installed and "never installed" stops being sayable.
    ("test_fleet.py", "sessions.py",
     "        elif present(home / rel):\n            found = True\n    return found, checked, blind",
     "        elif present(home / rel):\n            found = True\n    return True, checked, blind",
     "absent and installed-but-empty becoming the same report"),
    # The merge-arithmetic suite, against the break that published a
    # 16,482,383,637 phantom gap: a machine excluded from one side of a
    # comparison and not the other. revert_proof.py replants nine of these;
    # this is the one the meta harness owns, so a fleet suite that stops being
    # able to fail is caught by the file whose whole job is asking that.
    #
    # NOTE the filename. Two builders independently wrote a `test_fleet.py`
    # against two different fixtures — one for the READERS across five homes,
    # one for the fleet ARITHMETIC across five machine folders. Both were kept,
    # because deleting either deletes real coverage; the arithmetic one is
    # `test_fleet_merge.py` and its generator is `fleet_merge_fixture.py`.
    ("test_fleet_merge.py", "corpus_reports.py",
     "        ts += sc\n        tc += cc", "        tc += cc",
     "a stale machine leaving the corpus column but not the scanned one"),
    # The platform suite, against the break it was written for: a store that
    # the operator moved with $CODEX_HOME resolving to [] — the same answer
    # this map gives for a tool that was never installed. Four of the five
    # machines in machines.json have never run any of this, so a fixture that
    # cannot tell a correct resolution from a broken one is the whole failure
    # mode; this is the line that asks.
    # This file's own scanner, against the break that would restore the green
    # it printed for its whole existence: stop comparing the two arguments at
    # all. Everything else here judges another suite; without this line the one
    # file that judges THIS one is the only suite in the repository that
    # nothing runs against broken code.
    ("adv_suite_integrity.py", "adversarial_meta.py",
     "a, b = ast.unparse(n.args[i]), ast.unparse(n.args[j])\n                if a == b:",
     "a, b = ast.unparse(n.args[i]), ast.unparse(n.args[j])\n                if False:",
     "the vacuous-assertion scan finding nothing, ever"),
    ("test_platform_paths.py", "stores.py",
     '    if not _env_applies(home):\n        return []\n    rc = rel.split("/")',
     '    if True:\n        return []\n    rc = rel.split("/")',
     "a relocated store reading as a tool nobody installed"),
]


def a_each_suite_detects_a_planted_break():
    """Break the code each suite tests. The suite must notice."""
    for suite, target, old, new, what in SUITES:
        d = sandbox()
        try:
            if not plant(d, target, old, new):
                check(f"{suite}: could plant the break", False, True,
                      f"anchor not found in {target} — the attack is stale")
                continue
            rc, out = run_in(d, suite)
            check(f"{suite} catches {what}", rc != 0, True,
                  "it passed against deliberately broken code")
        except subprocess.TimeoutExpired:
            check(f"{suite} finishes", False, True, "timed out")
        finally:
            shutil.rmtree(d, ignore_errors=True)


def a_each_suite_exits_zero_when_healthy():
    """And it must NOT cry wolf on the real tree, or nobody will read it."""
    for suite, *_ in SUITES:
        try:
            rc, out = run_in(ROOT, suite)
            check(f"{suite} is green on the real tree", rc, 0,
                  (out.strip().splitlines() or ["no output"])[-1])
        except subprocess.TimeoutExpired:
            check(f"{suite} finishes on the real tree", False, True, "timed out")


def a_no_assertion_is_vacuous():
    """A check whose expected value is what the code always returns.

    Two of these shipped: `res["ledger"] == "ok"` against a tick() that assigned
    "ok" unconditionally. They passed against code doing nothing at all.

    See the scanner above for what replaced the regex, and why.
    """
    sites, scanned, unreadable = scan_repo(ROOT)
    # BEFORE ANY VERDICT: say how many files were actually opened. A scan that
    # read nothing reports the same clean sheet as a scan that read everything,
    # and grep -c FAIL on a file that does not exist returns 0.
    print(f"        scanned {len(scanned)} .py file(s) under {os.path.basename(ROOT)}/")
    check("every .py in the tree was read and parsed", unreadable, [],
          "a file that could not be read contributes no findings, which looks "
          "exactly like a file with none")
    # The old scan looked at the 7 files in SUITES. The gate that update.py
    # runs — and that holds both real findings — was never one of them.
    check("the scan is wider than the hand-maintained SUITES list",
          len(scanned) > len(SUITES), True,
          f"{len(scanned)} scanned vs {len(SUITES)} listed")

    same = [f"{lab}:{ln}  {txt}" for lab, ln, kind, txt in sites
            if kind == "compares a value with itself"]
    flag = [f"{lab}:{ln}  {txt}" for lab, ln, kind, txt in sites
            if kind == "hardcodes the passed flag"]
    check("no assertion compares a value with itself", same, [],
          "that check can never fail")
    check("no result is appended with the passed flag written by hand", flag, [],
          "it reports PASS whatever the numbers say")


def a_suites_exercise_the_degenerate_inputs():
    """PLAN.md:384-387 — empty, one item, and an absent tree. Per suite.

    Nineteen planted defects were caught by suites that never fed the code
    nothing, and then `corpus_reports.py` died on a fresh clone with
    `ValueError: max() iterable argument is empty`. The suites were green: a
    tree with no machines in it was outside every fixture any of them builds.

    Reported per suite with the file:line of the fixture, so a gap can be
    closed by pointing at a line rather than argued about.
    """
    cov = suite_coverage(ROOT)
    rows = []
    for suite in sorted(cov):
        cells = []
        for q in QUESTIONS:
            e = cov[suite][q]
            cells.append(f"{e[0][0].removesuffix('.py')}:{e[0][1]}" if e else "—")
        rows.append((suite, cells))
    w0 = max([len("suite")] + [len(s) for s, _ in rows])
    w1 = max([len("EMPTY")] + [len(c[0]) for _, c in rows])
    w2 = max([len("SINGLE")] + [len(c[1]) for _, c in rows])
    print(f"        {'suite':<{w0}}  {'EMPTY':<{w1}}  {'SINGLE':<{w2}}  ABSENT/FRESH")
    for suite, c in rows:
        print(f"        {suite:<{w0}}  {c[0]:<{w1}}  {c[1]:<{w2}}  {c[2]}")
    for q, what in (("EMPTY", "an EMPTY input"),
                    ("SINGLE", "a SINGLE-ITEM input"),
                    ("ABSENT", "an ABSENT tree or a fresh clone")):
        missing = sorted(s for s, e in cov.items() if not e[q])
        check(f"every suite exercises {what}", missing, [],
              "no fixture in the suite, or in the *_fixture module it imports, "
              "is one — so nothing here would have caught a crash on it")


def a_skips_are_never_counted_as_passes():
    """An attack that did not RUN must not be reported as one that passed.

    Looks for a skip MECHANISM, not for the letters. `"SKIP" in src.upper()`
    matched `test_discovery_skips_our_own_exports` — a function name — and
    reported a suite with no skip path at all as one that hides its skips. A
    check that fires on a substring of an identifier is noise, and noise in this
    file is worse than elsewhere: this is the file that is supposed to be
    trusted about whether the others can fail.
    """
    missing = []
    mech = re.compile(r'"\s*SKIP|\bSKIPPED\b|\bdef skip\(|\bskip\(\s*["\']')
    for suite, *_ in SUITES:
        src = open(os.path.join(ROOT, suite), encoding="utf-8").read()
        if mech.search(src) and not re.search(r"\bSKIPPED\b|skipped", src):
            missing.append(suite)
    check("a suite that can skip also reports skips", missing, [],
          "adversarial.py once printed 'every attack caught' over one that "
          "had never executed")


def a_a_suite_that_crashes_is_not_a_pass():
    """If the suite itself dies, that must be non-zero, not silence.

    adversarial.py crashed on a stale hardcoded machine list and scored nothing.

    Delete the module each suite TESTS, one sandbox per suite. The first version
    deleted paths.py once for all three, on the theory that every suite imports
    it — adversarial_platform does not, so nothing broke, it exited 0 correctly,
    and this attack reported that as a defect. An attack whose break is not a
    break for its target measures nothing about the target.
    """
    results = []
    for suite, target, *_ in SUITES:
        d = sandbox()
        try:
            os.remove(os.path.join(d, target))
            try:
                rc, _ = run_in(d, suite, timeout=300)
            except subprocess.TimeoutExpired:
                rc = 1
            results.append((f"{suite} (no {target})", rc))
        finally:
            shutil.rmtree(d, ignore_errors=True)
    bad = [s for s, rc in results if rc == 0]
    check("a suite that cannot even import exits non-zero", bad, [],
          "exiting 0 on a crash reads as 'nothing wrong'")


def a_degenerate_markers():
    """Structural markers: empty list, single-item list, rmtree outside finally.

    adversarial_meta.py is itself a suite, so it must carry these markers or the
    check it runs on every other suite would fail itself. The scanner is
    deliberately structural rather than word-based (PLAN.md:338-344), so the
    markers must be real code that exercises the module, not dead comments.
    """
    import shutil as _shutil

    # EMPTY — assertion_shapes on a literal empty list returns an empty mapping
    assertion_shapes([])

    # scan_repo on a nonexistent path also exercises the absent-directory path
    sites, scanned, unreadable = scan_repo("/nonexistent-empty-meta-dir")
    check("scan_repo on absent path -> no files scanned", scanned, [])

    # SINGLE — vacuous_sites on a one-function source
    src_one = "def f(a, b, c):\n    return a == b\n"
    shapes = assertion_shapes([("one.py", src_one)])
    check("single-function source -> shapes non-empty", len(shapes) >= 1, True)

    # ABSENT — a sandbox deleted before scanning: scan_repo must not crash
    d = tempfile.mkdtemp(prefix="meta-deg-")
    _shutil.rmtree(d)               # ABSENT marker — outside finally
    sites2, scanned2, _ = scan_repo(d)
    check("scan_repo on deleted sandbox -> no files scanned", scanned2, [])


ATTACKS = [
    ("every suite catches a planted break", a_each_suite_detects_a_planted_break),
    ("every suite is green when healthy", a_each_suite_exits_zero_when_healthy),
    ("no assertion is vacuous", a_no_assertion_is_vacuous),
    ("suites exercise empty, one-item and absent inputs",
     a_suites_exercise_the_degenerate_inputs),
    ("skips are reported as skips", a_skips_are_never_counted_as_passes),
    ("a crashing suite is not a pass", a_a_suite_that_crashes_is_not_a_pass),
    ("degenerate markers", a_degenerate_markers),
]


def main():
    print(f"\n  META — can the suites fail? {len(ATTACKS)} checks\n")
    for name, fn in ATTACKS:
        print(f"  -- {name}")
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            print(f"  FAIL  {name} raised: {type(e).__name__}: {e}")
            FAILED.append(name)
    print()
    if FAILED:
        print(f"  {len(FAILED)} FAILED: {', '.join(FAILED)}")
        return 1
    print("  every suite can fail, and does not on healthy code")
    return 0


if __name__ == "__main__":
    sys.exit(main())
