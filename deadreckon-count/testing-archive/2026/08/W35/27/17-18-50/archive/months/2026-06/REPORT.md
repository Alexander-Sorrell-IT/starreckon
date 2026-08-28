# 2026-06

**867,736,786 tokens** · 11 sessions · 3,842 turns · 3d 6h 9m

_This month is over. Frozen from the largest set of records anyone has held: it is rewritten only when a rescan finds MORE than the frozen copy, and never when it finds fewer — the transcripts behind it are deleted after `cleanupPeriodDays`, so a smaller recount is loss, not a correction._

_2026-06-01 .. 2026-06-28_

## By CLI

| | tokens | share | |
|---|---:|---:|---|
| claude | 815,702,924 |  94.0% | ★ |
| copilot | 42,818,540 |   4.9% | † |
| antigravity | 9,215,322 |   1.1% | † |

★ true lifetime — vendor counter on disk survives transcript deletion  † from daemon start — no vendor counter exists; the ledger is the only record

> **† figures depend on the retention daemon.** The ledger only grows when the daemon records, while transcripts keep expiring regardless. If it stops, these totals do not freeze — they decay, and nothing else will say so. `python3 run.py status` reports whether it is running on the machine you are on.

## By computer

| | tokens | share |
|---|---:|---:|
| MacBookAir | 571,753,755 |  65.9% |
| MacBook Air M1 (Darwin ARM64) | 295,983,031 |  34.1% |

## By model

| | tokens | share |
|---|---:|---:|
| claude-sonnet-4-6 | 815,094,848 |  93.9% |
| claude-opus-4.8 | 27,906,640 |   3.2% |
| claude-sonnet-4.6 | 14,911,900 |   1.7% |
| gemini-3-flash-agent | 9,215,322 |   1.1% |
| claude-opus-4-8 | 608,076 |   0.1% |
| proj-475024d6 | 0 |   0.0% |
| <synthetic> | 0 |   0.0% |

