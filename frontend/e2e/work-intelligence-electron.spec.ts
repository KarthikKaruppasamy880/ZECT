/**
 * Electron Work Items / Processes / Developer lattice. Skip if electron.exe
 * is missing — skip ≠ core PASS. Uses sidebar clicks (full page.goto remounts App).
 */
import { test, expect, _electron as electron, type Page } from "@playwright/test";
import fs from "fs";
import os from "os";
import path from "path";
import { fileURLToPath } from "url";
import { loadEnvCreds } from "./helpers/env";

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const ART = path.join(REPO, "test-results", "work-intelligence-electron");
const ELECTRON_MAIN = path.join(REPO, "electron", "main.js");
const ELECTRON_EXE = path.join(REPO, "electron", "node_modules", "electron", "dist", "electron.exe");
const API = process.env.VITE_API_URL || process.env.ZECT_API_URL || "http://127.0.0.1:8000";
const BASE = process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:5173";

test.describe("work intelligence electron", () => {
  test.setTimeout(180_000);

  test("Projects, Work Items, Processes via sidebar", async () => {
    test.skip(!fs.existsSync(ELECTRON_EXE), "Electron binary is not installed in electron/node_modules");
    fs.mkdirSync(ART, { recursive: true });
    const userData = fs.mkdtempSync(path.join(os.tmpdir(), "zect-electron-wi-"));
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

      await page.getByRole("link", { name: "Projects" }).first().click();
      await expect(page.getByTestId("projects-page")).toBeVisible({ timeout: 30_000 });
      await page.screenshot({ path: path.join(ART, "01-projects.png") });

      await page.getByRole("link", { name: "Work Items" }).first().click();
      await expect(page.getByTestId("work-items-page")).toBeVisible({ timeout: 30_000 });
      await page.getByTestId("work-items-sample").click();
      await expect(page.getByRole("button", { name: /Fix Failed Order Validation/ })).toBeVisible({
        timeout: 20_000,
      });
      await expect(page.getByTestId("work-item-detail")).toBeVisible();
      await page.screenshot({ path: path.join(ART, "02-work-items.png") });

      await page.getByRole("link", { name: "Processes" }).first().click();
      await expect(page.getByTestId("process-sample-card")).toBeVisible({ timeout: 30_000 });
      await expect(page.getByTestId("process-connector-status")).toBeVisible();
      await page.screenshot({ path: path.join(ART, "03-processes.png") });

      await page.getByRole("link", { name: "Developer" }).first().click();
      await expect(page.getByTestId("developer-workspace")).toBeVisible({ timeout: 30_000 });
      await expect(page.getByTestId("workspace-git-lattice")).toBeVisible();
      await page.screenshot({ path: path.join(ART, "04-developer.png") });
    } finally {
      await app.close();
    }
  });
});
