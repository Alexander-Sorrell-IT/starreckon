// Optional scheduled re-scan + transcript protection ticker.
//
// Why it exists: AI-coding logs age off disk (roughly 30 days), so a scan you
// run once shows one month and can never show more. Snapshots are the fix —
// they outlive the logs — but only if something takes them regularly. That is
// the whole job here: run the scan on a schedule so the monthly history keeps
// building instead of rolling off.
//
// Why it does NOT install itself: this module writes a plain-text schedule file
// and prints the ONE command that loads it. It never spawns launchctl, never
// edits a crontab behind your back, and never registers anything as a side
// effect of a normal scan. That is deliberate and it is the same principle the
// rest of the tool runs on — you can read the file before it is live, and the
// step that makes it live is a command you typed. A "privacy-first" tool that
// silently installs a background job that reads your disk every month would be
// arguing against itself.
//
// Two jobs:
//
//   SCAN   work.starreckon.scan    — monthly, 1st of each month at 09:00
//            runs: starreckon --yes --no-wrapped --no-pace --ledger
//            purpose: monthly snapshot so lifetime numbers keep growing past
//            the ~30-day log retention window
//
//   PROTECT  work.starreckon.protect — every 6 hours
//            runs: starreckon protect
//            purpose: raise cleanupPeriodDays and hard-link-archive ALL CLI
//            session files so a transcript deletion cannot erase the record
//            from the ledger.  optional but without it the numbers degrade.
//
// Nothing here is network-aware. Both scheduled runs are purely local.

import { existsSync, mkdirSync, readFileSync, writeFileSync, unlinkSync } from "node:fs";
import { homedir, platform } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { TRIGGER_ENV } from "./layerlog.mjs";

export const LABEL         = "work.starreckon.scan";
export const PROTECT_LABEL = "work.starreckon.protect";

// HOW A SCHEDULED RUN KNOWS IT IS ONE.
//
// The consent screen promises a log for every run of the daemon layer, and the
// daemon layer IS these two jobs. But a scheduled run reaches cli.mjs by the
// same argv a person can type, so the process cannot tell the two apart by
// looking at itself. The schedule file — the artifact this module writes and
// the user reads before loading it — is the one place that knows, so it says
// so, in an environment variable the job carries.
//
// Consequences, both of them honest and neither of them hidden:
//   · a SCHEDULE WRITTEN BEFORE THIS EXISTED carries no marker, so its runs are
//     indistinguishable from typed ones and write no log. `starreckon daemon on`
//     rewrites both files and fixes it; `daemon status` says which is installed.
//   · the marker is a CLAIM. Anyone can export it and get a run recorded as
//     scheduled, so the record names the variable it believed rather than
//     presenting "scheduled" as something it measured (layerlog.mjs).
// WHAT THE SCHEDULED SCAN DELIBERATELY DOES NOT DO.
//
// The argv below is `--yes --no-wrapped --no-pace --ledger`. It is NOT --full,
// and that is a decision rather than an omission: --full runs the model layer's
// auto-index, and the model layer is SEPARATELY CONSENTED. runSearch() exists
// so every model invocation passes through one door and writes one log, because
// the consent screen promises a log for every run of the layer. A daemon
// spawning a Python embedding job on a timer runs a consented-separately layer
// without its consent, on a schedule nobody is watching.
//
// The consequence is real and is named where it can be seen rather than papered
// over: nothing re-indexes on its own, so sessions recorded after the last
// manual `search --search-index` are counted, snapshotted and NOT SEARCHABLE.
// `search --search-status` now reports "N indexed · M on disk" for exactly that
// reason — it used to print only N, so a stale index and a complete one looked
// identical.
//
// The scan is what must run unattended: AI-coding logs age off disk in about
// thirty days and the snapshots are what outlive them. An index can be rebuilt
// from data that is still there; a transcript that aged out cannot.
export const SCAN_TRIGGER    = "daemon:scan";
export const PROTECT_TRIGGER = "daemon:protect";

const HOME = () => homedir();

// ---- macOS plist paths --------------------------------------------------------
const plistPath         = () => join(HOME(), "Library", "LaunchAgents", `${LABEL}.plist`);
const protectPlistPath  = () => join(HOME(), "Library", "LaunchAgents", `${PROTECT_LABEL}.plist`);

// ---- Linux systemd paths -----------------------------------------------------
const systemdDir         = () => join(HOME(), ".config", "systemd", "user");
const servicePath        = () => join(systemdDir(), "starreckon-scan.service");
const timerPath          = () => join(systemdDir(), "starreckon-scan.timer");
const protectServicePath = () => join(systemdDir(), "starreckon-protect.service");
const protectTimerPath   = () => join(systemdDir(), "starreckon-protect.timer");

// ---- Windows Task Scheduler paths --------------------------------------------
const winDir             = () => join(HOME(), ".starreckon", "daemon");
const winScanXmlPath     = () => join(winDir(), "starreckon-scan.xml");
const winProtectXmlPath  = () => join(winDir(), "starreckon-protect.xml");

// The CLI entry point to schedule. Resolved from THIS file so a checkout and an
// installed package both schedule the copy you actually ran.
export function cliEntry() {
  return join(dirname(fileURLToPath(import.meta.url)), "cli.mjs");
}

function esc(s) {
  return String(s).replace(/[<>&"']/g, (c) => ({
    "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;", "'": "&apos;",
  })[c]);
}

/**
 * The macOS launchd plist for the monthly scan job.
 * StartCalendarInterval fires on the 1st of each month at 09:00; launchd runs
 * a missed job at next login rather than skipping it, so a laptop that was
 * asleep still gets its snapshot.
 */
export function launchdPlist({ node = process.execPath, entry = cliEntry(), day = 1, hour = 9 } = {}) {
  const logDir = join(HOME(), ".starreckon", "daemon");
  return `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${esc(node)}</string>
    <string>${esc(entry)}</string>
    <string>--yes</string>
    <string>--no-wrapped</string>
    <string>--no-pace</string>
    <string>--ledger</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>${esc(TRIGGER_ENV)}</key><string>${SCAN_TRIGGER}</string>
  </dict>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Day</key><integer>${day}</integer>
    <key>Hour</key><integer>${hour}</integer>
    <key>Minute</key><integer>0</integer>
  </dict>
  <key>RunAtLoad</key><false/>
  <key>StandardOutPath</key><string>${esc(join(logDir, "scan.log"))}</string>
  <key>StandardErrorPath</key><string>${esc(join(logDir, "scan.err"))}</string>
</dict>
</plist>
`;
}

/**
 * The macOS launchd plist for the 6-hour protect+ledger job.
 * StartInterval fires every 21600 seconds (6 hours).
 */
export function launchdProtectPlist({ node = process.execPath, entry = cliEntry() } = {}) {
  const logDir = join(HOME(), ".starreckon", "daemon");
  return `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>${PROTECT_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${esc(node)}</string>
    <string>${esc(entry)}</string>
    <string>protect</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>${esc(TRIGGER_ENV)}</key><string>${PROTECT_TRIGGER}</string>
  </dict>
  <key>StartInterval</key><integer>21600</integer>
  <key>RunAtLoad</key><false/>
  <key>StandardOutPath</key><string>${esc(join(logDir, "protect.log"))}</string>
  <key>StandardErrorPath</key><string>${esc(join(logDir, "protect.err"))}</string>
</dict>
</plist>
`;
}

export function systemdUnits({ node = process.execPath, entry = cliEntry() } = {}) {
  return {
    service: `[Unit]
Description=starreckon monthly local scan (no network)

[Service]
Type=oneshot
Environment=${TRIGGER_ENV}=${SCAN_TRIGGER}
ExecStart=${node} ${entry} --yes --no-wrapped --no-pace --ledger
`,
    timer: `[Unit]
Description=Run starreckon monthly so snapshots outlive the ~30-day log retention

[Timer]
OnCalendar=monthly
Persistent=true

[Install]
WantedBy=timers.target
`,
  };
}

/**
 * The systemd units for the 6-hour protect+ledger job.
 * OnCalendar must be `0/6:00:00` (H/6:M:S). `*:0/6:00` normalizes to
 * `*-*-* *:00/6:00` — every 6 MINUTES, 240 ticks/day against the launchd
 * sibling's 4, and each tick is a depth-4 $HOME walk plus a recursive walk of
 * every CLI store. Check with: systemd-analyze calendar '0/6:00:00'
 */
export function systemdProtectUnits({ node = process.execPath, entry = cliEntry() } = {}) {
  return {
    service: `[Unit]
Description=starreckon 6-hour transcript protection + ledger tick (no network)

[Service]
Type=oneshot
Environment=${TRIGGER_ENV}=${PROTECT_TRIGGER}
ExecStart=${node} ${entry} protect
`,
    timer: `[Unit]
Description=Raise transcript retention and hard-link-archive AI session files every 6h

[Timer]
OnCalendar=0/6:00:00
Persistent=true

[Install]
WantedBy=timers.target
`,
  };
}

/**
 * The Windows Task Scheduler XML for the monthly scan job.
 * Fires on the 1st of each month at 09:00 with StartWhenAvailable to run on next wake.
 */
export function windowsTaskXml({ node = process.execPath, entry = cliEntry(), day = 1, hour = 9 } = {}) {
  const logDir = join(HOME(), ".starreckon", "daemon");
  const scanLog = join(logDir, "scan.log");
  const scanErr = join(logDir, "scan.err");
  const startHour = String(hour).padStart(2, "0");
  return `<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>starreckon monthly local scan (no network)</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-01-01T${startHour}:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByMonth>
        <DaysOfMonth>
          <Day>${day}</Day>
        </DaysOfMonth>
        <Months>
          <January/><February/><March/><April/><May/><June/><July/><August/><September/><October/><November/><December/>
        </Months>
      </ScheduleByMonth>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <ExecutionTimeLimit>PT2H</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>cmd.exe</Command>
      <Arguments>/c "set ${TRIGGER_ENV}=${SCAN_TRIGGER} &amp;&amp; \"${esc(node)}\" \"${esc(entry)}\" --yes --no-wrapped --no-pace --ledger &gt;&gt; \"${esc(scanLog)}\" 2&gt;&gt; \"${esc(scanErr)}\""</Arguments>
    </Exec>
  </Actions>
</Task>
`;
}

/**
 * The Windows Task Scheduler XML for the 6-hour protect+ledger job.
 * Fires every 6 hours (PT6H repetition).
 */
export function windowsProtectTaskXml({ node = process.execPath, entry = cliEntry() } = {}) {
  const logDir = join(HOME(), ".starreckon", "daemon");
  const protectLog = join(logDir, "protect.log");
  const protectErr = join(logDir, "protect.err");
  return `<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>starreckon 6-hour transcript protection + ledger tick (no network)</Description>
  </RegistrationInfo>
  <Triggers>
    <TimeTrigger>
      <StartBoundary>2026-01-01T00:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <Repetition>
        <Interval>PT6H</Interval>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
    </TimeTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <ExecutionTimeLimit>PT1H</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>cmd.exe</Command>
      <Arguments>/c "set ${TRIGGER_ENV}=${PROTECT_TRIGGER} &amp;&amp; \"${esc(node)}\" \"${esc(entry)}\" protect &gt;&gt; \"${esc(protectLog)}\" 2&gt;&gt; \"${esc(protectErr)}\""</Arguments>
    </Exec>
  </Actions>
</Task>
`;
}

// Does the schedule file ON DISK carry the marker that makes its runs
// identifiable? A schedule written before the marker existed still works — it
// scans, it protects — but its runs are indistinguishable from a typed command
// and so write no log, and the consent screen promised one. Silence there would
// be the exact failure this project keeps hitting: nothing written looks the
// same as nothing happened. So it is measured off the file and reported.
function marked(file) {
  if (!file || !existsSync(file)) return null; // null = no file, not "no marker"
  try { return readFileSync(file, "utf8").includes(TRIGGER_ENV); } catch { return null; }
}

export function daemonStatus() {
  const p = platform();
  if (p === "darwin") {
    const file          = plistPath();
    const protectFile   = protectPlistPath();
    return {
      platform:  p,
      supported: true,
      installed: existsSync(file),
      file,
      protectInstalled: existsSync(protectFile),
      protectFile,
      logged:        marked(file),
      protectLogged: marked(protectFile),
    };
  }
  if (p === "linux") {
    // The marker lives in the .service (what runs), not the .timer (when).
    return {
      platform:  p,
      supported: true,
      installed: existsSync(timerPath()) && existsSync(servicePath()),
      file:      timerPath(),
      protectInstalled: existsSync(protectTimerPath()) && existsSync(protectServicePath()),
      protectFile:      protectTimerPath(),
      logged:        marked(servicePath()),
      protectLogged: marked(protectServicePath()),
    };
  }
  if (p === "win32") {
    const file        = winScanXmlPath();
    const protectFile = winProtectXmlPath();
    return {
      platform:  p,
      supported: true,
      installed: existsSync(file),
      file,
      protectInstalled: existsSync(protectFile),
      protectFile,
      logged:        marked(file),
      protectLogged: marked(protectFile),
    };
  }
  return {
    platform: p, supported: false, installed: false, file: null,
    protectInstalled: false, protectFile: null, logged: null, protectLogged: null,
  };
}

/**
 * Write the schedule file(s). Returns { files, activate } — `activate` is the
 * command the USER runs to make it live. Nothing is loaded here.
 */
export function writeSchedule(opts = {}) {
  const p = platform();
  if (p === "darwin") {
    const file        = plistPath();
    const protectFile = protectPlistPath();
    mkdirSync(dirname(file), { recursive: true });
    mkdirSync(join(HOME(), ".starreckon", "daemon"), { recursive: true });
    writeFileSync(file, launchdPlist(opts));
    writeFileSync(protectFile, launchdProtectPlist(opts));
    return {
      files:      [file, protectFile],
      activate:   `launchctl load ${file} && launchctl load ${protectFile}`,
      deactivate: `launchctl unload ${file} && launchctl unload ${protectFile}`,
    };
  }
  if (p === "linux") {
    const dir = systemdDir();
    mkdirSync(dir, { recursive: true });
    const units        = systemdUnits(opts);
    const protectUnits = systemdProtectUnits(opts);
    writeFileSync(servicePath(), units.service);
    writeFileSync(timerPath(), units.timer);
    writeFileSync(protectServicePath(), protectUnits.service);
    writeFileSync(protectTimerPath(), protectUnits.timer);
    return {
      files:      [servicePath(), timerPath(), protectServicePath(), protectTimerPath()],
      activate:
        "systemctl --user daemon-reload && " +
        "systemctl --user enable --now starreckon-scan.timer && " +
        "systemctl --user enable --now starreckon-protect.timer",
      deactivate:
        "systemctl --user disable --now starreckon-scan.timer && " +
        "systemctl --user disable --now starreckon-protect.timer",
    };
  }
  if (p === "win32") {
    const dir = winDir();
    mkdirSync(dir, { recursive: true });
    const file = winScanXmlPath();
    const protectFile = winProtectXmlPath();
    writeFileSync(file, windowsTaskXml(opts));
    writeFileSync(protectFile, windowsProtectTaskXml(opts));
    return {
      files:      [file, protectFile],
      activate:
        `schtasks /Create /TN "${LABEL}" /XML "${file}" /F && ` +
        `schtasks /Create /TN "${PROTECT_LABEL}" /XML "${protectFile}" /F`,
      deactivate:
        `schtasks /Delete /TN "${LABEL}" /F && ` +
        `schtasks /Delete /TN "${PROTECT_LABEL}" /F`,
    };
  }
  return { files: [], activate: null, deactivate: null, unsupported: p };
}

/** Remove the schedule files. Returns the paths removed and the unload command. */
export function removeSchedule() {
  const st = daemonStatus();
  const removed = [];

  let scanFiles, protectFiles;
  if (st.platform === "linux") {
    scanFiles    = [timerPath(), servicePath()];
    protectFiles = [protectTimerPath(), protectServicePath()];
  } else if (st.platform === "win32") {
    scanFiles    = [winScanXmlPath()];
    protectFiles = [winProtectXmlPath()];
  } else {
    scanFiles    = [plistPath()];
    protectFiles = [protectPlistPath()];
  }

  for (const f of [...scanFiles, ...protectFiles]) {
    if (existsSync(f)) {
      try { unlinkSync(f); removed.push(f); } catch {}
    }
  }

  let deactivate;
  if (st.platform === "linux") {
    deactivate = "systemctl --user disable --now starreckon-scan.timer && systemctl --user disable --now starreckon-protect.timer";
  } else if (st.platform === "win32") {
    deactivate = `schtasks /Delete /TN "${LABEL}" /F && schtasks /Delete /TN "${PROTECT_LABEL}" /F`;
  } else {
    deactivate = `launchctl unload ${plistPath()} && launchctl unload ${protectPlistPath()}`;
  }

  return { removed, deactivate };
}

/** What a written schedule actually contains, for printing before it goes live. */
export function describeSchedule() {
  const st = daemonStatus();
  if (!st.supported) return null;
  if (!st.installed) return null;
  try {
    return readFileSync(st.file, "utf8");
  } catch {
    return null;
  }
}

