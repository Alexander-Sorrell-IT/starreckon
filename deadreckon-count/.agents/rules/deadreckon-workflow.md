# Deadreckon Project Rules

## Working Protocol (MUST FOLLOW)

1. **Git commits are mandatory.** After every meaningful change, `git add` + `git commit` + `git push`. Do not accumulate uncommitted work.

2. **Update the plan file after every commit.** The plan file is at the repo root: `PLAN-enhancement.md`. After each commit, update it to show:
   - What was just completed and WHY it was done that way
   - What is left to do
   - Current state of the repo (HEAD commit hash)
   - Any decisions made and their rationale

3. **The plan file is the handoff document.** Another AI (or the same AI with fresh context) will resume from where you left off. The plan must contain enough context that they can pick up immediately without asking the user to re-explain.

4. **Do not assume who made changes.** The user (a human) may have made local edits between sessions. Always check `git log` and `git status` before starting work.

5. **Explain WHY, not just WHAT.** Every commit message, plan update, and comment should explain the reasoning, not just describe the change.

## Project Context

- **Repo**: `deadreckon-count` -- a token-counting and AI tool tracking system
- **Sibling repo**: `deadreckon-record` -- redacted transcripts (evidence)
- **Owner**: matrixbuilderops (GitHub), matrixbuilderops@proton.me
- **Current enhancement project**: Two-section config (clis.json + programs.json), 4 Cisco AI models as optional components, dual test framework, graceful degradation

## Codebase Conventions

- **Authored files** (hand-edited): machines.json, accounts.json, cli-config.json, clis.json, programs.json
- **Machine-readable** (never hand-edit): totals.json, sessions.json, hardware.json
- **Human-readable** (never program input): all .md reports
- Four install states: DONE, ALREADY, SKIPPED, FAILED -- no fifth state
- Comments document past failures, not just current behavior
- The `_comment` field in JSON files is for documentation

## The Plan File

The plan file (`PLAN-enhancement.md`) should always say to save these rules into memory. If you are an AI reading this for the first time, use `/learn` to persist this knowledge.
