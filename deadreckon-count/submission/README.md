# Submission pack

Four documents, one corpus. Everything here was produced by running a tool over
the same input — 20,217 redacted transcripts, 401 project folders, five
computers — with each tool in its own container and the corpus mounted
read-only.

| file | what it is |
|---|---|
| [01-standout-result.md](01-standout-result.md) | their tool's output, and the payload it was about to upload |
| [02-starforge-result.md](02-starforge-result.md) | starforge's output on the same corpus |
| [03-the-difference.md](03-the-difference.md) | what actually differs, mechanism by mechanism |
| [04-the-118-billion.md](04-the-118-billion.md) | where the 118,688,898,254 comes from and why it holds |

**The single most useful fact in this pack:** the two tools independently agree
to within 0.07% on every shared measure. Numbers one tool produces are a claim.
Numbers two unrelated implementations derive from the same bytes are a
measurement. Everything else here rests on that.
