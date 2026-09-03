# By company

_What each vendor was actually paid for_

_Generated 2026-08-04T04:05:09-05:00 by `stats_page.py`. Do not edit by hand._

**41,881,904,108** tokens of Claude Code across 5 scanned computer(s) · **43,253,565,485** across every CLI on the 4 that ran `sessions.py`.

Those two are not added: the second contains the first. See [BY-COMPUTER.md](BY-COMPUTER.md) for the reconciliation.

Reports: [computers](BY-COMPUTER.md) · [accounts](BY-ACCOUNT.md) · [companies](BY-COMPANY.md) · [how it works](README.md)

---

Claude Code can be pointed at a non-Anthropic backend and the transcripts look identical, so a raw total is not an Anthropic total. Split on the model id.

| Company | Tag | Tokens | Share | |
|---|---|---:|---:|---|
| **Anthropic** | `anthropic` | 40,435,952,092 | 96.5% | ███████████████████████████· |
| **DeepSeek** | `deepseek` | 1,445,952,016 | 3.5% | █··························· |
| **All** | | **41,881,904,108** | 100% | |

### Who served it, versus who was paid for the tool

Different questions. Copilot runs Claude models: that is GitHub spend and Anthropic service.

| Company | Sessions | Active | Tokens | Via |
|---|---:|---:|---:|---|
| Anthropic | 187 | 590h 19m | 37,096,948,664 | claude 36.66B, copilot 437.66M |
| Google | 113 | 99h 08m | 2,638,026,464 | gemini 2.47B, antigravity 162.04M, kilocode 7.03M |
| OpenAI | 156 | 64h 09m | 1,925,881,186 | codex 1.64B, copilot 290.55M |
| DeepSeek | 47 | 76h 03m | 1,445,952,016 | claude 1.45B |
| xAI | 6 | 7h 40m | 76,735,508 | grok 76.72M, kilocode 10.65K |
| — (no API call) | 17 | 58h 09m | 65,311,661 | copilot 65.31M |
| — (unidentified) | 4 | 16m | 4,709,986 | antigravity 4.67M, kilocode 38.73K |

---

## Anthropic

**40,435,952,092 tokens** (96.5% of all Claude Code)

| Model | Tokens |
|---|---:|
| `claude-opus-4-8` | 17,625,907,201 |
| `claude-opus-5` | 13,728,208,038 |
| `claude-opus-4-7` | 5,747,588,911 |
| `claude-fable-5` | 3,069,761,389 |
| `claude-sonnet-4-6` | 238,157,236 |
| `claude-haiku-4-5-20251001` | 23,358,024 |
| `claude-sonnet-5` | 1,583,992 |
| `claude-opus-4-5-20251101` | 996,934 |
| `claude-opus-4-6` | 390,367 |

| Computer | Tokens |
|---|---:|
| MacBook Air M1 | 28,004,982,986 |
| HP Laptop Linux | 8,297,820,473 |
| Dell Latitude 7480 Linux | 3,864,871,344 |
| ASUS Laptop Linux | 266,146,676 |
| Dell Inspiron Desktop Linux | 2,130,613 |

| Account | Tokens |
|---|---:|
| second@example.com | 24,775,412,250 |
| third@example.com | 12,678,387,484 |
| owner@example.com | 2,974,432,873 |
| unknown | 7,281,866 |
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
| second@example.com | 36,164,393 |

