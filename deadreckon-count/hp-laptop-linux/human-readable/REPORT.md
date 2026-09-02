# Claude Code token usage — HP Laptop Linux

_Generated 2026-09-01T06:48:33-05:00_

## Total for this computer: 11,551,416,604 tokens (11.55B)

Across 15 account(s), 422 sessions, 62,480 assistant turns.

Counted from `message.usage` in the local session JSONL — the API's own
accounting, deduplicated by message uuid.

## Accounts

| Account | Sessions | Turns | Input | Cache write | Cache read | Output | Total |
|---|---:|---:|---:|---:|---:|---:|---:|
| codehunterextreme@gmail.com | 47 | 46,318 | 839.58K | 190.91M | 7.83B | 42.33M | **8.06B** |
| broodierchip@gmail.com | 87 | 9,891 | 1.65M | 68.75M | 2.66B | 11.71M | **2.74B** |
| user:73ae64bf180b | 6 | 5,101 | 21.80M | 0 | 493.71M | 4.99M | **520.50M** |
| alexander.sorrell.it@gmail.com | 10 | 1,164 | 12.93K | 6.74M | 216.42M | 683.94K | **223.85M** |
| user:4be462f3a2f9 | 1 | 6 | 1.92K | 10.86K | 125.20K | 3.23K | **141.21K** |
| broodierchip@gmail.com | 84 | 0 | 0 | 0 | 0 | 0 | **0** |
| codehunterextreme@gmail.com | 27 | 0 | 0 | 0 | 0 | 0 | **0** |
| user:4be462f3a2f9 | 1 | 0 | 0 | 0 | 0 | 0 | **0** |
| alexander.sorrell.it@gmail.com | 2 | 0 | 0 | 0 | 0 | 0 | **0** |
| user:73ae64bf180b | 6 | 0 | 0 | 0 | 0 | 0 | **0** |
| broodierchip@gmail.com | 87 | 0 | 0 | 0 | 0 | 0 | **0** |
| codehunterextreme@gmail.com | 47 | 0 | 0 | 0 | 0 | 0 | **0** |
| user:4be462f3a2f9 | 1 | 0 | 0 | 0 | 0 | 0 | **0** |
| alexander.sorrell.it@gmail.com | 10 | 0 | 0 | 0 | 0 | 0 | **0** |
| user:73ae64bf180b | 6 | 0 | 0 | 0 | 0 | 0 | **0** |

## By provider

Claude Code can be pointed at a non-Anthropic backend; those transcripts are
byte-identical to Claude ones. Totals are split on the model id so an
Anthropic figure is never inflated by tokens Anthropic did not serve.

| Provider | Tokens | Share |
|---|---:|---:|
| anthropic | 11,016,745,451 | 95.4% |
| deepseek | 534,671,153 | 4.6% |

**Anthropic-only total: 11,016,745,451 tokens (11.02B)**


## Profiles found and NOT counted

A profile-shaped directory with no config file of its own claims no
account, so its tokens are excluded rather than booked to an invented
one. Listed with their paths so the exclusion is checkable.

| Directory | Why |
|---|---|
| `/home/phantomcore/.ai-logs-archive/claude/Desktop_standout_clean_.claude` | no config file of its own |
| `/home/phantomcore/.ai-logs-archive/claude/Desktop_standout_full_.claude` | no config file of its own |
| `/home/phantomcore/.ai-logs-archive/claude/Desktop_standout_max_.claude` | no config file of its own |
| `/home/phantomcore/.ai-logs-archive/claude/Desktop_standout_sandbox_.claude` | no config file of its own |
| `/home/phantomcore/Desktop/standout_clean/.claude` | no config file of its own |
| `/home/phantomcore/Desktop/standout_full/.claude` | no config file of its own |
| `/home/phantomcore/Desktop/standout_max/.claude` | no config file of its own |
| `/home/phantomcore/Desktop/standout_sandbox/.claude` | no config file of its own |
| `/home/phantomcore/starreckon-latest/tests/conformance/home/.claude` | no config file of its own |

### Other AI tools on this machine

Listed so a provider missing from the table above is unambiguous: a tool
that records no usage cannot be counted from disk, which is different
from a tool that was never used.

| Tool | Directory | Files | Token usage on disk |
|---|---|---:|---|
| Gemini CLI | `/home/phantomcore/.gemini` | 1,654 | yes — countable |
| GitHub Copilot CLI | `/home/phantomcore/.copilot` | 557 | **no — not countable** |
| Antigravity CLI | `/home/phantomcore/.antigravitycli` | 1 | **no — not countable** |
| OpenAI Codex CLI | `/home/phantomcore/.codex` | 5 | yes — countable |

## Authentication and organization

An API-key profile bills to the organization the key belongs to, which is
not recorded on disk — rerun with `--probe-api` to resolve it. A profile is
linked to an account only when their organization UUIDs match.

| Account | Auth | Organization | Org UUID | Linked to |
|---|---|---|---|---|
| codehunterextreme@gmail.com | oauth | codehunterextreme@gmail.com's Organization | `ba511861-53b4-4599-8019-93db6389d991` | — |
| broodierchip@gmail.com | oauth | broodierchip@gmail.com's Organization | `6bfc754e-a205-41c3-9dac-80e593f494e0` | — |
| user:73ae64bf180b | unknown | — | `—` | — |
| alexander.sorrell.it@gmail.com | oauth | alexander.sorrell.it@gmail.com's Organization | `66565064-263e-4d54-b06f-15cae4b2febc` | — |
| user:4be462f3a2f9 | api_key | — | `—` | — |
| broodierchip@gmail.com | oauth | broodierchip@gmail.com's Organization | `6bfc754e-a205-41c3-9dac-80e593f494e0` | — |
| codehunterextreme@gmail.com | oauth | codehunterextreme@gmail.com's Organization | `ba511861-53b4-4599-8019-93db6389d991` | — |
| user:4be462f3a2f9 | api_key | — | `—` | — |
| alexander.sorrell.it@gmail.com | oauth | alexander.sorrell.it@gmail.com's Organization | `66565064-263e-4d54-b06f-15cae4b2febc` | — |
| user:73ae64bf180b | unknown | — | `—` | — |
| broodierchip@gmail.com | oauth | broodierchip@gmail.com's Organization | `6bfc754e-a205-41c3-9dac-80e593f494e0` | — |
| codehunterextreme@gmail.com | oauth | codehunterextreme@gmail.com's Organization | `ba511861-53b4-4599-8019-93db6389d991` | — |
| user:4be462f3a2f9 | api_key | — | `—` | — |
| alexander.sorrell.it@gmail.com | oauth | alexander.sorrell.it@gmail.com's Organization | `66565064-263e-4d54-b06f-15cae4b2febc` | — |
| user:73ae64bf180b | unknown | — | `—` | — |

### codehunterextreme@gmail.com

**8,062,476,061 tokens** (8.06B) — `/home/phantomcore/.claude-alt`

userID `7332676f0b84f06017ed5ef60ae6c498a7f6b1ea73c9ab98be498d78883ab952`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 47 | 5.48B | 68% |
| subagent | 60 | 346.81M | 4% |
| workflow | 1,540 | 2.24B | 28% |

| Model | Total |
|---|---:|
| claude-opus-5 | 6.69B |
| claude-fable-5 | 1.13B |
| claude-opus-4-8 | 246.85M |
| claude-sonnet-5 | 120.59K |

Active 2026-07-07 → 2026-08-21 (33 days). Busiest day 2026-08-10 at 945.03M.

| Project | Total |
|---|---:|
| `-media-phantomcore-AI-DRIVE-AI-Shit-mining-Quest-coder` | 3.76B |
| `-media-phantomcore-AI-DRIVE-AI-Shit-mining-Quest-coder-Claude-Code` | 3.55B |
| `-home-phantomcore` | 329.77M |
| `-media-phantomcore-AI-DRIVE-Transcribing` | 182.82M |
| `-media-phantomcore-AI-DRIVE-VORTEX-SYSTEM` | 167.91M |
| `-media-phantomcore-AI-DRIVE-pip` | 72.65M |
| `-media-phantomcore-AI-DRIVE-hackathons-mantle` | 167.26K |
| `-media-phantomcore-AI-DRIVE-hackathons-Pacto-secto` | 64.96K |

### broodierchip@gmail.com

**2,744,450,437 tokens** (2.74B) — `/home/phantomcore/.claude`

userID `79e85db2d81700a09041764ff53e316b5f85138932145b678e9343bb933075a8`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 87 | 2.60B | 95% |
| subagent | 59 | 31.36M | 1% |
| workflow | 196 | 115.75M | 4% |

| Model | Total |
|---|---:|
| claude-opus-4-7 | 2.55B |
| claude-opus-5 | 158.18M |
| deepseek-v4-pro | 14.16M |
| claude-sonnet-4-6 | 10.33M |
| claude-opus-4-8 | 6.17M |
| claude-haiku-4-5-20251001 | 3.31M |
| deepseek-v4-flash | 11.00K |

Active 2026-05-04 → 2026-08-17 (22 days). Busiest day 2026-05-13 at 650.12M.

| Project | Total |
|---|---:|
| `-media-phantomcore-AI-DRIVE-DeepSeek-work-deepseek-claude-code` | 810.30M |
| `-media-phantomcore-AI-DRIVE-DeepSeek-work-my-claude-seek-deepseek-bug-finder` | 320.28M |
| `-media-phantomcore-AI-DRIVE-AI-Shit-mining-Quest-coder-Claude-Code` | 276.20M |
| `-media-phantomcore-AI-DRIVE-DeepSeek-work-my-claude-seek-claude` | 220.64M |
| `-media-phantomcore-AI-DRIVE-DeepSeek-work-reddit` | 215.34M |
| `-home-phantomcore` | 164.75M |
| `-media-phantomcore-AI-DRIVE-Contra` | 157.97M |
| `-media-phantomcore-AI-DRIVE-hackathons-Slack` | 132.11M |

### user:73ae64bf180b

**520,497,793 tokens** (520.50M) — `/home/phantomcore/.my-claude`

userID `73ae64bf180bd1e9d1fd095bb0126c740a00c47d248a47e830ed9f2af12201b5`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 6 | 45.47M | 9% |
| subagent | 124 | 475.02M | 91% |

| Model | Total |
|---|---:|
| deepseek-v4-pro | 486.52M |
| deepseek-v4-flash | 33.98M |

Active 2026-05-12 → 2026-07-20 (22 days). Busiest day 2026-05-13 at 105.39M.

| Project | Total |
|---|---:|
| `-media-phantomcore-AI-DRIVE-DeepSeek-work-my-claude-seek-claude` | 254.02M |
| `-media-phantomcore-AI-DRIVE-DeepSeek-work-my-claude-seek-deepseek-bug-finder` | 61.80M |
| `-media-phantomcore-AI-DRIVE-DeepSeek-work-my-claude-seek-just-agents` | 56.63M |
| `-media-phantomcore-AI-DRIVE-hackathons-ai-ml-hack-2026` | 54.11M |
| `-media-phantomcore-AI-DRIVE-VORTEX-SYSTEM-deepseek` | 35.25M |
| `-media-phantomcore-AI-DRIVE-DeepSeek-work` | 14.06M |
| `-media-phantomcore-AI-DRIVE-pip` | 13.53M |
| `-media-phantomcore-AI-DRIVE-DeepSeek-work-deepseek-claude-code` | 10.72M |

### alexander.sorrell.it@gmail.com

**223,851,103 tokens** (223.85M) — `/home/phantomcore/.claude-it`

userID `53a6fc28c93264480360b0eac01b9f6ce310137e8581f22ff931dbaa003fd4fe`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 10 | 213.24M | 95% |
| subagent | 9 | 10.61M | 5% |

| Model | Total |
|---|---:|
| claude-sonnet-5 | 176.90M |
| claude-sonnet-4-6 | 43.09M |
| claude-opus-4-7 | 3.12M |
| claude-haiku-4-5-20251001 | 745.53K |

Active 2026-06-09 → 2026-09-01 (5 days). Busiest day 2026-08-31 at 89.50M.

| Project | Total |
|---|---:|
| `-home-phantomcore` | 204.44M |
| `-media-phantomcore-AI-DRIVE-hackathons-DeveloperWeek-New-York-2026-Hackathon` | 16.29M |
| `-home-phantomcore-deadreckon-count-latest` | 2.88M |
| `-home-phantomcore-starreckon-latest` | 241.62K |

### user:4be462f3a2f9

**141,210 tokens** (141.21K) — `/home/phantomcore/.claude-alt-api`

userID `4be462f3a2f9620e57e7f032c0d9b4a5005f30e7373904a9f7448a1fbface369`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 1 | 141.21K | 100% |

| Model | Total |
|---|---:|
| claude-opus-4-8 | 76.15K |
| claude-fable-5 | 65.06K |

Active 2026-06-09 → 2026-06-09 (1 days). Busiest day 2026-06-09 at 141.21K.

| Project | Total |
|---|---:|
| `-media-phantomcore-AI-DRIVE-DeepSeek-work-my-claude-seek-fable` | 141.21K |

### broodierchip@gmail.com

**0 tokens** (0) — `/home/phantomcore/.ai-logs-archive/claude/.claude`

userID `79e85db2d81700a09041764ff53e316b5f85138932145b678e9343bb933075a8`

### codehunterextreme@gmail.com

**0 tokens** (0) — `/home/phantomcore/.ai-logs-archive/claude/.claude-alt`

userID `7332676f0b84f06017ed5ef60ae6c498a7f6b1ea73c9ab98be498d78883ab952`

### user:4be462f3a2f9

**0 tokens** (0) — `/home/phantomcore/.ai-logs-archive/claude/.claude-alt-api`

userID `4be462f3a2f9620e57e7f032c0d9b4a5005f30e7373904a9f7448a1fbface369`

### alexander.sorrell.it@gmail.com

**0 tokens** (0) — `/home/phantomcore/.ai-logs-archive/claude/.claude-it`

userID `53a6fc28c93264480360b0eac01b9f6ce310137e8581f22ff931dbaa003fd4fe`

### user:73ae64bf180b

**0 tokens** (0) — `/home/phantomcore/.ai-logs-archive/claude/.my-claude`

userID `73ae64bf180bd1e9d1fd095bb0126c740a00c47d248a47e830ed9f2af12201b5`

### broodierchip@gmail.com

**0 tokens** (0) — `/home/phantomcore/.ai-logs-archive/claude/claude`

userID `79e85db2d81700a09041764ff53e316b5f85138932145b678e9343bb933075a8`

### codehunterextreme@gmail.com

**0 tokens** (0) — `/home/phantomcore/.ai-logs-archive/claude/claude-alt`

userID `7332676f0b84f06017ed5ef60ae6c498a7f6b1ea73c9ab98be498d78883ab952`

### user:4be462f3a2f9

**0 tokens** (0) — `/home/phantomcore/.ai-logs-archive/claude/claude-alt-api`

userID `4be462f3a2f9620e57e7f032c0d9b4a5005f30e7373904a9f7448a1fbface369`

### alexander.sorrell.it@gmail.com

**0 tokens** (0) — `/home/phantomcore/.ai-logs-archive/claude/claude-it`

userID `53a6fc28c93264480360b0eac01b9f6ce310137e8581f22ff931dbaa003fd4fe`

### user:73ae64bf180b

**0 tokens** (0) — `/home/phantomcore/.ai-logs-archive/claude/my-claude`

userID `73ae64bf180bd1e9d1fd095bb0126c740a00c47d248a47e830ed9f2af12201b5`
