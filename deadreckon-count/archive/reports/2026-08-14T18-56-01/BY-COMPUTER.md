# By computer

_Every machine, and everything on it_

_Generated 2026-08-14T18:56:00-05:00 by `stats_page.py`. Do not edit by hand._

**15,251,673,339** tokens of Claude Code across 1 scanned computer(s) · **19,817,745,559** across every CLI on the 1 that ran `sessions.py`.

Those two are not added: the second contains the first. See [BY-COMPUTER.md](BY-COMPUTER.md) for the reconciliation.

Reports: [computers](BY-COMPUTER.md) · [accounts](BY-ACCOUNT.md) · [companies](BY-COMPANY.md) · [how it works](README.md)

---

## Totals

_scans taken 2026-08-14 18:52:17_

Each row carries the moment that computer was scanned. Machines are scanned independently, so a total is a snapshot of several different instants, never one.

| Computer | Folder | Accounts | Tokens | Share | Scanned |
|---|---|---:|---:|---:|---|
| **MacBook Air M1** | `macbook-air-m1/` | 3 | 15,251,673,339 | 100.0% | 2026-08-14 18:52:17 |
| **All** | | | **15,251,673,339** | 100% | |

### The two scopes, reconciled

```
Claude Code, per account (totals.json)  :   15,251,673,339
Claude Code, per session (sessions.json):   16,426,489,244
difference                              :   -1,174,815,905
non-Claude-Code CLIs, additional        :    3,391,256,315
```

**These should agree and differ by 1,174,815,905.** The usual innocent cause is a session still being written during the scan; anything larger is a bug worth finding before quoting these.

---

## MacBook Air M1

scanned **2026-08-14 18:52:17** · sessions 2026-08-14 18:52:37

`macbook-air-m1/` · 3 account(s) · 61 sessions · 65,595 turns · **15,251,673,339 tokens** (100.0% of all Claude Code)

> ⚠️ **copilot-chat is installed here and read 0 sessions** — its usage is missing from every total below. These figures are a floor for this machine, not a total. `update.py` on it settles it.

### Accounts on this computer

| Account | Tokens | Share of machine |
|---|---:|---:|
| broodierchip@gmail.com | 9,686,425,191 | 63.5% |
| codehunterextreme@gmail.com | 5,321,298,979 | 34.9% |
| alexander.sorrell.it@gmail.com | 243,949,169 | 1.6% |

### Companies on this computer

| Company | Tokens | Share |
|---|---:|---:|
| Anthropic | 15,251,673,339 | 100.0% |

### CLIs on this computer

| CLI | Sessions | Active | Tokens |
|---|---:|---:|---:|
| claude | 77 | 494h 11m | 16,426,489,244 |
| codex | 125 | 29h 43m | 1,633,604,881 |
| gemini | 4 | 9h 38m | 995,360,683 |
| copilot | 36 | 79h 46m | 497,696,783 |
| antigravity | 35 | 13h 38m | 135,111,522 |
| grok | 8 | 10h 09m | 100,222,322 |
| bob | 1 | 0m | 29,206,965 |
| lmstudio | 3 | 0m | 53,159 |

### Installed here — 10 tool(s)

Presence is separate from usage: a tool with no token column is installed and not counted, which is different from unused.

| Tool | Kind | Counted | Sessions | Tokens | Usage |
|---|---|---|---:|---:|---|
| Claude Code | cli | yes | 58 | 15,252,064,267 | 2026-05-26 → 2026-08-14 |
| OpenAI Codex CLI | cli | yes | 125 | 1,633,604,881 | 2026-07-13 → 2026-08-05 |
| Google Gemini CLI | cli | yes | 4 | 995,360,683 | 2026-05-20 → 2026-05-23 |
| GitHub Copilot CLI | cli | yes | 36 | 497,696,783 | 2026-03-03 → 2026-06-10 |
| Antigravity CLI | cli | yes | 35 | 135,111,522 | 2026-05-28 → 2026-07-31 |
| xAI Grok CLI | cli | yes | 8 | 100,222,322 | 2026-07-21 → 2026-08-12 |
| Continue | agent | no — usage not located on disk | — | — | last touched 2026-06-11 |
| VS Code Insiders | editor | no — editor — hosts agents, spends no tokens itself | — | — | 10 launches, 2 workspaces, 7 day(s): 2025-10-16 → 2026-06-14 |
| Ollama | runtime | no — local runtime — models run on this machine, nothing is billed | — | — | last touched 2026-06-01 |
| LM Studio | runtime | no — local runtime — models run on this machine, nothing is billed | — | — | last touched 2026-08-08 |

---

## Tokens nobody was billed for

**53,159 tokens** across 3 sessions ran on this hardware. They are counted in every total in these reports, because a token is a token regardless of who pays for it. What differs is the invoice, and there isn't one.

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

Every figure elsewhere includes these. To read spend rather than volume, subtract them: 19,817,692,400 of the 19,817,745,559 total was billed to someone.

---

## The floor: the most defensible figure per machine

**49,353,411,503 tokens across 1 scanned computer(s).**

_scans taken 2026-08-14 18:52:17_

Two sources describe Claude Code usage and neither contains the other. `stats-cache.json` accumulates from a profile's first session to its own `lastComputedDate` and stops; the transcripts hold whatever has not been deleted, which includes days after that date.

Subtracting them is meaningless. **Concatenating them is exact** — the counter owns everything up to its end date, the transcripts own the days strictly after it, and no token falls in both. Profiles with no counter, and every non-Claude tool, contribute only their surviving records, because nothing else on disk remembers usage once its records are gone.

| Computer | Claude Code | Other tools | Floor | Measured on disk |
|---|---:|---:|---:|---:|
| MacBook Air M1 | 45,962,155,188 | 3,391,256,315 | **49,353,411,503** | 19,817,745,559 |
| **All** | | | **49,353,411,503** | |

It is a floor and not a total for three reasons, all measured rather than assumed: profiles without a counter lose anything pruned before the scan; the counter's own window has gaps where transcripts were deleted before it froze; and no non-Claude tool keeps a counter at all.

<details><summary>MacBook Air M1 — how its floor is built</summary>

| Account | Counter | Counter ends | Transcripts after | Floor |
|---|---:|---|---:|---:|
| broodierchip@gmail.com | 28,833,190,364 | 2026-07-21 | 7,203,914,892 | 36,037,105,256 |
| codehunterextreme@gmail.com | 6,946,344,675 | 2026-07-30 | 2,406,951,502 | 9,353,296,177 |
| alexander.sorrell.it@gmail.com | 571,753,755 | 2026-07-19 | 0 | 571,753,755 |

</details>

---

## Claude Code's own counter, versus the transcripts

Every profile keeps `stats-cache.json`. It is not a transcript, so the cleanup sweep never touches it, and it accumulates from that profile's first session — including sessions whose transcripts were deleted months ago.

| Profile | Account | Own counter | Counter covers | From transcripts |
|---|---|---:|---|---:|
| `.claude-main` | broodierchip@gmail.com | 28,833,190,364 | 2026-05-26 → 2026-07-21 | 9,686,425,191 |
| `.claude` | codehunterextreme@gmail.com | 6,946,344,675 | 2026-05-26 → 2026-07-30 | 5,321,298,979 |
| `.claude-it` | alexander.sorrell.it@gmail.com | 571,753,755 | 2026-06-10 → 2026-07-19 | 243,949,169 |

**Do not subtract these columns.** The two cover different periods: the counter runs from the first session to its own `lastComputedDate` and then stops, while the transcripts hold whatever has not expired, which includes days after that date. Neither contains the other — each holds usage the other lacks — so their difference is not a quantity of anything.

An earlier version of this report published exactly that subtraction as "tokens the transcripts can no longer see". It was arithmetic on two incomparable windows, and it is removed rather than reworded.

The overlap cannot be resolved either: the cache's only per-day breakdown is input+output, excluding cache reads, which are around 95% of the volume. What the comparison honestly shows is that far more usage happened than the surviving transcripts record, with both figures and both windows stated so a reader can see the shape of the gap without being handed a false number for it.

---

## Sessions that no longer have a transcript

**241 Claude Code sessions have existed across the scanned machines. 168 of them — 70% — no longer have a transcript on disk.**

Claude Code deletes transcripts older than `cleanupPeriodDays`, but it does not delete `history.jsonl`. That file records one entry per prompt with a session id, a timestamp and a project, and it reaches much further back than the transcripts do:

```
ledger reaches back to     2026-02-11
oldest surviving transcript 2026-05-26
```

It carries **no token counts**, so a lost session's cost is gone for good. What survives is proof the session happened, when, and in which project — which turns an unquantified loss into a number. The ledger is committed with each scan, so it accumulates permanently even as its own source expires. Prompt text is deliberately not stored.

| Account | Sessions ever | Transcript gone | Span |
|---|---:|---:|---|
| broodierchip@gmail.com | 174 | 130 | 2026-05-26 → 2026-08-14 |
| codehunterextreme@gmail.com | 61 | 36 | 2026-02-11 → 2026-08-14 |
| alexander.sorrell.it@gmail.com | 6 | 2 | 2026-06-10 → 2026-08-06 |

---

## Cross-tabs

_scans taken 2026-08-14 18:52:17_

### Computer x company

| Computer | Anthropic | Total |
|---|---|---|
| MacBook Air M1 | 15.25B | **15,251,673,339** |
| **All** | **15.25B** | **15,251,673,339** |

### Computer x CLI

| Computer | claude | codex | gemini | copilot | antigravity | grok | bob | lmstudio | kilocode | clawspring | copilot-chat | claude-orphans | Total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MacBook Air M1 | 16.43B | 1.63B | 995.36M | 497.70M | 135.11M | 100.22M | 29.21M | 53.16K | — | — | — | — | **19,817,745,559** |
| **All** | **16.43B** | **1.63B** | **995.36M** | **497.70M** | **135.11M** | **100.22M** | **29.21M** | **53.16K** | **0** | **0** | **0** | **0** | **19,817,745,559** |

---

## Sessions

289 sessions · 637h 06m active · 19,817,745,559 tokens

Gaps over 15 minutes are treated as idle and dropped. First-to-last timestamp instead produced a *436-hour day* on this data.

**The 15 minutes is a judgement call.** On the 288 session(s) measured both ways, counting only gaps under one minute gives **277h 34m** against **637h 06m**. The 359h 32m between is where reading output and walking away look identical. Read it as a range. The other 1 predate this and are counted only at fifteen minutes.

### Twenty longest

| When | Computer | CLI | Active | Tokens | Turns | Model |
|---|---|---|---:|---:|---:|---|
| 2026-07-05 | MacBook Air M1 | claude | 60h 53m | 1,542,903,336 | 3,290 | `claude-opus-4-8` |
| 2026-07-20 | MacBook Air M1 | claude | 48h 46m | 1,179,567,024 | 2,449 | `claude-opus-4-8` |
| 2026-08-08 | MacBook Air M1 | claude | 46h 23m | 1,701,179,327 | 6,633 | `claude-opus-5` |
| 2026-07-29 | MacBook Air M1 | claude | 39h 32m | 2,798,848,113 | 18,192 | `claude-opus-5` |
| 2026-07-15 | MacBook Air M1 | claude | 37h 57m | 1,057,003,622 | 2,268 | `claude-opus-4-8` |
| 2026-03-03 | MacBook Air M1 | copilot | 29h 55m | 1,404,767 | 11,231 | `unknown` |
| 2026-08-01 | MacBook Air M1 | claude | 28h 08m | 956,526,882 | 1,738 | `claude-opus-5` |
| 2026-08-04 | MacBook Air M1 | claude | 25h 42m | 688,426,156 | 1,261 | `claude-opus-5` |
| 2026-06-18 | MacBook Air M1 | claude | 19h 08m | 243,949,169 | 1,121 | `claude-sonnet-4-6` |
| 2026-07-26 | MacBook Air M1 | claude | 16h 49m | 659,569,404 | 1,561 | `claude-opus-5` |
| 2026-07-26 | MacBook Air M1 | claude | 15h 08m | 608,240,843 | 2,009 | `claude-opus-5` |
| 2026-07-07 | MacBook Air M1 | claude | 14h 01m | 273,759,955 | 3,977 | `claude-fable-5` |
| 2026-07-29 | MacBook Air M1 | claude | 13h 49m | 681,763,777 | 4,129 | `claude-opus-5` |
| 2026-07-22 | MacBook Air M1 | claude | 11h 29m | 338,721,757 | 3,642 | `claude-opus-4-8` |
| 2026-08-06 | MacBook Air M1 | claude | 11h 11m | 291,931,582 | 1,779 | `claude-opus-5` |
| 2026-05-21 | MacBook Air M1 | copilot | 10h 50m | 171,418,535 | 1,178 | `claude-sonnet-4.6` |
| 2026-07-14 | MacBook Air M1 | claude | 10h 08m | 218,545,136 | 608 | `claude-opus-4-8` |
| 2026-07-10 | MacBook Air M1 | claude | 9h 10m | 292,977,500 | 2,661 | `claude-opus-4-8` |
| 2026-07-20 | MacBook Air M1 | claude | 7h 59m | 160,767,700 | 436 | `claude-opus-4-8` |
| 2026-07-20 | MacBook Air M1 | claude | 7h 23m | 121,994,396 | 854 | `claude-opus-4-8` |

### Twenty heaviest

| When | Computer | CLI | Active | Tokens | Turns | Model |
|---|---|---|---:|---:|---:|---|
| 2026-07-29 | MacBook Air M1 | claude | 39h 32m | 2,798,848,113 | 18,192 | `claude-opus-5` |
| 2026-08-08 | MacBook Air M1 | claude | 46h 23m | 1,701,179,327 | 6,633 | `claude-opus-5` |
| 2026-07-05 | MacBook Air M1 | claude | 60h 53m | 1,542,903,336 | 3,290 | `claude-opus-4-8` |
| 2026-07-20 | MacBook Air M1 | claude | 48h 46m | 1,179,567,024 | 2,449 | `claude-opus-4-8` |
| 2026-07-15 | MacBook Air M1 | claude | 37h 57m | 1,057,003,622 | 2,268 | `claude-opus-4-8` |
| 2026-08-01 | MacBook Air M1 | claude | 28h 08m | 956,526,882 | 1,738 | `claude-opus-5` |
| 2026-05-20 | MacBook Air M1 | gemini | 7h 04m | 927,740,104 | 3,331 | `gemini-3-flash-preview` |
| 2026-08-04 | MacBook Air M1 | claude | 25h 42m | 688,426,156 | 1,261 | `claude-opus-5` |
| 2026-07-29 | MacBook Air M1 | claude | 13h 49m | 681,763,777 | 4,129 | `claude-opus-5` |
| 2026-07-26 | MacBook Air M1 | claude | 16h 49m | 659,569,404 | 1,561 | `claude-opus-5` |
| 2026-07-26 | MacBook Air M1 | claude | 15h 08m | 608,240,843 | 2,009 | `claude-opus-5` |
| 2026-07-22 | MacBook Air M1 | claude | 11h 29m | 338,721,757 | 3,642 | `claude-opus-4-8` |
| ? | MacBook Air M1 | claude | 0m | 317,059,214 | 0 | `claude-opus-4-8[1m]` |
| ? | MacBook Air M1 | claude | 0m | 306,861,442 | 0 | `claude-opus-4-8` |
| 2026-07-10 | MacBook Air M1 | claude | 9h 10m | 292,977,500 | 2,661 | `claude-opus-4-8` |
| 2026-08-06 | MacBook Air M1 | claude | 11h 11m | 291,931,582 | 1,779 | `claude-opus-5` |
| 2026-07-07 | MacBook Air M1 | claude | 14h 01m | 273,759,955 | 3,977 | `claude-fable-5` |
| 2026-06-18 | MacBook Air M1 | claude | 19h 08m | 243,949,169 | 1,121 | `claude-sonnet-4-6` |
| 2026-07-14 | MacBook Air M1 | claude | 10h 08m | 218,545,136 | 608 | `claude-opus-4-8` |
| 2026-08-06 | MacBook Air M1 | claude | 6h 17m | 205,997,162 | 652 | `claude-opus-5` |

### Busiest days

| Day | Tokens | Active |
|---|---:|---:|
| 2026-07-29 | 3,480,611,890 | 53h 22m |
| 2026-08-08 | 1,759,068,438 | 49h 37m |
| 2026-07-05 | 1,679,091,522 | 67h 11m |
| 2026-07-20 | 1,463,497,565 | 64h 32m |
| 2026-07-26 | 1,267,810,247 | 31h 56m |
| 2026-07-23 | 1,082,400,128 | 9h 34m |
| 2026-07-15 | 1,057,928,415 | 38h 16m |
| 2026-08-01 | 1,037,549,559 | 31h 14m |
| 2026-05-20 | 957,572,568 | 11h 08m |
| 2026-08-06 | 792,065,731 | 26h 49m |
| 2026-08-04 | 701,353,328 | 28h 26m |
| 2026-07-22 | 537,654,023 | 15h 51m |
| 2026-07-13 | 364,329,564 | 16h 23m |
| 2026-07-07 | 312,420,900 | 15h 58m |
| 2026-07-10 | 299,785,274 | 9h 42m |

Session-hours can exceed 24 in a day: parallel agents overlap, and that overlap is real work, so it is summed rather than clamped.

