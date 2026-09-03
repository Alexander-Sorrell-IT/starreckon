# By account

_What each login spent, across every computer_

_Generated 2026-08-12T00:58:32-05:00 by `stats_page.py`. Do not edit by hand._

**14,766,838,204** tokens of Claude Code across 1 scanned computer(s) · **19,302,153,082** across every CLI on the 1 that ran `sessions.py`.

Those two are not added: the second contains the first. See [BY-COMPUTER.md](BY-COMPUTER.md) for the reconciliation.

Reports: [computers](BY-COMPUTER.md) · [accounts](BY-ACCOUNT.md) · [companies](BY-COMPANY.md) · [how it works](README.md)

---

_scans taken 2026-08-11 15:39:21_

The per-account total across computers is the number that matters: the same login gets driven from several machines and no machine can see another's sessions.

| Account | Tokens | Share | Computers | Sessions | Turns | |
|---|---:|---:|---:|---:|---:|---|
| **second@example.com** | 9,211,228,521 | 62.4% | 1 | 64 | 50,228 | █████████████████··········· |
| **third@example.com** | 5,301,645,600 | 35.9% | 1 | 49 | 13,140 | ██████████·················· |
| **owner@example.com** | 243,949,169 | 1.7% | 1 | 8 | 1,124 | █··························· |
| **unknown (Documents)** | 10,014,914 | 0.1% | 1 | 4,360 | 106 | █··························· |
| **All** | **14,766,838,204** | 100% | | | | |

## Across every CLI, by account

The table above is Claude Code only, because it is the one tool that writes its account email to disk. This one folds in every other CLI using the ownership declared in [`accounts.json`](accounts.json).

| Account | Tokens | Sessions | Via |
|---|---:|---:|---|
| **second@example.com** | 10,730,490,661 | 48 | claude 9.74B, gemini 995.36M _file_ |
| **third@example.com** | 5,958,231,752 | 29 | claude 5.96B |
| **owner@example.com** | 243,949,169 | 4 | claude 243.95M |
| **fourth@example.com** | 99,062,873 | 7 | grok 99.06M _owner_ |
| **All attributed** | **17,031,734,455** | | |

`file` means the email was read out of that tool's own account file. `owner` means it was stated by the account holder and cannot be checked against anything on disk. Claude Code rows carry neither because the email is in the session record itself.

> ⚠️ **2,270,418,627 tokens have no account.** These tools record no identity on disk and none is declared for them yet:

| CLI | Company that served it | Sessions | Tokens |
|---|---|---:|---:|
| codex | OpenAI | 125 | 1,633,604,881 |
| copilot | Anthropic | 26 | 437,663,547 |
| antigravity | Google | 35 | 135,111,522 |
| copilot | — (no API call) | 8 | 59,372,409 |
| claude | Anthropic | 5 | 3,952,282 |
| copilot | OpenAI | 2 | 660,827 |
| lmstudio | — (unidentified) | 3 | 53,159 |

⚠️ marks a row where the tool's name and the company that served the tokens disagree. `claude` served by DeepSeek is a Claude Code build pointed at a DeepSeek backend: the interface is Claude Code, every token is DeepSeek, and Anthropic was paid nothing. Reading the CLI column alone would count it as Claude usage.


Add a `services` entry to the right account in `accounts.json` to fold any of these in. They are left under a placeholder rather than split across accounts by proportion, because that would invent numbers that look measured.

### Account x computer

| Account | MacBook Air M1 | Total |
|---|---|---|
| second@example.com | 9.21B | **9,211,228,521** |
| third@example.com | 5.30B | **5,301,645,600** |
| owner@example.com | 243.95M | **243,949,169** |
| unknown (Documents) | 10.01M | **10,014,914** |
| **All** | **14.77B** | **14,766,838,204** |

---

## second@example.com

**9,211,228,521 tokens** (62.4%) · 64 sessions · 50,228 turns · 33 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBook Air M1 | 9,211,228,521 | 100.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 9,211,228,521 |

| Model | Tokens |
|---|---:|
| `claude-opus-5` | 6,038,153,254 |
| `claude-opus-4-8` | 2,364,514,461 |
| `claude-fable-5` | 808,080,081 |
| `claude-haiku-4-5-20251001` | 480,725 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 3,778,559 | 275,752,062 | 8,880,873,576 | 50,824,324 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## third@example.com

**5,301,645,600 tokens** (35.9%) · 49 sessions · 13,140 turns · 30 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBook Air M1 | 5,301,645,600 | 100.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 5,301,645,600 |

| Model | Tokens |
|---|---:|
| `claude-opus-4-8` | 2,913,362,846 |
| `claude-opus-5` | 2,387,298,123 |
| `claude-sonnet-5` | 831,507 |
| `claude-opus-4-7` | 153,124 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 434,067 | 159,904,094 | 5,125,223,771 | 16,083,668 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## owner@example.com

**243,949,169 tokens** (1.7%) · 8 sessions · 1,124 turns · 3 active days

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

## unknown (Documents)

**10,014,914 tokens** (0.1%) · 4,360 sessions · 106 turns · 21 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBook Air M1 | 10,014,914 | 100.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 10,014,914 |

| Model | Tokens |
|---|---:|
| `claude-opus-4-8` | 5,533,673 |
| `claude-opus-5` | 3,705,389 |
| `claude-fable-5` | 775,852 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 25,899 | 483,893 | 9,441,167 | 63,955 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## Each computer

_The same accounts, grouped by machine. One login is usually driven from several computers, and no computer can see another's sessions — which is why the account totals above exist at all._

### MacBook Air M1

**14,766,838,204 tokens** across 4 login(s)

| Account | Tokens | Share |
|---|---:|---:|
| second@example.com | 9,211,228,521 |  62.4% |
| third@example.com | 5,301,645,600 |  35.9% |
| owner@example.com | 243,949,169 |   1.7% |
| unknown (Documents) | 10,014,914 |   0.1% |

