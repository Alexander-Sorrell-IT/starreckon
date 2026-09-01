# Claude Code token usage — HP-Phantom-Core

_Generated 2026-08-08T15:24:05-05:00_

## Total for this computer: 6,598,975,819 tokens (6.60B)

Across 23 account(s), 5,572 sessions, 31,872 assistant turns.

Counted from `message.usage` in the local session JSONL — the API's own
accounting, deduplicated by message uuid.

## Accounts

| Account | Sessions | Turns | Input | Cache write | Cache read | Output | Total |
|---|---:|---:|---:|---:|---:|---:|---:|
| codehunterextreme@gmail.com | 27 | 13,803 | 546.70K | 76.56M | 2.86B | 14.51M | **2.96B** |
| broodierchip@gmail.com | 84 | 7,912 | 1.54M | 58.26M | 2.52B | 9.32M | **2.58B** |
| user:73ae64bf180b | 6 | 5,101 | 21.80M | 0 | 493.71M | 4.99M | **520.50M** |
| unknown (Desktop_standout_clean_.claude) | 420 | 2,098 | 557.02K | 14.27M | 304.38M | 1.90M | **321.10M** |
| unknown (Desktop_standout_full_.claude) | 805 | 2,477 | 728.43K | 15.64M | 148.94M | 2.52M | **167.83M** |
| alexander.sorrell.it@gmail.com | 2 | 454 | 11.54K | 1.05M | 42.55M | 222.19K | **43.83M** |
| unknown (Desktop_standout_max_.claude) | 805 | 20 | 4.53K | 52.35K | 4.58M | 30.33K | **4.67M** |
| unknown (.claude-alt) | 27 | 1 | 2 | 669 | 912.29K | 295 | **913.26K** |
| user:4be462f3a2f9 | 1 | 6 | 1.92K | 10.86K | 125.20K | 3.23K | **141.21K** |
| broodierchip@gmail.com | 84 | 0 | 0 | 0 | 0 | 0 | **0** |
| unknown (.claude-alt-api) | 1 | 0 | 0 | 0 | 0 | 0 | **0** |
| unknown (.claude-it) | 2 | 0 | 0 | 0 | 0 | 0 | **0** |
| unknown (.my-claude) | 6 | 0 | 0 | 0 | 0 | 0 | **0** |
| unknown (Desktop_standout_sandbox_.claude) | 576 | 0 | 0 | 0 | 0 | 0 | **0** |
| unknown (claude) | 84 | 0 | 0 | 0 | 0 | 0 | **0** |
| unknown (claude-alt) | 27 | 0 | 0 | 0 | 0 | 0 | **0** |
| unknown (claude-alt-api) | 1 | 0 | 0 | 0 | 0 | 0 | **0** |
| unknown (claude-it) | 2 | 0 | 0 | 0 | 0 | 0 | **0** |
| unknown (my-claude) | 6 | 0 | 0 | 0 | 0 | 0 | **0** |
| broodierchip@gmail.com | 420 | 0 | 0 | 0 | 0 | 0 | **0** |
| broodierchip@gmail.com | 805 | 0 | 0 | 0 | 0 | 0 | **0** |
| broodierchip@gmail.com | 805 | 0 | 0 | 0 | 0 | 0 | **0** |
| broodierchip@gmail.com | 576 | 0 | 0 | 0 | 0 | 0 | **0** |

## By provider

Claude Code can be pointed at a non-Anthropic backend; those transcripts are
byte-identical to Claude ones. Totals are split on the model id so an
Anthropic figure is never inflated by tokens Anthropic did not serve.

| Provider | Tokens | Share |
|---|---:|---:|
| anthropic | 6,064,304,666 | 91.9% |
| deepseek | 534,671,153 | 8.1% |

**Anthropic-only total: 6,064,304,666 tokens (6.06B)**


### Other AI tools on this machine

Listed so a provider missing from the table above is unambiguous: a tool
that records no usage cannot be counted from disk, which is different
from a tool that was never used.

| Tool | Directory | Files | Token usage on disk |
|---|---|---:|---|
| Gemini CLI | `/home/testuser/.gemini` | 942 | **no — not countable** |
| GitHub Copilot CLI | `/home/testuser/.copilot` | 557 | **no — not countable** |
| Antigravity CLI | `/home/testuser/.antigravitycli` | 1 | **no — not countable** |
| OpenAI Codex CLI | `/home/testuser/.codex` | 5 | yes — countable |

## Authentication and organization

An API-key profile bills to the organization the key belongs to, which is
not recorded on disk — rerun with `--probe-api` to resolve it. A profile is
linked to an account only when their organization UUIDs match.

| Account | Auth | Organization | Org UUID | Linked to |
|---|---|---|---|---|
| codehunterextreme@gmail.com | oauth | codehunterextreme@gmail.com's Organization | `ba511861-53b4-4599-8019-93db6389d991` | — |
| broodierchip@gmail.com | oauth | broodierchip@gmail.com's Organization | `6bfc754e-a205-41c3-9dac-80e593f494e0` | — |
| user:73ae64bf180b | unknown | — | `—` | — |
| unknown (Desktop_standout_clean_.claude) | unknown | — | `—` | — |
| unknown (Desktop_standout_full_.claude) | unknown | — | `—` | — |
| alexander.sorrell.it@gmail.com | oauth | alexander.sorrell.it@gmail.com's Organization | `66565064-263e-4d54-b06f-15cae4b2febc` | — |
| unknown (Desktop_standout_max_.claude) | unknown | — | `—` | — |
| unknown (.claude-alt) | unknown | — | `—` | — |
| user:4be462f3a2f9 | api_key | — | `—` | — |
| broodierchip@gmail.com | oauth | broodierchip@gmail.com's Organization | `6bfc754e-a205-41c3-9dac-80e593f494e0` | — |
| unknown (.claude-alt-api) | unknown | — | `—` | — |
| unknown (.claude-it) | unknown | — | `—` | — |
| unknown (.my-claude) | unknown | — | `—` | — |
| unknown (Desktop_standout_sandbox_.claude) | unknown | — | `—` | — |
| unknown (claude) | unknown | — | `—` | — |
| unknown (claude-alt) | unknown | — | `—` | — |
| unknown (claude-alt-api) | unknown | — | `—` | — |
| unknown (claude-it) | unknown | — | `—` | — |
| unknown (my-claude) | unknown | — | `—` | — |
| broodierchip@gmail.com | oauth | broodierchip@gmail.com's Organization | `6bfc754e-a205-41c3-9dac-80e593f494e0` | — |
| broodierchip@gmail.com | oauth | broodierchip@gmail.com's Organization | `6bfc754e-a205-41c3-9dac-80e593f494e0` | — |
| broodierchip@gmail.com | oauth | broodierchip@gmail.com's Organization | `6bfc754e-a205-41c3-9dac-80e593f494e0` | — |
| broodierchip@gmail.com | oauth | broodierchip@gmail.com's Organization | `6bfc754e-a205-41c3-9dac-80e593f494e0` | — |

### codehunterextreme@gmail.com

**2,955,032,999 tokens** (2.96B) — `/home/testuser/.claude-alt`

userID `7332676f0b84f06017ed5ef60ae6c498a7f6b1ea73c9ab98be498d78883ab952`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 27 | 2.49B | 84% |
| subagent | 21 | 15.65M | 1% |
| workflow | 590 | 448.98M | 15% |

| Model | Total |
|---|---:|
| claude-opus-5 | 2.19B |
| claude-fable-5 | 568.00M |
| claude-opus-4-8 | 193.45M |
| claude-sonnet-5 | 120.59K |

Active 2026-07-07 → 2026-08-08 (21 days). Busiest day 2026-08-07 at 855.10M.

| Project | Total |
|---|---:|
| `-media-testuser-AI-DRIVE-AI-Shit-mining-Quest-coder-Claude-Code` | 2.28B |
| `-media-testuser-AI-DRIVE-Transcribing` | 182.82M |
| `-media-testuser-AI-DRIVE-VORTEX-SYSTEM` | 167.91M |
| `-home-testuser` | 146.00M |
| `-media-testuser-AI-DRIVE-AI-Shit-mining-Quest-coder` | 101.39M |
| `-media-testuser-AI-DRIVE-pip` | 72.65M |
| `-media-testuser-AI-DRIVE-hackathons-mantle` | 167.26K |
| `-media-testuser-AI-DRIVE-hackathons-Pacto-secto` | 64.96K |

### broodierchip@gmail.com

**2,584,957,850 tokens** (2.58B) — `/home/testuser/.claude`

userID `9fe225ab991233bf703aa663b6bf06bb04ddab782025753b968e194eeb2b0173`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 84 | 2.55B | 99% |
| subagent | 59 | 31.36M | 1% |

| Model | Total |
|---|---:|
| claude-opus-4-7 | 2.55B |
| deepseek-v4-pro | 14.16M |
| claude-sonnet-4-6 | 10.33M |
| claude-opus-4-8 | 4.85M |
| claude-haiku-4-5-20251001 | 3.31M |
| deepseek-v4-flash | 11.00K |

Active 2026-05-04 → 2026-07-02 (20 days). Busiest day 2026-05-13 at 650.12M.

| Project | Total |
|---|---:|
| `-media-testuser-AI-DRIVE-DeepSeek-work-deepseek-claude-code` | 810.30M |
| `-media-testuser-AI-DRIVE-DeepSeek-work-my-claude-seek-deepseek-bug-finder` | 320.28M |
| `-media-testuser-AI-DRIVE-AI-Shit-mining-Quest-coder-Claude-Code` | 276.20M |
| `-media-testuser-AI-DRIVE-DeepSeek-work-my-claude-seek-claude` | 220.64M |
| `-media-testuser-AI-DRIVE-DeepSeek-work-reddit` | 215.34M |
| `-media-testuser-AI-DRIVE-Contra` | 157.97M |
| `-media-testuser-AI-DRIVE-hackathons-Slack` | 132.11M |
| `-media-testuser-AI-DRIVE-hackathons-mind` | 126.49M |

### user:73ae64bf180b

**520,497,793 tokens** (520.50M) — `/home/testuser/.my-claude`

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
| `-media-testuser-AI-DRIVE-DeepSeek-work-my-claude-seek-claude` | 254.02M |
| `-media-testuser-AI-DRIVE-DeepSeek-work-my-claude-seek-deepseek-bug-finder` | 61.80M |
| `-media-testuser-AI-DRIVE-DeepSeek-work-my-claude-seek-just-agents` | 56.63M |
| `-media-testuser-AI-DRIVE-hackathons-ai-ml-hack-2026` | 54.11M |
| `-media-testuser-AI-DRIVE-VORTEX-SYSTEM-deepseek` | 35.25M |
| `-media-testuser-AI-DRIVE-DeepSeek-work` | 14.06M |
| `-media-testuser-AI-DRIVE-pip` | 13.53M |
| `-media-testuser-AI-DRIVE-DeepSeek-work-deepseek-claude-code` | 10.72M |

### unknown (Desktop_standout_clean_.claude)

**321,101,727 tokens** (321.10M) — `/home/testuser/.ai-logs-archive/claude/Desktop_standout_clean_.claude`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 420 | 321.10M | 100% |

| Model | Total |
|---|---:|
| claude-opus-4-8 | 274.07M |
| claude-fable-5 | 47.03M |

Active 2026-06-21 → 2026-07-07 (13 days). Busiest day 2026-06-29 at 151.19M.

| Project | Total |
|---|---:|
| `alt__-media-testuser-AI-DRIVE-pip` | 160.18M |
| `alt__-media-testuser-AI-DRIVE-hackathons-mantle` | 73.79M |
| `alt__-media-testuser-AI-DRIVE-pip__c9b9dba0-12af-4bbc-975b-6a4dc2996eaa__subagents` | 36.42M |
| `alt__-home-testuser` | 23.05M |
| `alt__-media-testuser-AI-DRIVE-pip__314e21c5-cdf8-4a5b-a667-2d2f2b44eb05__subagents` | 15.48M |
| `alt__-media-testuser-AI-DRIVE-hackathons-tierva` | 5.36M |
| `alt__-media-testuser-AI-DRIVE` | 5.05M |
| `alt__-home-testuser--claude-meta-teams-smoke-mixed-workdirs-t-claude` | 1.34M |

### unknown (Desktop_standout_full_.claude)

**167,829,804 tokens** (167.83M) — `/home/testuser/.ai-logs-archive/claude/Desktop_standout_full_.claude`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 805 | 167.83M | 100% |

| Model | Total |
|---|---:|
| claude-opus-4-8 | 164.53M |
| claude-haiku-4-5-20251001 | 2.23M |
| claude-fable-5 | 1.07M |

Active 2026-06-26 → 2026-07-07 (11 days). Busiest day 2026-06-27 at 100.51M.

| Project | Total |
|---|---:|
| `alt__-media-testuser-AI-DRIVE-hackathons-CodeCrusher__00e1fa7b-fc1e-48a9-b4a6-1f1eff13e305__subagents__workflows__wf_c2496bae-446` | 48.24M |
| `alt__-media-testuser-AI-DRIVE-VORTEX-SYSTEM` | 45.80M |
| `alt__-media-testuser-AI-DRIVE-VORTEX-SYSTEM__db6723e4-a658-4a0e-8977-7e7758b27be5__subagents__workflows__wf_4f331da5-c25` | 26.45M |
| `alt__-media-testuser-AI-DRIVE-VORTEX-SYSTEM__6e61c0f7-6283-4005-b056-8aacc175c5d3__subagents__workflows__wf_480a8ff7-e32` | 15.18M |
| `alt__-media-testuser-AI-DRIVE-hackathons-CodeCrusher__bcd58245-691e-490c-950b-c2bc992ebe2a__subagents__workflows__wf_30d16dcc-5ca` | 7.76M |
| `alt__-media-testuser-AI-DRIVE-hackathons-CodeCrusher` | 6.93M |
| `alt__-media-testuser-AI-DRIVE-VORTEX-SYSTEM__db6723e4-a658-4a0e-8977-7e7758b27be5__subagents__workflows__wf_1ba5b953-248` | 4.85M |
| `alt__-media-testuser-AI-DRIVE-VORTEX-SYSTEM__c2b6343a-e599-421c-8d80-0c91fff7a15d__subagents` | 3.21M |

### alexander.sorrell.it@gmail.com

**43,831,821 tokens** (43.83M) — `/home/testuser/.claude-it`

userID `53a6fc28c93264480360b0eac01b9f6ce310137e8581f22ff931dbaa003fd4fe`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 2 | 43.09M | 98% |
| subagent | 1 | 745.53K | 2% |

| Model | Total |
|---|---:|
| claude-sonnet-4-6 | 43.09M |
| claude-haiku-4-5-20251001 | 745.53K |

Active 2026-06-09 → 2026-06-10 (2 days). Busiest day 2026-06-09 at 25.89M.

| Project | Total |
|---|---:|
| `-home-testuser` | 27.54M |
| `-media-testuser-AI-DRIVE-hackathons-DeveloperWeek-New-York-2026-Hackathon` | 16.29M |

### unknown (Desktop_standout_max_.claude)

**4,669,359 tokens** (4.67M) — `/home/testuser/.ai-logs-archive/claude/Desktop_standout_max_.claude`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 805 | 4.67M | 100% |

| Model | Total |
|---|---:|
| claude-opus-4-7 | 3.71M |
| claude-opus-4-8 | 472.96K |
| claude-sonnet-4-6 | 279.59K |
| claude-fable-5 | 208.20K |

Active 2026-05-12 → 2026-07-18 (10 days). Busiest day 2026-05-24 at 2.93M.

| Project | Total |
|---|---:|
| `-workspace-p091` | 1.99M |
| `-workspace-p087` | 652.54K |
| `-workspace-p062` | 424.76K |
| `-workspace-p085` | 287.11K |
| `-workspace-p053` | 263.44K |
| `-workspace-p067` | 218.34K |
| `-workspace-p057` | 149.28K |
| `-workspace-p074` | 133.90K |

### unknown (.claude-alt)

**913,256 tokens** (913.26K) — `/home/testuser/.ai-logs-archive/claude/.claude-alt`

| Transcript | Files | Tokens | Share |
|---|---:|---:|---:|
| main | 27 | 913.26K | 100% |

| Model | Total |
|---|---:|
| claude-opus-5 | 913.26K |

Active 2026-08-08 → 2026-08-08 (1 days). Busiest day 2026-08-08 at 913.26K.

| Project | Total |
|---|---:|
| `-media-testuser-AI-DRIVE-AI-Shit-mining-Quest-coder-Claude-Code` | 913.26K |

### user:4be462f3a2f9

**141,210 tokens** (141.21K) — `/home/testuser/.claude-alt-api`

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
| `-media-testuser-AI-DRIVE-DeepSeek-work-my-claude-seek-fable` | 141.21K |

### broodierchip@gmail.com

**0 tokens** (0) — `/home/testuser/.ai-logs-archive/claude/.claude`

userID `9fe225ab991233bf703aa663b6bf06bb04ddab782025753b968e194eeb2b0173`

### unknown (.claude-alt-api)

**0 tokens** (0) — `/home/testuser/.ai-logs-archive/claude/.claude-alt-api`

### unknown (.claude-it)

**0 tokens** (0) — `/home/testuser/.ai-logs-archive/claude/.claude-it`

### unknown (.my-claude)

**0 tokens** (0) — `/home/testuser/.ai-logs-archive/claude/.my-claude`

### unknown (Desktop_standout_sandbox_.claude)

**0 tokens** (0) — `/home/testuser/.ai-logs-archive/claude/Desktop_standout_sandbox_.claude`

### unknown (claude)

**0 tokens** (0) — `/home/testuser/.ai-logs-archive/claude/claude`

### unknown (claude-alt)

**0 tokens** (0) — `/home/testuser/.ai-logs-archive/claude/claude-alt`

### unknown (claude-alt-api)

**0 tokens** (0) — `/home/testuser/.ai-logs-archive/claude/claude-alt-api`

### unknown (claude-it)

**0 tokens** (0) — `/home/testuser/.ai-logs-archive/claude/claude-it`

### unknown (my-claude)

**0 tokens** (0) — `/home/testuser/.ai-logs-archive/claude/my-claude`

### broodierchip@gmail.com

**0 tokens** (0) — `/home/testuser/Desktop/standout_clean/.claude`

userID `9fe225ab991233bf703aa663b6bf06bb04ddab782025753b968e194eeb2b0173`

### broodierchip@gmail.com

**0 tokens** (0) — `/home/testuser/Desktop/standout_full/.claude`

userID `9fe225ab991233bf703aa663b6bf06bb04ddab782025753b968e194eeb2b0173`

### broodierchip@gmail.com

**0 tokens** (0) — `/home/testuser/Desktop/standout_max/.claude`

userID `9fe225ab991233bf703aa663b6bf06bb04ddab782025753b968e194eeb2b0173`

### broodierchip@gmail.com

**0 tokens** (0) — `/home/testuser/Desktop/standout_sandbox/.claude`

userID `9fe225ab991233bf703aa663b6bf06bb04ddab782025753b968e194eeb2b0173`
