#!/usr/bin/env python3
"""Can the gate see a scanner_version that no commit could have produced?

    python3 adv_forged_stamp.py

THE ATTACK

`scanner_version` is sha256(sessions.py + analyze_tokens.py)[:12], and the
machine that writes it into its own totals.json is the only thing that decides
what it says. check_consistency.py's `every machine scanned by the same version`
compares those strings TO EACH OTHER. So the red team's move is not to change a
number — it is to have two machines stamp the same made-up value. They agree
perfectly. Every partition still sums. The banner reads 0 failed.

That is what this file plants, and the evidence is taken three ways for every
attack:

    AFTER     the gate as it stands in this checkout
    BEFORE    the same file with the scan-identity section sliced out at its
              anchors — the exact code that was here before the fix
    HEAD      `git show HEAD:check_consistency.py`, which proves the hole is
              structural and pre-existing rather than something introduced this
              morning

A scenario is only counted if BEFORE lets the forgery through and AFTER names
it. A test that is red for both is testing the fixture, not the fix.

AND THE OTHER DIRECTION, WHICH COSTS MORE TO GET WRONG

An honest scan that this verifier rejects sends somebody to four computers to
find out why. So the control scenarios are first-class here: two honest
machines must produce six clean checks; a fleet that records no commit at all —
which is every machine in this tree today — must WARN and must not turn the gate
red; a scan over a dirty tree must be reported as uncertifiable rather than
accused.

WHY THE GATE RUNS UNDER A STUBBED git

The verdict has to depend on what git says, so what git says is the input. A
directory of blob files is served by a `git` on PATH that answers in BYTES, and
the fixtures then differ only in which commit they name and what they stamp.
One scenario uses no stub at all: `an honest record verifies against real git`
runs the verifier against THIS repository's real HEAD and its real blobs, so the
whole suite does not rest on a stub agreeing with itself.

Nothing here writes outside a temporary directory, and no git command run by
this file mutates anything.
"""

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

SRC = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(SRC))
import paths                                                       # noqa: E402
import scan_identity                                               # noqa: E402
import sessions                                                    # noqa: E402

PASS, FAIL, ERROR = [], [], []

# The checkout whose REAL commits and REAL blobs the no-stub scenario reads, and
# whose committed gate the HEAD comparison runs. It is this directory, except
# for one caller: the revert harness copies these files into a throwaway that is
# not a checkout, and a scenario that quietly turned into "git said no" there
# would report the revert as caught for the wrong reason. It moves WHERE the
# evidence is read from and never WHAT is asserted; every command run against it
# is read-only.
REAL = pathlib.Path(os.environ.get("ADV_STAMP_REPO") or SRC)

# The six checks this fix adds. Named in full, because matching on a fragment
# like "stamp" would also match `every machine scanned by the same version`'s
# neighbours and the suite would be reporting on a check it did not mean.
C_PRESENT = "the scan-identity verifier is present"
C_ADJUDICATED = "every machine folder was adjudicated for scan identity"
C_CHECKED = "every machine's stamp was checked against the commit it claims"
C_REPRO = "every machine's stamp is reproducible from the commit it claims"
C_EXISTS = "every scan commit named by a machine exists in this repository"
C_DIRTY = "no machine's stamp rests on a tree that was dirty when it scanned"
STAMP_CHECKS = (C_PRESENT, C_ADJUDICATED, C_CHECKED, C_REPRO, C_EXISTS, C_DIRTY)

# The check that certifies the forgery today: it compares the labels to each
# other and is satisfied when they match.
C_SAME = "every machine scanned by the same version"

FAKE_HEAD = "1c0ffee5a11ad00d1c0ffee5a11ad00d1c0ffee5"
OTHER_COMMIT = "2b0bb1e50fa11e2b0bb1e50fa11e2b0bb1e50fa1"
NEVER_FETCHED = "9999999999999999999999999999999999999999"
# The string `adversarial.a_fake_scanner_version` plants, verbatim, extended to
# a full digest so the forgery is internally consistent and only the commit can
# expose it.
FORGED_SHORT = "deadbeefcafe"
FORGED_FULL = FORGED_SHORT + "0" * (64 - len(FORGED_SHORT))


def check(name, got, want, why=""):
    (PASS if got == want else FAIL).append((name, got, want, why))


# --------------------------------------------------------------------------
# a fleet, planted


def _split(total):
    out = int(total * 0.02)
    cc = int(total * 0.03)
    inp = int(total * 0.01)
    return {"input_tokens": inp, "cache_creation_input_tokens": cc,
            "cache_read_input_tokens": total - inp - cc - out,
            "output_tokens": out}


def plant_machine(root, folder, label, account, total, identity,
                  day="2026-01-05", stamp="2026-01-06T00:00:00+00:00"):
    """One machine folder whose every existing invariant already holds.

    Buckets sum to the account, accounts sum to the machine, sessions sum to the
    same figure, and by_account.csv corroborates totals.json. That is the point:
    the defect planted here has to survive every check the gate already makes,
    because in the real repository it did.
    """
    f = _split(total)
    totals = {"machine": label, "generated_at": stamp,
              "grand_total_tokens": total,
              "accounts": [{"account": account,
                            "config_dir": f"/home/op/{folder}/.claude",
                            "grand_total": total, "sessions": 1, "turns": 3,
                            "totals": f, "by_model": {"claude-opus-5": f},
                            "by_day": {day: total}}]}
    totals.update(identity)
    md = paths.machine(root / folder)
    md.joinpath("totals.json").write_text(json.dumps(totals, indent=1),
                                          encoding="utf-8")
    sess = [{"cli": "claude", "session_id": f"{folder}-claude",
             "account": account, "project": "p",
             "start": f"{day}T01:00:00Z", "end": f"{day}T02:00:00Z",
             "turns": 3, "tokens": f, "duration_min": 60.0,
             "duration_tight_min": 60.0, "elapsed_min": 60.0, "total": total,
             "sent": total - f["output_tokens"], "received": f["output_tokens"],
             "model": "claude-opus-5", "provider": "anthropic", "billed": True}]
    sdoc = {"machine": label, "generated_at": stamp, "stats_cache": [],
            "readers": [{"cli": "claude", "installed": True}],
            "sessions": sess}
    sdoc.update(identity)
    md.joinpath("sessions.json").write_text(json.dumps(sdoc, indent=1),
                                            encoding="utf-8")
    md.joinpath("by_account.csv").write_text(
        "account,config_dir,sessions,turns,input_tokens,"
        "cache_creation_input_tokens,cache_read_input_tokens,output_tokens,"
        "total\n"
        f'{account},/home/op/{folder}/.claude,1,3,{f["input_tokens"]},'
        f'{f["cache_creation_input_tokens"]},{f["cache_read_input_tokens"]},'
        f'{f["output_tokens"]},{total}\n', encoding="utf-8")
    hw = {"hostname": f"host-{folder}"}
    hw.update(identity)
    md.joinpath("hardware.json").write_text(json.dumps(hw), encoding="utf-8")


def scanner_blobs():
    """{commit: {filename: bytes}} — what git will be made to hold.

    Real bytes off this repository, so the digest under test is a digest of
    something that exists. OTHER_COMMIT carries a different scanner, because a
    fixture where every commit holds identical files cannot tell a verifier that
    reads the named commit from one that reads whatever it likes.
    """
    base = {n: (SRC / n).read_bytes() for n in scan_identity.SCANNER_FILES}
    return {FAKE_HEAD: dict(base),
            OTHER_COMMIT: {n: b + b"\n# an older scanner\n"
                           for n, b in base.items()}}


BLOBS = scanner_blobs()


def digest_at(commit):
    """The stamp an honest scan from `commit` would carry.

    A commit git does not hold falls back to the scanner as it is here: that is
    a real machine's real digest, naming a commit this checkout cannot resolve,
    which is the honest-but-unresolvable case and not a forgery.
    """
    files = BLOBS.get(commit) or BLOBS[FAKE_HEAD]
    return scan_identity.digest([files[n]
                                 for n in scan_identity.SCANNER_FILES])


def honest(commit=FAKE_HEAD):
    """The identity fields a real scan writes: the commit, and its own digest."""
    full = digest_at(commit)
    return {"scanner_version": full[:scan_identity.SHORT],
            "scanner_version_sha256": full,
            "scan_commit": commit, "scan_commit_dirty": False,
            "scanner_files": list(scan_identity.SCANNER_FILES)}


def forged(commit=FAKE_HEAD, **over):
    """A stamp the machine simply typed, alongside a commit that is real."""
    d = {"scanner_version": FORGED_SHORT,
         "scanner_version_sha256": FORGED_FULL,
         "scan_commit": commit, "scan_commit_dirty": False,
         "scanner_files": list(scan_identity.SCANNER_FILES)}
    d.update(over)
    return d


def legacy():
    """What every machine in this tree carries today: a stamp and no commit."""
    return {"scanner_version": scan_identity.working_tree_version(SRC)[:12]}


ALPHA = ("alpha", "Alpha", "a@example.com", 1_000_000)
BETA = ("beta", "Beta", "b@example.com", 2_000_000)


def build(tmp, fleet, blobs=None):
    """A repository with `fleet` planted and a `git` that answers from `blobs`.

    `fleet` is [(folder, label, account, total, identity)]. `blobs` maps a
    commit to {filename: bytes-on-disk}, which is what the verifier will
    recompute the stamp from.
    """
    root = tmp / "repo"
    root.mkdir(parents=True, exist_ok=True)
    for p in SRC.iterdir():
        if p.suffix == ".py":
            shutil.copy2(p, root / p.name)
    (root / "accounts.json").write_text(
        json.dumps({"accounts": [], "profiles": []}), encoding="utf-8")
    (root / "machines.json").write_text(json.dumps(
        {"machines": [{"folder": f, "label": lab} for f, lab, *_ in fleet]}),
        encoding="utf-8")
    for folder, label, account, total, identity in fleet:
        plant_machine(root, folder, label, account, total, identity)
    return root, git_stub(tmp, blobs if blobs is not None else default_blobs(tmp))


def default_blobs(tmp):
    """BLOBS, written to disk, as {commit: {filename: path}} for the stub."""
    store = tmp / "blobs"
    out = {}
    for commit, files in BLOBS.items():
        d = store / commit
        d.mkdir(parents=True, exist_ok=True)
        out[commit] = {}
        for name, data in files.items():
            (d / name).write_bytes(data)
            out[commit][name] = str(d / name)
    return out


# --------------------------------------------------------------------------
# a stubbed git, answering in bytes

GIT_STUB = r'''#!/usr/bin/env python3
"""The git questions this gate asks, answered from a JSON script."""
import json, os, pathlib, sys

spec = json.loads(pathlib.Path(os.environ["ADV_GIT_SCRIPT"]).read_text())
a = sys.argv[1:]
blobs = spec.get("blobs", {})

if a[:2] == ["rev-parse", "--git-dir"]:
    print(".git")
    sys.exit(0)
if a[:2] == ["rev-parse", "HEAD"]:
    print(spec.get("head", ""))
    sys.exit(0)
if a[:1] == ["rev-parse"] and "--verify" in a:
    sys.exit(0 if a[-1].replace("^{commit}", "") in blobs else 1)
if a[:1] == ["status"]:
    sys.exit(0)
if a[:1] == ["show"] and ":" in a[-1]:
    rev, _, path = a[-1].partition(":")
    p = blobs.get(rev, {}).get(path)
    if p is None:
        sys.exit(1)
    # BYTES. `print` would append a newline the blob does not have and every
    # honest machine would read as forged.
    sys.stdout.buffer.write(pathlib.Path(p).read_bytes())
    sys.exit(0)
if a[:1] == ["log"] and "--diff-filter=A" in a:
    sys.exit(0)
sys.exit(1)
'''


def git_stub(tmp, blobs):
    binp = tmp / "bin"
    binp.mkdir(exist_ok=True)
    (binp / "git").write_text(GIT_STUB, encoding="utf-8")
    (binp / "git").chmod(0o755)
    spec = tmp / "gitscript.json"
    spec.write_text(json.dumps({"head": FAKE_HEAD, "blobs": blobs}),
                    encoding="utf-8")
    return dict(os.environ, PATH=f"{binp}{os.pathsep}{os.environ['PATH']}",
                ADV_GIT_SCRIPT=str(spec))


# --------------------------------------------------------------------------
# running the gate, three ways

ANCHOR_TOP = ("    # 4. AND EVERY OTHER MACHINE'S STAMP MUST BE REPRODUCIBLE "
              "FROM THE COMMIT\n")
ANCHOR_END = "    # Did a rescan LOSE tokens?"


def before_gate(tmp):
    """This checkout's gate with the scan-identity section removed.

    Sliced at its own anchors rather than reconstructed, so BEFORE is the file
    that was here and not an approximation of it. A missing anchor raises: a
    revert that did not apply must never be reported as a revert that was
    survived.
    """
    src = (SRC / "check_consistency.py").read_text(encoding="utf-8")
    i, j = src.find(ANCHOR_TOP), src.find(ANCHOR_END)
    if i < 0 or j < 0 or j <= i:
        raise RuntimeError("ANCHOR MISSING in check_consistency.py — BEFORE "
                           f"could not be built (top={i}, end={j})")
    p = tmp / "before_check_consistency.py"
    p.write_text(src[:i] + src[j:], encoding="utf-8")
    return p


def head_gate(tmp):
    """`git show HEAD:check_consistency.py`, read-only, from this repository.

    Read from REAL, and an unreadable HEAD raises rather than quietly dropping
    the scenario: a comparison that did not happen is not a comparison that
    agreed.
    """
    r = subprocess.run(["git", "show", "HEAD:check_consistency.py"],
                       cwd=str(REAL), capture_output=True)
    if r.returncode != 0 or not r.stdout:
        raise RuntimeError("could not read HEAD:check_consistency.py")
    p = tmp / "head_check_consistency.py"
    p.write_bytes(r.stdout)
    return p


def gate(root, env, gate_src=None):
    """({check: PASS|FAIL|WARN}, output) — or (None, output) if it never ran.

    The summary line is looked for FIRST. A run that did not reach its own
    summary has not passed the checks it never printed, and `grep -c FAIL` over
    output that was never produced returns 0.
    """
    target = root / "check_consistency.py"
    if gate_src:
        shutil.copy2(gate_src, target)
    r = subprocess.run([sys.executable, str(target)], cwd=str(root),
                       capture_output=True, text=True, timeout=1800, env=env)
    out = r.stdout + r.stderr
    if " checks, " not in out:
        return None, out
    tags = {}
    for line in out.splitlines():
        s = line.strip()
        for t in ("PASS", "FAIL", "WARN"):
            if s.startswith(t + "  "):
                tags.setdefault(s[len(t):].strip().split("   ")[0].strip(), t)
                break
    return tags, out


def tag_of(tags, name):
    """The tag of the check called `name`, or 'ABSENT' if it did not run.

    ABSENT, not None, and never silently: a check that is not in the output did
    not pass — nobody asked it.
    """
    for n, t in tags.items():
        if n == name or n.startswith(name):
            return t
    return "ABSENT"


def failing(tags):
    return sorted(n for n, t in tags.items() if t == "FAIL")


def detail_for(out, name):
    """The whole reported line for `name`, so the folders it names can be read."""
    for line in out.splitlines():
        s = line.strip()
        if s[6:].startswith(name):
            return s
    return ""


def run_three(tmp, fleet, blobs=None, with_head=False):
    """(after, before, head) tag maps for one planted fleet.

    The same tree is handed to each gate, in its own copy, so the only variable
    between the three answers is the gate.
    """
    out = {}
    for label, src in (("after", None), ("before", before_gate(tmp)),
                       ("head", head_gate(tmp) if with_head else None)):
        if label == "head" and not with_head:
            continue
        sub = tmp / label
        sub.mkdir(exist_ok=True)
        root, env = build(sub, fleet, blobs)
        tags, text = gate(root, env, src)
        if tags is None:
            raise RuntimeError(f"the {label} gate never reached its summary:\n"
                               f"{text[-1200:]}")
        out[label] = (tags, text)
    return out


# --------------------------------------------------------------------------
# scenarios. (function, how many checks it must record)


def s_unit_against_real_git(tmp):
    """The verifier, against THIS repository's real commits and real blobs.

    No stub anywhere in this scenario. If it passes, something in the suite has
    genuinely been verified against bytes git holds — which is the one thing a
    gate full of "none of them is forged" cannot establish on its own.
    """
    head = scan_identity.head_commit(REAL)
    expected = scan_identity.version_at_commit(REAL, head)
    check("the verifier reproduces a real commit's scanner digest",
          isinstance(expected, str) and len(expected), 64,
          f"git show {str(head)[:12]}:sessions.py + analyze_tokens.py")
    # The digest here and the stamp sessions.py writes must be the same number.
    # If they ever drift — a file added to one list and not the other — every
    # honest machine in the fleet would read as forged, and this is the line
    # that says so before anyone drives to a laptop.
    check("the full digest truncates to the stamp the scanner writes",
          scan_identity.working_tree_version(SRC)[:scan_identity.SHORT],
          sessions.scanner_version(),
          "scan_identity.SCANNER_FILES has drifted from "
          "sessions.scanner_version()")
    good = {"scan_commit": head, "scan_commit_dirty": False,
            "scanner_version_sha256": expected,
            "scanner_version": (expected or "")[:12]}
    check("an honest record verifies against real git",
          scan_identity.verify(REAL, good, folder="real").status,
          scan_identity.VERIFIED)
    bad = dict(good, scanner_version=FORGED_SHORT,
               scanner_version_sha256=FORGED_FULL)
    check("a typed-in stamp on a real commit is FORGED",
          scan_identity.verify(REAL, bad, folder="real").status,
          scan_identity.FORGED)
    check("a stamp naming a commit nobody has is not called a forgery",
          scan_identity.verify(REAL, dict(good, scan_commit=NEVER_FETCHED),
                               folder="real").status,
          scan_identity.UNKNOWN_COMMIT,
          "it is unresolvable here, which is a different sentence")
    check("a stamp with no commit is NO_COMMIT",
          scan_identity.verify(REAL, {"scanner_version": "2e512dc55519"},
                               folder="real").status,
          scan_identity.NO_COMMIT)
    # EMPTY: a document with nothing in it at all.
    check("an empty document is NO_STAMP, not verified",
          scan_identity.verify(REAL, {}, folder="real").status,
          scan_identity.NO_STAMP)
    check("a mismatch over a dirty tree is DIRTY, never VERIFIED",
          scan_identity.verify(REAL, dict(bad, scan_commit_dirty=True),
                               folder="real").status,
          scan_identity.DIRTY)
    doctored = dict(good, scanner_version=FORGED_SHORT)
    check("editing only the displayed 12 characters is FORGED",
          scan_identity.verify(REAL, doctored, folder="real").status,
          scan_identity.FORGED,
          "the short field must be the head of the full digest beside it")
    check("a commit that is not even a string is rejected, not raised",
          scan_identity.verify(REAL, dict(good, scan_commit=["c0ffee"]),
                               folder="real").status,
          scan_identity.UNKNOWN_COMMIT)


def s_control_two_honest_machines(tmp):
    """Two real scans. Nothing in the new section may say a word about them."""
    fleet = [ALPHA + (honest(),), BETA + (honest(OTHER_COMMIT),)]
    r = run_three(tmp, fleet)
    tags, out = r["after"]
    noisy = sorted(n for n in STAMP_CHECKS if tag_of(tags, n) != "PASS")
    check("CONTROL: six clean checks over two honest machines", noisy, [],
          "an over-strict verifier that rejects a real scan costs a visit to "
          "the machine that produced it")
    check("CONTROL: every stamp check actually ran",
          sorted(n for n in STAMP_CHECKS if tag_of(tags, n) == "ABSENT"), [],
          "a check that is not in the output did not pass")
    check("CONTROL: the two machines were adjudicated, not skipped",
          tag_of(tags, C_CHECKED), "PASS",
          "PASS here means both stamps reached a real comparison against a "
          "commit; it is the population the forgery checks are counted over")


def s_red_team_two_machines_one_forged_stamp(tmp):
    """THE ATTACK. Both machines stamp the same invented value.

    They agree with each other, so the check that compares the labels is
    satisfied — and that is the whole of what the gate had.
    """
    ident = forged()
    fleet = [ALPHA + (ident,), BETA + (dict(ident),)]
    r = run_three(tmp, fleet, with_head=True)
    after, aout = r["after"]
    before, _bout = r["before"]
    head, hout = r["head"]

    check("the label-versus-label check is satisfied by the forged pair",
          tag_of(after, C_SAME), "PASS",
          "both machines carry deadbeefcafe, so they agree perfectly")
    check("AFTER: the forgery is named", tag_of(after, C_REPRO), "FAIL")
    line = detail_for(aout, C_REPRO)
    check("AFTER: both forged folders are named in the failure",
          sorted({f for f in ("alpha", "beta") if f in line}),
          ["alpha", "beta"], line[:200])
    check("BEFORE: the same tree passed every check the old gate had",
          tag_of(before, C_REPRO), "ABSENT",
          "the section did not exist, so nothing compared a stamp to a commit")
    check("BEFORE: the forgery adds no failure to the old gate",
          failing(before), [n for n in failing(after) if n not in STAMP_CHECKS],
          "every fatal failure the new gate reports on this tree, apart from "
          "the forgery itself, was already there — so the difference between "
          "the two runs is exactly the check that was added")
    # THE POPULATION FIRST. `no check failed` over a run whose output nobody
    # parsed is what a run that never happened also looks like, so how many
    # checks the committed gate reported is asserted in the same breath.
    #
    # This used to assert that HEAD PASSED the forgery — documenting a gap where
    # the committed gate had no stamp verification. That gap is now closed: HEAD
    # carries the full scan_identity section and must CATCH the forgery, exactly
    # as the AFTER gate does. The check is kept (same shape, flipped expectation)
    # so a revert that re-opens the gap fails here immediately.
    head_failures = [n for n, t in head.items() if t == "FAIL"]
    check("HEAD: the committed gate catches the forgery",
          (C_REPRO in head_failures, len(head) > 0),
          (True, True),
          "HEAD must reject a forged stamp; if this fails the committed gate has "
          "lost its scan-identity section — the forgery passes again. "
          "HEAD reported: " + (hout.strip().splitlines()[-1][:80] if hout else "?"))


def s_one_machine_forged_one_honest(tmp):
    """An honest machine standing next to a forged one must stay unaccused."""
    fleet = [ALPHA + (honest(),), BETA + (forged(),)]
    r = run_three(tmp, fleet)
    after, aout = r["after"]
    before, _ = r["before"]
    line = detail_for(aout, C_REPRO)
    check("the forged machine is named", tag_of(after, C_REPRO), "FAIL")
    check("only the forged machine is named", ("alpha" in line, bool(line)),
          (False, True),
          f"the honest folder must not appear, and the line must exist for "
          f"that to mean anything: {line[:200]}")
    check("beta is the one named", "beta" in line, True, line[:200])
    check("BEFORE: no fatal failure was added by the forgery",
          [n for n in failing(before) if n not in STAMP_CHECKS],
          [n for n in failing(after) if n not in STAMP_CHECKS])


def s_a_lone_machine_has_nobody_to_agree_with(tmp):
    """A one-machine fleet: the label check has literally nothing to compare.

    SINGLE, and the reason the old design could never be repaired by comparing
    machines to each other — with one machine there is no other side.
    """
    r = run_three(tmp, [ALPHA + (forged(),)])
    after, aout = r["after"]
    check("a lone forged machine is still named", tag_of(after, C_REPRO),
          "FAIL", detail_for(aout, C_REPRO)[:200])
    check("the label check has nothing to say about a fleet of one",
          tag_of(after, C_SAME), "PASS",
          "one machine always agrees with itself")


def s_commit_nobody_has(tmp):
    """A 40-hex commit this repository does not hold."""
    fleet = [ALPHA + (honest(),), BETA + (honest(NEVER_FETCHED),)]
    r = run_three(tmp, fleet)
    after, aout = r["after"]
    check("a commit nobody has is named", tag_of(after, C_EXISTS), "FAIL",
          detail_for(aout, C_EXISTS)[:200])
    check("and it is not reported as a forgery", tag_of(after, C_REPRO),
          "PASS", "unresolvable here is a different fact from disproved")


def s_commit_that_holds_no_scanner(tmp):
    """A commit that exists and carries neither scanner file.

    sha256 of nothing is a real, constant, guessable string. A verifier that
    hashed an empty blob list would certify `e3b0c442...` against any commit
    predating the scanner.
    """
    fleet = [ALPHA + (honest(),), BETA + (honest(OTHER_COMMIT),)]
    blobs = default_blobs(tmp)
    blobs[OTHER_COMMIT] = {}
    r = run_three(tmp, fleet, blobs)
    after, aout = r["after"]
    check("a commit holding no scanner cannot have produced a scan",
          tag_of(after, C_REPRO), "FAIL", detail_for(aout, C_REPRO)[:200])
    line = detail_for(aout, C_REPRO)
    # Non-emptiness asserted in the same comparison: `the string is absent` is
    # trivially true of a line that was never printed.
    check("the empty digest is not what it was compared against",
          ("e3b0c442" in line, bool(line)), (False, True),
          "sha256 of no bytes must never appear as an expected value, and this "
          f"is the line it would appear in: {line[:200]}")


def s_only_the_displayed_field_was_edited(tmp):
    """The full digest is right; the 12 characters people read are not."""
    ident = honest()
    ident["scanner_version"] = FORGED_SHORT
    fleet = [ALPHA + (ident,), BETA + (honest(),)]
    r = run_three(tmp, fleet)
    after, aout = r["after"]
    check("a doctored display field is named", tag_of(after, C_REPRO), "FAIL",
          detail_for(aout, C_REPRO)[:200])


def s_dirty_is_uncertifiable_not_accused(tmp):
    """A scan over uncommitted edits: named, never verified, never accused."""
    fleet = [ALPHA + (forged(scan_commit_dirty=True),), BETA + (honest(),)]
    r = run_three(tmp, fleet)
    after, aout = r["after"]
    check("a dirty scan is reported", tag_of(after, C_DIRTY), "WARN",
          detail_for(aout, C_DIRTY)[:200])
    check("a dirty scan is not called a forgery", tag_of(after, C_REPRO),
          "PASS", "the commit does not describe the code that ran")
    check("a dirty scan is not counted as verified",
          scan_identity.verify(REAL, {"scan_commit": scan_identity.head_commit(REAL),
                                      "scan_commit_dirty": True,
                                      "scanner_version": FORGED_SHORT}).status,
          scan_identity.DIRTY)


def s_todays_fleet_records_no_commit(tmp):
    """Every machine in this tree, today: a stamp and no commit anywhere.

    This must WARN and must not fail. Turning five folders red for a recorder
    that is not wired in yet is how a gate becomes something people pass with
    --force.
    """
    fleet = [ALPHA + (legacy(),), BETA + (legacy(),)]
    r = run_three(tmp, fleet)
    after, aout = r["after"]
    check("an unverifiable fleet is named", tag_of(after, C_CHECKED), "WARN",
          detail_for(aout, C_CHECKED)[:200])
    check("...and is not silently passed", tag_of(after, C_CHECKED) == "PASS",
          False, "nothing was compared to anything; PASS would be a lie")
    check("...and does not turn the gate red",
          [n for n in failing(after) if n in STAMP_CHECKS], [])


def s_the_ratchet(tmp):
    """Once one machine records a commit, a machine without one is a failure.

    The cheapest attack on this whole section is to stop recording the field and
    be unverifiable instead of caught. It works exactly once — on a fleet where
    nobody records it.
    """
    fleet = [ALPHA + (honest(),), BETA + (legacy(),)]
    r = run_three(tmp, fleet)
    after, aout = r["after"]
    line = detail_for(aout, C_CHECKED)
    check("dropping the commit while the fleet records it is fatal",
          tag_of(after, C_CHECKED), "FAIL", line[:200])
    check("the machine that dropped it is the one named", "beta" in line, True,
          line[:200])
    check("the machine that kept it is not named", "alpha" in line, False,
          line[:200])


FAILING_GIT = "#!/usr/bin/env python3\nimport sys\nsys.exit(128)\n"


def s_git_cannot_be_asked(tmp):
    """ABSENT: git answers nothing — an export without .git, a tarball, a copy.

    Nothing can be verified, so nothing may be certified. The failure mode this
    guards is the one this repository has shipped seven times: a check that
    surveyed nothing printing what a check that surveyed everything prints.

    The stub is REPLACED rather than deleted because check_consistency.py calls
    `subprocess.run(["git", ...])` unguarded in four places, so a PATH with no
    git at all kills the gate with FileNotFoundError before it prints a line —
    reported as a finding, not repaired here, because it is not this fix. `git`
    present and refusing to answer is the same input for everything below and is
    the shape a real export actually has: the binary is installed, the directory
    is not a repository, and every call exits 128.
    """
    sub = tmp / "blind"
    sub.mkdir()
    root, env = build(sub, [ALPHA + (honest(),), BETA + (honest(),)])
    os.remove(sub / "bin" / "git")
    (sub / "bin" / "git").write_text(FAILING_GIT, encoding="utf-8")
    (sub / "bin" / "git").chmod(0o755)
    tags, out = gate(root, env)
    if tags is None:
        raise RuntimeError(f"the gate never reached its summary:\n{out[-1200:]}")
    check("with no git, no stamp is reported as checked",
          tag_of(tags, C_CHECKED), "WARN", detail_for(out, C_CHECKED)[:200])
    check("with no git, nothing is accused of forgery",
          tag_of(tags, C_REPRO), "PASS")
    check("the gate says its git-backed checks were blind",
          tag_of(tags, "the last commit can be read"), "FAIL",
          "the existing check that this run had no evidence")


def s_deleting_the_verifier_is_not_a_pass(tmp):
    """Delete scan_identity.py. Two checks must go red, not none."""
    sub = tmp / "gone"
    sub.mkdir()
    root, env = build(sub, [ALPHA + (forged(),), BETA + (forged(),)])
    os.remove(root / "scan_identity.py")
    tags, out = gate(root, env)
    if tags is None:
        raise RuntimeError(f"the gate never reached its summary:\n{out[-1200:]}")
    check("a missing verifier is named", tag_of(tags, C_PRESENT), "FAIL",
          detail_for(out, C_PRESENT)[:200])
    check("and the population check goes red with it",
          tag_of(tags, C_ADJUDICATED), "FAIL",
          "0 folders adjudicated against 2 in the tree — deleting the feature "
          "must not read as a fleet with no forgeries")
    check("the forgery checks do not report a clean fleet on their own",
          tag_of(tags, C_REPRO), "PASS",
          "they pass over an empty population, which is exactly why the two "
          "checks above exist")


def s_a_crash_is_not_coverage(tmp):
    """The verifier raises on one folder. The count must catch it.

    adv_documents.py died at KeyError 'inputs' this morning and 11 later checks
    never ran, under a banner that counted the ones before it.
    """
    sub = tmp / "crash"
    sub.mkdir()
    root, env = build(sub, [ALPHA + (honest(),), BETA + (forged(),)])
    p = root / "scan_identity.py"
    src = p.read_text(encoding="utf-8")
    anchor = "    folder = folder or (doc.get(\"machine\")"
    if anchor not in src:
        raise RuntimeError("ANCHOR MISSING in scan_identity.verify")
    p.write_text(src.replace(
        anchor,
        "    if (folder or '') == 'beta':\n"
        "        raise KeyError('inputs')\n" + anchor, 1), encoding="utf-8")
    tags, out = gate(root, env)
    if tags is None:
        raise RuntimeError(f"the gate never reached its summary:\n{out[-1200:]}")
    check("a folder the verifier could not adjudicate is named",
          tag_of(tags, C_ADJUDICATED), "FAIL", detail_for(out, C_ADJUDICATED)[:200])
    check("the forgery check reports clean over the folders that survived",
          tag_of(tags, C_REPRO), "PASS",
          "beta was forged and never reached — which is why the count above is "
          "the check that matters")


SCENARIOS = [
    (s_unit_against_real_git, 10),
    (s_control_two_honest_machines, 3),
    (s_red_team_two_machines_one_forged_stamp, 6),
    (s_one_machine_forged_one_honest, 4),
    (s_a_lone_machine_has_nobody_to_agree_with, 2),
    (s_commit_nobody_has, 2),
    (s_commit_that_holds_no_scanner, 2),
    (s_only_the_displayed_field_was_edited, 1),
    (s_dirty_is_uncertifiable_not_accused, 3),
    (s_todays_fleet_records_no_commit, 3),
    (s_the_ratchet, 3),
    (s_git_cannot_be_asked, 3),
    (s_deleting_the_verifier_is_not_a_pass, 3),
    (s_a_crash_is_not_coverage, 2),
]
EXPECTED_CHECKS = sum(n for _, n in SCENARIOS)


def main():
    for fn, want in SCENARIOS:
        before = len(PASS) + len(FAIL)
        try:
            with tempfile.TemporaryDirectory(prefix="advstamp-") as d:
                fn(pathlib.Path(d))
        except Exception as e:                                  # noqa: BLE001
            ERROR.append((fn.__name__, f"{type(e).__name__}: {e}"))
        got = len(PASS) + len(FAIL) - before
        if got != want:
            # A SCENARIO THAT STOPPED EARLY HAS NOT PASSED THE CHECKS IT NEVER
            # REACHED. Counted as a failure by name, so a crash halfway through
            # can never be read off the banner as coverage.
            FAIL.append((f"{fn.__name__} ran all its checks", got, want,
                         "it recorded fewer checks than it declares"))
    for name, _got, _want, _why in PASS:
        print(f"  PASS  {name}")
    for name, got, want, why in FAIL:
        print(f"  FAIL  {name}\n        got {got!r}, want {want!r}"
              + (f"\n        {why}" if why else ""))
    for name, why in ERROR:
        print(f"  ERROR {name}\n        {why}")
    total = len(PASS) + len(FAIL)
    print(f"\n{total} checks, {len(FAIL)} failed, {len(ERROR)} could not run")
    if total != EXPECTED_CHECKS:
        print(f"  and the suite recorded {total} of the {EXPECTED_CHECKS} "
              "checks it declares — the ones it did not reach have not passed")
    return 1 if FAIL or ERROR or total != EXPECTED_CHECKS else 0


if __name__ == "__main__":
    sys.exit(main())
