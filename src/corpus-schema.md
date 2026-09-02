# Shared Corpus Schema (JSONL)

Both Starreckon and Deadreckon read/write this format.

## Line Format
Each line is a valid JSON object:
{
  "id": "unique-hash-or-uuid",
  "source_path": "/absolute/path/to/transcript.txt",
  "relative_path": "repo/subdir/transcript.txt",
  "timestamp": "ISO8601_string",
  "tool_origin": "deadreckon" | "starreckon",
  "counts": {
    "raw_chars": 12345,
    "raw_tokens_est": 1500,
    "model_specific_tokens": 1520,
    "model_name": "generic" | "claude-3" | etc
  },
  "status": "ok" | "partial" | "error",
  "error_msg": null | "description if failed"
}

## Rules
1. UTF-8 encoding.
2. One JSON object per line (JSONL).
3. Missing optional fields should be null.
4. Both tools must handle malformed lines gracefully (skip & log).
5. Both tools must operate in "Generic Mode" if model configs are missing.
