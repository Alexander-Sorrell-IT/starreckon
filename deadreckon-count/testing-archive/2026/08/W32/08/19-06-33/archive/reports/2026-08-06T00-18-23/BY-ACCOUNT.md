# By account

_What each login spent, across every computer_

_Generated 2026-08-06T00:18:09-05:00 by `stats_page.py`. Do not edit by hand._

**11,576,825,537** tokens of Claude Code across 1 scanned computer(s) · **13,376,595,505** across every CLI on the 1 that ran `sessions.py`.

Those two are not added: the second contains the first. See [BY-COMPUTER.md](BY-COMPUTER.md) for the reconciliation.

Reports: [computers](BY-COMPUTER.md) · [accounts](BY-ACCOUNT.md) · [companies](BY-COMPANY.md) · [how it works](README.md)

---

_scans taken 2026-08-06 00:06:37_

The per-account total across computers is the number that matters: the same login gets driven from several machines and no machine can see another's sessions.

| Account | Tokens | Share | Computers | Sessions | Turns | |
|---|---:|---:|---:|---:|---:|---|
| **broodierchip@gmail.com** | 6,365,568,232 | 55.0% | 1 | 2,690 | 25,106 | ███████████████············· |
| **codehunterextreme@gmail.com** | 3,717,819,380 | 32.1% | 1 | 40 | 22,543 | █████████··················· |
| **DeepSeek backend (~/.my-claude)** | 1,409,787,623 | 12.2% | 1 | 6 | 14,797 | ███························· |
| **alexander.sorrell.it@gmail.com** | 83,212,683 | 0.7% | 1 | 2 | 885 | █··························· |
| **API key (org 15a93e14-aabb-4293-8228-8c56a803d972)** | 437,619 | 0.0% | 1 | 1 | 18 | █··························· |
| **All** | **11,576,825,537** | 100% | | | | |

## Across every CLI, by account

The table above is Claude Code only, because it is the one tool that writes its account email to disk. This one folds in every other CLI using the ownership declared in [`accounts.json`](accounts.json).

| Account | Tokens | Sessions | Via |
|---|---:|---:|---|
| **broodierchip@gmail.com** | 7,833,930,781 | 143 | claude 6.33B, gemini 1.47B _file_, claude → DeepSeek 36.16M |
| **codehunterextreme@gmail.com** | 3,717,819,380 | 38 | claude 3.72B |
| **alexander.sorrell.it@gmail.com** | 83,212,683 | 2 | claude 83.21M |
| **All attributed** | **11,634,962,844** | | |

`file` means the email was read out of that tool's own account file. `owner` means it was stated by the account holder and cannot be checked against anything on disk. Claude Code rows carry neither because the email is in the session record itself.

> ⚠️ **1,741,632,661 tokens have no account.** These tools record no identity on disk and none is declared for them yet:

| CLI | Company that served it | Sessions | Tokens |
|---|---|---:|---:|
| claude ⚠️ | DeepSeek | 17 | 1,409,787,623 |
| copilot | OpenAI | 26 | 289,892,715 |
| antigravity | Google | 19 | 26,927,559 |
| kilocode | Google | 2 | 7,025,122 |
| copilot | — (no API call) | 5 | 5,939,252 |
| codex | OpenAI | 2 | 1,453,618 |
| claude | Anthropic | 1 | 437,619 |
| lmstudio | Mistral | 5 | 116,185 |
| kilocode | — (unidentified) | 1 | 38,733 |
| kilocode | xAI | 1 | 10,646 |
| lmstudio | DeepSeek | 1 | 3,530 |
| lmstudio | Meta | 1 | 59 |

⚠️ marks a row where the tool's name and the company that served the tokens disagree. `claude` served by DeepSeek is a Claude Code build pointed at a DeepSeek backend: the interface is Claude Code, every token is DeepSeek, and Anthropic was paid nothing. Reading the CLI column alone would count it as Claude usage.


Add a `services` entry to the right account in `accounts.json` to fold any of these in. They are left under a placeholder rather than split across accounts by proportion, because that would invent numbers that look measured.

> ⚠️ **Known account(s) with no usage found anywhere:** `nefabious@gmail.com`.

### Account x computer

| Account | HP Laptop Linux | Total |
|---|---|---|
| broodierchip@gmail.com | 6.37B | **6,365,568,232** |
| codehunterextreme@gmail.com | 3.72B | **3,717,819,380** |
| DeepSeek backend (~/.my-claude) | 1.41B | **1,409,787,623** |
| alexander.sorrell.it@gmail.com | 83.21M | **83,212,683** |
| API key (org 15a93e14-aabb-4293-8228-8c56a803d972) | 437.62K | **437,619** |
| **All** | **11.58B** | **11,576,825,537** |

---

## broodierchip@gmail.com

**6,365,568,232 tokens** (55.0%) · 2,690 sessions · 25,106 turns · 28 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 6,365,568,232 | 100.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 6,329,403,839 |
| DeepSeek | 36,164,393 |
| — (no API call) | 0 |

| Model | Tokens |
|---|---:|
| `claude-opus-4-7` | 5,474,046,655 |
| `claude-opus-4-8` | 739,083,459 |
| `claude-fable-5` | 87,931,439 |
| `deepseek-v4-pro` | 36,142,409 |
| `claude-sonnet-4-6` | 18,737,764 |
| `claude-haiku-4-5-20251001` | 9,604,522 |
| `deepseek-v4-flash` | 21,984 |
| `<synthetic>` | 0 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 6,665,327 | 219,984,438 | 6,109,187,198 | 29,731,269 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## codehunterextreme@gmail.com

**3,717,819,380 tokens** (32.1%) · 40 sessions · 22,543 turns · 30 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 3,717,819,380 | 100.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 3,717,819,380 |
| — (no API call) | 0 |

| Model | Tokens |
|---|---:|
| `claude-opus-5` | 1,548,775,431 |
| `claude-fable-5` | 1,255,508,734 |
| `claude-opus-4-8` | 913,535,215 |
| `<synthetic>` | 0 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 3,443,408 | 168,102,251 | 3,527,671,492 | 18,602,229 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## DeepSeek backend (~/.my-claude)

**1,409,787,623 tokens** (12.2%) · 6 sessions · 14,797 turns · 22 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 1,409,787,623 | 100.0% |

| Company | Tokens |
|---|---:|
| DeepSeek | 1,409,787,623 |
| — (no API call) | 0 |

| Model | Tokens |
|---|---:|
| `deepseek-v4-pro` | 1,292,420,894 |
| `deepseek-v4-flash` | 117,366,729 |
| `<synthetic>` | 0 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 61,324,095 | 0 | 1,343,468,672 | 4,994,856 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## alexander.sorrell.it@gmail.com

**83,212,683 tokens** (0.7%) · 2 sessions · 885 turns · 2 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 83,212,683 | 100.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 83,212,683 |

| Model | Tokens |
|---|---:|
| `claude-sonnet-4-6` | 80,693,159 |
| `claude-haiku-4-5-20251001` | 2,519,524 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 25,878 | 2,434,605 | 80,236,487 | 515,713 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## API key (org 15a93e14-aabb-4293-8228-8c56a803d972)

**437,619 tokens** (0.0%) · 1 sessions · 18 turns · 1 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 437,619 | 100.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 437,619 |

| Model | Tokens |
|---|---:|
| `claude-opus-4-8` | 307,503 |
| `claude-fable-5` | 130,116 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 3,856 | 28,703 | 394,815 | 10,245 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

