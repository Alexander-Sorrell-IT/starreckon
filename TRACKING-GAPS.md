# Tracking Gaps Between deadreckon-count and starreckon

## Summary
Both programs should support the same CLIs/programs with the same token counting depth. Currently deadreckon-count has broader coverage.

## CLIs Missing in starreckon (present in deadreckon-count/clis.json)

| CLI | Status in deadreckon | Status in starreckon | Gap |
|-----|---------------------|---------------------|-----|
| **Jules CLI** | Listed (no reader - cloud agent) | NOT DECLARED | starreckon missing declaration |
| **grok-cli (@vibe-kit)** | Listed (records no usage) | NOT DECLARED | starreckon missing declaration |

## Programs Missing in starreckon (present in deadreckon-count/programs.json)

| Program | Kind | Reader in deadreckon | Status in starreckon | Gap |
|---------|------|---------------------|---------------------|-----|
| **VS Code** | editor | N/A (hosts agents) | NOT DECLARED | starreckon missing declaration |
| **VS Code Insiders** | editor | N/A (hosts agents) | NOT DECLARED | starreckon missing declaration |
| **VSCodium** | editor | N/A (hosts agents) | NOT DECLARED | starreckon missing declaration |
| **Cursor** | editor | N/A (usage not located) | DECLARED but no reader | Both have no reader ✓ |
| **Windsurf** | editor | N/A (usage not located) | NOT DECLARED | starreckon missing declaration |
| **Zed** | editor | N/A (hosts agents) | NOT DECLARED | starreckon missing declaration |
| **Kilo Code (VS Code)** | agent | kilocode | DECLARED ✓ | Covered ✓ |
| **Kilo Code (Insiders)** | agent | kilocode | DECLARED ✓ | Covered ✓ |
| **Cline** | agent | N/A (usage not located) | NOT DECLARED | starreckon missing declaration |
| **Roo Code** | agent | N/A (usage not located) | NOT DECLARED | starreckon missing declaration |
| **Continue** | agent | N/A (usage not located) | NOT DECLARED | starreckon missing declaration |
| **Aider** | agent | N/A (usage not located) | NOT DECLARED | starreckon missing declaration |
| **Ollama** | runtime | N/A (local, not billed) | NOT DECLARED | starreckon missing declaration |
| **LM Studio** | app | lmstudio | DECLARED ✓ | Covered ✓ |
| **GitHub Copilot Chat** | agent | copilot-chat | DECLARED ✓ | Covered ✓ |

## Token Counting Depth Comparison

Both programs track the same 4 token fields when available:
- `input_tokens`
- `cache_creation_input_tokens`  
- `cache_read_input_tokens`
- `output_tokens`

**deadreckon-count additional tracking:**
- Per-account attribution
- Per-provider detection (anthropic, openai, google, etc.)
- Per-project attribution
- Billing status tracking
- Machine/computer identification

**starreckon additional tracking:**
- Skill "star" visualization
- Monthly snapshots for longitudinal tracking
- Privacy redaction (pseudonymization)
- OS-level sandboxing proofs

## Actions Needed for starreckon

1. Add declarations to `spec/sources.json` for:
   - Jules CLI
   - grok-cli (@vibe-kit)
   - VS Code, VS Code Insiders, VSCodium
   - Windsurf, Zed
   - Cline, Roo Code, Continue, Aider
   - Ollama

2. Verify readers exist in `src/readers.mjs` for all declared sources

3. Ensure `counted_by` field accurately reflects which program can count each source

## Files to Reference

- deadreckon-count CLIs: `/workspace/deadreckon-count/clis.json`
- deadreckon-count programs: `/workspace/deadreckon-count/programs.json`
- starreckon sources: `/workspace/spec/sources.json`
- starreckon readers: `/workspace/src/readers.mjs`
- starreckon sources command: `/workspace/src/sources.mjs`
