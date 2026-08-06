/**
 * Smoke: Agent Workspace Ask → Plan → Build shell loads (not a blank page).
 */
import { test, expect } from "@playwright/test";

test.describe("Agent Workspace phases", () => {
  test("Ask / Plan / Build routes render shell content", async ({ page }) => {
    await page.goto("/ask", { waitUntil: "domcontentloaded" });
    await expect(page.getByTestId("agent-workspace")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("agent-workspace-step-plan")).toBeVisible();

    await page.getByTestId("agent-workspace-step-plan").click();
    await expect(page).toHaveURL(/\/plan/);
    await expect(page.getByText(/Plan Mode/i).first()).toBeVisible({ timeout: 20_000 });

    await page.getByTestId("agent-workspace-step-build").click();
    await expect(page).toHaveURL(/\/build/);
    await expect(page.getByText(/Build/i).first()).toBeVisible({ timeout: 20_000 });
  });
});
