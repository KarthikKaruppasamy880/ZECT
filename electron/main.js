/**
 * ZECT Desktop App — Electron main process.
 *
 * Wraps the ZECT web application in a native desktop window.
 * Mentrix wake: global shortcut + renderer STT transcripts for "Hey Mentrix".
 */

const { app, BrowserWindow, Menu, shell, ipcMain, globalShortcut } = require("electron");
const path = require("path");
const { matchesWakePhrase } = require("./wake");

const isDev = process.env.NODE_ENV === "development" || process.env.ZECT_DEV === "true";
const DEV_URL = process.env.ZECT_DEV_URL || "http://localhost:5173";
const WAKE_PHRASE = process.env.WAKE_PHRASE || "Hey Mentrix";

let mainWindow;
let wakeEnabled = true;

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

function emitWake(phrase, source) {
  if (!wakeEnabled || !mainWindow) return;
  mainWindow.webContents.send("mentrix-wake", {
    phrase,
    source,
    ts: new Date().toISOString(),
  });
  mainWindow.webContents.executeJavaScript(
    "window.location.hash = '/mentrix'; window.dispatchEvent(new CustomEvent('mentrix-wake', { detail: { phrase: '" +
      phrase.replace(/'/g, "") +
      "' } }));"
  ).catch(() => {});
}

ipcMain.handle("get-app-path", () => app.getAppPath());
ipcMain.handle("mentrix-engage", (_e, goal) => {
  emitWake("Mentrix engage", "ipc");
  return { ok: true, goal: goal || "", agent: "Mentrix" };
});
ipcMain.handle("mentrix-wake-enabled", (_e, enabled) => {
  wakeEnabled = Boolean(enabled);
  return { wakeEnabled };
});
ipcMain.handle("mentrix-stt-transcript", (_e, transcript) => {
  if (matchesWakePhrase(transcript, WAKE_PHRASE)) {
    emitWake(WAKE_PHRASE, "stt");
    return { matched: true, phrase: WAKE_PHRASE };
  }
  return { matched: false };
});
/** Follow-up spoken goal after wake — forward to renderer Mentrix page. */
ipcMain.handle("mentrix-stt-goal", (_e, goal) => {
  if (!mainWindow || !goal) return { ok: false };
  mainWindow.webContents.send("mentrix-stt-goal", { goal: String(goal), ts: new Date().toISOString() });
  return { ok: true };
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
          mainWindow?.webContents.executeJavaScript("window.location.hash = '/settings'"),
      },
      { type: "separator" },
      { label: "Quit", accelerator: "CmdOrCtrl+Q", click: () => app.quit() },
    ],
  },
  {
    label: "Mentrix",
    submenu: [
      {
        label: "Open Mentrix",
        accelerator: "CmdOrCtrl+Shift+M",
        click: () => emitWake("Mentrix engage", "menu"),
      },
      {
        label: "Toggle wake listening",
        click: () => {
          wakeEnabled = !wakeEnabled;
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
          mainWindow?.webContents.executeJavaScript("window.location.hash = '/'"),
      },
      {
        label: "Lattice",
        accelerator: "CmdOrCtrl+2",
        click: () =>
          mainWindow?.webContents.executeJavaScript("window.location.hash = '/lattice'"),
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
          mainWindow?.webContents.executeJavaScript("window.location.hash = '/build'"),
      },
      {
        label: "Sandbox Gate",
        accelerator: "CmdOrCtrl+5",
        click: () =>
          mainWindow?.webContents.executeJavaScript("window.location.hash = '/sandbox'"),
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
  const menu = Menu.buildFromTemplate(menuTemplate);
  Menu.setApplicationMenu(menu);
  createWindow();

  // Hotkey fallback for Hey Mentrix when STT unavailable
  globalShortcut.register("CommandOrControl+Shift+Space", () => {
    emitWake(WAKE_PHRASE, "hotkey");
  });
});

app.on("will-quit", () => {
  globalShortcut.unregisterAll();
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
