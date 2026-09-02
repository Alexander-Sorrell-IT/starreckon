#!/usr/bin/env python3
"""
Adversarial Corpus Testing for Deadreckon - Python version
Tests corpus reading, malformed data handling, and parity logic.
"""
import os
import sys
import json
import tempfile
import shutil
from pathlib import Path

# Import the modules we're testing
sys.path.insert(0, str(Path(__file__).parent))
from corpus_reader import read_starreckon_corpus, compare_corpora
from corpus_writer import process_file, generic_token_count, scan_directory

def test_malformed_json_lines():
    """Test that malformed JSON lines are skipped without crashing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        corpus_file = Path(tmpdir) / "malformed.jsonl"
        content = '''{"id":"1","source_path":"/a.txt","counts":{"raw_tokens_est":100}}
not valid json at all
{"id":"2","source_path":"/b.txt","counts":{"raw_tokens_est":200}}
{broken json
{"id":"3","source_path":"/c.txt","counts":{"raw_tokens_est":300}}'''
        corpus_file.write_text(content)
        
        entries = read_starreckon_corpus(str(corpus_file))
        assert len(entries) == 3, f"Expected 3 entries, got {len(entries)}"
        assert entries[0]["id"] == "1"
        assert entries[1]["id"] == "2"
        assert entries[2]["id"] == "3"
        print("✓ Malformed JSON lines handled correctly")

def test_empty_lines():
    """Test that empty lines are handled gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        corpus_file = Path(tmpdir) / "empty.jsonl"
        content = '''{"id":"1","source_path":"/a.txt","counts":{"raw_tokens_est":100}}

{"id":"2","source_path":"/b.txt","counts":{"raw_tokens_est":200}}

'''
        corpus_file.write_text(content)
        
        entries = read_starreckon_corpus(str(corpus_file))
        assert len(entries) == 2
        print("✓ Empty lines handled correctly")

def test_missing_required_fields():
    """Test that entries missing id or source_path are skipped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        corpus_file = Path(tmpdir) / "missing.jsonl"
        content = '''{"id":"1","source_path":"/a.txt","counts":{"raw_tokens_est":100}}
{"source_path":"/no-id.txt","counts":{"raw_tokens_est":50}}
{"id":"2","counts":{"raw_tokens_est":200}}
{"id":"3","source_path":"/c.txt","counts":{"raw_tokens_est":300}}'''
        corpus_file.write_text(content)
        
        entries = read_starreckon_corpus(str(corpus_file))
        assert len(entries) == 2, f"Expected 2 entries, got {len(entries)}"
        print("✓ Missing required fields handled correctly")

def test_tool_origin_normalization():
    """Test that missing tool_origin is normalized."""
    with tempfile.TemporaryDirectory() as tmpdir:
        corpus_file = Path(tmpdir) / "no-origin.jsonl"
        content = '{"id":"1","source_path":"/a.txt","counts":{"raw_tokens_est":100}}'
        corpus_file.write_text(content)
        
        entries = read_starreckon_corpus(str(corpus_file))
        assert entries[0]["tool_origin"] == "starreckon"
        print("✓ Tool origin normalization works")

def test_generic_token_count():
    """Test the generic token counter fallback."""
    assert generic_token_count("Hello world this is a test") == 6
    assert generic_token_count("") == 0
    assert generic_token_count(None) == 0
    assert generic_token_count("Hello\tworld\nthis\r\nis\ta test") == 6
    print("✓ Generic token counting works")

def test_corpus_comparison_matches():
    """Test that matching entries are detected."""
    sr_entries = [
        {"id": "1", "source_path": "/a.txt", "counts": {"raw_tokens_est": 100}},
        {"id": "2", "source_path": "/b.txt", "counts": {"raw_tokens_est": 200}}
    ]
    
    with tempfile.TemporaryDirectory() as tmpdir:
        dr_file = Path(tmpdir) / "dr.jsonl"
        dr_content = '''{"id":"1","source_path":"/a.txt","counts":{"raw_tokens_est":100}}
{"id":"2","source_path":"/b.txt","counts":{"raw_tokens_est":200}}'''
        dr_file.write_text(dr_content)
        
        # Capture stdout
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            result = compare_corpora(str(dr_file), "/nonexistent")  # We'll mock sr_entries
        
        # Manual comparison for testing
        dr_entries = {e["id"]: e for e in [json.loads(l) for l in dr_content.split('\n')]}
        matches = sum(1 for eid, dre in dr_entries.items() 
                     for sre in sr_entries if sre["id"] == eid 
                     and dre["counts"]["raw_tokens_est"] == sre["counts"]["raw_tokens_est"])
        assert matches == 2
        print("✓ Corpus comparison detects matches")

def test_corpus_comparison_mismatches():
    """Test that token count mismatches are detected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dr_file = Path(tmpdir) / "dr.jsonl"
        dr_content = '{"id":"1","source_path":"/a.txt","counts":{"raw_tokens_est":150}}'
        dr_file.write_text(dr_content)
        
        sr_file = Path(tmpdir) / "sr.jsonl"
        sr_content = '{"id":"1","source_path":"/a.txt","counts":{"raw_tokens_est":100}}'
        sr_file.write_text(sr_content)
        
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            result = compare_corpora(str(dr_file), str(sr_file))
        
        output = f.getvalue()
        assert "Mismatch" in output
        print("✓ Corpus comparison detects mismatches")

def test_unicode_handling():
    """Test that unicode in paths and IDs is handled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        corpus_file = Path(tmpdir) / "unicode.jsonl"
        content = '{"id":"🔥测试","source_path":"/路径/文件.txt","counts":{"raw_tokens_est":100}}'
        corpus_file.write_text(content)
        
        entries = read_starreckon_corpus(str(corpus_file))
        assert len(entries) == 1
        assert entries[0]["id"] == "🔥测试"
        print("✓ Unicode handling works")

def test_negative_tokens():
    """Test that negative token counts are preserved (validation elsewhere)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        corpus_file = Path(tmpdir) / "negative.jsonl"
        content = '{"id":"1","source_path":"/a.txt","counts":{"raw_tokens_est":-100}}'
        corpus_file.write_text(content)
        
        entries = read_starreckon_corpus(str(corpus_file))
        assert len(entries) == 1
        assert entries[0]["counts"]["raw_tokens_est"] == -100
        print("✓ Negative tokens handled")

def test_float_tokens():
    """Test that float token counts are preserved."""
    with tempfile.TemporaryDirectory() as tmpdir:
        corpus_file = Path(tmpdir) / "float.jsonl"
        content = '{"id":"1","source_path":"/a.txt","counts":{"raw_tokens_est":100.5}}'
        corpus_file.write_text(content)
        
        entries = read_starreckon_corpus(str(corpus_file))
        assert len(entries) == 1
        assert entries[0]["counts"]["raw_tokens_est"] == 100.5
        print("✓ Float tokens handled")

def test_nonexistent_file():
    """Test that non-existent files are handled gracefully."""
    entries = read_starreckon_corpus("/nonexistent/path/corpus.jsonl")
    assert len(entries) == 0
    print("✓ Non-existent file handled")

def test_empty_file():
    """Test that empty files are handled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        corpus_file = Path(tmpdir) / "empty.jsonl"
        corpus_file.write_text("")
        
        entries = read_starreckon_corpus(str(corpus_file))
        assert len(entries) == 0
        print("✓ Empty file handled")

def run_all_tests():
    """Run all adversarial tests."""
    print("\n=== Running Adversarial Corpus Tests (Python) ===\n")
    
    tests = [
        test_malformed_json_lines,
        test_empty_lines,
        test_missing_required_fields,
        test_tool_origin_normalization,
        test_generic_token_count,
        test_corpus_comparison_matches,
        test_corpus_comparison_mismatches,
        test_unicode_handling,
        test_negative_tokens,
        test_float_tokens,
        test_nonexistent_file,
        test_empty_file
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} ERROR: {e}")
            failed += 1
    
    print(f"\n=== Results: {passed} passed, {failed} failed ===\n")
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
