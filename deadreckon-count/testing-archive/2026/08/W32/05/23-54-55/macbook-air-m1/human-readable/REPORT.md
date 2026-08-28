# Claude Code token usage — MacBook Air M1

_Generated 2026-08-04T20:44:23-05:00_

## Total for this computer: 28,492,335,565 tokens (28.49B)

Across 3 account(s), 53 sessions, 132,114 assistant turns.

Counted from `message.usage` in the local session JSONL — the API's own
accounting, deduplicated by message uuid.

## Accounts

| Account | Sessions | Turns | Input | Cache write | Cache read | Output | Total |
|---|---:|---:|---:|---:|---:|---:|---:|
| broodierchip@gmail.com | 29 | 106,204 | 9.89M | 640.14M | 16.77B | 63.28M | **17.48B** |
| codehunterextreme@gmail.com | 21 | 23,580 | 1.21M | 335.18M | 10.07B | 32.02M | **10.44B** |
| alexander.sorrell.it@gmail.com | 3 | 2,330 | 75.20K | 13.24M | 556.04M | 2.40M | **571.75M** |

## By provider

Claude Code can be pointed at a non-Anthropic backend; those transcripts are
byte-identical to Claude ones. Totals are split on the model id so an
Anthropic figure is never inflated by tokens Anthropic did not serve.

| Provider | Tokens | Share |
|---|---:|---:|
| anthropic | 28,492,335,565 | 100.0% |
| synthetic | 0 | 0.0% |

**Anthropic-only total: 28,492,335,565 tokens (28.49B)**


### Other AI tools on this machine

Listed so a provider missing from the table above is unambiguous: a tool
that records no usage cannot be counted from disk, which is different
from a tool that was never used.

| Tool | Directory | Files | Token usage on disk |
|---|---|---:|---|
| Gemini CLI | `/Users/broodierchip-m1air/.gemini` | 238 | **no — not countable** |
| GitHub Copilot CLI | `/Users/broodierchip-m1air/.copilot` | 215 | **no — not countable** |
| Antigravity CLI | `/Users/broodierchip-m1air/.antigravitycli` | 1 | **no — not countable** |
| OpenAI Codex CLI | `/Users/broodierchip-m1air/.codex` | 983 | yes — countable |
| Grok CLI | `/Users/broodierchip-m1air/.grok` | 410 | **no — not countable** |

## Authentication and organization

An API-key profile bills to the organization the key belongs to, which is
not recorded on disk — rerun with `--probe-api` to resolve it. A profile is
linked to an account only when their organization UUIDs match.

| Account | Auth | Organization | Org UUID | Linked to |
|---|---|---|---|---|
| broodierchip@gmail.com | oauth | broodierchip@gmail.com's Organization | `6bfc754e-a205-41c3-9dac-80e593f494e0` | — |
| codehunterextreme@gmail.com | oauth | codehunterextreme@gmail.com's Organization | `ba511861-53b4-4599-8019-93db6389d991` | — |
| alexander.sorrell.it@gmail.com | oauth | alexander.sorrell.it@gmail.com's Organization | `66565064-263e-4d54-b06f-15cae4b2febc` | — |

### broodierchip@gmail.com

**17,484,791,342 tokens** (17.48B) — `/Users/broodierchip-m1air/.claude-main`

userID `f2c6d8a64f23fdea16f037b8edd329f7f3f592a0f7cadfcdb2dbf51d256502f7`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 29 | 11.41B | 65% |
| subagent | 20 | 34.22M | 0% |
| workflow | 2,633 | 6.04B | 35% |

| Model | Total |
|---|---:|
| claude-opus-5 | 9.86B |
| claude-opus-4-8 | 6.04B |
| claude-fable-5 | 1.58B |
| claude-haiku-4-5-20251001 | 1.73M |
| <synthetic> | 0 |

Active 2026-07-05 → 2026-08-05 (28 days). Busiest day 2026-08-02 at 2.44B.

| Project | Total |
|---|---:|
| `-Users-broodierchip-m1air` | 13.77B |
| `-Users-broodierchip-m1air-Desktop-vulcan-delta-tests` | 3.71B |

### codehunterextreme@gmail.com

**10,435,790,468 tokens** (10.44B) — `/Users/broodierchip-m1air/.claude`

userID `c6ce9918ed51217d1701e1b6217b35699f346b95e2d17fec3b261d9ea2bea739`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 21 | 10.27B | 98% |
| subagent | 87 | 161.55M | 2% |

| Model | Total |
|---|---:|
| claude-opus-4-8 | 7.60B |
| claude-opus-5 | 2.84B |
| claude-sonnet-5 | 1.58M |
| claude-opus-4-7 | 380.66K |
| <synthetic> | 0 |

Active 2026-05-26 → 2026-08-05 (26 days). Busiest day 2026-07-18 at 1.31B.

| Project | Total |
|---|---:|
| `-Users-broodierchip-m1air` | 10.34B |
| `-Users-broodierchip-m1air-Documents-Hackthon` | 96.43M |
| `-Users-broodierchip-m1air-Documents-tools` | 83.86K |

### alexander.sorrell.it@gmail.com

**571,753,755 tokens** (571.75M) — `/Users/broodierchip-m1air/.claude-it`

userID `a842a0db1ce2f3e19742aa78893f10cf921a9d7e15a1412fec7c7cc4cf09525a`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 3 | 571.15M | 100% |
| subagent | 1 | 608.08K | 0% |

| Model | Total |
|---|---:|
| claude-opus-4-8 | 440.31M |
| claude-sonnet-4-6 | 131.44M |
| <synthetic> | 0 |

Active 2026-06-18 → 2026-08-04 (5 days). Busiest day 2026-06-20 at 297.83M.

| Project | Total |
|---|---:|
| `-Users-broodierchip-m1air-Desktop-Bug` | 571.75M |
| `-Users-broodierchip-m1air` | 0 |
