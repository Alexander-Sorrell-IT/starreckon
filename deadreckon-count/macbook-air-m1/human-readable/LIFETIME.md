# MacBook Air M1 — lifetime

**53,348,797,924 tokens** · 283 sessions · 108,823 turns · 29d 10h 26m

_Everything this computer has ever recorded, across every CLI._

_2025-07-03 .. 2026-08-20_

## By CLI

| | tokens | share | |
|---|---:|---:|---|
| claude | 49,684,924,274 |  93.1% | ★ |
| codex | 1,633,604,881 |   3.1% | † |
| gemini | 995,360,683 |   1.9% | † |
| copilot | 497,696,783 |   0.9% | † |
| bob | 301,824,300 |   0.6% | † |
| antigravity | 135,111,522 |   0.3% | † |
| grok | 100,222,322 |   0.2% | † |
| lmstudio | 53,159 |   0.0% | † |

★ true lifetime — vendor counter on disk survives transcript deletion  † from daemon start — no vendor counter exists; the ledger is the only record

## By computer

| | tokens | share |
|---|---:|---:|
| MacBook Air M1 | 53,348,797,924 | 100.0% |

## By model

| | tokens | share |
|---|---:|---:|
| claude-opus-5 | 11,931,558,295 |  22.4% |
| claude-opus-4-8 | 5,363,938,900 |  10.1% |
| gpt-5.6-sol | 1,451,179,368 |   2.7% |
| gemini-3-flash-preview | 935,481,455 |   1.8% |
| claude-fable-5 | 495,265,511 |   0.9% |
| claude-sonnet-4.6 | 279,118,768 |   0.5% |
| claude-sonnet-4-6 | 243,949,169 |   0.5% |
| gpt-5.6-luna | 180,826,644 |   0.3% |
| grok-4.5-build | 100,222,322 |   0.2% |
| claude-opus-4.7 | 94,058,304 |   0.2% |
| gemini-3.1-pro-preview | 62,655,823 |   0.1% |
| unknown | 59,372,409 |   0.1% |
| gemini-3-flash-d | 54,221,143 |   0.1% |
| gemini-3-flash-agent | 48,392,056 |   0.1% |
| claude-haiku-4.5 | 36,579,835 |   0.1% |

## What the ledger adds

**21,669,531,684** of the headline is on disk now. **971,454,645** is not on disk: it is work whose transcripts have been deleted, held only by the append-only `token_ledger.jsonl` in each machine folder. The session and turn counts above cover the scanned part only — a vanished session is one row of arithmetic, not a session anyone can still open — and no month below includes any of it, because a vanished session's last observation may carry no date.

| computer | scanned | ledger | beyond the scan | ledger file |
|---|---:|---:|---:|---|
| MacBook Air M1 | 21,669,531,684 | 22,640,986,329 | +971,454,645 | yes |

## What stats-cache adds

**30,707,811,595** tokens are added by the stats-cache floor. Claude Code writes `stats-cache.json` into each profile and accumulates every session there, including ones whose transcripts have since been deleted by `cleanupPeriodDays`. The counter survives deletion; the transcript does not. **30,707,811,595** of that is Claude Code; 0 is attributed to other tools. The floor is applied per account: `max(counter_total + transcripts_after_counter_date, scan_total)`, so it never contradicts work already on disk.

## What the tokens were

| | tokens | share |
|---|---:|---:|
| re-read from cache | 17,457,622,352 |  96.8% |
| written to cache | 494,608,452 |   2.7% |
| sent fresh | 4,303,668 |   0.0% |
| **generated** | 75,660,273 |   0.4% |

Most of any total is the conversation being re-sent, not new writing. Read that share before quoting the headline.

