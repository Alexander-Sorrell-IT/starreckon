#!/usr/bin/env python3
"""The credential-ancestry rule, driven through link_tree's DIRECTORY branch.

    python3 adv_archive_dirstore.py

WHY THIS FILE EXISTS

`only_dir_secret` is computed for BOTH of link_tree's branches:

    only = None
    if os.path.isfile(src):
        src, only, top_only = dirname(src), basename(src), True
    only_dir_secret = (secret_dir(basename(src)) or secret_ancestor(src, HOME))

The isfile() branch is the one where a store path names ONE FILE. The other —
the one that falls through with `only` still None — is every store whose path
names a DIRECTORY, and those are the stores os.walk descends recursively. All
39 conversation stores are that shape.

adversarial_daemon.py guards this rule, and every check it has plants through
the isfile() branch:

    RG.link_tree(str(p), str(arch), True)      # p is a file -> `only` branch

So the half of the rule that covers recursively-walked stores — which is to
say the stores that go deep enough to actually reach a credential — had no
check at all. It could be reverted to the `False` initialiser it used to carry
and every one of them stays green. That is measured below, not assumed.

PROVEN AGAINST THE REVERT, NOT ASSUMED. Restore the old shape in a copy —

    only_dir_secret = False
    if os.path.isfile(src):
        src, only, top_only = ...
        only_dir_secret = (secret_dir(...) or secret_ancestor(...))

— and 73 of the 114 checks below go RED, every one of them on an ASSERTION
with a got/want, none by raising, and the suite still runs to completion so
the 41 that pass are passes and not checks nobody reached.

Measured on that same reverted copy, the existing ancestry attack in
adversarial_daemon.py scores 32 PASS and 0 FAIL, and an instrumented link_tree
records what it drove:

    existing ancestry attack, FAILED against the revert: []
    its link_tree calls, by branch: {'FILE': 11}

Eleven calls, not one of them a directory. That is the gap, stated as a
number.

WHAT STAYS GREEN BOTH WAYS, AND MUST. The 16 control checks, the run()
control, and the empty/gone cases. Over-refusal here is permanent record loss,
so a change that turned any of those red would be a worse defect than the one
this file covers.

THE TWO DIRECTIONS, AND ONLY ONE OF THEM IS ABOUT CREDENTIALS

Refusing too little puts an OAuth token in the archive under a second name.
Refusing too MUCH is permanent record loss: this program is the only copy for
7 of the 8 CLIs, none of which keep a counter. So every attack here is paired
with a control that must archive, and the controls are asserted positively —
the archived path exists AND the live file's nlink went to 2 — before any
"nothing was refused" line is allowed to mean anything.

HOW THIS SUITE REFUSES TO LIE ABOUT ITSELF

  * Every check compares a VALUE against an expected value. No substring of a
    string this program builds unconditionally.
  * "Nothing was refused" is never asserted alone. It only ever appears after
    the record it is about has been shown to be in the archive at nlink 2.
  * The archive-is-empty assertion uses the same walker as the
    archive-holds-these assertion, so a walker that always returns [] fails
    the controls.
  * An attack that raises is recorded as a FAILURE, and the final check
    asserts the total number of checks that RAN. A suite that exits early has
    not passed the checks it never reached.
"""
import contextlib
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import export_corpus as EC
import retention_guard as RG

FAILED = []
RUN = []            # every check name that actually executed
DROVE = []          # (src, is_a_directory) for every link_tree call made here

# How many checks must run. A literal, because the whole point is to notice
# when fewer of them ran than were written.
EXPECTED_CHECKS = 113

SPELLINGS = ("MCP-Secrets", "mcp-secrets.", "mcp-secrets ", ".credentials")
DEPTHS = (1, 2, 3)


def check(name, got, want, why=""):
    RUN.append(name)
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        print(f"        got {got!r}, want {want!r}" + (f" — {why}" if why else ""))
        FAILED.append(name)


@contextlib.contextmanager
def patched(**kw):
    """Swap module attributes for one attack, always putting them back."""
    old = {k: getattr(RG, k) for k in kw}
    for k, v in kw.items():
        setattr(RG, k, v)
    try:
        yield
    finally:
        for k, v in old.items():
            setattr(RG, k, v)


def quiet(fn):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        r = fn()
    return r, buf.getvalue()


def build(root, rel, body="q\n"):
    """Plant one file, returning its path. Parents created."""
    p = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(body)
    return p


def files_under(root):
    """Relative paths of every FILE under root, sorted; [] if root is absent.

    THE SAME WALKER ANSWERS BOTH QUESTIONS. "The archive holds nothing" and
    "the archive holds exactly these two records" go through this one function,
    so a walker that always returned [] would pass every refusal check and fail
    every control.
    """
    out = []
    for dirpath, _dn, files in os.walk(root):
        for f in files:
            out.append(os.path.relpath(os.path.join(dirpath, f), root)
                       .replace(os.sep, "/"))
    return sorted(out)


def refused():
    """The names REFUSED_CONFIG is holding, relative to the store root."""
    return sorted(n.replace(os.sep, "/") for _l, n, _p in RG.REFUSED_CONFIG)


def nlinks(*paths):
    return [os.stat(p).st_nlink for p in paths]


def clear_globals():
    """link_tree APPENDS; only run() clears. An attack that did not clear would
    read the previous attack's refusals and report them as its own."""
    for lst in (RG.REFUSED_CONFIG, RG.NOT_A_RECORD, RG.UNRECOGNISED,
                RG.FAILED_LINKS, RG.GHOSTS, RG.VANISHED):
        lst.clear()


def drive(src, label, home, archive, record=True):
    """One link_tree call, through the DIRECTORY branch, globals cleared first.

    `src` and whether it was a directory are recorded for the final check: a
    test that quietly handed link_tree a FILE would be re-testing the branch
    that already has 15 checks, and would pass against the revert.

    `record=False` is for the one call whose src is deliberately GONE, which is
    neither a file nor a directory. That call's own check asserts the note it
    produced, which is the proof of which branch it took.
    """
    if record:
        DROVE.append((src, os.path.isdir(src)))
    clear_globals()
    with patched(HOME=home, ARCHIVE=archive):
        n, _sk, note = RG.link_tree(src, label, True)
    return n, note, refused(), files_under(os.path.join(archive, label))


# ---------------------------------------------------------------------------

def a_store_directory_that_is_itself_a_secret_directory():
    """The store path names ~/.copilot/mcp-secrets. Nothing inside may be taken.

    GitHub's own Copilot CLI reference puts mcp-secrets/ and mcp-oauth-config/
    inside ~/.copilot, beside the session state, and stores.py is one line away
    from naming one of them: `.copilot/mcp-secrets` written as a conversation
    store arrives here as a DIRECTORY, walked recursively, with `only` None.

    The isfile() branch cannot reach this shape at all. There the secret
    component is chopped off the walk root by `dirname(src)`; here it IS the
    walk root, so `rel` never contains it either — os.walk yields "." for the
    root and "sub", "a/b" below it. `secret_dir(basename(src))` is the only
    rule that can see it, and on this branch it used to not be asked.

    FOUR FILES, THREE DEPTHS, AND NOT ONE OF THEM IS A CREDENTIAL BY NAME.
    `gh.json`, `history.jsonl` and `session.jsonl` are what `_is_loose_record`
    exists to ADMIT and what `_is_secret` is guaranteed not to match, so the
    directory rule is the only thing standing in the way of all four.
    """
    import shutil
    import tempfile

    d = tempfile.mkdtemp(prefix="dirstore-secret-")
    try:
        home = os.path.join(d, "home")
        rels = ("gh.json", "sub/history.jsonl", "a/b/history.jsonl",
                "a/b/c/session.jsonl")
        planted = [build(home, ".copilot/mcp-secrets/" + r,
                         "ghp_SECRET" if r.endswith("gh.json") else "q\n")
                   for r in rels]
        src = os.path.join(home, ".copilot", "mcp-secrets")

        check("the fixture planted four files inside the secret store directory",
              files_under(src), sorted(rels),
              "if the fixture is empty every refusal check below is vacuous")

        n, note, ref, arch = drive(src, "other/copilot",
                                   home, os.path.join(d, "archive"))

        check("a store directory that IS a secret directory archives nothing",
              (n, note), (0, "ok"),
              "the secret component is the walk root itself, so it appears in "
              "no rel and only basename(src) can see it")
        check("store IS a secret directory: the archive holds no file at all",
              arch, [])
        check("store IS a secret directory: every live file still has exactly "
              "one name", nlinks(*planted), [1, 1, 1, 1],
              "nlink 2 is the archive holding the same inode")
        check("store IS a secret directory: every refusal is NAMED in "
              "REFUSED_CONFIG", ref, sorted(rels),
              "a credential dropped anonymously reads like a clean run")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def a_directory_store_whose_ancestor_is_secret_at_depth_1_2_3():
    """The store path is BELOW a secret directory. Depth 1, 2 and 3.

        .copilot/mcp-secrets/store            depth 1
        .copilot/mcp-secrets/pad1/store       depth 2
        .copilot/mcp-secrets/pad1/pad2/store  depth 3

    Here `basename(src)` is "store" — not a secret name at any depth — and the
    secret component is above the walk root, so the per-component test over
    `rel` cannot see it either. `secret_ancestor(src, HOME)` is the only rule
    left, and the check below proves that by asserting that NOTHING inside the
    walk names a secret directory. If a component under the store root were
    secret, this attack would be testing a different rule and would pass
    against the revert.

    Each store holds a record at its root and one in a subdirectory, so both
    the `rel == "."` path and the `rel != "."` path are driven.
    """
    import shutil
    import tempfile

    d = tempfile.mkdtemp(prefix="dirstore-anc-")
    try:
        home = os.path.join(d, "home")
        for depth in DEPTHS:
            pads = "/".join(f"pad{i}" for i in range(1, depth))
            base = ".copilot/mcp-secrets/" + (pads + "/" if pads else "") + "store"
            src = os.path.join(home, *base.split("/"))
            planted = [build(home, f"{base}/history.jsonl"),
                       build(home, f"{base}/inner/history.jsonl")]

            planted_rels = files_under(src)
            inside = [c for rel in planted_rels
                      for c in rel.split("/")[:-1] if EC.secret_dir(c)]
            # BOTH HALVES IN ONE ASSERTION. "no component inside the walk is
            # secret" is trivially true of an EMPTY fixture, which is the shape
            # of control that certifies nothing. The files are named here so
            # the emptiness cannot be what makes it pass.
            check(f"depth {depth}: two records planted, and nothing INSIDE the "
                  f"walk names a secret directory",
                  (planted_rels, inside),
                  (["history.jsonl", "inner/history.jsonl"], []),
                  "otherwise the per-component rel test catches it and this "
                  "attack proves nothing about ancestry")

            n, note, ref, arch = drive(src, f"other/anc{depth}",
                                       home, os.path.join(d, f"archive{depth}"))

            check(f"depth {depth}: a store directory under a secret ancestor "
                  f"archives nothing", (n, note), (0, "ok"))
            check(f"depth {depth}: the archive holds no file at all", arch, [])
            check(f"depth {depth}: both live records still have exactly one "
                  f"name", nlinks(*planted), [1, 1])
            check(f"depth {depth}: both refusals are NAMED in REFUSED_CONFIG",
                  ref, ["history.jsonl", "inner/history.jsonl"])
    finally:
        shutil.rmtree(d, ignore_errors=True)


def a_hostile_spellings_of_the_secret_ancestor_at_every_depth():
    """Four spellings no exact match catches, at all three depths.

        MCP-Secrets     case
        mcp-secrets.    trailing dot   — creatable on Linux and macOS, not Windows
        'mcp-secrets '  trailing space — same
        .credentials    leading dot

    `set(rel.parts) & SECRET_DIRS` caught the first spelling of each pair and
    none of the others; fs_name() folds case, leading/trailing dots and
    whitespace (interleaved, in any order), and Unicode category Cf. Two of the
    five machines in this fleet run case-insensitive filesystems, where
    `MCP-Secrets` and `mcp-secrets` are not two directories at all.

    THE FOLD IS ASSERTED TO BE LOAD-BEARING. None of these four is a literal
    member of SECRET_DIRS, so a rule that compared literals answers False for
    every one of them — that is checked first, against the real set, so the
    twelve cases below cannot be passing for the trivial reason.

    AND THE SPELLING IS READ BACK OFF THE FILESYSTEM. A trailing space or dot
    that the filesystem silently dropped would leave this testing
    `mcp-secrets`, the one spelling that was never broken.
    """
    import shutil
    import tempfile

    d = tempfile.mkdtemp(prefix="dirstore-spell-")
    try:
        home = os.path.join(d, "home")

        check("no hostile spelling is a literal member of SECRET_DIRS",
              [s for s in SPELLINGS if s in EC.SECRET_DIRS], [],
              "if one were, the case below would pass without fs_name")
        check("fs_name folds all four hostile spellings onto a secret name",
              [EC.secret_dir(s) for s in SPELLINGS], [True, True, True, True])

        case = 0
        for spell in SPELLINGS:
            for depth in DEPTHS:
                case += 1
                pads = "/".join(f"pad{i}" for i in range(1, depth))
                root = f"case{case}"
                base = (f"{root}/{spell}/" + (pads + "/" if pads else "")
                        + "store")
                src = os.path.join(home, *base.split("/"))
                rec = build(home, f"{base}/history.jsonl")
                parent = os.path.join(home, root)
                tag = f"{spell!r} at depth {depth}"

                check(f"{tag}: the fixture kept its exact spelling on disk",
                      [x for x in os.listdir(parent) if x == spell], [spell],
                      "a filesystem that folded it would leave this testing "
                      "the one spelling that was never broken")

                n, note, ref, arch = drive(
                    src, f"other/spell{case}", home,
                    os.path.join(d, f"archive{case}"))

                check(f"{tag}: the store archives nothing", (n, note), (0, "ok"))
                check(f"{tag}: the archive holds no file at all", arch, [])
                check(f"{tag}: the live record still has exactly one name",
                      nlinks(rec), [1])
                check(f"{tag}: the refusal is NAMED in REFUSED_CONFIG",
                      ref, ["history.jsonl"])
    finally:
        shutil.rmtree(d, ignore_errors=True)


def a_zero_archived_has_three_causes_and_they_must_not_read_alike():
    """`(0, 'ok')` is what a REFUSAL returns. It is also what NOTHING returns.

    This is the disease this repository keeps catching in itself: absent looks
    exactly like zero. Three different things make a directory store archive
    nothing —

        the store is under a secret ancestor   (0, 'ok')     refusals NAMED
        the store directory is EMPTY           (0, 'ok')     no refusals
        the store directory is GONE            (0, 'absent') no refusals

    — and the first two return the SAME TUPLE. REFUSED_CONFIG is the only thing
    that separates "a credential was stopped" from "there was nothing there",
    which is the whole reason every refusal check in this file asserts the
    NAMES and not just the count. If the names were dropped, an empty store and
    a store full of OAuth tokens would produce identical output, and so would
    the run where a tool started writing tokens into a directory it did not
    write them into last week.

    All three fixtures sit under the same secret ancestor, so the rule under
    test is the one deciding, and the deletion is a SCENARIO rather than
    teardown.
    """
    import shutil
    import tempfile

    d = tempfile.mkdtemp(prefix="dirstore-zero-")
    try:
        home = os.path.join(d, "home")
        secret = ".copilot/mcp-secrets"
        build(home, f"{secret}/full/history.jsonl")
        os.makedirs(os.path.join(home, *f"{secret}/empty".split("/")),
                    exist_ok=True)
        gone = os.path.join(home, *f"{secret}/gone".split("/"))
        os.makedirs(gone, exist_ok=True)

        full = drive(os.path.join(home, *f"{secret}/full".split("/")),
                     "other/full", home, os.path.join(d, "a-full"))
        empty = drive(os.path.join(home, *f"{secret}/empty".split("/")),
                      "other/empty", home, os.path.join(d, "a-empty"))
        shutil.rmtree(gone)          # the scenario, not the teardown
        vanished = drive(gone, "other/gone", home, os.path.join(d, "a-gone"),
                         record=False)

        check("a populated store under a secret ancestor: nothing linked, and "
              "the file NAMED", ((full[0], full[1]), full[2]),
              ((0, "ok"), ["history.jsonl"]))
        check("an EMPTY store directory: nothing linked, and nothing to name",
              ((empty[0], empty[1]), empty[2]), ((0, "ok"), []),
              "identical to the line above except for the names, which is why "
              "the names are the check")
        check("a store directory that is GONE: nothing linked, and the note "
              "says which of the three it was",
              ((vanished[0], vanished[1]), vanished[2]), ((0, "absent"), []))
        check("so the three causes of 'nothing archived' are three facts",
              len({(full[1], tuple(full[2])), (empty[1], tuple(empty[2])),
                   (vanished[1], tuple(vanished[2]))}), 3,
              "collapse any two and the run where a credential appeared reads "
              "exactly like the run before it")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def a_control_a_legitimate_directory_store_still_archives():
    """OVER-REFUSAL IS PERMANENT RECORD LOSS. The same depths, no secret name.

    A rule that refused this would be worse than the hole it closed: the
    archive is the only copy for 7 of the 8 CLIs, none of which keep a counter,
    so a record that never gets a second name is a record that stops existing
    the next time the tool sweeps.

    Asserted POSITIVELY — the archived path exists and the live inode's nlink
    went to 2 — before "nothing was refused" is allowed to mean anything.
    """
    import shutil
    import tempfile

    d = tempfile.mkdtemp(prefix="dirstore-ctl-")
    try:
        home = os.path.join(d, "home")
        shallow = build(home, ".copilot/session-state/history.jsonl")
        deep = build(home, ".copilot/session-state/a/b/history.jsonl")
        src = os.path.join(home, ".copilot", "session-state")

        n, note, ref, arch = drive(src, "other/copilot",
                                   home, os.path.join(d, "archive"))

        check("a legitimate directory store archives both of its records",
              (n, note), (2, "ok"),
              "a refusal here is a record that never gets a second name")
        check("control: the archive holds exactly the two records, layout kept",
              arch, ["a/b/history.jsonl", "history.jsonl"])
        check("control: both live records are now at the archive's inode too",
              nlinks(shallow, deep), [2, 2])
        check("control: and nothing was refused on the way through", ref, [])
    finally:
        shutil.rmtree(d, ignore_errors=True)


def a_control_home_named_keys_and_home_under_certs():
    """`keys` and `certs` ARE secret directory names. HOME is not judged.

    secret_ancestor() stops at HOME, and the boundary is the hard part of the
    rule. A user whose HOME is /home/keys, or a machine mounting
    /Volumes/certs/someone, would have every record they own refused by a
    component nobody in this program chose — the account name and the mount
    table are not the store map.

    Driven through the DIRECTORY branch: the store is ~/.ollama itself, walked
    recursively, holding a record at the root, a record one level down, and the
    private key that sits beside them on this machine (ino 43133463, nlink=1).
    The key must still be refused — by its NAME, which is a depth-independent
    rule that neither branch nor boundary can switch off — and the two records
    must still archive.
    """
    import shutil
    import tempfile

    d = tempfile.mkdtemp(prefix="dirstore-home-")
    try:
        homes = {
            "HOME is named 'keys'": os.path.join(d, "b1", "keys"),
            "HOME sits under 'certs'": os.path.join(d, "b2", "certs", "someone"),
        }
        for i, (why, home) in enumerate(homes.items()):
            rec = build(home, ".ollama/history", "what is a hard link\n")
            sub = build(home, ".ollama/sub/history.jsonl")
            key = build(home, ".ollama/id_ed25519",
                        "-----BEGIN OPENSSH PRIVATE KEY-----")
            src = os.path.join(home, ".ollama")
            label = "other/ollama"
            archive = os.path.join(d, f"archive{i}")

            n, note, ref, arch = drive(src, label, home, archive)

            check(f"{why}: ~/.ollama archives both of its records",
                  (n, note), (2, "ok"),
                  "components at or above HOME were chosen by the account and "
                  "the mount table, not by the store map")
            check(f"{why}: the archive holds exactly the two records",
                  arch, ["history", "sub/history.jsonl"])
            check(f"{why}: both live records are at the archive's inode",
                  nlinks(rec, sub), [2, 2])
            check(f"{why}: the private key beside them stays at exactly one "
                  f"name", nlinks(key), [1])
            check(f"{why}: and the key is the ONLY thing refused, by name",
                  ref, ["id_ed25519"])
            check(f"{why}: the key did not reach the archive",
                  os.path.exists(os.path.join(archive, label, "id_ed25519")),
                  False)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def a_through_run_which_is_the_only_caller():
    """A store map entry is how a directory store actually reaches link_tree.

    run() walks OTHER_SOURCES (recursive, records=None) and ROOT_FILE_SOURCES
    (top_only, records honoured) and hands BOTH of them paths built as
    os.path.join(HOME, *rel.split("/")). Both land on the directory branch when
    the rel names a directory, which is what every one of the 39 conversation
    stores does.

    Four stores, three of which must archive nothing:

        good        .copilot/session-state             the control
        deep        .copilot/mcp-secrets/store         secret ANCESTOR
        secretroot  .copilot/mcp-secrets               the store IS the secret dir
        rootdeep    .copilot/mcp-secrets/rootstore     top_only, secret ANCESTOR

    and the refusals must be PRINTED. A credential that is silently dropped
    makes the run where a new one appears in a tool's store byte-identical to
    the run before it, which is the failure this whole program is written
    around.
    """
    import shutil
    import tempfile

    d = tempfile.mkdtemp(prefix="dirstore-run-")
    try:
        home = os.path.join(d, "home")
        archive = os.path.join(d, "archive")
        gh = build(home, ".copilot/mcp-secrets/gh.json", "ghp_SECRET")
        inner = build(home, ".copilot/mcp-secrets/store/history.jsonl")
        rooted = build(home, ".copilot/mcp-secrets/rootstore/history.jsonl")
        good = build(home, ".copilot/session-state/a/b/history.jsonl")

        os.environ["RETENTION_GUARD_LEDGER"] = "0"
        try:
            with patched(HOME=home, ARCHIVE=archive,
                         OTHER_SOURCES={
                             "good": [".copilot/session-state"],
                             "deep": [".copilot/mcp-secrets/store"],
                             "secretroot": [".copilot/mcp-secrets"]},
                         ROOT_FILE_SOURCES={
                             "rootdeep": [".copilot/mcp-secrets/rootstore"]},
                         ROOT_FILE_RECORDS={},
                         claude_profiles=lambda: [],
                         windows_side_profiles=lambda: []):
                _rc, log = quiet(lambda: RG.run(apply=True))
        finally:
            os.environ.pop("RETENTION_GUARD_LEDGER", None)

        other = os.path.join(archive, "other")
        check("run(): the legitimate deep record is archived, layout kept",
              files_under(os.path.join(other, "good")),
              ["a/b/history.jsonl"],
              "the control comes first — an over-refusing run passes every "
              "line below it")
        check("run(): a store under a secret ancestor archived nothing",
              files_under(os.path.join(other, "deep")), [])
        check("run(): a store that IS a secret directory archived nothing",
              files_under(os.path.join(other, "secretroot")), [])
        check("run(): a top_only store under a secret ancestor archived nothing",
              files_under(os.path.join(other, "rootdeep")), [])
        check("run(): every live file inside the secret directory still has "
              "exactly one name", nlinks(gh, inner, rooted), [1, 1, 1])
        check("run(): the legitimate record is the one that gained a name",
              nlinks(good), [2])
        check("run(): the refusals are printed, with their names",
              ("REFUSED" in log, "gh.json" in log, "history.jsonl" in log),
              (True, True, True), f"got {log!r}")
        check("run(): and the printed refusal count is all five of them",
              "5 config/credential file(s) REFUSED" in log, True,
              f"got {log!r}")
        check("run(): exactly one file was linked, and it is the control",
              "1 file(s) linked" in log, True, f"got {log!r}")
    finally:
        shutil.rmtree(d, ignore_errors=True)


ATTACKS = [
    ("the store directory IS a secret directory",
     a_store_directory_that_is_itself_a_secret_directory),
    ("a secret ANCESTOR above a directory store, depth 1/2/3",
     a_directory_store_whose_ancestor_is_secret_at_depth_1_2_3),
    ("hostile spellings of that ancestor, every depth",
     a_hostile_spellings_of_the_secret_ancestor_at_every_depth),
    ("refused, empty and gone must not read alike",
     a_zero_archived_has_three_causes_and_they_must_not_read_alike),
    ("CONTROL: a legitimate directory store still archives",
     a_control_a_legitimate_directory_store_still_archives),
    ("CONTROL: HOME named 'keys', HOME under 'certs'",
     a_control_home_named_keys_and_home_under_certs),
    ("through run(), the only caller",
     a_through_run_which_is_the_only_caller),
]


def main():
    print("ARCHIVE — the credential rule on link_tree's DIRECTORY branch\n")
    for name, fn in ATTACKS:
        print(f"{name}:")
        try:
            fn()
        except Exception as e:      # noqa: BLE001
            # A CRASH IS NOT COVERAGE. adv_documents.py died at KeyError
            # 'inputs' and 11 later checks never ran, in a suite whose summary
            # counted only the ones that did. Recorded as a failure here, and
            # the count check below fails as well because the checks this
            # attack did not reach are missing from RUN.
            print(f"  FAIL  {name} RAISED {type(e).__name__}: {e}")
            FAILED.append(f"{name} raised")
        print()

    print("suite integrity:")
    drove = len(DROVE)
    check("every link_tree call this suite made was handed a path", drove, 21,
          "the attacks above are the only source of these")
    check("and not one of them landed on the isfile() branch",
          [s for s, isdir in DROVE if not isdir], [],
          "a FILE src re-tests the branch that already has 15 checks and "
          "passes against the revert")
    ran = len(RUN)
    check("every check written in this file ran", ran, EXPECTED_CHECKS,
          "fewer means an attack exited early and its remaining checks were "
          "never reached")

    print()
    total = len(RUN)
    if FAILED:
        print(f"{len(FAILED)} of {total} FAILED")
        for f in FAILED:
            print(f"  - {f}")
        return 1
    print(f"all {total} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
