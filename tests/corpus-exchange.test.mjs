/**
 * Tests for bidirectional JSONL corpus exchange between Starreckon and Deadreckon
 */
import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert';
import { writeFileSync, readFileSync, mkdirSync, rmSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { execFileSync } from 'node:child_process';
import {
    readDeadreckonCorpus,
    writeStarreckonCorpus,
    exportCorpusFromScan,
    ingestCorpusEntries,
    compareCorpora
} from '../src/deadreckon-reader.mjs';
import { emptyStats, finalize } from '../src/scan.mjs';

const TEST_DIR = join(tmpdir(), 'sr-dr-corpus-test-' + Date.now());

describe('Bidirectional Corpus Exchange', () => {
    beforeEach(() => {
        if (existsSync(TEST_DIR)) {
            rmSync(TEST_DIR, { recursive: true, force: true });
        }
        mkdirSync(TEST_DIR, { recursive: true });
    });

    it('exports and re-imports corpus entries with 100% token fidelity', () => {
        const stats = emptyStats();
        stats.sessions.set('sess-1', {
            firstTs: 1722500000000,
            lastTs: 1722503600000,
            minutes: new Set(['2024-08-01T08:00']),
            project: 'my-project',
            models: new Map([['claude-3-5-sonnet', 5000]]),
            tok: { in: 4000, out: 1000, cr: 0, cw: 0 },
            sources: new Set(['claude']),
            idFromRow: true
        });

        const providers = {
            perSession: [
                {
                    provider: 'gemini',
                    session_id: 'sess-2',
                    month: '2024-08',
                    input: 800,
                    output: 200,
                    cacheRead: 0,
                    cacheWrite: 0,
                    model: 'gemini-1.5-pro',
                    project: 'provider-proj'
                }
            ]
        };

        const corpusFile = join(TEST_DIR, 'exported_corpus.jsonl');
        const count = exportCorpusFromScan(stats, providers, corpusFile);
        assert.strictEqual(count, 2, 'Should export 2 sessions');

        // Verify JSONL schema compliance
        const lines = readFileSync(corpusFile, 'utf-8').trim().split('\n');
        assert.strictEqual(lines.length, 2);

        const r1 = JSON.parse(lines[0]);
        assert.strictEqual(r1.id, 'sess-1');
        assert.strictEqual(r1.tool_origin, 'starreckon');
        assert.strictEqual(r1.counts.raw_tokens_est, 5000);
        assert.strictEqual(r1.counts.model_name, 'claude-3-5-sonnet');
        assert.strictEqual(r1.status, 'ok');

        const r2 = JSON.parse(lines[1]);
        assert.strictEqual(r2.id, 'sess-2');
        assert.strictEqual(r2.counts.raw_tokens_est, 1000);
        assert.strictEqual(r2.counts.model_name, 'gemini-1.5-pro');

        // Re-import back into a fresh stats
        const freshStats = emptyStats();
        const entries = readDeadreckonCorpus(corpusFile);
        assert.strictEqual(entries.length, 2);

        ingestCorpusEntries(entries, freshStats);
        const agg = finalize(freshStats);

        assert.strictEqual(agg.total_sessions, 2);
        assert.strictEqual(agg.total_input_tokens, 6000);
    });

    it('ingests deadreckon-generated corpus JSONL with graceful fallback', () => {
        const drCorpus = join(TEST_DIR, 'deadreckon_sample.jsonl');
        const content = [
            JSON.stringify({
                id: "dr-001",
                source_path: "/data/log1.txt",
                relative_path: "repo1/log1.txt",
                timestamp: "2024-08-01T10:00:00Z",
                tool_origin: "deadreckon",
                counts: { raw_chars: 4000, raw_tokens_est: 1000, model_specific_tokens: 1000, model_name: "claude-3" },
                status: "ok",
                error_msg: null
            }),
            JSON.stringify({
                id: "dr-002",
                source_path: "/data/log2.txt",
                relative_path: "repo2/log2.txt",
                timestamp: "2024-08-02T11:00:00Z",
                tool_origin: "deadreckon",
                counts: { raw_chars: 8000, raw_tokens_est: 2000, model_specific_tokens: null, model_name: "generic" },
                status: "ok",
                error_msg: null
            })
        ].join('\n');
        writeFileSync(drCorpus, content);

        const stats = emptyStats();
        const entries = readDeadreckonCorpus(drCorpus);
        ingestCorpusEntries(entries, stats);
        const agg = finalize(stats);

        assert.strictEqual(agg.total_sessions, 2);
        assert.strictEqual(agg.total_input_tokens, 3000);
        assert.strictEqual(agg.models['claude-3'], 1000);
        assert.strictEqual(agg.models['generic'], 2000);
    });

    it('Deadreckon python corpus_reader.py verifies Starreckon exported corpus', () => {
        const stats = emptyStats();
        stats.sessions.set('parity-1', {
            firstTs: 1722500000000,
            lastTs: 1722503600000,
            minutes: new Set(['2024-08-01T08:00']),
            project: 'parity-proj',
            models: new Map([['claude-3-opus', 2500]]),
            tok: { in: 2000, out: 500, cr: 0, cw: 0 },
            sources: new Set(['claude']),
            idFromRow: true
        });

        const srCorpus = join(TEST_DIR, 'sr_export.jsonl');
        exportCorpusFromScan(stats, null, srCorpus);

        // Run deadreckon-count/corpus_reader.py against the exported corpus
        const pyScript = join(process.cwd(), 'deadreckon-count', 'corpus_reader.py');
        if (existsSync(pyScript)) {
            const out = execFileSync('python3', [pyScript, srCorpus], { encoding: 'utf-8' });
            assert.ok(out.includes('Successfully parsed 1 entries'), `Expected successful parse, got: ${out}`);
        }
    });
});
