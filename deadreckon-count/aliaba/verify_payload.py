#!/usr/bin/env python3
"""The gate over what a profile tool would UPLOAD, not over what is on disk.

    python3 verify_payload.py --capture capture/       # audit a captured run
    python3 verify_payload.py --selftest               # prove the gate works

Every other check in this repository looks at files. This one looks at the
bytes that were about to leave: `docker/sink.js` stands in for standout.work,
the CLI runs its whole flow against it, and every request lands in `capture/`.
That is the only artifact that matters, because it is the only one anybody else
would ever see.

WHY IT IMPORTS THE REDACTOR'S OWN RULES

The recurring failure in this repo is two copies of a rule drifting apart — a
redactor that matched drive C while the verifier flagged any drive, a redactor
that wanted three JWT segments while the verifier flagged two. Every time, the
weaker one was the one doing the removing, so the check reported leaks that
nothing could fix.

So this does not restate the patterns. It imports SPANS and TOPIC from
export_corpus and LEAK from merge_corpus, which makes the gate *at least* as
strict as both by construction. Then it adds rules of its own that neither has,
because a gate built only from the redactor's rules can never catch a redactor
bug — it would agree with it perfectly.

WHY THERE IS A SELF-TEST

A gate that has never failed proves nothing. `--selftest` feeds it a payload
stuffed with real-shaped secrets and asserts it FAILS, then a clean one and
asserts it PASSES. If the first ever passes, this file is decorative.

WHAT IT CANNOT DO

It removes what matches a pattern. Prose that describes something sensitive
matches nothing, and no gate here will catch it. Read the samples.
"""

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT))

# The redactor's rules, imported rather than restated — see the docstring.
try:
    from export_corpus import SPANS, TOPIC
except Exception as e:                                    # pragma: no cover
    raise SystemExit(f"cannot import export_corpus rules: {e}")

try:
    from merge_corpus import LEAK
except Exception:
    LEAK = {}

# Rules the other two do NOT have. A gate assembled purely from the redactor's
# own patterns agrees with the redactor by definition, including where it is
# wrong. These are the independent opinion.
EXTRA = {
    # Absolute paths under the roots that carry a PERSON's name. The corpus
    # rewrites cwd to /workspace, so one of these in an upload means something
    # reached the payload from a source the redaction never saw.
    #
    # NARROWED, deliberately, after a false positive: `/var/diags/datafile`
    # was flagged in a security assessment — a path on the APPLIANCE being
    # audited, quoted in the finding. /var, /opt and /srv are system
    # directories that appear in technical prose about other machines and
    # identify nobody; /home, /Users, /Volumes, /media and /root are where an
    # operating system puts a username. Keeping the broad form would have
    # trained the reader to dismiss this rule, which is how a real hit gets
    # waved through. Project names are covered by TOPIC, not by this.
    "absolute path": re.compile(
        r"(?<![A-Za-z0-9])/(?!workspace\b)"
        r"(?:home|Users|Volumes|media|mnt|root)/[A-Za-z0-9._-]+/[A-Za-z0-9._-]+"),
    # Windows, both spellings, any drive.
    "windows path": re.compile(r"[A-Za-z]:\\{1,2}(?:Users|Documents)\\{1,2}[A-Za-z0-9._-]+", re.I),
    # A private address in an upload usually means an internal service name
    # travelled with it.
    "private ip": re.compile(
        r"\b(?:10\.\d{1,3}|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b"),
    # cwd and gitBranch are rewritten to fixed values on export. Anything else
    # means an unexported source reached the payload.
    "raw cwd": re.compile(r'"cwd"\s*:\s*"(?!/workspace")[^"]{2,}"'),
    # ssh material that is not a key block (agent sockets, known_hosts lines).
    "ssh artifact": re.compile(r"\b(?:id_rsa|id_ed25519|known_hosts|authorized_keys)\b"),
    # Bearer/token assignments that SPANS' generic rule can miss when the value
    # is short but the key is unambiguous.
    "credential key": re.compile(
        r"(?i)\"(?:api_?key|secret|access_?token|refresh_?token|password)\"\s*:\s*\"[^\"]{8,}\""),
}

# Kept identical to export_corpus.EMAIL — see the note there for why the
# trailing \b is absent. A checker laxer than the redactor cannot catch what
# the redactor misses, which is the only job this constant has.
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# standout's own cap. A payload at the ceiling has silently dropped content,
# which matters because the gate can only judge what it was shown.
MAX_BODY_BYTES = 4_000_000


def walk_strings(o, out):
    """Every string in the decoded payload, KEYS INCLUDED.

    Keys matter: AskUserQuestion stores the question text as a dict key under
    toolUseResult, so a scan of values alone leaves it fully readable.
    """
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(k, str):
                out.append(k)
            walk_strings(v, out)
    elif isinstance(o, (list, tuple)):
        for v in o:
            walk_strings(v, out)
    elif isinstance(o, str):
        out.append(o)


def mask(s, keep=6):
    s = s.replace("\n", " ")
    return s[:keep] + "…" + str(len(s)) + "ch" if len(s) > keep else s


def scan_strings(strings, keep_email):
    """Returns {rule name: [samples]}. Decoded strings only — never raw bytes.

    Scanning raw JSON text reports `\\n@pytest.fixture` as an email address (a
    decorator after an escaped newline) and produced 613 false positives the
    first time it was done that way.
    """
    hits = {}

    def add(name, sample):
        hits.setdefault(name, [])
        if len(hits[name]) < 5:
            hits[name].append(mask(sample))

    for s in strings:
        if not s or len(s) < 3:
            continue
        for rx, _ in SPANS:
            for m in rx.findall(s):
                add("credential", m if isinstance(m, str) else str(m))
        for m in TOPIC.findall(s):
            add("protected topic", m if isinstance(m, str) else str(m))
        for name, rx in LEAK.items():
            for m in rx.findall(s):
                add(f"leak:{name}", m if isinstance(m, str) else str(m))
        for name, rx in EXTRA.items():
            for m in rx.findall(s):
                add(f"extra:{name}", m if isinstance(m, str) else str(m))
        for m in EMAIL.findall(s):
            if keep_email and m.lower() == keep_email.lower():
                continue
            add("third-party email", m)
    return hits


QUALITATIVE = ("exchanges", "prompt_samples", "conversation_samples")


def qualitative_counts(docs):
    """How much actual CONTENT survived capPayload, by key.

    These are the lists the profile is built to display. They are also the
    first things dropped when the payload is too big, so a zero here means the
    submission is counts-only — technically valid, entirely uninformative.
    """
    totals = {k: 0 for k in QUALITATIVE}

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in totals and isinstance(v, list):
                    totals[k] += len(v)
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    for d in docs:
        walk(d)
    return totals


def load(capture):
    """Every captured request, newest scheme first. Returns (docs, meta)."""
    files = sorted(pathlib.Path(capture).glob("*.json"))
    docs, meta = [], []
    for f in files:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            meta.append({"file": f.name, "error": str(e), "bytes": 0})
            continue
        meta.append({
            "file": f.name, "method": d.get("method"), "url": d.get("url"),
            "bytes": d.get("body_bytes", 0), "json": d.get("body_is_json"),
        })
        if d.get("body") is not None:
            docs.append(d["body"])
        elif d.get("body_raw"):
            docs.append(d["body_raw"])
    return docs, meta


def audit(capture, keep_email, quiet=False):
    docs, meta = load(capture)
    strings = []
    for d in docs:
        walk_strings(d, strings)

    hits = scan_strings(strings, keep_email)
    biggest = max((m.get("bytes", 0) for m in meta), default=0)
    total = sum(m.get("bytes", 0) for m in meta)

    # SAFETY vs ADVISORY is the whole difference between a gate people obey and
    # a gate people learn to click through.
    #
    # The first version failed the run because the payload was 19,938 bytes over
    # standout's own cap. That is truncation, not disclosure — nothing leaked,
    # the tool simply sends less than it read. Printing "DO NOT SUBMIT" for it
    # teaches you that the banner does not mean anything, and then it is not
    # believed on the day it says "credential".
    #
    # SAFETY blocks: something private would leave.
    # ADVISORY informs: the upload is not what you think it is.
    safety, advisory = [], []

    def block(name, ok, detail):
        safety.append((name, ok, detail))

    def note(name, ok, detail):
        advisory.append((name, ok, detail))

    # A gate that passes an empty capture proves nothing at all. These are
    # SAFETY because a silent no-op reads exactly like a clean result — the
    # single most repeated bug in this repository.
    block("capture is non-empty", len(meta) > 0, f"{len(meta)} request(s)")
    block("a payload was actually built", biggest > 10_000,
          f"largest body {biggest:,} bytes")
    block("payload has content to judge", len(strings) > 100,
          f"{len(strings):,} strings decoded")
    block("no parse failures", not any("error" in m for m in meta),
          f"{sum(1 for m in meta if 'error' in m)} unparseable")

    for name in sorted(hits):
        block(f"no {name}", False, f"{len(hits[name])}+ sample(s): {hits[name][:3]}")
    if not hits:
        block("no credentials, paths, topics or emails", True,
              f"{len(SPANS)} span rules + {len(LEAK)} leak rules + {len(EXTRA)} extra rules")

    note("payload under the size ceiling", biggest < MAX_BODY_BYTES,
         f"{biggest:,} of {MAX_BODY_BYTES:,}"
         + ("  <- OVER: capPayload could not get under it" if biggest >= MAX_BODY_BYTES else ""))

    # The submission is supposed to SHOW something. capPayload shrinks an
    # oversized profile by emptying exchanges, then prompt_samples, then
    # conversation_samples — and its loop stops when there is nothing left to
    # drop, NOT when the payload finally fits. On a fleet this size it emptied
    # all three and was still over, because the remaining bulk is per-day and
    # per-project aggregate structure that it has no rule to shrink.
    #
    # The result passes every safety check while being worth nothing: counts
    # with no conversations. Silence here would have read as success, so it is
    # measured and named.
    quals = qualitative_counts(docs)
    for key, n in sorted(quals.items()):
        note(f"payload keeps {key}", n > 0,
             f"{n:,}" + ("   <- STRIPPED: the profile shows no actual work" if n == 0 else ""))

    failed = [c for c in safety if not c[1]]
    warned = [c for c in advisory if not c[1]]

    if not quiet:
        print(f"\n  capture   {capture}")
        print(f"  requests  {len(meta)}   total {total:,} bytes   largest {biggest:,}")
        for m in meta:
            print(f"    {m.get('method','?'):5} {str(m.get('url'))[:52]:54}"
                  f"{m.get('bytes',0):>10,} B")
        print("\n  SAFETY — would anything private leave?")
        for name, ok, detail in safety:
            print(f"    {'PASS' if ok else 'FAIL'}  {name:42}{detail}")
        print("\n  ADVISORY — is the upload what you think it is?")
        for name, ok, detail in advisory:
            print(f"    {'ok  ' if ok else 'WARN'}  {name:42}{detail}")
        print(f"\n  {len(safety)} safety checks, {len(failed)} failed"
              f"   ·   {len(warned)} advisory warning(s)")
        if failed:
            print("\n  DO NOT SUBMIT. Every failure above is private content that\n"
                  "  would have been uploaded. Fix the export, re-run, re-check.")
        else:
            print("\n  Safe to submit as far as PATTERNS go. That is a real but\n"
                  "  narrow claim: prose describing something sensitive matches\n"
                  "  nothing here. Read the payload before deciding.")
    return len(failed), safety + advisory


DIRTY = {
    "sessions": [{
        "cwd": "/home/phantomcore/AI_DRIVE/secret-project",
        "prompt": "deploy with sk-ant-api03-AAAAAAAAAAAAAAAAAAAAAAAAAAAA and ghp_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        "note": "see C:\\Users\\realperson\\Desktop and /Users/someone/thing",
        "mail": "third.party@example.com",
        "host": "192.168.1.44",
        "topic": "the ks_system upflow arrow class",
    }] * 40
}
CLEAN = {
    "sessions": [{
        "cwd": "/workspace",
        "prompt": "refactor the parser and add a regression test for the empty case",
        "note": "the file lives at [path] and the key was [redacted]",
        "mail": "codehunterextreme@gmail.com",
        "host": "localhost",
        "topic": "a compression experiment",
    }] * 40
}


def selftest(keep_email):
    """Prove the gate fails dirty input and passes clean input."""
    import tempfile
    ok = True
    for label, doc, want_fail in (("unredacted", DIRTY, True), ("clean", CLEAN, False)):
        with tempfile.TemporaryDirectory() as td:
            (pathlib.Path(td) / "0001-POST-agent-submit.json").write_text(json.dumps({
                "seq": 1, "method": "POST", "url": "/api/agent-submit",
                "body_bytes": len(json.dumps(doc)), "body_is_json": True, "body": doc,
            }), encoding="utf-8")
            failed, checks = audit(td, keep_email, quiet=True)
            got_fail = failed > 0
            good = got_fail == want_fail
            ok &= good
            print(f"  {'PASS' if good else 'FAIL'}  {label:12} "
                  f"expected {'FAIL' if want_fail else 'PASS'}, "
                  f"got {failed} failing check(s)")
            if not good:
                for n, o, d in checks:
                    if not o:
                        print(f"          - {n}: {d}")
    print(f"\n  {'gate works' if ok else 'GATE IS BROKEN — do not rely on it'}")
    return 0 if ok else 1


def show_samples(capture, n):
    """Print the qualitative content, because the gate cannot judge it.

    Every check in this file matches a PATTERN. A serial number, a client's
    hardware, an unreleased product name, an opinion about an employer — none
    of those look like a credential and none will ever be caught here. The only
    control for that is a person reading the thing before it is sent, and that
    is impossible if the payload is a 3.8 MB single line of JSON.
    """
    docs, _ = load(capture)
    shown = 0
    for d in docs:
        au = (d.get("profile") or {}).get("ai_usage") or {}
        for tool, t in au.items():
            if not isinstance(t, dict):
                continue
            for field in QUALITATIVE:
                vals = t.get(field)
                if not isinstance(vals, list) or not vals:
                    continue
                print(f"\n=== {tool}.{field}  ({len(vals)} item(s), showing {min(n, len(vals))})")
                for v in vals[:n]:
                    if isinstance(v, dict):
                        v = v.get("user") or v.get("prompt") or json.dumps(v)
                    print(f"  - {str(v)[:400]}")
                    shown += 1
    if not shown:
        print("\n  nothing qualitative in this payload — it is counts only.")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--capture", default="capture")
    ap.add_argument("--show", type=int, metavar="N",
                    help="print N samples per field and exit — read before you send")
    ap.add_argument("--keep-email", default="codehunterextreme@gmail.com",
                    help="the one address kept for attribution")
    ap.add_argument("--selftest", action="store_true",
                    help="prove the gate fails a dirty payload")
    a = ap.parse_args()

    if a.selftest:
        raise SystemExit(selftest(a.keep_email))

    if not pathlib.Path(a.capture).is_dir():
        raise SystemExit(f"no capture directory at {a.capture} — run submit_gate.sh first")
    if a.show:
        return show_samples(a.capture, a.show)
    failed, _ = audit(a.capture, a.keep_email)
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
