/**
 * P0 Electron: same Present flow as headed browser (Dashboard → Create → Generate → Review → Export).
 * Opt-in: ZECT_LIVE_P0=1. Uses the running Vite + native API.
 */
import { test, expect, _electron as electron, type Page } from "@playwright/test";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { loadEnvCreds } from "./helpers/env";

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const ART = path.join(REPO, "test-results/present-p0-electron");
const ELECTRON_MAIN = path.join(REPO, "electron", "main.js");
const ELECTRON_EXE = path.join(REPO, "electron", "node_modules", "electron", "dist", "electron.exe");

test.skip(!process.env.ZECT_LIVE_P0, "opt-in P0 Electron (ZECT_LIVE_P0=1)");

async function login(page: Page) {
  const { username, password } = loadEnvCreds();
  await page.waitForLoadState("domcontentloaded");
  const loginForm = page.getByTestId("login-username");
  if (await loginForm.isVisible({ timeout: 20_000 }).catch(() => false)) {
    await page.getByTestId("login-username").fill(username);
    await page.getByTestId("login-password").fill(password);
    await page.getByTestId("login-submit").click();
    await expect(page.getByTestId("login-submit")).toBeHidden({ timeout: 30_000 });
  }
}

async function generateAndExport(page: Page, opts: { fast: boolean; shotPrefix: string }) {
  const { fast, shotPrefix } = opts;
  await page.goto("http://127.0.0.1:5173/present", { waitUntil: "domcontentloaded", timeout: 30_000 });
  await expect(page.getByTestId("present-dashboard")).toBeVisible({ timeout: 30_000 });
  await page.screenshot({ path: path.join(ART, `${shotPrefix}-01-dashboard.png`), timeout: 15_000 });
  await page.getByTestId("present-nav-create").click({ force: true, timeout: 20_000 });
  await expect(page.getByTestId("zect-present-workspace")).toBeVisible({ timeout: 20_000 });
  await page.getByTestId("zect-present-template-zinnia-executive-v1").click({ force: true, timeout: 20_000 });
  await page.getByTestId("zect-present-continue-generate").click({ force: true, timeout: 20_000 });
  await expect(page.getByTestId("present-deck-panel")).toBeVisible({ timeout: 20_000 });
  await page.getByTestId("present-deck-prompt").fill(
    "Zinnia executive brief: Q3 delivery status, top risks, and decisions needed. Do not invent owners or dates.",
  );
  await page.getByTestId("present-deck-n-slides").fill("4");
  const approve = page.getByTestId("present-deck-flow-b-approve").locator("input");
  if (await approve.isVisible().catch(() => false)) await approve.check();
  const generateWait = page.waitForResponse(
    (r) => r.url().includes("/api/mentrix/presenton/generate") && r.request().method() === "POST",
    { timeout: 600_000 },
  );
  if (fast) {
    await page.locator('[data-testid="present-advanced-generate"]').evaluate(
      (el: HTMLDetailsElement) => {
        el.open = true;
      },
      undefined,
      { timeout: 20_000 },
    );
    await expect(page.getByTestId("present-deck-generate-fast-basic")).toBeEnabled({ timeout: 90_000 });
    await page.getByTestId("present-deck-generate-fast-basic").click({ force: true });
  } else {
    await expect(page.getByTestId("present-deck-generate")).toBeEnabled({ timeout: 90_000 });
    await page.getByTestId("present-deck-generate").click({ force: true });
  }
  const genRes = await generateWait;
  if (!genRes.ok()) {
    throw new Error(`generate HTTP ${genRes.status()} ${(await genRes.text()).slice(0, 800)}`);
  }
  await expect(page.getByTestId("present-review")).toBeVisible({ timeout: 60_000 });
  await expect(page.getByTestId("present-editor")).toBeVisible({ timeout: 30_000 });
  await page.screenshot({ path: path.join(ART, `${shotPrefix}-02-review.png`), timeout: 15_000 });
  await page.goto(page.url().replace(/\/rehearse$|\/export$/, "") + "/export");
  await expect(page.getByTestId("present-export-gate")).toBeVisible({ timeout: 30_000 });
  await page.screenshot({ path: path.join(ART, `${shotPrefix}-03-export.png`), timeout: 15_000 });
  await expect(page.getByTestId("present-export-hard-block")).toHaveCount(0);
  const accept = page.getByTestId("present-export-accept-warnings");
  if (await accept.isVisible().catch(() => false)) {
    await accept.locator("input").check();
  }
  const downloadPromise = page.waitForEvent("download", { timeout: 30_000 });
  await page.getByTestId("present-export-pptx").click({ force: true });
  const download = await downloadPromise;
  const outFile = path.join(ART, download.suggestedFilename() || `${shotPrefix}.pptx`);
  await download.saveAs(outFile);
  expect(fs.statSync(outFile).size).toBeGreaterThan(1000);
}

test("Electron Dashboard → Create → Quality then Fast → Review → Export", async () => {
  test.setTimeout(20 * 60_000);
  fs.mkdirSync(ART, { recursive: true });
  expect(fs.existsSync(ELECTRON_MAIN)).toBeTruthy();
  const app = await electron.launch({
    executablePath: fs.existsSync(ELECTRON_EXE) ? ELECTRON_EXE : undefined,
    args: [ELECTRON_MAIN],
    cwd: path.join(REPO, "electron"),
    env: {
      ...process.env,
      ZECT_DEV: "true",
      ZECT_DEV_URL: "http://127.0.0.1:5173",
      ZECT_API_URL: process.env.VITE_API_URL || "http://127.0.0.1:8010",
      ZECT_MANAGE_SERVICES: "0",
      ZECT_DEVTOOLS: "0",
    },
  });
  try {
    const page = await app.firstWindow();
    await login(page);
    await generateAndExport(page, { fast: false, shotPrefix: "quality" });
    await generateAndExport(page, { fast: true, shotPrefix: "fast" });
  } finally {
    await app.close();
  }
});
