/**
 * Present editor + UI export from an allowlisted PPTX (ZECT UI, not Presenton).
 */
import { test, expect } from "@playwright/test";
import fs from "fs";
import os from "os";
import path from "path";
import { fileURLToPath } from "url";
import { gotoAuthed } from "./helpers/login";
import { runPythonScript } from "./helpers/python";

const FRONTEND = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const REPO = path.resolve(FRONTEND, "..");
const ART = path.join(REPO, "test-results/present-editor-export");

function encodeDeckId(p: string) {
  return Buffer.from(p, "utf8").toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

test.describe("Present editor export", () => {
  test("open generated-style PPTX in ZECT editor, edit notes, export", async ({ page }) => {
    fs.mkdirSync(ART, { recursive: true });
    const dest = path.join(os.homedir(), "Documents", "zect-closure-editor.pptx");
    runPythonScript(path.join(FRONTEND, "e2e/fixtures/make_tiny_pptx.py"), [dest]);
    expect(fs.existsSync(dest)).toBeTruthy();

    await gotoAuthed(page, `/present/d/${encodeDeckId(dest)}`, "present-review");
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
    await page.getByTestId("present-open-rehearse").click();
    const voice = page.getByTestId("present-deck-voice-select");
    await expect(voice).toBeVisible();
    await expect(voice.locator('option[value="none"]')).toHaveCount(1);
    expect(await voice.locator('option[value^="stock:"]').count()).toBeGreaterThan(0);
    await voice.selectOption("none");
    await page.screenshot({ path: path.join(ART, "01-editor.png") });
  });
});
