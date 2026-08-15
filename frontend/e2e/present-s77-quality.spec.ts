/**
 * S7.7 headed visual + UX comparison.
 * ZECT Present (default Presenton-backed API) vs Presenton UI as a quality reference.
 * Native quality generate is opt-in against zect_native API.
 * Requires ZECT_LIVE_S77=1. Does not fill the human A/B scorecard.
 */
import { test, expect } from "@playwright/test";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { gotoAuthed } from "./helpers/login";

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const ART = path.join(REPO, "test-results/s7-parity/headed-s77");
const PRESENTON = process.env.PRESENTON_BASE_URL || "http://127.0.0.1:5000";

test.use({ video: "on", screenshot: "on", trace: "on" });
test.skip(!process.env.ZECT_LIVE_S77, "opt-in S7.7 headed quality + UX comparison (ZECT_LIVE_S77=1)");

test("S7.7 headed: ZECT Present UX vs Presenton reference (no secret extraction)", async ({
  page,
  browser,
}) => {
  test.setTimeout(6 * 60_000);
  fs.mkdirSync(ART, { recursive: true });

    await gotoAuthed(page, "/present/create", "zect-present-page");
    expect(page.url()).not.toMatch(/:5000\b/);
    await page.screenshot({ path: path.join(ART, "zect-01-gallery.png"), fullPage: true });
    await expect(page.getByTestId("zect-present-template-zinnia-executive-v1")).toBeVisible();
    await page.getByTestId("zect-present-template-zinnia-executive-v1").click();
    await expect(page.getByTestId("zect-present-template-preview")).toBeVisible({ timeout: 20_000 });
    await page.screenshot({ path: path.join(ART, "zect-02-template.png") });
    const cont = page.getByTestId("zect-present-continue-generate");
    await expect(cont).toBeVisible();
    await cont.scrollIntoViewIfNeeded();
    await cont.click();
    await expect(page.getByTestId("present-deck-panel")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("present-deck-prompt")).toBeVisible();
  await expect(page.getByTestId("present-deck-template")).toBeVisible();
    await expect(page.getByTestId("present-deck-generate")).toBeVisible();
    await expect(page.getByTestId("present-advanced-generate")).toBeVisible();
    await page.getByTestId("present-advanced-generate").locator("summary").click();
    await expect(page.getByTestId("present-deck-generate-fast-basic")).toBeVisible();
  await page.screenshot({ path: path.join(ART, "zect-03-generate-panel.png"), fullPage: true });

  const zectCaps = {
    prompt_entry: await page.getByTestId("present-deck-prompt").isVisible(),
    template_select: await page.getByTestId("present-deck-template").isVisible(),
    n_slides: await page.getByTestId("present-deck-n-slides").isVisible(),
    generate: await page.getByTestId("present-deck-generate").isVisible(),
    fast_basic: await page.getByTestId("present-deck-generate-fast-basic").isVisible(),
    path_field: await page.getByTestId("present-deck-path").isVisible(),
    notes: await page.getByTestId("present-deck-notes").isVisible(),
    export_open: await page.getByTestId("present-deck-open-pptx").isVisible(),
    narrate: await page.getByTestId("present-deck-narrate").isVisible(),
    editor: await page.getByTestId("present-editor").isVisible().catch(() => false),
  };

  const presenton = await browser.newContext({ storageState: undefined });
  const p = await presenton.newPage();
  let presentonMode: "setup" | "login" | "app" | "unreachable" = "unreachable";
  let presentonStatus = 0;
  try {
    const res = await p.goto(PRESENTON, { waitUntil: "domcontentloaded", timeout: 20_000 });
    presentonStatus = res?.status() || 0;
    const body = ((await p.locator("body").innerText().catch(() => "")) || "").toLowerCase();
    if (/setup|create admin|first[- ]run|register/.test(body)) presentonMode = "setup";
    else if (/login|sign in|password/.test(body)) presentonMode = "login";
    else if (presentonStatus >= 200 && presentonStatus < 400) presentonMode = "app";
    await p.screenshot({ path: path.join(ART, "presenton-01-entry.png"), fullPage: true });
  } catch {
    presentonMode = "unreachable";
  }
  await presenton.close();

  const comparison = {
    presenton_url: PRESENTON,
    presenton_http_status: presentonStatus,
    presenton_mode: presentonMode,
    zect_present_url: page.url(),
    zect_capabilities: zectCaps,
    note: "Do not copy Presenton branding. Credentials are never written to this file.",
  };
  fs.writeFileSync(path.join(ART, "ux-comparison.json"), JSON.stringify(comparison, null, 2));
  expect(zectCaps.prompt_entry).toBe(true);
  expect(zectCaps.generate).toBe(true);
});

test("S7.7 headed native quality generate when API is zect_native", async ({ page }) => {
  test.setTimeout(12 * 60_000);
  const nativeOrigin = (process.env.ZECT_NATIVE_API_URL || "http://127.0.0.1:8010").replace(/\/$/, "");
  test.skip(
    !process.env.ZECT_NATIVE_HEADED && !/8010/.test(process.env.VITE_API_URL || process.env.PLAYWRIGHT_API_URL || ""),
    "native headed generate expects ZECT_NATIVE_HEADED=1 or VITE_API_URL on :8010",
  );
  fs.mkdirSync(ART, { recursive: true });
  const generateMeta: Record<string, unknown>[] = [];
  const presentonGenerateHits: string[] = [];
  page.on("request", (req) => {
    const url = req.url();
    if (/:5000\b/.test(url) && /\/ppt\/|\/generate/.test(url)) presentonGenerateHits.push(url);
  });
  await page.addInitScript((origin) => {
    sessionStorage.setItem("zect_api_origin", origin);
  }, nativeOrigin);
  page.on("response", async (res) => {
    if (!res.url().includes("/api/mentrix/presenton/generate")) return;
    try {
      const body = await res.json();
      const detail = body?.detail && typeof body.detail === "object" ? body.detail : body;
      generateMeta.push({
        status: res.status(),
        url: res.url(),
        provider: detail?.provider,
        planner_mode: detail?.planner_mode,
        zinnia_verified: detail?.zinnia_verified,
        final_quality_status: detail?.final_quality_status || detail?.quality?.final_quality_status,
        overlap_count: detail?.overlap_count,
        repair_attempts: detail?.repair_attempts,
        ungrounded_fact_count: detail?.ungrounded_fact_count,
        error: detail?.error,
      });
    } catch {
      generateMeta.push({ status: res.status(), parse: "non-json" });
    }
  });
    await gotoAuthed(page, "/present/create", "zect-present-page");
  const card = page.getByTestId("zect-present-template-zinnia-executive-v1");
  await expect(card).toBeVisible();
  await card.click();
  const cont = page.getByTestId("zect-present-continue-generate");
  await expect(cont).toBeVisible();
  await cont.scrollIntoViewIfNeeded();
  await cont.click();
  await page.getByTestId("present-deck-prompt").fill(
    "Executive update: Q3 delivery status, top risks, and decisions. Do not invent owners or dates.",
  );
  await page.getByTestId("present-deck-n-slides").fill("5");
  const gen = page.getByTestId("present-deck-generate");
  await expect(gen).toBeEnabled({ timeout: 90_000 });
  const approve = page.getByTestId("present-deck-flow-b-approve").locator("input");
  if (await approve.isVisible().catch(() => false)) await approve.check();
  await gen.click();
  await expect.poll(() => generateMeta.length, { timeout: 480_000 }).toBeGreaterThan(0);
  fs.writeFileSync(
    path.join(ART, "native-generate-meta.json"),
    JSON.stringify({ generateMeta, presentonGenerateHits }, null, 2),
  );
  const last = generateMeta[generateMeta.length - 1] || {};
  expect(String(last.url || "")).toContain("8010");
  expect(last.provider).toBe("zect_native");
  expect(last.planner_mode).toBe("LLM");
  expect(last.zinnia_verified).toBe(true);
  expect(last.final_quality_status).toBe("PASS");
  expect(presentonGenerateHits).toEqual([]);
  await expect(page.getByTestId("present-review")).toBeVisible();
  await expect(page.getByTestId("present-editor")).toBeVisible();
  await page.screenshot({ path: path.join(ART, "native-generated.png"), fullPage: true });
});
