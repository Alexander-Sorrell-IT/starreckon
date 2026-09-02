# By computer

_Every machine, and everything on it_

_Generated 2026-09-01T06:49:42-05:00 by `stats_page.py`. Do not edit by hand._

**29,583,611,349** tokens of Claude Code across 2 scanned computer(s) · **40,912,910,876** across every CLI on the 2 that ran `sessions.py`.

Those two are not added: the second contains the first. See [BY-COMPUTER.md](BY-COMPUTER.md) for the reconciliation.

Reports: [computers](BY-COMPUTER.md) · [accounts](BY-ACCOUNT.md) · [companies](BY-COMPANY.md) · [how it works](README.md)

---

## Totals

_scans taken 2026-08-19 21:24:07 .. 2026-09-01 06:48:33_

Each row carries the moment that computer was scanned. Machines are scanned independently, so a total is a snapshot of several different instants, never one.

| Computer | Folder | Accounts | Tokens | Share | Scanned |
|---|---|---:|---:|---:|---|
| **MacBook Air M1** | `macbook-air-m1/` | 8 | 18,032,194,745 | 61.0% | 2026-08-19 21:24:07 |
| **HP Laptop Linux** | `hp-laptop-linux/` | 15 | 11,551,416,604 | 39.0% | 2026-09-01 06:48:33 |
| **All** | | | **29,583,611,349** | 100% | |

### The two scopes, reconciled

```
Claude Code, per account (totals.json)  :   29,583,611,349
Claude Code, per session (sessions.json):   34,933,038,613
difference                              :   -5,349,427,264
non-Claude-Code CLIs, additional        :    5,979,872,263
```

**These should agree and differ by 5,349,427,264.** The usual innocent cause is a session still being written during the scan; anything larger is a bug worth finding before quoting these.

---

## MacBook Air M1

scanned **2026-08-19 21:24:07** · sessions 2026-08-19 21:29:02

`macbook-air-m1/` · 8 account(s) · 4,490 sessions · 73,107 turns · **18,032,194,745 tokens** (61.0% of all Claude Code)

> ⚠️ scanner `103c20d12f3a`, fleet is on `1db5dde1cc04` · **copilot-chat is installed here and read 0 sessions** — its usage is missing from every total below. These figures are a floor for this machine, not a total. `update.py` on it settles it.

### Accounts on this computer

| Account | Tokens | Share of machine |
|---|---:|---:|
| broodierchip@gmail.com | 12,456,931,683 | 69.1% |
| codehunterextreme@gmail.com | 5,321,298,979 | 29.5% |
| alexander.sorrell.it@gmail.com | 243,949,169 | 1.4% |
| unknown (Documents) | 10,014,914 | 0.1% |

### Companies on this computer

| Company | Tokens | Share |
|---|---:|---:|
| Anthropic | 18,032,194,745 | 100.0% |

### CLIs on this computer

| CLI | Sessions | Active | Tokens |
|---|---:|---:|---:|
| claude | 86 | 563h 31m | 19,209,289,976 |
| codex | 125 | 29h 43m | 1,633,604,881 |
| gemini | 4 | 9h 38m | 995,360,683 |
| copilot | 36 | 79h 46m | 497,696,783 |
| bob | 5 | 0m | 272,617,335 |
| antigravity | 35 | 13h 38m | 135,111,522 |
| grok | 8 | 10h 09m | 100,222,322 |
| lmstudio | 3 | 0m | 53,159 |

### Installed here — 10 tool(s)

Presence is separate from usage: a tool with no token column is installed and not counted, which is different from unused.

| Tool | Kind | Counted | Sessions | Tokens | Usage |
|---|---|---|---:|---:|---|
| Claude Code | cli | yes | 67 | 18,034,864,999 | 2026-05-26 → 2026-08-20 |
| OpenAI Codex CLI | cli | yes | 125 | 1,633,604,881 | 2026-07-13 → 2026-08-05 |
| Google Gemini CLI | cli | yes | 4 | 995,360,683 | 2026-05-20 → 2026-05-23 |
| GitHub Copilot CLI | cli | yes | 36 | 497,696,783 | 2026-03-03 → 2026-06-10 |
| Antigravity CLI | cli | yes | 35 | 135,111,522 | 2026-05-28 → 2026-07-31 |
| xAI Grok CLI | cli | yes | 8 | 100,222,322 | 2026-07-21 → 2026-08-15 |
| Continue | agent | no — usage not located on disk | — | — | last touched 2026-06-11 |
| VS Code Insiders | editor | no — editor — hosts agents, spends no tokens itself | — | — | 10 launches, 2 workspaces, 7 day(s): 2025-10-16 → 2026-06-14 |
| Ollama | runtime | no — local runtime — models run on this machine, nothing is billed | — | — | last touched 2026-06-01 |
| LM Studio | runtime | no — local runtime — models run on this machine, nothing is billed | — | — | last touched 2026-08-08 |

---

## HP Laptop Linux

scanned **2026-09-01 06:48:33** · sessions 2026-09-01 06:49:36

`hp-laptop-linux/` · 15 account(s) · 422 sessions · 62,480 turns · **11,551,416,604 tokens** (39.0% of all Claude Code)

### Accounts on this computer

| Account | Tokens | Share of machine |
|---|---:|---:|
| codehunterextreme@gmail.com | 8,062,476,061 | 69.8% |
| broodierchip@gmail.com | 2,744,450,437 | 23.8% |
| DeepSeek backend (~/.my-claude) | 520,497,793 | 4.5% |
| alexander.sorrell.it@gmail.com | 223,851,103 | 1.9% |
| API key (org 15a93e14-aabb-4293-8228-8c56a803d972) | 141,210 | 0.0% |

### Companies on this computer

| Company | Tokens | Share |
|---|---:|---:|
| Anthropic | 11,016,745,451 | 95.4% |
| DeepSeek | 534,671,153 | 4.6% |

### CLIs on this computer

| CLI | Sessions | Active | Tokens |
|---|---:|---:|---:|
| claude | 228 | 358h 02m | 15,723,748,637 |
| gemini | 46 | 70h 18m | 1,468,362,549 |
| copilot | 31 | 54h 41m | 295,831,967 |
| clawspring | 20 | 0m | 258,503,636 |
| bob | 59 | 8h 53m | 229,043,592 |
| antigravity | 27 | 7h 25m | 83,601,215 |
| kilocode | 4 | 1h 19m | 7,074,501 |
| codex | 5 | 23m | 1,454,074 |
| copilot-chat | 11 | 0m | 1,214,160 |
| lmstudio | 8 | 0m | 119,884 |

### Installed here — 16 tool(s)

Presence is separate from usage: a tool with no token column is installed and not counted, which is different from unused.

| Tool | Kind | Counted | Sessions | Tokens | Usage |
|---|---|---|---:|---:|---|
| Claude Code | cli | yes | 150 | 11,551,416,604 | 2026-05-04 → 2026-09-01 |
| Google Gemini CLI | cli | yes | 46 | 1,468,362,549 | 2025-12-27 → 2026-07-02 |
| GitHub Copilot CLI | cli | yes | 31 | 295,831,967 | 2026-02-24 → 2026-05-28 |
| Antigravity CLI | cli | yes | 27 | 83,601,215 | 2026-05-29 → 2026-08-30 |
| OpenAI Codex CLI | cli | yes | 5 | 1,454,074 | 2025-12-21 → 2026-01-08 |
| xAI Grok CLI | cli | yes | 0 | 0 | ? → ? |
| Jules CLI | cli | no — cloud agent — work runs on Google's servers, no local token record | — | — | last touched 2025-12-29 |
| grok-cli (@vibe-kit) | cli | no — records no usage of any kind | — | — | last touched 2026-05-22 |
| Kilo Code (VS Code) | agent | yes | 2 | 7,025,122 | 2025-07-17 → 2025-07-17 |
| Kilo Code (Insiders) | agent | yes | 2 | 49,379 | 2026-01-02 → 2026-01-13 |
| Aider | agent | no — usage not located on disk | — | — | last touched 2026-08-24 |
| VS Code | editor | no — editor — hosts agents, spends no tokens itself | — | — | 14 launches, 11 workspaces, 1 day(s): 2026-01-19 → 2026-01-19 |
| VS Code Insiders | editor | no — editor — hosts agents, spends no tokens itself | — | — | 10 launches, 27 workspaces, 6 day(s): 2026-01-08 → 2026-03-06 |
| Zed | editor | no — editor — hosts agents, spends no tokens itself | — | — | installed |
| Ollama | runtime | no — local runtime — models run on this machine, nothing is billed | — | — | last touched 2026-05-21 |
| LM Studio | runtime | no — local runtime — models run on this machine, nothing is billed | — | — | last touched 2025-07-14 |

---

## Tokens nobody was billed for

**173,043 tokens** across 11 sessions ran on this hardware. They are counted in every total in these reports, because a token is a token regardless of who pays for it. What differs is the invoice, and there isn't one.

That is a third dimension, independent of the other two:

| Dimension | Question | Example |
|---|---|---|
| `cli` | which tool did you pay for | Copilot running a Claude model is GitHub spend |
| `provider` | whose model actually ran | …and Anthropic service |
| `billed` | did money change hands | Ollama running llama is neither |

| CLI | Model | Sessions | Tokens |
|---|---|---:|---:|
| lmstudio | `Mixtral-8x7B-Instruct-v0.1.Q6_K.gguf` | 5 | 116,185 |
| lmstudio | `Wizard-Vicuna-7B-Uncensored.Q4_K_S.gguf` | 2 | 37,497 |
| lmstudio | `nomic-ai-gpt4all-falcon-Q4_K_S.gguf` | 1 | 15,662 |
| lmstudio | `deepseek-coder-6.7b-instruct.Q6_K.gguf` | 1 | 3,530 |
| lmstudio | `unknown` | 1 | 110 |
| lmstudio | `Llama-3-13B-Instruct-v0.1.Q4_K_S.gguf` | 1 | 59 |

Every figure elsewhere includes these. To read spend rather than volume, subtract them: 40,912,737,833 of the 40,912,910,876 total was billed to someone.

---

## The floor: the most defensible figure per machine

**90,912,228,903 tokens across 2 scanned computer(s).**

_scans taken 2026-08-19 21:24:07 .. 2026-09-01 06:48:33_

Two sources describe Claude Code usage and neither contains the other. `stats-cache.json` accumulates from a profile's first session to its own `lastComputedDate` and stops; the transcripts hold whatever has not been deleted, which includes days after that date.

Subtracting them is meaningless. **Concatenating them is exact** — the counter owns everything up to its end date, the transcripts own the days strictly after it, and no token falls in both. Profiles with no counter, and every non-Claude tool, contribute only their surviving records, because nothing else on disk remembers usage once its records are gone.

| Computer | Claude Code | Other tools | Floor | Measured on disk |
|---|---:|---:|---:|---:|
| MacBook Air M1 | 48,742,676,594 | 3,634,666,685 | **52,377,343,279** | 22,843,956,661 |
| HP Laptop Linux | 36,189,680,046 | 2,345,205,578 | **38,534,885,624** | 18,068,954,215 |
| **All** | | | **90,912,228,903** | |

It is a floor and not a total for three reasons, all measured rather than assumed: profiles without a counter lose anything pruned before the scan; the counter's own window has gaps where transcripts were deleted before it froze; and no non-Claude tool keeps a counter at all.

<details><summary>MacBook Air M1 — how its floor is built</summary>

| Account | Counter | Counter ends | Transcripts after | Floor |
|---|---:|---|---:|---:|
| broodierchip@gmail.com | 28,833,190,364 | 2026-07-21 | 9,974,421,384 | 38,807,611,748 |
| codehunterextreme@gmail.com | 6,946,344,675 | 2026-07-30 | 2,406,951,502 | 9,353,296,177 |
| alexander.sorrell.it@gmail.com | 571,753,755 | 2026-07-19 | 0 | 571,753,755 |
| unknown (Documents) | _none_ | — | 10,014,914 | 10,014,914 |

</details>

<details><summary>HP Laptop Linux — how its floor is built</summary>

| Account | Counter | Counter ends | Transcripts after | Floor |
|---|---:|---|---:|---:|
| codehunterextreme@gmail.com | 21,639,227,722 | 2026-08-19 | 688,862,496 | 22,328,090,218 |
| broodierchip@gmail.com | 12,290,485,337 | 2026-05-17 | 688,918,795 | 12,979,404,132 |
| DeepSeek backend (~/.my-claude) | _none_ | — | 520,497,793 | 520,497,793 |
| alexander.sorrell.it@gmail.com | 275,419,282 | 2026-08-31 | 86,127,411 | 361,546,693 |
| API key (org 15a93e14-aabb-4293-8228-8c56a803d972) | _none_ | — | 141,210 | 141,210 |

</details>

---

## Claude Code's own counter, versus the transcripts

Every profile keeps `stats-cache.json`. It is not a transcript, so the cleanup sweep never touches it, and it accumulates from that profile's first session — including sessions whose transcripts were deleted months ago.

| Profile | Account | Own counter | Counter covers | From transcripts |
|---|---|---:|---|---:|
| `.claude-main` | broodierchip@gmail.com | 28,833,190,364 | 2026-05-26 → 2026-07-21 | 12,456,931,683 |
| `.claude-alt` | codehunterextreme@gmail.com | 21,639,227,722 | 2026-06-09 → 2026-08-19 | 8,062,476,061 |
| `claude` | broodierchip@gmail.com | 12,290,485,337 | 2026-01-14 → 2026-05-17 | 2,744,450,437 |
| `.claude` | broodierchip@gmail.com | 12,290,485,337 | 2026-01-14 → 2026-05-17 | 2,744,450,437 |
| `claude-alt` | codehunterextreme@gmail.com | 11,440,918,343 | 2026-06-09 → 2026-07-11 | 8,062,476,061 |
| `.claude` | codehunterextreme@gmail.com | 6,946,344,675 | 2026-05-26 → 2026-07-30 | 5,321,298,979 |
| `.claude-it` | alexander.sorrell.it@gmail.com | 571,753,755 | 2026-06-10 → 2026-07-19 | 243,949,169 |
| `claude-it` | alexander.sorrell.it@gmail.com | 275,419,282 | 2026-06-09 → 2026-08-31 | 223,851,103 |
| `.claude-it` | alexander.sorrell.it@gmail.com | 275,419,282 | 2026-06-09 → 2026-08-31 | 223,851,103 |

**Do not subtract these columns.** The two cover different periods: the counter runs from the first session to its own `lastComputedDate` and then stops, while the transcripts hold whatever has not expired, which includes days after that date. Neither contains the other — each holds usage the other lacks — so their difference is not a quantity of anything.

An earlier version of this report published exactly that subtraction as "tokens the transcripts can no longer see". It was arithmetic on two incomparable windows, and it is removed rather than reworded.

The overlap cannot be resolved either: the cache's only per-day breakdown is input+output, excluding cache reads, which are around 95% of the volume. What the comparison honestly shows is that far more usage happened than the surviving transcripts record, with both figures and both windows stated so a reader can see the shape of the gap without being handed a false number for it.

---

## Sessions that no longer have a transcript

**1,426 Claude Code sessions have existed across the scanned machines. 990 of them — 69% — no longer have a transcript on disk.**

Claude Code deletes transcripts older than `cleanupPeriodDays`, but it does not delete `history.jsonl`. That file records one entry per prompt with a session id, a timestamp and a project, and it reaches much further back than the transcripts do:

```
ledger reaches back to     2026-01-14
oldest surviving transcript 2026-05-04
```

It carries **no token counts**, so a lost session's cost is gone for good. What survives is proof the session happened, when, and in which project — which turns an unquantified loss into a number. The ledger is committed with each scan, so it accumulates permanently even as its own source expires. Prompt text is deliberately not stored.

| Account | Sessions ever | Transcript gone | Span |
|---|---:|---:|---|
| broodierchip@gmail.com | 802 | 615 | 2026-01-14 → 2026-08-20 |
| codehunterextreme@gmail.com | 543 | 350 | 2026-02-11 → 2026-08-21 |
| user:73ae64bf180b | 62 | 20 | 2026-05-12 → 2026-07-18 |
| alexander.sorrell.it@gmail.com | 17 | 5 | 2026-06-09 → 2026-09-01 |
| user:4be462f3a2f9 | 2 | 0 | 2026-06-09 → 2026-06-09 |

---

## Cross-tabs

_scans taken 2026-08-19 21:24:07 .. 2026-09-01 06:48:33_

### Computer x company

| Computer | Anthropic | DeepSeek | Total |
|---|---|---|---|
| MacBook Air M1 | 18.03B | — | **18,032,194,745** |
| HP Laptop Linux | 11.02B | 534.67M | **11,551,416,604** |
| **All** | **29.05B** | **534.67M** | **29,583,611,349** |

### Computer x CLI

| Computer | claude | gemini | codex | copilot | bob | clawspring | antigravity | grok | kilocode | copilot-chat | lmstudio | claude-orphans | Total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| HP Laptop Linux | 15.72B | 1.47B | 1.45M | 295.83M | 229.04M | 258.50M | 83.60M | — | 7.07M | 1.21M | 119.88K | — | **18,068,954,215** |
| MacBook Air M1 | 19.21B | 995.36M | 1.63B | 497.70M | 272.62M | — | 135.11M | 100.22M | — | — | 53.16K | — | **22,843,956,661** |
| **All** | **34.93B** | **2.46B** | **1.64B** | **793.53M** | **501.66M** | **258.50M** | **218.71M** | **100.22M** | **7.07M** | **1.21M** | **173.04K** | **0** | **40,912,910,876** |

---

## Sessions

741 sessions · 1,207h 28m active · 40,912,910,876 tokens

Gaps over 15 minutes are treated as idle and dropped. First-to-last timestamp instead produced a *436-hour day* on this data.

**The 15 minutes is a judgement call.** On the 736 session(s) measured both ways, counting only gaps under one minute gives **511h 30m** against **1,207h 28m**. The 695h 57m between is where reading output and walking away look identical. Read it as a range. The other 5 predate this and are counted only at fifteen minutes.

### Twenty longest

| When | Computer | CLI | Active | Tokens | Turns | Model |
|---|---|---|---:|---:|---:|---|
| 2026-08-08 | MacBook Air M1 | claude | 85h 42m | 3,304,664,216 | 10,941 | `claude-opus-5` |
| 2026-07-30 | HP Laptop Linux | claude | 61h 55m | 3,314,505,487 | 17,381 | `claude-opus-5` |
| 2026-07-05 | MacBook Air M1 | claude | 60h 53m | 1,543,066,446 | 3,291 | `claude-opus-4-8` |
| 2026-07-20 | MacBook Air M1 | claude | 48h 46m | 1,180,176,108 | 2,450 | `claude-opus-4-8` |
| 2026-07-29 | MacBook Air M1 | claude | 39h 32m | 2,799,957,050 | 18,198 | `claude-opus-5` |
| 2026-07-15 | MacBook Air M1 | claude | 37h 57m | 1,057,823,005 | 2,269 | `claude-opus-4-8` |
| 2026-03-03 | MacBook Air M1 | copilot | 29h 55m | 1,404,767 | 11,231 | `unknown` |
| 2026-08-01 | MacBook Air M1 | claude | 28h 08m | 957,178,898 | 1,739 | `claude-opus-5` |
| 2026-08-18 | HP Laptop Linux | claude | 27h 41m | 1,583,306,365 | 5,452 | `claude-opus-5` |
| 2026-08-04 | MacBook Air M1 | claude | 25h 42m | 688,981,050 | 1,262 | `claude-opus-5` |
| 2026-06-18 | MacBook Air M1 | claude | 19h 08m | 243,949,169 | 1,121 | `claude-sonnet-4-6` |
| 2026-08-18 | MacBook Air M1 | claude | 18h 26m | 782,610,228 | 1,588 | `claude-opus-5` |
| 2026-03-04 | HP Laptop Linux | copilot | 17h 23m | 1,205,119 | 4,271 | `unknown` |
| 2026-07-26 | MacBook Air M1 | claude | 16h 49m | 659,873,265 | 1,563 | `claude-opus-5` |
| 2026-05-14 | HP Laptop Linux | claude | 15h 25m | 102,959,245 | 939 | `deepseek-v4-pro` |
| 2026-07-26 | MacBook Air M1 | claude | 15h 08m | 608,598,364 | 2,011 | `claude-opus-5` |
| 2026-07-07 | MacBook Air M1 | claude | 14h 01m | 273,850,474 | 3,980 | `claude-fable-5` |
| 2026-07-29 | MacBook Air M1 | claude | 13h 49m | 682,530,474 | 4,133 | `claude-opus-5` |
| 2026-08-15 | HP Laptop Linux | claude | 12h 22m | 897,089,663 | 6,015 | `claude-fable-5` |
| 2026-01-28 | HP Laptop Linux | gemini | 11h 52m | 115,970,794 | 347 | `gemini-3-flash-preview` |

### Twenty heaviest

| When | Computer | CLI | Active | Tokens | Turns | Model |
|---|---|---|---:|---:|---:|---|
| 2026-07-30 | HP Laptop Linux | claude | 61h 55m | 3,314,505,487 | 17,381 | `claude-opus-5` |
| 2026-08-08 | MacBook Air M1 | claude | 85h 42m | 3,304,664,216 | 10,941 | `claude-opus-5` |
| 2026-07-29 | MacBook Air M1 | claude | 39h 32m | 2,799,957,050 | 18,198 | `claude-opus-5` |
| 2026-08-18 | HP Laptop Linux | claude | 27h 41m | 1,583,306,365 | 5,452 | `claude-opus-5` |
| 2026-07-05 | MacBook Air M1 | claude | 60h 53m | 1,543,066,446 | 3,291 | `claude-opus-4-8` |
| 2026-07-20 | MacBook Air M1 | claude | 48h 46m | 1,180,176,108 | 2,450 | `claude-opus-4-8` |
| 2026-07-15 | MacBook Air M1 | claude | 37h 57m | 1,057,823,005 | 2,269 | `claude-opus-4-8` |
| 2026-08-01 | MacBook Air M1 | claude | 28h 08m | 957,178,898 | 1,739 | `claude-opus-5` |
| 2026-05-20 | MacBook Air M1 | gemini | 7h 04m | 927,740,104 | 3,331 | `gemini-3-flash-preview` |
| 2026-08-15 | HP Laptop Linux | claude | 12h 22m | 897,089,663 | 6,015 | `claude-fable-5` |
| ? | HP Laptop Linux | claude | 0m | 866,353,660 | 0 | `claude-opus-4-6` |
| 2026-08-18 | MacBook Air M1 | claude | 18h 26m | 782,610,228 | 1,588 | `claude-opus-5` |
| 2026-08-04 | MacBook Air M1 | claude | 25h 42m | 688,981,050 | 1,262 | `claude-opus-5` |
| 2026-07-29 | MacBook Air M1 | claude | 13h 49m | 682,530,474 | 4,133 | `claude-opus-5` |
| 2026-07-26 | MacBook Air M1 | claude | 16h 49m | 659,873,265 | 1,563 | `claude-opus-5` |
| 2026-07-26 | MacBook Air M1 | claude | 15h 08m | 608,598,364 | 2,011 | `claude-opus-5` |
| 2026-08-10 | HP Laptop Linux | claude | 10h 21m | 591,317,974 | 3,776 | `claude-opus-5` |
| 2026-08-13 | HP Laptop Linux | claude | 6h 25m | 476,302,536 | 5,647 | `claude-opus-5` |
| ? | HP Laptop Linux | claude | 0m | 449,999,538 | 0 | `claude-haiku-4-5-20251001` |
| 2026-05-13 | HP Laptop Linux | claude | 9h 01m | 393,266,899 | 865 | `claude-opus-4-7` |

### Busiest days

| Day | Tokens | Active |
|---|---:|---:|
| 2026-08-08 | 3,586,423,068 | 95h 03m |
| 2026-07-29 | 3,482,487,524 | 53h 22m |
| 2026-07-30 | 3,317,969,144 | 62h 17m |
| 2026-08-18 | 2,496,845,940 | 52h 05m |
| 2026-07-05 | 1,679,650,742 | 67h 18m |
| 2026-07-20 | 1,464,303,862 | 64h 32m |
| 2026-07-26 | 1,268,471,629 | 31h 56m |
| 2026-08-15 | 1,254,348,151 | 22h 38m |
| 2026-07-23 | 1,168,498,450 | 12h 15m |
| 2026-07-15 | 1,058,747,798 | 38h 16m |
| 2026-08-01 | 1,038,201,575 | 31h 14m |
| 2026-05-20 | 961,735,939 | 12h 47m |
| 2026-08-04 | 941,970,723 | 35h 54m |
| 2026-05-13 | 876,095,071 | 32h 51m |
| 2026-08-06 | 841,460,411 | 30h 00m |

Session-hours can exceed 24 in a day: parallel agents overlap, and that overlap is real work, so it is summed rather than clamped.

