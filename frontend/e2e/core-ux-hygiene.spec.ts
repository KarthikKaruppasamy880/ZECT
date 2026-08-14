/**
 * UX1/UX2/UX5 headed smoke: Projects hygiene, WorkItems, sample process, Developer toggles.
 */
import { test, expect, type Page } from "@playwright/test";
import { loadEnvCreds } from "./helpers/env";

async function ensureLoggedIn(page: Page) {
  const { username, password } = loadEnvCreds();
  await page.goto("/");
  const loginVisible = await page.getByTestId("login-username").isVisible().catch(() => false);
  const token = await page.evaluate(() => localStorage.getItem("zect_token"));
  if (loginVisible || !token) {
    await expect(page.getByTestId("login-username")).toBeVisible({ timeout: 15_000 });
    await page.getByTestId("login-username").fill(username);
    await page.getByTestId("login-password").fill(password);
    await page.getByTestId("login-submit").click();
    await expect(page.getByTestId("login-submit")).toBeHidden({ timeout: 30_000 });
  }
}

test.describe("Core UX hygiene", () => {
  test("Projects search, WorkItems sample, Processes sample, Developer layout toggles", async ({ page }) => {
    await ensureLoggedIn(page);

    await page.goto("/projects");
    await expect(page.getByTestId("projects-page")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId("projects-search")).toBeVisible();
    await page.getByTestId("projects-search").fill("zzz-no-such-project");
    await expect(page.getByText("Phase6", { exact: false })).toHaveCount(0);

    await page.goto("/work-items");
    await expect(page.getByTestId("work-items-page")).toBeVisible();
    await page.getByTestId("work-items-sample").click();
    await expect(page.getByText("Fix Failed Order Validation")).toBeVisible({ timeout: 20_000 });

    await page.goto("/fabric");
    await expect(page.getByTestId("process-sample-card")).toBeVisible();
    await expect(page.getByTestId("process-sample-create")).toBeVisible();
    await expect(page.getByTestId("process-ingest-form")).toBeVisible();

    await page.goto("/workspace");
    await expect(page.getByTestId("developer-workspace")).toBeVisible({ timeout: 20_000 });
    await page.getByTestId("workspace-toggle-explorer").click();
    await page.getByTestId("workspace-toggle-agent").click();
    await page.getByTestId("workspace-toggle-bottom").click();
    await expect(page.getByTestId("workspace-reset-layout")).toBeVisible();
  });
});
