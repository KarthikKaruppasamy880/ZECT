import { test, expect } from "@playwright/test";

test.describe("Ask clear blueprint context", () => {
  test("Clear context empties blueprint and does not refill after remount", async ({ page }) => {
    await page.route("**/api/context/load", async (route) => {
      const body = (route.request().postDataJSON() as { page?: string; keys?: string[] }) || {};
      const entries =
        body.page === "workspace"
          ? [{ key: "blueprint_prompt", value: "# Sticky blueprint for clear test", page: "workspace" }]
          : [];
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ page: body.page || "ask", entries, total_tokens_estimated: 10 }),
      });
    });
    let clearedAsk = false;
    await page.route("**/api/context/save", async (route) => {
      const body = (route.request().postDataJSON() as { page?: string; key?: string; value?: string }) || {};
      if (body.page === "workspace" && body.key === "blueprint_prompt" && body.value === "") {
        clearedAsk = true;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ saved: true, page: body.page, key: body.key }),
      });
    });
    await page.route("**/api/context/clear/**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ cleared: true, page: "ask" }),
      });
    });

    await page.goto("/ask");
    await expect(page.getByTestId("ask-repo-context")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("ask-repo-context")).toHaveValue(/Sticky blueprint/i, {
      timeout: 10_000,
    });

    await page.getByTestId("ask-clear-context").click();
    await expect(page.getByTestId("ask-repo-context")).toHaveValue("");
    await expect.poll(() => clearedAsk).toBeTruthy();

    await page.route("**/api/context/load", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ page: "workspace", entries: [], total_tokens_estimated: 0 }),
      });
    });
    await page.reload();
    await expect(page.getByTestId("ask-repo-context")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("ask-repo-context")).toHaveValue("");
  });
});
