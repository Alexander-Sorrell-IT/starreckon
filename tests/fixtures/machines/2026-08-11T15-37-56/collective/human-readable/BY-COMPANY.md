# By company

_What each vendor was actually paid for_

_Generated 2026-08-09T02:52:23-05:00 by `stats_page.py`. Do not edit by hand._

**6,868,321,450** tokens of Claude Code across 3 scanned computer(s) · **8,693,210,554** across every CLI on the 3 that ran `sessions.py`.

Those two are not added: the second contains the first. See [BY-COMPUTER.md](BY-COMPUTER.md) for the reconciliation.

Reports: [computers](BY-COMPUTER.md) · [accounts](BY-ACCOUNT.md) · [companies](BY-COMPANY.md) · [how it works](README.md)

---

_scans taken 2026-08-09 00:54:17 .. 2026-08-09 02:32:05_

Claude Code can be pointed at a non-Anthropic backend and the transcripts look identical, so a raw total is not an Anthropic total. Split on the model id.

| Company | Tag | Tokens | Share | |
|---|---|---:|---:|---|
| **Anthropic** | `anthropic` | 6,333,650,297 | 92.2% | ██████████████████████████·· |
| **DeepSeek** | `deepseek` | 534,671,153 | 7.8% | ██·························· |
| **All** | | **6,868,321,450** | 100% | |

### Who served it, versus who was paid for the tool

Different questions. Copilot runs Claude models: that is GitHub spend and Anthropic service.

| Company | Sessions | Active | Tokens | Via |
|---|---:|---:|---:|---|
| Anthropic | 143 | 216h 12m | 6,334,466,619 | claude 6.33B |
| Google | 78 | 77h 29m | 1,525,897,976 | gemini 1.47B, antigravity 45.27M, kilocode 7.03M |
| DeepSeek | 48 | 76h 03m | 534,674,683 | claude 534.67M, lmstudio 3.53K |
| OpenAI | 29 | 34h 10m | 292,016,406 | copilot 289.89M, codex 2.12M |
| — (no API call) | 9 | 21h 15m | 5,989,247 | copilot 5.94M, claude 49.99K |
| Mistral | 5 | 0m | 116,185 | lmstudio 116.19K |
| — (unidentified) | 1 | 1m | 38,733 | kilocode 38.73K |
| xAI | 1 | 0m | 10,646 | kilocode 10.65K |
| Meta | 1 | 0m | 59 | lmstudio 59 |

---

## Anthropic

**6,333,650,297 tokens** (92.2% of all Claude Code)

| Model | Tokens |
|---|---:|
| `claude-opus-4-7` | 2,685,485,936 |
| `claude-opus-5` | 2,329,706,523 |
| `claude-opus-4-8` | 637,452,927 |
| `claude-fable-5` | 616,373,544 |
| `claude-sonnet-4-6` | 53,696,007 |
| `claude-haiku-4-5-20251001` | 10,441,909 |
| `claude-opus-4-5-20251101` | 372,865 |
| `claude-sonnet-5` | 120,586 |

| Computer | Tokens |
|---|---:|
| HP Laptop Linux | 6,199,629,801 |
| ASUS Laptop Linux | 133,195,610 |
| Dell Inspiron Desktop Linux | 824,886 |

| Account | Tokens |
|---|---:|
| third@example.com | 3,091,271,390 |
| second@example.com | 2,704,804,986 |
| unknown (Desktop_standout_clean_.claude) | 321,101,727 |
| unknown (Desktop_standout_full_.claude) | 167,829,804 |
| owner@example.com | 43,831,821 |
| unknown (Desktop_standout_max_.claude) | 4,669,359 |
| API key (org 15a93e14-aabb-4293-8228-8c56a803d972) | 141,210 |

---

## DeepSeek

**534,671,153 tokens** (7.8% of all Claude Code)

| Model | Tokens |
|---|---:|
| `deepseek-v4-pro` | 500,679,426 |
| `deepseek-v4-flash` | 33,991,727 |

| Computer | Tokens |
|---|---:|
| HP Laptop Linux | 534,671,153 |

| Account | Tokens |
|---|---:|
| DeepSeek backend (~/.my-claude) | 520,497,793 |
| second@example.com | 14,173,360 |

---

## Each computer

_The same tokens, grouped by machine instead of by vendor._

### HP Laptop Linux

**6,734,300,954 tokens** from 2 company(s)

| Company | Tokens | Share |
|---|---:|---:|
| Anthropic | 6,199,629,801 |  92.1% |
| DeepSeek | 534,671,153 |   7.9% |

### ASUS Laptop Linux

**133,195,610 tokens** from 1 company(s)

| Company | Tokens | Share |
|---|---:|---:|
| Anthropic | 133,195,610 | 100.0% |

### Dell Inspiron Desktop Linux

**824,886 tokens** from 1 company(s)

| Company | Tokens | Share |
|---|---:|---:|
| Anthropic | 824,886 | 100.0% |

