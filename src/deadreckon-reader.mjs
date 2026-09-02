import fs from 'fs';
import path from 'path';

/**
 * Reader for Deadreckon-Count machine-readable corpus files.
 * Allows Starreckon to import and verify totals from existing Deadreckon outputs
 * when raw session logs are unavailable or archived.
 */

export async function readDeadreckonCorpus(corpusPath) {
    const machineReadablePath = path.join(corpusPath, 'machine-readable');
    const sessionsFile = path.join(machineReadablePath, 'sessions.json');
    const totalsFile = path.join(machineReadablePath, 'totals.json');

    if (!fs.existsSync(sessionsFile)) {
        throw new Error(`Deadreckon sessions.json not found at ${sessionsFile}`);
    }

    let sessionsData;
    try {
        const sessionsContent = fs.readFileSync(sessionsFile, 'utf8');
        // Limit file size to prevent DoS (10MB max)
        if (sessionsContent.length > 10 * 1024 * 1024) {
            throw new Error('Sessions file exceeds 10MB limit');
        }
        sessionsData = JSON.parse(sessionsContent);
    } catch (err) {
        if (err instanceof SyntaxError) {
            throw new Error(`Invalid JSON in sessions file: ${err.message}`);
        }
        throw err;
    }
    
    let totalsData = null;
    if (fs.existsSync(totalsFile)) {
        try {
            const totalsContent = fs.readFileSync(totalsFile, 'utf8');
            if (totalsContent.length > 10 * 1024 * 1024) {
                throw new Error('Totals file exceeds 10MB limit');
            }
            totalsData = JSON.parse(totalsContent);
        } catch (err) {
            if (err instanceof SyntaxError) {
                throw new Error(`Invalid JSON in totals file: ${err.message}`);
            }
            throw err;
        }
    }

    // Handle both array format and object with sessions property
    const sessions = Array.isArray(sessionsData) ? sessionsData : (sessionsData.sessions || []);
    
    const transformedSessions = sessions.map(session => {
        // Validate session_id - reject null/undefined
        const sessionId = session.session_id || session.id;
        if (!sessionId) {
            console.warn('Warning: Skipping session with missing session_id');
            return null;
        }
        
        // Safely extract token counts with validation
        const inputTokens = session.tokens?.input_tokens ?? session.input_tokens ?? 0;
        const outputTokens = session.tokens?.output_tokens ?? session.output_tokens ?? 0;
        const cacheCreationTokens = session.tokens?.cache_creation_input_tokens ?? session.cache_creation_input_tokens ?? 0;
        const cacheReadTokens = session.tokens?.cache_read_input_tokens ?? session.cache_read_input_tokens ?? 0;
        
        // Validate and sanitize token values
        const sanitizeTokenCount = (val, fieldName) => {
            if (typeof val !== 'number' || !Number.isFinite(val)) {
                console.warn(`Warning: Invalid ${fieldName} value: ${val}, using 0`);
                return 0;
            }
            // Reject negative tokens
            if (val < 0) {
                console.warn(`Warning: Negative ${fieldName} value: ${val}, using 0`);
                return 0;
            }
            // Round floats to integers
            if (!Number.isInteger(val)) {
                console.warn(`Warning: Float ${fieldName} value: ${val}, rounding to ${Math.round(val)}`);
                return Math.round(val);
            }
            // Check for unsafe integers
            if (!Number.isSafeInteger(val)) {
                console.warn(`Warning: Unsafe integer ${fieldName}: ${val}, capping at MAX_SAFE_INTEGER`);
                return Number.MAX_SAFE_INTEGER;
            }
            return val;
        };
        
        const safeInput = sanitizeTokenCount(inputTokens, 'input_tokens');
        const safeOutput = sanitizeTokenCount(outputTokens, 'output_tokens');
        const safeCacheCreation = sanitizeTokenCount(cacheCreationTokens, 'cache_creation_input_tokens');
        const safeCacheRead = sanitizeTokenCount(cacheReadTokens, 'cache_read_input_tokens');
        
        // Sanitize model name (limit length to prevent DoS)
        let modelName = session.model || 'unknown';
        if (typeof modelName !== 'string') {
            modelName = String(modelName);
        }
        if (modelName.length > 1024) {
            console.warn(`Warning: Truncating long model name (${modelName.length} chars)`);
            modelName = modelName.substring(0, 1024);
        }
        
        return {
            id: sessionId,
            provider: session.provider || detectProviderFromModel(modelName),
            model: modelName,
            timestamp: session.timestamp || session.date || session.start,
            tokens: {
                input: safeInput,
                output: safeOutput,
                cacheCreation: safeCacheCreation,
                cacheRead: safeCacheRead,
                total: safeInput + safeOutput + safeCacheCreation + safeCacheRead
            },
            cost: typeof session.total_cost === 'number' ? session.total_cost : 
                  typeof session.cost === 'number' ? session.cost : 0,
            sourceFile: sessionsFile,
            redacted: false
        };
    }).filter(s => s !== null); // Remove sessions with missing IDs

    return {
        sessions: transformedSessions,
        totals: totalsData ? {
            totalTokens: totalsData.anthropic_only_tokens || 
                        totalsData.total_tokens || 
                        (totalsData.grand_total && totalsData.grand_total.total_tokens) || 0,
            totalCost: totalsData.total_cost || 
                      (totalsData.grand_total && totalsData.grand_total.total_cost) || 0,
            sessionCount: totalsData.session_count || 
                         (totalsData.grand_total && totalsData.grand_total.session_count) || sessions.length,
            byProvider: totalsData.by_provider || totalsData.byProvider || {},
            byModel: totalsData.by_model || totalsData.byModel || {}
        } : calculateTotals(transformedSessions),
        source: 'deadreckon-corpus',
        importedAt: new Date().toISOString()
    };
}

function detectProviderFromModel(modelName) {
    if (!modelName) return 'unknown';
    const lower = modelName.toLowerCase();
    
    if (lower.includes('claude') || lower.includes('anthropic')) return 'claude-code';
    if (lower.includes('gemini')) return 'gemini-cli';
    if (lower.includes('copilot') || lower.includes('gpt-4')) return 'copilot-cli';
    if (lower.includes('cline')) return 'cline';
    
    return 'unknown';
}

function calculateTotals(sessions) {
    let totalTokens = 0;
    let totalCost = 0;
    const byProvider = {};
    const byModel = {};

    for (const session of sessions) {
        totalTokens += session.tokens.total;
        totalCost += session.cost;

        // Aggregate by provider
        if (!byProvider[session.provider]) {
            byProvider[session.provider] = { tokens: 0, cost: 0, sessions: 0 };
        }
        byProvider[session.provider].tokens += session.tokens.total;
        byProvider[session.provider].cost += session.cost;
        byProvider[session.provider].sessions += 1;

        // Aggregate by model
        if (!byModel[session.model]) {
            byModel[session.model] = { tokens: 0, cost: 0, sessions: 0 };
        }
        byModel[session.model].tokens += session.tokens.total;
        byModel[session.model].cost += session.cost;
        byModel[session.model].sessions += 1;
    }

    return {
        totalTokens,
        totalCost,
        sessionCount: sessions.length,
        byProvider,
        byModel
    };
}

export default readDeadreckonCorpus;
