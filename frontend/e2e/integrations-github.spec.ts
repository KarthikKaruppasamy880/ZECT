import { test, expect } from "@playwright/test";

test.describe("Integrations GitHub readiness", () => {
  test("GitHub + Zoom/Presenton cards render with mocked companion status", async ({ page }) => {
    await page.route("**/api/mentrix/companion/integrations", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          slack: false,
          jira: true,
          openai: true,
          github: true,
          presenton: true,
          presenton_base_url: "http://127.0.0.1:5000",
          zoom_join_url_configured: false,
          zoom_desktop_path_configured: false,
        }),
      });
    });
    await page.route("**/api/jira/status", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ configured: true, base_url: "https://example.atlassian.net", email: "a@b.c", is_active: true, linked_tickets: 0 }),
      });
    });
    await page.route("**/api/slack/status", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ configured: false }),
      });
    });
    await page.route("**/api/mcp/**", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    });

    await page.goto("/integrations");
    await expect(page.getByTestId("integrations-page")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("integrations-github-card")).toBeVisible();
    await expect(page.getByTestId("github-ready")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByTestId("integrations-zoom-card")).toContainText(/Presenton/i);
  });
});
