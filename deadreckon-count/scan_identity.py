#!/usr/bin/env python3
"""Which commit a scan ran from, and whether its stamp could have come from there.

    python3 scan_identity.py            # this checkout's record, then a verdict
                                        # on every machine folder in the tree

THE DEFECT THIS CLOSES

`sessions.scanner_version()` is sha256 of sessions.py + analyze_tokens.py cut to
12 characters, and every machine writes that string into its own totals.json.
`check_consistency.py` then asks whether the machines AGREE — `every machine
scanned by the same version` compares the labels to each other and to nothing
else. Two machines carrying `2e512dc55519` agree. Two machines carrying
`deadbeefcafe` agree exactly as well, and `adversarial.a_fake_scanner_version`
plants that pair verbatim. Measured against this tree and against HEAD: the
forged pair passes every check in the gate. Nothing in the repository had ever
compared a stamp to CODE.

A label that certifies itself certifies nothing. So a scan records the COMMIT it
ran from, and the stamp is recomputed here from THAT COMMIT'S BLOBS — the bytes
git holds, which the machine writing the stamp does not get to choose. A value no
commit could have produced is named as such.

WHAT `DIRTY` IS FOR, AND WHY IT IS NOT A LOOPHOLE

A scan run over uncommitted edits has a stamp that no commit can reproduce, and
that scan is not dishonest — it is a scan of code that was never committed. The
commit simply does not describe what ran. Recording `scan_commit_dirty` and
saying so is the honest answer; pretending the commit describes it is not.

That does hand a forger an escape: claim dirty and no mismatch can be called a
forgery. It is a smaller hole than the one it replaces, because DIRTY is never
VERIFIED — it is its own verdict, counted and named in the gate, and a fleet
whose machines all claim dirty is a fleet that has certified nothing and says so
on the banner. Silence was the old behaviour; this is not silent.

FULL DIGEST, NOT TWELVE CHARACTERS

The stored record carries all 64. Truncation is for display. 48 bits is plenty
of collision resistance for a fleet of five, but the truncated field is the one
an attacker gets to type, and a comparison that only ever looks at 12 characters
throws away the evidence that would settle it. `scanner_version` stays as it is,
for every reader that already prints it; `scanner_version_sha256` is what
decides.

NOTHING HERE WRITES. record() returns a dict for a caller to store; verify()
reads git and returns a verdict. This module never touches a file.
"""

import collections
import hashlib
import pathlib
import re
import subprocess

# The files whose BYTES are the scanner. Same two, in the same order, as
# sessions.scanner_version() hashes — the whole point is to recompute the value
# that function produces, so an edit there and no edit here would make this
# verifier disagree with reality on every machine at once. That is not left to
# memory: `adv_forged_stamp.py` asserts the digest computed here, truncated,
# equals sessions.scanner_version() on the live tree, and goes red if the two
# ever drift apart.
SCANNER_FILES = ("sessions.py", "analyze_tokens.py")

# What the existing field shows. Display only.
SHORT = 12

# A commit as git will accept it. Checked before it is handed to a subprocess,
# because `scan_commit` arrives from a JSON file that some other machine wrote,
# and a list, a None or a string with a space in it is not a commit — it is a
# question about what happens when you pass one to git. Answering it here means
# the verifier returns a verdict instead of an exception, and a verifier that
# raises is a machine that never gets adjudicated at all.
_SHA = re.compile(r"[0-9a-fA-F]{7,64}\Z")

VERIFIED = "VERIFIED"                 # the commit's blobs hash to the stamp
FORGED = "FORGED"                     # they do not, and the tree was clean
UNKNOWN_COMMIT = "UNKNOWN_COMMIT"     # this repository has no such commit
DIRTY = "DIRTY"                       # mismatch, and the scan admits it
NO_COMMIT = "NO_COMMIT"               # stamped, but claims no commit at all
NO_STAMP = "NO_STAMP"                 # not stamped, so there is nothing to check
GIT_BLIND = "GIT_BLIND"               # git could not be asked here

STATUSES = (VERIFIED, FORGED, UNKNOWN_COMMIT, DIRTY, NO_COMMIT, NO_STAMP,
            GIT_BLIND)

# Verdicts that mean a stamp was actually compared against a commit's blobs.
# Everything else is a reason the comparison did not happen, and the gate counts
# those separately: a machine that was not checked must never be counted with
# the machines that passed.
ADJUDICATED = (VERIFIED, FORGED, DIRTY)

Verdict = collections.namedtuple(
    "Verdict", "status folder claimed expected detail")


def _git(root, *args):
    """(answered, stdout AS BYTES) for `git <args>` in `root`.

    Bytes, not text. The digest has to be over what the file IS, and
    `subprocess(text=True)` decodes and normalises newlines — on a repository
    with a CRLF blob that produces a hash of something that has never existed on
    disk, which would read as a forgery on an honest machine.

    ANSWERED-WITH-NOTHING AND UNABLE-TO-ANSWER ARE NOT THE SAME FACT, which is
    why the flag is returned separately rather than inferred from empty output.
    `git show` of a file that exists and is empty succeeds with no bytes; git
    missing from PATH also produces no bytes. Collapsing those two is how a tree
    with no evidence in it reports a clean bill of health.
    """
    try:
        r = subprocess.run(["git"] + list(args), cwd=str(root),
                           capture_output=True)
    except (OSError, ValueError):        # no git binary, bad arguments
        return False, b""
    return r.returncode == 0, r.stdout


def digest(blobs):
    """sha256 over the scanner's bytes, in SCANNER_FILES order. All 64 chars."""
    h = hashlib.sha256()
    for b in blobs:
        h.update(b)
    return h.hexdigest()


def working_tree_version(root):
    """The scanner's full digest as it sits on disk right now.

    `if f.is_file()` mirrors sessions.scanner_version() exactly, including its
    behaviour when a file is absent: it is skipped and the remaining ones are
    hashed. That is a real state — a checkout without analyze_tokens.py — and
    the two functions have to answer it the same way or they disagree about a
    tree neither of them is wrong about.
    """
    root = pathlib.Path(root)
    blobs = []
    for name in SCANNER_FILES:
        f = root / name
        if f.is_file():
            blobs.append(f.read_bytes())
    return digest(blobs)


def git_available(root):
    """Can git be asked anything here at all?"""
    return _git(root, "rev-parse", "--git-dir")[0]


def head_commit(root):
    """The commit this working tree is on, or None if git will not say."""
    ok, out = _git(root, "rev-parse", "HEAD")
    v = out.decode("utf-8", "replace").strip() if ok else ""
    return v or None


def tree_dirty(root):
    """True, False, or None when git could not be asked.

    None is not False. A scan that could not establish whether the tree was
    clean has not established that it was, and `record()` stores the None so the
    verifier can treat it as unknown rather than as a clean bill of health.
    """
    ok, out = _git(root, "status", "--porcelain")
    if not ok:
        return None
    return bool(out.strip())


def commit_exists(root, commit):
    """Does this repository hold that commit?

    `^{commit}` so a tag or a tree object cannot answer for a commit, and so a
    12-character string that happens to be a valid abbreviation still has to
    resolve. A commit this checkout has never fetched is NOT a forgery and is
    not reported as one — it is a claim that cannot be settled here, which is a
    different sentence and gets a different verdict.
    """
    if not isinstance(commit, str) or not _SHA.match(commit.strip()):
        return False
    return _git(root, "rev-parse", "--verify", "--quiet",
                commit.strip() + "^{commit}")[0]


def version_at_commit(root, commit):
    """The scanner's full digest AT `commit`, or None if it cannot be computed.

    None means one of two different things and the caller separates them: the
    commit is not here, or the commit is here and holds no scanner at all. The
    second matters — `digest([])` is the sha256 of nothing, a real, constant,
    guessable hex string, and returning it would let a stamp of `e3b0c442...`
    verify against any commit predating the scanner. A commit that holds neither
    file could not have produced a scan, and says so instead.
    """
    if not commit_exists(root, commit):
        return None
    blobs = []
    for name in SCANNER_FILES:
        ok, data = _git(root, "show", f"{commit.strip()}:{name}")
        if ok:
            blobs.append(data)
    if not blobs:
        return None
    return digest(blobs)


def record(root=None):
    """What a scan should store about the code that produced it.

    Not written from here. sessions.stamped() is where this belongs — one
    helper, immediately before every artifact is written, for the same reason
    the scanner_version stamp lives there: this codebase has shipped one rule
    copied into three writers four separate times, and three of the five
    machine-readable files went unstamped for exactly that reason.
    """
    root = pathlib.Path(root or pathlib.Path(__file__).resolve().parent)
    full = working_tree_version(root)
    return {
        "scanner_version": full[:SHORT],
        "scanner_version_sha256": full,
        "scan_commit": head_commit(root),
        "scan_commit_dirty": tree_dirty(root),
        "scanner_files": list(SCANNER_FILES),
    }


def verify(root, doc, folder=None):
    """Adjudicate one machine's recorded (commit, stamp). Never raises.

    `doc` is a totals.json — or anything else carrying the same fields. The
    return is always a Verdict with a status from STATUSES, because the gate
    counts how many folders it adjudicated and compares that to how many folders
    exist: a verifier that throws on one machine would otherwise remove that
    machine from the population and leave the remainder reporting a clean sheet.
    A crash is not coverage.
    """
    folder = folder or (doc.get("machine") if isinstance(doc, dict) else None)
    doc = doc if isinstance(doc, dict) else {}

    claimed_full = doc.get("scanner_version_sha256")
    claimed_short = doc.get("scanner_version")
    claimed_full = claimed_full.strip().lower() if isinstance(claimed_full, str) else None
    claimed_short = claimed_short.strip().lower() if isinstance(claimed_short, str) else None
    claimed = claimed_full or claimed_short
    if not claimed:
        return Verdict(NO_STAMP, folder, None, None,
                       f"{folder}: no scanner_version to check")

    # THE FILE CONTRADICTING ITSELF IS ALREADY AN ANSWER. If both fields are
    # present, the short one must be the head of the long one — they are the
    # same number printed twice. Editing only the field that gets displayed is
    # the cheapest forgery available once the full digest exists, and it costs
    # one comparison to close, with no git involved.
    if claimed_full and claimed_short and not claimed_full.startswith(claimed_short):
        return Verdict(FORGED, folder, claimed, claimed_full,
                       f"{folder}: scanner_version {claimed_short} is not the "
                       f"first {len(claimed_short)} of its own "
                       f"scanner_version_sha256 {claimed_full[:SHORT]}…")

    commit = doc.get("scan_commit")
    if not commit:
        return Verdict(NO_COMMIT, folder, claimed, None,
                       f"{folder}: stamped {claimed[:SHORT]} and names no "
                       "commit, so nothing independent can confirm it")
    if not git_available(root):
        return Verdict(GIT_BLIND, folder, claimed, None,
                       f"{folder}: git could not be asked here, so the stamp "
                       "was compared against nothing")
    if not commit_exists(root, commit):
        return Verdict(UNKNOWN_COMMIT, folder, claimed, None,
                       f"{folder}: claims commit "
                       f"{str(commit)[:12]!r}, which this repository does not "
                       "hold — fetch it, or the stamp names a commit that has "
                       "never existed")

    expected = version_at_commit(root, commit)
    if expected is None:
        return Verdict(FORGED, folder, claimed, None,
                       f"{folder}: commit {str(commit)[:12]} holds none of "
                       f"{', '.join(SCANNER_FILES)}, so no scan could have run "
                       "from it")

    match = (claimed_full == expected if claimed_full
             else expected.startswith(claimed_short))
    if match:
        return Verdict(VERIFIED, folder, claimed, expected,
                       f"{folder}: {claimed[:SHORT]} reproduced from "
                       f"{str(commit)[:12]}")

    # Missing is not None. A record written by `record()` always carries the
    # key, so an explicit null means git was asked and would not answer, and a
    # missing key means the writer never asked — which is what a forged file
    # looks like. Unknown is uncertifiable; absent is judged.
    dirt = doc.get("scan_commit_dirty", False)
    if dirt is None or bool(dirt):
        return Verdict(DIRTY, folder, claimed, expected,
                       f"{folder}: stamped {claimed[:SHORT]}, commit "
                       f"{str(commit)[:12]} gives {expected[:SHORT]} — the tree "
                       "was "
                       + ("not known to be clean" if dirt is None else "dirty")
                       + " when it scanned, so the commit does not describe the "
                         "code that ran and nothing here can certify it")
    return Verdict(FORGED, folder, claimed, expected,
                   f"{folder}: stamped {claimed[:SHORT]}, but commit "
                   f"{str(commit)[:12]} gives {expected[:SHORT]}")


def main():
    import json
    import paths
    root = pathlib.Path(__file__).resolve().parent
    rec = record(root)
    print("  this checkout")
    for k, v in rec.items():
        print(f"    {k:24} {v}")
    if not git_available(root):
        print("\n  git could not be asked here — no stamp below was compared "
              "to a commit.")
    print("\n  machine folders")
    seen = 0
    for mdir, f in paths.iter_machine_files(root, "totals.json"):
        seen += 1
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            print(f"    {mdir.name:32} UNREADABLE  {type(e).__name__}")
            continue
        v = verify(root, doc, folder=mdir.name)
        print(f"    {mdir.name:32} {v.status:15} {v.detail}")
    # A LISTING OF NOTHING IS NOT A CLEAN FLEET. Printing the count is the
    # difference between "no folder is forged" and "no folder was looked at".
    print(f"\n  {seen} machine folder(s) adjudicated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
