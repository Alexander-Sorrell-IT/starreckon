# MacBook Air M1 (Darwin ARM64) — lifetime

**54,722,146,830 tokens** · 298 sessions · 118,194 turns · 32d 3h 29m

_Everything this computer has ever recorded, across every CLI._

_2025-07-03 .. 2026-08-26_

## By CLI

| | tokens | share | |
|---|---:|---:|---|
| claude | 50,010,376,436 |  91.4% | ★ |
| codex | 1,633,604,881 |   3.0% | † |
| antigravity | 1,137,465,925 |   2.1% | † |
| gemini | 995,360,683 |   1.8% | † |
| copilot | 572,446,089 |   1.0% | † |
| bob | 272,617,335 |   0.5% | † |
| grok | 100,222,322 |   0.2% | † |
| lmstudio | 53,159 |   0.0% | † |

★ true lifetime — vendor counter on disk survives transcript deletion  † from daemon start — no vendor counter exists; the ledger is the only record

> **† figures depend on the retention daemon.** The ledger only grows when the daemon records, while transcripts keep expiring regardless. If it stops, these totals do not freeze — they decay, and nothing else will say so. `python3 run.py status` reports whether it is running on the machine you are on.

## By computer

| | tokens | share |
|---|---:|---:|
| MacBook Air M1 (Darwin ARM64) | 54,722,146,830 | 100.0% |

## By model

| | tokens | share |
|---|---:|---:|
| claude-opus-5 | 12,384,457,033 |  22.6% |
| claude-opus-4-8 | 5,363,938,900 |   9.8% |
| gpt-5.6-sol | 1,451,179,368 |   2.7% |
| gemini-3-flash-preview | 932,704,860 |   1.7% |
| gemini-3.7-flash-safety-le | 930,363,796 |   1.7% |
| claude-fable-5 | 495,265,511 |   0.9% |
| claude-sonnet-4.6 | 279,118,768 |   0.5% |
| claude-sonnet-4-6 | 243,949,169 |   0.4% |
| gpt-5.6-luna | 180,826,644 |   0.3% |
| grok-4.5-build | 100,222,322 |   0.2% |
| claude-opus-4.7 | 94,058,304 |   0.2% |
| gpt-5.6-terra | 74,710,059 |   0.1% |
| gemini-3.7-flash-low | 63,791,884 |   0.1% |
| gemini-3.1-pro-preview | 62,655,823 |   0.1% |
| unknown | 59,372,409 |   0.1% |

## Undated sessions

**1,174,424,977 tokens** across **19 session(s)** have no start timestamp and cannot be placed in any month. They are real work — counted in the every-CLI total — but their transcripts carried no `timestamp` field, so the month is unknown. They are included in the headline token figure above; the session, turn and duration counts there cover dated sessions only.

| CLI | tokens |
|---|---:|
| claude | 1,174,424,977 |

## What the ledger adds

**23,139,167,869** of the headline is on disk now. **60,366,262** is not on disk: it is work whose transcripts have been deleted, held only by the append-only `token_ledger.jsonl` in each machine folder. The session and turn counts above cover the scanned part only — a vanished session is one row of arithmetic, not a session anyone can still open — and no month below includes any of it, because a vanished session's last observation may carry no date.

| computer | scanned | ledger | beyond the scan | ledger file |
|---|---:|---:|---:|---|
| MacBook Air M1 (Darwin ARM64) | 24,313,592,846 | 24,373,959,108 | +60,366,262 | yes |

## What stats-cache adds

**30,348,187,722** tokens are added by the stats-cache floor. Claude Code writes `stats-cache.json` into each profile and accumulates every session there, including ones whose transcripts have since been deleted by `cleanupPeriodDays`. The counter survives deletion; the transcript does not. **30,348,187,722** of that is Claude Code; 0 is attributed to other tools. The floor is applied per account: `max(counter_total + transcripts_after_counter_date, scan_total)`, so it never contradicts work already on disk.

## What the tokens were

| | tokens | share |
|---|---:|---:|
| re-read from cache | 17,903,132,137 |  96.8% |
| written to cache | 503,101,074 |   2.7% |
| sent fresh | 4,309,593 |   0.0% |
| **generated** | 77,220,933 |   0.4% |

Most of any total is the conversation being re-sent, not new writing. Read that share before quoting the headline.

