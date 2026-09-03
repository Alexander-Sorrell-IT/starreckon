# By company

_What each vendor was actually paid for_

_Generated 2026-08-08T14:46:59-05:00 by `stats_page.py`. Do not edit by hand._

**49,292,589,255** tokens of Claude Code across 5 scanned computer(s) · **56,574,551,436** across every CLI on the 5 that ran `sessions.py`.

Those two are not added: the second contains the first. See [BY-COMPUTER.md](BY-COMPUTER.md) for the reconciliation.

Reports: [computers](BY-COMPUTER.md) · [accounts](BY-ACCOUNT.md) · [companies](BY-COMPANY.md) · [how it works](README.md)

---

_scans taken 2026-08-06 00:50:35 .. 2026-08-08 14:46:25_

Claude Code can be pointed at a non-Anthropic backend and the transcripts look identical, so a raw total is not an Anthropic total. Split on the model id.

| Company | Tag | Tokens | Share | |
|---|---|---:|---:|---|
| **Anthropic** | `anthropic` | 47,846,637,239 | 97.1% | ███████████████████████████· |
| **DeepSeek** | `deepseek` | 1,445,952,016 | 2.9% | █··························· |
| **All** | | **49,292,589,255** | 100% | |

### Who served it, versus who was paid for the tool

Different questions. Copilot runs Claude models: that is GitHub spend and Anthropic service.

| Company | Sessions | Active | Tokens | Via |
|---|---:|---:|---:|---|
| Anthropic | 13,527 | 813h 09m | 48,291,424,393 | claude 47.85B, copilot 442.12M |
| Google | 155 | 130h 56m | 3,019,451,028 | gemini 2.79B, antigravity 222.72M, kilocode 7.03M |
| OpenAI | 176 | 93h 07m | 2,604,133,300 | codex 2.31B, copilot 290.55M |
| DeepSeek | 48 | 76h 03m | 1,445,955,546 | claude 1.45B, lmstudio 3.53K |
| — (no API call) | 3,271 | 138h 04m | 1,123,159,069 | copilot 1.12B |
| xAI | 7 | 8h 57m | 90,219,964 | grok 90.21M, kilocode 10.65K |
| Mistral | 5 | 0m | 116,185 | lmstudio 116.19K |
| — (unidentified) | 4 | 1m | 91,892 | lmstudio 53.16K, kilocode 38.73K |
| Meta | 1 | 0m | 59 | lmstudio 59 |

---

## Anthropic

**47,846,637,239 tokens** (97.1% of all Claude Code)

| Model | Tokens |
|---|---:|
| `claude-opus-5` | 18,494,684,062 |
| `claude-opus-4-8` | 18,229,389,271 |
| `claude-opus-4-7` | 5,748,576,800 |
| `claude-fable-5` | 3,565,152,147 |
| `claude-opus-4-6` | 834,041,599 |
| `claude-opus-4-5-20251101` | 575,579,698 |
| `claude-sonnet-4-6` | 244,400,986 |
| `claude-haiku-4-5-20251001` | 136,803,508 |
| `claude-sonnet-4-5-20250929` | 16,304,590 |
| `claude-sonnet-5` | 1,704,578 |

| Computer | Tokens |
|---|---:|
| MacBook Air M1 | 29,170,327,621 |
| HP Laptop Linux | 13,083,421,773 |
| Dell Latitude 7480 Linux | 5,324,610,556 |
| ASUS Laptop Linux | 266,146,676 |
| Dell Inspiron Desktop Linux | 2,130,613 |

| Account | Tokens |
|---|---:|
| second@example.com | 26,388,450,112 |
| third@example.com | 17,338,936,493 |
| owner@example.com | 2,894,443,336 |
| unknown (Desktop_standout_clean_.claude) | 731,855,322 |
| unknown (Desktop_standout_full_.claude) | 483,526,465 |
| user:2d4777822844 | 7,281,866 |
| unknown (.claude-alt) | 1,706,026 |
| API key (org 15a93e14-aabb-4293-8228-8c56a803d972) | 437,619 |

---

## DeepSeek

**1,445,952,016 tokens** (2.9% of all Claude Code)

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

**14,529,373,789 tokens** from 3 company(s)

| Company | Tokens | Share |
|---|---:|---:|
| Anthropic | 13,083,421,773 |  90.0% |
| DeepSeek | 1,445,952,016 |  10.0% |
| — (no API call) | 0 |   0.0% |

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

