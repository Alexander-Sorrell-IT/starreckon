# By company

_What each vendor was actually paid for_

_Generated 2026-08-06T01:23:13-05:00 by `stats_page.py`. Do not edit by hand._

**11,845,102,826** tokens of Claude Code across 3 scanned computer(s) · **13,662,872,659** across every CLI on the 3 that ran `sessions.py`.

Those two are not added: the second contains the first. See [BY-COMPUTER.md](BY-COMPUTER.md) for the reconciliation.

Reports: [computers](BY-COMPUTER.md) · [accounts](BY-ACCOUNT.md) · [companies](BY-COMPANY.md) · [how it works](README.md)

---

_scans taken 2026-08-06 00:06:37 .. 2026-08-06 01:00:55_

Claude Code can be pointed at a non-Anthropic backend and the transcripts look identical, so a raw total is not an Anthropic total. Split on the model id.

| Company | Tag | Tokens | Share | |
|---|---|---:|---:|---|
| **Anthropic** | `anthropic` | 10,399,150,810 | 87.8% | █████████████████████████··· |
| **DeepSeek** | `deepseek` | 1,445,952,016 | 12.2% | ███························· |
| **All** | | **11,845,102,826** | 100% | |

### Who served it, versus who was paid for the tool

Different questions. Copilot runs Claude models: that is GitHub spend and Anthropic service.

| Company | Sessions | Active | Tokens | Via |
|---|---:|---:|---:|---|
| Anthropic | 137 | 186h 01m | 10,399,150,810 | claude 10.40B |
| Google | 78 | 77h 03m | 1,519,645,022 | gemini 1.47B, antigravity 39.02M, kilocode 7.03M |
| DeepSeek | 48 | 76h 03m | 1,445,955,546 | claude 1.45B, lmstudio 3.53K |
| OpenAI | 29 | 34h 10m | 292,016,406 | copilot 289.89M, codex 2.12M |
| — (no API call) | 8 | 21h 13m | 5,939,252 | copilot 5.94M |
| Mistral | 5 | 0m | 116,185 | lmstudio 116.19K |
| — (unidentified) | 1 | 1m | 38,733 | kilocode 38.73K |
| xAI | 1 | 0m | 10,646 | kilocode 10.65K |
| Meta | 1 | 0m | 59 | lmstudio 59 |

---

## Anthropic

**10,399,150,810 tokens** (87.8% of all Claude Code)

| Model | Tokens |
|---|---:|
| `claude-opus-4-7` | 5,729,729,896 |
| `claude-opus-4-8` | 1,652,926,177 |
| `claude-opus-5` | 1,548,775,431 |
| `claude-fable-5` | 1,343,570,289 |
| `claude-sonnet-4-6` | 99,430,923 |
| `claude-haiku-4-5-20251001` | 23,721,160 |
| `claude-opus-4-5-20251101` | 996,934 |

| Computer | Tokens |
|---|---:|
| HP Laptop Linux | 10,130,873,521 |
| ASUS Laptop Linux | 266,146,676 |
| Dell Inspiron Desktop Linux | 2,130,613 |

| Account | Tokens |
|---|---:|
| broodierchip@gmail.com | 6,597,681,128 |
| codehunterextreme@gmail.com | 3,717,819,380 |
| alexander.sorrell.it@gmail.com | 83,212,683 |
| API key (org 15a93e14-aabb-4293-8228-8c56a803d972) | 437,619 |

---

## DeepSeek

**1,445,952,016 tokens** (12.2% of all Claude Code)

| Model | Tokens |
|---|---:|
| `deepseek-v4-pro` | 1,328,563,303 |
| `deepseek-v4-flash` | 117,388,713 |

| Computer | Tokens |
|---|---:|
| HP Laptop Linux | 1,445,952,016 |

| Account | Tokens |
|---|---:|
| DeepSeek backend (~/.my-claude) | 1,409,787,623 |
| broodierchip@gmail.com | 36,164,393 |

---

## Each computer

_The same tokens, grouped by machine instead of by vendor._

### HP Laptop Linux

**11,576,825,537 tokens** from 3 company(s)

| Company | Tokens | Share |
|---|---:|---:|
| Anthropic | 10,130,873,521 |  87.5% |
| DeepSeek | 1,445,952,016 |  12.5% |
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

