# Claude Code token usage — Dell Latitude 7480 Linux

_Generated 2026-08-25T01:55:20-05:00_

## Total for this computer: 2,225,228,697 tokens (2.23B)

Across 10 account(s), 33,157 sessions, 23,227 assistant turns.

Counted from `message.usage` in the local session JSONL — the API's own
accounting, deduplicated by message uuid.

## Accounts

| Account | Sessions | Turns | Input | Cache write | Cache read | Output | Total |
|---|---:|---:|---:|---:|---:|---:|---:|
| alexander.sorrell.it@gmail.com | 92 | 4,967 | 172.38K | 43.98M | 1.27B | 5.76M | **1.32B** |
| alexander.sorrell.it@gmail.com | 16,483 | 18,108 | 159.91M | 131.38M | 589.91M | 9.13M | **890.34M** |
| codehunterextreme@gmail.com | 2 | 99 | 3.56K | 1.44M | 10.27M | 75.34K | **11.79M** |
| user:2d4777822844 | 1 | 50 | 174 | 506.20K | 2.93M | 52.28K | **3.49M** |
| user:283b8e5b8e48 | 1 | 3 | 0 | 0 | 0 | 0 | **0** |
| alexander.sorrell.it@gmail.com | 16,483 | 0 | 0 | 0 | 0 | 0 | **0** |
| codehunterextreme@gmail.com | 2 | 0 | 0 | 0 | 0 | 0 | **0** |
| user:2d4777822844 | 1 | 0 | 0 | 0 | 0 | 0 | **0** |
| user:283b8e5b8e48 | 1 | 0 | 0 | 0 | 0 | 0 | **0** |
| alexander.sorrell.it@gmail.com | 91 | 0 | 0 | 0 | 0 | 0 | **0** |

## By provider

Claude Code can be pointed at a non-Anthropic backend; those transcripts are
byte-identical to Claude ones. Totals are split on the model id so an
Anthropic figure is never inflated by tokens Anthropic did not serve.

| Provider | Tokens | Share |
|---|---:|---:|
| anthropic | 2,225,228,697 | 100.0% |

**Anthropic-only total: 2,225,228,697 tokens (2.23B)**


## Profiles found and NOT counted

A profile-shaped directory with no config file of its own claims no
account, so its tokens are excluded rather than booked to an invented
one. Listed with their paths so the exclusion is checkable.

| Directory | Why |
|---|---|
| `/home/phantom-orchestrator/.ai-logs-archive/claude/old_.claude` | no config file of its own |
| `/home/phantom-orchestrator/.ai-logs-archive/claude/old_deadreckon-record.pre-clone_asus-laptop-linux_.claude` | no config file of its own |
| `/home/phantom-orchestrator/.ai-logs-archive/claude/old_deadreckon-record.pre-clone_dell-inspiron-desktop-linux_.claude` | no config file of its own |
| `/home/phantom-orchestrator/.ai-logs-archive/claude/old_deadreckon-record.pre-clone_dell-latitude-7480-linux_.claude` | no config file of its own |
| `/home/phantom-orchestrator/.ai-logs-archive/claude/old_deadreckon-record.pre-clone_hp-laptop-linux_.claude` | no config file of its own |
| `/home/phantom-orchestrator/.ai-logs-archive/claude/old_deadreckon-record.pre-clone_macbook-air-m1_.claude` | no config file of its own |
| `/home/phantom-orchestrator/old/.claude` | no config file of its own |
| `/home/phantom-orchestrator/old/deadreckon-record.pre-clone/asus-laptop-linux/.claude` | no config file of its own |
| `/home/phantom-orchestrator/old/deadreckon-record.pre-clone/dell-inspiron-desktop-linux/.claude` | no config file of its own |
| `/home/phantom-orchestrator/old/deadreckon-record.pre-clone/dell-latitude-7480-linux/.claude` | no config file of its own |
| `/home/phantom-orchestrator/old/deadreckon-record.pre-clone/hp-laptop-linux/.claude` | no config file of its own |
| `/home/phantom-orchestrator/old/deadreckon-record.pre-clone/macbook-air-m1/.claude` | no config file of its own |

### Other AI tools on this machine

Listed so a provider missing from the table above is unambiguous: a tool
that records no usage cannot be counted from disk, which is different
from a tool that was never used.

| Tool | Directory | Files | Token usage on disk |
|---|---|---:|---|
| Gemini CLI | `/home/phantom-orchestrator/.gemini` | 162 | **no — not countable** |
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
| alexander.sorrell.it@gmail.com | oauth | alexander.sorrell.it@gmail.com's Organization | `66565064-263e-4d54-b06f-15cae4b2febc` | — |
| codehunterextreme@gmail.com | oauth | codehunterextreme@gmail.com's Organization | `ba511861-53b4-4599-8019-93db6389d991` | — |
| user:2d4777822844 | api_key | — | `—` | — |
| user:283b8e5b8e48 | api_key | — | `—` | — |
| alexander.sorrell.it@gmail.com | oauth | alexander.sorrell.it@gmail.com's Organization | `66565064-263e-4d54-b06f-15cae4b2febc` | — |
| codehunterextreme@gmail.com | oauth | codehunterextreme@gmail.com's Organization | `ba511861-53b4-4599-8019-93db6389d991` | — |
| user:2d4777822844 | api_key | — | `—` | — |
| user:283b8e5b8e48 | api_key | — | `—` | — |
| alexander.sorrell.it@gmail.com | oauth | alexander.sorrell.it@gmail.com's Organization | `66565064-263e-4d54-b06f-15cae4b2febc` | — |

### alexander.sorrell.it@gmail.com

**1,319,619,643 tokens** (1.32B) — `/home/phantom-orchestrator/.claude-it`

userID `3572682e824fbb759bad843c8552a4fa8dd47736a85bfc94a44fecdfa8fc346b`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 92 | 1.30B | 99% |
| subagent | 10 | 15.91M | 1% |

| Model | Total |
|---|---:|
| claude-opus-5 | 592.14M |
| claude-opus-4-8 | 507.28M |
| claude-fable-5 | 203.77M |
| claude-opus-4-7 | 16.43M |

Active 2026-07-04 → 2026-08-25 (36 days). Busiest day 2026-07-23 at 106.65M.

| Project | Total |
|---|---:|
| `-home-phantom-orchestrator` | 1.04B |
| `-home-phantom-orchestrator-tv-tracker` | 118.40M |
| `-media-phantom-orchestrator-BitcoinNode-AI-Projects-MultiBoot` | 86.27M |
| `-home-phantom-orchestrator-questline` | 51.66M |
| `-media-phantom-orchestrator-Elements1-Build-From-Scratch-Ideas-look-at-this-Cognitive-profile` | 11.10M |
| `-home-phantom-orchestrator-deadreckon-count` | 4.91M |
| `-home-phantom-orchestrator-token-usage` | 3.29M |
| `-home-phantom-orchestrator-Documents-Transcript-engine` | 231.75K |

### alexander.sorrell.it@gmail.com

**890,336,925 tokens** (890.34M) — `/home/phantom-orchestrator/.claude`

userID `08537de04fe9cd9f989aa2c5fa9ffa076ee3f6a0286fc671f5c7a6016fc374b3`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 16,483 | 876.34M | 98% |
| workflow | 15 | 14.00M | 2% |

| Model | Total |
|---|---:|
| claude-opus-4-8 | 614.86M |
| claude-opus-5 | 251.32M |
| claude-sonnet-5 | 21.45M |
| claude-haiku-4-5-20251001 | 2.48M |
| claude-opus-4-6 | 223.25K |

Active 2026-07-03 → 2026-08-21 (24 days). Busiest day 2026-08-18 at 105.41M.

| Project | Total |
|---|---:|
| `-media-phantom-orchestrator-Elements1-logistis-app` | 583.43M |
| `-home-phantom-orchestrator` | 172.02M |
| `-home-phantom-orchestrator-Documents-Music` | 132.07M |
| `-tmp` | 2.48M |
| `-media-phantom-orchestrator-Elements1-logistis-App` | 344.65K |

### codehunterextreme@gmail.com

**11,786,126 tokens** (11.79M) — `/home/phantom-orchestrator/.claude-alt`

userID `2b2f79380228ba53af8e39adbd917e1bdd126de65caf3d62a42d62f349fd9473`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 2 | 11.79M | 100% |

| Model | Total |
|---|---:|
| claude-opus-4-8 | 11.79M |

Active 2026-07-25 → 2026-07-26 (2 days). Busiest day 2026-07-25 at 8.90M.

| Project | Total |
|---|---:|
| `-home-phantom-orchestrator-Documents-Transcript-engine` | 11.79M |

### user:2d4777822844

**3,486,003 tokens** (3.49M) — `/home/phantom-orchestrator/.claude-alt-api`

userID `2d4777822844690431e6e0c2b862bc04d5388b9850bcdef441c6342683a1c1d2`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 1 | 3.49M | 100% |

| Model | Total |
|---|---:|
| claude-sonnet-4-6 | 3.49M |

Active 2026-04-24 → 2026-04-24 (1 days). Busiest day 2026-04-24 at 3.49M.

| Project | Total |
|---|---:|
| `-media-phantom-orchestrator-Elements1-Final-API-alt` | 3.49M |

### user:283b8e5b8e48

**0 tokens** (0) — `/home/phantom-orchestrator/.claude-api`

userID `283b8e5b8e48d17836c99894017f4ce322b58772226367f320d5373a1104bd43`

### alexander.sorrell.it@gmail.com

**0 tokens** (0) — `/home/phantom-orchestrator/.ai-logs-archive/claude/claude`

userID `08537de04fe9cd9f989aa2c5fa9ffa076ee3f6a0286fc671f5c7a6016fc374b3`

### codehunterextreme@gmail.com

**0 tokens** (0) — `/home/phantom-orchestrator/.ai-logs-archive/claude/claude-alt`

userID `2b2f79380228ba53af8e39adbd917e1bdd126de65caf3d62a42d62f349fd9473`

### user:2d4777822844

**0 tokens** (0) — `/home/phantom-orchestrator/.ai-logs-archive/claude/claude-alt-api`

userID `2d4777822844690431e6e0c2b862bc04d5388b9850bcdef441c6342683a1c1d2`

### user:283b8e5b8e48

**0 tokens** (0) — `/home/phantom-orchestrator/.ai-logs-archive/claude/claude-api`

userID `283b8e5b8e48d17836c99894017f4ce322b58772226367f320d5373a1104bd43`

### alexander.sorrell.it@gmail.com

**0 tokens** (0) — `/home/phantom-orchestrator/.ai-logs-archive/claude/claude-it`

userID `3572682e824fbb759bad843c8552a4fa8dd47736a85bfc94a44fecdfa8fc346b`
