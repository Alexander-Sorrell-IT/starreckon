# Claude Code token usage — MacBook Air M1

_Generated 2026-08-06T03:30:07-05:00_

## Total for this computer: 29,170,327,621 tokens (29.17B)

Across 4 account(s), 2,180 sessions, 134,345 assistant turns.

Counted from `message.usage` in the local session JSONL — the API's own
accounting, deduplicated by message uuid.

## Accounts

| Account | Sessions | Turns | Input | Cache write | Cache read | Output | Total |
|---|---:|---:|---:|---:|---:|---:|---:|
| second@example.com | 29 | 107,067 | 9.91M | 645.97M | 16.84B | 63.95M | **17.56B** |
| third@example.com | 21 | 24,773 | 1.22M | 383.14M | 10.61B | 33.15M | **11.03B** |
| owner@example.com | 4 | 2,331 | 75.20K | 13.24M | 556.04M | 2.40M | **571.75M** |
| third@example.com | 2,126 | 174 | 58.73K | 957.96K | 8.30M | 107.36K | **9.43M** |

## By provider

Claude Code can be pointed at a non-Anthropic backend; those transcripts are
byte-identical to Claude ones. Totals are split on the model id so an
Anthropic figure is never inflated by tokens Anthropic did not serve.

| Provider | Tokens | Share |
|---|---:|---:|
| anthropic | 29,170,327,621 | 100.0% |
| synthetic | 0 | 0.0% |

**Anthropic-only total: 29,170,327,621 tokens (29.17B)**


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
| Grok CLI | `/Users/testuser/.grok` | 495 | **no — not countable** |

## Authentication and organization

An API-key profile bills to the organization the key belongs to, which is
not recorded on disk — rerun with `--probe-api` to resolve it. A profile is
linked to an account only when their organization UUIDs match.

| Account | Auth | Organization | Org UUID | Linked to |
|---|---|---|---|---|
| second@example.com | oauth | second@example.com's Organization | `6bfc754e-a205-41c3-9dac-80e593f494e0` | — |
| third@example.com | oauth | third@example.com's Organization | `ba511861-53b4-4599-8019-93db6389d991` | — |
| owner@example.com | oauth | owner@example.com's Organization | `66565064-263e-4d54-b06f-15cae4b2febc` | — |
| third@example.com | oauth | third@example.com's Organization | `ba511861-53b4-4599-8019-93db6389d991` | — |

### second@example.com

**17,557,582,699 tokens** (17.56B) — `/Users/testuser/.claude-main`

userID `f2c6d8a64f23fdea16f037b8edd329f7f3f592a0f7cadfcdb2dbf51d256502f7`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 29 | 11.45B | 65% |
| subagent | 20 | 34.22M | 0% |
| workflow | 2,656 | 6.08B | 35% |

| Model | Total |
|---|---:|
| claude-opus-5 | 9.87B |
| claude-opus-4-8 | 6.04B |
| claude-fable-5 | 1.64B |
| claude-haiku-4-5-20251001 | 1.73M |
| <synthetic> | 0 |

Active 2026-07-05 → 2026-08-06 (29 days). Busiest day 2026-08-02 at 2.44B.

| Project | Total |
|---|---:|
| `-Users-testuser` | 13.85B |
| `-Users-testuser-Desktop-vulcan-delta-tests` | 3.71B |

### third@example.com

**11,031,562,217 tokens** (11.03B) — `/Users/testuser/.claude`

userID `c6ce9918ed51217d1701e1b6217b35699f346b95e2d17fec3b261d9ea2bea739`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 21 | 10.87B | 99% |
| subagent | 87 | 161.55M | 1% |

| Model | Total |
|---|---:|
| claude-opus-4-8 | 7.60B |
| claude-opus-5 | 3.43B |
| claude-sonnet-5 | 1.58M |
| claude-opus-4-7 | 380.66K |
| <synthetic> | 0 |

Active 2026-05-26 → 2026-08-06 (27 days). Busiest day 2026-07-18 at 1.31B.

| Project | Total |
|---|---:|
| `-Users-testuser` | 10.94B |
| `-Users-testuser-Documents-Hackthon` | 96.43M |
| `-Users-testuser-Documents-tools` | 83.86K |

### owner@example.com

**571,753,755 tokens** (571.75M) — `/Users/testuser/.claude-it`

userID `a842a0db1ce2f3e19742aa78893f10cf921a9d7e15a1412fec7c7cc4cf09525a`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 4 | 571.15M | 100% |
| subagent | 1 | 608.08K | 0% |

| Model | Total |
|---|---:|
| claude-opus-4-8 | 440.31M |
| claude-sonnet-4-6 | 131.44M |
| <synthetic> | 0 |

Active 2026-06-18 → 2026-08-06 (6 days). Busiest day 2026-06-20 at 297.83M.

| Project | Total |
|---|---:|
| `-Users-testuser-Desktop-Bug` | 571.75M |
| `-Users-testuser` | 0 |

### third@example.com

**9,428,950 tokens** (9.43M) — `/Users/testuser/Desktop/standout_sandbox/.claude`

userID `c6ce9918ed51217d1701e1b6217b35699f346b95e2d17fec3b261d9ea2bea739`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 2,126 | 9.43M | 100% |

| Model | Total |
|---|---:|
| claude-opus-4-8 | 9.43M |

Active 2026-07-02 → 2026-07-05 (3 days). Busiest day 2026-07-02 at 7.58M.

| Project | Total |
|---|---:|
| `work` | 9.43M |
