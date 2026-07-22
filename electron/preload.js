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
  launcher: {
    getShortcutStatus: () => ipcRenderer.invoke("zect-shortcut-status"),
    createShortcut: () => ipcRenderer.invoke("zect-shortcut-create"),
    relaunch: () => ipcRenderer.invoke("zect-relaunch"),
    pullUpdatesAndRelaunch: () => ipcRenderer.invoke("zect-pull-relaunch"),
    onShortcutResult: (cb) => {
      const handler = (_event, payload) => cb(payload);
      ipcRenderer.on("zect-shortcut-result", handler);
      return () => ipcRenderer.removeListener("zect-shortcut-result", handler);
    },
  },
  mentrix: {
    engage: (goal) => ipcRenderer.invoke("mentrix-engage", goal),
    onWake: (cb) => {
      const handler = (_event, payload) => cb(payload);
      ipcRenderer.on("mentrix-wake", handler);
      return () => ipcRenderer.removeListener("mentrix-wake", handler);
    },
    onWakeStatus: (cb) => {
      const handler = (_event, payload) => cb(payload);
      ipcRenderer.on("mentrix-wake-status", handler);
      return () => ipcRenderer.removeListener("mentrix-wake-status", handler);
    },
    onSttGoal: (cb) => {
      const handler = (_event, payload) => cb(payload);
      ipcRenderer.on("mentrix-stt-goal", handler);
      return () => ipcRenderer.removeListener("mentrix-stt-goal", handler);
    },
    getWakeStatus: () => ipcRenderer.invoke("mentrix-wake-status"),
    setWakeEnabled: (enabled) => ipcRenderer.invoke("mentrix-wake-enabled", enabled),
    submitTranscript: (transcript) => ipcRenderer.invoke("mentrix-stt-transcript", transcript),
    submitGoal: (goal) => ipcRenderer.invoke("mentrix-stt-goal", goal),
    setComputerMode: (enabled) => ipcRenderer.invoke("mentrix-computer-mode", enabled),
    setDictationEnabled: (enabled) => ipcRenderer.invoke("mentrix-dictation-enabled", enabled),
    armDictation: (durationMs) => ipcRenderer.invoke("mentrix-dictation-arm", durationMs),
    disarmDictation: () => ipcRenderer.invoke("mentrix-dictation-disarm"),
    setDictationPaused: (paused) => ipcRenderer.invoke("mentrix-dictation-pause", paused),
    onComputerMode: (cb) => {
      const handler = (_event, payload) => cb(payload);
      ipcRenderer.on("mentrix-computer-mode", handler);
      return () => ipcRenderer.removeListener("mentrix-computer-mode", handler);
    },
    getPolicy: () => ipcRenderer.invoke("mentrix-get-policy"),
    confirmAction: (payload) => ipcRenderer.invoke("mentrix-confirm-action", payload),
    computer: (action, args) => ipcRenderer.invoke("mentrix-computer", action, args || {}),
  },
});
