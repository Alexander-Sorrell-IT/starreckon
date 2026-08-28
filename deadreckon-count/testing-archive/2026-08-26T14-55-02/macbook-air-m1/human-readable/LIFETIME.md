# MacBook Air M1 — lifetime

**49,129,681,020 tokens** · 277 sessions · 100,335 turns · 25d 22h 27m

_Everything this computer has ever recorded, across every CLI._

_2025-07-03 .. 2026-08-12_

## By CLI

| | tokens | share | |
|---|---:|---:|---|
| claude | 45,528,480,450 |  92.7% | ★ |
| codex | 1,633,604,881 |   3.3% | † |
| gemini | 995,360,683 |   2.0% | † |
| copilot | 497,696,783 |   1.0% | † |
| bob | 240,310,669 |   0.5% | † |
| antigravity | 135,111,522 |   0.3% | † |
| grok | 99,062,873 |   0.2% | † |
| lmstudio | 53,159 |   0.0% | † |

★ true lifetime — vendor counter on disk survives transcript deletion  † from daemon start — no vendor counter exists; the ledger is the only record

## By computer

| | tokens | share |
|---|---:|---:|
| MacBook Air M1 | 49,129,681,020 | 100.0% |

## By model

| | tokens | share |
|---|---:|---:|
| claude-opus-5 | 8,715,518,485 |  17.7% |
| claude-opus-4-8 | 5,363,938,900 |  10.9% |
| gpt-5.6-sol | 1,451,179,368 |   3.0% |
| gemini-3-flash-preview | 935,481,455 |   1.9% |
| claude-fable-5 | 495,265,511 |   1.0% |
| claude-sonnet-4.6 | 279,118,768 |   0.6% |
| claude-sonnet-4-6 | 243,949,169 |   0.5% |
| gpt-5.6-luna | 180,826,644 |   0.4% |
| grok-4.5-build | 99,062,873 |   0.2% |
| claude-opus-4.7 | 94,058,304 |   0.2% |
| gemini-3.1-pro-preview | 62,655,823 |   0.1% |
| unknown | 59,372,409 |   0.1% |
| gemini-3-flash-d | 54,221,143 |   0.1% |
| gemini-3-flash-agent | 48,392,056 |   0.1% |
| claude-haiku-4.5 | 36,579,835 |   0.1% |

## What the ledger adds

**18,420,025,759** of the headline is on disk now. **0** is not on disk: it is work whose transcripts have been deleted, held only by the append-only `token_ledger.jsonl` in each machine folder. The session and turn counts above cover the scanned part only — a vanished session is one row of arithmetic, not a session anyone can still open — and no month below includes any of it, because a vanished session's last observation may carry no date.

| computer | scanned | ledger | beyond the scan | ledger file |
|---|---:|---:|---:|---|
| MacBook Air M1 | 18,420,025,759 | 17,354,720,610 | +0 | yes |

## What stats-cache adds

**30,709,655,261** tokens are added by the stats-cache floor. Claude Code writes `stats-cache.json` into each profile and accumulates every session there, including ones whose transcripts have since been deleted by `cleanupPeriodDays`. The counter survives deletion; the transcript does not. **30,709,655,261** of that is Claude Code; 0 is attributed to other tools. The floor is applied per account: `max(counter_total + transcripts_after_counter_date, scan_total)`, so it never contradicts work already on disk.

## What the tokens were

| | tokens | share |
|---|---:|---:|
| re-read from cache | 14,300,619,229 |  96.5% |
| written to cache | 445,098,382 |   3.0% |
| sent fresh | 4,267,293 |   0.0% |
| **generated** | 68,013,697 |   0.5% |

Most of any total is the conversation being re-sent, not new writing. Read that share before quoting the headline.

