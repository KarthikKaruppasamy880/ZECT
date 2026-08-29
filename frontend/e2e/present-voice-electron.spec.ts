/**
 * Electron Present + Voice shell. Skip if electron.exe is missing — skip ≠ core PASS.
 * Does not click live Quality generate; live Presenton/Voicebox/COM remain BLOCKED_EXTERNAL.
 */
import { test, expect, _electron as electron, type Page } from "@playwright/test";
import fs from "fs";
import os from "os";
import path from "path";
import { fileURLToPath } from "url";
import { loadEnvCreds } from "./helpers/env";

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const ART = path.join(REPO, "test-results", "present-voice-electron");
const ELECTRON_MAIN = path.join(REPO, "electron", "main.js");
const ELECTRON_EXE = path.join(REPO, "electron", "node_modules", "electron", "dist", "electron.exe");
const API = process.env.VITE_API_URL || process.env.ZECT_API_URL || "http://127.0.0.1:8000";
const BASE = process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:5173";

test.describe("present + voice electron", () => {
  test.setTimeout(180_000);

  test("Present dashboard and Companion voice in Electron", async () => {
    test.skip(!fs.existsSync(ELECTRON_EXE), "Electron binary is not installed in electron/node_modules");
    fs.mkdirSync(ART, { recursive: true });
    const userData = fs.mkdtempSync(path.join(os.tmpdir(), "zect-electron-pv-"));
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
    const page: Page = await app.firstWindow({ timeout: 60_000 });
    try {
      await page.waitForLoadState("domcontentloaded").catch(() => {});
      if (await page.getByTestId("login-username").isVisible({ timeout: 15_000 }).catch(() => false)) {
        await page.getByTestId("login-username").fill(username);
        await page.getByTestId("login-password").fill(password);
        await page.getByTestId("login-submit").click();
        await expect(page.getByTestId("login-submit")).toBeHidden({ timeout: 30_000 });
      }
      const presentLink = page.getByRole("link", { name: "Present" }).first();
      await expect(presentLink).toBeVisible({ timeout: 45_000 });
      await presentLink.click();
      await expect(page.getByTestId("zect-present-page")).toBeVisible({ timeout: 30_000 });
      await expect(page.getByTestId("present-dashboard")).toBeVisible();
      await expect(page.getByTestId("present-create-with-ai")).toBeVisible();
      await expect(page.getByTestId("present-blank")).toBeVisible();
      await expect(page.getByTestId("present-import")).toBeVisible();
      await page.screenshot({ path: path.join(ART, "01-dashboard.png") });

      await page.getByTestId("present-create-with-ai").click();
      await expect(page.getByTestId("zect-present-workspace")).toBeVisible({ timeout: 20_000 });
      await expect(page.getByTestId("present-lifecycle-state")).toBeVisible();
      await page.getByTestId("zect-present-template-zinnia-executive-v1").click();
      await page.getByTestId("zect-present-continue-generate").click();
      await expect(page.getByTestId("present-deck-generate")).toBeVisible();
      await expect(page.getByTestId("present-deck-generate-fast-basic")).toBeAttached();
      await page.screenshot({ path: path.join(ART, "02-create.png") });

      await page.getByRole("link", { name: "Mentrix Companion" }).first().click();
      await expect(page.getByTestId("mentrix-companion-page")).toBeVisible({ timeout: 30_000 });
      const closeArt = page.getByTestId("mentrix-artifacts-close");
      if (await closeArt.isVisible().catch(() => false)) await closeArt.click();
      await page.getByTestId("mentrix-mode-voice").click();
      await expect(page.getByTestId("clone-voice-panel")).toBeVisible();
      await page.screenshot({ path: path.join(ART, "03-voice.png") });
    } finally {
      await app.close();
    }
  });
});
