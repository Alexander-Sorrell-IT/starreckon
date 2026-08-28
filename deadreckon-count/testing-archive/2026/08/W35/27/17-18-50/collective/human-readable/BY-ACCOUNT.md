# By account

_What each login spent, across every computer_

_Generated 2026-08-27T15:22:53-05:00 by `stats_page.py`. Do not edit by hand._

**60,524,260,897** tokens of Claude Code across 2 scanned computer(s) · **68,081,153,516** across every CLI on the 2 that ran `sessions.py`.

Those two are not added: the second contains the first. See [BY-COMPUTER.md](BY-COMPUTER.md) for the reconciliation.

Reports: [computers](BY-COMPUTER.md) · [accounts](BY-ACCOUNT.md) · [companies](BY-COMPANY.md) · [how it works](README.md)

---

_scans taken 2026-08-27 05:06:36 .. 2026-08-27 15:19:30_

The per-account total across computers is the number that matters: the same login gets driven from several machines and no machine can see another's sessions.

| Account | Tokens | Share | Computers | Sessions | Turns | |
|---|---:|---:|---:|---:|---:|---|
| **acct-83084ebd** | 28,623,097,827 | 47.3% | 1 | 37 | 147,433 | █████████████··············· |
| **broodierchip@gmail.com** | 12,834,169,588 | 21.2% | 1 | 74 | 60,017 | ██████······················ |
| **acct-17de7ff8** | 12,664,864,821 | 20.9% | 1 | 2,151 | 31,359 | ██████······················ |
| **codehunterextreme@gmail.com** | 5,321,298,979 | 8.8% | 1 | 50 | 13,265 | ██·························· |
| **acct-bc7f238c** | 738,375,002 | 1.2% | 1 | 7 | 3,012 | █··························· |
| **alexander.sorrell.it@gmail.com** | 322,280,256 | 0.5% | 1 | 14 | 1,430 | █··························· |
| **unknown (Desktop_standout_sandbox_.claude)** | 10,159,510 | 0.0% | 1 | 2,126 | 192 | █··························· |
| **unknown (Documents)** | 10,014,914 | 0.0% | 2 | 8,720 | 106 | █··························· |
| **unknown (claude)** | 0 | 0.0% | 1 | 25 | 0 | ···························· |
| **unknown (claude-it)** | 0 | 0.0% | 1 | 7 | 0 | ···························· |
| **unknown (claude-main)** | 0 | 0.0% | 1 | 37 | 0 | ···························· |
| **unknown (v10)** | 0 | 0.0% | 1 | 36 | 0 | ···························· |
| **All** | **60,524,260,897** | 100% | | | | |

## Across every CLI, by account

The table above is Claude Code only, because it is the one tool that writes its account email to disk. This one folds in every other CLI using the ownership declared in [`accounts.json`](accounts.json).

| Account | Tokens | Sessions | Via |
|---|---:|---:|---|
| **broodierchip@gmail.com** | 13,358,071,045 | 49 | claude 13.36B |
| **codehunterextreme@gmail.com** | 5,977,885,131 | 29 | claude 5.98B |
| **alexsorrellyan@gmail.com** | 5,906,801,516 | 260 | gemini 1.99B _owner_, codex 1.63B _owner_, antigravity 1.14B _owner_, copilot 875.41M _owner_, copilot 150.74M _owner_, copilot 118.74M _owner_ |
| **alexander.sorrell.it@gmail.com** | 322,280,256 | 7 | claude 322.28M |
| **nefabious@gmail.com** | 200,444,644 | 16 | grok 200.44M _owner_ |
| **All attributed** | **25,765,482,592** | | |

`file` means the email was read out of that tool's own account file. `owner` means it was stated by the account holder and cannot be checked against anything on disk. Claude Code rows carry neither because the email is in the session record itself.

> ⚠️ **42,315,670,924 tokens have no account.** These tools record no identity on disk and none is declared for them yet:

| CLI | Company that served it | Sessions | Tokens |
|---|---|---:|---:|
| claude | Anthropic | 2,634 | 42,040,449,442 |
| bob | None | 5 | 272,617,335 |
| bob | Anthropic | 2 | 2,550,988 |
| lmstudio | — (unidentified) | 3 | 53,159 |
| claude ⚠️ | — (unidentified) | 645 | 0 |

⚠️ marks a row where the tool's name and the company that served the tokens disagree. `claude` served by DeepSeek is a Claude Code build pointed at a DeepSeek backend: the interface is Claude Code, every token is DeepSeek, and Anthropic was paid nothing. Reading the CLI column alone would count it as Claude usage.


Add a `services` entry to the right account in `accounts.json` to fold any of these in. They are left under a placeholder rather than split across accounts by proportion, because that would invent numbers that look measured.

> ⚠️ **Known account(s) with no usage found anywhere:** `alexsorrellit@gmail.com`.

### Account x computer

| Account | MacBookAir | MacBook Air M1 (Darwin ARM64) | Total |
|---|---|---|---|
| acct-83084ebd | 28.62B | — | **28,623,097,827** |
| broodierchip@gmail.com | — | 12.83B | **12,834,169,588** |
| acct-17de7ff8 | 12.66B | — | **12,664,864,821** |
| codehunterextreme@gmail.com | — | 5.32B | **5,321,298,979** |
| acct-bc7f238c | 738.38M | — | **738,375,002** |
| alexander.sorrell.it@gmail.com | — | 322.28M | **322,280,256** |
| unknown (Desktop_standout_sandbox_.claude) | 10.16M | — | **10,159,510** |
| unknown (Documents) | — | 10.01M | **10,014,914** |
| unknown (claude) | — | — | **0** |
| unknown (claude-it) | — | — | **0** |
| unknown (claude-main) | — | — | **0** |
| unknown (v10) | — | — | **0** |
| **All** | **42.04B** | **18.49B** | **60,524,260,897** |

---

## acct-83084ebd

**28,623,097,827 tokens** (47.3%) · 37 sessions · 147,433 turns · 44 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBookAir | 28,623,097,827 | 100.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 28,623,097,827 |
| — (unidentified) | 0 |

| Model | Tokens |
|---|---:|
| `claude-opus-5` | 20,915,922,504 |
| `claude-opus-4-8` | 6,059,682,715 |
| `claude-fable-5` | 1,645,758,775 |
| `claude-haiku-4-5-20251001` | 1,733,833 |
| `proj-475024d6` | 0 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 10,398,929 | 876,458,658 | 27,645,850,005 | 90,390,235 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## broodierchip@gmail.com

**12,834,169,588 tokens** (21.2%) · 74 sessions · 60,017 turns · 42 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBook Air M1 (Darwin ARM64) | 12,834,169,588 | 100.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 12,834,169,588 |

| Model | Tokens |
|---|---:|
| `claude-opus-5` | 9,661,094,321 |
| `claude-opus-4-8` | 2,364,514,461 |
| `claude-fable-5` | 808,080,081 |
| `claude-haiku-4-5-20251001` | 480,725 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 3,820,245 | 333,605,510 | 12,437,108,824 | 59,635,009 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## acct-17de7ff8

**12,664,864,821 tokens** (20.9%) · 2,151 sessions · 31,359 turns · 33 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBookAir | 12,664,864,821 | 100.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 12,664,864,821 |
| — (unidentified) | 0 |

| Model | Tokens |
|---|---:|
| `claude-opus-4-8` | 7,595,933,626 |
| `claude-opus-5` | 5,066,966,543 |
| `claude-sonnet-5` | 1,583,992 |
| `claude-opus-4-7` | 380,660 |
| `proj-475024d6` | 0 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 1,323,062 | 437,529,397 | 12,187,548,458 | 38,463,904 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## codehunterextreme@gmail.com

**5,321,298,979 tokens** (8.8%) · 50 sessions · 13,265 turns · 33 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBook Air M1 (Darwin ARM64) | 5,321,298,979 | 100.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 5,321,298,979 |

| Model | Tokens |
|---|---:|
| `claude-opus-4-8` | 2,913,362,846 |
| `claude-opus-5` | 2,406,951,502 |
| `claude-sonnet-5` | 831,507 |
| `claude-opus-4-7` | 153,124 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 434,300 | 161,543,121 | 5,143,134,863 | 16,186,695 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## acct-bc7f238c

**738,375,002 tokens** (1.2%) · 7 sessions · 3,012 turns · 8 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBookAir | 738,375,002 | 100.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 738,375,002 |
| — (unidentified) | 0 |

| Model | Tokens |
|---|---:|
| `claude-opus-4-8` | 440,309,308 |
| `claude-opus-5` | 166,621,247 |
| `claude-sonnet-4-6` | 131,444,447 |
| `proj-475024d6` | 0 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 76,607 | 18,128,921 | 716,739,031 | 3,430,443 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## alexander.sorrell.it@gmail.com

**322,280,256 tokens** (0.5%) · 14 sessions · 1,430 turns · 5 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBook Air M1 (Darwin ARM64) | 322,280,256 | 100.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 322,280,256 |

| Model | Tokens |
|---|---:|
| `claude-opus-4-8` | 171,240,412 |
| `claude-opus-5` | 78,331,087 |
| `claude-sonnet-4-6` | 72,708,757 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 29,149 | 7,468,550 | 313,447,283 | 1,335,274 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## unknown (Desktop_standout_sandbox_.claude)

**10,159,510 tokens** (0.0%) · 2,126 sessions · 192 turns · 4 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBookAir | 10,159,510 | 100.0% |

| Company | Tokens |
|---|---:|
| Anthropic | 10,159,510 |

| Model | Tokens |
|---|---:|
| `claude-opus-4-8` | 9,428,950 |
| `claude-fable-5` | 730,560 |

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 69,154 | 1,018,531 | 8,957,522 | 114,303 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## unknown (Documents)

**10,014,914 tokens** (0.0%) · 8,720 sessions · 106 turns · 21 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBook Air M1 (Darwin ARM64) | 10,014,914 | 100.0% |
| MacBookAir | 0 | 0.0% |

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

## unknown (claude)

**0 tokens** (0.0%) · 25 sessions · 0 turns · 0 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBookAir | 0 | — |

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

**0 tokens** (0.0%) · 7 sessions · 0 turns · 0 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBookAir | 0 | — |

| Company | Tokens |
|---|---:|

| Model | Tokens |
|---|---:|

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 0 | 0 | 0 | 0 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## unknown (claude-main)

**0 tokens** (0.0%) · 37 sessions · 0 turns · 0 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBookAir | 0 | — |

| Company | Tokens |
|---|---:|

| Model | Tokens |
|---|---:|

| Input | Cache write | Cache read | Output |
|---:|---:|---:|---:|
| 0 | 0 | 0 | 0 |

All four are billed. Cache reads dominate because every turn re-reads the whole conversation, so a session's context is billed once per turn.

---

## unknown (v10)

**0 tokens** (0.0%) · 36 sessions · 0 turns · 0 active days

| Computer | Tokens | Share of this account |
|---|---:|---:|
| MacBookAir | 0 | — |

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

### MacBookAir

**42,036,497,160 tokens** across 9 login(s)

| Account | Tokens | Share |
|---|---:|---:|
| acct-83084ebd | 28,623,097,827 |  68.1% |
| acct-17de7ff8 | 12,664,864,821 |  30.1% |
| acct-bc7f238c | 738,375,002 |   1.8% |
| unknown (Desktop_standout_sandbox_.claude) | 10,159,510 |   0.0% |
| unknown (Documents) | 0 |   0.0% |
| unknown (claude) | 0 |   0.0% |
| unknown (claude-it) | 0 |   0.0% |
| unknown (claude-main) | 0 |   0.0% |
| unknown (v10) | 0 |   0.0% |

### MacBook Air M1 (Darwin ARM64)

**18,487,763,737 tokens** across 4 login(s)

| Account | Tokens | Share |
|---|---:|---:|
| broodierchip@gmail.com | 12,834,169,588 |  69.4% |
| codehunterextreme@gmail.com | 5,321,298,979 |  28.8% |
| alexander.sorrell.it@gmail.com | 322,280,256 |   1.7% |
| unknown (Documents) | 10,014,914 |   0.1% |

