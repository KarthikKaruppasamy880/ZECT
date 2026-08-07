/**
 * Chatterbox sidecar for Electron — managed process + optional bundled binary.
 *
 * Resolve order for start():
 *   1. CHATTERBOX_BIN (explicit path)
 *   2. Bundled resources/chatterbox/bin/* (packaged or electron/resources in dev)
 *   3. CHATTERBOX_START_CMD (shell command)
 *
 * ZECT does not commit ML weights; drop a Voicebox/Chatterbox-compatible
 * binary into resources/chatterbox/bin before packaging.
 */

const { spawn } = require("child_process");
const fs = require("fs");
const http = require("http");
const https = require("https");
const path = require("path");

let child = null;
let lastStatus = {
  running: false,
  pid: null,
  baseUrl: "",
  error: "",
  bundled: false,
  binaryPath: "",
};

function baseUrl() {
  let u = (process.env.CHATTERBOX_BASE_URL || "http://127.0.0.1:17493").replace(/\/$/, "");
  // Windows: localhost → ::1 often misses engines bound to 127.0.0.1 only.
  u = u.replace(/:\/\/localhost(?=:|\/|$)/i, "://127.0.0.1");
  return u;
}

function zectVoiceboxDir() {
  // electron/ → repo root → services/zect-voicebox
  return path.join(__dirname, "..", "services", "zect-voicebox");
}

function defaultZectVoiceboxCmd() {
  const dir = zectVoiceboxDir();
  if (!fs.existsSync(path.join(dir, "app", "main.py"))) return null;
  return {
    mode: "cmd",
    path: "python -m uvicorn app.main:app --host 127.0.0.1 --port 17493",
    cwd: dir,
    bundled: false,
    zectVoicebox: true,
  };
}

function resolveLaunch() {
  const explicit = (process.env.CHATTERBOX_BIN || "").trim();
  if (explicit && fs.existsSync(explicit)) {
    return { mode: "bin", path: explicit, bundled: false };
  }
  const bundled = findBundledBinary();
  if (bundled) {
    return { mode: "bin", path: bundled.path, bundled: true };
  }
  const cmd = (process.env.CHATTERBOX_START_CMD || "").trim();
  if (cmd) {
    return { mode: "cmd", path: cmd, cwd: process.env.CHATTERBOX_START_CWD || "", bundled: false };
  }
  return defaultZectVoiceboxCmd();
}

function chatterboxRootCandidates() {
  const roots = [];
  // Packaged: extraResources → process.resourcesPath/chatterbox
  if (process.resourcesPath) {
    roots.push(path.join(process.resourcesPath, "chatterbox"));
  }
  // Dev: electron/resources/chatterbox next to this file
  roots.push(path.join(__dirname, "resources", "chatterbox"));
  // Optional override
  if (process.env.CHATTERBOX_BUNDLE_DIR) {
    roots.unshift(path.resolve(process.env.CHATTERBOX_BUNDLE_DIR));
  }
  return roots;
}

function loadManifest(root) {
  try {
    const p = path.join(root, "manifest.json");
    if (!fs.existsSync(p)) return null;
    return JSON.parse(fs.readFileSync(p, "utf8"));
  } catch {
    return null;
  }
}

function platformBinNames(manifest) {
  const plat = process.platform;
  const fromManifest = manifest && manifest.binaries && manifest.binaries[plat];
  if (Array.isArray(fromManifest) && fromManifest.length) return fromManifest;
  if (plat === "win32") return ["chatterbox-server.exe", "Voicebox.exe", "chatterbox.exe"];
  if (plat === "darwin") return ["chatterbox-server", "Voicebox", "Chatterbox"];
  return ["chatterbox-server", "chatterbox"];
}

function findBundledBinary() {
  for (const root of chatterboxRootCandidates()) {
    const binDir = path.join(root, "bin");
    if (!fs.existsSync(binDir)) continue;
    const manifest = loadManifest(root);
    for (const name of platformBinNames(manifest)) {
      const full = path.join(binDir, name);
      if (fs.existsSync(full)) {
        return { path: full, root, bundled: true };
      }
    }
    // Any executable-looking file in bin/
    try {
      const entries = fs.readdirSync(binDir);
      for (const name of entries) {
        if (name === ".gitkeep" || name.startsWith(".")) continue;
        const full = path.join(binDir, name);
        const st = fs.statSync(full);
        if (st.isFile()) {
          return { path: full, root, bundled: true };
        }
      }
    } catch {
      /* ignore */
    }
  }
  return null;
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
  const launch = resolveLaunch();
  const bundled = Boolean(launch && launch.bundled);
  const binaryPath = launch && launch.mode === "bin" ? launch.path : "";
  return {
    ...lastStatus,
    running: Boolean(child && !child.killed),
    pid: child && !child.killed ? child.pid : null,
    baseUrl: baseUrl(),
    online: Boolean(health.online),
    managed: Boolean(launch || process.env.CHATTERBOX_MANAGED === "1"),
    bundled,
    binaryPath,
    autoStart:
      process.env.CHATTERBOX_AUTO_START === "1" ||
      process.env.CHATTERBOX_AUTO_START === "true" ||
      bundled,
    hint: health.online
      ? bundled
        ? "Bundled Chatterbox answering /profiles"
        : launch && launch.zectVoicebox
          ? "ZECT Voicebox answering /profiles"
          : "Chatterbox answering /profiles"
      : bundled
        ? "Bundled binary found — click Start (or enable CHATTERBOX_AUTO_START)"
        : launch && launch.zectVoicebox
          ? "Offline — click Start to launch ZECT Voicebox (uvicorn on 127.0.0.1:17493)"
          : "Offline — drop binary in resources/chatterbox/bin, set CHATTERBOX_BIN, or CHATTERBOX_START_CMD",
  };
}

function stop() {
  if (child && !child.killed) {
    try {
      if (process.platform === "win32") {
        spawn("taskkill", ["/pid", String(child.pid), "/T", "/F"], {
          stdio: "ignore",
          windowsHide: true,
        });
      } else {
        child.kill("SIGTERM");
      }
    } catch {
      /* ignore */
    }
  }
  child = null;
  lastStatus = {
    running: false,
    pid: null,
    baseUrl: baseUrl(),
    error: "",
    bundled: lastStatus.bundled,
    binaryPath: lastStatus.binaryPath,
  };
  return { ok: true, ...lastStatus };
}

function start() {
  const launch = resolveLaunch();
  if (!launch) {
    lastStatus = {
      running: false,
      pid: null,
      baseUrl: baseUrl(),
      error:
        "No Chatterbox launch path — place engine in resources/chatterbox/bin, set CHATTERBOX_BIN / CHATTERBOX_START_CMD, or keep services/zect-voicebox in the repo",
      bundled: false,
      binaryPath: "",
    };
    return { ok: false, ...lastStatus };
  }
  if (child && !child.killed) {
    return {
      ok: true,
      already: true,
      pid: child.pid,
      baseUrl: baseUrl(),
      bundled: launch.bundled,
      binaryPath: launch.mode === "bin" ? launch.path : "",
      zectVoicebox: Boolean(launch.zectVoicebox),
    };
  }
  try {
    const childEnv = {
      ...process.env,
      CHATTERBOX_BASE_URL: baseUrl(),
      PORT: "17493",
      ZECT_VOICEBOX_BACKEND: process.env.ZECT_VOICEBOX_BACKEND || "native",
      ZECT_VOICEBOX_SYNTH: process.env.ZECT_VOICEBOX_SYNTH || "auto",
      ZECT_VOICEBOX_ALLOW_STUB: process.env.ZECT_VOICEBOX_ALLOW_STUB || "1",
    };
    if (launch.mode === "bin") {
      child = spawn(launch.path, [], {
        cwd: path.dirname(launch.path),
        detached: process.platform !== "win32",
        stdio: "ignore",
        windowsHide: true,
        env: childEnv,
      });
    } else {
      child = spawn(launch.path, {
        shell: true,
        cwd: launch.cwd || undefined,
        detached: process.platform !== "win32",
        stdio: "ignore",
        windowsHide: true,
        env: childEnv,
      });
    }
    child.unref?.();
    child.on("exit", () => {
      child = null;
      lastStatus.running = false;
      lastStatus.pid = null;
    });
    lastStatus = {
      running: true,
      pid: child.pid,
      baseUrl: baseUrl(),
      error: "",
      bundled: Boolean(launch.bundled),
      binaryPath: launch.mode === "bin" ? launch.path : "",
      zectVoicebox: Boolean(launch.zectVoicebox),
    };
    return { ok: true, ...lastStatus };
  } catch (err) {
    lastStatus = {
      running: false,
      pid: null,
      baseUrl: baseUrl(),
      error: String(err && err.message ? err.message : err),
      bundled: Boolean(launch.bundled),
      binaryPath: launch.mode === "bin" ? launch.path : "",
    };
    return { ok: false, ...lastStatus };
  }
}

/** Start if bundled binary exists or CHATTERBOX_AUTO_START is set. */
async function maybeAutoStart() {
  const st = await status();
  if (st.online) return { ok: true, skipped: "already_online", ...st };
  if (!st.autoStart) return { ok: false, skipped: "auto_start_disabled", ...st };
  const out = start();
  return { ...out, auto: true };
}

module.exports = {
  start,
  stop,
  status,
  baseUrl,
  resolveLaunch,
  findBundledBinary,
  maybeAutoStart,
};
