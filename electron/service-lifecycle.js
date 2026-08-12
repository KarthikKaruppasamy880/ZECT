/**
 * Optional managed local service probes for Windows desktop.
 *
 * When ZECT_MANAGE_SERVICES=1, Electron can probe API/UI health and optionally
 * spawn start helpers. Backend is NOT bundled in the NSIS installer yet —
 * see docs/WINDOWS_INSTALL.md (packaging status: PARTIAL).
 */

const { spawn } = require("child_process");
const http = require("http");
const path = require("path");
const fs = require("fs");

const API_URL = process.env.ZECT_API_URL || process.env.VITE_API_URL || "http://127.0.0.1:8000";
const UI_URL = process.env.ZECT_DEV_URL || process.env.ZECT_UI_URL || "http://127.0.0.1:5173";

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

async function checkReadiness() {
  const api = await probe(`${API_URL.replace(/\/$/, "")}/api/system/health`.replace("/api/system/health", "/docs"));
  // /docs is unauthenticated; health may require auth — probe root docs or openapi
  const apiAlt = api.ok ? api : await probe(`${API_URL.replace(/\/$/, "")}/openapi.json`);
  const ui = await probe(UI_URL);
  return {
    api: apiAlt,
    ui,
    manage_services: process.env.ZECT_MANAGE_SERVICES === "1",
    packaging_status: "PARTIAL",
    backend_bundled: false,
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
      ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script],
      { detached: true, stdio: "ignore", windowsHide: true },
    );
    child.unref();
    return { started: true, script, pid: child.pid };
  } catch (e) {
    return { started: false, reason: e instanceof Error ? e.message : String(e) };
  }
}

module.exports = {
  checkReadiness,
  tryStartLocalScript,
  API_URL,
  UI_URL,
};
