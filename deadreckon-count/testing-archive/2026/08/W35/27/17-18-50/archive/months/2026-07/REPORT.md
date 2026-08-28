# 2026-07

**34,478,818,356 tokens** · 2,291 sessions · 161,341 turns · 92d 19h 54m

_This month is over. Frozen from the largest set of records anyone has held: it is rewritten only when a rescan finds MORE than the frozen copy, and never when it finds fewer — the transcripts behind it are deleted after `cleanupPeriodDays`, so a smaller recount is loss, not a correction._

_2026-07-02 .. 2026-08-05_

## By CLI

| | tokens | share | |
|---|---:|---:|---|
| claude | 32,702,958,675 |  94.8% | ★ |
| codex | 1,633,604,881 |   4.7% | † |
| grok | 76,724,862 |   0.2% | † |
| antigravity | 65,529,938 |   0.2% | † |

★ true lifetime — vendor counter on disk survives transcript deletion  † from daemon start — no vendor counter exists; the ledger is the only record

> **† figures depend on the retention daemon.** The ledger only grows when the daemon records, while transcripts keep expiring regardless. If it stops, these totals do not freeze — they decay, and nothing else will say so. `python3 run.py status` reports whether it is running on the machine you are on.

## By computer

| | tokens | share |
|---|---:|---:|
| MacBookAir | 22,043,318,614 |  63.9% |
| MacBook Air M1 (Darwin ARM64) | 12,435,499,742 |  36.1% |

## By model

| | tokens | share |
|---|---:|---:|
| claude-opus-4-8 | 18,960,751,446 |  55.0% |
| claude-opus-5 | 12,136,621,242 |  35.2% |
| claude-fable-5 | 1,602,268,162 |   4.6% |
| gpt-5.6-sol | 1,451,179,368 |   4.2% |
| gpt-5.6-luna | 180,826,644 |   0.5% |
| grok-4.5-build | 76,724,862 |   0.2% |
| gemini-3-flash-agent | 39,176,734 |   0.1% |
| gemini-3.1-flash-image | 25,696,363 |   0.1% |
| claude-haiku-4-5-20251001 | 1,733,833 |   0.0% |
| codex-auto-review | 1,598,869 |   0.0% |
| claude-sonnet-5 | 1,583,992 |   0.0% |
| gemini-3.6-flash-medium | 656,841 |   0.0% |
| proj-475024d6 | 0 |   0.0% |
| codex | 0 |   0.0% |

