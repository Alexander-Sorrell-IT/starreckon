# Claude Code token usage — Dell Latitude 7480 Linux

_Generated 2026-08-06T06:17:15-05:00_

## Total for this computer: 5,324,610,556 tokens (5.32B)

Across 6 account(s), 16,549 sessions, 61,252 assistant turns.

Counted from `message.usage` in the local session JSONL — the API's own
accounting, deduplicated by message uuid.

## Accounts

| Account | Sessions | Turns | Input | Cache write | Cache read | Output | Total |
|---|---:|---:|---:|---:|---:|---:|---:|
| alexander.sorrell.it@gmail.com | 73 | 9,203 | 482.90K | 96.90M | 2.13B | 12.83M | **2.24B** |
| broodierchip@gmail.com | 31 | 19,237 | 1.74M | 143.88M | 1.39B | 1.43M | **1.54B** |
| broodierchip@gmail.com | 16,441 | 32,475 | 321.50M | 252.69M | 919.53M | 17.63M | **1.51B** |
| codehunterextreme@gmail.com | 2 | 223 | 11.07K | 3.40M | 23.16M | 206.90K | **26.78M** |
| user:2d4777822844 | 1 | 111 | 457 | 1.21M | 5.94M | 135.01K | **7.28M** |
| user:283b8e5b8e48 | 1 | 3 | 0 | 0 | 0 | 0 | **0** |

## By provider

Claude Code can be pointed at a non-Anthropic backend; those transcripts are
byte-identical to Claude ones. Totals are split on the model id so an
Anthropic figure is never inflated by tokens Anthropic did not serve.

| Provider | Tokens | Share |
|---|---:|---:|
| anthropic | 5,324,610,556 | 100.0% |
| synthetic | 0 | 0.0% |

**Anthropic-only total: 5,324,610,556 tokens (5.32B)**


### Other AI tools on this machine

Listed so a provider missing from the table above is unambiguous: a tool
that records no usage cannot be counted from disk, which is different
from a tool that was never used.

| Tool | Directory | Files | Token usage on disk |
|---|---|---:|---|
| Gemini CLI | `/home/phantom-orchestrator/.gemini` | 103 | **no — not countable** |
| GitHub Copilot CLI | `/home/phantom-orchestrator/.copilot` | 205 | **no — not countable** |
| Antigravity CLI | `/home/phantom-orchestrator/.antigravitycli` | 1 | **no — not countable** |
| OpenAI Codex CLI | `/home/phantom-orchestrator/.codex` | 282 | yes — countable |

## Authentication and organization

An API-key profile bills to the organization the key belongs to, which is
not recorded on disk — rerun with `--probe-api` to resolve it. A profile is
linked to an account only when their organization UUIDs match.

| Account | Auth | Organization | Org UUID | Linked to |
|---|---|---|---|---|
| alexander.sorrell.it@gmail.com | oauth | alexander.sorrell.it@gmail.com's Organization | `66565064-263e-4d54-b06f-15cae4b2febc` | — |
| broodierchip@gmail.com | oauth | broodierchip@gmail.com's Organization | `6bfc754e-a205-41c3-9dac-80e593f494e0` | — |
| broodierchip@gmail.com | oauth | broodierchip@gmail.com's Organization | `6bfc754e-a205-41c3-9dac-80e593f494e0` | — |
| codehunterextreme@gmail.com | oauth | codehunterextreme@gmail.com's Organization | `ba511861-53b4-4599-8019-93db6389d991` | — |
| user:2d4777822844 | api_key | — | `—` | — |
| user:283b8e5b8e48 | api_key | — | `—` | — |

### alexander.sorrell.it@gmail.com

**2,239,476,898 tokens** (2.24B) — `/home/phantom-orchestrator/.claude-it`

userID `3572682e824fbb759bad843c8552a4fa8dd47736a85bfc94a44fecdfa8fc346b`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 73 | 2.20B | 98% |
| subagent | 10 | 43.93M | 2% |

| Model | Total |
|---|---:|
| claude-opus-4-8 | 1.20B |
| claude-fable-5 | 515.99M |
| claude-opus-5 | 504.80M |
| claude-opus-4-7 | 18.47M |
| <synthetic> | 0 |

Active 2026-07-04 → 2026-08-06 (26 days). Busiest day 2026-07-23 at 278.30M.

| Project | Total |
|---|---:|
| `-home-phantom-orchestrator` | 1.42B |
| `-media-phantom-orchestrator-BitcoinNode-AI-Projects-MultiBoot` | 422.53M |
| `-home-phantom-orchestrator-tv-tracker` | 239.71M |
| `-home-phantom-orchestrator-questline` | 131.49M |
| `-media-phantom-orchestrator-Elements1-Build-From-Scratch-Ideas-look-at-this-Cognitive-profile` | 28.60M |
| `-home-phantom-orchestrator-token-usage` | 987.89K |
| `-home-phantom-orchestrator-Documents-Transcript-engine` | 428.77K |

### broodierchip@gmail.com

**1,539,728,749 tokens** (1.54B) — `/home/phantom-orchestrator/old/.claude`

userID `08537de04fe9cd9f989aa2c5fa9ffa076ee3f6a0286fc671f5c7a6016fc374b3`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 31 | 1.24B | 80% |
| subagent | 275 | 302.85M | 20% |

| Model | Total |
|---|---:|
| claude-opus-4-6 | 833.65M |
| claude-opus-4-5-20251101 | 574.58M |
| claude-haiku-4-5-20251001 | 108.95M |
| claude-sonnet-4-5-20250929 | 16.30M |
| claude-sonnet-4-6 | 6.24M |
| <synthetic> | 0 |

Active 2026-01-17 → 2026-02-24 (21 days). Busiest day 2026-02-22 at 472.41M.

| Project | Total |
|---|---:|
| `-media-phantom-orchestrator-BitcoinNode-AI-Projects-MultiBoot` | 577.41M |
| `-media-phantom-orchestrator-BitcoinNode-AI-Projects-Bug-Solving` | 221.92M |
| `-media-phantom-orchestrator-BitcoinNode-gemini-crazy-idea-forta` | 183.94M |
| `-home-phantom-orchestrator` | 164.70M |
| `-media-phantom-orchestrator-BitcoinNode-gemini-crazy-idea-real-math-solving-KS-COMPRESS-ENCRYPT-SYSTEM` | 140.26M |
| `-media-phantom-orchestrator-BitcoinNode-Claude-workspace` | 91.12M |
| `-media-phantom-orchestrator-BitcoinNode-Claude-workspace-BIOS-upgrade` | 49.27M |
| `-media-phantom-orchestrator-BitcoinNode-copilot` | 45.86M |

### broodierchip@gmail.com

**1,511,346,979 tokens** (1.51B) — `/home/phantom-orchestrator/.claude`

userID `08537de04fe9cd9f989aa2c5fa9ffa076ee3f6a0286fc671f5c7a6016fc374b3`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 16,441 | 1.47B | 97% |
| workflow | 15 | 38.35M | 3% |

| Model | Total |
|---|---:|
| claude-opus-4-8 | 1.26B |
| claude-opus-5 | 248.96M |
| claude-haiku-4-5-20251001 | 2.40M |
| claude-opus-4-6 | 390.37K |
| <synthetic> | 0 |

Active 2026-07-03 → 2026-08-02 (20 days). Busiest day 2026-07-26 at 172.42M.

| Project | Total |
|---|---:|
| `-media-phantom-orchestrator-Elements1-logistis-app` | 1.18B |
| `-home-phantom-orchestrator-Documents-Music` | 309.61M |
| `-home-phantom-orchestrator` | 19.88M |
| `-tmp` | 2.40M |
| `-media-phantom-orchestrator-Elements1-logistis-App` | 689.30K |

### codehunterextreme@gmail.com

**26,776,064 tokens** (26.78M) — `/home/phantom-orchestrator/.claude-alt`

userID `2b2f79380228ba53af8e39adbd917e1bdd126de65caf3d62a42d62f349fd9473`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 2 | 26.78M | 100% |

| Model | Total |
|---|---:|
| claude-opus-4-8 | 26.78M |
| <synthetic> | 0 |

Active 2026-07-25 → 2026-08-01 (3 days). Busiest day 2026-07-25 at 21.94M.

| Project | Total |
|---|---:|
| `-home-phantom-orchestrator-Documents-Transcript-engine` | 26.78M |
| `-home-phantom-orchestrator` | 0 |

### user:2d4777822844

**7,281,866 tokens** (7.28M) — `/home/phantom-orchestrator/.claude-alt-api`

userID `2d4777822844690431e6e0c2b862bc04d5388b9850bcdef441c6342683a1c1d2`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 1 | 7.28M | 100% |

| Model | Total |
|---|---:|
| claude-sonnet-4-6 | 7.28M |

Active 2026-04-24 → 2026-04-24 (1 days). Busiest day 2026-04-24 at 7.28M.

| Project | Total |
|---|---:|
| `-media-phantom-orchestrator-Elements1-Final-API-alt` | 7.28M |

### user:283b8e5b8e48

**0 tokens** (0) — `/home/phantom-orchestrator/.claude-api`

userID `283b8e5b8e48d17836c99894017f4ce322b58772226367f320d5373a1104bd43`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 1 | 0 | 0% |

| Model | Total |
|---|---:|
| <synthetic> | 0 |

Active 2026-04-24 → 2026-04-24 (1 days). Busiest day 2026-04-24 at 0.

| Project | Total |
|---|---:|
| `-media-phantom-orchestrator-Elements1-Final-API-alt` | 0 |
