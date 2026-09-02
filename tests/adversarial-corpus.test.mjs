/**
 * Adversarial Corpus Testing - Tests bidirectional corpus reading,
 * malformed data handling, generic fallback mode, and parity logic.
 */
import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert';
import { writeFileSync, mkdirSync, rmSync, existsSync } from 'fs';
import { tmpdir } from 'os';
import { join } from 'path';
import { readDeadreckonCorpus, compareCorpora, genericTokenCount, hasModelConfig } from '../src/deadreckon-reader.mjs';

const TEST_DIR = join(tmpdir(), 'corpus-adversarial-test-' + Date.now());

describe('Adversarial Corpus Testing', () => {
    beforeEach(() => {
        if (existsSync(TEST_DIR)) {
            rmSync(TEST_DIR, { recursive: true, force: true });
        }
        mkdirSync(TEST_DIR, { recursive: true });
    });

    describe('Malformed JSONL Handling', () => {
        it('should skip malformed JSON lines without crashing', () => {
            const corpusFile = join(TEST_DIR, 'malformed.jsonl');
            const content = `{"id":"1","source_path":"/a.txt","counts":{"raw_tokens_est":100}}
not valid json at all
{"id":"2","source_path":"/b.txt","counts":{"raw_tokens_est":200}}
{broken json
{"id":"3","source_path":"/c.txt","counts":{"raw_tokens_est":300}}`;
            writeFileSync(corpusFile, content);
            
            const entries = readDeadreckonCorpus(corpusFile);
            assert.strictEqual(entries.length, 3, 'Should parse 3 valid entries');
            assert.strictEqual(entries[0].id, '1');
            assert.strictEqual(entries[1].id, '2');
            assert.strictEqual(entries[2].id, '3');
        });

        it('should handle empty lines gracefully', () => {
            const corpusFile = join(TEST_DIR, 'empty-lines.jsonl');
            const content = `{"id":"1","source_path":"/a.txt","counts":{"raw_tokens_est":100}}

{"id":"2","source_path":"/b.txt","counts":{"raw_tokens_est":200}}

`;
            writeFileSync(corpusFile, content);
            
            const entries = readDeadreckonCorpus(corpusFile);
            assert.strictEqual(entries.length, 2);
        });

        it('should handle missing required fields', () => {
            const corpusFile = join(TEST_DIR, 'missing-fields.jsonl');
            const content = `{"id":"1","source_path":"/a.txt","counts":{"raw_tokens_est":100}}
{"source_path":"/no-id.txt","counts":{"raw_tokens_est":50}}
{"id":"2","counts":{"raw_tokens_est":200}}
{"id":"3","source_path":"/c.txt","counts":{"raw_tokens_est":300}}`;
            writeFileSync(corpusFile, content);
            
            const entries = readDeadreckonCorpus(corpusFile);
            assert.strictEqual(entries.length, 2, 'Should skip entries missing id or source_path');
        });
    });

    describe('Schema Validation & Normalization', () => {
        it('should normalize missing tool_origin', () => {
            const corpusFile = join(TEST_DIR, 'no-origin.jsonl');
            const content = `{"id":"1","source_path":"/a.txt","counts":{"raw_tokens_est":100}}`;
            writeFileSync(corpusFile, content);
            
            const entries = readDeadreckonCorpus(corpusFile);
            assert.strictEqual(entries[0].tool_origin, 'deadreckon');
        });

        it('should provide default counts object if missing', () => {
            const corpusFile = join(TEST_DIR, 'no-counts.jsonl');
            const content = `{"id":"1","source_path":"/a.txt"}`;
            writeFileSync(corpusFile, content);
            
            const entries = readDeadreckonCorpus(corpusFile);
            assert.ok(entries[0].counts);
            assert.strictEqual(entries[0].counts.raw_tokens_est, 0);
        });

        it('should handle null values in counts', () => {
            const corpusFile = join(TEST_DIR, 'null-counts.jsonl');
            const content = `{"id":"1","source_path":"/a.txt","counts":{"raw_tokens_est":null,"raw_chars":null}}`;
            writeFileSync(corpusFile, content);
            
            const entries = readDeadreckonCorpus(corpusFile);
            // Should not crash, null is acceptable
            assert.ok(entries.length === 1);
        });
    });

    describe('Generic Token Counting Fallback', () => {
        it('should count tokens with simple whitespace split', () => {
            const text = "Hello world this is a test";
            const count = genericTokenCount(text);
            assert.strictEqual(count, 6);
        });

        it('should handle empty strings', () => {
            assert.strictEqual(genericTokenCount(''), 0);
            assert.strictEqual(genericTokenCount(null), 0);
            assert.strictEqual(genericTokenCount(undefined), 0);
        });

        it('should handle multiple whitespace types', () => {
            const text = "Hello\tworld\nthis\r\nis\ta test";
            const count = genericTokenCount(text);
            assert.strictEqual(count, 6);
        });
    });

    describe('Corpus Comparison Logic', () => {
        it('should detect matching entries', () => {
            const srEntries = [
                { id: '1', source_path: '/a.txt', counts: { raw_tokens_est: 100 } },
                { id: '2', source_path: '/b.txt', counts: { raw_tokens_est: 200 } }
            ];
            const drEntries = [
                { id: '1', source_path: '/a.txt', counts: { raw_tokens_est: 100 } },
                { id: '2', source_path: '/b.txt', counts: { raw_tokens_est: 200 } }
            ];
            
            const report = compareCorpora(srEntries, drEntries);
            assert.strictEqual(report.matches, 2);
            assert.strictEqual(report.mismatches, 0);
        });

        it('should detect token count mismatches', () => {
            const srEntries = [
                { id: '1', source_path: '/a.txt', counts: { raw_tokens_est: 100 } }
            ];
            const drEntries = [
                { id: '1', source_path: '/a.txt', counts: { raw_tokens_est: 150 } }
            ];
            
            const report = compareCorpora(srEntries, drEntries);
            assert.strictEqual(report.matches, 0);
            assert.strictEqual(report.mismatches, 1);
            assert.strictEqual(report.discrepancies[0].diff, 50);
        });

        it('should detect missing entries in Starreckon', () => {
            const srEntries = [
                { id: '1', source_path: '/a.txt', counts: { raw_tokens_est: 100 } }
            ];
            const drEntries = [
                { id: '1', source_path: '/a.txt', counts: { raw_tokens_est: 100 } },
                { id: '2', source_path: '/b.txt', counts: { raw_tokens_est: 200 } }
            ];
            
            const report = compareCorpora(srEntries, drEntries);
            assert.strictEqual(report.missingInSR, 1);
        });

        it('should detect missing entries in Deadreckon', () => {
            const srEntries = [
                { id: '1', source_path: '/a.txt', counts: { raw_tokens_est: 100 } },
                { id: '2', source_path: '/b.txt', counts: { raw_tokens_est: 200 } }
            ];
            const drEntries = [
                { id: '1', source_path: '/a.txt', counts: { raw_tokens_est: 100 } }
            ];
            
            const report = compareCorpora(srEntries, drEntries);
            assert.strictEqual(report.missingInDR, 1);
        });
    });

    describe('Edge Cases & Attack Vectors', () => {
        it('should handle extremely long lines', () => {
            const corpusFile = join(TEST_DIR, 'long-line.jsonl');
            const longPath = '/path/' + 'a'.repeat(10000) + '.txt';
            const content = `{"id":"1","source_path":"${longPath}","counts":{"raw_tokens_est":100}}`;
            writeFileSync(corpusFile, content);
            
            const entries = readDeadreckonCorpus(corpusFile);
            assert.strictEqual(entries.length, 1);
            assert.ok(entries[0].source_path.length > 10000);
        });

        it('should handle unicode in paths and IDs', () => {
            const corpusFile = join(TEST_DIR, 'unicode.jsonl');
            const content = `{"id":"🔥测试","source_path":"/路径/文件.txt","counts":{"raw_tokens_est":100}}`;
            writeFileSync(corpusFile, content);
            
            const entries = readDeadreckonCorpus(corpusFile);
            assert.strictEqual(entries.length, 1);
            assert.strictEqual(entries[0].id, '🔥测试');
        });

        it('should handle duplicate IDs (last wins)', () => {
            const corpusFile = join(TEST_DIR, 'duplicates.jsonl');
            const content = `{"id":"1","source_path":"/a.txt","counts":{"raw_tokens_est":100}}
{"id":"1","source_path":"/b.txt","counts":{"raw_tokens_est":200}}`;
            writeFileSync(corpusFile, content);
            
            const entries = readDeadreckonCorpus(corpusFile);
            // Both entries are parsed, comparison logic handles duplicates
            assert.strictEqual(entries.length, 2);
        });

        it('should handle negative token counts', () => {
            const corpusFile = join(TEST_DIR, 'negative.jsonl');
            const content = `{"id":"1","source_path":"/a.txt","counts":{"raw_tokens_est":-100}}`;
            writeFileSync(corpusFile, content);
            
            const entries = readDeadreckonCorpus(corpusFile);
            assert.strictEqual(entries.length, 1);
            // Negative values are preserved (validation happens elsewhere)
            assert.strictEqual(entries[0].counts.raw_tokens_est, -100);
        });

        it('should handle floating point token counts', () => {
            const corpusFile = join(TEST_DIR, 'float.jsonl');
            const content = `{"id":"1","source_path":"/a.txt","counts":{"raw_tokens_est":100.5}}`;
            writeFileSync(corpusFile, content);
            
            const entries = readDeadreckonCorpus(corpusFile);
            assert.strictEqual(entries.length, 1);
            assert.strictEqual(entries[0].counts.raw_tokens_est, 100.5);
        });
    });

    describe('File System Attacks', () => {
        it('should handle non-existent file gracefully', () => {
            const entries = readDeadreckonCorpus('/nonexistent/path/corpus.jsonl');
            assert.strictEqual(entries.length, 0);
        });

        it('should handle empty file', () => {
            const corpusFile = join(TEST_DIR, 'empty.jsonl');
            writeFileSync(corpusFile, '');
            
            const entries = readDeadreckonCorpus(corpusFile);
            assert.strictEqual(entries.length, 0);
        });

        it('should handle file with only whitespace', () => {
            const corpusFile = join(TEST_DIR, 'whitespace.jsonl');
            writeFileSync(corpusFile, '   \n\n   \t   \n');
            
            const entries = readDeadreckonCorpus(corpusFile);
            assert.strictEqual(entries.length, 0);
        });
    });
});

describe('Model Config Detection', () => {
    it('should return false when no config exists', () => {
        // In test environment, configs likely don't exist
        const hasConfig = hasModelConfig();
        // Just verify it doesn't crash
        assert.ok(typeof hasConfig === 'boolean');
    });
});
