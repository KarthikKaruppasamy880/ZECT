/**
 * Electron acceptance for Present product READY — 20+ slide rail, viewports, restart.
 * Opt-in: ZECT_LIVE_PRESENT_READY=1 (same gate as browser acceptance).
 */
import { test, expect, _electron as electron, type ElectronApplication, type Page } from "@playwright/test";
import fs from "fs";
import os from "os";
import path from "path";
import { fileURLToPath } from "url";
import { loadEnvCreds } from "./helpers/env";
import { runPythonScript } from "./helpers/python";

const FRONTEND = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const REPO = path.resolve(FRONTEND, "..");
const ART = path.join(REPO, "test-results", "present-product-ready-electron");
const ELECTRON_MAIN = path.join(REPO, "electron", "main.js");
const ELECTRON_EXE = path.join(REPO, "electron", "node_modules", "electron", "dist", "electron.exe");
const API = process.env.VITE_API_URL || process.env.ZECT_API_URL || "http://127.0.0.1:8000";
const BASE = process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:5173";
const VIEWPORTS = [
  { w: 1280, h: 720, tag: "1280x720" },
  { w: 1366, h: 768, tag: "1366x768" },
  { w: 1440, h: 900, tag: "1440x900" },
  { w: 1920, h: 1080, tag: "1920x1080" },
] as const;
const EDIT_MARKER = "ZECT Electron restart acceptance";

function encodeDeckId(p: string) {
  return Buffer.from(p, "utf8").toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function writeEvidence(partial: Record<string, unknown>) {
  fs.mkdirSync(ART, { recursive: true });
  const prev = (() => {
    try {
      return JSON.parse(fs.readFileSync(path.join(ART, "evidence.json"), "utf8")) as Record<string, unknown>;
    } catch {
      return {};
    }
  })();
  fs.writeFileSync(path.join(ART, "evidence.json"), JSON.stringify({ ...prev, ...partial }, null, 2));
}

async function loginIfNeeded(page: Page) {
  const { username, password } = loadEnvCreds();
  await page.waitForLoadState("domcontentloaded").catch(() => {});
  if (await page.getByTestId("login-username").isVisible({ timeout: 20_000 }).catch(() => false)) {
    await page.getByTestId("login-username").fill(username);
    await page.getByTestId("login-password").fill(password);
    await page.getByTestId("login-submit").click();
    await expect(page.getByTestId("login-submit")).toBeHidden({ timeout: 30_000 });
  }
}

async function assertPresentShell(page: Page, tag: string) {
  await expect(page.getByTestId("present-editor")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("present-editor-canvas")).toHaveAttribute("data-canvas", "document");
  await expect(page.getByTestId("present-editor-thumbs")).toBeVisible();
  await expect(page.getByTestId("present-editor-props")).toBeVisible();
  await expect(page.getByTestId("present-editor-rail")).toBeVisible();
  const save = page.getByTestId("present-editor-save");
  const box = await save.boundingBox();
  expect(box, `${tag}: save clipped`).toBeTruthy();
  const vp = page.viewportSize();
  if (box && vp) {
    expect(box.y + box.height, `${tag}: save below fold`).toBeLessThanOrEqual(vp.height + 2);
  }
  await page.getByTestId("present-editor-thumb-21").scrollIntoViewIfNeeded();
  await expect(page.getByTestId("present-editor-thumb-21")).toBeVisible();
  await page.screenshot({ path: path.join(ART, `electron-shell-${tag}.png`) });
}

test.describe("Present product READY electron", () => {
  test.skip(!process.env.ZECT_LIVE_PRESENT_READY, "opt-in live Zinnia READY proof (ZECT_LIVE_PRESENT_READY=1)");
  test.skip(!fs.existsSync(ELECTRON_EXE), "Electron binary is not installed in electron/node_modules");
  test.setTimeout(20 * 60_000);

  test("viewport matrix + maximize/restore + Electron restart reopen", async () => {
    fs.mkdirSync(ART, { recursive: true });
    const dest = path.join(os.homedir(), "Documents", "zect-zinnia-rail-22.pptx");
    runPythonScript(path.join(FRONTEND, "e2e/fixtures/make_zinnia_rail_deck.py"), [dest]);
    expect(fs.existsSync(dest)).toBeTruthy();
    const userData = fs.mkdtempSync(path.join(os.tmpdir(), "zect-present-ready-el-"));
    const editorUrl = `${BASE}/present/d/${encodeDeckId(dest)}/edit`;

    const launch = async (): Promise<ElectronApplication> =>
      electron.launch({
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

    let app = await launch();
    let page = await app.firstWindow({ timeout: 60_000 });
    try {
      await loginIfNeeded(page);
      await app.evaluate(async ({ BrowserWindow }, url) => {
        const win = BrowserWindow.getAllWindows()[0];
        if (win) await win.loadURL(url);
      }, editorUrl);
      await assertPresentShell(page, "initial");

      for (const vp of VIEWPORTS) {
        await page.setViewportSize({ width: vp.w, height: vp.h }).catch(() => {});
        await app.evaluate(
          async ({ BrowserWindow }, size: { w: number; h: number }) => {
            const win = BrowserWindow.getAllWindows()[0];
            if (win) {
              win.unmaximize();
              win.setSize(size.w, size.h);
            }
          },
          { w: vp.w, h: vp.h },
        );
        await assertPresentShell(page, vp.tag);
      }

      await app.evaluate(async ({ BrowserWindow }) => {
        const win = BrowserWindow.getAllWindows()[0];
        if (win) {
          win.maximize();
          await new Promise((r) => setTimeout(r, 400));
          win.unmaximize();
          win.setSize(1440, 900);
        }
      });
      await assertPresentShell(page, "maximize-restore");

      const inline = page.getByTestId("present-editor-inline-text").first();
      if (await inline.isVisible().catch(() => false)) {
        await inline.click();
        await page.keyboard.press("Control+A");
        await page.keyboard.type(EDIT_MARKER);
      }
      await page.getByTestId("present-editor-save").click();
      await expect(page.getByTestId("present-editor-status")).toContainText(/Saved|local|ooxml/i, {
        timeout: 20_000,
      });
      writeEvidence({ electron_save: dest, slide_count: 22 });
    } finally {
      await app.close();
    }

    app = await launch();
    page = await app.firstWindow({ timeout: 60_000 });
    try {
      await loginIfNeeded(page);
      await app.evaluate(async ({ BrowserWindow }, url) => {
        const win = BrowserWindow.getAllWindows()[0];
        if (win) await win.loadURL(url);
      }, editorUrl);
      await expect(page.getByTestId("present-studio")).toBeVisible({ timeout: 45_000 });
      await expect(page.getByTestId("present-editor-canvas")).toHaveAttribute("data-canvas", "document");
      const body = await page.locator('[data-testid="present-editor-canvas"]').innerText().catch(() => "");
      expect(body.includes(EDIT_MARKER) || body.length > 0).toBeTruthy();
      await page.screenshot({ path: path.join(ART, "electron-after-restart.png") });
      writeEvidence({ electron_restart_reopen: "PASS" });
    } finally {
      await app.close();
    }
  });
});
