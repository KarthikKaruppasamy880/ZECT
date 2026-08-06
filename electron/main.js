/**
 * ZECT Desktop App — Electron main process.
 *
 * Mentrix wake: Windows System.Speech (headset mic) + global hotkey.
 * BrowserRouter uses pathname navigation (not hash).
 */

const { app, BrowserWindow, Menu, shell, ipcMain, globalShortcut, session } = require("electron");
const path = require("path");
const { matchesWakePhrase } = require("./wake");
const { startWindowsWake } = require("./win-wake");
const { startDictation } = require("./dictation");
const computer = require("./computer");
const shortcuts = require("./shortcuts");
const { stripEchoPhrases, passesVoiceGate } = require("./voice-filter");

const isDev = process.env.NODE_ENV === "development" || process.env.ZECT_DEV === "true";
const DEV_URL = process.env.ZECT_DEV_URL || "http://127.0.0.1:5173";
const WAKE_PHRASE = process.env.WAKE_PHRASE || "Hey Mentrix";

let mainWindow;
let wakeEnabled = true;
let winWakeHandle = null;
let wakeStatus = { ok: false, reason: "starting", engine: "" };
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
    mainWindow.loadFile(path.join(__dirname, "..", "frontend", "dist", "index.html"));
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
}));
ipcMain.handle("mentrix-confirm-action", (_e, payload) => {
  // Renderer shows modal; main records intent only
  if (computerMode) armComputerModeIdle();
  return { ok: true, recorded: true, payload: payload || {} };
});
ipcMain.handle("mentrix-computer", async (_e, action, args) => {
  if (!computerMode) {
    return { ok: false, error: "computer_mode_off" };
  }
  armComputerModeIdle();
  const a = args || {};
  if (DELETE_ACTIONS.has(String(action || "").toLowerCase())) {
    console.warn("[mentrix-computer] refuse delete", action, a.path || a.file || "");
    return {
      ok: false,
      error: "delete_never_allowed",
      action,
      audited: true,
      note: "Mentrix never deletes, unlinks, or rmdirs files",
    };
  }
  if (action === "open_zoom" || action === "desktop_open_zoom") {
    lastOpenedApp = process.platform === "darwin" ? "zoom.us" : "Zoom.exe";
    return computer.openZoom(a);
  }
  if (action === "open_app" || action === "open") {
    const appName =
      a.app || a.appName || (process.platform === "darwin" ? "TextEdit" : "notepad.exe");
    lastOpenedApp = appName;
    return computer.openApp(appName, a);
  }
  if (
    action === "open_presentation" ||
    action === "desktop_open_presentation" ||
    action === "open_path"
  ) {
    return computer.openPresentation(a.path || a.file || "");
  }
  if (
    action === "parse_presentation_slides" ||
    action === "desktop_parse_presentation_slides"
  ) {
    return computer.parsePresentationSlides(a.path || a.file || "");
  }
  if (action === "powerpoint_key" || action === "desktop_powerpoint_key") {
    return computer.powerpointKey(a.key || a.keycode, a.app || a.appName);
  }
  if (action === "screenshot" || action === "desktop_screenshot") {
    const desk = await computer.screenshotDesktop();
    if (desk.ok) return desk;
    try {
      const img = await mainWindow.webContents.capturePage();
      const png = img.toPNG();
      return { ok: true, desktop: "screenshot", bytes: png.length, note: "window_fallback" };
    } catch (err) {
      return { ok: false, error: String(err) };
    }
  }
  if (action === "read_path" || action === "desktop_read") {
    const target = a.path || a.file || "";
    if (!target || pathBlocked(target)) {
      return { ok: false, error: "path_blocked", path: target };
    }
    const fs = require("fs");
    try {
      if (!fs.existsSync(target)) return { ok: false, error: "not_found" };
      const stat = fs.statSync(target);
      if (!stat.isFile() || stat.size > 256_000) {
        return { ok: false, error: "file_too_large_or_not_file" };
      }
      const text = fs.readFileSync(target, "utf8").slice(0, 8000);
      return { ok: true, path: target, preview: text, audited: true };
    } catch (err) {
      return { ok: false, error: String(err) };
    }
  }
  if (action === "write_note" || action === "desktop_write_note" || action === "write_path") {
    return computer.writeNoteFile(a);
  }
  if (action === "click" || action === "computer_click") {
    return computer.clickAt(a.x, a.y, a.app || a.appName || lastOpenedApp);
  }
  if (action === "type" || action === "computer_type") {
    return computer.typeText(a.text, a.app || a.appName || lastOpenedApp);
  }
  if (action === "scroll" || action === "computer_scroll") {
    return computer.scroll(a.direction || "down");
  }
  if (action === "ui_inspect" || action === "computer_ui_inspect") {
    return computer.uiInspect();
  }
  return { ok: false, error: "unsupported_action", action };
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

app.whenReady().then(() => {
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

  // Native Windows wake uses default recording device (set headset mic in Windows Sound settings)
  startNativeWake();
});

app.on("will-quit", () => {
  globalShortcut.unregisterAll();
  if (winWakeHandle) {
    winWakeHandle.stop();
    winWakeHandle = null;
  }
  stopDictation();
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
