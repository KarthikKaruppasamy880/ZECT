/**
 * Desktop shortcut helpers for ZECT Mentrix (Windows primary).
 */
const { app, shell } = require("electron");
const path = require("path");
const fs = require("fs");
const { spawnSync } = require("child_process");

const SHORTCUT_NAME = "ZECT Mentrix.lnk";
const PKG_VERSION = require("./package.json").version;

function isDevMode() {
  return (
    process.env.NODE_ENV === "development" ||
    process.env.ZECT_DEV === "true" ||
    !app.isPackaged
  );
}

function getRepoRoot() {
  return path.resolve(__dirname, "..");
}

function getLauncherScript() {
  return path.join(getRepoRoot(), "RUN_MENTRIX.ps1");
}

function getIconPath() {
  const ico = path.join(__dirname, "icons", "icon.ico");
  if (fs.existsSync(ico)) return ico;
  return path.join(__dirname, "icons", "icon.png");
}

function getShortcutPath() {
  return path.join(app.getPath("desktop"), SHORTCUT_NAME);
}

function getPowerShellPath() {
  const winRoot = process.env.SystemRoot || "C:\\Windows";
  const ps = path.join(winRoot, "System32", "WindowsPowerShell", "v1.0", "powershell.exe");
  return fs.existsSync(ps) ? ps : "powershell.exe";
}

function buildShortcutOptions() {
  if (process.platform !== "win32") {
    return { ok: false, error: "unsupported_platform", platform: process.platform };
  }

  const icon = getIconPath();
  const description = `ZECT Mentrix Control Tower v${PKG_VERSION}`;

  if (isDevMode()) {
    const script = getLauncherScript();
    if (!fs.existsSync(script)) {
      return { ok: false, error: "launcher_not_found", script };
    }
    return {
      ok: true,
      mode: "dev",
      options: {
        target: getPowerShellPath(),
        args: `-ExecutionPolicy Bypass -NoProfile -File "${script}"`,
        cwd: getRepoRoot(),
        description,
        icon,
        iconIndex: 0,
      },
    };
  }

  return {
    ok: true,
    mode: "production",
    options: {
      target: process.execPath,
      cwd: path.dirname(process.execPath),
      description,
      icon,
      iconIndex: 0,
    },
  };
}

function readExistingShortcut(shortcutPath) {
  try {
    return shell.readShortcutLink(shortcutPath);
  } catch {
    return null;
  }
}

function shortcutIsStale(existing, built) {
  if (!existing || !built?.ok) return true;
  const opts = built.options;
  if (existing.target?.toLowerCase() !== opts.target?.toLowerCase()) return true;
  if ((existing.args || "").trim() !== (opts.args || "").trim()) return true;
  if ((existing.cwd || "").toLowerCase() !== (opts.cwd || "").toLowerCase()) return true;
  if (!(existing.description || "").includes(PKG_VERSION)) return true;
  return false;
}

function getDesktopShortcutStatus() {
  const shortcutPath = getShortcutPath();
  const exists = fs.existsSync(shortcutPath);
  const built = buildShortcutOptions();
  const existing = exists ? readExistingShortcut(shortcutPath) : null;

  return {
    ok: built.ok,
    supported: process.platform === "win32",
    platform: process.platform,
    exists,
    stale: exists && shortcutIsStale(existing, built),
    shortcutPath,
    shortcutName: SHORTCUT_NAME,
    mode: built.mode || (isDevMode() ? "dev" : "production"),
    launcherScript: getLauncherScript(),
    version: PKG_VERSION,
    target: built.ok ? built.options.target : null,
    error: built.ok ? undefined : built.error,
    currentTarget: existing?.target || null,
  };
}

function createOrUpdateDesktopShortcut() {
  const status = getDesktopShortcutStatus();
  if (!status.supported) {
    return { ok: false, error: "unsupported_platform", platform: process.platform };
  }
  if (!status.ok) {
    return { ok: false, error: status.error || "shortcut_options_failed" };
  }

  const built = buildShortcutOptions();
  const shortcutPath = getShortcutPath();
  const operation = status.exists ? "update" : "create";

  const wrote = shell.writeShortcutLink(shortcutPath, operation, built.options);
  if (!wrote) {
    return { ok: false, error: "write_failed", shortcutPath };
  }

  return {
    ok: true,
    operation,
    shortcutPath,
    mode: built.mode,
    version: PKG_VERSION,
  };
}

function relaunchApp() {
  app.relaunch();
  app.exit(0);
  return { ok: true };
}

function pullUpdatesAndRelaunch() {
  const repoRoot = getRepoRoot();
  const gitDir = path.join(repoRoot, ".git");
  let pull = { ok: true, skipped: true, message: "not_a_git_repo" };

  if (fs.existsSync(gitDir)) {
    pull = spawnSync("git", ["pull", "--ff-only"], {
      cwd: repoRoot,
      encoding: "utf8",
      windowsHide: true,
    });
    if (pull.status !== 0) {
      return {
        ok: false,
        error: "git_pull_failed",
        stderr: (pull.stderr || pull.stdout || "").trim(),
      };
    }
    pull = { ok: true, skipped: false, message: (pull.stdout || "").trim() || "updated" };
  }

  const shortcut = createOrUpdateDesktopShortcut();
  relaunchApp();
  return { ok: true, pull, shortcut };
}

module.exports = {
  getDesktopShortcutStatus,
  createOrUpdateDesktopShortcut,
  relaunchApp,
  pullUpdatesAndRelaunch,
};
