/**
 * Combined V3 Present headed acceptance — real human failure scenario.
 * Run: ZECT_LIVE_PRESENT_V3_HEADED=1 npx playwright test e2e/present-v3-combined-headed-acceptance.spec.ts --headed
 */
import { test, expect, type Page } from "@playwright/test";
import { execFileSync } from "child_process";
import fs from "fs";
import os from "os";
import path from "path";
import { fileURLToPath } from "url";
import { gotoAuthed } from "./helpers/login";

const FRONTEND = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const REPO = path.resolve(FRONTEND, "..");
const ART = path.join(REPO, "test-results", "present-v3-headed-acceptance");
const GOLDEN_PROMPT =
  "Difference between AI Agentic and the Graph, loop and KV catch with LLM fine tuning";
const REQUESTED = 3;

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

async function captureSlideEvidence(page: Page, tag: string, slideIndex: number) {
  await page.getByTestId(`present-editor-thumb-${slideIndex}`).click();
  await expect(page.getByTestId("present-editor-slide-preview")).toBeVisible({ timeout: 30_000 });
  const main = path.join(ART, `${tag}-slide-${slideIndex + 1}-main.png`);
  await page.getByTestId("present-editor-slide-preview").screenshot({ path: main });
  const thumb = path.join(ART, `${tag}-slide-${slideIndex + 1}-thumb.png`);
  const thumbImg = page.getByTestId(`present-editor-thumb-img-${slideIndex}`);
  if (await thumbImg.isVisible().catch(() => false)) {
    await thumbImg.screenshot({ path: thumb });
  }
  return { main, thumb };
}

test.describe("Present V3 combined headed acceptance", () => {
  test.skip(!process.env.ZECT_LIVE_PRESENT_V3_HEADED, "opt-in (ZECT_LIVE_PRESENT_V3_HEADED=1)");

  test.setTimeout(25 * 60_000);

  test("Create → 3 slides → Review → Edit → Export + Repair flow", async ({ page, context }) => {
    fs.mkdirSync(ART, { recursive: true });
    const consoleErrors: string[] = [];
    const asset404: string[] = [];
    page.on("console", (msg) => {
      const t = msg.text();
      if (/duplicate.*key|Warning.*key/i.test(t)) consoleErrors.push(t);
      if (msg.type() === "error") consoleErrors.push(t);
    });
    page.on("response", (res) => {
      if (res.status() === 404 && /\/api\/|asset|present/i.test(res.url())) {
        asset404.push(res.url());
      }
    });

    await gotoAuthed(page, "/present/create", "zect-present-page");
    await page.getByTestId("zect-present-template-zinnia-executive-v1").click();
    await page.getByTestId("zect-present-continue-generate").click();
    await expect(page.getByTestId("present-deck-prompt")).toBeVisible({ timeout: 20_000 });

    await page.getByTestId("present-deck-prompt").fill(GOLDEN_PROMPT);
    await page.getByTestId("present-deck-n-slides").fill(String(REQUESTED));
    const autoSlides = page.getByTestId("present-generate-auto-slides");
    if (await autoSlides.isChecked().catch(() => false)) {
      await autoSlides.uncheck();
    }
    await page.getByTestId("present-deck-template").selectOption("zinnia-executive-v1").catch(() => undefined);

    await page.getByTestId("present-deck-generate").click();

    const confirm = page.getByTestId("present-deck-confirm");
    const review = page.getByTestId("present-review");
    const flowB = page.getByTestId("present-deck-flow-b-approve");
    await page.waitForTimeout(1500);
    if (await flowB.isVisible().catch(() => false)) {
      const status = await page.getByTestId("present-deck-status").innerText().catch(() => "");
      if (/Approve generation|claims/i.test(status)) {
        await flowB.check();
        await page.getByTestId("present-deck-generate").click();
      }
    }
    const sawConfirm = await confirm.isVisible().catch(() => false);
    if (sawConfirm) {
      const outline = await page.getByTestId("present-deck-adapted-prompt").inputValue();
      expect(outline.toLowerCase()).toContain("agentic");
      expect(page.getByText(new RegExp(`Target:\\s*${REQUESTED}\\s*slides`, "i"))).toBeVisible();
      await page.getByTestId("present-deck-generate").click();
    }
    await expect(review).toBeVisible({ timeout: 10 * 60_000 });
    await expect(page.getByTestId("present-review-quality")).toBeVisible({ timeout: 120_000 });

    const outline = sawConfirm
      ? await page.getByTestId("present-deck-adapted-prompt").inputValue()
      : GOLDEN_PROMPT;

    const qualityText = await page.getByTestId("present-review-quality").innerText();
    writeUiEvidence({ outline_excerpt: outline.slice(0, 400), review_quality_text: qualityText });

    let deckPath = "";
    for (let i = 0; i < 90; i++) {
      deckPath = await page.evaluate(() => localStorage.getItem("zect_mentrix_present_deck_path") || "");
      if (deckPath) break;
      await page.waitForTimeout(1000);
    }
    expect(deckPath, "generated deck path in localStorage").toBeTruthy();
    const deckId = encodeDeckId(deckPath);
    const reviewUrl = `/present/d/${deckId}`;
    const editUrl = `/present/d/${deckId}/edit`;
    const exportUrl = `/present/d/${deckId}/export`;
    const base = process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:5173";
    writeUiEvidence({
      deck_path: deckPath,
      deck_id: deckId,
      review_url: `${base}${reviewUrl}`,
      edit_url: `${base}${editUrl}`,
      export_url: `${base}${exportUrl}`,
      electron_url: `${base}${reviewUrl}`,
    });

    for (let i = 0; i < REQUESTED; i++) {
      await captureSlideEvidence(page, "review", i);
    }
    expect(consoleErrors.filter((e) => /duplicate.*key/i.test(e))).toHaveLength(0);

    await page.goto(`${base}${editUrl}`);
    await expect(page.getByTestId("present-studio")).toBeVisible({ timeout: 60_000 });
    for (let i = 0; i < REQUESTED; i++) {
      await captureSlideEvidence(page, "edit", i);
    }

    await page.goto(`${base}${exportUrl}`);
    await expect(page.getByTestId("present-export-gate")).toBeVisible({ timeout: 30_000 });
    const hardBlock = await page.getByTestId("present-export-hard-block").isVisible().catch(() => false);
    if (hardBlock) {
      await page.goto(`${base}${reviewUrl}`);
      const repairBtn = page.getByTestId("present-review-repair-deck");
      if (await repairBtn.isVisible().catch(() => false)) {
        await repairBtn.click();
        await expect(page.getByTestId("present-review-repair-status")).toContainText(/Repair|quality/i, {
          timeout: 120_000,
        });
      }
      await page.goto(`${base}${exportUrl}`);
    }
    const exportBtn = page.getByTestId("present-export-pptx");
    await expect(exportBtn).toBeEnabled({ timeout: 60_000 });
    const downloadPromise = page.waitForEvent("download", { timeout: 120_000 });
    await exportBtn.click();
    const download = await downloadPromise;
    const exportPath = path.join(ART, "exported-golden-v3.pptx");
    await download.saveAs(exportPath);
    expect(fs.statSync(exportPath).size).toBeGreaterThan(10_000);
    writeUiEvidence({
      export_download_path: exportPath,
      export_bytes: fs.statSync(exportPath).size,
      asset_404s: asset404,
      console_errors: consoleErrors.slice(0, 20),
    });

    execFileSync(process.env.ZECT_PYTHON || "python", [path.join(REPO, "backend", "scripts", "present_v3_combined_acceptance.py")], {
      cwd: REPO,
      stdio: "inherit",
      env: { ...process.env, ZECT_LIVE_PPT_COM: process.env.ZECT_LIVE_PPT_COM || "1" },
    });

    await page.goto(`${base}${reviewUrl}`);
    await expect(page.getByTestId("present-editor-slide-preview")).toBeVisible({ timeout: 30_000 });
    writeUiEvidence({ final_state: "review_open_for_human", headed_complete: true });
  });
});
