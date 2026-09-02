#!/usr/bin/env python3
"""Count Claude Code token usage per account, from the local session files.

Claude Code stores every session as JSONL:

    <config-dir>/projects/<slugified-cwd>/<session-uuid>.jsonl

One JSON object per line. Assistant turns carry `message.usage`, which is the
API's own accounting — not an estimate:

    input_tokens                   uncached prompt tokens
    cache_creation_input_tokens    tokens written into the prompt cache
    cache_read_input_tokens        tokens served from cache
    output_tokens                  generated tokens

Which config dir is used is keyed by $CLAUDE_CONFIG_DIR, so one machine can hold
several accounts side by side. Each dir's own .claude.json names the account it
is signed into, so accounts are read from the data rather than assumed.

Usage:
    python3 analyze_tokens.py                     # scan, print, write ./out
    python3 analyze_tokens.py --out DIR           # choose output dir
    python3 analyze_tokens.py --label "m1-air"    # machine name in the report
"""

import argparse
import csv
import datetime
import json
import os
import pathlib
import paths
import re
import sys
import urllib.error
import urllib.request
from collections import defaultdict

# The four usage counters, in the order they are reported everywhere below.
FIELDS = ("input_tokens", "cache_creation_input_tokens",
          "cache_read_input_tokens", "output_tokens")


# Directories that hold COPIES of transcripts rather than a live profile: this
# tool's own redacted exports, and the merged tree built from them. Reading them
# is not wrong — global dedup makes a copy contribute nothing — but walking
# hundreds of MB to learn that is a waste, so they are skipped by name.
COPY_DIRS = {"corpus", "merged", "token-corpus", "deadreckon-record",
             "deadreckon-transcripts", "node_modules", ".git",
             "archive", "snap", ".cache", ".local", "venv", ".venv"}


def _same_dir(a, b):
    """True when two paths name the same directory, symlink or not."""
    try:
        return a.resolve() == b.resolve()
    except OSError:
        return str(a) == str(b)


# This repository's OWN preservation tree. retention_guard hard-links every
# transcript into ~/.ai-logs-archive/claude/<profile>/ before Claude Code's
# cleanup sweep reaches the original, so a profile-shaped directory in there is
# not somebody's copy of somebody's work — it is the same profile, at the same
# inodes, and the day the sweep deletes the live transcript it is the ONLY copy.
# Hardcoded here because retention_guard.py hardcodes it (ARCHIVE) and
# sessions.read_claude_orphans already globs it; there is no shared constant to
# import, and inventing one would mean editing files this change does not own.
ARCHIVE_DIR = ".ai-logs-archive"


def _own_claim(config_dir, home):
    """What this directory claims BY ITSELF, inheriting nothing."""
    inside = config_dir / ".claude.json"
    try:
        if inside.is_file():
            return inside, "own config"
    except OSError:
        pass
    if _same_dir(config_dir.parent, home):
        if config_dir.name == ".claude":
            # Returned whether or not it exists: a default profile with a
            # missing or corrupt config is still the default profile.
            return home / ".claude.json", "home config"
        return None, "home directory"
    return None, None


def _archived_source(config_dir, home):
    """The home profile this directory is THIS TOOL'S ARCHIVE OF, or None.

    Only inside ~/.ai-logs-archive, and only when a directory of that name —
    with or without the leading dot, which the archive strips — exists in $HOME
    and claims an account itself. `Desktop_standout_full_.claude` names no
    profile in $HOME, so the sandbox copies stay excluded through their archived
    mirrors as well as directly, which matters: the mirrors are where their
    tokens were actually being published.

    Deliberately NOT a name match anywhere on the disk. ~/Desktop/x/.claude is
    also called `.claude` and inheriting from the name is exactly the defect
    being fixed. The archive root is the evidence, and it is this tool's own.
    """
    arch = home / ARCHIVE_DIR
    try:
        if not config_dir.is_relative_to(arch):
            return None
    except (OSError, ValueError):
        return None
    name = config_dir.name
    for cand in (home / name, home / ("." + name.lstrip("."))):
        try:
            if cand == config_dir or not cand.is_dir():
                continue
        except OSError:
            continue
        if _own_claim(cand, home)[1] is not None:
            return cand
    return None


def profile_claim(config_dir, home):
    """Where a profile's account comes from — or nothing, in which case it is
    NOT COUNTED. Returns (config_file_or_None, basis_or_None, identity_dir).

    THE AUTHOR'S RULING. ~/Desktop/standout_full/.claude and
    ~/Desktop/standout_sandbox/.claude are profile-shaped copies with no config
    file anywhere near them. find_config_dirs recognises a profile by SHAPE, so
    both were found, and 489,464,459 tokens were published under invented
    `unknown (<dirname>)` accounts nobody has ever logged into. They are the
    author's own data and they must not be counted. Excluded, not
    re-attributed: moving them to a real account would be worse than the bug.

    Four bases, and every one of them is evidence rather than a guess:

        own config      <profile>/.claude.json — the profile says who it is.
        home config     ~/.claude, the DEFAULT profile, whose state lives in
                        ~/.claude.json BESIDE it rather than inside it. Anchored
                        to `home` by path, never by name: the old rule was
                        `config_dir.name == ".claude"`, so ANY directory called
                        `.claude` anywhere on the disk read the live default
                        profile's config and inherited that person's identity.
                        That is the line that gave the sandbox copies a real
                        address.
        home directory  a dotdir sitting directly in $HOME with no config of its
                        own. That IS this machine's own profile — it is where
                        the tool and $CLAUDE_CONFIG_DIR put them — so it counts,
                        under the weakest handle (`unknown (<dir>)`), exactly as
                        before. Only profiles found DEEPER in the tree have to
                        produce a config, because a profile buried under
                        ~/Desktop/x/ is a copy someone made.
        archive of X    a mirror inside ~/.ai-logs-archive of a profile that
                        DOES claim an account (_archived_source). It inherits
                        that profile's config, so its transcripts are booked to
                        the account that produced them. This machine's last
                        published scan holds ten such mirrors: nine under
                        phantom `unknown (...)` accounts, and the tenth — the
                        one literally named `.claude` — under the live default
                        profile's identity, by the very name bug above.
                        Measured before writing this: all ten contribute 0
                        tokens beyond the live profiles today — but the archive
                        is
                        hard-linked precisely so it SURVIVES the sweep that
                        deletes the live transcript, and on that day it is the
                        only copy. Excluding it would cost nothing today and
                        silently delete recovered history later, which is this
                        repository's signature bug with a longer fuse.

    A config file that exists but cannot be parsed still claims the profile: it
    is a profile whose name we failed to read, which is a different fact from a
    profile that never claimed a name. ABSENT IS NOT EMPTY, and this function
    is where the two are told apart.
    """
    cfg, basis = _own_claim(config_dir, home)
    if basis is not None:
        return cfg, basis, config_dir
    src = _archived_source(config_dir, home)
    if src is not None:
        cfg, _basis = _own_claim(src, home)
        # The SOURCE supplies the identity, including the last-resort label, so
        # a profile and its archive are one account rather than two.
        return cfg, f"archive of {src.name}", src
    return None, None, config_dir


def find_config_dirs(home, extra_roots=(), excluded=None, include_unclaimed=False):
    """Every Claude Code config dir on this machine, found by SHAPE not by name.

    $CLAUDE_CONFIG_DIR accepts any path. Matching `~/.claude*` missed
    `~/.my-claude`; widening to `~/.*claude*` still missed
    `~/Desktop/standout_full/.claude`, which on the machine this was written on
    held 13,414 messages and 818,673,995 tokens present in no live profile —
    copies whose mtime was reset, which is why Claude Code's cleanup never took
    them. Both misses are the same error: deciding where a profile is allowed to
    live instead of recognising one when it is seen.

    A Claude Code profile is any directory containing `projects/` with at least
    one `.jsonl` beneath it. That is the test used here. The home directory is
    walked to `max_depth` (default 4) so nested copies are reached, skipping
    COPY_DIRS and anything already found.

    Safe to be greedy ONLY because dedup is global — see scan(). A directory
    that is a pure copy of another adds zero. Without that, this function would
    be a token-inflation machine.

    Greedy discovery, NARROW counting. A profile that claims no account
    (profile_claim) is dropped from the result and appended to `excluded` as
    {"path", "reason"} so the omission is visible with its path rather than
    silent — a scan that quietly counted 489 M fewer tokens and said nothing
    would be indistinguishable from a scan that lost them. Pass
    `include_unclaimed=True` to get the old greedy list back; a caller that
    ARCHIVES or EXPORTS transcripts wants that one, because "must not be
    counted" is not "must not be preserved".
    """
    seen_real, out = set(), []

    def is_dir(p):
        """is_dir() that survives a directory this user cannot enter.

        pathlib's is_dir() swallows ENOENT, ENOTDIR, EBADF and ELOOP and
        RE-RAISES EACCES. One `chmod 700` folder anywhere under $HOME therefore
        took down every caller of this function — which is the scanner, the
        session reader AND the retention guard:

            PermissionError: [Errno 13] Permission denied:
            '<home>/work/secret/projects'

        Loud from a hand-run scan, silent from the daemon, and in both cases
        nothing was counted or archived because discovery never returned.
        """
        try:
            return p.is_dir()
        except OSError:
            return False

    def looks_like_profile(p):
        proj = p / "projects"
        if not is_dir(proj):
            return False
        try:
            for _ in proj.rglob("*.jsonl"):     # at least one, cheaply
                return True
        except OSError:
            return False
        return False

    def add(p):
        # (st_dev, st_ino) identifies a directory even through a bind mount, a
        # junction, or a case-insensitive filesystem that resolve() renders as
        # two different strings. Reproduced on a real vfat mount: one directory
        # reachable by two paths counted as two profiles, inventing a phantom
        # zero-token account that inflated the account and session counts in
        # every rollup.
        #
        # THE st_ino == 0 FALLBACK IS MANDATORY. Network and some FUSE mounts
        # report inode 0 for everything, so keying on it alone would collapse
        # EVERY profile into one and silently drop all but the first — a far
        # worse failure than the one being fixed. Where the inode is unusable,
        # fall back to the resolved path, which is what this always did.
        try:
            st = p.stat()
            key = (st.st_dev, st.st_ino) if st.st_ino else p.resolve()
        except OSError:
            return
        if key not in seen_real and looks_like_profile(p):
            seen_real.add(key)
            out.append(p)

    for p in sorted(home.glob(".*claude*")):    # the fast, common case first
        if p.is_dir():
            add(p)

    # $CLAUDE_CONFIG_DIR may legitimately point outside the home directory, so
    # it is honoured — but ONLY when scanning the real home. `--home X` means
    # "treat X as the home", and letting the environment override that made the
    # flag a no-op: a scan of a temp directory still returned this machine's
    # live profiles. That breaks any test, and would silently export the wrong
    # computer's transcripts if the flag were used in earnest.
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    if env and home.resolve() == pathlib.Path.home().resolve():
        add(pathlib.Path(env).expanduser())

    def walk(root, depth):
        if depth < 0 or not is_dir(root):
            return
        try:
            kids = sorted(root.iterdir())
        except OSError:
            return
        for d in kids:
            try:
                skip = not d.is_dir() or d.is_symlink() or d.name in COPY_DIRS
            except OSError:
                continue                    # cannot even classify it
            if skip:
                continue
            if is_dir(d / "projects"):
                add(d)
            walk(d, depth - 1)

    walk(home, 4)
    for r in extra_roots:
        walk(pathlib.Path(r).expanduser(), 4)

    kept = []
    for p in out:
        if profile_claim(p, home)[1] is None:
            if excluded is not None:
                excluded.append({"path": str(p),
                                 "reason": "no config file of its own"})
            if not include_unclaimed:
                continue
        kept.append(p)
    return kept


def account_for(config_dir, home):
    """The account a config dir is signed into.

    The default dir keeps its state in ~/.claude.json, not ~/.claude/.claude.json
    — a quirk worth encoding, since guessing it wrong silently attributes every
    default-profile token to 'unknown'.

    A profile with no email is still a real profile with real usage, so it is
    never skipped and never allowed to fail the scan — it is identified by the
    weaker handle instead. Three tiers, strongest first:

        1. oauthAccount.emailAddress   subscription logins
        2. user:<userID prefix>        API-key profiles — no email, but userID
                                       is stable and, unlike a directory name,
                                       identical for the same profile on every
                                       machine, so combine.py merges it correctly
        3. unknown (<dir>)             unreadable config; last resort

    Tier 2 matters for the rollup: two machines may hold the same nameless
    profile under different directory names, and keying on the name would report
    one account as two. Distinct profiles must also never collapse into a shared
    "unknown" — that would invent an account by summing unrelated usage.

    Returns None for a profile that claims no account at all. None, not
    "unknown (<dir>)": a profile with no config is not a nameless account, it is
    not an account, and it is not counted (profile_claim).
    """
    cfg, basis, src = profile_claim(config_dir, home)
    if basis is None:
        return None
    return account_from(_read_json(cfg) if cfg else None,
                        f"unknown ({src.name})")


def _read_json(path):
    """A JSON file, or None when it could not be read. None, never {}."""
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def account_from(data, fallback):
    """The account a config document names: email, then userID, then `fallback`.

    THE ONE ACCOUNT RULE, and it lives in one function because it had three
    copies — analyze_tokens.account_for, sessions._claude_account and the inline
    expression in sessions.read_claude_orphans — and the third had drifted:
    it skipped the userID tier entirely and went straight to a directory name,
    so an orphan record from a config with no email was booked to an account
    named after the HOME DIRECTORY. Three copies of a rule is three rules.
    """
    d = data or {}
    email = (d.get("oauthAccount") or {}).get("emailAddress")
    if email:
        return email
    uid = d.get("userID")
    if uid:
        return f"user:{uid[:12]}"
    return fallback


def _config_json(config_dir, home):
    cfg, _basis, _src = profile_claim(config_dir, home)
    return (_read_json(cfg) if cfg else None) or {}


def user_id_for(config_dir, home):
    """The profile's stable userID hash, recorded alongside the account label."""
    return _config_json(config_dir, home).get("userID")


def identity_for(config_dir, home):
    """How a profile authenticates, and to which organization.

    Two ways in, and they are not interchangeable:

      oauth    a subscription login. .claude.json carries oauthAccount with the
               email, organizationUuid and accountUuid.
      api_key  an ANTHROPIC_API_KEY profile. There is no oauthAccount and no
               email — only customApiKeyResponses.approved, a fingerprint of the
               keys the user approved for this profile.

    An API-key profile bills to whatever organization the key belongs to, which
    is NOT knowable from disk: the org is only reported by the API itself, in the
    anthropic-organization-id response header. Nothing on the filesystem states
    it, so any claim about which account an API profile bills to is an assumption
    until probed (see --probe-api). Two profiles are the same billing identity
    only when their org_uuid matches.
    """
    d = _config_json(config_dir, home)
    oa = d.get("oauthAccount") or {}
    approved = ((d.get("customApiKeyResponses") or {}).get("approved")) or []
    ident = {
        "auth": "oauth" if oa.get("emailAddress") else ("api_key" if approved else "unknown"),
        "email": oa.get("emailAddress"),
        "org_uuid": oa.get("organizationUuid"),
        "org_name": oa.get("organizationName"),
        "account_uuid": oa.get("accountUuid"),
        "user_id": d.get("userID"),
        "approved_api_keys": approved,
    }
    if ident["auth"] == "api_key":
        # Key material is never read or recorded — only which file supplies it.
        cand = home / ".config/anthropic" / f"{config_dir.name.lstrip('.')}.key"
        ident["api_key_file"] = str(cand) if cand.exists() else None
    return ident


def probe_api_org(key_file):
    """Ask the API which organization a key belongs to. Opt-in, read-only.

    The org is not on disk, so this is the only way to know what an API-key
    profile actually bills to. GET /v1/models is the cheapest authenticated
    endpoint and generates no tokens; the answer is a response header. The key
    is read to send the request and is never stored or logged.
    """
    try:
        key = pathlib.Path(key_file).read_text(encoding="utf-8").strip()
    except Exception:
        return None
    if not key:
        return None
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/models",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.headers.get("anthropic-organization-id")
    except urllib.error.HTTPError as e:
        # An expired or revoked key still identifies itself in the header.
        return e.headers.get("anthropic-organization-id") if e.headers else None
    except Exception:
        return None


def link_api_profiles(accounts):
    """Attach each api_key profile to the oauth account sharing its organization.

    Only an org_uuid match counts. A directory naming convention (.claude-alt ->
    .claude-alt-api) looks like a link and is not one: the key can belong to a
    different organization entirely, and on this machine it does.
    """
    by_org = {a["identity"]["org_uuid"]: a["account"]
              for a in accounts
              if a["identity"]["auth"] == "oauth" and a["identity"].get("org_uuid")}
    for a in accounts:
        i = a["identity"]
        if i["auth"] == "api_key":
            i["linked_account"] = by_org.get(i.get("org_uuid"))
            i["link_basis"] = ("organizationUuid match" if i.get("linked_account")
                               else "unlinked — org not among this machine's logins")


def max_into(dst, src):
    """Per-field MAXIMUM, in place. Returns what that ADDED, field by field.

    THE UNION-WITH-MAXIMUM RULE, in one function because it is needed in three
    places that used to disagree: the running maximum per message.id (both
    scanners), and the merge of two copies of one session found in two
    directories (sessions.multi_base, which used to keep the first and throw
    the rest away).

    Two observations of ONE thing merge to the larger of each field. Never a
    sum — that double-counts a copy. Never first-wins — the first write of a
    streaming message carries PARTIAL usage, and a truncated copy of a session
    is a real state on this disk. Never last-wins — a truncated rewrite would
    then shrink a total that was already right. Only a maximum cannot go
    backwards, and only a per-FIELD maximum keeps {output:100, cache_read:0} and
    {output:0, cache_read:150} from discarding one of them wholesale, which is
    what a max-of-the-sum does.
    """
    delta = {}
    for k in FIELDS:
        v = src.get(k)
        v = v if isinstance(v, int) and v > 0 else 0
        cur = dst.get(k) or 0
        delta[k] = v - cur if v > cur else 0
        if v > cur:
            dst[k] = v
    return delta


class MessageMax:
    """message -> the running MAXIMUM usage seen for it, across a whole machine.

    THE ONE COLLATION FUNCTION. It had two implementations and they disagreed:
    analyze_tokens.scan held its per-message maxima in a `pending` dict that was
    created fresh PER CONFIG DIRECTORY while the `seen` set spanned all of them,
    so the first directory to hold a message id banked whatever it had and every
    later directory's larger value was skipped outright — first-DIRECTORY-wins.
    sessions.read_claude held one running-max map for the whole machine. On a
    live-partial-plus-archive-complete pair that is 3 against 37,178 for the
    same message, and check_consistency could say the two scanners differed but
    never which one was right.

    `seen` stays a plain set, because that is what every caller already passes
    from directory to directory. Each element is (key, (v0, v1, v2, v3)) — the
    key AND what has been credited for it — so the map is rebuilt from the set
    at the start of each scan and a later directory can credit the DIFFERENCE.
    That is what keeps each directory's own report equal to what that directory
    added, while the machine total is the union.

    Three shapes of row, three keys, because Claude Code writes all three:

        message.id present   the real dedup key, scoped to its SESSION. A
                             message id identifies a message within the
                             conversation that produced it; two conversations
                             that both call a message "m1" are two messages, and
                             a machine-wide id key silently deletes the second.
                             Measured on this machine before choosing: 33,749
                             distinct message ids over 77,438 usage rows, and
                             exactly 0 of them appeared under more than one
                             session id — so the two rules give the same number
                             on real data and only the session-scoped one
                             survives data where they do not.
        no id, row uuid      nothing else can identify it; count it once on the
                             uuid, machine-wide, which is what both scanners
                             have always done with it.
        neither              keyed on what it says and where it sits in its own
                             file: (session, timestamp, model, the four
                             counters) plus how many rows of that exact shape
                             the file has already produced. The ordinal is
                             per-file, so a byte-identical copy of that file in
                             another profile produces the SAME key and adds
                             nothing, while two genuinely different turns that
                             happen to bill the same are still two keys. The
                             old code deduplicated this shape on nothing at all
                             and counted the copy twice.
    """

    def __init__(self, seen=None):
        self.seen = set() if seen is None else seen
        self.best = {k: dict(zip(FIELDS, v)) for k, v in self.seen}
        self.meta = {}
        self._nth = defaultdict(int)

    def key(self, path, mid, row_uuid, ident, usage):
        if mid:
            return ("id", ident[0], mid)
        if row_uuid:
            return ("uuid", row_uuid)
        shape = (tuple(ident), tuple((usage.get(k) if isinstance(usage.get(k), int)
                                      else None) for k in FIELDS))
        n = self._nth[(str(path), shape)]
        self._nth[(str(path), shape)] = n + 1
        return ("row", shape, n)

    def credit(self, key, usage, meta=None):
        """Fold one row in. Returns (delta, meta, new).

        `delta` is what this row ADDS to the machine total — zero for every
        field when the row is a copy of, or a partial write of, something
        already credited. `meta` is what the caller passed the FIRST time this
        key was seen in this pass, so the delta is booked where the message
        belongs rather than wherever its last rewrite happened to be found.
        `new` is True only when the key had never been seen, which is what makes
        a turn a turn.
        """
        cur = self.best.get(key)
        new = cur is None
        if new:
            cur = self.best[key] = dict.fromkeys(FIELDS, 0)
        else:
            self.seen.discard((key, tuple(cur[k] for k in FIELDS)))
        delta = max_into(cur, usage)
        self.seen.add((key, tuple(cur[k] for k in FIELDS)))
        return delta, self.meta.setdefault(key, meta), new


def iter_usage(path):
    """Yield one dict per assistant turn in one session file.

    Only lines that mention "usage" are parsed — most lines are user turns and
    tool results, and parsing all of them roughly triples the scan time.

    `usage.iterations` restates the same counters for multi-step turns; the
    top-level numbers already include them, so it is deliberately not summed.
    """
    with open(path, encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if '"usage"' not in line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue          # a truncated final line in a live session
            msg = rec.get("message") or {}
            usage = msg.get("usage")
            if not isinstance(usage, dict):
                continue
            # THE DEDUP KEY IS message.id, NOT rec["uuid"].
            #
            # Claude Code writes one assistant message many times while it
            # streams. Every write is a new ROW with a fresh row uuid, carrying
            # the SAME message.id. Keying on the row uuid therefore dedups
            # nothing at all — measured on ~/.claude-alt:
            #
            #     usage rows            33,740
            #     distinct row uuids    33,740     dedup removed 0 rows (0.00%)
            #     distinct message ids  13,794     the real number of API calls
            #
            # The row uuid is still yielded, because a row with no message id
            # cannot be deduplicated by anything else and must be counted on its
            # own terms. The consumer decides; this only stops hiding the key it
            # needs to make that decision.
            #
            # The session id and the FULL timestamp are yielded too: a row with
            # neither a message id nor a row uuid can only be identified by what
            # it says, and MessageMax needs all of it to build that key.
            ts = rec.get("timestamp") or ""
            yield {
                "mid": msg.get("id"),
                "uuid": rec.get("uuid"),
                "model": msg.get("model") or "unknown",
                "session_id": rec.get("sessionId"),
                "ts": ts,
                "day": ts[:10],
                "usage": usage,
                "sidechain": bool(rec.get("isSidechain")),
            }


# model-id prefix -> vendor. Claude Code can be pointed at any backend, so the
# model id is the only reliable discriminator of who actually served a turn.
PROVIDER_PREFIXES = (
    ("claude",     "anthropic"),
    ("deepseek",   "deepseek"),
    ("gemini",     "google"),
    ("gemma",      "google"),
    ("antigravity", "antigravity"),
    ("copilot",    "copilot"),
    ("gpt",        "openai"),
    ("o1", "openai"), ("o3", "openai"), ("o4", "openai"), ("codex", "openai"),
    ("grok",       "xai"),
    ("llama",      "meta"),
    ("mistral",    "mistral"), ("mixtral", "mistral"),
    ("qwen",       "qwen"),
    ("kimi",       "moonshot"),
    ("glm",        "zhipu"),
)

# Tools that keep local state but record no token usage, so their absence from
# the numbers is a property of the tool and not a gap in this scanner.
OTHER_TOOLS = (
    ("gemini",      ".gemini",          "Gemini CLI"),
    ("copilot",     ".copilot",         "GitHub Copilot CLI"),
    ("antigravity", ".antigravitycli",  "Antigravity CLI"),
    ("openai",      ".codex",           "OpenAI Codex CLI"),
    ("xai",         ".grok",            "Grok CLI"),
    ("xai",         ".config/grok",     "Grok CLI (XDG)"),
    ("cursor",      ".cursor",          "Cursor"),
)

USAGE_KEY_RE = re.compile(
    r'"(total_tokens|input_tokens|output_tokens|promptTokenCount'
    r'|candidatesTokenCount|totalTokenCount|cached_input_tokens|usageMetadata)"')


def provider_of(model):
    """Which vendor a model id belongs to.

    Claude Code can be pointed at a non-Anthropic backend, and the transcripts
    look identical — same JSONL, same usage block. Summing them yields a
    "Claude" total that includes tokens Anthropic never served.
    """
    m = (model or "").lower()
    for prefix, vendor in PROVIDER_PREFIXES:
        if m.startswith(prefix):
            return vendor
    if m in ("<synthetic>", "unknown", ""):
        return "synthetic"
    return "other"


def detect_other_tools(home):
    """Other AI CLIs on this machine, and whether they record token usage.

    A provider missing from the token tables is ambiguous on its own: it could
    mean unused, or it could mean the tool never writes usage to disk. Those are
    very different facts, so presence is reported separately from countability.
    A tool is 'countable' only if some file in its tree actually carries a usage
    key — checked, not assumed.
    """
    found = []
    for vendor, dirname, label in OTHER_TOOLS:
        d = home / dirname
        if not d.exists():
            continue
        files = usage_files = 0
        for f in d.rglob("*"):
            if not f.is_file() or f.suffix not in (".json", ".jsonl", ".log", ".toml"):
                continue
            files += 1
            if usage_files == 0 and files <= 4000:
                try:
                    if USAGE_KEY_RE.search(f.read_text(encoding="utf-8", errors="ignore")[:200000]):
                        usage_files += 1
                except Exception:
                    pass
        found.append({
            "vendor": vendor, "label": label, "dir": str(d),
            "files": files,
            "records_usage": bool(usage_files),
        })
    return found


def classify(rel):
    """What kind of transcript a session-relative path is.

    Claude Code nests spawned work underneath the session that started it:

        <proj>/<session>.jsonl                                 main
        <proj>/<session>/subagents/agent-<id>.jsonl            subagent
        <proj>/<session>/subagents/workflows/wf_<id>/….jsonl   workflow agent

    Each is its own API conversation with its own billing, so all three count.
    Only the top level is the "session"; the rest are fan-out beneath it.
    """
    parts = rel.parts
    if "workflows" in parts:
        return "workflow"
    if "subagents" in parts:
        return "subagent"
    return "main"


def scan(config_dir, seen=None):
    """Aggregate one config dir, including subagent and workflow transcripts.

    Deduplicated by message uuid: resuming a session can rewrite earlier turns
    into the new file, and a subagent's turns are also inlined into its parent
    transcript as sidechain records. Counting either twice would inflate the
    total, and the uuid is stable across both copies.

    `seen` is passed IN so the set spans every config dir rather than resetting
    per dir. That is what makes broad discovery safe: a directory that is a copy
    of another — a backup, a staging tree for some tool — contributes exactly
    zero instead of doubling its source. With a per-dir set, adding the four
    copy trees on one machine's Desktop would have added ~10 B phantom tokens.
    Only genuinely-unseen messages can move the total.

    The maxima now span directories too, via MessageMax — the same object
    sessions.read_claude uses, so the two scanners cannot drift apart again.
    What this dir REPORTS is what this dir ADDED: a directory holding a larger
    write of a message an earlier directory already banked contributes the
    difference, so the per-dir numbers still sum to the machine total.
    """
    mm = MessageMax(seen)
    totals = dict.fromkeys(FIELDS, 0)
    by_model = defaultdict(lambda: dict.fromkeys(FIELDS, 0))
    by_day = defaultdict(lambda: dict.fromkeys(FIELDS, 0))
    by_project = defaultdict(lambda: dict.fromkeys(FIELDS, 0))
    by_kind = defaultdict(lambda: dict.fromkeys(FIELDS, 0))
    by_provider = defaultdict(lambda: dict.fromkeys(FIELDS, 0))
    files = defaultdict(int)
    turns = 0

    root = config_dir / "projects"
    # A DIRECTORY THAT WILL NOT OPEN IS COUNTED AND NAMED, NEVER SKIPPED.
    #
    # `rglob` swallows EACCES and yields nothing — no flag, no callback, no
    # exception — so one `chmod 000` project directory inside an otherwise
    # readable profile removed 1,251,500 tokens from the fixture's total and
    # left every partition summing to its whole. The scan and a scan of the
    # same tree with that directory emptied were byte-for-byte identical.
    #
    # `unreadable_dirs` rides in `files`, which is the per-scan counter dict
    # this function already publishes, and `unreadable` carries the paths:
    # a count alone cannot be acted on, and 0 is what a clean scan reports too.
    blind = []

    def onerror(err):
        blind.append(str(getattr(err, "filename", None) or root))

    found = []
    for dirpath, _dirnames, names in os.walk(str(root), onerror=onerror):
        found += [pathlib.Path(dirpath) / n for n in names if n.endswith(".jsonl")]
    if blind:
        files["unreadable_dirs"] = len(blind)
    for f in sorted(found):
        rel = f.relative_to(root)
        if not rel.parts:
            continue
        project = rel.parts[0]
        kind = classify(rel)
        files[kind] += 1
        for row in iter_usage(f):
            usage = row["usage"]
            # `or f.stem` is sessions.read_claude's fallback for a row with no
            # sessionId, restated here so both scanners scope a message id to
            # the same session and cannot disagree about which rows are one
            # conversation.
            key = mm.key(f, row["mid"], row["uuid"],
                         (row["session_id"] or f.stem, row["ts"], row["model"]),
                         usage)
            # RUNNING MAXIMUM per field — not first-wins, not last-wins, and
            # not per-directory. See MessageMax; the rule is stated once there
            # and sessions.read_claude runs the same object.
            delta, meta, new = mm.credit(
                key, usage, (row["model"], row["day"], project, kind))
            if new:
                turns += 1
            model, day, project_, kind_ = meta
            provider = provider_of(model)
            for k in FIELDS:
                v = delta[k]
                if not v:
                    continue
                totals[k] += v
                by_model[model][k] += v
                by_project[project_][k] += v
                by_kind[kind_][k] += v
                by_provider[provider][k] += v
                if day:
                    by_day[day][k] += v

    return {
        "config_dir": str(config_dir),
        "sessions": files["main"],
        "files": dict(files),
        # Named, not merely counted — see the walk above. An empty list is a
        # scan that looked and everything opened.
        "unreadable": blind,
        "turns": turns,
        "totals": totals,
        "by_kind": {k: v for k, v in by_kind.items()},
        "by_provider": {k: v for k, v in by_provider.items()},
        "by_model": {k: v for k, v in by_model.items()},
        "by_day": {k: v for k, v in by_day.items()},
        "by_project": {k: v for k, v in by_project.items()},
    }


def grand(u):
    """Every token the account was billed for, cached or not."""
    return sum(u[k] for k in FIELDS)


def human(n):
    for unit, size in (("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if n >= size:
            return f"{n / size:.2f}{unit}"
    return str(n)


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out", help="output directory")
    ap.add_argument("--label", default=os.uname().nodename, help="machine name")
    ap.add_argument("--home", default=str(pathlib.Path.home()))
    ap.add_argument("--probe-api", action="store_true",
                    help="ask the API which org each API-key profile bills to "
                         "(one read-only request per key, generates no tokens)")
    args = ap.parse_args()

    home = pathlib.Path(args.home)
    # Profiles that claim no account are dropped here, WITH their paths, so a
    # smaller total always comes with the list of what was left out.
    excluded = []
    dirs = find_config_dirs(home, excluded=excluded)
    for x in excluded:
        sys.stderr.write(f"excluded (not counted): {x['path']} — {x['reason']}\n")
    if not dirs:
        sys.exit(f"no Claude Code config dirs with sessions under {home}")

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    data, docs = paths.machine(out), paths.human(out)

    accounts = []
    # One set across every config dir. A dir that duplicates another adds zero,
    # which is what lets find_config_dirs look beyond ~/.claude* without risk.
    # Ordering matters: real profiles come first out of find_config_dirs, so a
    # message is attributed to the live profile and a copy only ever supplies
    # what the live profile has already lost.
    seen = set()
    for d in dirs:
        sys.stderr.write(f"scanning {d} ...\n")
        sys.stderr.flush()
        r = scan(d, seen)
        r["account"] = account_for(d, home)
        r["user_id"] = user_id_for(d, home)
        r["identity"] = identity_for(d, home)
        r["grand_total"] = grand(r["totals"])
        accounts.append(r)

    if args.probe_api:
        for a in accounts:
            i = a["identity"]
            if i["auth"] == "api_key" and i.get("api_key_file"):
                sys.stderr.write(f"probing org for {a['config_dir']} ...\n")
                org = probe_api_org(i["api_key_file"])
                if org:
                    i["org_uuid"] = org
                    i["org_source"] = "anthropic-organization-id header"
    link_api_profiles(accounts)
    accounts.sort(key=lambda a: -a["grand_total"])
    machine_total = sum(a["grand_total"] for a in accounts)

    generated_at = datetime.datetime.now().astimezone().isoformat(timespec="seconds")

    other_tools = detect_other_tools(home)

    provider_totals = defaultdict(int)
    for a in accounts:
        for pname, v in a.get("by_provider", {}).items():
            provider_totals[pname] += grand(v)

    import sessions as _sess
    _hw_uuid = _sess._machine_uuid(out)
    report = {
        "machine": args.label,
        "generated_at": generated_at,
        "scanner_version": _sess.scanner_version(),
        **( {"hardware_uuid": _hw_uuid} if _hw_uuid else {} ),
        "anthropic_only_tokens": provider_totals.get("anthropic", 0),
        "by_provider": dict(provider_totals),
        "other_tools": other_tools,
        "grand_total_tokens": machine_total,
        # Profile-shaped directories that were FOUND and deliberately not
        # counted, each with its path. Recorded rather than dropped: an
        # exclusion nobody can see is indistinguishable from data that was lost.
        "excluded_profiles": excluded,
        "accounts": accounts,
    }
    (data / "totals.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    write_csv(data / "by_account.csv",
              ["account", "config_dir", "sessions", "turns", *FIELDS, "total"],
              [[a["account"], a["config_dir"], a["sessions"], a["turns"],
                *[a["totals"][k] for k in FIELDS], a["grand_total"]] for a in accounts])

    write_csv(data / "by_model.csv", ["account", "model", *FIELDS, "total"],
              [[a["account"], m, *[v[k] for k in FIELDS], grand(v)]
               for a in accounts for m, v in
               sorted(a["by_model"].items(), key=lambda kv: -grand(kv[1]))])

    write_csv(data / "by_day.csv", ["account", "date", *FIELDS, "total"],
              [[a["account"], d, *[v[k] for k in FIELDS], grand(v)]
               for a in accounts for d, v in sorted(a["by_day"].items())])

    write_csv(data / "by_project.csv", ["account", "project", *FIELDS, "total"],
              [[a["account"], p, *[v[k] for k in FIELDS], grand(v)]
               for a in accounts for p, v in
               sorted(a["by_project"].items(), key=lambda kv: -grand(kv[1]))])

    lines = [f"# Claude Code token usage — {args.label}", "",
             f"_Generated {generated_at}_", ""]
    lines += [f"## Total for this computer: {machine_total:,} tokens "
              f"({human(machine_total)})", "",
              f"Across {len(accounts)} account(s), "
              f"{sum(a['sessions'] for a in accounts):,} sessions, "
              f"{sum(a['turns'] for a in accounts):,} assistant turns.", ""]
    lines += ["Counted from `message.usage` in the local session JSONL — the API's own",
              "accounting, deduplicated by message uuid.", "",
              "## Accounts", "",
              "| Account | Sessions | Turns | Input | Cache write | Cache read | Output | Total |",
              "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for a in accounts:
        t = a["totals"]
        lines.append(f"| {a['account']} | {a['sessions']:,} | {a['turns']:,} | "
                     + " | ".join(human(t[k]) for k in FIELDS)
                     + f" | **{human(a['grand_total'])}** |")

    prov = provider_totals
    anthropic_total = prov.get("anthropic", 0)
    lines += ["", "## By provider", "",
              "Claude Code can be pointed at a non-Anthropic backend; those transcripts are",
              "byte-identical to Claude ones. Totals are split on the model id so an",
              "Anthropic figure is never inflated by tokens Anthropic did not serve.", "",
              "| Provider | Tokens | Share |", "|---|---:|---:|"]
    for name, tot in sorted(prov.items(), key=lambda kv: -kv[1]):
        share = tot / machine_total if machine_total else 0
        lines.append(f"| {name} | {tot:,} | {share:.1%} |")
    lines += ["", f"**Anthropic-only total: {anthropic_total:,} tokens "
                  f"({human(anthropic_total)})**", ""]

    if excluded:
        lines += ["", "## Profiles found and NOT counted", "",
                  "A profile-shaped directory with no config file of its own claims no",
                  "account, so its tokens are excluded rather than booked to an invented",
                  "one. Listed with their paths so the exclusion is checkable.", "",
                  "| Directory | Why |", "|---|---|"]
        lines += [f"| `{x['path']}` | {x['reason']} |" for x in excluded]

    if other_tools:
        lines += ["", "### Other AI tools on this machine", "",
                  "Listed so a provider missing from the table above is unambiguous: a tool",
                  "that records no usage cannot be counted from disk, which is different",
                  "from a tool that was never used.", "",
                  "| Tool | Directory | Files | Token usage on disk |",
                  "|---|---|---:|---|"]
        for t in other_tools:
            state = "yes — countable" if t["records_usage"] else "**no — not countable**"
            lines.append(f"| {t['label']} | `{t['dir']}` | {t['files']:,} | {state} |")

    lines += ["", "## Authentication and organization", "",
              "An API-key profile bills to the organization the key belongs to, which is",
              "not recorded on disk — rerun with `--probe-api` to resolve it. A profile is",
              "linked to an account only when their organization UUIDs match.", "",
              "| Account | Auth | Organization | Org UUID | Linked to |",
              "|---|---|---|---|---|"]
    for a in accounts:
        i = a["identity"]
        lines.append(f"| {a['account']} | {i['auth']} | {i.get('org_name') or '—'} | "
                     f"`{i.get('org_uuid') or '—'}` | {i.get('linked_account') or '—'} |")

    for a in accounts:
        lines += ["", f"### {a['account']}", "",
                  f"**{a['grand_total']:,} tokens** ({human(a['grand_total'])}) — "
                  f"`{a['config_dir']}`"]
        if a.get("user_id"):
            lines += ["", f"userID `{a['user_id']}`"]
        if a["by_kind"]:
            lines += ["", "| Transcript | Files | Tokens | Share |", "|---|---:|---:|---:|"]
            for kind in ("main", "subagent", "workflow"):
                v = a["by_kind"].get(kind)
                if not v:
                    continue
                g = grand(v)
                share = g / a["grand_total"] if a["grand_total"] else 0
                lines.append(f"| {kind} | {a['files'].get(kind, 0):,} | {human(g)} | "
                             f"{share:.0%} |")
        top_m = sorted(a["by_model"].items(), key=lambda kv: -grand(kv[1]))[:8]
        if top_m:
            lines += ["", "| Model | Total |", "|---|---:|"]
            lines += [f"| {m} | {human(grand(v))} |" for m, v in top_m]
        days = sorted(a["by_day"].items())
        if days:
            busiest = max(days, key=lambda kv: grand(kv[1]))
            lines += ["", f"Active {days[0][0]} → {days[-1][0]} ({len(days)} days). "
                          f"Busiest day {busiest[0]} at {human(grand(busiest[1]))}."]
        top_p = sorted(a["by_project"].items(), key=lambda kv: -grand(kv[1]))[:8]
        if top_p:
            lines += ["", "| Project | Total |", "|---|---:|"]
            lines += [f"| `{p}` | {human(grand(v))} |" for p, v in top_p]

    (docs / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines))
    sys.stderr.write(f"\nwrote {out}/REPORT.md, totals.json, by_*.csv\n")


if __name__ == "__main__":
    main()
