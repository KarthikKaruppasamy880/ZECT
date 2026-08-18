/**
 * Electron Permissions / Security / Sandbox. Skip if electron.exe is missing —
 * skip ≠ core PASS. Uses sidebar clicks (full page.goto remounts App).
 */
import { test, expect, _electron as electron, type Page } from "@playwright/test";
import fs from "fs";
import os from "os";
import path from "path";
import { fileURLToPath } from "url";
import { loadEnvCreds } from "./helpers/env";

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const ART = path.join(REPO, "test-results", "security-electron");
const ELECTRON_MAIN = path.join(REPO, "electron", "main.js");
const ELECTRON_EXE = path.join(REPO, "electron", "node_modules", "electron", "dist", "electron.exe");
const API = process.env.VITE_API_URL || process.env.ZECT_API_URL || "http://127.0.0.1:8000";
const BASE = process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:5173";

test.describe("security production electron", () => {
  test.setTimeout(180_000);

  test("Permissions, Security, Sandbox via sidebar", async () => {
    test.skip(!fs.existsSync(ELECTRON_EXE), "Electron binary is not installed in electron/node_modules");
    fs.mkdirSync(ART, { recursive: true });
    const userData = fs.mkdtempSync(path.join(os.tmpdir(), "zect-electron-sec-"));
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

      const nav = page.getByTestId("app-sidebar");
      await nav.getByTestId("sidebar-labs-more").click();
      await nav.getByRole("link", { name: "Permissions" }).click();
      await expect(page.getByTestId("permissions-page")).toBeVisible({ timeout: 30_000 });
      await page.screenshot({ path: path.join(ART, "01-permissions.png") });

      await nav.getByRole("link", { name: /^Security$/ }).click();
      await expect(page.getByTestId("security-incidents-page")).toBeVisible({ timeout: 30_000 });
      await page.screenshot({ path: path.join(ART, "02-security.png") });

      await nav.getByRole("link", { name: "Sandbox" }).click();
      await expect(page.getByTestId("sandbox-page")).toBeVisible({ timeout: 30_000 });
      await page.screenshot({ path: path.join(ART, "03-sandbox.png") });
    } finally {
      await app.close();
    }
  });
});
