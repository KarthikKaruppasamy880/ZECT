/**
 * Node assertions for sidecar lifecycle (no Electron).
 */
const fs = require("fs");
const os = require("os");
const path = require("path");
const sl = require("./service-lifecycle");

const resources = path.join(__dirname, "resources");
const tmpUd = fs.mkdtempSync(path.join(os.tmpdir(), "zect-lifecycle-"));

function cleanup() {
  try {
    sl.stopManagedChildren();
  } catch {
    /* ignore */
  }
  try {
    fs.rmSync(tmpUd, { recursive: true, force: true });
  } catch {
    /* ignore */
  }
}

try {
  if (!sl.detectBackendLauncher(resources)) {
    console.error("launcher missing");
    process.exit(1);
  }
  const started = sl.startBackendSidecar({
    resourcesPath: resources,
    userData: "",
    packaged: true,
  });
  if (started.started) {
    console.error("expected fail without userData");
    process.exit(1);
  }
  const missingUd = sl.startBackendSidecar({
    resourcesPath: resources,
    userData: tmpUd,
    packaged: true,
  });
  if (missingUd.started && !sl.detectBackendRuntime(resources) && process.env.ZECT_ALLOW_SYSTEM_PYTHON !== "1") {
    console.error("must not start without runtime unless ZECT_ALLOW_SYSTEM_PYTHON");
    process.exit(1);
  }
  if (!missingUd.started && missingUd.reason !== "backend_runtime_missing") {
    console.error("unexpected", missingUd);
    process.exit(1);
  }
  console.log("service-lifecycle node ok", sl.serviceClassification());
} finally {
  cleanup();
}
