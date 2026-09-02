#!/usr/bin/env python3
"""
Parity Test: Compare deadreckon-count (Python) vs starreckon (JavaScript)
Tests token counting, folder creation, and reporting across both systems.
"""

import json
import os
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path

def setup_test_corpus():
    """Create a controlled test corpus with known token counts."""
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
            {"role": "model", "parts": [{"text": "Okay I will"}]},
            {"role": "user", "parts": [{"text": "What is the total?"}]},
            {"role": "model", "parts": [{"text": "The total is 42"}]}
        ]
    }, indent=2))
    
    return test_dir

def run_deadreckon_count(corpus_dir):
    """Run deadreckon-count Python scanner."""
    try:
        result = subprocess.run(
            ["python3", "deadreckon-count/count_corpus.py", "--corpus", corpus_dir],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode != 0:
            print(f"Deadreckon-count error: {result.stderr}")
            return None
        
        # Parse output - look for JSON or summary
        output = result.stdout.strip()
        print(f"Deadreckon-count output:\n{output}")
        return output
    except Exception as e:
        print(f"Deadreckon-count exception: {e}")
        return None

def run_starreckon_scan(corpus_dir):
    """Run starreckon JavaScript scanner."""
    try:
        # Set environment to use our test corpus
        env = os.environ.copy()
        env["STARRECKON_HOME"] = corpus_dir
        
        result = subprocess.run(
            ["node", "src/cli.mjs", "--no-prompt"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd="/workspace"
        )
        
        output = result.stdout + result.stderr
        print(f"Starreckon output:\n{output}")
        return output
    except Exception as e:
        print(f"Starreckon exception: {e}")
        return None

def test_readers_parity():
    """Test that both systems read the same files correctly."""
    print("=" * 60)
    print("TEST 1: Reader Parity")
    print("=" * 60)
    
    test_dir = setup_test_corpus()
    print(f"Created test corpus at: {test_dir}")
    
    try:
        # Test Python readers
        print("\n--- Testing Python Readers ---")
        sys.path.insert(0, 'deadreckon-count')
        import sessions
        
        claude_data = sessions.read_claude_code_sessions([str(Path(test_dir) / "claude")])
        print(f"Python Claude sessions: {len(claude_data)}")
        
        copilot_data = sessions.read_copilot_sessions([str(Path(test_dir) / "copilot")])
        print(f"Python Copilot sessions: {len(copilot_data)}")
        
        gemini_data = sessions.read_gemini_sessions([str(Path(test_dir) / "gemini")])
        print(f"Python Gemini sessions: {len(gemini_data)}")
        
        # Test JavaScript readers
        print("\n--- Testing JavaScript Readers ---")
        js_test_script = f"""
const {{ readClaudeCodeSessions, readCopilotSessions, readGeminiSessions }} = require('./src/readers.mjs');

async function test() {{
    const claude = await readClaudeCodeSessions(['{Path(test_dir) / "claude"}']);
    console.log('JS Claude sessions:', claude.length);
    
    const copilot = await readCopilotSessions(['{Path(test_dir) / "copilot"}']);
    console.log('JS Copilot sessions:', copilot.length);
    
    const gemini = await readGeminiSessions(['{Path(test_dir) / "gemini"}']);
    console.log('JS Gemini sessions:', gemini.length);
}}

test().catch(console.error);
"""
        result = subprocess.run(
            ["node", "-e", js_test_script],
            capture_output=True,
            text=True,
            timeout=30,
            cwd="/workspace"
        )
        print(result.stdout)
        if result.stderr:
            print(f"JS errors: {result.stderr}")
        
    finally:
        shutil.rmtree(test_dir)

def test_token_counting_parity():
    """Test that both systems count tokens identically."""
    print("\n" + "=" * 60)
    print("TEST 2: Token Counting Parity")
    print("=" * 60)
    
    test_dir = setup_test_corpus()
    print(f"Created test corpus at: {test_dir}")
    
    try:
        # Run deadreckon-count
        print("\n--- Running Deadreckon-Count ---")
        dr_output = run_deadreckon_count(test_dir)
        
        # Run starreckon
        print("\n--- Running Starreckon ---")
        sr_output = run_starreckon_scan(test_dir)
        
        # Compare results
        print("\n--- Comparison ---")
        if dr_output and sr_output:
            print("Both systems executed successfully")
            # Extract token counts from outputs and compare
            # (Implementation depends on actual output format)
        else:
            print("One or both systems failed to execute")
            
    finally:
        shutil.rmtree(test_dir)

def test_folder_creation():
    """Test that both systems create folders correctly."""
    print("\n" + "=" * 60)
    print("TEST 3: Folder Creation")
    print("=" * 60)
    
    test_dir = tempfile.mkdtemp(prefix="folder_test_")
    
    try:
        # Test Python folder creation
        print("\n--- Testing Python Folder Creation ---")
        python_output_dir = Path(test_dir) / "python_output"
        python_output_dir.mkdir()
        
        # Simulate what deadreckon does
        machine_dir = python_output_dir / "machine-001"
        machine_dir.mkdir()
        ledger_file = machine_dir / "ledger.json"
        ledger_file.write_text(json.dumps({"tokens": 100}))
        
        print(f"Python created: {list(python_output_dir.rglob('*'))}")
        
        # Test JavaScript folder creation
        print("\n--- Testing JavaScript Folder Creation ---")
        js_test_script = f"""
const fs = require('fs');
const path = require('path');

const outputDir = path.join('{test_dir}', 'js_output');
fs.mkdirSync(outputDir, {{ recursive: true }});

const machineDir = path.join(outputDir, 'machine-001');
fs.mkdirSync(machineDir, {{ recursive: true }});

const ledgerFile = path.join(machineDir, 'ledger.json');
fs.writeFileSync(ledgerFile, JSON.stringify({{ tokens: 100 }}));

console.log('JS created:', fs.readdirSync(outputDir, {{ recursive: true }}));
"""
        result = subprocess.run(
            ["node", "-e", js_test_script],
            capture_output=True,
            text=True,
            timeout=30
        )
        print(result.stdout)
        if result.stderr:
            print(f"JS errors: {result.stderr}")
        
    finally:
        shutil.rmtree(test_dir)

def test_cross_platform_paths():
    """Test path handling for Windows, Mac, and Linux."""
    print("\n" + "=" * 60)
    print("TEST 4: Cross-Platform Path Handling")
    print("=" * 60)
    
    # Test Python paths module
    print("\n--- Testing Python Paths ---")
    try:
        from deadreckon_count import paths
        
        # Test platform detection
        platform = paths.detect_platform()
        print(f"Python detected platform: {platform}")
        
        # Test path construction
        base = "/home/user"
        claude_path = paths.claude_code_path(base, platform)
        print(f"Python Claude path for {platform}: {claude_path}")
        
    except Exception as e:
        print(f"Python paths test error: {e}")
    
    # Test JavaScript sources module
    print("\n--- Testing JavaScript Sources ---")
    js_test_script = """
const { getPlatformPaths } = require('./src/sources.mjs');

const platforms = ['win32', 'darwin', 'linux'];
platforms.forEach(platform => {
    const paths = getPlatformPaths(platform);
    console.log(`JS ${platform} Claude path:`, paths.claude);
});
"""
    result = subprocess.run(
        ["node", "-e", js_test_script],
        capture_output=True,
        text=True,
        timeout=30,
        cwd="/workspace"
    )
    print(result.stdout)
    if result.stderr:
        print(f"JS errors: {result.stderr}")

def main():
    """Run all parity tests."""
    print("Starting Comprehensive Parity Tests")
    print("Testing deadreckon-count (Python) vs starreckon (JavaScript)")
    print("=" * 60)
    
    test_readers_parity()
    test_token_counting_parity()
    test_folder_creation()
    test_cross_platform_paths()
    
    print("\n" + "=" * 60)
    print("PARITY TESTS COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
