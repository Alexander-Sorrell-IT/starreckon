# By account

_What each login spent, across every computer_

_Generated 2026-08-14T18:52:39-05:00 by `stats_page.py`. Do not edit by hand._

**15,251,673,339** tokens of Claude Code across 1 scanned computer(s) · **19,817,745,559** across every CLI on the 1 that ran `sessions.py`.

Those two are not added: the second contains the first. See [BY-COMPUTER.md](BY-COMPUTER.md) for the reconciliation.

Reports: [computers](BY-COMPUTER.md) · [accounts](BY-ACCOUNT.md) · [companies](BY-COMPANY.md) · [how it works](README.md)

---

_scans taken 2026-08-14 18:52:17_

The per-account total across computers is the number that matters: the same login gets driven from several machines and no machine can see another's sessions.

| Account | Tokens | Share | Computers | Sessions | Turns | |
|---|---:|---:|---:|---:|---:|---|
| **broodierchip@gmail.com** | 9,686,425,191 | 63.5% | 1 | 32 | 51,206 | ██████████████████·········· |
| **codehunterextreme@gmail.com** | 5,321,298,979 | 34.9% | 1 | 25 | 13,265 | ██████████·················· |
| **alexander.sorrell.it@gmail.com** | 243,949,169 | 1.6% | 1 | 4 | 1,124 | █··························· |
| **All** | **15,251,673,339** | 100% | | | | |

## Across every CLI, by account

The table above is Claude Code only, because it is the one tool that writes its account email to disk. This one folds in every other CLI using the ownership declared in [`accounts.json`](accounts.json).

| Account | Tokens | Sessions | Via |
|---|---:|---:|---|
| **broodierchip@gmail.com** | 10,207,447,689 | 44 | claude 10.21B |
| **codehunterextreme@gmail.com** | 5,975,092,386 | 29 | claude 5.98B |
| **alexsorrellyan@gmail.com** | 3,261,773,869 | 200 | codex 1.63B _owner_, gemini 995.36M _owner_, copilot 437.66M _owner_, antigravity 135.11M _owner_, copilot 59.37M _owner_, copilot 660.83K _owner_ |
| **alexander.sorrell.it@gmail.com** | 243,949,169 | 4 | claude 243.95M |
| **nefabious@gmail.com** | 100,222,322 | 8 | grok 100.22M _owner_ |
| **All attributed** | **19,788,485,435** | | |

`file` means the email was read out of that tool's own account file. `owner` means it was stated by the account holder and cannot be checked against anything on disk. Claude Code rows carry neither because the email is in the session record itself.

> ⚠️ **29,260,124 tokens have no account.** These tools record no identity on disk and none is declared for them yet:

| CLI | Company that served it | Sessions | Tokens |
|---|---|---:|---:|
| bob | None | 1 | 29,206,965 |
| lmstudio | — (unidentified) | 3 | 53,159 |

⚠️ marks a row where the tool's name and the company that served the tokens disagree. `claude` served by DeepSeek is a Claude Code build pointed at a DeepSeek backend: the interface is Claude Code, every token is DeepSeek, and Anthropic was paid nothing. Reading the CLI column alone would count it as Claude usage.


Add a `services` entry to the right account in `accounts.json` to fold any of these in. They are left under a placeholder rather than split across accounts by proportion, because that would invent numbers that look measured.

> ⚠️ **Known account(s) with no usage found anywhere:** `alexsorrellit@gmail.com`.

### Account x computer

| Account | MacBook Air M1 | Total |
|---|---|---|
| broodierchip@gmail.com | 9.69B | **9,686,425,191** |
| codehunterextreme@gmail.com | 5.32B | **5,321,298,979** |
| alexander.sorrell.it@gmail.com | 243.95M | **243,949,169** |
| **All** | **15.25B** | **15,251,673,339** |

---

## broodierchip@gmail.com

**9,686,425,191 tokens** (63.5%) · 32 sessions · 51,206 turns · 36 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBook Air M1 | 9,686,425,191 | 100.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 9,686,425,191 |

| Model | Tokens |
|---|---:|
| `claude-opus-5` | 6,513,349,924 |
| `claude-opus-4-8` | 2,364,514,461 |
| `claude-fable-5` | 808,080,081 |
| `claude-haiku-4-5-20251001` | 480,725 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 3,780,583 | 288,310,886 | 9,342,630,501 | 51,703,221 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## codehunterextreme@gmail.com

**5,321,298,979 tokens** (34.9%) · 25 sessions · 13,265 turns · 33 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBook Air M1 | 5,321,298,979 | 100.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 5,321,298,979 |

| Model | Tokens |
|---|---:|
| `claude-opus-4-8` | 2,913,362,846 |
| `claude-opus-5` | 2,406,951,502 |
| `claude-sonnet-5` | 831,507 |
| `claude-opus-4-7` | 153,124 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 434,300 | 161,543,121 | 5,143,134,863 | 16,186,695 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## alexander.sorrell.it@gmail.com

**243,949,169 tokens** (1.6%) · 4 sessions · 1,124 turns · 3 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBook Air M1 | 243,949,169 | 100.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 243,949,169 |

| Model | Tokens |
|---|---:|
| `claude-opus-4-8` | 171,240,412 |
| `claude-sonnet-4-6` | 72,708,757 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 28,533 | 5,274,501 | 237,710,186 | 935,949 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## Each computer

_The same accounts, grouped by machine. One login is usually driven from several computers, and no computer can see another's sessions — which is why the account totals above exist at all._

### MacBook Air M1

**15,251,673,339 tokens** across 3 login(s)

| Account | Tokens | Share |
|---|---:|---:|
| broodierchip@gmail.com | 9,686,425,191 |  63.5% |
| codehunterextreme@gmail.com | 5,321,298,979 |  34.9% |
| alexander.sorrell.it@gmail.com | 243,949,169 |   1.6% |

