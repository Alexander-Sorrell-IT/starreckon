#!/usr/bin/env python3
"""Stop AI-coding CLIs from deleting your history. Two layers, neither destructive.

THE PROBLEM

Claude Code deletes session files older than `cleanupPeriodDays` AT STARTUP.
The default is 30 and the documented minimum is 1 — there is no "off". Worse,
cleanup only runs for the profile you launch, so a profile you have not opened
in months still holds old logs that will be destroyed the moment you do open it.

Measured on this machine when this was written:

    .claude       cleanupPeriodDays=30   oldest log  94 days  -> 64 days would die
    .my-claude    cleanupPeriodDays=30   oldest log  87 days  -> 57 days would die
    .claude-it    cleanupPeriodDays=30   oldest log  59 days  -> 29 days would die

No other CLI does this. gemini still holds files from 2023-06-26; copilot,
codex, kilocode and lmstudio have no retention setting at all. Claude Code is
the only one deleting, so it is the only one that needs defending against.

LAYER 1 — RAISE THE PERIOD (the box)

Set `cleanupPeriodDays` to 36500 (100 years). Cleanup still runs; it simply
never matches anything. This is not a hack around the feature, it is the
feature: "delete things older than N" with an N nothing reaches.

This script NEVER LOWERS the value. A lower number deletes MORE, so shrinking it
is the one edit that could destroy data, and the code refuses to make it.

LAYER 2 — HARD-LINK ARCHIVE (the belt)

A setting can be reset by an update, a sync, or a stray edit, and a config that
is right today is not a guarantee. So every transcript also gets a hard link in
an archive directory.

A hard link is a second NAME for the same inode. Claude Code's cleanup unlinks
its own name; the data lives on under this one. Measured here: content and mtime
intact after the original was removed, and the archive costs **0 bytes**,
because it is the same disk blocks, not a copy.

Requires the archive to be on the same filesystem as the profile — a hard link
cannot cross one. The script checks and says so rather than silently copying
581 MB.

WHY NOT THE OTHER IDEAS

  Touching mtimes so files look new — works, but mtime IS data. It is how the
  retention of every CLI was measured in the first place. Falsifying it to
  protect it defeats the point.

  Making the directory immutable (chattr +i) — cleanup would fail, but so might
  Claude Code's own writes, and a tool that cannot write its session file is a
  broken tool.

  Both were considered and rejected. Raising the period and hard-linking change
  nothing about how the tools behave.

USAGE
    retention_guard.py --check     report exposure, change NOTHING
    retention_guard.py --apply     raise the period + link new transcripts
    retention_guard.py --daemon    re-assert periodically (default every 6h)
"""
import glob
import json
import os
import pathlib
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import paths
import stores
# THE RECORD/CONFIG TEST IS IMPORTED, NOT COPIED.
#
# export_corpus already carries it, and its comment names the exact two files
# this archiver put on disk — ~/.devvit/token and ~/.gemini/oauth_creds.json —
# in the PAST TENSE, as an incident already dealt with. It was dealt with in the
# exporter and nowhere else, so for every day since, the archiver went on
# hard-linking both at the same inode as the live original.
#
# A second copy of the rule here is how that happens again. This codebase has
# shipped one rule from two places four separate times.
#
# AND IT IS THE WHOLE RULE, NOT A THIRD OF IT. export_corpus applies THREE
# tests, and the first version of this import took one:
#
#     _is_loose_record   root files only    export_corpus.py:499
#     SECRET_DIRS        EVERY depth        export_corpus.py:512
#     _is_config         EVERY depth        export_corpus.py:515
#
# Only the 10 root_files stores are walked with top_only, so importing the
# root-only test covered 10 stores of 49 and left the 39 conversation stores
# walked recursively with no test at all. Reproduced against the shipped file,
# called exactly the way run() calls it for a conversation store:
#
#     link_tree(src, 'other/probe', apply=True) -> (4, 0, 'ok')
#     other/probe/proj/oauth_creds.json      nlink(live)=2
#     other/probe/proj/.credentials.json     nlink(live)=2
#     other/probe/proj/mcp-secrets/gh.json   nlink(live)=2
#     REFUSED_CONFIG == []
#
# export_corpus's own comment says a root-only rule is not enough in the same
# words, and names the file that proved it: ~/.gemini/oauth_creds.json reached
# an export from the ARCHIVE, nested, where no root-only test ever looked.
from export_corpus import (_is_loose_record, _is_secret, secret_ancestor,
                           secret_dir, secret_symlink_target)

FAILED_LINKS = []   # stores whose links failed this run
GHOSTS = []         # live files whose archived copy is a DIFFERENT inode
REFUSED_CONFIG = [] # (label, name, already_in_archive) — config, never linked
UNRECOGNISED = []   # (label, name) — LINKED, but the name is not a record name
NOT_A_RECORD = []   # (label, name) — NOT LINKED: the store named its records
VANISHED = []       # (label, path, n_archived) — archived once, source now gone
try:
    import sys as _sys
    import os.path as _osp
    _rg_dir = _osp.dirname(_osp.realpath(__file__))
    if _rg_dir not in _sys.path:
        _sys.path.insert(0, _rg_dir)
    from platform_detect import real_home as _real_home
    HOME = str(_real_home())
except Exception:   # noqa: BLE001
    HOME = os.path.expanduser("~")
ARCHIVE = os.path.join(HOME, ".ai-logs-archive")
TARGET_DAYS = 36500  # 100 years

# INTERVAL comes from cli-config.json (daemon.ledger_interval_hours), falling
# back to the env var override, then to the 6h default. The env var is kept so
# the existing systemd/launchd service files that set it keep working without
# change. Config takes precedence over the env var when both are present,
# because the config is the committed, visible source of truth and the env var
# is an operator override that is often forgotten.
def _load_interval():
    try:
        import config as _cfg
        _, ledger_h = _cfg.daemon_intervals()
        return int(ledger_h * 3600)
    except Exception:
        pass
    return int(os.environ.get("RETENTION_GUARD_INTERVAL", str(6 * 3600)))

INTERVAL = _load_interval()

# Directories never worth walking when looking for a profile. Same spirit as the
# collector's COPY_DIRS: large, and structurally incapable of holding one.
# Library and AppData are here because on macOS and Windows they are enormous and
# a Claude profile does not live inside them.
SKIP_WALK = {".cache", ".npm", ".gradle", ".wine", ".git", "node_modules",
             "__pycache__", ".venv", "venv", "site-packages", ".rustup",
             ".cargo", ".mozilla", ".thunderbird", ".ai-logs-archive",
             ".basilisk", "models", "Library", "AppData"}


# Claude profiles are DISCOVERED, and by SHAPE rather than by name.
#
# Three versions of this were wrong, each one narrower than the problem:
#
#   hardcoded list      missed .claude-alt-api, which was still at 30 days with
#                       59-day-old transcripts.
#   name match ~/.*claude*   misses a profile that is not named for Claude, and
#                       misses every copy outside the home root.
#   name match, depth 1 misses macOS and Windows layouts entirely, and misses
#                       ~/Desktop/<something>/.claude — where analyze_tokens
#                       measured 818,673,995 tokens present in NO live profile.
#
# analyze_tokens.find_config_dirs already solved this: a Claude profile is any
# directory containing `projects/` with at least one .jsonl beneath it, found by
# walking home to depth 4. That test is the same on Linux, macOS and Windows,
# because it describes the profile instead of describing where an operating
# system puts things.
#
# It is imported rather than reimplemented. This file used to carry its own
# discovery, and two copies of one rule is how this codebase has shipped the
# same defect four separate times.
def _archive_key(prof):
    """A unique, stable archive folder name for a profile path.

    Basename alone is not unique: this machine has three different directories
    named `.claude`, and folding them into one archive folder would silently
    merge three profiles' history into one.
    """
    rel = os.path.relpath(prof, HOME) if _under(prof, HOME) else prof
    return rel.replace(os.sep, "_").replace(":", "").lstrip("._") or "root"


def windows_side_profiles():
    """Claude profiles on the WINDOWS side, when this is running inside WSL.

    WSL has its own Linux home. A Windows machine that runs Claude Code in
    PowerShell AND in WSL therefore has TWO independent installations, each with
    its own ~/.claude and its own cleanupPeriodDays, and protecting one does
    nothing for the other.

    This is the cross-platform equivalent of the per-profile asymmetry that made
    the guard necessary in the first place: the side you are not looking at is
    the side quietly holding the most.

    Reported, never modified. Writing into /mnt/c from WSL works, but a Windows
    settings.json edited through the WSL mount is exactly the kind of surprise
    this tool should not spring on someone — run the guard natively on that side
    instead, in PowerShell.

    BY SHAPE, NOT BY NAME. This used `glob(".*claude*")` at depth 1 — the exact
    rule analyze_tokens.find_config_dirs calls defective 55 lines into its own
    docstring, because $CLAUDE_CONFIG_DIR accepts any path and a profile is
    whatever contains projects/ with a .jsonl beneath it. On this machine a
    name-glob found 6 profiles where discovery by shape found 23. There is no
    reason the Windows side should be searched worse than the Linux one.
    """
    try:
        with open("/proc/version") as fh:
            if "microsoft" not in fh.read().lower():
                return []
    except OSError:
        return []
    import pathlib
    from analyze_tokens import find_config_dirs
    out = []
    for drive in sorted(glob.glob("/mnt/[a-z]")):
        for user in sorted(glob.glob(os.path.join(drive, "Users", "*"))):
            base = os.path.basename(user)
            if base in ("Public", "Default", "Default User", "All Users"):
                continue
            try:
                for p in find_config_dirs(pathlib.Path(user)):
                    out.append(str(p))
            except OSError:
                # An unreadable Windows user directory is normal — every other
                # account on that machine. Skip it, do not abandon the drive.
                continue
    return sorted(set(out))


def _under(path, root):
    try:
        return os.path.commonpath([os.path.realpath(path), os.path.realpath(root)]) == \
               os.path.realpath(root)
    except (ValueError, OSError):
        return False


def claude_profiles():
    import pathlib

    home = pathlib.Path(HOME)
    try:
        sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
        from analyze_tokens import find_config_dirs
        found = [str(p) for p in find_config_dirs(home)]
        # find_config_dirs is deliberately greedy — for COUNTING that is right,
        # because global dedup makes a copy worth zero. For DEFENDING it is not:
        # it returns this script's own hard-link archive (whose entries are the
        # same inodes) and every copied profile on the disk. Archiving the
        # archive nests forever, and a copy has no settings.json to raise.
        return [p for p in found if not _under(p, ARCHIVE)]
    except Exception:  # noqa: BLE001 - standalone copy, outside the repo
        pass

    # Fallback for a copy of this script living on its own: the SAME shape test,
    # walked to the same depth. Kept deliberately short so the two cannot drift
    # in behaviour, only in speed.
    out, seen = [], set()

    def looks_like_profile(p):
        # Same EACCES guard as the primary in analyze_tokens: pathlib's
        # is_dir() re-raises Permission denied, and one directory this user
        # cannot enter took the whole guard down. Silent under --daemon: the
        # tick caught it, systemd showed active, and no archive was ever made.
        proj = p / "projects"
        try:
            if not proj.is_dir():
                return False
            for _ in proj.rglob("*.jsonl"):
                return True
        except OSError:
            return False
        return False

    def add(p):
        try:
            key = p.resolve()
        except OSError:
            return
        if key not in seen and looks_like_profile(p) and not _under(str(p), ARCHIVE):
            seen.add(key)
            out.append(str(p))

    for p in sorted(home.glob(".*claude*")):
        add(p)
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    if env:
        for part in env.split(os.pathsep):
            if part.strip():
                add(pathlib.Path(part.strip()).expanduser())
    stack = [(home, 0)]
    while stack:
        cur, depth = stack.pop()
        if depth >= 4:
            continue
        try:
            entries = list(cur.iterdir())
        except (OSError, PermissionError):
            continue
        for e in entries:
            try:
                if not e.is_dir() or e.name in SKIP_WALK:
                    continue
            except OSError:
                continue                    # unreadable: skip it, not the walk
            add(e)
            stack.append((e, depth + 1))
    return out


# EVERY path Claude Code deletes on startup, from the official docs
# (claude-directory#cleaned-up-automatically). The first version of this script
# linked only `projects/`, which left twelve other categories — including
# file-history (pre-edit snapshots) and plans/ — unprotected.
CLAUDE_CLEANED = [
    "projects",           # transcripts, plus subagents/ and tool-results/ under them
    "file-history",       # pre-edit snapshots used by checkpoint restore
    "plans",              # plan-mode plans
    "debug",              # per-session debug logs
    "paste-cache",
    "image-cache",
    "session-env",
    "tasks",              # per-session task lists
    "shell-snapshots",
    "backups",            # copies of ~/.claude.json before config migrations
    "feedback-bundles",
    "todos", "statsig", "logs",   # legacy, swept and then removed entirely
]

# LOOSE RECORDS AT A PROFILE'S ROOT. Not in CLAUDE_CLEANED, because Claude Code
# does not sweep them — and that is exactly why nothing was archiving them: the
# per-profile loop below only ever walked the swept subdirectories, so the two
# files sitting BESIDE those directories belonged to no rule at all.
#
#   history.jsonl    every prompt typed at this profile, with its sessionId.
#                    5 profiles, 5,089,378 B, 15,051 prompts, 570 sessionIds —
#                    of which 460 have NO transcript on disk and none in the
#                    archive, because cleanupPeriodDays took the transcript and
#                    left the prompt. All five at nlink=1: no second name
#                    anywhere. For those 460 sessions this file is not the best
#                    evidence, it is the ONLY evidence.
#   stats-cache.json lifetime token counters — 12,290,485,337 in ~/.claude and
#                    11,440,918,343 in ~/.claude-alt — which survive the
#                    transcripts they were counted from, the same way
#                    .claude.json's per-project counters do.
#
# HUNG ON claude_profiles(), NOT ON A GLOB AND NOT ON A LIST OF NAMES, and both
# of the obvious alternatives were tried first and are worse:
#
#   Store("claude-profile-root", ".*claude*", kind="root_files", records=(...))
#       ROOT_FILE_SOURCES paths go to link_tree through os.path.join with NO
#       glob expansion — every other root store's path is a literal. `~/.*claude*`
#       is neither a file nor a directory, so link_tree returns (0, 0, 'absent')
#       and BOTH print gates in run() are `if note != "absent"`. The store
#       archives nothing AND SAYS NOTHING: a silent zero, this repository's
#       single most-repeated bug. Reproduced before this was written.
#       It also resolves onto ~/.claude.json and ~/.claude.json.backup, which are
#       FILES — link_tree's file branch sets `only`, and `only` disables the
#       records allow-list and the loose-record whitelist outright, so both
#       would be linked under a new label whose preserve defaults to True,
#       re-admitting the exact bytes claude-config carries preserve=False for.
#
#   five literal stores, one per profile directory
#       names this machine's spelling of a fact that has no fixed spelling.
#       $CLAUDE_CONFIG_DIR takes ANY path: `.claude*` misses ~/.my-claude and
#       `.*claude*` misses ~/Desktop/standout_full/.claude, which is why
#       find_config_dirs recognises a profile BY SHAPE and why
#       windows_side_profiles() already says so 60 lines up. Here that is 5 of
#       the 9 profiles this machine has, and 0 on a machine that names its own
#       something else.
#
# claude_profiles() returns a directory only when `projects/` with a .jsonl is
# under it, so the source of this pass EXISTS BY CONSTRUCTION — "absent" is not
# a state it can reach quietly, and run() treats it as a fault if it ever does.
CLAUDE_PROFILE_RECORDS = ("history.jsonl", "stats-cache.json")

# Non-Claude CLIs. None has a retention setting — verified by gemini still
# holding 2023 files — so these are linked for safety, not defended.
# Conversation directories, measured — not whole tool trees, and not guessed
# subfolders either. Both of those were tried and both were wrong:
#
#   guessed subfolder   .proteus keeps history.jsonl at its ROOT, outside the
#                       sessions/ folder that was being linked, so most of it
#                       was missed.
#
#   whole directory     pulled in .gemini/extensions (404 MB, 17,600 files) and
#                       .copilot/pkg (120 MB) — program files, not history. They
#                       even survive a grep for `input_tokens`, because the
#                       tools' own SOURCE names those fields. That is the same
#                       false positive as a browser extension's locale file
#                       containing the literal string "total_tokens".
#
# So each tool lists the directories that actually hold conversations, plus its
# root-level files where those carry data. Verified by walking every subdirectory
# of every installed tool and checking which ones hold real records.
# Both of these are DERIVED from stores.py now. The tables that used to be
# written out here held 40 entries, 6 of which were also spelled out in
# sessions.DETECT and again in sweep_usage.COVERED — the same fact in three
# files, each one a place a fix could land without landing in the others.
#
# This file's job is the two layers in the docstring: raise cleanupPeriodDays,
# and hard-link. Knowing where every CLI on earth keeps its records is not that
# job; it is a fact the counter, the archiver and the exporter all need, which
# is exactly what makes it shared rather than local.
# rel_paths(), not .path: a VS Code store expands to more than one place on
# macOS (~/Library/Application Support AND ~/.config), and `.path` carries the
# unexpanded `{vscode}` token, which joins to a directory that cannot exist.
# Values are LISTS for that reason; only one of them is normally present.
OTHER_SOURCES = {s.label: s.rel_paths() for s in stores.conversation_stores()}
ROOT_FILE_SOURCES = {s.label: s.rel_paths() for s in stores.root_file_stores()}

# AND WHAT, INSIDE A ROOT_FILES STORE, IS ACTUALLY A RECORD.
#
# `records` was decorative until this line existed. `grep -c "is_record\|\.records"
# retention_guard.py` returned 0: the archiver read the store map for PATHS and
# for nothing else, so every loose file beside a tool's program directories was
# a CANDIDATE that then had to be denied by NAME. That is backwards — it is why
# ~/.gemini/oauth_creds.json and ~/.devvit/token are in the archive at the same
# inode as the live original, from before `_refuse` existed. A rule that lists
# what a store's records ARE cannot be surprised by a credential it has never
# heard of; a rule that lists what to refuse can, and was, twice.
#
# ROOT_FILES ONLY, AND THAT IS NOT AN OVERSIGHT. A root_files store's records
# are a short list of names at depth 0 and everything else there is the tool's
# configuration, so an allow-list is the whole truth about it. A conversation
# store is the opposite: copilot-chat's root is 4.5 GB of other extensions'
# state, its tuple names only the shapes somebody has already thought to write
# down, and this program ships nothing — so the cost of wiring the tuple into
# OTHER_SOURCES is every record shape NOBODY HAS NOTICED YET, dropped silently,
# forever.
#
# That is not hypothetical, and the example is the reason to state the rule this
# way rather than by naming a pattern. For as long as it existed that tuple said
# `*/chatSessions/*.json` and nothing else, while 196 files / 494,067,931 B of
# `*/chatEditingSessions/*/state.json` — one holding linearHistory with 369
# entries — sat beside it unnamed. The tuple has since been WIDENED to name
# them, so the old wording here ("they do not match it") is no longer true; the
# rule it was defending is, and more strongly. The next unnamed shape has not
# been discovered yet, and the archiver keeps it either way only because no
# allow-list runs on a conversation store.
#
# A label with no entry, or an entry of None, is filtered by nothing — the
# archiver's default stays "keep it, a link costs 0 bytes". Only a store that
# has written down what its records are gets narrowed to them.
ROOT_FILE_RECORDS = {s.label: s.records for s in stores.root_file_stores()}


# Directories that look like an AI CLI's store but are not in OTHER_SOURCES.
# Reported, never linked: a tool nobody configured is exactly the tool whose
# data goes missing, and printing the name is how it stops being invisible.
DISCOVER_HINTS = ("session", "conversation", "chat", "history", "thread", "task")
DISCOVER_SKIP = {".cache", ".local", ".config", ".mozilla", ".pki", ".gnupg", ".ssh",
                 ".npm", ".gradle", ".wine", ".zoom", ".vscode", ".vscode-insiders",
                 ".ai-logs-archive", ".git",
                 # 239,591 files / 26 GB, with timestamps back to 1969 — this is
                 # the VORTEX/basilisk workspace, not a conversation store.
                 # Linking it would add a quarter-million directory entries for
                 # data that is not usage history.
                 ".basilisk",
                 # browser/credential profiles, not AI sessions
                 ".creds-profile", ".creds-profile-ff", ".melius_browser_session",
                 # A CREDENTIAL STORE THAT LOOKS SESSION-SHAPED AND IS NOT.
                 # ~/.devvit holds exactly two files, `token` (a Reddit OAuth
                 # access+refresh pair, scope *, the refresh half with no
                 # expiry) and `session-id` (a bare UUID). Devvit is a
                 # subreddit-app deploy CLI: it has no conversations, at the
                 # root or below. Its store was removed from stores.py for that
                 # reason, and DISCOVERY WOULD THEN REPORT IT ON EVERY RUN —
                 # `session-id` contains "session", which is a DISCOVER_HINT.
                 # An alarm that is wrong every time is one people stop
                 # reading, which costs the real one its meaning; that exact
                 # sentence is already in run(), about this exact directory.
                 ".devvit"}


def log(msg):
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {msg}", flush=True)


def oldest_age_days(root):
    """Age in days of the oldest file under root, or None if there are none."""
    oldest = None
    for dirpath, _d, files in os.walk(root):
        for f in files:
            try:
                m = os.path.getmtime(os.path.join(dirpath, f))
            except OSError:
                continue
            if oldest is None or m < oldest:
                oldest = m
    return None if oldest is None else int((time.time() - oldest) / 86400)


def settings_path(profile):
    """profile is an ABSOLUTE path — profiles are no longer assumed to sit
    directly under $HOME, because on macOS and Windows they often do not."""
    return os.path.join(profile, "settings.json")


def current_period(profile):
    try:
        with open(settings_path(profile)) as fh:
            return json.load(fh).get("cleanupPeriodDays", 30)
    except Exception:  # noqa: BLE001 - a missing/bad file means the default applies
        return 30


WINDOWS_MOUNTS = ("/mnt", "/media")


def is_windows_side(profile, roots=WINDOWS_MOUNTS):
    """Does this profile live on a Windows filesystem reached from WSL?

    RESOLVED, not string-matched on the path as given. A profile arrives here
    two ways that both look local: a SYMLINK in the Linux home pointing into
    /mnt/c, and $CLAUDE_CONFIG_DIR set to one. realpath() collapses both, and
    the symlink is the one that matters — the path the caller holds says
    nothing about where the bytes are.

    `roots` is injectable only so this can be tested. The first version
    hardcoded an absolute /mnt and the test built its mount under a temp
    directory, so the check answered False and the fixture reported the guard
    had failed when the guard was right and the fixture was wrong.
    """
    try:
        real = os.path.realpath(profile)
    except OSError:
        return False
    real = real.replace("\\", "/")
    for base in roots:
        # RESOLVE THE ROOT TOO. On macOS /var/folders is a symlink to
        # /private/var/folders, so a test-injected `root/mnt` path that is not
        # realpath'd would not match the realpath'd profile. The production
        # default ("/mnt", "/media") has no symlinks, but injectable roots do.
        try:
            base = os.path.realpath(base)
        except OSError:
            pass
        base = base.rstrip("/").replace("\\", "/")
        if not real.startswith(base + "/"):
            continue
        rest = real[len(base) + 1:].split("/")
        # /mnt/c/... — a single-letter drive directory is the WSL convention.
        if rest and len(rest[0]) == 1 and rest[0].isalpha():
            return True
    # A UNC path, or a bare drive letter from a config written on Windows.
    return real.startswith("//") or (len(real) > 1 and real[1] == ":")


def raise_period(profile, apply, mounts=WINDOWS_MOUNTS):
    """Raise cleanupPeriodDays. Returns (changed, message).

    REFUSES a Windows-side profile, here rather than at discovery.
    windows_side_profiles() reports those deliberately — the counter must keep
    counting them, and the whole point of that report is to tell you the other
    half of the machine exists. What must not happen is this function EDITING
    one: writing into /mnt/c from WSL works, and a Windows settings.json
    silently rewritten through the mount, unattended, every six hours, is
    exactly the surprise the docstring above promises not to spring.

    Reproduced before the guard existed, with a symlink from the Linux home
    into a Windows profile:

        raise_period(...) -> changed=True '30 -> 36500 (not applied, --check)'

    And it compounded: windows_side_profiles() then re-read the file the guard
    had just written and printed the raised number as evidence the Windows side
    was fine.
    """
    if is_windows_side(profile, mounts):
        return False, ("WINDOWS-SIDE — reported, never modified. Run the guard "
                       "natively in PowerShell on that side.")
    p = settings_path(profile)
    if not os.path.exists(p):
        return False, "no settings.json"
    cur = current_period(profile)
    if cur >= TARGET_DAYS:
        return False, f"already {cur}"
    if not apply:
        return True, f"{cur} -> {TARGET_DAYS} (not applied, --check)"
    try:
        with open(p) as fh:
            doc = json.load(fh)
    except Exception as e:  # noqa: BLE001
        return False, f"unreadable settings.json ({e}) — NOT touched"
    # Back up before the first edit, once, so the original is always recoverable.
    bak = p + ".before-retention-guard"
    if not os.path.exists(bak):
        shutil.copy2(p, bak)
    doc["cleanupPeriodDays"] = TARGET_DAYS
    tmp = p + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(doc, fh, indent=2)
    os.replace(tmp, p)  # atomic: a crash mid-write cannot leave a truncated config
    return True, f"{cur} -> {TARGET_DAYS} (backup: {os.path.basename(bak)})"


def same_filesystem(a, b):
    """Are these on one filesystem? `b` need not exist yet.

    The filesystem check has to happen BEFORE the destination is created —
    creating it first leaves an empty look-alike skeleton in the archive for a
    profile nothing can ever link into, and a directory that exists and holds
    nothing reads like a profile with no history.

    But a path that does not exist has no st_dev, and returning False for that
    reported "DIFFERENT FILESYSTEM" for every store on a first run. So walk up
    to the nearest ancestor that DOES exist: a directory inherits the
    filesystem it will be created on.
    """
    def dev(p):
        try:
            return os.stat(_nearest_existing(p)).st_dev
        except OSError:
            return None

    da, db = dev(a), dev(b)
    return da is not None and da == db


def _nearest_existing(path):
    """The closest ancestor of `path` that can be stat'd — possibly itself.

    Split out of same_filesystem because _link_barrier needs the same anchor: a
    destination that does not exist yet still inherits the filesystem, the
    read-only flag and the write permission of the directory it will be created
    in, and asking those three questions of three different paths is how they
    end up disagreeing.
    """
    p = os.path.abspath(path)
    while True:
        try:
            os.stat(p)
            return p
        except OSError:
            parent = os.path.dirname(p)
            if parent == p:
                return p
            p = parent


def _link_barrier(src, dest_root):
    """Why NO link into dest_root can succeed — answered WITHOUT attempting one.

    --check counts what it WOULD do. It never calls os.link, so every cause of a
    link failure was structurally invisible to the one mode documented as
    "report exposure", and --apply was barely better: the DIFFERENT FILESYSTEM
    branch returned before FAILED_LINKS was touched. Measured with a tmpfs
    source (dev=29) and an ext4 archive (dev=66306), 4 files, none archived:

        link_tree  -> (0, 0, 'DIFFERENT FILESYSTEM — hard links impossible here')
        FAILED_LINKS -> []
        run()      -> exit 0
        tick()     -> {'retention': 'ok'}

    These are the causes that can be READ rather than provoked, and they are the
    ones link_tree's own comment names as reachable: a whole filesystem away, an
    ext4 error-remount-ro, and an archive directory that cannot be written (which
    os.makedirs(exist_ok=True) turned into an uncaught PermissionError out of the
    middle of the walk).

    A probe link is deliberately NOT how this is answered. That would mean
    creating a name in the archive and then removing it, and nothing in this file
    removes anything.
    """
    if not same_filesystem(src, dest_root):
        return "DIFFERENT FILESYSTEM — hard links impossible here"
    anchor = _nearest_existing(dest_root)
    try:
        if os.statvfs(anchor).f_flag & os.ST_RDONLY:
            return "READ-ONLY FILESYSTEM — the archive cannot be written"
    except (OSError, AttributeError, ValueError):
        pass          # no statvfs on Windows. Not knowing is not the same as broken.
    if not os.access(anchor, os.W_OK | os.X_OK):
        return f"ARCHIVE NOT WRITABLE ({anchor})"
    return ""


def _same_file(a, b):
    """One inode under two names? NOT "both paths exist".

    lstat, not stat. A hard link duplicates the directory ENTRY, and on Linux
    os.link on a symlink links the symlink itself — ~/.claude-alt/debug/latest
    is one, dangling since February, and its inode carries nlink=3. Following it
    made stat() raise on both sides, so the archived copy read as "not the same
    file", the guard re-linked over a name that already existed, and EEXIST made
    it a FAILED link on every tick forever.
    """
    try:
        sa, sb = os.lstat(a), os.lstat(b)
    except OSError:
        return False
    return (sa.st_dev, sa.st_ino) == (sb.st_dev, sb.st_ino)


def _archive_name(src, dest):
    """Where THIS INODE belongs in the archive, or None if it is already there.

    "ALREADY ARCHIVED" WAS PATH EXISTENCE, NEVER IDENTITY.
    `if os.path.exists(d): skipped += 1` is true of a destination holding the
    file's PREVIOUS inode, and every atomic rename makes a new one — which is
    how ~/.claude.json is written, and ~/.claude.json is the only surviving
    record of 4,062,282,405 tokens whose transcripts are gone. Measured on the
    live archive today, 15,203 destinations already present and 6 of them ghosts:

        ~/.claude.json   live ino=42210401 nlink=1   archive ino=42216256

    nlink=1 is the whole story: the live file is archived NOWHERE, and the guard
    reported it protected on every run since the rewrite.

    The orphan is NEVER touched — it is a real earlier version and this archive
    exists because things do not get deleted. The live inode is linked BESIDE it
    under a name carrying that inode number, which also makes the next run
    idempotent: same inode, same name, already there, skipped. The daemon ticks
    every 6h, so a file rewritten all day costs at most 4 archived versions —
    ~/.claude.json is 161,203 bytes, so ~630 KB a day in the worst case.

    The inode goes BEFORE the extension. `history.jsonl` -> `history.ino42.jsonl`
    keeps the suffix export_corpus tests for; appending it would have hidden the
    record from the corpus instead.
    """
    if not os.path.lexists(dest):
        return dest
    if _same_file(src, dest):
        return None
    try:
        ino = os.lstat(src).st_ino
    except OSError:
        # Deleted between the walk and here — routine for paste-cache. Hand back
        # the plain name and let os.link report it, rather than inventing one.
        return dest
    root, ext = os.path.splitext(dest)
    alt = f"{root}.ino{ino}{ext}"
    return None if _same_file(src, alt) else alt


def _refuse(name, in_secret_dir):
    """Is this file a CREDENTIAL? Not "is it config" — the two are not the same.

    THE RULE IS CALLED, NOT REWRITTEN. `_is_secret` and `secret_dir` are
    imported; nothing here restates what counts as a credential.

    IT ASKS `_is_secret`, NOT `_is_config`, AND THAT IS THE WHOLE POINT.
    The first version of this imported `_is_config`, which is NEVER_EXPORT, and
    NEVER_EXPORT matches `state`. Copilot Chat names its editing-session record
    `state.json`, so importing the exporter's rule wholesale dropped

        ~/.config/Code/.../chatEditingSessions/*/state.json           17 files
        ~/.config/Code - Insiders/.../chatEditingSessions/*/state.json  179
                                                     196 files, 494,067,931 B

    one of which holds `linearHistory` with 369 entries. The exporter is right
    to refuse those: it SHIPS bytes, so anything it cannot vouch for stays out.
    This file ships nothing and deletes nothing, so a refusal here is only ever
    a record that never got a second name. Same question, two callers, two
    correct answers — which is why the split lives in export_corpus beside the
    rule it splits, and not as a fourth private copy here.

    Four live Claude OAuth tokens are the reason the dotted spelling is handled,
    and `_is_secret` handles it:

        ~/.claude/.credentials.json       1,578 B   nlink=1
        ~/.claude-alt/.credentials.json   2,468 B   nlink=1
        ~/.my-claude/.credentials.json    1,927 B   nlink=1
        ~/.claude-it/.credentials.json      466 B   nlink=1

    `name` MAY BE A FULL PATH, and when it is, the symlink test can run. A
    symlink is judged by what it points at because os.link() follows it: the
    second directory entry this program creates lands on the TARGET's inode, so
    `session.jsonl -> credentials.json` gave a credential a name inside the
    archive — measured, at the credential's own inode.

    GUARDED ON `os.sep`, so a bare basename is answered exactly as before. Two
    suites call this with a plain name, and os.path.islink() on a plain name
    resolves it against the CURRENT WORKING DIRECTORY — a test's answer would
    have depended on where the test was run from. link_tree always passes the
    joined path, so the real caller always gets the symlink test.
    """
    if in_secret_dir:
        return True
    return (_is_secret(pathlib.Path(os.path.basename(name)))
            or (os.sep in name and secret_symlink_target(name)))


def _archive_holds(label, cap=5000):
    """How many files the archive already holds under this label.

    Only asked when the SOURCE IS GONE, which is what makes walking it
    affordable: the expensive labels are the ones that are still there.
    Capped, because other/copilot-chat is 4.5 GB and the answer only has to be
    "some" versus "none".
    """
    root = os.path.join(ARCHIVE, label)
    if not os.path.isdir(root):
        return 0
    n = 0
    for _d, _dn, files in os.walk(root):
        n += len(files)
        if n >= cap:
            return cap
    return n


def link_tree(src, label, apply, top_only=False, records=None):
    """Hard-link files under src into ARCHIVE/label, preserving layout.

    top_only stops at the root: it takes the loose files a tool keeps beside its
    program directories, without dragging those directories in.

    `records` is an ALLOW-LIST of fnmatch globs, relative to src — the store
    saying which of its loose files ARE the records. None means the store has
    not said, and the default is unchanged: keep it. () means it said "none of
    them", which is a different sentence and is honoured as one.

    IT RUNS AFTER `_refuse`, NOT BEFORE, AND THE ORDER IS THE REPORT. A file has
    to pass both to be linked, so the order cannot change WHAT is archived —
    only which line of --check it appears on. Put the allow-list first and a
    credential is dropped anonymously, REFUSED_CONFIG goes empty, and the run
    where a NEW credential shows up in a tool's root reads exactly like the run
    before it. Refuse-then-narrow keeps the credential named.
    """
    # A store is not always a directory. ~/.ollama/history is a 4,422-byte FILE
    # and `not isdir` returned "absent" — which run() suppresses entirely, so
    # "installed and unprotected" printed identically to "not installed".
    # Confirmed: link_tree returned (0, 0, 'absent') and `grep -ci ollama` over
    # the live log returned 0. `only` is load-bearing: without it the file case
    # degenerates into top_only over ~/.ollama and links whatever else is there,
    # including id_ed25519.
    #
    # WHAT `only` MAY SKIP, AND WHAT IT MAY NOT. It skips the two tests that ask
    # "which of these loose files is the record" — the name whitelist and the
    # store's records glob — because a path that names ONE FILE has already
    # answered that question by naming it. It does NOT skip the credential test:
    # "this named file is a record" is not a reason to stop asking "is this
    # named file an OAuth token". Nothing about naming a path makes a secret
    # safe to give a second name to. Three shipped store paths land on this
    # branch today — `.claude.json`, `.ollama/history`, `.proteus/.claude.json`,
    # the last of them added hours ago — and a fourth is one line of stores.py
    # away. `.copilot/mcp-secrets/gh.json` written there would arrive here with
    # every credential test switched off, including the directory one: `only`
    # makes src the file's PARENT, so `mcp-secrets` is not in any `rel`.
    only = None
    if os.path.isfile(src):
        src, only, top_only = os.path.dirname(src), os.path.basename(src), True
    # AND EVERY COMPONENT AT OR ABOVE THE WALK ROOT, not just the one the line
    # above chopped off. The per-component SECRET_DIRS test below runs over
    # paths RELATIVE to src, so nothing at or above src appears in any rel —
    # ~/.copilot/mcp-secrets/gh.json is walked with rel "." and in_secret_dir
    # False. Asking `secret_dir(basename(src))` covered exactly one level, and
    # one subdirectory was a bypass:
    #
    #     .copilot/mcp-secrets/gh.json            parent 'mcp-secrets'  refused
    #     .copilot/mcp-secrets/sub/history.jsonl  parent 'sub'          ARCHIVED
    #
    # Asked on the DIRECTORY branch too. It used to be assigned only inside the
    # isfile() arm above, so a store whose path names a directory carried the
    # `False` initialiser through the whole walk and the ancestry rule was off
    # for every recursive store — the ones that go deep enough to reach a
    # credential in the first place.
    #
    # TWO TESTS, OR-ED, AND THE FIRST ONE IS NOT REDUNDANT. secret_ancestor()
    # bounds its walk at HOME and states why there — but link_tree is also
    # called with roots that are not under HOME at all (the archive tree, an
    # OTHER_SOURCES root, a store path handed in directly), and outside HOME it
    # answers False because nothing above the user is ours to judge. Dropping
    # the immediate-parent test in favour of it made this rule NARROWER than the
    # line it replaced for exactly those paths: `.copilot/MCP-Secrets/gh.json`
    # under a root outside HOME went from refused to archived, and four checks
    # that were green went red.
    #
    # So the shipped test stays, unconditional, and the ancestry test is added
    # on top. This can only ever refuse MORE than the line it replaced, never
    # less, which is the only direction a credential rule is allowed to move.
    only_dir_secret = (secret_dir(os.path.basename(src))
                       or secret_ancestor(src, HOME))
    if not os.path.isdir(src):
        # "ABSENT" WAS TWO DIFFERENT FACTS SHARING ONE WORD, AND run() PRINTS
        # NEITHER. A tool that was never installed and a tool whose store the
        # belt used to catch and no longer can both returned (0, 0, 'absent')
        # with FAILED_LINKS empty, so the run where a store stopped being
        # protected is byte-identical to every run before it.
        #
        # The archive is what tells them apart, and it is the only thing that
        # can: this program never deletes, so files under other/<label> are
        # proof the store existed and was being caught. Source gone + archive
        # holding its history = the belt stopped catching it.
        #
        # It is NOT a FAILED_LINK. Uninstalling a tool is allowed, and an alarm
        # that fires forever over a tool nobody has any more is the alarm people
        # learn to skip — which costs the real one its meaning. Named, counted,
        # and not counted as failure.
        held = _archive_holds(label)
        if held:
            VANISHED.append((label, src, held))
            return 0, 0, (f"SOURCE GONE — the archive holds "
                          f"{held}{'+' if held >= 5000 else ''} file(s) this "
                          f"store no longer has; nothing new can be caught")
        return 0, 0, "absent"
    dest_root = os.path.join(ARCHIVE, label)
    barrier = _link_barrier(src, dest_root)
    if barrier:
        # Copying 581 MB while claiming to be a zero-cost link would be a lie
        # about what this does. Report instead.
        #
        # The check comes BEFORE makedirs. Creating dest_root first left an
        # empty look-alike skeleton in the archive for a profile nothing could
        # ever link into — a directory that exists and holds nothing reads like
        # a profile with no history.
        #
        # AND IT GOES THROUGH FAILED_LINKS. This branch returned straight to the
        # caller, so a store a whole filesystem away was not a failed store: 0 of
        # 4 files archived across a mount boundary, FAILED_LINKS empty, run()
        # exit 0, tick() {'retention': 'ok'}. A dead belt reporting healthy is
        # the exact failure the rest of this function was already written for.
        FAILED_LINKS.append(f"{label}: {barrier}")
        return 0, 0, barrier
    os.makedirs(dest_root, exist_ok=True)
    # A FAILED LINK IS NOT A SKIPPED ONE. They shared one counter and the note
    # was hardcoded "ok", so:
    #     every link fails  -> (0, 5, 'ok')   archive holds 0 files
    #     fully caught up   -> (0, 5, 'ok')   archive holds 5 files
    # byte-identical, and run() then printed "0 file(s) linked — 0 bytes either
    # way", the exact wording of a healthy idle tick. The belt layer could be
    # entirely gone with nothing to say so.
    #
    # Reachable, not hypothetical: protected_hardlinks=1 makes any file not
    # owned by this user fail permanently; an ext4 error-remount-ro routes every
    # link here; and os.makedirs(exist_ok=True) swallows EROFS rather than
    # raising. ENOENT also lands here routinely when Claude Code deletes a
    # paste-cache file between the walk and the link, which is why the count is
    # reported rather than treated as fatal.
    linked = skipped = failed = 0
    last_err = None
    # os.walk's default onerror is None, which means "discard the exception and
    # carry on" — a directory this user cannot read (one chmod 700 project) is
    # not walked, its files are never linked, and the walk finishes with no sign
    # anything was missed. (1, 0, "ok") for a tree that was half read is the
    # same tuple as (1, 0, "ok") for a tree that was fully read.
    walk_errs = []
    for dirpath, dnames, files in os.walk(src, onerror=walk_errs.append):
        if top_only:
            dnames[:] = []          # do not descend: root-level files only
        rel = os.path.relpath(dirpath, src)
        out = os.path.join(dest_root, rel) if rel != "." else dest_root
        # SECRET_DIRS is a test on the DIRECTORY components, and it is the same
        # set export_corpus applies at every depth. GitHub's own Copilot CLI
        # reference puts mcp-secrets/ and mcp-oauth-config/ inside ~/.copilot,
        # beside the session state — so descending into a tool's store and
        # taking everything reaches them, and a root-only rule never can.
        #
        # ASKED PER COMPONENT, NORMALISED — `set(...) & SECRET_DIRS` was an
        # exact, case-sensitive, dot-sensitive intersection, so of
        #
        #     mcp-secrets/gh.json   refused
        #     MCP-Secrets/gh.json   ARCHIVED
        #     Credentials/gh.json   ARCHIVED
        #     .credentials/gh.json  ARCHIVED
        #
        # only the first spelling was caught. Two of the five machines run
        # case-insensitive filesystems, where those are not four directories —
        # they are one directory whose stored spelling happens to differ.
        in_secret_dir = (any(secret_dir(p) for p in rel.split(os.sep))
                         if rel != "." else False) or only_dir_secret
        for f in files:
            if only is not None and f != only:
                continue
            s = os.path.join(dirpath, f)
            shown = f if rel == "." else os.path.join(rel, f)
            # A root_files store exists to catch the records a tool leaves LOOSE
            # beside its program directories — proteus writes history.jsonl
            # straight into ~/.proteus. Taking every root file instead takes the
            # tool's config with it, and config is where credentials live.
            # Measured before this line existed: 48 live root files, 8 records
            # and 40 config, and 39 of those config files already hard-linked
            # into the archive at the SAME INODE as the live original —
            # including ~/.gemini/oauth_creds.json (access_token, refresh_token,
            # id_token) and ~/.devvit/token.
            #
            # AND IT APPLIES AT EVERY DEPTH, TO EVERY STORE. Gated on `top_only`
            # it covered the 10 root_files stores and none of the 39 conversation
            # stores, which are the ones walked recursively — the depth a
            # credential actually sits at. A conversation store holding
            # proj/oauth_creds.json, proj/.credentials.json and
            # proj/mcp-secrets/gh.json linked all three at the live inode and
            # reported (4, 0, 'ok') with REFUSED_CONFIG empty.
            #
            # AND `only` DOES NOT EXEMPT ANYTHING FROM THIS ONE. It used to:
            # the test read `only is None and _refuse(...)`, so a store whose
            # path named one file had the credential test switched off entirely
            # — the single case where the store map, not a filesystem walk,
            # chooses the file, so the only thing standing between a credential
            # and the archive was that nobody had yet written its path down.
            #
            # The defence for `only is None` was real and it is kept — two lines
            # down, where it belongs. A store whose path names ONE FILE names it
            # because that file IS the record (~/.ollama/history, and
            # ~/.claude.json, the last surviving evidence of 4,062,282,405
            # tokens), so the tests that ask WHICH loose file is the record do
            # not get to overrule it. That says nothing about whether the named
            # file is a credential, and the two questions were sharing one flag.
            # Neither of those two files is a secret by any spelling —
            # `_is_secret` matches oauth_creds, credentials, auth, token,
            # session-id, installation_id, netrc, id_rsa/id_ed25519 — so both
            # still archive, and `id_ed25519` named by a store's path no longer
            # walks straight past the check written to catch it.
            # `s`, NOT `f` — the FULL path, so _refuse can see that this entry
            # is a symlink and ask what it points at. os.link() below follows
            # it, so the name that gets archived and the name that was tested
            # were two different files. _refuse takes the basename itself, so
            # every name-based answer is unchanged.
            if _refuse(s, in_secret_dir):
                prior = os.path.join(out, f)
                REFUSED_CONFIG.append((label, shown, _same_file(s, prior)))
                continue
            # AND THE STORE'S OWN ALLOW-LIST, WHERE IT HAS ONE.
            #
            # `only is None` is load-bearing HERE, and on the whitelist below,
            # and nowhere else — this is a test of WHICH loose file is the
            # record: a store whose path names ONE FILE names it because
            # that file IS the record — ~/.ollama/history, ~/.claude.json — and
            # a list of "which of these loose files is history" was never
            # written for it. Those two have no records tuple today, and if one
            # ever gains one it must not be able to filter out the single file
            # the store exists for.
            # stores.matches_records, not a second fnmatch loop written here.
            # `Store.is_record` is the same call. Two spellings of one rule is
            # how this repository shipped one defect four times.
            if only is None and not stores.matches_records(shown, records):
                NOT_A_RECORD.append((label, shown))
                continue
            # AND THE WHITELIST DOES NOT DECIDE. `_is_loose_record` answers
            # "is this name one of the names we know records by" — history,
            # conversation, chat, thread, message, transcript, prompt, .jsonl.
            # Used as an admission gate it dropped ~/.copilot/session-store.db:
            # 1,822,720 bytes, 38 sessions and 370 turns by read-only sqlite,
            # already archived at nlink=3 — while admitting
            # conversation_summaries.db-shm (32 KB) and .db-wal (0 B), which
            # carry no record at all and got in because their SIBLING is named
            # for a conversation.
            #
            # The exporter is right to whitelist: it ships bytes into a public
            # corpus, so anything it cannot vouch for stays out. The archiver
            # ships nothing. A hard link costs 0 bytes and nothing here ever
            # deletes, so the two mistakes are not symmetric: keeping a file
            # that is not a record costs nothing, and dropping one that is
            # costs the only copy. So the refusal is the config/secret test
            # above, and the whitelist only decides what gets NAMED.
            if top_only and only is None and not _is_loose_record(pathlib.Path(f)):
                UNRECOGNISED.append((label, shown))
            d = _archive_name(s, os.path.join(out, f))
            if d is None:
                skipped += 1
                continue
            if os.path.basename(d) != f:
                # The archived copy is a DIFFERENT inode, so the live file is
                # archived nowhere. Recorded in both modes: --check exists to
                # report exposure, and this is exposure.
                GHOSTS.append(s)
            if not apply:
                linked += 1
                continue
            try:
                os.makedirs(out, exist_ok=True)
                os.link(s, d)
                linked += 1
            except OSError as e:
                # A DANGLING SYMLINK IS NOT A FAILED LINK. os.link follows the
                # symlink to its target; if the target is gone os.link raises
                # ENOENT. _same_file uses lstat (does not follow) so it already
                # found the inode and decided this was a new copy to make. The
                # right answer is: skip it, nothing to link. It is not a belt
                # failure — the source path exists as a name on disk, just not
                # as bytes. Counted as a failure it would fire on every tick
                # forever for any dangling symlink in any Claude project dir.
                import errno as _errno
                if e.errno == _errno.ENOENT and os.path.islink(s):
                    skipped += 1
                else:
                    failed += 1
                    last_err = e
    parts = []
    if failed:
        parts.append(f"{failed} FAILED ({last_err.strerror})")
    if walk_errs:
        parts.append(f"{len(walk_errs)} UNREADABLE ({walk_errs[-1].strerror}: "
                     f"{os.path.basename(walk_errs[-1].filename or '?')})")
    note = "; ".join(parts) or "ok"
    if note != "ok":
        FAILED_LINKS.append(f"{label}: {note}")
    return linked, skipped, note


def run(apply):
    FAILED_LINKS.clear()
    GHOSTS.clear()
    REFUSED_CONFIG.clear()
    UNRECOGNISED.clear()
    NOT_A_RECORD.clear()
    VANISHED.clear()
    log(f"{'APPLYING' if apply else 'CHECK ONLY — nothing will change'}")
    print()
    profiles = claude_profiles()
    # Two categories, because they need different things:
    #   live  — has settings.json, so Claude Code launches here and SWEEPS here.
    #           These get the period raised.
    #   copy  — a profile-shaped directory with no settings.json. Claude Code
    #           never launches it, so nothing deletes it; raising a period on a
    #           file that does not exist would be theatre. Archived, not defended.
    live = [p for p in profiles if os.path.exists(os.path.join(p, "settings.json"))]
    copies = [p for p in profiles if p not in live]
    print(f"  CLAUDE PROFILES — {len(live)} live, {len(copies)} copies "
          f"(only Claude Code deletes)")
    for prof in live:
        root = os.path.join(prof, "projects")
        age = oldest_age_days(root) if os.path.isdir(root) else None
        cur = current_period(prof)
        at_risk = age is not None and age > cur
        changed, msg = raise_period(prof, apply)
        flag = "  AT RISK" if at_risk and not (apply and changed) else ""
        shown = f"{age}d" if age is not None else "-"
        label = prof.replace(HOME, "~")
        if len(label) > 40:
            label = "~/..." + label[-36:]
        print(f"    {label:<40} oldest {shown:<7} period {cur:<7} {msg}{flag}")

    win = windows_side_profiles()
    if win:
        print()
        print("  WSL DETECTED — Claude profiles on the WINDOWS side, NOT protected here:")
        for w in win:
            per = "?"
            sp = os.path.join(w, "settings.json")
            if os.path.exists(sp):
                try:
                    per = json.load(open(sp)).get("cleanupPeriodDays", 30)
                except Exception:  # noqa: BLE001
                    per = "unreadable"
            print(f"      {w}   cleanupPeriodDays={per}")
        print("      WSL and Windows have separate homes and separate installs.")
        print("      Run this script in PowerShell on that side too:")
        print("        python retention_guard.py --apply")

    if copies:
        print(f"    + {len(copies)} copy/copies with no settings.json — nothing "
              "launches them, so nothing sweeps them; archived below")
        for c in copies[:4]:
            print(f"      {c.replace(HOME, '~')}")
        if len(copies) > 4:
            print(f"      ... and {len(copies) - 4} more")
    print()
    print("  HARD-LINK ARCHIVE  ->  " + ARCHIVE)
    total_new = 0
    for prof in profiles:
        # Every path Claude sweeps, not only projects/. The first version linked
        # projects/ alone and left twelve other categories exposed, including
        # file-history (pre-edit snapshots) and plans/.
        pn = pk = 0
        covered = []
        # THE NOTE WAS READ ONLY FOR "absent" AND OTHERWISE THROWN AWAY —
        # for Claude profiles, the one thing on this machine that deletes.
        # So "DIFFERENT FILESYSTEM" and every link failure printed nothing here,
        # while the loops below (for tools that delete nothing) printed both.
        # A subdirectory that could not be linked was still appended to
        # `covered`, which is the word "covered" meaning its opposite.
        bad = []
        for sub in CLAUDE_CLEANED:
            n, sk, note = link_tree(os.path.join(prof, sub),
                                    f"claude/{_archive_key(prof)}/{sub}", apply)
            if note == "absent":
                continue
            if note.startswith("SOURCE GONE"):
                # Not "NOT ARCHIVED" — it WAS archived, and the live directory
                # is the thing that went. VANISHED prints it in those words.
                continue
            if note != "ok":
                bad.append(f"{sub}: {note}")
            else:
                covered.append(sub)
            pn += n
            pk += sk
        # AND THE PROFILE ROOT ITSELF. top_only, so the swept subdirectories
        # above are not walked a second time, and `records` so this takes the
        # two loose records and not .credentials.json / .claude.json / the
        # settings files sitting beside them. `src` is a directory, so `only`
        # stays None and both the allow-list and the loose-record whitelist
        # apply — which is the difference between this and pointing a store at
        # `.*claude*`.
        n, sk, note = link_tree(prof, f"claude/{_archive_key(prof)}", apply,
                                top_only=True, records=CLAUDE_PROFILE_RECORDS)
        if note == "absent":
            # NOT `continue`. Everywhere else "absent" means a tool nobody
            # installed and is rightly suppressed; here the path came from
            # claude_profiles(), which only returns it because projects/ exists
            # under it. Absent means it went between that call and this one, and
            # a profile disappearing mid-run is a fault, not a quiet zero.
            bad.append("<root>: absent — profile vanished mid-run")
        elif note != "ok":
            bad.append(f"<root>: {note}")
        else:
            covered.append("<root>")
        pn += n
        pk += sk
        total_new += pn
        if covered or bad:
            lab = prof.replace(HOME, "~")
            if len(lab) > 34:
                lab = "~/..." + lab[-30:]
            print(f"    {lab:<34} {pn:>5} new {pk:>6} already  [{', '.join(covered)}]")
            for b in bad:
                print(f"      !! NOT ARCHIVED  {b}")
    for label, rels in OTHER_SOURCES.items():
        n = sk = 0
        note = "absent"
        for rel in rels:
            a, b, nt = link_tree(os.path.join(HOME, *rel.split("/")),
                                 f"other/{label}", apply)
            n += a
            sk += b
            # "absent" only if EVERY expansion was absent. One present path
            # settles it; a failure on any of them must not be hidden by
            # another that simply was not there.
            if nt != "absent":
                note = nt if note in ("absent", "ok") else note
        total_new += n
        if note != "absent":
            print(f"    {label:<22} {n:>6} new  {sk:>6} already  {note}")
    for label, rels in ROOT_FILE_SOURCES.items():
        n = sk = 0
        note = "absent"
        for rel in rels:
            a, b, nt = link_tree(os.path.join(HOME, *rel.split("/")),
                                 f"other/{label}", apply, top_only=True,
                                 records=ROOT_FILE_RECORDS.get(label))
            n += a
            sk += b
            if nt != "absent":
                note = nt if note in ("absent", "ok") else note
        total_new += n
        # `note != "ok"` belongs in this condition. A store whose every link
        # failed returns n=0 and sk=0, so the old test printed NOTHING for it —
        # quieter than a store that worked. Demonstrated:
        #   link_tree -> n=0 sk=0 note='3 FAILED (Read-only file system)'
        #   condition -> False
        if note != "absent" and (n or sk or note != "ok"):
            # And the note itself, not just the shape of the store. The
            # condition above was fixed to let a total failure through, and then
            # this line printed the constant "root files only" over the top of
            # it — so `3 FAILED (Read-only file system)` reached the screen as
            # the same eleven characters a healthy store prints.
            detail = "root files only" if note == "ok" else f"root files only — {note}"
            print(f"    {label:<22} {n:>6} new  {sk:>6} already  {detail}")
    # Anything session-shaped that no rule above claims. Reported, never linked.
    # A tool nobody configured is exactly the tool whose data goes missing
    # quietly, and printing its name is how it stops being invisible.
    # ROOT_FILE_SOURCES counts as claimed too. Leaving it out reported .devvit
    # and .jules as "not covered" on every single run while both were being
    # linked — and an alarm that is wrong every time is one people stop reading,
    # which costs the real one its meaning.
    known = {os.path.normpath(os.path.join(HOME, *r.split("/")))
             for rels in list(OTHER_SOURCES.values()) + list(ROOT_FILE_SOURCES.values())
             for r in rels}
    known |= set(profiles)
    unknown = []
    for name in sorted(os.listdir(HOME)):
        d = os.path.join(HOME, name)
        if not name.startswith(".") or not os.path.isdir(d) or name in DISCOVER_SKIP:
            continue
        if any(k == d or k.startswith(d + os.sep) for k in known):
            continue
        try:
            hit = any(any(h in sub.lower() for h in DISCOVER_HINTS) for sub in os.listdir(d))
        except OSError:
            continue
        if hit:
            unknown.append(name)
    if unknown:
        print()
        print("  NOT COVERED — session-shaped stores no rule claims:")
        for u in unknown:
            print(f"    {u}")

    print()
    print(f"  {total_new} file(s) {'linked' if apply else 'would be linked'} — 0 bytes either way")
    if GHOSTS:
        print(f"  {len(GHOSTS)} file(s) had an archived copy at a DIFFERENT inode"
              f" — {'re-linked' if apply else 'would be re-linked'} beside it, "
              f"the older inode kept")
        for g in GHOSTS[:4]:
            print(f"    {g.replace(HOME, '~')}")
        if len(GHOSTS) > 4:
            print(f"    ... and {len(GHOSTS) - 4} more")
    # TWO DIFFERENT REFUSALS, TWO DIFFERENT LINES. They shared one, and the
    # line read "config/credential file(s) refused" over a list whose bulk was
    # ADVISOR.md, cli.log, GEMINI.md and last_check.timestamp. Calling a
    # markdown doc a credential is how the two files that ARE credentials —
    # ~/.gemini/oauth_creds.json and ~/.devvit/token — got read past.
    if REFUSED_CONFIG:
        # NAMED, because the rule arriving late does not un-link what it already
        # linked. 39 config files are in the archive at the same inode as the
        # live original, two of them live credentials, and nothing in this file
        # deletes anything — so the only thing it can do about them is stop them
        # being invisible.
        counts = {}
        for _lbl, n, _p in REFUSED_CONFIG:
            counts[os.path.basename(n)] = counts.get(os.path.basename(n), 0) + 1
        print(f"  {len(REFUSED_CONFIG)} config/credential file(s) REFUSED — "
              f"never linked, at any depth, in any store")
        # And the names. 200 of these were being linked out of the recursive
        # stores and not one was printed, so the fix had to be reasoned about
        # from a filesystem walk rather than from the tool's own output.
        #
        # The cap is 12 and not 8 because 8 was measured and was not enough:
        # `state.json x197` out of copilot-chat's workspaceStorage crowded
        # oauth_creds.json and token off the bottom of the list, and those two
        # are the entire reason this list exists. 12 shows every distinct name
        # on this machine.
        for name, c in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:12]:
            print(f"      {name}" + (f"  x{c}" if c > 1 else ""))
        if len(counts) > 12:
            print(f"      ... and {len(counts) - 12} more distinct name(s)")
        prior = [f"{lbl}/{n}" for lbl, n, p in REFUSED_CONFIG if p]
        if prior:
            print(f"    {len(prior)} of them are ALREADY in the archive from "
                  f"before this rule, at the SAME INODE as the live original:")
            for p in prior[:6]:
                print(f"      {p}")
            if len(prior) > 6:
                print(f"      ... and {len(prior) - 6} more")
            print("    nothing here deletes them — move them out yourself.")
    if UNRECOGNISED:
        # ARCHIVED, and said out loud. This is not a refusal and must never be
        # printed as one: ~/.copilot/session-store.db is 1,822,720 bytes holding
        # 38 sessions and 370 turns, and it lands here because no rule knows the
        # name, not because there is anything wrong with it.
        print(f"  {len(UNRECOGNISED)} loose root file(s) ARCHIVED whose name is "
              f"not a known record name — kept, because a name nobody "
              f"recognises is not a reason to lose a record")
        for lbl, n in UNRECOGNISED[:6]:
            print(f"      {lbl}/{n}")
        if len(UNRECOGNISED) > 6:
            print(f"      ... and {len(UNRECOGNISED) - 6} more")
    if NOT_A_RECORD:
        # A THIRD LINE, BECAUSE IT IS A THIRD FACT — and the only one of the
        # three that costs something. REFUSED_CONFIG is "a credential, never
        # linked". UNRECOGNISED is "linked anyway, name unknown". This is
        # "NOT linked, because the store wrote down what its records are and
        # this is not one of them" — the one narrowing in a program whose whole
        # doctrine is that a link costs 0 bytes and a missed record is
        # permanent. Printed in full, every run, with the store that decided
        # it, so the day one of these turns out to have been a record there is
        # a name to point at instead of a silence. `records=()` on a store is
        # how a whole tool's root ends up here.
        print(f"  {len(NOT_A_RECORD)} loose root file(s) NOT ARCHIVED — the "
              f"store names its records and these are not among them")
        for lbl, n in NOT_A_RECORD[:12]:
            print(f"      {lbl}/{n}")
        if len(NOT_A_RECORD) > 12:
            print(f"      ... and {len(NOT_A_RECORD) - 12} more")
    if VANISHED:
        # The run where the belt stopped catching a store used to be
        # byte-identical to every run before it.
        print(f"  {len(VANISHED)} store(s) the belt USED TO catch and cannot "
              f"any more — the source is gone, the archive still holds it:")
        for lbl, p, held in VANISHED[:6]:
            print(f"      {lbl:<22} {p.replace(HOME, '~')}  ({held} archived)")
        if len(VANISHED) > 6:
            print(f"      ... and {len(VANISHED) - 6} more")
        print("    not a failure — a tool can be uninstalled. It is only "
              "invisible that it must not be.")
    if FAILED_LINKS:
        print(f"  {len(FAILED_LINKS)} store(s) could NOT be archived: "
              f"{', '.join(FAILED_LINKS[:4])}")
    if not apply:
        # WHAT --check DID NOT CHECK. It never calls os.link, so the count above
        # is what WOULD happen, and the only link failures it can report are the
        # barriers _link_barrier can read without attempting one. Saying "0
        # failures" about links nobody tried is the same sentence a healthy run
        # prints, which is the defect this whole file keeps having.
        print("\n  --check attempts no link: the count above is what WOULD "
              "happen, and only\n  a barrier no link could cross is verified. "
              "Run with --apply to make it real.")
    # THE OUTCOME, not a constant. tick() hardcoded out["retention"] = "ok"
    # regardless of what happened here — replacing run() with a no-op that
    # archives nothing still reported {'retention': 'ok'}. So the belt could be
    # entirely dead and the daemon would log healthy every six hours forever.
    return 1 if FAILED_LINKS else 0


def record_ledger(apply=True, _home=None):
    """Append this machine's per-session token counts to the append-only ledger.

    `_home` is injectable for tests only — it is passed as `--home` to the
    sessions.py subprocess so the scan runs over a small fixture directory rather
    than the real home. Production callers never set it; its name signals that.

    The third layer, and the only one that survives BOTH failures at once. The
    box (cleanupPeriodDays) can be reset by an update. The belt (hard links)
    needs the archive to still be there. The ledger needs neither: once a
    session's number is written down it is a fact on disk, and nothing that
    happens to the transcript afterwards can change it.

    It belongs in the daemon rather than in `run.py update` because the daemon
    is what runs unattended. A number that is only recorded when somebody
    remembers to run a scan is not a lifetime record, it is a snapshot with
    extra steps.

    Advisory, like every other layer here: a ledger that raises stops the guard
    from guarding, which is a strictly worse trade than a ledger that skips one
    tick and says so.

    IT HAS TO SCAN, AND IT DID NOT. record() diffs the ledger against
    machine-readable/sessions.json, and nothing here writes that file —
    sessions.py is its only writer, reached only through `run.py update`. Handed
    a folder whose sessions.json held one invented session, the old code
    reported:

        FAIL  the ledger job SCANNED rather than re-reading the stale file
              got: TOKEN LEDGER  +1 observation(s); lifetime 42 across 1 session(s)

    A lifetime of 42 tokens, printed in the same shape as a real one.

    The scan goes to a SCRATCH directory, never the machine folder: writing
    sessions.json there leaves it newer than totals.json, tripping the fatal
    cross-check in check_consistency.py, and dirties git every six hours. It
    costs about half a minute out of every 21,600.

    Returns (outcome, message), because tick() assigned "ok" to any string this
    returned — including the "no machine folder" skip:

        FAIL  a skipped ledger is NOT reported as ok
              got 'ok' for a job that did nothing
    """
    import pathlib
    import subprocess
    import tempfile
    root = pathlib.Path(os.path.dirname(os.path.realpath(__file__)))
    try:
        import token_ledger
        mdir = token_ledger.this_machine(root)
        if not mdir:
            return "skipped", "  TOKEN LEDGER  no machine folder for this host — skipped"
        if not apply:
            # A dry run must not spend 30 seconds scanning, and must not append.
            # It reports what it WOULD do — "dry" is a distinct outcome from
            # "ok", so a caller cannot mistake a rehearsal for a recording.
            lt = token_ledger.lifetime(mdir)
            return "dry", (f"  TOKEN LEDGER  dry run — would scan and record; "
                           f"lifetime stands at {lt['total']:,}")

        with tempfile.TemporaryDirectory(prefix="ledger-scan-") as td:
            cmd = [sys.executable, "sessions.py", "--out", td, "--label", mdir.name]
            if _home is not None:
                cmd += ["--home", str(_home)]
            r = subprocess.run(
                cmd, cwd=str(root), capture_output=True, text=True, timeout=1800)
            fresh = paths.find(pathlib.Path(td), "sessions.json")
            if r.returncode != 0 or not fresh:
                # Record from the last scan on disk rather than nothing — but SAY
                # the figure is stale, instead of printing the same healthy line
                # either way, which is the whole defect above.
                tail = (r.stderr or r.stdout or "").strip().splitlines()
                why = tail[-1][:70] if tail else f"exit {r.returncode}"
                n, _seen, _note = token_ledger.record(mdir)
                lt = token_ledger.lifetime(mdir)
                return "stale", (f"  TOKEN LEDGER  SCAN FAILED ({why}) — recorded +{n} "
                                 f"from the last scan on disk; lifetime {lt['total']:,}")
            scan_dir = pathlib.Path(td)
            n, seen_n, _note = token_ledger.record(mdir, scan_dir=scan_dir)
            lt = token_ledger.lifetime(mdir)
            seen, _ = token_ledger.observe(mdir, scan_dir)
            gone = lt["total"] - sum(int(x.get("total") or 0) for x in seen.values())
            held = (f", {gone:,} of it from transcripts that no longer exist"
                    if gone > 0 else "")
            return "ok", (f"  TOKEN LEDGER  scanned {seen_n} session(s), +{n} new; "
                          f"lifetime {lt['total']:,} across "
                          f"{lt['sessions']:,} session(s){held}")
    except Exception as e:  # noqa: BLE001 - never let the ledger stop the guard
        return "error", f"  TOKEN LEDGER  skipped ({type(e).__name__}: {e})"


# ONE DAEMON, THREE JOBS, AND NONE MAY TAKE THE OTHERS DOWN.
#
# They belong in one process — they run on the same schedule, over the same
# files, and three services would triple the ways this stops running silently.
# But they are independent jobs, each in its own try block.
#
# Job 1 — sync:       git pull + run.py update + commit own folder + push
#                     + rebuild root reports.  Implemented in sync_job.py.
# Job 2 — retention:  raise cleanupPeriodDays + hard-link archive.
# Job 3 — ledger:     append per-session token counts to token_ledger.jsonl.
#
# Demonstrated, not theorised — with run() raising RuntimeError("disk full"),
# record_ledger() was never called when they shared a try block. A retention
# failure silently stopped the lifetime record, and the log said only
# "ERROR: disk full", which reads like one thing went wrong rather than two.
#
# Each job is now attempted on its own, and each can be switched off without
# touching the other. Off is announced on every tick: a job that is disabled
# must not look like a job that is working.
#
# Disable env vars:
#   RETENTION_GUARD_SYNC=0       skip Job 1 (repo sync)
#   RETENTION_GUARD_RETENTION=0  skip Job 2 (retention guard)
#   RETENTION_GUARD_LEDGER=0     skip Job 3 (lifetime ledger)
JOBS = ("sync", "retention", "ledger")

# DID IT COME BACK? — recorded, not remembered.
#
# `Restart=always` was proven by SIGKILL. Surviving a REBOOT is a different
# claim and could not be checked at all: this machine last booted 33 days
# before the service existed, so the enablement and Linger=yes had never once
# been exercised.
#
# It cannot be checked afterwards from memory either — a reboot ends whatever
# was watching. So the daemon writes down that it started, stamped with the
# kernel's boot_id, which is a fresh random value on every boot and is the one
# thing that cannot be faked by a process claiming to have restarted.
#
# Then the question becomes arithmetic instead of recollection: is there a
# record for the boot_id the machine is running under right now, and how many
# seconds after boot did it appear.
BOOTLOG = os.path.join(HOME, ".local", "share", "retention_guard.boots.jsonl")


def _sh(cmd):
    """Run a command, return stdout or "" — never raise, never block forever."""
    import subprocess
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:  # noqa: BLE001
        return ""


def _remediation(what):
    """What to run when --verify-boot FAILS, for THIS platform.

    The failure paths printed `systemctl` and `journalctl` unconditionally. The
    launchctl and schtasks equivalents existed, but only inside the "cannot read
    /proc" branch — which is now unreachable off Linux, because _boot_id() was
    taught to use kern.bootsessionuuid and LastBootUpTime. Fixing that branch
    stranded the only platform-aware help behind it, so a real FAIL on a Mac
    printed four Linux commands that do not exist there.

    `what` is "running" (it started and died) or "enabled" (it never started).
    """
    import platform
    s = platform.system()
    if s == "Darwin":
        if what == "running":
            return ["check: launchctl list | grep retention-guard",
                    "       log show --predicate 'process == \"python3\"' --last 1h"]
        return ["check: launchctl list | grep retention-guard",
                "       ls ~/Library/LaunchAgents/com.tokenusage.retention-guard.plist"]
    if s == "Windows":
        if what == "running":
            return ["check: Get-ScheduledTask retention-guard | Get-ScheduledTaskInfo",
                    "       Get-Process python -ErrorAction SilentlyContinue"]
        return ["check: Get-ScheduledTask retention-guard",
                "       schtasks /query /tn retention-guard /v"]
    if what == "running":
        return ["check: systemctl --user is-active retention-guard.service",
                "       journalctl --user -u retention-guard.service -n 50"]
    return ["check: systemctl --user is-enabled retention-guard.service",
            "       loginctl show-user $USER --property=Linger"]


def _boot_id():
    """A value that changes on every boot and cannot be forged by a restart.

    Linux has one directly. macOS and Windows do not, so the boot TIME stands in
    for it — it is equally unique per boot, which is the only property this
    needs. Returning "" on a platform we cannot read was worse than useless:
    every record carried "" too, so `"" in seen` was permanently true and
    --verify-boot printed PASS forever on a machine it could not observe.
    """
    import platform
    sysname = platform.system()
    if sysname == "Linux":
        try:
            with open("/proc/sys/kernel/random/boot_id") as fh:
                return fh.read().strip()
        except OSError:
            pass
    if sysname == "Darwin":
        # kern.bootsessionuuid is exactly this; kern.boottime is the fallback.
        v = _sh(["sysctl", "-n", "kern.bootsessionuuid"])
        if v:
            return v
        v = _sh(["sysctl", "-n", "kern.boottime"])
        if v:
            return "boottime:" + v.replace(" ", "")
    if sysname == "Windows":
        v = _sh(["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToString('o')"])
        if v:
            return "boottime:" + v
    bt = _boot_time()
    return f"boottime:{bt}" if bt else ""


def _alive(pid):
    """Is that pid a RUNNING retention guard?

    Checking `/proc/<pid>` alone is wrong — pids are reused, and after a few
    weeks of uptime the number in an old boot record very plausibly belongs to
    something else. The cmdline is what makes it this daemon rather than
    whatever inherited its number.
    """
    if not pid:
        return False
    import platform
    sysname = platform.system()
    try:
        pid = int(pid)
    except (ValueError, TypeError):
        return False
    if sysname == "Linux":
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as fh:
                return b"retention_guard" in fh.read()
        except OSError:
            return False
    if sysname == "Darwin":
        # ps prints the full command line; -o command= suppresses the header.
        return "retention_guard" in _sh(["ps", "-p", str(pid), "-o", "command="])
    if sysname == "Windows":
        out = _sh(["powershell", "-NoProfile", "-Command",
                   f"(Get-CimInstance Win32_Process -Filter 'ProcessId={pid}').CommandLine"])
        return "retention_guard" in out
    return False


def _boot_time():
    """Seconds since epoch when this machine booted. 0 if it cannot be read."""
    import platform, re as _re
    sysname = platform.system()
    if sysname == "Linux":
        try:
            with open("/proc/stat") as fh:
                for line in fh:
                    if line.startswith("btime "):
                        return int(line.split()[1])
        except OSError:
            pass
        try:
            return int(time.time() - float(open("/proc/uptime").read().split()[0]))
        except OSError:
            return 0
    if sysname == "Darwin":
        # kern.boottime prints: { sec = 1786250000, usec = 123 } Sat Aug  9 ...
        m = _re.search(r"sec\s*=\s*(\d+)", _sh(["sysctl", "-n", "kern.boottime"]))
        return int(m.group(1)) if m else 0
    if sysname == "Windows":
        v = _sh(["powershell", "-NoProfile", "-Command",
                 "[int](Get-Date (Get-CimInstance Win32_OperatingSystem)."
                 "LastBootUpTime -UFormat %s)"])
        try:
            return int(v)
        except ValueError:
            return 0
    return 0


def note_start():
    """Append one line saying the daemon came up under this boot."""
    bid, bt = _boot_id(), _boot_time()
    row = {"boot_id": bid, "boot_time": bt, "started": int(time.time()),
           "delay_s": max(0, int(time.time()) - bt) if bt else None,
           "pid": os.getpid()}
    try:
        os.makedirs(os.path.dirname(BOOTLOG), exist_ok=True)
        with open(BOOTLOG, "a") as fh:
            fh.write(json.dumps(row) + "\n")
    except OSError:
        pass
    return row


def verify_boot():
    """Has the daemon started under the boot this machine is running now?

    Prints the whole history, because one success is an anecdote and the point
    of writing it down is to watch it hold across every boot.
    """
    rows = []
    try:
        with open(BOOTLOG) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except Exception:  # noqa: BLE001
                        pass
    except OSError:
        pass

    now_id, now_bt = _boot_id(), _boot_time()
    if not now_id:
        # /proc is Linux. On macOS and Windows _boot_id() returns "" and every
        # record carries "" too, so `"" in seen` is permanently true and this
        # would print PASS forever on a platform it cannot observe at all.
        # "Cannot tell" is a third answer, and it is the honest one.
        print("  cannot read /proc — this check only works on Linux.")
        print("  Ask the service manager instead:")
        print("    launchctl list | grep retention-guard      (macOS)")
        print("    Get-ScheduledTask retention-guard          (Windows)")
        return 2

    # ANY live row for this boot, not the first and not the last.
    #
    # First is wrong: Restart=always means a healthy daemon has several rows per
    # boot and the earliest pid is dead by definition. Last is wrong too, and it
    # produced a FAIL against a demonstrably healthy daemon —
    #
    #     MainPID 2223247 active and running
    #     last boot row: pid 2245983, dead (a stray invocation that exited)
    #     FAIL  it started under this boot but is NOT running now
    #
    # because a second short-lived instance leaves the newest row and buries the
    # real one. The question is not "which row is newest", it is "is any daemon
    # from this boot alive", so all of them are kept and any live pid answers it.
    seen = {}
    for r in rows:
        if r.get("boot_id"):
            seen.setdefault(r["boot_id"], []).append(r)

    print(f"  this boot   {now_id}")
    print(f"  booted      {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now_bt))}"
          f"   ({int((time.time() - now_bt) / 86400)} day(s) ago)")
    print()
    print(f"  {'boot_id':<38}{'daemon started':<22}{'after boot':>12}")
    for bid, rs in seen.items():
        r = rs[-1]
        when = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(r.get("started", 0)))
        d = r.get("delay_s")
        mark = "  <- this boot" if bid == now_id else ""
        print(f"  {str(bid):<38}{when:<22}{(str(d) + 's') if d is not None else '?':>12}{mark}")
    if not seen:
        print("  (nothing recorded yet — the daemon has not started since this was added)")

    # A RECORDED START IS NOT PROOF OF A RUNNING DAEMON.
    #
    # The verdict was `now_id in seen` and nothing else — the pid was written
    # and never read back — so `systemctl stop`, a disable, a dangling ExecStart
    # after a repo move, or a tick wedged one second after startup all printed
    # PASS and exited 0:
    #     FAIL  verify_boot FAILS when no daemon is running under that record
    #           a recorded start is not proof the daemon is alive now
    #
    # Two separate questions, and they have different remedies: did it come back
    # after this boot (is-enabled, Linger), and is it alive right now (is-active).
    here = seen.get(now_id) or []
    live = [r for r in here if _alive(r.get("pid"))]
    started, alive = (here[-1] if here else None), bool(live)
    print()
    if started and alive:
        print("  PASS  the daemon came back under the CURRENT boot, and is running")
        print(f"        {len(seen)} boot(s) with a record; "
              f"pid {live[0].get('pid')} alive of {len(here)} start(s) this boot")
        return 0
    if started:
        print("  FAIL  it started under this boot but is NOT running now")
        print(f"        {len(here)} start(s) recorded this boot, none still running "
              f"(newest pid {started.get('pid')})")
        for line in _remediation("running"):
            print(f"        {line}")
        return 1
    print("  FAIL  no record for the current boot — the daemon did NOT come back")
    for line in _remediation("enabled"):
        print(f"        {line}")
    return 1


def enabled(job):
    """Whether a job runs. Default on; `0`, `no`, `off` or `false` turn it off."""
    v = os.environ.get(f"RETENTION_GUARD_{job.upper()}", "1").strip().lower()
    return v not in ("0", "no", "off", "false")


def tick(apply=True):
    """One pass of every enabled job. Returns {job: outcome}, never raises.

    Extracted from the loop so it can be called by a test. A daemon whose only
    entry point is `while True` is a daemon nobody tests.

    Jobs run in this order: sync first (so fresh transcripts are on disk before
    the ledger reads them), then retention (protect against the next Claude
    startup), then ledger (record what the scan found).
    """
    out = {}
    for job in JOBS:
        if not enabled(job):
            out[job] = "disabled"
            log(f"{job}: disabled (RETENTION_GUARD_{job.upper()})")
            continue
        try:
            if job == "sync":
                # Job 1: repo sync — git pull + scan + commit own folder + push
                # + rebuild root reports. A dry-run pass uses apply=False.
                import sync_job
                res = sync_job.sync(dry=not apply)
                msg = sync_job.outcome_line(res)
                log(msg.strip())
                out[job] = "ok" if res.ok else f"INCOMPLETE: {msg}"
            elif job == "retention":
                rc = run(apply=apply)
                # The outcome comes from what the run DID. A no-op run() used to
                # report "ok" here, so a dead belt logged healthy forever.
                out[job] = "ok" if not rc else (
                    f"INCOMPLETE: {len(FAILED_LINKS)} store(s) not archived")
            else:
                # Job 3: ledger.
                # The OUTCOME comes from the job, not from "it returned without
                # raising". `out[job] = "ok"` on any string meant a ledger that
                # skipped reported success:
                #     FAIL  a skipped ledger is NOT reported as ok
                #           got 'ok' for a job that did nothing
                # and it made two assertions in adversarial_daemon.py unfalsifiable.
                outcome, msg = record_ledger(apply=apply)
                log(msg.strip())
                out[job] = outcome
        except Exception as e:  # noqa: BLE001 - one job failing is not both
            out[job] = f"ERROR: {e}"
            log(f"{job} ERROR: {e} — the other job(s) still ran")
    return out


def main(argv):
    if "--verify-boot" in argv:
        return verify_boot()
    if "--daemon" in argv:
        # Record the daemon baseline in cli-config.json the first time only.
        # This is the † timestamp shown in reports for non-Claude CLIs — it
        # anchors "from daemon start" so the figure is honest about when
        # monitoring began rather than claiming to be lifetime.
        try:
            import config as _cfg
            _cfg.record_daemon_start()
        except Exception:
            pass  # never block startup on a config write

        r = note_start()
        log(f"started under boot {r['boot_id'][:8]}, "
            f"{r['delay_s']}s after boot" if r.get("delay_s") is not None
            else "started")
        on = [j for j in JOBS if enabled(j)]
        off = [j for j in JOBS if not enabled(j)]
        # Re-read interval from config each startup so a change to cli-config.json
        # takes effect on the next service restart without touching the unit file.
        interval = _load_interval()
        log(f"retention guard up, every {interval}s — running {', '.join(on) or 'NOTHING'}"
            + (f"; disabled: {', '.join(off)}" if off else ""))
        if not on:
            log("every job is disabled — this daemon has nothing to do")
        while True:
            tick(apply=True)
            # WALL-CLOCK DEADLINE, NOT time.sleep(interval).
            #
            # time.sleep(21600) does not advance while the machine is suspended.
            # Measured on this machine: two consecutive gaps of 12h43m and 11h07m
            # against a configured 6h, because the laptop was closed each night.
            # A guard whose period doubles every time the lid closes is not
            # guarding every 6 hours. The announcement even says "every 6h" and
            # then waits longer, which is the "claims to work while doing less"
            # shape this suite was built to catch.
            #
            # The fix is to sleep in short chunks and compare wall clock. Each
            # chunk is 60 s — short enough to not delay a SIGTERM or a clean
            # shutdown, long enough that the overhead is negligible. On every
            # wakeup (including the ones inside a sleep after a resume) the
            # deadline is tested, not the accumulated sleep time.
            deadline = time.time() + interval
            while time.time() < deadline:
                time.sleep(min(60, deadline - time.time()))
    rc = run(apply="--apply" in argv)
    if "--apply" in argv:
        print()
        _outcome, _msg = record_ledger()
        print(_msg.strip())
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
