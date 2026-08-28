# By account

_What each login spent, across every computer_

_Generated 2026-08-05T23:40:00-05:00 by `stats_page.py`. Do not edit by hand._

**43,985,918,776** tokens of Claude Code across 5 scanned computer(s) · **51,134,071,679** across every CLI on the 5 that ran `sessions.py`.

Those two are not added: the second contains the first. See [BY-COMPUTER.md](BY-COMPUTER.md) for the reconciliation.

Reports: [computers](BY-COMPUTER.md) · [accounts](BY-ACCOUNT.md) · [companies](BY-COMPANY.md) · [how it works](README.md)

---

_scans taken 2026-08-04 01:46:32 .. 2026-08-05 23:39:34_

The per-account total across computers is the number that matters: the same login gets driven from several machines and no machine can see another's sessions.

| Account | Tokens | Share | Computers | Sessions | Turns | |
|---|---:|---:|---:|---:|---:|---|
| **broodierchip@gmail.com** | 25,629,983,842 | 58.3% | 5 | 19,189 | 165,426 | ████████████████············ |
| **codehunterextreme@gmail.com** | 14,102,690,317 | 32.1% | 3 | 63 | 46,246 | █████████··················· |
| **alexander.sorrell.it@gmail.com** | 2,835,737,509 | 6.4% | 3 | 75 | 11,912 | ██·························· |
| **DeepSeek backend (~/.my-claude)** | 1,409,787,623 | 3.2% | 1 | 6 | 14,797 | █··························· |
| **user:2d4777822844** | 7,281,866 | 0.0% | 1 | 1 | 111 | █··························· |
| **API key (org 15a93e14-aabb-4293-8228-8c56a803d972)** | 437,619 | 0.0% | 1 | 1 | 18 | █··························· |
| **user:283b8e5b8e48** | 0 | 0.0% | 1 | 1 | 3 | ···························· |
| **All** | **43,985,918,776** | 100% | | | | |

## Across every CLI, by account

The table above is Claude Code only, because it is the one tool that writes its account email to disk. This one folds in every other CLI using the ownership declared in [`accounts.json`](accounts.json).

| Account | Tokens | Sessions | Via |
|---|---:|---:|---|
| **broodierchip@gmail.com** | 28,227,608,591 | 16,643 | claude 25.59B, gemini 2.60B _file_, claude → DeepSeek 36.16M |
| **codehunterextreme@gmail.com** | 14,182,695,417 | 58 | claude 14.18B |
| **alexander.sorrell.it@gmail.com** | 2,837,977,700 | 75 | claude 2.84B |
| **nefabious@gmail.com** | 76,724,862 | 5 | grok 76.72M _owner_ |
| **All attributed** | **45,325,006,570** | | |

`file` means the email was read out of that tool's own account file. `owner` means it was stated by the account holder and cannot be checked against anything on disk. Claude Code rows carry neither because the email is in the session record itself.

> ⚠️ **5,809,065,109 tokens have no account.** These tools record no identity on disk and none is declared for them yet:

| CLI | Company that served it | Sessions | Tokens |
|---|---|---:|---:|
| codex | OpenAI | 148 | 2,313,178,830 |
| claude ⚠️ | DeepSeek | 17 | 1,409,787,623 |
| copilot | — (no API call) | 36 | 1,123,159,069 |
| copilot | Anthropic | 27 | 442,116,658 |
| copilot | OpenAI | 28 | 290,553,542 |
| antigravity | Google | 59 | 210,631,215 |
| claude | Anthropic | 2 | 7,719,485 |
| kilocode | Google | 2 | 7,025,122 |
| antigravity ⚠️ | — (unidentified) | 3 | 4,671,253 |
| lmstudio | Mistral | 5 | 116,185 |
| lmstudio | — (unidentified) | 3 | 53,159 |
| kilocode | — (unidentified) | 1 | 38,733 |
| kilocode | xAI | 1 | 10,646 |
| lmstudio | DeepSeek | 1 | 3,530 |
| lmstudio | Meta | 1 | 59 |
| claude ⚠️ | — (no API call) | 1 | 0 |

⚠️ marks a row where the tool's name and the company that served the tokens disagree. `claude` served by DeepSeek is a Claude Code build pointed at a DeepSeek backend: the interface is Claude Code, every token is DeepSeek, and Anthropic was paid nothing. Reading the CLI column alone would count it as Claude usage.


Add a `services` entry to the right account in `accounts.json` to fold any of these in. They are left under a placeholder rather than split across accounts by proportion, because that would invent numbers that look measured.

### Account x computer

| Account | MacBook Air M1 | HP Laptop Linux | Dell Latitude 7480 Linux | ASUS Laptop Linux | Dell Inspiron Desktop Linux | Total |
|---|---|---|---|---|---|---|
| broodierchip@gmail.com | 17.48B | 6.37B | 1.51B | 266.15M | 2.13M | **25,629,983,842** |
| codehunterextreme@gmail.com | 10.44B | 3.64B | 26.78M | — | — | **14,102,690,317** |
| alexander.sorrell.it@gmail.com | 571.75M | 83.21M | 2.18B | — | — | **2,835,737,509** |
| DeepSeek backend (~/.my-claude) | — | 1.41B | — | — | — | **1,409,787,623** |
| user:2d4777822844 | — | — | 7.28M | — | — | **7,281,866** |
| API key (org 15a93e14-aabb-4293-8228-8c56a803d972) | — | 437.62K | — | — | — | **437,619** |
| user:283b8e5b8e48 | — | — | — | — | — | **0** |
| **All** | **28.49B** | **11.50B** | **3.73B** | **266.15M** | **2.13M** | **43,985,918,776** |

---

## broodierchip@gmail.com

**25,629,983,842 tokens** (58.3%) · 19,189 sessions · 165,426 turns · 66 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBook Air M1 | 17,484,791,342 | 68.2% |
| HP Laptop Linux | 6,365,568,232 | 24.8% |
| Dell Latitude 7480 Linux | 1,511,346,979 | 5.9% |
| ASUS Laptop Linux | 266,146,676 | 1.0% |
| Dell Inspiron Desktop Linux | 2,130,613 | 0.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 25,593,819,449 |
| DeepSeek | 36,164,393 |
| — (no API call) | 0 |

| Model | Tokens |
|---|---:|
| `claude-opus-5` | 10,104,981,704 |
| `claude-opus-4-8` | 8,043,095,219 |
| `claude-opus-4-7` | 5,729,729,896 |
| `claude-fable-5` | 1,670,549,994 |
| `deepseek-v4-pro` | 36,142,409 |
| `claude-haiku-4-5-20251001` | 25,337,571 |
| `claude-sonnet-4-6` | 18,737,764 |
| `claude-opus-4-5-20251101` | 996,934 |
| `claude-opus-4-6` | 390,367 |
| `deepseek-v4-flash` | 21,984 |
| `<synthetic>` | 0 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 338,161,481 | 1,132,866,128 | 24,046,423,568 | 112,532,665 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## codehunterextreme@gmail.com

**14,102,690,317 tokens** (32.1%) · 63 sessions · 46,246 turns · 41 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBook Air M1 | 10,435,790,468 | 74.0% |
| HP Laptop Linux | 3,640,123,785 | 25.8% |
| Dell Latitude 7480 Linux | 26,776,064 | 0.2% |

| Company | Tokens |
|---|---:|
| Anthropic | 14,102,690,317 |
| — (no API call) | 0 |

| Model | Tokens |
|---|---:|
| `claude-opus-4-8` | 8,536,244,905 |
| `claude-opus-5` | 4,308,972,026 |
| `claude-fable-5` | 1,255,508,734 |
| `claude-sonnet-5` | 1,583,992 |
| `claude-opus-4-7` | 380,660 |
| `<synthetic>` | 0 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 4,668,626 | 506,526,690 | 13,540,780,015 | 50,714,986 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## alexander.sorrell.it@gmail.com

**2,835,737,509 tokens** (6.4%) · 75 sessions · 11,912 turns · 31 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| Dell Latitude 7480 Linux | 2,180,771,071 | 76.9% |
| MacBook Air M1 | 571,753,755 | 20.2% |
| HP Laptop Linux | 83,212,683 | 2.9% |

| Company | Tokens |
|---|---:|
| Anthropic | 2,835,737,509 |
| — (no API call) | 0 |

| Model | Tokens |
|---|---:|
| `claude-opus-4-8` | 1,640,532,780 |
| `claude-fable-5` | 515,987,926 |
| `claude-opus-5` | 447,081,318 |
| `claude-sonnet-4-6` | 212,137,606 |
| `claude-opus-4-7` | 17,478,355 |
| `claude-haiku-4-5-20251001` | 2,519,524 |
| `<synthetic>` | 0 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 580,910 | 110,352,944 | 2,709,609,347 | 15,194,308 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## DeepSeek backend (~/.my-claude)

**1,409,787,623 tokens** (3.2%) · 6 sessions · 14,797 turns · 22 active days

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

## user:2d4777822844

**7,281,866 tokens** (0.0%) · 1 sessions · 111 turns · 1 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| Dell Latitude 7480 Linux | 7,281,866 | 100.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 7,281,866 |

| Model | Tokens |
|---|---:|
| `claude-sonnet-4-6` | 7,281,866 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 457 | 1,210,774 | 5,935,628 | 135,007 |

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

## user:283b8e5b8e48

**0 tokens** (0.0%) · 1 sessions · 3 turns · 1 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| Dell Latitude 7480 Linux | 0 | — |

| Company | Tokens |
|---|---:|
| — (no API call) | 0 |

| Model | Tokens |
|---|---:|
| `<synthetic>` | 0 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 0 | 0 | 0 | 0 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

