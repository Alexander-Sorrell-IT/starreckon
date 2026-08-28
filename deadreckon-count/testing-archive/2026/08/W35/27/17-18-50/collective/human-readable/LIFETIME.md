# Lifetime

**109,863,590,176 tokens** · 3,572 sessions · 300,190 turns · 162d 1h 47m

_Everything ever recorded on any computer in this fleet, across every CLI. This counts what still exists plus what was captured before it expired._

_2025-07-03 .. 2026-08-26_

## By CLI

| | tokens | share | |
|---|---:|---:|---|
| claude | 103,420,756,272 |  94.1% | ★ |
| gemini | 1,990,721,366 |   1.8% | † |
| codex | 1,633,604,881 |   1.5% | † |
| antigravity | 1,197,949,353 |   1.1% | † |
| copilot | 1,144,892,178 |   1.0% | † |
| bob | 275,168,323 |   0.3% | † |
| grok | 200,444,644 |   0.2% | † |
| lmstudio | 53,159 |   0.0% | † |

★ true lifetime — vendor counter on disk survives transcript deletion  † from daemon start — no vendor counter exists; the ledger is the only record

> **† figures depend on the retention daemon.** The ledger only grows when the daemon records, while transcripts keep expiring regardless. If it stops, these totals do not freeze — they decay, and nothing else will say so. `python3 run.py status` reports whether it is running on the machine you are on.

## By computer

| | tokens | share |
|---|---:|---:|
| MacBookAir | 55,141,443,346 |  50.2% |
| MacBook Air M1 (Darwin ARM64) | 54,722,146,830 |  49.8% |

## By model

| | tokens | share |
|---|---:|---:|
| claude-opus-5 | 38,611,588,236 |  35.1% |
| claude-opus-4-8 | 19,390,023,278 |  17.6% |
| claude-fable-5 | 1,703,702,926 |   1.6% |
| gpt-5.6-sol | 1,451,179,368 |   1.3% |
| gemini-3-flash-preview | 932,704,860 |   0.8% |
| gemini-3.7-flash-safety-le | 930,363,796 |   0.8% |
| claude-sonnet-4-6 | 815,094,848 |   0.7% |
| claude-sonnet-4.6 | 279,118,768 |   0.3% |
| gpt-5.6-luna | 180,826,644 |   0.2% |
| grok-4.5-build | 100,222,322 |   0.1% |
| claude-opus-4.7 | 94,058,304 |   0.1% |
| gpt-5.6-terra | 74,710,059 |   0.1% |
| gemini-3.7-flash-low | 63,791,884 |   0.1% |
| gemini-3.1-pro-preview | 62,655,823 |   0.1% |
| unknown | 59,372,409 |   0.1% |

## Undated sessions

**2,905,488,487 tokens** across **78 session(s)** have no start timestamp and cannot be placed in any month. They are real work — counted in the every-CLI total — but their transcripts carried no `timestamp` field, so the month is unknown. They are included in the headline token figure above; the session, turn and duration counts there cover dated sessions only.

| CLI | tokens |
|---|---:|
| claude | 1,174,424,977 |
| gemini | 995,360,683 |
| copilot | 572,446,089 |
| grok | 100,222,322 |
| antigravity | 60,483,428 |
| bob | 2,550,988 |

## Each computer

### MacBookAir

**42,036,497,160 tokens** · 3,274 sessions · 181,996 turns · 129d 22h 17m

_2026-05-26 .. 2026-08-26_

| CLI | tokens | share |
|---|---:|---:|
| claude | 42,036,497,160 | 100.0% |

### MacBook Air M1 (Darwin ARM64)

**23,139,167,869 tokens** · 298 sessions · 118,194 turns · 32d 3h 29m

_2025-07-03 .. 2026-08-26_

| CLI | tokens | share |
|---|---:|---:|
| claude | 18,487,763,737 |  79.9% |
| codex | 1,633,604,881 |   7.1% |
| antigravity | 1,077,099,663 |   4.7% |
| gemini | 995,360,683 |   4.3% |
| copilot | 572,446,089 |   2.5% |
| bob | 272,617,335 |   1.2% |
| grok | 100,222,322 |   0.4% |
| lmstudio | 53,159 |   0.0% |

## What the ledger adds

**65,175,665,029** of the headline is on disk now. **60,366,262** is not on disk: it is work whose transcripts have been deleted, held only by the append-only `token_ledger.jsonl` in each machine folder. The session and turn counts above cover the scanned part only — a vanished session is one row of arithmetic, not a session anyone can still open — and no month below includes any of it, because a vanished session's last observation may carry no date.

| computer | scanned | ledger | beyond the scan | ledger file |
|---|---:|---:|---:|---|
| MacBook Air M1 (Darwin ARM64) | 24,313,592,846 | 24,373,959,108 | +60,366,262 | yes |
| MacBookAir | 43,767,560,670 | 0 | +0 | **none — never recorded, which is not the same as a ledger that says zero** |

## What stats-cache adds

**41,722,070,398** tokens are added by the stats-cache floor. Claude Code writes `stats-cache.json` into each profile and accumulates every session there, including ones whose transcripts have since been deleted by `cleanupPeriodDays`. The counter survives deletion; the transcript does not. **41,722,070,398** of that is Claude Code; 0 is attributed to other tools. The floor is applied per account: `max(counter_total + transcripts_after_counter_date, scan_total)`, so it never contradicts work already on disk.

## What the tokens were

| | tokens | share |
|---|---:|---:|
| re-read from cache | 58,462,227,153 |  96.6% |
| written to cache | 1,836,236,581 |   3.0% |
| sent fresh | 16,177,345 |   0.0% |
| **generated** | 209,619,818 |   0.3% |

Most of any total is the conversation being re-sent, not new writing. Read that share before quoting the headline.

