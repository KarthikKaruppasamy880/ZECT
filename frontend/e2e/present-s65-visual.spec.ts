/**
 * S6.5 headed visual parity: native plan → image/chart/table → editor → export → reopen.
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
const ART = path.join(REPO, "test-results/present-s65-visual");
const PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
  "base64",
);

test.describe("S6.5 visual content editor", () => {
  test("chart, table, and image survive editor save/export/reopen", async ({ page }) => {
    fs.mkdirSync(ART, { recursive: true });
    const dest = path.join(os.homedir(), "Documents", "zect-s65-visual.pptx");
    runPythonScript(path.join(FRONTEND, "e2e/fixtures/make_visual_pptx.py"), [dest]);
    expect(fs.existsSync(dest)).toBeTruthy();
    expect(fs.statSync(dest).size).toBeGreaterThan(1000);

    await gotoAuthed(page, "/present", "zect-present-page");
    await page.getByTestId("zect-present-template-zinnia-executive-v1").click();
    await page.getByTestId("zect-present-continue-generate").click();
    await expect(page.getByTestId("present-deck-panel")).toBeVisible();
    await page.getByTestId("present-deck-path").fill(dest);
    await expect(page.getByTestId("present-editor")).toBeVisible({ timeout: 20_000 });

    await page.getByTestId("present-editor-thumb-2").click();
    await expect(page.getByTestId("present-editor-block-chart")).toBeVisible({ timeout: 15_000 });
    await page.getByTestId("present-editor-chart-title").fill("Updated example chart");

    await page.getByTestId("present-editor-thumb-3").click();
    await expect(page.getByTestId("present-editor-block-table")).toBeVisible();
    await expect(page.getByTestId("present-editor-table-data")).toBeVisible();

    await page.getByTestId("present-editor-thumb-1").click();
    await page.getByTestId("present-editor-add-image").setInputFiles({
      name: "dot.png",
      mimeType: "image/png",
      buffer: PNG,
    });
    await expect(page.getByTestId("present-editor-block-image")).toBeVisible({ timeout: 15_000 });

    await page.getByTestId("present-editor-save").click();
    await expect(page.getByTestId("present-editor-status")).toContainText(/Saved|local|Image/i, { timeout: 15_000 });

    const downloadPromise = page.waitForEvent("download", { timeout: 20_000 });
    await page.getByTestId("present-editor-export").click();
    const download = await downloadPromise;
    const outFile = path.join(ART, download.suggestedFilename() || "export.pptx");
    await download.saveAs(outFile);
    expect(fs.statSync(outFile).size).toBeGreaterThan(1000);

    await page.getByTestId("present-deck-path").fill("");
    await page.getByTestId("present-deck-path").fill(dest);
    await expect(page.getByTestId("present-editor-thumbs")).toBeVisible({ timeout: 20_000 });
    await page.getByTestId("present-editor-thumb-2").click();
    await expect(page.getByTestId("present-editor-chart-title")).toHaveValue(/Updated example chart/i);
    await page.getByTestId("present-editor-thumb-1").click();
    await expect(page.getByTestId("present-editor-block-image")).toBeVisible();
    await page.screenshot({ path: path.join(ART, "01-visual-editor.png") });
  });
});
