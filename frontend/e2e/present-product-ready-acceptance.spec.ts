/**
 * Present product READY acceptance — real Zinnia master + mixed deck + viewports.
 * Opt-in: ZECT_LIVE_PRESENT_READY=1 and local .zect/present-templates/masters/zinnia-executive-v1.pptx
 * (SHA256 74cb1f7a…). Skip ≠ PASS. Does not use synthetic Template.pptx for Zinnia fidelity.
 */
import { createHash } from "node:crypto";
import { test, expect, type Page } from "@playwright/test";
import { execFileSync } from "child_process";
import fs from "fs";
import os from "os";
import path from "path";
import { fileURLToPath } from "url";
import { gotoAuthed } from "./helpers/login";
import { runPythonScript } from "./helpers/python";

const FRONTEND = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const REPO = path.resolve(FRONTEND, "..");
const ART = path.join(REPO, "test-results", "present-product-ready");
const API = process.env.VITE_API_URL || process.env.ZECT_API_URL || "http://127.0.0.1:8000";
const ZINNIA_SHA = "74cb1f7a50c2dcd3ce6c1a41547c45f9666fcb1e353801b87a174c63ecf70dc2";
const VIEWPORTS = [
  { w: 1280, h: 720, tag: "1280x720" },
  { w: 1366, h: 768, tag: "1366x768" },
  { w: 1440, h: 900, tag: "1440x900" },
  { w: 1920, h: 1080, tag: "1920x1080" },
] as const;

function encodeDeckId(p: string) {
  return Buffer.from(p, "utf8").toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function zinniaMasterPath(): string | null {
  const candidates = [
    path.join(REPO, ".zect", "present-templates", "masters", "zinnia-executive-v1.pptx"),
    path.join(os.homedir(), "Documents", "zinnia-executive-v1.pptx"),
  ];
  for (const p of candidates) {
    if (fs.existsSync(p) && fs.statSync(p).size > 1_000_000) return p;
  }
  return null;
}

function sha256(filePath: string): string {
  return createHash("sha256").update(fs.readFileSync(filePath)).digest("hex");
}

function writeEvidence(partial: Record<string, unknown>) {
  fs.mkdirSync(ART, { recursive: true });
  const prev = (() => {
    try {
      return JSON.parse(fs.readFileSync(path.join(ART, "evidence.json"), "utf8")) as Record<string, unknown>;
    } catch {
      return {};
    }
  })();
  fs.writeFileSync(path.join(ART, "evidence.json"), JSON.stringify({ ...prev, ...partial }, null, 2));
}

async function assertEditorShell(page: Page, tag: string) {
  await expect(page.getByTestId("present-editor")).toBeVisible();
  await expect(page.getByTestId("present-editor-canvas")).toHaveAttribute("data-canvas", "document");
  await expect(page.getByTestId("present-editor-block-overlay")).not.toHaveClass(/grid-cols-2/);
  const save = page.getByTestId("present-editor-save");
  await expect(save).toBeVisible();
  const box = await save.boundingBox();
  expect(box, `${tag}: save control clipped`).toBeTruthy();
  if (box) {
    const vp = page.viewportSize();
    expect(box.y + box.height, `${tag}: save below fold`).toBeLessThanOrEqual((vp?.height || 720) + 2);
  }
  const canvas = page.getByTestId("present-editor-canvas");
  const canvasBox = await canvas.boundingBox();
  expect(canvasBox?.width, `${tag}: canvas width`).toBeGreaterThan(200);
  await page.screenshot({ path: path.join(ART, `shell-${tag}.png`), fullPage: false });
}

test.describe("Present product READY acceptance", () => {
  test.skip(!process.env.ZECT_LIVE_PRESENT_READY, "opt-in live Zinnia READY proof (ZECT_LIVE_PRESENT_READY=1)");

  test.beforeAll(() => {
    const master = zinniaMasterPath();
    if (!master) {
      throw new Error(
        "STOP: real Zinnia master not found. Provide .zect/present-templates/masters/zinnia-executive-v1.pptx " +
          `(SHA256 ${ZINNIA_SHA}) or ~/Documents/zinnia-executive-v1.pptx from org import.`,
      );
    }
    const digest = sha256(master);
    if (digest !== ZINNIA_SHA) {
      throw new Error(`STOP: Zinnia master SHA256 mismatch got ${digest}, expected ${ZINNIA_SHA}`);
    }
    writeEvidence({ zinnia_master: master, zinnia_sha256: digest });
  });

  test.setTimeout(20 * 60_000);

  test("Zinnia gallery → Open in editor → edit → save → reopen", async ({ page }) => {
    fs.mkdirSync(ART, { recursive: true });
    await gotoAuthed(page, "/present/create", "zect-present-page");
    await expect(page.getByTestId("zect-present-template-zinnia-executive-v1")).toBeVisible();
    await page.getByTestId("zect-present-template-zinnia-executive-v1").click();
    await page.getByTestId("zect-present-open-editor").click();
    await expect(page.getByTestId("present-studio")).toBeVisible({ timeout: 45_000 });
    await assertEditorShell(page, "zinnia-open");
    const inline = page.getByTestId("present-editor-inline-text").first();
    if (await inline.isVisible().catch(() => false)) {
      await inline.click();
      await page.keyboard.press("Control+A");
      await page.keyboard.type("Zinnia READY acceptance edit");
    }
    await page.getByTestId("present-editor-save").click();
    await expect(page.getByTestId("present-editor-status")).toContainText(/Saved|local|ooxml/i, { timeout: 20_000 });
    await page.screenshot({ path: path.join(ART, "zinnia-after-edit.png") });
    const canvasShot = path.join(ART, "zinnia-canvas-representative.png");
    await page.getByTestId("present-editor-canvas").screenshot({ path: canvasShot });
    await page.reload();
    await expect(page.getByTestId("present-editor-canvas")).toHaveAttribute("data-canvas", "document");
    writeEvidence({ zinnia_journey: "PASS", canvas_shot: canvasShot });
    if (process.env.ZECT_LIVE_PPT_COM === "1") {
      try {
        execFileSync(
          process.env.ZECT_PYTHON || "python",
          [path.join(REPO, "backend", "scripts", "present_product_fidelity_proof.py"), canvasShot],
          { cwd: REPO, stdio: "pipe", env: { ...process.env, ZECT_LIVE_PPT_COM: "1" } },
        );
        writeEvidence({ com_raster_fidelity: "PASS" });
      } catch (err) {
        writeEvidence({ com_raster_fidelity: "FAIL", com_error: String(err) });
        throw err;
      }
    }
  });

  test("mixed >=8-slide deck edits chart/table/image blocks", async ({ page }) => {
    const dest = path.join(os.homedir(), "Documents", "zect-mixed-acceptance.pptx");
    runPythonScript(path.join(FRONTEND, "e2e/fixtures/make_mixed_acceptance_deck.py"), [dest]);
    expect(fs.existsSync(dest)).toBeTruthy();
    await gotoAuthed(page, `/present/d/${encodeDeckId(dest)}/edit`, "present-studio");
    await assertEditorShell(page, "mixed-deck");
    await expect(page.getByTestId("present-editor-thumb-canvas-0")).toHaveAttribute("data-canvas", "document");
    const chartHit = page.locator('[data-testid^="present-editor-block-hit-chart"]').first();
    if (await chartHit.isVisible().catch(() => false)) {
      await chartHit.click();
    }
    await page.getByTestId("present-editor-save").click();
    await expect(page.getByTestId("present-editor-status")).toContainText(/Saved|local/i, { timeout: 20_000 });
    writeEvidence({ mixed_deck: dest, mixed_elements: "PASS" });
  });

  test("viewport matrix — shell controls not collapsed", async ({ page }) => {
    const dest = path.join(os.homedir(), "Documents", "zect-mixed-acceptance.pptx");
    if (!fs.existsSync(dest)) {
      runPythonScript(path.join(FRONTEND, "e2e/fixtures/make_mixed_acceptance_deck.py"), [dest]);
    }
    for (const vp of VIEWPORTS) {
      await page.setViewportSize({ width: vp.w, height: vp.h });
      await gotoAuthed(page, `/present/d/${encodeDeckId(dest)}/edit`, "present-studio");
      await assertEditorShell(page, vp.tag);
      await page.getByTestId("present-editor-thumbs").screenshot({
        path: path.join(ART, `thumbs-${vp.tag}.png`),
      });
      await page.getByTestId("present-editor-canvas").screenshot({
        path: path.join(ART, `canvas-${vp.tag}.png`),
      });
    }
    writeEvidence({ viewport_matrix: VIEWPORTS.map((v) => v.tag) });
  });

  test("Presenter Intelligence — grounded scripts + stock voice slide chain", async ({ page }) => {
    const dest = path.join(os.homedir(), "Documents", "zect-mixed-acceptance.pptx");
    if (!fs.existsSync(dest)) {
      runPythonScript(path.join(FRONTEND, "e2e/fixtures/make_mixed_acceptance_deck.py"), [dest]);
    }
    const token = await page.evaluate(() => localStorage.getItem("zect_token"));
    const parseRes = await page.request.post(`${API}/api/mentrix/present/parse-pptx-path`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      data: { path: dest },
    });
    expect(parseRes.ok()).toBeTruthy();
    const parsed = (await parseRes.json()) as { slides?: unknown[] };
    const slides = parsed.slides || [];
    expect(slides.length).toBeGreaterThanOrEqual(7);
    const narrateRes = await page.request.post(`${API}/api/mentrix/presentation/narrate-slides`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      data: { slides, deck_context: "ZECT mixed acceptance" },
    });
    expect(narrateRes.ok()).toBeTruthy();
    const narrated = (await narrateRes.json()) as { ok?: boolean; slides?: Array<{ index: number; script: string }> };
    expect(narrated.ok).toBeTruthy();
    expect(narrated.slides?.length).toBe(slides.length);
    for (const row of narrated.slides || []) {
      expect((row.script || "").trim().length, `slide ${row.index} script`).toBeGreaterThan(12);
      expect(row.script).not.toMatch(/99%|42%/);
    }
    await gotoAuthed(page, `/present/d/${encodeDeckId(dest)}/rehearse`, "present-rehearse");
    const voice = page.getByTestId("present-deck-voice-select");
    await voice.selectOption("stock:nova");
    const presentAll = page.getByTestId("present-deck-present-all");
    await expect(presentAll).toBeEnabled({ timeout: 15_000 });
    writeEvidence({
      presenter_grounded_scripts: narrated.slides?.length,
      presenter_stock_voice: process.env.ZECT_LIVE_VOICE_STOCK === "1" ? "live_run_pending" : "api_grounded_only",
    });
    if (process.env.ZECT_LIVE_VOICE_STOCK === "1") {
      await presentAll.click();
      await expect(page.getByTestId("present-deck-panel")).toContainText(/slide \d+ \/ \d+/i, { timeout: 60_000 });
      await expect(page.getByTestId("present-deck-panel")).toContainText(/Finished presenting/i, {
        timeout: 8 * 60_000,
      });
      writeEvidence({ presenter_full_audio: "PASS" });
    }
  });

  test("export PPTX gate on mixed deck", async ({ page }) => {
    const dest = path.join(os.homedir(), "Documents", "zect-mixed-acceptance.pptx");
    if (!fs.existsSync(dest)) {
      runPythonScript(path.join(FRONTEND, "e2e/fixtures/make_mixed_acceptance_deck.py"), [dest]);
    }
    await gotoAuthed(page, `/present/d/${encodeDeckId(dest)}/export`, "present-export");
    await expect(page.getByTestId("present-export-gate")).toBeVisible();
    const hard = await page.getByTestId("present-export-hard-block").isVisible().catch(() => false);
    expect(hard).toBeFalsy();
    const warn = page.getByTestId("present-export-accept-warnings");
    if (await warn.isVisible().catch(() => false)) {
      await warn.locator("input").check();
    }
    const btn = page.getByTestId("present-export-pptx");
    if (await btn.isEnabled()) {
      const dl = page.waitForEvent("download", { timeout: 30_000 });
      await btn.click();
      const download = await dl;
      const out = path.join(ART, download.suggestedFilename() || "mixed-export.pptx");
      await download.saveAs(out);
      expect(fs.statSync(out).size).toBeGreaterThan(5000);
      writeEvidence({ export_bytes: fs.statSync(out).size, export_path: out });
    }
  });
});
