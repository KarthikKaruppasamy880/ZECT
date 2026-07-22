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

const isDev = process.env.NODE_ENV === "development" || process.env.ZECT_DEV === "true";
const DEV_URL = process.env.ZECT_DEV_URL || "http://127.0.0.1:5173";
const WAKE_PHRASE = process.env.WAKE_PHRASE || "Hey Mentrix";

let mainWindow;
let wakeEnabled = true;
let winWakeHandle = null;
let wakeStatus = { ok: false, reason: "starting", engine: "" };
let dictationHandle = null;

let computerMode = false;
let computerModeIdleTimer = null;
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

function navigateMentrix() {
  if (!mainWindow) return;
  const js = `
    (function () {
      try {
        if (window.location.pathname !== '/mentrix-home') {
          window.location.assign('/mentrix-home');
        } else {
          window.dispatchEvent(new CustomEvent('mentrix-wake', { detail: { phrase: 'Mentrix' } }));
        }
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

  if (isDev) {
    mainWindow.loadURL(DEV_URL);
    mainWindow.webContents.openDevTools({ mode: "detach" });
  } else {
    mainWindow.loadFile(path.join(__dirname, "..", "frontend", "dist", "index.html"));
  }

  mainWindow.once("ready-to-show", () => {
    mainWindow.show();
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
  if (dictationHandle) {
    dictationHandle.stop();
    dictationHandle = null;
  }
  if (!enabled) return { ok: true, dictation: false };
  dictationHandle = startDictation(
    (text) => {
      if (!mainWindow || !text) return;
      // Strip wake phrase if user says Hey Mentrix + command
      let goal = String(text);
      const lower = goal.toLowerCase();
      for (const p of ["hey mentrix", "mentrix engage", "wake mentrix", "hey matrix"]) {
        if (lower.startsWith(p)) {
          goal = goal.slice(p.length).trim();
          break;
        }
      }
      if (!goal) return;
      mainWindow.webContents.send("mentrix-stt-goal", { goal, ts: new Date().toISOString() });
    },
    (status) => {
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send("mentrix-wake-status", { ...wakeStatus, dictation: status });
      }
    },
  );
  return { ok: true, dictation: true };
});
ipcMain.handle("mentrix-computer-mode", (_e, enabled) => {
  computerMode = Boolean(enabled);
  if (computerMode) armComputerModeIdle();
  else clearComputerModeIdle();
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
  if (action === "open_app" || action === "open") {
    const appName =
      a.app || a.appName || (process.platform === "darwin" ? "TextEdit" : "notepad.exe");
    return computer.openApp(appName);
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
  if (action === "click" || action === "computer_click") {
    return computer.clickAt(a.x, a.y);
  }
  if (action === "type" || action === "computer_type") {
    return computer.typeText(a.text);
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
  if (dictationHandle) {
    dictationHandle.stop();
    dictationHandle = null;
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
