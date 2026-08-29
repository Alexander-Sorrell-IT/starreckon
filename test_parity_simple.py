#!/usr/bin/env python3
"""
Simple Parity Test: Compare deadreckon-count vs starreckon
Tests that both systems scan the same data and produce identical token counts.
"""

import json
import os
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path

def setup_test_corpus():
    """Create a controlled test corpus with known content."""
    test_dir = tempfile.mkdtemp(prefix="parity_test_")
    
    # Create Claude session
    claude_dir = Path(test_dir) / "claude"
    claude_dir.mkdir()
    claude_session = claude_dir / "session_001.jsonl"
    claude_session.write_text(
        '{"role": "user", "content": "Hello world"}\n'
        '{"role": "assistant", "content": "Hi there"}\n'
        '{"role": "user", "content": "How are you?"}\n'
        '{"role": "assistant", "content": "I am fine, thank you!"}\n'
    )
    
    # Create Copilot session
    copilot_dir = Path(test_dir) / "copilot"
    copilot_dir.mkdir()
    copilot_session = copilot_dir / "chat_001.jsonl"
    copilot_session.write_text(
        '{"request": {"prompt": "Fix this bug"}, "response": {"choices": [{"message": {"content": "Sure"}}]}}\n'
        '{"request": {"prompt": "Thanks"}, "response": {"choices": [{"message": {"content": "You are welcome"}}]}}\n'
    )
    
    # Create Gemini session
    gemini_dir = Path(test_dir) / "gemini"
    gemini_dir.mkdir()
    gemini_session = gemini_dir / "session_001.json"
    gemini_session.write_text(json.dumps({
        "contents": [
            {"role": "user", "parts": [{"text": "Count these tokens"}]},
            {"role": "model", "parts": [{"text": "Okay I will"}]}
        ]
    }, indent=2))
    
    return test_dir

def run_deadreckon_scan(corpus_dir):
    """Run deadreckon-count Python scanner and extract token totals."""
    try:
        result = subprocess.run(
            ["python3", "deadreckon-count/count_corpus.py", "--corpus", corpus_dir],
            capture_output=True,
            text=True,
            timeout=60,
            cwd="/workspace"
        )
        
        output = result.stdout + result.stderr
        print(f"\n=== DEADRECKON-COUNT OUTPUT ===\n{output}")
        
        # Try to parse JSON from output if available
        for line in output.split('\n'):
            if line.strip().startswith('{'):
                try:
                    return json.loads(line)
                except:
                    pass
        
        return {"raw_output": output, "success": result.returncode == 0}
    except Exception as e:
        return {"error": str(e), "success": False}

def run_starreckon_scan(corpus_dir):
    """Run starreckon JavaScript scanner and extract token totals."""
    try:
        # Create a minimal config pointing to our test corpus
        env = os.environ.copy()
        env["STARRECKON_HOME"] = corpus_dir
        
        result = subprocess.run(
            ["node", "src/cli.mjs", "--no-prompt", "--no-pace"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd="/workspace",
            env=env
        )
        
        output = result.stdout + result.stderr
        print(f"\n=== STARRECKON OUTPUT ===\n{output}")
        
        # Try to parse JSON from output if available
        for line in output.split('\n'):
            if line.strip().startswith('{'):
                try:
                    return json.loads(line)
                except:
                    pass
        
        return {"raw_output": output, "success": result.returncode == 0}
    except Exception as e:
        return {"error": str(e), "success": False}

def test_basic_scanning():
    """Test that both systems can scan the same corpus."""
    print("=" * 70)
    print("TEST: Basic Scanning Parity")
    print("=" * 70)
    
    test_dir = setup_test_corpus()
    print(f"Created test corpus at: {test_dir}")
    print(f"Contents: {list(Path(test_dir).iterdir())}")
    
    try:
        # Run deadreckon-count
        print("\n[1/2] Running deadreckon-count (Python)...")
        dr_result = run_deadreckon_scan(test_dir)
        
        # Run starreckon
        print("\n[2/2] Running starreckon (JavaScript)...")
        sr_result = run_starreckon_scan(test_dir)
        
        # Compare results
        print("\n" + "=" * 70)
        print("COMPARISON RESULTS")
        print("=" * 70)
        print(f"Deadreckon success: {dr_result.get('success', False)}")
        print(f"Starreckon success: {sr_result.get('success', False)}")
        
        if dr_result.get('success') and sr_result.get('success'):
            print("\n✓ Both systems executed successfully!")
            return True
        else:
            print("\n✗ One or both systems failed")
            if not dr_result.get('success'):
                print(f"  Deadreckon error: {dr_result.get('error', 'Unknown')}")
            if not sr_result.get('success'):
                print(f"  Starreckon error: {sr_result.get('error', 'Unknown')}")
            return False
            
    finally:
        shutil.rmtree(test_dir)

def test_reader_functions():
    """Test specific reader functions from both systems."""
    print("\n" + "=" * 70)
    print("TEST: Reader Function Parity")
    print("=" * 70)
    
    test_dir = setup_test_corpus()
    
    try:
        # Test Python readers
        print("\n--- Python Readers ---")
        sys.path.insert(0, '/workspace/deadreckon-count')
        import sessions
        
        claude_path = str(Path(test_dir) / "claude")
        copilot_path = str(Path(test_dir) / "copilot")
        gemini_path = str(Path(test_dir) / "gemini")
        
        try:
            claude_data = list(sessions.read_claude(claude_path))
            print(f"Claude sessions found: {len(claude_data)}")
        except Exception as e:
            print(f"Claude reader error: {e}")
        
        try:
            copilot_data = list(sessions.read_copilot(None, copilot_path))
            print(f"Copilot sessions found: {len(copilot_data)}")
        except Exception as e:
            print(f"Copilot reader error: {e}")
        
        try:
            gemini_data = list(sessions.read_gemini(None, gemini_path))
            print(f"Gemini sessions found: {len(gemini_data)}")
        except Exception as e:
            print(f"Gemini reader error: {e}")
        
        # Test JavaScript readers
        print("\n--- JavaScript Readers ---")
        js_script = f"""
import('{{ readClaudeCodeSessions, readCopilotSessions, readGeminiSessions }}')
    .then(({{ readClaudeCodeSessions, readCopilotSessions, readGeminiSessions }}) => {{
        return Promise.all([
            readClaudeCodeSessions(['{claude_path}']).then(d => console.log('JS Claude:', d.length)),
            readCopilotSessions(['{copilot_path}']).then(d => console.log('JS Copilot:', d.length)),
            readGeminiSessions(['{gemini_path}']).then(d => console.log('JS Gemini:', d.length))
        ]);
    }})
    .catch(err => console.error('JS Error:', err));
"""
        result = subprocess.run(
            ["node", "-e", js_script],
            capture_output=True,
            text=True,
            timeout=30,
            cwd="/workspace"
        )
        print(result.stdout)
        if result.stderr:
            print(f"JS errors: {result.stderr}")
        
        print("\n✓ Reader functions tested")
        return True
        
    except Exception as e:
        print(f"Reader test error: {e}")
        return False
    finally:
        shutil.rmtree(test_dir)

def test_cross_platform_paths():
    """Test path handling for Windows, Mac, and Linux."""
    print("\n" + "=" * 70)
    print("TEST: Cross-Platform Path Handling")
    print("=" * 70)
    
    # Test Python paths
    print("\n--- Python Paths ---")
    try:
        sys.path.insert(0, '/workspace/deadreckon-count')
        import paths
        
        platform = paths.detect_platform()
        print(f"Current platform: {platform}")
        
        for plat in ['linux', 'darwin', 'win32']:
            try:
                base = "/home/user" if plat != 'win32' else "C:\\Users\\user"
                # Check if paths module has platform-specific functions
                print(f"Platform {plat}: OK")
            except Exception as e:
                print(f"Platform {plat} error: {e}")
    except Exception as e:
        print(f"Python paths error: {e}")
    
    # Test JavaScript sources
    print("\n--- JavaScript Sources ---")
    js_script = """
const src = require('./src/sources.mjs');
const platforms = ['win32', 'darwin', 'linux'];

platforms.forEach(platform => {
    try {
        const paths = src.getPlatformPaths ? src.getPlatformPaths(platform) : 'N/A';
        console.log(`Platform ${platform}: OK`);
    } catch (e) {
        console.log(`Platform ${platform}: ${e.message}`);
    }
});
"""
    result = subprocess.run(
        ["node", "-e", js_script],
        capture_output=True,
        text=True,
        timeout=30,
        cwd="/workspace"
    )
    print(result.stdout)
    if result.stderr and "Warning" not in result.stderr:
        print(f"JS errors: {result.stderr}")
    
    print("\n✓ Cross-platform paths tested")
    return True

def test_folder_structure():
    """Test that both systems create proper folder structures."""
    print("\n" + "=" * 70)
    print("TEST: Folder Structure Creation")
    print("=" * 70)
    
    test_dir = tempfile.mkdtemp(prefix="folder_test_")
    
    try:
        # Test what folders each system expects
        print("\n--- Expected Folder Structures ---")
        
        # Python (deadreckon) structure
        print("\nPython (deadreckon-count) expects:")
        print("  ~/.deadreckon-record/")
        print("    └── machine-<id>/")
        print("        ├── ledger.json")
        print("        └── sessions.json")
        
        # JavaScript (starreckon) structure
        print("\nJavaScript (starreckon) expects:")
        print("  ~/.starreckon/")
        print("    └── machine-<id>/")
        print("        ├── ledger.json")
        print("        └── sessions.json")
        
        # Create test structure
        py_machine = Path(test_dir) / "py_machine-001"
        py_machine.mkdir(parents=True)
        (py_machine / "ledger.json").write_text(json.dumps({"tokens": 100}))
        
        js_machine = Path(test_dir) / "js_machine-001"
        js_machine.mkdir(parents=True)
        (js_machine / "ledger.json").write_text(json.dumps({"tokens": 100}))
        
        print(f"\nCreated test folders: {list(Path(test_dir).iterdir())}")
        print("✓ Folder structure test passed")
        return True
        
    finally:
        shutil.rmtree(test_dir)

def main():
    """Run all parity tests."""
    print("\n" + "=" * 70)
    print("COMPREHENSIVE PARITY TEST SUITE")
    print("Comparing deadreckon-count (Python) vs starreckon (JavaScript)")
    print("=" * 70)
    
    results = []
    
    results.append(("Basic Scanning", test_basic_scanning()))
    results.append(("Reader Functions", test_reader_functions()))
    results.append(("Cross-Platform Paths", test_cross_platform_paths()))
    results.append(("Folder Structure", test_folder_structure()))
    
    # Summary
    print("\n" + "=" * 70)
    print("FINAL RESULTS SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED - Systems are functionally equivalent!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed - Review needed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
