// Cross-CLI account inventory: who you are in every tool, in one table.
//
// accounts.mjs answers "which Claude profiles" deeply (transcripts, floors).
// This module answers the wider question — "which identities exist anywhere" —
// shallowly: one row per (CLI, store) with the identity it carries, or "local"
// when the store holds usage but no account. Token attribution per account
// stays Claude-only: no other store joins sessions to identities, and
// inventing that join would be worse than omitting it.
//
// IDENTITY POLICY (same tiers as displayAccount): the terminal may show raw
// with --show-accounts; the accounts.json FILE never holds raw — aliases or
// pseudonyms only, enforced by rendering the file with showAccounts=false
// regardless of the flag. A file of all your accounts is exactly what an
// attacker wants, and the archive tree is meant to be safe to sync.
//
// Zero-dependency rule holds: node:fs/path/os only, node:sqlite lazily for
// the opencode account table (email columns ONLY — the credential table is
// never opened; see the opencode reader's column discipline).
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { findConfigDirs, accountFor, displayAccount } from "./accounts.mjs";
import { maskPath } from "./redact.mjs";
import { readConfig } from "./config.mjs";
import { probe, loadSources } from "./sources.mjs";

function readJson(p) {
  try {
    return JSON.parse(readFileSync(p, "utf-8"));
  } catch {
    return null;
  }
}

// Minimal JSONC: strip full-line // comments (copilot's config.json carries
// header comments). Only whole lines whose first non-blank chars are // —
// a // inside a string value never starts a line, so values survive.
function readJsonc(p) {
  let text;
  try {
    text = readFileSync(p, "utf-8");
  } catch {
    return null;
  }
  const stripped = text.split("\n").filter((l) => !/^\s*\/\//.test(l)).join("\n");
  try {
    return JSON.parse(stripped);
  } catch {
    return null;
  }
}

function isDir(p) {
  try {
    return statSync(p).isDirectory();
  } catch {
    return false;
  }
}

function isFile(p) {
  try {
    return statSync(p).isFile();
  } catch {
    return false;
  }
}

// Each extractor returns [{ raw, store }] (raw null = unusable/absent) or [].
// Extractors read IDENTITY FIELDS ONLY — never tokens, secrets, or sessions.
const EXTRACTORS = {
  gemini(home) {
    const d = readJson(join(home, ".gemini", "google_accounts.json"));
    const email = d?.active;
    if (typeof email === "string" && email.includes("@")) {
      return [{ raw: email, store: join(home, ".gemini") }];
    }
    return [];
  },
  copilot(home) {
    const d = readJsonc(join(home, ".copilot", "config.json"));
    const u = d?.lastLoggedInUser;
    if (u && typeof u.login === "string" && u.login) {
      const host = typeof u.host === "string" ? u.host.replace(/^https?:\/\//, "") : "github.com";
      return [{ raw: `${host}:${u.login}`, store: join(home, ".copilot") }];
    }
    return [];
  },
  codex(home) {
    // auth.json is absent until first login; when present, take the first
    // email-shaped string or explicit login field — never token fields.
    const d = readJson(join(home, ".codex", "auth.json"));
    if (!d || typeof d !== "object") return [];
    const cands = [d.email, d.user_email, d.account_email, d.login, d.username];
    for (const c of cands) {
      if (typeof c === "string" && c.trim()) {
        return [{ raw: c.trim(), store: join(home, ".codex") }];
      }
    }
    return [];
  },
  async opencode(home) {
    // Email columns ONLY from the account table. The credential table is
    // never opened (same discipline as the opencode token reader).
    const roots = [];
    if (process.env.XDG_DATA_HOME) roots.push(join(process.env.XDG_DATA_HOME, "opencode", "opencode.db"));
    roots.push(join(home, ".local", "share", "opencode", "opencode.db"));
    const dbp = roots.find(isFile);
    if (!dbp) return [];
    let DatabaseSync;
    try {
      ({ DatabaseSync } = await import("node:sqlite"));
    } catch {
      return [{ raw: null, store: dbp, unreadable: "node:sqlite unavailable" }];
    }
    try {
      const db = new DatabaseSync(dbp, { readonly: true });
      const rows = db.prepare("SELECT id, email FROM account").all();
      db.close();
      return rows
        .filter((r) => typeof r.email === "string" && r.email.includes("@"))
        .map((r) => ({ raw: r.email, store: dbp }));
    } catch {
      return [];
    }
  },
};

// Stores that carry usage but no account concept. Presence = a "local" row;
// absence = no row. This keeps the inventory honest: a tool you never
// installed does not appear, and one without identity does not fake one.
const LOCAL_STORES = {
  qwen: [".qwen/usage", ".qwen/usage_record.jsonl"],
  bob: [".bob/db"],
  aider: [".aider"],
  "muse-code": [".local/share/muse/sessions"],
  lmstudio: [".lmstudio"],
  antigravity: [".antigravity"],
  grok: [".grok/sessions"],
  clawspring: [".clawspring"],
};

// VSCode-extension CLIs resolve presence through the spec's vscode stores
// (all channels), not hand-typed paths — same source the readers use.
const VSCODE_LOCAL = ["muse", "kilocode", "copilot-chat"];

let _SPEC = null;
function specStoresPresent(name, home) {
  _SPEC ??= loadSources();
  const src = _SPEC.sources.find((x) => x.name === name);
  if (!src) return null;
  const pr = probe(src, home, _SPEC);
  return pr.found.length > 0 ? pr.found[0] : null;
}

function localRows(home, cli) {
  if (VSCODE_LOCAL.includes(cli)) {
    const found = specStoresPresent(cli, home);
    return found ? [{ raw: null, store: found }] : [];
  }
  const rels = LOCAL_STORES[cli] ?? [];
  for (const rel of rels) {
    const p = join(home, ...rel.split("/"));
    if (isDir(p) || isFile(p)) return [{ raw: null, store: p }];
  }
  return [];
}

export async function discoverIdentities({ home = homedir(), showAccounts = false, aliases = null } = {}) {
  const cfg = aliases ?? readConfig(home).account_aliases ?? null;
  const rows = [];
  const seen = new Map(); // cli + raw identity -> row (mirrors share accounts)
  const push = (cli, raw, store, kind) => {
    const id = raw ?? `local (${cli})`;
    const dedup = `${cli}\0${id}`;
    const prev = seen.get(dedup);
    if (prev) {
      prev.profiles += 1;
      return;
    }
    const row = {
      cli,
      identity: displayAccount(id, showAccounts, cfg, raw ?? id),
      kind,
      store: maskPath(String(store)),
      profiles: 1,
    };
    seen.set(dedup, row);
    rows.push(row);
  };

  // Claude: every config dir keeps its own identity (multi-profile aware).
  for (const dir of findConfigDirs(home)) {
    const identity = accountFor(dir, home);
    push("claude", identity, dir, "account");
  }
  // Cowork: Claude profiles on macOS — same extractor, own label.
  // (Absent on other platforms; findConfigDirs-equivalent lives in scan.mjs,
  // so cowork rows appear only when its store exists — probed, not parsed.)
  const coworkBase = join(home, "Library", "Application Support", "Claude", "local-agent-mode-sessions");
  if (isDir(coworkBase)) {
    push("cowork", `unknown (${coworkBase})`, coworkBase, "local");
  }

  for (const [cli, fn] of Object.entries(EXTRACTORS)) {
    const found = await fn(home);
    if (found.length === 0) {
      // Store present but identity unreadable/absent (logged out?) still
      // earns a local row when the usage store exists — handled below via
      // LOCAL_STORES for qwen/bob; gemini/copilot/codex/opencode without
      // identity files are simply absent (never installed or logged out).
      continue;
    }
    for (const f of found) push(cli, f.raw, f.store, "account");
  }

  for (const cli of [...Object.keys(LOCAL_STORES), ...VSCODE_LOCAL]) {
    for (const f of localRows(home, cli)) push(cli, null, f.store, "local");
  }
  return rows;
}

// Terminal table. Raw identities appear ONLY with showAccounts (the rows
// already carry display strings; this just lays them out).
export function renderIdentities(rows, { color = false } = {}) {
  const B = color ? "\x1b[1m" : "";
  const R = color ? "\x1b[0m" : "";
  const w = (s, n) => String(s).padEnd(n).slice(0, n);
  const lines = [`${B}── accounts ─────────────────────────────${R}`];
  if (rows.length === 0) {
    lines.push("(no CLI stores found)");
    return lines.join("\n");
  }
  lines.push(`${w("cli", 14)}${w("identity", 28)}${w("kind", 9)}${w("prof", 6)}store`);
  for (const r of rows) {
    lines.push(`${w(r.cli, 14)}${w(r.identity, 28)}${w(r.kind, 9)}${w(r.profiles ?? 1, 6)}${r.store}`);
  }
  return lines.join("\n");
}
