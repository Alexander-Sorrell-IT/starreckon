/**
 * Deadreckon Reader Module - Reads Deadreckon corpus files for Starreckon.
 * Handles malformed lines, missing fields, and schema validation.
 * Falls back to generic mode if models/daemons config is missing.
 */
import { readFileSync, writeFileSync, existsSync } from 'fs';
import { resolve, dirname } from 'path';

/**
 * Read a Deadreckon corpus file (JSONL format)
 * @param {string} filepath - Path to corpus file
 * @returns {Array} Array of parsed entries
 */
export function readDeadreckonCorpus(filepath) {
    const absPath = resolve(filepath);
    
    if (!existsSync(absPath)) {
        console.error(`Error: Corpus file not found: ${absPath}`);
        return [];
    }
    
    const content = readFileSync(absPath, 'utf-8');
    const lines = content.split('\n').filter(l => l.trim());
    const entries = [];
    let errors = 0;
    
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue;
        
        try {
            const entry = JSON.parse(line);
            // Support raw deadreckon token_ledger rows as well as standardized corpus rows
            if (!entry.id && entry.session_id) {
                entry.id = entry.session_id;
                if (!entry.source_path) {
                    entry.source_path = `${entry.machine || 'deadreckon'}/${entry.cli || 'cli'}/${entry.id}`;
                }
            }
            
            // Validate minimal schema
            if (!entry.id || !entry.source_path) {
                console.error(`Warning: Line ${i + 1} missing required fields (id, source_path), skipping`);
                errors++;
                continue;
            }
            
            // Normalize tool_origin if missing
            if (!entry.tool_origin) {
                entry.tool_origin = entry.cli || 'deadreckon';
            }
            
            // Ensure counts object exists with defaults
            if (!entry.counts) {
                entry.counts = {
                    raw_chars: 0,
                    raw_tokens_est: 0,
                    model_specific_tokens: null,
                    model_name: 'generic'
                };
            }
            
            entries.push(entry);
            
        } catch (e) {
            console.error(`Warning: Line ${i + 1} malformed JSON: ${e.message}, skipping`);
            errors++;
            continue;
        }
    }
    
    console.error(`Read ${entries.length} entries from ${absPath} (${errors} errors)`);
    return entries;
}

/**
 * Compare Starreckon results against Deadreckon corpus
 * @param {Array} srEntries - Starreckon entries
 * @param {Array} drEntries - Deadreckon entries
 * @returns {Object} Comparison report
 */
export function compareCorpora(srEntries, drEntries) {
    const drMap = new Map(drEntries.map(e => [e.id, e]));
    
    const report = {
        matches: 0,
        mismatches: 0,
        missingInSR: 0,
        missingInDR: 0,
        discrepancies: []
    };
    
    // Check DR entries against SR
    for (const [id, drEntry] of drMap) {
        const srEntry = srEntries.find(e => e.id === id);
        
        if (!srEntry) {
            report.missingInSR++;
            continue;
        }
        
        const drTokens = drEntry.counts?.raw_tokens_est || 0;
        const srTokens = srEntry.counts?.raw_tokens_est || 0;
        
        if (drTokens === srTokens) {
            report.matches++;
        } else {
            report.mismatches++;
            report.discrepancies.push({
                id,
                deadreckon: drTokens,
                starreckon: srTokens,
                diff: Math.abs(drTokens - srTokens)
            });
            console.error(`Mismatch for ${id}: DR=${drTokens}, SR=${srTokens}`);
        }
    }
    
    // Check for SR entries not in DR
    for (const srEntry of srEntries) {
        if (!drMap.has(srEntry.id)) {
            report.missingInDR++;
        }
    }
    
    return report;
}

/**
 * Generic token counter fallback when models/daemons unavailable
 * @param {string} text - Input text
 * @returns {number} Estimated token count
 */
export function genericTokenCount(text) {
    if (!text || typeof text !== 'string') return 0;
    // Simple whitespace-based estimation
    return text.split(/\s+/).filter(w => w.length > 0).length;
}

/**
 * Check if models/daemons configuration exists
 * @returns {boolean} True if configured, false for generic mode
 */
export function hasModelConfig() {
    const modelPaths = [
        './models.json',
        './config/models.json',
        '../models.json'
    ];
    return modelPaths.some(p => existsSync(p));
}

/**
 * Write a standardized JSONL corpus file matching corpus-schema.md
 * @param {Array} entries - Array of corpus entry objects
 * @param {string} filepath - Destination file path
 * @returns {number} Count of entries written
 */
export function writeStarreckonCorpus(entries, filepath) {
    const absPath = resolve(filepath);
    const lines = entries.map(e => JSON.stringify({
        id: String(e.id),
        source_path: String(e.source_path || ''),
        relative_path: String(e.relative_path || ''),
        timestamp: e.timestamp || new Date().toISOString(),
        tool_origin: e.tool_origin || 'starreckon',
        counts: {
            raw_chars: Number.isInteger(e.counts?.raw_chars) ? e.counts.raw_chars : (e.counts?.raw_tokens_est ? e.counts.raw_tokens_est * 4 : 0),
            raw_tokens_est: Number.isInteger(e.counts?.raw_tokens_est) ? e.counts.raw_tokens_est : 0,
            model_specific_tokens: e.counts?.model_specific_tokens ?? null,
            model_name: e.counts?.model_name || 'generic'
        },
        status: e.status || 'ok',
        error_msg: e.error_msg || null
    }));
    writeFileSync(absPath, lines.join('\n') + (lines.length ? '\n' : ''), 'utf-8');
    return entries.length;
}

/**
 * Ingest parsed corpus entries into a Starreckon stats object
 * @param {Array} entries - Parsed corpus entries from readDeadreckonCorpus
 * @param {Object} stats - Target stats object (from emptyStats)
 * @returns {number} Count of entries ingested
 */
export function ingestCorpusEntries(entries, stats) {
    let count = 0;
    for (const entry of entries) {
        if (!entry || entry.status === 'error' || !entry.id) continue;
        const fallbackTok = (entry.input_tokens || 0) + (entry.output_tokens || 0) + (entry.cache_creation_input_tokens || 0) + (entry.cache_read_input_tokens || 0) || entry.total || 0;
        const tokens = (typeof entry.counts?.model_specific_tokens === 'number' && entry.counts.model_specific_tokens >= 0)
            ? entry.counts.model_specific_tokens
            : (typeof entry.counts?.raw_tokens_est === 'number' && entry.counts.raw_tokens_est >= 0
                ? entry.counts.raw_tokens_est
                : fallbackTok);

        const tokIn = entry.input_tokens !== undefined ? entry.input_tokens : tokens;
        const tokOut = entry.output_tokens || 0;
        const tokCr = entry.cache_read_input_tokens || 0;
        const tokCw = entry.cache_creation_input_tokens || 0;

        const rawTs = entry.timestamp || entry.observed || (entry.start ? entry.start + 'T00:00:00Z' : null);
        const ts = rawTs ? Date.parse(rawTs) : Date.now();
        const validTs = isFinite(ts) ? ts : Date.now();
        const iso = new Date(validTs).toISOString();
        const day = iso.slice(0, 10);
        const minute = iso.slice(0, 16);
        const hour = new Date(validTs).getUTCHours();
        const project = entry.relative_path || entry.project || 'corpus';
        const model = entry.counts?.model_name || entry.model || 'generic';
        const origin = entry.tool_origin || entry.cli || 'corpus';

        stats.totalEvents = (stats.totalEvents || 0) + 1;
        if (stats.activeDays instanceof Set) stats.activeDays.add(day);
        if (Array.isArray(stats.hourCounts)) stats.hourCounts[hour] = (stats.hourCounts[hour] || 0) + 1;
        if (hour < 6) {
            if (stats.nightMinutes instanceof Set) stats.nightMinutes.add(minute);
            const mKey = minute.slice(0, 7);
            if (stats.nightMinutesByMonth instanceof Map) {
                if (!stats.nightMinutesByMonth.has(mKey)) stats.nightMinutesByMonth.set(mKey, new Set());
                stats.nightMinutesByMonth.get(mKey).add(minute);
            }
        }
        if (stats.projectsSeen instanceof Map) {
            stats.projectsSeen.set(project, project);
        }

        if (stats.sessions instanceof Map) {
            if (stats.sessions.has(entry.id)) {
                const s = stats.sessions.get(entry.id);
                s.tok.in += tokIn;
                s.tok.out += tokOut;
                s.tok.cr += tokCr;
                s.tok.cw += tokCw;
                s.models.set(model, (s.models.get(model) || 0) + tokens);
                s.minutes.add(minute);
                if (Array.isArray(s.hours)) s.hours[hour] = (s.hours[hour] || 0) + 1;
                if (s.days instanceof Set) s.days.add(day);
                if (validTs < s.firstTs) s.firstTs = validTs;
                if (validTs > s.lastTs) s.lastTs = validTs;
                s.sources.add(origin);
            } else {
                const hours = new Array(24).fill(0);
                hours[hour] = 1;
                const s = {
                    firstTs: validTs,
                    lastTs: validTs,
                    minutes: new Set([minute]),
                    project,
                    models: new Map([[model, tokens]]),
                    tok: { in: tokIn, out: tokOut, cr: tokCr, cw: tokCw },
                    tools: 0,
                    exts: new Map(),
                    hours,
                    days: new Set([day]),
                    sources: new Set([origin]),
                    idFromRow: true
                };
                stats.sessions.set(entry.id, s);
            }
        }
        count++;
    }
    return count;
}

/**
 * Export scanned stats and providers into a standardized JSONL corpus file
 * @param {Object} stats - Finalized or live stats object
 * @param {Object} providers - Providers object containing perSession
 * @param {string} filepath - Destination file path
 * @param {Object} opts - Export options (noProjects)
 * @returns {number} Count of entries exported
 */
export function exportCorpusFromScan(stats, providers, filepath, opts = {}) {
    const entries = [];
    const seenIds = new Set();

    if (stats?.sessions instanceof Map) {
        for (const [id, s] of stats.sessions) {
            const sid = String(id);
            if (seenIds.has(sid)) continue;
            seenIds.add(sid);

            const total = (s.tok?.in || 0) + (s.tok?.out || 0) + (s.tok?.cr || 0) + (s.tok?.cw || 0);
            let topModel = 'generic';
            if (s.models instanceof Map && s.models.size > 0) {
                const sorted = [...s.models.entries()].sort((a, b) => b[1] - a[1]);
                topModel = sorted[0][0] || 'generic';
            }

            const ts = s.firstTs ? new Date(s.firstTs).toISOString() : new Date().toISOString();
            const proj = opts.noProjects ? 'project' : (s.project || 'default');
            entries.push({
                id: sid,
                source_path: s.sourcePath || `projects/${proj}/${sid}.jsonl`,
                relative_path: proj,
                timestamp: ts,
                tool_origin: 'starreckon',
                counts: {
                    raw_chars: total * 4,
                    raw_tokens_est: total,
                    model_specific_tokens: total,
                    model_name: topModel
                },
                status: 'ok',
                error_msg: null
            });
        }
    }

    if (Array.isArray(providers?.perSession)) {
        for (const ps of providers.perSession) {
            const sid = String(ps.session_id || `session-${entries.length + 1}`);
            if (seenIds.has(sid)) continue;
            seenIds.add(sid);

            const total = (ps.input || 0) + (ps.output || 0) + (ps.cacheRead || 0) + (ps.cacheWrite || 0);
            const ts = ps.month ? `${ps.month}-01T00:00:00.000Z` : new Date().toISOString();
            const proj = opts.noProjects ? 'project' : (ps.project || ps.provider || 'provider');
            entries.push({
                id: sid,
                source_path: ps.source_path || `${ps.provider || 'provider'}/${sid}`,
                relative_path: proj,
                timestamp: ts,
                tool_origin: 'starreckon',
                counts: {
                    raw_chars: total * 4,
                    raw_tokens_est: total,
                    model_specific_tokens: total,
                    model_name: ps.model || 'generic'
                },
                status: 'ok',
                error_msg: null
            });
        }
    }

    return writeStarreckonCorpus(entries, filepath);
}

// CLI usage
if (import.meta.url === `file://${process.argv[1]}`) {
    const args = process.argv.slice(2);
    if (args.length < 1) {
        console.log('Usage: node deadreckon-reader.mjs <corpus.jsonl> [compare_with.jsonl]');
        process.exit(1);
    }
    
    const drFile = args[0];
    const entries = readDeadreckonCorpus(drFile);
    console.log(`Successfully parsed ${entries.length} entries`);
    
    if (args.length > 1) {
        // Would need SR corpus reader here for full comparison
        console.log('Comparison mode requires Starreckon corpus integration');
    }
}
