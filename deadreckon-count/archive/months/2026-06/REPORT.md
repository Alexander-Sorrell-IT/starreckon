# 2026-06

**295,983,031 tokens** · 8 sessions · 1,513 turns · 1d 1h 41m

_This month is over. Frozen from the largest set of records anyone has held: it is rewritten only when a rescan finds MORE than the frozen copy, and never when it finds fewer — the transcripts behind it are deleted after `cleanupPeriodDays`, so a smaller recount is loss, not a correction._

_2026-06-01 .. 2026-06-28_

## By CLI

| | tokens | share | |
|---|---:|---:|---|
| claude | 243,949,169 |  82.4% | ★ |
| copilot | 42,818,540 |  14.5% | † |
| antigravity | 9,215,322 |   3.1% | † |

★ true lifetime — vendor counter on disk survives transcript deletion  † from daemon start — no vendor counter exists; the ledger is the only record

> **† figures depend on the retention daemon.** The ledger only grows when the daemon records, while transcripts keep expiring regardless. If it stops, these totals do not freeze — they decay, and nothing else will say so. `python3 run.py status` reports whether it is running on the machine you are on.

## By computer

| | tokens | share |
|---|---:|---:|
| MacBook Air M1 | 295,983,031 | 100.0% |

## By model

| | tokens | share |
|---|---:|---:|
| claude-sonnet-4-6 | 243,949,169 |  82.4% |
| claude-opus-4.8 | 27,906,640 |   9.4% |
| claude-sonnet-4.6 | 14,911,900 |   5.0% |
| gemini-3-flash-agent | 9,215,322 |   3.1% |
| <synthetic> | 0 |   0.0% |

