# Dell Latitude 7480 Linux — lifetime

**32,030,529,227 tokens** · 16,644 sessions · 42,124 turns · 9d 1h 47m

_Everything this computer has ever recorded, across every CLI._

_2025-12-30 .. 2026-08-25_

## By CLI

| | tokens | share | |
|---|---:|---:|---|
| claude | 29,868,745,106 |  93.3% | ★ |
| copilot | 1,062,300,519 |   3.3% | † |
| codex | 677,851,186 |   2.1% | † |
| gemini | 320,741,667 |   1.0% | † |
| antigravity | 63,895,537 |   0.2% | † |
| bob | 36,995,212 |   0.1% | † |

★ true lifetime — vendor counter on disk survives transcript deletion  † from daemon start — no vendor counter exists; the ledger is the only record

> **† figures depend on the retention daemon.** The ledger only grows when the daemon records, while transcripts keep expiring regardless. If it stops, these totals do not freeze — they decay, and nothing else will say so. `python3 run.py status` reports whether it is running on the machine you are on.

## By computer

| | tokens | share |
|---|---:|---:|
| Dell Latitude 7480 Linux | 32,030,529,227 | 100.0% |

## By model

| | tokens | share |
|---|---:|---:|
| claude-opus-4-8 | 1,261,579,052 |   3.9% |
| unknown | 1,057,847,408 |   3.3% |
| claude-opus-5 | 856,243,027 |   2.7% |
| gpt-5.5 | 379,804,407 |   1.2% |
| gpt-5.4-mini | 289,062,995 |   0.9% |
| gemini-3-flash-preview | 256,769,016 |   0.8% |
| claude-fable-5 | 86,273,259 |   0.3% |
| gemini-3-pro-preview | 63,953,140 |   0.2% |
| gemini-3.5-flash-low | 39,462,940 |   0.1% |
| claude-opus-4-7 | 16,429,203 |   0.1% |
| gemini_model | 11,561,079 |   0.0% |
| gemini-3.6-flash-high | 6,928,018 |   0.0% |
| gpt-5.3-codex | 4,981,236 |   0.0% |
| claude-haiku-4.5 | 4,453,111 |   0.0% |
| codex-auto-review | 4,002,548 |   0.0% |

## Undated sessions

**2,324,208,273 tokens** across **48 session(s)** have no start timestamp and cannot be placed in any month. They are real work — counted in the every-CLI total — but their transcripts carried no `timestamp` field, so the month is unknown. They are included in the headline token figure above; the session, turn and duration counts there cover dated sessions only.

| CLI | tokens |
|---|---:|
| claude | 2,324,208,273 |

## What the ledger adds

**4,388,500,055** of the headline is on disk now. **17,152,754,320** is not on disk: it is work whose transcripts have been deleted, held only by the append-only `token_ledger.jsonl` in each machine folder. The session and turn counts above cover the scanned part only — a vanished session is one row of arithmetic, not a session anyone can still open — and no month below includes any of it, because a vanished session's last observation may carry no date.

| computer | scanned | ledger | beyond the scan | ledger file |
|---|---:|---:|---:|---|
| Dell Latitude 7480 Linux | 6,712,708,328 | 23,864,801,604 | +17,152,754,320 | yes |

## What stats-cache adds

**8,165,066,579** tokens are added by the stats-cache floor. Claude Code writes `stats-cache.json` into each profile and accumulates every session there, including ones whose transcripts have since been deleted by `cleanupPeriodDays`. The counter survives deletion; the transcript does not. **8,165,066,579** of that is Claude Code; 0 is attributed to other tools. The floor is applied per account: `max(counter_total + transcripts_after_counter_date, scan_total)`, so it never contradicts work already on disk.

## What the tokens were

| | tokens | share |
|---|---:|---:|
| re-read from cache | 1,872,808,572 |  84.2% |
| written to cache | 177,309,501 |   8.0% |
| sent fresh | 160,090,468 |   7.2% |
| **generated** | 15,020,156 |   0.7% |

Most of any total is the conversation being re-sent, not new writing. Read that share before quoting the headline.

