# By computer

_Every machine, and everything on it_

_Generated 2026-08-27T15:22:53-05:00 by `stats_page.py`. Do not edit by hand._

**60,524,260,897** tokens of Claude Code across 2 scanned computer(s) · **68,081,153,516** across every CLI on the 2 that ran `sessions.py`.

Those two are not added: the second contains the first. See [BY-COMPUTER.md](BY-COMPUTER.md) for the reconciliation.

Reports: [computers](BY-COMPUTER.md) · [accounts](BY-ACCOUNT.md) · [companies](BY-COMPANY.md) · [how it works](README.md)

---

## Totals

_scans taken 2026-08-27 05:06:36 .. 2026-08-27 15:19:30_

Each row carries the moment that computer was scanned. Machines are scanned independently, so a total is a snapshot of several different instants, never one.

| Computer | Folder | Accounts | Tokens | Share | Scanned |
|---|---|---:|---:|---:|---|
| **MacBookAir** | `macbookair/` | 9 | 42,036,497,160 | 69.5% | 2026-08-27 05:06:36 |
| **MacBook Air M1 (Darwin ARM64)** | `macbookair-attlocal-net/` | 8 | 18,487,763,737 | 30.5% | 2026-08-27 15:19:30 |
| **All** | | | **60,524,260,897** | 100% | |

### The two scopes, reconciled

```
Claude Code, per account (totals.json)  :   60,524,260,897
Claude Code, per session (sessions.json):   61,698,685,874
difference                              :   -1,174,424,977
non-Claude-Code CLIs, additional        :    6,382,467,642
```

**These should agree and differ by 1,174,424,977.** The usual innocent cause is a session still being written during the scan; anything larger is a bug worth finding before quoting these.

---

## MacBookAir

scanned **2026-08-27 05:06:36**

`macbookair/` · 9 account(s) · 8,786 sessions · 181,996 turns · **42,036,497,160 tokens** (69.5% of all Claude Code)

### Accounts on this computer

| Account | Tokens | Share of machine |
|---|---:|---:|
| acct-83084ebd | 28,623,097,827 | 68.1% |
| acct-17de7ff8 | 12,664,864,821 | 30.1% |
| acct-bc7f238c | 738,375,002 | 1.8% |
| unknown (Desktop_standout_sandbox_.claude) | 10,159,510 | 0.0% |
| unknown (Documents) | 0 | 0.0% |
| unknown (claude) | 0 | 0.0% |
| unknown (claude-it) | 0 | 0.0% |
| unknown (claude-main) | 0 | 0.0% |
| unknown (v10) | 0 | 0.0% |

### Companies on this computer

| Company | Tokens | Share |
|---|---:|---:|
| Anthropic | 42,036,497,160 | 100.0% |
| — (unidentified) | 0 | 0.0% |

### CLIs on this computer

| CLI | Sessions | Active | Tokens |
|---|---:|---:|---:|
| claude | 3,274 | 3,118h 18m | 42,036,497,160 |
| gemini | 4 | 9h 38m | 995,360,683 |
| copilot | 38 | 81h 54m | 572,446,089 |
| grok | 8 | 10h 09m | 100,222,322 |
| antigravity | 7 | 7h 30m | 60,483,428 |
| bob | 2 | 0m | 2,550,988 |

---

## MacBook Air M1 (Darwin ARM64)

scanned **2026-08-27 15:19:30** · sessions 2026-08-26 17:03:53

`macbookair-attlocal-net/` · 8 account(s) · 4,498 sessions · 74,818 turns · **18,487,763,737 tokens** (30.5% of all Claude Code)

> ⚠️ scanner `103c20d12f3a`, fleet is on `b9154bfefd2c` · **copilot-chat is installed here and read 0 sessions** — its usage is missing from every total below. These figures are a floor for this machine, not a total. `update.py` on it settles it.

### Accounts on this computer

| Account | Tokens | Share of machine |
|---|---:|---:|
| broodierchip@gmail.com | 12,834,169,588 | 69.4% |
| codehunterextreme@gmail.com | 5,321,298,979 | 28.8% |
| alexander.sorrell.it@gmail.com | 322,280,256 | 1.7% |
| unknown (Documents) | 10,014,914 | 0.1% |

### Companies on this computer

| Company | Tokens | Share |
|---|---:|---:|
| Anthropic | 18,487,763,737 | 100.0% |

### CLIs on this computer

| CLI | Sessions | Active | Tokens |
|---|---:|---:|---:|
| claude | 90 | 578h 19m | 19,662,188,714 |
| codex | 125 | 29h 43m | 1,633,604,881 |
| antigravity | 44 | 61h 45m | 1,077,099,663 |
| gemini | 4 | 9h 38m | 995,360,683 |
| copilot | 38 | 81h 54m | 572,446,089 |
| bob | 5 | 0m | 272,617,335 |
| grok | 8 | 10h 09m | 100,222,322 |
| lmstudio | 3 | 0m | 53,159 |

### Installed here — 10 tool(s)

Presence is separate from usage: a tool with no token column is installed and not counted, which is different from unused.

| Tool | Kind | Counted | Sessions | Tokens | Usage |
|---|---|---|---:|---:|---|
| Claude Code | cli | yes | 71 | 18,487,763,737 | 2026-05-26 → 2026-08-26 |
| OpenAI Codex CLI | cli | yes | 125 | 1,633,604,881 | 2026-07-13 → 2026-08-05 |
| Antigravity CLI | cli | yes | 44 | 1,077,099,663 | 2026-06-02 → 2026-08-26 |
| Google Gemini CLI | cli | yes | 4 | 995,360,683 | 2026-05-20 → 2026-05-23 |
| GitHub Copilot CLI | cli | yes | 38 | 572,446,089 | 2026-03-03 → 2026-08-24 |
| xAI Grok CLI | cli | yes | 8 | 100,222,322 | 2026-07-21 → 2026-08-15 |
| Continue | agent | no — usage not located on disk | — | — | last touched 2026-06-11 |
| VS Code Insiders | editor | no — editor — hosts agents, spends no tokens itself | — | — | 10 launches, 2 workspaces, 7 day(s): 2025-10-16 → 2026-06-14 |
| Ollama | runtime | no — local runtime — models run on this machine, nothing is billed | — | — | last touched 2026-06-01 |
| LM Studio | runtime | no — local runtime — models run on this machine, nothing is billed | — | — | last touched 2026-08-24 |

---

## Tokens nobody was billed for

**53,159 tokens** across 648 sessions ran on this hardware. They are counted in every total in these reports, because a token is a token regardless of who pays for it. What differs is the invoice, and there isn't one.

That is a third dimension, independent of the other two:

| Dimension | Question | Example |
|---|---|---|
| `cli` | which tool did you pay for | Copilot running a Claude model is GitHub spend |
| `provider` | whose model actually ran | …and Anthropic service |
| `billed` | did money change hands | Ollama running llama is neither |

| CLI | Model | Sessions | Tokens |
|---|---|---:|---:|
| lmstudio | `Wizard-Vicuna-7B-Uncensored.Q4_K_S.gguf` | 2 | 37,497 |
| lmstudio | `nomic-ai-gpt4all-falcon-Q4_K_S.gguf` | 1 | 15,662 |
| claude | `proj-475024d6` | 645 | 0 |

Every figure elsewhere includes these. To read spend rather than volume, subtract them: 68,081,100,357 of the 68,081,153,516 total was billed to someone.

---

## The floor: the most defensible figure per machine

**109,803,223,914 tokens across 2 scanned computer(s).**

_scans taken 2026-08-27 05:06:36 .. 2026-08-27 15:19:30_

Two sources describe Claude Code usage and neither contains the other. `stats-cache.json` accumulates from a profile's first session to its own `lastComputedDate` and stops; the transcripts hold whatever has not been deleted, which includes days after that date.

Subtracting them is meaningless. **Concatenating them is exact** — the counter owns everything up to its end date, the transcripts own the days strictly after it, and no token falls in both. Profiles with no counter, and every non-Claude tool, contribute only their surviving records, because nothing else on disk remembers usage once its records are gone.

| Computer | Claude Code | Other tools | Floor | Measured on disk |
|---|---:|---:|---:|---:|
| MacBookAir | 53,410,379,836 | 1,731,063,510 | **55,141,443,346** | 43,767,560,670 |
| MacBook Air M1 (Darwin ARM64) | 50,010,376,436 | 4,651,404,132 | **54,661,780,568** | 24,313,592,846 |
| **All** | | | **109,803,223,914** | |

It is a floor and not a total for three reasons, all measured rather than assumed: profiles without a counter lose anything pruned before the scan; the counter's own window has gaps where transcripts were deleted before it froze; and no non-Claude tool keeps a counter at all.

<details><summary>MacBookAir — how its floor is built</summary>

| Account | Counter | Counter ends | Transcripts after | Floor |
|---|---:|---|---:|---:|
| acct-83084ebd | 39,996,980,503 | 2026-08-25 | 0 | 39,996,980,503 |
| acct-17de7ff8 | 6,946,344,675 | 2026-07-30 | 5,066,966,543 | 12,664,864,821 |
| acct-bc7f238c | 571,753,755 | 2026-07-19 | 166,621,247 | 738,375,002 |
| unknown (Desktop_standout_sandbox_.claude) | _none_ | — | 10,159,510 | 10,159,510 |
| unknown (Documents) | _none_ | — | 0 | 0 |
| unknown (claude) | _none_ | — | 0 | 0 |
| unknown (claude-it) | _none_ | — | 0 | 0 |
| unknown (claude-main) | _none_ | — | 0 | 0 |
| unknown (v10) | _none_ | — | 0 | 0 |

</details>

<details><summary>MacBook Air M1 (Darwin ARM64) — how its floor is built</summary>

| Account | Counter | Counter ends | Transcripts after | Floor |
|---|---:|---|---:|---:|
| broodierchip@gmail.com | 39,996,980,503 | 2026-08-25 | 0 | 39,996,980,503 |
| codehunterextreme@gmail.com | 6,946,344,675 | 2026-07-30 | 2,406,951,502 | 9,353,296,177 |
| alexander.sorrell.it@gmail.com | 571,753,755 | 2026-07-19 | 78,331,087 | 650,084,842 |
| unknown (Documents) | _none_ | — | 10,014,914 | 10,014,914 |

</details>

---

## Claude Code's own counter, versus the transcripts

Every profile keeps `stats-cache.json`. It is not a transcript, so the cleanup sweep never touches it, and it accumulates from that profile's first session — including sessions whose transcripts were deleted months ago.

| Profile | Account | Own counter | Counter covers | From transcripts |
|---|---|---:|---|---:|
| `.claude-main` | acct-83084ebd | 39,996,980,503 | 2026-05-26 → 2026-08-25 | 28,623,097,827 |
| `.claude-main` | broodierchip@gmail.com | 39,996,980,503 | 2026-05-26 → 2026-08-25 | 12,834,169,588 |
| `.claude` | acct-17de7ff8 | 6,946,344,675 | 2026-05-26 → 2026-07-30 | 12,664,864,821 |
| `.claude` | codehunterextreme@gmail.com | 6,946,344,675 | 2026-05-26 → 2026-07-30 | 5,321,298,979 |
| `.claude-it` | acct-bc7f238c | 571,753,755 | 2026-06-10 → 2026-07-19 | 738,375,002 |
| `.claude-it` | alexander.sorrell.it@gmail.com | 571,753,755 | 2026-06-10 → 2026-07-19 | 322,280,256 |

**Do not subtract these columns.** The two cover different periods: the counter runs from the first session to its own `lastComputedDate` and then stops, while the transcripts hold whatever has not expired, which includes days after that date. Neither contains the other — each holds usage the other lacks — so their difference is not a quantity of anything.

An earlier version of this report published exactly that subtraction as "tokens the transcripts can no longer see". It was arithmetic on two incomparable windows, and it is removed rather than reworded.

The overlap cannot be resolved either: the cache's only per-day breakdown is input+output, excluding cache reads, which are around 95% of the volume. What the comparison honestly shows is that far more usage happened than the surviving transcripts record, with both figures and both windows stated so a reader can see the shape of the gap without being handed a false number for it.

---

## Sessions that no longer have a transcript

**251 Claude Code sessions have existed across the scanned machines. 165 of them — 66% — no longer have a transcript on disk.**

Claude Code deletes transcripts older than `cleanupPeriodDays`, but it does not delete `history.jsonl`. That file records one entry per prompt with a session id, a timestamp and a project, and it reaches much further back than the transcripts do:

```
ledger reaches back to     2026-02-11
oldest surviving transcript 2026-05-26
```

It carries **no token counts**, so a lost session's cost is gone for good. What survives is proof the session happened, when, and in which project — which turns an unquantified loss into a number. The ledger is committed with each scan, so it accumulates permanently even as its own source expires. Prompt text is deliberately not stored.

| Account | Sessions ever | Transcript gone | Span |
|---|---:|---:|---|
| broodierchip@gmail.com | 179 | 125 | 2026-05-26 → 2026-08-26 |
| codehunterextreme@gmail.com | 61 | 36 | 2026-02-11 → 2026-08-14 |
| alexander.sorrell.it@gmail.com | 11 | 4 | 2026-06-10 → 2026-08-26 |

---

## Cross-tabs

_scans taken 2026-08-27 05:06:36 .. 2026-08-27 15:19:30_

### Computer x company

| Computer | Anthropic | Total |
|---|---|---|
| MacBookAir | 42.04B | **42,036,497,160** |
| MacBook Air M1 (Darwin ARM64) | 18.49B | **18,487,763,737** |
| **All** | **60.52B** | **60,524,260,897** |

### Computer x CLI

| Computer | claude | gemini | codex | copilot | antigravity | bob | grok | lmstudio | kilocode | clawspring | copilot-chat | claude-orphans | Total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MacBook Air M1 (Darwin ARM64) | 19.66B | 995.36M | 1.63B | 572.45M | 1.08B | 272.62M | 100.22M | 53.16K | — | — | — | — | **24,313,592,846** |
| MacBookAir | 42.04B | 995.36M | — | 572.45M | 60.48M | 2.55M | 100.22M | — | — | — | — | — | **43,767,560,670** |
| **All** | **61.70B** | **1.99B** | **1.63B** | **1.14B** | **1.14B** | **275.17M** | **200.44M** | **53.16K** | **0** | **0** | **0** | **0** | **68,081,153,516** |

---

## Sessions

3,650 sessions · 3,998h 59m active · 68,081,153,516 tokens

Gaps over 15 minutes are treated as idle and dropped. First-to-last timestamp instead produced a *436-hour day* on this data.

**The 15 minutes is a judgement call.** On the 3,645 session(s) measured both ways, counting only gaps under one minute gives **3,510h 16m** against **3,998h 59m**. The 488h 44m between is where reading output and walking away look identical. Read it as a range. The other 5 predate this and are counted only at fifteen minutes.

### Twenty longest

| When | Computer | CLI | Active | Tokens | Turns | Model |
|---|---|---|---:|---:|---:|---|
| 2026-08-08 | MacBookAir | claude | 289h 41m | 678,064,467 | 1,389 | `claude-opus-5` |
| 2026-08-08 | MacBookAir | claude | 257h 18m | 6,126,048,910 | 11,510 | `claude-opus-5` |
| 2026-07-05 | MacBookAir | claude | 193h 13m | 3,897,768,211 | 7,872 | `claude-opus-4-8` |
| 2026-07-20 | MacBookAir | claude | 181h 36m | 373,158,385 | 970 | `claude-opus-4-8` |
| 2026-07-20 | MacBookAir | claude | 164h 50m | 3,091,416,443 | 5,998 | `claude-opus-4-8` |
| 2026-07-07 | MacBookAir | claude | 127h 15m | 260,568,103 | 834 | `claude-fable-5` |
| 2026-07-29 | MacBookAir | claude | 121h 45m | 945,786,775 | 2,107 | `claude-opus-5` |
| 2026-07-22 | MacBookAir | claude | 107h 43m | 354,809,933 | 860 | `claude-opus-4-8` |
| 2026-07-15 | MacBookAir | claude | 105h 10m | 2,784,385,725 | 5,328 | `claude-opus-4-8` |
| 2026-07-29 | MacBookAir | claude | 103h 54m | 1,931,515,538 | 3,844 | `claude-opus-5` |
| 2026-07-07 | MacBookAir | claude | 96h 22m | 83,049,743 | 396 | `claude-opus-4-8` |
| 2026-08-08 | MacBook Air M1 (Darwin ARM64) | claude | 85h 42m | 3,304,664,216 | 10,941 | `claude-opus-5` |
| 2026-08-11 | MacBookAir | claude | 74h 01m | 42,486,049 | 299 | `claude-opus-5` |
| 2026-08-18 | MacBookAir | claude | 72h 42m | 2,332,626,915 | 4,337 | `claude-opus-5` |
| 2026-08-01 | MacBookAir | claude | 71h 34m | 2,051,373,637 | 3,691 | `claude-opus-5` |
| 2026-07-05 | MacBookAir | claude | 68h 58m | 235,689,476 | 950 | `claude-fable-5` |
| 2026-08-04 | MacBookAir | claude | 67h 25m | 1,477,175,634 | 2,634 | `claude-opus-5` |
| 2026-07-05 | MacBook Air M1 (Darwin ARM64) | claude | 60h 53m | 1,543,066,446 | 3,291 | `claude-opus-4-8` |
| 2026-06-18 | MacBookAir | claude | 52h 26m | 571,145,679 | 2,309 | `claude-sonnet-4-6` |
| 2026-07-26 | MacBookAir | claude | 51h 26m | 1,275,406,853 | 2,495 | `claude-opus-5` |

### Twenty heaviest

| When | Computer | CLI | Active | Tokens | Turns | Model |
|---|---|---|---:|---:|---:|---|
| 2026-08-08 | MacBookAir | claude | 257h 18m | 6,126,048,910 | 11,510 | `claude-opus-5` |
| 2026-07-05 | MacBookAir | claude | 193h 13m | 3,897,768,211 | 7,872 | `claude-opus-4-8` |
| 2026-08-08 | MacBook Air M1 (Darwin ARM64) | claude | 85h 42m | 3,304,664,216 | 10,941 | `claude-opus-5` |
| 2026-07-20 | MacBookAir | claude | 164h 50m | 3,091,416,443 | 5,998 | `claude-opus-4-8` |
| 2026-07-29 | MacBook Air M1 (Darwin ARM64) | claude | 39h 32m | 2,799,957,050 | 18,198 | `claude-opus-5` |
| 2026-07-15 | MacBookAir | claude | 105h 10m | 2,784,385,725 | 5,328 | `claude-opus-4-8` |
| 2026-08-18 | MacBookAir | claude | 72h 42m | 2,332,626,915 | 4,337 | `claude-opus-5` |
| 2026-08-01 | MacBookAir | claude | 71h 34m | 2,051,373,637 | 3,691 | `claude-opus-5` |
| 2026-07-29 | MacBookAir | claude | 103h 54m | 1,931,515,538 | 3,844 | `claude-opus-5` |
| 2026-07-05 | MacBook Air M1 (Darwin ARM64) | claude | 60h 53m | 1,543,066,446 | 3,291 | `claude-opus-4-8` |
| 2026-08-04 | MacBookAir | claude | 67h 25m | 1,477,175,634 | 2,634 | `claude-opus-5` |
| 2026-07-26 | MacBookAir | claude | 47h 30m | 1,310,743,646 | 2,218 | `claude-opus-5` |
| 2026-07-26 | MacBookAir | claude | 51h 26m | 1,275,406,853 | 2,495 | `claude-opus-5` |
| 2026-07-20 | MacBook Air M1 (Darwin ARM64) | claude | 48h 46m | 1,180,176,108 | 2,450 | `claude-opus-4-8` |
| 2026-08-18 | MacBook Air M1 (Darwin ARM64) | claude | 27h 21m | 1,101,155,152 | 2,920 | `claude-opus-5` |
| 2026-07-15 | MacBook Air M1 (Darwin ARM64) | claude | 37h 57m | 1,057,823,005 | 2,269 | `claude-opus-4-8` |
| 2026-08-01 | MacBook Air M1 (Darwin ARM64) | claude | 28h 08m | 957,178,898 | 1,739 | `claude-opus-5` |
| 2026-07-29 | MacBookAir | claude | 121h 45m | 945,786,775 | 2,107 | `claude-opus-5` |
| ? | MacBookAir | gemini | 7h 04m | 927,740,104 | 3,331 | `gemini-3-flash-preview` |
| 2026-05-20 | MacBook Air M1 (Darwin ARM64) | gemini | 7h 04m | 927,740,104 | 3,331 | `gemini-3-flash-preview` |

### Busiest days

| Day | Tokens | Active |
|---|---:|---:|
| 2026-08-08 | 10,834,207,606 | 659h 59m |
| 2026-07-29 | 6,480,239,901 | 283h 31m |
| 2026-07-05 | 5,826,090,897 | 355h 49m |
| 2026-07-20 | 5,283,953,028 | 452h 04m |
| 2026-08-01 | 4,141,687,003 | 153h 48m |
| 2026-07-26 | 3,956,423,142 | 133h 47m |
| 2026-07-15 | 3,843,217,379 | 143h 26m |
| 2026-08-18 | 3,454,219,674 | 101h 13m |
| 2026-08-04 | 2,199,913,814 | 146h 14m |
| 2026-08-02 | 2,163,801,252 | 48h 05m |
| 2026-08-06 | 2,083,395,750 | 102h 26m |
| 2026-07-22 | 1,124,090,630 | 143h 36m |
| 2026-07-23 | 1,113,820,894 | 12h 48m |
| 2026-07-31 | 1,075,185,657 | 36h 14m |
| 2026-05-20 | 957,572,568 | 11h 08m |

Session-hours can exceed 24 in a day: parallel agents overlap, and that overlap is real work, so it is summed rather than clamped.

