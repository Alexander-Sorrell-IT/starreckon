# FINISH PLAN: Starreckon Parity with Deadreckon-count

## Current State

**deadreckon-count (Python)** - Reference implementation
- ✅ 10 CLIs defined in `clis.json`
- ✅ 15 programs/editors/agents defined in `programs.json`
- ✅ Dynamic discovery engine (`discover.py`) scans by SHAPE not name
- ✅ OS-aware path resolution (Linux, macOS, Windows)
- ✅ Full adversarial test suite (27 test modules)
- ✅ Fleet-wide token tracking with account attribution
- ✅ Reports: by-computer, by-account, by-company, lifetime
- ✅ Archive management with retention guard
- ✅ Machine-readable JSON + human-readable Markdown

**starreckon (Node.js)** - Primary product with visualizations
- ✅ 16 sources defined in `spec/sources.json`
- ❌ No dynamic discovery engine
- ❌ Missing CLI readers: jules, grok-cli (@vibe-kit)
- ❌ Missing program readers: cursor, windsurf, zed, aider, continue, cline, roo-code, ollama, kilocode, copilot-chat variants
- ❌ Limited adversarial testing
- ❌ No OS-aware discovery (hardcoded paths)
- ⚠️ Token depth matches for common tools, but missing account/provider attribution

## Critical Gaps to Close

### 1. Dynamic Discovery Engine (P0)
**What deadreckon has:** `discover.py` walks home directory to depth 4, finds conversational content by SHAPE (usage/token fields in JSON, session tables in SQLite), classifies as KNOWN/UNKNOWN/AMBIGUOUS.

**What starreckon needs:** `src/discovery.mjs` that:
- Reads `spec/clis.json` and `spec/programs.json` (split like deadreckon)
- Scans $PATH for CLI binaries from clis.json
- Walks home directory for program stores by shape
- Detects OS (linux/darwin/win32) and uses correct base paths
- Outputs: KNOWN (covered by reader), UNKNOWN (found but no reader), AMBIGUOUS (unreadable)

**Files to create:**
- `spec/clis.json` - Extract CLI entries from sources.json
- `spec/programs.json` - Extract program/editor/agent entries from sources.json
- `src/discovery.mjs` - Port discover.py logic to Node.js
- `src/os-paths.mjs` - OS-aware path resolution

### 2. Missing Tool Readers (P0)
**CLIs to add:**
- `jules` - Google's cloud agent (no local tokens, track presence only)
- `grok-cli` - @vibe-kit variant (records no usage)

**Programs to add:**
- `cursor` - Editor (usage not located on disk)
- `windsurf` - Editor (usage not located on disk)
- `zed` - Editor (hosts agents, spends no tokens itself)
- `aider` - Agent (usage not located on disk)
- `continue` - Extension (usage not located on disk)
- `cline` - VS Code extension (usage not located on disk)
- `roo-code` - VS Code extension (usage not located on disk)
- `ollama` - Local runtime (no billing, models run locally)
- `kilocode` - Already in sources.json but verify reader exists
- `copilot-chat` - Already in sources.json but verify reader handles all 4 store variants

### 3. Folder Structure Alignment (P1)
**Current starreckon:** Flat structure, logs/reports at root
**Target structure (match deadreckon):**
```
<user-workspace>/starreckon/
├── logs/
│   ├── incoming/      # New sessions to process
│   └── archive/       # Processed sessions by date
├── reports/
│   ├── human/         # Markdown reports
│   │   ├── by-computer/
│   │   ├── by-account/
│   │   └── lifetime/
│   └── machine/       # JSON reports
│       ├── by-computer/
│       ├── by-account/
│       └── lifetime/
├── data/
│   ├── stars/         # Skill snapshots
│   │   ├── lifetime/
│   │   └── monthly/
│   └── fleet/         # Fleet-wide aggregates
│       ├── lifetime/
│       └── monthly/
└── adversarial/       # Test fixtures
```

**Config location:** `.starreckon/config.json` (hidden, like deadreckon's `.deadreckon/`)

### 4. Token Depth Parity (P1)
**deadreckon tracks per session:**
- input_tokens
- cache_creation_input_tokens
- cache_read_input_tokens
- output_tokens
- account_id (hashed)
- provider (anthropic, openai, google, etc.)
- project/path attribution
- timestamp

**starreckon currently tracks:**
- Same 4 token fields ✅
- ❌ Account attribution (pseudonymized)
- ❌ Provider detection
- ❌ Per-project attribution in reports

**Action:** Add account hashing, provider detection, project attribution to match deadreckon's depth.

### 5. Adversarial Test Suite (P2)
**deadreckon has 27 test modules covering:**
- adv_forged_stamp - Timestamp manipulation
- adv_orphan_merge - Session merge attacks
- adv_platform_behaviour - OS-specific attacks
- adv_vendor_and_identical - Vendor format attacks
- adv_statscache_floor - Stats cache manipulation
- adv_gate_git_blind - Gate certification bypass
- adv_profile_claim - Profile claim attacks
- adv_archive_dirstore - Archive directory attacks
- adv_collation - Report collation attacks
- adv_copilot_ids - Copilot ID spoofing
- adv_documents - Document injection
- adv_export_walk - Export traversal attacks
- adv_install_folder - Install folder injection
- adv_published_gate - Published gate attacks
- adv_reports - Report manipulation
- adv_store_locations - Store location attacks
- adv_suite_integrity - Suite integrity checks

**starreckon has basic tests for:**
- Token count validation
- JSON resilience
- Malformed data handling
- Model ID sanitization
- Unicode attacks
- Directory permissions

**Action:** Port key adversarial tests from Python to Node.js, focusing on:
- Timestamp forgery
- Orphan merge attacks
- Stats cache manipulation
- Gate certification tests
- Archive directory attacks

### 6. Report Output Parity (P2)
**deadreckon outputs:**
- `machine-readable/lifetime.json` - Fleet totals
- `machine-readable/by-computer/*.json` - Per-machine breakdown
- `machine-readable/by-account/*.json` - Per-account breakdown
- `machine-readable/months/YYYY-MM.json` - Monthly snapshots
- `human-readable/*.md` - Markdown reports

**starreckon outputs:**
- HTML stats pages
- SVG skill cards
- Terminal visualization

**Action:** Add JSON report generation matching deadreckon's schema for direct comparison, keep HTML/SVG as value-add.

## Migration Steps

### Phase 1: Spec Files (Day 1)
1. Split `spec/sources.json` into:
   - `spec/clis.json` - CLI-only entries (name, binary, paths, reader)
   - `spec/programs.json` - Programs/editors/agents (name, kind, paths, binary, reader)
2. Verify all 25 tools from deadreckon are represented
3. Add missing entries: jules, grok-cli, cursor, windsurf, zed, aider, continue, cline, roo-code, ollama

### Phase 2: Discovery Engine (Day 2-3)
1. Create `src/os-paths.mjs` - OS detection and base path resolution
2. Create `src/discovery.mjs` - Port discover.py logic:
   - Walk home to depth 4
   - Detect conversational content by shape
   - Classify KNOWN/UNKNOWN/AMBIGUOUS
   - Attribute to tool root (not subdirectories)
3. Integrate discovery into CLI flow (run before scan)
4. Add `--discovery-only` flag for standalone use

### Phase 3: Missing Readers (Day 3-4)
1. Add readers for missing CLIs (jules, grok-cli) - may be presence-only
2. Add readers for missing programs (cursor, windsurf, zed, aider, continue, cline, roo-code, ollama)
3. Verify existing readers handle all store variants (copilot-chat 4 variants, kilocode insiders)
4. Update `spec/sources.json` with `counted_by` field for each tool

### Phase 4: Folder Structure (Day 4)
1. Update CLI to create `starreckon/` folder in user's workspace
2. Create subfolders: logs/incoming, logs/archive, reports/human, reports/machine, data/stars, data/fleet
3. Move config to `.starreckon/config.json`
4. Update archive logic to match deadreckon's date-based structure

### Phase 5: Token Depth (Day 5)
1. Add account hashing (same algorithm as deadreckon)
2. Add provider detection from model IDs
3. Add per-project attribution in reports
4. Verify token field extraction matches deadreckon exactly

### Phase 6: Adversarial Tests (Day 6-7)
1. Port key adversarial tests to Node.js
2. Create `adversarial/` fixture directory
3. Integrate into test suite
4. Run both tools against same fixtures, compare results

### Phase 7: Report Parity (Day 7-8)
1. Add JSON report generation matching deadreckon schema
2. Create `reports/machine/lifetime.json`, `by-computer/`, `by-account/`
3. Add monthly snapshot generation
4. Keep HTML/SVG as additional output formats

## Success Criteria

✅ **Tool Coverage:** starreckon detects same 25 tools as deadreckon
✅ **Discovery:** Both find same KNOWN/UNKNOWN/AMBIGUOUS stores
✅ **Token Counts:** Identical totals when run on same corpus (± rounding)
✅ **Folder Structure:** `starreckon/` mirrors `deadreckon-count/` layout
✅ **Adversarial:** Both pass same attack scenarios
✅ **Reports:** JSON schemas match for automated comparison
✅ **OS Support:** Both work identically on Linux, macOS, Windows

## Long-term Vision

Once parity is achieved:
- Run both tools on same corpus weekly
- Automated diff of token counts (any divergence = bug)
- Use deadreckon as "red team" to validate starreckon
- When 100% parity confirmed across 10+ runs, consider deprecating Python version
- Keep Python as reference implementation and adversarial oracle

## Questions for User

1. **clis.json vs programs.json split** - Confirm you want separate files like deadreckon, or keep single sources.json?
2. **Discovery frequency** - Run discovery every scan, or only on `--discover` flag?
3. **Report priority** - JSON parity first, or keep focus on HTML/SVG visualizations?
4. **Test coverage** - Port all 27 adversarial tests, or prioritize top 10?
5. **Windows support** - Deadreckon has Windows paths in spec; should starreckon prioritize Linux/macOS first?
