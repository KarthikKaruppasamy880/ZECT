import { test, expect } from "@playwright/test";

/**
 * Labs pages previously called APIs without Bearer and showed 401 toasts.
 * Authenticated setup (auth.setup.ts) must yield successful loads.
 */
test.describe("Labs auth", () => {
  test("Memory System loads without 401 toast", async ({ page }) => {
    await page.goto("/memory");
    await expect(page.getByRole("heading", { name: /Memory System/i })).toBeVisible({
      timeout: 20_000,
    });
    await page.waitForTimeout(1500);
    await expect(page.getByText(/Failed to load.*\(401\)|Unauthorized/i)).toHaveCount(0);
  });

  test("Skills Engine loads with auth", async ({ page }) => {
    await page.goto("/skills-engine");
    await expect(page.getByRole("heading", { name: /Skills Engine/i })).toBeVisible({
      timeout: 20_000,
    });
    await page.waitForTimeout(1500);
    await expect(page.getByText(/Failed to load.*\(401\)|Unauthorized/i)).toHaveCount(0);
  });

  test("Dream Engine page loads", async ({ page }) => {
    await page.goto("/dream-engine");
    await expect(page.getByRole("heading", { name: /Dream Engine/i })).toBeVisible({
      timeout: 20_000,
    });
    await page.waitForTimeout(1500);
    await expect(page.getByText(/Failed to load.*\(401\)|\(401\)/)).toHaveCount(0);
  });
});
