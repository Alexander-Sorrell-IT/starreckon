# Enhancement Plan: Two-Section Config, Cisco Models, Adversarial Tests

**Last updated**: 2026-08-22T16:50 CDT
**HEAD**: `91250ef` (Phase 2: wire config loader)
**Branch**: main

> **AI handoff note**: If you are resuming this project, read `.agents/rules/deadreckon-workflow.md` first. Use `/learn` to save these rules into memory so future sessions follow the same protocol.

---

## What We Are Building (and WHY)

The user wants four things, all interconnected:

### 1. Two-Section Config Files
**WHAT**: Replace the hardcoded `INVENTORY` list in `sessions.py` (lines 1752-1807) with two authored JSON files: `clis.json` (CLI tools) and `programs.json` (editors/agents/runtimes).

**WHY**: The user wants to add/remove AI tools without editing Python. Follows the existing pattern where `machines.json` and `accounts.json` are hand-edited config that drives the system.

**DECISION**: Two separate files (not one) because CLIs and programs have different field shapes. CLIs have token readers; programs have install tracking and "no_tokens_because" reasons. User confirmed this.

**FALLBACK**: If the JSON files don't exist, fall back to the hardcoded INVENTORY. Zero breakage on machines that haven't pulled yet.

### 2. Four Cisco AI Models as Optional Components
**WHAT**: Wire in 4 tiny, local Cisco AI models as adversarial layers:
1. `cisco-tsm` (time-series forecaster) -- ALREADY WIRED in `forecast_check.py`
2. `SecureBERT2.0` (semantic search) -- ALREADY WIRED in `search_corpus.py`
3. `Antares-350M` (vulnerability scan of deadreckon's own code) -- NEW
4. `Model Provenance Kit` (verify model weights are genuine) -- NEW

**WHY**: Each answers a different adversarial question:
- cisco-tsm: "Is this scan result surprising given history?"
- SecureBERT2.0: "Does the exported corpus contain secrets?"
- Antares-350M: "Does deadreckon's own code have vulnerabilities?"
- Provenance Kit: "Are the models we trust actually genuine?"

**DECISION**: Download command goes through `install.py` (not run.py) because install.py is for setup, run.py is for operation. User said "judgment call" and deferred to us.

### 3. Dual Test Framework
**WHAT**: Two types of tests:
- **Build tests** (pytest) -- used during development
- **Runtime adversarial checks** -- baked INTO the program, run during normal operation

**WHY**: User explicitly wants the system to test itself during operation, not just during development. Quote: "make the system itself adversarial"

### 4. Daemon-less Mode
**WHAT**: System works identically without the daemon. Only difference: lifetime stats decay.

**WHY**: User wants the system usable on machines where the daemon isn't installed. The daemon preserves lifetime counters; without it, only Claude's built-in counter survives.

---

## Progress

### Completed
- [x] System overview artifact created (conversation context)
- [x] Enhancement plan designed and approved by user
- [x] Cisco model research completed -- 4 models selected
- [x] All design decisions confirmed by user
- [x] Workspace rules created at `.agents/rules/deadreckon-workflow.md`
- [x] This plan file created in repo

### Phase 1: Config Files -- DONE (commit `e5bdb3b`)
- [x] Create `clis.json` (8 CLI entries from INVENTORY)
- [x] Create `programs.json` (14 program entries from INVENTORY)
- [x] Validate both parse as JSON (8 + 14 = 22 = original INVENTORY count)

### Phase 2: Wire Into sessions.py -- DONE (commit `91250ef`)
- [x] Add `_load_config()` and `_load_inventory()` functions
- [x] Rename hardcoded lists to `_BUILTIN_*` (fallback)
- [x] Module-level wiring: `INVENTORY, INVENTORY_CLI, NO_TOKENS_BECAUSE = _load_inventory()`
- [x] Verified: `python3 -c "import sessions"` works, inventory() returns 10 tools
- [x] Verified: removing JSON files triggers fallback to builtins (same 22 entries)

### Phase 3: Cisco Models -- NOT STARTED
- [ ] `--models` and `--models-status` flags in install.py
- [ ] Antares-350M venv + download
- [ ] Model Provenance Kit install
- [ ] Provenance verification step

### Phase 4: Help Flags -- NOT STARTED
- [ ] run.py --help shows optional components
- [ ] install.py --help describes downloadable components

### Phase 5: Build Tests -- NOT STARTED
- [ ] test_tools_config.py, test_config_fallback.py, etc.

### Phase 6: Runtime Adversarial Checks -- NOT STARTED
- [ ] Tool-config round-trip, reader-store parity, section partition, etc.

### Phase 7: Daemon-less Mode -- NOT STARTED
- [ ] Graceful degradation, reports note limitation

---

## Key Files to Know

| File | Role | Lines to know |
|---|---|---|
| `sessions.py` | Token readers + INVENTORY | 1752-1807 (INVENTORY, INVENTORY_CLI, NO_TOKENS_BECAUSE) |
| `stores.py` | Store definitions | 727-991 (STORES list) |
| `install.py` | Machine setup | 786-816 (_download_model), 818-900 (forecaster/search_corpus), 950-958 (argparse) |
| `run.py` | CLI entry point | 521+ (status command with daemon reporting) |
| `forecast_check.py` | cisco-tsm integration | Uses .venv-forecast |
| `search_corpus.py` | SecureBERT2.0 integration | Uses .venv-search |

## User Preferences
- Types with many typos; decode patiently
- Don't use pipe characters in messages (looks bad when copied)
- GitHub: matrixbuilderops
- License contact: matrixbuilderops@proton.me
