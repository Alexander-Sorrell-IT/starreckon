# Multi-Machine Telemetry & Session Corpus

This directory contains raw telemetry exports, session logs, hardware manifests, and accounting rolls collected across a heterogeneous multi-machine developer fleet.

---

## 1. Context & Operational History

The files in this corpus represent logs and session captures gathered across multiple development workstations, laptops, and compute nodes running Linux and macOS (Darwin ARM64). 

Throughout the tracking period, several routine and exceptional operational events occurred:
- **Hostname & Network Transitions:** Systems transitioned across different network identities, DHCP leases, local hostnames, and domain suffixes.
- **Hardware & Profile Migrations:** Development profiles were migrated, backed up, and restored across operating systems and storage locations.
- **Multi-CLI Usage:** Sessions were recorded across multiple AI coding tools (Claude Code, Antigravity, Codex, Gemini, Copilot, Bob, and Grok).
- **Retention Sweeps & Ledger Updates:** Local transcript retention sweeps ran asynchronously, with some historical sessions expiring from live storage while remaining preserved in persistent ledgers and frozen monthly snapshots.

---

## 2. Dataset Contents

The directory structure includes:

* **Machine Directories:** Machine-specific subdirectories containing:
  * `machine-readable/sessions.json`: Raw session definitions, turn counts, duration, and token usage buckets (`input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`).
  * `machine-readable/hardware.json`: Hardware fingerprints, CPU architecture, platform strings, and system UUIDs.
  * `machine-readable/totals.json`: Aggregated totals recorded at the time of each scan.
  * `machine-readable/by_account.csv` & `by_model.csv`: Attribution breakdowns by authenticated account and model identifier.
* **Archive & Rollup Snapshots:** Historical month snapshots (`archive/months/`) and fleet-level summary files.

---

## 3. Evaluation Objective

This dataset is provided in its uncurated state. It contains both unique independent machine telemetry and overlapping datasets originating from shared hardware or profile migrations. 

The evaluation task requires analyzing the underlying hardware identifiers, session UUIDs, message hashes, and timestamps to correctly deduce:
1. True unique sessions vs. duplicate observations.
2. Canonical machine identities across rename boundaries.
3. Accurate fleet-wide and single-machine token totals without double-counting.
