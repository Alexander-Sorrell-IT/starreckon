#!/usr/bin/env python3
"""
Deadreckon Corpus Reader - Reads Starreckon corpus files for comparison.
Handles malformed lines, missing fields, and foreign schema gracefully.
"""
import sys
import json
from pathlib import Path

def read_starreckon_corpus(filepath):
    """Read Starreckon corpus file with error handling."""
    filepath = Path(filepath)
    if not filepath.exists():
        print(f"Error: File {filepath} not found", file=sys.stderr)
        return []
    
    entries = []
    line_num = 0
    errors = 0
    
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line_num += 1
            line = line.strip()
            if not line:
                continue
            
            try:
                entry = json.loads(line)
                # Validate minimal schema
                if "id" not in entry or "source_path" not in entry:
                    print(f"Warning: Line {line_num} missing required fields, skipping", file=sys.stderr)
                    errors += 1
                    continue
                
                # Normalize tool_origin if missing
                if "tool_origin" not in entry:
                    entry["tool_origin"] = "starreckon"
                
                entries.append(entry)
                
            except json.JSONDecodeError as e:
                print(f"Warning: Line {line_num} malformed JSON: {e}, skipping", file=sys.stderr)
                errors += 1
                continue
    
    print(f"Read {len(entries)} entries from {filepath} ({errors} errors)", file=sys.stderr)
    return entries

def compare_corpora(deadreckon_file, starreckon_file):
    """Compare two corpus files and report discrepancies."""
    dr_entries = {}
    sr_entries = read_starreckon_corpus(starreckon_file)
    
    # Load deadreckon corpus
    if Path(deadreckon_file).exists():
        with open(deadreckon_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if "id" in entry:
                        dr_entries[entry["id"]] = entry
                except:
                    continue
    
    # Compare by ID
    matches = 0
    mismatches = 0
    missing_in_sr = 0
    missing_in_dr = 0
    
    for entry_id, dr_entry in dr_entries.items():
        if entry_id in sr_entries:
            sr_entry = sr_entries[entry_id] if isinstance(sr_entries, dict) else next((e for e in sr_entries if e.get("id") == entry_id), None)
            if sr_entry:
                dr_tokens = dr_entry.get("counts", {}).get("raw_tokens_est", 0)
                sr_tokens = sr_entry.get("counts", {}).get("raw_tokens_est", 0)
                if dr_tokens == sr_tokens:
                    matches += 1
                else:
                    mismatches += 1
                    print(f"Mismatch for {entry_id}: DR={dr_tokens}, SR={sr_tokens}")
            else:
                missing_in_sr += 1
        else:
            missing_in_sr += 1
    
    # Check for entries only in starreckon
    if isinstance(sr_entries, list):
        for sr_entry in sr_entries:
            if sr_entry.get("id") not in dr_entries:
                missing_in_dr += 1
    
    print(f"\n=== Parity Report ===")
    print(f"Matches: {matches}")
    print(f"Mismatches: {mismatches}")
    print(f"Missing in Starreckon: {missing_in_sr}")
    print(f"Missing in Deadreckon: {missing_in_dr}")
    
    return mismatches == 0

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: corpus_reader.py <starreckon_corpus.jsonl> [deadreckon_corpus.jsonl]")
        sys.exit(1)
    
    sr_file = sys.argv[1]
    dr_file = sys.argv[2] if len(sys.argv) > 2 else "deadreckon_corpus.jsonl"
    
    if len(sys.argv) > 2:
        success = compare_corpora(dr_file, sr_file)
        sys.exit(0 if success else 1)
    else:
        entries = read_starreckon_corpus(sr_file)
        print(f"Successfully parsed {len(entries)} entries")
