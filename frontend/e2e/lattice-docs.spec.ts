import { test, expect } from "@playwright/test";

test.describe("Lattice docs graph", () => {
  test("layer toggles and force graph render", async ({ page }) => {
    await page.goto("/lattice?layer=docs");
    await expect(page.getByTestId("lattice-page")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("lattice-layer-docs")).toBeVisible();
    await expect(page.getByTestId("lattice-layer-combined")).toBeVisible();
  });
});
