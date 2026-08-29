import { test, expect } from "@playwright/test";

const VIEWPORTS = [
  { width: 1280, height: 720 },
  { width: 1366, height: 768 },
  { width: 1440, height: 900 },
  { width: 1920, height: 1080 },
];

test.describe("Developer split layout", () => {
  for (const vp of VIEWPORTS) {
    test(`hide/restore panes at ${vp.width}x${vp.height}`, async ({ page }) => {
      await page.setViewportSize(vp);
      await page.goto("/workspace");
      await expect(page.getByRole("heading", { name: /Developer Workspace/i })).toBeVisible({ timeout: 30_000 });
      await page.getByTestId("workspace-toggle-explorer").click();
      await page.getByTestId("workspace-toggle-explorer").click();
      await page.getByTestId("workspace-toggle-agent").click();
      await page.getByTestId("workspace-toggle-agent").click();
      await page.getByTestId("workspace-toggle-bottom").click();
      await page.getByTestId("workspace-toggle-bottom").click();
      await expect(page.getByTestId("workspace-toggle-agent")).toBeVisible();
    });
  }
});
