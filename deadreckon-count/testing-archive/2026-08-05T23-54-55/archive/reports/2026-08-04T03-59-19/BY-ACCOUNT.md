# By account

_What each login spent, across every computer_

_Generated 2026-08-04T03:59:19-05:00 by `stats_page.py`. Do not edit by hand._

**41,881,904,108** tokens of Claude Code across 5 scanned computer(s) · **43,245,366,216** across every CLI on the 4 that ran `sessions.py`.

Those two are not added: the second contains the first. See [BY-COMPUTER.md](BY-COMPUTER.md) for the reconciliation.

Reports: [computers](BY-COMPUTER.md) · [accounts](BY-ACCOUNT.md) · [companies](BY-COMPANY.md) · [how it works](README.md)

---

The per-account total across computers is the number that matters: the same login gets driven from several machines and no machine can see another's sessions.

| Account | Tokens | Share | Computers | Sessions | Turns | |
|---|---:|---:|---:|---:|---:|---|
| **broodierchip@gmail.com** | 24,811,576,643 | 59.2% | 5 | 16,583 | 157,319 | █████████████████··········· |
| **codehunterextreme@gmail.com** | 12,678,387,484 | 30.3% | 3 | 61 | 41,901 | ████████···················· |
| **alexander.sorrell.it@gmail.com** | 2,974,432,873 | 7.1% | 3 | 74 | 12,602 | ██·························· |
| **DeepSeek backend (~/.my-claude)** | 1,409,787,623 | 3.4% | 1 | 6 | 14,797 | █··························· |
| **unknown** | 7,281,866 | 0.0% | 1 | 2 | 114 | █··························· |
| **API key (org 15a93e14-aabb-4293-8228-8c56a803d972)** | 437,619 | 0.0% | 1 | 1 | 18 | █··························· |
| **All** | **41,881,904,108** | 100% | | | | |

## Across every CLI, by account

The table above is Claude Code only, because it is the one tool that writes its account email to disk. This one folds in every other CLI using the ownership declared in [`accounts.json`](accounts.json).

| Account | Tokens | Sessions | Via |
|---|---:|---:|---|
| **broodierchip@gmail.com** | 25,769,191,925 | 192 | claude 23.26B, gemini 2.47B _file_, claude → DeepSeek 36.16M |
| **codehunterextreme@gmail.com** | 12,731,616,520 | 54 | claude 12.73B |
| **alexander.sorrell.it@gmail.com** | 654,966,438 | 5 | claude 654.97M |
| **nefabious@gmail.com** | 76,724,862 | 5 | grok 76.72M _owner_ |
| **All attributed** | **39,232,499,745** | | |

`file` means the email was read out of that tool's own account file. `owner` means it was stated by the account holder and cannot be checked against anything on disk. Claude Code rows carry neither because the email is in the session record itself.

> ⚠️ **4,012,866,471 tokens have no account.** These tools record no identity on disk and none is declared for them yet:

| CLI | Company that served it | Sessions | Tokens |
|---|---|---:|---:|
| codex | OpenAI | 128 | 1,635,327,644 |
| claude ⚠️ | DeepSeek | 17 | 1,409,787,623 |
| copilot | Anthropic | 26 | 437,663,547 |
| copilot | OpenAI | 28 | 290,553,542 |
| antigravity | Google | 54 | 162,039,081 |
| copilot | — (no API call) | 13 | 65,311,661 |
| kilocode | Google | 2 | 7,025,122 |
| antigravity ⚠️ | — (unidentified) | 3 | 4,671,253 |
| claude | Anthropic | 1 | 437,619 |
| kilocode | — (unidentified) | 1 | 38,733 |
| kilocode | xAI | 1 | 10,646 |

⚠️ marks a row where the tool's name and the company that served the tokens disagree. `claude` served by DeepSeek is a Claude Code build pointed at a DeepSeek backend: the interface is Claude Code, every token is DeepSeek, and Anthropic was paid nothing. Reading the CLI column alone would count it as Claude usage.


Add a `services` entry to the right account in `accounts.json` to fold any of these in. They are left under a placeholder rather than split across accounts by proportion, because that would invent numbers that look measured.

### Account x computer

| Account | MacBook Air M1 | HP Laptop Linux | Dell Latitude 7480 Linux | ASUS Laptop Linux | Dell Inspiron Desktop Linux | Total |
|---|---|---|---|---|---|---|
| broodierchip@gmail.com | 17.48B | 5.55B | 1.51B | 266.15M | 2.13M | **24,811,576,643** |
| codehunterextreme@gmail.com | 9.95B | 2.70B | 26.78M | — | — | **12,678,387,484** |
| alexander.sorrell.it@gmail.com | 571.75M | 83.21M | 2.32B | — | — | **2,974,432,873** |
| DeepSeek backend (~/.my-claude) | — | 1.41B | — | — | — | **1,409,787,623** |
| unknown | — | — | 7.28M | — | — | **7,281,866** |
| API key (org 15a93e14-aabb-4293-8228-8c56a803d972) | — | 437.62K | — | — | — | **437,619** |
| **All** | **28.00B** | **9.74B** | **3.86B** | **266.15M** | **2.13M** | **41,881,904,108** |

---

## broodierchip@gmail.com

**24,811,576,643 tokens** (59.2%) · 16,583 sessions · 157,319 turns · 60 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBook Air M1 | 17,484,273,586 | 70.5% |
| HP Laptop Linux | 5,547,678,789 | 22.4% |
| Dell Latitude 7480 Linux | 1,511,346,979 | 6.1% |
| ASUS Laptop Linux | 266,146,676 | 1.1% |
| Dell Inspiron Desktop Linux | 2,130,613 | 0.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 24,775,412,250 |
| DeepSeek | 36,164,393 |
| — (no API call) | 0 |

| Model | Tokens |
|---|---:|
| `claude-opus-5` | 10,104,981,704 |
| `claude-opus-4-8` | 7,317,636,286 |
| `claude-opus-4-7` | 5,729,729,896 |
| `claude-fable-5` | 1,582,100,799 |
| `deepseek-v4-pro` | 36,142,409 |
| `claude-haiku-4-5-20251001` | 20,838,500 |
| `claude-sonnet-4-6` | 18,737,764 |
| `claude-opus-4-5-20251101` | 996,934 |
| `claude-opus-4-6` | 390,367 |
| `deepseek-v4-flash` | 21,984 |
| `<synthetic>` | 0 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 335,499,679 | 1,075,962,035 | 23,291,966,332 | 108,148,597 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## codehunterextreme@gmail.com

**12,678,387,484 tokens** (30.3%) · 61 sessions · 41,901 turns · 39 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBook Air M1 | 9,948,955,645 | 78.5% |
| HP Laptop Linux | 2,702,655,775 | 21.3% |
| Dell Latitude 7480 Linux | 26,776,064 | 0.2% |

| Company | Tokens |
|---|---:|
| Anthropic | 12,678,387,484 |
| — (no API call) | 0 |

| Model | Tokens |
|---|---:|
| `claude-opus-4-8` | 8,536,141,635 |
| `claude-opus-5` | 3,194,001,451 |
| `claude-fable-5` | 946,279,746 |
| `claude-sonnet-5` | 1,583,992 |
| `claude-opus-4-7` | 380,660 |
| `<synthetic>` | 0 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 4,653,368 | 449,304,033 | 12,177,385,522 | 47,044,561 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## alexander.sorrell.it@gmail.com

**2,974,432,873 tokens** (7.1%) · 74 sessions · 12,602 turns · 31 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| Dell Latitude 7480 Linux | 2,319,466,435 | 78.0% |
| MacBook Air M1 | 571,753,755 | 19.2% |
| HP Laptop Linux | 83,212,683 | 2.8% |

| Company | Tokens |
|---|---:|
| Anthropic | 2,974,432,873 |
| — (no API call) | 0 |

| Model | Tokens |
|---|---:|
| `claude-opus-4-8` | 1,771,821,777 |
| `claude-fable-5` | 541,250,728 |
| `claude-opus-5` | 429,224,883 |
| `claude-sonnet-4-6` | 212,137,606 |
| `claude-opus-4-7` | 17,478,355 |
| `claude-haiku-4-5-20251001` | 2,519,524 |
| `<synthetic>` | 0 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 627,852 | 113,275,388 | 2,844,578,781 | 15,950,852 |

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

## unknown

**7,281,866 tokens** (0.0%) · 2 sessions · 114 turns · 1 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| Dell Latitude 7480 Linux | 7,281,866 | 100.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 7,281,866 |
| — (no API call) | 0 |

| Model | Tokens |
|---|---:|
| `claude-sonnet-4-6` | 7,281,866 |
| `<synthetic>` | 0 |

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

