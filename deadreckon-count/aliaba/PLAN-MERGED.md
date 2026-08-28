# The one plan — merged, ordered, and handed off in place

Supersedes nothing; **sequences three lists that were all real**:

| source | what it is | items |
|---|---|---|
| [PLAN.md](PLAN.md) | plan of record, 45 adversarial findings, 2026-08-09 | 31 |
| [FIX-PLAN-2026-08-21.md](FIX-PLAN-2026-08-21.md) | sweep during the dell-latitude rescan | 8 fixed, 7 open |
| Antigravity `todo.md` | config-driven registry, models, tests, daemon-less | 41 |

## How to use this file

Work **top to bottom**. Tick a box the moment it is proved, not when it is
written. Each item names the check that proves it. If you are the next agent
picking this up, find the first unticked box — everything above it is done and
verified, everything below it is untouched.

**Ordering rule.** A test that asserts a guarantee the code does not yet have
must not be written before the guarantee. A feature that reads a number must
not be built before the number is right. That is the only reason the stages sit
in this order — it is dependency, not importance.

---

## DONE — 2026-08-21/22 (Claude, commits c0a7d97 · 44b03dc · c07e8ac · a813c81)

- [x] Gate no longer aborts the scanning machine's writes (`update.py`)
- [x] `machine_floor` no longer discards a counter — 25,359,992,209 recovered
- [x] Every session row records `source`, the reader that produced it
- [x] Gate subtracts orphans before comparing — both drift failures cleared
- [x] `fun_stats` per-machine CLI table no longer truncated at `[:8]`
- [x] Orphan-only accounts reach the floor — 523,372,063 recovered
- [x] `run.py` six shadowed duplicate definitions removed (122 dead lines)
- [x] `archive/` + `testing-archive/` by year/month/week/day, ledger per level
- [x] `retire --wipe`, verified per repo before it deletes

Proof: `check_consistency` **68 checks, 0 failed** (was 3 failed) ·
`test_scanner.py` **91 checks, 0 failed** · floor this machine 5.87B → 31.76B.

---

## STAGE 1 — irreversible loss. Nothing else runs first. (PLAN.md P0)

**STAGE 1 COMPLETE 2026-08-22.** All five P0 items closed or verified fixed.

- [x] **1.1** ~~Move the pre-rule credential files out of the hard-link archive.~~
      **DONE 2026-08-22.** 6 files moved to
      `~/.ai-logs-quarantine/2026-08-22T14-25-47/` with a `WHY.md`. Every one
      had `nlink>1` at the time of the move, asserted before touching it, so
      the live original still held the data and nothing was destroyed. Kept
      rather than deleted so the removal is reversible.
      **Proved:** 0 credential-shaped files remain under `~/.ai-logs-archive`;
      all five live credentials present at full size; `--check` still reports
      them REFUSED and the "ALREADY in the archive at the SAME INODE" line is
      gone.
      *(original text below)*
      `oauth_creds.json`, `auth.json`, `google_accounts.json` under
      `~/.ai-logs-archive/other/` are `nlink=2` — the same inode as the live
      credential. The guard REFUSES new ones; these predate the rule and it
      says so: *"nothing here deletes them — move them out yourself."*
      **Proof:** no file under `~/.ai-logs-archive` has `nlink>1` with a live
      credential; `retention_guard.py --check` still reports them REFUSED.
- [x] **1.2** ~~Settle PLAN.md P0.2 — whether 451 transcripts exist in no copy.~~
      **CLOSED 2026-08-22 on this machine.** The flat glob is gone from
      `export_corpus.py` — the fourth and last copy of it. Measured, not
      assumed:

          live claude transcripts   16,585 recursive · 16,560 flat · 25 nested
          exported                  70,375 (superset: includes the hard-link
                                    archive of transcripts already deleted)
          nested in the export      300 subagent + 15 workflow

      The nested transcripts the flat glob could not see are captured.
      **Caveat, tracked as 6.2:** that is the LOCAL export. The offsite release
      asset for this machine is still 2026-08-09 — 16,516 files, no nested
      ones. The data is safe in two places on this disk; it is not yet safe
      off it.
- [x] **1.3** ~~PLAN.md P0.4 — a dead belt reports `retention: ok`.~~
      **VERIFIED FIXED 2026-08-22 by breaking it**, not by reading the comment.
      Pointed `ARCHIVE` at a `/dev/shm` directory (dev 43 against home's dev
      51, a real mount boundary) and ran `link_tree(apply=True)`:

          link_tree returned : (0, 0, 'DIFFERENT FILESYSTEM — hard links impossible here')
          FAILED_LINKS       : ['belt-test: DIFFERENT FILESYSTEM — hard links impossible here']

      The branch now goes through `FAILED_LINKS` instead of returning before
      it. A dead belt is recorded.

      **P0.3 also closed** — `_archive_name()` decides "already archived" by
      inode, not path existence. **P0.5 closed** — daemon `active`,
      `Linger=yes`, `--verify-boot` PASS, and unprotected live transcripts are
      down from the 44 P0.5 measured to 1 (this session's own transcript,
      still being written; the guard links it on the next tick).

## STAGE 2 — the ledger guarantee (PLAN.md P1)

**2.2 and 2.3 were already fixed upstream. 2.1 is open and needs a schema
change — read its note before starting.**

Before Antigravity Phase 5, because `test_ledger_monotonicity` asserts exactly
what P1.1 says is currently inverted. **If that test passes on today's code,
the test is wrong, not the ledger.**

- [ ] **2.1** P1.1 — a deletion must not lower the lifetime.
      **REPRODUCED 2026-08-22, and it is NOT a one-line fix.** Read this before
      attempting it.

      The reproduction is real. Driving the module: rows `S1@v1=1,000,000,000`
      then `S1@v2=10,000,000` yields a lifetime of **10,000,000**.

      **The obvious fix is wrong.** "Only the code running now may lower a
      session" (compare `r["scanner"]` against `sessions.scanner_version()`,
      a sha256 of the code, so a forged string can only raise) blocks the
      forgery *and* breaks two tests that encode a deliberate property:

          FAIL  a corrected scanner DOES lower it, for what it can still see
          FAIL  re-running the corrected scanner does not restore the old figure

      Those tests are right. A correction made by ANY version must be able to
      lower the sessions that version still saw — the rule already separates
      deletion from correction, because a deleted session gets **no new row**
      at all and its high-water mark stands. Tried, measured (+22,296,345 on
      the real ledger, 0.09%), reverted; suite back to 91/0.

      **What the fix actually needs.** A *partial* deletion is a session the
      newer scanner still sees but reads less of, which is byte-identical in
      the ledger to a recount. No rule over `(version, total)` can separate
      them, because the distinguishing fact is not in the row. The scanner must
      record EVIDENCE OF COMPLETENESS at observation time — transcript size, or
      a content hash — so a shrunken source is distinguishable from a changed
      counting rule. That is a `sessions.py`/`token_ledger.py` schema change,
      not a tweak to `lifetime()`.
- [x] **2.2** ~~P1.2 — no report ever opens the ledger.~~ **ALREADY FIXED.**
      `monthly.py:134 fold_ledger()` adds what the append-only ledger holds
      BEYOND the scan, per CLI per machine, as a difference rather than a sum.
      16 modules now reference `token_ledger`. Verified by reading, not by
      the commit message.
- [x] **2.3** ~~P1.3 — 4.07 B dropped for want of a start date.~~
      **ALREADY FIXED.** `monthly.py` carries an `undated` accumulator and
      `LIFETIME.md` publishes the section:

          ## Undated sessions
          7,670,972,451 tokens across 146 session(s) have no start timestamp
          and cannot be placed in any month ... included in the headline token
          figure above; the session, turn and duration counts cover dated
          sessions only.

      Absent no longer looks like zero. The gate still WARNs about the split,
      which is the note doing its job, not a defect.

## STAGE 3 — the gate reads what it certifies (PLAN.md P3)

**STAGE 3 COMPLETE — all three already fixed upstream, each verified here.**

- [x] **3.1** ~~P3.1 — the gate compares `totals.json` to `totals.json`.~~
      **ALREADY FIXED.** P3.1's own test was "a grep for
      `ALL-COMPUTERS|BY-COMPUTER|README|STATS|LIFETIME` returns nothing." It
      now returns **74**, and the gate opens `README.md`, `BY-COMPUTER.md` and
      `STATS.md` through `text()` at lines 443, 523, 622. This is what caught
      the `fun_stats` `[:8]` truncation today.
- [x] **3.2** ~~P3.2 — three checks put the identical expression on both sides.~~
      **CLOSED, audited by AST rather than grep**: every `chk()`/`want()` call
      in `check_consistency.py` was parsed and its two sides compared as
      source text. **0 checks have the same expression on both sides.**
- [x] **3.3** ~~P3.3 — `scanner_version` is forgeable, and forging it switches
      off the retire exemption.~~ **ALREADY FIXED, with two defences.**
      `sessions.scanner_version()` is recomputed from source and compared to
      the stamp — *"which a stamped file cannot forge without matching it."*
      And the closed-day audit no longer trusts the version field at all: it
      uses the SESSION INVENTORY, because *"re-reading the same transcripts
      through new counting rules cannot reduce how many sessions were FOUND;
      fewer tokens and fewer sessions together is a loss wearing a recount's
      clothes."*
      Verified live: `totals.json`, `sessions.json` and
      `sessions.scanner_version()` all read `7e744606de07`.

      **Note for item 2.1:** that inventory trick is the missing discriminator
      the ledger needs. The gate already tells a deletion from a recount by
      counting sessions, not by comparing versions. The ledger can do the same.

## STAGE 4 — the master file (Antigravity Phases 1–2)

The owner's own requirement: *adding a CLI should be one edit in one place.*
Path discovery is already OS-first and derived (`platform_detect.family()` →
`stores.tool_forms()`); this closes the half that is not.

- [ ] **4.1** `clis.json` from `INVENTORY` (cli kind), with `_comment` blocks
- [ ] **4.2** `programs.json` from `INVENTORY` (editor/agent/runtime kinds)
- [ ] **4.3** `load_clis()` / `load_programs()` with graceful fallback to the
      hardcoded `INVENTORY` when the files are absent
- [ ] **4.4** `detect()`, `inventory()`, `probe_uncountable()` read the loader;
      `NO_TOKENS_BECAUSE` becomes a config field
- [ ] **4.5** One registry entry per tool declares BOTH where it lives and which
      reader parses it, so a store with no parser is impossible rather than
      something `NOT COVERED` catches afterwards
      **Proof:** `test_scanner.py` and the gate stay green; deleting both JSON
      files changes no number.

## STAGE 5 — runtime adversarial checks (Antigravity Phase 6)

The strongest part of any of the three lists. Same instinct as PLAN.md's rule:
*a number is real when something that could have contradicted it did not.*

- [ ] **5.1** Tool-config round-trip in `run.py update`
- [ ] **5.2** Reader-store parity in `check_consistency.py`
- [ ] **5.3** Section partition: CLI tokens + Program tokens = grand total
      *(this class of check would have caught the orphans problem alone)*
- [ ] **5.4** Inventory-vs-scan: an installed tool must have non-empty store state
- [ ] **5.5** Daemon heartbeat: hard-link count never decreases,
      `cleanupPeriodDays` never lowered
- [ ] **5.6** Ledger floor: session totals ≥ ledger floor after every scan
- [ ] **5.7** Config drift: hash config at scan start, re-hash at end

## STAGE 6 — chores (FIX-PLAN-2026-08-21)

- [x] **6.1** ~~README claims `run.py update` exports transcripts.~~ **FIXED.**
      Corrected the runbook and made `update` say the step it does not do:
      it now prints "transcripts are NOT exported by this command" with the
      two commands that do it. Calling `export_corpus.py` from `update` was
      rejected — the export takes ~55 min here and `update` is ~2 min.
- [x] **6.2** ~~`export_corpus.py --exclude-profile`.~~ **BUILT.** Repeatable
      flag; the default is DERIVED, not hardcoded — every machine folder in the
      repo whose `.machine-id` hostname is not this host contributes its name,
      so a machine added later is covered without touching the code. Simulated
      against the real paths: **8 foreign profiles skipped, 12 kept**, and this
      machine's own pre-clone correctly KEPT because `mine` is resolved by
      hostname. Pass `--exclude-profile ''` to export everything.
      **Still to do:** re-export and ship, so the release asset stops being
      2026-08-09.
- [x] **6.3** ~~Daemon runs a copy with nothing enforcing it matches the repo.~~
      **FIXED.** `run.py status` now hashes both and prints "guard copy matches
      the repo" or "DIFFERS — the daemon is running stale code" with the `cp`
      to fix it. Left `ExecStart` on the copy deliberately: pointing it at the
      repo would have the daemon execute half-saved edits mid-session.
- [x] **6.4** ~~Surface the daemon's failure count where a human looks.~~
      **FIXED.** `run.py status` reads the journal and prints
      "28 archive failure(s) logged in the last 7 days" plus the newest line,
      beside `daemon active, linger=yes`.
- [x] **6.5** ~~`.playwright-mcp` is `NOT COVERED`.~~ **RECORDED AS SKIPPED,
      with the reason.** It is 41 MB of 200 `.yml` accessibility snapshots, 81
      `console-<ISO>.log` files and 76 `.png` screenshots — **not one `.json`
      or `.jsonl`**. Session-SHAPED, holds no usage record. Added to
      `DISCOVER_SKIP` on the grounds the discovery loop's own comment gives:
      an alarm that is wrong every time is one people stop reading, which costs
      the real one its meaning. All three of the README's "something went
      wrong" lines are now clean.
- [x] **6.6** ~~Stale `token-usage` references survive the rename.~~ **FIXED
      the one that was real.** `Documentation=` in the installed unit pointed
      at `~/token-usage/`; repointed and `daemon-reload`ed, daemon still
      active. The hits in `migrate_rename.py` / `test_migrate_rename.py` are
      INTENTIONAL — that is the tool that maps the old name to the new, and it
      says so: *"harmless in Documentation=, silent and dangerous"* elsewhere.
      Left alone.
- [ ] **6.7** Rerun `update` on hp-laptop-linux, asus, dell-inspiron — scanner
      version parity, and asus/dell-inspiron regain their scorecards

## STAGE 7 — build tests (Antigravity Phase 5)

After Stage 2, so the ledger test asserts a guarantee that exists.

- [ ] **7.1** `test_tools_config.py` — schema validation
- [ ] **7.2** `test_config_fallback.py` — fallback when files missing
- [ ] **7.3** `test_inventory_completeness.py` — every config tool has a Store
- [ ] **7.4** `test_daemon_lifecycle.py` — start/stop/verify-boot
- [ ] **7.5** `test_ledger_monotonicity.py` — never decreases after deletion

## STAGE 8 — components and ergonomics (Antigravity Phases 3, 4, 7)

- [ ] **8.1** `install.py --models` / `--models-status` covering all four:
      `cisco-ai/cisco-time-series-model-1.0`,
      `cisco-ai/SecureBERT2.0-biencoder`, `cisco-ai/SecureBERT2.0-cross_encoder`
      (already wired) plus `fdtn-ai/antares-350m` (new, own venv).
      Note the namespaces differ — `cisco-ai` vs `fdtn-ai`.
- [ ] **8.2** Model Provenance Kit + a verification step after download
- [ ] **8.3** `models.json` tracking model status; all four optional
- [ ] **8.4** `run.py --help` shows optional components: daemon, models, config
      files (custom/default). Fast checks — file existence, not model loading
- [ ] **8.5** `install.py --help` describes every downloadable component
- [ ] **8.6** Daemon-less mode: runs identically, reports note that lifetime
      stats decay without it, `--help` says "not running" rather than erroring

## STAGE 9 — the rest of the plan of record (PLAN.md P2, P4, P5)

- [ ] **9.1** P2 — republish the numbers, once the gate can catch a wrong one
- [ ] **9.2** P4 — machines writing into each other's folders
- [ ] **9.3** P5 — `claims.py`, `redteam.py`, no-stale-derived, retire-as-test

---

## Definition of done

From PLAN.md, unchanged, because it is the right one:

1. Both red teams re-run against the fixed code and cannot falsify any of the
   ten claims.
2. The clean-start run is identical in correctness to the populated run.
3. The fleet reconciles — every machine on one scanner version, `count_corpus`
   reports every CLI at 0.00% against the corpus.

**A number is not real because it is consistent. It is real when something that
could have contradicted it did not.**
