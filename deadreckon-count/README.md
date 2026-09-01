# deadreckon-count

> **Sibling repository:** [`deadreckon-record`](https://github.com/matrixbuilderops/deadreckon-record)
> — the transcripts these numbers were counted from. This repo holds the
> **claim**; that one holds the **evidence**. They are two halves of one system
> and neither is complete alone: `count` without `record` is a number you cannot
> check, and `record` without `count` is a pile of JSONL.

Count AI coding-tool token usage from the session files those tools write to
disk. No API call, no dashboard, no estimate — the numbers are the ones each
provider's API itself reported, read back off the local transcripts.

**Why "dead reckoning".** It is navigation by your own measurements, with no
external beacon to fix your position against — which is exactly the situation
here. Of the eight CLIs this counts, only Claude keeps a lifetime counter of
its own. Gemini writes nothing unless telemetry is switched on, Copilot's quota
lives on a server behind a counter its own documentation calls an undercount,
and Antigravity does not persist counts at all. Nobody is going to tell you the
number. You work it out from where you have been.

Claude Code is counted per account. Gemini CLI, GitHub Copilot CLI, Antigravity,
Kilo Code, Codex and xAI's Grok CLI are counted per session.

One folder per machine. Three root reports roll them all up:
**[BY-COMPUTER.md](human-readable/BY-COMPUTER.md)** · **[BY-ACCOUNT.md](human-readable/BY-ACCOUNT.md)** · **[BY-COMPANY.md](human-readable/BY-COMPANY.md)** · **[STATS.md](human-readable/STATS.md)** · **[LIFETIME.md](human-readable/LIFETIME.md)** · **[THIS-MONTH.md](human-readable/THIS-MONTH.md)**

## Setting up a new computer — one command

```bash
# Clone the repo (once, on a machine that has never had it)
git clone https://github.com/matrixbuilderops/deadreckon-count.git ~/deadreckon-count
cd ~/deadreckon-count

# Bootstrap everything: protect transcripts, register this machine, write the
# daemon service file, create the forecaster and search-corpus environments,
# pre-download all model weights.
python3 install.py --apply
```

`install.py --apply` does these things in the safe order, reports each step as
`DONE / ALREADY / SKIPPED / FAILED`, and exits non-zero if anything failed.
Nothing above is a warning. Read the output before continuing.

After it completes, **enable the daemon** (one manual step — an installer that
starts a background process unattended is a surprise):

```bash
# Linux
systemctl --user daemon-reload
systemctl --user enable --now retention-guard.service
loginctl enable-linger "$USER"          # survive without a login session

# macOS
launchctl load -w ~/Library/LaunchAgents/com.deadreckon.retention-guard.plist

# Windows
schtasks /Create /TN "deadreckon-retention-guard" /XML retention-guard.xml
```

Then verify it came up:

```bash
python3 install.py --verify             # checks daemon running, re-pulls if not
python3 retention_guard.py --verify-boot  # 0 came back · 1 did not · 2 cannot tell
```

Then scan, ship, and repeat on every machine in the fleet:

```bash
# Scan this computer and push results to both repos (daemon does this every 6h
# automatically; run once by hand to get the first result in immediately).
python3 run.py update

# Ship transcripts as a release asset (never through git — too large).
python3 corpus_ship.py pack && python3 corpus_ship.py push
```

**macOS** — `--verify-boot` returns **2** (cannot read `/proc`) — that is
"cannot tell", not a failure; use `launchctl list | grep retention-guard`
instead. **Windows** — if you also run WSL that is **two independent installs**;
run `install.py --apply` on both sides.

### Model weights and optional environments

`install.py --apply` creates two optional Python environments and pre-downloads
all model weights so inference never hits the network at runtime:

| Environment | Models | Purpose |
|---|---|---|
| `.venv-forecast` (python3.11) | `cisco-ai/cisco-time-series-model-1.0` | Time-series forecast check — independent pre-commit witness |
| `.venv-search` (python3) | `cisco-ai/SecureBERT2.0-biencoder` · `cisco-ai/SecureBERT2.0-cross_encoder` | Semantic search over exported transcripts |

Skip both with `--no-forecaster`. A machine without them still scans and
archives normally — these are extra senses, not prerequisites.

Set `DEADRECKON_MODEL_CACHE=/path/to/drive` to keep weights on an external disk
shared across machines (default: `~/.cache/huggingface`).

### Three lines that mean something went wrong

All three used to be silent. If you see one, send it over rather than re-running:

```
!! NOT ARCHIVED  <dir>: N FAILED (...)    the hard-link archive failed. A failed
                                          link used to be counted as "already
                                          there", so a dead archive printed the
                                          same line as a healthy one.
   TOKEN LEDGER  SCAN FAILED (...)        the lifetime number came from the last
                                          scan on disk, not from now. The word
                                          `scanned` must appear on a good tick.
   NOT COVERED — session-shaped stores     a CLI whose records nothing claims
```

<!-- BEGIN OVERVIEW -->
| Machine | Hardware | Accounts | Floor | On disk now | Every CLI | Scanned |
|---|---|---:|---:|---:|---:|---|
| [`macbook-air-m1/`](macbook-air-m1/human-readable/REPORT.md) | Apple M1 · 8 cores · 16 GB | 8 | **52.38B** | 18.03B | 22.84B | 2026-08-19 |
| [`hp-laptop-linux/`](hp-laptop-linux/human-readable/REPORT.md) | x86_64 · 12 cores · 62.5 GB | 15 | **38.53B** | 11.55B | 18.07B | 2026-09-01 |
| `dell-inspiron-desktop-linux/` | — | — | — | — | — | ❌ never |
| `dell-latitude-7480-linux/` | — | — | — | — | — | ❌ never |
| `dell-latitude-7480-windows/` | — | — | — | — | — | ❌ never |
| `asus-laptop-linux/` | — | — | — | — | — | ❌ never |
| **All computers** | | | **90.91B** | **29.58B** | | |


**Floor** is the defensible figure: what is still on disk PLUS what Claude Code's own frozen counter remembers of work whose transcripts have since been deleted. **On disk now** is only what survived retention — it is always the smaller number, and it drops over time even when usage does not.

The append-only token ledgers stand behind **36.25B** across these machines, of which **37.08M** is usage no scan can still see, because the transcripts behind it have been deleted. `LIFETIME.md` counts it; the columns above do not.

_2 of 6 computers scanned; generated by `combine.py` 2026-09-01. Do not edit by hand._
<!-- END OVERVIEW -->

The two token columns answer different questions and must not be added. *Claude
Code* is what `analyze_tokens.py` counts per account; *Every CLI* is what
`sessions.py` counts per session across Claude Code, Gemini, Copilot, Antigravity,
Kilo Code, Codex and Grok — it contains the first column, plus everything the
account totals never saw.

<!-- BEGIN ACCOUNTS -->
| Account | Tokens | Share | Computers |
|---|---:|---:|---|
| broodierchip@gmail.com | 15.20B | 51.4% | 2 |
| codehunterextreme@gmail.com | 13.38B | 45.2% | 2 |
| DeepSeek backend (~/.my-claude) | 520.50M | 1.8% | 1 |
| alexander.sorrell.it@gmail.com | 467.80M | 1.6% | 2 |
| unknown (Documents) | 10.01M | 0.0% | 1 |
| API key (org 15a93e14-aabb-4293-8228-8c56a803d972) | 141.21K | 0.0% | 1 |

_6 account(s) across 2 scanned computer(s), 29.58B total. Generated by `combine.py`. Do not edit by hand._
<!-- END ACCOUNTS -->

### Read the Anthropic-only column, not the raw total

**Not all of it is Anthropic's.** `~/.my-claude` is a `0.0.0-leaked` build wired
to DeepSeek — `deepseek-v4-pro` and `deepseek-v4-flash`, zero Claude models — and
another account carries some DeepSeek too. The transcripts are byte-identical to
Claude Code's, so summing them produced a "Claude" figure that Anthropic never
served. Totals are split on the model id; the per-company split above is the real
one, and the raw figure is not an Anthropic figure.

### archive/ — every scan, dated, kept

`update.py` snapshots **every** machine folder present, plus the reports:

```
archive/<machine>/<YYYY-MM-DDTHH-MM-SS>/   totals.json, sessions.json, hardware.json
archive/reports/<YYYY-MM-DDTHH-MM-SS>/     the reports + ALL-COMPUTERS.json
```

Every machine, not just the one being scanned. Pulling another computer's scan
brings data that will exist nowhere else once its transcripts expire, so it is
archived on whichever machine sees it rather than only on the one that produced
it. Each computer therefore ends up holding the fleet's history independently.

**Every total is a snapshot of several different instants, never one.** Machines
are scanned independently, so the report carries the scan time on the totals row
and again at the head of each per-machine section — a figure from a computer
scanned three days ago sits beside one scanned a minute ago, and the reader can
see which is which.

This exists because of the section below: transcripts are deleted after
`cleanupPeriodDays`, so **a scan is the only durable record of what those
sessions cost**. Git already holds that history, but reading it means diff
archaeology; this keeps each scan as a plain dated folder.

It writes only when something changed — each snapshot carries a `.digest` of its
contents and an identical one is skipped, so re-running on an idle machine does
not fill the archive with copies.

### The source data expires

**Claude Code deletes transcripts older than `cleanupPeriodDays`, default 30 —
but only in profiles you actually launch.** The sweep runs at startup, per
config directory, so an idle profile keeps everything indefinitely while the one
you work in is trimmed to the last 30 days.

That asymmetry is measurable on one machine, where no profile has the setting
configured and all five therefore default to 30:

```
~/.claude       oldest file 91 days   idle    — never swept
~/.my-claude    oldest file 84 days   idle    — never swept
~/.claude-it    oldest file 56 days   rare
~/.claude-alt   oldest file 32 days   ACTIVE  — swept
```

The consequence is worse than steady erosion: **the longer a profile sits
untouched, the more it has to lose the moment you open it.** On that machine
~/.claude holds 5.55 billion tokens, 5.5 billion of it from May, and the next
launch in that profile would take nearly all of it. The data looks safest right
before it disappears.

Caught on this repo rather than reasoned about: the MacBook Air went from
32,659,024,382 to 28,004,982,986 between two scans **54 minutes apart**.

What is measured, not inferred:

- both scans saw the same three config directories and the same 25 projects, so
  nothing was skipped
- `.claude-main` went from 2,709 transcript files to 2,682 — **27 files were
  deleted from disk** in that window
- the 11 lost sessions are all dated 2026-06-27 to 2026-07-03, and that
  account's oldest survivor is now exactly 30 days old
- 4,691,850,175 tokens are gone

The mechanism is retention, but not "they expired during those 54 minutes" —
they had been past 30 days for over a week and were still present at the first
scan. Cleanup does not run continuously; it runs on startup and sweeps
everything already expired in one pass. What happened in the window was the
sweep, not the aging. The deletion is therefore bursty and unpredictable: a
machine can sit for weeks holding expired transcripts and then lose all of them
at once, the next time the tool is launched.

Two consequences worth holding onto:

- **A rescan can lose data.** Re-running a machine is not always an improvement;
  if transcripts expired since the last run, it publishes a smaller number.
  `check_consistency.py` warns when a machine's total drops, because "this
  machine got smaller" reads exactly like "this machine was idle."
- **Git history is the only durable record.** Once a transcript is pruned, the
  committed `totals.json` from a previous scan is the sole surviving evidence
  that the usage happened. That is a real reason to commit after every scan.

To stop further loss, raise it in each config directory's `settings.json`:

```json
{ "cleanupPeriodDays": 36500 }
```

Per config directory, not per machine — the profiles on one computer expire
independently. On the fleet right now the oldest surviving session ranges from
199 days on the ASUS to exactly 30 on the MacBook Air, which is the difference
between a profile that never pruned and one that just did.

### Running it on macOS, Windows and WSL

`~/.claude` is the location on **every** platform — the docs are explicit that on
Windows it resolves to `%USERPROFILE%\.claude`, not AppData. So profile discovery
needs no per-platform table: a Claude profile is any directory containing
`projects/` with a `.jsonl` under it, and that test reads the same everywhere.

```bash
# macOS / Linux
cd ~/deadreckon-count && git pull
python3 retention_guard.py --check
python3 retention_guard.py --apply
python3 run.py update
```

```powershell
# Windows — PowerShell
cd $env:USERPROFILE\deadreckon-count; git pull
python retention_guard.py --check
python retention_guard.py --apply
python run.py update
```

```bat
:: Windows — cmd.exe
cd /d %USERPROFILE%\deadreckon-count && git pull
python retention_guard.py --check
python retention_guard.py --apply
python run.py update
```

**`python3` on macOS/Linux, `python` on Windows.** Windows has no `python3` on
PATH from the official installer, and `python3` there is a Store shim that opens
the Microsoft Store instead of running anything.

#### WSL is a SECOND machine, not the same one

This is the trap, and it is the per-profile asymmetry all over again one level
up. WSL has its own Linux home, so a Windows box running Claude Code in
PowerShell **and** in WSL has **two independent installations** — two
`~/.claude` directories, two `cleanupPeriodDays`, two sets of transcripts.
Protecting one does nothing for the other, and the side you are not looking at
is the side quietly holding the most.

`retention_guard.py` detects WSL (via `/proc/version`) and reports any Claude
profile it can see under `/mnt/<drive>/Users/<you>/`, with that profile's current
`cleanupPeriodDays`:

```
  WSL DETECTED — Claude profiles on the WINDOWS side, NOT protected here:
      /mnt/c/Users/you/.claude   cleanupPeriodDays=30
      Run this script in PowerShell on that side too
```

It **reports and never modifies** them. Editing a Windows `settings.json` through
the `/mnt` mount works, but doing it silently from the other operating system is
not a surprise this tool should spring on anyone.

**Scan both sides.** Register them as separate machines — `--machine
box-windows` and `--machine box-wsl`. One `run.py update` in WSL counts the WSL
home only; the Windows-side tokens are simply absent, and absent looks exactly
like zero on every report.

**What is verified and what is not:** all of this ran on Linux. The discovery
rule, the WSL detection and the path handling use `os.path.expanduser`, `os.sep`
and `os.walk` throughout, and the WSL branch correctly stays silent on native
Linux — but the macOS and Windows paths have **not been executed**. Run
`--check` first on each; it changes nothing and prints what it would do.

### `retention_guard.py` — doing that, and not having to remember

Editing five `settings.json` files by hand is a fix that lasts until an update
rewrites one, a profile is added, or a machine is set up in a hurry. The guard
does it, keeps doing it, and does not rely on the setting being the only defence.

```
python3 retention_guard.py --check     # report exposure, change NOTHING
python3 retention_guard.py --apply     # raise the period + link new files + record the ledger
python3 retention_guard.py --daemon    # re-assert every 6h, forever
```

**Install it as a service, or it stops guarding the moment you reboot.** It was
started by hand with `setsid` here for a while, and that is the worst state this
tool can be in: you stop checking a guard you believe is up, and Claude Code's
cleanup runs *at startup* — exactly when the machine comes back and the guard
does not.

```bash
# Linux — systemd user service (survives reboot, no login needed)
cp retention-guard.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now retention-guard.service
loginctl enable-linger "$USER"          # run without a login session

systemctl --user status retention-guard.service
journalctl --user -u retention-guard.service -f

# the two lines worth grepping for — a job that failed, and a tree not archived
journalctl --user -u retention-guard.service --since today | grep -E 'ERROR|NOT ARCHIVED'
```

```bash
# macOS — launchd
cat > ~/Library/LaunchAgents/com.tokenusage.retention-guard.plist <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.tokenusage.retention-guard</string>
  <key>ProgramArguments</key>
  <array><string>/usr/bin/python3</string>
    <string>REPLACE/WITH/PATH/retention_guard.py</string><string>--daemon</string></array>
  <key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/tmp/retention_guard.log</string>
</dict></plist>
PLIST
launchctl load ~/Library/LaunchAgents/com.tokenusage.retention-guard.plist
```

```powershell
# Windows — Scheduled Task at logon
schtasks /create /tn "retention-guard" /sc onlogon /rl highest `
  /tr "python C:\path\to\retention_guard.py --daemon"
```

**Run it from a symlink, not a copy.** `~/.local/bin/retention_guard.py` was a
copy here, four hours stale, and it was what the daemon actually executed — so a
fix committed to this repository was not the code doing the work. It is a symlink
now, and the service points at the symlink, so what runs is always what is
committed. If you copy it, you have re-created the drift.

**Layer 1 — raise the period.** Sets `cleanupPeriodDays` to 36500 in every
Claude profile. Profiles are **discovered, not listed**: the first version
carried a hardcoded list and missed `.claude-alt-api`, which was still at 30
with 59-day-old transcripts. It writes atomically via `os.replace`, backs the
file up once to `settings.json.before-retention-guard`, and **never lowers the
value** — a smaller number deletes more, so shrinking it is the one edit that
could destroy data, and the code refuses to make it.

There is no "off". The docs give a default of 30 and a minimum of 1; `0` fails
validation. 36500 is not a trick around the feature, it is the feature with a
threshold nothing reaches.

**Layer 2 — a hard-link archive.** A setting that is right today is not a
guarantee, so every file also gets a hard link under `~/.ai-logs-archive`. A
hard link is a second NAME for the same inode: when Claude Code unlinks its own
name, the bytes live on under this one. Verified before being relied on — file
created, linked, original deleted, content and mtime intact.

**A failed link is not a skipped one, and for a long time they were counted the
same.** `except OSError: skipped += 1` shared a counter with the legitimate
"already there" case, and the note was hardcoded `"ok"`:

```
every link fails  ->  (0, 5, 'ok')   archive holds 0 files
fully caught up   ->  (0, 5, 'ok')   archive holds 5 files
```

Byte-identical, and the summary line read `0 file(s) linked — 0 bytes either
way` in both cases — the exact wording of a healthy idle tick. The belt could
have been entirely gone with nothing to say so.

That is reachable, not theoretical: `protected_hardlinks=1` makes any file not
owned by you fail permanently, an ext4 error-remount-ro routes every link into
that branch, and `os.makedirs(exist_ok=True)` swallows `EROFS` instead of
raising. `ENOENT` lands there routinely too, when Claude Code deletes a
paste-cache file between the walk and the link.

Failures have their own counter now and reach the note, and `run()` prints it —
including for **Claude profiles, where it had been read only for `"absent"` and
otherwise discarded**, which is the one tree on this machine that anything
deletes. The line to look for:

```
    ~/.claude                      12 new    840 already  [projects, todos, ...]
      !! NOT ARCHIVED  file-history: 37 FAILED (Read-only file system)
```

Measured on the machine this was written on: **50,591 files, 2.6 GB covered,
3.04% extra disk** (directory entries; `du` across both trees deduplicates hard
links, so a real copy would have shown 100%).

It covers **all thirteen paths Claude Code sweeps**, not just `projects/` — the
first version linked transcripts alone and left `file-history` (pre-edit
snapshots), `plans`, `tasks`, `debug`, `session-env` and `backups` exposed.

**Every CLI, not just Claude.** Claude Code is the only tool here that deletes —
gemini still holds files from 2023-06-26, and copilot, codex, kilocode and
lmstudio have no retention setting at all. The rest are archived as insurance.

**Where each tool keeps its records comes from [`stores.py`](stores.py)** — one
map, read by the counter, the archiver, the sweep and the exporter. It used to be
written out three separate times (`sessions.DETECT`, `retention_guard`'s own
tables, `sweep_usage.COVERED`) with six paths spelled out identically in two of
them, which is a fix landing in one place and not the others.

An earlier rule linked **whole tool directories** rather than the subfolder that
holds records, and the cost is still on disk: `.gemini` is 985 MB against
`.gemini/tmp`'s 122 MB, so the archive carries ~1 GB of Go, Python and bytecode
from a plugin tree. The map is specific now, and the exporter skips that residue
(42,035 files on the last run) — but a hard link already made is a link that
stays until removed.

`kind="root_files"` handles the case a subfolder misses: proteus keeps
`history.jsonl` loose in `~/.proteus`, beside its program directories. Those
stores take **records** — `history.jsonl`, `*.jsonl`, `cli_history` — and not
every file sitting next to them. Taking everything is how `~/.devvit/token` (a
live OAuth refresh token) and `~/.gemini/oauth_creds.json` got archived. A token
counter has no business holding a token; the rule is *records, not config*, and
it needs no secret-scanner to enforce.

`~/.ollama/history` is a **file**, not a directory — it read as "absent",
indistinguishable from ollama not being installed, for as long as that rule
existed.

Anything session-shaped that no rule claims is **reported by
[`sweep_usage.py`](sweep_usage.py)**, which searches by content rather than by
name — that is how `.deepseek-code` was found. Deliberate exclusions carry their
reason in the code: `.basilisk` (239,591 files, 26 GB, a workspace not a
conversation store) and `.lmstudio` itself (108 GB of models; only
`conversations/` is linked).

**`export_corpus.py --archive` reads this archive alongside the live profiles**,
so the corpus keeps work whose original is already gone. That is the point of
the whole arrangement: the two consequences above — that a rescan can lose data,
and that git history was the only durable record — stop being true.

### `token_ledger.py` — the lifetime total, and why only Claude has one

```
python3 token_ledger.py              # what the ledger says
python3 token_ledger.py --record     # observe now, append what is new
python3 token_ledger.py --compare    # ledger vs the current scan
```

The daemon **scans and then records** on every tick, so under normal use you
never run it by hand. `--compare` is the one worth knowing: it tells you how much
of your lifetime total exists **only** in the ledger because the transcripts
behind it are gone.

**"Scans" is load-bearing, and for six hours it did not.** `record()` diffs
against `machine-readable/sessions.json`, and `sessions.py` is that file's only
writer — reached only through `run.py update`. So the daemon re-read a file a
human had to regenerate, appended nothing, and logged a large growing-looking
lifetime. Four of five live ticks were `+0`; the one that wasn't followed a
manual scan. Handed a folder whose `sessions.json` held one invented session, it
reported `lifetime 42 across 1 session(s)` — in the shape of a real figure.

The scan goes to a **scratch directory**, never the machine folder: writing
`sessions.json` there leaves it newer than `totals.json`, which trips the fatal
cross-check in `check_consistency.py`, and dirties git every six hours. It costs
about thirty seconds out of every 21,600. A dry run reports `dry` and skips it
rather than spending that time rehearsing.

The line to look for:

```
TOKEN LEDGER  scanned 269 session(s), +1 new; lifetime 8,591,411,142 across 269
```

If `scanned` is missing, or it says `SCAN FAILED`, the number came from the last
scan on disk — which it now says out loud instead of printing the healthy line
either way.

**Checked against the vendors' own documentation, not from memory:**

| CLI | lifetime counter on disk |
|---|---|
| Claude | **yes** — `stats-cache.json`, and `.claude.json`'s `lastTotalCacheReadInputTokens` |
| Gemini | **no.** `telemetry.md` gives `"enabled": false` and no default `outfile`; nothing is written unless you switch it on |
| Copilot | **no.** The quota lives on github.com, and GitHub's own counter is a [documented undercount](https://github.com/github/copilot-cli/issues/1582) |
| Antigravity | **no.** Counts are not persisted — they are reconstructed from protobuf BLOBs |

So for seven of the eight CLIs counted here, if this file does not remember the
number, nobody does.

**`lifetime.json` cannot be that record.** `run.py` lists it under `DERIVED_ROOT`
and recomputes it from whatever is on disk, so a deletion simply makes it smaller
and nothing says anything was lost. `history_ledger` in `sessions.json` is
closer — it remembers 567 sessions whose transcripts are already gone — but it
carries *prompt* counts, not tokens. It can tell you a session existed; it cannot
tell you what it cost.

**Keyed by session, not by day.** A session's token count is a fact about that
session and never changes. A day's is an aggregate that depends on how sessions
are attributed to days — and they go to their **start** date, so a session
running from the 7th to the 8th puts everything on the 7th. Measured here: ten
days where `by_day` holds hundreds of millions and the per-session view holds
zero, with the grand totals agreeing to 18,395.

**Every row carries the scanner that produced it**, and a session's value is the
maximum among rows from the **newest scanner that ever saw it**. That gives two
properties which pull against each other:

- **deleting a transcript cannot lower the total** — the old observation is still
  in the file, and no newer scanner will ever read that session again
- **correcting the scanner can** — otherwise fixing the dedup rule would have
  enshrined its own wrong 14,529,373,789 as "lifetime" forever

Both are asserted together in `test_scanner.py`, because a rule that satisfies
one and not the other looks correct in isolation.

The file is `<machine>/machine-readable/token_ledger.jsonl`, append-only. 269
rows / 96 KB after seven months; roughly 150 KB a year. One row per session, plus
one more only when the scanner version changes.

It reproduces `lifetime.json` exactly by a completely different route —
**8,415,422,675 across 269 sessions, 7 CLIs** — which is the point: two
independent constructions agreeing is evidence, one construction is a claim.

### Adding a computer

The fleet is listed in [`machines.json`](machines.json). Append a row, run the
scanners on that machine, and `combine.py` — every table, provider column and
total is derived, so nothing else is edited anywhere. The README block above is
generated too; it says so, and it should not be typed into.

That file exists because folders are the only other evidence a machine exists,
and a computer that has never been scanned has no folder — so it was not
reported as missing, it was simply absent, while the grand total quietly
understated by whatever it holds. Listing the fleet turns those into visible
gaps: **3 of 6 are scanned**, so every number here is currently a floor.

One row per OS install, not per physical machine. The Dell Latitude 7480 is
dual-booted and gets two rows — each install writes its own session files and
neither can see the other, so merging them would hide which side the work
happened on.

### Two scanned folders are stale

Both predate three fixes and their numbers are floors, not totals:

1. `find_config_dirs` matched `.claude*`, which skips any profile not named that
   way — `~/.my-claude` held 1.41B and was invisible.
2. Profiles with no email all collapsed to `unknown`, so unrelated profiles were
   summed into one account that does not exist. Identity now falls back to the
   stable `userID`, which also joins correctly across machines where a directory
   name would not.
3. No provider split, so DeepSeek usage counted as Claude.

Run `update.py` on each of them. Until then the rollup mixes scanner versions,
and the per-CLI section covers only the machines that have been through
`sessions.py` — the figure at the top of this file is a floor, not a total.

### Known accounts

[`accounts.json`](accounts.json) lists the accounts that exist, for the same
reason [`machines.json`](machines.json) lists the computers: accounts are
discovered from whatever machines have been scanned, so one that is signed in
only on an unscanned machine does not read as missing — it is simply not there,
and its usage is in no total.

`nefabious@gmail.com` is currently that case, and it is confirmed real — a CLI
account signed in on other machines, just not this one. It appears on none of the
three scanned machines, so it is either on one of the three unscanned ones, or it
is the Dell Latitude's `unknown` 7.28M profile, whose email that pre-fix scan
discarded rather than recorded. Rescanning the Dell settles which.

An account listed here and not found is not a stale entry to be cleaned up. The
mismatch is the whole point of the file: it is the difference between "this
account has no usage" and "this account's usage is not in the numbers yet."

The file also labels the two profiles that legitimately have no email, so each
rescan stops rediscovering the same cryptic `user:<uid>` row. They are not
missing emails to be filled in; they are different things:

| Profile | What it is |
|---|---|
| `~/.claude-alt-api` | An API key. Keys carry no email, and the billing org is only knowable by asking the API — it resolves to an organization none of the three logged-in accounts own, despite the directory name implying otherwise. |
| `~/.my-claude` | A `0.0.0-leaked` build pointed at DeepSeek: 12,959 `deepseek-v4-pro` and 2,727 `deepseek-v4-flash` calls, zero Claude models. Not an Anthropic account. |

Only add a `userID` mapping with evidence. A naming convention is not evidence —
that is precisely what the API-key directory name gets wrong.

### API-key profiles

An API-key profile has no email and bills to whatever organization owns the key —
**which is not recorded anywhere on disk.** `--probe-api` resolves it from the
`anthropic-organization-id` response header (one read-only request, no tokens
generated). Profiles are linked to an account only on an `organizationUuid` match;
a naming convention is not evidence. On this machine `~/.claude-alt-api` looks like
it belongs to `~/.claude-alt` and does not — its key bills to
`15a93e14-aabb-4293-8228-8c56a803d972`, an organization none of the three logged-in
accounts own.

## Per-session stats across every CLI

`analyze_tokens.py` answers *how many tokens per account*. `sessions.py` +
`stats.py` answer *which session, how long, how heavy* — across Claude Code,
Gemini CLI, Copilot CLI, Antigravity, Kilo Code, Codex and Grok.

```bash
python3 sessions.py --out <machine-folder>      # writes sessions.json
python3 stats.py                                # everything
python3 stats.py --machine hp-laptop-linux
python3 stats.py --cli copilot --by tokens
python3 stats.py --provider anthropic --top 10
```

`combine.py` folds `sessions.json` into the rollup too, and the three reports
carry it by computer, account and company.

**Those CLI rows are not additive with the account totals.** The `claude` row is
the same usage counted per session instead of per account; the other every CLI
are the 1.80B the account totals never saw. The report says so inline, and
`ALL-COMPUTERS.json` keeps `by_cli` / `by_provider` out of `grand_total_tokens`
for the same reason. A machine that has not been through `sessions.py` is named
explicitly rather than silently contributing zero — absent and none are different
facts.

**`--cli` and `--provider` are different questions.** Copilot runs Claude models;
that is Copilot spend, not Anthropic subscription spend. `--cli copilot` answers
"what did this subscription cost me", `--provider anthropic` answers "how much
did Anthropic actually serve", across every tool. Across every scanned machine:

<!-- BEGIN CLI -->
| by CLI | | | by company | |
|---|---:|---|---|---:|
| claude | 34.93B | | anthropic | 34.80B |
| gemini | 2.46B | | google | 2.69B |
| codex | 1.64B | | openai | 1.93B |
| copilot | 793.53M | | deepseek | 543.65M |
| bob | 501.66M | | synthetic | 355.71M |
| clawspring | 258.50M | | - | 272.62M |
| antigravity | 218.71M | | other | 229.14M |
| grok | 100.22M | | xai | 100.23M |
| kilocode | 7.07M | | copilot | 1.21M |
| copilot-chat | 1.21M | | mistral | 116.19K |
| lmstudio | 173.04K | | meta | 59 |
| claude-orphans | 0 | | | |

_Generated by `combine.py` from 2 scanned machine(s); 40.91B across 12 CLI(s). Do not edit by hand._
<!-- END CLI -->

`kilocode` is a VS Code extension rather than a CLI, and it is counted because it
bills per request like one. Finding it required scanning
`~/.config/Code - Insiders` as well as `~/.config/Code` — checking only the
stable channel missed it entirely.

**Kilo Code and Grok are separate things, and the `xai` row is why the two
columns exist.** Kilo Code is its own tool with its own 7.07M; one of its
requests happened to call a Grok model (`x-ai/grok-code-fast-1`, provider
`xai`, 10,646 tokens). That is Kilo Code *spend* and xAI *service*, which is
exactly the split `--cli` and `--provider` are for. xAI's own Grok CLI is a
different program with its own reader here, and it is not installed on this
machine — `~/.grok` does not exist. The `@vibe-kit/grok-cli` npm package is
installed, is a third unrelated thing, and records no usage at all.

**Gemini CLI and Antigravity are also separate programs**, despite Antigravity
parking its data under `~/.gemini/antigravity-cli/`. Different binaries (`gemini`
vs `agy`), different storage formats, disjoint globs, and two separate rows —
verified at zero overlapping files. Their shared parent directory is the only
thing they have in common.

### Traps, each verified against raw records

**Codex stacks three traps on one field.** Every `token_count` event carries
both `total_token_usage` (running total) and `last_token_usage` (that turn).
Summing the former compounds. But summing the latter is *also* wrong: it is
emitted twice per turn, byte-identical, the repeat always immediately following
the first — 60 of this machine's 122 usage events are repeats. And
`cached_input_tokens` is a subset of `input_tokens`, not a separate bucket, so
adding it counts the cached prompt twice more:

```
summing total_token_usage           : 59,193,380   <- 40.7x, cumulative
summing last_token_usage + cached   :  5,373,949   <- 3.7x, what this repo shipped
summing last_token_usage            :  2,859,773   <- 1.97x, the duplicate emissions
dropping repeats, cached as a split :  1,453,618   <- correct
```

The last line is confirmed by a completely independent route: each session's
own final `total_token_usage`, the cumulative counter read once instead of
summed, gives **1,453,618** exactly. Two unrelated methods, same number to the
token.

That middle line shipped in this repo for two commits. It looked right — it
used the documented per-turn field and avoided the obvious cumulative trap —
and it was still 3.7x the truth. A number being defensible is not the same as
it being checked against something.

**Copilot has five token-shaped fields and one is usage.** `session.shutdown` ->
`modelMetrics.<model>.usage.*` is authoritative. `session.truncation`
(`tokenLimit`, `preTruncationTokensInMessages`, `tokensRemovedDuringTruncation`)
and the `currentTokens` / `conversationTokens` snapshots are context-window
bookkeeping, not billed usage:

```
authoritative (session.shutdown)   292,157,006
+ reasoningTokens                      335,250
+ compaction (a real billed call)    3,339,711
= counted                          295,831,967

bookkeeping (excluded)             555,396,004
naive sum of everything            848,753,178   ->  2.9x inflation
```

`assistant.message.outputTokens` is a per-message fragment already inside the
rollup — summing those gives 1,200,168, exactly equal to the rollup's own
`outputTokens` of 1,200,168, which is the double-count proven rather than
assumed. `subagent.completed.totalTokens` (25,361,804) is the same story.

**The compaction object contains a field that is not tokens.** Compaction is a
real model call and its tokens count, but `compactionTokensUsed` also carries
`duration` — milliseconds. Summing every integer in a dict named `...TokensUsed`
adds 194,163 phantom tokens. Only known token keys are read, across both schema
generations (13 events old-style, 5 new, never both in one event).

**Duration must be active time, not elapsed time.** A resumed session's
transcript spans days while holding minutes of work. Measuring first-to-last
timestamp produced a *436-hour day* here, and a 2,513-hour machine total against
a true 247.9. Gaps longer than 15 minutes are idle and dropped — the same
segmentation Claude Code itself uses.

Session-hours can still exceed 24 in a day: parallel agents overlap, and that
overlap is real work, so it is summed rather than clamped.

### What "uncountable" cost, and the rule that came out of it

This section used to list Gemini CLI as uncountable, on the grounds that most
`token` matches under `~/.gemini` are `anyio`'s `CapacityLimiter.total_tokens`
in vendored Python — concurrency slots, not LLM tokens. That observation was
true and the conclusion drawn from it was wrong by **1,468,362,549 tokens**. The
usage was in `~/.gemini/tmp/<projectHash>/chats/`, under the Gemini API's own
field names, in a directory the search never reached.

The same mistake had already been made once, on Copilot — declared uncountable
after reading `session-store.db`'s schema, while 295 million tokens sat in
`session-state/*.jsonl` next to it. Twice is a pattern, so it is now a rule:

> **A search that finds nothing is not a negative result.** "Not countable"
> requires naming what *was* searched and what a positive result would have
> looked like. Absence of evidence gets recorded as absence of evidence.

Applying that rule turned up 1.7B+ tokens across four tools in one pass, and
everything it found is now counted rather than footnoted:

| Tool | Status |
|---|---|
| Antigravity CLI | **counted.** Protobuf blobs in SQLite plus two AES-256-GCM `.pb` files, whose key is a string constant compiled into the `agy` binary. It was a footnote for one commit — "countable but not counted" is just a slower way of being absent, so it is a reader like every other tool. It is the one reader a vendor update can break silently, so it identifies a usage record by a structural invariant rather than by position, and fails soft. |
| `@vibe-kit/grok-cli` | installed, records no usage of any kind. Distinct from xAI's official Grok CLI, which does — `sessions.py` reads that one, for the machines that have it. |
| Copilot `session-store.db` | schema has no token columns; the real data is in `session-state/*.jsonl`, and is counted. |

## The five commands

Everything goes through one entry point, and each verb does the whole job across
**both** repositories rather than leaving half for you to remember.

```bash
python3 run.py status      what state is all of this in
python3 run.py update      scan this computer, export, rebuild everything
python3 run.py rebuild     no scan — delete every derived file and recompute
python3 run.py archive     snapshot today into archive/, then rescan
python3 run.py retire      move everything to testing-archive/, start clean
```

| verb | scans? | touches the corpus? | when |
|---|---|---|---|
| `status` | no | reads | before asking anyone anything |
| `update` | **yes** | exports + rebuilds | the normal one, on every computer |
| `rebuild` | no | rebuilds | after pulling someone else's scan |
| `archive` | **yes** | exports | when you want today frozen first |
| `retire` | no | clears | once, when the building stops |

### Why `rebuild` deletes before it regenerates

It removes every generated file and recreates it, rather than overwriting in
place. Twice in one day a generator was changed to write somewhere new while a
reader still looked at the old path — and the **stale copy won**. A scan sat
beside a file from hours earlier, every check passed, and the reports were
quietly wrong.

Deleting first makes that impossible: a file nothing rewrites is simply gone,
which is loud. Demonstrated by re-introducing the bug — overwrite-in-place kept
serving a three-minute-old file; delete-first left it missing.

It never touches `totals.json`, `sessions.json`, `hardware.json`, `.machine-id`
or the CSVs. A scan produces those and a rebuild cannot recreate them.

### What `retire` is for

Once, at the point this stops being built and starts being used. It moves the
development churn into `testing-archive/` so `archive/` can begin as an
operating record — and it retires any machine folder scanned by a superseded
version, because a folder counted by code with known defects is not "slightly
out of date". Nothing is deleted, and each machine restores itself the moment it
runs `update` again. The number comes back because it was re-measured.

## Run it

**There are two repositories and every computer feeds both.** This one holds the
numbers; `deadreckon-record` holds the redacted transcripts those numbers came from.
Running only the first half is the easiest mistake to make here, and it is
silent — the tables all update and look finished while the corpus stays a
computer short.

**Every computer creates its own folder in BOTH repositories.** That is the
whole model: `deadreckon-count/<machine>/` holds its numbers,
`deadreckon-record/<machine>/` holds its conversations. No computer ever writes into
another's folder, and no computer writes the shared root documents.

Copy this verbatim. Nothing needs filling in — `run.py update` prints the exact
commit lines with your machine name already in them.

**Before step 5, check which GitHub account is active.** Both repositories are
private and owned by `matrixbuilderops`. `gh auth token` returns whichever
account is ACTIVE, and more than one can be logged in at once — so with a
different account active every call returns a bare:

```
{"message": "Not Found", "status": "404"}
```

which is byte-identical to the repository having been deleted. That is not a
hypothetical: it produced the conclusion *"the corpus repo does not exist, the
archives exist only on this drive, there is no offsite copy"* — about a 1.49 GB
private repo that already held all five machines' archives.

```bash
gh auth status                              # who is active?
gh auth switch --user matrixbuilderops      # the owner of both repos
```

`corpus_ship.py push` and `pull` now check this first and print that fix, rather
than failing in a way that gets believed.

```bash
# 0. protect the source data BEFORE scanning (see retention_guard.py above)
python3 retention_guard.py --apply

# 1. get everyone else's work
cd ~/deadreckon-count && git pull

# 2. scan this computer, export its transcripts, write BOTH folders
python3 run.py update

# 3. push this computer's numbers
git commit -m "scan <machine>" && git pull --rebase && git push

# 4. push this computer's conversations — as a release asset, NOT through git
cd ~/deadreckon-count && python3 corpus_ship.py pack && python3 corpus_ship.py push
```

### Do not git-commit transcripts

This step used to read
`cd ~/deadreckon-record && git add <machine> && git commit && git pull --rebase && git push`.
**Do not run it.** Measured on 2026-08-08, it hung for 25 minutes with zero
progress and had to be killed — twice — leaving a partial rebase and a lock file
behind each time.

The cause is structural, not a bad connection:

| | `.git` | content | files | commits |
|---|---:|---:|---:|---:|
| `deadreckon-count` — numbers | 16 MB | 137 MB | 842 | many |
| `deadreckon-record` — transcripts | **4.0 GB** | 3.8 GB | 19,708 | **21** |
| the same transcripts, packed | — | **624 MB** | 10 | — |

Four gigabytes of history for twenty-one commits. Transcripts are append-only
JSONL that never diff usefully, so git writes a **whole new blob per file per
scan** — one corpus commit here was `1610 files changed, 188852 insertions`.
Five machines times every scan, and `.git` grows about as fast as the corpus
does, permanently. A fetch is also one pack over one connection and **cannot
resume**: half a gigabyte in, a drop is a failed transfer, not a slow one.

**Numbers go in git. Transcripts go in release assets.** That is the whole rule.

Retrieval, verified end to end on 2026-08-08:

```bash
gh auth switch --user matrixbuilderops
python3 corpus_ship.py pull                    # or --machine <name>
python3 corpus_ship.py unpack --into ~/corpus
```

`pack` was 5.9x (560.3 MB to 94.7 MB); the uploaded asset downloaded back with a
matching sha256; unpack produced 1,687 real transcripts with `cwd` redacted to
`/workspace`; and a file truncated to half its size resumed to the exact byte
count with `sha256 ok`. A dropped connection costs one 16 MB chunk.

If a machine's folder is missing from `deadreckon-record`, it is recoverable —
`corpus_ship.py pull --machine <name>` then `unpack`.

`run.py update` does the scan, the export, every report in both repositories,
and prints this computer's scorecard. The individual scripts still work if you
want one step on its own.

### The same six documents, at both levels

Every machine folder answers every question the root does — for itself:

```
                        root/              <machine>/
BY-ACCOUNT.md           every login        the logins on this computer
BY-COMPANY.md           every vendor       who served THIS computer's tokens
BY-COMPUTER.md          all machines       (n/a — it IS the machine)
STATS.md                the fleet          this computer, at human scale
LIFETIME.md             everything ever    this computer, ever
THIS-MONTH.md           the month so far   this computer this month
machine-readable/months/YYYY-MM.json       both levels, one file per month
```

None of that is derivable from the fleet report — "which vendors served the
MacBook" is not a slice of "which vendors served the fleet" that a reader can
take out again. So both are generated, from the same renderers, over different
slices. One implementation, not two that have to agree.

### How the dynamic files stay current

Nothing is hand-written and nothing is copied between repositories:

```
a scan writes      <machine>/machine-readable/totals · sessions · hardware
                   (only a scan can produce these — a rebuild cannot)

everything else    derived from those, every run, in both repos:
                   combine.py      → ALL-COMPUTERS.json + the README tables
                   stats_page.py   → BY-COMPUTER · BY-ACCOUNT · BY-COMPANY
                   fun_stats.py    → STATS, root and per machine
                   monthly.py      → LIFETIME · THIS-MONTH · months/, both levels
                   scorecard.py    → SCORECARD, per machine
                   corpus_reports.py → the corpus's own copies, from transcripts
```

`combine.py` and the rest **glob the machine folders**. A folder that is present
is in the totals; one you have not pulled does not exist. That is the whole
mechanism — which is why `git pull` comes first, and why a machine only ever
commits its own folder.

### A machine writes its own folder and nothing else

**`git add -A` is wrong here, and that was the real bug** — not the git
incantation around it. The root reports are derived from *every* machine
folder, so a computer that commits them is publishing a rollup of whatever it
happened to have pulled, and overwriting a fresher one. Worse, they are the
only files every machine touches, which is exactly what makes two computers
scanning at once collide.

So `run.py update` stages `<machine>/` and nothing more. It still rebuilds the
root documents locally — you want to read them — but does not stage them. Two
computers can now scan and push simultaneously and never conflict, because
they write disjoint paths.

The collective is regenerated on demand, by whoever wants current numbers:

```bash
git pull && python3 run.py rebuild
```

`git pull --rebase` before the push is still there as a belt: a scan takes
minutes, and rebasing across disjoint folders can never conflict. Commit
**before** pulling, or the rebase fails on the unstaged scan.

### If a machine has never run since the last `retire`

`retire` moves every machine folder aside, and `.machine-id` goes with it — so
the folder no longer claims a hostname and `update` refuses to guess rather
than write one computer's numbers into another's:

```bash
python3 run.py update --machine macbook-air-m1
python3 run.py update --machine dell-latitude-7480-linux
python3 run.py update --machine dell-inspiron-desktop-linux
python3 run.py update --machine asus-laptop-linux
python3 run.py update --machine dell-latitude-7480-windows --label "Dell Latitude 7480 Windows"
```

Once, per machine. After that the folder carries a fresh `.machine-id` and
plain `python3 run.py update` is enough forever.

**A reporting computer never clones `deadreckon-record`.** It writes its own archive
and uploads it; it has no reason to hold anyone else's transcripts. That removes
the step most likely to fail — cloning that repository is what broke here with
`fatal: fetch-pack: invalid index-pack output`, on 184 GB of free disk and 47 GB
of free RAM, because a git pack arrives in one piece or not at all.

Needs `zstd` (`sudo apt install zstd`) and `gh`, plus `pip install cryptography`
where Antigravity is used.

On Windows use `python` if `python3` is not on PATH.

Both repositories are private, but every computer that has already pushed a scan
here has working GitHub credentials by definition, and they are the same
credentials for both repos — so the clone above just works. If a computer that
has never pushed stalls on `could not read Username for 'https://github.com'`,
its credentials are missing rather than wrong: `gh auth login` once, or
`gh repo clone matrixbuilderops/deadreckon-record ~/deadreckon-record` instead.

Never had a `deadreckon-count` checkout either? `git clone
https://github.com/matrixbuilderops/deadreckon-count.git` first.

**Two computers need a flag on their next run**, because their folders have no
`.machine-id` yet and `update.py` refuses to guess:

| Computer | instead of plain `update.py` |
|---|---|
| Dell Latitude 7480 Linux | `python3 update.py --machine dell-latitude-7480-linux` |
| Dell Latitude 7480 Windows | `python update.py --machine dell-latitude-7480-windows --label "Dell Latitude 7480 Windows"` |

**Install `cryptography` first if Antigravity is used on that computer** — its
records are AES-encrypted, and without the library they are counted as
unreadable rather than counted at all. On the machine this was written on that
was 23.5 M tokens.

### What each half does

`update.py` works out which folder belongs to this computer, runs the three
scanners into it, re-derives every root document, archives a dated snapshot, and
proves the numbers add up before saying it is done.

`export_corpus.py` writes that computer's transcripts, redacted, to
`corpus/<machine>/` — **gitignored here on purpose**, ~216 MB per machine, which
is why it goes to a separate repo instead.

`corpus/*` rather than `corpus/<machine>` in the copy: `export_corpus.py` writes
exactly one folder, named for this computer, so there is no name to look up and
no way to copy the wrong one.

**Commit, then pull, then push — in that order.** Several computers push to
`deadreckon-record`, so a stale local `main` gets its push rejected; the rebase fixes
that. But rebasing while the freshly-copied files are still uncommitted fails
with `cannot pull with rebase: You have unstaged changes`. Pulling first instead
would leave the same hole, since the copy happens after it.

### Moving the corpus: archives, not git

**Do not clone `deadreckon-record` to get the transcripts.** A git fetch is one pack
over one connection and **cannot resume**, so half a gigabyte in, a dropped
connection is a failed transfer that starts over. That is what happened here,
twice, on 184 GB of free disk and 47 GB of free RAM:

```
fatal: fetch-pack: invalid index-pack output
fatal: could not fetch <oid> from promisor remote
```

The corpus is also the wrong shape for git — ~120,000 small files that will
never be diffed, in a repository that only grows.

```bash
python3 corpus_ship.py pack     # corpus/ -> dist/<machine>.tar.zst + .sha256
python3 corpus_ship.py push     # upload as a release asset
python3 corpus_ship.py pull     # fetch every machine's archive, resumably
python3 corpus_ship.py unpack   # expand into ~/deadreckon-record
```

Release assets are plain HTTP objects that honour Range requests, so `curl -C -`
resumes from wherever it stopped — the same reason model weights are fetched
that way instead of cloned. `pull` retries up to 8 times and verifies sha256.

Measured on this machine: **463 MB of transcripts becomes 84 MB in about three
seconds** (zstd -10; -19 saves 5 MB and costs 40 seconds, which is not worth it).
A download killed at 16.4 MB resumed and fetched only the remaining 67.3 MB, and
the result was byte-identical — `dacf424b…`. Unpacking reproduces all 1,460
files at 463 MB, diff-clean against the original.

Six computers is therefore ~500 MB in six independently resumable files, rather
than a 3 GB repository that has to arrive in one piece.

Requires `zstd` (`sudo apt install zstd`) and `gh`.

### digests/ — the corpus, small enough to carry

The corpus is ~480 MB per computer and outgrew being moved around: a plain
`git clone` of it failed here, and the blobless fallback then failed to fetch
lazily during a merge. Almost nothing actually needs the transcripts, though —
the reports want totals, rankings and distributions, and those are additive over
a window.

```bash
python3 digest.py                                  # from this machine's profiles
python3 digest.py --corpus ~/deadreckon-record/<machine>
```

One file per 30-day window, anchored to a fixed epoch so every machine buckets
identically and windows can be added together. On this machine that is **8 KB
against 463 MB**, and the digests sum to 11,014,008,662 — the same figure
`count_corpus.py` gets by reading all 1,460 files.

Each window holds token totals by model and project, session and turn counts,
tool-use frequency, an hour-of-day histogram, and message-length distributions.

**Counts and distributions, never text.** Message *lengths* rather than
messages, tool *names* rather than arguments, the first word of a turn rather
than the turn. Enough to characterise how a computer gets used without carrying
content — which is the entire reason the corpus is a separate private
repository. A digest must not quietly become a second copy of the conversations.

Two things it gets right that are easy to get wrong:

- **A "user" turn is not always a person.** The harness files background-task
  notifications, interrupt notices and hook output under the same role. Counting
  those put `tasknotification` and `request` among the most common opening words
  here — 120 turns in one window that nobody typed. They are excluded from every
  style measure.
- **A tool-only assistant turn has no text.** Including it as length 0 dragged
  the median to 0, which reads as "says nothing" rather than "acted instead of
  talking". Length stats cover turns that actually said something, and the count
  of those is reported alongside.

Digests are lossy on purpose and replace nothing. `deadreckon-record` stays the
source of truth, and `count_corpus.py` still checks the scanner against it.

### Then, once, after every machine has reported

Run this on one computer only — whichever holds a checkout of both repos.

```bash
git -C ~/deadreckon-record pull
python3 merge_corpus.py
```

`merge_corpus.py` reads `~/deadreckon-record` by default, so the second line is run
from a checkout of **this** repo and needs no path. Override either side with
`--corpus DIR` / `--out DIR`.

`merge_corpus.py` collapses every machine's folder into ONE
`merged/.claude/projects/` tree, because profile tools read a single home
directory and would otherwise see one computer. It:

- **renumbers project folders globally** — each machine numbers its own from
  `-workspace-p001`, so an unchanged copy has one machine's first project
  overwrite another's
- **drops duplicate messages by uuid** across machines, and reports how many
- **re-checks for leaks and refuses to finish if it finds any**, on the decoded
  JSON rather than the file text

It does not re-redact. Each export already did, and redacting again here would
mask an export that had skipped it.

Point a tool at the result as if it were a home directory:

```bash
cd merged && HOME=$(pwd) npx standout ...
```

`update.py` measures tokens and writes into this repo. `export_corpus.py` writes
redacted transcripts to `corpus/<machine>/`, which is **gitignored here on
purpose** — ~216 MB per machine, and this repo stays small enough to read.

### The other repository: what `deadreckon-record` can do

#### → https://github.com/matrixbuilderops/deadreckon-record

**The same folder structure and the same documents as this one** —
`human-readable/`, `machine-readable/`, one folder per machine, `STATS.md` at
both levels. What differs is where its numbers come from.

**What it holds**

```
<machine>/.claude/projects/-workspace-pNNN/*.jsonl   the conversations
<machine>/MANIFEST.json      what was exported, when, how much was redacted
<machine>/human-readable/    STATS for that computer, from its own transcripts
<machine>/machine-readable/  the same, as data
human-readable/              STATS · LIFETIME · COVERAGE
machine-readable/            stats.json
```

Every message keeps its uuid, sessionId, timestamp, model and all four usage
counters — untouched by redaction. That is what lets anyone recompute the
numbers rather than take them on trust.

**Its commands**, all run from this repository:

| command | does |
|---|---|
| `corpus_reports.py` | STATS · LIFETIME · COVERAGE, derived from the transcripts |
| `corpus_ship.py pack \| push \| pull \| unpack` | resumable archives, each 16 MB chunk re-checked against the source |
| `merge_corpus.py` | every machine into one `.claude/projects/` tree, renumbered and deduped |
| `count_corpus.py` | recount the transcripts and compare with the scans |
| `scrub_corpus.py` | re-apply today's redaction rules to an older export |
| `export_corpus.py` | produce this computer's folder in the first place |

**`COVERAGE.md` is the payoff.** Because both sides are computed independently,
it can publish the difference per machine and name the cause — which is how two
computers were found sitting in every table here and in no conversation there.

**What is deliberately not in it:** the account. That lives in a config file
which is never exported, so the corpus can count tokens but can never say whose
login spent them.

This repo counts by reading each tool's session files. That repo **holds the
conversations** and counts them directly. Nothing is copied between the two;
both are computed, from different inputs, by different code. So they are a
cross-check on each other rather than two views of one calculation — and
`deadreckon-record/human-readable/COVERAGE.md` publishes the difference per machine.
Right now that difference is 7,062,575,741 tokens, and it names two computers
that appear in every table here and in no conversation there.

**Only this repo can answer:**

- per **account** — which login spent what. The account lives in a config file
  that is deliberately never exported, so the corpus cannot know it.
- **every CLI** — Gemini, Copilot, Codex, Antigravity, Kilo Code, Grok, LM
  Studio. Only Claude Code transcripts are exported.
- the **floor** — usage whose transcripts are already deleted, recovered from
  `stats-cache.json`. The corpus can only hold what still existed at export.
- **first and last seen** per tool, including dates read from the editor's own
  state rather than from any transcript.

**Only that repo can answer:**

- what was actually **said** — the material behind every number here.
- per **project** and per **conversation** content, at message granularity.
- anything a profile tool needs. Counts alone tell those nothing; they parse
  message content for language, framework and repository signals.
- whether these numbers are **true** — it is the independent recount.

Neither is a subset of the other, which is why both exist.

### Where the corpus goes: `deadreckon-record`

A second repository, **private**, one folder per machine — the same shape as this
one, so two computers never touch the same files and never conflict:

```
deadreckon-record/
  hp-laptop-linux/     .claude/projects/…  README.md  MANIFEST.json
  macbook-air-m1/      …
```

**It already exists** — created 2026-08-04, private. Do not run `gh repo create`
for it; that fails with "name already exists". Clone it:

```bash
git clone --filter=blob:none https://github.com/matrixbuilderops/deadreckon-record.git ~/deadreckon-record
```

Then on each machine, after `export_corpus.py`:

```bash
cp -r corpus/* ~/deadreckon-record/
cd ~/deadreckon-count && python3 corpus_ship.py pack && python3 corpus_ship.py push

```

The clone above uses `--filter=blob:none` so it does not pull 4 GB of blobs, and
it is only needed to READ another machine's folder. Nothing is committed into it
— see *Do not git-commit transcripts*. Transcripts move as release assets.

**Private is not optional.** These are real conversations. Redaction removes
credentials, paths, third-party emails and protected project names — 559 secrets
were stripped from one machine's export — but redaction is a filter, not a
guarantee: it catches what matches a pattern, and prose describing something
sensitive matches nothing. Treat the corpus as readable-by-whoever-you-hand-it-to
and no wider.

Each machine's folder carries its own `README.md`, generated by the export,
explaining what was removed, what was kept, and how to verify it. That is written
for whoever receives the corpus, not for you — hand them the folder and they can
check every claim in it without asking you anything.

Why a second repo rather than a branch: this one is counts and is small; that one
is hundreds of megabytes of conversation. Different size, different audience,
different risk. Mixing them means every clone of the numbers drags the
transcripts along.

Why both: `update.py` answers *how many tokens*. Some tools need the transcripts
themselves — Standout parses message `content`, `input` and `summary` to derive
language, framework and repo signals, so counts alone tell it nothing.

**`export_corpus.py` redacts before writing, never after.** Transcripts contain
live credentials: 237 credential strings across 40 files on the machine this was
written on, and 559 secrets were removed from its export. It also strips home and
external-drive paths, third-party emails, and protected project names — the term
only, never the sentence around it, because wiping whole messages once destroyed
55% of the prompts and took the substance with it.

Timestamps, session ids, message uuids, models and usage blocks are preserved
deliberately. That is what lets anyone receiving the corpus check a figure
against it instead of taking it on trust.

Verify any export before it leaves the machine:

```bash
python3 -c "
import re,json,pathlib
KEEP='alexander.sorrell.it@gmail.com'
P={'secret':r'gh[pousr]_[A-Za-z0-9]{30,}|sk-ant-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{35}',
   'path':r'/home/|/media/|/Users/','email':r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'}
bad={k:0 for k in P}
def v(o):
    if isinstance(o,dict):
        for k,x in o.items(): v(k); v(x)
    elif isinstance(o,list): [v(x) for x in o]
    elif isinstance(o,str):
        for k,p in P.items():
            for m in re.findall(p,o):
                if k=='email' and KEEP in m: continue
                bad[k]+=1
for f in pathlib.Path('corpus').rglob('*.jsonl'):
    for ln in f.open(errors='ignore'):
        try: v(json.loads(ln))
        except Exception: pass
print(bad, 'CLEAN' if sum(bad.values())==0 else 'LEAKS — do not publish')"
```

Check the decoded JSON, not the raw file. Scanning raw bytes reports `\n@mcp.tool`
and `\n@pytest.fixture` as email addresses — 613 false positives on the first
run here, every one a Python decorator after an escaped newline.

### First run on a computer

It has to be told which folder is its own, once. After that a `.machine-id`
file in the folder remembers it, and plain `python3 update.py` is enough
forever after.

```bash
python3 update.py --machine <folder> --label "Human Readable Name"
```

The two computers that still need this are listed under
[Run it](#run-it) — the Windows Latitude has never been scanned, and the Linux
Latitude was scanned by a version that predates `.machine-id`.

The rest carry a `.machine-id` and claim themselves:

| Computer | Folder |
|---|---|
| Dell Inspiron Desktop Linux | `dell-inspiron-desktop-linux` |
| HP Laptop Linux | `hp-laptop-linux` |
| MacBook Air M1 | `macbook-air-m1` |
| ASUS Laptop Linux | `asus-laptop-linux` |

It refuses to guess. If it cannot identify the computer it stops and asks for
`--machine` rather than picking one — writing this computer's numbers into
another computer's folder produces output that looks entirely normal and is
wrong.

```bash
python3 update.py --list           # which folder does this computer resolve to?
python3 update.py --combine-only   # someone else pushed; re-derive without scanning
```

### Two things that matter

**`git pull` first is not optional.** `combine.py` globs `*/totals.json` — a
machine whose folder you have not pulled does not exist as far as the rollup is
concerned, so combining on a stale checkout publishes a root document that
silently drops whatever the others last pushed.

**`pip install cryptography` if this machine uses Antigravity.** Without it the
AES-encrypted conversation files are reported as unreadable rather than counted
as zero — on one machine here that was 23,580,539 tokens, 88% of Antigravity's
total. Everything else is standard library only.

### What a run writes

Into this computer's folder:

```
totals.json     Claude Code, per account: tokens, models, days, projects
sessions.json   every session from every CLI, plus readers, inventory and ledger
hardware.json   chip, cores, memory, GPU, OS, disk, accounts signed in
REPORT.md       this machine's own summary
by_*.csv        account / model / day / project, spreadsheet-friendly
.machine-id     which physical computer owns this folder
```

Readers run on every scan (8): `antigravity`, `claude`, `codex`, `copilot`, `gemini`, `grok`, `kilocode`, `lmstudio`.
A reader that finds nothing still reports a row of zeros saying whether the tool
was installed, so a missing tool can never look like a tool that was never
checked.

Then the root documents are re-derived from every machine folder present, and a
dated snapshot of all of them goes into `archive/`.

<details><summary>The individual steps, if you want to run them by hand</summary>

```bash
python3 analyze_tokens.py --out <folder> --label "<Name>"   # Claude Code, per account
python3 sessions.py       --out <folder>                    # every CLI, per session
python3 check_hardware.py --out <folder>                    # specs + accounts present
python3 combine.py                                          # root data + README tables
python3 stats_page.py                                       # the three reports
python3 check_consistency.py                                # prove it all adds up
```

</details>
### What the "automatic" part actually is

Nothing fires on a timer. There is no scheduler, no git hook, no CI — you run
`update.py`. What is automatic is *derivation*: one scan of one computer
regenerates every document, and no total, table, column or share is ever typed by
hand.

| Rebuilt on every run | Contents |
|---|---|
| `<folder>/` | this computer's own scan — totals, sessions, hardware, CSVs |
| [`machine-readable/ALL-COMPUTERS.json`](machine-readable/ALL-COMPUTERS.json) | the rollup, structured, for anything that reads it |
| **[`BY-COMPUTER.md`](human-readable/BY-COMPUTER.md)** | every machine: accounts, companies, CLIs, installed tools, sessions |
| **[`BY-ACCOUNT.md`](human-readable/BY-ACCOUNT.md)** | every login, across every machine |
| **[`BY-COMPANY.md`](human-readable/BY-COMPANY.md)** | every vendor, and what actually served the tokens |
| three tables in `README.md` | rewritten between the `BEGIN/END OVERVIEW`, `CLI` and `ACCOUNTS` markers |

Adding a computer, an account, a company or a whole new CLI needs no edit
anywhere: it appears in every table with all totals and shares recalculated.

The derivation step is deterministic — running `combine.py` and `stats_page.py`
twice over unchanged machine folders produces byte-identical documents apart from
the generated-at line, so rerunning is always safe. A full `update.py` does move
the numbers, because it rescans first and the machine has genuinely done more
work since. That is data changing, not output drifting.

Each computer writes only into its own folder and reads all the others from the
checkout, which is why `git pull` comes first: `combine.py` can only roll up
folders that are actually present, so combining on a stale checkout publishes a
root document missing whatever the others last pushed.

**Every run proves its own arithmetic.** `check_consistency.py` runs last and
asserts that each slice is a real partition — accounts, companies and computers
must each sum to the same grand total, every account's models and buckets must
sum to its own total, and `analyze_tokens.py` and `sessions.py` must agree per
machine despite being separate code counting by different units. If any check
fails, `update.py` exits non-zero and says not to quote the numbers, because a
total that is 3% wrong reads exactly like a total that is right.

That last check needs one allowance, and getting it wrong in either direction
matters. The two scanners run one after the other, so on the computer you are
working on right now a live session writes more tokens in between — the first
time this ran it reported a 284,127 drift that was simply this session growing
mid-scan. The tolerance is therefore bounded by exactly that: tokens in sessions
still being written when the first scan finished. A blanket percentage would have
been easier and would have swallowed real bugs. Injecting a 5,000,000,000 drift
still fails it, with `only 652,301,478 is attributable to sessions still being
written`.

The registries catch what arithmetic cannot: a computer in `machines.json` with
no folder is reported `❌ never scanned`, and an account in `accounts.json` that
no scan has seen is flagged as absent from every total.

## The three reports

`stats.py` answers one question at a time from the command line. These are the
whole set written down, one file per question people actually ask:

| Report | What it holds |
|---|---|
| **[BY-COMPUTER.md](human-readable/BY-COMPUTER.md)** | totals, the two-scope reconciliation, then per machine: its accounts, companies, CLIs, **every AI tool installed on it**, and cross-tabs. Ends with the longest and heaviest sessions and the busiest days. |
| **[BY-ACCOUNT.md](human-readable/BY-ACCOUNT.md)** | every login across every computer — the number that matters, since the same account is driven from several machines and none can see another's sessions. Per account: computers, companies, models, token buckets. Flags any known account no scan has found. |
| **[BY-COMPANY.md](human-readable/BY-COMPANY.md)** | every vendor and what it was actually paid for, plus who served the tokens versus who was paid for the tool. Per company: models, computers, accounts. |

Three files rather than one, because these are three different questions and a
single page meant scrolling past two of them to reach the third. All three are
generated from one aggregation in a single pass, so they cannot disagree with
each other, and each carries the same header totals.

Per computer, the folder holds the raw material behind all of it:

```
<machine>/totals.json     Claude Code per account: tokens, models, days, projects
<machine>/sessions.json   every session from every CLI, plus readers and inventory
<machine>/hardware.json   chip, cores, memory, GPU, OS, disk, accounts signed in
<machine>/REPORT.md       that machine's own summary
<machine>/by_*.csv        account / model / day / project, spreadsheet-friendly
<machine>/.machine-id     which physical computer owns this folder
```

**The two scopes are never added.** *Claude Code* (per account, every machine)
and *every AI CLI* (per session, scanned machines only) overlap — the second
contains the first. Summing them double-counts every Claude Code token on any
machine that ran both scanners, so the page states the overlap instead of hiding
it.

Hardware is recorded because token counts are not comparable without it. A number
from a 16 GB laptop and a number from a workstation describe different work, and a
machine folder that doesn't say which it came from can't be read later.
`check_hardware.py` takes the account list from the same place `analyze_tokens.py`
does — each config directory's own `.claude.json` — so the two files can never
disagree about who was signed in.

The rollup exists because **the per-account total across machines is the only real
number.** The same account gets driven from several computers, and no machine's
session files can see any other machine's. Each folder is a partial view.

## Where the numbers come from

Claude Code stores every conversation as JSONL under a config directory:

```
<config-dir>/projects/<slugified-cwd>/<session-uuid>.jsonl
```

One JSON object per line. Assistant turns carry a `message.usage` object, which is
the API's own accounting:

| Field | Meaning |
|---|---|
| `input_tokens` | uncached prompt tokens |
| `cache_creation_input_tokens` | tokens written into the prompt cache |
| `cache_read_input_tokens` | tokens served from cache |
| `output_tokens` | generated tokens |

All four are billed, at different rates, so the totals here add all four. Cache
reads dominate by a wide margin on long sessions — that is expected, not an error:
every turn re-reads the whole conversation, so a session's context is billed once
per turn as a cache read.

## Three things that make a naive count wrong

**Multiple accounts on one machine.** `$CLAUDE_CONFIG_DIR` selects the config
directory, so a machine can hold several accounts side by side (`~/.claude`,
`~/.claude-main`, `~/.claude-it`). Scanning only the default directory measures
one account and silently reports it as the total. Each directory's own
`.claude.json` names the account it is signed into, so this reads the account from
the data instead of assuming it.

The default profile is the exception worth knowing: its state lives in
`~/.claude.json`, *not* `~/.claude/.claude.json`.

**Spawned work is nested, not flat.** Subagents and workflow agents get their own
transcripts underneath the session that started them:

```
<proj>/<session>.jsonl                                 main session
<proj>/<session>/subagents/agent-<id>.jsonl            subagent
<proj>/<session>/subagents/workflows/wf_<id>/….jsonl   workflow agent
```

Each is a separate API conversation with separate billing. A flat glob over
`projects/*/*.jsonl` finds only the main sessions — on the machine measured here
that is 61 files out of 2,812, and it undercounted the total by 20%. The report
breaks the three tiers out so the fan-out is visible.

**The same turn can appear twice.** Resuming a session rewrites earlier turns into
the new file, and a subagent's turns are also inlined into its parent transcript as
sidechain records. Both copies carry the same message `uuid`, so everything is
deduplicated on it.

## Every script

`run.py` calls all of these. They also work on their own when you want one step.

| script | does |
|---|---|
| **`run.py`** | **the five verbs — start here** |
| `paths.py` | where every generated file lives. One definition, imported by all |
| `stores.py` | where every **CLI** keeps its records. One definition, same idea |
| `update.py` | scan this computer, then rebuild every document |
| `analyze_tokens.py` | Claude Code, per account → `totals.json` |
| `sessions.py` | all 8 CLIs, per session → `sessions.json` |
| `check_hardware.py` | CPU/RAM/disk → `hardware.json` |
| `combine.py` | rolls the machine folders into `ALL-COMPUTERS.json` + README tables |
| `stats_page.py` | BY-COMPUTER · BY-ACCOUNT · BY-COMPANY |
| `fun_stats.py` | STATS.md, fleet and per computer, at human scale |
| `monthly.py` | LIFETIME + THIS-MONTH; freezes a month once it closes |
| `scorecard.py` | did this computer's run actually work — per machine |
| `check_consistency.py` | 39 checks; **refuses to publish** if a slice doesn't add up |
| `test_scanner.py` | 35 assertions on the arithmetic; runs **before** any scan |
| `adversarial.py` | 6 attacks that keep every sum intact, judged against a control |
| `sweep_usage.py` | finds usage data by CONTENT that no reader claims |
| `retention_guard.py` | stops CLIs deleting history; runs as a service |
| `token_ledger.py` | the append-only lifetime total a deletion cannot shrink |
| `adversarial_daemon.py` | 12 attacks on the daemon: every one is a success that wasn't |
| `export_corpus.py` | redacted transcripts → `corpus/<machine>/` |
| `scrub_corpus.py` | re-apply today's redaction rules to an older export |
| `corpus_reports.py` | the same reports, derived from the conversations |
| `count_corpus.py` | independent recount: corpus vs scanner |
| `merge_corpus.py` | every machine into one `.claude/projects/` tree |
| `corpus_ship.py` | pack / push / pull / unpack — resumable, chunk-verified |
| `digest.py` | 30-day windows, a few KB each |
| `archive_all.py` | dated snapshot of everything before a fleet-wide rescan |
| `retire_archive.py` | move development churn and stale machines aside |
| `stats.py` | ad-hoc per-session queries |

## Layout

Every folder — the root and each machine — splits the same two ways:

```
human-readable/     what a person reads.  Generated. Never an input.
machine-readable/   what a program reads and rewrites. The source.
```

Nothing under `machine-readable/` is hand-written, and everything under
`human-readable/` can be thrown away and rebuilt from it. A directory holding
`totals.json` next to `BY-COMPANY.md` gave no hint which was which; they are not
peers.

```
README.md                 you are here
machines.json             AUTHORED — the fleet roster
accounts.json             AUTHORED — labels for emailless profiles
human-readable/           BY-COMPUTER · BY-ACCOUNT · BY-COMPANY · STATS
machine-readable/         ALL-COMPUTERS.json

<machine>/
  .machine-id             which computer owns this folder
  human-readable/         REPORT · STATS · SCORECARD  (the same documents, for it alone)
  machine-readable/       totals · sessions · hardware · stats · scorecard · 4 CSVs
```

The per-machine `STATS.md` comes out of the same renderer as the fleet one, over
a different slice — so a computer's own figures cannot drift from the collective
ones. They are one implementation, not two that have to agree.

```
update.py               ONE COMMAND: scan this computer, rebuild every document
analyze_tokens.py       the per-machine token scanner (Claude Code, per account)
sessions.py             per-session records across every CLI on the machine
stats.py                query the session records — longest, heaviest, streaks
check_hardware.py       records machine specs + accounts signed in on it
combine.py              rolls every machine folder into the all-computers report
stats_page.py           writes the three reports: computers, accounts, companies
check_consistency.py    asserts every slice is a real partition of the total
machines.json           the known fleet, so unscanned computers read as gaps
accounts.json           the known accounts, and labels for the emailless profiles
BY-COMPUTER.md          every machine: accounts, companies, CLIs, tools, sessions
BY-ACCOUNT.md           every login across every machine
BY-COMPANY.md           every vendor, models, machines, accounts
ALL-COMPUTERS.json      the same, structured
<machine>/REPORT.md     human-readable summary for one machine
<machine>/totals.json   full structured output for one machine
<machine>/sessions.json every session on that machine, every CLI
<machine>/hardware.json specs + accounts for that machine
<machine>/.machine-id   which computer owns this folder, so it is never re-guessed
<machine>/by_*.csv      account / model / day / project breakdowns
```

`analyze_tokens.py` and `sessions.py` are deliberately separate. The first answers
*how much did this account spend*, reading only Claude Code's own transcripts; the
second answers *which session, how long, how heavy*, across every CLI. Merging them
would force one file to hold two different notions of what a row is.

### Did the daemon come back? — `--verify-boot`

```
python3 retention_guard.py --verify-boot
```

`Restart=always` is provable with a SIGKILL. Surviving a **reboot** is a
different claim, and it cannot be checked from memory: a reboot ends whatever
was watching. So the daemon writes down that it started, stamped with the
kernel's `boot_id` — a fresh random value on every boot, and the one thing a
process cannot fake by claiming to have restarted.

The question then becomes arithmetic rather than recollection: *is there a
record for the boot_id this machine is running under right now, and how many
seconds after boot did it appear.*

```
  PASS  the daemon came back under the CURRENT boot, and is running
        1 boot(s) with a record; pid 2223247 alive of 2 start(s) this boot
```

**A recorded start is not proof of a running daemon**, and the first version of
this check made exactly that mistake — the pid was written and never read back,
so `systemctl stop`, a disable, a dangling `ExecStart` or a wedged tick all
printed PASS and exited 0. It reads `/proc` now, matching on **cmdline** rather
than the bare pid, because pids get reused.

Both obvious rules for *which* record to check are wrong. **First** is wrong:
`Restart=always` means a healthy daemon has several starts per boot and the
earliest pid is dead by definition. **Last** is wrong too, and it FAILED a
demonstrably healthy daemon — `MainPID 2223247` running while the newest row
held a dead 2245983 from a stray invocation. The question is *"is any daemon
from this boot alive"*, so every row is kept and any live pid answers it.

Three exit codes, because there are three answers:

```
0   came back, and is running
1   did not come back, OR started and is now dead   (the message says which)
2   cannot tell — no /proc. macOS and Windows: ask the service manager
```

That third one matters: `_boot_id()` returns `""` on a platform without `/proc`,
and every record would carry `""` too, so `"" in seen` is permanently true and it
would print PASS forever on a machine it cannot observe at all.

A large `after boot` means the record was written by a manual restart long into
an existing boot, not by the boot itself. After a real reboot the number is
small and the `boot_id` is new.
