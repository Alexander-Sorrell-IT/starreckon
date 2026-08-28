# What `standout` made of the corpus

The output of **their** tool, on its own — `npx standout standout-founding-eng`
over the merged fleet corpus (20,217 transcripts, 401 project folders, 5
computers), captured from the exact bytes it was about to upload.

Payload `POST /api/public/wrapped` — **4,019,909 bytes**, tagged
`group: 'standout-founding-eng'`.

## Two windows, and it reports both

| | last 30 days | all time |
|---|---:|---:|
| sessions | 11,662 | 16,800 |
| active days | 31 | 97 |
| duration (h) | 897.3 | 1533.4 |
| input tokens | 74,818,549 | 188,465,919 |
| output tokens | 37,126,433 | 56,235,267 |
| cache read | 12,076,373,045 | 17,449,275,636 |
| cache write | 476,208,766 | 650,705,683 |
| **all four counters** | **12,664,526,793** | **18,344,682,505** |

The public card mixes the two — "896 session-hours" is the 30-day figure,
"~1,533 hours from local logs" is all-time. Quoting either without the window
is how a number stops meaning anything.

## What it derived

| | |
|---|---|
| first session | 2026-07-07T22:38:31.170Z |
| last session | 2026-08-06T11:19:07.889Z |
| peak hour | 22:00 |
| weekend ratio | 0.3 |
| longest streak | 31 days |
| current streak | 31 days |
| parallel workspaces | 0 |

**languages** — python 769, markdown 396, shell 75, javascript 59, json 37, typescript 17, yaml 13, rust 3, cpp 1, c 1, swift 1

**frameworks** — python 5, rails 1, github-actions 1

**models** — claude-opus-4-8, claude-fable-5, claude-opus-5, claude-haiku-4-5-20251001, deepseek-v4-flash, deepseek-v4-pro, claude-opus-4-7, claude-opus-4-6

## What it could not show

| field | count |
|---|---:|
| exchanges | 0 |
| prompt_samples | 0 |
| conversation_samples | 0 |

All three are empty, on a corpus holding 19,790 prompts. `capPayload` shrinks an
oversized payload by emptying those three lists in order and stops when there is
nothing left to empty rather than when the payload fits — and it never touches
`sessions`, which is one ~256-byte row per session and 99.7% of the bulk. So it
deleted every prompt and every conversation and still exited **19,909 bytes
over** its own 4,000,000 cap.

The live run printed the consequence verbatim:

```
  HOW YOU TALK
    no message sample provided.
    19,790 prompts  ·  23% questions  ·  ~3786 chars
    recurring: no sample available
```

## The live result

Submitted from a terminal, network on:

```
UNICORN · 100/100 · top 1% of 3,756 users
Technical Growth Wizard
intensity 89 · consistency 99 · craft +7
1,533h · 44-day streak · 13B tokens
```

The score is not a measurement of this corpus so much as a saturation: three of
the five sub-scores are at or within a point of their ceiling, so a much lighter
user reaches the same place. Recorded here as what the tool returned, not as a
finding about the work.

