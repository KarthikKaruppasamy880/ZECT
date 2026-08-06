import { test, expect } from "@playwright/test";

/**
 * P0 spine smoke: Mentrix Delivery owns ship; confirm-plan / batch UI + Workspace deep link.
 * Uses route mocks so CI does not need a live Mentrix ForgeLoop.
 */
function mockRun(overrides: Record<string, unknown> = {}) {
  return {
    id: 9101,
    goal: "ZOAS spine smoke — fix auth retry",
    mode: "bugfix",
    status: "awaiting_batch_confirm",
    next_step: "await_human_batch",
    current_agent: "builder",
    batch_index: 0,
    batch_total: 2,
    batch_files: ["src/auth/retry.ts"],
    files_written: ["src/auth/retry.ts"],
    files_expected: ["src/auth/retry.ts", "tests/auth_retry.test.ts"],
    approved_at: null,
    pr_url: null,
    events: [
      { agent: "planner", phase: "plan", message: "Plan confirmed", next_step: "build" },
      { agent: "builder", phase: "build", message: "Batch 1 done", next_step: "await_human_batch" },
    ],
    gates: { plan_confirmed: true, incomplete_ok: true },
    result: {
      plan: {
        summary: "Fix ZOAS auth retry flake",
        files_expected: ["src/auth/retry.ts", "tests/auth_retry.test.ts"],
        steps: [{ title: "Patch retry", action: "edit", files: ["src/auth/retry.ts"] }],
      },
      batch_index: 0,
      batch_total: 2,
      batch_files: ["src/auth/retry.ts"],
      builder: {
        files_written: ["src/auth/retry.ts"],
        files_expected: ["src/auth/retry.ts", "tests/auth_retry.test.ts"],
      },
    },
    ...overrides,
  };
}

test.describe("ZOAS Mentrix Delivery spine smoke", () => {
  test("shows ship spine, batch confirm, and Workspace deep link", async ({ page }) => {
    const run = mockRun();
    await page.route("**/api/mentrix/agents", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ wake_phrases: ["Hey Mentrix"], roles: [], pipelines: {} }),
      });
    });
    await page.route("**/api/mentrix/runs/**", async (route) => {
      // Detail / action routes: /runs/9101, /runs/9101/confirm-batch, etc.
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(run),
      });
    });
    await page.route("**/api/mentrix/runs**", async (route) => {
      const method = route.request().method();
      const url = route.request().url();
      if (method === "GET" && /\/runs\/\d+/.test(url)) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(run),
        });
        return;
      }
      if (method === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([run]),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(run),
      });
    });

    await page.goto("/mentrix");
    await expect(page.getByTestId("mentrix-page")).toBeVisible();
    await expect(page.getByTestId("mentrix-spine-hint")).toContainText(/Ship here/i);
    await expect(page.getByTestId("mentrix-run-9101")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("mentrix-run-9101")).toContainText("awaiting_batch_confirm");

    const [getRun] = await Promise.all([
      page.waitForResponse(
        (res) => res.request().method() === "GET" && /\/api\/mentrix\/runs\/9101/.test(res.url()),
        { timeout: 15_000 },
      ),
      page.getByTestId("mentrix-run-9101").click(),
    ]);
    expect(getRun.status(), await getRun.text()).toBe(200);
    await expect(page.getByTestId("mentrix-run-owns-build")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("mentrix-batch-confirm")).toBeVisible();
    const ws = page.getByTestId("mentrix-open-workspace");
    await expect(ws).toBeVisible();
    await expect(ws).toHaveAttribute("href", /\/workspace\?.*run=9101/);
  });

  test("Agent Workspace and Build handoff point at Mentrix Delivery", async ({ page }) => {
    await page.goto("/ask");
    await expect(page.getByTestId("agent-workspace-spine-hint")).toContainText(/Ship here/i);
    await page.goto("/build");
    await expect(page.getByTestId("build-mentrix-handoff")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("build-continue-mentrix")).toHaveAttribute("href", /\/mentrix\?goal=/);
  });
});
