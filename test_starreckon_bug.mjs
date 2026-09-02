import { creditUsage } from './src/scan.mjs';
import { parseClaudeFile } from './src/scan.mjs';
import { writeFileSync, mkdirSync, rmSync, createWriteStream } from 'fs';
import { join } from 'path';

console.log("=== STARRECKON BUG HUNTING ===\n");

// Test 1: creditUsage with null/undefined usage
console.log("Test 1: creditUsage with null usage");
const seen = new Map();
try {
    const result = creditUsage(seen, "test-id", null);
    console.log("Result:", result);
    if (result.in !== 0 || result.out !== 0) {
        console.log("BUG FOUND: Null usage should return zeros\n");
    } else {
        console.log("PASS: Null handled correctly\n");
    }
} catch (e) {
    console.log("Error:", e.message, "\n");
}

// Test 2: creditUsage with negative values
console.log("Test 2: creditUsage with negative token values");
const seen2 = new Map();
try {
    const result = creditUsage(seen2, "test-id-2", {
        input_tokens: -1000,
        output_tokens: -500,
        cache_read_input_tokens: -200,
        cache_creation_input_tokens: -300
    });
    console.log("Result:", result);
    if (result.in < 0 || result.out < 0 || result.cr < 0 || result.cw < 0) {
        console.log("BUG FOUND: Negative tokens accepted in creditUsage\n");
    } else {
        console.log("PASS: Negative values zeroed\n");
    }
} catch (e) {
    console.log("Error:", e.message, "\n");
}

// Test 3: creditUsage with float values
console.log("Test 3: creditUsage with float token values");
const seen3 = new Map();
try {
    const result = creditUsage(seen3, "test-id-3", {
        input_tokens: 100.9,
        output_tokens: 50.1
    });
    console.log("Result:", result);
    if (!Number.isInteger(result.in) || !Number.isInteger(result.out)) {
        console.log("BUG FOUND: Float tokens accepted (must be integers)\n");
    } else {
        console.log("PASS: Floats handled\n");
    }
} catch (e) {
    console.log("Error:", e.message, "\n");
}

// Test 4: creditUsage with string numbers
console.log("Test 4: creditUsage with string numbers");
const seen4 = new Map();
try {
    const result = creditUsage(seen4, "test-id-4", {
        input_tokens: "999999999999999999999",
        output_tokens: "100"
    });
    console.log("Input:", result.in);
    if (!Number.isSafeInteger(result.in)) {
        console.log("BUG FOUND: Unsafe integer from string conversion\n");
    }
} catch (e) {
    console.log("Error:", e.message, "\n");
}

// Test 5: creditUsage duplicate detection bypass
console.log("Test 5: creditUsage duplicate detection with same ID");
const seen5 = new Map();
creditUsage(seen5, "dup-id", { input_tokens: 100, output_tokens: 50 });
const result5a = creditUsage(seen5, "dup-id", { input_tokens: 200, output_tokens: 100 });
const result5b = creditUsage(seen5, "dup-id", { input_tokens: 150, output_tokens: 75 });
console.log("First delta:", result5a);
console.log("Second delta:", result5b);
console.log("Total credited:", result5a.in + result5b.in, "input,", result5a.out + result5b.out, "output");
console.log("Expected total: 200 input, 100 output");
if ((result5a.in + result5b.in) !== 200 || (result5a.out + result5b.out) !== 100) {
    console.log("BUG FOUND: Duplicate detection not working correctly\n");
} else {
    console.log("PASS: Duplicates handled correctly\n");
}

// Test 6: creditUsage with NaN values
console.log("Test 6: creditUsage with NaN values");
const seen6 = new Map();
try {
    const result = creditUsage(seen6, "test-id-6", {
        input_tokens: NaN,
        output_tokens: Infinity,
        cache_read_input_tokens: -Infinity
    });
    console.log("Result:", result);
    if (!isFinite(result.in + result.out + result.cr + result.cw)) {
        console.log("BUG FOUND: NaN/Infinity not handled\n");
    } else {
        console.log("PASS: NaN/Infinity zeroed\n");
    }
} catch (e) {
    console.log("Error:", e.message, "\n");
}

// Test 7: Create malformed Claude log file
console.log("Test 7: Malformed JSON lines in Claude log");
const testDir = '/tmp/sr-test-bug';
const testFile = join(testDir, 'test.jsonl');
try { rmSync(testDir, { recursive: true }); } catch {}
mkdirSync(testDir, { recursive: true });

const malformedLog = `{"timestamp": "2024-01-01T00:00:00Z", "sessionId": "test", "message": {"id": "m1", "usage": {"input_tokens": 100}}}
{ invalid json here }}}
{"timestamp": "2024-01-01T00:00:01Z", "sessionId": "test", "message": {"id": "m2", "usage": {"input_tokens": 200}}}
null
{"type": "not_an_object"}
[1,2,3]
`;
writeFileSync(testFile, malformedLog);

const stats = {
    seenMessageIds: new Map(),
    projectsSeen: new Map(),
    undatedSessions: new Set(),
    sessions: new Map(),
    byDay: new Map(),
    byMonth: new Map(),
    lifetime: { in: 0, out: 0, cr: 0, cw: 0 },
    total_sessions: 0,
    undated_tokens: { in: 0, out: 0, cr: 0, cw: 0 }
};

try {
    await parseClaudeFile(testFile, stats, { excluded: () => false });
    console.log("Sessions found:", stats.total_sessions);
    console.log("Lifetime tokens:", stats.lifetime);
    console.log("PASS: Malformed lines skipped gracefully\n");
} catch (e) {
    console.log("BUG FOUND: Crashed on malformed log:", e.message, "\n");
}

// Test 8: Empty file
console.log("Test 8: Empty log file");
writeFileSync(testFile, '');
const stats2 = {
    seenMessageIds: new Map(),
    projectsSeen: new Map(),
    undatedSessions: new Set(),
    sessions: new Map(),
    byDay: new Map(),
    byMonth: new Map(),
    lifetime: { in: 0, out: 0, cr: 0, cw: 0 },
    total_sessions: 0,
    undated_tokens: { in: 0, out: 0, cr: 0, cw: 0 }
};
try {
    await parseClaudeFile(testFile, stats2, { excluded: () => false });
    console.log("Sessions:", stats2.total_sessions);
    console.log("PASS: Empty file handled\n");
} catch (e) {
    console.log("Error:", e.message, "\n");
}

// Test 9: Very long line (DoS)
console.log("Test 9: Very long line in log file");
const longLine = '{"timestamp": "2024-01-01T00:00:00Z", "sessionId": "test", "message": {"content": "' + 'x'.repeat(10000000) + '"}}\n';
writeFileSync(testFile, longLine);
const stats3 = {
    seenMessageIds: new Map(),
    projectsSeen: new Map(),
    undatedSessions: new Set(),
    sessions: new Map(),
    byDay: new Map(),
    byMonth: new Map(),
    lifetime: { in: 0, out: 0, cr: 0, cw: 0 },
    total_sessions: 0,
    undated_tokens: { in: 0, out: 0, cr: 0, cw: 0 }
};
try {
    await parseClaudeFile(testFile, stats3, { excluded: () => false });
    console.log("Processed long line without crash");
    console.log("ISSUE: No limit on line length - potential memory issue\n");
} catch (e) {
    console.log("Error:", e.message, "\n");
}

rmSync(testDir, { recursive: true });
console.log("=== Bug hunting complete ===");
