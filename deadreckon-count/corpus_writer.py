#!/usr/bin/env python3
"""
Deadreckon Corpus Writer - Generates standardized JSONL corpus files.
Handles missing models/daemons by falling back to generic counting.
"""
import os
import sys
import json
import hashlib
from datetime import datetime
from pathlib import Path

def generic_token_count(text):
    """Fallback token counter when models are unavailable."""
    if not text:
        return 0
    # Simple whitespace split as fallback
    return len(text.split())

def get_file_hash(filepath):
    """Generate unique ID based on file content."""
    try:
        with open(filepath, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except Exception:
        return hashlib.sha256(str(datetime.now()).encode()).hexdigest()[:16]

def process_file(filepath, base_dir="."):
    """Process a single transcript file into corpus entry."""
    filepath = Path(filepath)
    abs_path = str(filepath.absolute())
    rel_path = str(filepath.relative_to(Path(base_dir).absolute())) if base_dir else str(filepath.name)
    
    entry = {
        "id": get_file_hash(filepath),
        "source_path": abs_path,
        "relative_path": rel_path,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "tool_origin": "deadreckon",
        "counts": {
            "raw_chars": 0,
            "raw_tokens_est": 0,
            "model_specific_tokens": None,
            "model_name": "generic"
        },
        "status": "ok",
        "error_msg": None
    }
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        entry["counts"]["raw_chars"] = len(content)
        entry["counts"]["raw_tokens_est"] = generic_token_count(content)
        
        # Try to load model-specific logic if available
        try:
            models_config = Path("models.json")
            if models_config.exists():
                # Would load specific model logic here
                entry["counts"]["model_name"] = "configured"
        except Exception:
            pass  # Stay in generic mode
            
    except Exception as e:
        entry["status"] = "error"
        entry["error_msg"] = str(e)
    
    return entry

def scan_directory(target_dir, output_file="deadreckon_corpus.jsonl"):
    """Scan directory for transcripts and write corpus."""
    target = Path(target_dir)
    if not target.exists():
        print(f"Error: Directory {target_dir} does not exist", file=sys.stderr)
        sys.exit(1)
    
    entries = []
    for ext in ['*.txt', '*.md', '*.json', '*.log']:
        for filepath in target.rglob(ext):
            if filepath.is_file():
                entry = process_file(filepath, target_dir)
                entries.append(entry)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for entry in entries:
            f.write(json.dumps(entry) + '\n')
    
    print(f"Wrote {len(entries)} entries to {output_file}")
    return entries

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    output = sys.argv[2] if len(sys.argv) > 2 else "deadreckon_corpus.jsonl"
    scan_directory(target, output)
