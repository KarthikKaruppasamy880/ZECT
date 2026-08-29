/**
 * Headed Review/Edit/Export evidence for an existing golden V3 deck (skips generation latency).
 * Run: ZECT_LIVE_PRESENT_V3_HEADED=1 ZECT_V3_DECK_PATH="C:\...\golden-v3-agentic-deck-5.pptx" npx playwright test present-v3-headed-review-export.spec.ts --headed
 */
import { test, expect } from "@playwright/test";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { gotoAuthed } from "./helpers/login";

const FRONTEND = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const REPO = path.resolve(FRONTEND, "..");
const ART = path.join(REPO, "test-results", "present-v3-headed-acceptance");

function encodeDeckId(p: string) {
  return Buffer.from(p, "utf8").toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function writeUiEvidence(partial: Record<string, unknown>) {
  fs.mkdirSync(ART, { recursive: true });
  const prev = (() => {
    try {
      return JSON.parse(fs.readFileSync(path.join(ART, "ui-evidence.json"), "utf8")) as Record<string, unknown>;
    } catch {
      return {};
    }
  })();
  fs.writeFileSync(path.join(ART, "ui-evidence.json"), JSON.stringify({ ...prev, ...partial }, null, 2));
}

test.describe("Present V3 headed review/export evidence", () => {
  test.skip(!process.env.ZECT_LIVE_PRESENT_V3_HEADED, "opt-in (ZECT_LIVE_PRESENT_V3_HEADED=1)");

  test("Review + Edit + Export on golden deck", async ({ page }) => {
    const deckPath =
      process.env.ZECT_V3_DECK_PATH ||
      path.join(process.env.USERPROFILE || "", "Documents", "golden-v3-agentic-deck-5.pptx");
    expect(fs.existsSync(deckPath), `deck missing: ${deckPath}`).toBeTruthy();
    fs.mkdirSync(ART, { recursive: true });
    const deckId = encodeDeckId(deckPath);
    const base = process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:5173";
    const reviewUrl = `/present/d/${deckId}`;
    const editUrl = `/present/d/${deckId}/edit`;
    const exportUrl = `/present/d/${deckId}/export`;
    writeUiEvidence({
      deck_path: deckPath,
      deck_id: deckId,
      review_url: `${base}${reviewUrl}`,
      edit_url: `${base}${editUrl}`,
      export_url: `${base}${exportUrl}`,
      electron_url: `${base}${reviewUrl}`,
    });

    await gotoAuthed(page, reviewUrl, "present-review");
    await expect(page.getByTestId("present-review-quality")).toBeVisible({ timeout: 60_000 });
    for (let i = 0; i < 3; i++) {
      await page.getByTestId(`present-editor-thumb-${i}`).click();
      await expect(page.getByTestId("present-editor-slide-preview")).toBeVisible({ timeout: 30_000 });
      await page.getByTestId("present-editor-slide-preview").screenshot({
        path: path.join(ART, `review-slide-${i + 1}-main.png`),
      });
      const thumb = page.getByTestId(`present-editor-thumb-img-${i}`);
      if (await thumb.isVisible().catch(() => false)) {
        await thumb.screenshot({ path: path.join(ART, `review-slide-${i + 1}-thumb.png`) });
      }
    }

    await page.goto(`${base}${editUrl}`);
    await expect(page.getByTestId("present-studio")).toBeVisible({ timeout: 60_000 });
    for (let i = 0; i < 3; i++) {
      await page.getByTestId(`present-editor-thumb-${i}`).click();
      await expect(page.getByTestId("present-editor-slide-preview")).toBeVisible({ timeout: 30_000 });
      await page.getByTestId("present-editor-slide-preview").screenshot({
        path: path.join(ART, `edit-slide-${i + 1}-main.png`),
      });
    }

    await page.goto(`${base}${exportUrl}`);
    await expect(page.getByTestId("present-export-gate")).toBeVisible({ timeout: 30_000 });
    const exportBtn = page.getByTestId("present-export-pptx");
    await expect(exportBtn).toBeEnabled({ timeout: 60_000 });
    const downloadPromise = page.waitForEvent("download", { timeout: 120_000 });
    await exportBtn.click();
    const download = await downloadPromise;
    const exportPath = path.join(ART, "exported-golden-v3-ui.pptx");
    await download.saveAs(exportPath);
    expect(fs.statSync(exportPath).size).toBeGreaterThan(10_000);
    writeUiEvidence({
      export_download_path: exportPath,
      export_bytes: fs.statSync(exportPath).size,
      ui_review_export: "PASS",
    });
  });
});
