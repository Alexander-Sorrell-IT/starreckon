# MacBook Air M1 — lifetime

**55,252,475,890 tokens** · 327 sessions · 121,171 turns · 30d 21h 10m

_Everything this computer has ever recorded, across every CLI._

_2025-07-03 .. 2026-08-27_

## By CLI

| | tokens | share | |
|---|---:|---:|---|
| claude | 50,010,376,436 |  90.5% | ★ |
| codex | 1,633,604,881 |   3.0% | † |
| antigravity | 1,137,465,925 |   2.1% | † |
| gemini | 995,360,683 |   1.8% | † |
| bob | 802,946,395 |   1.5% | † |
| copilot | 572,446,089 |   1.0% | † |
| grok | 100,222,322 |   0.2% | † |
| lmstudio | 53,159 |   0.0% | † |

★ true lifetime — vendor counter on disk survives transcript deletion  † from daemon start — no vendor counter exists; the ledger is the only record

> **† figures depend on the retention daemon.** The ledger only grows when the daemon records, while transcripts keep expiring regardless. If it stops, these totals do not freeze — they decay, and nothing else will say so. `python3 run.py status` reports whether it is running on the machine you are on.

## By computer

| | tokens | share |
|---|---:|---:|
| MacBook Air M1 | 55,252,475,890 | 100.0% |

## By model

| | tokens | share |
|---|---:|---:|
| claude-opus-5 | 12,384,457,033 |  22.4% |
| claude-opus-4-8 | 5,363,938,900 |   9.7% |
| gpt-5.6-sol | 1,451,179,368 |   2.6% |
| gemini-3-flash-preview | 932,704,860 |   1.7% |
| claude-fable-5 | 495,265,511 |   0.9% |
| claude-sonnet-4.6 | 279,118,768 |   0.5% |
| gemini-3.7-flash-safety-le | 258,520,721 |   0.5% |
| claude-sonnet-4-6 | 243,949,169 |   0.4% |
| gpt-5.6-luna | 180,826,644 |   0.3% |
| gemini-antigravity-root.is_record | 123,203,781 |   0.2% |
| grok-4.5-build | 100,222,322 |   0.2% |
| claude-opus-4.7 | 94,058,304 |   0.2% |
| gpt-5.6-terra | 74,710,059 |   0.1% |
| gemini-3.7-flash-high | 68,400,916 |   0.1% |
| gemini-3.1-pro-preview | 62,655,823 |   0.1% |

## Undated sessions

**1,174,424,977 tokens** across **19 session(s)** have no start timestamp and cannot be placed in any month. They are real work — counted in the every-CLI total — but their transcripts carried no `timestamp` field, so the month is unknown. They are included in the headline token figure above; the session, turn and duration counts there cover dated sessions only.

| CLI | tokens |
|---|---:|
| claude | 1,174,424,977 |

## What the ledger adds

**23,189,885,203** of the headline is on disk now. **539,977,988** is not on disk: it is work whose transcripts have been deleted, held only by the append-only `token_ledger.jsonl` in each machine folder. The session and turn counts above cover the scanned part only — a vanished session is one row of arithmetic, not a session anyone can still open — and no month below includes any of it, because a vanished session's last observation may carry no date.

| computer | scanned | ledger | beyond the scan | ledger file |
|---|---:|---:|---:|---|
| MacBook Air M1 | 24,364,310,180 | 24,373,959,108 | +539,977,988 | yes |

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

