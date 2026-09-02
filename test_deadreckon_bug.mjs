import { readDeadreckonCorpus } from './src/deadreckon-reader.mjs';
import { writeFileSync, mkdirSync, rmSync } from 'fs';
import { join } from 'path';

const testDir = '/tmp/dr-test-bug';
const mrDir = join(testDir, 'machine-readable');
try { rmSync(testDir, { recursive: true }); } catch {}
mkdirSync(mrDir, { recursive: true });

console.log("=== DEADRECKON BUG HUNTING ===\n");

// Test 1: Malformed JSON handling
console.log("Test 1: Malformed JSON parsing");
writeFileSync(join(mrDir, 'sessions.json'), '{ invalid json }}}');
try {
    await readDeadreckonCorpus(testDir);
    console.log("BUG FOUND: No error thrown for malformed JSON - crashes with unhandled SyntaxError");
} catch (e) {
    console.log("Error type:", e.constructor.name);
    console.log("Error message:", e.message.substring(0, 100));
    if (e.message.includes('Unexpected token') || e.message.includes('JSON')) {
        console.log("ISSUE: Raw JSON parse error exposed to caller (should be sanitized)\n");
    }
}

// Test 2: Null session_id
console.log("Test 2: Null session_id field");
writeFileSync(join(mrDir, 'sessions.json'), JSON.stringify([{
    session_id: null,
    model: "test-model",
    tokens: { input_tokens: 100, output_tokens: 50 }
}]));
try {
    const result = await readDeadreckonCorpus(testDir);
    console.log("Session ID:", result.sessions[0].id);
    if (result.sessions[0].id === null || result.sessions[0].id === undefined) {
        console.log("BUG FOUND: Session ID is null/undefined when session_id is null\n");
    }
} catch (e) {
    console.log("Error:", e.message);
}

// Test 3: Prototype pollution via __proto__
console.log("Test 3: Prototype pollution attempt");
writeFileSync(join(mrDir, 'sessions.json'), JSON.stringify([{
    session_id: "__proto__",
    model: "test",
    tokens: { input_tokens: 100, output_tokens: 50 }
}]));
try {
    const result = await readDeadreckonCorpus(testDir);
    console.log("Session id:", result.sessions[0].id);
    // Check if pollution occurred
    const testObj = {};
    if (testObj.polluted) {
        console.log("BUG FOUND: Prototype pollution successful!\n");
    } else {
        console.log("PASS: No prototype pollution (using safe assignment)\n");
    }
} catch (e) {
    console.log("Error:", e.message);
}

// Test 4: Integer overflow
console.log("Test 4: Integer overflow test");
writeFileSync(join(mrDir, 'sessions.json'), JSON.stringify([{
    session_id: "overflow-test",
    model: "test",
    tokens: { 
        input_tokens: 9007199254740992, // MAX_SAFE_INTEGER + 1
        output_tokens: 9007199254740992
    }
}]));
try {
    const result = await readDeadreckonCorpus(testDir);
    const total = result.sessions[0].tokens.total;
    console.log("Input:", result.sessions[0].tokens.input);
    console.log("Total:", total);
    if (!Number.isSafeInteger(total)) {
        console.log("BUG FOUND: Precision loss in token calculation (unsafe integer)\n");
    }
} catch (e) {
    console.log("Error:", e.message);
}

// Test 5: Missing tokens object
console.log("Test 5: Missing tokens object");
writeFileSync(join(mrDir, 'sessions.json'), JSON.stringify([{
    session_id: "no-tokens",
    model: "test"
}]));
try {
    const result = await readDeadreckonCorpus(testDir);
    console.log("Tokens:", result.sessions[0].tokens);
    console.log("Total:", result.sessions[0].tokens.total);
    if (result.sessions[0].tokens.total !== 0) {
        console.log("BUG FOUND: Missing tokens should default to 0\n");
    } else {
        console.log("PASS: Defaults to 0 correctly\n");
    }
} catch (e) {
    console.log("Error:", e.message, "\n");
}

// Test 6: Array instead of object for tokens
console.log("Test 6: Tokens as array (type confusion)");
writeFileSync(join(mrDir, 'sessions.json'), JSON.stringify([{
    session_id: "array-tokens",
    model: "test",
    tokens: [100, 200, 300]
}]));
try {
    const result = await readDeadreckonCorpus(testDir);
    console.log("Tokens:", result.sessions[0].tokens);
    console.log("BUG FOUND: Array accepted as tokens object - will cause NaN issues\n");
} catch (e) {
    console.log("Error:", e.message, "\n");
}

// Test 7: Extremely long strings (DoS)
console.log("Test 7: Extremely long model name (DoS test)");
const longString = "x".repeat(1000000);
writeFileSync(join(mrDir, 'sessions.json'), JSON.stringify([{
    session_id: "dos-test",
    model: longString,
    tokens: { input_tokens: 100, output_tokens: 50 }
}]));
try {
    const result = await readDeadreckonCorpus(testDir);
    console.log("Model name length:", result.sessions[0].model.length);
    console.log("BUG FOUND: No limit on string length - potential DoS\n");
} catch (e) {
    console.log("Error:", e.message, "\n");
}

// Test 8: Negative token values
console.log("Test 8: Negative token values");
writeFileSync(join(mrDir, 'sessions.json'), JSON.stringify([{
    session_id: "negative-tokens",
    model: "test",
    tokens: { input_tokens: -1000, output_tokens: -500 }
}]));
try {
    const result = await readDeadreckonCorpus(testDir);
    console.log("Input tokens:", result.sessions[0].tokens.input);
    console.log("Output tokens:", result.sessions[0].tokens.output);
    if (result.sessions[0].tokens.input < 0 || result.sessions[0].tokens.output < 0) {
        console.log("BUG FOUND: Negative tokens accepted (should be rejected or zeroed)\n");
    } else {
        console.log("PASS: Negative values handled correctly\n");
    }
} catch (e) {
    console.log("Error:", e.message, "\n");
}

// Test 9: Float token values
console.log("Test 9: Float token values");
writeFileSync(join(mrDir, 'sessions.json'), JSON.stringify([{
    session_id: "float-tokens",
    model: "test",
    tokens: { input_tokens: 100.5, output_tokens: 50.999 }
}]));
try {
    const result = await readDeadreckonCorpus(testDir);
    console.log("Input tokens:", result.sessions[0].tokens.input);
    console.log("Output tokens:", result.sessions[0].tokens.output);
    if (!Number.isInteger(result.sessions[0].tokens.input)) {
        console.log("BUG FOUND: Float tokens accepted (tokens must be integers)\n");
    }
} catch (e) {
    console.log("Error:", e.message, "\n");
}

// Test 10: Deeply nested structure
console.log("Test 10: Deeply nested tokens object");
const deepTokens = { input_tokens: { nested: { value: 100 } } };
writeFileSync(join(mrDir, 'sessions.json'), JSON.stringify([{
    session_id: "deep-nest",
    model: "test",
    tokens: deepTokens
}]));
try {
    const result = await readDeadreckonCorpus(testDir);
    console.log("Input tokens:", result.sessions[0].tokens.input);
    if (typeof result.sessions[0].tokens.input === 'object') {
        console.log("BUG FOUND: Nested object not handled - will cause calculation errors\n");
    }
} catch (e) {
    console.log("Error:", e.message, "\n");
}

rmSync(testDir, { recursive: true });
console.log("=== Bug hunting complete ===");
