import { test, expect } from "@playwright/test";

/**
 * ZOAS-in-ZECT workflow smoke: Repo Workspace → Lattice → Mentrix bugfix path.
 * Uses bugfix mode with workspace fields (no live clone required in CI).
 */
test.describe("ZOAS workflow", () => {
  test("Repo Workspace page loads clone form", async ({ page }) => {
    await page.goto("/repo-workspace");
    await expect(page.getByRole("heading", { name: "Repo Workspace", exact: true })).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByRole("button", { name: /Clone Repository/i })).toBeVisible();
  });

  test("Mentrix bugfix mode exposes workspace and project key fields", async ({ page }) => {
    await page.goto("/mentrix");
    await expect(page.getByTestId("mentrix-page")).toBeVisible();
    await page.getByTestId("mentrix-mode").selectOption("bugfix");
    await expect(page.getByTestId("mentrix-workspace")).toBeVisible();
    await expect(page.getByTestId("mentrix-project-key")).toBeVisible();
    await page.getByTestId("mentrix-workspace").fill("C:\\Users\\karuppk\\zect-workspaces\\zinnia\\zoas");
    await page.getByTestId("mentrix-project-key").fill("zinnia-zoas");
    await page.getByTestId("mentrix-goal").fill("ZOAS workflow smoke: verify bugfix gate rail");
    await page.getByTestId("mentrix-engage").click();
    await expect(page.getByTestId("mentrix-chat")).toBeVisible();
    await expect(page.getByTestId("mentrix-run-status")).toContainText(
      /completed|awaiting|needs_human|running|approved|failed/i,
      { timeout: 120_000 },
    );
    await expect(page.getByTestId("mentrix-gates")).toBeVisible();
    await expect(page.getByTestId("mentrix-step-lattice")).toBeVisible();
  });

  test("Blueprint From Lattice mode available after workflow", async ({ page }) => {
    await page.goto("/blueprint");
    await page.getByRole("button", { name: /From Lattice/i }).click();
    await expect(page.getByTestId("blueprint-lattice-mode")).toBeVisible();
    await page.getByTestId("blueprint-lattice-key").fill("zinnia-zoas");
  });
});
