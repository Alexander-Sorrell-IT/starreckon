# Scorecard — Dell Latitude 7480 Linux

_2026-08-09T03:21:45-05:00_

**Everything checked out.**

| area | check | | detail |
|---|---|---|---|
| scan | totals.json written | ✅ |  |
| scan | sessions.json written | ✅ |  |
| scan | hardware.json written | ✅ |  |
| scan | scan is recent | ✅ | 0.6h old |
| scan | both scanners same version | ✅ | 2e512dc55519 / 2e512dc55519 |
| readers | every CLI has a row | ✅ | 8 rows |
| readers | no CLI is installed-but-silent | ✅ | none |
| readers | no reader raised | ✅ | none |
| agreement | analyze_tokens == sessions | ✅ | 2,353,868,873 vs 2,354,908,812 — 1,039,939 apart (0.04%) |
| corpus | export exists | ✅ | /home/phantom-orchestrator/token-corpus/dell-latitude-7480-linux |
| corpus | export is recent | ✅ | 2026-08-09T03:20:38-05:00 |
| corpus | profiles match the scan | ✅ | 12 exported / 12 scanned |
| corpus | redaction ran | ✅ | topic 52,190, span 6,041, path 443,044, email 17,442 |
| archive | a dated snapshot exists | ✅ | 2 snapshot(s), newest 2026-08-09T02-49-45 |

---

A check that could not run shows `—`, never `✅`. A reader that is installed and reported zero sessions is a **failure**, not a quiet success — that exact confusion hid four broken readers for months.
