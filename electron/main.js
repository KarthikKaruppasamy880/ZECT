/**
 * ZECT Desktop App — Electron main process.
 *
 * Wraps the ZECT web application in a native desktop window.
 * Supports both local dev server and production build.
 */

const { app, BrowserWindow, Menu, shell } = require("electron");
const path = require("path");

const isDev = process.env.NODE_ENV === "development" || process.env.ZECT_DEV === "true";
const DEV_URL = process.env.ZECT_DEV_URL || "http://localhost:5173";

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    title: "ZECT — Engineering Control Tower",
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

  // Open external links in default browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith("http")) {
      shell.openExternal(url);
    }
    return { action: "deny" };
  });
}

// Application menu
const menuTemplate = [
  {
    label: "ZECT",
    submenu: [
      { label: "About ZECT", role: "about" },
      { type: "separator" },
      { label: "Settings", accelerator: "CmdOrCtrl+,", click: () => mainWindow?.webContents.executeJavaScript("window.location.hash = '/settings'") },
      { type: "separator" },
      { label: "Quit", accelerator: "CmdOrCtrl+Q", click: () => app.quit() },
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
      { label: "Dashboard", accelerator: "CmdOrCtrl+1", click: () => mainWindow?.webContents.executeJavaScript("window.location.hash = '/'") },
      { label: "Projects", accelerator: "CmdOrCtrl+2", click: () => mainWindow?.webContents.executeJavaScript("window.location.hash = '/projects'") },
      { label: "Ask Mode", accelerator: "CmdOrCtrl+3", click: () => mainWindow?.webContents.executeJavaScript("window.location.hash = '/ask'") },
      { label: "Build Phase", accelerator: "CmdOrCtrl+4", click: () => mainWindow?.webContents.executeJavaScript("window.location.hash = '/build'") },
      { label: "Agent Mode", accelerator: "CmdOrCtrl+5", click: () => mainWindow?.webContents.executeJavaScript("window.location.hash = '/agent-mode'") },
    ],
  },
  {
    label: "Help",
    submenu: [
      { label: "Documentation", click: () => shell.openExternal("https://github.com/KarthikKaruppasamy880/ZECT") },
    ],
  },
];

app.whenReady().then(() => {
  const menu = Menu.buildFromTemplate(menuTemplate);
  Menu.setApplicationMenu(menu);
  createWindow();
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
