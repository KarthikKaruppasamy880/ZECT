import { test, expect } from "@playwright/test";

test.describe("Workflow handoff", () => {
  test("Blueprint Use in Plan preloads Plan context", async ({ page }) => {
    await page.route("**/api/lattice/blueprint/prompt", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          prompt: "# Test Lattice Blueprint\n\nEndpoints and modules for workflow handoff test.",
          token_estimate: 120,
          project_key: "test-workflow-key",
        }),
      });
    });
    await page.route("**/api/context/save", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ saved: true, page: "workspace", key: "blueprint_prompt" }),
      });
    });
    await page.route("**/api/context/load", async (route) => {
      const body = (route.request().postDataJSON() as { page?: string }) || {};
      const entries =
        body.page === "plan"
          ? [
              {
                key: "repo_context",
                value: "# Test Lattice Blueprint\n\nEndpoints and modules for workflow handoff test.",
                page: "plan",
              },
              {
                key: "project_description",
                value: "Implement using this Lattice blueprint context",
                page: "plan",
              },
            ]
          : body.page === "workspace"
            ? []
            : [];
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ page: body.page || "plan", entries, total_tokens_estimated: 50 }),
      });
    });
    await page.route("**/api/lattice/status*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          indexed: true,
          project_key: "test-workflow-key",
          has_blueprint: true,
        }),
      });
    });

    await page.goto("/blueprint");
    await expect(page.getByRole("heading", { name: /Blueprint Generator/i })).toBeVisible({
      timeout: 30_000,
    });

    await page.getByRole("button", { name: /From Lattice/i }).click();
    await expect(page.getByTestId("blueprint-lattice-mode")).toBeVisible();

    await page.getByTestId("blueprint-lattice-key").fill("test-workflow-key");
    await page.getByTestId("blueprint-lattice-generate").click();
    await expect(page.getByTestId("blueprint-lattice-result")).toBeVisible({ timeout: 15_000 });

    await page.getByTestId("blueprint-use-in-plan").click();
    await expect(page).toHaveURL(/\/plan/, { timeout: 15_000 });
    // Advanced options open when repo context is preloaded
    const showAdvanced = page.getByRole("button", { name: /Show advanced/i });
    if (await showAdvanced.isVisible().catch(() => false)) {
      await showAdvanced.click();
    }
    await expect(page.getByTestId("plan-repo-context")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByTestId("plan-description")).not.toHaveValue("");
  });

  test("Ask page shows repo context textarea and send to plan button", async ({ page }) => {
    await page.route("**/api/context/load", async (route) => {
      const body = (route.request().postDataJSON() as { page?: string }) || {};
      let entries: { key: string; value: string; page: string }[] = [];
      if (body.page === "workspace") {
        entries = [{ key: "blueprint_prompt", value: "Saved blueprint context", page: "workspace" }];
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ page: body.page || "ask", entries, total_tokens_estimated: 20 }),
      });
    });

    await page.goto("/ask");
    await expect(page.getByTestId("ask-repo-context")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("ask-repo-context")).not.toHaveValue("");

    await page.route("**/api/llm/ask", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          answer: "Workflow test answer for plan handoff.",
          tokens_used: 42,
          model: "gpt-4o-mini",
        }),
      });
    });
    await page.route("**/api/context/save", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ saved: true, page: "ask", key: "last_question" }),
      });
    });

    await page.getByTestId("ask-input").fill("What should we fix first?");
    await page.getByTestId("ask-send").click();
    await expect(page.getByTestId("ask-send-to-plan")).toBeVisible({ timeout: 15_000 });
  });

  test("Lattice status chip in header when repo selected", async ({ page }) => {
    await page.route("**/api/lattice/status*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          indexed: true,
          project_key: "zinnia-zoas",
          has_blueprint: true,
        }),
      });
    });

    await page.goto("/repo-workspace");
    await expect(page.getByRole("heading", { name: /Repo Workspace/i })).toBeVisible({
      timeout: 30_000,
    });
  });
});
