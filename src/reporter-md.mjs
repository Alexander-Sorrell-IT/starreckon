#!/usr/bin/env node
// Markdown reporter matching deadreckon-count format
import { writeFileSync, mkdirSync } from 'fs';
import { join, dirname } from 'path';

export function generateMarkdownReports(stats, outputDir) {
  const humanDir = join(outputDir, 'reports', 'human');
  const machineDir = join(outputDir, 'reports', 'machine');
  
  mkdirSync(humanDir, { recursive: true });
  mkdirSync(machineDir, { recursive: true });
  
  // Generate BY-COMPUTER.md
  const byComputerMd = generateByComputerReport(stats);
  writeFileSync(join(humanDir, 'BY-COMPUTER.md'), byComputerMd);
  
  // Generate BY-ACCOUNT.md
  const byAccountMd = generateByAccountReport(stats);
  writeFileSync(join(humanDir, 'BY-ACCOUNT.md'), byAccountMd);
  
  // Generate LIFETIME.md
  const lifetimeMd = generateLifetimeReport(stats);
  writeFileSync(join(humanDir, 'LIFETIME.md'), lifetimeMd);
  
  // Generate machine-readable JSON
  const lifetimeJson = {
    generated_at: new Date().toISOString(),
    total_tokens: stats.lifetime.total,
    by_type: {
      input: stats.lifetime.input,
      cache_creation: stats.lifetime.cache_creation,
      cache_read: stats.lifetime.cache_read,
      output: stats.lifetime.output
    },
    sessions: stats.sessionCount,
    computers: Object.keys(stats.byComputer || {}),
    accounts: Object.keys(stats.byAccount || {})
  };
  writeFileSync(join(machineDir, 'lifetime.json'), JSON.stringify(lifetimeJson, null, 2));
  
  // Generate per-computer JSON files
  if (stats.byComputer) {
    const byComputerDir = join(machineDir, 'by-computer');
    mkdirSync(byComputerDir, { recursive: true });
    
    for (const [computer, data] of Object.entries(stats.byComputer)) {
      const safeName = computer.replace(/[^a-zA-Z0-9_-]/g, '_');
      const jsonPath = join(byComputerDir, `${safeName}.json`);
      writeFileSync(jsonPath, JSON.stringify({
        computer,
        total: data.total,
        by_type: {
          input: data.input,
          cache_creation: data.cache_creation,
          cache_read: data.cache_read,
          output: data.output
        },
        sessions: data.sessions,
        accounts: Object.keys(data.byAccount || {})
      }, null, 2));
    }
  }
  
  return {
    byComputer: join(humanDir, 'BY-COMPUTER.md'),
    byAccount: join(humanDir, 'BY-ACCOUNT.md'),
    lifetime: join(humanDir, 'LIFETIME.md'),
    lifetimeJson: join(machineDir, 'lifetime.json')
  };
}

function generateByComputerReport(stats) {
  const lines = [
    '# Token Usage by Computer',
    '',
    `Generated: ${new Date().toISOString()}`,
    '',
    '| Computer | Total | Input | Cache Create | Cache Read | Output | Sessions |',
    '|----------|-------|-------|--------------|------------|--------|----------|'
  ];
  
  if (stats.byComputer) {
    for (const [computer, data] of Object.entries(stats.byComputer)) {
      lines.push(
        `| ${computer} | ${formatNumber(data.total)} | ${formatNumber(data.input)} | ${formatNumber(data.cache_creation)} | ${formatNumber(data.cache_read)} | ${formatNumber(data.output)} | ${data.sessions} |`
      );
    }
  }
  
  lines.push('', '## Summary', '');
  lines.push(`**Total Computers:** ${Object.keys(stats.byComputer || {}).length}`);
  lines.push(`**Total Sessions:** ${stats.sessionCount}`);
  lines.push(`**Grand Total Tokens:** ${formatNumber(stats.lifetime.total)}`);
  
  return lines.join('\n');
}

function generateByAccountReport(stats) {
  const lines = [
    '# Token Usage by Account',
    '',
    `Generated: ${new Date().toISOString()}`,
    '',
    '| Account | Provider | Total | Input | Cache Create | Cache Read | Output |',
    '|---------|----------|-------|-------|--------------|------------|--------|'
  ];
  
  if (stats.byAccount) {
    for (const [account, providers] of Object.entries(stats.byAccount)) {
      for (const [provider, data] of Object.entries(providers)) {
        lines.push(
          `| ${account} | ${provider} | ${formatNumber(data.total)} | ${formatNumber(data.input)} | ${formatNumber(data.cache_creation)} | ${formatNumber(data.cache_read)} | ${formatNumber(data.output)} |`
        );
      }
    }
  }
  
  lines.push('', '## Summary', '');
  const accountCount = Object.keys(stats.byAccount || {}).length;
  lines.push(`**Total Accounts:** ${accountCount}`);
  lines.push(`**Grand Total Tokens:** ${formatNumber(stats.lifetime.total)}`);
  
  return lines.join('\n');
}

function generateLifetimeReport(stats) {
  const lines = [
    '# Lifetime Token Statistics',
    '',
    `Generated: ${new Date().toISOString()}`,
    '',
    '## Grand Totals',
    '',
    `| Metric | Value |`,
    `|--------|-------|`,
    `| **Total Tokens** | ${formatNumber(stats.lifetime.total)} |`,
    `| Input Tokens | ${formatNumber(stats.lifetime.input)} |`,
    `| Cache Creation Tokens | ${formatNumber(stats.lifetime.cache_creation)} |`,
    `| Cache Read Tokens | ${formatNumber(stats.lifetime.cache_read)} |`,
    `| Output Tokens | ${formatNumber(stats.lifetime.output)} |`,
    '',
    '## Session Statistics',
    '',
    `| Metric | Value |`,
    `|--------|-------|`,
    `| Total Sessions | ${stats.sessionCount} |`,
    `| Unique Computers | ${Object.keys(stats.byComputer || {}).length} |`,
    `| Unique Accounts | ${Object.keys(stats.byAccount || {}).length} |`
  ];
  
  return lines.join('\n');
}

function formatNumber(num) {
  return num.toLocaleString();
}
