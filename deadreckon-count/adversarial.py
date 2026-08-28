"""Harder attacks. The first round was too easy — 4 of 4 caught.

Round one broke arithmetic: doubled everything, moved tokens between accounts,
deleted a session, bent a bucket. All caught, because the checks are partition
checks and those attacks all broke a partition.

So round two attacks the SHAPE of the checks instead of the numbers:

  - corruptions that keep every sum intact
  - corruptions in files no check reads
  - corruptions that make the checker's own inputs disappear

A check that cannot see a file cannot fail on it, and "not checked" prints
identically to "fine". That is the failure mode this repository keeps finding,
so it is the one worth attacking on purpose.

Every attack runs on a COPY, with git history, since the drop check needs it.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

# Derived from __file__ so the harness works regardless of where the repo
# was cloned. The old hardcoded "~/deadreckon-count" silently broke every
# attack the moment the repo moved — git clone failed against a path that
# did not exist and every attack scored nothing while printing a summary.
SRC = os.path.dirname(os.path.realpath(__file__))


def machines(d):
    """Machines the CLONE actually has. Never a hardcoded list.

    It was a hardcoded list of five, and a retire moved four of them out — so
    every attack crashed on a path that no longer existed and the suite scored
    nothing at all. A harness that cannot survive its own repository being
    maintained is a harness that gets skipped.
    """
    out = []
    for name in sorted(os.listdir(d)):
        if os.path.isfile(os.path.join(d, name, "machine-readable", "totals.json")):
            out.append(name)
    return out


def fresh():
    d = tempfile.mkdtemp(prefix="adv2-")
    r = subprocess.run(["git", "clone", "-q", "--local", SRC, d + "/repo"],
                       capture_output=True, text=True, timeout=600)
    if r.returncode:
        raise SystemExit(f"clone failed: {r.stderr[-300:]}")
    repo = d + "/repo"
    # The clone carries the COMMITTED checks. Write a new check, run this, and
    # it reports on the old one — a harness that silently grades last week's
    # code. Overlay the working tree so an attack is judged by the checks that
    # are actually on disk. The clone is still what supplies git history, which
    # the drop and closed-day checks compare against.
    for f in os.listdir(SRC):
        if f.endswith(".py"):
            shutil.copy2(os.path.join(SRC, f), os.path.join(repo, f))
    return repo


def run_checks(d):
    """(failures, warnings, output) — counting the EXIT STATUS as a failure.

    This grep-graded the output and threw `returncode` away, which is the one
    signal check_consistency.py actually gates on. Reproduced with a checker
    that exits 3 and prints no "FAIL":

        check_consistency really exited: 3
        what run_checks() reports    : (0, 0)

    Zero failures at BASELINE, before any attack is planted — so every attack
    below is then measured against a baseline of nothing, scores "skipped" or
    "*** SURVIVED ***", and the table update.py publishes says the fleet is
    clean. A traceback, an import error, or a SystemExit anywhere in the gate
    all land here, and none of them contain the word FAIL.

    Counted as one failure rather than added to the grep, because a run that
    died has an unknown number of them and reporting 0 is the bug.
    """
    r = subprocess.run([sys.executable, "check_consistency.py"], cwd=d,
                       capture_output=True, text=True, timeout=900)
    out = r.stdout + r.stderr
    failures = out.count("FAIL")
    if r.returncode and not failures:
        out += (f"\n  [adversarial.py] check_consistency exited "
                f"{r.returncode} without printing FAIL — counted as a failure\n")
        failures = 1
    return failures, out.count("WARN"), out


def load(d, m, name):
    p = os.path.join(d, m, "machine-readable", name)
    return json.load(open(p)), p


def save(doc, p):
    json.dump(doc, open(p, "w"), indent=1)


# ---- attacks that keep every sum intact ------------------------------------

def a_swap_model_labels(d):
    """Reattribute tokens from one MODEL to another. Every total unchanged.

    Turns Anthropic usage into DeepSeek usage, or the reverse. The per-company
    split is the number this repository is most careful about, and no partition
    check can see it: the machine still sums, the account still sums, the
    buckets still sum.
    """
    # CROSS-COMPANY. The first version relabelled claude-opus-4-8 as
    # claude-opus-5 — both map to `anthropic`, so the per-company split never
    # moved and the check correctly stayed silent. That made the attack weaker
    # than the threat it was meant to model. The figure worth protecting is
    # WHICH COMPANY served the tokens, so the relabel has to cross that line.
    doc, p = load(d, machines(d)[0], "totals.json")
    for a in doc.get("accounts", []):
        bm = a.get("by_model") or {}
        keys = [k for k in bm if "claude" in k.lower()]
        if keys:
            src = bm[keys[0]]
            dst = bm.setdefault("deepseek-v4-pro", {k: 0 for k in src} if isinstance(src, dict) else 0)
            if isinstance(src, dict) and isinstance(dst, dict):
                for k, v in src.items():
                    if isinstance(v, int):
                        dst[k] = (dst.get(k, 0) or 0) + v
                        src[k] = 0
                save(doc, p)
                return f"all {keys[0][:24]} tokens relabelled as deepseek-v4-pro"
        keys = list(bm)
        if len(keys) >= 2:
            src, dst = bm[keys[0]], bm.get(keys[1])
            if isinstance(src, dict) and isinstance(dst, dict):
                for k, v in src.items():
                    if isinstance(v, int):
                        dst[k] = (dst.get(k, 0) or 0) + v
                        src[k] = 0
            elif isinstance(src, int):
                bm[keys[1]] = (dst or 0) + src
                bm[keys[0]] = 0
            else:
                return "SKIPPED (unknown by_model shape)"
            save(doc, p)
            return f"all {keys[0][:26]} tokens relabelled as {keys[1][:26]}"
    return "SKIPPED (needs 2 models)"


def a_shift_days(d):
    """Move tokens between DAYS. Totals unchanged, history rewritten.

    by_day is what the floor's `after last_computed` term reads. Shifting a day
    changes the floor without changing a single total.

    A by_day value is a dict of the 4 token fields, not an integer. The first
    version of this attack tested isinstance(int) and skipped every time, so it
    ran zero times while the summary still said "every attack caught".
    """
    doc, p = load(d, machines(d)[0], "totals.json")
    for a in doc.get("accounts", []):
        bd = a.get("by_day") or {}
        days = sorted(bd)
        if len(days) < 2:
            continue
        first, last = days[0], days[-1]
        src, dst = bd[first], bd[last]
        if isinstance(src, dict) and isinstance(dst, dict):
            for k, v in src.items():
                dst[k] = dst.get(k, 0) + v
                src[k] = 0
        elif isinstance(src, int) and isinstance(dst, int):
            bd[last] = dst + src
            bd[first] = 0
        else:
            continue
        save(doc, p)
        return f"{first} tokens moved onto {last} (totals unchanged)"
    return "SKIPPED (no account has 2 days)"


def a_fake_scanner_version(d):
    """Claim a scan came from the CURRENT scanner when it did not.

    The version check compares machines to each other. A stale machine that
    LIES about its version looks perfectly consistent.
    """
    doc, p = load(d, machines(d)[0], "totals.json")
    doc["scanner_version"] = "deadbeefcafe"
    save(doc, p)
    doc2, p2 = load(d, machines(d)[-1], "totals.json")
    doc2["scanner_version"] = "deadbeefcafe"
    save(doc2, p2)
    return "two machines both claim scanner deadbeefcafe"


def a_delete_the_evidence(d):
    """Delete a machine folder outright, rather than shrinking it.

    Shrinking is caught by the drop check. Removing the folder means there is
    nothing to compare — the machine simply stops existing, and a total that
    never mentions it cannot disagree with itself.
    """
    victim = machines(d)[0]
    t = os.path.join(d, victim)
    if not os.path.isdir(t):
        return "SKIPPED"
    shutil.rmtree(t)
    return f"{victim} folder deleted entirely"


def a_forge_a_retire(d):
    """Delete a machine, then fake the marker that says it was retired.

    Added the same hour the retire exemption was, because an exemption is a
    hole until something tries to climb through it. The check now treats a
    machine as retired-not-lost when it appears under
    testing-archive/<stamp>/stale-machines/ — so the obvious attack is to
    delete the folder and mkdir that path.

    It must not work: retire_archive.py MOVES the machine's documents there, so
    the archived copy holds its totals.json. An empty directory does not.
    """
    ms = machines(d)
    if not ms:
        return "SKIPPED (no machines)"
    victim = ms[0]
    t = os.path.join(d, victim)
    if not os.path.isdir(t):
        return "SKIPPED"
    shutil.rmtree(t)
    os.makedirs(os.path.join(d, "testing-archive", "FORGED",
                             "stale-machines", victim), exist_ok=True)
    return f"{victim} deleted, then a retire marker forged for it"


def a_truncate_sessions(d):
    """Empty sessions.json but leave totals.json intact."""
    doc, p = load(d, machines(d)[0], "sessions.json")
    if isinstance(doc, dict):
        doc["sessions"] = []
    else:
        doc = []
    save(doc, p)
    return "sessions.json emptied, totals untouched"


def a_backdate_last_computed(d):
    """Move a stats_cache last_computed EARLIER.

    The floor is counter + days strictly after last_computed. Backdating makes
    more days count as 'after', so the same data yields a larger floor. Nothing
    sums differently.
    """
    doc, p = load(d, machines(d)[0], "sessions.json")
    sc = doc.get("stats_cache") or []
    if not sc:
        return "SKIPPED (no stats_cache)"
    before = sc[0].get("last_computed")
    sc[0]["last_computed"] = "2020-01-01"
    save(doc, p)
    return f"last_computed {before} -> 2020-01-01 (inflates the floor)"


ATTACKS = [
    ("relabel a model", a_swap_model_labels),
    ("shift tokens between days", a_shift_days),
    ("forge a scanner_version", a_fake_scanner_version),
    ("delete a whole machine", a_delete_the_evidence),
    ("forge a retire marker", a_forge_a_retire),
    ("empty sessions.json", a_truncate_sessions),
    ("backdate last_computed", a_backdate_last_computed),
]


def main():
    # The baseline is the CONTROL, and it must be subtracted. The first version
    # of this harness compared warn counts against a constant, and the repo
    # already emits 3 warnings — so every attack scored "flagged" and the run
    # concluded "every attack caught" while catching none of them. A harness
    # that cannot fail is worth exactly as much as a test that cannot fail.
    base = fresh()
    bf, bw, _ = run_checks(base)
    print(f"  BASELINE (control)              {bf} failed, {bw} warned\n")
    shutil.rmtree(os.path.dirname(base), ignore_errors=True)

    survived, skipped, warn_only = [], [], []
    for name, fn in ATTACKS:
        d = fresh()
        what = fn(d)
        f, w, _ = run_checks(d)
        if what.startswith("SKIPPED"):
            verdict = "skipped"
            skipped.append(name)
        elif f > bf:
            verdict = f"CAUGHT (+{f - bf} fail)"
        elif w > bw:
            verdict = f"flagged (+{w - bw} warn)"
            warn_only.append(name)
        else:
            verdict = "*** SURVIVED ***"
            survived.append(name)
        print(f"  {name:<30} {f} failed, {w} warned  (base {bf}/{bw})  {verdict}")
        print(f"    {what}")
        shutil.rmtree(os.path.dirname(d), ignore_errors=True)

    # A skipped attack is not a passing attack. Saying "every attack caught"
    # while one of them never executed is the exact failure this file exists to
    # find, one level up: not-run printing identically to fine.
    print()
    if survived:
        print(f"  {len(survived)} attack(s) SURVIVED: {', '.join(survived)}")
    if skipped:
        print(f"  {len(skipped)} attack(s) NEVER RAN: {', '.join(skipped)}")
    if warn_only:
        print(f"  {len(warn_only)} warned but did not fail: {', '.join(warn_only)}")
    ran = len(ATTACKS) - len(skipped)
    if not survived and not skipped:
        print(f"  all {ran} attacks ran, all {ran} caught")
    else:
        print(f"  {ran}/{len(ATTACKS)} attacks actually ran")
    return 1 if (survived or skipped) else 0


if __name__ == "__main__":
    sys.exit(main())
