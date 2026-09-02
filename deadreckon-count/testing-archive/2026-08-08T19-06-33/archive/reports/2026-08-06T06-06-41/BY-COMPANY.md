# By company

_What each vendor was actually paid for_

_Generated 2026-08-06T06:06:29-05:00 by `stats_page.py`. Do not edit by hand._

**41,163,845,403** tokens of Claude Code across 4 scanned computer(s) · **46,336,106,950** across every CLI on the 4 that ran `sessions.py`.

Those two are not added: the second contains the first. See [BY-COMPUTER.md](BY-COMPUTER.md) for the reconciliation.

Reports: [computers](BY-COMPUTER.md) · [accounts](BY-ACCOUNT.md) · [companies](BY-COMPANY.md) · [how it works](README.md)

---

_scans taken 2026-08-06 00:50:35 .. 2026-08-06 03:30:07_

Claude Code can be pointed at a non-Anthropic backend and the transcripts look identical, so a raw total is not an Anthropic total. Split on the model id.

| Company | Tag | Tokens | Share | |
|---|---|---:|---:|---|
| **Anthropic** | `anthropic` | 39,717,893,387 | 96.5% | ███████████████████████████· |
| **DeepSeek** | `deepseek` | 1,445,952,016 | 3.5% | █··························· |
| **All** | | **41,163,845,403** | 100% | |

### Who served it, versus who was paid for the tool

Different questions. Copilot runs Claude models: that is GitHub spend and Anthropic service.

| Company | Sessions | Active | Tokens | Via |
|---|---:|---:|---:|---|
| Anthropic | 214 | 635h 15m | 40,158,012,302 | claude 39.72B, copilot 437.66M |
| Google | 117 | 100h 20m | 2,650,117,227 | gemini 2.47B, antigravity 174.13M, kilocode 7.03M |
| OpenAI | 156 | 64h 10m | 1,926,282,114 | codex 1.64B, copilot 290.55M |
| DeepSeek | 48 | 76h 03m | 1,445,955,546 | claude 1.45B, lmstudio 3.53K |
| xAI | 7 | 8h 57m | 90,219,964 | grok 90.21M, kilocode 10.65K |
| — (no API call) | 20 | 58h 09m | 65,311,661 | copilot 65.31M |
| Mistral | 5 | 0m | 116,185 | lmstudio 116.19K |
| — (unidentified) | 4 | 1m | 91,892 | lmstudio 53.16K, kilocode 38.73K |
| Meta | 1 | 0m | 59 | lmstudio 59 |

---

## Anthropic

**39,717,893,387 tokens** (96.5% of all Claude Code)

| Model | Tokens |
|---|---:|
| `claude-opus-4-8` | 15,742,792,660 |
| `claude-opus-5` | 15,000,359,225 |
| `claude-opus-4-7` | 5,730,110,556 |
| `claude-fable-5` | 2,985,719,657 |
| `claude-sonnet-4-6` | 230,875,370 |
| `claude-haiku-4-5-20251001` | 25,454,993 |
| `claude-sonnet-5` | 1,583,992 |
| `claude-opus-4-5-20251101` | 996,934 |

| Computer | Tokens |
|---|---:|
| MacBook Air M1 | 29,170,327,621 |
| HP Laptop Linux | 10,279,288,477 |
| ASUS Laptop Linux | 266,146,676 |
| Dell Inspiron Desktop Linux | 2,130,613 |

| Account | Tokens |
|---|---:|
| broodierchip@gmail.com | 24,156,212,641 |
| codehunterextreme@gmail.com | 14,906,276,689 |
| alexander.sorrell.it@gmail.com | 654,966,438 |
| API key (org 15a93e14-aabb-4293-8228-8c56a803d972) | 437,619 |

---

## DeepSeek

**1,445,952,016 tokens** (3.5% of all Claude Code)

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

### MacBook Air M1

**29,170,327,621 tokens** from 2 company(s)

| Company | Tokens | Share |
|---|---:|---:|
| Anthropic | 29,170,327,621 | 100.0% |
| — (no API call) | 0 |   0.0% |

### HP Laptop Linux

**11,725,240,493 tokens** from 3 company(s)

| Company | Tokens | Share |
|---|---:|---:|
| Anthropic | 10,279,288,477 |  87.7% |
| DeepSeek | 1,445,952,016 |  12.3% |
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

