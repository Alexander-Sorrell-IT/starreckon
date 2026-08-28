#!/usr/bin/env python3
"""Does the store map resolve on a macOS layout and on a Windows layout.

    python3 test_platform_paths.py

FOUR OF THE FIVE MACHINES IN machines.json HAVE NEVER RUN THIS CODE, and every
non-Linux claim in the repository is a documentation sentence or the absence of
a branch in somebody's source. stores.py has exactly one platform branch — the
`{vscode}` token — and it exists because the reader and the map disagreed on
macOS and 1,050 tokens went missing. The other forty-odd stores are `$HOME`
dotdirs with no branch at all.

So: build a HOME shaped like each platform, put the SAME records in each, and
run the real resolution code against them. A store that resolves on one shape
and not another, with identical data underneath, is a machine reporting zero for
a tool it is running.

WHAT CANNOT BE TESTED HERE, AND IS NOT PRETENDED TO BE

There is no Windows kernel under this file. `os.name = "nt"` is patched into
`stores` so the `AppData/Roaming` branch is taken, and nothing else is claimed
from it — `os.path` is bound to posixpath at interpreter start and does not
follow, and `pathlib.Path()` starts raising NotImplementedError the moment it
does follow, which is why sessions.pathlib is shimmed for the one test that
constructs a fresh Path. Separator handling on a real Windows filesystem is
UNTESTED and is marked so.

WHERE THE PLATFORM LAYOUT COMES FROM

  ~/.codex          "Codex stores its local state under CODEX_HOME (defaults
                    to ~/.codex)"; on Windows %USERPROFILE%\\.codex.
                    developers.openai.com/codex/config-advanced
  ~/.copilot        "By default, the configuration directory is ~/.copilot
                    (that is, $HOME/.copilot)" on every platform; overridden
                    by COPILOT_HOME.
                    docs.github.com/en/copilot/reference/copilot-cli-reference
                    /cli-config-dir-reference
  ~/.gemini         gemini-cli's packages/core/src/config/storage.ts calls
                    node's homedir() and appends .gemini/ — the dotdir, not
                    ~/Library, on macOS. GEMINI_CLI_HOME overrides homedir(),
                    so the store lands at $GEMINI_CLI_HOME/.gemini.
                    google-gemini/gemini-cli issue #23622
  ~/.claude         ~/.claude on macOS and Linux, %USERPROFILE%\\.claude on
                    Windows; CLAUDE_CONFIG_DIR overrides.
  VS Code family    ~/.config/Code (Linux, honouring XDG_CONFIG_HOME),
                    ~/Library/Application Support/Code (macOS),
                    %APPDATA%\\Code (Windows).

  DOC: none of the above was observed on a real macOS or Windows box from here.
  Each is a documented default with the source named. `.config/goose/sessions`
  is UNKNOWN off Linux and is deliberately not asserted about — goose has moved
  to a SQLite sessions.db and its path strategy could not be established.
"""
import contextlib
import os
import pathlib
import shutil
import sys
import tempfile
import types

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import sessions
import stores

FAILED = []


def check(name, got, want, why=""):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        print(f"        got {got!r}\n        want {want!r}" + (f"\n        — {why}" if why else ""))
        FAILED.append(name)


# --------------------------------------------------------------- fixtures

def touch(p):
    p = pathlib.Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("x")


COMMON = [
    ".claude/projects/-p/aaa.jsonl",
    ".claude.json",
    ".gemini/tmp/sess/logs.json",
    ".gemini/antigravity-cli/brain/n.md",
    ".gemini/antigravity-cli/history.jsonl",
    ".codex/sessions/2026/01/01/rollout.jsonl",
    ".codex/history.jsonl",
    ".copilot/session-state/s1/state.json",
    ".copilot/session-store.db",
    ".grok/sessions/g.json",
    ".lmstudio/conversations/c.json",
]
VSCODE_TREE = [
    "Code/User/workspaceStorage/ws1/chatSessions/a.json",
    "Code/User/globalStorage/kilocode.kilo-code/tasks/t1/api_conversation_history.json",
    "Code - Insiders/User/workspaceStorage/ws2/chatSessions/b.json",
]
SHAPES = {
    #  name      sys.platform  os.name  where the VS Code family sits
    "linux":   ("linux",  "posix", ".config"),
    "macos":   ("darwin", "posix", "Library/Application Support"),
    "windows": ("win32",  "nt",    "AppData/Roaming"),
}


def build(root):
    homes = {}
    for name, (_, _, vsbase) in SHAPES.items():
        h = root / name
        for rel in COMMON:
            touch(h / rel)
        for rel in VSCODE_TREE:
            touch(h / vsbase / rel)
        homes[name] = h
    return homes


@contextlib.contextmanager
def pretend(shape):
    """Take the platform branch under test and claim nothing else from it."""
    plat, osname, _ = SHAPES[shape]
    op, on = stores.sys.platform, stores.os.name
    stores.sys.platform, stores.os.name = plat, osname
    try:
        yield
    finally:
        stores.sys.platform, stores.os.name = op, on


@contextlib.contextmanager
def env(home, **kw):
    """Set $HOME to the fixture as well as the vars under test.

    stores._env_applies() honours a relocation only for the home the process is
    actually in — the rule analyze_tokens already draws, so that `--home X` is
    not silently overridden by this machine's environment. A test that did not
    move HOME would be testing the guard, not the relocation.
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


def rel_to(paths, home):
    return sorted(str(p).replace(str(home), "~") for p in paths)


# --------------------------------------------------------------- the tests

def t_vscode_token_expands_on_every_layout(homes):
    """{vscode} must land on the directory that platform really uses.

    The same three files are on disk under each fixture. A shape that finds them
    and a shape that does not are two machines reporting different totals for
    one dataset.
    """
    for shape, (_, _, vsbase) in SHAPES.items():
        h = homes[shape]
        with pretend(shape):
            got = rel_to(stores.resolve(stores.BY_LABEL["copilot-chat"], str(h)), h)
            kilo = rel_to(stores.resolve(stores.BY_LABEL["kilocode"], str(h)), h)
        check(f"{shape}: copilot-chat resolves under {vsbase}",
              got, [f"~/{vsbase}/Code/User/workspaceStorage"])
        check(f"{shape}: kilocode resolves under {vsbase}",
              kilo, [f"~/{vsbase}/Code/User/globalStorage/kilocode.kilo-code/tasks"])


def t_same_data_same_stores(homes):
    """Identical records under three home shapes -> identical store coverage."""
    found = {}
    for shape in SHAPES:
        with pretend(shape):
            found[shape] = sorted(s.label for s in stores.STORES
                                  if stores.resolve(s, str(homes[shape])))
    check("macOS finds exactly what Linux finds, on identical data",
          found["macos"], found["linux"])
    check("Windows finds exactly what Linux finds, on identical data",
          found["windows"], found["linux"],
          "a store that resolves on one shape and not another is a machine "
          "reporting zero for a tool it is running")
    check("and that is not the empty set", len(found["linux"]) > 10, True)


def t_dotdir_stores_resolve_everywhere(homes):
    """A literal $HOME dotdir has no platform branch. It must not need one."""
    for shape in SHAPES:
        with pretend(shape):
            missing = [lbl for lbl in ("gemini", "codex", "copilot", "claude",
                                       "grok", "lmstudio", "codex-root",
                                       "copilot-root", "gemini-antigravity-brain")
                       if not stores.resolve(stores.BY_LABEL[lbl], str(homes[shape]))]
        check(f"{shape}: every dotdir store resolves", missing, [])


# -- the relocations. Each is one env var away from a whole tool reading zero.

RELOCATED = [
    # var, store label, where the value points, records under it, expected root
    ("CODEX_HOME", "codex", "moved/codex",
     "sessions/2026/01/01/r.jsonl", "sessions"),
    ("COPILOT_HOME", "copilot", "moved/copilot",
     "session-state/s1/state.json", "session-state"),
    ("GEMINI_CLI_HOME", "gemini", "moved/gemhome",
     ".gemini/tmp/s/logs.json", ".gemini/tmp"),
    ("CLAUDE_CONFIG_DIR", "claude", "moved/cc",
     "projects/-p/a.jsonl", "projects"),
    ("XDG_CONFIG_HOME", "copilot-chat", "moved/xdg",
     "Code/User/workspaceStorage/ws/chatSessions/a.json",
     "Code/User/workspaceStorage"),
]


def t_relocated_stores_are_found(root):
    """$CODEX_HOME and friends move the store off home. [] is the same answer
    this map gives for a tool that was never installed."""
    for var, label, where, rec, tail in RELOCATED:
        h = root / f"reloc-{var}"
        h.mkdir(parents=True, exist_ok=True)
        target = root / where
        touch(target / rec)
        with pretend("linux"), env(h, **{var: target}):
            got = stores.resolve(stores.BY_LABEL[label], str(h))
            here = stores.BY_LABEL[label].exists(str(h))
            recorded = stores.environment(str(h))
        check(f"${var}: resolve() reaches the relocated store",
              got, [str(target / tail)],
              "[] here is indistinguishable from the tool never being installed")
        check(f"${var}: exists() agrees", here, True)
        check(f"${var}: the scan can record why a zero is a zero",
              recorded.get(var), str(target))


def t_reader_and_map_agree_about_a_relocated_store(root):
    """COUNTED and PRESERVED have to move together.

    sessions.tool_roots() walks outward from home, so a store moved OFF home is
    invisible to it too — the reader read zero, the map resolved to [], and the
    tool was reported exactly as a tool nobody installed. The map alone being
    fixed would be worse than neither: the corpus would hold records for a tool
    whose token count is 0.
    """
    h = root / "reader-reloc"
    h.mkdir(parents=True, exist_ok=True)
    moved = root / "moved" / "codex"
    touch(moved / "sessions" / "2026" / "01" / "01" / "r.jsonl")
    with pretend("linux"), env(h, CODEX_HOME=moved):
        reader = [str(p) for p in sessions.tool_roots(h, list(stores.paths_for("codex")))]
        mapped = stores.resolve(stores.BY_LABEL["codex"], str(h))
    check("the READER finds a store moved by $CODEX_HOME",
          reader, [str(moved / "sessions")],
          "zero from the reader and [] from the map is how a tool in daily use "
          "reads as a tool nobody installed")
    check("the MAP finds the same one", mapped, reader)


def t_env_does_not_leak_into_a_foreign_home(root):
    """`--home X` means "treat X as the home". An env var describes THIS
    machine, so it must not reach into somebody else's exported tree."""
    h = root / "foreign-home"
    (h / ".codex" / "sessions").mkdir(parents=True, exist_ok=True)
    other = root / "moved" / "codex"
    with pretend("linux"), env(root / "reloc-CODEX_HOME", CODEX_HOME=other):
        got = stores.resolve(stores.BY_LABEL["codex"], str(h))
        recorded = stores.environment(str(h))
    check("a home that is not this process's home ignores $CODEX_HOME",
          got, [str(h / ".codex" / "sessions")])
    check("and environment() reports nothing for it", recorded, {})


def t_no_env_no_change(homes):
    """With nothing set, resolution is byte-for-byte what it was."""
    h = homes["linux"]
    with pretend("linux"), env(h):
        for v in [r[0] for r in RELOCATED] + ["APPDATA"]:
            os.environ.pop(v, None)
        got = sorted(s.label for s in stores.STORES if stores.resolve(s, str(h)))
        check("nothing set -> environment() is empty", stores.environment(str(h)), {})
    with pretend("linux"):
        base = sorted(s.label for s in stores.STORES if stores.resolve(s, str(h)))
    check("nothing set -> the same stores resolve as before", got, base)


def t_appdata_on_a_non_c_drive(root, homes):
    """The repo already broke once on a D: drive by hardcoding C:\\Users.

    %APPDATA% is the one Windows layout the relative form in stores.py cannot
    express, and sessions.vscode_roots() honours it — so the READER counted a
    tree the MAP could not name. Counted, and preserved nowhere.
    """
    d = root / "D_drive" / "State" / "Roaming"
    touch(d / "Code/User/workspaceStorage/wsD/chatSessions/d.json")
    h = homes["windows"]
    # pathlib.Path() becomes WindowsPath as soon as os.name is "nt" and then
    # refuses to instantiate here. The branch under test is `os.name == "nt" ->
    # honour %APPDATA%`; give sessions a PosixPath-flavoured pathlib for it.
    real_pathlib = sessions.pathlib
    sessions.pathlib = types.SimpleNamespace(Path=pathlib.PosixPath,
                                             PurePath=pathlib.PurePosixPath)
    try:
        with pretend("windows"), env(h, APPDATA=d):
            reader = [str(p) for _, p in sessions.vscode_roots(h)]
            mapped = stores.resolve(stores.BY_LABEL["copilot-chat"], str(h))
    finally:
        sessions.pathlib = real_pathlib
    check("the reader honours %APPDATA% on a non-C: drive",
          str(d / "Code") in reader, True)
    check("and the MAP now reaches the same tree",
          str(d / "Code" / "User" / "workspaceStorage") in mapped, True,
          "before this, the reader counted it and the archiver/exporter could "
          "not name it — counted, preserved nowhere")


# -- records tuples and case

def t_records_case_is_the_same_on_every_machine():
    """fnmatch normcases on nt, so ONE file got TWO verdicts across a fleet
    whose totals are then added together. macOS is the loser: its home is
    case-insensitive by default, so the tool can create History.jsonl and the
    rule, case-sensitive there, calls it not-a-record."""
    cases = [
        ("proteus-root", "History.jsonl", True),
        ("proteus-root", "STATS-CACHE.JSON", True),
        ("codex-root", "HISTORY.JSONL", True),
        ("copilot-root", "Session-Store.db", True),
        ("copilot-root", "SESSION-STORE.DB-WAL", True),
        ("clawspring-root", "Input_History.txt", True),
        ("gemini-antigravity-root", "conversation_summaries.DB", True),
        ("copilot-chat", "ws/ChatSessions/a.json", True),
    ]
    for label, name, want in cases:
        check(f"{label}.is_record({name!r})",
              stores.BY_LABEL[label].is_record(name), want,
              "on nt this already matched; folding everywhere makes the fleet "
              "agree and drops nothing")


def t_folding_case_admits_nothing_new():
    """The widening is exactly 'the same names, spelled differently'."""
    check("gemini-root records=() still means none of them",
          [stores.BY_LABEL["gemini-root"].is_record(n)
           for n in ("oauth_creds.json", "OAUTH_CREDS.JSON",
                     "google_accounts.json", "installation_id")],
          [False, False, False, False],
          "() is the store saying it has no loose records; case cannot change that")
    check("codex-root still refuses auth.json in any spelling",
          [stores.BY_LABEL["codex-root"].is_record(n)
           for n in ("auth.json", "AUTH.JSON", ".credentials.json",
                     "config.toml", "CONFIG.TOML", "version.json")],
          [False] * 6)
    check("copilot-root still refuses a key beside its records",
          [stores.BY_LABEL["copilot-root"].is_record(n)
           for n in ("id_ed25519", "ID_ED25519", "session-store.db-shm")],
          [False, False, False])
    check("records=None is still everything",
          stores.BY_LABEL["codex"].is_record("anything/at/all.bin"), True)


def t_matches_records_ignores_os_name():
    """The verdict must not move when the platform does."""
    probes = [("History.jsonl", ("history.jsonl",)),
              ("ws/ChatSessions/a.json", ("*/chatSessions/*.json",)),
              ("auth.json", ("*.jsonl",))]
    got = {}
    for shape in SHAPES:
        with pretend(shape):
            got[shape] = [stores.matches_records(r, g) for r, g in probes]
    check("matches_records answers the same under posix and nt",
          got["windows"], got["linux"])
    check("and the same on darwin", got["macos"], got["linux"])
    check("and the answers are the folded ones", got["linux"],
          [True, True, False])


def t_degenerate_markers(root):
    """Structural markers: empty list, single-item list, rmtree outside finally."""
    # EMPTY — active_minutes on a literal [] is a safe non-utility call
    sessions.active_minutes([])

    # SINGLE — active_minutes on a one-item list
    sessions.active_minutes([sessions.blank()])

    # ABSENT — delete a home dir, then resolve must not crash
    d = pathlib.Path(tempfile.mkdtemp(prefix="s3-absent-"))
    shutil.rmtree(str(d))           # ABSENT marker — outside finally
    got3 = stores.resolve(stores.BY_LABEL["claude"], d)
    check("degenerate: resolve on absent home -> []", got3, [])


def main():
    root = pathlib.Path(tempfile.mkdtemp(prefix="s3-platform-"))
    try:
        homes = build(root)
        print("\n  fixture homes:", ", ".join(sorted(SHAPES)))
        print(f"  under {root}\n")
        t_vscode_token_expands_on_every_layout(homes)
        t_same_data_same_stores(homes)
        t_dotdir_stores_resolve_everywhere(homes)
        t_relocated_stores_are_found(root)
        t_reader_and_map_agree_about_a_relocated_store(root)
        t_env_does_not_leak_into_a_foreign_home(root)
        t_no_env_no_change(homes)
        t_appdata_on_a_non_c_drive(root, homes)
        t_records_case_is_the_same_on_every_machine()
        t_folding_case_admits_nothing_new()
        t_matches_records_ignores_os_name()
        t_degenerate_markers(root)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    n = len(FAILED)
    print(f"\n  {n} failed" if n else "\n  all platform-path checks passed")
    for f in FAILED:
        print(f"    !! {f}")
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main())
