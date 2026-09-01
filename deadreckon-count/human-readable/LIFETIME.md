# Lifetime

**90,958,286,161 tokens** · 630 sessions · 185,017 turns · 50d 7h 27m

_Everything ever recorded on any computer in this fleet, across every CLI. This counts what still exists plus what was captured before it expired._

_2025-07-01 .. 2026-09-01_

## By CLI

| | tokens | share | |
|---|---:|---:|---|
| claude | 84,949,206,933 |  93.4% | ★ |
| gemini | 2,463,723,232 |   2.7% | † |
| codex | 1,635,058,955 |   1.8% | † |
| copilot | 793,528,750 |   0.9% | † |
| bob | 530,867,892 |   0.6% | † |
| clawspring | 258,502,806 |   0.3% | † |
| antigravity | 218,712,737 |   0.2% | † |
| grok | 100,222,322 |   0.1% | † |
| kilocode | 7,074,501 |   0.0% | † |
| lmstudio | 172,933 |   0.0% | † |

★ true lifetime — vendor counter on disk survives transcript deletion  † from daemon start — no vendor counter exists; the ledger is the only record

## By computer

| | tokens | share |
|---|---:|---:|
| MacBook Air M1 | 52,414,424,292 |  57.6% |
| HP Laptop Linux | 38,543,861,869 |  42.4% |

## By model

| | tokens | share |
|---|---:|---:|
| claude-opus-5 | 18,392,974,111 |  20.2% |
| claude-opus-4-8 | 5,591,772,105 |   6.1% |
| claude-opus-4-7 | 2,442,708,241 |   2.7% |
| gemini-3-flash-preview | 2,135,901,976 |   2.3% |
| claude-fable-5 | 2,032,809,158 |   2.2% |
| gpt-5.6-sol | 1,451,179,368 |   1.6% |
| deepseek-v4-pro | 534,671,153 |   0.6% |
| claude-sonnet-4-6 | 414,274,920 |   0.5% |
| unknown | 323,814,467 |   0.4% |
| claude-sonnet-4.6 | 279,118,768 |   0.3% |
| bob | 229,043,592 |   0.3% |
| gpt-5.5 | 225,314,053 |   0.2% |
| gemini-3-pro-preview | 201,035,389 |   0.2% |
| gpt-5.6-luna | 180,826,644 |   0.2% |
| claude-sonnet-5 | 177,021,920 |   0.2% |

## Undated sessions

**5,347,972,110 tokens** across **111 session(s)** have no start timestamp and cannot be placed in any month. They are real work — counted in the every-CLI total — but their transcripts carried no `timestamp` field, so the month is unknown. They are included in the headline figure above.

| CLI | tokens |
|---|---:|
| claude | 5,346,757,010 |
| copilot-chat | 1,214,160 |
| clawspring | 830 |
| lmstudio | 110 |

## Each computer

### MacBook Air M1

**21,669,531,684 tokens** · 283 sessions · 108,823 turns · 29d 10h 26m

_2025-07-03 .. 2026-08-20_

| CLI | tokens | share |
|---|---:|---:|
| claude | 18,034,864,999 |  83.2% |
| codex | 1,633,604,881 |   7.5% |
| gemini | 995,360,683 |   4.6% |
| copilot | 497,696,783 |   2.3% |
| bob | 272,617,335 |   1.3% |
| antigravity | 135,111,522 |   0.6% |
| grok | 100,222,322 |   0.5% |
| lmstudio | 53,159 |   0.0% |

### HP Laptop Linux

**13,895,407,082 tokens** · 347 sessions · 76,194 turns · 20d 21h 1m

_2025-07-01 .. 2026-09-01_

| CLI | tokens | share |
|---|---:|---:|
| claude | 11,551,416,604 |  83.1% |
| gemini | 1,468,362,549 |  10.6% |
| copilot | 295,831,967 |   2.1% |
| clawspring | 258,502,806 |   1.9% |
| bob | 229,043,592 |   1.6% |
| antigravity | 83,601,215 |   0.6% |
| kilocode | 7,074,501 |   0.1% |
| codex | 1,454,074 |   0.0% |

## What the ledger adds

**35,564,938,766** of the headline is on disk now. **37,081,013** is not on disk: it is work whose transcripts have been deleted, held only by the append-only `token_ledger.jsonl` in each machine folder. The session and turn counts above cover the scanned part only — a vanished session is one row of arithmetic, not a session anyone can still open — and no month below includes any of it, because a vanished session's last observation may carry no date.

| computer | scanned | ledger | beyond the scan | ledger file |
|---|---:|---:|---:|---|
| MacBook Air M1 | 22,843,956,661 | 22,881,037,674 | +37,081,013 | yes |
| HP Laptop Linux | 18,068,954,215 | 13,367,051,701 | +0 | yes |

## What stats-cache adds

**55,356,266,382** tokens are added by the stats-cache floor. Claude Code writes `stats-cache.json` into each profile and accumulates every session there, including ones whose transcripts have since been deleted by `cleanupPeriodDays`. The counter survives deletion; the transcript does not. **55,355,051,282** of that is Claude Code; 1,215,100 is attributed to other tools. The floor is applied per account: `max(counter_total + transcripts_after_counter_date, scan_total)`, so it never contradicts work already on disk.

## What the tokens were

| | tokens | share |
|---|---:|---:|
| re-read from cache | 28,658,603,961 |  96.9% |
| written to cache | 761,017,199 |   2.6% |
| sent fresh | 28,606,840 |   0.1% |
| **generated** | 135,383,349 |   0.5% |

Most of any total is the conversation being re-sent, not new writing. Read that share before quoting the headline.

