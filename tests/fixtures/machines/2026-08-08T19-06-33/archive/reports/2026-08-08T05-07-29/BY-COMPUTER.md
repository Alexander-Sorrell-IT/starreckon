# By computer

_Every machine, and everything on it_

_Generated 2026-08-08T05:07:13-05:00 by `stats_page.py`. Do not edit by hand._

**49,137,728,155** tokens of Claude Code across 5 scanned computer(s) · **56,419,690,336** across every CLI on the 5 that ran `sessions.py`.

Those two are not added: the second contains the first. See [BY-COMPUTER.md](BY-COMPUTER.md) for the reconciliation.

Reports: [computers](BY-COMPUTER.md) · [accounts](BY-ACCOUNT.md) · [companies](BY-COMPANY.md) · [how it works](README.md)

---

## Totals

_scans taken 2026-08-06 00:50:35 .. 2026-08-08 05:06:43_

Each row carries the moment that computer was scanned. Machines are scanned independently, so a total is a snapshot of several different instants, never one.

| Computer | Folder | Accounts | Tokens | Share | Scanned |
|---|---|---:|---:|---:|---|
| **MacBook Air M1** | `macbook-air-m1/` | 4 | 29,170,327,621 | 59.4% | 2026-08-06 03:30:07 |
| **HP Laptop Linux** | `hp-laptop-linux/` | 14 | 14,374,512,689 | 29.3% | 2026-08-08 05:06:43 |
| **Dell Latitude 7480 Linux** | `dell-latitude-7480-linux/` | 6 | 5,324,610,556 | 10.8% | 2026-08-06 06:17:15 |
| **ASUS Laptop Linux** | `asus-laptop-linux/` | 1 | 266,146,676 | 0.5% | 2026-08-06 00:50:35 |
| **Dell Inspiron Desktop Linux** | `dell-inspiron-desktop-linux/` | 1 | 2,130,613 | 0.0% | 2026-08-06 01:00:55 |
| **All** | | | **49,137,728,155** | 100% | |

### The two scopes, reconciled

```
Claude Code, per account (totals.json)  :   49,137,728,155
Claude Code, per session (sessions.json):   49,140,398,651
difference                              :       -2,670,496
non-Claude-Code CLIs, additional        :    7,279,291,685
```

**These should agree and differ by 2,670,496.** The usual innocent cause is a session still being written during the scan; anything larger is a bug worth finding before quoting these.

---

## MacBook Air M1

scanned **2026-08-06 03:30:07** · sessions 2026-08-06 03:36:39

`macbook-air-m1/` · 4 account(s) · 2,180 sessions · 134,345 turns · **29,170,327,621 tokens** (59.4% of all Claude Code)

### Accounts on this computer

| Account | Tokens | Share of machine |
|---|---:|---:|
| second@example.com | 17,557,582,699 | 60.2% |
| third@example.com | 11,040,991,167 | 37.9% |
| owner@example.com | 571,753,755 | 2.0% |

### Companies on this computer

| Company | Tokens | Share |
|---|---:|---:|
| Anthropic | 29,170,327,621 | 100.0% |
| — (no API call) | 0 | 0.0% |

### CLIs on this computer

| CLI | Sessions | Active | Tokens |
|---|---:|---:|---:|
| claude | 55 | 405h 53m | 29,172,782,989 |
| codex | 125 | 29h 43m | 1,633,604,881 |
| gemini | 4 | 9h 38m | 995,360,683 |
| copilot | 36 | 79h 46m | 497,696,783 |
| antigravity | 35 | 13h 38m | 135,111,522 |
| grok | 6 | 8h 57m | 90,209,318 |
| lmstudio | 3 | 0m | 53,159 |

### Installed here — 10 tool(s)

Presence is separate from usage: a tool with no token column is installed and not counted, which is different from unused.

| Tool | Kind | Counted | Sessions | Tokens | Usage |
|---|---|---|---:|---:|---|
| Claude Code | cli | yes | 55 | 29,172,782,989 | 2026-05-26 → 2026-08-06 |
| OpenAI Codex CLI | cli | yes | 125 | 1,633,604,881 | 2026-07-13 → 2026-08-05 |
| Google Gemini CLI | cli | yes | 4 | 995,360,683 | 2026-05-20 → 2026-05-23 |
| GitHub Copilot CLI | cli | yes | 36 | 497,696,783 | 2026-03-03 → 2026-06-10 |
| Antigravity CLI | cli | yes | 35 | 135,111,522 | 2026-05-28 → 2026-07-31 |
| xAI Grok CLI | cli | yes | 6 | 90,209,318 | 2026-07-21 → 2026-08-05 |
| Continue | agent | no — usage not located on disk | — | — | last touched 2026-06-11 |
| VS Code Insiders | editor | no — editor — hosts agents, spends no tokens itself | — | — | 10 launches, 2 workspaces, 7 day(s): 2025-10-16 → 2026-06-14 |
| Ollama | runtime | no — local runtime — models run on this machine, nothing is billed | — | — | last touched 2026-06-01 |
| LM Studio | runtime | no — local runtime — models run on this machine, nothing is billed | — | — | last touched 2026-07-29 |

---

## HP Laptop Linux

scanned **2026-08-08 05:06:43** · sessions 2026-08-08 05:07:11

`hp-laptop-linux/` · 14 account(s) · 2,846 sessions · 78,560 turns · **14,374,512,689 tokens** (29.3% of all Claude Code)

### Accounts on this computer

| Account | Tokens | Share of machine |
|---|---:|---:|
| second@example.com | 6,763,060,576 | 47.0% |
| third@example.com | 6,118,014,188 | 42.6% |
| DeepSeek backend (~/.my-claude) | 1,409,787,623 | 9.8% |
| owner@example.com | 83,212,683 | 0.6% |
| API key (org 15a93e14-aabb-4293-8228-8c56a803d972) | 437,619 | 0.0% |
| unknown (.claude-alt) | 0 | 0.0% |
| unknown (.claude-alt-api) | 0 | 0.0% |
| unknown (.claude-it) | 0 | 0.0% |
| unknown (.my-claude) | 0 | 0.0% |

### Companies on this computer

| Company | Tokens | Share |
|---|---:|---:|
| Anthropic | 12,928,560,673 | 89.9% |
| DeepSeek | 1,445,952,016 | 10.1% |
| — (no API call) | 0 | 0.0% |

### CLIs on this computer

| CLI | Sessions | Active | Tokens |
|---|---:|---:|---:|
| claude | 162 | 275h 50m | 14,374,512,689 |
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
| Claude Code | cli | yes | 162 | 14,374,512,689 | 2026-05-04 → 2026-08-08 |
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

scanned **2026-08-06 06:17:15** · sessions 2026-08-06 06:18:06

`dell-latitude-7480-linux/` · 6 account(s) · 16,549 sessions · 61,252 turns · **5,324,610,556 tokens** (10.8% of all Claude Code)

### Accounts on this computer

| Account | Tokens | Share of machine |
|---|---:|---:|
| second@example.com | 3,051,075,728 | 57.3% |
| owner@example.com | 2,239,476,898 | 42.1% |
| third@example.com | 26,776,064 | 0.5% |
| user:2d4777822844 | 7,281,866 | 0.1% |
| user:283b8e5b8e48 | 0 | 0.0% |

### Companies on this computer

| Company | Tokens | Share |
|---|---:|---:|
| Anthropic | 5,324,610,556 | 100.0% |
| — (no API call) | 0 | 0.0% |

### CLIs on this computer

| CLI | Sessions | Active | Tokens |
|---|---:|---:|---:|
| claude | 16,533 | 151h 45m | 5,324,825,684 |
| copilot | 24 | 80h 36m | 1,062,300,519 |
| codex | 20 | 28h 57m | 677,851,186 |
| gemini | 33 | 27h 32m | 320,741,667 |
| antigravity | 5 | 3h 04m | 48,592,134 |

### Installed here — 10 tool(s)

Presence is separate from usage: a tool with no token column is installed and not counted, which is different from unused.

| Tool | Kind | Counted | Sessions | Tokens | Usage |
|---|---|---|---:|---:|---|
| Claude Code | cli | yes | 16,533 | 5,324,825,684 | 2026-01-17 → 2026-08-06 |
| GitHub Copilot CLI | cli | yes | 24 | 1,062,300,519 | 2026-02-26 → 2026-05-28 |
| OpenAI Codex CLI | cli | yes | 20 | 677,851,186 | 2026-04-26 → 2026-05-18 |
| Google Gemini CLI | cli | yes | 33 | 320,741,667 | 2025-12-30 → 2026-05-05 |
| Antigravity CLI | cli | yes | 5 | 48,592,134 | 2026-07-09 → 2026-07-24 |
| Jules CLI | cli | no — cloud agent — work runs on Google's servers, no local token record | — | — | last touched 2026-02-26 |
| VS Code | editor | no — editor — hosts agents, spends no tokens itself | — | — | 5 launches, 1 workspaces, 3 day(s): 2026-03-23 → 2026-04-11 |
| VS Code Insiders | editor | no — editor — hosts agents, spends no tokens itself | — | — | 1 launches, 1 workspaces, 1 day(s): 2026-03-25 → 2026-03-25 |
| Zed | editor | no — editor — hosts agents, spends no tokens itself | — | — | installed |
| Ollama | runtime | no — local runtime — models run on this machine, nothing is billed | — | — | installed |

---

## ASUS Laptop Linux

scanned **2026-08-06 00:50:35** · sessions 2026-08-06 00:50:53

`asus-laptop-linux/` · 1 account(s) · 28 sessions · 1,574 turns · **266,146,676 tokens** (0.5% of all Claude Code)

> ⚠️ **copilot is installed here and read 0 sessions** — its usage is missing from every total below. These figures are a floor for this machine, not a total. `update.py` on it settles it.

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
| antigravity | 1 | 21m | 3,073,371 |
| codex | 1 | 19m | 670,073 |

### Installed here — 8 tool(s)

Presence is separate from usage: a tool with no token column is installed and not counted, which is different from unused.

| Tool | Kind | Counted | Sessions | Tokens | Usage |
|---|---|---|---:|---:|---|
| Claude Code | cli | yes | 29 | 266,146,676 | 2026-01-17 → 2026-05-05 |
| Google Gemini CLI | cli | yes | 5 | 4,837,000 | 2025-12-28 → 2026-05-05 |
| Antigravity CLI | cli | yes | 1 | 3,073,371 | 2026-08-03 → 2026-08-06 |
| OpenAI Codex CLI | cli | yes | 1 | 670,073 | 2025-12-21 → 2025-12-21 |
| GitHub Copilot CLI | cli | yes | 0 | 0 | ? → ? |
| Jules CLI | cli | no — cloud agent — work runs on Google's servers, no local token record | — | — | last touched 2026-01-01 |
| VS Code Insiders | editor | no — editor — hosts agents, spends no tokens itself | — | — | 7 launches, 5 workspaces, 6 day(s): 2025-12-15 → 2026-01-01 |
| Zed | editor | no — editor — hosts agents, spends no tokens itself | — | — | installed |

---

## Dell Inspiron Desktop Linux

scanned **2026-08-06 01:00:55** · sessions 2026-08-06 01:00:57

`dell-inspiron-desktop-linux/` · 1 account(s) · 1 sessions · 68 turns · **2,130,613 tokens** (0.0% of all Claude Code)

> ⚠️ **copilot is installed here and read 0 sessions** — its usage is missing from every total below. These figures are a floor for this machine, not a total. `update.py` on it settles it.

### Accounts on this computer

| Account | Tokens | Share of machine |
|---|---:|---:|
| second@example.com | 2,130,613 | 100.0% |

### Companies on this computer

| Company | Tokens | Share |
|---|---:|---:|
| Anthropic | 2,130,613 | 100.0% |
| — (no API call) | 0 | 0.0% |

### CLIs on this computer

| CLI | Sessions | Active | Tokens |
|---|---:|---:|---:|
| antigravity | 3 | 50m | 9,017,392 |
| claude | 3 | 16m | 2,130,613 |
| gemini | 2 | 16m | 402,029 |

### Installed here — 7 tool(s)

Presence is separate from usage: a tool with no token column is installed and not counted, which is different from unused.

| Tool | Kind | Counted | Sessions | Tokens | Usage |
|---|---|---|---:|---:|---|
| Antigravity CLI | cli | yes | 3 | 9,017,392 | 2026-08-04 → 2026-08-06 |
| Claude Code | cli | yes | 3 | 2,130,613 | 2026-01-21 → 2026-08-04 |
| Google Gemini CLI | cli | yes | 2 | 402,029 | 2026-01-13 → 2026-01-13 |
| GitHub Copilot CLI | cli | yes | 0 | 0 | ? → ? |
| Jules CLI | cli | no — cloud agent — work runs on Google's servers, no local token record | — | — | last touched 2026-01-09 |
| VS Code Insiders | editor | no — editor — hosts agents, spends no tokens itself | — | — | 3 launches, 4 workspaces, 2 day(s): 2025-12-16 → 2026-01-09 |
| Zed | editor | no — editor — hosts agents, spends no tokens itself | — | — | installed |

---

## Tokens nobody was billed for

**172,933 tokens** across 10 sessions ran on this hardware. They are counted in every total in these reports, because a token is a token regardless of who pays for it. What differs is the invoice, and there isn't one.

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
| lmstudio | `Llama-3-13B-Instruct-v0.1.Q4_K_S.gguf` | 1 | 59 |

Every figure elsewhere includes these. To read spend rather than volume, subtract them: 56,419,517,403 of the 56,419,690,336 total was billed to someone.

---

## The floor: the most defensible figure per machine

**121,735,662,794 tokens across 5 scanned computer(s).**

_scans taken 2026-08-06 00:50:35 .. 2026-08-08 05:06:43_

Two sources describe Claude Code usage and neither contains the other. `stats-cache.json` accumulates from a profile's first session to its own `lastComputedDate` and stops; the transcripts hold whatever has not been deleted, which includes days after that date.

Subtracting them is meaningless. **Concatenating them is exact** — the counter owns everything up to its end date, the transcripts own the days strictly after it, and no token falls in both. Profiles with no counter, and every non-Claude tool, contribute only their surviving records, because nothing else on disk remembers usage once its records are gone.

| Computer | Claude Code | Other tools | Floor | Measured on disk |
|---|---:|---:|---:|---:|
| MacBook Air M1 | 51,929,935,685 | 3,352,036,346 | **55,281,972,031** | 32,524,819,335 |
| HP Laptop Linux | 33,653,333,054 | 1,799,769,968 | **35,453,103,022** | 16,174,282,657 |
| Dell Latitude 7480 Linux | 28,420,721,167 | 2,109,485,506 | **30,530,206,673** | 7,434,311,190 |
| ASUS Laptop Linux | 414,530,550 | 8,580,444 | **423,110,994** | 274,727,120 |
| Dell Inspiron Desktop Linux | 37,850,653 | 9,419,421 | **47,270,074** | 11,550,034 |
| **All** | | | **121,735,662,794** | |

It is a floor and not a total for three reasons, all measured rather than assumed: profiles without a counter lose anything pruned before the scan; the counter's own window has gaps where transcripts were deleted before it froze; and no non-Claude tool keeps a counter at all.

<details><summary>MacBook Air M1 — how its floor is built</summary>

| Account | Counter | Counter ends | Transcripts after | Floor |
|---|---:|---|---:|---:|
| second@example.com | 28,833,190,364 | 2026-07-21 | 11,484,000,399 | 40,317,190,763 |
| third@example.com | 6,946,344,675 | 2026-07-30 | 3,433,663,939 | 11,040,991,167 |
| owner@example.com | 571,753,755 | 2026-07-19 | 0 | 571,753,755 |

</details>

<details><summary>HP Laptop Linux — how its floor is built</summary>

| Account | Counter | Counter ends | Transcripts after | Floor |
|---|---:|---|---:|---:|
| third@example.com | 11,440,918,343 | 2026-07-11 | 5,748,757,106 | 17,189,675,449 |
| second@example.com | 12,290,485,337 | 2026-05-17 | 2,679,734,343 | 14,970,219,680 |
| DeepSeek backend (~/.my-claude) | _none_ | — | 1,409,787,623 | 1,409,787,623 |
| owner@example.com | _none_ | — | 83,212,683 | 83,212,683 |
| API key (org 15a93e14-aabb-4293-8228-8c56a803d972) | _none_ | — | 437,619 | 437,619 |
| unknown (.claude-alt) | _none_ | — | 0 | 0 |
| unknown (.claude-alt-api) | _none_ | — | 0 | 0 |
| unknown (.claude-it) | _none_ | — | 0 | 0 |
| unknown (.my-claude) | _none_ | — | 0 | 0 |

</details>

<details><summary>Dell Latitude 7480 Linux — how its floor is built</summary>

| Account | Counter | Counter ends | Transcripts after | Floor |
|---|---:|---|---:|---:|
| second@example.com | 25,359,992,209 | 2026-07-26 | 105,683,430 | 25,465,675,639 |
| owner@example.com | 2,442,457,035 | 2026-07-26 | 478,530,563 | 2,920,987,598 |
| third@example.com | 26,776,064 | 2026-07-26 | 0 | 26,776,064 |
| user:2d4777822844 | _none_ | — | 7,281,866 | 7,281,866 |
| user:283b8e5b8e48 | _none_ | — | 0 | 0 |

</details>

<details><summary>ASUS Laptop Linux — how its floor is built</summary>

| Account | Counter | Counter ends | Transcripts after | Floor |
|---|---:|---|---:|---:|
| second@example.com | 158,006,803 | 2026-04-30 | 256,523,747 | 414,530,550 |

</details>

<details><summary>Dell Inspiron Desktop Linux — how its floor is built</summary>

| Account | Counter | Counter ends | Transcripts after | Floor |
|---|---:|---|---:|---:|
| second@example.com | 37,850,653 | 2026-08-03 | 0 | 37,850,653 |

</details>

---

## Claude Code's own counter, versus the transcripts

Every profile keeps `stats-cache.json`. It is not a transcript, so the cleanup sweep never touches it, and it accumulates from that profile's first session — including sessions whose transcripts were deleted months ago.

| Profile | Account | Own counter | Counter covers | From transcripts |
|---|---|---:|---|---:|
| `.claude-main` | second@example.com | 28,833,190,364 | 2026-05-26 → 2026-07-21 | 17,557,582,699 |
| `.claude` | second@example.com | 25,359,992,209 | 2026-02-26 → 2026-07-26 | 3,051,075,728 |
| `.claude` | second@example.com | 12,290,485,337 | 2026-01-14 → 2026-05-17 | 6,763,060,576 |
| `.claude-alt` | third@example.com | 11,440,918,343 | 2026-06-09 → 2026-07-11 | 6,118,014,188 |
| `.claude` | third@example.com | 6,946,344,675 | 2026-05-26 → 2026-07-30 | 11,040,991,167 |
| `.claude-it` | owner@example.com | 2,442,457,035 | 2026-06-10 → 2026-07-26 | 2,239,476,898 |
| `.claude-it` | owner@example.com | 571,753,755 | 2026-06-10 → 2026-07-19 | 571,753,755 |
| `.claude` | second@example.com | 158,006,803 | 2026-01-17 → 2026-04-30 | 266,146,676 |
| `.claude` | second@example.com | 37,850,653 | 2026-01-20 → 2026-08-03 | 2,130,613 |
| `.claude-alt` | third@example.com | 26,776,064 | 2026-07-25 → 2026-07-26 | 26,776,064 |

**Do not subtract these columns.** The two cover different periods: the counter runs from the first session to its own `lastComputedDate` and then stops, while the transcripts hold whatever has not expired, which includes days after that date. Neither contains the other — each holds usage the other lacks — so their difference is not a quantity of anything.

An earlier version of this report published exactly that subtraction as "tokens the transcripts can no longer see". It was arithmetic on two incomparable windows, and it is removed rather than reworded.

The overlap cannot be resolved either: the cache's only per-day breakdown is input+output, excluding cache reads, which are around 95% of the volume. What the comparison honestly shows is that far more usage happened than the surviving transcripts record, with both figures and both windows stated so a reader can see the shape of the gap without being handed a false number for it.

---

## Sessions that no longer have a transcript

**1,127 Claude Code sessions have existed across the scanned machines. 926 of them — 82% — no longer have a transcript on disk.**

Claude Code deletes transcripts older than `cleanupPeriodDays`, but it does not delete `history.jsonl`. That file records one entry per prompt with a session id, a timestamp and a project, and it reaches much further back than the transcripts do:

```
ledger reaches back to     2026-01-14
oldest surviving transcript 2026-01-17
```

It carries **no token counts**, so a lost session's cost is gone for good. What survives is proof the session happened, when, and in which project — which turns an unquantified loss into a number. The ledger is committed with each scan, so it accumulates permanently even as its own source expires. Prompt text is deliberately not stored.

| Account | Sessions ever | Transcript gone | Span |
|---|---:|---:|---|
| second@example.com | 585 | 501 | 2026-01-14 → 2026-08-06 |
| third@example.com | 470 | 402 | 2026-02-11 → 2026-08-08 |
| owner@example.com | 38 | 9 | 2026-06-09 → 2026-08-06 |
| user:73ae64bf180b | 31 | 14 | 2026-05-12 → 2026-07-18 |
| user:2d4777822844 | 1 | 0 | 2026-04-24 → 2026-04-24 |
| user:283b8e5b8e48 | 1 | 0 | 2026-04-24 → 2026-04-24 |
| user:4be462f3a2f9 | 1 | 0 | 2026-06-09 → 2026-06-09 |

---

## Cross-tabs

_scans taken 2026-08-06 00:50:35 .. 2026-08-08 05:06:43_

### Computer x company

| Computer | Anthropic | DeepSeek | Total |
|---|---|---|---|
| MacBook Air M1 | 29.17B | — | **29,170,327,621** |
| HP Laptop Linux | 12.93B | 1.45B | **14,374,512,689** |
| Dell Latitude 7480 Linux | 5.32B | — | **5,324,610,556** |
| ASUS Laptop Linux | 266.15M | — | **266,146,676** |
| Dell Inspiron Desktop Linux | 2.13M | — | **2,130,613** |
| **All** | **47.69B** | **1.45B** | **49,137,728,155** |

### Computer x CLI

| Computer | claude | gemini | codex | copilot | antigravity | grok | kilocode | lmstudio | Total |
|---|---|---|---|---|---|---|---|---|---|
| ASUS Laptop Linux | 266.15M | 4.84M | 670.07K | — | 3.07M | — | — | — | **274,727,120** |
| Dell Inspiron Desktop Linux | 2.13M | 402.03K | — | — | 9.02M | — | — | — | **11,550,034** |
| Dell Latitude 7480 Linux | 5.32B | 320.74M | 677.85M | 1.06B | 48.59M | — | — | — | **7,434,311,190** |
| HP Laptop Linux | 14.37B | 1.47B | 1.45M | 295.83M | 26.93M | — | 7.07M | 119.77K | **16,174,282,657** |
| MacBook Air M1 | 29.17B | 995.36M | 1.63B | 497.70M | 135.11M | 90.21M | — | 53.16K | **32,524,819,335** |
| **All** | **49.14B** | **2.79B** | **2.31B** | **1.86B** | **222.72M** | **90.21M** | **7.07M** | **172.93K** | **56,419,690,336** |

---

## Sessions

17,194 sessions · 1,258h 42m active · 56,419,690,336 tokens

Gaps over 15 minutes are treated as idle and dropped. First-to-last timestamp instead produced a *436-hour day* on this data.

**The 15 minutes is a judgement call.** On the 17,194 session(s) measured both ways, counting only gaps under one minute gives **516h 23m** against **1,258h 42m**. The 742h 18m between is where reading output and walking away look identical. Read it as a range.

### Twenty longest

| When | Computer | CLI | Active | Tokens | Turns | Model |
|---|---|---|---:|---:|---:|---|
| 2026-07-05 | MacBook Air M1 | claude | 60h 53m | 3,953,220,565 | 8,569 | `claude-opus-4-8` |
| 2026-07-20 | MacBook Air M1 | claude | 48h 46m | 3,121,851,274 | 6,471 | `claude-opus-4-8` |
| 2026-07-29 | MacBook Air M1 | claude | 39h 32m | 5,968,942,051 | 45,141 | `claude-opus-5` |
| 2026-07-15 | MacBook Air M1 | claude | 37h 57m | 2,867,068,267 | 6,387 | `claude-opus-4-8` |
| 2026-07-30 | HP Laptop Linux | claude | 36h 26m | 3,937,306,856 | 16,608 | `claude-opus-5` |
| 2026-03-03 | MacBook Air M1 | copilot | 29h 55m | 1,404,767 | 11,231 | `unknown` |
| 2026-08-01 | MacBook Air M1 | claude | 28h 08m | 2,052,235,656 | 3,718 | `claude-opus-5` |
| 2026-08-04 | MacBook Air M1 | claude | 19h 32m | 1,193,324,997 | 2,277 | `claude-opus-5` |
| 2026-06-18 | MacBook Air M1 | claude | 19h 08m | 571,753,755 | 2,328 | `claude-sonnet-4-6` |
| 2026-03-04 | HP Laptop Linux | copilot | 17h 23m | 1,205,119 | 4,271 | `unknown` |
| 2026-07-26 | MacBook Air M1 | claude | 16h 49m | 1,427,934,999 | 3,395 | `claude-opus-5` |
| 2026-05-14 | HP Laptop Linux | claude | 15h 25m | 284,178,186 | 2,724 | `deepseek-v4-pro` |
| 2026-07-26 | MacBook Air M1 | claude | 15h 08m | 1,429,845,256 | 5,246 | `claude-opus-5` |
| 2026-07-07 | MacBook Air M1 | claude | 14h 01m | 554,990,824 | 9,736 | `claude-fable-5` |
| 2026-01-26 | Dell Latitude 7480 Linux | claude | 13h 52m | 190,216,255 | 1,856 | `claude-opus-4-5-20251101` |
| 2026-07-29 | MacBook Air M1 | claude | 13h 49m | 1,531,175,772 | 10,880 | `claude-opus-5` |
| 2026-04-20 | Dell Latitude 7480 Linux | copilot | 12h 52m | 5,817,377 | 2,204 | `unknown` |
| 2026-01-24 | Dell Latitude 7480 Linux | claude | 12h 41m | 140,258,193 | 1,618 | `claude-opus-4-5-20251101` |
| 2026-01-28 | HP Laptop Linux | gemini | 11h 52m | 115,970,794 | 347 | `gemini-3-flash-preview` |
| 2026-07-22 | MacBook Air M1 | claude | 11h 29m | 715,564,869 | 8,475 | `claude-opus-4-8` |

### Twenty heaviest

| When | Computer | CLI | Active | Tokens | Turns | Model |
|---|---|---|---:|---:|---:|---|
| 2026-07-29 | MacBook Air M1 | claude | 39h 32m | 5,968,942,051 | 45,141 | `claude-opus-5` |
| 2026-07-05 | MacBook Air M1 | claude | 60h 53m | 3,953,220,565 | 8,569 | `claude-opus-4-8` |
| 2026-07-30 | HP Laptop Linux | claude | 36h 26m | 3,937,306,856 | 16,608 | `claude-opus-5` |
| 2026-07-20 | MacBook Air M1 | claude | 48h 46m | 3,121,851,274 | 6,471 | `claude-opus-4-8` |
| 2026-07-15 | MacBook Air M1 | claude | 37h 57m | 2,867,068,267 | 6,387 | `claude-opus-4-8` |
| 2026-08-01 | MacBook Air M1 | claude | 28h 08m | 2,052,235,656 | 3,718 | `claude-opus-5` |
| 2026-07-29 | MacBook Air M1 | claude | 13h 49m | 1,531,175,772 | 10,880 | `claude-opus-5` |
| 2026-07-26 | MacBook Air M1 | claude | 15h 08m | 1,429,845,256 | 5,246 | `claude-opus-5` |
| 2026-07-26 | MacBook Air M1 | claude | 16h 49m | 1,427,934,999 | 3,395 | `claude-opus-5` |
| 2026-08-04 | MacBook Air M1 | claude | 19h 32m | 1,193,324,997 | 2,277 | `claude-opus-5` |
| 2026-05-20 | MacBook Air M1 | gemini | 7h 04m | 927,740,104 | 3,331 | `gemini-3-flash-preview` |
| 2026-07-22 | MacBook Air M1 | claude | 11h 29m | 715,564,869 | 8,475 | `claude-opus-4-8` |
| 2026-05-13 | HP Laptop Linux | claude | 11h 14m | 702,326,538 | 1,690 | `claude-opus-4-7` |
| 2026-07-10 | MacBook Air M1 | claude | 9h 10m | 695,003,481 | 6,774 | `claude-opus-4-8` |
| 2026-05-13 | HP Laptop Linux | claude | 9h 01m | 675,728,816 | 1,490 | `claude-opus-4-7` |
| 2026-06-18 | MacBook Air M1 | claude | 19h 08m | 571,753,755 | 2,328 | `claude-sonnet-4-6` |
| 2026-05-12 | HP Laptop Linux | claude | 6h 12m | 569,253,437 | 1,287 | `claude-opus-4-7` |
| 2026-07-07 | MacBook Air M1 | claude | 14h 01m | 554,990,824 | 9,736 | `claude-fable-5` |
| 2026-07-18 | HP Laptop Linux | claude | 8h 25m | 553,188,821 | 2,675 | `claude-fable-5` |
| 2026-07-14 | MacBook Air M1 | claude | 8h 38m | 478,479,728 | 1,262 | `claude-opus-4-8` |

### Busiest days

| Day | Tokens | Active |
|---|---:|---:|
| 2026-07-29 | 7,564,156,995 | 56h 30m |
| 2026-07-05 | 4,314,123,022 | 68h 00m |
| 2026-07-30 | 3,940,770,513 | 36h 48m |
| 2026-07-20 | 3,836,616,610 | 64h 32m |
| 2026-07-26 | 3,243,956,175 | 38h 52m |
| 2026-07-15 | 2,868,034,988 | 38h 16m |
| 2026-08-01 | 2,291,566,310 | 32h 23m |
| 2026-05-13 | 1,762,350,200 | 32h 51m |
| 2026-08-04 | 1,754,675,004 | 29h 43m |
| 2026-05-12 | 1,456,849,631 | 32h 18m |
| 2026-07-22 | 1,403,866,946 | 20h 22m |
| 2026-07-23 | 1,385,859,270 | 13h 39m |
| 2026-07-07 | 1,341,551,617 | 30h 11m |
| 2026-07-18 | 1,177,431,546 | 21h 00m |
| 2026-05-24 | 1,103,839,029 | 23h 57m |

Session-hours can exceed 24 in a day: parallel agents overlap, and that overlap is real work, so it is summed rather than clamped.

