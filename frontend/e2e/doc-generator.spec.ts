import { test, expect } from "@playwright/test";

test.describe("Doc Generator", () => {
  test("help text + generate button; mocked API smoke", async ({ page }) => {
    await page.route("**/api/analysis/docs/**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          repo_name: "zoas",
          owner: "zinnia",
          sections: [
            { title: "Overview", content: "# Overview\nMocked doc section for smoke." },
          ],
          total_tokens: 42,
        }),
      });
    });

    await page.goto("/doc-generator");
    await expect(page.getByTestId("doc-generator-help")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("doc-generator-help")).toContainText(/GITHUB_TOKEN|Mentrix Delivery|Lattice/i);
    await page.getByTestId("doc-generator-owner").fill("zinnia");
    await page.getByTestId("doc-generator-repo").fill("zoas");
    await page.getByTestId("doc-generator-submit").click();
    await expect(page.getByText(/Documentation:\s*zoas/i)).toBeVisible({ timeout: 15_000 });
  });
});
