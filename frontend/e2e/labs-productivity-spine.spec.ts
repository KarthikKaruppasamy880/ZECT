import { test, expect } from "@playwright/test";

test.describe("Labs productivity spine", () => {
  test("primary Labs links visible; More Labs disclosure; Demo Mode gone", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("link", { name: "Skills Engine" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Playbooks" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Knowledge Base" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Scheduled Tasks" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Memory System" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Permissions" })).toBeVisible();

    // Experimental pages not in primary Labs list
    await expect(page.getByRole("link", { name: "Dream Engine" })).toHaveCount(0);
    await expect(page.getByRole("link", { name: "File Explorer" })).toHaveCount(0);

    await page.getByTestId("sidebar-labs-more").click();
    await expect(page.getByRole("link", { name: "Architecture" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Security Incidents" })).toBeVisible();

    await page.goto("/settings");
    await expect(page.getByTestId("settings-demo-mode-toggle")).toHaveCount(0);
    await expect(page.getByText("Demo Mode")).toHaveCount(0);
  });

  test("Knowledge Base and Scheduled Tasks pages load", async ({ page }) => {
    await page.goto("/knowledge-base");
    await expect(page.getByRole("heading", { name: /Knowledge Base/i })).toBeVisible();

    await page.goto("/scheduled-tasks");
    await expect(page.getByTestId("scheduled-tasks-page")).toBeVisible();
    await page.getByRole("button", { name: /New Schedule/i }).click();
    await expect(page.getByTestId("schedule-task-type")).toBeVisible();
    await expect(page.getByTestId("schedule-playbook")).toBeVisible();
  });

  test("Playbooks page and Architecture (no competitor matrix)", async ({ page }) => {
    await page.goto("/playbooks");
    await expect(page.getByTestId("playbooks-page")).toBeVisible();

    await page.goto("/tool-comparison");
    await expect(page.getByTestId("architecture-guide")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Architecture" })).toBeVisible();
    await expect(page.getByText(/Comparison matrix/i)).toHaveCount(0);
  });

  test("Skills Use skill → New Project deep link", async ({ page }) => {
    await page.goto("/skills-engine");
    await expect(page.getByRole("heading", { name: /Skills Engine/i })).toBeVisible();
    const useBtn = page.getByTestId("skill-use-new-project").first();
    if (await useBtn.count()) {
      await useBtn.click();
      await expect(page).toHaveURL(/\/projects\/new\?.*skill_id=/);
    }
  });
});
