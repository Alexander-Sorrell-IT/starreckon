#!/usr/bin/env python3
"""Where every AI CLI keeps its conversations. One definition, imported by everything.

    python3 stores.py            what is on this machine, and who claims it

Same role `paths.py` plays for generated files, for a different fact. This one
answers: given a tool, where does it write the record of what you said to it.

WHY THIS FILE EXISTS

That fact was written down THREE times, in three files, by three authors of the
same codebase:

    sessions.py         DETECT              8 tools    the counter
    retention_guard.py  OTHER_SOURCES       31 tools   the archiver
                      + ROOT_FILE_SOURCES    9
    sweep_usage.py      COVERED             15 paths   the sweep

Six of them overlapped with byte-identical paths — `.codex/sessions`,
`.copilot/session-state`, `.gemini/tmp`, `.grok/sessions`,
`.lmstudio/conversations`, and the kilocode globalStorage path — each written
out twice. This repository has already shipped one defect four times over
exactly this shape, and every one of those three lists was a place a fix could
land without landing in the others.

WHAT THE THREE FIELDS MEAN, AND WHY THEY ARE SEPARATE

  path         where the records are
  cli          which reader in sessions.py counts them, or None
  kind         "conversations" (a directory of records) or
               "root_files"    (loose records beside a tool's program dirs)
  records      glob, relative to path, matching the files that ARE the records.
               Default None = the whole tree is records.

`records` exists because one store's path is far wider than its records.
copilot-chat's path has to be `workspaceStorage` — that is the directory its
reader iterates — but 4.5 GB of that is other extensions' state and only the
`*/chatSessions/*.json` inside it is anybody's conversation. Without this the
archiver either preserves nothing (the store is not listed) or preserves 2 GB
of unrelated cache to get 2.25 GB of chat. The reader's base and the records'
shape are two different facts about one store, so they are two fields.

`preserve=False` marks a store that is COUNTED and must never be COPIED.

Until this existed, being in the map at all meant being exported, and
`.claude.json` reached corpus/tools/claude-config/ carrying oauthAccount,
organizationUuid, userID and machineID. `export_corpus.NEVER_EXPORT` is meant
to stop exactly that and could not: it matches file NAMES like `config`,
`credentials`, `auth`, and `.claude.json` is none of them.

Patching that regex would have been the wrong fix. The file is not a record
that happens to be sensitive — it is not a record at all. It holds Claude
Code's own per-session counters, which is why `read_claude_orphans` reads it
and recovered 4,071,258,650 tokens whose transcripts are gone. There is
nothing to preserve even in principle: the counter IS the surviving evidence,
and it is already captured in sessions.json and the ledger. Counted, never
copied — two properties of one store, so two fields.

Keeping `cli` explicit is what makes two different failures visible instead of
invisible. A store with `cli=None` is preserved but never counted. A reader with
no store is counted but never preserved — which is how the corpus ended up
holding Claude and nothing else while every report said eight tools. Neither of
those is discoverable from a list of paths alone.

kind="root_files" is NOT recursive, and that is the whole point of it: proteus
keeps history.jsonl loose in ~/.proteus beside its program directories, so the
records are taken and the directories are not.

THE PATHS BELOW WERE COLLECTED, AND COLLECTING IS NOT KNOWING

Every one of the forty-odd paths in this map was read off ONE Linux machine.
That is why the file had exactly four macOS-specific branches — all of them the
`{vscode}` token — and not one line about Windows, while machines.json lists
`dell-latitude-7480-windows` and deadreckon-record holds no folder for it. A
Windows box running this code would scan its home for `~/.codex/sessions`,
find that and nothing else, and report every VS Code-family tool as absent.

A tool keeps its data in ITS OWN FOLDER, and that folder has a KNOWN FORM per
platform. So the location is DERIVED from the tool's name — see `tool_forms()`
— and the collected path is kept only as the canonical spelling and as the
first candidate. `IRREGULAR` names every store the derivation cannot reach, so
the exceptions are one short countable list instead of being the whole design.

INSTALLED, ABSENT, UNREADABLE — THREE ANSWERS, BECAUSE TWO ARE A KNOWN LIE

`os.path.exists` returns False when the parent cannot be entered and `glob`
returns [] for a directory it cannot list. Both are byte-identical to "there is
nothing there", and 22 of the stores below reported exactly that way under
`chmod 000`. It is not hypothetical on the fleet: macOS returns EPERM rather
than not-found when TCC denies a background process access to Desktop or
Documents, and the MacBook publishes scans from a launchd agent.

`state()` answers with one of installed / absent / unreadable AND KEEPS THE
ERRNO. `resolve()` is unchanged and still answers only the first question, so
every existing caller keeps the behaviour it was written against.
"""

import errno
import fnmatch
import os
import stat
import sys

import platform_detect

HOME = os.path.expanduser("~")

# WHERE THE VS CODE FAMILY KEEPS USER DATA, per platform. ONE definition.
#
# Eight stores wrote `.config/Code/...` as a literal, and sessions.py wrote the
# platform branch separately in vscode_roots(). On macOS the two disagreed by
# construction, in opposite directions, and both failures were silent:
#
#   kilocode      the READER branches on darwin and found 1,050 tokens; the
#                 store resolved to [] — counted, and preserved nowhere.
#   copilot-chat  its reader's @multi_base rels were literals too, so it was a
#                 zero on BOTH sides — the shape that looks like a tool nobody
#                 uses.
#
# `{vscode}` in a store path expands to each of these. resolve() does it, so
# every caller that goes through resolve() is correct everywhere, and
# sessions.vscode_roots() reads this list rather than keeping a second copy.
#
# IT IS ALSO THE MIDDLE RUNG OF THE GENERAL MODEL BELOW, which is why it is a
# table rather than a branch now: the VS Code family is not a special case, it
# is this table with the EDITOR as the tool.
#
# `.config` stays in the list on macOS and Windows deliberately: Electron's
# appData honours XDG_CONFIG_HOME on Linux only, but a CLI installed by npm or
# brew writes the POSIX form on every platform it runs on, and a candidate that
# does not exist costs one stat.
CONFIG_BASE = {
    "linux":   (".config",),
    "macos":   ("Library/Application Support", ".config"),
    # Relative to home, which is where APPDATA points on any normal install.
    # sessions.vscode_roots() honours %APPDATA% itself for the case where it
    # does not, and RELOCATIONS carries the same fact for this map.
    "windows": ("AppData/Roaming", ".config"),
}


def family():
    """linux | macos | windows — which FOLDER LAYOUT this machine uses.

    Read through this module's own `sys` and `os` on purpose. `platform_as()`
    and `test_platform_paths.pretend()` fake a platform by rebinding
    `stores.sys` / `stores.os`, and the real branch has to run under them —
    fleet_fixture already documents what happens when a test patches the
    function under test instead: eleven planted defects, ten caught, and the
    one the macOS half of the fleet exists for went green.

    The mapping itself lives in platform_detect, which is the file whose whole
    job is "what machine is this". It is a pure function of the two values, so
    asking it here is not the same as asking it about THIS process.
    """
    return platform_detect.family(sys.platform, os.name)


def vscode_bases():
    """Parent directories of the VS Code channels, most specific first."""
    return list(CONFIG_BASE.get(family(), CONFIG_BASE["linux"]))


VSCODE = "{vscode}"


# ---------------------------------------------------------------------------
# THE DERIVED MODEL. A tool's folder, from the tool's name, per platform.
# ---------------------------------------------------------------------------

def tool_forms(fam=None):
    """Every home-relative form a tool's own data folder can take here.

    `{tool}` is the folder name — `codex`, `gemini`, `Code`. Ordered with the
    hidden dotdir FIRST on every platform, so that for a regular store the
    first candidate is byte-for-byte the path that was collected off this
    machine: the derivation reproduces what was already there and then adds to
    it, which is what makes it safe to hand every existing caller.

        Linux     ~/.<tool>, ~/.config/<tool>, ~/.local/share/<tool>
        macOS     the Linux forms — npm and brew CLIs use ~/.<tool> there and
                  gemini-cli, codex and claude all document exactly that —
                  plus ~/Library/Application Support/<tool>,
                  ~/Library/Caches/<tool>, and the sandbox container form.
        Windows   %USERPROFILE%\\.<tool>, %APPDATA%\\<tool>,
                  %LOCALAPPDATA%\\<tool>

    XDG_CONFIG_HOME, XDG_DATA_HOME, APPDATA and LOCALAPPDATA move three of
    these off home entirely; RELOCATIONS carries that and `relocations()`
    applies it to every form here, so a base directory the operator moved is
    not a fifth kind of answer.

    THE CONTAINER FORM IS A GLOB, NOT A TABLE. macOS puts a sandboxed app's
    data under ~/Library/Containers/<bundle id>/Data/…, and a table of bundle
    ids is a table of guesses — no bundle id for any tool in this map has been
    observed from here, and a WRONG id looks exactly like a tool that is not
    installed. `*` finds the container whatever it is called, costs one listing
    of a directory that only exists on macOS, and cannot be wrong about a name
    it never has to know.
    """
    fam = fam or family()
    forms = [".{tool}"]
    forms += [b + "/{tool}" for b in CONFIG_BASE.get(fam, CONFIG_BASE["linux"])]
    if fam == "windows":
        forms.append("AppData/Local/{tool}")
    else:
        forms.append(".local/share/{tool}")
    if fam == "macos":
        forms.append("Library/Caches/{tool}")
        forms.append("Library/Containers/*/Data/Library/Application Support/{tool}")
    return tuple(forms)


# The base directories a form can start with, longest first so that
# `.local/share` is recognised before `.local` would be. Used only to read a
# COLLECTED path back into (tool, subpath): `.config/goose/sessions` was
# written in the config form already, and splitting it as tool=".config" would
# derive `~/..config/goose/sessions` and nothing useful.
_BASES = tuple(sorted(
    {b for bs in CONFIG_BASE.values() for b in bs}
    | {".local/share", "AppData/Local", "Library/Caches",
       "Library/Application Support"},
    key=len, reverse=True))


def split_tool(rel):
    """(tool folder, subpath under it) for a collected store path, or None.

    None means the path is not of the regular shape and cannot be derived —
    `IRREGULAR` has to name it and say why.
    """
    for b in _BASES:
        if rel.startswith(b + "/"):
            parts = rel[len(b) + 1:].split("/")
            return parts[0], "/".join(parts[1:])
    parts = rel.split("/")
    head = parts[0]
    if not head.startswith(".") or len(head) < 2:
        return None
    if len(parts) == 1 and "." in head[1:]:
        # `.claude.json` — a FILE sitting in the home directory. There is no
        # ~/.claude.json/ folder to place under a base directory.
        return None
    return head[1:], "/".join(parts[1:])


# EVERY STORE THE DERIVATION CANNOT REACH, WITH THE REASON. Visible and
# countable: `irregular_stores()` recomputes this set from the map, and
# adv_store_locations asserts the two agree, so an exception cannot be added by
# accident and cannot be removed without being noticed.
IRREGULAR = {
    "claude-config":
        "~/.claude.json is a FILE BESIDE the folder, not inside it, so there "
        "is no ~/.claude-config/ for a base directory to hold. When "
        "CLAUDE_CONFIG_DIR moves the folder the file moves with it, and that "
        "copy is `.claude*/.claude.json` — claude-config-profiles, which IS "
        "derived.",
}


def irregular_stores():
    """Labels the derivation cannot reach, computed from the map itself."""
    out = []
    for s in STORES:
        if not any(split_tool(rel) for rel in s.rel_paths()):
            out.append(s.label)
    return sorted(out)


def candidates(store):
    """Every home-relative path this store's records could be at, here.

    A SUPERSET of `rel_paths()`, and the two are deliberately different
    questions. `rel_paths()` is the CANONICAL spelling — documented defaults,
    observed on disk — and it is what the archiver's source map, the sweep's
    covered list and the readers' bases are built from, where claiming a path
    means claiming something about it. This is the RESOLVER's question: where
    could it be, so that a machine nobody here has ever logged into is not told
    "not installed" because its operating system files things somewhere else.
    """
    out = []
    for rel in store.rel_paths():
        out.append(rel)
        d = split_tool(rel)
        if not d:
            continue
        tool, sub = d
        for form in tool_forms():
            p = form.format(tool=tool)
            out.append(p + "/" + sub if sub else p)
    seen, uniq = set(), []
    for p in out:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq


# EVERY PATH IN THIS MAP IS HOME-RELATIVE, AND FIVE OF THESE TOOLS LET THE
# OPERATOR MOVE THEIR STORE OFF HOME ENTIRELY. Measured on synthetic homes
# (probe: fixture with the records really on disk, one env var set):
#
#     CODEX_HOME=<dir>        resolve() -> []   exists() -> False
#     GEMINI_CLI_HOME=<dir>   resolve() -> []   exists() -> False
#     COPILOT_HOME=<dir>      resolve() -> []   exists() -> False
#     CLAUDE_CONFIG_DIR=<dir> resolve() -> []   exists() -> False
#     XDG_CONFIG_HOME=<dir>   resolve() -> []   exists() -> False
#
# [] is the SAME ANSWER this map gives for a tool that was never installed, so
# the archiver prints "absent", the exporter writes no tools/<label>/, and every
# report reads zero. That is this repository's most-repeated defect — absent
# looking exactly like zero — sitting under four of the eight CLIs it counts.
#
# WHAT EACH VARIABLE ACTUALLY REPLACES, which is not the same for all of them:
#
#   CODEX_HOME        the whole ~/.codex directory. "Codex stores its local
#                     state under CODEX_HOME (defaults to ~/.codex)."
#                     developers.openai.com/codex/config-advanced
#   COPILOT_HOME      the whole ~/.copilot directory. "To override the default
#                     ~/.copilot location, set the COPILOT_HOME environment
#                     variable to the path of the directory you want to use."
#                     docs.github.com/en/copilot/reference/copilot-cli-reference
#                     /cli-config-dir-reference
#   CLAUDE_CONFIG_DIR the whole ~/.claude directory. os.pathsep-separated, the
#                     same parse retention_guard.find_profiles already does.
#   GEMINI_CLI_HOME   THE HOME, NOT THE DOTDIR. gemini-cli's storage.ts calls
#                     homedir() and appends .gemini/, and homedir() is the one
#                     GEMINI_CLI_HOME overrides — so the store lands at
#                     $GEMINI_CLI_HOME/.gemini, one level deeper than the other
#                     three. google-gemini/gemini-cli issue #23622.
#   XDG_CONFIG_HOME   ~/.config, which is where the VS Code family and goose
#                     live on Linux (Electron's appData honours it).
#   XDG_DATA_HOME     ~/.local/share, the third Linux form. Set by nix, by
#                     home-manager and by anyone who moves ~/.local off a small
#                     root partition, and it takes the whole directory with it.
#   APPDATA           AppData/Roaming, and ONLY on Windows — CONFIG_BASE emits
#                     that prefix nowhere else, so this entry is inert on every
#                     other platform without needing a branch.
#   LOCALAPPDATA      AppData/Local, the same fact for the non-roaming half.
#                     Redirected by policy on managed Windows machines, which
#                     is exactly the kind of box a work laptop is.
#
# The four base-directory variables are here BECAUSE OF THE DERIVED MODEL: it
# puts real candidates under `.config`, `.local/share`, `AppData/Roaming` and
# `AppData/Local`, and a candidate whose base has been moved out from under it
# resolves to [] — the answer this map also gives for a tool nobody installed.
#
# The prefix is matched COMPONENT BY COMPONENT with fnmatch, so `.claude*` in
# the profile-glob store is matched by the literal `.claude` here and the rest
# of the path is re-applied under the new root.
RELOCATIONS = (
    # (env var, prefix it replaces, sub-path the value still needs)
    ("CLAUDE_CONFIG_DIR", ".claude", ""),
    ("CODEX_HOME", ".codex", ""),
    ("COPILOT_HOME", ".copilot", ""),
    ("GEMINI_CLI_HOME", ".gemini", ".gemini"),
    ("XDG_CONFIG_HOME", ".config", ""),
    ("XDG_DATA_HOME", ".local/share", ""),
    ("APPDATA", "AppData/Roaming", ""),
    ("LOCALAPPDATA", "AppData/Local", ""),
)


def _env_applies(home):
    """Is `home` the home this process is actually running in?

    analyze_tokens.find_config_dirs already draws this line and says why:
    `--home X` means "treat X as the home", and letting the environment override
    that made the flag a no-op — a scan of a temp directory still returned this
    machine's live profiles. An env var describes THIS machine's layout, so it
    applies to THIS machine's home and to no other.
    """
    try:
        return os.path.realpath(home) == os.path.realpath(os.path.expanduser("~"))
    except OSError:
        return False


def relocations(rel, home=None):
    """Extra absolute roots this home-relative store path may have been moved to.

    Empty when nothing is set, which is the case on every machine measured so
    far — so this adds paths and removes none.
    """
    home = home or HOME
    if not _env_applies(home):
        return []
    rc = rel.split("/")
    out = []
    for var, prefix, under in RELOCATIONS:
        raw = os.environ.get(var)
        if not raw:
            continue
        pc = prefix.split("/")
        if len(rc) < len(pc):
            continue
        # prefix component (literal) tested against store component (pattern):
        # `.claude` matches the store's `.claude*`.
        if not all(fnmatch.fnmatch(a, b) for a, b in zip(pc, rc)):
            continue
        for part in raw.split(os.pathsep):
            part = part.strip()
            if not part:
                continue
            base = os.path.expanduser(part)
            if under:
                base = os.path.join(base, *under.split("/"))
            tail = rc[len(pc):]
            out.append(os.path.join(base, *tail) if tail else base)
    return out


def environment(home=None):
    """{var: value} for every relocation variable set on this machine.

    RECORDED, so that a zero can be read. Without it a store that resolved to
    nothing because the operator moved it is written down identically to a store
    that resolved to nothing because the tool was never installed, and no report
    downstream can tell the two apart — not from the totals, not from the
    corpus, not from the archive. With it, the scan carries the one fact that
    separates them.
    """
    home = home or HOME
    if not _env_applies(home):
        return {}
    return {var: os.environ[var] for var, _, _ in RELOCATIONS
            if os.environ.get(var)}


def matches_records(rel, records):
    """Is this path, relative to a store root, one of the records `records` names?

    ONE RULE, TWO CALLERS. `Store.is_record` is this function, and so is the
    archiver's allow-list in retention_guard.link_tree. It is a module function
    rather than a method because the archiver holds the TUPLE, not the Store —
    and a second fnmatch loop written over there is exactly the shape this file
    was created to end.

    `records is None` and `records == ()` ARE NOT THE SAME SENTENCE, and this is
    the line where they stopped being. `if not self.records: return True` made
    them identical, so

        Store('gemini-root', '.gemini', kind='root_files', records=())
            .is_record('oauth_creds.json')   ->   True

    and writing `records=()` to mean "this store has no loose records" was
    byte-for-byte the same as writing nothing at all. None = the store has not
    said, so keep everything. () = the store said none of them.

    CASE IS FOLDED, ON EVERY PLATFORM, AND THAT IS A FLEET DECISION.
    `fnmatch.fnmatch` runs both sides through `os.path.normcase`, which is
    identity on posix and lowercasing on nt — so the SAME file gave two answers
    on two machines whose totals this repository then adds together. Measured:
    seven tuples changed verdict on a differently-cased name —

        gemini-antigravity-root  History.jsonl, HISTORY.JSONL,
                                 conversation_summaries.DB
        proteus-root             History.jsonl, HISTORY.JSONL, STATS-CACHE.JSON
        codex-root               HISTORY.JSONL
        copilot-root             Session-Store.db
        clawspring-root          Input_History.txt
        copilot-chat(-insiders)  ws/ChatSessions/a.json

    macOS is the machine that loses by it: its home is case-INSENSITIVE by
    default, so the tool can create `History.jsonl` and the FILE EXISTS while
    the rule, being case-sensitive there, calls it not-a-record — archived
    nowhere, exported nowhere, reported as absent. Windows already folded and
    kept it. Folding everywhere makes the fleet agree and drops nothing: the
    other direction (`fnmatchcase`) would have made Windows stricter and started
    dropping records that machine keeps today.

    Permissive is the safe direction here for the reason the copilot-chat store
    already documents: export_corpus picks the files with `root.glob(g)` and
    only re-checks them with this function, so widening it cannot pull in a file
    pathlib did not already offer. retention_guard.link_tree holds no second
    filter, and there this widens the allow-list by exactly the differently-
    cased spellings of names already on it.

    `os.sep` is replaced first and `fnmatchcase` is used rather than `fnmatch`
    so the separator survives: `ntpath.normcase` rewrites "/" to "\\" as well as
    lowercasing, which happened to work only because it rewrote pattern and path
    alike.
    """
    if records is None:
        return True
    rel = str(rel).replace(os.sep, "/").lower()
    return any(fnmatch.fnmatchcase(rel, g.lower()) for g in records)


class Store:
    __slots__ = ("label", "path", "cli", "kind", "note", "records", "preserve",
                 "no_preserve_because")

    def __init__(self, label, path, cli=None, kind="conversations", note="",
                 records=None, preserve=True, no_preserve_because=""):
        self.label, self.path, self.cli = label, path, cli
        self.kind, self.note, self.records = kind, note, records
        self.preserve, self.no_preserve_because = preserve, no_preserve_because

    def rel_paths(self):
        """Every platform-expanded path for this store, relative to home.

        For callers that need the RELATIVE form rather than a resolved absolute
        one — retention_guard's source map, sweep_usage's covered list, and
        count_corpus working out a reader's base inside the corpus. Those three
        read `store.path` directly, so a `{vscode}` token would have reached
        them unexpanded and matched nothing.
        """
        if VSCODE not in self.path:
            return [self.path]
        return [self.path.replace(VSCODE, b) for b in vscode_bases()]

    def is_record(self, rel):
        """Is this path, relative to the store root, one of the store's records?"""
        return matches_records(rel, self.records)

    def abspath(self, home=None):
        """First platform-expanded absolute path. See rel_paths() for all of them."""
        return os.path.join(home or HOME, *self.rel_paths()[0].split("/"))

    def candidates(self):
        """Every home-relative form this store could take here. See candidates()."""
        return candidates(self)

    def exists(self, home=None):
        # Every candidate, not just the first: on macOS a VS Code store can
        # live under Library/Application Support OR under .config, and asking
        # about one of them answers a narrower question than the caller meant.
        #
        # STILL TWO-VALUED, and still the narrow question. A store that exists
        # and cannot be entered answers False here, exactly as it did before —
        # `state()` is the one that can say so, and every caller of this was
        # written against the two-valued answer.
        return bool(_lookup(self, home or HOME)[0])

    def state(self, home=None):
        """installed | absent | unreadable, with the errno. See state()."""
        return state(self, home)

    def __repr__(self):
        return f"<Store {self.label} {self.path}>"


# ---------------------------------------------------------------------------
# LOOKING, AND BEING ABLE TO SAY THAT LOOKING FAILED.
# ---------------------------------------------------------------------------

# errnos that mean the thing is genuinely not there. Everything else that
# os.stat or os.listdir can raise means SOMETHING IS IN THE WAY, and the
# difference is the whole point of this section.
_MISSING = frozenset((errno.ENOENT, errno.ENOTDIR, errno.ENAMETOOLONG))

INSTALLED, ABSENT, UNREADABLE = "installed", "absent", "unreadable"


def _wild(part):
    return any(c in part for c in "*?[")


def _stat_errno(p):
    """None when `p` is there, else the errno saying why the answer is no."""
    try:
        os.stat(p)
        return None
    except OSError as e:
        return e.errno or errno.ENOENT


def _expand(pattern):
    """(paths that are there, [(path, errno)] for what could not be looked at).

    THE REPLACEMENT FOR `glob.glob(p) if "*" in p else os.path.exists(p)`, and
    it exists because both halves of that answer the same "no" to two different
    questions:

        os.path.exists  catches OSError and returns False, so a store whose
                        PARENT is chmod 000 is reported not-there.
        glob.glob       has an onerror hook nowhere; it swallows the OSError
                        from listing a directory it cannot enter and yields
                        nothing.

    Component by component, so `*` cannot cross "/" — the same rule glob has,
    and the same rule the `records` tuples are written against. glob's hidden
    rule is kept too (a `*` component does not match a name starting with ".")
    so that the paths this returns are the paths glob returned, exactly, and
    the ERRORS are the only thing that is new.
    """
    pat = str(pattern).replace(os.sep, "/") if os.sep != "/" else str(pattern)
    parts = pat.split("/")
    lead = []
    while parts and not _wild(parts[0]):
        lead.append(parts.pop(0))
    cur = ["/".join(lead) or "/"]
    blocked = []
    for part in parts:
        nxt = []
        for d in cur:
            if not _wild(part):
                nxt.append(os.path.join(d, part))
                continue
            try:
                names = os.listdir(d)
            except OSError as e:
                # NORMALISED, because `e.errno` is None for a handful of OSError
                # subclasses and a None in this list makes `sorted()` raise on
                # the comparison — a report that cannot be printed is a report
                # that says nothing, which is the failure mode of the whole file.
                code = e.errno or errno.EACCES
                if code not in _MISSING:
                    blocked.append((d, code))
                continue
            if not part.startswith("."):
                names = [n for n in names if not n.startswith(".")]
            nxt.extend(os.path.join(d, n)
                       for n in sorted(fnmatch.filter(names, part)))
        cur = nxt
    out = []
    for p in cur:
        e = _stat_errno(p)
        if e is None:
            out.append(p)
        elif e not in _MISSING:
            blocked.append((p, e))
    return out, blocked


def _lookup(store, home):
    """(every path that is there, [(path, errno)] for every one in the way)."""
    found, blocked = [], []
    for rel in candidates(store):
        for p in [os.path.join(home, *rel.split("/"))] + relocations(rel, home):
            hits, errs = _expand(p)
            found.extend(hits)
            blocked.extend(errs)
    return sorted(set(found)), blocked


def _readable(p):
    """None when the records can actually be read, else the errno saying no.

    STAT IS NOT ENOUGH, and macOS is the reason. TCC denies a background
    process access to Desktop, Documents and Downloads by returning EPERM from
    the OPEN, not from the stat — the directory is there, its metadata reads
    fine, and every walk of it yields nothing. On the MacBook that agent is
    launchd, so the published scan can be a row of zeros for folders that are
    full. The probe is the cheapest real one: one entry of a directory, zero
    bytes of a file.
    """
    try:
        st = os.stat(p)
    except OSError as e:
        return e.errno or errno.ENOENT
    try:
        if stat.S_ISDIR(st.st_mode):
            with os.scandir(p) as it:
                next(it, None)
        elif stat.S_ISREG(st.st_mode):
            with open(p, "rb"):
                pass
    except OSError as e:
        return e.errno or errno.EACCES
    return None


def state(store, home=None):
    """One store's THIRD STATE: installed, absent or unreadable, with the errno.

        {"state": "unreadable",
         "paths": [],
         "blocked": [["/home/me/.codex/sessions", 13, "EACCES"]]}

    `paths` holds only what can actually be read, so `installed` means the
    records are reachable and not merely present. Anything that is there and
    cannot be opened, and anything whose parent could not be entered, lands in
    `blocked` WITH ITS ERRNO — which is the fact that separates "this tool was
    never installed" from "this process is not allowed to look".

    A store can be BOTH: one profile readable and another not. It reports
    installed, and `blocked` still names the one nobody can see, because the
    total that gets published is short by whatever is in there.
    """
    home = home or HOME
    found, blocked = _lookup(store, home)
    readable = []
    for p in found:
        e = _readable(p)
        if e is None:
            readable.append(p)
        else:
            blocked.append((p, e))
    if readable:
        st = INSTALLED
    elif blocked:
        st = UNREADABLE
    else:
        st = ABSENT
    return {
        "state": st,
        "paths": readable,
        "blocked": [[p, e, errno.errorcode.get(e, str(e))]
                    for p, e in sorted(set(blocked))],
    }


def scan(home=None):
    """{label: state(...)} for every store. The map's whole answer about a home.

    Two runs of this over the same tree must not agree when one of them could
    not read something — that inequality is what adv_store_locations asserts,
    and it is not satisfiable by printing a constant.
    """
    home = home or HOME
    return {s.label: state(s, home) for s in STORES}


def counts(scanned):
    """{state: n} over a scan(). What a machine's report should be leading with."""
    out = {INSTALLED: 0, ABSENT: 0, UNREADABLE: 0}
    for v in scanned.values():
        out[v["state"]] = out.get(v["state"], 0) + 1
    return out


# ---------------------------------------------------------------------------
# Every store. `cli` names the reader in sessions.READERS that counts it.
# ---------------------------------------------------------------------------
STORES = [
    # -- Claude. The only CLI that DELETES on a timer, which is why the profile
    #    glob matters: this machine has five profile directories and a hardcoded
    #    ~/.claude missed 818,673,995 tokens living in the others.
    # `.claude*` ANCHORS ON THE FIRST CHARACTER AND $CLAUDE_CONFIG_DIR DOES NOT.
    # ~/.my-claude/projects is 136,918,123 B across 228 files and matched none
    # of the four hits `.claude*/projects` returns on this machine — it survives
    # only as archive residue, because retention_guard finds profiles through
    # analyze_tokens.find_config_dirs (which is shape-based) rather than through
    # this store. Everything that reads the MAP — the exporter, sweep_usage's
    # covered list, detect() — was blind to it. `.*claude*` still requires the
    # leading dot, so ~/claude-code-wiki is not newly claimed.
    Store("claude", ".*claude*/projects", cli="claude",
          note="cleanupPeriodDays deletes these at startup"),

    # THE FROZEN LIFETIME COUNTER, FOR THE ACTUAL .claude PROFILES.
    #
    # stats-cache.json accumulates modelUsage per profile from its first
    # session and is never cleared by cleanupPeriodDays — it is the only
    # record of billed tokens whose transcript has already been deleted (see
    # CLAUDE_PROFILE_RECORDS in retention_guard.py, which already protects it
    # from deletion). Before this store existed, nothing shipped it into the
    # corpus: the "claude" store above only walks projects/, and stats-cache
    # sits at the profile ROOT, one level up. "proteus-root" named it in a
    # records tuple for the Claude Code fork, but the real, ordinary .claude
    # profile — the common case — had no store at all, so export_corpus.py
    # never had a chance to ship the file that machine_floor() and every
    # lifetime total in this repo depend on.
    Store("claude-root", ".*claude*", kind="root_files", cli="claude",
          note="stats-cache.json is the frozen lifetime counter; "
               "history.jsonl is the only surviving record of sessions "
               "whose transcript cleanupPeriodDays already deleted",
          records=("history.jsonl", "stats-cache.json")),

    # -- THE ONLY SURVIVING RECORD of sessions Claude has already deleted.
    #
    # .claude.json keeps per-project counters — lastTotal{Input,Output,
    # CacheRead,CacheCreation}Tokens keyed on lastSessionId — and does NOT clear
    # them when cleanupPeriodDays sweeps the transcript. On this machine that is
    # 4,062,282,405 tokens across 69 sessions with no transcript left, which
    # nothing counted and nothing backed up.
    #
    # It is registered as a store for two reasons and both matter: so the
    # archiver preserves it (a config file everyone treats as disposable is the
    # last copy of half this machine's history), and so `detect` can tell
    # "claude was never installed" from "the reader found nothing".
    Store("claude-config", ".claude.json", cli="claude-orphans",
          note="per-project counters for sessions whose transcript is gone",
          preserve=False,
          no_preserve_because="config, not a record — holds oauthAccount, "
                              "userID and machineID; the counters it carries "
                              "are the surviving evidence and are already in "
                              "sessions.json and the ledger"),
    Store("claude-config-profiles", ".claude*/.claude.json", cli="claude-orphans",
          preserve=False,
          no_preserve_because="same file, one per profile"),

    # -- counted and preserved
    Store("gemini", ".gemini/tmp", cli="gemini"),
    Store("gemini-antigravity", ".gemini/antigravity-cli/conversations",
          cli="antigravity"),
    Store("copilot", ".copilot/session-state", cli="copilot"),
    Store("codex", ".codex/sessions", cli="codex"),
    # ARCHIVING A THREAD MOVES IT OUT OF EVERY COVERED PATH. codex's
    # archive_thread.rs does archive_folder.join(&file_name) — FLAT, with none
    # of the YYYY/MM/DD structure sessions/ has — so a rollout leaves
    # ~/.codex/sessions/... and lands in ~/.codex/archived_sessions/<name>.jsonl,
    # which Store("codex") does not reach and Store("codex-root") does not
    # either, being kind="root_files" and therefore never recursed.
    #
    # grok already has exactly this pair (grok/grok-archived) for exactly this
    # reason; codex was the half that never got written. And codex is the worse
    # case of the two: it keeps NO lifetime counter, so a rollout that moves
    # while uncovered leaves no number behind to notice it by.
    #
    # NOT PRESENT ON THIS MACHINE, and that is the expected state — the
    # directory is created on the first archive. A store that is not there yet
    # and a store the belt used to catch are told apart by link_tree's
    # _archive_holds/VANISHED branch, which this reaches because
    # OTHER_SOURCES is built from every conversation store.
    #
    # cli=None, AND IT IS A STATEMENT. grok-archived can say cli="grok" because
    # read_grok is @multi_base(".grok/sessions", ".grok/archived_sessions").
    # read_codex is @multi_base(".codex/sessions") and nothing else, so claiming
    # cli="codex" here would put this path in covered_paths() — sweep_usage
    # would report it as already COUNTED by a reader that never opens it, which
    # is the precise blindness that function's docstring exists to refuse.
    # Preserved and counted are different questions; this store answers only the
    # first, and uncounted_stores() is where it will show up saying so.
    Store("codex-archived", ".codex/archived_sessions",
          note="archive_thread.rs moves rollouts here, flat, out of sessions/"),
    Store("lmstudio", ".lmstudio/conversations", cli="lmstudio",
          note="NOT all of .lmstudio — 108 GB of model weights live there"),
    Store("grok", ".grok/sessions", cli="grok"),
    Store("grok-archived", ".grok/archived_sessions", cli="grok"),
    Store("kilocode", "{vscode}/Code/User/globalStorage/kilocode.kilo-code/tasks",
          cli="kilocode"),
    Store("kilocode-insiders",
          "{vscode}/Code - Insiders/User/globalStorage/kilocode.kilo-code/tasks",
          cli="kilocode"),

    # -- antigravity keeps three more stores beside conversations/, and none of
    #    them were claimed by any rule until asked for directly. Depth is the
    #    reason: a pass that lists ~/.* and stops sees .gemini as handled the
    #    moment .gemini/tmp is claimed.
    Store("gemini-antigravity-brain", ".gemini/antigravity-cli/brain",
          note="3.6 MB across 64 files — the model's own notes"),
    Store("gemini-antigravity-cache", ".gemini/antigravity-cli/cache",
          note="last_conversations.json, conversation_metadata.json"),
    Store("gemini-antigravity-root", ".gemini/antigravity-cli",
          kind="root_files", note="history.jsonl, 40 lines",
          records=("history.jsonl", "conversation_summaries.db")),

    # -- preserved, counted by nobody. cli=None is a statement, not an omission:
    #    these hold real records that no reader in sessions.py can read, so they
    #    appear in the corpus and in no total.
    Store("clawspring", ".clawspring/sessions", cli="clawspring",
          note="258,502,806 tokens; read daily/ only — history.json is a rollup"),

    # GitHub Copilot Chat in VS Code — a DIFFERENT product from ~/.copilot, and
    # 2.29 GB across 76 files that was in NO store: not counted, not archived,
    # not in the corpus. NO_TOKENS_BECAUSE called VS Code "an editor — hosts
    # agents, spends no tokens itself"; it holds 1,214,160 reasoning tokens.
    #
    # chatEditingSessions/ IS THE SECOND HALF OF THE SAME RECORD, and the tuple
    # named only the first. Measured: 196 files / 494,067,931 B across
    # ~/.config/Code (17) and ~/.config/Code - Insiders (179), one of them
    # holding linearHistory with 369 entries — a conversation store's records
    # tuple saying they are not records was simply false.
    #
    # THE PATTERN HAS TO BE LEGAL IN BOTH GLOB DIALECTS THIS TUPLE IS READ IN.
    # export_corpus picks the walk with `root.glob(g)` — pathlib, where `*` does
    # NOT cross "/" — and then re-checks every path with `store.is_record`, which
    # is matches_records/fnmatch, where `*` DOES cross "/". A pattern that leans
    # on either behaviour matches in one caller and not the other. Spelling every
    # level explicitly, `*/chatEditingSessions/*/state.json`, is exact under
    # pathlib and merely permissive under fnmatch, which is the safe direction.
    Store("copilot-chat", "{vscode}/Code/User/workspaceStorage",
          cli="copilot-chat", note="chatSessions/ under each workspace",
          records=("*/chatSessions/*.json",
                   "*/chatEditingSessions/*/state.json")),
    Store("copilot-chat-insiders", "{vscode}/Code - Insiders/User/workspaceStorage",
          cli="copilot-chat", records=("*/chatSessions/*.json",
                                       "*/chatEditingSessions/*/state.json")),
    Store("copilot-chat-empty", "{vscode}/Code/User/globalStorage/emptyWindowChatSessions",
          cli="copilot-chat"),
    Store("copilot-chat-empty-insiders",
          "{vscode}/Code - Insiders/User/globalStorage/emptyWindowChatSessions",
          cli="copilot-chat"),
    Store("clawspring-memory", ".clawspring/memory"),
    Store("clawspring-root", ".clawspring", kind="root_files",
          records=("input_history.txt",)),
    Store("proteus-sessions", ".proteus/sessions"),
    Store("proteus-memory", ".proteus/memory"),
    Store("proteus-root", ".proteus", kind="root_files",
          note="history.jsonl lives loose here",
          records=("history.jsonl", "stats-cache.json")),

    # ~/.proteus/.claude.json — THE SAME FILE SHAPE AS ~/.claude.json, IN A
    # TOOL NOBODY WAS LOOKING AT, AND ITS OWN STORE FOR THE SAME REASON
    # `.claude.json` HAS ONE.
    #
    # proteus is a Claude Code fork and it writes the fork's own copy of the
    # counter file: projects.<path>.lastTotal{Input,Output,CacheRead,
    # CacheCreation}Tokens keyed on lastSessionId — verified by reading the
    # keys, not assumed from the name. That is the exact structure
    # `read_claude_orphans` exists for, the one that recovered 4,062,282,405
    # tokens whose transcripts were already deleted. Its counters read 0 today.
    # The SHAPE is the point: nothing counts this file, so if it ever holds a
    # number, the archive is the only place that number can survive from.
    #
    # It needs to be a store because proteus-root now names its records, and
    # `.claude.json` is not one of them — the loose-file sweep that has been
    # archiving it since August would stop. A store whose path names ONE FILE
    # goes down link_tree's `only` branch, which no records tuple and no
    # name-based whitelist can filter, which is precisely why ~/.ollama/history
    # and ~/.claude.json are written that way too.
    #
    # preserve=False for the same reason as the other two .claude.json stores:
    # archived, never copied into a corpus that gets published.
    Store("proteus-claude-config", ".proteus/.claude.json",
          note="proteus is a Claude Code fork; per-project token counters",
          preserve=False,
          no_preserve_because="config, not a record — Claude Code's own "
                              "per-project counter file, kept because nothing "
                              "counts it and the archive is its only copy"),

    Store("nanobot", ".nanobot/sessions"),
    Store("nanobot-history", ".nanobot/history"),
    Store("nanobot-workspace", ".nanobot/workspace"),
    Store("deepseek-code", ".deepseek-code/sessions"),
    Store("codex-root", ".codex", kind="root_files",
          # WIDER THAN WHAT IS ON THIS MACHINE, ON PURPOSE. ~/.codex holds one
          # loose file here (config.toml, 0 bytes) — but macbook-air-m1
          # exported 3 files / 21,603 B out of it and nobody knows their names.
          # The two patterns admit any JSONL-shaped record while still refusing
          # auth.json, .credentials.json, version.json and config.toml, none of
          # which is JSONL. Narrowed to the one observed name, this would
          # silently drop 2 of 3 real records on a machine that cannot be
          # inspected from here.
          records=("history.jsonl", "*.jsonl", "*.ndjson")),
    Store("copilot-root", ".copilot", kind="root_files",
          # session-store.db-wal is IN. PRAGMA journal_mode is wal and the db
          # is 445 pages against a 1000-page autocheckpoint, so a whole
          # session's turns can sit un-checkpointed in the -wal with nothing in
          # the .db yet. -shm is OUT: read directly, it carries zero rows.
          records=("command-history-state.json", "session-store.db",
                   "session-store.db-wal")),
    # NO LOOSE RECORD HAS EVER BEEN OBSERVED IN ~/.gemini, and three of its six
    # root files are credentials — oauth_creds.json, google_accounts.json,
    # installation_id — all three of which are in the archive at the live inode
    # from before `_refuse` existed. `()` is the store saying so; it is not the
    # same as saying nothing, and until matches_records() it was.
    #
    # The records under .gemini are all one directory down (tmp/, and
    # antigravity-cli/), and those have their own stores.
    Store("gemini-root", ".gemini", kind="root_files", records=()),
    Store("jules", ".jules", kind="root_files", records=("history.txt",)),

    # REMOVED, NOT preserve=False — and the difference is the whole reason
    # these three lines are a comment instead of a flag:
    #
    #   Store("devvit", ".devvit", kind="root_files")
    #       the entire tree is `token` (a Reddit OAuth access+refresh pair,
    #       scope *, the refresh half with NO EXPIRY) and `session-id` (a bare
    #       UUID). devvit is a subreddit-app deploy CLI. It has no
    #       conversations, at the root or below, so there is nothing here for a
    #       records tuple to name. ~/.devvit is in retention_guard's
    #       DISCOVER_SKIP so its removal does not turn into a NOT COVERED
    #       alarm that is wrong on every run.
    #   Store("nanobot-root", ".nanobot", kind="root_files")
    #       one loose file, config.json, whose schema is 26 credential-named
    #       string fields — channels.telegram.token, channels.feishu.appSecret,
    #       providers.*.apiKey. The real records are already covered by
    #       nanobot, nanobot-history and nanobot-workspace.
    #   Store("deepseek-code-root", ".deepseek-code", kind="root_files")
    #       one loose file, config.json, 324 B of model/effortLevel/_version.
    #       deepseek-code covers the (empty) sessions/ directory.
    #
    # preserve=False would NOT have done this. It is read by the EXPORTER
    # (_tool_roots skips it) and by nothing in retention_guard: OTHER_SOURCES
    # and ROOT_FILE_SOURCES are built from every store regardless, so a store
    # marked unpreservable is still walked and still hard-linked. Using it here
    # would have left both credential files exactly where they are and looked
    # like a fix.
    #
    # Nothing deletes what is already archived. other/devvit/token,
    # other/devvit/session-id, other/nanobot-root/config.json and
    # other/deepseek-code-root/config.json are hard links made before the
    # refuse rule existed and they stay until somebody moves them by hand.
    # ~/.ollama/history is a FILE, not a directory. Every rule here assumed a
    # directory, so it read as "absent" — indistinguishable from ollama not
    # being installed — for as long as the rule has existed.
    Store("ollama", ".ollama/history", note="a file, not a directory"),

    # -- not on this machine; covered the day they appear. A tool that shows up
    #    on a laptop nobody has scanned yet should be preserved on its first run,
    #    not on the run after somebody notices.
    # Bob AI assistant — ~/.bob/db/ holds a SQLite database (bob.db) with all
    # conversation history and per-turn token spend. The database is WAL-mode;
    # the -shm file is OUT (read-only, carries no rows); the -wal file is IN
    # (may hold unflushed turns). preserve=False: the DB is never deleted by
    # Bob itself, so the archiver hard-links for inode-safety but the exporter
    # does not ship it (contains full unredacted conversation text).
    Store("bob", ".bob/db",
          cli="bob",
          kind="root_files",
          records=("bob.db", "bob.db-wal"),
          preserve=False,
          no_preserve_because="SQLite DB holds full unredacted conversation "
                              "text; counted but never exported to the corpus"),

    Store("deepseek", ".deepseek/sessions"),
    Store("cursor", ".cursor/chats"),
    Store("aider", ".aider"),
    Store("cline", "{vscode}/Code/User/globalStorage/saoudrizwan.claude-dev/tasks"),
    Store("roo", "{vscode}/Code/User/globalStorage/rooveterinaryinc.roo-cline/tasks"),
    Store("continue", ".continue/sessions"),
    Store("opencode", ".opencode/sessions"),
    Store("goose", ".config/goose/sessions"),
    Store("openhands", ".openhands/sessions"),
    Store("qwen", ".qwen/tmp"),
    Store("amp", ".amp/threads"),
]

BY_LABEL = {s.label: s for s in STORES}


# ---------------------------------------------------------------------------
# The four views the rest of the system already asks for.
# ---------------------------------------------------------------------------

def conversation_stores():
    """Directories of records. What the archiver links and the exporter backs up."""
    return [s for s in STORES if s.kind == "conversations"]


def root_file_stores():
    """Loose records beside a tool's program directories. Never recursed."""
    return [s for s in STORES if s.kind == "root_files"]


def detect_patterns():
    """{cli: (path, ...)} for sessions.detect() — only stores a reader counts.

    Grouped by cli rather than by label because grok writes to two directories
    and one reader counts both; asking "is grok present" must not depend on
    which of its two directories was checked.

    `rel_paths()`, NOT `path`. This function handed sessions.detect() the raw
    `path` string, so the six VS Code-family stores were checked at a directory
    literally named `{vscode}` — measured on this machine, where
    ~/.config/Code/User/workspaceStorage holds 4.75 GB:

        kilocode      not found   ~/{vscode}/Code/User/globalStorage/…/tasks
        copilot-chat  not found   ~/{vscode}/Code/User/workspaceStorage

    Both reported `installed: false` in sessions.json on every run this
    repository has ever made, on every platform, while their readers counted
    real tokens out of the very trees detect() said were not there. It is the
    same failure the `{vscode}` token was introduced to fix, one caller down.
    """
    out = {}
    for s in STORES:
        if s.cli:
            out.setdefault(s.cli, []).extend("~/" + r for r in s.rel_paths())
    return {k: tuple(v) for k, v in out.items()}


def covered_paths():
    """Paths sweep_usage should treat as already COUNTED. Requires a reader.

    `cli` is the whole condition, and getting it wrong is silent. The first
    version returned every conversation store, which would have marked
    clawspring, proteus, nanobot, deepseek-code and ollama as covered — they are
    ARCHIVED, and no reader counts a token in any of them. The sweep would then
    have reported "every numeric token field sits in a path a reader already
    reads" about five tools it reads nothing from, which is the precise blindness
    the sweep was written to break.

    Preserved and counted are different questions. This one answers counted.

    A root_files store is excluded for a related reason: claiming all of
    ~/.copilot would blind the sweep to a NEW subdirectory copilot starts
    writing to, and noticing that is the job.
    """
    # rel_paths(), or the sweep compares a real path against a literal holding
    # `{vscode}` and reports every VS Code store as uncounted on every run.
    return [p for s in conversation_stores() if s.cli for p in s.rel_paths()]


def paths_for(*labels):
    """Platform-expanded relative paths for these labels, for a reader's bases.

    sessions.py's @multi_base decorators listed their own literals — including
    `.config/Code/User/workspaceStorage` — so read_copilot_chat was a hardcoded
    Linux path on every platform and returned 0 on macOS while the store map
    returned []. Two lists of the same fact, wrong in the same place. Now the
    reader asks the map.
    """
    out = []
    for lbl in labels:
        s = BY_LABEL.get(lbl)
        if s:
            out.extend(s.rel_paths())
    # Order preserved, duplicates dropped: two labels can expand onto the same
    # directory, and multi_base would then read it twice.
    seen, uniq = set(), []
    for p in out:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return tuple(uniq)


def counted_never_preserved():
    """{cli: reason} for stores that a reader counts and the exporter must skip.

    Read rather than restated. The first version of this fact lived as a literal
    dict in count_corpus.py asserting "config, never exported" — written while
    the exporter was, at that moment, exporting it. A second copy of a fact is a
    second place for it to be wrong, and this one was wrong immediately.

    Keyed by CLI, and several stores can feed one reader — claude-orphans has
    two, `.claude.json` and `.claude*/.claude.json`. Taking the last one's
    reason left the caller printing "same file, one per profile", which explains
    nothing on its own. Longest wins: the store that bothered to say why.
    """
    out = {}
    for s in STORES:
        if s.cli and not s.preserve:
            if len(s.no_preserve_because) > len(out.get(s.cli, "")):
                out[s.cli] = s.no_preserve_because
    return out


def uncounted_stores():
    """Preserved by the archive, counted by no reader.

    The honest gap, queryable instead of anecdotal: everything here is history
    that survives a disk failure and appears in no total.
    """
    return [s for s in conversation_stores() if not s.cli]


def unpreserved_readers(readers):
    """Readers with no store IN THE MAP — counted, and nothing is even meant to
    back them up.

    This is a question about the map, and it is worth asking, but on its own it
    was read as an answer to a question it cannot reach. It says every reader
    has somewhere to be preserved TO. It says nothing about whether anything is
    preserved there. copilot-chat sat in this list at a correct path holding
    4.75 GB, exported never, and this function returned clean the whole time —
    a map compared against itself agrees with itself.

    `unpreserved_in_corpus()` is the one that can fail on real data.
    """
    have = {s.cli for s in STORES if s.cli}
    return sorted(set(readers) - have)


def unpreserved_in_corpus(readers, corpus_machine):
    """Readers whose store has NO directory in this machine's corpus export.

    The gap the map cannot see. `corpus_machine` is one machine folder in
    deadreckon-record; a reader counts as preserved when at least one store feeding
    it has a `tools/<label>/` directory, or — for Claude — the profile tree the
    exporter writes instead.
    """
    tools = os.path.join(corpus_machine, "tools")
    try:
        present = set(os.listdir(tools))
    except OSError:
        present = set()
    if os.path.isdir(os.path.join(corpus_machine, ".claude", "projects")):
        present.add("claude")
    covered = {s.cli for s in STORES if s.cli and s.label in present}
    return sorted(set(readers) - covered)


def resolve(store, home=None):
    """Every real path for a store, expanding the profile glob.

    `.claude*/projects` is five directories on this machine and one on most.
    Callers that treated it as a literal path found none of them.

    Every path in this file is written with "/" separators, and the hand-rolled
    version split them on `os.sep`. On Linux those are the same character and it
    worked; on native Windows `os.sep` is "\\", so `.claude*/projects` split into
    a single part, `pat` became the whole string, and every globbed store
    resolved to []. Worse than empty — `tail` was "" too, so a bare `~/projects`
    directory would have matched as a Claude store. `glob` handles both
    separators on both platforms, and it is the same call `exists()` and
    `detect()` were already making, which is why they kept saying yes while this
    said no.

    A store the operator MOVED with $CODEX_HOME, $COPILOT_HOME,
    $GEMINI_CLI_HOME, $CLAUDE_CONFIG_DIR, $XDG_CONFIG_HOME or %APPDATA% is
    reached here too — see RELOCATIONS. Before that, every one of those returned
    [] with the records sitting on disk, which is the answer this map also gives
    for a tool nobody ever installed.

    IT LOOKS AT `candidates()`, NOT AT `rel_paths()`, which is what makes the
    same call correct on a machine nobody here has logged into: the collected
    path is the first thing checked and the derived forms follow it.

    STILL TWO-VALUED. [] here means "found nothing", and it still cannot say
    whether that is because nothing is there or because nothing could be
    entered. `state()` answers that; this signature has a dozen callers written
    against a list of paths and they keep it.
    """
    return _lookup(store, home or HOME)[0]


def main(argv=None):
    import json
    scanned = scan()
    if argv and "--json" in argv:
        json.dump({"family": family(), "forms": list(tool_forms()),
                   "environment": environment(), "stores": scanned},
                  sys.stdout, indent=1)
        print()
        return 0

    import sessions
    print(f"\n  {family()}: a tool's folder is looked for at "
          + ", ".join(f.replace("{tool}", "<tool>") for f in tool_forms()))
    print()
    print(f"  {'store':<28}{'cli':<14}{'kind':<15}{'here':<12}note")
    for s in STORES:
        st = scanned[s.label]
        # UNREADABLE IS PRINTED, not folded into the blank that means absent.
        # A row that reads "" for a directory nobody could enter is this
        # repository's oldest defect wearing the report's own clothes.
        here = {INSTALLED: "yes", ABSENT: "", UNREADABLE: "UNREADABLE"}[st["state"]]
        print(f"  {s.label:<28}{s.cli or '—':<14}{s.kind:<15}{here:<12}{s.note}")
    n = counts(scanned)
    unc = [s.label for s in uncounted_stores() if resolve(s)]
    unp = unpreserved_readers(sessions.READERS)
    print()
    print(f"  installed {n[INSTALLED]}   absent {n[ABSENT]}   "
          f"UNREADABLE {n[UNREADABLE]}")
    for label, st in sorted(scanned.items()):
        for p, e, name in st["blocked"]:
            print(f"    {label:<26}{name:<10}{p}")
    print(f"  present but counted by nobody   {len(unc)}: {', '.join(unc) or 'none'}")
    print(f"  counted but preserved by nobody {len(unp)}: {', '.join(unp) or 'none'}")
    env = environment()
    print(f"  store paths moved by the env    {len(env)}: "
          + (", ".join(f"{k}={v}" for k, v in env.items()) or "none set"))
    irr = irregular_stores()
    print(f"  derived from the tool's name    {len(STORES) - len(irr)} of "
          f"{len(STORES)}; {len(irr)} exception(s): {', '.join(irr) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
