# Scorecard — MacBook Air M1

_2026-08-09T03:41:05-05:00_

**1 failed, 0 to look at.**

| area | check | | detail |
|---|---|---|---|
| scan | totals.json written | ✅ |  |
| scan | sessions.json written | ✅ |  |
| scan | hardware.json written | ✅ |  |
| scan | scan is recent | ✅ | 1.1h old |
| scan | both scanners same version | ✅ | 2e512dc55519 / 2e512dc55519 |
| readers | every CLI has a row | ✅ | 8 rows |
| readers | no CLI is installed-but-silent | ✅ | none |
| readers | no reader raised | ✅ | none |
| agreement | analyze_tokens == sessions | ✅ | 13,955,323,225 vs 13,986,083,796 — 30,760,571 apart (0.22%) |
| corpus | export exists | ✅ | /Users/testuser/token-corpus/macbook-air-m1 |
| corpus | export is recent | ✅ | 2026-08-09T03:38:04-05:00 |
| corpus | profiles match the scan | ❌ | 8 exported / 10 scanned |
| corpus | redaction ran | ✅ | topic 209,000, span 16,710, path 704,209, email 13,853 |
| archive | a dated snapshot exists | ✅ | 1 snapshot(s), newest 2026-08-09T02-49-00 |

---

A check that could not run shows `—`, never `✅`. A reader that is installed and reported zero sessions is a **failure**, not a quiet success — that exact confusion hid four broken readers for months.
