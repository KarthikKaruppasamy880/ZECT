/**
 * S7.6 headed native LLM planner proof.
 * Login → /present → real Zinnia → Generate → editor notes → export/reopen.
 * Requires VITE_API_URL=http://127.0.0.1:8010 (zect_native) and live Model Gateway.
 */
import { test, expect } from "@playwright/test";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { gotoAuthed } from "./helpers/login";

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const ART = path.join(REPO, "test-results/s7-parity/headed-llm-native");
const BUILTINS = new Set(["modern", "general", "standard", "swift", ""]);

test.use({ video: "on", screenshot: "on", trace: "on" });
test.skip(!process.env.ZECT_LIVE_S76, "opt-in live S7.6 headed native LLM proof (ZECT_LIVE_S76=1)");

test("S7.6 headed LLM-native: Zinnia generate uses Model Gateway planner and editor round-trip", async ({
  page,
}) => {
    test.setTimeout(12 * 60_000);
    fs.mkdirSync(ART, { recursive: true });
    const generateMeta: Record<string, unknown>[] = [];
    page.on("response", async (res) => {
      if (!res.url().includes("/api/mentrix/presenton/generate")) return;
      try {
        const body = await res.json();
        const detail = body?.detail && typeof body.detail === "object" ? body.detail : body;
        generateMeta.push({
          status: res.status(),
          provider: detail?.provider,
          planner_mode: detail?.planner_mode,
          model: detail?.model,
          zinnia_verified: detail?.zinnia_verified,
          template_sent: detail?.template_sent,
          lifecycle: detail?.lifecycle,
          has_path: Boolean(detail?.path),
          path: detail?.path,
          degraded: detail?.degraded,
          fallback: detail?.fallback,
        });
      } catch {
        generateMeta.push({ status: res.status(), parse: "non-json" });
      }
    });

    await gotoAuthed(page, "/present", "zect-present-page");
    expect(page.url()).not.toMatch(/:5000\b/);
    await expect(page.getByTestId("zect-present-template-zinnia-executive-v1")).toBeVisible();
    await page.getByTestId("zect-present-template-zinnia-executive-v1").click();
    await expect(page.getByTestId("zect-present-template-preview")).toBeVisible({ timeout: 20_000 });
    await page.screenshot({ path: path.join(ART, "01-gallery-zinnia.png") });
    await page.getByTestId("zect-present-continue-generate").click();
    await expect(page.getByTestId("present-deck-panel")).toBeVisible();
    await expect(page.getByTestId("present-deck-template")).toHaveValue("zinnia-executive-v1");

    await page.getByTestId("present-deck-prompt").fill(
      "Zinnia Executive board pack: Q3 delivery status, top risks, decisions needed, and owners. Formal tone.",
    );
    const audience = page.getByTestId("present-deck-audience");
    if (await audience.isVisible().catch(() => false)) {
      await audience.selectOption("executive");
    }
    await page.getByTestId("present-deck-n-slides").fill("5");
    await page.screenshot({ path: path.join(ART, "02-prompt.png") });

    const gen = page.getByTestId("present-deck-generate");
    await expect(gen).toBeEnabled({ timeout: 90_000 });
    await page.getByTestId("present-deck-flow-b-approve").locator("input").check();
    await gen.click();
    const st = await page.getByTestId("present-deck-status").innerText().catch(() => "");
    if (/Approve generation/i.test(st)) {
      await page.getByTestId("present-deck-flow-b-approve").locator("input").check();
      await gen.click();
    }
    await expect.poll(() => generateMeta.length, { timeout: 480_000 }).toBeGreaterThan(0);
    const last = generateMeta[generateMeta.length - 1] || {};
    fs.writeFileSync(path.join(ART, "generate-meta.json"), JSON.stringify({ generateMeta, last }, null, 2));
    expect(last.status).toBe(200);
    expect(last.provider).toBe("zect_native");
    expect(last.planner_mode).toBe("LLM");
    expect(last.zinnia_verified).toBe(true);
    expect(BUILTINS.has(String(last.template_sent || "").toLowerCase())).toBeFalsy();
    expect(last.has_path).toBe(true);
    await page.screenshot({ path: path.join(ART, "03-generated.png") });

    await expect(page.getByTestId("present-editor")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("present-editor-notes")).toBeVisible({ timeout: 30_000 });
    await page.getByTestId("present-editor-notes").fill("S7.6 headed notes: confirm owners this week.");
    await page.getByTestId("present-editor-save").click();
    await expect(page.getByTestId("present-editor-status")).toContainText(/Saved|local/i, { timeout: 20_000 });
    const downloadPromise = page.waitForEvent("download", { timeout: 30_000 });
    await page.getByTestId("present-editor-export").click();
    const download = await downloadPromise;
    const outFile = path.join(ART, download.suggestedFilename() || "export.pptx");
    await download.saveAs(outFile);
    expect(fs.statSync(outFile).size).toBeGreaterThan(1000);

    const deckPath = String(last.path || "");
    if (deckPath) {
      await page.getByTestId("present-deck-path").fill("");
      await page.getByTestId("present-deck-path").fill(deckPath);
      await expect(page.getByTestId("present-editor-thumbs")).toBeVisible({ timeout: 20_000 });
      await expect(page.getByTestId("present-editor-notes")).toHaveValue(/S7.6 headed notes/i);
    }
    await page.screenshot({ path: path.join(ART, "04-editor-reopen.png") });
    fs.writeFileSync(
      path.join(ART, "evidence.json"),
      JSON.stringify(
        {
          ok: true,
          provider: last.provider,
          planner_mode: last.planner_mode,
          model: last.model,
          zinnia_verified: last.zinnia_verified,
          template_sent: last.template_sent,
          path: last.path,
          export_bytes: fs.statSync(outFile).size,
          presenton_standalone_ui_used: false,
        },
        null,
        2,
      ),
    );
  });
