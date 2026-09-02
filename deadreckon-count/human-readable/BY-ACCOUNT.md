# By account

_What each login spent, across every computer_

_Generated 2026-09-01T06:49:42-05:00 by `stats_page.py`. Do not edit by hand._

**29,583,611,349** tokens of Claude Code across 2 scanned computer(s) · **40,912,910,876** across every CLI on the 2 that ran `sessions.py`.

Those two are not added: the second contains the first. See [BY-COMPUTER.md](BY-COMPUTER.md) for the reconciliation.

Reports: [computers](BY-COMPUTER.md) · [accounts](BY-ACCOUNT.md) · [companies](BY-COMPANY.md) · [how it works](README.md)

---

_scans taken 2026-08-19 21:24:07 .. 2026-09-01 06:48:33_

The per-account total across computers is the number that matters: the same login gets driven from several machines and no machine can see another's sessions.

| Account | Tokens | Share | Computers | Sessions | Turns | |
|---|---:|---:|---:|---:|---:|---|
| **broodierchip@gmail.com** | 15,201,382,120 | 51.4% | 2 | 330 | 68,503 | ██████████████·············· |
| **codehunterextreme@gmail.com** | 13,383,775,040 | 45.2% | 2 | 171 | 59,583 | █████████████··············· |
| **DeepSeek backend (~/.my-claude)** | 520,497,793 | 1.8% | 1 | 18 | 5,101 | █··························· |
| **alexander.sorrell.it@gmail.com** | 467,800,272 | 1.6% | 2 | 30 | 2,288 | █··························· |
| **unknown (Documents)** | 10,014,914 | 0.0% | 1 | 4,360 | 106 | █··························· |
| **API key (org 15a93e14-aabb-4293-8228-8c56a803d972)** | 141,210 | 0.0% | 1 | 3 | 6 | █··························· |
| **All** | **29,583,611,349** | 100% | | | | |

## Across every CLI, by account

The table above is Claude Code only, because it is the one tool that writes its account email to disk. This one folds in every other CLI using the ownership declared in [`accounts.json`](accounts.json).

| Account | Tokens | Sessions | Via |
|---|---:|---:|---|
| **broodierchip@gmail.com** | 17,694,935,200 | 153 | claude 17.65B, claude → — (no API call) 31.89M, claude → DeepSeek 14.17M |
| **codehunterextreme@gmail.com** | 16,236,735,611 | 120 | claude 16.24B |
| **alexsorrellyan@gmail.com** | 5,118,098,175 | 313 | gemini 2.46B _owner_, codex 1.64B _owner_, copilot 437.66M _owner_, copilot 290.55M _owner_, antigravity 218.71M _owner_, copilot 65.31M _owner_, kilocode 7.03M _owner_, kilocode 38.73K _owner_, kilocode 10.65K _owner_ |
| **alexander.sorrell.it@gmail.com** | 467,800,272 | 14 | claude 467.80M |
| **nefabious@gmail.com** | 100,222,322 | 8 | grok 100.22M _owner_ |
| **All attributed** | **39,617,791,580** | | |

`file` means the email was read out of that tool's own account file. `owner` means it was stated by the account holder and cannot be checked against anything on disk. Claude Code rows carry neither because the email is in the session record itself.

> ⚠️ **1,295,119,296 tokens have no account.** These tools record no identity on disk and none is declared for them yet:

| CLI | Company that served it | Sessions | Tokens |
|---|---|---:|---:|
| claude ⚠️ | DeepSeek | 21 | 529,474,038 |
| bob | None | 5 | 272,617,335 |
| clawspring | — (no API call) | 20 | 258,503,636 |
| bob | — (unidentified) | 59 | 229,043,592 |
| claude | Anthropic | 6 | 4,093,492 |
| copilot-chat | GitHub | 11 | 1,214,160 |
| lmstudio | Mistral | 5 | 116,185 |
| lmstudio | — (unidentified) | 3 | 53,159 |
| lmstudio | DeepSeek | 1 | 3,530 |
| lmstudio | — (no API call) | 1 | 110 |
| lmstudio | Meta | 1 | 59 |

⚠️ marks a row where the tool's name and the company that served the tokens disagree. `claude` served by DeepSeek is a Claude Code build pointed at a DeepSeek backend: the interface is Claude Code, every token is DeepSeek, and Anthropic was paid nothing. Reading the CLI column alone would count it as Claude usage.


Add a `services` entry to the right account in `accounts.json` to fold any of these in. They are left under a placeholder rather than split across accounts by proportion, because that would invent numbers that look measured.

> ⚠️ **Known account(s) with no usage found anywhere:** `alexsorrellit@gmail.com`.

### Account x computer

| Account | MacBook Air M1 | HP Laptop Linux | Total |
|---|---|---|---|
| broodierchip@gmail.com | 12.46B | 2.74B | **15,201,382,120** |
| codehunterextreme@gmail.com | 5.32B | 8.06B | **13,383,775,040** |
| DeepSeek backend (~/.my-claude) | — | 520.50M | **520,497,793** |
| alexander.sorrell.it@gmail.com | 243.95M | 223.85M | **467,800,272** |
| unknown (Documents) | 10.01M | — | **10,014,914** |
| API key (org 15a93e14-aabb-4293-8228-8c56a803d972) | — | 141.21K | **141,210** |
| **All** | **18.03B** | **11.55B** | **29,583,611,349** |

---

## broodierchip@gmail.com

**15,201,382,120 tokens** (51.4%) · 330 sessions · 68,503 turns · 62 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBook Air M1 | 12,456,931,683 | 81.9% |
| HP Laptop Linux | 2,744,450,437 | 18.1% |

| Company | Tokens |
|---|---:|
| Anthropic | 15,187,208,760 |
| DeepSeek | 14,173,360 |

| Model | Tokens |
|---|---:|
| `claude-opus-5` | 9,442,032,194 |
| `claude-opus-4-7` | 2,552,286,127 |
| `claude-opus-4-8` | 2,370,684,661 |
| `claude-fable-5` | 808,080,081 |
| `deepseek-v4-pro` | 14,162,359 |
| `claude-sonnet-4-6` | 10,330,121 |
| `claude-haiku-4-5-20251001` | 3,795,576 |
| `deepseek-v4-flash` | 11,001 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 5,467,228 | 396,057,965 | 14,729,674,597 | 70,182,330 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## codehunterextreme@gmail.com

**13,383,775,040 tokens** (45.2%) · 171 sessions · 59,583 turns · 45 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 8,062,476,061 | 60.2% |
| MacBook Air M1 | 5,321,298,979 | 39.8% |

| Company | Tokens |
|---|---:|
| Anthropic | 13,383,775,040 |

| Model | Tokens |
|---|---:|
| `claude-opus-5` | 9,095,922,400 |
| `claude-opus-4-8` | 3,160,211,654 |
| `claude-fable-5` | 1,126,535,769 |
| `claude-sonnet-5` | 952,093 |
| `claude-opus-4-7` | 153,124 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 1,273,884 | 352,453,272 | 12,971,528,788 | 58,519,096 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## DeepSeek backend (~/.my-claude)

**520,497,793 tokens** (1.8%) · 18 sessions · 5,101 turns · 22 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 520,497,793 | 100.0% |

| Company | Tokens |
|---|---:|
| DeepSeek | 520,497,793 |

| Model | Tokens |
|---|---:|
| `deepseek-v4-pro` | 486,517,067 |
| `deepseek-v4-flash` | 33,980,726 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 21,796,441 | 0 | 493,706,496 | 4,994,856 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## alexander.sorrell.it@gmail.com

**467,800,272 tokens** (1.6%) · 30 sessions · 2,288 turns · 8 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBook Air M1 | 243,949,169 | 52.1% |
| HP Laptop Linux | 223,851,103 | 47.9% |

| Company | Tokens |
|---|---:|
| Anthropic | 467,800,272 |

| Model | Tokens |
|---|---:|
| `claude-sonnet-5` | 176,901,334 |
| `claude-opus-4-8` | 171,240,412 |
| `claude-sonnet-4-6` | 115,795,052 |
| `claude-opus-4-7` | 3,117,948 |
| `claude-haiku-4-5-20251001` | 745,526 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 41,466 | 12,011,205 | 454,127,715 | 1,619,886 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## unknown (Documents)

**10,014,914 tokens** (0.0%) · 4,360 sessions · 106 turns · 21 active days

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

## API key (org 15a93e14-aabb-4293-8228-8c56a803d972)

**141,210 tokens** (0.0%) · 3 sessions · 6 turns · 1 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 141,210 | 100.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 141,210 |

| Model | Tokens |
|---|---:|
| `claude-opus-4-8` | 76,152 |
| `claude-fable-5` | 65,058 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 1,922 | 10,864 | 125,198 | 3,226 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## Each computer

_The same accounts, grouped by machine. One login is usually driven from several computers, and no computer can see another's sessions — which is why the account totals above exist at all._

### MacBook Air M1

**18,032,194,745 tokens** across 4 login(s)

| Account | Tokens | Share |
|---|---:|---:|
| broodierchip@gmail.com | 12,456,931,683 |  69.1% |
| codehunterextreme@gmail.com | 5,321,298,979 |  29.5% |
| alexander.sorrell.it@gmail.com | 243,949,169 |   1.4% |
| unknown (Documents) | 10,014,914 |   0.1% |

### HP Laptop Linux

**11,551,416,604 tokens** across 5 login(s)

| Account | Tokens | Share |
|---|---:|---:|
| codehunterextreme@gmail.com | 8,062,476,061 |  69.8% |
| broodierchip@gmail.com | 2,744,450,437 |  23.8% |
| DeepSeek backend (~/.my-claude) | 520,497,793 |   4.5% |
| alexander.sorrell.it@gmail.com | 223,851,103 |   1.9% |
| API key (org 15a93e14-aabb-4293-8228-8c56a803d972) | 141,210 |   0.0% |

