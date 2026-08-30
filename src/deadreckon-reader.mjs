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

    const sessionsData = JSON.parse(fs.readFileSync(sessionsFile, 'utf8'));
    const totalsData = fs.existsSync(totalsFile) 
        ? JSON.parse(fs.readFileSync(totalsFile, 'utf8')) 
        : null;

    // Handle both array format and object with sessions property
    const sessions = Array.isArray(sessionsData) ? sessionsData : (sessionsData.sessions || []);
    
    const transformedSessions = sessions.map(session => ({
        id: session.session_id || session.id,
        provider: session.provider || detectProviderFromModel(session.model),
        model: session.model,
        timestamp: session.timestamp || session.date || session.start,
        tokens: {
            input: session.tokens?.input_tokens || session.input_tokens || 0,
            output: session.tokens?.output_tokens || session.output_tokens || 0,
            cacheCreation: session.tokens?.cache_creation_input_tokens || session.cache_creation_input_tokens || 0,
            cacheRead: session.tokens?.cache_read_input_tokens || session.cache_read_input_tokens || 0,
            total: (session.tokens?.input_tokens || session.input_tokens || 0) + 
                   (session.tokens?.output_tokens || session.output_tokens || 0) + 
                   (session.tokens?.cache_creation_input_tokens || session.cache_creation_input_tokens || 0) + 
                   (session.tokens?.cache_read_input_tokens || session.cache_read_input_tokens || 0)
        },
        cost: session.total_cost || session.cost || 0,
        sourceFile: sessionsFile,
        redacted: false
    }));

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
