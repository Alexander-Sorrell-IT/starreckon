# By account

_What each login spent, across every computer_

_Generated 2026-08-06T06:57:50-05:00 by `stats_page.py`. Do not edit by hand._

**46,488,455,959** tokens of Claude Code across 5 scanned computer(s) · **53,770,418,140** across every CLI on the 5 that ran `sessions.py`.

Those two are not added: the second contains the first. See [BY-COMPUTER.md](BY-COMPUTER.md) for the reconciliation.

Reports: [computers](BY-COMPUTER.md) · [accounts](BY-ACCOUNT.md) · [companies](BY-COMPANY.md) · [how it works](README.md)

---

_scans taken 2026-08-06 00:50:35 .. 2026-08-06 06:17:15_

The per-account total across computers is the number that matters: the same login gets driven from several machines and no machine can see another's sessions.

| Account | Tokens | Share | Computers | Sessions | Turns | |
|---|---:|---:|---:|---:|---:|---|
| **second@example.com** | 27,243,452,762 | 58.6% | 5 | 19,220 | 185,528 | ████████████████············ |
| **third@example.com** | 14,933,052,753 | 32.1% | 3 | 2,189 | 47,879 | █████████··················· |
| **owner@example.com** | 2,894,443,336 | 6.2% | 3 | 79 | 12,419 | ██·························· |
| **DeepSeek backend (~/.my-claude)** | 1,409,787,623 | 3.0% | 1 | 6 | 14,797 | █··························· |
| **user:2d4777822844** | 7,281,866 | 0.0% | 1 | 1 | 111 | █··························· |
| **API key (org 15a93e14-aabb-4293-8228-8c56a803d972)** | 437,619 | 0.0% | 1 | 1 | 18 | █··························· |
| **user:283b8e5b8e48** | 0 | 0.0% | 1 | 1 | 3 | ···························· |
| **All** | **46,488,455,959** | 100% | | | | |

## Across every CLI, by account

The table above is Claude Code only, because it is the one tool that writes its account email to disk. This one folds in every other CLI using the ownership declared in [`accounts.json`](accounts.json).

| Account | Tokens | Sessions | Via |
|---|---:|---:|---|
| **second@example.com** | 30,034,663,244 | 16,704 | claude 27.21B, gemini 2.79B _file_, claude → DeepSeek 36.16M |
| **third@example.com** | 14,934,001,567 | 62 | claude 14.93B |
| **owner@example.com** | 2,894,658,464 | 79 | claude 2.89B |
| **fourth@example.com** | 90,209,318 | 6 | grok 90.21M _owner_ |
| **All attributed** | **47,953,532,593** | | |

`file` means the email was read out of that tool's own account file. `owner` means it was stated by the account holder and cannot be checked against anything on disk. Claude Code rows carry neither because the email is in the session record itself.

> ⚠️ **5,816,885,547 tokens have no account.** These tools record no identity on disk and none is declared for them yet:

| CLI | Company that served it | Sessions | Tokens |
|---|---|---:|---:|
| codex | OpenAI | 148 | 2,313,579,758 |
| claude ⚠️ | DeepSeek | 17 | 1,409,787,623 |
| copilot | — (no API call) | 36 | 1,123,159,069 |
| copilot | Anthropic | 27 | 442,116,658 |
| copilot | OpenAI | 28 | 290,553,542 |
| antigravity | Google | 63 | 222,721,978 |
| claude | Anthropic | 2 | 7,719,485 |
| kilocode | Google | 2 | 7,025,122 |
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
| second@example.com | 17.56B | 6.37B | 3.05B | 266.15M | 2.13M | **27,243,452,762** |
| third@example.com | 11.04B | 3.87B | 26.78M | — | — | **14,933,052,753** |
| owner@example.com | 571.75M | 83.21M | 2.24B | — | — | **2,894,443,336** |
| DeepSeek backend (~/.my-claude) | — | 1.41B | — | — | — | **1,409,787,623** |
| user:2d4777822844 | — | — | 7.28M | — | — | **7,281,866** |
| API key (org 15a93e14-aabb-4293-8228-8c56a803d972) | — | 437.62K | — | — | — | **437,619** |
| user:283b8e5b8e48 | — | — | — | — | — | **0** |
| **All** | **29.17B** | **11.73B** | **5.32B** | **266.15M** | **2.13M** | **46,488,455,959** |

---

## second@example.com

**27,243,452,762 tokens** (58.6%) · 19,220 sessions · 185,528 turns · 85 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBook Air M1 | 17,557,582,699 | 64.4% |
| HP Laptop Linux | 6,366,517,046 | 23.4% |
| Dell Latitude 7480 Linux | 3,051,075,728 | 11.2% |
| ASUS Laptop Linux | 266,146,676 | 1.0% |
| Dell Inspiron Desktop Linux | 2,130,613 | 0.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 27,207,288,369 |
| DeepSeek | 36,164,393 |
| — (no API call) | 0 |

| Model | Tokens |
|---|---:|
| `claude-opus-5` | 10,119,411,148 |
| `claude-opus-4-8` | 8,042,875,133 |
| `claude-opus-4-7` | 5,729,729,896 |
| `claude-fable-5` | 1,730,080,807 |
| `claude-opus-4-6` | 834,041,599 |
| `claude-opus-4-5-20251101` | 575,579,698 |
| `claude-haiku-4-5-20251001` | 134,283,984 |
| `deepseek-v4-pro` | 36,142,409 |
| `claude-sonnet-4-6` | 24,981,514 |
| `claude-sonnet-4-5-20250929` | 16,304,590 |
| `deepseek-v4-flash` | 21,984 |
| `<synthetic>` | 0 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 339,928,130 | 1,282,574,726 | 25,506,321,472 | 114,628,434 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## third@example.com

**14,933,052,753 tokens** (32.1%) · 2,189 sessions · 47,879 turns · 42 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBook Air M1 | 11,040,991,167 | 73.9% |
| HP Laptop Linux | 3,865,285,522 | 25.9% |
| Dell Latitude 7480 Linux | 26,776,064 | 0.2% |

| Company | Tokens |
|---|---:|
| Anthropic | 14,933,052,753 |
| — (no API call) | 0 |

| Model | Tokens |
|---|---:|
| `claude-opus-4-8` | 8,545,673,855 |
| `claude-opus-5` | 5,129,905,512 |
| `claude-fable-5` | 1,255,508,734 |
| `claude-sonnet-5` | 1,583,992 |
| `claude-opus-4-7` | 380,660 |
| `<synthetic>` | 0 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 4,732,674 | 555,837,016 | 14,320,266,513 | 52,216,550 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## owner@example.com

**2,894,443,336 tokens** (6.2%) · 79 sessions · 12,419 turns · 32 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| Dell Latitude 7480 Linux | 2,239,476,898 | 77.4% |
| MacBook Air M1 | 571,753,755 | 19.8% |
| HP Laptop Linux | 83,212,683 | 2.9% |

| Company | Tokens |
|---|---:|
| Anthropic | 2,894,443,336 |
| — (no API call) | 0 |

| Model | Tokens |
|---|---:|
| `claude-opus-4-8` | 1,640,532,780 |
| `claude-fable-5` | 515,987,926 |
| `claude-opus-5` | 504,799,256 |
| `claude-sonnet-4-6` | 212,137,606 |
| `claude-opus-4-7` | 18,466,244 |
| `claude-haiku-4-5-20251001` | 2,519,524 |
| `<synthetic>` | 0 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 583,985 | 112,570,210 | 2,765,544,970 | 15,744,171 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## DeepSeek backend (~/.my-claude)

**1,409,787,623 tokens** (3.0%) · 6 sessions · 14,797 turns · 22 active days

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

---

## Each computer

_The same accounts, grouped by machine. One login is usually driven from several computers, and no computer can see another's sessions — which is why the account totals above exist at all._

### MacBook Air M1

**29,170,327,621 tokens** across 3 login(s)

| Account | Tokens | Share |
|---|---:|---:|
| second@example.com | 17,557,582,699 |  60.2% |
| third@example.com | 11,040,991,167 |  37.9% |
| owner@example.com | 571,753,755 |   2.0% |

### HP Laptop Linux

**11,725,240,493 tokens** across 5 login(s)

| Account | Tokens | Share |
|---|---:|---:|
| second@example.com | 6,366,517,046 |  54.3% |
| third@example.com | 3,865,285,522 |  33.0% |
| DeepSeek backend (~/.my-claude) | 1,409,787,623 |  12.0% |
| owner@example.com | 83,212,683 |   0.7% |
| API key (org 15a93e14-aabb-4293-8228-8c56a803d972) | 437,619 |   0.0% |

### Dell Latitude 7480 Linux

**5,324,610,556 tokens** across 5 login(s)

| Account | Tokens | Share |
|---|---:|---:|
| second@example.com | 3,051,075,728 |  57.3% |
| owner@example.com | 2,239,476,898 |  42.1% |
| third@example.com | 26,776,064 |   0.5% |
| user:2d4777822844 | 7,281,866 |   0.1% |
| user:283b8e5b8e48 | 0 |   0.0% |

### ASUS Laptop Linux

**266,146,676 tokens** across 1 login(s)

| Account | Tokens | Share |
|---|---:|---:|
| second@example.com | 266,146,676 | 100.0% |

### Dell Inspiron Desktop Linux

**2,130,613 tokens** across 1 login(s)

| Account | Tokens | Share |
|---|---:|---:|
| second@example.com | 2,130,613 | 100.0% |

