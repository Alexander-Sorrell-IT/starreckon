# By company

_What each vendor was actually paid for_

_Generated 2026-08-06T00:18:09-05:00 by `stats_page.py`. Do not edit by hand._

**11,576,825,537** tokens of Claude Code across 1 scanned computer(s) · **13,376,595,505** across every CLI on the 1 that ran `sessions.py`.

Those two are not added: the second contains the first. See [BY-COMPUTER.md](BY-COMPUTER.md) for the reconciliation.

Reports: [computers](BY-COMPUTER.md) · [accounts](BY-ACCOUNT.md) · [companies](BY-COMPANY.md) · [how it works](README.md)

---

_scans taken 2026-08-06 00:06:37_

Claude Code can be pointed at a non-Anthropic backend and the transcripts look identical, so a raw total is not an Anthropic total. Split on the model id.

| Company | Tag | Tokens | Share | |
|---|---|---:|---:|---|
| **Anthropic** | `anthropic` | 10,130,873,521 | 87.5% | █████████████████████████··· |
| **DeepSeek** | `deepseek` | 1,445,952,016 | 12.5% | ███························· |
| **All** | | **11,576,825,537** | 100% | |

### Who served it, versus who was paid for the tool

Different questions. Copilot runs Claude models: that is GitHub spend and Anthropic service.

| Company | Sessions | Active | Tokens | Via |
|---|---:|---:|---:|---|
| Anthropic | 106 | 175h 06m | 10,130,873,521 | claude 10.13B |
| Google | 67 | 73h 15m | 1,502,315,230 | gemini 1.47B, antigravity 26.93M, kilocode 7.03M |
| DeepSeek | 48 | 76h 03m | 1,445,955,546 | claude 1.45B, lmstudio 3.53K |
| OpenAI | 28 | 33h 51m | 291,346,333 | copilot 289.89M, codex 1.45M |
| — (no API call) | 7 | 21h 13m | 5,939,252 | copilot 5.94M |
| Mistral | 5 | 0m | 116,185 | lmstudio 116.19K |
| — (unidentified) | 1 | 1m | 38,733 | kilocode 38.73K |
| xAI | 1 | 0m | 10,646 | kilocode 10.65K |
| Meta | 1 | 0m | 59 | lmstudio 59 |

---

## Anthropic

**10,130,873,521 tokens** (87.5% of all Claude Code)

| Model | Tokens |
|---|---:|
| `claude-opus-4-7` | 5,474,046,655 |
| `claude-opus-4-8` | 1,652,926,177 |
| `claude-opus-5` | 1,548,775,431 |
| `claude-fable-5` | 1,343,570,289 |
| `claude-sonnet-4-6` | 99,430,923 |
| `claude-haiku-4-5-20251001` | 12,124,046 |

| Computer | Tokens |
|---|---:|
| HP Laptop Linux | 10,130,873,521 |

| Account | Tokens |
|---|---:|
| broodierchip@gmail.com | 6,329,403,839 |
| codehunterextreme@gmail.com | 3,717,819,380 |
| alexander.sorrell.it@gmail.com | 83,212,683 |
| API key (org 15a93e14-aabb-4293-8228-8c56a803d972) | 437,619 |

---

## DeepSeek

**1,445,952,016 tokens** (12.5% of all Claude Code)

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

