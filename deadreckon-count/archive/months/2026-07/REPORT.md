# 2026-07

**12,435,499,742 tokens** · 201 sessions · 64,756 turns · 15d 19h 14m

_This month is over. Frozen from the largest set of records anyone has held: it is rewritten only when a rescan finds MORE than the frozen copy, and never when it finds fewer — the transcripts behind it are deleted after `cleanupPeriodDays`, so a smaller recount is loss, not a correction._

_2026-07-02 .. 2026-08-05_

## By CLI

| | tokens | share | |
|---|---:|---:|---|
| claude | 10,659,640,061 |  85.7% | ★ |
| codex | 1,633,604,881 |  13.1% | † |
| grok | 76,724,862 |   0.6% | † |
| antigravity | 65,529,938 |   0.5% | † |

★ true lifetime — vendor counter on disk survives transcript deletion  † from daemon start — no vendor counter exists; the ledger is the only record

> **† figures depend on the retention daemon.** The ledger only grows when the daemon records, while transcripts keep expiring regardless. If it stops, these totals do not freeze — they decay, and nothing else will say so. `python3 run.py status` reports whether it is running on the machine you are on.

## By computer

| | tokens | share |
|---|---:|---:|
| MacBook Air M1 | 12,435,499,742 | 100.0% |

## By model

| | tokens | share |
|---|---:|---:|
| claude-opus-4-8 | 5,363,938,900 |  43.1% |
| claude-opus-5 | 4,813,362,822 |  38.7% |
| gpt-5.6-sol | 1,451,179,368 |  11.7% |
| claude-fable-5 | 482,338,339 |   3.9% |
| gpt-5.6-luna | 180,826,644 |   1.5% |
| grok-4.5-build | 76,724,862 |   0.6% |
| gemini-3-flash-agent | 39,176,734 |   0.3% |
| gemini-3.1-flash-image | 25,696,363 |   0.2% |
| codex-auto-review | 1,598,869 |   0.0% |
| gemini-3.6-flash-medium | 656,841 |   0.0% |
| codex | 0 |   0.0% |

