/**
 * Optional managed local Chatterbox process for Electron.
 * Does NOT bundle a binary — starts a user-provided command if configured.
 */

const { spawn } = require("child_process");
const http = require("http");
const https = require("https");

let child = null;
let lastStatus = { running: false, pid: null, baseUrl: "", error: "" };

function baseUrl() {
  return (process.env.CHATTERBOX_BASE_URL || "http://localhost:17493").replace(/\/$/, "");
}

function healthCheck() {
  const url = `${baseUrl()}/profiles`;
  return new Promise((resolve) => {
    const lib = url.startsWith("https") ? https : http;
    const req = lib.get(url, { timeout: 2500 }, (res) => {
      resolve({ online: res.statusCode >= 200 && res.statusCode < 500, statusCode: res.statusCode });
    });
    req.on("error", () => resolve({ online: false }));
    req.on("timeout", () => {
      req.destroy();
      resolve({ online: false });
    });
  });
}

async function status() {
  const health = await healthCheck();
  return {
    ...lastStatus,
    running: Boolean(child && !child.killed),
    pid: child && !child.killed ? child.pid : null,
    baseUrl: baseUrl(),
    online: Boolean(health.online),
    managed: Boolean(process.env.CHATTERBOX_START_CMD || process.env.CHATTERBOX_MANAGED === "1"),
    hint: health.online
      ? "Chatterbox answering /profiles"
      : "Offline — start local engine or use Mentrix → Voice Start (managed)",
  };
}

function stop() {
  if (child && !child.killed) {
    try {
      child.kill();
    } catch {
      /* ignore */
    }
  }
  child = null;
  lastStatus = { running: false, pid: null, baseUrl: baseUrl(), error: "" };
  return { ok: true, ...lastStatus };
}

function start() {
  const cmd = (process.env.CHATTERBOX_START_CMD || "").trim();
  if (!cmd) {
    lastStatus = {
      running: false,
      pid: null,
      baseUrl: baseUrl(),
      error: "CHATTERBOX_START_CMD not set — configure managed launch or start Chatterbox yourself",
    };
    return { ok: false, ...lastStatus };
  }
  if (child && !child.killed) {
    return { ok: true, already: true, pid: child.pid, baseUrl: baseUrl() };
  }
  try {
    const shell = process.platform === "win32";
    child = spawn(cmd, {
      shell: true,
      detached: !shell,
      stdio: "ignore",
      env: { ...process.env },
    });
    child.unref?.();
    child.on("exit", () => {
      child = null;
      lastStatus.running = false;
      lastStatus.pid = null;
    });
    lastStatus = { running: true, pid: child.pid, baseUrl: baseUrl(), error: "" };
    return { ok: true, ...lastStatus };
  } catch (err) {
    lastStatus = {
      running: false,
      pid: null,
      baseUrl: baseUrl(),
      error: String(err && err.message ? err.message : err),
    };
    return { ok: false, ...lastStatus };
  }
}

module.exports = { start, stop, status, baseUrl };
