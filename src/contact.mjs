// Contact info — the optional block shown in the QR and on the Share card.
//
// Storage: ~/.starreckon/contact.json. That file is NEVER written by a scan or
// by any automatic process — only by the [C] menu in the terminal, or by the
// user editing it directly. That keeps the privacy contract intact: starreckon
// never collects contact info, you opt in by creating the file.
//
// The fields are deliberate: name, github, email, phone, website, linkedin,
// twitter. `name` lives HERE and not behind a --name flag: a flag is retyped
// every run, is invisible to the [R] screen that claims to show what is
// shared, and bypassed the opt-in contract below. One place owns identity.
// No freeform keys. A controlled set means the QR serialiser knows every tag
// prefix and the menu knows every prompt, and neither has to handle unknowns.

import { existsSync, mkdirSync, readFileSync, writeFileSync, unlinkSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";

// Canonical field order — also the priority order for QR packing (most
// important first, so if the payload is tight the useful fields survive).
export const SOCIAL_SLOTS = 5;
export const SOCIAL_FIELDS = Array.from({ length: SOCIAL_SLOTS }, (_, i) => `social${i + 1}`);

export const FIELDS = [
  "name", "github", "linkedin", "email",
  ...SOCIAL_FIELDS,
  "phone", "website", "twitter",
];

// Short key for each field. ONE map, used by both outputs: the share URL
// (shareurl.mjs imports this) and the text payload (TAGS below derives from it).
// Two hand-maintained copies is how PROVIDER_PREFIXES drifted in deadreckon —
// add an eighth field to FIELDS and there is now exactly one place to update.
export const URL_KEYS = {
  name: "n", github: "gh", email: "em", phone: "tel",
  website: "web", linkedin: "li", twitter: "tw",
  ...Object.fromEntries(SOCIAL_FIELDS.map((f, i) => [f, `s${i + 1}`])),
};

// A social slot holds a URL and NOTHING ELSE. There is no "which platform"
// field to keep in step with it, because the URL already says: the host is the
// answer, and a stored label could disagree with the link beside it.
//
// Byte-mode QR is the constraint, so what travels is the URL with the scheme
// and a leading www. stripped — "twitter.com/someone" instead of
// "https://www.twitter.com/someone", which is 12 bytes cheaper per social and
// re-expands to the same place.
export const SOCIAL_HOSTS = [
  [/(^|\.)x\.com$/,              "X"],
  [/(^|\.)twitter\.com$/,        "Twitter"],
  [/(^|\.)github\.com$/,         "GitHub"],
  [/(^|\.)gitlab\.com$/,         "GitLab"],
  [/(^|\.)linkedin\.com$/,       "LinkedIn"],
  [/(^|\.)youtube\.com$/,        "YouTube"],
  [/(^|\.)youtu\.be$/,           "YouTube"],
  [/(^|\.)instagram\.com$/,      "Instagram"],
  [/(^|\.)facebook\.com$/,       "Facebook"],
  [/(^|\.)tiktok\.com$/,         "TikTok"],
  [/(^|\.)reddit\.com$/,         "Reddit"],
  [/(^|\.)twitch\.tv$/,          "Twitch"],
  [/(^|\.)bsky\.app$/,           "Bluesky"],
  [/(^|\.)threads\.net$/,        "Threads"],
  [/(^|\.)mastodon\.(social|online|world)$/, "Mastodon"],
  [/(^|\.)t\.me$/,               "Telegram"],
  [/(^|\.)discord\.(gg|com)$/,   "Discord"],
  [/(^|\.)medium\.com$/,         "Medium"],
  [/(^|\.)substack\.com$/,       "Substack"],
  [/(^|\.)dev\.to$/,             "DEV"],
  [/(^|\.)hashnode\.(dev|com)$/, "Hashnode"],
  [/(^|\.)stackoverflow\.com$/,  "Stack Overflow"],
  [/(^|\.)huggingface\.co$/,     "Hugging Face"],
  [/(^|\.)kaggle\.com$/,         "Kaggle"],
  [/(^|\.)npmjs\.com$/,          "npm"],
  [/(^|\.)pypi\.org$/,           "PyPI"],
  [/(^|\.)crates\.io$/,          "crates.io"],
  [/(^|\.)news\.ycombinator\.com$/, "Hacker News"],
];

/** Host of a social URL, with or without a scheme, lowercased, www. stripped. */
export function socialHost(url) {
  if (typeof url !== "string" || !url.trim()) return "";
  const s = url.trim();
  const withScheme = /^[a-z][a-z0-9+.-]*:\/\//i.test(s) ? s : "https://" + s;
  let host;
  try {
    host = new URL(withScheme).hostname.toLowerCase();
  } catch {
    return "";
  }
  return host.replace(/^www\./, "");
}

/**
 * What the site IS, read off the link itself.
 *
 * A known host gets its proper name ("X", "Hugging Face"). Anything else gets
 * its own registrable domain, so a personal site or a niche network still gets
 * a truthful heading instead of being labelled "Other" or dropped. An
 * unparseable value has no label — it is not guessed at.
 */
export function labelForUrl(url) {
  const host = socialHost(url);
  if (!host) return "";
  for (const [re, name] of SOCIAL_HOSTS) if (re.test(host)) return name;
  const parts = host.split(".");
  const base = parts.length > 2 ? parts.slice(-2).join(".") : host;
  return base;
}

/** The compact form that travels in the QR: no scheme, no leading www. */
export function compactSocial(url) {
  if (typeof url !== "string" || !url.trim()) return "";
  return url.trim().replace(/^[a-z][a-z0-9+.-]*:\/\//i, "").replace(/^www\./i, "").replace(/\/+$/, "");
}

/**
 * The socials on a contact, in slot order, each with the label read off its
 * own URL. Slots that are empty or unparseable are omitted entirely.
 */
export function socialsOf(contact) {
  const c = contact ?? {};
  const out = [];
  for (const f of SOCIAL_FIELDS) {
    const v = c[f];
    if (typeof v !== "string" || !v.trim()) continue;
    const label = labelForUrl(v);
    if (!label) continue;
    out.push({ field: f, label, url: v.trim(), compact: compactSocial(v) });
  }
  return out;
}

// Tag prefix for the text QR payload. DERIVED, never hand-written: the same key
// as the URL plus a colon, with name unprefixed because it leads the block.
export const TAGS = Object.fromEntries(
  FIELDS.map((f) => [f, f === "name" ? "" : URL_KEYS[f] + ":"]),
);

// Human label for each field — used in the terminal menu.
export const LABELS = {
  name:     "Name",
  github:   "GitHub",
  email:    "Email",
  phone:    "Phone",
  website:  "Website",
  linkedin: "LinkedIn",
  twitter:  "Twitter/X",
  ...Object.fromEntries(SOCIAL_FIELDS.map((f, i) => [f, `Social ${i + 1} (URL)`])),
};

// Menu key bindings — single letter, unique, shown in [brackets].
export const KEYS = {
  N: "name",
  G: "github",
  E: "email",
  P: "phone",
  W: "website",
  L: "linkedin",
  T: "twitter",
  // S1..S5, not 1..5. A JavaScript object orders integer-like keys FIRST
  // whatever the insertion order, so numeric keys put five empty social slots
  // above the user's own name in the menu. A letter prefix keeps the block
  // where it was written.
  ...Object.fromEntries(SOCIAL_FIELDS.map((f, i) => [`S${i + 1}`, f])),
};

export function contactPath(home) {
  return join(home ?? homedir(), ".starreckon", "contact.json");
}

/**
 * Read ~/.starreckon/contact.json. Returns {} when absent or unparseable.
 * Only the known FIELDS keys are kept — unknown keys from manual edits are
 * silently dropped rather than propagated (they would show up in the QR as
 * unrecognised garbage, and nothing in the menu knows how to display them).
 */
export function readContact(home) {
  const file = contactPath(home);
  if (!existsSync(file)) return {};
  let raw;
  try {
    raw = JSON.parse(readFileSync(file, "utf8"));
  } catch {
    return {};
  }
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return {};
  const out = {};
  for (const f of FIELDS) {
    const v = raw[f];
    if (typeof v === "string" && v.trim()) out[f] = v.trim();
  }
  return out;
}

/**
 * Write a contact object back to ~/.starreckon/contact.json.
 * Passing an empty object (or one with no non-empty fields) deletes the file.
 * Only FIELDS keys are written — anything else is stripped.
 */
export function writeContact(home, obj) {
  const file = contactPath(home);
  const set = {};
  for (const f of FIELDS) {
    const v = (obj ?? {})[f];
    if (typeof v === "string" && v.trim()) set[f] = v.trim();
  }
  // Nothing set means no file. That is the opt-in contract: starreckon never
  // collects contact info, and an absent file is how "I have not opted in" is
  // stored. Writing a template of empty strings would look like a half-filled
  // form nobody asked for.
  if (Object.keys(set).length === 0) {
    if (existsSync(file)) unlinkSync(file);
    return;
  }
  // EVERY SLOT IS WRITTEN, in canonical order, empty ones included.
  //
  // Only non-empty fields used to be written, so the file showed whichever
  // fields happened to be filled and the rest did not exist — you could not
  // learn from the file that five social slots were available, only from the
  // menu. The file is the source of truth for this data and it should say what
  // it can hold. An empty string reads the same as absent everywhere that
  // consumes it (readContact keeps only non-empty values), so this changes what
  // the file SHOWS, not what anything downstream sees.
  const clean = {};
  for (const f of FIELDS) clean[f] = set[f] ?? "";
  mkdirSync(join(home ?? homedir(), ".starreckon"), { recursive: true });
  writeFileSync(file, JSON.stringify(clean, null, 2) + "\n", "utf8");
}

/**
 * Build the lines that go into the QR payload for contact fields.
 *
 * Each line is "TAG:value". Lines are packed in FIELDS priority order.
 * A field whose line would push the total past `budget` bytes is skipped
 * entirely — never truncated mid-value, because a half-email is worse than
 * no email. Returns an array of strings (may be empty).
 */
export function contactLines(contact, budget) {
  const enc = new TextEncoder();
  const lines = [];
  let used = 0;
  for (const f of FIELDS) {
    const v = (contact ?? {})[f];
    if (!v) continue;
    const line = TAGS[f] + v;
    const bytes = enc.encode(line + "\n").length;
    if (used + bytes > (budget ?? Infinity)) continue; // skip, never truncate mid-value
    lines.push(line);
    used += bytes;
  }
  return lines;
}
