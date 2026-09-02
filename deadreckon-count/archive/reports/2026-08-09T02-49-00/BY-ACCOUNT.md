# By account

_What each login spent, across every computer_

_Generated 2026-08-09T02:48:38-05:00 by `stats_page.py`. Do not edit by hand._

**20,689,624,179** tokens of Claude Code across 2 scanned computer(s) · **25,881,910,936** across every CLI on the 2 that ran `sessions.py`.

Those two are not added: the second contains the first. See [BY-COMPUTER.md](BY-COMPUTER.md) for the reconciliation.

Reports: [computers](BY-COMPUTER.md) · [accounts](BY-ACCOUNT.md) · [companies](BY-COMPANY.md) · [how it works](README.md)

---

_scans taken 2026-08-09 00:54:17 .. 2026-08-09 02:34:15_

The per-account total across computers is the number that matters: the same login gets driven from several machines and no machine can see another's sessions.

| Account | Tokens | Share | Computers | Sessions | Turns | |
|---|---:|---:|---:|---:|---:|---|
| **broodierchip@gmail.com** | 11,016,451,059 | 53.2% | 2 | 2,805 | 54,558 | ███████████████············· |
| **codehunterextreme@gmail.com** | 8,361,023,577 | 40.4% | 2 | 2,177 | 27,100 | ███████████················· |
| **DeepSeek backend (~/.my-claude)** | 520,497,793 | 2.5% | 1 | 6 | 5,101 | █··························· |
| **unknown (Desktop_standout_clean_.claude)** | 321,101,727 | 1.6% | 1 | 420 | 2,098 | █··························· |
| **alexander.sorrell.it@gmail.com** | 287,780,990 | 1.4% | 2 | 6 | 1,578 | █··························· |
| **unknown (Desktop_standout_full_.claude)** | 167,829,804 | 0.8% | 1 | 805 | 2,477 | █··························· |
| **unknown (Documents)** | 6,062,632 | 0.0% | 1 | 4,360 | 31 | █··························· |
| **unknown (Desktop_standout_max_.claude)** | 4,669,359 | 0.0% | 1 | 805 | 20 | █··························· |
| **unknown (Desktop_standout_sandbox_.claude)** | 3,952,282 | 0.0% | 2 | 2,702 | 75 | █··························· |
| **API key (org 15a93e14-aabb-4293-8228-8c56a803d972)** | 141,210 | 0.0% | 1 | 1 | 6 | █··························· |
| **unknown (claude-main)** | 113,746 | 0.0% | 1 | 31 | 1 | █··························· |
| **unknown (claude)** | 0 | 0.0% | 2 | 108 | 0 | ···························· |
| **unknown (claude-it)** | 0 | 0.0% | 2 | 6 | 0 | ···························· |
| **unknown (.claude-alt)** | 0 | 0.0% | 1 | 27 | 0 | ···························· |
| **unknown (.claude-alt-api)** | 0 | 0.0% | 1 | 1 | 0 | ···························· |
| **unknown (.claude-it)** | 0 | 0.0% | 1 | 2 | 0 | ···························· |
| **unknown (.my-claude)** | 0 | 0.0% | 1 | 6 | 0 | ···························· |
| **unknown (claude-alt)** | 0 | 0.0% | 1 | 27 | 0 | ···························· |
| **unknown (claude-alt-api)** | 0 | 0.0% | 1 | 1 | 0 | ···························· |
| **unknown (my-claude)** | 0 | 0.0% | 1 | 6 | 0 | ···························· |
| **All** | **20,689,624,179** | 100% | | | | |

## Across every CLI, by account

The table above is Claude Code only, because it is the one tool that writes its account email to disk. This one folds in every other CLI using the ownership declared in [`accounts.json`](accounts.json).

| Account | Tokens | Sessions | Via |
|---|---:|---:|---|
| **broodierchip@gmail.com** | 13,487,496,222 | 156 | claude 11.01B, gemini 2.46B _file_, claude → DeepSeek 14.17M, claude → — (no API call) 49.99K |
| **codehunterextreme@gmail.com** | 8,395,361,752 | 46 | claude 8.40B |
| **alexander.sorrell.it@gmail.com** | 288,060,581 | 6 | claude 288.06M |
| **nefabious@gmail.com** | 99,062,873 | 7 | grok 99.06M _owner_ |
| **All attributed** | **22,269,981,428** | | |

`file` means the email was read out of that tool's own account file. `owner` means it was stated by the account holder and cannot be checked against anything on disk. Claude Code rows carry neither because the email is in the session record itself.

> ⚠️ **3,611,929,508 tokens have no account.** These tools record no identity on disk and none is declared for them yet:

| CLI | Company that served it | Sessions | Tokens |
|---|---|---:|---:|
| codex | OpenAI | 127 | 1,635,058,499 |
| claude ⚠️ | DeepSeek | 17 | 520,497,793 |
| claude | Anthropic | 47 | 493,557,951 |
| copilot | Anthropic | 26 | 437,663,547 |
| copilot | OpenAI | 28 | 290,553,542 |
| antigravity | Google | 54 | 162,039,081 |
| copilot | — (no API call) | 13 | 65,311,661 |
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

| Account | MacBook Air M1 | HP Laptop Linux | Total |
|---|---|---|---|
| broodierchip@gmail.com | 8.43B | 2.58B | **11,016,451,059** |
| codehunterextreme@gmail.com | 5.27B | 3.09B | **8,361,023,577** |
| DeepSeek backend (~/.my-claude) | — | 520.50M | **520,497,793** |
| unknown (Desktop_standout_clean_.claude) | — | 321.10M | **321,101,727** |
| alexander.sorrell.it@gmail.com | 243.95M | 43.83M | **287,780,990** |
| unknown (Desktop_standout_full_.claude) | — | 167.83M | **167,829,804** |
| unknown (Documents) | 6.06M | — | **6,062,632** |
| unknown (Desktop_standout_max_.claude) | — | 4.67M | **4,669,359** |
| unknown (Desktop_standout_sandbox_.claude) | 3.95M | — | **3,952,282** |
| API key (org 15a93e14-aabb-4293-8228-8c56a803d972) | — | 141.21K | **141,210** |
| unknown (claude-main) | 113.75K | — | **113,746** |
| unknown (claude) | — | — | **0** |
| unknown (claude-it) | — | — | **0** |
| unknown (.claude-alt) | — | — | **0** |
| unknown (.claude-alt-api) | — | — | **0** |
| unknown (.claude-it) | — | — | **0** |
| unknown (.my-claude) | — | — | **0** |
| unknown (claude-alt) | — | — | **0** |
| unknown (claude-alt-api) | — | — | **0** |
| unknown (my-claude) | — | — | **0** |
| **All** | **13.96B** | **6.73B** | **20,689,624,179** |

---

## broodierchip@gmail.com

**11,016,451,059 tokens** (53.2%) · 2,805 sessions · 54,558 turns · 51 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBook Air M1 | 8,431,493,209 | 76.5% |
| HP Laptop Linux | 2,584,957,850 | 23.5% |

| Company | Tokens |
|---|---:|
| Anthropic | 11,002,277,699 |
| DeepSeek | 14,173,360 |

| Model | Tokens |
|---|---:|
| `claude-opus-5` | 5,260,954,660 |
| `claude-opus-4-7` | 2,552,286,127 |
| `claude-opus-4-8` | 2,366,831,134 |
| `claude-fable-5` | 808,080,081 |
| `deepseek-v4-pro` | 14,162,359 |
| `claude-sonnet-4-6` | 10,330,121 |
| `claude-haiku-4-5-20251001` | 3,795,576 |
| `deepseek-v4-flash` | 11,001 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 5,253,984 | 311,445,981 | 10,642,529,238 | 57,221,856 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## codehunterextreme@gmail.com

**8,361,023,577 tokens** (40.4%) · 2,177 sessions · 27,100 turns · 33 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBook Air M1 | 5,269,752,187 | 63.0% |
| HP Laptop Linux | 3,091,271,390 | 37.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 8,361,023,577 |

| Model | Tokens |
|---|---:|
| `claude-opus-5` | 4,704,278,800 |
| `claude-opus-4-8` | 3,087,644,513 |
| `claude-fable-5` | 567,995,047 |
| `claude-sonnet-5` | 952,093 |
| `claude-opus-4-7` | 153,124 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 981,158 | 237,312,763 | 8,092,142,934 | 30,586,722 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## DeepSeek backend (~/.my-claude)

**520,497,793 tokens** (2.5%) · 6 sessions · 5,101 turns · 22 active days

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

## unknown (Desktop_standout_clean_.claude)

**321,101,727 tokens** (1.6%) · 420 sessions · 2,098 turns · 13 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 321,101,727 | 100.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 321,101,727 |

| Model | Tokens |
|---|---:|
| `claude-opus-4-8` | 274,069,558 |
| `claude-fable-5` | 47,032,169 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 557,017 | 14,268,145 | 304,377,575 | 1,898,990 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## alexander.sorrell.it@gmail.com

**287,780,990 tokens** (1.4%) · 6 sessions · 1,578 turns · 5 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBook Air M1 | 243,949,169 | 84.8% |
| HP Laptop Linux | 43,831,821 | 15.2% |

| Company | Tokens |
|---|---:|
| Anthropic | 287,780,990 |

| Model | Tokens |
|---|---:|
| `claude-opus-4-8` | 171,240,412 |
| `claude-sonnet-4-6` | 115,795,052 |
| `claude-haiku-4-5-20251001` | 745,526 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 40,075 | 6,323,397 | 280,259,375 | 1,158,143 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## unknown (Desktop_standout_full_.claude)

**167,829,804 tokens** (0.8%) · 805 sessions · 2,477 turns · 11 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 167,829,804 | 100.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 167,829,804 |

| Model | Tokens |
|---|---:|
| `claude-opus-4-8` | 164,531,635 |
| `claude-haiku-4-5-20251001` | 2,225,100 |
| `claude-fable-5` | 1,073,069 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 728,428 | 15,635,400 | 148,941,469 | 2,524,507 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## unknown (Documents)

**6,062,632 tokens** (0.0%) · 4,360 sessions · 31 turns · 18 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBook Air M1 | 6,062,632 | 100.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 6,062,632 |

| Model | Tokens |
|---|---:|
| `claude-opus-5` | 3,705,389 |
| `claude-opus-4-8` | 1,948,248 |
| `claude-fable-5` | 408,995 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 62 | 106,705 | 5,935,687 | 20,178 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## unknown (Desktop_standout_max_.claude)

**4,669,359 tokens** (0.0%) · 805 sessions · 20 turns · 10 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 4,669,359 | 100.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 4,669,359 |

| Model | Tokens |
|---|---:|
| `claude-opus-4-7` | 3,708,610 |
| `claude-opus-4-8` | 472,957 |
| `claude-sonnet-4-6` | 279,591 |
| `claude-fable-5` | 208,201 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 4,528 | 52,353 | 4,582,144 | 30,334 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## unknown (Desktop_standout_sandbox_.claude)

**3,952,282 tokens** (0.0%) · 2,702 sessions · 75 turns · 4 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBook Air M1 | 3,952,282 | 100.0% |
| HP Laptop Linux | 0 | 0.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 3,952,282 |

| Model | Tokens |
|---|---:|
| `claude-opus-4-8` | 3,585,425 |
| `claude-fable-5` | 366,857 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 25,837 | 377,188 | 3,505,480 | 43,777 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## API key (org 15a93e14-aabb-4293-8228-8c56a803d972)

**141,210 tokens** (0.0%) · 1 sessions · 6 turns · 1 active days

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

## unknown (claude-main)

**113,746 tokens** (0.0%) · 31 sessions · 1 turns · 1 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBook Air M1 | 113,746 | 100.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 113,746 |

| Model | Tokens |
|---|---:|
| `claude-opus-5` | 113,746 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 2 | 376 | 112,355 | 1,013 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## unknown (claude)

**0 tokens** (0.0%) · 108 sessions · 0 turns · 0 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBook Air M1 | 0 | — |
| HP Laptop Linux | 0 | — |

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

**0 tokens** (0.0%) · 6 sessions · 0 turns · 0 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBook Air M1 | 0 | — |
| HP Laptop Linux | 0 | — |

| Company | Tokens |
|---|---:|

| Model | Tokens |
|---|---:|

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 0 | 0 | 0 | 0 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## unknown (.claude-alt)

**0 tokens** (0.0%) · 27 sessions · 0 turns · 0 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 0 | — |

| Company | Tokens |
|---|---:|

| Model | Tokens |
|---|---:|

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 0 | 0 | 0 | 0 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## unknown (.claude-alt-api)

**0 tokens** (0.0%) · 1 sessions · 0 turns · 0 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 0 | — |

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

**0 tokens** (0.0%) · 2 sessions · 0 turns · 0 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 0 | — |

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

**0 tokens** (0.0%) · 6 sessions · 0 turns · 0 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 0 | — |

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

**0 tokens** (0.0%) · 27 sessions · 0 turns · 0 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 0 | — |

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

**0 tokens** (0.0%) · 1 sessions · 0 turns · 0 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 0 | — |

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

**0 tokens** (0.0%) · 6 sessions · 0 turns · 0 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 0 | — |

| Company | Tokens |
|---|---:|

| Model | Tokens |
|---|---:|

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 0 | 0 | 0 | 0 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## Each computer

_The same accounts, grouped by machine. One login is usually driven from several computers, and no computer can see another's sessions — which is why the account totals above exist at all._

### MacBook Air M1

**13,955,323,225 tokens** across 8 login(s)

| Account | Tokens | Share |
|---|---:|---:|
| broodierchip@gmail.com | 8,431,493,209 |  60.4% |
| codehunterextreme@gmail.com | 5,269,752,187 |  37.8% |
| alexander.sorrell.it@gmail.com | 243,949,169 |   1.7% |
| unknown (Documents) | 6,062,632 |   0.0% |
| unknown (Desktop_standout_sandbox_.claude) | 3,952,282 |   0.0% |
| unknown (claude-main) | 113,746 |   0.0% |
| unknown (claude) | 0 |   0.0% |
| unknown (claude-it) | 0 |   0.0% |

### HP Laptop Linux

**6,734,300,954 tokens** across 18 login(s)

| Account | Tokens | Share |
|---|---:|---:|
| codehunterextreme@gmail.com | 3,091,271,390 |  45.9% |
| broodierchip@gmail.com | 2,584,957,850 |  38.4% |
| DeepSeek backend (~/.my-claude) | 520,497,793 |   7.7% |
| unknown (Desktop_standout_clean_.claude) | 321,101,727 |   4.8% |
| unknown (Desktop_standout_full_.claude) | 167,829,804 |   2.5% |
| alexander.sorrell.it@gmail.com | 43,831,821 |   0.7% |
| unknown (Desktop_standout_max_.claude) | 4,669,359 |   0.1% |
| API key (org 15a93e14-aabb-4293-8228-8c56a803d972) | 141,210 |   0.0% |
| unknown (.claude-alt) | 0 |   0.0% |
| unknown (.claude-alt-api) | 0 |   0.0% |
| unknown (.claude-it) | 0 |   0.0% |
| unknown (.my-claude) | 0 |   0.0% |
| unknown (Desktop_standout_sandbox_.claude) | 0 |   0.0% |
| unknown (claude) | 0 |   0.0% |
| unknown (claude-alt) | 0 |   0.0% |
| unknown (claude-alt-api) | 0 |   0.0% |
| unknown (claude-it) | 0 |   0.0% |
| unknown (my-claude) | 0 |   0.0% |

