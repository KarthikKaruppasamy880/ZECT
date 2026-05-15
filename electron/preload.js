/**
 * ZECT Desktop App — Electron preload script.
 *
 * Exposes safe APIs to the renderer process via contextBridge.
 */

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("zectDesktop", {
  isDesktopApp: true,
  platform: process.platform,
  version: process.env.npm_package_version || "2.0.0",
  getAppPath: () => ipcRenderer.invoke("get-app-path"),
});
