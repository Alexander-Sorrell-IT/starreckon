# By account

_What each login spent, across every computer_

_Generated 2026-08-06T01:30:20-05:00 by `stats_page.py`. Do not edit by hand._

**11,993,517,782** tokens of Claude Code across 3 scanned computer(s) · **13,811,287,615** across every CLI on the 3 that ran `sessions.py`.

Those two are not added: the second contains the first. See [BY-COMPUTER.md](BY-COMPUTER.md) for the reconciliation.

Reports: [computers](BY-COMPUTER.md) · [accounts](BY-ACCOUNT.md) · [companies](BY-COMPANY.md) · [how it works](README.md)

---

_scans taken 2026-08-06 00:50:35 .. 2026-08-06 01:29:54_

The per-account total across computers is the number that matters: the same login gets driven from several machines and no machine can see another's sessions.

| Account | Tokens | Share | Computers | Sessions | Turns | |
|---|---:|---:|---:|---:|---:|---|
| **broodierchip@gmail.com** | 6,634,794,335 | 55.3% | 3 | 2,719 | 26,749 | ███████████████············· |
| **codehunterextreme@gmail.com** | 3,865,285,522 | 32.2% | 1 | 40 | 22,709 | █████████··················· |
| **DeepSeek backend (~/.my-claude)** | 1,409,787,623 | 11.8% | 1 | 6 | 14,797 | ███························· |
| **alexander.sorrell.it@gmail.com** | 83,212,683 | 0.7% | 1 | 2 | 885 | █··························· |
| **API key (org 15a93e14-aabb-4293-8228-8c56a803d972)** | 437,619 | 0.0% | 1 | 1 | 18 | █··························· |
| **All** | **11,993,517,782** | 100% | | | | |

## Across every CLI, by account

The table above is Claude Code only, because it is the one tool that writes its account email to disk. This one folds in every other CLI using the ownership declared in [`accounts.json`](accounts.json).

| Account | Tokens | Sessions | Via |
|---|---:|---:|---|
| **broodierchip@gmail.com** | 8,107,447,099 | 182 | claude 6.60B, gemini 1.47B _file_, claude → DeepSeek 36.16M |
| **codehunterextreme@gmail.com** | 3,866,234,336 | 38 | claude 3.87B |
| **alexander.sorrell.it@gmail.com** | 83,212,683 | 2 | claude 83.21M |
| **All attributed** | **12,056,894,118** | | |

`file` means the email was read out of that tool's own account file. `owner` means it was stated by the account holder and cannot be checked against anything on disk. Claude Code rows carry neither because the email is in the session record itself.

> ⚠️ **1,754,393,497 tokens have no account.** These tools record no identity on disk and none is declared for them yet:

| CLI | Company that served it | Sessions | Tokens |
|---|---|---:|---:|
| claude ⚠️ | DeepSeek | 17 | 1,409,787,623 |
| copilot | OpenAI | 26 | 289,892,715 |
| antigravity | Google | 23 | 39,018,322 |
| kilocode | Google | 2 | 7,025,122 |
| copilot | — (no API call) | 5 | 5,939,252 |
| codex | OpenAI | 3 | 2,123,691 |
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

| Account | HP Laptop Linux | ASUS Laptop Linux | Dell Inspiron Desktop Linux | Total |
|---|---|---|---|---|
| broodierchip@gmail.com | 6.37B | 266.15M | 2.13M | **6,634,794,335** |
| codehunterextreme@gmail.com | 3.87B | — | — | **3,865,285,522** |
| DeepSeek backend (~/.my-claude) | 1.41B | — | — | **1,409,787,623** |
| alexander.sorrell.it@gmail.com | 83.21M | — | — | **83,212,683** |
| API key (org 15a93e14-aabb-4293-8228-8c56a803d972) | 437.62K | — | — | **437,619** |
| **All** | **11.73B** | **266.15M** | **2.13M** | **11,993,517,782** |

---

## broodierchip@gmail.com

**6,634,794,335 tokens** (55.3%) · 2,719 sessions · 26,749 turns · 39 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 6,366,517,046 | 96.0% |
| ASUS Laptop Linux | 266,146,676 | 4.0% |
| Dell Inspiron Desktop Linux | 2,130,613 | 0.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 6,598,629,942 |
| DeepSeek | 36,164,393 |
| — (no API call) | 0 |

| Model | Tokens |
|---|---:|
| `claude-opus-4-7` | 5,729,729,896 |
| `claude-opus-4-8` | 739,083,459 |
| `claude-fable-5` | 87,931,439 |
| `deepseek-v4-pro` | 36,142,409 |
| `claude-haiku-4-5-20251001` | 21,201,636 |
| `claude-sonnet-4-6` | 18,737,764 |
| `claude-opus-4-5-20251101` | 996,934 |
| `claude-opus-5` | 948,814 |
| `deepseek-v4-flash` | 21,984 |
| `<synthetic>` | 0 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 6,776,749 | 240,034,450 | 6,356,365,784 | 31,617,352 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## codehunterextreme@gmail.com

**3,865,285,522 tokens** (32.2%) · 40 sessions · 22,709 turns · 30 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 3,865,285,522 | 100.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 3,865,285,522 |
| — (no API call) | 0 |

| Model | Tokens |
|---|---:|
| `claude-opus-5` | 1,696,241,573 |
| `claude-fable-5` | 1,255,508,734 |
| `claude-opus-4-8` | 913,535,215 |
| `<synthetic>` | 0 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 3,443,694 | 168,343,002 | 3,674,745,491 | 18,753,335 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## DeepSeek backend (~/.my-claude)

**1,409,787,623 tokens** (11.8%) · 6 sessions · 14,797 turns · 22 active days

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

---

## Each computer

_The same accounts, grouped by machine. One login is usually driven from several computers, and no computer can see another's sessions — which is why the account totals above exist at all._

### HP Laptop Linux

**11,725,240,493 tokens** across 5 login(s)

| Account | Tokens | Share |
|---|---:|---:|
| broodierchip@gmail.com | 6,366,517,046 |  54.3% |
| codehunterextreme@gmail.com | 3,865,285,522 |  33.0% |
| DeepSeek backend (~/.my-claude) | 1,409,787,623 |  12.0% |
| alexander.sorrell.it@gmail.com | 83,212,683 |   0.7% |
| API key (org 15a93e14-aabb-4293-8228-8c56a803d972) | 437,619 |   0.0% |

### ASUS Laptop Linux

**266,146,676 tokens** across 1 login(s)

| Account | Tokens | Share |
|---|---:|---:|
| broodierchip@gmail.com | 266,146,676 | 100.0% |

### Dell Inspiron Desktop Linux

**2,130,613 tokens** across 1 login(s)

| Account | Tokens | Share |
|---|---:|---:|
| broodierchip@gmail.com | 2,130,613 | 100.0% |

