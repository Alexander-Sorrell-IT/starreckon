# By company

_What each vendor was actually paid for_

_Generated 2026-08-08T15:30:53-05:00 by `stats_page.py`. Do not edit by hand._

**47,977,825,597** tokens of Claude Code across 6 scanned computer(s) · **48,660,830,354** across every CLI on the 5 that ran `sessions.py`.

Those two are not added: the second contains the first. See [BY-COMPUTER.md](BY-COMPUTER.md) for the reconciliation.

Reports: [computers](BY-COMPUTER.md) · [accounts](BY-ACCOUNT.md) · [companies](BY-COMPANY.md) · [how it works](README.md)

---

_scans taken 2026-08-06 00:50:35 .. 2026-08-08 15:30:18_

Claude Code can be pointed at a non-Anthropic backend and the transcripts look identical, so a raw total is not an Anthropic total. Split on the model id.

| Company | Tag | Tokens | Share | |
|---|---|---:|---:|---|
| **Anthropic** | `anthropic` | 46,908,483,291 | 97.8% | ███████████████████████████· |
| **DeepSeek** | `deepseek` | 1,069,342,306 | 2.2% | █··························· |
| **All** | | **47,977,825,597** | 100% | |

### Who served it, versus who was paid for the tool

Different questions. Copilot runs Claude models: that is GitHub spend and Anthropic service.

| Company | Sessions | Active | Tokens | Via |
|---|---:|---:|---:|---|
| Anthropic | 13,526 | 813h 52m | 41,288,934,179 | claude 40.85B, copilot 442.12M |
| Google | 155 | 130h 56m | 3,019,451,028 | gemini 2.79B, antigravity 222.72M, kilocode 7.03M |
| OpenAI | 176 | 93h 07m | 2,604,133,300 | codex 2.31B, copilot 290.55M |
| — (no API call) | 3,272 | 138h 05m | 1,123,209,064 | copilot 1.12B, claude 49.99K |
| DeepSeek | 48 | 76h 03m | 534,674,683 | claude 534.67M, lmstudio 3.53K |
| xAI | 7 | 8h 57m | 90,219,964 | grok 90.21M, kilocode 10.65K |
| Mistral | 5 | 0m | 116,185 | lmstudio 116.19K |
| — (unidentified) | 4 | 1m | 91,892 | lmstudio 53.16K, kilocode 38.73K |
| Meta | 1 | 0m | 59 | lmstudio 59 |

---

## Anthropic

**46,908,483,291 tokens** (97.8% of all Claude Code)

| Model | Tokens |
|---|---:|
| `claude-opus-5` | 18,462,346,798 |
| `claude-opus-4-8` | 17,851,368,948 |
| `claude-opus-4-7` | 5,386,519,619 |
| `claude-fable-5` | 3,390,884,382 |
| `claude-opus-4-6` | 834,041,599 |
| `claude-opus-4-5-20251101` | 575,579,698 |
| `claude-sonnet-4-6` | 252,362,077 |
| `claude-haiku-4-5-20251001` | 137,250,416 |
| `claude-sonnet-4-5-20250929` | 16,304,590 |
| `claude-sonnet-5` | 1,825,164 |

| Computer | Tokens |
|---|---:|
| MacBook Air M1 | 29,170,327,621 |
| HP Laptop Linux | 6,080,963,159 |
| HP-Phantom-Core | 6,064,304,666 |
| Dell Latitude 7480 Linux | 5,324,610,556 |
| ASUS Laptop Linux | 266,146,676 |
| Dell Inspiron Desktop Linux | 2,130,613 |

| Account | Tokens |
|---|---:|
| second@example.com | 26,018,504,696 |
| third@example.com | 16,994,468,769 |
| owner@example.com | 2,898,894,295 |
| unknown (Desktop_standout_clean_.claude) | 642,203,454 |
| unknown (Desktop_standout_full_.claude) | 335,659,608 |
| unknown (Desktop_standout_max_.claude) | 9,338,718 |
| user:2d4777822844 | 7,281,866 |
| unknown (.claude-alt) | 1,849,465 |
| API key (org 15a93e14-aabb-4293-8228-8c56a803d972) | 282,420 |

---

## DeepSeek

**1,069,342,306 tokens** (2.2% of all Claude Code)

| Model | Tokens |
|---|---:|
| `deepseek-v4-pro` | 1,001,358,852 |
| `deepseek-v4-flash` | 67,983,454 |

| Computer | Tokens |
|---|---:|
| HP Laptop Linux | 534,671,153 |
| HP-Phantom-Core | 534,671,153 |

| Account | Tokens |
|---|---:|
| DeepSeek backend (~/.my-claude) | 1,040,995,586 |
| second@example.com | 28,346,720 |

---

## Each computer

_The same tokens, grouped by machine instead of by vendor._

### MacBook Air M1

**29,170,327,621 tokens** from 2 company(s)

| Company | Tokens | Share |
|---|---:|---:|
| Anthropic | 29,170,327,621 | 100.0% |
| — (no API call) | 0 |   0.0% |

### HP Laptop Linux

**6,615,634,312 tokens** from 2 company(s)

| Company | Tokens | Share |
|---|---:|---:|
| Anthropic | 6,080,963,159 |  91.9% |
| DeepSeek | 534,671,153 |   8.1% |

### HP-Phantom-Core

**6,598,975,819 tokens** from 2 company(s)

| Company | Tokens | Share |
|---|---:|---:|
| Anthropic | 6,064,304,666 |  91.9% |
| DeepSeek | 534,671,153 |   8.1% |

### Dell Latitude 7480 Linux

**5,324,610,556 tokens** from 2 company(s)

| Company | Tokens | Share |
|---|---:|---:|
| Anthropic | 5,324,610,556 | 100.0% |
| — (no API call) | 0 |   0.0% |

### ASUS Laptop Linux

**266,146,676 tokens** from 2 company(s)

| Company | Tokens | Share |
|---|---:|---:|
| Anthropic | 266,146,676 | 100.0% |
| — (no API call) | 0 |   0.0% |

### Dell Inspiron Desktop Linux

**2,130,613 tokens** from 2 company(s)

| Company | Tokens | Share |
|---|---:|---:|
| Anthropic | 2,130,613 | 100.0% |
| — (no API call) | 0 |   0.0% |

