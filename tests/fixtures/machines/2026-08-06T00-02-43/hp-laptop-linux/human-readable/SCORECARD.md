# Scorecard — HP Laptop Linux

_2026-08-06T00:00:32-05:00_

**Everything checked out.**

| area | check | | detail |
|---|---|---|---|
| scan | totals.json written | ✅ |  |
| scan | sessions.json written | ✅ |  |
| scan | hardware.json written | ✅ |  |
| scan | scan is recent | ✅ | 0.0h old |
| scan | both scanners same version | ✅ | a8105fb5e7a5 / a8105fb5e7a5 |
| readers | every CLI has a row | ✅ | 8 rows |
| readers | no CLI is installed-but-silent | ✅ | none |
| readers | no reader raised | ✅ | none |
| agreement | analyze_tokens == sessions | ✅ | 11,555,816,157 vs 11,555,816,157 — 0 apart (0.00%) |
| corpus | export exists | ✅ | /home/phantomcore/token-corpus/hp-laptop-linux |
| corpus | export is recent | ✅ | 2026-08-05T03:20:21-05:00 |
| corpus | profiles match the scan | ✅ | 9 exported / 9 scanned |
| corpus | redaction ran | ✅ | topic 227,122, span 1,543, path 92,878, email 2,453 |
| archive | a dated snapshot exists | ✅ | 1 snapshot(s), newest 2026-08-05T23-58-23 |

---

A check that could not run shows `—`, never `✅`. A reader that is installed and reported zero sessions is a **failure**, not a quiet success — that exact confusion hid four broken readers for months.
