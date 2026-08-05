import { test, expect } from "@playwright/test";

test.describe("Mentrix smoke", () => {
  test("Lattice page loads", async ({ page }) => {
    await page.goto("/lattice");
    await expect(page.getByTestId("lattice-page")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Lattice" })).toBeVisible();
  });

  test("Mentrix page engage run", async ({ page }) => {
    await page.goto("/mentrix");
    await expect(page.getByTestId("mentrix-page")).toBeVisible();
    await expect(page.getByTestId("mentrix-step-rail")).toBeVisible();
    await expect(page.getByTestId("mentrix-step-lattice")).toBeVisible();
    await expect(page.getByTestId("mentrix-step-pr")).toBeVisible();
    await expect(page.getByTestId("mentrix-empty-state")).toContainText(/Clone or Lattice-ingest/i);
    await page.getByTestId("mentrix-goal").fill("Smoke test: summarize delivery gates");
    await page.getByTestId("mentrix-mode").selectOption("chat");
    await page.getByTestId("mentrix-engage").click();
    await expect(page.getByTestId("mentrix-chat")).toBeVisible();
    await expect(page.getByTestId("mentrix-run-status")).toContainText(/completed|awaiting|needs_human|running/i, {
      timeout: 45_000,
    });
    await expect(page.getByTestId("mentrix-events")).toBeVisible();
  });

  test("Blueprint From Lattice mode is available", async ({ page }) => {
    await page.goto("/blueprint");
    await page.getByRole("button", { name: /From Lattice/i }).click();
    await expect(page.getByTestId("blueprint-lattice-mode")).toBeVisible();
    await expect(page.getByTestId("blueprint-lattice-key")).toBeVisible();
  });

  test("Snippet Review banner clarifies Mentrix delivery", async ({ page }) => {
    await page.goto("/review");
    await expect(page.getByTestId("snippet-review-banner")).toBeVisible();
    await expect(page.getByRole("heading", { name: /Snippet Review/i })).toBeVisible();
  });

  test("Workflow sidebar links to Agent Workspace", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("link", { name: /Agent Workspace/i })).toBeVisible();
    await page.getByRole("link", { name: /Agent Workspace/i }).click();
    await expect(page.getByTestId("mentrix-page")).toBeVisible();
  });

  test("Mentrix upgrade mode chat + gates", async ({ page }) => {
    await page.goto("/mentrix");
    await expect(page.getByTestId("mentrix-page")).toBeVisible();
    await page.getByTestId("mentrix-mode").selectOption("upgrade");
    await page
      .getByTestId("mentrix-goal")
      .fill("Upgrade smoke: port sample module python to typescript with API evals");
    await page.getByTestId("mentrix-engage").click();
    await expect(page.getByTestId("mentrix-live-status")).toBeVisible();
    await expect(page.getByTestId("mentrix-chat")).toBeVisible();
    await expect(page.getByTestId("mentrix-error").or(page.getByTestId("mentrix-run-status"))).toBeVisible({
      timeout: 90_000,
    });
    if (await page.getByTestId("mentrix-error").isVisible()) {
      throw new Error(await page.getByTestId("mentrix-error").innerText());
    }
    await expect(page.getByTestId("mentrix-run-status")).toContainText(
      /completed|awaiting|needs_human|running|approved/i,
      { timeout: 90_000 }
    );
    await expect(page.getByTestId("mentrix-gates")).toContainText(/lint_ok|api_eval_ok|incomplete_ok/i);
  });

  test("Sandbox gate shows blockers for low score", async ({ page }) => {
    await page.goto("/sandbox");
    await expect(page.getByTestId("sandbox-page")).toBeVisible();
    // Quality score input — leave default or set low
    const scoreInput = page.locator('input[type="number"]').first();
    await scoreInput.fill("40");
    const criticalInput = page.locator('input[type="number"]').nth(1);
    await criticalInput.fill("2");
    await page.getByTestId("sandbox-check").click();
    await expect(page.getByTestId("sandbox-result")).toContainText(/hard-blocked|Ready to open PR/i, {
      timeout: 30_000,
    });
  });

  test("Integrations shows MCP adapters", async ({ page }) => {
    await page.goto("/integrations");
    await expect(page.getByRole("heading", { name: /Integrations/i })).toBeVisible();
    await expect(page.getByText(/MCP|Jira|Slack/i).first()).toBeVisible();
    await expect(page.getByText(/Playwright|Datadog|GitHub/i).first()).toBeVisible();
  });
});
