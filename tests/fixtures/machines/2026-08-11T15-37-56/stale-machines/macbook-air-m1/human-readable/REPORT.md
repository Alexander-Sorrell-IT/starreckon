# Claude Code token usage — MacBook Air M1

_Generated 2026-08-09T02:34:15-05:00_

## Total for this computer: 13,955,323,225 tokens (13.96B)

Across 10 account(s), 8,730 sessions, 60,788 assistant turns.

Counted from `message.usage` in the local session JSONL — the API's own
accounting, deduplicated by message uuid.

## Accounts

| Account | Sessions | Turns | Input | Cache write | Cache read | Output | Total |
|---|---:|---:|---:|---:|---:|---:|---:|
| second@example.com | 31 | 46,646 | 3.71M | 253.18M | 8.13B | 47.91M | **8.43B** |
| third@example.com | 24 | 12,911 | 433.65K | 159.14M | 5.09B | 15.80M | **5.27B** |
| owner@example.com | 4 | 1,124 | 28.53K | 5.27M | 237.71M | 935.95K | **243.95M** |
| unknown (Documents) | 2,180 | 31 | 62 | 106.70K | 5.94M | 20.18K | **6.06M** |
| unknown (Desktop_standout_sandbox_.claude) | 2,126 | 75 | 25.84K | 377.19K | 3.51M | 43.78K | **3.95M** |
| unknown (claude-main) | 31 | 1 | 2 | 376 | 112.36K | 1.01K | **113.75K** |
| unknown (claude) | 24 | 0 | 0 | 0 | 0 | 0 | **0** |
| unknown (claude-it) | 4 | 0 | 0 | 0 | 0 | 0 | **0** |
| third@example.com | 2,126 | 0 | 0 | 0 | 0 | 0 | **0** |
| unknown (Documents) | 2,180 | 0 | 0 | 0 | 0 | 0 | **0** |

## By provider

Claude Code can be pointed at a non-Anthropic backend; those transcripts are
byte-identical to Claude ones. Totals are split on the model id so an
Anthropic figure is never inflated by tokens Anthropic did not serve.

| Provider | Tokens | Share |
|---|---:|---:|
| anthropic | 13,955,323,225 | 100.0% |

**Anthropic-only total: 13,955,323,225 tokens (13.96B)**


### Other AI tools on this machine

Listed so a provider missing from the table above is unambiguous: a tool
that records no usage cannot be counted from disk, which is different
from a tool that was never used.

| Tool | Directory | Files | Token usage on disk |
|---|---|---:|---|
| Gemini CLI | `/Users/testuser/.gemini` | 238 | **no — not countable** |
| GitHub Copilot CLI | `/Users/testuser/.copilot` | 215 | **no — not countable** |
| Antigravity CLI | `/Users/testuser/.antigravitycli` | 1 | **no — not countable** |
| OpenAI Codex CLI | `/Users/testuser/.codex` | 983 | yes — countable |
| Grok CLI | `/Users/testuser/.grok` | 572 | **no — not countable** |

## Authentication and organization

An API-key profile bills to the organization the key belongs to, which is
not recorded on disk — rerun with `--probe-api` to resolve it. A profile is
linked to an account only when their organization UUIDs match.

| Account | Auth | Organization | Org UUID | Linked to |
|---|---|---|---|---|
| second@example.com | oauth | second@example.com's Organization | `6bfc754e-a205-41c3-9dac-80e593f494e0` | — |
| third@example.com | oauth | third@example.com's Organization | `ba511861-53b4-4599-8019-93db6389d991` | — |
| owner@example.com | oauth | owner@example.com's Organization | `66565064-263e-4d54-b06f-15cae4b2febc` | — |
| unknown (Documents) | unknown | — | `—` | — |
| unknown (Desktop_standout_sandbox_.claude) | unknown | — | `—` | — |
| unknown (claude-main) | unknown | — | `—` | — |
| unknown (claude) | unknown | — | `—` | — |
| unknown (claude-it) | unknown | — | `—` | — |
| third@example.com | oauth | third@example.com's Organization | `ba511861-53b4-4599-8019-93db6389d991` | — |
| unknown (Documents) | unknown | — | `—` | — |

### second@example.com

**8,431,493,209 tokens** (8.43B) — `/Users/testuser/.claude-main`

userID `f2c6d8a64f23fdea16f037b8edd329f7f3f592a0f7cadfcdb2dbf51d256502f7`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 31 | 5.56B | 66% |
| subagent | 20 | 13.57M | 0% |
| workflow | 2,786 | 2.86B | 34% |

| Model | Total |
|---|---:|
| claude-opus-5 | 5.26B |
| claude-opus-4-8 | 2.36B |
| claude-fable-5 | 808.08M |
| claude-haiku-4-5-20251001 | 480.73K |

Active 2026-07-05 → 2026-08-09 (31 days). Busiest day 2026-08-02 at 1.15B.

| Project | Total |
|---|---:|
| `-Users-testuser` | 6.79B |
| `-Users-testuser-Desktop-vulcan-delta-tests` | 1.64B |

### third@example.com

**5,269,752,187 tokens** (5.27B) — `/Users/testuser/.claude`

userID `c6ce9918ed51217d1701e1b6217b35699f346b95e2d17fec3b261d9ea2bea739`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 24 | 5.05B | 96% |
| subagent | 95 | 73.85M | 1% |
| workflow | 60 | 144.05M | 3% |

| Model | Total |
|---|---:|
| claude-opus-4-8 | 2.89B |
| claude-opus-5 | 2.37B |
| claude-sonnet-5 | 831.51K |
| claude-opus-4-7 | 153.12K |

Active 2026-05-26 → 2026-08-08 (29 days). Busiest day 2026-08-07 at 509.78M.

| Project | Total |
|---|---:|
| `-Users-testuser` | 5.23B |
| `-Users-testuser-Documents-Hackthon` | 38.81M |
| `-Users-testuser-Documents-tools` | 41.93K |

### owner@example.com

**243,949,169 tokens** (243.95M) — `/Users/testuser/.claude-it`

userID `a842a0db1ce2f3e19742aa78893f10cf921a9d7e15a1412fec7c7cc4cf09525a`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 4 | 243.62M | 100% |
| subagent | 1 | 325.57K | 0% |

| Model | Total |
|---|---:|
| claude-opus-4-8 | 171.24M |
| claude-sonnet-4-6 | 72.71M |

Active 2026-06-18 → 2026-06-20 (3 days). Busiest day 2026-06-20 at 113.46M.

| Project | Total |
|---|---:|
| `-Users-testuser-Desktop-Bug` | 243.95M |

### unknown (Documents)

**6,062,632 tokens** (6.06M) — `/Users/testuser/.ai-logs-archive/claude/Documents`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 2,180 | 6.06M | 100% |

| Model | Total |
|---|---:|
| claude-opus-5 | 3.71M |
| claude-opus-4-8 | 1.95M |
| claude-fable-5 | 409.00K |

Active 2026-07-05 → 2026-08-05 (18 days). Busiest day 2026-07-30 at 1.09M.

| Project | Total |
|---|---:|
| `token-usage` | 6.06M |

### unknown (Desktop_standout_sandbox_.claude)

**3,952,282 tokens** (3.95M) — `/Users/testuser/.ai-logs-archive/claude/Desktop_standout_sandbox_.claude`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 2,126 | 3.95M | 100% |

| Model | Total |
|---|---:|
| claude-opus-4-8 | 3.59M |
| claude-fable-5 | 366.86K |

Active 2026-07-02 → 2026-07-06 (4 days). Busiest day 2026-07-02 at 2.91M.

| Project | Total |
|---|---:|
| `work` | 3.95M |

### unknown (claude-main)

**113,746 tokens** (113.75K) — `/Users/testuser/.ai-logs-archive/claude/claude-main`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 31 | 113.75K | 100% |

| Model | Total |
|---|---:|
| claude-opus-5 | 113.75K |

Active 2026-08-09 → 2026-08-09 (1 days). Busiest day 2026-08-09 at 113.75K.

| Project | Total |
|---|---:|
| `-Users-testuser` | 113.75K |

### unknown (claude)

**0 tokens** (0) — `/Users/testuser/.ai-logs-archive/claude/claude`

### unknown (claude-it)

**0 tokens** (0) — `/Users/testuser/.ai-logs-archive/claude/claude-it`

### third@example.com

**0 tokens** (0) — `/Users/testuser/Desktop/standout_sandbox/.claude`

userID `c6ce9918ed51217d1701e1b6217b35699f346b95e2d17fec3b261d9ea2bea739`

### unknown (Documents)

**0 tokens** (0) — `/Users/testuser/Documents`
