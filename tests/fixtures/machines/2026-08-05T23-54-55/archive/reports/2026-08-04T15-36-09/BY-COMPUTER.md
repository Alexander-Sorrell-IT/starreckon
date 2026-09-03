# By computer

_Every machine, and everything on it_

_Generated 2026-08-04T15:36:08-05:00 by `stats_page.py`. Do not edit by hand._

**42,328,036,989** tokens of Claude Code across 5 scanned computer(s) · **43,694,497,788** across every CLI on the 4 that ran `sessions.py`.

Those two are not added: the second contains the first. See [BY-COMPUTER.md](BY-COMPUTER.md) for the reconciliation.

Reports: [computers](BY-COMPUTER.md) · [accounts](BY-ACCOUNT.md) · [companies](BY-COMPANY.md) · [how it works](README.md)

---

## Totals

_scans taken 2026-08-04 01:46:32 .. 2026-08-04 15:13:51 · 1 machine(s) with no recorded scan time_

Each row carries the moment that computer was scanned. Machines are scanned independently, so a total is a snapshot of several different instants, never one.

| Computer | Folder | Accounts | Tokens | Share | Scanned |
|---|---|---:|---:|---:|---|
| **MacBook Air M1** | `macbook-air-m1/` | 3 | 28,004,982,986 | 66.2% | 2026-08-04 03:07:29 |
| **HP Laptop Linux** | `hp-laptop-linux/` | 5 | 10,189,905,370 | 24.1% | 2026-08-04 15:13:51 |
| **Dell Latitude 7480 Linux** | `dell-latitude-7480-linux/` | 5 | 3,864,871,344 | 9.1% | ⚠️ not recorded |
| **ASUS Laptop Linux** | `asus-laptop-linux/` | 1 | 266,146,676 | 0.6% | 2026-08-04 01:46:32 |
| **Dell Inspiron Desktop Linux** | `dell-inspiron-desktop-linux/` | 1 | 2,130,613 | 0.0% | 2026-08-04 02:05:52 |
| **All** | | | **42,328,036,989** | 100% | |

### The two scopes, reconciled

```
Claude Code, per account (totals.json)  :   38,463,165,645
Claude Code, per session (sessions.json):   38,546,049,662
difference                              :      -82,884,017
non-Claude-Code CLIs, additional        :    5,148,448,126
```

**These should agree and differ by 82,884,017.** The usual innocent cause is a session still being written during the scan; anything larger is a bug worth finding before quoting these.

---

## MacBook Air M1

scanned **2026-08-04 03:07:29** · sessions 2026-08-04 03:07:48

`macbook-air-m1/` · 3 account(s) · 53 sessions · 131,394 turns · **28,004,982,986 tokens** (66.2% of all Claude Code)

> ⚠️ scanned before the scanner recorded its version. These figures are a floor for this machine, not a total. `update.py` on it settles it.

### Accounts on this computer

| Account | Tokens | Share of machine |
|---|---:|---:|
| second@example.com | 17,484,273,586 | 62.4% |
| third@example.com | 9,948,955,645 | 35.5% |
| owner@example.com | 571,753,755 | 2.0% |

### Companies on this computer

| Company | Tokens | Share |
|---|---:|---:|
| Anthropic | 28,004,982,986 | 100.0% |
| — (no API call) | 0 | 0.0% |

### CLIs on this computer

| CLI | Sessions | Active | Tokens |
|---|---:|---:|---:|
| claude | 50 | 386h 58m | 28,084,988,086 |
| codex | 125 | 29h 42m | 1,633,203,953 |
| gemini | 4 | 9h 38m | 995,360,683 |
| copilot | 36 | 79h 46m | 497,696,783 |
| antigravity | 35 | 13h 38m | 135,111,522 |
| grok | 5 | 7h 40m | 76,724,862 |

### Installed here — 9 tool(s)

Presence is separate from usage: a tool with no token column is installed and not counted, which is different from unused.

| Tool | Kind | Counted | Sessions | Tokens | Usage |
|---|---|---|---:|---:|---|
| Claude Code | cli | yes | 50 | 28,084,988,086 | 2026-05-26 → 2026-08-04 |
| OpenAI Codex CLI | cli | yes | 125 | 1,633,203,953 | 2026-07-13 → 2026-07-31 |
| Google Gemini CLI | cli | yes | 4 | 995,360,683 | 2026-05-20 → 2026-05-23 |
| GitHub Copilot CLI | cli | yes | 36 | 497,696,783 | 2026-03-03 → 2026-06-10 |
| Antigravity CLI | cli | yes | 35 | 135,111,522 | 2026-05-28 → 2026-07-31 |
| xAI Grok CLI | cli | yes | 5 | 76,724,862 | 2026-07-21 → 2026-07-27 |
| Continue | agent | no — usage not located on disk | — | — | last touched 2026-06-11 |
| Ollama | runtime | no — local runtime — models run on this machine, nothing is billed | — | — | last touched 2026-06-01 |
| LM Studio | runtime | no — local runtime — models run on this machine, nothing is billed | — | — | last touched 2026-07-29 |

---

## HP Laptop Linux

scanned **2026-08-04 15:13:51** · sessions 2026-08-04 15:14:01

`hp-laptop-linux/` · 5 account(s) · 133 sessions · 53,899 turns · **10,189,905,370 tokens** (24.1% of all Claude Code)

### Accounts on this computer

| Account | Tokens | Share of machine |
|---|---:|---:|
| second@example.com | 5,547,678,789 | 54.4% |
| third@example.com | 3,148,788,656 | 30.9% |
| DeepSeek backend (~/.my-claude) | 1,409,787,623 | 13.8% |
| owner@example.com | 83,212,683 | 0.8% |
| API key (org 15a93e14-aabb-4293-8228-8c56a803d972) | 437,619 | 0.0% |

### Companies on this computer

| Company | Tokens | Share |
|---|---:|---:|
| Anthropic | 8,743,953,354 | 85.8% |
| DeepSeek | 1,445,952,016 | 14.2% |
| — (no API call) | 0 | 0.0% |

### CLIs on this computer

| CLI | Sessions | Active | Tokens |
|---|---:|---:|---:|
| claude | 133 | 231h 33m | 10,192,784,287 |
| gemini | 46 | 70h 18m | 1,468,362,549 |
| copilot | 31 | 54h 41m | 295,831,967 |
| antigravity | 19 | 1h 39m | 26,927,559 |
| kilocode | 4 | 1h 19m | 7,074,501 |
| codex | 2 | 23m | 1,453,618 |
| lmstudio | 7 | 0m | 119,774 |

### Installed here — 14 tool(s)

Presence is separate from usage: a tool with no token column is installed and not counted, which is different from unused.

| Tool | Kind | Counted | Sessions | Tokens | Usage |
|---|---|---|---:|---:|---|
| Claude Code | cli | yes | 133 | 10,192,784,287 | 2026-05-04 → 2026-08-04 |
| Google Gemini CLI | cli | yes | 46 | 1,468,362,549 | 2025-12-27 → 2026-07-02 |
| GitHub Copilot CLI | cli | yes | 31 | 295,831,967 | 2026-02-24 → 2026-05-28 |
| Antigravity CLI | cli | yes | 19 | 26,927,559 | 2026-05-29 → 2026-07-23 |
| OpenAI Codex CLI | cli | yes | 2 | 1,453,618 | 2025-12-21 → 2026-01-08 |
| Jules CLI | cli | no — cloud agent — work runs on Google's servers, no local token record | — | — | last touched 2025-12-29 |
| grok-cli (@vibe-kit) | cli | no — records no usage of any kind | — | — | last touched 2026-05-22 |
| Kilo Code (VS Code) | agent | yes | 2 | 7,025,122 | 2025-07-17 → 2025-07-17 |
| Kilo Code (Insiders) | agent | yes | 2 | 49,379 | 2026-01-02 → 2026-01-13 |
| VS Code | editor | no — editor — hosts agents, spends no tokens itself | — | — | 14 launches, 11 workspaces, 1 day(s): 2026-01-19 → 2026-01-19 |
| VS Code Insiders | editor | no — editor — hosts agents, spends no tokens itself | — | — | 10 launches, 27 workspaces, 6 day(s): 2026-01-08 → 2026-03-06 |
| Zed | editor | no — editor — hosts agents, spends no tokens itself | — | — | installed |
| Ollama | runtime | no — local runtime — models run on this machine, nothing is billed | — | — | last touched 2026-05-21 |
| LM Studio | runtime | no — local runtime — models run on this machine, nothing is billed | — | — | last touched 2025-07-14 |

---

## Dell Latitude 7480 Linux

**scan time not recorded** (pre-timestamp scanner)

`dell-latitude-7480-linux/` · 5 account(s) · 16,514 sessions · 42,199 turns · **3,864,871,344 tokens** (9.1% of all Claude Code)

### Accounts on this computer

| Account | Tokens | Share of machine |
|---|---:|---:|
| owner@example.com | 2,319,466,435 | 60.0% |
| second@example.com | 1,511,346,979 | 39.1% |
| third@example.com | 26,776,064 | 0.7% |
| unknown | 7,281,866 | 0.2% |

### Companies on this computer

| Company | Tokens | Share |
|---|---:|---:|
| Anthropic | 3,864,871,344 | 100.0% |
| — (no API call) | 0 | 0.0% |

> `sessions.py` has not run here — only Claude Code is counted.

---

## ASUS Laptop Linux

scanned **2026-08-04 01:46:32**

`asus-laptop-linux/` · 1 account(s) · 28 sessions · 1,574 turns · **266,146,676 tokens** (0.6% of all Claude Code)

> ⚠️ scanned before the scanner recorded its version · **copilot is installed here and read 0 sessions** — its usage is missing from every total below. These figures are a floor for this machine, not a total. `update.py` on it settles it.

### Accounts on this computer

| Account | Tokens | Share of machine |
|---|---:|---:|
| second@example.com | 266,146,676 | 100.0% |

### Companies on this computer

| Company | Tokens | Share |
|---|---:|---:|
| Anthropic | 266,146,676 | 100.0% |
| — (no API call) | 0 | 0.0% |

### CLIs on this computer

| CLI | Sessions | Active | Tokens |
|---|---:|---:|---:|
| claude | 29 | 10h 39m | 266,146,676 |
| gemini | 5 | 2h 21m | 4,837,000 |
| antigravity | 1 | 7m | 1,593,022 |
| codex | 1 | 19m | 670,073 |

---

## Dell Inspiron Desktop Linux

scanned **2026-08-04 02:05:52** · sessions 2026-08-04 02:05:53

`dell-inspiron-desktop-linux/` · 1 account(s) · 1 sessions · 67 turns · **2,130,613 tokens** (0.0% of all Claude Code)

> ⚠️ scanned before the scanner recorded its version · **copilot is installed here and read 0 sessions** — its usage is missing from every total below. These figures are a floor for this machine, not a total. `update.py` on it settles it.

### Accounts on this computer

| Account | Tokens | Share of machine |
|---|---:|---:|
| second@example.com | 2,130,613 | 100.0% |

### Companies on this computer

| Company | Tokens | Share |
|---|---:|---:|
| Anthropic | 2,130,613 | 100.0% |

### CLIs on this computer

| CLI | Sessions | Active | Tokens |
|---|---:|---:|---:|
| antigravity | 2 | 9m | 3,078,231 |
| claude | 2 | 16m | 2,130,613 |
| gemini | 2 | 16m | 402,029 |

---

## Tokens nobody was billed for

**119,774 tokens** across 7 sessions ran on this hardware. They are counted in every total in these reports, because a token is a token regardless of who pays for it. What differs is the invoice, and there isn't one.

That is a third dimension, independent of the other two:

| Dimension | Question | Example |
|---|---|---|
| `cli` | which tool did you pay for | Copilot running a Claude model is GitHub spend |
| `provider` | whose model actually ran | …and Anthropic service |
| `billed` | did money change hands | Ollama running llama is neither |

| CLI | Model | Sessions | Tokens |
|---|---|---:|---:|
| lmstudio | `Mixtral-8x7B-Instruct-v0.1.Q6_K.gguf` | 5 | 116,185 |
| lmstudio | `deepseek-coder-6.7b-instruct.Q6_K.gguf` | 1 | 3,530 |
| lmstudio | `Llama-3-13B-Instruct-v0.1.Q4_K_S.gguf` | 1 | 59 |

Every figure elsewhere includes these. To read spend rather than volume, subtract them: 43,694,378,014 of the 43,694,497,788 total was billed to someone.

---

## The floor: the most defensible figure per machine

**66,437,818,236 tokens across 5 scanned computer(s).**

_scans taken 2026-08-04 01:46:32 .. 2026-08-04 15:13:51 · 1 machine(s) with no recorded scan time_

Two sources describe Claude Code usage and neither contains the other. `stats-cache.json` accumulates from a profile's first session to its own `lastComputedDate` and stops; the transcripts hold whatever has not been deleted, which includes days after that date.

Subtracting them is meaningless. **Concatenating them is exact** — the counter owns everything up to its end date, the transcripts own the days strictly after it, and no token falls in both. Profiles with no counter, and every non-Claude tool, contribute only their surviving records, because nothing else on disk remembers usage once its records are gone.

| Computer | Claude Code | Other tools | Floor | Measured on disk |
|---|---:|---:|---:|---:|
| MacBook Air M1 | 28,084,988,086 | 3,338,097,803 | **31,423,085,889** | 31,423,085,889 |
| HP Laptop Linux | 29,071,233,391 | 1,799,769,968 | **30,871,003,359** | 11,992,554,255 |
| Dell Latitude 7480 Linux | 3,864,871,344 | 0 | **3,864,871,344** | 3,864,871,344 |
| ASUS Laptop Linux | 266,146,676 | 7,100,095 | **273,246,771** | 273,246,771 |
| Dell Inspiron Desktop Linux | 2,130,613 | 3,480,260 | **5,610,873** | 5,610,873 |
| **All** | | | **66,437,818,236** | |

It is a floor and not a total for three reasons, all measured rather than assumed: profiles without a counter lose anything pruned before the scan; the counter's own window has gaps where transcripts were deleted before it froze; and no non-Claude tool keeps a counter at all.

<details><summary>HP Laptop Linux — how its floor is built</summary>

| Account | Counter | Counter ends | Transcripts after | Floor |
|---|---:|---|---:|---:|
| second@example.com | 12,290,485,337 | 2026-05-17 | 1,464,352,556 | 13,754,837,893 |
| third@example.com | 11,440,918,343 | 2026-07-11 | 2,382,039,230 | 13,822,957,573 |
| DeepSeek backend (~/.my-claude) | _none_ | — | 1,409,787,623 | 1,409,787,623 |
| owner@example.com | _none_ | — | 83,212,683 | 83,212,683 |
| API key (org 15a93e14-aabb-4293-8228-8c56a803d972) | _none_ | — | 437,619 | 437,619 |

</details>

---

## Claude Code's own counter, versus the transcripts

Every profile keeps `stats-cache.json`. It is not a transcript, so the cleanup sweep never touches it, and it accumulates from that profile's first session — including sessions whose transcripts were deleted months ago.

| Profile | Account | Own counter | Counter covers | From transcripts |
|---|---|---:|---|---:|
| `.claude` | second@example.com | 12,290,485,337 | 2026-01-14 → 2026-05-17 | 5,547,678,789 |
| `.claude-alt` | third@example.com | 11,440,918,343 | 2026-06-09 → 2026-07-11 | 3,148,788,656 |

**Do not subtract these columns.** The two cover different periods: the counter runs from the first session to its own `lastComputedDate` and then stops, while the transcripts hold whatever has not expired, which includes days after that date. Neither contains the other — each holds usage the other lacks — so their difference is not a quantity of anything.

An earlier version of this report published exactly that subtraction as "tokens the transcripts can no longer see". It was arithmetic on two incomparable windows, and it is removed rather than reworded.

The overlap cannot be resolved either: the cache's only per-day breakdown is input+output, excluding cache reads, which are around 95% of the volume. What the comparison honestly shows is that far more usage happened than the surviving transcripts record, with both figures and both windows stated so a reader can see the shape of the gap without being handed a false number for it.

---

## Sessions that no longer have a transcript

**565 Claude Code sessions have existed across the scanned machines. 469 of them — 83% — no longer have a transcript on disk.**

Claude Code deletes transcripts older than `cleanupPeriodDays`, but it does not delete `history.jsonl`. That file records one entry per prompt with a session id, a timestamp and a project, and it reaches much further back than the transcripts do:

```
ledger reaches back to     2026-01-14
oldest surviving transcript 2026-01-17
```

It carries **no token counts**, so a lost session's cost is gone for good. What survives is proof the session happened, when, and in which project — which turns an unquantified loss into a number. The ledger is committed with each scan, so it accumulates permanently even as its own source expires. Prompt text is deliberately not stored.

| Account | Sessions ever | Transcript gone | Span |
|---|---:|---:|---|
| second@example.com | 310 | 271 | 2026-01-14 → 2026-07-06 |
| third@example.com | 220 | 183 | 2026-02-26 → 2026-08-04 |
| user:73ae64bf180b | 31 | 14 | 2026-05-12 → 2026-07-18 |
| owner@example.com | 3 | 1 | 2026-06-09 → 2026-06-10 |
| user:4be462f3a2f9 | 1 | 0 | 2026-06-09 → 2026-06-09 |

---

## Cross-tabs

_scans taken 2026-08-04 01:46:32 .. 2026-08-04 15:13:51 · 1 machine(s) with no recorded scan time_

### Computer x company

| Computer | Anthropic | DeepSeek | Total |
|---|---|---|---|
| MacBook Air M1 | 28.00B | — | **28,004,982,986** |
| HP Laptop Linux | 8.74B | 1.45B | **10,189,905,370** |
| Dell Latitude 7480 Linux | 3.86B | — | **3,864,871,344** |
| ASUS Laptop Linux | 266.15M | — | **266,146,676** |
| Dell Inspiron Desktop Linux | 2.13M | — | **2,130,613** |
| **All** | **40.88B** | **1.45B** | **42,328,036,989** |

### Computer x CLI

| Computer | claude | gemini | codex | copilot | antigravity | grok | kilocode | lmstudio | Total |
|---|---|---|---|---|---|---|---|---|---|
| ASUS Laptop Linux | 266.15M | 4.84M | 670.07K | — | 1.59M | — | — | — | **273,246,771** |
| Dell Inspiron Desktop Linux | 2.13M | 402.03K | — | — | 3.08M | — | — | — | **5,610,873** |
| HP Laptop Linux | 10.19B | 1.47B | 1.45M | 295.83M | 26.93M | — | 7.07M | 119.77K | **11,992,554,255** |
| MacBook Air M1 | 28.08B | 995.36M | 1.63B | 497.70M | 135.11M | 76.72M | — | — | **31,423,085,889** |
| **All** | **38.55B** | **2.47B** | **1.64B** | **793.53M** | **166.71M** | **76.72M** | **7.07M** | **119.77K** | **43,694,497,788** |

---

## Sessions

539 sessions · 901h 22m active · 43,694,497,788 tokens

Gaps over 15 minutes are treated as idle and dropped. First-to-last timestamp instead produced a *436-hour day* on this data.

**The 15 minutes is a judgement call.** On the 497 session(s) measured both ways, counting only gaps under one minute gives **358h 34m** against **887h 16m**. The 528h 41m between is where reading output and walking away look identical. Read it as a range. The other 42 predate this and are counted only at fifteen minutes.

### Twenty longest

| When | Computer | CLI | Active | Tokens | Turns | Model |
|---|---|---|---:|---:|---:|---|
| 2026-07-05 | MacBook Air M1 | claude | 60h 53m | 3,953,220,565 | 8,569 | `claude-opus-4-8` |
| 2026-07-20 | MacBook Air M1 | claude | 48h 46m | 3,121,851,274 | 6,471 | `claude-opus-4-8` |
| 2026-07-29 | MacBook Air M1 | claude | 39h 32m | 5,968,942,051 | 45,141 | `claude-opus-5` |
| 2026-07-15 | MacBook Air M1 | claude | 37h 57m | 2,867,068,267 | 6,387 | `claude-opus-4-8` |
| 2026-03-03 | MacBook Air M1 | copilot | 29h 55m | 1,404,767 | 11,231 | `unknown` |
| 2026-08-01 | MacBook Air M1 | claude | 28h 08m | 2,052,235,656 | 3,718 | `claude-opus-5` |
| 2026-06-18 | MacBook Air M1 | claude | 19h 08m | 571,753,755 | 2,328 | `claude-sonnet-4-6` |
| 2026-03-04 | HP Laptop Linux | copilot | 17h 23m | 1,205,119 | 4,271 | `unknown` |
| 2026-07-26 | MacBook Air M1 | claude | 16h 49m | 1,427,934,999 | 3,395 | `claude-opus-5` |
| 2026-05-14 | HP Laptop Linux | claude | 15h 25m | 284,178,186 | 2,724 | `deepseek-v4-pro` |
| 2026-07-26 | MacBook Air M1 | claude | 15h 08m | 1,429,845,256 | 5,246 | `claude-opus-5` |
| 2026-07-07 | MacBook Air M1 | claude | 14h 01m | 554,990,824 | 9,736 | `claude-fable-5` |
| 2026-07-29 | MacBook Air M1 | claude | 13h 49m | 1,531,175,772 | 10,880 | `claude-opus-5` |
| 2026-07-30 | HP Laptop Linux | claude | 12h 26m | 1,078,514,286 | 3,410 | `claude-opus-5` |
| 2026-01-28 | HP Laptop Linux | gemini | 11h 52m | 115,970,794 | 347 | `gemini-3-flash-preview` |
| 2026-07-22 | MacBook Air M1 | claude | 11h 29m | 715,564,869 | 8,475 | `claude-opus-4-8` |
| 2026-05-22 | HP Laptop Linux | claude | 11h 22m | 320,149,649 | 3,824 | `deepseek-v4-pro` |
| 2026-05-13 | HP Laptop Linux | claude | 11h 14m | 702,326,538 | 1,690 | `claude-opus-4-7` |
| 2026-05-21 | MacBook Air M1 | copilot | 10h 50m | 171,418,535 | 1,178 | `claude-sonnet-4.6` |
| 2026-07-14 | MacBook Air M1 | claude | 10h 08m | 533,028,875 | 1,514 | `claude-opus-4-8` |

### Twenty heaviest

| When | Computer | CLI | Active | Tokens | Turns | Model |
|---|---|---|---:|---:|---:|---|
| 2026-07-29 | MacBook Air M1 | claude | 39h 32m | 5,968,942,051 | 45,141 | `claude-opus-5` |
| 2026-07-05 | MacBook Air M1 | claude | 60h 53m | 3,953,220,565 | 8,569 | `claude-opus-4-8` |
| 2026-07-20 | MacBook Air M1 | claude | 48h 46m | 3,121,851,274 | 6,471 | `claude-opus-4-8` |
| 2026-07-15 | MacBook Air M1 | claude | 37h 57m | 2,867,068,267 | 6,387 | `claude-opus-4-8` |
| 2026-08-01 | MacBook Air M1 | claude | 28h 08m | 2,052,235,656 | 3,718 | `claude-opus-5` |
| 2026-07-29 | MacBook Air M1 | claude | 13h 49m | 1,531,175,772 | 10,880 | `claude-opus-5` |
| 2026-07-26 | MacBook Air M1 | claude | 15h 08m | 1,429,845,256 | 5,246 | `claude-opus-5` |
| 2026-07-26 | MacBook Air M1 | claude | 16h 49m | 1,427,934,999 | 3,395 | `claude-opus-5` |
| 2026-07-30 | HP Laptop Linux | claude | 12h 26m | 1,078,514,286 | 3,410 | `claude-opus-5` |
| 2026-05-20 | MacBook Air M1 | gemini | 7h 04m | 927,740,104 | 3,331 | `gemini-3-flash-preview` |
| 2026-07-22 | MacBook Air M1 | claude | 11h 29m | 715,564,869 | 8,475 | `claude-opus-4-8` |
| 2026-05-13 | HP Laptop Linux | claude | 11h 14m | 702,326,538 | 1,690 | `claude-opus-4-7` |
| 2026-07-10 | MacBook Air M1 | claude | 9h 10m | 695,003,481 | 6,774 | `claude-opus-4-8` |
| 2026-05-13 | HP Laptop Linux | claude | 9h 01m | 675,728,816 | 1,490 | `claude-opus-4-7` |
| 2026-06-18 | MacBook Air M1 | claude | 19h 08m | 571,753,755 | 2,328 | `claude-sonnet-4-6` |
| 2026-05-12 | HP Laptop Linux | claude | 6h 12m | 569,253,437 | 1,287 | `claude-opus-4-7` |
| 2026-07-07 | MacBook Air M1 | claude | 14h 01m | 554,990,824 | 9,736 | `claude-fable-5` |
| 2026-07-18 | HP Laptop Linux | claude | 8h 25m | 553,188,821 | 2,675 | `claude-fable-5` |
| 2026-07-14 | MacBook Air M1 | claude | 10h 08m | 533,028,875 | 1,514 | `claude-opus-4-8` |
| 2026-07-18 | MacBook Air M1 | claude | 7h 05m | 402,887,670 | 954 | `claude-opus-4-8` |

### Busiest days

| Day | Tokens | Active |
|---|---:|---:|
| 2026-07-29 | 7,500,117,823 | 53h 22m |
| 2026-07-05 | 4,204,983,943 | 67h 11m |
| 2026-07-20 | 3,836,616,610 | 64h 32m |
| 2026-07-15 | 2,868,034,988 | 38h 16m |
| 2026-07-26 | 2,857,780,255 | 31h 56m |
| 2026-08-01 | 2,221,299,603 | 31h 14m |
| 2026-05-13 | 1,762,350,200 | 32h 51m |
| 2026-05-12 | 1,456,849,631 | 32h 18m |
| 2026-07-23 | 1,311,133,105 | 12h 15m |
| 2026-07-18 | 1,177,431,546 | 21h 00m |
| 2026-05-24 | 1,103,839,029 | 23h 57m |
| 2026-07-30 | 1,081,577,015 | 12h 47m |
| 2026-07-07 | 1,003,974,938 | 24h 46m |
| 2026-05-20 | 961,735,939 | 12h 47m |
| 2026-07-22 | 916,166,193 | 15h 51m |

Session-hours can exceed 24 in a day: parallel agents overlap, and that overlap is real work, so it is summed rather than clamped.

