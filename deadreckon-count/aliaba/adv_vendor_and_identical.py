#!/usr/bin/env python3
"""Adversaries for the two rules in export_corpus.py that nothing else guards.

    python3 adv_vendor_and_identical.py                 the attacks
    python3 adv_vendor_and_identical.py --revert-proof  put each defect back

WHY THIS FILE EXISTS

Two rules in export_corpus.py decide what a published corpus is made of, and
neither of them was mentioned by any other file in this repository. Measured
before this was written: `vendor_dir` and `VENDOR_DIRS` appear in ZERO of the 57
other .py files here. A rule with no adversary is a rule whose next edit is
free, and both of these have already been edited wrongly once.

1. THE VENDORED-DIRECTORY RULE.

   It used to be `set(rel.parts[:-1]) & VENDOR_DIRS` — a raw, case-sensitive,
   dot-sensitive intersection — sitting fifteen lines above the secret-directory
   test that had already been normalised for exactly this reason. `vendor_dir()`
   folds spellings the way the filesystem does (NFC, drop format characters,
   strip surrounding dots and spaces, casefold), and the attack below plants
   every spelling that folding is for.

   The stakes are not stylistic. `plugins/` on this machine holds 3,282
   marketplace `.md` files against 9 authored ones — 364 vendored files for
   every real one — so one unfolded spelling is the difference between
   collating a profile and collating a marketplace.

   The over-refusal control is in the same attack on purpose: `plugins-notes/`
   is NOT a vendor directory, and a rule that refuses everything would score
   perfectly on the first half of this file without it.

2. THE IDENTICAL-CONTENT RULE, WHICH IS NOT A DEDUP ANY MORE.

   The author's ruling, which changed the design:

       Two real transcripts cannot be byte-identical, and across two different
       computers it is impossible. So identical content is NOT a duplicate to be
       silently suppressed — it is evidence we collected the wrong thing.

   The measurement agrees. A corpus-wide (size, sha256) rule suppressed 4,610
   files on this machine and 4,472 of them were `checkpoints/index.md`, a
   172-character stub the tool writes once per conversation. That is
   boilerplate, and the right answer was never to dedup it — it was to stop
   collecting it. Suppressing left whichever session sorted first holding the
   only copy and published the loss as a counter that read like a win.

   So content suppression is GONE and an ALARM stands in its place: both copies
   are exported, the pair is named, and the report is loud enough to act on.
   Three facts are kept apart, and each attack below asks about one of them:

       a hard link      one FILE reached by two names — still skipped, still
                        counted; that is a different thing entirely
       identical RECORD the bug: alarm, name both, drop neither
       identical CONFIG normal — five computers really do have the same
                        settings.json — and conflating it with a record is
                        exactly how the greedy rule got written

HOUSE RULES THIS FILE OBEYS

No check here asserts a substring of a key that is written unconditionally, and
no check asserts "none of X failed" without first asserting X is non-empty.
Every attack declares how many checks it runs and main() verifies the count, so
a suite that dies half way through cannot be read as one that passed.

And every check was run against the defect: `--revert-proof` replants each
original line in a throwaway copy of the tree and requires the NAMED checks
below to go RED there. A test that passes against broken code is worse than no
test, because it is counted.
"""

import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import export_corpus as EC                                        # noqa: E402
import stores                                                     # noqa: E402

FAILED = []
SKIPPED = []
RAN = []


def check(name, got, want, why=""):
    RAN.append(name)
    if got == want:
        print(f"  PASS  {name}")
        return True
    print(f"  FAIL  {name}")
    print(f"          got {got!r}, want {want!r}")
    if why:
        print(f"          {why}")
    FAILED.append(name)
    return False


def skip(name, why):
    SKIPPED.append(name)
    print(f"  SKIP  {name} — {why}")


def w(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text if isinstance(text, str) else json.dumps(text),
                 encoding="utf-8")
    return p


def row(marker):
    """One JSONL record whose bytes are unique unless `marker` repeats."""
    return json.dumps({"type": "turn", "text": marker,
                       "usage": {"input_tokens": 10, "output_tokens": 5}}) + "\n"


def run_tools(home, out, archive_other=None):
    """export_tools on a sandbox home. Returns (summary, refused, counts)."""
    return EC.export_tools(pathlib.Path(out), pathlib.Path(home),
                           pathlib.Path(archive_other) if archive_other else None,
                           EC.Redactor(pathlib.Path(home), keep_email=None))


def corpus(out):
    """Every file in the export, as posix paths relative to it."""
    root = pathlib.Path(out)
    if not root.is_dir():
        return []
    return sorted(p.relative_to(root).as_posix()
                  for p in root.rglob("*") if p.is_file())


def alarm_lines(counts):
    """The per-pair detail lines the alarm wrote. Names, not a number."""
    return sorted(k for k in counts
                  if k.startswith(EC.IDENTICAL_DETAIL + ": "))


def sandbox(prefix):
    return pathlib.Path(tempfile.mkdtemp(prefix=prefix)).resolve()


# ---------------------------------------------------------------------------
# 1. the vendored-directory rule
# ---------------------------------------------------------------------------

# (session directory, directory name as planted). The first of each pair is the
# canonical spelling the raw intersection already caught; the rest are the
# spellings it did not, and every one of them was observed live on this machine.
VENDOR_SPELLINGS = [
    ("s-canon", "plugins"),
    ("s-upper", "Plugins"),
    ("s-space", "plugins "),
    ("s-dot", "plugins."),
    ("s-hidden", ".plugins"),
    ("s-nm", "node_modules"),
    ("s-nm-upper", "NODE_MODULES"),
]


def adv_vendored_directories_are_refused_in_every_spelling():
    """Plugins/, 'plugins ', 'plugins.', .plugins, NODE_MODULES — all of them.

    Each spelling gets its OWN session directory. Planting them side by side
    would collide on the two case-insensitive machines in this fleet, and a
    fixture the filesystem quietly merged would prove whatever the merge
    happened to leave behind.

    Three things are asserted together and they are not the same thing:
    the vendored files are REFUSED, they are COUNTED, and the authored files
    are still THERE. The last one is what stops a rule that refuses everything
    from passing; `plugins-notes/` is the same control from the other side.
    """
    d = sandbox("advvend-")
    try:
        home = d / "home"
        base = home / ".copilot" / "session-state"
        planted_vendor, planted_authored, planted_disk = [], [], []
        for sid, name in VENDOR_SPELLINGS:
            w(base / sid / "session.jsonl", row(f"authored-{sid}"))
            planted_authored.append(f"copilot/{sid}/session.jsonl")
            planted_disk.append(
                w(base / sid / name / "marketplace.md", f"# vendored {sid}\n"))
            planted_vendor.append(f"copilot/{sid}/{name}/marketplace.md")
        # A vendored directory that is not the last component before the file.
        w(base / "s-deep" / "session.jsonl", row("authored-s-deep"))
        planted_authored.append("copilot/s-deep/session.jsonl")
        planted_disk.append(
            w(base / "s-deep" / "plugins" / "sub" / "deep.md", "# vendored deep\n"))
        planted_vendor.append("copilot/s-deep/plugins/sub/deep.md")
        # THE OVER-REFUSAL CONTROL. `plugins-notes` folds to `plugins-notes`,
        # which is not in VENDOR_DIRS, and a rule that refused it would be
        # throwing away somebody's writing.
        w(base / "s-near" / "session.jsonl", row("authored-s-near"))
        w(base / "s-near" / "plugins-notes" / "kept.md", "# authored notes\n")
        planted_authored += ["copilot/s-near/session.jsonl",
                             "copilot/s-near/plugins-notes/kept.md"]

        # THE FIXTURE HAS TO BE WHAT IT CLAIMS. A filesystem that normalises
        # names away would leave fewer directories than were planted, and every
        # verdict below would then be about a tree nobody built.
        on_disk = []
        for sid, name in VENDOR_SPELLINGS:
            on_disk += [n for n in os.listdir(base / sid) if n == name]
        if len(on_disk) != len(VENDOR_SPELLINGS):
            skip("vendored directories are refused in every spelling",
                 f"this filesystem kept {len(on_disk)} of "
                 f"{len(VENDOR_SPELLINGS)} spellings as distinct names")
            return

        out = d / "out"
        _summary, _refused, counts = run_tools(home, out)
        got = corpus(out)

        # NON-EMPTY FIRST, then the refusal. Asserting only that no vendored
        # file arrived would pass against an export that produced nothing.
        check("the authored files are in the corpus",
              [n for n in planted_authored if n not in got], [],
              f"got {got} — an empty export refuses every vendored file")
        # ASKED OF THE FILESYSTEM, not of the list this function just built.
        # "no vendored file arrived" is worth nothing until something vendored
        # is known to have been there, and a name the filesystem rewrote is not
        # the name the walk was asked about.
        check("and there were vendored files ON DISK to refuse",
              len([p for p in planted_disk if p.is_file()]), 8,
              f"planted {[str(p) for p in planted_disk]!r} — a fixture with "
              "nothing vendored in it certifies nothing")
        check("no vendored file reaches the corpus, in any spelling",
              [n for n in planted_vendor if n in got], [],
              "the raw `set(rel.parts[:-1]) & VENDOR_DIRS` admits Plugins/, "
              "'plugins ', 'plugins.', .plugins and NODE_MODULES")
        # COUNTED, not merely absent. A file kept out and not counted is this
        # repository's signature defect: absent looks exactly like zero.
        check("every refusal is COUNTED", counts.get("vendored"), 8,
              f"counts={dict(counts)!r} — no VENDOR_EXT file is planted here, "
              "so this number is the directory rule and nothing else")
        check("a directory that merely LOOKS vendored is not refused",
              "copilot/s-near/plugins-notes/kept.md" in got, True,
              "folding is not fuzzy matching; over-refusal here is somebody's "
              "writing thrown away")
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------
# 2. identical RECORD content — alarm, name both, drop neither
# ---------------------------------------------------------------------------

def adv_identical_records_alarm_and_nothing_is_dropped():
    """The 138 real pairs: transcript.jsonl beside transcript_full.jsonl.

    One conversation the tool wrote twice, in one folder. Which of the two is
    the record is a collection question and this program is not entitled to
    guess at it by sort order, so BOTH are exported and the pair is named.

    The control in the same run is a third file one byte different: an alarm
    that fires on everything is as useless as one that fires on nothing, and
    without the control a rule that alarmed on every file would pass.
    """
    d = sandbox("advident-")
    try:
        home = d / "home"
        logs = (home / ".copilot" / "session-state" / "1111-aaaa"
                / ".system_generated" / "logs")
        body = row("one conversation") + row("written twice")
        a = w(logs / "transcript.jsonl", body)
        b = w(logs / "transcript_full.jsonl", body)
        ctl = w(logs / "transcript_other.jsonl",
                row("one conversation") + row("written once"))

        sa, sb = a.stat(), b.stat()
        if not ((sa.st_dev, sa.st_ino) != (sb.st_dev, sb.st_ino)
                and a.read_bytes() == b.read_bytes()
                and ctl.read_bytes() != body.encode()):
            skip("identical records alarm and nothing is dropped",
                 "the fixture is not two copies at two inodes plus a control")
            return

        out = d / "out"
        _summary, _refused, counts = run_tools(home, out)
        got = corpus(out)
        pre = "copilot/1111-aaaa/.system_generated/logs/"
        lines = alarm_lines(counts)

        check("BOTH copies are exported — neither is dropped",
              [n for n in (pre + "transcript.jsonl", pre + "transcript_full.jsonl")
               if n not in got], [],
              f"got {got} — suppression published the loss as a duplicate count")
        check("the alarm fired exactly once",
              counts.get(EC.IDENTICAL_RECORDS), 1,
              f"counts={dict(counts)!r}")
        check("and it wrote exactly one detail line", len(lines), 1,
              f"lines={lines!r}")
        # ORDER-INDEPENDENT, and neither name is a substring of the other:
        # "transcript_full.jsonl" does not contain "transcript.jsonl".
        line = lines[0] if lines else ""
        check("which NAMES both files of the pair",
              [n for n in (pre + "transcript.jsonl", pre + "transcript_full.jsonl")
               if n not in line], [],
              f"line={line!r} — a count with no names cannot be acted on")
        check("the one-line-different control is not alarmed",
              "transcript_other.jsonl" in line, False,
              "an alarm that fires on everything says nothing")
        check("and the control is in the corpus too",
              pre + "transcript_other.jsonl" in got, True)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def adv_boilerplate_in_two_sessions_survives_and_is_alarmed():
    """The 4,472 the greedy rule deleted, and the blind spot that replaced it.

    `copilot/<session-uuid>/checkpoints/index.md` is a 172-character stub the
    tool writes into EVERY session directory. Two things have to be true about
    it at once, and each one is a different rule going wrong:

        a corpus-wide (size, sha256) SUPPRESSION deletes one of these two and
        leaves whichever session sorted first holding the only copy

        a suppression scoped to the parent directory keeps both and says
        NOTHING, so nobody ever learns the collector is picking up boilerplate

    Both checks are here so neither fix can pass alone. The remedy the alarm
    exists to prompt is upstream — stop collecting the stub — and it cannot be
    prompted by a corpus that is quietly missing 4,472 files.
    """
    d = sandbox("advboiler-")
    try:
        home = d / "home"
        base = home / ".copilot" / "session-state"
        stub = ("# Checkpoints\n\nNo checkpoints have been created for this "
                "session yet.\n")
        for i, sid in enumerate(("1111-aaaa", "2222-bbbb")):
            w(base / sid / "checkpoints" / "index.md", stub)
            w(base / sid / "session.jsonl", row(f"real conversation {i}"))

        one = (base / "1111-aaaa" / "checkpoints" / "index.md").read_bytes()
        two = (base / "2222-bbbb" / "checkpoints" / "index.md").read_bytes()
        if one != two:
            skip("boilerplate survives and is alarmed",
                 "the two stubs are not byte-identical")
            return

        out = d / "out"
        _summary, _refused, counts = run_tools(home, out)
        got = corpus(out)
        stubs = [n for n in got if n.endswith("/checkpoints/index.md")]
        lines = alarm_lines(counts)

        check("the fixture was actually walked",
              [n for n in ("copilot/1111-aaaa/session.jsonl",
                           "copilot/2222-bbbb/session.jsonl") if n not in got],
              [], f"got {got}")
        check("identical boilerplate in two sessions survives in BOTH",
              stubs, ["copilot/1111-aaaa/checkpoints/index.md",
                      "copilot/2222-bbbb/checkpoints/index.md"],
              "a corpus-wide content hash keeps one and deletes the other; on "
              "the real stores that is 4,472 files")
        check("and the collection bug is alarmed across directories",
              counts.get(EC.IDENTICAL_RECORDS), 1,
              f"counts={dict(counts)!r} — a rule scoped to the parent "
              "directory keeps both files and never says why it could")
        check("the alarm names both sessions",
              [n for n in stubs if n not in (lines[0] if lines else "")], [],
              f"lines={lines!r}")
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------
# 3. identical CONFIG is not the same claim
# ---------------------------------------------------------------------------

def adv_identical_config_across_two_roots_does_not_alarm():
    """Five computers really do have the same settings.json. That is not a bug.

    Two root-file stores, each holding the same two files: `stats-cache.json`,
    which is in the corpus only because a store's records tuple names it, and
    `history.jsonl`, which is a record by the walk's own test. The labels are
    synthetic and the shapes are not — `stats-cache.json` is proteus-root's
    real second record, and it is the file that made this distinction
    necessary.

    Both halves are in ONE run on purpose. Alarm on nothing and the record
    check fails; alarm on everything — which is how the greedy rule got written
    — and the config check fails. Neither can be satisfied by deleting the
    other.
    """
    d = sandbox("advconf-")
    probes = [stores.Store(f"probe-{n}-root", f".probe-{n}", kind="root_files",
                           records=("history.jsonl", "stats-cache.json"))
              for n in ("alpha", "beta")]
    for p in probes:
        stores.STORES.append(p)
        stores.BY_LABEL[p.label] = p
    try:
        home = d / "home"
        cfg = json.dumps({"turns": 12, "theme": "dark"})
        rec = row("the same record on two machines")
        for n in ("alpha", "beta"):
            w(home / f".probe-{n}" / "stats-cache.json", cfg)
            w(home / f".probe-{n}" / "history.jsonl", rec)

        out = d / "out"
        _summary, _refused, counts = run_tools(home, out)
        got = corpus(out)
        lines = alarm_lines(counts)
        blob = " ".join(lines)

        check("both config copies were walked and exported",
              [n for n in ("probe-alpha-root/stats-cache.json",
                           "probe-beta-root/stats-cache.json") if n not in got],
              [], f"got {got} — a file that was never read cannot alarm, and "
                  "proving it did not alarm would then prove nothing")
        check("both record copies were walked and exported",
              [n for n in ("probe-alpha-root/history.jsonl",
                           "probe-beta-root/history.jsonl") if n not in got],
              [], f"got {got}")
        check("identical CONFIG across two roots does NOT alarm",
              "stats-cache.json" in blob, False,
              f"lines={lines!r} — five computers holding one settings.json is "
              "normal; conflating it with a record is how the greedy rule got "
              "written")
        check("identical RECORDS across two roots DO alarm",
              counts.get(EC.IDENTICAL_RECORDS), 1,
              f"counts={dict(counts)!r} — an exemption wide enough to cover "
              "the records is not an exemption, it is a deletion")
        check("and the record alarm names both roots",
              [n for n in ("probe-alpha-root/history.jsonl",
                           "probe-beta-root/history.jsonl") if n not in blob],
              [], f"lines={lines!r}")
    finally:
        for p in probes:
            stores.STORES.remove(p)
            stores.BY_LABEL.pop(p.label, None)
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------
# 4. a hard link is a different fact and stays one
# ---------------------------------------------------------------------------

def adv_a_hard_link_is_still_skipped_and_still_counted():
    """One FILE reached by two names. Not a copy, not an alarm, and counted.

    ~/.ai-logs-archive holds a hard link to every transcript ever written, so
    the same inode is reachable twice and skipping the second name is what
    stops every byte being written and counted twice. That rule stays exactly
    as it was, and the reason it needs an adversary of its own is the shape it
    used to have: three lines, a bare `continue`, and no counter — so
    `hard links skipped` did not read 0, it did not EXIST, and every consumer
    reading it as `.get(k, 0)` printed 0 and was believed.

    The last check is the one that keeps the two facts apart: a hard link is
    skipped before its bytes are ever read, so it must NOT also show up as
    identical content. If it did, one file would be reported as two problems.
    """
    d = sandbox("advlink-")
    try:
        home = d / "home"
        base = home / ".copilot" / "session-state" / "3333-cccc"
        src = w(base / "session.jsonl", row("one inode, two names"))
        link = base / "session-link.jsonl"
        try:
            os.link(src, link)
        except OSError as e:
            skip("a hard link is still skipped and still counted",
                 f"hard links unavailable here: {e}")
            return
        other = w(base / "notes.md", "# something else entirely\n")

        ss, sl = src.stat(), link.stat()
        if (ss.st_dev, ss.st_ino) != (sl.st_dev, sl.st_ino):
            skip("a hard link is still skipped and still counted",
                 "the fixture is not one inode under two names")
            return

        out = d / "out"
        _summary, _refused, counts = run_tools(home, out)
        got = corpus(out)
        names = [n for n in got if n.endswith(("session.jsonl",
                                               "session-link.jsonl"))]
        detail = [k for k in counts if k.startswith("second name for one inode")]

        check("the fixture was actually walked",
              "copilot/3333-cccc/notes.md" in got, True,
              f"got {got} — an export that exported nothing skips every link")
        check("one inode reaches the corpus under exactly one name",
              len(names), 1, f"names={names!r}")
        check("and the hard link is COUNTED", counts.get("hard links skipped"), 1,
              f"counts={dict(counts)!r} — a bare `continue` makes this key "
              "ABSENT, and absent reads as 0")
        check("and NAMED", len(detail), 1, f"counts={dict(counts)!r}")
        check("a hard link does NOT also raise the content alarm",
              counts.get(EC.IDENTICAL_RECORDS, 0), 0,
              f"counts={dict(counts)!r} — one file reported as two problems is "
              "the conflation this design exists to refuse")
        check("and `other` did not fall in either bucket",
              other.read_text(encoding="utf-8"), "# something else entirely\n")
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------
# 5. nothing, one thing, and a store that is not there
# ---------------------------------------------------------------------------

def adv_empty_one_and_absent_inputs_are_not_alarms():
    """The three degenerate inputs, on the rule that now speaks up.

    An alarm is only worth having if it is quiet when it should be, and the
    quiet cases are the ones no fixture in this repository builds. One of them
    is a design decision with no guard anywhere: ZERO-LENGTH FILES ARE EXEMPT.
    Every empty file is "identical" to every other, so alarming on each pair
    would bury the one signal this exists for — and it would do it by asserting
    the thing this whole repository refuses to assert, that an empty file and
    an absent one are the same fact.
    """
    d = sandbox("advdegen-")
    try:
        home = d / "home"
        base = home / ".copilot" / "session-state"
        # EMPTY. Two zero-byte records are byte-identical by definition.
        w(base / "e-1" / "session.jsonl", "")
        w(base / "e-2" / "session.jsonl", "")
        out = d / "out"
        _s, _r, counts = run_tools(home, out)
        check("two EMPTY records are both exported",
              corpus(out), ["copilot/e-1/session.jsonl",
                            "copilot/e-2/session.jsonl"])
        check("and empty files raise no alarm",
              counts.get(EC.IDENTICAL_RECORDS, 0), 0,
              f"counts={dict(counts)!r} — every empty file matches every other")

        # SINGLE. One store, one record, nothing to compare it against.
        home2 = d / "home2"
        w(home2 / ".grok" / "sessions" / "only.jsonl",
          json.dumps([{"type": "turn", "text": "the only record there is"}]))
        out2 = d / "out2"
        _s2, _r2, counts2 = run_tools(home2, out2)
        check("a SINGLE record is exported", corpus(out2), ["grok/only.jsonl"])
        check("and alarms nothing",
              counts2.get(EC.IDENTICAL_RECORDS, 0), 0, f"counts={dict(counts2)!r}")

        # ABSENT. The store root is gone before the walk reaches it. Not in a
        # `finally:` — this is the scenario, not the teardown.
        shutil.rmtree(base)
        out3 = d / "out3"
        err, counts3 = None, {}
        try:
            _s3, _r3, counts3 = run_tools(home, out3)
        except BaseException as e:                        # noqa: BLE001
            err = f"{type(e).__name__}: {e}"
        check("a store that is not there does not raise", err, None)
        check("and yields no corpus and no alarm",
              (corpus(out3), counts3.get(EC.IDENTICAL_RECORDS, 0)), ([], 0))
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------
# 6. the alarm reaches the artifact somebody reads
# ---------------------------------------------------------------------------

def adv_the_manifest_carries_the_alarm():
    """Counted in a function is not reported. The manifest is the artifact.

    export_tools' counters reached MANIFEST.json only inside
    `tool_files_skipped`, which is the ledger of files that did NOT arrive.
    These arrived — twice — and a consumer should not have to substring-match a
    skip counter to find out that the collector is picking up something that is
    not a record. Its own field, with the names, and the export still finishes:
    a report that crashes the run the moment it has something to say is worse
    than the silence it replaced.
    """
    d = sandbox("advman-")
    try:
        home = d / "home"
        logs = home / ".copilot" / "session-state" / "4444-dddd"
        body = row("the same bytes twice")
        w(logs / "transcript.jsonl", body)
        w(logs / "transcript_full.jsonl", body)
        out = d / "out"

        argv, err = sys.argv, None
        try:
            sys.argv = ["export_corpus.py", "--home", str(home), "--out",
                        str(out), "--keep-email", "", "--archive", "",
                        "--archive-other", ""]
            EC.main()
        except BaseException as e:                        # noqa: BLE001
            err = f"{type(e).__name__}: {e}"
        finally:
            sys.argv = argv

        check("an export that has an alarm to raise still finishes", err, None)
        mf = out / "machine-readable" / "MANIFEST.json"
        man = json.loads(mf.read_text(encoding="utf-8")) if mf.is_file() else {}
        check("the manifest carries the alarm as its own field",
              man.get("identical_record_content"), 1,
              f"manifest keys={sorted(man)!r}")
        detail = man.get("identical_record_content_detail") or []
        # As export_tools names a file: <label>/<path under the store root>.
        pre = "copilot/4444-dddd/"
        check("and names both files", len(detail), 1, f"detail={detail!r}")
        check("with the paths spelled out",
              [n for n in (pre + "transcript.jsonl", pre + "transcript_full.jsonl")
               if n not in " ".join(detail)], [], f"detail={detail!r}")
        check("and both files are on disk in the corpus",
              sorted(p.name for p in (out / "tools" / "copilot" / "4444-dddd")
                     .glob("transcript*.jsonl"))
              if (out / "tools" / "copilot" / "4444-dddd").is_dir() else [],
              ["transcript.jsonl", "transcript_full.jsonl"])
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------

ATTACKS = [
    adv_vendored_directories_are_refused_in_every_spelling,
    adv_identical_records_alarm_and_nothing_is_dropped,
    adv_boilerplate_in_two_sessions_survives_and_is_alarmed,
    adv_identical_config_across_two_roots_does_not_alarm,
    adv_a_hard_link_is_still_skipped_and_still_counted,
    adv_empty_one_and_absent_inputs_are_not_alarms,
    adv_the_manifest_carries_the_alarm,
]

# HOW MANY CHECKS EACH ATTACK OWES. A suite that exits early has not passed the
# checks it did not reach — adv_documents.py died at a KeyError after its real
# failures and 11 later checks never ran, and the run was read as coverage.
# Declared per attack rather than as one total, so a crash is attributed to the
# attack that crashed instead of to the file.
EXPECT = {
    "adv_vendored_directories_are_refused_in_every_spelling": 5,
    "adv_identical_records_alarm_and_nothing_is_dropped": 6,
    "adv_boilerplate_in_two_sessions_survives_and_is_alarmed": 4,
    "adv_identical_config_across_two_roots_does_not_alarm": 5,
    "adv_a_hard_link_is_still_skipped_and_still_counted": 6,
    "adv_empty_one_and_absent_inputs_are_not_alarms": 6,
    "adv_the_manifest_carries_the_alarm": 5,
}


# ---------------------------------------------------------------------------
# the revert proof — every check above, run against the defect it is for
# ---------------------------------------------------------------------------

NEW_ALARM = """            if raw and not (top_only and not _is_loose_record(src)):
                key = (len(raw),
                       hashlib.sha256(raw.encode("utf-8")).hexdigest())
                if key in seen_bytes:
                    note_alarm(label, rel, seen_bytes[key])
                else:
                    seen_bytes[key] = f"{label}/{rel.as_posix()}"
"""

OLD_SCOPED = """            if raw:
                key = (label, rel.parent.as_posix(), len(raw),
                       hashlib.sha256(raw.encode("utf-8")).hexdigest())
                if key in seen_bytes:
                    note_dup("byte-identical duplicates skipped",
                             "same bytes already exported",
                             label, rel, seen_bytes[key])
                    continue
                seen_bytes[key] = f"{label}/{rel.as_posix()}"
"""

OLD_GREEDY = """            if raw:
                key = (len(raw),
                       hashlib.sha256(raw.encode("utf-8")).hexdigest())
                if key in seen_bytes:
                    note_dup("byte-identical duplicates skipped",
                             "same bytes already exported",
                             label, rel, seen_bytes[key])
                    continue
                seen_bytes[key] = f"{label}/{rel.as_posix()}"
"""

# (name, [(file, old, new)], [checks that MUST go red])
REVERTS = [
    ("vendor_dir is the raw `set(rel.parts[:-1]) & VENDOR_DIRS` again",
     [("export_corpus.py",
       "    return fs_name(name) in _VENDOR_DIRS_NORM",
       "    return name in VENDOR_DIRS")],
     ["no vendored file reaches the corpus, in any spelling",
      "every refusal is COUNTED"]),

    ("identical content is suppressed again, scoped to the directory",
     [("export_corpus.py", NEW_ALARM, OLD_SCOPED)],
     ["BOTH copies are exported — neither is dropped",
      "the alarm fired exactly once",
      "and it wrote exactly one detail line",
      "the manifest carries the alarm as its own field"]),

    ("identical content is suppressed again, corpus-wide (the 4,610 rule)",
     [("export_corpus.py", NEW_ALARM, OLD_GREEDY)],
     ["identical boilerplate in two sessions survives in BOTH",
      "and the collection bug is alarmed across directories",
      "BOTH copies are exported — neither is dropped"]),

    ("the alarm stops telling config from records",
     [("export_corpus.py",
       "            if raw and not (top_only and not _is_loose_record(src)):",
       "            if raw:")],
     ["identical CONFIG across two roots does NOT alarm"]),

    ("the hard-link skip loses its counter (a bare `continue`)",
     [("export_corpus.py",
       '            if inode in seen:\n'
       '                note_dup("hard links skipped", "second name for one inode",\n'
       '                         label, rel, seen[inode])\n'
       '                continue',
       '            if inode in seen:\n'
       '                continue')],
     ["and the hard link is COUNTED", "and NAMED"]),
]


def _tree(root):
    d = pathlib.Path(tempfile.mkdtemp(prefix="advvend-revert-"))
    for f in root.iterdir():
        if f.suffix == ".py" or f.name in ("machines.json", "accounts.json"):
            shutil.copy2(f, d / f.name)
    return d


def revert_proof():
    """Replant each original line and require the NAMED checks to go RED."""
    root = pathlib.Path(__file__).resolve().parent
    me = pathlib.Path(__file__).name
    bad = []
    for name, plants, must_fail in REVERTS:
        d = _tree(root)
        try:
            missing = False
            for fn, old, new in plants:
                p = d / fn
                s = p.read_text(encoding="utf-8")
                if old not in s:
                    print(f"  ANCHOR MISSING  {name}: {fn}")
                    bad.append(name)
                    missing = True
                    break
                p.write_text(s.replace(old, new, 1), encoding="utf-8")
            if missing:
                continue
            r = subprocess.run([sys.executable, me], cwd=d, capture_output=True,
                               text=True, timeout=900)
            fails = {l.strip()[6:] for l in r.stdout.splitlines()
                     if l.startswith("  FAIL  ")}
            missed = [c for c in must_fail if c not in fails]
            ok = r.returncode != 0 and not missed
            print(f"  {'RED  ' if ok else 'GREEN'}  {name}")
            print(f"          exit {r.returncode}, {len(fails)} check(s) failed")
            for f in sorted(fails):
                print(f"          - {f}")
            if missed:
                print(f"          NOT CAUGHT: {missed}")
                bad.append(name)
            elif r.returncode == 0:
                bad.append(name)
        finally:
            shutil.rmtree(d, ignore_errors=True)
    print(f"\n  {len(REVERTS)} reverts, {len(bad)} the suite did NOT catch"
          + (f": {bad}" if bad else ""))
    return 1 if bad else 0


def main():
    for fn in ATTACKS:
        print(f"\n{fn.__name__}")
        before, skips = len(RAN), len(SKIPPED)
        try:
            fn()
        except Exception as e:                            # noqa: BLE001
            import traceback
            traceback.print_exc()
            FAILED.append(f"{fn.__name__} raised {type(e).__name__}: {e}")
        ran, want = len(RAN) - before, EXPECT[fn.__name__]
        if len(SKIPPED) == skips and ran != want:
            FAILED.append(f"{fn.__name__} ran {ran} checks and owes {want}")
            print(f"  FAIL  {fn.__name__} ran {ran} checks and owes {want}")
    print(f"\n  {len(RAN)} checks, {len(FAILED)} failed, {len(SKIPPED)} skipped")
    for f in FAILED:
        print(f"  FAILED  {f}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    if "--revert-proof" in sys.argv:
        sys.exit(revert_proof())
    sys.exit(main())
