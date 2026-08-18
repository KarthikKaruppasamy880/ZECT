/**
 * Runtime recovery production (headed).
 * System Health is visible. Live NSIS / clean-machine install is never clicked.
 * Occupied-port sidecar policy is unit-tested in Electron lifecycle, not pentested here.
 */
import { test, expect } from "@playwright/test";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { gotoAuthed } from "./helpers/login";

const FRONTEND = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const REPO = path.resolve(FRONTEND, "..");
const ART = path.join(REPO, "test-results", "runtime-recovery-production");
const API = process.env.VITE_API_URL || process.env.ZECT_API_URL || "http://127.0.0.1:8000";

test.describe("runtime recovery production — unauthenticated", () => {
  test.use({ storageState: { cookies: [], origins: [] } });
  test.setTimeout(60_000);

  test("healthz open; privileged health bounces to login", async ({ page }) => {
    fs.mkdirSync(ART, { recursive: true });
    const hz = await page.request.get(`${API}/healthz`);
    expect(hz.ok()).toBeTruthy();
    await page.goto("/system-health");
    await expect(page.getByTestId("login-username")).toBeVisible({ timeout: 20_000 });
    await page.screenshot({ path: path.join(ART, "01-unauth-health.png") });
  });
});

test.describe("runtime recovery production — authenticated", () => {
  test.setTimeout(120_000);

  test("system health and developer workspace remain after login", async ({ page }) => {
    fs.mkdirSync(ART, { recursive: true });
    const evidence: Record<string, unknown> = {
      nsis_clean_machine: false,
      live_installer_clicked: false,
    };
    await gotoAuthed(page, "/system-health", "system-health-page");
    await expect(page.getByTestId("system-health-status")).toBeVisible({ timeout: 20_000 });
    evidence.health_status = ((await page.getByTestId("system-health-status").innerText()) || "").trim();
    await page.screenshot({ path: path.join(ART, "02-system-health.png") });

    await gotoAuthed(page, "/workspace", "developer-workspace");
    await page.screenshot({ path: path.join(ART, "03-developer.png") });
    fs.writeFileSync(path.join(ART, "evidence.json"), JSON.stringify(evidence, null, 2));
  });
});
