/**
 * Node assertions for sidecar lifecycle (no Electron).
 */
const path = require("path");
const sl = require("./service-lifecycle");

const resources = path.join(__dirname, "resources");
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
  userData: "C:\\tmp\\zect-ud-test",
  packaged: true,
});
if (missingUd.started && !sl.detectBackendRuntime(resources)) {
  console.error("must not start without runtime unless ZECT_ALLOW_SYSTEM_PYTHON");
  process.exit(1);
}
if (!missingUd.started && missingUd.reason !== "backend_runtime_missing" && missingUd.reason !== "userData_required") {
  // runtime missing is the expected packaged fail on a clean checkout
  if (missingUd.reason !== "backend_runtime_missing") {
    console.error("unexpected", missingUd);
    process.exit(1);
  }
}
console.log("service-lifecycle node ok", sl.serviceClassification());
