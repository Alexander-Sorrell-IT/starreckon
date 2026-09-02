# Lifetime

**49,768,570,900 tokens** · 279 sessions · 101,685 turns · 26d 17h 49m

_Everything ever recorded on any computer in this fleet, across every CLI. This counts what still exists plus what was captured before it expired._

_2025-07-03 .. 2026-08-15_

## By CLI

| | tokens | share | |
|---|---:|---:|---|
| claude | 46,104,697,250 |  92.6% | ★ |
| codex | 1,633,604,881 |   3.3% | † |
| gemini | 995,360,683 |   2.0% | † |
| copilot | 497,696,783 |   1.0% | † |
| bob | 301,824,300 |   0.6% | † |
| antigravity | 135,111,522 |   0.3% | † |
| grok | 100,222,322 |   0.2% | † |
| lmstudio | 53,159 |   0.0% | † |

★ true lifetime — vendor counter on disk survives transcript deletion  † from daemon start — no vendor counter exists; the ledger is the only record

## By computer

| | tokens | share |
|---|---:|---:|
| MacBook Air M1 | 49,768,570,900 | 100.0% |

## By model

| | tokens | share |
|---|---:|---:|
| claude-opus-5 | 9,292,056,280 |  18.7% |
| claude-opus-4-8 | 5,363,938,900 |  10.8% |
| gpt-5.6-sol | 1,451,179,368 |   2.9% |
| gemini-3-flash-preview | 935,481,455 |   1.9% |
| claude-fable-5 | 495,265,511 |   1.0% |
| claude-sonnet-4.6 | 279,118,768 |   0.6% |
| claude-sonnet-4-6 | 243,949,169 |   0.5% |
| gpt-5.6-luna | 180,826,644 |   0.4% |
| grok-4.5-build | 100,222,322 |   0.2% |
| claude-opus-4.7 | 94,058,304 |   0.2% |
| gemini-3.1-pro-preview | 62,655,823 |   0.1% |
| unknown | 59,372,409 |   0.1% |
| gemini-3-flash-d | 54,221,143 |   0.1% |
| gemini-3-flash-agent | 48,392,056 |   0.1% |
| claude-haiku-4.5 | 36,579,835 |   0.1% |

## Undated sessions

**1,174,424,977 tokens** across **19 session(s)** have no start timestamp and cannot be placed in any month. They are real work — counted in the every-CLI total — but their transcripts carried no `timestamp` field, so the month is unknown. They are included in the headline figure above.

| CLI | tokens |
|---|---:|
| claude | 1,174,424,977 |

## Each computer

### MacBook Air M1

**19,030,029,669 tokens** · 279 sessions · 101,685 turns · 26d 17h 49m

_2025-07-03 .. 2026-08-15_

| CLI | tokens | share |
|---|---:|---:|
| claude | 15,395,362,984 |  80.9% |
| codex | 1,633,604,881 |   8.6% |
| gemini | 995,360,683 |   5.2% |
| copilot | 497,696,783 |   2.6% |
| bob | 272,617,335 |   1.4% |
| antigravity | 135,111,522 |   0.7% |
| grok | 100,222,322 |   0.5% |
| lmstudio | 53,159 |   0.0% |

## What the ledger adds

**19,030,029,669** of the headline is on disk now. **29,206,965** is not on disk: it is work whose transcripts have been deleted, held only by the append-only `token_ledger.jsonl` in each machine folder. The session and turn counts above cover the scanned part only — a vanished session is one row of arithmetic, not a session anyone can still open — and no month below includes any of it, because a vanished session's last observation may carry no date.

| computer | scanned | ledger | beyond the scan | ledger file |
|---|---:|---:|---:|---|
| MacBook Air M1 | 20,204,454,646 | 20,233,661,611 | +29,206,965 | yes |

## What stats-cache adds

**30,709,334,266** tokens are added by the stats-cache floor. Claude Code writes `stats-cache.json` into each profile and accumulates every session there, including ones whose transcripts have since been deleted by `cleanupPeriodDays`. The counter survives deletion; the transcript does not. **30,709,334,266** of that is Claude Code; 0 is attributed to other tools. The floor is applied per account: `max(counter_total + transcripts_after_counter_date, scan_total)`, so it never contradicts work already on disk.

## What the tokens were

| | tokens | share |
|---|---:|---:|
| re-read from cache | 14,863,743,267 |  96.6% |
| written to cache | 457,075,679 |   3.0% |
| sent fresh | 4,269,822 |   0.0% |
| **generated** | 69,126,633 |   0.4% |

Most of any total is the conversation being re-sent, not new writing. Read that share before quoting the headline.

