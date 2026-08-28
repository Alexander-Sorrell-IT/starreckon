# What starforge made of the corpus

`starforge-cli`, same 20,217 transcripts, run in a container with
**`--network none`** — so "nothing left the machine" is enforced by the kernel
rather than asserted by the program.

```
              FIRST PRINCIPLES LV.7
TENACITY LV.5.4                    ENGINEERING LV.4.1
OUTSIDE THE BOX LV.5.6             CODING LV.5.7

        SKILL POINTS 27.8/35
```

## Measured

| | |
|---|---:|
| sessions | 16,800 |
| active days | 97 |
| duration | 1,533.4 h |
| user turns | **30,680** |
| tool calls | **86,925** across 73 distinct tools |
| file paths touched | 27,005 |
| night hours (00:00–05:59) | 150 |
| longest streak | 44 days |
| input tokens | 188,465,919 |
| output tokens | 56,193,756 |
| cache read | 17,449,275,636 |
| cache write | 650,705,683 |
| **all four counters** | **18,344,640,994** |

**Languages, 14:** python 7,159 · markdown 3,395 · solidity 1,550 · shell 832 ·
typescript 555 · json 416 …

## Artefacts, all local

| file | bytes |
|---|---:|
| `stats-*.html` | 97,473 |
| `expanded-*.json` | 30,783 |
| `star-*.svg` | 10,520 |
| `baseline-*.json` | 7,296 |

Plus seven monthly snapshots and seven per-month star SVGs — a longitudinal
record that outlives the logs, which age off disk after ~30 days. Total 146,072
bytes written, **0 bytes transmitted**.

## What it shows that the other tool could not

`HOW YOU TALK` came back blank next door on a corpus holding 19,790 prompts.
Here the same corpus yields 30,680 user turns and the full tool distribution —
Bash 51,340, Read 16,530, Edit 6,384, Write 3,237 — because nothing has to be
squeezed under an upload cap.

## Where this score was wrong, and now is not

The number this corpus first produced was **23.9/25**, and it was wrong three
separate ways:

- `computeLevels` clamped every axis at 5 while the log curve underneath kept
  climbing — FIRST PRINCIPLES was really 7.0
- a **5,000-path memory cap** was also the only input to language detection, so
  two languages were never seen (12 instead of 14)
- `finalize()`'s top-20 project list — a display truncation — was being read as
  a scoring input, capping ENGINEERING at 2.46 from that term forever

Fixed, the honest figure is **27.8/35**. Sessions, active days and every token
counter are unchanged: the scan was always right, the scoring was throwing
information away.

**ENGINEERING at 4.1 is still understated, and that is this corpus's fault.**
`projects_count` reads 1 because every `cwd` was rewritten to `/workspace`
during redaction. On unredacted machines that arm would be near the top.
