/** Repair deck UI flow on a deliberately failing legacy deck. */
import { test, expect } from "@playwright/test";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { gotoAuthed } from "./helpers/login";

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const ART = path.join(REPO, "test-results", "present-v3-headed-acceptance");

function encodeDeckId(p: string) {
  return Buffer.from(p, "utf8").toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

test.describe("Present V3 repair deck UI", () => {
  test.skip(!process.env.ZECT_LIVE_PRESENT_V3_HEADED, "opt-in");

  test("Quality FAIL → Repair deck → Export enabled", async ({ page }) => {
    const src = path.join(REPO, "prompts", "zect-deck.pptx");
    const dest = path.join(process.env.USERPROFILE || "", "Documents", "v3-repair-ui-headed.pptx");
    fs.copyFileSync(src, dest);
    const deckId = encodeDeckId(dest);
    const base = process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:5173";
    await gotoAuthed(page, `/present/d/${deckId}`, "present-review");
    await expect(page.getByTestId("present-review-quality")).toBeVisible({ timeout: 60_000 });
    const qualityBefore = await page.getByTestId("present-review-quality").innerText();
    expect(/FAIL|blocked/i.test(qualityBefore)).toBeTruthy();
    const repair = page.getByTestId("present-review-repair-deck");
    await expect(repair).toBeVisible({ timeout: 30_000 });
    await repair.click();
    await expect(page.getByTestId("present-review-repair-status")).toContainText(/Repair|quality|PASS/i, {
      timeout: 120_000,
    });
    await page.goto(`${base}/present/d/${deckId}/export`);
    await expect(page.getByTestId("present-export-gate")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("present-export-pptx")).toBeEnabled({ timeout: 60_000 });
    fs.mkdirSync(ART, { recursive: true });
    fs.writeFileSync(
      path.join(ART, "repair-ui-evidence.json"),
      JSON.stringify({ deck_path: dest, quality_before: qualityBefore, repair_ui: "PASS" }, null, 2),
    );
  });
});
