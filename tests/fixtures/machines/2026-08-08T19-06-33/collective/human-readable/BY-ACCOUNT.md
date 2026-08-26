# By account

_What each login spent, across every computer_

_Generated 2026-08-08T15:30:53-05:00 by `stats_page.py`. Do not edit by hand._

**47,977,825,597** tokens of Claude Code across 6 scanned computer(s) · **48,660,830,354** across every CLI on the 5 that ran `sessions.py`.

Those two are not added: the second contains the first. See [BY-COMPUTER.md](BY-COMPUTER.md) for the reconciliation.

Reports: [computers](BY-COMPUTER.md) · [accounts](BY-ACCOUNT.md) · [companies](BY-COMPANY.md) · [how it works](README.md)

---

_scans taken 2026-08-06 00:50:35 .. 2026-08-08 15:30:18_

The per-account total across computers is the number that matters: the same login gets driven from several machines and no machine can see another's sessions.

| Account | Tokens | Share | Computers | Sessions | Turns | |
|---|---:|---:|---:|---:|---:|---|
| **broodierchip@gmail.com** | 26,046,851,416 | 54.3% | 6 | 22,078 | 176,245 | ███████████████············· |
| **codehunterextreme@gmail.com** | 16,994,468,769 | 35.4% | 4 | 2,203 | 52,794 | ██████████·················· |
| **alexander.sorrell.it@gmail.com** | 2,898,894,295 | 6.0% | 4 | 81 | 12,442 | ██·························· |
| **DeepSeek backend (~/.my-claude)** | 1,040,995,586 | 2.2% | 2 | 12 | 10,202 | █··························· |
| **unknown (Desktop_standout_clean_.claude)** | 642,203,454 | 1.3% | 2 | 840 | 4,196 | █··························· |
| **unknown (Desktop_standout_full_.claude)** | 335,659,608 | 0.7% | 2 | 1,610 | 4,954 | █··························· |
| **unknown (Desktop_standout_max_.claude)** | 9,338,718 | 0.0% | 2 | 1,610 | 40 | █··························· |
| **user:2d4777822844** | 7,281,866 | 0.0% | 1 | 1 | 111 | █··························· |
| **unknown (.claude-alt)** | 1,849,465 | 0.0% | 2 | 54 | 2 | █··························· |
| **API key (org 15a93e14-aabb-4293-8228-8c56a803d972)** | 282,420 | 0.0% | 2 | 2 | 12 | █··························· |
| **unknown (.claude-alt-api)** | 0 | 0.0% | 2 | 2 | 0 | ···························· |
| **unknown (.claude-it)** | 0 | 0.0% | 2 | 4 | 0 | ···························· |
| **unknown (.my-claude)** | 0 | 0.0% | 2 | 12 | 0 | ···························· |
| **unknown (Desktop_standout_sandbox_.claude)** | 0 | 0.0% | 2 | 1,152 | 0 | ···························· |
| **unknown (claude)** | 0 | 0.0% | 2 | 168 | 0 | ···························· |
| **unknown (claude-alt)** | 0 | 0.0% | 2 | 54 | 0 | ···························· |
| **unknown (claude-alt-api)** | 0 | 0.0% | 2 | 2 | 0 | ···························· |
| **unknown (claude-it)** | 0 | 0.0% | 2 | 4 | 0 | ···························· |
| **unknown (my-claude)** | 0 | 0.0% | 2 | 12 | 0 | ···························· |
| **user:283b8e5b8e48** | 0 | 0.0% | 1 | 1 | 3 | ···························· |
| **All** | **47,977,825,597** | 100% | | | | |

## Across every CLI, by account

The table above is Claude Code only, because it is the one tool that writes its account email to disk. This one folds in every other CLI using the ownership declared in [`accounts.json`](accounts.json).

| Account | Tokens | Sessions | Via |
|---|---:|---:|---|
| **broodierchip@gmail.com** | 26,257,761,472 | 16,682 | claude 23.45B, gemini 2.79B _file_, claude → DeepSeek 14.17M, claude → — (no API call) 49.99K |
| **codehunterextreme@gmail.com** | 14,040,538,604 | 49 | claude 14.04B |
| **alexander.sorrell.it@gmail.com** | 2,855,557,193 | 79 | claude 2.86B |
| **nefabious@gmail.com** | 90,209,318 | 6 | grok 90.21M _owner_ |
| **All attributed** | **43,244,066,587** | | |

`file` means the email was read out of that tool's own account file. `owner` means it was stated by the account holder and cannot be checked against anything on disk. Claude Code rows carry neither because the email is in the session record itself.

> ⚠️ **5,416,763,767 tokens have no account.** These tools record no identity on disk and none is declared for them yet:

| CLI | Company that served it | Sessions | Tokens |
|---|---|---:|---:|
| codex | OpenAI | 148 | 2,313,579,758 |
| copilot | — (no API call) | 36 | 1,123,159,069 |
| claude ⚠️ | DeepSeek | 17 | 520,497,793 |
| claude | Anthropic | 43 | 496,887,535 |
| copilot | Anthropic | 27 | 442,116,658 |
| copilot | OpenAI | 28 | 290,553,542 |
| antigravity | Google | 63 | 222,721,978 |
| kilocode | Google | 2 | 7,025,122 |
| lmstudio | Mistral | 5 | 116,185 |
| lmstudio | — (unidentified) | 3 | 53,159 |
| kilocode | — (unidentified) | 1 | 38,733 |
| kilocode | xAI | 1 | 10,646 |
| lmstudio | DeepSeek | 1 | 3,530 |
| lmstudio | Meta | 1 | 59 |
| claude ⚠️ | — (no API call) | 2 | 0 |

⚠️ marks a row where the tool's name and the company that served the tokens disagree. `claude` served by DeepSeek is a Claude Code build pointed at a DeepSeek backend: the interface is Claude Code, every token is DeepSeek, and Anthropic was paid nothing. Reading the CLI column alone would count it as Claude usage.


Add a `services` entry to the right account in `accounts.json` to fold any of these in. They are left under a placeholder rather than split across accounts by proportion, because that would invent numbers that look measured.

### Account x computer

| Account | MacBook Air M1 | HP Laptop Linux | HP-Phantom-Core | Dell Latitude 7480 Linux | ASUS Laptop Linux | Dell Inspiron Desktop Linux | Total |
|---|---|---|---|---|---|---|---|
| broodierchip@gmail.com | 17.56B | 2.58B | 2.58B | 3.05B | 266.15M | 2.13M | **26,046,851,416** |
| codehunterextreme@gmail.com | 11.04B | 2.97B | 2.96B | 26.78M | — | — | **16,994,468,769** |
| alexander.sorrell.it@gmail.com | 571.75M | 43.83M | 43.83M | 2.24B | — | — | **2,898,894,295** |
| DeepSeek backend (~/.my-claude) | — | 520.50M | 520.50M | — | — | — | **1,040,995,586** |
| unknown (Desktop_standout_clean_.claude) | — | 321.10M | 321.10M | — | — | — | **642,203,454** |
| unknown (Desktop_standout_full_.claude) | — | 167.83M | 167.83M | — | — | — | **335,659,608** |
| unknown (Desktop_standout_max_.claude) | — | 4.67M | 4.67M | — | — | — | **9,338,718** |
| user:2d4777822844 | — | — | — | 7.28M | — | — | **7,281,866** |
| unknown (.claude-alt) | — | 936.21K | 913.26K | — | — | — | **1,849,465** |
| API key (org 15a93e14-aabb-4293-8228-8c56a803d972) | — | 141.21K | 141.21K | — | — | — | **282,420** |
| unknown (.claude-alt-api) | — | — | — | — | — | — | **0** |
| unknown (.claude-it) | — | — | — | — | — | — | **0** |
| unknown (.my-claude) | — | — | — | — | — | — | **0** |
| unknown (Desktop_standout_sandbox_.claude) | — | — | — | — | — | — | **0** |
| unknown (claude) | — | — | — | — | — | — | **0** |
| unknown (claude-alt) | — | — | — | — | — | — | **0** |
| unknown (claude-alt-api) | — | — | — | — | — | — | **0** |
| unknown (claude-it) | — | — | — | — | — | — | **0** |
| unknown (my-claude) | — | — | — | — | — | — | **0** |
| user:283b8e5b8e48 | — | — | — | — | — | — | **0** |
| **All** | **29.17B** | **6.62B** | **6.60B** | **5.32B** | **266.15M** | **2.13M** | **47,977,825,597** |

---

## broodierchip@gmail.com

**26,046,851,416 tokens** (54.3%) · 22,078 sessions · 176,245 turns · 79 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBook Air M1 | 17,557,582,699 | 67.4% |
| Dell Latitude 7480 Linux | 3,051,075,728 | 11.7% |
| HP Laptop Linux | 2,584,957,850 | 9.9% |
| HP-Phantom-Core | 2,584,957,850 | 9.9% |
| ASUS Laptop Linux | 266,146,676 | 1.0% |
| Dell Inspiron Desktop Linux | 2,130,613 | 0.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 26,018,504,696 |
| DeepSeek | 28,346,720 |
| — (no API call) | 0 |

| Model | Tokens |
|---|---:|
| `claude-opus-5` | 10,118,462,334 |
| `claude-opus-4-8` | 7,313,498,456 |
| `claude-opus-4-7` | 5,360,255,495 |
| `claude-fable-5` | 1,642,149,368 |
| `claude-opus-4-6` | 834,041,599 |
| `claude-opus-4-5-20251101` | 575,579,698 |
| `claude-haiku-4-5-20251001` | 131,309,164 |
| `deepseek-v4-pro` | 28,324,718 |
| `claude-sonnet-4-6` | 26,903,992 |
| `claude-sonnet-4-5-20250929` | 16,304,590 |
| `deepseek-v4-flash` | 22,002 |
| `<synthetic>` | 0 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 336,351,461 | 1,179,113,461 | 24,427,858,198 | 103,528,296 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## codehunterextreme@gmail.com

**16,994,468,769 tokens** (35.4%) · 2,203 sessions · 52,794 turns · 35 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBook Air M1 | 11,040,991,167 | 65.0% |
| HP Laptop Linux | 2,971,668,539 | 17.5% |
| HP-Phantom-Core | 2,955,032,999 | 17.4% |
| Dell Latitude 7480 Linux | 26,776,064 | 0.2% |

| Company | Tokens |
|---|---:|
| Anthropic | 16,994,468,769 |
| — (no API call) | 0 |

| Model | Tokens |
|---|---:|
| `claude-opus-4-8` | 8,019,037,108 |
| `claude-opus-5` | 7,837,235,743 |
| `claude-fable-5` | 1,135,990,094 |
| `claude-sonnet-5` | 1,825,164 |
| `claude-opus-4-7` | 380,660 |
| `<synthetic>` | 0 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 2,382,404 | 540,628,286 | 16,388,960,531 | 62,497,548 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## alexander.sorrell.it@gmail.com

**2,898,894,295 tokens** (6.0%) · 81 sessions · 12,442 turns · 32 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| Dell Latitude 7480 Linux | 2,239,476,898 | 77.3% |
| MacBook Air M1 | 571,753,755 | 19.7% |
| HP Laptop Linux | 43,831,821 | 1.5% |
| HP-Phantom-Core | 43,831,821 | 1.5% |

| Company | Tokens |
|---|---:|
| Anthropic | 2,898,894,295 |
| — (no API call) | 0 |

| Model | Tokens |
|---|---:|
| `claude-opus-4-8` | 1,640,532,780 |
| `claude-fable-5` | 515,987,926 |
| `claude-opus-5` | 504,799,256 |
| `claude-sonnet-4-6` | 217,617,037 |
| `claude-opus-4-7` | 18,466,244 |
| `claude-haiku-4-5-20251001` | 1,491,052 |
| `<synthetic>` | 0 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 581,191 | 112,233,397 | 2,770,406,861 | 15,672,846 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## DeepSeek backend (~/.my-claude)

**1,040,995,586 tokens** (2.2%) · 12 sessions · 10,202 turns · 22 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 520,497,793 | 50.0% |
| HP-Phantom-Core | 520,497,793 | 50.0% |

| Company | Tokens |
|---|---:|
| DeepSeek | 1,040,995,586 |

| Model | Tokens |
|---|---:|
| `deepseek-v4-pro` | 973,034,134 |
| `deepseek-v4-flash` | 67,961,452 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 43,592,882 | 0 | 987,412,992 | 9,989,712 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## unknown (Desktop_standout_clean_.claude)

**642,203,454 tokens** (1.3%) · 840 sessions · 4,196 turns · 13 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 321,101,727 | 50.0% |
| HP-Phantom-Core | 321,101,727 | 50.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 642,203,454 |

| Model | Tokens |
|---|---:|
| `claude-opus-4-8` | 548,139,116 |
| `claude-fable-5` | 94,064,338 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 1,114,034 | 28,536,290 | 608,755,150 | 3,797,980 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## unknown (Desktop_standout_full_.claude)

**335,659,608 tokens** (0.7%) · 1,610 sessions · 4,954 turns · 11 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 167,829,804 | 50.0% |
| HP-Phantom-Core | 167,829,804 | 50.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 335,659,608 |

| Model | Tokens |
|---|---:|
| `claude-opus-4-8` | 329,063,270 |
| `claude-haiku-4-5-20251001` | 4,450,200 |
| `claude-fable-5` | 2,146,138 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 1,456,856 | 31,270,800 | 297,882,938 | 5,049,014 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## unknown (Desktop_standout_max_.claude)

**9,338,718 tokens** (0.0%) · 1,610 sessions · 40 turns · 10 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 4,669,359 | 50.0% |
| HP-Phantom-Core | 4,669,359 | 50.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 9,338,718 |

| Model | Tokens |
|---|---:|
| `claude-opus-4-7` | 7,417,220 |
| `claude-opus-4-8` | 945,914 |
| `claude-sonnet-4-6` | 559,182 |
| `claude-fable-5` | 416,402 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 9,056 | 104,706 | 9,164,288 | 60,668 |

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

## unknown (.claude-alt)

**1,849,465 tokens** (0.0%) · 54 sessions · 2 turns · 1 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 936,209 | 50.6% |
| HP-Phantom-Core | 913,256 | 49.4% |

| Company | Tokens |
|---|---:|
| Anthropic | 1,849,465 |

| Model | Tokens |
|---|---:|
| `claude-opus-5` | 1,849,465 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 4 | 1,097 | 1,847,776 | 588 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## API key (org 15a93e14-aabb-4293-8228-8c56a803d972)

**282,420 tokens** (0.0%) · 2 sessions · 12 turns · 1 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 141,210 | 50.0% |
| HP-Phantom-Core | 141,210 | 50.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 282,420 |

| Model | Tokens |
|---|---:|
| `claude-opus-4-8` | 152,304 |
| `claude-fable-5` | 130,116 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 3,844 | 21,728 | 250,396 | 6,452 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## unknown (.claude-alt-api)

**0 tokens** (0.0%) · 2 sessions · 0 turns · 0 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 0 | — |
| HP-Phantom-Core | 0 | — |

| Company | Tokens |
|---|---:|

| Model | Tokens |
|---|---:|

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 0 | 0 | 0 | 0 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## unknown (.claude-it)

**0 tokens** (0.0%) · 4 sessions · 0 turns · 0 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 0 | — |
| HP-Phantom-Core | 0 | — |

| Company | Tokens |
|---|---:|

| Model | Tokens |
|---|---:|

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 0 | 0 | 0 | 0 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## unknown (.my-claude)

**0 tokens** (0.0%) · 12 sessions · 0 turns · 0 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 0 | — |
| HP-Phantom-Core | 0 | — |

| Company | Tokens |
|---|---:|

| Model | Tokens |
|---|---:|

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 0 | 0 | 0 | 0 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## unknown (Desktop_standout_sandbox_.claude)

**0 tokens** (0.0%) · 1,152 sessions · 0 turns · 0 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 0 | — |
| HP-Phantom-Core | 0 | — |

| Company | Tokens |
|---|---:|

| Model | Tokens |
|---|---:|

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 0 | 0 | 0 | 0 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## unknown (claude)

**0 tokens** (0.0%) · 168 sessions · 0 turns · 0 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 0 | — |
| HP-Phantom-Core | 0 | — |

| Company | Tokens |
|---|---:|

| Model | Tokens |
|---|---:|

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 0 | 0 | 0 | 0 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## unknown (claude-alt)

**0 tokens** (0.0%) · 54 sessions · 0 turns · 0 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 0 | — |
| HP-Phantom-Core | 0 | — |

| Company | Tokens |
|---|---:|

| Model | Tokens |
|---|---:|

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 0 | 0 | 0 | 0 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## unknown (claude-alt-api)

**0 tokens** (0.0%) · 2 sessions · 0 turns · 0 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 0 | — |
| HP-Phantom-Core | 0 | — |

| Company | Tokens |
|---|---:|

| Model | Tokens |
|---|---:|

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 0 | 0 | 0 | 0 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## unknown (claude-it)

**0 tokens** (0.0%) · 4 sessions · 0 turns · 0 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 0 | — |
| HP-Phantom-Core | 0 | — |

| Company | Tokens |
|---|---:|

| Model | Tokens |
|---|---:|

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 0 | 0 | 0 | 0 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## unknown (my-claude)

**0 tokens** (0.0%) · 12 sessions · 0 turns · 0 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 0 | — |
| HP-Phantom-Core | 0 | — |

| Company | Tokens |
|---|---:|

| Model | Tokens |
|---|---:|

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 0 | 0 | 0 | 0 |

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
| broodierchip@gmail.com | 17,557,582,699 |  60.2% |
| codehunterextreme@gmail.com | 11,040,991,167 |  37.9% |
| alexander.sorrell.it@gmail.com | 571,753,755 |   2.0% |

### HP Laptop Linux

**6,615,634,312 tokens** across 18 login(s)

| Account | Tokens | Share |
|---|---:|---:|
| codehunterextreme@gmail.com | 2,971,668,539 |  44.9% |
| broodierchip@gmail.com | 2,584,957,850 |  39.1% |
| DeepSeek backend (~/.my-claude) | 520,497,793 |   7.9% |
| unknown (Desktop_standout_clean_.claude) | 321,101,727 |   4.9% |
| unknown (Desktop_standout_full_.claude) | 167,829,804 |   2.5% |
| alexander.sorrell.it@gmail.com | 43,831,821 |   0.7% |
| unknown (Desktop_standout_max_.claude) | 4,669,359 |   0.1% |
| unknown (.claude-alt) | 936,209 |   0.0% |
| API key (org 15a93e14-aabb-4293-8228-8c56a803d972) | 141,210 |   0.0% |
| unknown (.claude-alt-api) | 0 |   0.0% |
| unknown (.claude-it) | 0 |   0.0% |
| unknown (.my-claude) | 0 |   0.0% |
| unknown (Desktop_standout_sandbox_.claude) | 0 |   0.0% |
| unknown (claude) | 0 |   0.0% |
| unknown (claude-alt) | 0 |   0.0% |
| unknown (claude-alt-api) | 0 |   0.0% |
| unknown (claude-it) | 0 |   0.0% |
| unknown (my-claude) | 0 |   0.0% |

### HP-Phantom-Core

**6,598,975,819 tokens** across 18 login(s)

| Account | Tokens | Share |
|---|---:|---:|
| codehunterextreme@gmail.com | 2,955,032,999 |  44.8% |
| broodierchip@gmail.com | 2,584,957,850 |  39.2% |
| DeepSeek backend (~/.my-claude) | 520,497,793 |   7.9% |
| unknown (Desktop_standout_clean_.claude) | 321,101,727 |   4.9% |
| unknown (Desktop_standout_full_.claude) | 167,829,804 |   2.5% |
| alexander.sorrell.it@gmail.com | 43,831,821 |   0.7% |
| unknown (Desktop_standout_max_.claude) | 4,669,359 |   0.1% |
| unknown (.claude-alt) | 913,256 |   0.0% |
| API key (org 15a93e14-aabb-4293-8228-8c56a803d972) | 141,210 |   0.0% |
| unknown (.claude-alt-api) | 0 |   0.0% |
| unknown (.claude-it) | 0 |   0.0% |
| unknown (.my-claude) | 0 |   0.0% |
| unknown (Desktop_standout_sandbox_.claude) | 0 |   0.0% |
| unknown (claude) | 0 |   0.0% |
| unknown (claude-alt) | 0 |   0.0% |
| unknown (claude-alt-api) | 0 |   0.0% |
| unknown (claude-it) | 0 |   0.0% |
| unknown (my-claude) | 0 |   0.0% |

### Dell Latitude 7480 Linux

**5,324,610,556 tokens** across 5 login(s)

| Account | Tokens | Share |
|---|---:|---:|
| broodierchip@gmail.com | 3,051,075,728 |  57.3% |
| alexander.sorrell.it@gmail.com | 2,239,476,898 |  42.1% |
| codehunterextreme@gmail.com | 26,776,064 |   0.5% |
| user:2d4777822844 | 7,281,866 |   0.1% |
| user:283b8e5b8e48 | 0 |   0.0% |

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

