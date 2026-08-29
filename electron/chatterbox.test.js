/**
 * Unit tests for Chatterbox sidecar resolve (no Electron required).
 * Run: node --test electron/chatterbox.test.js
 */

const { describe, it } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs");
const os = require("os");
const path = require("path");

const chatterbox = require("./chatterbox");

describe("chatterbox resolveLaunch", () => {
  it("finds a dropped binary under CHATTERBOX_BUNDLE_DIR", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "zect-cb-"));
    const bin = path.join(root, "bin");
    fs.mkdirSync(bin, { recursive: true });
    const fake = path.join(bin, process.platform === "win32" ? "chatterbox-server.exe" : "chatterbox-server");
    fs.writeFileSync(fake, "fake");
    fs.writeFileSync(
      path.join(root, "manifest.json"),
      JSON.stringify({
        binaries: {
          win32: ["chatterbox-server.exe"],
          darwin: ["chatterbox-server"],
          linux: ["chatterbox-server"],
        },
      }),
    );
    const prev = process.env.CHATTERBOX_BUNDLE_DIR;
    const prevBin = process.env.CHATTERBOX_BIN;
    const prevCmd = process.env.CHATTERBOX_START_CMD;
    try {
      delete process.env.CHATTERBOX_BIN;
      delete process.env.CHATTERBOX_START_CMD;
      process.env.CHATTERBOX_BUNDLE_DIR = root;
      const launch = chatterbox.resolveLaunch();
      assert.ok(launch);
      assert.equal(launch.mode, "bin");
      assert.equal(launch.bundled, true);
      assert.equal(launch.path, fake);
    } finally {
      if (prev === undefined) delete process.env.CHATTERBOX_BUNDLE_DIR;
      else process.env.CHATTERBOX_BUNDLE_DIR = prev;
      if (prevBin === undefined) delete process.env.CHATTERBOX_BIN;
      else process.env.CHATTERBOX_BIN = prevBin;
      if (prevCmd === undefined) delete process.env.CHATTERBOX_START_CMD;
      else process.env.CHATTERBOX_START_CMD = prevCmd;
      fs.rmSync(root, { recursive: true, force: true });
    }
  });

  it("prefers CHATTERBOX_BIN over bundled", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "zect-cb-"));
    const explicit = path.join(root, "explicit-engine.exe");
    fs.writeFileSync(explicit, "x");
    const prev = process.env.CHATTERBOX_BIN;
    try {
      process.env.CHATTERBOX_BIN = explicit;
      const launch = chatterbox.resolveLaunch();
      assert.equal(launch.mode, "bin");
      assert.equal(launch.bundled, false);
      assert.equal(launch.path, explicit);
    } finally {
      if (prev === undefined) delete process.env.CHATTERBOX_BIN;
      else process.env.CHATTERBOX_BIN = prev;
      fs.rmSync(root, { recursive: true, force: true });
    }
  });

  it("defaults to ZECT Voicebox uvicorn when no binary", () => {
    const prevBin = process.env.CHATTERBOX_BIN;
    const prevCmd = process.env.CHATTERBOX_START_CMD;
    const prevBundle = process.env.CHATTERBOX_BUNDLE_DIR;
    try {
      delete process.env.CHATTERBOX_BIN;
      delete process.env.CHATTERBOX_START_CMD;
      delete process.env.CHATTERBOX_BUNDLE_DIR;
      const launch = chatterbox.resolveLaunch();
      assert.ok(launch);
      assert.equal(launch.mode, "cmd");
      assert.equal(launch.zectVoicebox, true);
      assert.match(launch.path, /uvicorn/);
      assert.ok(launch.cwd && launch.cwd.includes("zect-voicebox"));
    } finally {
      if (prevBin === undefined) delete process.env.CHATTERBOX_BIN;
      else process.env.CHATTERBOX_BIN = prevBin;
      if (prevCmd === undefined) delete process.env.CHATTERBOX_START_CMD;
      else process.env.CHATTERBOX_START_CMD = prevCmd;
      if (prevBundle === undefined) delete process.env.CHATTERBOX_BUNDLE_DIR;
      else process.env.CHATTERBOX_BUNDLE_DIR = prevBundle;
    }
  });

  it("normalizes localhost to 127.0.0.1 in baseUrl", () => {
    const prev = process.env.CHATTERBOX_BASE_URL;
    try {
      process.env.CHATTERBOX_BASE_URL = "http://localhost:17493";
      assert.equal(chatterbox.baseUrl(), "http://127.0.0.1:17493");
    } finally {
      if (prev === undefined) delete process.env.CHATTERBOX_BASE_URL;
      else process.env.CHATTERBOX_BASE_URL = prev;
    }
  });
});
