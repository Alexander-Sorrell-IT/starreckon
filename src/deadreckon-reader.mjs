/**
 * Deadreckon Reader Module - Reads Deadreckon corpus files for Starreckon.
 * Handles malformed lines, missing fields, and schema validation.
 * Falls back to generic mode if models/daemons config is missing.
 */
import { readFileSync, existsSync } from 'fs';
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
            
            // Validate minimal schema
            if (!entry.id || !entry.source_path) {
                console.error(`Warning: Line ${i + 1} missing required fields (id, source_path), skipping`);
                errors++;
                continue;
            }
            
            // Normalize tool_origin if missing
            if (!entry.tool_origin) {
                entry.tool_origin = 'deadreckon';
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
