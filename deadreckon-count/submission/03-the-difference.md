# Two wrapped tools, one corpus

Both tools were pointed at the **same** merged fleet corpus — 20,217 transcripts,
401 project folders, 5 computers — each in its own container, with the corpus
mounted read-only. Generated 2026-08-07.

| | `standout` 0.7.1 | `starforge-cli` 0.6.1 |
|---|---|---|
| where scoring happens | remote, server-side | in-process, this machine |
| network at scan time | required (it uploads) | **none** — run under `--network none` |
| what leaves the machine | **4,019,909 bytes** | **0** |
| artefacts produced | a URL | 146,072 bytes, local |
| dependencies | full tree | **zero** |
| result | UNICORN 100/100, top 1% of 3,756 | 23.9/25 as shipped — see below |

**Neither score is a measurement, and the second one is ours to fix.** An
adversarial audit of both tools found that starforge's total saturates: a
synthetic corpus with **one fifth** the tokens and under half the tool calls
scored 25.0/25 against this corpus's 23.9 — the lighter user ranked *higher*.
Ten times the work moved the total by 0.0. Two causes, both since fixed
locally: `computeLevels` clamped every axis at 5 while the underlying log
curve kept climbing, and an undisclosed `.slice(0, 20)` on the project list —
a display truncation — was silently feeding the ENGINEERING axis. Raising the
ceiling to 7 and letting the computation use it puts this corpus at
**28.9/35** and separates the profiles that used to tie.

A separate 5,000-path cap in the scan means the published 23.9 was wrong by
0.2 even on its own terms: uncapped it is 24.1, because two languages were
never seen.

This section stays in the document. A comparison that only reported the other
tool's defects would be marketing.

---

## They agree, which is the point

Two independent implementations, different languages of expression, same input.
Nothing here was reconciled — these are the raw figures each produced.

| | standout | starforge |
|---|---:|---:|
| sessions | 16,800 | 16,800 |
| active days | 97 | 97 |
| duration hours | 1,533.4 | 1,533.4 |
| input tokens | 188,465,919 | 188,465,919 |
| cache read tokens | 17,449,275,636 | 17,449,275,636 |
| cache write tokens | 650,705,683 | 650,705,683 |
| output tokens | 56,235,267 | 56,193,756 |

The only divergence is 41,511 output tokens — 0.07% — which is a tokenisation
or attribution edge, not a disagreement about what happened.

**A number that two unrelated readers derive independently is a measurement.
One that only one tool produces is a claim.** This is the first time either
figure has been corroborated.

---

## Where they stop agreeing

standout's live run printed this, on a developer with 19,790 prompts:

```
  HOW YOU TALK

    no message sample provided.

    reads    you mostly take the AI's lead.
    drives   you keep a tight rein on each

    19,790 prompts  ·  23% questions  ·  ~3786 chars
    recurring: no sample available
```

It counted the prompts and had none to show. starforge, same corpus:

```
  user_turns            30,680
  tool_call_counts      Bash 51,340 · Read 16,530 · Edit 6,384 · Write 3,237
                        WebFetch 1,303 · WebSearch 971 · Grep 524 · Agent 265
  star_levels           FIRST PRINCIPLES 5 · TENACITY 5 · CODING 5
                        OUTSIDE THE BOX 5 · ENGINEERING 3.9
```

---

## Why the card was blank

Measured from the payload itself, captured before the live run by a local sink
standing in for the API:

```
POST /api/public/wrapped        4,019,909 bytes   (MAX_BODY_BYTES = 4,000,000)
  exchanges                             0
  prompt_samples                        0
  conversation_samples                  0
  sessions                      4,311,105 bytes   = 99.7% of the payload
```

The cause is in `capPayload`:

```js
const over = () => byteLength(p) > MAX_BODY_BYTES;
while (over() && totalExchanges(p) > 0) { ... }
```

The loop ends when there is **nothing left to delete**, not when the payload
fits. It empties `exchanges`, then `prompt_samples`, then
`conversation_samples` — and it never touches `sessions`, which is one ~256-byte
telemetry row per session and 99.7% of the bulk. So on this corpus it deleted
every prompt and every conversation and **still exited 19,909 bytes over its own
cap**.

The failure scales the wrong way: the more a developer uses the tool, the more
sessions they accumulate, and the more certain it becomes that their profile
arrives with nothing in it. A light user is fine. A heavy user — the one worth
looking at — gets counts and silence.

### It is fixable without shrinking anything

Slicing the same corpus into four and merging the results afterwards:

```
per slice          ~2,045,000 bytes   500 exchanges · 50 prompts · 160 conversations
assembled          3,859,239 bytes    500 exchanges · 50 prompts ·  46 conversations
                                      + full-corpus aggregates, under cap
```

The totals never needed the session rows: `all_time` already carries
`total_sessions`, `active_days`, `total_duration_hours` and every token counter
in about 2,243 bytes.

---

## What neither tool can see

Both read transcripts, so both are bounded by what is still on disk. Claude Code
deletes sessions after `cleanupPeriodDays` but its `stats-cache.json` keeps the
lifetime counters.

| | tokens |
|---|---:|
| standout, this corpus | 18,344,682,505 |
| starforge, this corpus | 18,344,640,994 |
| every CLI still on disk, 5 machines | 53,770,418,140 |
| Claude Code per account | 46,491,126,455 |
| **floor, including deleted transcripts** | **118,688,898,254** |

Roughly **72 billion tokens exist only as frozen counters** — the transcripts
are already gone and no corpus can recover them.

Three caveats that matter more than the size of the numbers:

- **94.5% of any of these totals is the conversation being re-sent.** Only
  2,546,523,889 tokens are new content. A headline that does not say so is
  reporting the same sentences hundreds of times.
- The four rows above answer four different questions and must not be compared
  to each other, or added.
- `standout` reads one `HOME`; the 53.77 B figure spans 8 CLIs and 5 computers.
  It is not a like-for-like correction of their number.

---

## Cost and speed, same corpus, same host

Measured with `/usr/bin/time -v` on the identical 20,217-transcript tree:

| | wall | peak RSS | bytes leaving | deps |
|---|---:|---:|---:|---:|
| starforge | **74.15 s** | **409,092 KB** | **0** | **0** |
| standout | 218.84 s | 687,780 KB | 4,020,700 | 14 |

starforge is 2.95× faster on 1.68× less memory, and the zero is literal: the
run completed under `docker --network none`.

## What happened while auditing this

One of the audit runs invoked `standout` against a **real home directory**
before an interception sink existed, and it uploaded — `agent-enrich` carrying
an email address, then a 34,409-byte profile containing a name, git remotes
naming a private repository, 84 commit subjects and five corpus paths. No
credentials and no transcript text, but a private repo name reached a third
party.

It is recorded here because it is the strongest evidence in this document for
the thing the document argues. `standout` POSTs **before rendering a single
card** when stdin is not a TTY — even on an unrecognised flag, where a
reasonable reader would expect usage text and an exit. There is no confirmation
step to miss, because the upload happens first. A tool that cannot leave the
machine cannot make that mistake, which is the entire case for the local one.

## Fair to the other side

- **The single blank card is not carelessness** — it is one loop with the wrong
  termination condition, and it only misbehaves on corpora larger than most
  people have.
- **"Workspace, 11,621 sessions" — one project out of 401 — is our fault, not
  theirs.** The corpus renames every project folder to `-workspace-pNNNN` to
  protect private repository names, and their derivation reasonably collapses
  them.
- **starforge's tripwire is not a security boundary and says so.**
  `TRIPWIRE_LIMITS` enumerates its own four bypasses — Worker realms,
  `child_process`, `process.binding('tcp_wrap')`, filesystem egress — and the
  `verify` command prints them. The boundary is OS confinement; here it was a
  container with no network at all.

---

## Reproducing this

```bash
# their tool, upload intercepted, nothing sent
./submit_gate.sh --merged merged -- standout-founding-eng
python3 verify_payload.py --capture capture          # the payload, audited

# the fix
python3 chunk_corpus.py --merged merged --out chunks --chunks 4
python3 assemble_payload.py --full cap-full --chunks cap-0{1,2,3,4}

# starforge, separate image, no network
docker run --rm --network none \
  -v "$PWD/merged/.claude:/home/runner/.claude:ro" \
  -v "$PWD/sf-home:/home/runner/.starforge" \
  starforge-runner \
  'node /opt/starforge/src/cli.mjs --yes --no-pace --card --page --json'
```

Every figure above came out of one of those commands. The captured payloads and
the starforge reports are on disk and can be re-read by anyone who doubts a
number in this file.

---

## Cost of running, same corpus, same host

| | wall | peak RSS | bytes out | deps |
|---|---:|---:|---:|---:|
| starforge | **74.15 s** | **409,092 KB** | **0** | **0** |
| standout | 218.84 s | 687,780 KB | 4,020,700 | 14 |

2.95× faster on 1.68× less memory. The zero is literal — the run completed
under `docker --network none`.

## The mechanism difference, in one line each

**Where scoring happens.** standout uploads and scores server-side; starforge
computes in-process. That is the whole disagreement, and everything below
follows from it.

**What that costs standout.** It must fit a profile through a 4 MB pipe, so
`capPayload` sheds content — and its loop terminates on "nothing left to drop"
rather than "it fits", which on a heavy user deletes every prompt and
conversation and *still* overflows. The product gets worse the more you use it.

**What that costs starforge.** No cohort. No percentile, no leaderboard, no
"top 1% of 3,756 users" — because those need everyone else's data, and it
refuses to collect anyone's. `ownRank` compares you only to your own history,
and says nothing at all with fewer than three months. That is a real feature
gap, not a rounding error, and it is the honest price of the position.

**What is checkable either way.** starforge ships `TRIPWIRE_LIMITS`, which
enumerates the four ways its own egress tripwire can be defeated, and `verify`
prints them. A tool that publishes its own bypasses is making a different kind
of claim than one that asks to be trusted.
