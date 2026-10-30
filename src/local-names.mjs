// Directory names that belong to ONE machine and must never ship: checkouts
// and archives of private programs that sit in the home directory beside the
// live stores. They are read from ~/.starreckon/local-dirs.json, outside this
// tree, so the skip still happens on the machines that have them:
//
//   { "copyDirs": [...], "skipDirs": [...], "fleetDirs": [...] }
//
// copyDirs joins accounts.mjs COPY_DIRS, skipDirs joins discover.mjs SKIP,
// fleetDirs (paths relative to $HOME) are tried before ~/token-usage when no
// --fleet is given. A missing or unreadable file means no extras, never a crash.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";

function load() {
  const file = process.env.STARRECKON_LOCAL_DIRS
    || join(process.env.HOME || homedir(), ".starreckon", "local-dirs.json");
  try {
    const j = JSON.parse(readFileSync(file, "utf8"));
    const list = (k) => (Array.isArray(j[k]) ? j[k].filter((s) => typeof s === "string" && s) : []);
    return { copyDirs: list("copyDirs"), skipDirs: list("skipDirs"), fleetDirs: list("fleetDirs") };
  } catch {
    return { copyDirs: [], skipDirs: [], fleetDirs: [] };
  }
}

export const LOCAL = Object.freeze(load());
