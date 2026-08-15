/**
 * P0 headed: Dashboard → Create → Generate → Review → Export (Quality then Fast).
 * Requires running Vite + native API. Opt-in: ZECT_LIVE_P0=1.
 */
import { test, expect, type Page } from "@playwright/test";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { gotoAuthed } from "./helpers/login";

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const ART = path.join(REPO, "test-results/present-p0-headed");
const API = process.env.VITE_API_URL || process.env.ZECT_API_URL || "http://127.0.0.1:8010";

test.use({ video: "on", screenshot: "on" });
test.skip(!process.env.ZECT_LIVE_P0, "opt-in P0 headed (ZECT_LIVE_P0=1)");

async function generateAndExport(page: Page, opts: { fast: boolean; shotPrefix: string }) {
  const { fast, shotPrefix } = opts;
  fs.mkdirSync(ART, { recursive: true });
  fs.writeFileSync(path.join(ART, `${shotPrefix}-started.txt`), new Date().toISOString());
  await gotoAuthed(page, "/present", "present-dashboard");
  await page.screenshot({ path: path.join(ART, `${shotPrefix}-01-dashboard.png`), timeout: 15_000 });
  const click = (id: string) => page.getByTestId(id).click({ force: true, timeout: 20_000 });
  await click("present-create-with-ai");
  await expect(page.getByTestId("zect-present-page")).toBeVisible();
  await expect(page.getByTestId("zect-present-workspace")).toBeVisible({ timeout: 20_000 });
  await click("zect-present-template-zinnia-executive-v1");
  const cont = page.getByTestId("zect-present-continue-generate");
  await expect(cont).toBeVisible({ timeout: 20_000 });
  await cont.scrollIntoViewIfNeeded();
  await cont.click({ force: true, timeout: 20_000 });
  await expect(page.getByTestId("present-deck-panel")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByTestId("present-deck-generate")).toBeVisible({ timeout: 20_000 });
  await page.getByTestId("present-deck-prompt").fill(
    "Zinnia executive brief: Q3 delivery status, top risks, and decisions needed. Do not invent owners or dates.",
  );
  await page.getByTestId("present-deck-n-slides").fill("4");
  const approve = page.getByTestId("present-deck-flow-b-approve").locator("input");
  if (await approve.isVisible().catch(() => false)) await approve.check();
  const generateWait = page.waitForResponse(
    (r) => r.url().includes("/api/mentrix/presenton/generate") && r.request().method() === "POST",
    { timeout: 600_000 },
  );
  const clickGenerate = async () => {
    if (fast) {
      await page.getByTestId("present-deck-generate-fast-basic").click({ force: true });
    } else {
      await page.getByTestId("present-deck-generate").click();
    }
  };
  if (fast) {
    await page.locator('[data-testid="present-advanced-generate"]').evaluate(
      (el: HTMLDetailsElement) => {
        el.open = true;
      },
      undefined,
      { timeout: 20_000 },
    );
    await expect(page.getByTestId("present-deck-generate-fast-basic")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId("present-deck-generate-fast-basic")).toBeEnabled({ timeout: 90_000 });
  } else {
    await expect(page.getByTestId("present-deck-generate")).toBeEnabled({ timeout: 90_000 });
  }
  await clickGenerate();
  const bounced = page.getByText(/click Generate again/i);
  const first = await Promise.race([
    generateWait.then((r) => ({ kind: "gen" as const, r })),
    bounced.waitFor({ state: "visible", timeout: 600_000 }).then(() => ({ kind: "bounce" as const })),
  ]);
  let genRes = first.kind === "gen" ? first.r : undefined;
  if (first.kind === "bounce") {
    await approve.check();
    await clickGenerate();
    genRes = await generateWait;
  }
  expect(genRes, "generate response missing").toBeTruthy();
  if (!genRes!.ok()) {
    const body = await genRes!.text();
    throw new Error(`generate HTTP ${genRes!.status()} ${body.slice(0, 800)}`);
  }
  await expect(page).toHaveURL(/\/present\/d\//, { timeout: 60_000 });
  await expect(page.getByTestId("present-review")).toBeVisible();
  await expect(page.getByTestId("present-editor")).toBeVisible({ timeout: 30_000 });
  await page.screenshot({ path: path.join(ART, `${shotPrefix}-02-review.png`), timeout: 15_000 });
  await page.getByTestId("present-open-export").click();
  await expect(page.getByTestId("present-export")).toBeVisible();
  await expect(page.getByTestId("present-export-gate")).toBeVisible({ timeout: 30_000 });
  await page.screenshot({ path: path.join(ART, `${shotPrefix}-03-export.png`), timeout: 15_000 });
  const hard = page.getByTestId("present-export-hard-block");
  const blocked = await hard.isVisible().catch(() => false);
  if (blocked) {
    await expect(page.getByTestId("present-export-pptx")).toBeDisabled();
    await expect(page.getByTestId("present-export-accept-warnings")).toHaveCount(0);
    return { blocked: true };
  }
  const accept = page.getByTestId("present-export-accept-warnings");
  if (await accept.isVisible().catch(() => false)) {
    await accept.locator("input").check();
  }
  const downloadPromise = page.waitForEvent("download", { timeout: 30_000 });
  await page.getByTestId("present-export-pptx").click();
  const download = await downloadPromise;
  const outFile = path.join(ART, download.suggestedFilename() || `${shotPrefix}.pptx`);
  await download.saveAs(outFile);
  expect(fs.statSync(outFile).size).toBeGreaterThan(1000);
  return { blocked: false, outFile };
}

async function assertProjectsHygiene(page: Page) {
  const token = await page.evaluate(() => localStorage.getItem("zect_token"));
  expect(token).toBeTruthy();
  const listed = await page.request.get(`${API}/api/projects?exclude_fixtures=1`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(listed.ok()).toBeTruthy();
  const rows = (await listed.json()) as Array<{ name?: string; provenance?: string }>;
  const names = rows.map((r) => String(r.name || ""));
  expect(names.some((n) => /e2e|onboard|fixture|playwright/i.test(n))).toBeFalsy();
  const audit = await page.request.get(`${API}/api/projects/fixtures/audit`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(audit.ok()).toBeTruthy();
  const body = await audit.json();
  expect(body.proven_test || []).toEqual([]);
}

test.describe("P0 Present headed generate/export", () => {
  test("Dashboard → Create → Quality → Review → Export", async ({ page }) => {
    test.setTimeout(15 * 60_000);
    fs.mkdirSync(ART, { recursive: true });
    const r = await generateAndExport(page, { fast: false, shotPrefix: "quality" });
    expect(r.blocked).toBeFalsy();
    await assertProjectsHygiene(page);
  });

  test("Dashboard → Create → Fast → Review → Export", async ({ page }) => {
    test.setTimeout(15 * 60_000);
    fs.mkdirSync(ART, { recursive: true });
    const r = await generateAndExport(page, { fast: true, shotPrefix: "fast" });
    expect(r.blocked).toBeFalsy();
    await assertProjectsHygiene(page);
  });

  test("Developer layout: Context Used tab + Lattice states", async ({ page }) => {
    test.setTimeout(120_000);
    fs.mkdirSync(ART, { recursive: true });
    await gotoAuthed(page, "/workspace", "developer-workspace");
    await expect(page.getByTestId("workspace-toggle-context")).toBeVisible();
    await expect(page.getByTestId("workspace-context-used")).toHaveCount(0);
    await page.getByTestId("workspace-toggle-context").click();
    await expect(page.getByTestId("workspace-context-used")).toBeVisible();
    await expect(page.getByTestId("context-used-lattice")).toBeVisible();
    await expect(page.getByTestId("context-used-lattice")).toContainText(
      /state=(NOT_CONFIGURED|NOT_INDEXED|INDEXING|READY|STALE|ERROR|NOT_APPLICABLE)/,
    );
    await page.screenshot({ path: path.join(ART, "workspace-layout.png"), timeout: 15_000 });
    const header = page.getByTestId("workspace-lattice-status");
    if (await header.isVisible().catch(() => false)) {
      const state = await header.getAttribute("data-lattice-state");
      expect(state).toMatch(/^(NOT_CONFIGURED|NOT_INDEXED|INDEXING|READY|STALE|ERROR|NOT_APPLICABLE)$/);
      await expect(header).toContainText(`Lattice ${state}`);
      await expect(page.getByTestId("context-used-lattice")).toContainText(`state=${state}`);
    }
  });
});
