/**
 * Managed local service lifecycle for Windows desktop packaging.
 *
 * Packaged builds auto-start the bundled backend sidecar (run-api.ps1 /
 * zect-api.exe / python-runtime). Voicebox + Presenton stay optional external.
 * See docs/WINDOWS_INSTALL.md.
 */

const { spawn } = require("child_process");
const http = require("http");
const path = require("path");
const fs = require("fs");

const API_URL = process.env.ZECT_API_URL || process.env.VITE_API_URL || "http://127.0.0.1:8000";
const UI_URL = process.env.ZECT_DEV_URL || process.env.ZECT_UI_URL || "http://127.0.0.1:5173";

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

function backendDir(resourcesPath) {
  if (resourcesPath) return path.join(resourcesPath, "backend");
  return path.join(__dirname, "resources", "backend");
}

function detectBackendLauncher(resourcesPath) {
  try {
    return fs.existsSync(path.join(backendDir(resourcesPath), "run-api.ps1"));
  } catch {
    return false;
  }
}

function detectBackendRuntime(resourcesPath) {
  const dir = backendDir(resourcesPath);
  const candidates = [
    path.join(dir, "zect-api.exe"),
    path.join(dir, "python-runtime", "python.exe"),
    path.join(dir, "python-runtime", "Scripts", "python.exe"),
    path.join(dir, "python-runtime", "bin", "python"),
  ];
  return candidates.some((p) => {
    try {
      return fs.existsSync(p);
    } catch {
      return false;
    }
  });
}

function detectBackendSidecar(resourcesPath) {
  return detectBackendRuntime(resourcesPath) || detectBackendLauncher(resourcesPath);
}

function serviceClassification() {
  return {
    electron: "PACKAGED",
    frontend: "PACKAGED",
    backend: "PACKAGED",
    storage_database: "PACKAGED",
    voicebox: "OPTIONAL",
    presentation_provider: "OPTIONAL",
    local_model_runtime: "NOT_REQUIRED",
    helpers: "MANAGED_EXTERNAL",
  };
}

async function checkReadiness(opts = {}) {
  const resourcesPath = opts.resourcesPath || null;
  const api = await probe(`${API_URL.replace(/\/$/, "")}/docs`);
  const apiAlt = api.ok ? api : await probe(`${API_URL.replace(/\/$/, "")}/openapi.json`);
  const ui = await probe(UI_URL);
  const launcher = detectBackendLauncher(resourcesPath);
  const runtime = detectBackendRuntime(resourcesPath);
  const backendBundled = runtime;
  return {
    api: apiAlt,
    ui,
    manage_services: process.env.ZECT_MANAGE_SERVICES === "1" || Boolean(opts.packaged),
    packaging_status: backendBundled ? "PARTIAL" : launcher ? "PARTIAL" : "PARTIAL",
    backend_bundled: backendBundled,
    backend_launcher_present: launcher,
    backend_runtime_present: runtime,
    api_url: API_URL,
    ui_url: UI_URL,
    single_instance: true,
    classification: serviceClassification(),
  };
}

async function waitForApi(timeoutMs = 45000) {
  const deadline = Date.now() + timeoutMs;
  let last = { ok: false, detail: "not_probed" };
  while (Date.now() < deadline) {
    last = await probe(`${API_URL.replace(/\/$/, "")}/docs`, 2000);
    if (!last.ok) last = await probe(`${API_URL.replace(/\/$/, "")}/openapi.json`, 2000);
    if (last.ok) return last;
    await new Promise((r) => setTimeout(r, 750));
  }
  return last;
}

function startBackendSidecar({ resourcesPath, userData, packaged } = {}) {
  const dir = backendDir(resourcesPath);
  const script = path.join(dir, "run-api.ps1");
  if (!fs.existsSync(script)) {
    return { started: false, reason: "run-api.ps1_missing" };
  }
  const runtime = detectBackendRuntime(resourcesPath);
  if (!runtime && process.env.ZECT_ALLOW_SYSTEM_PYTHON !== "1") {
    return { started: false, reason: "backend_runtime_missing", blocked_external: !packaged };
  }
  if (!userData) {
    return { started: false, reason: "userData_required" };
  }
  try {
    const args = [
      "-NoProfile",
      "-ExecutionPolicy",
      "Bypass",
      "-File",
      script,
      "-UserData",
      userData,
      "-ResourcesDir",
      dir,
    ];
    const childEnv = {
      ...process.env,
      ZECT_PACKAGED: packaged ? "1" : process.env.ZECT_PACKAGED || "",
      ZECT_USER_DATA: userData,
      ZECT_API_URL: API_URL,
    };
    for (const k of ["ZECT_PASSWORD", "ENCRYPTION_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GITHUB_TOKEN"]) {
      delete childEnv[k];
    }
    const child = spawn("powershell.exe", args, {
      detached: false,
      stdio: "ignore",
      windowsHide: true,
      env: childEnv,
    });
    managedChildren.push(child);
    child.on("error", (err) => {
      const i = managedChildren.indexOf(child);
      if (i >= 0) managedChildren.splice(i, 1);
      console.warn("[zect] backend sidecar launch failed", err && err.message ? err.message : err);
    });
    child.on("exit", () => {
      const i = managedChildren.indexOf(child);
      if (i >= 0) managedChildren.splice(i, 1);
    });
    return { started: true, script, pid: child.pid, runtime };
  } catch (e) {
    return { started: false, reason: e instanceof Error ? e.message : String(e) };
  }
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
  startBackendSidecar,
  waitForApi,
  stopManagedChildren,
  detectBackendSidecar,
  detectBackendRuntime,
  detectBackendLauncher,
  serviceClassification,
  API_URL,
  UI_URL,
};
