import { test, expect } from "@playwright/test";

test.describe("Mentrix incident runbook", () => {
  test("Incident deep link shows runbook panel", async ({ page }) => {
    await page.goto("/mentrix-home?incident=1");
    await expect(page.getByTestId("mentrix-companion-page")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("incident-runbook-panel")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByTestId("incident-issue-key")).toBeVisible();
    await expect(page.getByTestId("incident-load")).toBeVisible();
  });

  test("Load issue then handoff to Delivery", async ({ page }) => {
    await page.route("**/api/mcp/execute", async (route) => {
      const body = route.request().postDataJSON() as { tool_name?: string };
      if (body?.tool_name === "get_issue") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            server_id: "jira",
            tool_name: "get_issue",
            status: "success",
            result: {
              key: "INC-99",
              fields: {
                summary: "Checkout latency spike",
                status: { name: "Open" },
                issuetype: { name: "Incident" },
                description: "p99 latency exceeded SLA",
              },
            },
          }),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "success", result: { data: [] } }),
      });
    });

    await page.goto("/mentrix-home?incident=1");
    await expect(page.getByTestId("incident-runbook-panel")).toBeVisible({ timeout: 30_000 });
    await page.getByTestId("incident-issue-key").fill("INC-99");
    await page.getByTestId("incident-load").click();
    await expect(page.getByTestId("incident-issue-card")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByTestId("incident-issue-card")).toContainText("INC-99");
    await page.getByTestId("incident-use-delivery").click();
    await expect(page).toHaveURL(/\/mentrix/, { timeout: 15_000 });
    await expect(page.getByTestId("mentrix-page")).toBeVisible({ timeout: 30_000 });
    const goal = page.getByTestId("mentrix-goal");
    await expect(goal).toBeVisible();
    await expect(goal).toHaveValue(/INC-99|Checkout latency/i);
  });

  test("Sidebar Incident Runbook link", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: /Incident Runbook/i }).click();
    await expect(page).toHaveURL(/incident=1/, { timeout: 15_000 });
    await expect(page.getByTestId("incident-runbook-panel")).toBeVisible({ timeout: 30_000 });
  });
});
