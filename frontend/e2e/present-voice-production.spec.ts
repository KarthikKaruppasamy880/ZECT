/**
 * Present + Voice production surface (headed).
 * Dashboard → Create AI / Blank / Import → templates → Quality/Fast controls →
 * Review/Export gate → Rehearse voice none/stock → Companion clone panel.
 * Does not click live Generate unless the provider button is enabled; then it
 * still does not wait for a finished deck (live Quality remains BLOCKED_EXTERNAL
 * / opt-in present-p0-headed). Skip ≠ PASS.
 */
import { test, expect } from "@playwright/test";
import { execFileSync } from "child_process";
import fs from "fs";
import os from "os";
import path from "path";
import { fileURLToPath } from "url";
import { gotoAuthed } from "./helpers/login";
import { runPythonScript } from "./helpers/python";

const FRONTEND = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const REPO = path.resolve(FRONTEND, "..");
const ART = path.join(REPO, "test-results", "present-voice-production");
const API = process.env.VITE_API_URL || process.env.ZECT_API_URL || "http://127.0.0.1:8000";

function encodeDeckId(p: string) {
  return Buffer.from(p, "utf8").toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function pythonBin(): string | null {
  const override = (process.env.ZECT_PYTHON || "").trim();
  if (override) return override;
  const venv = path.join(REPO, "backend", ".venv", "Scripts", "python.exe");
  if (fs.existsSync(venv)) return venv;
  const posix = path.join(REPO, "backend", ".venv", "bin", "python");
  if (fs.existsSync(posix)) return posix;
  return null;
}

function writeOverlapPptx(dest: string) {
  const script = path.join(FRONTEND, "e2e", "fixtures", "make_overlap_pptx.py");
  const bin = pythonBin();
  const args = [script, dest];
  if (bin) {
    try {
      execFileSync(bin, args, { stdio: "pipe" });
      if (fs.existsSync(dest)) return;
    } catch {
      /* venv may lack python-pptx — fall through to PATH python */
    }
  }
  runPythonScript(script, [dest]);
}

test.describe("present + voice production", () => {
  test.setTimeout(180_000);

  test("lifecycle: dashboard, create, blank, import, export gate, voice", async ({ page }) => {
    fs.mkdirSync(ART, { recursive: true });
    const evidence: Record<string, unknown> = {
      generate_clicked: false,
      presenton_generate_enabled: false,
      voicebox_online: null as boolean | null,
      hard_block_ui: false,
      powerpoint_com: "not_run",
    };

    await gotoAuthed(page, "/present", "present-dashboard");
    await expect(page.getByTestId("present-create-with-ai")).toBeVisible();
    await expect(page.getByTestId("present-blank")).toBeVisible();
    await expect(page.getByTestId("present-import")).toBeVisible();
    await expect(page.getByTestId("zect-present-gallery")).toBeVisible();
    await expect(page.getByTestId("zect-present-template-zinnia-executive-v1")).toBeVisible();
    await page.screenshot({ path: path.join(ART, "01-dashboard.png") });

    await page.getByTestId("present-create-with-ai").click();
    await expect(page.getByTestId("zect-present-workspace")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId("present-lifecycle-state")).toBeVisible();
    const lifecycle = (await page.getByTestId("present-lifecycle-state").innerText()).trim();
    evidence.lifecycle = lifecycle;
    await page.getByTestId("zect-present-template-zinnia-executive-v1").click();
    await expect(page.getByTestId("zect-present-template-preview")).toBeVisible();
    await page.getByTestId("zect-present-continue-generate").click();
    await expect(page.getByTestId("present-deck-panel")).toBeVisible();
    await expect(page.getByTestId("present-deck-generate")).toBeVisible();
    await page.locator('[data-testid="present-advanced-generate"]').evaluate((el: HTMLDetailsElement) => {
      el.open = true;
    });
    await expect(page.getByTestId("present-deck-generate-fast-basic")).toBeVisible();
    const genEnabled = await page.getByTestId("present-deck-generate").isEnabled();
    evidence.presenton_generate_enabled = genEnabled;
    if (!genEnabled) {
      evidence.generate_blocked_external = true;
    }
    await page.screenshot({ path: path.join(ART, "02-create-quality-fast.png") });

    await page.getByTestId("present-nav-dashboard").click();
    await expect(page.getByTestId("present-dashboard")).toBeVisible();
    await page.getByTestId("present-blank").click();
    await expect(page.getByTestId("present-studio")).toBeVisible({ timeout: 25_000 });
    await expect(page.getByTestId("present-editor")).toBeVisible();
    await expect(page.getByTestId("present-editor-thumbs")).toBeVisible();
    await page.getByTestId("present-editor-notes-toggle").click();
    await page.getByTestId("present-editor-notes").fill("Executive note: owners needed this week.");
    await page.getByTestId("present-editor-save").click();
    await expect(page.getByTestId("present-editor-status")).toContainText(/Saved|local|ooxml/i, { timeout: 15_000 });
    await page.getByTestId("present-open-export").click();
    await expect(page.getByTestId("present-export")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("present-export-gate")).toBeVisible();
    const blankHard = await page.getByTestId("present-export-hard-block").isVisible().catch(() => false);
    evidence.blank_hard_blocked = blankHard;
    expect(blankHard, "blank deck must not be critically export-blocked").toBeFalsy();
    if (!blankHard) {
      const warn = page.getByTestId("present-export-accept-warnings");
      if (await warn.isVisible().catch(() => false)) {
        await warn.locator("input").check();
      }
      const exportBtn = page.getByTestId("present-export-pptx");
      if (await exportBtn.isEnabled()) {
        const downloadPromise = page.waitForEvent("download", { timeout: 20_000 });
        await exportBtn.click();
        const download = await downloadPromise;
        const outFile = path.join(ART, download.suggestedFilename() || "blank-export.pptx");
        await download.saveAs(outFile);
        evidence.blank_export_bytes = fs.statSync(outFile).size;
        expect(fs.statSync(outFile).size).toBeGreaterThan(100);
      }
    }
    await page.screenshot({ path: path.join(ART, "03-blank-export.png") });

    const token = await page.evaluate(() => localStorage.getItem("zect_token"));
    const blankApi = await page.request.post(`${API}/api/mentrix/present/blank`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    expect(blankApi.ok()).toBeTruthy();
    const blankJson = await blankApi.json();
    const importBytes = fs.readFileSync(String(blankJson.path));
    await page.goto("/present/import");
    await expect(page.getByTestId("present-import-page")).toBeVisible();
    await page.getByTestId("present-import-file").setInputFiles({
      name: "imported-prod.pptx",
      mimeType: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
      buffer: importBytes,
    });
    await expect(page.getByTestId("present-studio")).toBeVisible({ timeout: 25_000 });
    await page.getByTestId("present-open-rehearse").click();
    await expect(page.getByTestId("present-rehearse")).toBeVisible();
    const voice = page.getByTestId("present-deck-voice-select");
    await expect(voice).toBeVisible();
    await expect(voice.locator('option[value="none"]')).toHaveCount(1);
    expect(await voice.locator('option[value^="stock:"]').count()).toBeGreaterThan(0);
    await voice.selectOption("none");
    await page.screenshot({ path: path.join(ART, "04-rehearse-voice.png") });

    const dest = path.join(os.homedir(), "Documents", "zect-present-hardblock.pptx");
    writeOverlapPptx(dest);
    expect(fs.existsSync(dest)).toBeTruthy();
    await page.goto(`/present/d/${encodeDeckId(dest)}/export`);
    await expect(page.getByTestId("present-export")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId("present-export-gate")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId("present-export-hard-block")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByTestId("present-export-pptx")).toBeDisabled();
    evidence.hard_block_ui = true;
    await page.screenshot({ path: path.join(ART, "05-hard-block.png") });

    await page.getByRole("link", { name: "Mentrix Companion" }).first().click();
    await expect(page.getByTestId("mentrix-companion-page")).toBeVisible({ timeout: 30_000 });
    await page.getByTestId("mentrix-mode-voice").click();
    await expect(page.getByTestId("mentrix-voice-section")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId("clone-voice-panel")).toBeVisible();
    const engine = page.getByTestId("clone-voice-engine-status");
    if (await engine.isVisible().catch(() => false)) {
      await expect(engine).not.toContainText(/checking/i, { timeout: 20_000 });
      const txt = (await engine.innerText()).toLowerCase();
      evidence.voicebox_status_text = txt;
      evidence.voicebox_online = /\bonline\b|\bready\b/.test(txt) && !/offline|start /.test(txt);
    }
    const testSpeak = page.getByTestId("clone-voice-test-speak");
    if (await testSpeak.isVisible().catch(() => false)) {
      evidence.clone_test_speak_enabled = await testSpeak.isEnabled();
    }
    await page.screenshot({ path: path.join(ART, "06-companion-voice.png") });

    fs.writeFileSync(path.join(ART, "evidence.json"), JSON.stringify(evidence, null, 2));
  });
});
