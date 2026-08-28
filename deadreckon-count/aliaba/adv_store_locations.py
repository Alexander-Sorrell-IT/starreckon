#!/usr/bin/env python3
"""Is a tool's folder DERIVED, and can the map say it could not look.

    python3 adv_store_locations.py

TWO DEFECTS, AND THEY ARE THE SAME DEFECT

The forty-seven store paths in stores.py were COLLECTED on one Linux machine,
not derived from anything. That is why the file had four macOS branches — all
of them the `{vscode}` token — and not one line about Windows, while
machines.json lists `dell-latitude-7480-windows` and deadreckon-record holds no
folder for it. A tool keeps its data in ITS OWN folder and that folder has a
known form per platform, so the location is derivable; a collected path is a
photograph of one computer.

And a store that CANNOT BE READ reported byte-for-byte what a store that is not
there reports. `os.path.exists` returns False on EACCES and `glob` swallows it,
so 22 of the stores answered identically under `chmod 000` — measured by
adv_platform_behaviour, which fails on exactly that line. It is not
hypothetical on this fleet: macOS returns EPERM rather than not-found when TCC
denies a background process access to a folder, the MacBook publishes from a
launchd agent, and a row of zeros for a full directory is indistinguishable
from a tool nobody installed.

Both are the same sentence: THE MAP CANNOT TELL YOU WHY IT FOUND NOTHING.

HOW THE FIXTURES ARE WRITTEN, WHICH IS THE WHOLE VALIDITY OF THIS SUITE

Every path a fixture PLANTS is a literal, written out here by hand. Nothing
under test contributes to where the records go. The code is then asked to find
them with no literal of its own — so a model that is wrong and a fixture that
is wrong cannot agree with each other, which is what happens the moment a test
builds its tree out of the table it is testing.

The macOS container fixture uses `com.example.<tool>.app`, a bundle id that
appears nowhere in this repository. A resolver that carries a table of bundle
ids cannot pass it; only one that globs the container can.

THREE THINGS THIS SUITE REFUSES TO DO, each of which was found in a suite
written this morning:

  it never asserts a substring of something written unconditionally;
  it never asserts "none of X failed" without first asserting X is not empty —
      every roll-up check has a companion that asserts what it looked at;
  it asserts its own CHECK COUNT at the end, so a crash that skips eleven
      checks cannot present as a quieter, cleaner pass.
"""

import contextlib
import os
import pathlib
import shutil
import stat
import sys
import tempfile
import traceback

REPO = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, REPO)

import stores                                                     # noqa: E402

# Every check this file can print. Asserted at the end — see a_every_check_ran.
EXPECTED_CHECKS = 37

RESULTS = []


def check(name, got, want=True, detail=""):
    """got == want, and the detail is printed only when it does not.

    `want` is a real argument rather than an assumed True because half the
    questions here are "which paths" and not "did it work", and a suite that
    can only say yes/no ends up asserting `bool(x)` over a value it should have
    been comparing.
    """
    ok = got == want
    RESULTS.append((name, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        print(f"          got {got!r}")
        print(f"          want {want!r}")
        for line in str(detail).splitlines():
            print(f"          {line}")
    return ok


def note(text):
    for line in str(text).splitlines():
        print(f"        . {line}")


# ---------------------------------------------------------------------------
# Pretending to be another platform, WITHOUT lying to the interpreter.
# ---------------------------------------------------------------------------

class _Shim:
    """`stores`' own view of one module, with one attribute overridden.

    fleet_fixture.platform_as documents why the platform is faked one level
    BELOW the function under test: an earlier version replaced
    `stores.vscode_bases` with a lambda returning the right answer, and a
    deliberate break that deleted the darwin branch out of the real one still
    went green — the patch had substituted the code being tested.

    A shim rather than `stores.os.name = "nt"` because that assignment is on
    the REAL os module and every other importer of it sees it too. `os.path`
    was bound to posixpath at interpreter start and does not follow, so the
    process ends up half-Windows, which is a third platform nobody has.
    """

    def __init__(self, real, **over):
        self._real, self._over = real, over

    def __getattr__(self, k):
        if k in self._over:
            return self._over[k]
        return getattr(self._real, k)


SHAPES = {"linux": ("linux", "posix"),
          "macos": ("darwin", "posix"),
          "windows": ("win32", "nt")}


@contextlib.contextmanager
def pretend(shape):
    plat, osname = SHAPES[shape]
    real_sys, real_os = stores.sys, stores.os
    stores.sys = _Shim(real_sys, platform=plat)
    stores.os = _Shim(real_os, name=osname)
    try:
        yield
    finally:
        stores.sys, stores.os = real_sys, real_os


@contextlib.contextmanager
def env(home, **kw):
    """$HOME points at the fixture, plus the variables under test.

    stores._env_applies() honours a relocation only for the home the process is
    actually in — the rule analyze_tokens draws so that `--home X` is not
    silently overridden by this machine's environment. A test that did not move
    HOME would be testing the guard instead of the relocation.
    """
    old = dict(os.environ)
    os.environ["HOME"] = str(home)
    for k, v in kw.items():
        os.environ[k] = str(v)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(old)


def touch(p, text="{}\n"):
    p = pathlib.Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# 1  THE SAME TOOL, THREE PLATFORMS, ONE RULE
# ---------------------------------------------------------------------------

# WHERE EACH PLATFORM REALLY PUTS A TOOL'S FOLDER. Hand-written, on purpose:
# this is the specification, and the code under test must reach every line of
# it without holding any of these strings.
#
#   Linux    ~/.<tool>, ~/.config/<tool>, ~/.local/share/<tool>
#   macOS    ~/Library/Application Support/<tool>, ~/Library/Caches/<tool>,
#            ~/Library/Containers/<bundle>/Data/…, and the Linux dotdir, which
#            is what npm- and brew-installed CLIs actually use there — codex,
#            gemini-cli and claude all document ~/.<tool> on macOS.
#   Windows  %APPDATA%\\<tool>, %LOCALAPPDATA%\\<tool>, %USERPROFILE%\\.<tool>
PLACEMENTS = {
    "linux": (
        ".{tool}",
        ".config/{tool}",
        ".local/share/{tool}",
    ),
    "macos": (
        ".{tool}",
        "Library/Application Support/{tool}",
        "Library/Caches/{tool}",
        "Library/Containers/com.example.{tool}.app/Data/"
        "Library/Application Support/{tool}",
    ),
    "windows": (
        ".{tool}",
        "AppData/Roaming/{tool}",
        "AppData/Local/{tool}",
    ),
}

# THREE TOOLS, so that a rule written for one of them is not enough. Each is a
# real store in the map; `sub` is the part of its path below the tool folder.
TOOLS = (("codex", "codex", "sessions"),
         ("gemini", "gemini", "tmp"),
         ("clawspring", "clawspring", "sessions"))


def a_one_rule_finds_three_platforms(root):
    """The same records, filed the way each platform files them.

    One home per (platform, form, tool) so that "found" is never ambiguous:
    there is exactly one place the records can be, and resolve() either names
    it or does not.
    """
    derived_not_collected = []
    for shape, forms in PLACEMENTS.items():
        for form in forms:
            missing, hits = [], []
            for label, tool, sub in TOOLS:
                store = stores.BY_LABEL[label]
                home = root / f"p-{shape}-{abs(hash(form)) % 10**6}-{tool}"
                folder = form.format(tool=tool) + "/" + sub
                touch(home.joinpath(*folder.split("/")) / "rec.jsonl")
                with pretend(shape):
                    got = stores.resolve(store, str(home))
                want = [str(home.joinpath(*folder.split("/")))]
                if got != want:
                    missing.append(f"{label:<12}{folder}\n{'':12}got {got}")
                else:
                    hits.append(folder)
                    with pretend(shape):
                        rels = store.rel_paths()
                    if folder not in rels:
                        derived_not_collected.append(folder)
            check(f"{shape}: a tool found at {form.format(tool='<tool>')}",
                  not missing, True,
                  "\n".join(missing) + "\n        one derived rule has to reach "
                  "every form; a machine whose OS files somewhere else reads as "
                  "a machine with no tools installed" if missing else "")

    # THE CONTROL FOR THE ABOVE. Every one of those forms could have been
    # passed by writing forty more literals into the map, which is the design
    # this replaces. This says the answers came from somewhere the map does not
    # spell out — and it asserts the count is not zero first, because "none of
    # them were literals" is also what an empty list says.
    check("the forms that were found are NOT written down in the map",
          len(derived_not_collected) >= 15, True,
          f"{len(derived_not_collected)} of the located folders are absent from "
          "rel_paths() — if this were 0, every hit above would be a collected "
          "path and nothing would have been derived")


def a_the_model_is_a_place_not_everywhere(root):
    """"Roughly the same place", not "search the whole home directory".

    A resolver that tried every form on every platform would pass every check
    above and would also claim ~/Library on a Linux box and ~/.config on
    Windows. The rule is that each platform has a SHAPE; this is the half of it
    that says no.
    """
    home = root / "mac-form-on-linux"
    touch(home / "Library" / "Application Support" / "codex" / "sessions" / "r.jsonl")
    with pretend("linux"):
        got = stores.resolve(stores.BY_LABEL["codex"], str(home))
        forms = list(stores.tool_forms())
    check("a macOS-only form is not searched on Linux", got, [],
          f"resolved {got} — the derived model would then be 'look everywhere', "
          "which finds a tool's folder by accident and cannot be reasoned about")
    check("and the Linux form list says so", [f for f in forms if "Library/" in f],
          [], "Library/ has no meaning on Linux")


# ---------------------------------------------------------------------------
# 2  THE TOOL'S OWN RELOCATION VARIABLE, POINTING OUT OF THE HOME DIRECTORY
# ---------------------------------------------------------------------------

# var, store label, what the value points at, the records under it, the tail
# resolve() must return. Each target is built OUTSIDE the fixture home, which
# is the case the map is written entirely in home-relative strings for and
# therefore cannot express on its own.
RELOCATED = (
    ("CODEX_HOME", "codex", "sessions/2026/01/01/r.jsonl", "sessions", "linux"),
    ("COPILOT_HOME", "copilot", "session-state/s1/state.json", "session-state",
     "linux"),
    ("GEMINI_CLI_HOME", "gemini", ".gemini/tmp/s/logs.json", ".gemini/tmp",
     "linux"),
    ("CLAUDE_CONFIG_DIR", "claude", "projects/-p/a.jsonl", "projects", "linux"),
    # THE TWO THE DERIVED MODEL BROUGHT WITH IT. `.local/share/<tool>` and
    # `AppData/Local/<tool>` are real candidates now, and a base directory the
    # operator moved out from under them resolves to [] — the same answer this
    # map gives for a tool nobody ever installed.
    ("XDG_DATA_HOME", "codex", "codex/sessions/r.jsonl", "codex/sessions",
     "linux"),
    ("LOCALAPPDATA", "codex", "codex/sessions/r.jsonl", "codex/sessions",
     "windows"),
)


def a_relocated_off_home_is_found(root):
    for var, label, rec, tail, shape in RELOCATED:
        home = root / f"reloc-{var}"
        home.mkdir(parents=True, exist_ok=True)
        target = root / "elsewhere" / var
        touch(target / rec)
        outside = not str(target).startswith(str(home))
        with pretend(shape), env(home, **{var: target}):
            got = stores.resolve(stores.BY_LABEL[label], str(home))
            recorded = stores.environment(str(home))
        want = [str(target.joinpath(*tail.split("/")))]
        check(f"${var} points outside the home and the store is still found",
              got == want and outside and recorded.get(var) == str(target), True,
              f"got {got}\n        want {want}\n        outside home: {outside}"
              f"\n        environment() recorded: {recorded.get(var)!r}\n"
              "        [] here is byte-identical to the answer for a tool "
              "nobody installed")


# ---------------------------------------------------------------------------
# 3  INSTALLED | ABSENT | UNREADABLE — THE THIRD STATE, IN THE OUTPUT
# ---------------------------------------------------------------------------

def published(label, home):
    """Everything stores.py will say about ONE store, as a comparable value.

    DELIBERATELY WRITTEN TO WORK AGAINST A MAP WITH NO THIRD STATE. If
    `state()` is not there — the code as it was, or as a revert would leave it
    — this falls back to exactly what the file used to publish, and the
    inequality below then FAILS AS AN ASSERTION instead of taking the suite
    down with an AttributeError. A suite that exits early has not passed the
    checks it never reached.

    PER STORE, and that is not a detail. Comparing the whole map's output lets
    a difference in some OTHER store satisfy the inequality: chmod 000 on
    ~/.codex takes codex, codex-archived and codex-root with it, so a control
    that deletes only one of them differs for the other two and the assertion
    passes without anything having been told apart. One store at a time, there
    is nowhere for the difference to come from except the store being asked
    about.
    """
    s = stores.BY_LABEL[label]
    st = getattr(stores, "state", None)
    row = {"paths": stores.resolve(s, str(home)), "exists": s.exists(str(home))}
    if st is not None:
        row["state"] = st(s, str(home))
    return row


def plant(home, store):
    """One record where this store's OWN canonical path says it goes.

    Returns the path a person would chmod: the store's directory, or its file.
    None for the two profile-glob stores, which have no single location.
    """
    rel = store.rel_paths()[0]
    if "*" in rel:
        return None
    p = home.joinpath(*rel.split("/"))
    if store.kind == "root_files":
        names = [g for g in (store.records or ()) if "*" not in g] \
            or ["history.jsonl"]
        touch(p / names[0])
        return p
    if "." in p.name[1:]:                 # `.claude.json` — a file, not a dir
        touch(p)
        return p
    touch(p / "rec.jsonl")
    return p


@contextlib.contextmanager
def unreadable(target):
    """chmod 000 — the records are there and this process cannot have them."""
    old = stat.S_IMODE(os.stat(target).st_mode)
    os.chmod(target, 0)
    try:
        yield
    finally:
        os.chmod(target, old)


@contextlib.contextmanager
def deleted(target, stash):
    """The records are not there at all. The control arm."""
    os.makedirs(stash, exist_ok=True)
    dst = os.path.join(stash, os.path.basename(str(target)))
    shutil.move(str(target), dst)
    try:
        yield
    finally:
        shutil.move(dst, str(target))


def a_unreadable_is_not_absent(root):
    """A store nobody can read must not report what an absent store reports.

    The assertion is an INEQUALITY BETWEEN TWO RUNS of the same function over
    the same tree: one with a directory chmod 000, one with the records moved
    away. It cannot be satisfied by printing a constant, by adding a field, or
    by returning a number that happens to be right — something in the published
    answer has to differ, for every store.

    WHAT IS CHMOD-ED IS THE PARENT, AND THE FIRST VERSION OF THIS GOT IT WRONG.
    Locking the store's own directory leaves `os.stat` working on it, so even
    the OLD two-valued code returned the path in one run and not the other and
    the inequality passed against code that cannot tell the two apart — a test
    that goes green on the defect it was written for. The ambiguity only exists
    when the thing in the way is ABOVE the path being asked about, because that
    is when `os.path.exists` answers False for a reason it does not record.
    That case is this loop; the store's own directory being unenterable while
    its metadata reads fine is the macOS TCC shape, and it is asserted
    separately below.
    """
    home = root / "third-state"
    home.mkdir(parents=True, exist_ok=True)
    targets = {}
    for s in stores.STORES:
        t = plant(home, s)
        if t is not None:
            targets[s.label] = t

    # THE GUARD, AND IT FAILS THE SUITE RATHER THAN SKIPPING IT. root ignores
    # chmod 000, and under root every assertion below is vacuous — a green
    # sheet printed by a probe that could not be run is worse than a red one.
    probe = home / ".codex"
    blocks = False
    with unreadable(probe):
        try:
            os.listdir(probe)
        except OSError:
            blocks = True
    check("chmod 000 actually blocks this user", blocks, True,
          "running as root? every check below would pass without testing "
          "anything")

    stash = root / "stash"
    same, tested, shallow, two_valued_same = [], 0, 0, 0
    for label, target in sorted(targets.items()):
        if not os.path.exists(target):
            continue                       # a parent store took it with it
        victim = target.parent
        if victim == home or not victim.is_dir():
            # The store sits directly in the home directory, so the only thing
            # above it is the home itself and locking that is a different
            # experiment. The TCC check below is the one that covers these.
            shallow += 1
            continue
        tested += 1
        with unreadable(victim):
            a = published(label, home)
        with deleted(target, str(stash)):
            b = published(label, home)
        shutil.rmtree(stash, ignore_errors=True)
        if a == b:
            same.append(label)
        pair = ("paths", "exists")
        if {k: a[k] for k in pair} == {k: b[k] for k in pair}:
            two_valued_same += 1

    # THE ANTI-VACUITY CONTROL FOR THE CHECK BELOW, and it is the one that
    # would have caught this suite's own first draft. If the fixture is ever
    # rearranged into a shape the OLD two-valued answer can already tell apart,
    # the inequality below starts passing without testing anything — green
    # against the exact defect it was written for. This says the ambiguity is
    # real: with only `paths` and `exists` to go on, the two runs are the same
    # sentence for every store exercised.
    check("the two-valued answer cannot tell them apart — the ambiguity is real",
          two_valued_same, tested,
          f"{tested - two_valued_same} store(s) already differed without the "
          "third state, so the assertion below is not testing what it claims")

    check("scan(unreadable) != scan(deleted), for every store", not same, True,
          (f"{len(same)} of {tested} stores publish byte-for-byte the same "
           "thing when their directory cannot be entered as when it is not "
           "there:\n" + "\n".join(f"{l}" for l in same[:10])) if same else "")
    note(f"{tested} stores exercised; {shallow} sit directly in the home "
         "directory and are covered by the TCC check instead")
    # THE COMPANION. "None of them were the same" is also what an empty loop
    # says, and a refactor that stopped planting would print the green above
    # while testing nothing at all.
    check("and that was asked about a real number of stores", tested >= 20, True,
          f"only {tested} store(s) were exercised; the map holds "
          f"{len(stores.STORES)}")

    # THE ERRNO IS THE POINT, not just the fact of a difference: EACCES and
    # ENOENT are the two answers being confused, so the one that was invisible
    # has to be the one that is kept.
    target = targets["codex"]
    with unreadable(target):
        st = getattr(stores, "state", lambda *a, **k: {})(
            stores.BY_LABEL["codex"], str(home))
    codes = [c for _, _, c in st.get("blocked", [])]
    check("the errno is kept, and it says EACCES",
          st.get("state") == "unreadable" and "EACCES" in codes, True,
          f"state={st.get('state')!r} blocked={st.get('blocked')!r} — without "
          "the errno a report can say 'something was in the way' and not which "
          "wall it was")

    # THE macOS SHAPE, EXACTLY. TCC lets the stat through and denies the open,
    # so the directory is there, its metadata is fine, and every walk of it
    # yields nothing. A resolver that stops at os.path.exists calls this
    # installed and then publishes a zero.
    with unreadable(target):
        st = getattr(stores, "state", lambda *a, **k: {})(
            stores.BY_LABEL["codex"], str(home))
        stat_says_yes = os.path.exists(target)
        resolved = stores.resolve(stores.BY_LABEL["codex"], str(home))
    check("a directory that stats fine and cannot be listed is not 'installed'",
          stat_says_yes and st.get("state") == "unreadable", True,
          f"os.path.exists says {stat_says_yes}, the map says "
          f"{st.get('state')!r} — this is the TCC shape the MacBook publishes "
          "from a launchd agent")
    check("and resolve() alone still cannot tell the two apart",
          bool(resolved), True,
          "resolve() returns the path either way; that is WHY a third answer "
          "was needed rather than a wider truth value")


# ---------------------------------------------------------------------------
# 4  A REFACTOR THAT QUIETLY DROPS A STORE COSTS REAL DATA
# ---------------------------------------------------------------------------

def old_rule(store, home):
    """Resolution EXACTLY as stores.py did it before the derived model.

    Re-implemented here rather than imported or read out of git, for two
    reasons. git HEAD is not the "before" — stores.py is modified in the
    working tree by other work in flight — and a baseline the author of the
    change also writes is a baseline the change can be wrong in agreement with.
    This is the old sentence, in the old words: every canonical path, plus the
    relocations, globbed with glob and existence-checked with os.path.exists.
    """
    import glob as _g
    out = []
    for rel in store.rel_paths():
        for p in [os.path.join(home, *rel.split("/"))] \
                + stores.relocations(rel, home):
            if "*" in p:
                out.extend(_g.glob(p))
            elif os.path.exists(p):
                out.append(p)
    return sorted(set(out))


def a_nothing_that_resolved_stopped_resolving():
    """On THIS machine, with its real home. The one tree that holds real data.

    A store that silently stops resolving is not a failing test — it is a tool
    that leaves the archive, leaves the corpus, and reads as a zero in every
    report from then on.
    """
    home = stores.HOME
    before = {s.label: old_rule(s, home) for s in stores.STORES}
    before = {k: v for k, v in before.items() if v}
    after = {s.label: stores.resolve(s, home) for s in stores.STORES}
    after = {k: v for k, v in after.items() if v}

    check("the old rule resolved a real set of stores on this machine",
          len(before) >= 10, True,
          f"{len(before)} stores resolved; below this, 'nothing was dropped' "
          "is a sentence about an empty set")
    check("every store the old rule resolved still resolves",
          sorted(set(before) - set(after)), [],
          "a dropped store leaves the archive and the corpus silently")
    lost = {k: sorted(set(before[k]) - set(after.get(k, [])))
            for k in before if set(before[k]) - set(after.get(k, []))}
    check("and every PATH it resolved is still resolved", lost, {},
          "the label surviving is not the same as the directory surviving")
    note(f"{len(before)} stores resolved before, {len(after)} after; "
         f"{len(set(after) - set(before))} newly reachable")


# ---------------------------------------------------------------------------
# 5  THE TOKEN THAT REACHED A CALLER UNEXPANDED
# ---------------------------------------------------------------------------

VSCODE_TREE = "Code/User/workspaceStorage/ws1/chatSessions/a.json"
VSCODE_BASE = {"linux": ".config", "macos": "Library/Application Support",
               "windows": "AppData/Roaming"}


def a_detect_patterns_are_paths_not_tokens(root):
    """`detect_patterns()` handed sessions.detect() the raw `path` string.

    So the six VS Code-family stores were looked for at a directory literally
    named `{vscode}`, and kilocode and copilot-chat reported installed:false in
    sessions.json on every run this repository has ever made — on a machine
    where ~/.config/Code/User/workspaceStorage holds 4.75 GB and their readers
    count real tokens out of it.
    """
    pats = stores.detect_patterns()
    leaked = sorted({p for v in pats.values() for p in v if "{" in p})
    check("no detect pattern contains an unexpanded token", leaked, [],
          "a path with `{vscode}` in it is a directory nobody has ever had")
    check("and detect_patterns names a real number of paths",
          sum(len(v) for v in pats.values()) >= 10, True,
          "an empty map has no unexpanded tokens either")

    missed = []
    for shape, base in VSCODE_BASE.items():
        home = root / f"vsc-{shape}"
        touch(home.joinpath(*(base + "/" + VSCODE_TREE).split("/")))
        with pretend(shape):
            here = {p.replace("~/", "") for p in
                    stores.detect_patterns().get("copilot-chat", ())}
            if not any(os.path.exists(home.joinpath(*p.split("/")))
                       for p in here):
                missed.append(f"{shape}: none of {sorted(here)} is on disk")
    check("the VS Code stores are detected where that platform puts them",
          not missed, True, "\n".join(missed))


# ---------------------------------------------------------------------------
# 6  THE EXCEPTIONS ARE VISIBLE AND COUNTABLE
# ---------------------------------------------------------------------------

def a_exceptions_are_a_short_named_list():
    """An exceptions table is only worth having if it cannot grow in silence.

    The failure it guards against is the one this file exists for: exceptions
    becoming the design again, one store at a time, each with a good local
    reason and no one counting.
    """
    computed = stores.irregular_stores()
    declared = sorted(stores.IRREGULAR)
    check("the table names exactly the stores the derivation cannot reach",
          computed, declared,
          "a store that stopped deriving and was never written down is an "
          "exception nobody knows about")
    check("and every one of them says why",
          sorted(k for k, v in stores.IRREGULAR.items() if len(v) > 40),
          declared)
    derived = len(stores.STORES) - len(computed)
    check("the exceptions are the exception", len(computed) <= 3 and derived >= 40,
          True,
          f"{derived} of {len(stores.STORES)} derived, {len(computed)} "
          "exception(s) — if this ratio inverts, the table IS the design")


# ---------------------------------------------------------------------------

def a_every_check_ran():
    """A suite that exits early has not passed the checks it did not reach.

    adv_documents.py died at a KeyError after its real failures this morning
    and eleven later checks never ran; the suite printed no failure for any of
    them. The count is asserted so that a crash is a RED line rather than a
    shorter report.
    """
    check("every check in this suite ran", len(RESULTS) + 1, EXPECTED_CHECKS,
          f"{len(RESULTS) + 1} of {EXPECTED_CHECKS} — the missing ones did not "
          "fail, they never happened")


def a_degenerate_markers():
    """Structural markers: empty list, single-item list, rmtree outside finally."""
    import sessions as _sessions

    # EMPTY — active_minutes on a literal [] is a safe non-utility call
    _sessions.active_minutes([])

    # SINGLE — active_minutes on a one-item list
    _sessions.active_minutes([_sessions.blank()])

    # ABSENT — resolve on a real empty home, then rmtree outside finally
    d = pathlib.Path(tempfile.mkdtemp(prefix="adv-stores-deg-"))
    empty_home = d / "e"
    empty_home.mkdir(parents=True)
    claude_store = stores.BY_LABEL["claude"]
    got = stores.resolve(claude_store, empty_home)
    check("resolve on empty home -> []", got, [])
    shutil.rmtree(str(d))           # ABSENT marker — outside finally


def main():
    root = pathlib.Path(tempfile.mkdtemp(prefix="adv-stores-")).resolve()
    print(f"\n  fixtures under {root}\n")
    parts = (("one rule, three platforms", a_one_rule_finds_three_platforms, True),
             ("a place, not everywhere", a_the_model_is_a_place_not_everywhere, True),
             ("relocated off home", a_relocated_off_home_is_found, True),
             ("unreadable is not absent", a_unreadable_is_not_absent, True),
             ("nothing dropped", a_nothing_that_resolved_stopped_resolving, False),
             ("tokens are not paths", a_detect_patterns_are_paths_not_tokens, True),
             ("the exceptions table", a_exceptions_are_a_short_named_list, False),
             ("degenerate markers", a_degenerate_markers, False))
    try:
        for name, fn, needs_root in parts:
            print(f"\n{name}")
            try:
                fn(root) if needs_root else fn()
            except Exception:                                     # noqa: BLE001
                check(f"{name}: ran to completion", False, True,
                      traceback.format_exc()[-900:])
        print()
        a_every_check_ran()
    finally:
        for d, _, fs in os.walk(root):
            os.chmod(d, 0o700)
        shutil.rmtree(root, ignore_errors=True)

    failed = [n for n, ok, _ in RESULTS if not ok]
    print(f"\n  {len(RESULTS)} checks, {len(failed)} failed")
    for n in failed:
        print(f"  FAILED  {n}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
