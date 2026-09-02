#!/usr/bin/env python3
"""Export this machine's Claude Code transcripts, redacted, for tools that need depth.

`update.py` measures tokens. Some tools need the transcripts themselves — Standout
parses message `content`, `input`, `summary` and `usage` to derive language,
framework, repo and skill signals, so counts alone tell it nothing.

    python3 export_corpus.py                 # -> corpus/<machine>/.claude/projects/
    python3 export_corpus.py --out /some/dir

WHY THIS IS NOT JUST A COPY

Transcripts contain live credentials. Measured on the machine this was written
on: 237 credential-shaped strings across 40 transcript files — GitHub tokens
(gho_, ghp_, github_pat_), sk- keys, JWTs. Those are the same files a profile
tool parses for content. Copying them into any repository publishes them.

So every line is rewritten on the way out:

  secrets      replaced span-wise, in values AND in keys — AskUserQuestion
               stores the question text as a dict KEY under toolUseResult, so
               scrubbing only values leaves it fully readable
  paths        /home/<user>/... and external mounts -> [path]
  emails       -> [email], except the one address kept for attribution
  topics       protected project names -> [redacted], the TERM only

That last one is the important one and it was learned the hard way. Replacing
the whole message because one word matched destroyed 55% of the prompts and took
the substance with it. The sentence around a protected term is the work; only
the term goes.

WHAT IS DELIBERATELY PRESERVED

Timestamps, session ids, message uuids, parent links, model names and usage
blocks are untouched. That is what makes any figure derived from this corpus
reproducible and checkable by whoever receives it — a corpus you cannot verify
against is a claim, not evidence.

Project directories are renamed `-workspace-pNNN`. Their real names identify
private repositories, and the structure a profile tool needs (how many projects,
how work is distributed across them) survives the renaming intact.
"""

import argparse
import fnmatch
import hashlib
import json
from collections import Counter, defaultdict
import os
import paths
import pathlib
import platform
import re
import shutil
import stores
import unicodedata
from stores import BY_LABEL

# ---------------------------------------------------------------- redaction

# Protected work. The TERM is replaced, never the message around it.
TOPIC = re.compile(
    r"(?i)ks[_-]?hunter|knuth\w*|sorrellian\w*|vortex\w*|ks[_-]?system|"
    r"infinity[_ ]?manifold|iquest-coder|ksz\w*|kscoord|(?:up|down|sideways)arrow|"
    r"\bks60|\b60[- ](?:level|class)\w*|\b(?:up|down|side)\s+arrow\w*|"
    r"complete_60_level|tensor_to_ks|ks_to_tensor|deep\s+up\s+class|"
    r"shallow\s+projection|fold\s+equation|arrow.{0,20}class|"
    r"vortex[- ]?(?:system|anchor)|codecrusher|basilisk\w*|build-from-scratch|"
    r"sovereign-markets|pacto-seco|terravista|codegazer|glass-box-(?:engine|tools)|"
    r"cli-enforcement|songscribe|voicemaker|layerzero-test-drive|vulcan-delta")

SPANS = [(re.compile(p), r) for p, r in [
    (r"-----BEGIN[A-Z ]*PRIVATE KEY-----[\s\S]*?-----END[A-Z ]*PRIVATE KEY-----", "[redacted]"),
    # AND THE SAME KEY WITH NO -----END-----, which is the one that shipped.
    #
    # The pattern above requires a well-formed block, so a key whose tail was
    # cut off does not match it and passes through untouched. That is not a
    # hypothetical: the 2026-08-10 audit found four BEGIN OPENSSH PRIVATE KEY
    # markers inside a copilot-chat session file in dist/hp-laptop-linux.tar.zst,
    # one decoding to openssh-key-v1 with ciphername=none and kdfname=none -- no
    # passphrase -- and TRUNCATED, private exponent absent. Truncation is the
    # normal case in a transcript: a tool prints part of a file, a message is
    # cut at a context boundary, a paste is abbreviated.
    #
    # Measured before this line existed: a lone BEGIN header plus its base64
    # body survived _redact_text intact, while README.md published
    # "0 credential-shaped survivors".
    #
    # Bounded rather than greedy. `[\s\S]*` would swallow the remainder of a
    # 83 MB session the moment one header appeared; this consumes only the
    # base64 body -- including the \n escapes a key carries when it sits inside
    # a JSON string -- and stops at the first character that cannot be key
    # material. Over-redaction here costs a few characters of a transcript;
    # under-redaction ships a private key.
    (r"-----BEGIN[A-Z ]*PRIVATE KEY-----(?:\\n|[A-Za-z0-9+/=\s]){0,8192}", "[redacted]"),
    (r"sk-ant-[A-Za-z0-9_-]{20,}", "[redacted]"),
    # Google AI Studio's CURRENT key form. `AIza[0-9A-Za-z_-]{35}` below is the
    # older shape and it is the only Google credential this file knew about;
    # keys issued by aistudio.google.com today look like `AQ.Ab8...` and matched
    # nothing. Found by testing the redactor against a fabricated key of each
    # shape rather than by reading the list and assuming it was complete --
    # 2 of 8 shapes survived, and both are on this line and the one above.
    (r"AQ\.[A-Za-z0-9_-]{20,}", "[redacted]"),
    (r"sk-(?:proj-)?[A-Za-z0-9]{20,}", "[redacted]"),
    (r"npm_[A-Za-z0-9]{36}", "[redacted]"),
    (r"gh[pousr]_[A-Za-z0-9]{30,}", "[redacted]"),
    (r"github_pat_[A-Za-z0-9_]{30,}", "[redacted]"),
    (r"A[KS]IA[0-9A-Z]{16}", "[redacted]"),
    (r"AIza[0-9A-Za-z_-]{35}", "[redacted]"),
    (r"ya29\.[A-Za-z0-9_-]{20,}", "[redacted]"),
    (r"xox[baprs]-[A-Za-z0-9-]{10,}", "[redacted]"),
    (r"xai-[A-Za-z0-9]{20,}", "[redacted]"),
    (r"[rs]k_(?:live|test)_[A-Za-z0-9]{20,}", "[redacted]"),
    # header.payload is enough to match. Requiring the signature too let a real
    # token through: 8 copies of an api_read credential with no `exp` claim
    # survived one machine's export, because the signature had been split off in
    # the transcript. The header and payload alone identify the account and
    # scopes, and merge_corpus.py flags two segments — a redactor stricter than
    # its own verifier reports leaks it cannot fix.
    (r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}(?:\.[A-Za-z0-9_-]+)?", "[redacted]"),
    (r"ssh-(?:rsa|ed25519|dss)\s+AAAA[A-Za-z0-9+/=]+", "[redacted]"),
    # RFC1918 addresses. Found by the PAYLOAD gate, not by this file: a real
    # internal log server reached Standout's upload inside an exchange sample,
    # in a line of the form 'Login path (PuTTY/MobaXterm -> 10.x.x.x -> ssh
    # <account>@)'. It survived every rule here because none describe an IP.
    #
    # The address itself is deliberately NOT written here. Documenting a leak
    # by pasting the leaked value into a repository that exists to stay small
    # enough to read and safe to share just moves it.
    #
    # It stayed invisible for a second reason worth recording: on the full
    # corpus, capPayload had already deleted every sample to fit the 4 MB cap,
    # so the leak only became reachable once the sliced runs put the samples
    # back. A redaction rule that is only exercised by content the transport
    # happens to drop is a rule nobody has tested.
    #
    # Only private ranges. Public addresses are not matched because version
    # strings and numeric ids look exactly like them.
    (r"\b(?:10\.\d{1,3}|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b",
     "[redacted]"),
    (r"\b0x[0-9a-fA-F]{64}\b", "[redacted]"),
    (r"(?i)\b(?:api[_-]?key|secret|token|password|passwd|bearer|authorization)\b"
     r"[\"'\s:=]{1,4}[A-Za-z0-9_\-./+]{20,}", "[redacted]"),
    (r"\(?\b\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b", "[phone]"),
]]

# NO trailing \b. It was there, and a digit glued to the TLD defeated the whole
# match rather than shortening it: in `mhsain@nvidia.com1` the boundary test
# between `m` and `1` fails, backtracking to `.co` fails between `o` and `m`,
# and the address ships in clear. Found in this machine's own export — a
# footnote marker pasted from a document, which is not an exotic input.
# Dropping it redacts that case to `[email]1`; a stray digit is the correct
# trade against publishing a third party's address. The LEADING \b stays: it
# stops the match widening left into things like `x+bob@corp.io`.
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# Values that cannot carry prose: uuids, timestamps, enums. `version` and `id`
# were on this list once and both turned out to hold free text from tool inputs,
# so they are scrubbed like anything else.
SKIP_KEYS = {"uuid", "parentUuid", "sessionId", "session_id", "timestamp",
             "type", "model", "requestId", "userType", "leafUuid"}
REPLACE_KEYS = {"cwd": "/workspace", "gitBranch": "main"}


# Per-platform starting points. These are JUMPING-OFF POINTS, not the answer:
# the roots are where to begin looking, and what is actually found underneath
# them is what gets redacted. Hardcoding the leaves ("C:\Users") is what broke
# on a D: drive; hardcoding the roots is fine, because the set of places an
# operating system puts homes and mounts is small and stable.
#
# ALL platforms' generic shapes are applied regardless of which one is running,
# because transcripts discuss other computers — a mac path appears in an export
# produced on Linux, and did: /Users/broodierchip-m1air, 33 times.
PLATFORM_ROOTS = {
    "Linux":   {"homes": ["/home", "/root"],
                "mounts": ["/media", "/mnt", "/run/media"]},
    "Darwin":  {"homes": ["/Users", "/var/root"],
                "mounts": ["/Volumes"]},
    "Windows": {"homes": ["Users"],          # joined to each real drive below
                "mounts": []},
}


def _drives():
    """Drive letters that actually exist. Windows only; empty elsewhere."""
    out = []
    if platform.system() != "Windows":
        return out
    for letter in "CDEFGHIJKLMNOPQRSTUVWXYZAB":
        p = pathlib.Path(f"{letter}:\\")
        try:
            if p.exists():
                out.append(f"{letter}:")
        except OSError:
            pass
    return out


def build_path_res(home):
    """Path patterns: this machine's real directories, plus any machine's shape.

    Two layers, and both are needed.

    DISCOVERED — start from the roots this platform actually uses, then
    enumerate what is under them. That is what makes it correct on a computer
    nobody anticipated: a relocated home, a second drive, an external disk named
    after its owner, a profile somewhere unusual. `find_config_dirs` already
    walked the disk, so its results are the strongest signal available and are
    fed straight in.

    GENERIC — the shape of a home directory on every platform, applied no matter
    which one is running. Transcripts discuss other computers, so the MacBook's
    `/Users/broodierchip-m1air` appeared 33 times in an export produced on Linux,
    a username from a machine this script never touched. Discovery cannot find
    that; only the shape can.

    `/home/runner` and `/home/dev` get caught too. They are a CI runner and a
    sandbox rather than anyone's account, but a rule that tries to tell real
    usernames from generic ones is a rule that eventually guesses wrong about a
    real one.
    """
    TAIL = r"[^\s\"',)\]]*"
    pats = [re.compile(re.escape(str(home)) + TAIL)]

    literals = {str(home)}
    roots = PLATFORM_ROOTS.get(platform.system(), PLATFORM_ROOTS["Linux"])

    # The environment's own idea of home, on every platform that has one.
    for var in ("HOME", "USERPROFILE", "XDG_CONFIG_HOME", "XDG_DATA_HOME",
                "XDG_CACHE_HOME", "APPDATA", "LOCALAPPDATA", "TMPDIR", "TEMP"):
        v = os.environ.get(var)
        if v and len(v) > 3:
            literals.add(v.rstrip("/\\"))
    drive, hpath = os.environ.get("HOMEDRIVE"), os.environ.get("HOMEPATH")
    if drive and hpath:
        literals.add((drive + hpath).rstrip("\\"))

    # Every sibling account under this platform's home roots — the other people
    # on this computer, whose names appear in shared paths and in prose.
    home_roots = [pathlib.Path(r) for r in roots["homes"]]
    for d in _drives():
        home_roots.append(pathlib.Path(f"{d}\\Users"))
    for root in home_roots:
        try:
            if root.is_dir():
                literals.add(str(root))
                for d in root.iterdir():
                    if d.is_dir():
                        literals.add(str(d))
        except OSError:
            pass

    # Where the profiles actually are. find_config_dirs walked the disk and
    # returned real paths, so their parents are real directories worth removing,
    # wherever they turned out to live.
    try:
        from analyze_tokens import find_config_dirs
        for d in find_config_dirs(home):
            literals.add(str(d))
            literals.add(str(d.parent))
    except Exception:
        pass

    # Mounted volumes, enumerated rather than listed. /proc/mounts is the
    # authority where it exists (Linux, WSL); the directory scan covers macOS
    # /Volumes and anything the kernel does not report.
    try:
        with open("/proc/mounts", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) > 1 and any(
                        parts[1].startswith(m + "/") for m in roots["mounts"]):
                    literals.add(parts[1])
    except OSError:
        pass
    for mount in roots["mounts"]:
        p = pathlib.Path(mount)
        try:
            if p.is_dir():
                for d in p.iterdir():
                    literals.add(str(d))
        except OSError:
            pass

    # The account name on its own, which appears in paths this never sees and in
    # prose that no path pattern would match at all.
    try:
        import getpass
        u = getpass.getuser()
        if u and len(u) > 2:
            pats.append(re.compile(r"\b" + re.escape(u) + r"\b"))
    except Exception:
        pass

    # Longest first: /home/x/.claude must be replaced before /home/x, or the
    # shorter match wins and leaves the tail behind.
    for lit in sorted(literals, key=len, reverse=True):
        if len(lit) > 3:
            pats.append(re.compile(re.escape(lit) + TAIL))
            # The same path as JSON stores it, with backslashes doubled. A
            # Windows path is written C:\\Users\\x in the file, so the literal
            # form never matches there — the leak check found 30 paths this way
            # that the redactor had walked straight past.
            if "\\" in lit:
                pats.append(re.compile(re.escape(lit.replace("\\", "\\\\")) + TAIL))
    # Any home directory, on any platform, belonging to anyone.
    #
    # The Windows pattern matched drive C only, while merge_corpus.py flags any
    # drive letter. So a D:\Users\... path was reported as a leak by the check
    # and never removed by the redactor — two files' worth on this fleet. The
    # exporter and the verifier have to agree on what counts, or the verifier is
    # reporting a bug the exporter cannot fix. Any letter, both cases.
    pats += [
        re.compile(r"/Users/[A-Za-z0-9._-]+" + TAIL),
        re.compile(r"/home/[A-Za-z0-9._-]+" + TAIL),
        # Windows, as written and as JSON stores it. Any drive letter, because
        # a home directory is not always on C.
        re.compile(r"[A-Za-z]:\\\\Users\\\\[A-Za-z0-9._-]+" + TAIL, re.I),
        re.compile(r"[A-Za-z]:\\Users\\[A-Za-z0-9._-]+" + TAIL, re.I),
        # WSL reaches the Windows disk through /mnt/<letter>, so the same
        # directory has a second spelling that none of the above matches.
        re.compile(r"/mnt/[a-z]/Users/[A-Za-z0-9._-]+" + TAIL, re.I),
        # UNC shares: \\server\share\... and the doubled form.
        re.compile(r"\\\\\\\\[A-Za-z0-9._-]+\\\\[A-Za-z0-9._$-]+" + TAIL),
        re.compile(r"\\\\[A-Za-z0-9._-]+\\[A-Za-z0-9._$-]+" + TAIL),
        # macOS puts removable and network volumes here, with the volume name
        # often being a person's or machine's name.
        re.compile(r"/Volumes/[A-Za-z0-9._ -]+" + TAIL),
        # Removable media on Linux mounts under the account name, so the path
        # carries a username without being a home directory. Enumerating real
        # mounts above only covers THIS computer; a transcript discussing
        # another names a drive this machine has never seen.
        re.compile(r"/(?:run/)?media/[A-Za-z0-9._-]+/[A-Za-z0-9._ -]+" + TAIL),
        re.compile(r"/root/" + TAIL, re.I),
    ]
    return pats


class Redactor:
    def __init__(self, home, keep_email):
        self.paths = build_path_res(home)
        self.keep = keep_email
        self.stats = {"topic": 0, "span": 0, "path": 0, "email": 0,
                      "lines": 0, "files": 0, "dropped": 0}

    def scrub(self, s):
        if not isinstance(s, str) or not s:
            return s
        s, n = TOPIC.subn("[redacted]", s)
        self.stats["topic"] += n
        if self.keep:
            s = s.replace(self.keep, "\x00K\x00")
        for rx, rep in SPANS:
            s, n = rx.subn(rep, s)
            self.stats["span"] += n
        for rx in self.paths:
            s, n = rx.subn("[path]", s)
            self.stats["path"] += n
        s, n = EMAIL.subn("[email]", s)
        self.stats["email"] += n
        return s.replace("\x00K\x00", self.keep) if self.keep else s

    def walk(self, o, key=None):
        if isinstance(o, dict):
            out = {}
            for k, v in o.items():
                nk = k if (k in SKIP_KEYS or k in REPLACE_KEYS) else self.scrub(k)
                out[nk] = (REPLACE_KEYS[k] if k in REPLACE_KEYS else
                           v if k in SKIP_KEYS else self.walk(v, k))
            return out
        if isinstance(o, list):
            return [self.walk(v, key) for v in o]
        if isinstance(o, str) and key not in SKIP_KEYS:
            return self.scrub(o)
        return o


# ------------------------------------------------- every other CLI's history

# The counter reads 8 CLIs. The corpus backed up 1. Every report in this repo
# said "8 tools, 118 billion tokens" while the thing being PRESERVED was Claude
# and nothing else — so the day a machine dies, seven of those eight survive
# only as arithmetic.
#
# Where each tool keeps records comes from stores.py, the same map the counter
# and the archiver read. A fourth hand-written list here is how the corpus and
# the archive would end up covering different ground without either one saying so.

# A tool tree is not conversation history. These are reachable only through
# ARCHIVE RESIDUE: ~/.gemini/tmp/extensions does not exist and never did, but an
# older source map said ".gemini" where it now says ".gemini/tmp", and the hard
# links that rule made outlive the rule. 1,022 MB of Go, Python and bytecode,
# still linked, still shaped exactly like history.
VENDOR_DIRS = {"node_modules", "extensions", "plugins", "pkg", "vendor", "dist",
               "build", "__pycache__", ".git", "target", "testdata", "site-packages"}
VENDOR_EXT = {".py", ".pyc", ".pyo", ".go", ".ts", ".tsx", ".js", ".mjs", ".cjs",
              ".map", ".mdx", ".snap", ".lock", ".sum", ".mod", ".h", ".c", ".cc",
              ".rs", ".java", ".class", ".css", ".scss", ".html", ".svg", ".png",
              ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".ttf", ".wasm",
              ".so", ".dylib", ".dll", ".exe", ".zip", ".gz", ".tar", ".whl"}

# Binary stores cannot be redacted, so they are never shipped. Antigravity keeps
# conversations as SQLite whose payload is an undocumented protobuf, and as .pb
# that is AES-256-GCM encrypted; sessions.read_antigravity gets token counts out
# of it, not readable text. Shipping them would put unredactable bytes in the
# corpus; dropping them silently would make a tool with 12 MB of real history
# look like a tool with none. Recorded, with the reason.
OPAQUE_EXT = {".db", ".db-wal", ".db-shm", ".sqlite", ".sqlite3", ".pb", ".bin"}

# TWO REAL TRANSCRIPTS CANNOT BE BYTE-IDENTICAL, AND ACROSS TWO COMPUTERS IT IS
# IMPOSSIBLE. So identical record content is not a duplicate to suppress — it is
# evidence that the collector picked up something that is not a record, and the
# remedy is to stop collecting it, not to delete one copy of it.
#
# The measurement that settled it. A corpus-wide (size, sha256) rule suppressed
# 4,610 files on this machine and 4,472 of them were `checkpoints/index.md`, a
# 172-character stub the tool writes once per conversation. Boilerplate, not
# records: the correct answer was never to dedup them.
#
# So nothing is dropped for its content any more. These two keys are an ALARM,
# and they are the only reason the hash is still computed. The aggregate is the
# number a report can read; the detail line names BOTH paths, because a count
# with no names cannot be acted on and acting on it is the entire point.
IDENTICAL_RECORDS = ("identical record content — ALARM, nothing dropped, "
                     "every copy exported")
IDENTICAL_DETAIL = "identical record content"

# A root_files store exists to catch records a tool leaves LOOSE beside its
# program directories — proteus writes history.jsonl straight into ~/.proteus.
# Taking every root file instead takes the tool's config with it, and config is
# where credentials live: that is how ~/.devvit/token (an OAuth refresh token)
# and ~/.gemini/oauth_creds.json ended up in the archive.
#
# The fix is not to detect secrets. It is to take records and leave config. A
# usage counter has no business holding either one, but only one of them is
# history.
HISTORY_NAMES = re.compile(r"(history|conversation|chat|thread|message|"
                           r"transcript|prompt)", re.I)
HISTORY_EXT = {".jsonl", ".ndjson"}

# CONFIG IS NEVER A RECORD, AT ANY DEPTH, FROM ANY SOURCE.
#
# Applying the record/config test only at a store's ROOT was not enough, and the
# first full export proved it: ~/.gemini/oauth_creds.json reached the output.
# Not from the live tree — the exporter never walks ~/.gemini — but from the
# ARCHIVE, where residue from an older source map left a copy nested inside
# other/gemini/. Archive directories are walked recursively, so a root-only rule
# never looked at it. `devvit/session-id` and `deepseek-code/config.json` came
# through the same hole.
#
# So the test is by name and applies everywhere. These names are configuration
# in every tool that uses them; none of them is anybody's conversation.
NEVER_EXPORT = re.compile(
    r"^(oauth_creds|credentials?|auth|config|settings|state|token|session-id|"
    r"installation_id|user-settings|permissions-config|lsp-config|mcp-config|"
    r"mcp-oauth-config|google_accounts|\.?netrc|id_(rsa|ed25519).*)"
    r"(\.(json|toml|yaml|yml|ini|cfg|conf))?$", re.I)

# THE SECRET HALF OF THAT LIST, AND WHY IT HAS TO BE SEPARATE.
#
# NEVER_EXPORT is right for an EXPORTER, which ships bytes into a corpus: a file
# it cannot vouch for stays out, so refusing `config|settings|state` costs
# nothing. It is wrong for the ARCHIVER, which ships nothing and deletes
# nothing, because there a refusal is a record that never gets a second name.
#
# Measured when this split was written: Copilot Chat names its editing-session
# record `state.json`, and `state` is in NEVER_EXPORT. Importing the whole rule
# into retention_guard dropped
#
#     ~/.config/Code/.../chatEditingSessions/*/state.json          17 files
#     ~/.config/Code - Insiders/.../chatEditingSessions/*/state.json  179 files
#                                                     196 files, 494,067,931 B
#
# and one of them holds `linearHistory` with 369 entries — the sequence of what
# that session actually did. That is a record by any reading.
#
# So: SECRET_NAMES is the subset that is a credential in every tool that uses
# it. The config names are deliberately absent. Both rules live here, next to
# each other, because splitting them across two files is how this repository
# has already shipped one defect four times.
SECRET_NAMES = re.compile(
    r"^(oauth_creds|credentials?|auth|token|session-id|installation_id|"
    r"mcp-oauth-config|google_accounts|\.?netrc|id_(rsa|ed25519).*)"
    r"(\.(json|toml|yaml|yml|ini|cfg|conf))?$", re.I)

# Directories that hold secrets by design. GitHub's own Copilot CLI reference
# lists mcp-secrets/ and mcp-oauth-config/ inside ~/.copilot, beside the session
# state — so a tool's config directory is not a safe thing to walk for history.
#
# Compared NORMALISED, never as literals. This set is matched against directory
# names that come off a real filesystem, and `Credentials/`, `.credentials/` and
# `MCP-Secrets/` all passed an exact lowercase test while only `mcp-secrets/`
# was refused. macOS and Windows filesystems are case-insensitive, so on two of
# the five machines those are not even different directories — they are one
# directory whose stored spelling happens to differ. Use secret_dir() to ask.
SECRET_DIRS = {"mcp-secrets", "mcp-oauth-config", "auth", "credentials", ".ssh",
               "keys", "certs"}

# ONE NORMALISER, AND EVERY NAME RULE GOES THROUGH IT.
#
# Each of the four name defects this repository has shipped was the same shape:
# a rule written for the spelling THIS machine happens to produce. `.lower()`
# caught Credentials but not `credentials.`; `.lstrip(".")` caught
# `.credentials` but not `credentials `. Enumerating spellings is how you get
# the fifth one. So the spellings are folded once, here, and the rules ask
# about the folded name.
#
# Zero-width characters are removed rather than stripped because str.strip()
# CANNOT remove them: str.isspace() is False for ZWSP, ZWNJ, ZWJ, WORD JOINER
# and BOM, so `mcp-secrets​` survived every strip()-based rule.
#
# BY UNICODE CATEGORY, NOT BY A LIST OF FIVE. A hardcoded list is the same
# antipattern as a hardcoded set of spellings: it covers the characters
# somebody has already been bitten by, and the sixth one — LEFT-TO-RIGHT MARK,
# SOFT HYPHEN, MONGOLIAN VOWEL SEPARATOR — walks straight past. Category Cf is
# "format", which is the definition of a character that occupies no width, so
# it is the property the rule actually means. Removing Cf cannot make two
# different names collide into a SECRET name: every name in SECRET_DIRS and
# SECRET_NAMES is pure ASCII, so a name that still contains letters outside
# ASCII after the removal cannot match one whatever else is done to it.


def fs_name(name):
    """ONE filesystem name, reduced to what the name IS.

    Removes only what a filesystem or a display convention ADDS around a name:

      NFC          macOS APFS/HFS+ store filenames DECOMPOSED and hand them back
                   that way; ext4 hands back the bytes that were written. Two of
                   the five machines in this fleet are macOS, so composed and
                   decomposed are one name and must fold to one string.
      zero-width   every character of Unicode category Cf — ZWSP, ZWNJ, ZWJ,
                   WORD JOINER, BOM, LEFT-TO-RIGHT MARK, SOFT HYPHEN. See the
                   note above for why this is a category test and not a list.
      whitespace   leading and trailing, in any script: space, tab, CR, LF, and
                   NBSP / EN QUAD / IDEOGRAPHIC SPACE, all of which str.strip()
                   does remove because str.isspace() is True for them.
      dots         leading and trailing, interleaved with the whitespace in any
                   order (`credentials. `, `credentials .`), which is why this
                   loops instead of doing one strip of each.
      case         casefold, NOT lower: str.lower() leaves LATIN SMALL LETTER
                   LONG S alone, so `credentialſ` passed a .lower() test.

    TRAILING DOTS AND SPACES ARE A LINUX AND macOS PROBLEM, NOT A WINDOWS ONE,
    and the earlier note in this repository had the reason backwards. Windows
    STRIPS trailing dots and spaces at creation — `mkdir "mcp-secrets."` there
    yields `mcp-secrets`, so the variant cannot exist on Windows at all. It can
    be created on Linux and macOS, which is where it bit: 14 payload files
    shipped through `credentials.`, `credentials `, `mcp-secrets.` and
    `mcp-secrets `.

    IT DOES NOT TOUCH THE LETTERS, AND THAT IS THE WHOLE DISCIPLINE.
    No NFKC — fullwidth `ｃｒｅｄｅｎｔｉａｌｓ` stays a different name. No
    confusables folding — a Cyrillic homoglyph stays a different name. Both
    would start matching real RECORD directories, and in retention_guard a
    wrongful refusal is permanent record loss: 7 of the 8 CLIs keep no counter,
    so the file on disk is the only evidence there ever was. Measured over every
    directory and file name in the live store paths and in ~/.ai-logs-archive,
    this normaliser newly matches NOTHING that the old rules let through as a
    record.
    """
    n = name
    if not n.isascii():
        # Exact fast path, not an approximation: ASCII is already NFC, and no
        # ASCII character is category Cf. This rule is called once per path
        # COMPONENT for every file the daemon walks — 146,690 of them on this
        # machine — and almost all of those names are ASCII.
        n = unicodedata.normalize("NFC", n)
        n = "".join(c for c in n if unicodedata.category(c) != "Cf")
    prev = None
    while n != prev:
        prev = n
        n = n.strip().strip(".")
    return n.casefold()


_SECRET_DIRS_NORM = {fs_name(d) for d in SECRET_DIRS}
_VENDOR_DIRS_NORM = {fs_name(d) for d in VENDOR_DIRS}


def secret_dir(name):
    """Is this ONE directory name a secret directory, in any spelling?"""
    return fs_name(name) in _SECRET_DIRS_NORM


def vendor_dir(name):
    """Is this ONE directory name a vendored directory, in any spelling?

    The vendored test was `set(rel.parts[:-1]) & VENDOR_DIRS` — a raw,
    case-sensitive, dot-sensitive intersection — sitting fifteen lines above the
    secret-directory test that had already been normalised FOR EXACTLY THIS
    REASON, comment still attached. Verified live on this machine: `Plugins`,
    `plugins `, `plugins.` and `.plugins` all walked past it, and fs_name folds
    every one of them.

    It matters more here than the spelling suggests. `plugins/` on this machine
    holds 3,282 marketplace `.md` files shape-identical to the 9 authored ones —
    364 vendored files for every real one — so a single unfolded spelling is the
    difference between collating a profile and collating a marketplace.
    """
    return fs_name(name) in _VENDOR_DIRS_NORM


def secret_ancestor(path, home):
    """Does ANY component of `path` below `home` name a secret directory?

    `secret_dir()` answers about one name, and every caller that needed to ask
    about a PATH re-derived the walk itself and stopped at a different depth.
    The archiver asked `secret_dir(basename(src))` — the immediate parent alone,
    because link_tree chops the file off the walk root and the per-component
    test over `rel` then has nothing left to see. One subdirectory was a bypass:

        .copilot/mcp-secrets/gh.json            parent 'mcp-secrets'  refused
        .copilot/mcp-secrets/sub/history.jsonl  parent 'sub'          ARCHIVED
        .copilot/mcp-secrets/a/b/history.jsonl  parent 'b'            ARCHIVED

    and the names that got through are the ones nothing else can catch:
    `history.jsonl` is what `_is_loose_record` exists to admit and what
    `_is_secret` is guaranteed not to match, so ancestry was the only rule in
    the way.

    HOME IS THE BOUNDARY, AND THE BOUNDARY IS THE HARD PART. Walking to `/`
    closes this hole and opens a worse one in the other direction: in the
    archiver a wrongful refusal is a record that never gets a second name, and
    the archive is the only copy for 7 of the 8 CLIs. A user whose HOME is
    /home/keys, or a machine mounting /Volumes/certs, would have
    ~/.ollama/history refused by a component nobody in this program chose.
    Every path that reaches these callers is built as os.path.join(home, *rel),
    so the components the STORE MAP named are exactly the ones below home.

    `home` is a PARAMETER and not `expanduser("~")` — retention_guard patches
    its own module-level HOME, and a helper that re-derived the real one would
    answer about a different filesystem than the caller is walking.

    Outside `home`, or unresolvable: False. Nothing above the user is ours to
    judge, and guessing costs records.
    """
    try:
        rel = pathlib.Path(os.path.realpath(path)).relative_to(
            pathlib.Path(os.path.realpath(home)))
    except (OSError, ValueError):
        return False
    return any(secret_dir(c) for c in rel.parts)


def _is_config(path):
    """A file that is configuration or a credential, not a record.

    ASKED ON THE NORMALISED NAME, and it was not. `_is_secret` below was fixed
    for the dotted spelling and THIS RULE — the one that guards the corpus this
    program PUBLISHES — was left anchored on the raw name, so
    `_is_config('.credentials.json')` returned False. That is the exact spelling
    of the OAuth token in all four live Claude profiles, and of every other name
    in NEVER_EXPORT the moment a tool writes it hidden. Two rules, one fix, one
    of them applied: the same defect this repository has now shipped four times.
    """
    return bool(NEVER_EXPORT.match(fs_name(path.name)))


def _is_secret(path):
    """A file that is a CREDENTIAL. Narrower than _is_config, on purpose.

    The dotted spelling is the same file. NEVER_EXPORT and SECRET_NAMES are both
    anchored with `^`, so `credentials.json` matches and `.credentials.json`
    does not — and all four live Claude profiles keep their OAuth token as
    `.credentials.json`. On Unix a leading dot is a display convention; it is
    not part of what the file IS.

    THE HAND-ROLLED `lstrip(".")` THAT USED TO LIVE HERE IS GONE. It handled the
    one spelling somebody had been bitten by and none of the others:
    `credentials.json.`, `credentials.json `, `credentials​.json` and
    ` credentials.json` all walked past it. fs_name() folds them all, including
    the dotted spelling this docstring was written for.
    """
    return bool(SECRET_NAMES.match(fs_name(path.name)))


def secret_symlink_target(path):
    """A symlink is judged by what it POINTS AT, because that is what is taken.

    os.link() follows symlinks (linkat with AT_SYMLINK_FOLLOW), so the archive's
    second directory entry lands on the TARGET's inode, and this program opens
    the target and ships the TARGET's bytes. Measured before this existed: a
    symlink named `session.jsonl` pointing at `credentials.json` was archived at
    the credential's inode AND its bytes reached out_root; the same link
    pointing into `mcp-secrets/` did too, because the walk never sees that
    component.

    THE TARGET'S OWN NAME AND ITS IMMEDIATE PARENT, AND NOTHING ABOVE THAT.
    realpath() returns an ABSOLUTE path, so testing every component would refuse
    any record that happens to live under a directory somebody called `keys` or
    `auth` anywhere in its ancestry — over-refusal, which in retention_guard is
    permanent record loss. Two components is what the corpus of real shapes
    needs and it is where this stops.
    """
    if not os.path.islink(path):
        return False
    try:
        real = pathlib.Path(os.path.realpath(path, strict=True))
    except OSError:
        return False          # dangling or a loop: nothing to take, nothing to leak
    return _is_secret(real) or secret_dir(real.parent.name)


def _is_loose_record(path):
    """A root-level file that is a RECORD, not configuration.

    "session" is deliberately NOT a history word here. ~/.devvit/session-id is a
    session IDENTIFIER, and matching on the word exported it; the records these
    stores exist for are named history.jsonl, cli_history, input_history.txt.
    """
    if _is_config(path):
        return False
    n = path.name.lower()
    return path.suffix.lower() in HISTORY_EXT or bool(HISTORY_NAMES.search(n))


# ------------------------------------------------------------------- the walk
#
# A DIRECTORY THAT WAS NEVER ENUMERATED IS NOT AN EMPTY ONE, and `Path.rglob`
# cannot tell you which it walked. Its recursion calls os.scandir under a bare
# `except OSError: return`, so a directory this process cannot enter yields
# NOTHING and raises NOTHING. Verified here before this was written: a project
# holding
#
#     proj/top.jsonl
#     proj/locked/hidden.jsonl        chmod 000
#
# returns exactly `[proj/top.jsonl]`, and the export, the manifest and every
# number in it are byte-for-byte what the same tree produces with `locked/`
# present, readable and EMPTY. That is this repository's signature defect —
# absent looking exactly like zero — sitting in the one place where the loss is
# permanent: 7 of the 8 CLIs keep no counter, so a record the walk did not see
# is a record nothing downstream can notice is gone.
#
# rglob ALSO DOES NOT DESCEND A SYMLINKED DIRECTORY. Probed the same way:
# projects/<proj>/linked -> elsewhere/ holding one transcript was walked past
# and the exporter printed a clean `files 3`.
#
# Both are properties of the WALK, so both are fixed in the walk and in one
# place, and both walks in this file go through it.

MAX_PATH = 260


def walk_tree(root, keep_dir=None):
    """Every file under `root`, what could not be read, and what was followed.

    Returns (files, blind, links):

      files   sorted Paths. Files only; a symlink TO a file is a file.
      blind   [{"path": Path, "reason": str}] — directories that were not
              enumerated. NAMED, not merely counted: a number with no name
              cannot be acted on, because the operator cannot tell which
              directory to go and unlock.
      links   [{"path": Path, "target": Path}] — symlinked directories that
              were followed, so the corpus can state where it reached.

    SYMLINKED DIRECTORIES ARE FOLLOWED, DELIBERATELY, BEHIND A SEEN-SET ON
    (st_dev, st_ino). Refusing and reporting is equally defensible and silence
    is not; following is chosen because a symlink inside a profile is how
    somebody MOVES transcripts off a full disk, and refusing would drop exactly
    the records this program exists to keep. The seen-set is what makes it
    safe: a link back to an ancestor is a second NAME for an inode already
    walked, so it is skipped rather than followed forever. A walk that follows
    links without one does not return, and in run.py that is not a slow export
    — sh() raises SystemExit, so the machine records nothing at all.

    A symlinked directory whose TARGET is named like a secret directory is
    refused and reported instead, on exactly the reasoning secret_symlink_target
    already applies to files: a link is judged by what it points AT, because
    that is what would be read. Its name is not what would be shipped.

    `keep_dir(rel)` prunes, and is asked about a directory's path relative to
    `root`: "could anything under here still be wanted?". A pruned directory is
    a decision, not a failure, so it is not reported as blind.
    """
    root = pathlib.Path(root)
    files, blind, links = [], [], []

    def refuse(p, reason):
        blind.append({"path": pathlib.Path(p), "reason": reason})

    def onerror(err):
        # os.walk hands the scandir failure here instead of swallowing it.
        # `filename` is the directory it could not enumerate.
        refuse(getattr(err, "filename", None) or root, "could not be read")

    seen = set()
    try:
        st = os.stat(str(root))
        seen.add((st.st_dev, st.st_ino))
    except OSError:
        refuse(root, "could not be read")
        return [], blind, links

    for dirpath, dirnames, filenames in os.walk(str(root), onerror=onerror,
                                                followlinks=True):
        here = pathlib.Path(dirpath)
        keep = []
        for name in sorted(dirnames):
            child = here / name
            if keep_dir is not None and not keep_dir(child.relative_to(root)):
                continue
            is_link = os.path.islink(str(child))
            target = None
            if is_link:
                try:
                    target = pathlib.Path(os.path.realpath(str(child),
                                                           strict=True))
                except OSError:
                    refuse(child, "dangling symlink")
                    continue
                if secret_dir(target.name):
                    refuse(child, "symlink to a secret directory")
                    continue
            try:
                st = os.stat(str(child))
            except OSError:
                refuse(child, "could not be read")
                continue
            key = (st.st_dev, st.st_ino)
            if key in seen:
                continue          # a loop, or a second name for one directory
            seen.add(key)
            if is_link:
                links.append({"path": child, "target": target})
            keep.append(name)
        dirnames[:] = keep
        for name in sorted(filenames):
            files.append(here / name)
    return sorted(files), blind, links


def _record_prune(records):
    """Prune a walk to the directories a store's records glob could still reach.

    THE PICKER AND THE CHECKER WERE TWO RULES AND THEY DISAGREED. Files were
    picked with `root.glob(g)` — pathlib, which runs both sides through
    os.path.normcase, identity on posix — and then re-checked with
    stores.matches_records, which folds case on EVERY platform and says why:
    two of the five machines here run case-insensitive filesystems, so
    `ChatSessions/` and `chatSessions/` are ONE directory whose stored spelling
    happens to differ. The picker ran first and decided the other way, so a
    record that EXISTS was exported nowhere while `is_record` agreed the whole
    time that it was a record.

    So the picker is gone. The walk decides nothing; `store.is_record` decides.
    This only PRUNES, and it prunes the way the pattern is written — component
    by component, folded — because copilot-chat's root is 4.5 GB of other
    extensions' state and walking it whole to discard nearly all of it costs
    minutes on every run.

    COMPONENT-WISE IS ALSO WHAT KEEPS matches_records' DOCUMENTED GUARANTEE
    TRUE. fnmatch's `*` crosses "/" and pathlib's does not, and that
    permissiveness is only ever used to ACCEPT a file this walk already offered
    — never to reach one it did not.
    """
    pats = [[c for c in g.replace(os.sep, "/").lower().split("/") if c]
            for g in records]

    def keep(rel):
        parts = [p.lower() for p in rel.parts]
        d = len(parts)
        for pat in pats:
            if len(pat) <= d:
                continue          # this pattern ends at or above here
            if "**" in pat[:d]:
                return True       # nothing below a ** can be ruled out
            if all(fnmatch.fnmatchcase(a, b) for a, b in zip(parts, pat)):
                return True
        return False

    return keep


def _tool_roots(home, archive_other):
    """(label, root, origin, top_only) for every store, live and archived.

    The archive is not a duplicate of live. It holds what retention already
    deleted, which on this machine is most of copilot's older sessions —
    exporting live only would quietly export only recent history.
    """
    out = []
    # preserve=False is the one store property that must be honoured HERE and
    # not by a later filename test. `.claude.json` is config carrying
    # oauthAccount, userID and machineID; it is in the map because a reader
    # counts it, and NEVER_EXPORT could not stop it because that rule matches
    # names like `config` and `credentials` and this file is called neither.
    skip = {s.label for s in stores.STORES if not s.preserve}
    for s in stores.conversation_stores():
        if s.label == "claude" or not s.preserve:
            continue                      # exported above, with its own dedup
        for p in stores.resolve(s, str(home)):
            out.append((s.label, pathlib.Path(p), "live", False))
    for s in stores.root_file_stores():
        if not s.preserve:
            continue
        for p in stores.resolve(s, str(home)):
            out.append((s.label, pathlib.Path(p), "live", True))
    if archive_other and archive_other.is_dir():
        for d in sorted(archive_other.iterdir()):
            # The archive is walked by directory NAME, so residue from an
            # earlier run under a now-unpreservable label gets in unless the
            # same rule is applied to it. That is how oauth_creds.json reached
            # the output the first time.
            if d.is_dir() and d.name not in skip:
                top_only = d.name in {s.label for s in stores.root_file_stores()}
                out.append((d.name, d, "archive", top_only))
    return out


def write_text(path, text):
    """Write UTF-8 with '\\n' line endings, and return the bytes that landed.

    ONE BYTE DEFINITION, SERVING BOTH SIDES. `Path.write_text` passes
    newline=None, which CPython translates to os.linesep on the way out, so on
    Windows every \\n becomes \\r\\n. This file then counts bytes two ways —

        export_tools   per_tool[label]["bytes"] += len(text.encode("utf-8"))
        main           size = sum(f.stat().st_size for f in dst.rglob(...))

    — and the two diverge in OPPOSITE directions: st_size grows by one byte per
    line while len(text.encode()) does not move at all. The manifest then
    carries two byte totals for one corpus, one of them short by exactly the
    line count, and both look entirely reasonable on the page.

    The CRLF is the second half and the worse one. This corpus is JSONL, read
    line by line by whoever receives it, and a redaction audit that greps raw
    bytes is then reading a different file than the one that was written.

    Returning the count is what makes the definition single: a caller that
    wants "how many bytes" asks the writer rather than measuring the string it
    handed over or the file it left behind.
    """
    data = text.encode("utf-8")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return len(data)


def export_tools(out_root, home, archive_other, red):
    """Redacted conversation history for every CLI that is not Claude."""
    rows, skipped = [], Counter()

    def refuse(label, rel, reason):
        """Count it AND name it. `rows` had no other way to be non-empty.

        It was created here, returned at the bottom of this function, and
        appended to by no line in this file — so every export shipped
        MANIFEST.json with `"tool_files_refused": []`, a ledger structurally
        incapable of recording a refusal, sitting beside a Counter that had the
        numbers the whole time. An empty list there reads as "nothing was
        withheld", which is the one sentence this field exists to contradict.

        Only the four CLASSIFICATION refusals route through here — a file kept
        out because of what it IS. `unreadable`, `vendored`, `not a record for
        this store` and the binary skips stay counted-only: they are properties
        of the walk, not decisions about a file's contents, and mixing them in
        would make a security ledger that is mostly noise.
        """
        skipped[reason] += 1
        rows.append({"tool": label, "path": str(rel), "reason": reason})

    def note_dir(label, path, root, reason):
        """A DIRECTORY the walk did not enumerate. Counted AND named.

        It does not go through refuse(), which is the ledger of CLASSIFICATION
        decisions — a file kept out because of what it IS. This is the opposite
        fact: nothing was classified, because nothing was seen. Naming it in
        the same Counter that already carries per-label detail
        (`lone surrogates replaced (<label>)`) keeps export_tools' three return
        values exactly three, which adv_collation.py unpacks positionally.

        The aggregate and the name are BOTH written. The aggregate is the
        number a report can read; the name is the only thing an operator can
        act on.
        """
        try:
            rel = pathlib.Path(path).relative_to(root)
        except ValueError:
            rel = pathlib.Path(path)
        skipped["directories not enumerated"] += 1
        skipped[f"not enumerated: {label}/{rel.as_posix()}/ ({reason})"] += 1

    def note_link(label, link, root):
        """A symlinked directory that was FOLLOWED. Also counted, also named.

        Following is the deliberate answer to rglob walking past it (see
        walk_tree). A corpus that reached outside the tree it was pointed at
        has to say so, or the next person cannot tell which files came from
        where.
        """
        try:
            rel = pathlib.Path(link["path"]).relative_to(root)
        except ValueError:
            rel = pathlib.Path(link["path"])
        skipped["symlinked directories followed"] += 1
        skipped[f"followed symlink: {label}/{rel.as_posix()}/"] += 1

    def note_dup(kind, detail, label, rel, first):
        """A file suppressed as a duplicate. COUNTED AND NAMED, both.

        THIS IS THE SIGNATURE BUG OF THIS REPOSITORY, AND IT WAS HERE.

            if (st.st_dev, st.st_ino) in seen:
                continue

        Three lines, no counter. `hard links skipped` was therefore not 0 for
        the tools half of the corpus — it did not EXIST, and every consumer
        reading it as `.get(k, 0)` printed 0 and was believed. main() has
        counted the same thing for the Claude half since it was written
        (`hard_links += 1`), so one program held two answers to one question
        and published the emptier one.

        The aggregate key is inserted BEFORE the per-path key and neither
        per-path key repeats the aggregate's words, so a reader searching the
        ledger by name cannot pick up a detail line instead of the count.
        """
        skipped[kind] += 1
        skipped[f"{detail}: {label}/{pathlib.Path(rel).as_posix()}"
                f" (kept {first})"] += 1

    def note_alarm(label, rel, first):
        """Two records with the same bytes. NEITHER IS DROPPED. Both are named.

        note_dup() above records a file that was SUPPRESSED; this records one
        that was KEPT and is evidence of a collection bug. They are deliberately
        two functions writing two vocabularies, because the one thing this must
        never turn back into is a counter that reads like a win while history
        goes missing under it.

        `(kept X)` is note_dup's word for the copy that survived a suppression
        and would be a lie here — both survive. `also at X` says the true thing:
        the same bytes are in the corpus twice, under two names, and somebody
        has to decide which one is the record.
        """
        skipped[IDENTICAL_RECORDS] += 1
        skipped[f"{IDENTICAL_DETAIL}: {label}/{pathlib.Path(rel).as_posix()}"
                f" also at {first}"] += 1

    per_tool = defaultdict(lambda: {"files": 0, "bytes": 0, "origins": set(),
                                    "opaque": 0, "opaque_bytes": 0})
    # Live and archive are the SAME inode — the archive is hard links. Deduping
    # on (device, inode) is what stops every byte being counted and written twice.
    seen = {}
    # AND A COPY IS NOT A HARD LINK — BUT IT IS NOT A DUPLICATE TO DELETE
    # EITHER. A copy is a DIFFERENT inode holding the same bytes, so the map
    # above cannot see it, and this one is what sees it. It used to suppress the
    # second copy. It does not any more, and the reason is a ruling, not a
    # preference:
    #
    #   Two real transcripts cannot be byte-identical, and across two different
    #   computers it is impossible. Identical content is therefore NOT a
    #   duplicate to suppress — it is evidence we collected the wrong thing.
    #
    # The measurement says the same thing. Read-only over this machine's real
    # stores, 11,865 files offered to the walk:
    #
    #     key = (size, sha256)                    4,610 suppressed
    #     key = (label, parent dir, size, sha256)    138 suppressed
    #
    # 4,472 of that difference is `copilot/<session-uuid>/checkpoints/index.md`,
    # a 172-character stub copilot writes into EVERY session directory. Those
    # are not one record under many names; they are BOILERPLATE, and the right
    # response to 4,472 copies of it was never to dedup them — it was to stop
    # collecting them. Suppressing instead left whichever session sorted first
    # holding the only copy and published the loss as "4,610 duplicates
    # skipped", which reads as a win.
    #
    # The remaining 138 are pairs like `<session>/.system_generated/logs/
    # transcript.jsonl` beside `transcript_full.jsonl` — ONE conversation the
    # tool wrote twice. Which of the two is the record is a collection question,
    # and this program is not entitled to guess at it by sort order. So both are
    # exported and the pair is named.
    #
    # WHAT IS ASKED IS "IS THIS A RECORD", AND CONFIG IS DELIBERATELY EXEMPT.
    # Five computers really do have the same settings.json; identical CONFIG is
    # normal and expected and alarming on it is exactly how the greedy rule got
    # written in the first place. The record test is not a new list — it is the
    # rule the walk ALREADY used to admit the file: everything on the recursive
    # path has passed `not _is_config`, and a root file is a record when
    # `_is_loose_record` says so rather than because a store's tuple named it.
    # `proteus-root/stats-cache.json` is admitted by tuple and is not a record.
    #
    # Keyed on the DECODED text, not the raw bytes, because the text is what
    # gets written and read_text() has already folded CRLF. Zero-length files
    # are exempt: they are all "identical" to each other, and an alarm on every
    # pair of empty files is noise in front of the one signal this exists for.
    #
    # NOT SCOPED TO A DIRECTORY. The old key carried (label, parent dir) to hold
    # the suppression down to where it was survivable. Nothing is suppressed
    # now, so the scope that made deletion safe would only make the alarm blind:
    # the boilerplate case is identical bytes in two DIFFERENT directories, and
    # that is the case worth hearing about.
    seen_bytes = {}

    for label, root, origin, top_only in _tool_roots(home, archive_other):
        store = BY_LABEL.get(label)
        if root.is_file():                       # ~/.ollama/history is a file
            walk = [root]
            root = root.parent
        elif top_only:
            # NOT recursive by definition (see stores.py), so os.walk buys
            # nothing here — but a root that cannot be listed still has to be
            # said out loud rather than raising out of the whole export.
            try:
                walk = sorted(p for p in root.iterdir() if p.is_file())
            except OSError:
                note_dir(label, root, root, "could not be read")
                continue
        else:
            # ONE WALK, PRUNED BY THE STORE'S OWN PATTERN. `records is not
            # None`, not truthiness: `records=()` means the store has SAID it
            # keeps no records here, and the honest walk for that is the empty
            # one. Under truthiness it fell through to a full recursion and
            # exported the whole tree — the store's own statement read as
            # silence.
            #
            # The prune is what makes walking affordable where the old picker
            # was globbing to stay cheap: copilot-chat's root is 4.5 GB of other
            # extensions' state, and _record_prune stops at the first component
            # that cannot lead to a record. What is a record is still decided
            # below, by store.is_record, which is the rule the archiver uses too.
            keep = (_record_prune(store.records)
                    if store is not None and store.records is not None else None)
            walk, blind, links = walk_tree(root, keep_dir=keep)
            for b in blind:
                note_dir(label, b["path"], root, b["reason"])
            for lk in links:
                note_link(label, lk, root)
        for src in walk:
            if not src.is_file():
                continue
            rel = src.relative_to(root)
            # THE WHITELIST DECIDES ONLY WHERE THE STORE HAS NOT.
            #
            # This ran BEFORE the records test, so `records=` could only ever
            # NARROW a root_files store and never ADMIT anything:
            # _is_loose_record('session-store.db') is False and
            # _is_loose_record('stats-cache.json') is False, so naming either
            # one in a tuple did not let it through. The first is 1,822,720 B
            # holding 38 sessions and 370 turns.
            #
            # `_is_config` STAYS ON THIS PATH, and that is the difference
            # between this program and the archiver. A store's records tuple is
            # read by both, and the two are not owed the same answer: the
            # archiver ships nothing, so it keeps whatever the tuple names,
            # while this one copies bytes into a corpus that gets published. A
            # tuple is permission to look at a file, not permission to ship one
            # whose NAME is config or a credential in every tool that uses it.
            # Without this clause a records tuple would be the one way into the
            # corpus with no NEVER_EXPORT check at all — top_only skips the
            # `not top_only and _is_config(src)` test below.
            if top_only and not _is_loose_record(src) and (
                    store is None or store.records is None or _is_config(src)):
                refuse(label, rel, "config, not a record")
                continue
            # The archive is walked by directory NAME, so a store with a records
            # glob has to be re-checked here or its archived copy comes in whole.
            if store is not None and not store.is_record(rel):
                skipped["not a record for this store"] += 1
                continue
            if not top_only and any(vendor_dir(p) for p in rel.parts[:-1]):
                skipped["vendored"] += 1
                continue
            # Applies to every file from every source, live or archive, at any
            # depth. This is the check oauth_creds.json got past.
            #
            # ASKED PER COMPONENT, NORMALISED, exactly as retention_guard does.
            # `set(...) & SECRET_DIRS` was an exact, case-sensitive,
            # dot-sensitive intersection, so of mcp-secrets/ MCP-Secrets/
            # Credentials/ .credentials/ only the first spelling was refused —
            # and this program SHIPS. A missed secret directory in the archiver
            # costs 0 bytes (a hard link to a file already on the disk); a
            # missed one here puts the bytes in a published corpus. The
            # recursive walk of ~/.ai-logs-archive/other/<label> is exactly the
            # path by which oauth_creds.json reached the corpus once before.
            if any(secret_dir(p) for p in rel.parts[:-1]):
                refuse(label, rel, "secret directory")
                continue
            # AND THE NAME ON THE LINK IS NOT THE NAME OF THE BYTES. Every test
            # above reads `rel`, which is the name the WALK found; this program
            # then opens `src`, which for a symlink is a different file with a
            # different name in a different directory. `session.jsonl ->
            # credentials.json` passed all of them and shipped.
            if secret_symlink_target(src):
                refuse(label, rel, "symlink to a credential")
                continue
            if not top_only and _is_config(src):
                refuse(label, rel, "config, not a record")
                continue
            ext = src.suffix.lower()
            if ext in VENDOR_EXT:
                skipped["vendored"] += 1
                continue
            try:
                st = src.stat()
            except OSError:
                skipped["unreadable"] += 1
                continue
            inode = (st.st_dev, st.st_ino)
            if inode in seen:
                note_dup("hard links skipped", "second name for one inode",
                         label, rel, seen[inode])
                continue
            seen[inode] = f"{label}/{rel.as_posix()}"
            if ext in OPAQUE_EXT:
                per_tool[label]["opaque"] += 1
                per_tool[label]["opaque_bytes"] += st.st_size
                skipped["binary, unredactable"] += 1
                continue
            try:
                raw = src.read_text(encoding="utf-8", errors="replace")
            except OSError:
                skipped["unreadable"] += 1
                continue
            # THE ALARM. No `continue` under it, on purpose — see seen_bytes.
            #
            # `top_only and not _is_loose_record(src)` is the config exemption,
            # and it is the walk's own admission rule read back: a file on the
            # recursive path is here because it passed `not _is_config(src)`,
            # while a root file can be here purely because a store's records
            # tuple named it. The second kind is `stats-cache.json`, which five
            # machines may legitimately hold identically.
            if raw and not (top_only and not _is_loose_record(src)):
                key = (len(raw),
                       hashlib.sha256(raw.encode("utf-8")).hexdigest())
                if key in seen_bytes:
                    note_alarm(label, rel, seen_bytes[key])
                else:
                    seen_bytes[key] = f"{label}/{rel.as_posix()}"
            text = _redact_text(src, raw, red)
            text, lone = _no_lone_surrogates(text)
            if lone:
                skipped[f"lone surrogates replaced ({label})"] += lone
            dest = out_root / label / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            per_tool[label]["files"] += 1
            per_tool[label]["bytes"] += write_text(dest, text)
            per_tool[label]["origins"].add(origin)

    summary = []
    for label in sorted(per_tool):
        d = per_tool[label]
        if not (d["files"] or d["opaque"]):
            continue
        s = BY_LABEL.get(label)
        summary.append({"tool": label, "counted_by": (s.cli if s else None),
                        "files": d["files"], "bytes": d["bytes"],
                        "origins": sorted(d["origins"]),
                        "not_exported_binary": d["opaque"],
                        "not_exported_bytes": d["opaque_bytes"]})
    return summary, rows, dict(skipped)


_LONE_SURROGATE = re.compile(r"[\ud800-\udfff]")


def _no_lone_surrogates(text):
    """(clean text, how many were replaced). A lone surrogate cannot be written.

    JSON permits any \\udXXX escape, including an unpaired one, and json.loads
    turns it into a real lone surrogate — which has no UTF-8 encoding at all.
    Reading with errors="replace" does not help: that only handles bad BYTES on
    the way in, and these arrive as a well-formed ESCAPE that decodes to an
    unencodable character.

    Three characters in 2.29 GB killed the entire export:

        UnicodeEncodeError: 'utf-8' codec can't encode character '\\udc80'
        in position 23082819: surrogates not allowed

    from two copilot-chat transcripts carrying `"text": "- \\udc80 Intelligent
    Node Killer"` — somebody's mangled emoji, stored faithfully by VS Code. And
    it is not a lost file, it is a lost RUN: run.py calls export_corpus.py
    through sh(), which raises SystemExit on a non-zero return, so the whole
    update aborts and the machine records nothing.

    Replaced with U+FFFD, the same character errors="replace" would have used
    had the problem been bytes. COUNTED and reported, not silently repaired:
    the corpus is a record, and a record that quietly edits itself is worth
    less than one that says where it was damaged.
    """
    if not _LONE_SURROGATE.search(text):
        return text, 0
    out, n = _LONE_SURROGATE.subn("�", text)
    return out, n


def _redact_text(src, raw, red):
    """Redact a file whatever shape it is. JSONL line-wise, JSON whole, else text.

    Every one of these is somebody's conversation store: Claude and copilot write
    JSONL, lmstudio and kilocode write one JSON document, proteus writes Markdown.
    The Redactor works on all of them because it scrubs STRINGS — including the
    secrets people paste into conversations, which is why a transcript holding an
    API key is kept and cleaned rather than dropped.
    """
    red.stats["files"] += 1
    if src.suffix.lower() in (".jsonl", ".ndjson") or (raw.lstrip()[:1] == "{" and "\n{" in raw):
        keep = []
        for ln in raw.splitlines():
            ln = ln.strip()
            if not ln:
                continue
            red.stats["lines"] += 1
            try:
                keep.append(json.dumps(red.walk(json.loads(ln)), ensure_ascii=False))
            except Exception:
                # Not JSON after all. Scrub as prose rather than drop a line of
                # somebody's history because a format guess was wrong.
                keep.append(red.scrub(ln))
        return "\n".join(keep) + "\n"
    try:
        return json.dumps(red.walk(json.loads(raw)), ensure_ascii=False, indent=1)
    except Exception:
        red.stats["lines"] += raw.count("\n")
        return red.scrub(raw)



# ---------------------------------------------------------------- export

# NAME_MAX in BYTES. 255 on ext4, xfs, btrfs and APFS; 143 under eCryptfs, which
# is why the destination is asked rather than assumed. Bytes, not characters:
# the kernel limit is on the encoded name, so a UTF-8 name has to be measured
# and cut as bytes or the cut lands mid-character.
NAME_MAX_FALLBACK = 255


def _name_max(d):
    try:
        return min(int(os.pathconf(d, "PC_NAME_MAX")), NAME_MAX_FALLBACK)
    except (OSError, ValueError, AttributeError):
        return NAME_MAX_FALLBACK


def folded_name(rel):
    """The name a transcript at `rel` gets before any bound is applied.

    A function rather than an expression because main() has to ask which BOUND
    shortened a name, and re-deriving the fold there is how the two answers
    drift apart.
    """
    return rel.name if rel.parent == pathlib.Path(".") else "__".join(rel.parts)


def path_limit(dest_dir):
    """The widest NAME that still fits inside a 260-character path.

    NAME_MAX bounds the component and NOTHING bounded the path. Windows caps
    the whole path at 260 characters, not the component, so a name that is
    legal on ext4 and legal as a 255-byte component is refused the moment it
    sits more than a few characters below the drive. Measured on this fleet: a
    live archive path is already 262 characters under a C:\\Users\\ prefix.

    And a refusal here is not one lost file. run.py calls this program through
    sh(), which raises SystemExit on a non-zero return, so one long path loses
    a RUN — the machine records nothing at all that day.

    Applied on every platform rather than behind a `platform.system()` test,
    because the corpus is written on one machine and checked out on the others.
    A bound that only exists on Windows produces names a Windows checkout
    cannot hold.
    """
    return MAX_PATH - len(str(dest_dir)) - 1


def out_name(rel, limit, taken=()):
    """Output filename for a transcript at `rel` inside its project directory.

    The consuming tool reads projects/<proj>/*.jsonl and nothing deeper, so the
    corpus stays exactly two levels and the depth is folded into the NAME.

    It cannot be `f.name`. 111 of these files share a basename with another file
    in the same project — agent-*.jsonl repeats across sessions — so recursing
    and then writing f.name walks the whole tree and silently overwrites 111 of
    what it walked, which is the same data loss wearing a different hat.

    And it cannot be the bare `"__".join(rel.parts)` either, which is the defect
    this function exists to hold. `f.name` could never break NAME_MAX because it
    came OFF a filesystem and was bounded by construction. A folded name is
    INVENTED here, and its length is the sum of every component on the path:
    two legal 120-byte directories and a 20-byte file make a legal path and a
    264-byte filename, and the write raises OSError [Errno 36] File name too
    long. Uncaught, mid-run, so one long path anywhere kills the whole export.

    Two rules, and both have to hold at once:

      bounded     no name longer than `limit`, in bytes. `limit` is the TIGHTER
                  of two different bounds and the caller works out which:
                  the destination's NAME_MAX, which bounds the component, and
                  path_limit(), which bounds the whole path at 260. They fail
                  differently and they are reported apart — see main().
      injective   two source paths never land on one output name

    Truncation alone satisfies the first and destroys the second. So a name over
    the limit is cut and given a 12-hex-digit SHA-1 of the FULL relative path,
    which is what carries the distinction the truncated part used to: 48 bits
    against the 3,394 distinct transcripts on this machine is a ~1e-10 chance of
    one collision. `taken` catches the remaining case — two real paths that fold
    onto one name under the limit, "a/b.jsonl" against a real "a__b.jsonl",
    measured 0 across all 23 profiles here — and resolves it the same way.

    Depth-0 files keep their exact name, so the 5,896 already in the corpus do
    not churn; the bound is applied to them too, in case a name that was legal
    on the source filesystem is too long for the destination's.
    """
    name = folded_name(rel)
    if len(name.encode()) <= limit and name not in taken:
        return name
    tail = "__" + hashlib.sha1(rel.as_posix().encode()).hexdigest()[:12] + ".jsonl"
    stem = name[:-len(".jsonl")] if name.endswith(".jsonl") else name
    # Cut on encoded bytes, then decode discarding a partial character.
    stem = stem.encode()[:max(limit - len(tail), 0)].decode("utf-8", "ignore")
    return stem + tail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None, help="output dir (default: corpus/<machine>)")
    ap.add_argument("--home", default=str(pathlib.Path.home()))
    ap.add_argument("--keep-email", default="alexander.sorrell.it@gmail.com",
                    help="the one address kept for attribution; '' to redact all")
    ap.add_argument("--archive", default="~/.ai-logs-archive/claude",
                    help="hard-link archive of transcripts Claude has since deleted "
                         "(retention_guard.py); '' to export live profiles only")
    ap.add_argument("--archive-other", default="~/.ai-logs-archive/other",
                    help="hard-link archive for every non-Claude CLI")
    args = ap.parse_args()

    root = pathlib.Path(__file__).parent
    home = pathlib.Path(args.home)

    machine = "unknown-machine"
    for d in root.iterdir():
        mid = d / ".machine-id" if d.is_dir() else None
        if mid and mid.is_file():
            try:
                if json.loads(mid.read_text()).get("hostname") == __import__("platform").node():
                    machine = d.name
                    break
            except Exception:
                pass

    out = pathlib.Path(args.out) if args.out else root / "corpus" / machine
    dst = out / ".claude" / "projects"
    if out.exists():
        shutil.rmtree(out)
    dst.mkdir(parents=True)

    red = Redactor(home, args.keep_email)
    # Every profile, not just ~/.claude — the tool that consumes this reads one
    # hardcoded directory, which on this fleet is the idle one. Merging them here
    # is the whole point: it is the same person's work either way.
    seq = 0
    seen_uuid = set()
    # One set for the whole walk, live profiles and archive together: that span
    # is half of export_tools' rule and the half that does the work.
    seen_inode = set()
    hard_links = unreadable = no_unique_rows = 0
    # THE TWO BOUNDS ARE COUNTED APART BECAUSE THEY HAVE DIFFERENT REMEDIES.
    # Shortened-for-PATH is fixed by exporting somewhere shallower; the name
    # itself was fine. Shortened-for-NAME_MAX is fixed by nothing — the name is
    # simply longer than any filesystem here will hold. One counter for both
    # tells an operator a number and not which of the two they are looking at.
    short_for_path = short_for_name = short_for_collision = over_budget = 0
    name_max = _name_max(dst)
    # Directories the walk could not enumerate, and symlinked directories it
    # followed. Both NAMED. `blind` is the signature bug of this repository and
    # a count with no name cannot be acted on.
    blind_dirs, followed = [], []

    def under_home(p):
        """A path as the manifest should say it: relative to home where it is."""
        try:
            return pathlib.Path(p).relative_to(home).as_posix()
        except ValueError:
            return str(p)

    manifest = []
    # Same discovery as the counter, deliberately shared rather than repeated:
    # this file used to carry its own `home.glob(".*claude*")`, which meant the
    # corpus and the token totals could disagree about what a machine even has.
    # Profiles are found by shape — a directory with projects/*.jsonl under it —
    # so a config dir outside $HOME is exported rather than silently skipped.
    # Safe because seen_uuid above spans every profile: a copy adds nothing.
    from analyze_tokens import find_config_dirs

    # The LIVE profiles, plus the hard-link archive.
    #
    # Live profiles only ever hold what survived: Claude Code deletes session
    # files older than cleanupPeriodDays at startup, per profile, and the
    # profile in daily use is therefore the one holding the least. Measured on
    # this machine before the archive existed: .claude-alt held 32 days while
    # dormant profiles still held 87 and 202, and every one of them was one
    # launch away from losing the difference.
    #
    # ~/.ai-logs-archive holds a hard link to every transcript ever written
    # (retention_guard.py). A hard link is a second NAME for the same inode, so
    # when Claude unlinks its own name the data survives here at no disk cost.
    # Exporting from both means the corpus keeps work whose original is gone.
    #
    # Duplicates are free: seen_uuid above spans every profile, so a transcript
    # reachable by both paths is counted once.
    sources = list(find_config_dirs(home))
    archive = pathlib.Path(args.archive).expanduser() if args.archive else None
    if archive and archive.is_dir():
        for prof in sorted(p for p in archive.iterdir() if p.is_dir()):
            if (prof / "projects").is_dir():
                sources.append(prof)

    for cfg in sources:
        if not (cfg / "projects").is_dir():
            continue
        try:
            projects = sorted(p for p in (cfg / "projects").iterdir()
                              if p.is_dir())
        except OSError:
            # A profile whose projects/ cannot be listed used to take the whole
            # export down with it — and with run.py's sh() that is a RUN, not a
            # profile. Said out loud instead.
            blind_dirs.append({"path": under_home(cfg / "projects"),
                               "reason": "could not be read"})
            continue
        for proj in projects:
            # rglob, NOT glob. The flat glob that stood here was the FOURTH
            # copy of one defect: sessions.py, count_corpus.py and
            # corpus_reports.py were all widened on 2026-08-09 and this file
            # was missed because nobody checked whether the pattern existed
            # anywhere else. Subagent and workflow transcripts sit one and two
            # levels down — projects/<proj>/<session-uuid>/subagents/agent-*.jsonl
            # and .../subagents/workflows/wf_*/agent-*.jsonl — and they are
            # separate API conversations that every reader in this repo counts.
            #
            # Measured here before the change: 5,896 of 8,675 live transcripts
            # exported, 68.0%; 2,779 files / 792,295,606 bytes copied nowhere.
            # In .claude-alt — the profile in daily use, and therefore the one
            # Claude Code's cleanupPeriodDays empties first — it was 30 of 909,
            # 3.3%. 577 of the missed files had no copy under
            # ~/deadreckon-record at all (124,692,204 bytes, 588,728,384
            # tokens), which the next launch turns into a permanent loss.
            #
            # AND NOT rglob EITHER, for the reason walk_tree exists: rglob
            # cannot report the directory it could not enter, and does not
            # descend a symlinked one. Both were measured here.
            #
            # The suffix test folds case, which `rglob("*.jsonl")` does not:
            # pathlib runs both sides through os.path.normcase, identity on
            # posix, so on the two machines in this fleet with a
            # case-insensitive filesystem a transcript written `Session.JSONL`
            # EXISTS and matches nothing. That is the same disagreement
            # _record_prune was written for, one directory over.
            found, blind, links = walk_tree(proj)
            for b in blind:
                blind_dirs.append({"path": under_home(b["path"]),
                                   "reason": b["reason"]})
            for lk in links:
                followed.append({"path": under_home(lk["path"]),
                                 "target": under_home(lk["target"])})
            files = [p for p in found if p.suffix.lower() == ".jsonl"]
            if not files:
                continue
            seq += 1
            od = dst / f"-workspace-p{seq:03d}"
            od.mkdir(parents=True, exist_ok=True)
            # The path budget is a property of THIS destination directory, so
            # it is worked out here and not once for the whole run.
            budget = path_limit(od)
            limit = min(name_max, budget)
            written = set()
            for f in files:
                # export_tools' rule, whole, not a third of it: the key is
                # (st_dev, st_ino); the stat is guarded and a file that cannot
                # be stat'd is skipped and COUNTED, not crashed on; the check
                # runs before the read, once per file; and the set spans every
                # source in the walk, live and archive alike. The archive is
                # hard links — a second NAME for the same inode — so without
                # this the same transcript is read, redacted and written twice
                # under two names. 10,312 of the 13,706 files reachable on this
                # machine are hard links to one already in.
                #
                # It is load-bearing for the write below, not an optimisation.
                # Now that existence alone earns a file in the corpus, skipping
                # the second name for one inode is the only thing standing
                # between the corpus and 10,312 empty files.
                try:
                    st = f.stat()
                except OSError:
                    unreadable += 1
                    continue
                if (st.st_dev, st.st_ino) in seen_inode:
                    hard_links += 1
                    continue
                seen_inode.add((st.st_dev, st.st_ino))
                red.stats["files"] += 1
                lines = []
                for ln in f.open(encoding="utf-8", errors="replace"):
                    ln = ln.strip()
                    if not ln:
                        continue
                    red.stats["lines"] += 1
                    try:
                        o = json.loads(ln)
                    except Exception:
                        red.stats["dropped"] += 1
                        continue
                    # Resumed sessions rewrite earlier turns into the new file and
                    # subagent turns are inlined into the parent, so the same uuid
                    # appears more than once. Dropping repeats keeps any total
                    # derived from this corpus honest.
                    u = o.get("uuid")
                    if u:
                        if u in seen_uuid:
                            continue
                        seen_uuid.add(u)
                    lines.append(json.dumps(red.walk(o), ensure_ascii=False))
                # WRITTEN WHETHER OR NOT `lines` IS EMPTY. This was `if lines:`,
                # and the decision it made silently is the one that has to be
                # made out loud: a file's EXISTENCE and a file's CONTENT are two
                # different facts, and only one of them can be shared.
                #
                # The dedup above is row-level and global, so a transcript whose
                # every row was already claimed by a file that sorted earlier
                # produced no lines and was written nowhere. It happens for real
                # in two shapes: subagent turns inlined into the parent, and a
                # resumed session rewriting earlier turns into a new file.
                # Measured on this machine, after the inode rule has taken the
                # hard links out: 1,482 distinct transcripts, 435,152,279 bytes,
                # walked, read, redacted and dropped on the floor.
                #
                # So: existence is preserved unconditionally, content stays
                # deduplicated. A file that contributed no unique row is written
                # EMPTY — the transcript is in the corpus, every one of its rows
                # is in the corpus, and no row is counted twice. The two
                # alternatives were both worse. Writing its rows again inflates
                # any naive sum over the corpus and re-adds 435 MB of text that
                # is already there; leaving it out is the bug. Counted below and
                # reported in the manifest, because a corpus that quietly omits
                # is worth less than one that says what it did.
                rel = f.relative_to(proj)
                natural = folded_name(rel)
                name = out_name(rel, limit, written)
                # WHICH BOUND BIT, asked once, here, where both are known.
                # Attributed to the bound that was actually exceeded — NAME_MAX
                # first, because a name over it is over it on every
                # destination, while the path budget moves with where the
                # corpus is written.
                if name != natural:
                    if len(natural.encode()) > name_max:
                        short_for_name += 1
                    elif len(natural.encode()) > budget:
                        short_for_path += 1
                    else:
                        short_for_collision += 1
                if len(name.encode()) > limit:
                    # Even the 20-byte hash tail does not fit. Nothing this
                    # function can do makes the path legal; the destination is
                    # too deep. Reported rather than written and forgotten.
                    over_budget += 1
                written.add(name)
                if lines:
                    write_text(od / name, "\n".join(lines) + "\n")
                else:
                    no_unique_rows += 1
                    write_text(od / name, "")
            # Relative to home, not cfg.name: a profile found outside the home
            # directory is still called ".claude", so four of them collapsed
            # onto the real ~/.claude and the manifest under-reported what had
            # actually been read.
            try:
                label = str(cfg.relative_to(home))
            except ValueError:
                label = str(cfg)
            manifest.append({"profile": label, "source_project": proj.name,
                             "exported_as": od.name, "files": len(files)})

    # Every other CLI. Same redactor, so one pass of statistics covers the whole
    # corpus and "how much was removed" stays answerable for all of it.
    tools, refused, tool_skips = export_tools(
        out / "tools", home,
        pathlib.Path(os.path.expanduser(args.archive_other)) if args.archive_other else None,
        red)

    # EVERY FILE, not `rglob("*.jsonl")`. The walk above now admits a transcript
    # spelled `Session.JSONL` — it exists on the two case-insensitive machines
    # in this fleet and matched nothing before — and that file keeps its own
    # name in the corpus. A size that only counts one spelling would report the
    # newly-rescued transcripts as weighing nothing, which is the same defect
    # this pass exists to close, one measurement further down.
    size = sum(f.stat().st_size for f in dst.rglob("*") if f.is_file())
    # THE ALARM GETS ITS OWN FIELD, not a needle in the skip ledger. Everything
    # else in tool_files_skipped is a file that did NOT arrive; these arrived,
    # twice, and a consumer should not have to substring-match a counter's name
    # to find out that the collector is picking up something that is not a
    # record. Count and names both, for the same reason as the blind directories
    # above: a number nobody can trace to a file cannot be acted on.
    identical = sorted(k[len(IDENTICAL_DETAIL) + 2:] for k in tool_skips
                       if k.startswith(IDENTICAL_DETAIL + ": "))
    write_text(paths.machine(out) / "MANIFEST.json", json.dumps({
        "machine": machine,
        "tools": tools,
        "tool_files_refused": refused,
        "tool_files_skipped": tool_skips,
        "identical_record_content": tool_skips.get(IDENTICAL_RECORDS, 0),
        "identical_record_content_detail": identical,
        "generated_at": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"),
        "profiles": sorted({m["profile"] for m in manifest}),
        "projects": len(manifest),
        "files": red.stats["files"],
        "hard_links_skipped": hard_links,
        "files_unreadable": unreadable,
        # NAMED, not only counted. A directory that could not be entered
        # withheld everything under it and there is no per-file line that can
        # say so, because the files were never seen. Without the names an
        # operator is told a number and cannot find the directory it is about.
        "directories_not_enumerated": len(blind_dirs),
        "directories_not_enumerated_detail": blind_dirs,
        "symlinked_directories_followed": len(followed),
        "symlinked_directories_followed_detail": followed,
        "files_without_a_unique_row": no_unique_rows,
        # Two bounds, two remedies, two counters. See the note where they are
        # incremented.
        "names_shortened_for_name_max": short_for_name,
        "names_shortened_for_path": short_for_path,
        "names_shortened_for_collision": short_for_collision,
        "names_over_budget": over_budget,
        "name_max": name_max,
        "lines_kept": len(seen_uuid) or red.stats["lines"],
        "bytes": size,
        "redactions": {k: v for k, v in red.stats.items()
                       if k in ("topic", "span", "path", "email")},
        "mapping": manifest,
    }, indent=1))

    # A corpus nobody can interpret is a pile of files. Whoever receives this
    # needs to know what was removed, what was kept, and how to check both
    # without taking anyone's word for it.
    kept = len(seen_uuid)
    profs = ", ".join(f"`{x}`" for x in sorted({m["profile"] for m in manifest}))
    stamp = __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds")
    write_text(out / "README.md", f"""# Claude Code transcripts — {machine}

Redacted export of real Claude Code sessions from one computer, produced by
`export_corpus.py`. Generated {stamp}.

| | |
|---|---|
| machine | `{machine}` |
| profiles merged | {profs} |
| projects | {len(manifest)} |
| transcript files | {red.stats["files"]} exported, {hard_links} skipped as hard links to one of them |
| lines | {red.stats["lines"]:,} read, {kept:,} kept after de-duplication |
| size | {size/1e6:.1f} MB |

{no_unique_rows} of the exported files are empty. Every transcript that exists is
in this corpus, but rows are de-duplicated across all of them: a subagent's turns
are inlined into its parent, and a resumed session rewrites earlier turns into a
new file, so the same row uuid arrives more than once. Whichever file is read
first keeps the row. A file whose every row was kept elsewhere is still exported,
because it existed — it is empty rather than absent, and no row is counted twice.

## Why several profiles are merged

Claude Code keeps a separate directory per account, selected by
`CLAUDE_CONFIG_DIR`. Tools that read `~/.claude` alone see one of them. On this
machine that is the idle profile, so a single-directory read misses most of the
work. All profiles are merged here because it is the same person's work either
way.

## What was removed

| | count |
|---|---:|
| secrets (API keys, tokens, JWTs, private keys) | {red.stats["span"]:,} |
| filesystem paths | {red.stats["path"]:,} |
| third-party email addresses | {red.stats["email"]:,} |
| protected project names | {red.stats["topic"]:,} |

Secrets are removed because transcripts genuinely contain them — live GitHub
tokens, API keys, JWTs pasted into or echoed by a session. Anything shaped like
a credential is replaced whether or not it is still valid.

Only the protected **term** is replaced, never the message around it. Replacing
whole messages was tried first and destroyed 55% of the prompts, taking the
substance with them. The sentence around a term is the work.

Keys are scrubbed as well as values: some tools store their prompt text as a
dictionary key, so scrubbing only values leaves it readable.

## What was deliberately kept

Timestamps, session ids, message uuids, parent links, model names and `usage`
blocks are untouched. Any figure derived from this corpus can therefore be
recomputed from it. A corpus you cannot check against is a claim, not evidence.

Project directories are renamed `-workspace-pNNN`; their real names identify
private repositories. How many projects there are, and how work is distributed
across them, survives the renaming.

## Verifying it yourself

```bash
python3 -c "
import re,json,pathlib
P={{'secret':r'gh[pousr]_[A-Za-z0-9]{{30,}}|sk-ant-[A-Za-z0-9_-]{{20,}}|AIza[0-9A-Za-z_-]{{35}}',
   'home dir':r'/home/[A-Za-z0-9._-]+|/Users/[A-Za-z0-9._-]+|/root/'}}
bad={{k:0 for k in P}}
def v(o):
    if isinstance(o,dict):
        for k,x in o.items(): v(k); v(x)
    elif isinstance(o,list): [v(x) for x in o]
    elif isinstance(o,str):
        for k,p in P.items(): bad[k]+=len(re.findall(p,o))
for f in pathlib.Path('.').rglob('*.jsonl'):
    for ln in f.open(errors='ignore'):
        try: v(json.loads(ln))
        except Exception: pass
print(bad)"
```

Check the **decoded JSON**, not the raw bytes. Scanning raw text reports
`\n@pytest.fixture` and `\n@mcp.tool` as email addresses — every one a Python
decorator following an escaped newline.

## Using it

Point a profile tool at this directory as if it were a home directory:

```bash
HOME=$(pwd) npx standout ...
```

`.claude/projects/` sits at the root of this folder for exactly that reason.

`MANIFEST.json` maps every exported project directory back to the profile and
source directory it came from.
""")

    print(f"  machine        {machine}")
    print(f"  profiles       {sorted({m['profile'] for m in manifest})}")
    print(f"  projects       {len(manifest)}")
    print(f"  files          {red.stats['files']}")
    print(f"  lines          {red.stats['lines']:,} read, {len(seen_uuid):,} unique kept")
    print(f"  redactions     topic {red.stats['topic']:,}  secrets {red.stats['span']:,}  "
          f"paths {red.stats['path']:,}  emails {red.stats['email']:,}")
    print(f"  size           {size/1e6:.1f} MB")
    if tools:
        tb = sum(t["bytes"] for t in tools)
        tf = sum(t["files"] for t in tools)
        print(f"  other CLIs     {len(tools)} tools, {tf:,} files, {tb/1e6:.1f} MB")
        for t in tools:
            extra = (f"   [{t['not_exported_binary']} binary not exported, "
                     f"{t['not_exported_bytes']/1e6:.1f} MB]"
                     if t["not_exported_binary"] else "")
            print(f"    {t['tool']:<24}{t['files']:>7,} files {t['bytes']/1e6:>8.1f} MB"
                  f"  {'+'.join(t['origins'])}{extra}")
    # `reason`, which is the key refuse() writes. This read `r['why']` — a key
    # no line in this file has ever written — so the moment the ledger had
    # anything to say, the print raised KeyError and run.py's sh() turned that
    # into SystemExit. A security ledger that kills the run when it is
    # non-empty is worse than the empty list it replaced.
    for r in refused:
        print(f"  REFUSED        {r['tool']}/{r['path']} — {r['reason']}")
    # LOUD, BECAUSE IT IS A COLLECTION BUG AND NOT A STATISTIC. Two real
    # transcripts cannot hold the same bytes, so every line here is a file the
    # collector should probably not be picking up at all. Nothing was dropped to
    # produce it; the remedy is upstream, in what gets collected.
    if identical:
        print(f"  ALARM          {len(identical)} record(s) whose bytes are"
              f" already in this corpus — NOTHING WAS DROPPED:")
        for line in identical:
            print(f"    {line}")
        print("    two real transcripts cannot be byte-identical; this is the"
              " collector picking up something that is not a record")
    if blind_dirs:
        print(f"  NOT ENUMERATED {len(blind_dirs)} directories:")
        for b in blind_dirs:
            print(f"    {b['path']} — {b['reason']}")
    if followed:
        print(f"  FOLLOWED       {len(followed)} symlinked directories:")
        for lk in followed:
            print(f"    {lk['path']} -> {lk['target']}")
    if short_for_path or short_for_name or over_budget:
        print(f"  shortened      {short_for_name} over NAME_MAX ({name_max}), "
              f"{short_for_path} over the {MAX_PATH}-char path budget, "
              f"{short_for_collision} to break a collision, "
              f"{over_budget} that still do not fit")
    # The alarm keys live in the same Counter — it is the general ledger, and
    # `symlinked directories followed` is not a skip either — but they are the
    # one entry in it about files that DID arrive, and printing those under the
    # word "skipped" is the exact misreading this whole change is against. They
    # have their own block above.
    plain = {k: v for k, v in tool_skips.items()
             if k != IDENTICAL_RECORDS and not k.startswith(IDENTICAL_DETAIL + ": ")}
    if plain:
        print("  skipped        " + ", ".join(f"{v:,} {k}" for k, v in sorted(plain.items())))
    print(f"  wrote          {out}")


if __name__ == "__main__":
    main()
