/**
 * ZECT Desktop App — Electron preload script.
 *
 * Exposes safe APIs to the renderer process via contextBridge.
 */

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("zectDesktop", {
  isDesktopApp: true,
  platform: process.platform,
  version: process.env.npm_package_version || "3.0.0",
  getAppPath: () => ipcRenderer.invoke("get-app-path"),
  mentrix: {
    engage: (goal) => ipcRenderer.invoke("mentrix-engage", goal),
    onWake: (cb) => {
      const handler = (_event, payload) => cb(payload);
      ipcRenderer.on("mentrix-wake", handler);
      return () => ipcRenderer.removeListener("mentrix-wake", handler);
    },
    setWakeEnabled: (enabled) => ipcRenderer.invoke("mentrix-wake-enabled", enabled),
  },
});
