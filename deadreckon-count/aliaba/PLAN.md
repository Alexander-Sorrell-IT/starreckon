# Plan of record — 2026-08-09

45 findings, confirmed by adversarial red team: 10 attackers given the system's
published CLAIMS and told to refute them, method of their own choosing, each
finding then re-run by independent skeptics who killed 22 of 74 candidates.

    run 1  6 attackers   47 candidates   35 confirmed   30 after merge
    run 2  4 attackers   27 candidates   17 confirmed   15 after merge
           133 agents · 8.0 M tokens · ~2 hours

**All six repo claims and all four mission claims came back FALSE.**

## Why the previous plan missed all of this

FIX-PLAN.md closed 25 of 25 and the suites reached 19 of 19 planted defects
caught. Both numbers were real. Both measured the wrong axis.

A planted-break harness asks *did I break it*. Every finding below is *it was
never right*. Nothing is broken in the sense a diff can show: each is a correct
computation of a smaller or different thing, published under the name of the
bigger one.

    export_corpus      123 of 1,059 transcripts    "every conversation preserved"
    COVERAGE           5 machines vs 1 machine     "the gap"
    LIFETIME           3 of 5 machines             "everything ever recorded"
    archive/months     one partial checkout        "the only thing that still knows"
    os.path.exists     a path is occupied          "already archived"
    root-file archive  every file                  "records, never config"

That is why `check_consistency` reports 38 checks, 0 failed over a 26.7 billion
token undercount: the parts genuinely do sum to the whole they were told to sum.

---

## P0 — credentials and irreversible loss. Nothing else runs first.

**P0.1 Live OAuth refresh tokens are in the hard-link archive, same inode as
the originals.** `retention_guard.py`, link_tree top_only branch.

    ~/.ai-logs-archive/other/gemini-root/oauth_creds.json  ino=42500290 nlink=3
        keys: access_token, refresh_token, id_token
    ~/.ai-logs-archive/other/devvit/token                  ino=42205535 nlink=2

41 of 49 archived root files are config, not records. `_is_loose_record` — the
record/config test — exists only in `export_corpus.py`. The archiver has no
filter at all, while `export_corpus.py:379` names these exact two files as the
motivating incident and states the fix **in the past tense**.

Fix: the archiver calls the same test. One rule, both callers.

**P0.2 The exporter uses the flat glob. 451 transcripts exist in no copy
anywhere.** `export_corpus.py:708` — `sorted(proj.glob("*.jsonl"))`.

936 of 1,059 live transcripts invisible; 451 files / 101,422,464 bytes /
1,204,376,673 tokens with zero copies under `deadreckon-record`. Irreversible
the moment `cleanupPeriodDays` deletes the live file.

This is the FOURTH copy of the flat glob. Three were fixed today —
`sessions.py`, `count_corpus.py`, `corpus_reports.py` — and the one component
that writes the durable copy was never checked.

**P0.3 "Already archived" is decided by path existence, never inode.**
`retention_guard.py:497` — `if os.path.exists(d): skipped += 1`.

Any file rewritten by atomic rename gets a new inode while the destination holds
the orphan, so the live file is never linked and reports protected forever.
6 ghost entries measured; `~/.claude.json` live `ino=42210401 nlink=1` against
archive `ino=42216256`. 205,167 live bytes reported archived that are not.

**P0.4 A dead belt reports `retention: ok`.** The DIFFERENT FILESYSTEM path
returns before `FAILED_LINKS` is touched, so 0 of 4 files archived across a
mount boundary still records ok, exit 0. `--check` structurally cannot see a
link failure at all — it counts what it WOULD do.

**P0.5 The daemon is not running and nothing says so.** 44 live transcript
files currently have no hard link.

---

## P1 — the ledger's one guarantee, inverted

**P1.1 A deletion DOES lower the lifetime.** `token_ledger.py:136-175`.
Driving the real module: a partial deletion plus one `scanner_version` bump took
a session from 1,000,000,000 to 10,000,000. The newest-scanner-wins rule, which
exists so a correction can lower a total and a deletion cannot, is satisfied by
a forged version.

**P1.2 No report ever opens the ledger.** `monthly.py`, `README.md:543`.
LIFETIME.md states it includes usage whose transcripts are gone. It is scan-only
and misses 4,895,744,312 tokens the ledger holds.

**P1.3 4.07 billion tokens dropped for want of a start date.**
`monthly.py:69-72` — sessions with no `start` are skipped silently.

**P1.4 Published lifetime is 26.7 B below what the repo holds**, and 38
consistency checks pass over it.

---

## P2 — the published numbers are false

**P2.1 The front page drops 2 of the 5 machines it holds and calls them
"never scanned".** README.md:86-100, ALL-COMPUTERS.json, BY-COMPUTER.md.

Both are committed with complete scans dated 2026-08-09 — *earlier than the
rollup's own timestamp*. Running the repo's own `combine.py` on the untouched
committed data gives **109,394,493,211**; the front page publishes 30.43 B.

The repository publishes THREE mutually exclusive fleet totals at HEAD, and the
sibling repo publishes a fourth for the same quantity. Cross-repo disagreement:
16,309,192,098.

**P2.2 `archive/months` is permanently short 18,784,531,262 tokens and its
failure direction is inverted.** `monthly.py:246` — `if dest.is_dir() and not
args.all: continue`. Each month froze from whatever one checkout held; the
docstring says recomputing would read FEWER records, and it reads more.

**P2.3 COVERAGE publishes a 16.4 B gap that does not exist.**
`corpus_reports.py:315` — `ts += sc` unconditional, `tc += cc` guarded, so five
machines are compared against one. Honest gap: −39,995,929. *Written 2026-08-09,
by me, hours before this run.*

**P2.4 `detect_patterns()` leaks the literal `{vscode}`.** `stores.py:308`.
kilocode and copilot-chat report `installed: false` on every machine while their
own readers return 7,074,501 and 1,214,160 tokens in the same run. *Also mine,
same evening, from the platform-path work.*

**P2.5 `sweep_usage.py` prints "NOT COVERED — nothing"** on a home holding
1,735,000,000 uncounted tokens. It is the documented backstop for a CLI nobody
wrote a reader for.

**P2.6 Three invented accounts holding 493,600,890 tokens** — the guard's own
hard-link archive counted as separate profiles.

---

## P3 — the gate does not read what it certifies

**P3.1** `check_consistency.py` compares `totals.json` to `totals.json`. A grep
for `ALL-COMPUTERS|BY-COMPUTER|README|STATS|LIFETIME` in it returns nothing. It
has never opened a published document. That single fact explains every P2 item
surviving 38/38.

**P3.2** Three of the 38 checks put the identical expression on both sides —
after five of exactly that shape were fixed this morning.

**P3.3** `scanner_version` is forgeable and forging it switches OFF the
closed-day audit; 22.7 M tokens erased with no failure.

---

## P4 — machines write into each other's folders

Already in git: `fun_stats.py` and `monthly.py` rewrote 12 tracked files inside
4 other computers' folders, reaching commit `4a5b42c`. `corpus_reports.py`
writes into every machine's folder in the record repo. `run.py rebuild` deletes
two other computers' tracked SCORECARD.md and never regenerates them.
`update.py` routes a different physical host into a folder already claimed.
`corpus_ship.py push` drops its ownership filter and re-uploads everyone's asset.

`foreign_staged()` — written today — reports this at commit time. It does not
prevent the write.

---

## P5 — the red team becomes part of the system

This is the structural item, and without it the rest is a one-off.

Everything above was found by attackers given a CLAIM and told to refute it,
choosing their own method. Nothing above was found by the suites, because the
suites test implementations against breaks I chose, and my blind spots chose
them.

**P5.1 `claims.py` — every published statement is a registered claim.**
A file listing, for each published document, what it asserts and which code is
supposed to make it true. A document with no registered claim is a finding.

**P5.2 The gate reads the published documents.** `check_consistency` must open
README.md, BY-COMPUTER.md, ALL-COMPUTERS.json, LIFETIME.md, STATS.md,
COVERAGE.md, parse the figures it finds, and check them against the machine
folders. This is the root fix for all of P2 — those numbers were wrong for
weeks because nothing ever looked at them.

**P5.3 `redteam.py` — the adversarial run, in the repo.** The workflow used
tonight, as a committed script: claims in, attackers out, findings refuted by
independent skeptics, survivors reported. Run on demand and before any
publication.

**P5.4 Fixes land in every copy.** The flat glob was in four files. The
record/config rule in one of two. A check that greps the tree for a
just-fixed pattern and fails when a second copy exists.

**P5.5 `retire` IS A TEST, and a clean start is the strongest one we have.**

The command exists for two reasons and the second is the important one:

1. production starts uncontaminated by past runs
2. **it proves the system works from zero**

Countless bugs here have surfaced only AFTER a clean. That is backwards — it
means the clean was doing the work the suites should have done. The invariant:

> The system must produce the same correct behaviour from an empty tree as from
> a populated one. Any defect that appears only after a clean is a defect in
> the system, not a consequence of cleaning.

Proven twice on 2026-08-09 and both times I treated it as an incident rather
than as the point: `corpus_reports.py` died with `ValueError: max() iterable
argument is empty` on a FRESH CLONE — hit by dell-latitude, the first machine
to follow the new instructions — and not one of the 19 planted defects
exercised an absent, empty or single-item input.

So: empty / partial / single-item / fresh-clone is a standing test class, and
`retire` is run deliberately as a verification step before production, with the
full suite and a red-team pass executed against the cleaned tree. A clean that
reveals a bug means the bug was always there.

**P5.6 `retire` covers the DOCUMENTS, in BOTH repositories.**

Documentation describes behaviour, and when the behaviour was wrong the
documents recorded the wrong thing. Right now the published documents assert:
two scanned machines "never scanned", three mutually exclusive fleet totals, a
LIFETIME 26.7 B below what the repo holds. Those are archived and cleared, not
edited in place — kept as the record of what was believed, removed from the
tree so production starts from documents that were generated by correct code.

`retire_archive.py` already copies `human-readable/` and `machine-readable/`
per machine and collectively. It must do the same in `deadreckon-record`, and
both repos need the verb reachable from `run.py`.

**P5.7 The DYNAMICALLY CREATED structures must not carry development residue
into production.**

This system creates directories and files as it runs: per-machine folders,
`human-readable/`, `machine-readable/`, `archive/<machine>/<stamp>/`,
`months/`, `corpus/<machine>/tools/<label>/`. Anything produced by an approach
that was later abandoned simply STAYS, because nothing enumerates those
directories to ask what still belongs to the current code.

Confirmed instances, on disk right now:

    two contradictory MANIFEST.json per machine, committed side by side --
        one at the machine root from the old flat layout, one in
        machine-readable/ from the split; both shipped, both read
    corpus/hp-laptop-linux/tools/claude-config/  -- written by a store that
        must never be preserved
    testing-archive/.../stale-machines/out/  -- a scratch scan directory that
        looked like a machine folder to every consumer

A retire clears these so production regenerates them from the code that exists
now. Otherwise a folder written by code that was deleted months ago outlives
every fix, and the only thing that would notice is a person who happens to look.

The check that belongs with it: after a clean run, every file present under a
dynamically created directory must be attributable to a generator that still
exists. Anything else is residue and is reported.

**P5.8 A DYNAMIC FILE MUST STAY DYNAMIC. Staleness has to be impossible, not
merely unlikely.**

The root documents — README tables, BY-COMPUTER.md, BY-ACCOUNT.md,
BY-COMPANY.md, STATS.md, LIFETIME.md, THIS-MONTH.md, ALL-COMPUTERS.json,
lifetime.json, COVERAGE.md — are DERIVED. Every one is computed from the
machine folders. None is a source.

They are also persisted and tracked, and that is how the worst finding in this
report happened: a rollup generated from 2 machines sat on the front page,
committed, while 5 machines were committed beside it with complete scans dated
EARLIER than the rollup itself. Nobody regenerated it, nothing required it to
be regenerated, and the gate never opened it. The front page understated the
fleet by 78,967,248,634 tokens and every check passed.

I defended tracking them earlier that same day as "tracked on purpose, so a
reader sees current numbers". The red team proved the inverse: tracking a
derived file WITHOUT forcing regeneration is precisely what manufactures the
lie. A derived file that persists is a claim with no expiry date.

A derived document must be in exactly one of two states:

    REGENERATED   from inputs at least as new as itself, or
    MOVED         into testing-archive/<stamp>/ and gone from the working tree

never STALE, and never DELETED. The working tree going to zero means the
content went into the archive, not that it stopped existing. A clean is a
relocation — that rule is the same for root documents as for everything else,
and "regenerated or absent" was my wording for it, which leaves room to `rm` a
stale report and call that compliance. It is not.

A stale report is EVIDENCE. It is what the system believed at that moment, and
the 2026-08-09 red team found that those beliefs are exactly where the defects
live: the front page asserting two scanned machines were never scanned, three
mutually exclusive fleet totals, a LIFETIME 26.7 B under. Destroying the wrong
number destroys the proof of how it got that way.

Concretely:

  - every derived document carries the input fingerprint it was built from --
    the machine folders present and each one's scanner_version and
    generated_at. Not a timestamp alone; a timestamp cannot say WHICH inputs.
  - the gate reads each derived document, recomputes that fingerprint from the
    tree, and FAILS when they differ. This is P3.1 and it is the same fix: the
    gate must open what it certifies.
  - any operation that changes a machine folder either regenerates the
    documents or MOVES them to the archive. A missing report is a loud, honest
    state; a stale one is a quiet false one; a deleted one is both quiet and
    unrecoverable.
  - `run.py status` reports any derived document whose fingerprint no longer
    matches the tree, so the condition is visible before anyone publishes.

This is what turns P2 from "republish the numbers" into "the numbers cannot be
wrong in this way again".

---

## Order

1. **P0** — credentials, then the 451 unbacked transcripts, then the belt.
2. **P3.1** — make the gate read the documents. It is the cheapest change with
   the widest reach: it turns every P2 item into a failing check rather than a
   thing someone has to notice.
3. **P1** — the ledger, which is what the system is FOR.
4. **P2** — republish the numbers, once the gate can catch them being wrong.
5. **P4**, then **P5**.

**The fleet run stays blocked until P0 is done.** Running `update` now writes
more archive entries under P0.1 and more partial exports under P0.2.

## The work: how much, and how each piece is proved

**31 work items covering 45 findings.** Sized by wall clock, because the
constraint here is verification runtime and I/O, not typing. Every figure below
is grounded in what the same kind of change actually cost on 2026-08-09.

| group | items | what it is | est. |
|---|---|---|---|
| P0 | 5 | credentials, the 451 unbacked transcripts, the belt, the daemon | 1.5 h |
| P3 | 3 | the gate reads the documents it certifies | 1.5 h |
| P1 | 4 | the ledger: a deletion must not lower the lifetime | 1.5 h |
| P2 | 6 | republish, behind a gate that can now catch a wrong number | 1.5 h |
| P4 | 5 | machines writing into each other's folders | 1.0 h |
| P5 | 8 | claims registry, redteam.py, no-stale-derived, retire-as-test | 3.0 h |
| — | — | two red-team re-runs against the fixed code | 1.5 h |
| **total** | **31** | | **~11 h** |

Three or four working sessions. The fleet run is on top of that and is
unattended: ~5 min each for the two small machines, 20-45 min for the two
large ones.

### How each piece is proved

The rule, and it is the whole lesson of 2026-08-09: **every fix lands with an
ADVERSARY that would have caught the defect, not a test that agrees with the
fix.** A test written alongside a fix tends to assert exactly what the fix
does. That is how 25 of 25 and 19 of 19 were both true and both worthless.

Concretely, per group:

**P0 — demonstrate the loss, then demonstrate it is impossible.**
Build a home with an OAuth file in a root store, run the archiver, assert no
credential is linked. Build a profile with subagent transcripts two levels
down, run the exporter, assert every file is preserved. Rewrite a file by
atomic rename and assert the guard notices the inode changed. Each of these is
a state that exists on disk right now, so the test is written FROM the current
failure, not from the intended fix.

**P3 — the gate must fail on today's tree before it passes on tomorrow's.**
Point the new document-reading gate at HEAD as it stands. It must FAIL, naming
the front page's 78,967,248,634 shortfall. A gate that passes on the current
repository has not been fixed, it has been re-written to agree.

**P1 — attack the guarantee directly.** Drive the real `token_ledger` module:
delete transcripts, forge a `scanner_version`, and assert the lifetime does not
move. The red team already has the reproduction that takes a session from
1,000,000,000 to 10,000,000; that becomes the test.

**P2 — regenerate, then check the fingerprint, then delete a machine folder
and check it fails.** Both directions, always.

**P4 — run the real generators and diff every other machine's folder.**
`fun_stats.py` and `monthly.py` rewrote 12 tracked files in 4 other computers'
folders; the test runs them and asserts zero foreign paths changed.

**P5 — the suites are tested by attacking them.** `adversarial_meta.py`
already asks whether each suite can fail. It gains: does the suite exercise an
EMPTY input, does it exercise a FRESH CLONE, and does the fix exist in every
copy of the pattern.

### The clean-start test, run for real

`retire` is not the last step before production, it is a verification step.
Run it, then run everything against the cleaned tree: the full suites,
`run.py update`, both red teams. Anything that only appears after the clean was
always there. That is the whole reason the command exists, and it is the test
this system has historically been worst at.

### Definition of done

Not "all items closed". Three conditions, in order:

1. **Both red teams re-run against the fixed code and cannot falsify any of the
   ten claims.** Same prompts, no hints, independent refuters. If an attacker
   still kills a claim, that claim is still false regardless of how many items
   are ticked.
2. **The clean-start run is identical in correctness to the populated run.**
   Retire, then rebuild from zero, and the numbers match what the populated
   tree produced.
3. **The fleet reconciles.** Every machine scanned on one scanner version, and
   `count_corpus` reports every CLI at 0.00% against the corpus, with COVERAGE
   naming any genuine gap.

Only then does the production history begin.

## The rule this plan is built on

A number is not real because it is consistent. It is real when something that
could have contradicted it did not. Every fix here lands with an adversary that
would have caught the defect, not a test that agrees with the fix.
