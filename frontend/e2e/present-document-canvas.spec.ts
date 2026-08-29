/**
 * Headed proof: editor canvas is PresentationDocument-driven (not PNG + hit-boxes).
 * Opens an allowlisted mixed PPTX, edits inline text, saves, reopens, checks 1280x720.
 */
import { test, expect } from "@playwright/test";
import fs from "fs";
import os from "os";
import path from "path";
import { fileURLToPath } from "url";
import { gotoAuthed } from "./helpers/login";
import { runPythonScript } from "./helpers/python";
import { editCanvasTextBlock } from "./helpers/presentStudio";

const FRONTEND = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const REPO = path.resolve(FRONTEND, "..");
const ART = path.join(REPO, "test-results/present-document-canvas");

function encodeDeckId(p: string) {
  return Buffer.from(p, "utf8").toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

test.describe("Present document canvas", () => {
  test.use({ viewport: { width: 1280, height: 720 } });

  test("document canvas + thumbs + save + reopen at 1280x720", async ({ page }) => {
    fs.mkdirSync(ART, { recursive: true });
    const dest = path.join(os.homedir(), "Documents", "zect-document-canvas.pptx");
    runPythonScript(path.join(FRONTEND, "e2e/fixtures/make_tiny_pptx.py"), [dest]);
    expect(fs.existsSync(dest)).toBeTruthy();

    await gotoAuthed(page, `/present/d/${encodeDeckId(dest)}/edit`, "present-studio");
    await expect(page.getByTestId("present-editor")).toBeVisible({ timeout: 20_000 });
    const canvas = page.getByTestId("present-editor-canvas");
    await expect(canvas).toBeVisible();
    await expect(canvas).toHaveAttribute("data-canvas", "document");
    await expect(page.getByTestId("present-editor-block-overlay")).not.toHaveClass(/grid-cols-2/);
    await expect(page.getByTestId("present-editor-thumb-0")).toBeVisible();
    await expect(page.getByTestId("present-editor-thumb-img-0")).toBeVisible({ timeout: 15_000 });
    await editCanvasTextBlock(page, "Edited on canvas");
    await page.getByTestId("present-editor-save").click();
    await expect(page.getByTestId("present-editor-status")).toContainText(/Saved|local/i, { timeout: 15_000 });
    await page.screenshot({ path: path.join(ART, "01-document-canvas-1280x720.png") });

    await page.reload();
    await expect(page.getByTestId("present-editor-canvas")).toHaveAttribute("data-canvas", "document");
    await expect(page.locator('[data-testid^="present-editor-block-hit-"]').first()).toBeVisible();
    await page.screenshot({ path: path.join(ART, "02-reopen.png") });
  });

  test("Zinnia Open in editor shows a document canvas, not diagnostic boxes", async ({ page }) => {
    test.skip(!process.env.ZECT_LIVE_PRESENT, "opt-in live Zinnia template (ZECT_LIVE_PRESENT=1)");
    fs.mkdirSync(ART, { recursive: true });
    await gotoAuthed(page, "/present/create", "zect-present-page");
    await expect(page.getByTestId("zect-present-template-zinnia-executive-v1")).toBeVisible();
    await page.getByTestId("zect-present-template-zinnia-executive-v1").click();
    await page.getByTestId("zect-present-open-editor").click();
    await expect(page.getByTestId("present-editor")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("present-editor-canvas")).toHaveAttribute("data-canvas", "document");
    await expect(page.getByTestId("present-editor-block-overlay")).not.toHaveClass(/grid-cols-2/);
    await page.screenshot({ path: path.join(ART, "03-zinnia-open-editor.png") });
  });
});
