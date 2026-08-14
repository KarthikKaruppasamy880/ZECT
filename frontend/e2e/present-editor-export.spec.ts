/**
 * Present editor + UI export from an allowlisted PPTX (ZECT UI, not Presenton).
 */
import { test, expect, type Page } from "@playwright/test";
import { execSync } from "child_process";
import fs from "fs";
import os from "os";
import path from "path";
import { fileURLToPath } from "url";
import { loadEnvCreds } from "./helpers/env";

const FRONTEND = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const REPO = path.resolve(FRONTEND, "..");
const ART = path.join(REPO, "test-results/present-editor-export");

async function ensureLoggedIn(page: Page) {
  const { username, password } = loadEnvCreds();
  await page.goto("/");
  const loginVisible = await page.getByTestId("login-username").isVisible().catch(() => false);
  const token = await page.evaluate(() => localStorage.getItem("zect_token"));
  if (loginVisible || !token) {
    await expect(page.getByTestId("login-username")).toBeVisible({ timeout: 15_000 });
    await page.getByTestId("login-username").fill(username);
    await page.getByTestId("login-password").fill(password);
    await page.getByTestId("login-submit").click();
    await expect(page.getByTestId("login-submit")).toBeHidden({ timeout: 30_000 });
  }
}

test.describe("Present editor export", () => {
  test("open generated-style PPTX in ZECT editor, edit notes, export", async ({ page }) => {
    fs.mkdirSync(ART, { recursive: true });
    const dest = path.join(os.homedir(), "Documents", "zect-closure-editor.pptx");
    execSync(`py -3.12 "${path.join(FRONTEND, "e2e/fixtures/make_tiny_pptx.py")}" "${dest}"`, { stdio: "pipe" });
    expect(fs.existsSync(dest)).toBeTruthy();

    await ensureLoggedIn(page);
    await page.goto("/present");
    await expect(page.getByTestId("zect-present-page")).toBeVisible({ timeout: 20_000 });
    await page.getByTestId("zect-present-template-zinnia-executive-v1").click();
    await page.getByTestId("zect-present-continue-generate").click();
    await expect(page.getByTestId("present-deck-panel")).toBeVisible();
    await page.getByTestId("present-deck-path").fill(dest);
    await expect(page.getByTestId("present-editor")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId("present-editor-thumbs")).toBeVisible();
    await page.getByTestId("present-editor-thumb-1").click();
    await page.getByTestId("present-editor-notes").fill("Executive note: owners needed this week.");
    await page.getByTestId("present-editor-save").click();
    await expect(page.getByTestId("present-editor-status")).toContainText(/Saved|local/i, { timeout: 15_000 });
    const downloadPromise = page.waitForEvent("download", { timeout: 20_000 });
    await page.getByTestId("present-editor-export").click();
    const download = await downloadPromise;
    const outFile = path.join(ART, download.suggestedFilename() || "export.pptx");
    await download.saveAs(outFile);
    expect(fs.statSync(outFile).size).toBeGreaterThan(100);
    const voice = page.getByTestId("present-deck-voice-select");
    await expect(voice).toBeVisible();
    await expect(voice.locator('option[value="none"]')).toHaveCount(1);
    expect(await voice.locator('option[value^="stock:"]').count()).toBeGreaterThan(0);
    await voice.selectOption("none");
    await page.screenshot({ path: path.join(ART, "01-editor.png") });
  });
});
