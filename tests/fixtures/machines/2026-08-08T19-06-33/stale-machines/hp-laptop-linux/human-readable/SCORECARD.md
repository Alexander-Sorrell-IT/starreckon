# Scorecard — HP Laptop Linux

_2026-08-08T18:34:43-05:00_

**Everything checked out.**

| area | check | | detail |
|---|---|---|---|
| scan | totals.json written | ✅ |  |
| scan | sessions.json written | ✅ |  |
| scan | hardware.json written | ✅ |  |
| scan | scan is recent | ✅ | 3.1h old |
| scan | both scanners same version | ✅ | 1108dc477b34 / 1108dc477b34 |
| readers | every CLI has a row | ✅ | 8 rows |
| readers | no CLI is installed-but-silent | ✅ | none |
| readers | no reader raised | ✅ | none |
| agreement | analyze_tokens == sessions | ✅ | 6,615,634,312 vs 6,615,652,707 — 18,395 apart (0.00%) |
| corpus | export exists | ✅ | /home/phantomcore/token-corpus/hp-laptop-linux |
| corpus | export is recent | ✅ | 2026-08-08T15:39:37-05:00 |
| corpus | profiles match the scan | ✅ | 23 exported / 23 scanned |
| corpus | redaction ran | ✅ | topic 302,789, span 1,924, path 592,495, email 3,108 |
| archive | a dated snapshot exists | ✅ | 7 snapshot(s), newest 2026-08-08T15-31-11 |

---

A check that could not run shows `—`, never `✅`. A reader that is installed and reported zero sessions is a **failure**, not a quiet success — that exact confusion hid four broken readers for months.
