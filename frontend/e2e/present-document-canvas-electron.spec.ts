/**
 * Electron viewport proof for the PresentationDocument editor.
 * Skip if electron.exe is missing — skip ≠ READY.
 */
import { test, expect, _electron as electron } from "@playwright/test";
import fs from "fs";
import os from "os";
import path from "path";
import { fileURLToPath } from "url";
import { loadEnvCreds } from "./helpers/env";
import { runPythonScript } from "./helpers/python";

const FRONTEND = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const REPO = path.resolve(FRONTEND, "..");
const ART = path.join(REPO, "test-results/present-document-canvas-electron");
const ELECTRON_MAIN = path.join(REPO, "electron", "main.js");
const ELECTRON_EXE = path.join(REPO, "electron", "node_modules", "electron", "dist", "electron.exe");
const API = process.env.VITE_API_URL || process.env.ZECT_API_URL || "http://127.0.0.1:8000";
const BASE = process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:5173";

function encodeDeckId(p: string) {
  return Buffer.from(p, "utf8").toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

test.describe("present document canvas electron", () => {
  test.setTimeout(180_000);

  test("1280x720 document canvas in Electron", async () => {
    test.skip(!fs.existsSync(ELECTRON_EXE), "Electron binary is not installed in electron/node_modules");
    fs.mkdirSync(ART, { recursive: true });
    const dest = path.join(os.homedir(), "Documents", "zect-document-canvas-electron.pptx");
    runPythonScript(path.join(FRONTEND, "e2e/fixtures/make_tiny_pptx.py"), [dest]);
    const userData = fs.mkdtempSync(path.join(os.tmpdir(), "zect-electron-dc-"));
    const { username, password } = loadEnvCreds();
    const app = await electron.launch({
      executablePath: ELECTRON_EXE,
      args: [`--user-data-dir=${userData}`, ELECTRON_MAIN],
      cwd: path.join(REPO, "electron"),
      env: {
        ...process.env,
        ZECT_DEV: "true",
        ZECT_DEV_URL: BASE,
        ZECT_API_URL: API,
        ZECT_MANAGE_SERVICES: "0",
        ZECT_DEVTOOLS: "0",
        ELECTRON_USER_DATA: userData,
        ZECT_ALLOW_MULTI_INSTANCE: "1",
      },
    });
    const page = await app.firstWindow({ timeout: 60_000 });
    try {
      await page.waitForLoadState("domcontentloaded").catch(() => {});
      await page.setViewportSize({ width: 1280, height: 720 }).catch(() => {});
      if (await page.getByTestId("login-username").isVisible({ timeout: 20_000 }).catch(() => false)) {
        await page.getByTestId("login-username").fill(username);
        await page.getByTestId("login-password").fill(password);
        await page.getByTestId("login-submit").click();
        await expect(page.getByTestId("login-submit")).toBeHidden({ timeout: 30_000 });
      }
      await expect(page.getByRole("link", { name: "Present" }).first()).toBeVisible({ timeout: 45_000 });
      const editorUrl = `${BASE}/present/d/${encodeDeckId(dest)}/edit`;
      await app.evaluate(async ({ BrowserWindow }, url) => {
        const win = BrowserWindow.getAllWindows()[0];
        if (win) await win.loadURL(url);
      }, editorUrl);
      await expect(page.getByTestId("present-studio")).toBeVisible({ timeout: 30_000 });
      await expect(page.getByTestId("present-editor-canvas")).toHaveAttribute("data-canvas", "document", { timeout: 20_000 });
      await page.screenshot({ path: path.join(ART, "01-electron-1280x720.png") });
    } finally {
      await app.close();
    }
  });
});
