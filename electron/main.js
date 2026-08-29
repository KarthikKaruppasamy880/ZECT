/**
 * ZECT Desktop App — Electron main process.
 *
 * Mentrix wake: Windows System.Speech (headset mic) + global hotkey.
 * BrowserRouter uses pathname navigation (not hash).
 */

const { app, BrowserWindow, Menu, shell, ipcMain, globalShortcut, session, dialog } = require("electron");
const path = require("path");
const fs = require("fs");
const { matchesWakePhrase } = require("./wake");
const { startWindowsWake } = require("./win-wake");
const { startDictation } = require("./dictation");
const computer = require("./computer");
const shortcuts = require("./shortcuts");
const chatterbox = require("./chatterbox");
const { stripEchoPhrases, passesVoiceGate } = require("./voice-filter");
const serviceLifecycle = require("./service-lifecycle");

// Single-instance lock (A7) — second launch focuses the existing window.
const gotSingleInstanceLock =
  process.env.ZECT_ALLOW_MULTI_INSTANCE === "1" ? true : app.requestSingleInstanceLock();
if (!gotSingleInstanceLock) {
  app.quit();
}

// Unpackaged `electron .` must hit Vite — otherwise loadFile(dist) uses file:// + absolute
// /assets paths and the window stays blank (navy backgroundColor only).
// Force dist locally with ZECT_USE_DIST=1. Packaged builds always use dist.
const preferDist = process.env.ZECT_USE_DIST === "1";
const isDev =
  !preferDist &&
  (process.env.NODE_ENV === "development" ||
    process.env.ZECT_DEV === "true" ||
    !app.isPackaged);
const DEV_URL = process.env.ZECT_DEV_URL || "http://127.0.0.1:5173";
const WAKE_PHRASE = process.env.WAKE_PHRASE || "Hey Mentrix";

/** Canonical packaged UI index candidates (asar + unpacked layouts). */
function resolvePackagedIndexHtml() {
  const candidates = [
    path.join(__dirname, "frontend", "dist", "index.html"),
    path.join(__dirname, "..", "frontend", "dist", "index.html"),
    path.join(process.resourcesPath || "", "frontend", "dist", "index.html"),
    path.join(process.resourcesPath || "", "app.asar.unpacked", "frontend", "dist", "index.html"),
  ];
  for (const p of candidates) {
    try {
      if (p && fs.existsSync(p)) return p;
    } catch {
      /* ignore */
    }
  }
  return candidates[0];
}

function ensureUserDataDirs() {
  try {
    const base = app.getPath("userData");
    for (const sub of ["logs", "config", "data"]) {
      const dir = path.join(base, sub);
      if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    }
    return base;
  } catch {
    return null;
  }
}

let mainWindow;
let wakeEnabled = false;
let winWakeHandle = null;
let wakeStatus = { ok: false, reason: "disabled", engine: "" };
let dictationHandle = null;
let dictationArmedUntil = 0;
let dictationPaused = false;
let dictationArmTimer = null;

function isDictationArmed() {
  return Date.now() < dictationArmedUntil && !dictationPaused;
}

function stopDictation() {
  if (dictationArmTimer) {
    clearTimeout(dictationArmTimer);
    dictationArmTimer = null;
  }
  dictationArmedUntil = 0;
  if (dictationHandle) {
    dictationHandle.stop();
    dictationHandle = null;
  }
  if (wakeEnabled) startNativeWake();
}

function startDictationLoop() {
  if (dictationHandle) return;
  if (winWakeHandle) {
    winWakeHandle.stop();
    winWakeHandle = null;
  }
  dictationHandle = startDictation(
    (text) => {
      if (!mainWindow || !text || !isDictationArmed()) return;
      const goal = stripEchoPhrases(String(text));
      if (!passesVoiceGate(goal)) return;
      mainWindow.webContents.send("mentrix-stt-goal", {
        goal,
        ts: new Date().toISOString(),
        staged: true,
      });
      stopDictation();
    },
    (status) => {
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send("mentrix-wake-status", { ...wakeStatus, dictation: status });
      }
    },
  );
}

function armDictation(durationMs = 15000) {
  if (process.platform !== "win32") {
    return { ok: false, reason: "not_windows" };
  }
  const ms = Math.max(3000, Math.min(Number(durationMs) || 15000, 30000));
  dictationArmedUntil = Date.now() + ms;
  startDictationLoop();
  if (dictationArmTimer) clearTimeout(dictationArmTimer);
  dictationArmTimer = setTimeout(() => {
    stopDictation();
  }, ms);
  return { ok: true, armedUntil: dictationArmedUntil, durationMs: ms };
}

let computerMode = false;
let computerModeIdleTimer = null;
/** Ring buffer of Computer Mode audits (never includes secrets). */
const computerAuditLog = [];
const COMPUTER_AUDIT_MAX = 200;
/** Mobile Companion → desktop command queue (Electron agent). */
const desktopCommandQueue = [];
const DESKTOP_QUEUE_MAX = 50;

function pushComputerAudit(entry) {
  computerAuditLog.unshift({
    ts: new Date().toISOString(),
    ...entry,
  });
  if (computerAuditLog.length > COMPUTER_AUDIT_MAX) computerAuditLog.length = COMPUTER_AUDIT_MAX;
}
let lastOpenedApp = null;
const COMPUTER_MODE_IDLE_MS = Number(process.env.MENTRIX_COMPUTER_IDLE_MS || 10 * 60 * 1000);
const ALLOWLISTED_APPS =
  process.platform === "darwin" ? computer.MAC_APPS : computer.WIN_APPS;
const BLOCKED_PATH_FRAGMENTS = [".env", "id_rsa", "credentials", "password", "secrets", ".aws", ".ssh"];

function clearComputerModeIdle() {
  if (computerModeIdleTimer) {
    clearTimeout(computerModeIdleTimer);
    computerModeIdleTimer = null;
  }
}

function armComputerModeIdle() {
  clearComputerModeIdle();
  if (!computerMode) return;
  computerModeIdleTimer = setTimeout(() => {
    computerMode = false;
    lastOpenedApp = null;
    clearComputerModeIdle();
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send("mentrix-computer-mode", { computerMode: false, reason: "idle_auto_off" });
    }
  }, COMPUTER_MODE_IDLE_MS);
}

function pathBlocked(p) {
  const s = String(p || "").toLowerCase();
  return BLOCKED_PATH_FRAGMENTS.some((frag) => s.includes(frag));
}

const DELETE_ACTIONS = new Set([
  "delete",
  "delete_file",
  "desktop_delete",
  "unlink",
  "rmdir",
  "rm",
  "remove",
  "remove_file",
  "remove_dir",
]);

async function waitForDevServer(url, attempts = 20, delayMs = 500) {
  const http = require("http");
  const target = new URL(url);
  for (let i = 0; i < attempts; i += 1) {
    try {
      await new Promise((resolve, reject) => {
        const req = http.get(
          { hostname: target.hostname, port: target.port, path: target.pathname || "/", timeout: 2000 },
          (res) => {
            res.resume();
            if (res.statusCode && res.statusCode >= 200 && res.statusCode < 500) resolve(undefined);
            else reject(new Error(`status ${res.statusCode}`));
          },
        );
        req.on("error", reject);
        req.on("timeout", () => {
          req.destroy();
          reject(new Error("timeout"));
        });
      });
      return true;
    } catch {
      await new Promise((r) => setTimeout(r, delayMs));
    }
  }
  return false;
}

async function loadDevUrlWithRetry(win, url) {
  const ready = await waitForDevServer(url);
  if (!ready) {
    console.warn("ZECT dev server not ready yet — loading anyway:", url);
  }
  if (win && !win.isDestroyed()) {
    await win.loadURL(url);
  }
}

function navigateMentrix() {
  if (!mainWindow) return;
  // Wake only — persistent dock expands + Connect Voice. Avoid hard location.assign (remounts React).
  const js = `
    (function () {
      try {
        window.dispatchEvent(new CustomEvent('mentrix-wake', { detail: { phrase: 'Mentrix', expand: true } }));
      } catch (e) {}
    })();
  `;
  mainWindow.webContents.executeJavaScript(js).catch(() => {});
}

function emitWake(phrase, source) {
  if (!wakeEnabled || !mainWindow) return;
  if (mainWindow.isMinimized()) mainWindow.restore();
  mainWindow.show();
  mainWindow.focus();
  mainWindow.webContents.send("mentrix-wake", {
    phrase,
    source,
    ts: new Date().toISOString(),
  });
  navigateMentrix();
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    title: "ZECT — Mentrix Control Tower",
    icon: path.join(__dirname, "icons", "icon.png"),
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
    titleBarStyle: "default",
    backgroundColor: "#0f172a",
    show: false,
  });

  // Phase 11 Stage B — production CSP (dev keeps Vite HMR flexible)
  if (!isDev) {
    session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
      const headers = { ...details.responseHeaders };
      headers["Content-Security-Policy"] = [
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self' http://127.0.0.1:* http://localhost:* ws://127.0.0.1:* ws://localhost:*; media-src 'self' blob:; font-src 'self' data:; object-src 'none'; base-uri 'self'; form-action 'self'",
      ];
      callback({ responseHeaders: headers });
    });
  }

  if (isDev) {
    loadDevUrlWithRetry(mainWindow, DEV_URL);
    // Detached DevTools + Realtime audio can destabilize the renderer; keep optional.
    if (process.env.ZECT_DEVTOOLS === "1") {
      mainWindow.webContents.openDevTools({ mode: "detach" });
    }
  } else {
    const indexHtml = resolvePackagedIndexHtml();
    mainWindow.loadFile(indexHtml).catch((err) => {
      console.error("[zect] failed to load packaged UI", indexHtml, err);
    });
  }

  mainWindow.once("ready-to-show", () => {
    mainWindow.show();
  });

  if (isDev) {
    mainWindow.webContents.on("did-fail-load", (_event, errorCode, errorDescription, validatedURL, isMainFrame) => {
      if (!isMainFrame || errorCode === -3) return;
      console.error("ZECT dev load failed:", errorCode, errorDescription, validatedURL);
      setTimeout(() => {
        if (mainWindow && !mainWindow.isDestroyed()) {
          loadDevUrlWithRetry(mainWindow, DEV_URL);
        }
      }, 1500);
    });
  }

  // Recover from blank screen after Connect Voice / audio renderer crashes.
  // Cap + debounce — ACCESS_VIOLATION (0xC0000005 / -1073741819) during WebAudio
  // TTS used to reload on every Mentrix turn and looked like a restart loop.
  let rendererCrashReloads = 0;
  let rendererCrashReloadTimer = null;
  mainWindow.webContents.on("did-finish-load", () => {
    rendererCrashReloads = 0;
  });
  mainWindow.webContents.on("render-process-gone", (_event, details) => {
    console.error("ZECT renderer gone:", details.reason, details.exitCode);
    if (!mainWindow || mainWindow.isDestroyed()) return;
    if (rendererCrashReloads >= 2) {
      console.error(
        "ZECT renderer crash loop — not auto-reloading again. Use View → Reload if the window is blank.",
      );
      return;
    }
    rendererCrashReloads += 1;
    if (rendererCrashReloadTimer) clearTimeout(rendererCrashReloadTimer);
    rendererCrashReloadTimer = setTimeout(() => {
      rendererCrashReloadTimer = null;
      if (mainWindow && !mainWindow.isDestroyed()) {
        console.warn("ZECT recovering from renderer crash — reloading once");
        mainWindow.webContents.reload();
      }
    }, 750);
  });
  // Do not auto-reload on "unresponsive" — Mentrix TTS/Realtime can briefly block
  // the renderer without it being permanently stuck.
  mainWindow.webContents.on("unresponsive", () => {
    console.warn("ZECT renderer unresponsive — not auto-reloading");
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith("http")) {
      shell.openExternal(url);
    }
    return { action: "deny" };
  });
}

function startNativeWake() {
  if (!wakeEnabled) {
    if (winWakeHandle) {
      winWakeHandle.stop();
      winWakeHandle = null;
    }
    wakeStatus = { ok: false, reason: "disabled", engine: "windows-speech" };
    if (mainWindow) {
      mainWindow.webContents.send("mentrix-wake-status", { wakeEnabled, ...wakeStatus });
    }
    return;
  }
  if (winWakeHandle) {
    winWakeHandle.stop();
    winWakeHandle = null;
  }
  if (process.platform !== "win32") {
    wakeStatus = { ok: false, reason: "use_hotkey", engine: "hotkey" };
    return;
  }
  winWakeHandle = startWindowsWake(
    (phrase) => {
      if (matchesWakePhrase(phrase, WAKE_PHRASE) || /mentrix|matrix/i.test(phrase)) {
        emitWake(phrase || WAKE_PHRASE, "windows-speech");
      }
    },
    (status) => {
      wakeStatus = { ...status, engine: status.engine || "windows-speech" };
      if (mainWindow) {
        mainWindow.webContents.send("mentrix-wake-status", wakeStatus);
      }
    },
  );
}

ipcMain.handle("get-app-path", () => app.getAppPath());
ipcMain.handle("zect-select-directory", async (_e, opts = {}) => {
  const result = await dialog.showOpenDialog(mainWindow || undefined, {
    title: opts.title || "Select local Git repository folder",
    defaultPath: opts.defaultPath || app.getPath("desktop"),
    properties: ["openDirectory", "createDirectory"],
  });
  if (result.canceled || !result.filePaths?.length) {
    return { ok: false, canceled: true };
  }
  return { ok: true, path: result.filePaths[0] };
});
ipcMain.handle("zect-select-file", async (_e, opts = {}) => {
  const filters = Array.isArray(opts.filters) && opts.filters.length
    ? opts.filters
    : [{ name: "All files", extensions: ["*"] }];
  const result = await dialog.showOpenDialog(mainWindow || undefined, {
    title: opts.title || "Select file",
    defaultPath: opts.defaultPath || app.getPath("desktop"),
    properties: ["openFile"],
    filters,
  });
  if (result.canceled || !result.filePaths?.length) {
    return { ok: false, canceled: true };
  }
  return { ok: true, path: result.filePaths[0] };
});
ipcMain.handle("zect-save-presentation-file", async (_e, opts = {}) => {
  const fs = require("fs");
  const defaultName = String(opts.defaultName || "zect-deck.pptx");
  const result = await dialog.showSaveDialog(mainWindow || undefined, {
    title: opts.title || "Save presentation",
    defaultPath: opts.defaultPath || path.join(app.getPath("documents"), defaultName),
    filters: [{ name: "PowerPoint", extensions: ["pptx"] }],
  });
  if (result.canceled || !result.filePath) {
    return { ok: false, canceled: true };
  }
  const dataBase64 = String(opts.dataBase64 || "");
  if (!dataBase64) {
    return { ok: false, error: "missing_data" };
  }
  const buf = Buffer.from(dataBase64, "base64");
  fs.writeFileSync(result.filePath, buf);
  const stat = fs.statSync(result.filePath);
  return { ok: true, path: result.filePath, bytes: stat.size };
});
ipcMain.handle("zect-read-presentation-file", async (_e, filePath) => {
  return computer.readPresentationBytes(filePath || "");
});
ipcMain.handle("zect-shortcut-status", () => shortcuts.getDesktopShortcutStatus());
ipcMain.handle("zect-shortcut-create", () => shortcuts.createOrUpdateDesktopShortcut());
ipcMain.handle("zect-relaunch", () => shortcuts.relaunchApp());
ipcMain.handle("zect-pull-relaunch", () => shortcuts.pullUpdatesAndRelaunch());
ipcMain.handle("mentrix-engage", (_e, goal) => {
  emitWake("Mentrix engage", "ipc");
  return { ok: true, goal: goal || "", agent: "Mentrix" };
});
ipcMain.handle("mentrix-wake-enabled", (_e, enabled) => {
  wakeEnabled = Boolean(enabled);
  if (wakeEnabled) startNativeWake();
  else if (winWakeHandle) {
    winWakeHandle.stop();
    winWakeHandle = null;
  }
  return { wakeEnabled };
});
ipcMain.handle("mentrix-wake-status", () => ({ wakeEnabled, ...wakeStatus }));
ipcMain.handle("mentrix-stt-transcript", (_e, transcript) => {
  if (matchesWakePhrase(transcript, WAKE_PHRASE)) {
    emitWake(WAKE_PHRASE, "stt");
    return { matched: true, phrase: WAKE_PHRASE };
  }
  return { matched: false };
});
ipcMain.handle("mentrix-stt-goal", (_e, goal) => {
  if (!mainWindow || !goal) return { ok: false };
  mainWindow.webContents.send("mentrix-stt-goal", { goal: String(goal), ts: new Date().toISOString() });
  return { ok: true };
});
ipcMain.handle("mentrix-dictation-enabled", (_e, enabled) => {
  if (!enabled) {
    stopDictation();
    return { ok: true, dictation: false };
  }
  return armDictation(15000);
});
ipcMain.handle("mentrix-dictation-arm", (_e, durationMs) => armDictation(durationMs));
ipcMain.handle("mentrix-dictation-disarm", () => {
  stopDictation();
  return { ok: true, dictation: false };
});
ipcMain.handle("mentrix-dictation-pause", (_e, paused) => {
  dictationPaused = Boolean(paused);
  return { ok: true, paused: dictationPaused };
});
ipcMain.handle("mentrix-computer-mode", (_e, enabled) => {
  computerMode = Boolean(enabled);
  if (computerMode) armComputerModeIdle();
  else {
    clearComputerModeIdle();
    lastOpenedApp = null;
  }
  return { computerMode, idleMs: COMPUTER_MODE_IDLE_MS };
});
ipcMain.handle("mentrix-get-policy", () => ({
  computerMode,
  wakeEnabled,
  allowlistedApps: ALLOWLISTED_APPS,
  blockedPathFragments: BLOCKED_PATH_FRAGMENTS,
  idleMs: COMPUTER_MODE_IDLE_MS,
  platform: process.platform,
  lastOpenedApp,
  emergencyStop: Boolean(globalThis.__zectEmergencyStop),
  note: "Desktop actions require Electron + Computer Mode on.",
}));
ipcMain.handle("mentrix-computer-audit", () => ({
  items: computerAuditLog.slice(0, 50),
}));
ipcMain.handle("mentrix-chatterbox-status", async () => chatterbox.status());
ipcMain.handle("mentrix-chatterbox-start", async () => chatterbox.start());
ipcMain.handle("mentrix-chatterbox-stop", async () => chatterbox.stop());
ipcMain.handle("mentrix-chatterbox-resolve", async () => {
  const launch = chatterbox.resolveLaunch();
  return {
    launch,
    bundled: Boolean(launch && launch.bundled),
    binaryPath: launch && launch.mode === "bin" ? launch.path : "",
  };
});
ipcMain.handle("mentrix-desktop-queue-push", (_e, cmd) => {
  const item = {
    id: `dc-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    ts: new Date().toISOString(),
    command: cmd || {},
    status: "queued",
  };
  desktopCommandQueue.push(item);
  if (desktopCommandQueue.length > DESKTOP_QUEUE_MAX) desktopCommandQueue.shift();
  return { ok: true, id: item.id, queued: desktopCommandQueue.length };
});
ipcMain.handle("mentrix-desktop-queue-list", () => ({
  items: desktopCommandQueue.slice(),
  computerMode,
  online: true,
}));
ipcMain.handle("mentrix-desktop-queue-ack", (_e, id) => {
  const idx = desktopCommandQueue.findIndex((x) => x.id === id);
  if (idx >= 0) {
    desktopCommandQueue[idx].status = "acked";
    return { ok: true };
  }
  return { ok: false, error: "not_found" };
});
ipcMain.handle("mentrix-confirm-action", (_e, payload) => {
  // Renderer shows modal; main records intent only
  if (computerMode) armComputerModeIdle();
  pushComputerAudit({ kind: "confirm", payload: payload || {} });
  return { ok: true, recorded: true, payload: payload || {} };
});
ipcMain.handle("mentrix-computer", async (_e, action, args) => {
  if (!computerMode) {
    pushComputerAudit({ kind: "refuse", action, error: "computer_mode_off" });
    return { ok: false, error: "computer_mode_off", hint: "Desktop actions require Electron + Computer Mode on." };
  }
  // PA-5: honor global emergency stop (env or cached flag from renderer)
  const emergency =
    process.env.MENTRIX_EMERGENCY_STOP === "1" ||
    process.env.ZECT_EMERGENCY_STOP === "1" ||
    globalThis.__zectEmergencyStop === true;
  if (emergency) {
    pushComputerAudit({ kind: "refuse", action, error: "emergency_stop_active" });
    return {
      ok: false,
      error: "emergency_stop_active",
      hint: "Global emergency stop is active — desktop automation blocked",
    };
  }
  armComputerModeIdle();
  const a = args || {};
  if (DELETE_ACTIONS.has(String(action || "").toLowerCase())) {
    console.warn("[mentrix-computer] refuse delete", action, a.path || a.file || "");
    pushComputerAudit({ kind: "refuse_delete", action, path: a.path || a.file || "" });
    return {
      ok: false,
      error: "delete_never_allowed",
      action,
      audited: true,
      note: "Mentrix never deletes, unlinks, or rmdirs files",
    };
  }
  let result;
  if (action === "open_zoom" || action === "desktop_open_zoom") {
    lastOpenedApp = process.platform === "darwin" ? "zoom.us" : "Zoom.exe";
    result = await computer.openZoom(a);
  } else if (action === "open_app" || action === "open") {
    const appName =
      a.app || a.appName || (process.platform === "darwin" ? "TextEdit" : "notepad.exe");
    lastOpenedApp = appName;
    result = await computer.openApp(appName, a);
  } else if (
    action === "open_presentation" ||
    action === "desktop_open_presentation" ||
    action === "open_path"
  ) {
    result = await computer.openPresentation(a.path || a.file || "");
  } else if (
    action === "parse_presentation_slides" ||
    action === "desktop_parse_presentation_slides"
  ) {
    result = await computer.parsePresentationSlides(a.path || a.file || "");
  } else if (action === "powerpoint_key" || action === "desktop_powerpoint_key") {
    result = await computer.powerpointKey(a.key || a.keycode, a.app || a.appName);
  } else if (action === "screenshot" || action === "desktop_screenshot") {
    const desk = await computer.screenshotDesktop();
    if (desk.ok) {
      result = desk;
    } else {
      try {
        const img = await mainWindow.webContents.capturePage();
        const png = img.toPNG();
        result = { ok: true, desktop: "screenshot", bytes: png.length, note: "window_fallback" };
      } catch (err) {
        result = { ok: false, error: String(err) };
      }
    }
  } else if (action === "read_path" || action === "desktop_read") {
    const target = a.path || a.file || "";
    if (!target || pathBlocked(target)) {
      result = { ok: false, error: "path_blocked", path: target };
    } else {
      const fs = require("fs");
      try {
        if (!fs.existsSync(target)) result = { ok: false, error: "not_found" };
        else {
          const stat = fs.statSync(target);
          if (!stat.isFile() || stat.size > 256_000) {
            result = { ok: false, error: "file_too_large_or_not_file" };
          } else {
            const text = fs.readFileSync(target, "utf8").slice(0, 8000);
            result = { ok: true, path: target, preview: text, audited: true };
          }
        }
      } catch (err) {
        result = { ok: false, error: String(err) };
      }
    }
  } else if (action === "write_note" || action === "desktop_write_note" || action === "write_path") {
    result = await computer.writeNoteFile(a);
  } else if (action === "mkdir" || action === "desktop_mkdir" || action === "create_folder") {
    result = computer.mkdirPath(a);
  } else if (action === "list_dir" || action === "desktop_list_dir") {
    result = computer.listDir(a);
  } else if (action === "move_path" || action === "desktop_move_path" || action === "rename_path") {
    result = computer.movePath(a);
  } else if (action === "click" || action === "computer_click") {
    const intended = a.app || a.appName || lastOpenedApp;
    const before = await computer.uiInspect();
    if (!before?.ok || before.allowlisted !== true) {
      result = {
        ok: false,
        error: "foreground_not_allowlisted",
        verified: false,
        verification: { kind: "a11y_before", before: before?.summary || before },
        hint: "Focus an allowlisted app window before click",
      };
    } else if (intended && !computer.processMatchesIntended(before, intended)) {
      result = {
        ok: false,
        error: "foreground_mismatch",
        verified: false,
        intended,
        verification: { kind: "a11y_before", before: before?.summary || before },
        hint: `Foreground does not match intended app ${intended}`,
      };
    } else {
      result = await computer.clickAt(a.x, a.y, intended);
      const after = await computer.uiInspect();
      const matched = computer.processMatchesIntended(after, intended);
      if (result && typeof result === "object") {
        result.verification = {
          kind: "a11y_before_after",
          before: before?.summary || before,
          after: after?.summary || after,
          matched,
          note: "Coordinate click is fallback only — prefer UI inspect target match",
        };
        result.verified = Boolean(result.ok) && matched;
        if (result.ok && !matched) {
          result.ok = false;
          result.error = "post_click_verify_failed";
        }
      }
    }
  } else if (action === "type" || action === "computer_type") {
    const intended = a.app || a.appName || lastOpenedApp;
    if (intended) {
      await computer.waitForAllowlistedForeground(intended, { attempts: 6, delayMs: 200 });
    }
    const before = await computer.uiInspect();
    if (!before?.ok || before.allowlisted !== true) {
      result = {
        ok: false,
        error: "foreground_not_allowlisted",
        verified: false,
        verification: { kind: "a11y_before", before: before?.summary || before },
        hint: "Focus an allowlisted app window (Notepad / Notepad++ / Zoom / …) before type — Mentrix may still be in front",
      };
    } else if (intended && !computer.processMatchesIntended(before, intended)) {
      result = {
        ok: false,
        error: "foreground_mismatch",
        verified: false,
        intended,
        verification: { kind: "a11y_before", before: before?.summary || before },
        hint: `Foreground does not match intended app ${intended}`,
      };
    } else {
      result = await computer.typeText(a.text, intended);
      const after = await computer.uiInspect();
      const matched = computer.processMatchesIntended(after, intended);
      if (result && typeof result === "object") {
        result.verification = {
          kind: "a11y_before_after",
          before: before?.summary || before,
          after: after?.summary || after,
          allowlisted: after?.allowlisted,
          matched,
        };
        result.verified = Boolean(result.ok) && matched;
        if (result.ok && !matched) {
          result.ok = false;
          result.error = "post_type_verify_failed";
        }
      }
    }
  } else if (action === "scroll" || action === "computer_scroll") {
    result = await computer.scroll(a.direction || "down");
  } else if (action === "ui_inspect" || action === "computer_ui_inspect") {
    result = await computer.uiInspect();
  } else {
    result = { ok: false, error: "unsupported_action", action };
  }
  pushComputerAudit({
    kind: "action",
    action,
    ok: Boolean(result && result.ok),
    error: result && result.error ? result.error : undefined,
    app: a.app || a.appName || lastOpenedApp || undefined,
    correlation_id: a.correlation_id || a.correlationId || undefined,
    verification: (result && result.verification) || {
      kind: "desktop",
      note: "Prefer active-window / a11y read-back; screenshot is fallback only",
      path: a.path || a.file || undefined,
    },
  });
  return result;
});

ipcMain.handle("mentrix-emergency-stop", (_e, active) => {
  globalThis.__zectEmergencyStop = Boolean(active);
  pushComputerAudit({ kind: "emergency_stop", active: Boolean(active) });
  return { ok: true, active: Boolean(active) };
});

const menuTemplate = [
  {
    label: "ZECT",
    submenu: [
      { label: "About ZECT", role: "about" },
      { type: "separator" },
      {
        label: "Settings",
        accelerator: "CmdOrCtrl+,",
        click: () =>
          mainWindow?.webContents.executeJavaScript("window.location.assign('/settings')"),
      },
      {
        label: "Create Desktop Shortcut",
        click: async () => {
          const res = shortcuts.createOrUpdateDesktopShortcut();
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send("zect-shortcut-result", res);
          }
          if (res.ok) {
            mainWindow?.webContents.executeJavaScript(
              "window.location.assign('/mentrix-home')",
            );
          }
        },
      },
      { type: "separator" },
      { label: "Quit", accelerator: "CmdOrCtrl+Q", click: () => app.quit() },
    ],
  },
  {
    label: "File",
    submenu: [
      {
        label: "Add Folder to Workspace…",
        click: () => {
          mainWindow?.webContents.executeJavaScript(`
            (function () {
              window.__zectWsCommand = "add-folder";
              if (!String(location.pathname || "").includes("/workspace")) {
                location.assign("/workspace");
                return;
              }
              window.dispatchEvent(new CustomEvent("zect-workspace-command", { detail: { action: "add-folder" } }));
            })();
          `);
        },
      },
      {
        label: "Remove Folder from Workspace",
        click: () => {
          mainWindow?.webContents.executeJavaScript(`
            (function () {
              window.__zectWsCommand = "remove-folder";
              if (!String(location.pathname || "").includes("/workspace")) {
                location.assign("/workspace");
                return;
              }
              window.dispatchEvent(new CustomEvent("zect-workspace-command", { detail: { action: "remove-folder" } }));
            })();
          `);
        },
      },
    ],
  },
  {
    label: "Mentrix",
    submenu: [
      {
        label: "Open Mentrix / Wake",
        accelerator: "CmdOrCtrl+Shift+Space",
        click: () => emitWake("Mentrix engage", "menu"),
      },
      {
        label: "Restart wake listening",
        click: () => {
          wakeEnabled = true;
          startNativeWake();
        },
      },
      {
        label: "Toggle wake listening",
        click: () => {
          wakeEnabled = !wakeEnabled;
          if (wakeEnabled) startNativeWake();
          else if (winWakeHandle) {
            winWakeHandle.stop();
            winWakeHandle = null;
            wakeStatus = { ok: false, reason: "disabled", engine: "windows-speech" };
          }
        },
      },
    ],
  },
  {
    label: "Edit",
    submenu: [
      { role: "undo" },
      { role: "redo" },
      { type: "separator" },
      { role: "cut" },
      { role: "copy" },
      { role: "paste" },
      { role: "selectAll" },
    ],
  },
  {
    label: "View",
    submenu: [
      { role: "reload" },
      { role: "forceReload" },
      { role: "toggleDevTools" },
      { type: "separator" },
      { role: "resetZoom" },
      { role: "zoomIn" },
      { role: "zoomOut" },
      { type: "separator" },
      { role: "togglefullscreen" },
    ],
  },
  {
    label: "Navigate",
    submenu: [
      {
        label: "Dashboard",
        accelerator: "CmdOrCtrl+1",
        click: () =>
          mainWindow?.webContents.executeJavaScript("window.location.assign('/')"),
      },
      {
        label: "Lattice",
        accelerator: "CmdOrCtrl+2",
        click: () =>
          mainWindow?.webContents.executeJavaScript("window.location.assign('/lattice')"),
      },
      {
        label: "Mentrix",
        accelerator: "CmdOrCtrl+3",
        click: () => emitWake("Mentrix", "nav"),
      },
      {
        label: "Build",
        accelerator: "CmdOrCtrl+4",
        click: () =>
          mainWindow?.webContents.executeJavaScript("window.location.assign('/build')"),
      },
      {
        label: "Sandbox Gate",
        accelerator: "CmdOrCtrl+5",
        click: () =>
          mainWindow?.webContents.executeJavaScript("window.location.assign('/sandbox')"),
      },
    ],
  },
  {
    label: "Help",
    submenu: [
      {
        label: "Documentation",
        click: () => shell.openExternal("https://github.com/KarthikKaruppasamy880/ZECT"),
      },
    ],
  },
];

app.on("second-instance", () => {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  if (mainWindow.isMinimized()) mainWindow.restore();
  mainWindow.show();
  mainWindow.focus();
});

app.whenReady().then(async () => {
  if (!gotSingleInstanceLock) return;

  const userData = ensureUserDataDirs();
  if (userData) {
    console.log("[zect] userData", userData);
  }

  // Packaged: auto-start bundled API sidecar into userData. Voicebox/Presenton optional.
  try {
    const packaged = Boolean(app.isPackaged);
    const resourcesPath = packaged ? process.resourcesPath : path.join(__dirname, "resources");
    const readiness = await serviceLifecycle.checkReadiness({
      resourcesPath,
      packaged,
    });
    const shouldManage =
      packaged ||
      process.env.ZECT_MANAGE_SERVICES === "1" ||
      process.env.ZECT_START_SIDECAR === "1";
    if (!readiness.api.ok && shouldManage) {
      const started = serviceLifecycle.startBackendSidecar({
        resourcesPath,
        userData,
        packaged,
      });
      console.log("[zect] backend sidecar", JSON.stringify(started));
      if (started.started) {
        const waited = await serviceLifecycle.waitForApi(45000);
        console.log("[zect] api wait", JSON.stringify(waited));
      } else if (!started.started && packaged) {
        console.warn("[zect] packaged backend sidecar unavailable", started.reason || "");
      }
    } else if (!readiness.api.ok && process.env.ZECT_MANAGE_SERVICES === "1") {
      const repoRoot = packaged ? path.join(process.resourcesPath, "..") : path.join(__dirname, "..");
      const started = serviceLifecycle.tryStartLocalScript(repoRoot);
      console.log("[zect] manage services start", JSON.stringify(started));
    }
    console.log("[zect] service readiness", JSON.stringify(readiness));
  } catch (e) {
    console.warn("[zect] service readiness probe failed", e);
  }

  session.defaultSession.setPermissionRequestHandler((_wc, permission, callback) => {
    if (permission === "media" || permission === "microphone" || permission === "audioCapture") {
      callback(true);
      return;
    }
    callback(false);
  });

  const menu = Menu.buildFromTemplate(menuTemplate);
  Menu.setApplicationMenu(menu);
  createWindow();

  globalShortcut.register("CommandOrControl+Shift+Space", () => {
    emitWake(WAKE_PHRASE, "hotkey");
  });

  // Hey Mentrix wake stays off until the operator enables it (Companion chip or Mentrix menu).

  // Bundled Chatterbox sidecar: auto-start when binary is present (or CHATTERBOX_AUTO_START=1)
  chatterbox.maybeAutoStart().then((out) => {
    if (out && out.ok && !out.skipped) {
      console.log("[chatterbox] auto-started", out.pid || "", out.binaryPath || "");
    } else if (out && out.skipped) {
      console.log("[chatterbox]", out.skipped, out.hint || "");
    } else if (out && out.error) {
      console.warn("[chatterbox] auto-start failed:", out.error);
    }
  }).catch((err) => console.warn("[chatterbox] auto-start error", err));
});

app.on("will-quit", () => {
  globalShortcut.unregisterAll();
  if (winWakeHandle) {
    winWakeHandle.stop();
    winWakeHandle = null;
  }
  stopDictation();
  try {
    serviceLifecycle.stopManagedChildren();
  } catch {
    /* ignore */
  }
  try {
    chatterbox.stop();
  } catch {
    /* ignore */
  }
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("activate", () => {
  if (mainWindow === null) {
    createWindow();
  }
});
