/**
 * P0 Electron: same Present flow as headed browser (Dashboard → Create → Generate → Review → Export).
 * Opt-in: ZECT_LIVE_P0=1. Uses the running Vite + native API.
 */
import { test, expect, _electron as electron, type ElectronApplication, type Page } from "@playwright/test";
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

async function armElectronDownload(app: ElectronApplication, destFile: string) {
  fs.mkdirSync(path.dirname(destFile), { recursive: true });
  if (fs.existsSync(destFile)) fs.unlinkSync(destFile);
  await app.evaluate(async ({ session }, dest) => {
    const ses = session.defaultSession;
    ses.removeAllListeners("will-download");
    ses.on("will-download", (_event, item) => {
      item.setSavePath(dest);
    });
  }, destFile);
}

async function waitForSavedPptx(destFile: string, timeoutMs = 30_000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    if (fs.existsSync(destFile) && fs.statSync(destFile).size > 1000) return;
    await new Promise((r) => setTimeout(r, 200));
  }
  throw new Error(`electron PPTX was not saved: ${destFile}`);
}

async function generateAndExport(
  page: Page,
  app: ElectronApplication,
  opts: { fast: boolean; shotPrefix: string },
) {
  const { fast, shotPrefix } = opts;
  const api = process.env.VITE_API_URL || process.env.ZECT_API_URL || "http://127.0.0.1:8010";
  await page.addInitScript((origin: string) => {
    sessionStorage.setItem("zect_api_origin", origin);
  }, api);
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
    await page.locator('[data-testid="present-advanced-generate"]').evaluate((el: HTMLDetailsElement) => {
      el.open = true;
      el.dispatchEvent(new Event("toggle", { bubbles: true }));
    });
    const fastBtn = page.getByTestId("present-deck-generate-fast-basic");
    await expect(fastBtn).toBeEnabled({ timeout: 90_000 });
    await fastBtn.evaluate((el: HTMLButtonElement) => el.click());
  } else {
    await expect(page.getByTestId("present-deck-generate")).toBeEnabled({ timeout: 90_000 });
    await page.getByTestId("present-deck-generate").click({ force: true });
  }
  const bounced = page.getByText(/click Generate again/i);
  const first = await Promise.race([
    generateWait.then((r) => ({ kind: "gen" as const, r })),
    bounced.waitFor({ state: "visible", timeout: 600_000 }).then(() => ({ kind: "bounce" as const })),
  ]);
  let genRes = first.kind === "gen" ? first.r : undefined;
  if (first.kind === "bounce") {
    await approve.check();
    if (fast) {
      await page.getByTestId("present-deck-generate-fast-basic").evaluate((el: HTMLButtonElement) => el.click());
    } else {
      await page.getByTestId("present-deck-generate").click({ force: true });
    }
    genRes = await generateWait;
  }
  if (!genRes?.ok()) {
    throw new Error(`generate HTTP ${genRes?.status()} ${genRes ? (await genRes.text()).slice(0, 800) : "missing"}`);
  }
  await expect(page.getByTestId("present-review")).toBeVisible({ timeout: 60_000 });
  await expect(page.getByTestId("present-editor")).toBeVisible({ timeout: 30_000 });
  await page.screenshot({ path: path.join(ART, `${shotPrefix}-02-review.png`), timeout: 15_000 });
  await page.getByTestId("present-open-export").click({ force: true, timeout: 20_000 });
  await expect(page.getByTestId("present-export-gate")).toBeVisible({ timeout: 30_000 });
  await page.screenshot({ path: path.join(ART, `${shotPrefix}-03-export.png`), timeout: 15_000 });
  await expect(page.getByTestId("present-export-hard-block")).toHaveCount(0);
  const accept = page.getByTestId("present-export-accept-warnings");
  if (await accept.isVisible().catch(() => false)) {
    await accept.locator("input").check();
  }
  const destFile = path.join(ART, `${shotPrefix}.pptx`);
  await armElectronDownload(app, destFile);
  await page.getByTestId("present-export-pptx").click({ force: true });
  await waitForSavedPptx(destFile);
  expect(fs.statSync(destFile).size).toBeGreaterThan(1000);
}

test("Electron Dashboard → Create → Quality then Fast → Review → Export", async () => {
  test.setTimeout(20 * 60_000);
  fs.mkdirSync(ART, { recursive: true });
  expect(fs.existsSync(ELECTRON_MAIN)).toBeTruthy();
  const userData = path.join(ART, `electron-user-data-${Date.now()}`);
  fs.mkdirSync(userData, { recursive: true });
  const app = await electron.launch({
    executablePath: fs.existsSync(ELECTRON_EXE) ? ELECTRON_EXE : undefined,
    args: [`--user-data-dir=${userData}`, ELECTRON_MAIN],
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
    await generateAndExport(page, app, { fast: false, shotPrefix: "quality" });
    await generateAndExport(page, app, { fast: true, shotPrefix: "fast" });
  } finally {
    await app.close();
  }
});
