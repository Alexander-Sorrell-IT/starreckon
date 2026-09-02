# By account

_What each login spent, across every computer_

_Generated 2026-08-06T06:06:29-05:00 by `stats_page.py`. Do not edit by hand._

**41,163,845,403** tokens of Claude Code across 4 scanned computer(s) · **46,336,106,950** across every CLI on the 4 that ran `sessions.py`.

Those two are not added: the second contains the first. See [BY-COMPUTER.md](BY-COMPUTER.md) for the reconciliation.

Reports: [computers](BY-COMPUTER.md) · [accounts](BY-ACCOUNT.md) · [companies](BY-COMPANY.md) · [how it works](README.md)

---

_scans taken 2026-08-06 00:50:35 .. 2026-08-06 03:30:07_

The per-account total across computers is the number that matters: the same login gets driven from several machines and no machine can see another's sessions.

| Account | Tokens | Share | Computers | Sessions | Turns | |
|---|---:|---:|---:|---:|---:|---|
| **broodierchip@gmail.com** | 24,192,377,034 | 58.8% | 4 | 2,748 | 133,816 | ████████████████············ |
| **codehunterextreme@gmail.com** | 14,906,276,689 | 36.2% | 2 | 2,187 | 47,656 | ██████████·················· |
| **DeepSeek backend (~/.my-claude)** | 1,409,787,623 | 3.4% | 1 | 6 | 14,797 | █··························· |
| **alexander.sorrell.it@gmail.com** | 654,966,438 | 1.6% | 2 | 6 | 3,216 | █··························· |
| **API key (org 15a93e14-aabb-4293-8228-8c56a803d972)** | 437,619 | 0.0% | 1 | 1 | 18 | █··························· |
| **All** | **41,163,845,403** | 100% | | | | |

## Across every CLI, by account

The table above is Claude Code only, because it is the one tool that writes its account email to disk. This one folds in every other CLI using the ownership declared in [`accounts.json`](accounts.json).

| Account | Tokens | Sessions | Via |
|---|---:|---:|---|
| **broodierchip@gmail.com** | 26,662,845,849 | 215 | claude 24.16B, gemini 2.47B _file_, claude → DeepSeek 36.16M |
| **codehunterextreme@gmail.com** | 14,907,225,503 | 60 | claude 14.91B |
| **alexander.sorrell.it@gmail.com** | 654,966,438 | 6 | claude 654.97M |
| **nefabious@gmail.com** | 90,209,318 | 6 | grok 90.21M _owner_ |
| **All attributed** | **42,315,247,108** | | |

`file` means the email was read out of that tool's own account file. `owner` means it was stated by the account holder and cannot be checked against anything on disk. Claude Code rows carry neither because the email is in the session record itself.

> ⚠️ **4,020,859,842 tokens have no account.** These tools record no identity on disk and none is declared for them yet:

| CLI | Company that served it | Sessions | Tokens |
|---|---|---:|---:|
| codex | OpenAI | 128 | 1,635,728,572 |
| claude ⚠️ | DeepSeek | 17 | 1,409,787,623 |
| copilot | Anthropic | 26 | 437,663,547 |
| copilot | OpenAI | 28 | 290,553,542 |
| antigravity | Google | 58 | 174,129,844 |
| copilot | — (no API call) | 13 | 65,311,661 |
| kilocode | Google | 2 | 7,025,122 |
| claude | Anthropic | 1 | 437,619 |
| lmstudio | Mistral | 5 | 116,185 |
| lmstudio | — (unidentified) | 3 | 53,159 |
| kilocode | — (unidentified) | 1 | 38,733 |
| kilocode | xAI | 1 | 10,646 |
| lmstudio | DeepSeek | 1 | 3,530 |
| lmstudio | Meta | 1 | 59 |

⚠️ marks a row where the tool's name and the company that served the tokens disagree. `claude` served by DeepSeek is a Claude Code build pointed at a DeepSeek backend: the interface is Claude Code, every token is DeepSeek, and Anthropic was paid nothing. Reading the CLI column alone would count it as Claude usage.


Add a `services` entry to the right account in `accounts.json` to fold any of these in. They are left under a placeholder rather than split across accounts by proportion, because that would invent numbers that look measured.

### Account x computer

| Account | MacBook Air M1 | HP Laptop Linux | ASUS Laptop Linux | Dell Inspiron Desktop Linux | Total |
|---|---|---|---|---|---|
| broodierchip@gmail.com | 17.56B | 6.37B | 266.15M | 2.13M | **24,192,377,034** |
| codehunterextreme@gmail.com | 11.04B | 3.87B | — | — | **14,906,276,689** |
| DeepSeek backend (~/.my-claude) | — | 1.41B | — | — | **1,409,787,623** |
| alexander.sorrell.it@gmail.com | 571.75M | 83.21M | — | — | **654,966,438** |
| API key (org 15a93e14-aabb-4293-8228-8c56a803d972) | — | 437.62K | — | — | **437,619** |
| **All** | **29.17B** | **11.73B** | **266.15M** | **2.13M** | **41,163,845,403** |

---

## broodierchip@gmail.com

**24,192,377,034 tokens** (58.8%) · 2,748 sessions · 133,816 turns · 66 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBook Air M1 | 17,557,582,699 | 72.6% |
| HP Laptop Linux | 6,366,517,046 | 26.3% |
| ASUS Laptop Linux | 266,146,676 | 1.1% |
| Dell Inspiron Desktop Linux | 2,130,613 | 0.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 24,156,212,641 |
| DeepSeek | 36,164,393 |
| — (no API call) | 0 |

| Model | Tokens |
|---|---:|
| `claude-opus-5` | 9,870,453,713 |
| `claude-opus-4-8` | 6,783,278,058 |
| `claude-opus-4-7` | 5,729,729,896 |
| `claude-fable-5` | 1,730,080,807 |
| `deepseek-v4-pro` | 36,142,409 |
| `claude-haiku-4-5-20251001` | 22,935,469 |
| `claude-sonnet-4-6` | 18,737,764 |
| `claude-opus-4-5-20251101` | 996,934 |
| `deepseek-v4-flash` | 21,984 |
| `<synthetic>` | 0 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 16,689,936 | 886,002,243 | 23,194,114,449 | 95,570,406 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## codehunterextreme@gmail.com

**14,906,276,689 tokens** (36.2%) · 2,187 sessions · 47,656 turns · 42 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBook Air M1 | 11,040,991,167 | 74.1% |
| HP Laptop Linux | 3,865,285,522 | 25.9% |

| Company | Tokens |
|---|---:|
| Anthropic | 14,906,276,689 |
| — (no API call) | 0 |

| Model | Tokens |
|---|---:|
| `claude-opus-4-8` | 8,518,897,791 |
| `claude-opus-5` | 5,129,905,512 |
| `claude-fable-5` | 1,255,508,734 |
| `claude-sonnet-5` | 1,583,992 |
| `claude-opus-4-7` | 380,660 |
| `<synthetic>` | 0 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 4,721,600 | 552,438,558 | 14,297,106,878 | 52,009,653 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## DeepSeek backend (~/.my-claude)

**1,409,787,623 tokens** (3.4%) · 6 sessions · 14,797 turns · 22 active days

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

**654,966,438 tokens** (1.6%) · 6 sessions · 3,216 turns · 8 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBook Air M1 | 571,753,755 | 87.3% |
| HP Laptop Linux | 83,212,683 | 12.7% |

| Company | Tokens |
|---|---:|
| Anthropic | 654,966,438 |
| — (no API call) | 0 |

| Model | Tokens |
|---|---:|
| `claude-opus-4-8` | 440,309,308 |
| `claude-sonnet-4-6` | 212,137,606 |
| `claude-haiku-4-5-20251001` | 2,519,524 |
| `<synthetic>` | 0 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 101,081 | 15,673,198 | 636,279,251 | 2,912,908 |

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

### MacBook Air M1

**29,170,327,621 tokens** across 3 login(s)

| Account | Tokens | Share |
|---|---:|---:|
| broodierchip@gmail.com | 17,557,582,699 |  60.2% |
| codehunterextreme@gmail.com | 11,040,991,167 |  37.9% |
| alexander.sorrell.it@gmail.com | 571,753,755 |   2.0% |

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

