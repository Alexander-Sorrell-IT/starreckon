# By account

_What each login spent, across every computer_

_Generated 2026-08-09T02:52:23-05:00 by `stats_page.py`. Do not edit by hand._

**6,868,321,450** tokens of Claude Code across 3 scanned computer(s) · **8,693,210,554** across every CLI on the 3 that ran `sessions.py`.

Those two are not added: the second contains the first. See [BY-COMPUTER.md](BY-COMPUTER.md) for the reconciliation.

Reports: [computers](BY-COMPUTER.md) · [accounts](BY-ACCOUNT.md) · [companies](BY-COMPANY.md) · [how it works](README.md)

---

_scans taken 2026-08-09 00:54:17 .. 2026-08-09 02:32:05_

The per-account total across computers is the number that matters: the same login gets driven from several machines and no machine can see another's sessions.

| Account | Tokens | Share | Computers | Sessions | Turns | |
|---|---:|---:|---:|---:|---:|---|
| **codehunterextreme@gmail.com** | 3,091,271,390 | 45.0% | 1 | 27 | 14,189 | █████████████··············· |
| **broodierchip@gmail.com** | 2,718,978,346 | 39.6% | 3 | 2,803 | 8,704 | ███████████················· |
| **DeepSeek backend (~/.my-claude)** | 520,497,793 | 7.6% | 1 | 6 | 5,101 | ██·························· |
| **unknown (Desktop_standout_clean_.claude)** | 321,101,727 | 4.7% | 1 | 420 | 2,098 | █··························· |
| **unknown (Desktop_standout_full_.claude)** | 167,829,804 | 2.4% | 1 | 805 | 2,477 | █··························· |
| **alexander.sorrell.it@gmail.com** | 43,831,821 | 0.6% | 1 | 2 | 454 | █··························· |
| **unknown (Desktop_standout_max_.claude)** | 4,669,359 | 0.1% | 1 | 805 | 20 | █··························· |
| **API key (org 15a93e14-aabb-4293-8228-8c56a803d972)** | 141,210 | 0.0% | 1 | 1 | 6 | █··························· |
| **unknown (.claude-alt)** | 0 | 0.0% | 1 | 27 | 0 | ···························· |
| **unknown (.claude-alt-api)** | 0 | 0.0% | 1 | 1 | 0 | ···························· |
| **unknown (.claude-it)** | 0 | 0.0% | 1 | 2 | 0 | ···························· |
| **unknown (.my-claude)** | 0 | 0.0% | 1 | 6 | 0 | ···························· |
| **unknown (Desktop_standout_sandbox_.claude)** | 0 | 0.0% | 1 | 576 | 0 | ···························· |
| **unknown (claude)** | 0 | 0.0% | 3 | 113 | 0 | ···························· |
| **unknown (claude-alt)** | 0 | 0.0% | 1 | 27 | 0 | ···························· |
| **unknown (claude-alt-api)** | 0 | 0.0% | 1 | 1 | 0 | ···························· |
| **unknown (claude-it)** | 0 | 0.0% | 1 | 2 | 0 | ···························· |
| **unknown (my-claude)** | 0 | 0.0% | 1 | 6 | 0 | ···························· |
| **All** | **6,868,321,450** | 100% | | | | |

## Across every CLI, by account

The table above is Claude Code only, because it is the one tool that writes its account email to disk. This one folds in every other CLI using the ownership declared in [`accounts.json`](accounts.json).

| Account | Tokens | Sessions | Via |
|---|---:|---:|---|
| **broodierchip@gmail.com** | 4,196,288,534 | 160 | claude 2.71B, gemini 1.47B _file_, claude → DeepSeek 14.17M, claude → — (no API call) 49.99K |
| **codehunterextreme@gmail.com** | 3,092,285,937 | 25 | claude 3.09B |
| **alexander.sorrell.it@gmail.com** | 44,111,412 | 2 | claude 44.11M |
| **All attributed** | **7,332,685,883** | | |

`file` means the email was read out of that tool's own account file. `owner` means it was stated by the account holder and cannot be checked against anything on disk. Claude Code rows carry neither because the email is in the session record itself.

> ⚠️ **1,360,524,671 tokens have no account.** These tools record no identity on disk and none is declared for them yet:

| CLI | Company that served it | Sessions | Tokens |
|---|---|---:|---:|
| claude ⚠️ | DeepSeek | 17 | 520,497,793 |
| claude | Anthropic | 42 | 489,605,669 |
| copilot | OpenAI | 26 | 289,892,715 |
| antigravity | Google | 23 | 45,271,276 |
| kilocode | Google | 2 | 7,025,122 |
| copilot | — (no API call) | 5 | 5,939,252 |
| codex | OpenAI | 3 | 2,123,691 |
| lmstudio | Mistral | 5 | 116,185 |
| kilocode | — (unidentified) | 1 | 38,733 |
| kilocode | xAI | 1 | 10,646 |
| lmstudio | DeepSeek | 1 | 3,530 |
| lmstudio | Meta | 1 | 59 |
| claude ⚠️ | — (no API call) | 1 | 0 |

⚠️ marks a row where the tool's name and the company that served the tokens disagree. `claude` served by DeepSeek is a Claude Code build pointed at a DeepSeek backend: the interface is Claude Code, every token is DeepSeek, and Anthropic was paid nothing. Reading the CLI column alone would count it as Claude usage.


Add a `services` entry to the right account in `accounts.json` to fold any of these in. They are left under a placeholder rather than split across accounts by proportion, because that would invent numbers that look measured.

> ⚠️ **Known account(s) with no usage found anywhere:** `nefabious@gmail.com`.

### Account x computer

| Account | HP Laptop Linux | ASUS Laptop Linux | Dell Inspiron Desktop Linux | Total |
|---|---|---|---|---|
| codehunterextreme@gmail.com | 3.09B | — | — | **3,091,271,390** |
| broodierchip@gmail.com | 2.58B | 133.20M | 824.89K | **2,718,978,346** |
| DeepSeek backend (~/.my-claude) | 520.50M | — | — | **520,497,793** |
| unknown (Desktop_standout_clean_.claude) | 321.10M | — | — | **321,101,727** |
| unknown (Desktop_standout_full_.claude) | 167.83M | — | — | **167,829,804** |
| alexander.sorrell.it@gmail.com | 43.83M | — | — | **43,831,821** |
| unknown (Desktop_standout_max_.claude) | 4.67M | — | — | **4,669,359** |
| API key (org 15a93e14-aabb-4293-8228-8c56a803d972) | 141.21K | — | — | **141,210** |
| unknown (.claude-alt) | — | — | — | **0** |
| unknown (.claude-alt-api) | — | — | — | **0** |
| unknown (.claude-it) | — | — | — | **0** |
| unknown (.my-claude) | — | — | — | **0** |
| unknown (Desktop_standout_sandbox_.claude) | — | — | — | **0** |
| unknown (claude) | — | — | — | **0** |
| unknown (claude-alt) | — | — | — | **0** |
| unknown (claude-alt-api) | — | — | — | **0** |
| unknown (claude-it) | — | — | — | **0** |
| unknown (my-claude) | — | — | — | **0** |
| **All** | **6.73B** | **133.20M** | **824.89K** | **6,868,321,450** |

---

## codehunterextreme@gmail.com

**3,091,271,390 tokens** (45.0%) · 27 sessions · 14,189 turns · 22 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 3,091,271,390 | 100.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 3,091,271,390 |

| Model | Tokens |
|---|---:|
| `claude-opus-5` | 2,329,706,523 |
| `claude-fable-5` | 567,995,047 |
| `claude-opus-4-8` | 193,449,234 |
| `claude-sonnet-5` | 120,586 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 547,508 | 78,169,730 | 2,997,763,966 | 14,790,186 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## broodierchip@gmail.com

**2,718,978,346 tokens** (39.6%) · 2,803 sessions · 8,704 turns · 29 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 2,584,957,850 | 95.1% |
| ASUS Laptop Linux | 133,195,610 | 4.9% |
| Dell Inspiron Desktop Linux | 824,886 | 0.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 2,704,804,986 |
| DeepSeek | 14,173,360 |

| Model | Tokens |
|---|---:|
| `claude-opus-4-7` | 2,681,777,326 |
| `deepseek-v4-pro` | 14,162,359 |
| `claude-sonnet-4-6` | 10,330,121 |
| `claude-haiku-4-5-20251001` | 7,471,283 |
| `claude-opus-4-8` | 4,853,391 |
| `claude-opus-4-5-20251101` | 372,865 |
| `deepseek-v4-flash` | 11,001 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 1,585,313 | 65,975,994 | 2,641,287,325 | 10,129,714 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## DeepSeek backend (~/.my-claude)

**520,497,793 tokens** (7.6%) · 6 sessions · 5,101 turns · 22 active days

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

**321,101,727 tokens** (4.7%) · 420 sessions · 2,098 turns · 13 active days

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

## unknown (Desktop_standout_full_.claude)

**167,829,804 tokens** (2.4%) · 805 sessions · 2,477 turns · 11 active days

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

## alexander.sorrell.it@gmail.com

**43,831,821 tokens** (0.6%) · 2 sessions · 454 turns · 2 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 43,831,821 | 100.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 43,831,821 |

| Model | Tokens |
|---|---:|
| `claude-sonnet-4-6` | 43,086,295 |
| `claude-haiku-4-5-20251001` | 745,526 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 11,542 | 1,048,896 | 42,549,189 | 222,194 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## unknown (Desktop_standout_max_.claude)

**4,669,359 tokens** (0.1%) · 805 sessions · 20 turns · 10 active days

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

## unknown (Desktop_standout_sandbox_.claude)

**0 tokens** (0.0%) · 576 sessions · 0 turns · 0 active days

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

## unknown (claude)

**0 tokens** (0.0%) · 113 sessions · 0 turns · 0 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| HP Laptop Linux | 0 | — |
| ASUS Laptop Linux | 0 | — |
| Dell Inspiron Desktop Linux | 0 | — |

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

## unknown (claude-it)

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

### ASUS Laptop Linux

**133,195,610 tokens** across 2 login(s)

| Account | Tokens | Share |
|---|---:|---:|
| broodierchip@gmail.com | 133,195,610 | 100.0% |
| unknown (claude) | 0 |   0.0% |

### Dell Inspiron Desktop Linux

**824,886 tokens** across 2 login(s)

| Account | Tokens | Share |
|---|---:|---:|
| broodierchip@gmail.com | 824,886 | 100.0% |
| unknown (claude) | 0 |   0.0% |

