/**
 * Optional managed local service probes for Windows desktop.
 *
 * When ZECT_MANAGE_SERVICES=1, Electron can probe API/UI health and optionally
 * spawn start helpers. Backend is NOT bundled in the NSIS installer yet —
 * see docs/WINDOWS_INSTALL.md (packaging status: PARTIAL).
 *
 * Canonical packaged API port is :8000 (override with ZECT_API_URL / VITE_API_URL).
 * Dev scripts may use :8020 via env; do not hard-code conflicting defaults here.
 */

const { spawn } = require("child_process");
const http = require("http");
const path = require("path");
const fs = require("fs");

const API_URL = process.env.ZECT_API_URL || process.env.VITE_API_URL || "http://127.0.0.1:8000";
const UI_URL = process.env.ZECT_DEV_URL || process.env.ZECT_UI_URL || "http://127.0.0.1:5173";

/** Track children started by this process so will-quit can stop them. */
const managedChildren = [];

function probe(url, timeoutMs = 2500) {
  return new Promise((resolve) => {
    let settled = false;
    const done = (ok, detail) => {
      if (settled) return;
      settled = true;
      resolve({ ok, detail, url });
    };
    try {
      const req = http.get(url, { timeout: timeoutMs }, (res) => {
        res.resume();
        done(res.statusCode >= 200 && res.statusCode < 500, `status=${res.statusCode}`);
      });
      req.on("error", (e) => done(false, e.message));
      req.on("timeout", () => {
        req.destroy();
        done(false, "timeout");
      });
    } catch (e) {
      done(false, e instanceof Error ? e.message : String(e));
    }
  });
}

function detectBackendSidecar(resourcesPath) {
  if (!resourcesPath) return false;
  const candidates = [
    path.join(resourcesPath, "backend", "zect-api.exe"),
    path.join(resourcesPath, "backend", "run-api.ps1"),
    path.join(resourcesPath, "backend", "uvicorn.exe"),
  ];
  return candidates.some((p) => {
    try {
      return fs.existsSync(p);
    } catch {
      return false;
    }
  });
}

async function checkReadiness(opts = {}) {
  const api = await probe(`${API_URL.replace(/\/$/, "")}/docs`);
  const apiAlt = api.ok ? api : await probe(`${API_URL.replace(/\/$/, "")}/openapi.json`);
  const ui = await probe(UI_URL);
  const backendBundled = Boolean(opts.backendBundled) || detectBackendSidecar(opts.resourcesPath);
  return {
    api: apiAlt,
    ui,
    manage_services: process.env.ZECT_MANAGE_SERVICES === "1",
    packaging_status: backendBundled ? "PASS" : "PARTIAL",
    backend_bundled: backendBundled,
    api_url: API_URL,
    ui_url: UI_URL,
    single_instance: true,
  };
}

function tryStartLocalScript(repoRoot) {
  if (process.env.ZECT_MANAGE_SERVICES !== "1") {
    return { started: false, reason: "ZECT_MANAGE_SERVICES not enabled" };
  }
  const candidates = [
    path.join(repoRoot, "scripts", "start-local.ps1"),
    path.join(repoRoot, "start-local.ps1"),
  ];
  const script = candidates.find((p) => fs.existsSync(p));
  if (!script) {
    return { started: false, reason: "start-local.ps1 not found" };
  }
  try {
    const child = spawn(
      "powershell.exe",
      ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script, "-NoElectron"],
      { detached: false, stdio: "ignore", windowsHide: true },
    );
    managedChildren.push(child);
    child.on("error", (err) => {
      const i = managedChildren.indexOf(child);
      if (i >= 0) managedChildren.splice(i, 1);
      console.warn("[zect] managed service launch failed", err && err.message ? err.message : err);
    });
    child.on("exit", () => {
      const i = managedChildren.indexOf(child);
      if (i >= 0) managedChildren.splice(i, 1);
    });
    return { started: true, script, pid: child.pid };
  } catch (e) {
    return { started: false, reason: e instanceof Error ? e.message : String(e) };
  }
}

function stopManagedChildren() {
  const stopped = [];
  for (const child of [...managedChildren]) {
    try {
      if (child.pid && !child.killed) {
        if (process.platform === "win32") {
          spawn("taskkill", ["/pid", String(child.pid), "/T", "/F"], {
            stdio: "ignore",
            windowsHide: true,
          });
        } else {
          child.kill("SIGTERM");
        }
        stopped.push(child.pid);
      }
    } catch {
      /* ignore */
    }
  }
  managedChildren.length = 0;
  return { stopped };
}

module.exports = {
  checkReadiness,
  tryStartLocalScript,
  stopManagedChildren,
  detectBackendSidecar,
  API_URL,
  UI_URL,
};
