import { test, expect } from "@playwright/test";

test.describe("Agent Workspace shell", () => {
  test("Mentrix shows shared workspace rail; no Agent Mode step exists", async ({ page }) => {
    await page.goto("/mentrix");
    await expect(page.getByTestId("agent-workspace")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("agent-workspace-rail")).toBeVisible();
    await expect(page.getByTestId("agent-workspace-step-mentrix")).toBeVisible();
    await expect(page.getByTestId("mentrix-page")).toBeVisible();
    await expect(page.getByTestId("agent-workspace-step-agent")).toHaveCount(0);
  });

  test("legacy /agent-mode hard-redirects to the Developer Workspace, no flag brings it back", async ({ page }) => {
    // The legacy Agent Workspace (a second, disconnected coding engine) is
    // retired -- /agent-mode always redirects, there is no feature flag or
    // Settings toggle left that could resurrect it.
    await page.goto("/agent-mode");
    await expect(page).toHaveURL(/\/workspace(\?|$)/, { timeout: 30_000 });
    await expect(page.getByTestId("developer-workspace")).toBeVisible({ timeout: 30_000 });
  });

  test("Settings no longer has an Agent Mode toggle", async ({ page }) => {
    await page.goto("/settings");
    await expect(page.getByTestId("settings-advanced")).toHaveCount(0);
    await expect(page.getByTestId("settings-agent-mode-toggle")).toHaveCount(0);
  });

  test("Sidebar collapses phase tools into Agent Workspace entry", async ({ page }) => {
    await page.goto("/mentrix");
    await expect(page.getByTestId("agent-workspace")).toBeVisible({ timeout: 30_000 });
    // Agent Workspace is hidden from primary nav (superseded by Developer
    // cockpit) — the route remains live, just not a sidebar entry.
    await expect(page.getByTestId("app-sidebar").getByRole("link", { name: "Agent Workspace", exact: true })).toHaveCount(0);
    // Phase tools live in Agent Workspace rail — not as Ask/Plan/Build sidebar entries
    await expect(page.getByTestId("app-sidebar").getByRole("link", { name: "Ask", exact: true })).toHaveCount(0);
    await expect(page.getByTestId("app-sidebar").getByRole("link", { name: "Plan", exact: true })).toHaveCount(0);
    await expect(page.getByTestId("app-sidebar").getByRole("link", { name: "Build", exact: true })).toHaveCount(0);
    await expect(page.getByTestId("agent-workspace-step-ask")).toBeVisible();
    await expect(page.getByTestId("agent-workspace-step-plan")).toBeVisible();
  });
});
