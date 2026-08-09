import { test, expect } from "@playwright/test";

test.describe("Agent Workspace shell", () => {
  test("Mentrix shows shared workspace rail; Agent Mode gated by default", async ({ page }) => {
    await page.goto("/mentrix");
    await expect(page.getByTestId("agent-workspace")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("agent-workspace-rail")).toBeVisible();
    await expect(page.getByTestId("agent-workspace-step-mentrix")).toBeVisible();
    await expect(page.getByTestId("mentrix-page")).toBeVisible();
    await expect(page.getByTestId("agent-workspace-step-agent")).toHaveCount(0);

    await page.goto("/agent-mode");
    await expect(page.getByTestId("agent-mode-gated")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("agent-mode-page")).toHaveCount(0);
  });

  test("Settings Advanced enables Agent Mode in rail and page", async ({ page }) => {
    await page.goto("/settings");
    await expect(page.getByTestId("settings-advanced")).toBeVisible({ timeout: 30_000 });
    await page.getByTestId("settings-agent-mode-toggle").click();

    await page.goto("/mentrix");
    await expect(page.getByTestId("agent-workspace-step-agent")).toBeVisible({ timeout: 15_000 });

    await page.goto("/agent-mode");
    await expect(page.getByTestId("agent-mode-page")).toBeVisible({ timeout: 30_000 });
  });

  test("Sidebar collapses phase tools into Agent Workspace entry", async ({ page }) => {
    await page.goto("/mentrix");
    await expect(page.getByTestId("agent-workspace")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("app-sidebar").getByRole("link", { name: "Agent Workspace" })).toBeVisible();
    // Ask/Plan/Build live in Agent Workspace rail — not app sidebar
    await expect(page.getByTestId("app-sidebar").getByRole("link", { name: "Ask" })).toHaveCount(0);
    await expect(page.getByTestId("app-sidebar").getByRole("link", { name: "Plan" })).toHaveCount(0);
    await expect(page.getByTestId("app-sidebar").getByRole("link", { name: "Build" })).toHaveCount(0);
    await expect(page.getByTestId("agent-workspace-step-ask")).toBeVisible();
    await expect(page.getByTestId("agent-workspace-step-plan")).toBeVisible();
  });
});
