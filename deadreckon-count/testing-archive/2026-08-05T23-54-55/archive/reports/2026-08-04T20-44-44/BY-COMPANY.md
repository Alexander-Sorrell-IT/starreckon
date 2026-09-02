# By company

_What each vendor was actually paid for_

_Generated 2026-08-04T20:44:44-05:00 by `stats_page.py`. Do not edit by hand._

**42,876,749,644** tokens of Claude Code across 5 scanned computer(s) · **44,240,384,685** across every CLI on the 4 that ran `sessions.py`.

Those two are not added: the second contains the first. See [BY-COMPUTER.md](BY-COMPUTER.md) for the reconciliation.

Reports: [computers](BY-COMPUTER.md) · [accounts](BY-ACCOUNT.md) · [companies](BY-COMPANY.md) · [how it works](README.md)

---

_scans taken 2026-08-04 01:46:32 .. 2026-08-04 20:44:23 · 1 machine(s) with no recorded scan time_

Claude Code can be pointed at a non-Anthropic backend and the transcripts look identical, so a raw total is not an Anthropic total. Split on the model id.

| Company | Tag | Tokens | Share | |
|---|---|---:|---:|---|
| **Anthropic** | `anthropic` | 41,430,797,628 | 96.6% | ███████████████████████████· |
| **DeepSeek** | `deepseek` | 1,445,952,016 | 3.4% | █··························· |
| **All** | | **42,876,749,644** | 100% | |

### Who served it, versus who was paid for the tool

Different questions. Copilot runs Claude models: that is GitHub spend and Anthropic service.

| Company | Sessions | Active | Tokens | Via |
|---|---:|---:|---:|---|
| Anthropic | 189 | 602h 08m | 38,083,594,931 | claude 37.65B, copilot 437.66M |
| Google | 113 | 99h 08m | 2,638,026,464 | gemini 2.47B, antigravity 162.04M, kilocode 7.03M |
| OpenAI | 156 | 64h 09m | 1,925,881,186 | codex 1.64B, copilot 290.55M |
| DeepSeek | 48 | 76h 03m | 1,445,955,546 | claude 1.45B, lmstudio 3.53K |
| xAI | 6 | 7h 40m | 76,735,508 | grok 76.72M, kilocode 10.65K |
| — (no API call) | 17 | 58h 09m | 65,311,661 | copilot 65.31M |
| — (unidentified) | 7 | 16m | 4,763,145 | antigravity 4.67M, lmstudio 53.16K, kilocode 38.73K |
| Mistral | 5 | 0m | 116,185 | lmstudio 116.19K |
| Meta | 1 | 0m | 59 | lmstudio 59 |

---

## Anthropic

**41,430,797,628 tokens** (96.6% of all Claude Code)

| Model | Tokens |
|---|---:|
| `claude-opus-4-8` | 17,626,010,471 |
| `claude-opus-5` | 14,517,137,370 |
| `claude-opus-4-7` | 5,747,588,911 |
| `claude-fable-5` | 3,275,574,323 |
| `claude-sonnet-4-6` | 238,157,236 |
| `claude-haiku-4-5-20251001` | 23,358,024 |
| `claude-sonnet-5` | 1,583,992 |
| `claude-opus-4-5-20251101` | 996,934 |
| `claude-opus-4-6` | 390,367 |

| Computer | Tokens |
|---|---:|
| MacBook Air M1 | 28,492,335,565 |
| HP Laptop Linux | 8,805,313,430 |
| Dell Latitude 7480 Linux | 3,864,871,344 |
| ASUS Laptop Linux | 266,146,676 |
| Dell Inspiron Desktop Linux | 2,130,613 |

| Account | Tokens |
|---|---:|
| broodierchip@gmail.com | 24,775,930,006 |
| codehunterextreme@gmail.com | 13,672,715,264 |
| alexander.sorrell.it@gmail.com | 2,974,432,873 |
| unknown | 7,281,866 |
| API key (org 15a93e14-aabb-4293-8228-8c56a803d972) | 437,619 |

---

## DeepSeek

**1,445,952,016 tokens** (3.4% of all Claude Code)

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

