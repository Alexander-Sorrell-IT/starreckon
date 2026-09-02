# By company

_What each vendor was actually paid for_

_Generated 2026-08-05T05:53:14-05:00 by `stats_page.py`. Do not edit by hand._

**43,720,186,216** tokens of Claude Code across 5 scanned computer(s) · **50,050,449,676** across every CLI on the 5 that ran `sessions.py`.

Those two are not added: the second contains the first. See [BY-COMPUTER.md](BY-COMPUTER.md) for the reconciliation.

Reports: [computers](BY-COMPUTER.md) · [accounts](BY-ACCOUNT.md) · [companies](BY-COMPANY.md) · [how it works](README.md)

---

_scans taken 2026-08-04 01:46:32 .. 2026-08-05 04:13:10_

Claude Code can be pointed at a non-Anthropic backend and the transcripts look identical, so a raw total is not an Anthropic total. Split on the model id.

| Company | Tag | Tokens | Share | |
|---|---|---:|---:|---|
| **Anthropic** | `anthropic` | 42,274,234,200 | 96.7% | ███████████████████████████· |
| **DeepSeek** | `deepseek` | 1,445,952,016 | 3.3% | █··························· |
| **All** | | **43,720,186,216** | 100% | |

### Who served it, versus who was paid for the tool

Different questions. Copilot runs Claude models: that is GitHub spend and Anthropic service.

| Company | Sessions | Active | Tokens | Via |
|---|---:|---:|---:|---|
| Anthropic | 13,454 | 664h 47m | 41,980,706,706 | claude 41.54B, copilot 442.12M |
| Google | 130 | 112h 57m | 2,815,281,086 | gemini 2.60B, antigravity 210.63M, kilocode 7.03M |
| OpenAI | 176 | 93h 06m | 2,603,732,372 | codex 2.31B, copilot 290.55M |
| DeepSeek | 48 | 76h 03m | 1,445,955,546 | claude 1.45B, lmstudio 3.53K |
| — (no API call) | 3,267 | 138h 04m | 1,123,159,069 | copilot 1.12B |
| xAI | 6 | 7h 40m | 76,735,508 | grok 76.72M, kilocode 10.65K |
| — (unidentified) | 7 | 16m | 4,763,145 | antigravity 4.67M, lmstudio 53.16K, kilocode 38.73K |
| Mistral | 5 | 0m | 116,185 | lmstudio 116.19K |
| Meta | 1 | 0m | 59 | lmstudio 59 |

---

## Anthropic

**42,274,234,200 tokens** (96.7% of all Claude Code)

| Model | Tokens |
|---|---:|
| `claude-opus-4-8` | 18,220,180,407 |
| `claude-opus-5` | 14,596,755,106 |
| `claude-opus-4-7` | 5,747,588,911 |
| `claude-fable-5` | 3,440,724,152 |
| `claude-sonnet-4-6` | 238,157,236 |
| `claude-haiku-4-5-20251001` | 27,857,095 |
| `claude-sonnet-5` | 1,583,992 |
| `claude-opus-4-5-20251101` | 996,934 |
| `claude-opus-4-6` | 390,367 |

| Computer | Tokens |
|---|---:|
| MacBook Air M1 | 28,492,335,565 |
| HP Laptop Linux | 9,787,445,366 |
| Dell Latitude 7480 Linux | 3,726,175,980 |
| ASUS Laptop Linux | 266,146,676 |
| Dell Inspiron Desktop Linux | 2,130,613 |

| Account | Tokens |
|---|---:|
| broodierchip@gmail.com | 25,594,119,794 |
| codehunterextreme@gmail.com | 13,836,657,412 |
| alexander.sorrell.it@gmail.com | 2,835,737,509 |
| user:2d4777822844 | 7,281,866 |
| API key (org 15a93e14-aabb-4293-8228-8c56a803d972) | 437,619 |

---

## DeepSeek

**1,445,952,016 tokens** (3.3% of all Claude Code)

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

