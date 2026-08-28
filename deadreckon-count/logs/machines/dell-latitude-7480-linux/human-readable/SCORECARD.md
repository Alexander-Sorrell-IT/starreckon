# Scorecard — Dell Latitude 7480 Linux

_2026-08-25T08:46:20-05:00_

**3 failed, 0 to look at.**

| area | check | | detail |
|---|---|---|---|
| scan | totals.json written | ✅ |  |
| scan | sessions.json written | ✅ |  |
| scan | hardware.json written | ✅ |  |
| scan | scan is recent | ✅ | 6.9h old |
| scan | both scanners same version | ✅ | c8bf2d838dde / c8bf2d838dde |
| readers | every CLI has a row | ✅ | 12 rows |
| readers | no CLI is installed-but-silent | ❌ | copilot-chat |
| readers | no reader raised | ✅ | none |
| agreement | analyze_tokens == sessions | ❌ | 2,225,228,697 vs 4,550,924,207 — 2,325,695,510 apart (51.10%) |
| corpus | export exists | ✅ | /home/phantom-orchestrator/deadreckon-record/dell-latitude-7480-linux |
| corpus | export is recent | ✅ | 2026-08-24T15:19:06-05:00 |
| corpus | profiles match the scan | ❌ | 12 exported / 10 scanned |
| corpus | redaction ran | ✅ | topic 59,374, span 5,861, path 499,573, email 13,596 |
| archive | a dated snapshot exists | ✅ | 3 snapshot(s), newest LEDGER.md |

---

A check that could not run shows `—`, never `✅`. A reader that is installed and reported zero sessions is a **failure**, not a quiet success — that exact confusion hid four broken readers for months.
