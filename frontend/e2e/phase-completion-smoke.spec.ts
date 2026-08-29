/**
 * Playwright smoke: navigate core Phase 10/11 surfaces with soft healing retries.
 */
import { test, expect, type Page } from "@playwright/test";

async function gotoWithHeal(page: Page, path: string) {
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      await page.goto(path, { waitUntil: "domcontentloaded", timeout: 20000 });
      return;
    } catch {
      await page.waitForTimeout(800 * (attempt + 1));
    }
  }
  await page.goto(path, { waitUntil: "domcontentloaded" });
}

test.describe("ZECT phase completion smoke", () => {
  test("Architecture guide loads (no competitor matrix)", async ({ page }) => {
    await gotoWithHeal(page, "/tool-comparison");
    await expect(page.getByTestId("architecture-guide")).toBeVisible({ timeout: 20000 });
    await expect(page.getByRole("heading", { name: "Architecture" })).toBeVisible();
    await expect(page.getByText(/Comparison matrix/i)).toHaveCount(0);
  });

  test("memory and security nav surfaces", async ({ page }) => {
    await gotoWithHeal(page, "/memory");
    await expect(page.locator("body")).toContainText(/Memory|Working|Episodic|typed|ZECT/i, {
      timeout: 20000,
    });
    await gotoWithHeal(page, "/security-incidents");
    await expect(page.locator("body")).toContainText(/Security|Finding|Incident|Scan/i, {
      timeout: 20000,
    });
  });

  test("settings telemetry consent control", async ({ page }) => {
    await gotoWithHeal(page, "/settings");
    await expect(page.getByTestId("telemetry-consent")).toBeVisible({ timeout: 20000 });
  });
});
