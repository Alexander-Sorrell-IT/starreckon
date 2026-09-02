# HP Laptop Linux — lifetime

**38,545,076,029 tokens** · 347 sessions · 76,194 turns · 20d 21h 1m

_Everything this computer has ever recorded, across every CLI._

_2025-07-01 .. 2026-09-01_

## By CLI

| | tokens | share | |
|---|---:|---:|---|
| claude | 36,198,656,291 |  93.9% | ★ |
| gemini | 1,468,362,549 |   3.8% | † |
| copilot | 295,831,967 |   0.8% | † |
| clawspring | 258,502,806 |   0.7% | † |
| bob | 229,043,592 |   0.6% | † |
| antigravity | 83,601,215 |   0.2% | † |
| kilocode | 7,074,501 |   0.0% | † |
| codex | 1,454,074 |   0.0% | † |
| copilot-chat | 1,214,160 |   0.0% | † |
| lmstudio | 119,774 |   0.0% | † |

★ true lifetime — vendor counter on disk survives transcript deletion  † from daemon start — no vendor counter exists; the ledger is the only record

## By computer

| | tokens | share |
|---|---:|---:|
| HP Laptop Linux | 38,545,076,029 | 100.0% |

## By model

| | tokens | share |
|---|---:|---:|
| claude-opus-5 | 6,461,415,816 |  16.8% |
| claude-opus-4-7 | 2,442,555,117 |   6.3% |
| claude-fable-5 | 1,537,543,647 |   4.0% |
| gemini-3-flash-preview | 1,200,420,521 |   3.1% |
| deepseek-v4-pro | 534,671,153 |   1.4% |
| unknown | 264,442,058 |   0.7% |
| bob | 229,043,592 |   0.6% |
| claude-opus-4-8 | 227,833,205 |   0.6% |
| gpt-5.5 | 225,314,053 |   0.6% |
| gemini-3-pro-preview | 201,035,389 |   0.5% |
| claude-sonnet-5 | 177,021,920 |   0.5% |
| claude-sonnet-4-6 | 170,325,751 |   0.4% |
| gemini-2.5-pro | 66,610,041 |   0.2% |
| gpt-5.4-mini | 64,578,662 |   0.2% |
| gemini-3-flash-d | 20,218,246 |   0.1% |

## What the ledger adds

**13,895,407,082** of the headline is on disk now. **1,214,160** is on disk and was NOT READ: the committed scan has no reader for copilot-chat, so their whole lifetime falls outside the scan. Nothing was deleted; the scanner is behind, and this number goes DOWN when a reader is added. **1,214,160** is not on disk: it is work whose transcripts have been deleted, held only by the append-only `token_ledger.jsonl` in each machine folder. The session and turn counts above cover the scanned part only — a vanished session is one row of arithmetic, not a session anyone can still open — and no month below includes any of it, because a vanished session's last observation may carry no date.

| computer | scanned | ledger | beyond the scan | ledger file |
|---|---:|---:|---:|---|
| HP Laptop Linux | 13,895,407,082 | 13,367,051,701 | +0 | yes |

## What stats-cache adds

**24,648,454,787** tokens are added by the stats-cache floor. Claude Code writes `stats-cache.json` into each profile and accumulates every session there, including ones whose transcripts have since been deleted by `cleanupPeriodDays`. The counter survives deletion; the transcript does not. **24,647,239,687** of that is Claude Code; 1,215,100 is attributed to other tools. The floor is applied per account: `max(counter_total + transcripts_after_counter_date, scan_total)`, so it never contradicts work already on disk.

## What the tokens were

| | tokens | share |
|---|---:|---:|
| re-read from cache | 11,200,981,609 |  97.0% |
| written to cache | 266,408,747 |   2.3% |
| sent fresh | 24,303,172 |   0.2% |
| **generated** | 59,723,076 |   0.5% |

Most of any total is the conversation being re-sent, not new writing. Read that share before quoting the headline.

